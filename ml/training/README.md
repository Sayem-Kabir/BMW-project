# Module 1D — Driver monitoring YOLO training
#
# Official dataset: Vicomtech DMD (request access)
#   https://github.com/Vicomtech/DMD-Driver-Monitoring-Dataset
#
# Workflow:
#   1. Request + download DMD RGB subset
#   2. Export frames/boxes with Vicomtech DEx → convert to YOLO .txt labels
#      Classes: 0=phone, 1=smoking, 2=no_seatbelt
#   3. Scaffold / validate layout:
#        python -m ml.training.prepare_dmd_yolo --root data/dmd_yolo --scaffold
#        python -m ml.training.prepare_dmd_yolo --root data/dmd_yolo --check
#   4. Upload folder to Kaggle as dataset (e.g. dmd-driver-monitoring)
#   5. Run notebooks/train_driver_yolo_kaggle.py on GPU
#      OR open notebooks/train_driver_yolo_colab.ipynb in Google Colab (GPU)
#   6. Download best.pt → ml/models/driver_monitor_best.pt
#   7. Inference:
#        from ml.driver_monitoring import YOLODriverDetector
#
# Fallback (if DMD access is delayed):
#   Use a public Kaggle distraction dataset and map labels to the same 3 classes,
#   then keep the same train / inference pipeline.
#
# Local train (optional):
#   pip install ultralytics
#   python -m ml.training.train_driver_yolo --data path/to/dataset.yaml --epochs 50
