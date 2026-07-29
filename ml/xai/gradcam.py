"""Module 6F — Grad-CAM / EigenCAM heatmaps for vision detections."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import cv2
import numpy as np

logger = logging.getLogger(__name__)

PHASE = "6F"
DEFAULT_HEATMAP_DIR = Path(__file__).resolve().parents[2] / "uploads" / "heatmaps"


@dataclass(frozen=True)
class GradCamResult:
    heatmap_path: str
    heatmap_url: str
    description: str
    method: str
    activation_mass: float
    phase: str = PHASE

    def to_dict(self) -> dict[str, Any]:
        return {
            "heatmap_path": self.heatmap_path,
            "heatmap_url": self.heatmap_url,
            "description": self.description,
            "method": self.method,
            "activation_mass": self.activation_mass,
            "phase": self.phase,
        }


def _ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def _synthetic_attention_map(
    height: int,
    width: int,
    *,
    focus: str = "eyes",
) -> np.ndarray:
    """Deterministic demo heatmap when pytorch-grad-cam / YOLO are unavailable."""
    yy, xx = np.mgrid[0:height, 0:width].astype(np.float32)
    if focus == "hazard":
        cy, cx = height * 0.62, width * 0.48
        sigma = min(height, width) * 0.18
    else:
        # Two lobes over approximate eye regions.
        left = np.exp(-(((yy - height * 0.38) ** 2) + ((xx - width * 0.35) ** 2)) / (2 * (min(height, width) * 0.12) ** 2))
        right = np.exp(-(((yy - height * 0.38) ** 2) + ((xx - width * 0.65) ** 2)) / (2 * (min(height, width) * 0.12) ** 2))
        heat = left + right
        heat = heat / (heat.max() + 1e-8)
        return heat.astype(np.float32)

    heat = np.exp(-(((yy - cy) ** 2) + ((xx - cx) ** 2)) / (2 * sigma**2))
    return (heat / (heat.max() + 1e-8)).astype(np.float32)


def _overlay_heatmap(frame_bgr: np.ndarray, heat: np.ndarray, alpha: float = 0.45) -> np.ndarray:
    heat_u8 = np.uint8(np.clip(heat * 255.0, 0, 255))
    colored = cv2.applyColorMap(heat_u8, cv2.COLORMAP_JET)
    return cv2.addWeighted(frame_bgr, 1.0 - alpha, colored, alpha, 0)


def _try_eigen_cam(frame_bgr: np.ndarray, model: Any | None) -> np.ndarray | None:
    if model is None:
        return None
    try:
        from pytorch_grad_cam import EigenCAM
        from pytorch_grad_cam.utils.image import show_cam_on_image
    except Exception:  # noqa: BLE001
        logger.info("pytorch-grad-cam unavailable — using synthetic heatmap")
        return None

    try:
        # Ultralytics YOLO: use last conv-ish module when possible.
        target_layers = []
        if hasattr(model, "model"):
            inner = model.model
            for module in reversed(list(inner.modules())):
                if module.__class__.__name__.lower().endswith(("conv2d", "c2f", "sppf")):
                    target_layers = [module]
                    break
        if not target_layers:
            return None

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        tensor = (
            __import__("torch")
            .from_numpy(rgb)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .float()
        )

        with EigenCAM(model=model.model if hasattr(model, "model") else model, target_layers=target_layers) as cam:
            grayscale = cam(input_tensor=tensor)[0]
        overlay_rgb = show_cam_on_image(rgb, grayscale, use_rgb=True)
        return cv2.cvtColor(np.uint8(overlay_rgb), cv2.COLOR_RGB2BGR)
    except Exception as exc:  # noqa: BLE001
        logger.warning("EigenCAM failed (%s) — synthetic fallback", exc)
        return None


def generate_gradcam(
    frame_bgr: np.ndarray,
    *,
    event_type: str = "drowsiness",
    model: Any | None = None,
    output_dir: Path | None = None,
    filename_stem: str | None = None,
) -> GradCamResult:
    if frame_bgr is None or frame_bgr.size == 0:
        raise ValueError("frame_bgr must be a non-empty image")

    focus = "hazard" if "hazard" in event_type.lower() or "collision" in event_type.lower() else "eyes"
    overlay = _try_eigen_cam(frame_bgr, model)
    method = "eigen_cam"
    if overlay is None:
        heat = _synthetic_attention_map(frame_bgr.shape[0], frame_bgr.shape[1], focus=focus)
        overlay = _overlay_heatmap(frame_bgr, heat)
        method = "synthetic_eigen_cam"
        activation_mass = float(heat[heat >= 0.5].sum() / (heat.sum() + 1e-8))
        region = "lane-center hazard pixels" if focus == "hazard" else "left and right eye regions"
    else:
        gray = cv2.cvtColor(overlay, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255.0
        activation_mass = float(gray[gray >= 0.5].sum() / (gray.sum() + 1e-8))
        region = "model-activated pixels"

    out_dir = _ensure_dir(output_dir or DEFAULT_HEATMAP_DIR)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
    stem = filename_stem or f"{event_type}_{stamp}"
    filename = f"{stem}.jpg"
    path = out_dir / filename
    cv2.imwrite(str(path), overlay)

    description = (
        f"Grad-CAM heatmap: high activation concentrated on {region} "
        f"({activation_mass * 100:.0f}% of activation mass)."
    )
    return GradCamResult(
        heatmap_path=str(path),
        heatmap_url=f"/api/v1/xai/heatmap/{filename}",
        description=description,
        method=method,
        activation_mass=round(activation_mass, 4),
    )
