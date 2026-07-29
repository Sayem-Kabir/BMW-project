from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class HeadPose(BaseModel):
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0
    distracted: bool = False


class DriverAnalysisResponse(BaseModel):
    alertness_score: int = Field(ge=0, le=100)
    risk_level: str
    ear_value: float = 0.0
    mar_value: float = 0.0
    yawn_count: int = 0
    head_pose: HeadPose = Field(default_factory=HeadPose)
    phone_detected: bool = False
    smoking_detected: bool = False
    seatbelt_worn: bool = True
    is_drowsy: bool = False
    is_yawning: bool = False
    face_detected: bool = False
    consecutive_drowsy_frames: int = 0
    yolo_model_loaded: bool = False
    vehicle_id: str | None = None
    session_id: str | None = None
    xai_heatmap_url: str | None = None
    phase: str = "1"
    message: str = "ok"


class CabinPersonDetection(BaseModel):
    confidence: float = 0.0
    bbox: list[float] = Field(default_factory=list)
    seat_zone: str | None = None
    is_child: bool = False


class CabinOccupancyResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    total_occupants: int = 0
    driver_present: bool = False
    front_passenger: bool = False
    rear_passengers: int = 0
    child_detected: bool = False
    child_alert: bool = False
    unattended_vehicle: bool = False
    occupant_map: dict[str, bool] = Field(default_factory=dict)
    persons: list[CabinPersonDetection] = Field(default_factory=list)
    model_loaded: bool = False
    message: str | None = None
    phase: str = "02"


class DriverSessionResponse(BaseModel):
    id: UUID
    vehicle_id: UUID
    driver_id: UUID
    started_at: datetime
    ended_at: datetime | None = None
    alertness_score_avg: float | None = None
    drowsy_events: int = 0
    yawn_events: int = 0
    phone_events: int = 0
    total_frames_analyzed: int = 0

    model_config = {"from_attributes": True}


class RiskScoreResponse(BaseModel):
    vehicle_id: UUID
    score: int = Field(ge=0, le=100)
    level: str
    factors: list[dict[str, Any]] = []
    reasons: list[str] = []
    overrides: list[dict[str, Any]] = []
    base_score: float | None = None
    base_level: str | None = None
    timestamp: datetime
    method: str | None = None
    phase: str = "4F"
    message: str | None = None


class RiskComputeRequest(BaseModel):
    """Driver/road/telemetry inputs for one Module 4F evaluation."""

    driver_state: dict[str, Any] = Field(default_factory=dict)
    road_state: dict[str, Any] = Field(default_factory=dict)
    telemetry: dict[str, Any] = Field(default_factory=dict)
    publish: bool = True
    cache: bool = True
    persist: bool = True


class RiskComputeResponse(BaseModel):
    vehicle_id: UUID
    score: float
    level: str
    risk_score: float
    risk_level: str
    base_score: float
    base_level: str
    factors: list[dict[str, Any]] = []
    overrides: list[dict[str, Any]] = []
    reasons: list[str] = []
    timestamp: datetime
    method: str
    published: bool = False
    receivers: int = 0
    cached: bool = False
    persisted: bool = False
    record_id: UUID | None = None
    warning: str | None = None
    persist_warning: str | None = None
    phase: str = "4F"


class RiskHistoryItem(BaseModel):
    id: UUID
    vehicle_id: UUID
    score: float
    level: str
    timestamp: datetime
    factors: list[dict[str, Any]] = Field(default_factory=list)
    reasons: list[str] = Field(default_factory=list)
    overrides: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RiskHistoryResponse(BaseModel):
    vehicle_id: UUID
    history: list[RiskHistoryItem] = Field(default_factory=list)
    count: int = 0
    phase: str = "4F"
    warning: str | None = None

class RoadObject(BaseModel):
    id: str
    class_name: str = Field(alias="class")
    confidence: float
    bbox: list[float] | None = None
    track_id: int | None = None
    track_age_frames: int | None = None
    track_hits: int | None = None
    track_confirmed: bool = False
    relative_inverse_depth: float | None = None
    distance_m: float | None = None
    distance_calibrated: bool = False
    state: str | None = None
    state_confidence: float | None = None
    temporal_confidence: float | None = None
    temporal_bbox: list[float] | None = None
    temporally_confirmed: bool = False

    model_config = {"populate_by_name": True}


