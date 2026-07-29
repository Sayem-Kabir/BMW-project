# Training Guide

ML training starts in **Phase 1**. Use Kaggle free GPU for YOLOv8 / LSTM jobs.

Scripts live under `ml/training/`. Model weights go in `ml/models/` (gitignored: `*.pt` / `*.pth`).

## Download / place weights (Phase 7G / 8C)

Large checkpoints are **not** committed (`yolov8*.pt`, `ml/models/*`). The platform still demos with CPU/synthetic fallbacks.

```bash
# Module 8C — registry check + Ultralytics base downloads
python -m ml.models.download_registry --check
python -m ml.models.download_registry --only yolov8n_base,yolov8m_base

# Or one-shot Ultralytics
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

Canonical filenames are listed in [`ml/models/registry.json`](../ml/models/registry.json) and [`ml/models/README.md`](../ml/models/README.md).

See [DEMO.md](DEMO.md) for the cold-demo path without GPU weights.

## Module 8D — Domain YOLO retrain + export (only Phase 8 training)

```bash
# Export existing best.pt into ml/models/
python -m ml.training.export_domain_weights_8d \
  --driver-best path/to/best.pt \
  --road-best path/to/road_best.pt

# Or train then export (needs dataset YAML + GPU recommended)
python -m ml.training.export_domain_weights_8d --train-driver \
  --data ml/training/datasets/driver_monitoring_dataset.yaml --epochs 50
```

Assistant **LoRA fine-tuning** remains out of scope.

## Kaggle workflow

1. Create Kaggle account + enable GPU
2. Upload datasets (DMD, BDD100K, Caltech Pedestrian YOLO)
3. Create notebooks from `notebooks/train_*.py` scripts
4. Download trained `.pt` weights to `ml/models/` (or run Module 8D export)
