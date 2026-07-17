"""Driver monitoring package — Phase 1 (Module 01).

Module 1A: download_assets / verify_setup
Module 1B: analyze_frame, compute_ear, compute_mar
Module 1C: HeadPoseEstimator, estimate_head_pose
Module 1D: YOLODriverDetector, detect_driver_objects
           (train: python -m ml.training.train_driver_yolo)
"""

from ml.driver_monitoring.config import (
    DLIB_LANDMARK_PATH,
    DISTRACTION_PITCH_THRESHOLD,
    DISTRACTION_YAW_THRESHOLD,
    DROWSY_FRAME_COUNT,
    EAR_THRESHOLD,
    MAR_THRESHOLD,
    YOLO_CLASS_NAMES,
    YOLO_DRIVER_MODEL_PATH,
    dlib_landmark_ready,
    yolo_driver_model_ready,
)
from ml.driver_monitoring.ear_detector import (
    DriverFaceState,
    analyze_frame,
    compute_ear,
)
from ml.driver_monitoring.head_pose import (
    HeadPoseEstimator,
    HeadPoseState,
    estimate_head_pose,
)
from ml.driver_monitoring.mar_detector import compute_mar
from ml.driver_monitoring.yolo_detector import (
    DriverObjectDetections,
    YOLODriverDetector,
    detect_driver_objects,
)

__all__ = [
    "DLIB_LANDMARK_PATH",
    "EAR_THRESHOLD",
    "MAR_THRESHOLD",
    "DROWSY_FRAME_COUNT",
    "DISTRACTION_PITCH_THRESHOLD",
    "DISTRACTION_YAW_THRESHOLD",
    "YOLO_CLASS_NAMES",
    "YOLO_DRIVER_MODEL_PATH",
    "dlib_landmark_ready",
    "yolo_driver_model_ready",
    "DriverFaceState",
    "analyze_frame",
    "compute_ear",
    "compute_mar",
    "HeadPoseEstimator",
    "HeadPoseState",
    "estimate_head_pose",
    "DriverObjectDetections",
    "YOLODriverDetector",
    "detect_driver_objects",
]
