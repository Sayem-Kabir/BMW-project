# ML training guides

## Module 1D — Driver monitoring YOLO
#
# Primary dataset (used in Colab notebook):
#   https://www.kaggle.com/datasets/habbas11/dms-driver-monitoring-system
#
# Classes (5):
#   0 Open Eye | 1 Closed Eye | 2 Cigarette | 3 Phone | 4 Seatbelt
#
# Workflow:
#   1. Open notebooks/train_driver_yolo_colab.ipynb in Google Colab (GPU)
#   2. Download DMS via opendatasets (needs Kaggle API token)
#   3. Train YOLOv8n (~100 epochs)
#   4. Download best.pt → ml/models/driver_monitor_best.pt
#   5. Inference:
#        from ml.driver_monitoring import YOLODriverDetector
#
# Local train (optional):
#   pip install ultralytics
#   python -m ml.training.train_driver_yolo --data path/to/data.yaml --epochs 50

## Module 2B — Road semantic segmentation (BDD100K)
#
# Dataset: BDD100K semantic segmentation images + train-ID masks
#
# Model: DeepLabV3Plus, ResNet50 encoder, 512x512 input
# Output classes:
#   0 road | 1 shoulder | 2 background
#
# Workflow:
#   1. Open notebooks/train_road_seg.ipynb in Colab
#   2. Download the BDD100K segmentation dataset used by the notebook
#   3. Train the three-class model
#   4. Download deeplabv3_road.pt → ml/models/seg_road.pt
#   5. Inference:
#        from ml.road_understanding import segment_road
#
# `train_road_yolo.py` and `prepare_bdd100k_yolo.py` are optional utilities
# for a separate bounding-box detector needed by tracking/object modules.

## Module 2F — Temporal pedestrian localization (Caltech Pedestrian YOLO)
#
# Dataset:
#   https://www.kaggle.com/datasets/abhinavsasikumar/caltech-pedestrian-yolo/data
#
# Model: YOLOv8n backbone + 256-unit LSTM, 224x224 input, five-frame window
# Output: one primary normalized pedestrian bbox + confidence
#
# Workflow:
#   1. Open notebooks/train_pedestrian_temporal.ipynb in Colab or Kaggle
#   2. Attach/download the Caltech Pedestrian YOLO dataset
#   3. Train and evaluate with sequence-group-level splits
#   4. Download best_pedestrian_yololstm.pt → ml/models/
#   5. Inference:
#        from ml.road_understanding import TemporalPedestrianLocalizer
#
# Local checkpoint check:
#   python -m ml.training.train_pedestrian_temporal --verify-weights ml/models/best_pedestrian_yololstm.pt
#
# This module performs temporal localization and short-occlusion confirmation.
# It does not classify pedestrian crossing intent because Caltech has no intent
# labels.
