"""
Smoke-test Module 1A–1C foundations: paths, OpenCV, Dlib, MediaPipe head pose.

Usage (from repo root):
    python -m ml.driver_monitoring.verify_setup
"""

from __future__ import annotations

import sys


def _check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return ok


def main() -> None:
    print("=== Module 1A–1C — Foundation check ===\n")
    failed = False

    # Paths / config
    from ml.driver_monitoring.config import (
        DLIB_LANDMARK_PATH,
        EAR_THRESHOLD,
        MAR_THRESHOLD,
        DROWSY_FRAME_COUNT,
        DISTRACTION_PITCH_THRESHOLD,
        DISTRACTION_YAW_THRESHOLD,
        MODELS_DIR,
        dlib_landmark_ready,
        ensure_models_dir,
    )

    ensure_models_dir()
    print("Config thresholds:")
    print(f"  EAR_THRESHOLD={EAR_THRESHOLD}")
    print(f"  MAR_THRESHOLD={MAR_THRESHOLD}")
    print(f"  DROWSY_FRAME_COUNT={DROWSY_FRAME_COUNT}")
    print(f"  DISTRACTION_PITCH/YAW={DISTRACTION_PITCH_THRESHOLD}/{DISTRACTION_YAW_THRESHOLD}")
    print(f"  MODELS_DIR={MODELS_DIR}")
    print()

    print("Assets:")
    ok = _check(
        "Dlib landmark .dat present",
        dlib_landmark_ready(),
        str(DLIB_LANDMARK_PATH),
    )
    failed = failed or not ok

    print("\nPython packages:")
    try:
        import cv2

        ok = _check("opencv-python", True, f"cv2={cv2.__version__}")
    except ImportError as exc:
        ok = _check("opencv-python", False, str(exc))
        failed = True

    try:
        import numpy as np

        _check("numpy", True, f"numpy={np.__version__}")
    except ImportError as exc:
        _check("numpy", False, str(exc))
        failed = True

    try:
        import scipy

        _check("scipy", True, f"scipy={scipy.__version__}")
    except ImportError as exc:
        _check("scipy", False, str(exc))
        failed = True

    dlib_ok = False
    try:
        import dlib

        dlib_ok = _check("dlib", True, f"dlib={dlib.__version__}")
    except ImportError as exc:
        _check("dlib", False, f"{exc} (install later if build tools missing)")

    print("\nOpenCV smoke:")
    try:
        import cv2
        import numpy as np

        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ok = _check("cvtColor on blank frame", gray.shape == (480, 640))
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("cvtColor on blank frame", False, str(exc))
        failed = True

    if dlib_ok and dlib_landmark_ready():
        print("\nDlib landmark load:")
        try:
            import dlib

            predictor = dlib.shape_predictor(str(DLIB_LANDMARK_PATH))
            _check("shape_predictor loads", predictor is not None)
        except Exception as exc:  # noqa: BLE001
            _check("shape_predictor loads", False, str(exc))
            failed = True

    mp_ok = False
    try:
        import mediapipe as mp

        mp_ok = _check("mediapipe", True, f"mediapipe={getattr(mp, '__version__', '?')}")
    except ImportError as exc:
        _check("mediapipe", False, f"{exc} (pip install -r apps/backend/requirements-phase1.txt)")
        failed = True

    if mp_ok:
        print("\nHead pose (Module 1C):")
        try:
            import numpy as np
            from ml.driver_monitoring.head_pose import HeadPoseEstimator

            blank = np.zeros((480, 640, 3), dtype=np.uint8)
            with HeadPoseEstimator() as estimator:
                pose = estimator.estimate(blank)
            ok = _check(
                "HeadPoseEstimator on blank frame",
                pose.face_detected is False and pose.distracted is False,
            )
            failed = failed or not ok
        except Exception as exc:  # noqa: BLE001
            _check("HeadPoseEstimator on blank frame", False, str(exc))
            failed = True

    print("\nYOLO driver model (Module 1D):")
    from ml.driver_monitoring.config import YOLO_DRIVER_MODEL_PATH, yolo_driver_model_ready
    from ml.driver_monitoring.yolo_detector import YOLODriverDetector
    import numpy as np

    if yolo_driver_model_ready():
        _check("driver_monitor_best.pt present", True, str(YOLO_DRIVER_MODEL_PATH))
    else:
        _check(
            "driver_monitor_best.pt present",
            True,
            f"optional until Kaggle training finishes ({YOLO_DRIVER_MODEL_PATH.name} missing)",
        )

    try:
        det = YOLODriverDetector(model_path=YOLO_DRIVER_MODEL_PATH.parent / "__missing__.pt")
        out = det.detect(np.zeros((480, 640, 3), dtype=np.uint8))
        ok = _check(
            "YOLODriverDetector safe mode without weights",
            out.model_loaded is False and out.seatbelt_worn is False,
        )
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("YOLODriverDetector safe mode without weights", False, str(exc))
        failed = True

    print()
    if failed:
        print("Result: INCOMPLETE — fix FAIL items above.")
        print("  Tip: python -m ml.driver_monitoring.download_assets")
        print("  Tip: pip install -r apps/backend/requirements-phase1.txt")
        raise SystemExit(1)

    print("Result: Module 1A–1D foundations OK (YOLO weights optional until trained).")


if __name__ == "__main__":
    main()
