"""GPU detection for ML inference — works even when PyTorch is CPU-only.

Adapted from the Nitsol E-Surveillance GPUDetector pattern:
nvidia-smi → PyTorch CUDA → environment hints, then resolve an Ultralytics device.
"""

from __future__ import annotations

import logging
import os
import subprocess
from typing import Any

logger = logging.getLogger(__name__)


def _normalize_device(device: str | int) -> str:
    if isinstance(device, int):
        return f"cuda:{device}" if device >= 0 else "cpu"
    text = str(device).strip().lower()
    if text in {"cpu", "mps"}:
        return text
    if text.isdigit():
        return f"cuda:{text}"
    if text.startswith("cuda"):
        return text
    return text


class GPUDetector:
    """Multi-method GPU detector + inference device resolver."""

    def __init__(self) -> None:
        self._gpu_info: dict[str, Any] | None = None
        self._detected = False

    def detect_gpu_via_nvidia_smi(self) -> dict[str, Any] | None:
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total,driver_version",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode != 0 or not result.stdout.strip():
                return None
            line = result.stdout.strip().splitlines()[0]
            parts = [p.strip() for p in line.split(",")]
            if len(parts) < 3:
                return None
            return {
                "available": True,
                "name": parts[0],
                "memory_gb": float(parts[1]) / 1024.0,
                "driver_version": parts[2],
                "method": "nvidia-smi",
            }
        except FileNotFoundError:
            logger.debug("nvidia-smi not found in PATH")
        except subprocess.TimeoutExpired:
            logger.warning("nvidia-smi timed out")
        except Exception as exc:  # noqa: BLE001
            logger.debug("nvidia-smi detection failed: %s", exc)
        return None

    def detect_gpu_via_pytorch(self) -> dict[str, Any] | None:
        try:
            import torch

            if not torch.cuda.is_available() or torch.cuda.device_count() == 0:
                return None
            props = torch.cuda.get_device_properties(0)
            return {
                "available": True,
                "name": torch.cuda.get_device_name(0),
                "memory_gb": props.total_memory / (1024**3),
                "cuda_version": torch.version.cuda,
                "pytorch_version": torch.__version__,
                "device_count": torch.cuda.device_count(),
                "method": "pytorch",
            }
        except ImportError:
            logger.debug("PyTorch not installed")
        except Exception as exc:  # noqa: BLE001
            logger.debug("PyTorch GPU detection failed: %s", exc)
        return None

    def detect_gpu_via_environment(self) -> dict[str, Any] | None:
        cuda_visible = os.environ.get("CUDA_VISIBLE_DEVICES")
        if cuda_visible is not None:
            logger.debug("CUDA_VISIBLE_DEVICES=%s", cuda_visible)

        cuda_paths = [
            os.environ.get("CUDA_PATH"),
            os.environ.get("CUDA_HOME"),
            r"C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA",
        ]
        found = [p for p in cuda_paths if p and os.path.exists(p)]
        if not found:
            return None
        return {
            "available": True,
            "method": "environment",
            "cuda_paths": found,
        }

    def detect_gpu(self, *, force: bool = False) -> dict[str, Any]:
        if self._detected and self._gpu_info is not None and not force:
            return self._gpu_info

        logger.info("GPU detection — trying nvidia-smi, PyTorch, then environment")
        info: dict[str, Any] = {
            "available": False,
            "methods_tried": [],
            "detected_by": None,
        }

        nvidia = self.detect_gpu_via_nvidia_smi()
        info["methods_tried"].append("nvidia-smi")
        if nvidia:
            info.update(nvidia)
            info["detected_by"] = "nvidia-smi"
            self._gpu_info = info
            self._detected = True
            logger.info("GPU detected via nvidia-smi: %s", nvidia.get("name"))
            return info

        pytorch = self.detect_gpu_via_pytorch()
        info["methods_tried"].append("pytorch")
        if pytorch:
            info.update(pytorch)
            info["detected_by"] = "pytorch"
            self._gpu_info = info
            self._detected = True
            logger.info("GPU detected via PyTorch: %s", pytorch.get("name"))
            return info

        env = self.detect_gpu_via_environment()
        info["methods_tried"].append("environment")
        if env:
            info.update(env)
            info["detected_by"] = "environment"
            logger.info("CUDA toolkit paths found via environment")
        else:
            logger.warning(
                "No GPU detected (tried: %s)",
                ", ".join(info["methods_tried"]),
            )

        self._gpu_info = info
        self._detected = True
        return info

    def is_pytorch_cuda_enabled(self) -> tuple[bool, str | None]:
        try:
            import torch

            version = torch.__version__
            has_cuda = bool(torch.cuda.is_available()) and not (
                "+cpu" in version.lower()
            )
            return has_cuda, version
        except ImportError:
            return False, None
        except Exception:  # noqa: BLE001
            return False, None

    def get_cuda_version_from_system(self) -> str | None:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
            )
            if result.returncode == 0 and result.stdout.strip():
                driver_version = result.stdout.strip().splitlines()[0].strip()
                try:
                    driver_major = int(driver_version.split(".")[0])
                    if driver_major >= 550:
                        return "12.1"
                    if driver_major >= 525:
                        return "12.0"
                    if driver_major >= 520:
                        return "11.8"
                    if driver_major >= 470:
                        return "11.7"
                except (ValueError, IndexError):
                    pass
        except Exception:  # noqa: BLE001
            pass

        cuda_version = os.environ.get("CUDA_VERSION")
        if cuda_version:
            parts = cuda_version.split(".")
            if len(parts) >= 2:
                return f"{parts[0]}.{parts[1]}"
        return "12.1"

    def get_recommended_cuda_index(self) -> str:
        cuda_version = self.get_cuda_version_from_system() or "12.1"
        if cuda_version.startswith("12."):
            return "cu121"
        if cuda_version.startswith("11.8"):
            return "cu118"
        if cuda_version.startswith("11.7"):
            return "cu117"
        return "cu121"

    def get_inference_device(
        self, preferred: str | int | None = None
    ) -> str:
        """
        Resolve Ultralytics/Torch device for inference.

        Priority:
          1. explicit `preferred` argument
          2. ML_DEVICE / BMW_ML_DEVICE env
          3. first usable CUDA device via PyTorch
          4. cpu (even if nvidia-smi sees a GPU but torch cannot use it)
        """
        if preferred is not None and str(preferred).strip() != "":
            return _normalize_device(preferred)

        env_device = os.environ.get("ML_DEVICE") or os.environ.get("BMW_ML_DEVICE")
        if env_device and env_device.strip():
            return _normalize_device(env_device)

        has_cuda, torch_version = self.is_pytorch_cuda_enabled()
        if has_cuda:
            try:
                import torch

                count = torch.cuda.device_count()
                if count > 0:
                    # cuda:0 is the first device visible under CUDA_VISIBLE_DEVICES
                    device = "cuda:0"
                    name = torch.cuda.get_device_name(0)
                    logger.info(
                        "Using GPU for inference: %s (%s), torch=%s",
                        device,
                        name,
                        torch_version,
                    )
                    return device
            except Exception as exc:  # noqa: BLE001
                logger.warning("CUDA reported available but device resolve failed: %s", exc)

        gpu_info = self.detect_gpu()
        if gpu_info.get("available"):
            logger.warning(
                "GPU hardware detected (%s via %s) but PyTorch CUDA is not usable "
                "— falling back to CPU. Install CUDA PyTorch (index %s) to enable GPU.",
                gpu_info.get("name") or "unknown",
                gpu_info.get("detected_by"),
                self.get_recommended_cuda_index(),
            )
        else:
            logger.info("Using CPU for inference")
        return "cpu"


gpu_detector = GPUDetector()


def get_inference_device(preferred: str | int | None = None) -> str:
    """Module-level helper used by YOLO detectors / training."""
    return gpu_detector.get_inference_device(preferred)


def get_gpu_info(*, force: bool = False) -> dict[str, Any]:
    info = dict(gpu_detector.detect_gpu(force=force))
    info["inference_device"] = gpu_detector.get_inference_device()
    has_cuda, torch_version = gpu_detector.is_pytorch_cuda_enabled()
    info["pytorch_cuda_enabled"] = has_cuda
    info["pytorch_version"] = torch_version
    info["recommended_cuda_index"] = gpu_detector.get_recommended_cuda_index()
    return info
