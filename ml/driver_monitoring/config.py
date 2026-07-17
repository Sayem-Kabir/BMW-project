"""Phase 1A — shared paths and detection thresholds for driver monitoring."""

from pathlib import Path

# ── Repo / model paths ──────────────────────────────────────────────
# ml/ is the package root; models live alongside it under ml/models/
ML_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = ML_ROOT / "models"

DLIB_LANDMARK_FILENAME = "shape_predictor_68_face_landmarks.dat"
DLIB_LANDMARK_URL = (
    "https://github.com/davisking/dlib-models/raw/master/"
    "shape_predictor_68_face_landmarks.dat.bz2"
)
# Fallback if GitHub raw is unavailable
DLIB_LANDMARK_URL_FALLBACK = (
    "http://dlib.net/files/shape_predictor_68_face_landmarks.dat.bz2"
)
DLIB_LANDMARK_PATH = MODELS_DIR / DLIB_LANDMARK_FILENAME

# YOLO weights (populated in Module 1D after Kaggle training)
YOLO_DRIVER_MODEL_PATH = MODELS_DIR / "driver_monitor_best.pt"

# ── EAR / MAR (Module 1B) ───────────────────────────────────────────
EAR_THRESHOLD = 0.25  # below → eyes closing / drowsy
MAR_THRESHOLD = 0.60  # above → yawning
DROWSY_FRAME_COUNT = 30  # consecutive frames before drowsy alert (~1s @ 30fps)

# Dlib 68-point landmark indices
LEFT_EYE_IDX = list(range(36, 42))
RIGHT_EYE_IDX = list(range(42, 48))
MOUTH_IDX = list(range(60, 68))  # inner mouth for MAR

# ── Head pose (Module 1C) ───────────────────────────────────────────
DISTRACTION_PITCH_THRESHOLD = 15.0  # degrees — looking down
DISTRACTION_YAW_THRESHOLD = 15.0  # degrees — looking sideways

# ── YOLO object detection (Module 1D) ───────────────────────────────
YOLO_PHONE_CONFIDENCE = 0.70
YOLO_SMOKING_CONFIDENCE = 0.65
YOLO_SEATBELT_CONFIDENCE = 0.80
YOLO_CLASS_NAMES = ("phone", "smoking", "no_seatbelt")


def ensure_models_dir() -> Path:
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR


def dlib_landmark_ready() -> bool:
    return DLIB_LANDMARK_PATH.is_file() and DLIB_LANDMARK_PATH.stat().st_size > 0


def yolo_driver_model_ready() -> bool:
    return YOLO_DRIVER_MODEL_PATH.is_file() and YOLO_DRIVER_MODEL_PATH.stat().st_size > 0
