# Module 1D — Driver monitoring YOLO training
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