class RoadSegmentationSummary(BaseModel):
    """Module 2B DeepLabV3+ mask metadata (pixel classes, not boxes)."""

    model_config = ConfigDict(protected_namespaces=())

    model_loaded: bool = False
    weights_path: str | None = None
    device: str | None = None
    mask_shape: list[int] | None = None
    class_names: list[str] = Field(
        default_factory=lambda: ["road", "shoulder", "background"]
    )
    class_ratios: dict[str, float] = Field(default_factory=dict)
    mean_confidence: float | None = None
    checkpoint_epoch: int | None = None
    checkpoint_val_acc: float | None = None
    message: str | None = None


class RoadTrackingSummary(BaseModel):
    """Module 2C ByteTrack status for object-centric downstream modules."""

    tracker_ready: bool = False
    frame_index: int = 0
    active_tracks: int = 0
    confirmed_tracks: int = 0
    min_hits: int = 3
    message: str | None = None


class RoadDepthSummary(BaseModel):
    """Module 2D pretrained MiDaS availability and calibration state."""

    model_available: bool = False
    model_loaded: bool = False
    model_type: str = "MiDaS_small"
    device: str | None = None
    map_shape: list[int] | None = None
    inference_ms: float | None = None
    metric_calibrated: bool = False
    message: str | None = None

    model_config = ConfigDict(protected_namespaces=())


class RoadTrafficLightSummary(BaseModel):
    """Module 2E HSV classifier status."""

    classifier_ready: bool = False
    states: list[str] = Field(
        default_factory=lambda: ["RED", "AMBER", "GREEN", "UNKNOWN"]
    )
    classified_count: int = 0
    known_count: int = 0
    message: str | None = None


class RoadPedestrianTemporalSummary(BaseModel):
    """Module 2F Caltech YOLO-LSTM temporal localizer status."""

    model_config = ConfigDict(protected_namespaces=())

    model_loaded: bool = False
    weights_path: str | None = None
    sequence_length: int = 5
    input_size: int = 224
    confidence_threshold: float = 0.5
    buffered_frames: int = 0
    detected: bool = False
    confidence: float | None = None
    bbox: list[float] | None = None
    message: str | None = None


class RoadPipelineSummary(BaseModel):
    """Module 2G orchestration timing and degradation metadata."""

    processing_ms: float = 0.0
    stage_times_ms: dict[str, float] = Field(default_factory=dict)
    warnings: list[str] = Field(default_factory=list)


class RoadAnalysisResponse(BaseModel):
    objects: list[RoadObject] = Field(default_factory=list)
    segmentation: RoadSegmentationSummary | None = None
    tracking: RoadTrackingSummary | None = None
    depth: RoadDepthSummary | None = None
    traffic_lights: RoadTrafficLightSummary | None = None
    pedestrian_temporal: RoadPedestrianTemporalSummary | None = None
    pipeline: RoadPipelineSummary | None = None
    stream_id: str | None = None
    frame_id: int = 0
    timestamp: datetime
    phase: str = "2H"
    message: str = "Road frame processed by Modules 2B–2G"


class MaintenancePredictRequest(BaseModel):
    """Nested 3B–3E component feature maps, or one flat enriched map."""

    telemetry: dict[str, Any] = Field(default_factory=dict)


class MaintenanceComponentSummary(BaseModel):
    component: str
    status: str
    severity: str | None = None
    health_score: float | None = None
    maintenance_required: bool | None = None
    confidence: float | None = None
    result: dict[str, Any] | None = None
    explanation: dict[str, Any] | None = None
    explanation_error: str | None = None
    missing_features: list[str] = Field(default_factory=list)
    error: str | None = None
    latency_ms: float = 0.0


class MaintenanceAlertSummary(BaseModel):
    component: str
    severity: str
    message: str


