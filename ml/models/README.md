# Model weights (too large for Git)

## Module 8C — registry

```bash
python -m ml.models.download_registry --check
python -m ml.models.download_registry --only yolov8n_base,yolov8m_base
```

See `registry.json` for filenames, sources, and which modules consume each weight.

## Module 8D — train / export domain YOLO

```bash
python -m ml.training.export_domain_weights_8d --driver-best path/to/best.pt
```

## Phase 1 — Driver monitoring

```bash
python -m ml.driver_monitoring.download_assets
```

Expected files:
- `shape_predictor_68_face_landmarks.dat` (~99 MB, Module 1A)
- `driver_monitor_best.pt` (Module 1D — Colab DMS YOLOv8n, 5 classes)

## Phase 2 — Road understanding

Expected files (place after training / 8D export):
- `seg_road.pt`
- `road_yolov8m_best.pt`
- `best_pedestrian_yololstm.pt`

Falls back to Ultralytics `yolov8m.pt` / `yolov8n.pt` when domain weights are missing.

## Phase 3 — Predictive maintenance

Joblib artifacts (`engine_fault_clf.joblib`, etc.) are documented in Phase 3 notebooks; not part of the YOLO registry.
