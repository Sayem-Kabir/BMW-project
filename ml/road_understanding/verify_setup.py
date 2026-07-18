"""
Smoke-test Module 2A road-understanding foundations.

Usage (from repo root):
    python -m ml.road_understanding.verify_setup
"""

from __future__ import annotations


def _check(label: str, ok: bool, detail: str = "") -> bool:
    status = "PASS" if ok else "FAIL"
    suffix = f" — {detail}" if detail else ""
    print(f"  [{status}] {label}{suffix}")
    return ok


def main() -> None:
    print("=== Module 2A–2G — Road understanding foundation check ===\n")
    failed = False

    from ml.road_understanding.config import (
        MODELS_DIR,
        PEDESTRIAN_TEMPORAL_INPUT_SIZE,
        PEDESTRIAN_TEMPORAL_MODEL_PATH,
        PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH,
        SEG_ROAD_CLASS_NAMES,
        SEG_ROAD_INPUT_SIZE,
        SEG_ROAD_MODEL_PATH,
        ensure_models_dir,
        pedestrian_temporal_model_ready,
        seg_road_model_ready,
    )

    ensure_models_dir()
    print("Config:")
    print(f"  MODELS_DIR={MODELS_DIR}")
    print(f"  SEG_ROAD_INPUT_SIZE={SEG_ROAD_INPUT_SIZE}")
    print(f"  SEG_ROAD_CLASS_NAMES={SEG_ROAD_CLASS_NAMES}")
    print(f"  PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH={PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH}")
    print(f"  PEDESTRIAN_TEMPORAL_INPUT_SIZE={PEDESTRIAN_TEMPORAL_INPUT_SIZE}")
    print()

    print("Model assets:")
    if seg_road_model_ready():
        _check("seg_road.pt present", True, str(SEG_ROAD_MODEL_PATH))
    else:
        _check("seg_road.pt present", False, str(SEG_ROAD_MODEL_PATH))
        failed = True

    if pedestrian_temporal_model_ready():
        _check(
            "best_pedestrian_yololstm.pt present",
            True,
            str(PEDESTRIAN_TEMPORAL_MODEL_PATH),
        )
    else:
        _check(
            "best_pedestrian_yololstm.pt present",
            False,
            str(PEDESTRIAN_TEMPORAL_MODEL_PATH),
        )
        failed = True

    print("\nDependencies:")
    try:
        import cv2  # noqa: F401

        ok = _check("opencv-python", True)
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("opencv-python", False, str(exc))
        failed = True

    try:
        import torch

        ok = _check("torch", True, torch.__version__)
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("torch", False, str(exc))
        failed = True

    try:
        import segmentation_models_pytorch as smp

        ok = _check("segmentation-models-pytorch", True, smp.__version__)
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check(
            "segmentation-models-pytorch",
            False,
            f"{exc} — pip install -r apps/backend/requirements-phase2.txt",
        )
        failed = True

    try:
        import supervision as sv

        ok = _check("supervision (ByteTrack)", True, sv.__version__)
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check(
            "supervision (ByteTrack)",
            False,
            f"{exc} — pip install -r apps/backend/requirements-phase2.txt",
        )
        failed = True

    try:
        import timm

        ok = _check("timm (MiDaS encoder)", True, timm.__version__)
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check(
            "timm (MiDaS encoder)",
            False,
            f"{exc} — pip install -r apps/backend/requirements-phase2.txt",
        )
        failed = True

    print("\nGPU / inference device:")
    try:
        from ml.common.gpu_detector import get_gpu_info

        info = get_gpu_info()
        device = info.get("inference_device", "cpu")
        ok = _check(
            "Inference device resolved",
            device in {"cpu", "mps"} or str(device).startswith("cuda"),
            f"device={device} name={info.get('name')}",
        )
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("Inference device resolved", False, str(exc))
        failed = True

    print("\nRoad segmenter (Module 2B):")
    try:
        import numpy as np
        from ml.road_understanding.road_segmenter import RoadSegmenter

        segmenter = RoadSegmenter()
        out = segmenter.segment(np.zeros((64, 96, 3), dtype=np.uint8))
        ok = _check(
            "RoadSegmenter blank frame",
            out.is_valid and out.mask is not None and out.mask.shape == (64, 96),
            (
                f"classes={SEG_ROAD_CLASS_NAMES} device={segmenter.device} "
                f"checkpoint_acc={out.checkpoint_val_acc}"
            ),
        )
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("RoadSegmenter blank frame", False, str(exc))
        failed = True

    print("\nObject tracker (Module 2C):")
    try:
        from ml.road_understanding.object_detector import RoadDetection, RoadDetections
        from ml.road_understanding.tracker import RoadObjectTracker

        tracker = RoadObjectTracker(min_hits=1)
        tracked = tracker.update(
            RoadDetections(
                detections=[
                    RoadDetection("car", 0.9, [10, 10, 40, 40], class_id=2)
                ],
                model_loaded=True,
            )
        )
        ok = _check(
            "ByteTrack synthetic detection",
            (
                tracked.tracker_ready
                and len(tracked.tracks) == 1
                and tracked.tracks[0].track_id > 0
            ),
            f"track_id={tracked.tracks[0].track_id if tracked.tracks else None}",
        )
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("ByteTrack synthetic detection", False, str(exc))
        failed = True

    print("\nDepth estimator (Module 2D):")
    try:
        from ml.road_understanding.depth_estimator import MiDaSDepthEstimator

        depth_estimator = MiDaSDepthEstimator()
        depth = depth_estimator.estimate(np.zeros((64, 96, 3), dtype=np.uint8))
        ok = _check(
            "MiDaS_small blank frame",
            (
                depth.is_valid
                and depth.relative_inverse_depth is not None
                and depth.relative_inverse_depth.shape == (64, 96)
            ),
            (
                f"device={depth_estimator.device} map="
                f"{depth.relative_inverse_depth.shape if depth.relative_inverse_depth is not None else None} "
                f"inference_ms={depth.inference_ms:.1f}"
                if depth.inference_ms is not None
                else depth.message or ""
            ),
        )
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("MiDaS_small blank frame", False, str(exc))
        failed = True

    print("\nTraffic-light classifier (Module 2E):")
    try:
        from ml.road_understanding.traffic_light import TrafficLightClassifier

        red_crop = np.zeros((24, 24, 3), dtype=np.uint8)
        red_crop[..., 2] = 255
        light = TrafficLightClassifier().classify_crop(red_crop)
        ok = _check(
            "HSV red synthetic crop",
            light.state == "RED" and light.confidence > 0.9,
            f"state={light.state} confidence={light.confidence:.2f}",
        )
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("HSV red synthetic crop", False, str(exc))
        failed = True

    print("\nTemporal pedestrian localizer (Module 2F):")
    try:
        import numpy as np

        from ml.road_understanding.pedestrian_temporal import (
            TemporalPedestrianLocalizer,
        )

        localizer = TemporalPedestrianLocalizer()
        temporal = localizer.localize(
            [
                np.zeros((224, 224, 3), dtype=np.uint8)
                for _ in range(PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH)
            ]
        )
        ok = _check(
            "Caltech YOLO-LSTM blank sequence",
            (
                temporal.model_loaded
                and temporal.normalized_bbox_xywh is not None
                and temporal.frames_used == PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH
            ),
            (
                f"device={localizer.device} frames={temporal.frames_used} "
                f"confidence={temporal.confidence:.3f}"
            ),
        )
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("Caltech YOLO-LSTM blank sequence", False, str(exc))
        failed = True

    print("\nUnified pipeline (Module 2G):")
    try:
        import numpy as np

        from ml.road_understanding.pipeline import (
            RoadPipelineOptions,
            RoadUnderstandingPipeline,
        )

        pipeline = RoadUnderstandingPipeline(
            segmenter=object(),
            detector=object(),
            tracker=object(),
            depth_estimator=object(),
            traffic_light_classifier=object(),
            pedestrian_localizer=object(),
            options=RoadPipelineOptions(
                segmentation=False,
                detection_tracking=False,
                depth=False,
                traffic_lights=False,
                pedestrian_temporal=False,
            ),
        )
        pipeline_result = pipeline.process_frame(
            np.zeros((32, 48, 3), dtype=np.uint8)
        )
        payload = pipeline_result.to_dict()
        ok = _check(
            "2G frame orchestration + serialization",
            (
                pipeline_result.is_valid
                and payload["phase"] == "2G"
                and payload["frame_id"] == 1
            ),
            f"phase={payload['phase']} frame_id={payload['frame_id']}",
        )
        failed = failed or not ok
    except Exception as exc:  # noqa: BLE001
        _check("2G frame orchestration + serialization", False, str(exc))
        failed = True

    print()
    if failed:
        print("Result: INCOMPLETE — fix FAIL items above.")
        print("  Tip: pip install -r apps/backend/requirements-phase2.txt")
        raise SystemExit(1)

    print("Result: Module 2A–2G road understanding foundations OK.")


if __name__ == "__main__":
    main()
