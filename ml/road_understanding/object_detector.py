"""Optional YOLOv8m road-object detection for box-based downstream modules.

Until `ml/models/road_yolov8m_best.pt` exists, falls back to Ultralytics
`yolov8m.pt` (COCO) filtered to road-relevant classes.

Module 2B itself is semantic segmentation; see ``road_segmenter.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ml.common.gpu_detector import get_inference_device
from ml.road_understanding.config import (
    COCO_ROAD_CLASS_IDS,
    ROAD_CLASS_NAMES,
    YOLO_ROAD_CONFIDENCE,
    YOLO_ROAD_IOU,
    YOLO_ROAD_MODEL_PATH,
    resolve_yolo_road_weights,
    yolo_road_model_ready,
)

# Map COCO class names → BDD-style taxonomy used by later modules
_COCO_TO_ROAD: dict[str, str] = {
    "person": "pedestrian",
    "bicycle": "bicycle",
    "car": "car",
    "motorcycle": "motorcycle",
    "bus": "bus",
    "train": "train",
    "truck": "truck",
    "traffic light": "traffic light",
    "stop sign": "traffic sign",
}


@dataclass
class RoadDetection:
    class_name: str
    confidence: float
    bbox_xyxy: list[float] = field(default_factory=list)
    class_id: int | None = None


@dataclass
class RoadDetections:
    detections: list[RoadDetection] = field(default_factory=list)
    model_loaded: bool = False
    using_fallback: bool = False
    weights_path: str | None = None
    message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "detections": [
                {
                    "class": d.class_name,
                    "confidence": d.confidence,
                    "bbox": d.bbox_xyxy,
                    "class_id": d.class_id,
                }
                for d in self.detections
            ],
            "count": len(self.detections),
            "model_loaded": self.model_loaded,
            "using_fallback": self.using_fallback,
            "weights_path": self.weights_path,
            "message": self.message,
        }


def _normalize_class(name: str) -> str:
    return " ".join(name.lower().replace("_", " ").replace("-", " ").split())


def _map_class_name(raw: str, *, using_fallback: bool) -> str:
    name = _normalize_class(raw)
    if using_fallback:
        return _COCO_TO_ROAD.get(name, name)
    return name


class YOLORoadDetector:
    """
    Optional road-object detector for tracking, depth, and traffic-light modules.

    Place fine-tuned weights at:
      ml/models/road_yolov8m_best.pt
    Train with:
      notebooks/train_road_yolo_colab.ipynb
      or python -m ml.training.train_road_yolo
    """

    def __init__(
        self,
        model_path: str | Path | None = None,
        *,
        conf: float = YOLO_ROAD_CONFIDENCE,
        iou: float = YOLO_ROAD_IOU,
        device: str | int | None = None,
        auto_load: bool = True,
    ) -> None:
        if model_path is None:
            self.weights_ref = resolve_yolo_road_weights()
            self.using_fallback = not yolo_road_model_ready()
        else:
            path = Path(model_path)
            if path.is_file() and path.stat().st_size > 0:
                self.weights_ref = str(path)
                self.using_fallback = False
            else:
                # Explicit missing path → still allow COCO fallback for demos
                self.weights_ref = resolve_yolo_road_weights()
                self.using_fallback = not yolo_road_model_ready()

        self.conf = conf
        self.iou = iou
        self.device = get_inference_device(device)
        self._model = None
        self._names: dict[int, str] = {
            i: name for i, name in enumerate(ROAD_CLASS_NAMES)
        }
        self._load_error: str | None = None

        if auto_load:
            self._load_model()

    def _load_model(self) -> None:
        try:
            from ultralytics import YOLO

            self._model = YOLO(self.weights_ref)
            names = getattr(self._model, "names", None)
            if isinstance(names, dict) and names:
                self._names = {int(k): str(v) for k, v in names.items()}
            self._load_error = None
        except Exception as exc:  # noqa: BLE001
            self._model = None
            self._load_error = str(exc)

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    def detect(self, frame: np.ndarray) -> RoadDetections:
        if frame is None or getattr(frame, "size", 0) == 0:
            return RoadDetections(
                model_loaded=self.is_ready,
                using_fallback=self.using_fallback,
                weights_path=self.weights_ref,
                message="Empty frame",
            )

        if not self.is_ready:
            return RoadDetections(
                model_loaded=False,
                using_fallback=self.using_fallback,
                weights_path=self.weights_ref,
                message=(
                    self._load_error
                    or (
                        f"Could not load weights ({self.weights_ref}). "
                        "Train BDD100K with notebooks/train_road_yolo_colab.ipynb "
                        f"and copy best.pt → {YOLO_ROAD_MODEL_PATH}"
                    )
                ),
            )

        kwargs: dict[str, Any] = {
            "verbose": False,
            "device": self.device,
            "conf": self.conf,
            "iou": self.iou,
        }
        if self.using_fallback:
            kwargs["classes"] = list(COCO_ROAD_CLASS_IDS)

        results = self._model(frame, **kwargs)
        detections: list[RoadDetection] = []

        for result in results:
            if result.boxes is None:
                continue
            for box in result.boxes:
                cls_id = int(box.cls.item())
                conf = float(box.conf.item())
                raw_name = self._names.get(cls_id, str(cls_id))
                class_name = _map_class_name(raw_name, using_fallback=self.using_fallback)
                xyxy = [float(x) for x in box.xyxy[0].tolist()]
                detections.append(
                    RoadDetection(
                        class_name=class_name,
                        confidence=conf,
                        bbox_xyxy=xyxy,
                        class_id=cls_id,
                    )
                )

        msg = None
        if self.using_fallback:
            msg = (
                "Using COCO yolov8m.pt fallback — place the optional BDD "
                f"object-detector fine-tune at {YOLO_ROAD_MODEL_PATH.name}"
            )

        return RoadDetections(
            detections=detections,
            model_loaded=True,
            using_fallback=self.using_fallback,
            weights_path=self.weights_ref,
            message=msg,
        )


_detector: YOLORoadDetector | None = None


def get_road_detector() -> YOLORoadDetector:
    global _detector
    if _detector is None:
        _detector = YOLORoadDetector()
    return _detector


def detect_road_objects(frame: np.ndarray) -> RoadDetections:
    """Convenience wrapper using a process-wide lazy detector."""
    return get_road_detector().detect(frame)
