# Spec Phase 13 — CV / inference optimizations

## Driver monitoring (Module 01)

| Knob | Location | Default | Effect |
|------|----------|---------|--------|
| `FRAME_SAMPLE_EVERY` | `ml/driver_monitoring/config.py` | `3` | Full EAR+pose+YOLO every N frames; reuse last result between |
| `FACE_GATE_ENABLED` | same | `True` | Skip mesh/landmarks when cheap luminance-variance gate fails |
| `FACE_GATE_MIN_PIXELS` | same | `1.0` | Variance threshold for empty-cabin frames |

Pipeline sets `inference_mode`: `full` | `interpolated` | `face_gate_skip`.

## Road understanding (Module 02)

| Knob | Location | Default |
|------|----------|---------|
| `SEG_FULL_EVERY_N` | `ml/road_understanding/config.py` | `5` |
| `DEPTH_ROI_INSET_RATIO` | same | `0.15` (existing) |

Wire periodic re-seg in the road pipeline using `SEG_FULL_EVERY_N` when extending Module 2B.

## ONNX / INT8 (optional follow-up)

```bash
# Export YOLOv8n after ultralytics is installed
yolo export model=ml/models/driver_monitor_best.pt format=onnx int8=True
# Profile with:
#   py-spy record -o cv_profile.svg -- python scripts/profile_driver_pipeline.py
```

Document measured FPS before/after in this file when hardware is available.

## Independent workers

Driver (`/api/v1/driver/analysis`) and road (`/api/v1/road/analysis`) are separate HTTP workers —
call them concurrently from the demo runner / Celery `ml_tasks` queue rather than sequentially.
