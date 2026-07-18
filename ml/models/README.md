# Model weights (too large for Git)

## Phase 1 — Driver monitoring
Download via:
```bash
python -m ml.driver_monitoring.download_assets
```

Expected files:
- `shape_predictor_68_face_landmarks.dat` (~99 MB, Module 1A)
- `driver_monitor_best.pt` (Module 1D — Colab DMS YOLOv8n, 5 classes)

Train YOLO:
- `notebooks/train_driver_yolo_colab.ipynb`
- Dataset: https://www.kaggle.com/datasets/habbas11/dms-driver-monitoring-system

## Phase 2 — Road understanding (Module 2A+)
Expected files (place after training):
- `seg_road.pt` — DeepLabV3+ / ResNet50 BDD100K segmentation checkpoint
  (Module 2B: road, shoulder, background)
- `road_yolov8m_best.pt` — optional road-object detector for later modules that
  need bounding boxes (vehicles, pedestrians, traffic lights)
- `best_pedestrian_yololstm.pt` — Caltech Pedestrian YOLO temporal localizer
  (Module 2F: primary pedestrian bbox + confidence over five frames)

Train Module 2B with `notebooks/train_road_seg.ipynb`. The checkpoint must
contain `model_state_dict` from a three-class `DeepLabV3Plus` with a ResNet50
encoder. Object detection remains separate and may fall back to Ultralytics
`yolov8m.pt` (COCO).

Module 2C uses ByteTrack from `supervision`; it has no separate trained weights.
It assigns persistent IDs to sequential YOLO road-object detections.

Module 2D uses pretrained `MiDaS_small` from torch hub. Its weights download to
the local PyTorch cache on first inference; no training or file in this folder
is required. MiDaS output is relative inverse depth. `distance_m` remains empty
until scale/offset are calibrated using known distances for the target camera.

Module 2E uses OpenCV HSV masks on tracked traffic-light crops to classify
`RED`, `AMBER`, `GREEN`, or `UNKNOWN`; it requires no model weights or training.

Module 2F uses a YOLOv8n feature backbone and LSTM trained by
`notebooks/train_pedestrian_temporal.ipynb` on the Caltech Pedestrian YOLO
dataset. This is localization—not crossing-intent classification—because
Caltech has bounding boxes but no intent labels.

Module 2G (`ml/road_understanding/pipeline.py`) runs Modules 2B–2F in
dependency order for each sequential frame. It owns ByteTrack/temporal state,
merges depth, traffic-light, and pedestrian annotations, and returns partial
results with warnings when one stage is unavailable.

Verify foundations:
```bash
python -m ml.road_understanding.verify_setup
```

Deps:
```bash
pip install -r apps/backend/requirements-phase2.txt
```
