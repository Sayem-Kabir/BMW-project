"""Phase 2A — shared paths and thresholds for road understanding."""

from __future__ import annotations

from pathlib import Path

# ── Repo / model paths ──────────────────────────────────────────────
ML_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ML_ROOT / "models"

# DeepLabV3+ / ResNet50 trained by notebooks/train_road_seg.ipynb (Module 2B)
SEG_ROAD_MODEL_FILENAME = "seg_road.pt"
SEG_ROAD_MODEL_PATH = MODELS_DIR / SEG_ROAD_MODEL_FILENAME
SEG_ROAD_INPUT_SIZE = 512
SEG_ROAD_CLASS_NAMES = ("road", "shoulder", "background")
SEG_ROAD_CLASS_COLORS_BGR = (
    (60, 200, 60),    # road — green
    (0, 180, 255),    # shoulder — amber
    (0, 0, 0),        # background — transparent in overlays
)
SEG_ROAD_BACKGROUND_CLASS_ID = 2
SEG_ROAD_OVERLAY_ALPHA = 0.45

# YOLO road-object detection remains available for later box-based modules.
YOLO_ROAD_MODEL_FILENAME = "road_yolov8m_best.pt"
YOLO_ROAD_MODEL_PATH = MODELS_DIR / YOLO_ROAD_MODEL_FILENAME

# Fallback while fine-tuned weights are missing (COCO pretrained via Ultralytics)
YOLO_ROAD_FALLBACK_MODEL = "yolov8m.pt"

# YOLOv8n-backbone + LSTM temporal localizer (Module 2F — Caltech Pedestrian)
PEDESTRIAN_TEMPORAL_MODEL_FILENAME = "best_pedestrian_yololstm.pt"
PEDESTRIAN_TEMPORAL_MODEL_PATH = MODELS_DIR / PEDESTRIAN_TEMPORAL_MODEL_FILENAME

# MiDaS depth (Module 2D — pretrained torch hub model, cached after first use)
MIDAS_REPOSITORY = "intel-isl/MiDaS"
MIDAS_MODEL_TYPE = "MiDaS_small"  # fast default; DPT_Hybrid improves quality

# ── Optional BDD100K object-detection taxonomy ───────────────────────
# Used by downstream modules that require boxes, not by Module 2B segmentation.
ROAD_CLASS_NAMES = (
    "pedestrian",
    "rider",
    "car",
    "truck",
    "bus",
    "train",
    "motorcycle",
    "bicycle",
    "traffic light",
    "traffic sign",
)

# COCO person / vehicle subset usable before an optional BDD detector fine-tune.
COCO_ROAD_CLASS_IDS = (
    0,   # person
    1,   # bicycle
    2,   # car
    3,   # motorcycle
    5,   # bus
    7,   # truck
    9,   # traffic light
    11,  # stop sign
)

# ── Detection / tracking thresholds ─────────────────────────────────
YOLO_ROAD_CONFIDENCE = 0.40
YOLO_ROAD_IOU = 0.50
TRACK_ACTIVATION_THRESHOLD = 0.25
TRACK_MAX_AGE = 30          # ByteTrack: frames to keep lost tracks
TRACK_MIN_HITS = 3          # application-level confirmation threshold
TRACK_MINIMUM_MATCHING_THRESHOLD = 0.80
TRACK_FRAME_RATE = 30
# Reserved for downstream overlap / association checks. Do not feed this
# directly into ByteTrack matching — 0.30 is too permissive for ID stability.
TRACK_IOU_THRESHOLD = 0.30

# ── Depth / distance (Module 2D) ────────────────────────────────────
# MiDaS emits relative inverse depth (larger means closer), not metric depth.
# distance ≈ scale / (inverse_depth + offset). The defaults are only a rough
# demo heuristic; fit scale/offset using known-distance samples per camera.
DEPTH_METERS_SCALE = 12.0
DEPTH_METERS_OFFSET = 0.0
DEPTH_ROI_INSET_RATIO = 0.15
DEPTH_MAX_DISTANCE_M = 200.0

# ── Traffic light HSV (Module 2E) ───────────────────────────────────
TRAFFIC_LIGHT_MIN_CROP_PX = 8
TRAFFIC_LIGHT_STATES = ("RED", "AMBER", "GREEN", "UNKNOWN")
TRAFFIC_LIGHT_RED_HUE_RANGES = ((0, 10), (170, 179))
TRAFFIC_LIGHT_AMBER_HUE_RANGE = (11, 35)
TRAFFIC_LIGHT_GREEN_HUE_RANGE = (36, 95)
TRAFFIC_LIGHT_MIN_SATURATION = 80
TRAFFIC_LIGHT_MIN_VALUE = 100
TRAFFIC_LIGHT_MIN_ACTIVE_PIXELS = 4
TRAFFIC_LIGHT_MIN_ACTIVE_RATIO = 0.01
TRAFFIC_LIGHT_MIN_COLOR_CONFIDENCE = 0.55
TRAFFIC_LIGHT_MIN_DOMINANCE_MARGIN = 0.10

# ── Temporal pedestrian localization (Module 2F) ────────────────────
PEDESTRIAN_TEMPORAL_SEQUENCE_LENGTH = 5
PEDESTRIAN_TEMPORAL_INPUT_SIZE = 224
PEDESTRIAN_TEMPORAL_HIDDEN_SIZE = 256
PEDESTRIAN_TEMPORAL_CONFIDENCE = 0.50


def ensure_models_dir() -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR


def seg_road_model_ready() -> bool:
    return SEG_ROAD_MODEL_PATH.is_file() and SEG_ROAD_MODEL_PATH.stat().st_size > 0


def yolo_road_model_ready() -> bool:
    return YOLO_ROAD_MODEL_PATH.is_file() and YOLO_ROAD_MODEL_PATH.stat().st_size > 0


def pedestrian_temporal_model_ready() -> bool:
    return (
        PEDESTRIAN_TEMPORAL_MODEL_PATH.is_file()
        and PEDESTRIAN_TEMPORAL_MODEL_PATH.stat().st_size > 0
    )


def resolve_yolo_road_weights() -> str:
    """
    Prefer fine-tuned BDD weights; otherwise Ultralytics will fetch yolov8m.pt.
    Returns a path string or model name suitable for ultralytics.YOLO(...).
    """
    if yolo_road_model_ready():
        return str(YOLO_ROAD_MODEL_PATH)
    return YOLO_ROAD_FALLBACK_MODEL