class MaintenanceRunResponse(BaseModel):
    vehicle_id: UUID
    status: str
    overall_severity: str
    timestamp: datetime
    components: dict[str, MaintenanceComponentSummary]
    alerts: list[MaintenanceAlertSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    processing_ms: float = 0.0
    stage_times_ms: dict[str, float] = Field(default_factory=dict)
    persisted: int = 0
    ml_model_version: str
    phase: str = "3H"


class MaintenancePredictionResponse(BaseModel):
    id: UUID | None = None
    vehicle_id: UUID
    component: str
    health_score: float
    anomaly_score: float | None = None
    predicted_replacement_date: datetime | None = None
    predicted_remaining_km: int | None = None
    confidence: float | None = None
    shap_explanation: dict[str, Any] | None = None
    ml_model_version: str | None = None
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


class SafetyEventResponse(BaseModel):
    id: UUID
    vehicle_id: UUID
    driver_id: UUID
    session_id: UUID | None = None
    event_type: str
    severity: str
    timestamp: datetime
    latitude: float | None = None
    longitude: float | None = None
    telemetry_snapshot: dict[str, Any] | None = None
    video_clip_url: str | None = None
    xai_explanation: str | None = None
    acknowledged: bool = False
    acknowledged_at: datetime | None = None

    model_config = {"from_attributes": True}


class EventDetectRequest(BaseModel):
    driver_id: UUID
    session_id: UUID | None = None
    driver_state: dict[str, Any] = Field(default_factory=dict)
    road_state: dict[str, Any] = Field(default_factory=dict)
    telemetry: dict[str, Any] = Field(default_factory=dict)
    risk_score: float | None = None
    attach_clips: bool = True
    enqueue_clip_retry: bool = False


class EventSummary(BaseModel):
    id: UUID
    event_type: str
    severity: str
    timestamp: datetime
    video_clip_url: str | None = None
    xai_explanation: str | None = None


class EventDetectResponse(BaseModel):
    vehicle_id: UUID
    driver_id: UUID
    session_id: UUID | None = None
    detected: int = 0
    persisted: int = 0
    events: list[EventSummary] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    skipped_detectors: list[str] = Field(default_factory=list)
    completed_at: datetime
    phase: str = "4F"


class EventAcknowledgeRequest(BaseModel):
    driver_id: UUID | None = None


class EventListResponse(BaseModel):
    vehicle_id: UUID
    events: list[SafetyEventResponse] = Field(default_factory=list)
    count: int = 0
    phase: str = "4F"
    warning: str | None = None


class ChatRequest(BaseModel):
    message: str
    vehicle_id: UUID | None = None
    driver_id: UUID | None = None
    conversation_id: UUID | None = None
    stream: bool = True
    persist: bool = True


class ChatCitation(BaseModel):
    source: str


class ChatResponse(BaseModel):
    conversation_id: UUID | None = None
    vehicle_id: UUID | None = None
    message: str
    reply: str
    intent: str
    route: str
    citations: list[str] = Field(default_factory=list)
    obd_matches: list[dict[str, Any]] = Field(default_factory=list)
    telemetry_context: str | None = None
    maintenance_context: str | None = None
    conversation_memory: str | None = None
    memory_message_count: int = 0
    llm_backend: str | None = None
    llm_model: str | None = None
    warnings: list[str] = Field(default_factory=list)
    phase: str = "5G"


class ConversationSummary(BaseModel):
    id: UUID
    vehicle_id: UUID | None = None
    driver_id: UUID | None = None
    started_at: datetime
    message_count: int = 0
    last_user_message: str | None = None
    last_assistant_message: str | None = None


class ConversationListResponse(BaseModel):
    vehicle_id: UUID
    conversations: list[ConversationSummary] = Field(default_factory=list)
    count: int = 0
    phase: str = "5G"
    warning: str | None = None


class ConversationDetailResponse(BaseModel):
    id: UUID
    vehicle_id: UUID | None = None
    driver_id: UUID | None = None
    started_at: datetime
    messages: list[dict[str, Any]] = Field(default_factory=list)
    phase: str = "5G"


class FleetOverviewResponse(BaseModel):
    vehicle_count: int = 0
    active_alerts: int = 0
    average_risk: float = 0.0
    online_vehicles: int = 0
    phase: str = "6A"


class TelemetrySnapshot(BaseModel):
    vehicle_id: UUID
    speed_kmh: float | None = None
    rpm: int | None = None
    battery_soc_pct: float | None = None
    latitude: float | None = None
    longitude: float | None = None
    timestamp: datetime


class XAIExplainRequest(BaseModel):
    event_id: UUID | None = None
    event_type: str | None = None
    frame_id: str | None = None
    component: str | None = None
    vehicle_id: UUID | None = None


class XAIExplainResponse(BaseModel):
    explanation: str
    method: str
    heatmap_url: str | None = None
    ig_heatmap_url: str | None = None
    shap_values: dict[str, Any] | None = None
    rule_trace: dict[str, Any] | None = None
    activation_mass: float | None = None
    attribution: str | None = None
    phase: str = "6G"
