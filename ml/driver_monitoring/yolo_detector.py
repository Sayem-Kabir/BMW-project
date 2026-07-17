"""YOLOv8 driver-object detection — phone / smoking / no_seatbelt (Module 1D)."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ml.driver_monitoring.config import (
    YOLO_CLASS_NAMES,
    YOLO_DRIVER_MODEL_PATH,
    YOLO_PHONE_CONFIDENCE,
    YOLO_SEATBELT_CONFIDENCE,
    YOLO_SMOKING_CONFIDENCE,
    yolo_driver_model_ready,
)


@dataclass
class Detection:
    class_name: str
    confidence: float
    bbox_xyxy: list[float] = field(default_factory=list)


@dataclass
class DriverObjectDetections:
    phone_detected: bool = False
    smoking_detected: bool = False
    seatbelt_worn: bool = True  # True until no_seatbelt is detected
    detections: list[Detection] = field(default_factory=list)
    model_loaded: bool = False
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "phone_detected": self.phone_detected,
            "smoking_detected": self.smoking_detected,
            "seatbelt_worn": self.seatbelt_worn,
            "detections": [
                {
                    "class": d.class_name,
                    "confidence": d.confidence,
                    "bbox": d.bbox_xyxy,
                }
                for d in self.detections
            ],
            "model_loaded": self.model_loaded,
            "message": self.message,
        }


class YOLODriverDetector:
    """
    Inference wrapper for the Phase 1D fine-tuned YOLOv8n weights.

    Place trained weights at:
      ml/models/driver_monitor_best.pt

    Until that file exists, detect() returns empty results with model_loaded=False.
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        phone_conf: float = YOLO_PHONE_CONFIDENCE,
        smoking_conf: float = YOLO_SMOKING_CONFIDENCE,
        seatbelt_conf: float = YOLO_SEATBELT_CONFIDENCE,
        device: str | int | None = None,
    ) -> None:
        self.model_path = Path(model_path) if model_path else YOLO_DRIVER_MODEL_PATH
        self.phone_conf = phone_conf
        self.smoking_conf = smoking_conf
        self.seatbelt_conf = seatbelt_conf
        self.device = device
        self._model = None
        self._names: dict[int, str] = {
            i: name for i, name in enumerate(YOLO_CLASS_NAMES)
        }

        if self.model_path.is_file() and self.model_path.stat().st_size > 0:
            self._load_model()

    def _load_model(self) -> None:
        from ultralytics import YOLO

        self._model = YOLO(str(self.model_path))
        # Prefer names from the checkpoint when available
        names = getattr(self._model, "names", None)
        if isinstance(names, dict) and names:
            self._names = {int(k): str(v) for k, v in names.items()}

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def detect(self, frame: np.ndarray) -> DriverObjectDetections:
        if frame is None or frame.size == 0:
            return DriverObjectDetections(
                model_loaded=self.is_ready,
                message="Empty frame",
            )

        if not self.is_ready:
            return DriverObjectDetections(
                model_loaded=False,
                message=(
                    f"Weights missing at {self.model_path}. "
                    "Train on Kaggle (see ml/training/train_driver_yolo.py) "
                    "then copy best.pt to ml/models/driver_monitor_best.pt"
                ),
            )

        kwargs: dict[str, Any] = {"verbose": False}
        if self.device is not None:
            kwargs["device"] = self.device

        results = self._model(frame, **kwargs)
        detections: list[Detection] = []
        phone = smoking = no_seatbelt = False

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                class_name = self._names.get(cls_id, str(cls_id)).lower()
                xyxy = [float(x) for x in box.xyxy[0].tolist()]

                if class_name == "phone" and conf >= self.phone_conf:
                    phone = True
                    detections.append(Detection(class_name, conf, xyxy))
                elif class_name == "smoking" and conf >= self.smoking_conf:
                    smoking = True
                    detections.append(Detection(class_name, conf, xyxy))
                elif class_name in ("no_seatbelt", "no-seatbelt", "unbelted") and conf >= self.seatbelt_conf:
                    no_seatbelt = True
                    detections.append(Detection("no_seatbelt", conf, xyxy))

        return DriverObjectDetections(
            phone_detected=phone,
            smoking_detected=smoking,
            seatbelt_worn=not no_seatbelt,
            detections=detections,
            model_loaded=True,
        )


_detector: YOLODriverDetector | None = None


def get_yolo_detector() -> YOLODriverDetector:
    global _detector
    if _detector is None:
        _detector = YOLODriverDetector()
    return _detector


def detect_driver_objects(frame: np.ndarray) -> DriverObjectDetections:
    """Convenience wrapper using a process-wide lazy detector."""
    return get_yolo_detector().detect(frame)
