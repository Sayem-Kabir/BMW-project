from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class HeadPose(BaseModel):
    pitch: float = 0.0
    yaw: float = 0.0
    roll: float = 0.0


class DriverAnalysisResponse(BaseModel):
    alertness_score: int = Field(ge=0, le=100)
    risk_level: str
    ear_value: float
    mar_value: float
    yawn_count: int = 0
    head_pose: HeadPose
    phone_detected: bool = False
    seatbelt_worn: bool = True
    consecutive_drowsy_frames: int = 0
    xai_heatmap_url: str | None = None
    phase: str = "scaffold"
    message: str = "Driver monitoring pipeline not trained yet (Phase 1)"


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
    timestamp: datetime


class RoadObject(BaseModel):
    id: str
    class_name: str = Field(alias="class")
    confidence: float
    bbox: list[float] | None = None
    distance_m: float | None = None
    intent: str | None = None
    state: str | None = None

    model_config = {"populate_by_name": True}


class RoadAnalysisResponse(BaseModel):
    objects: list[RoadObject] = []
    frame_id: int = 0
    timestamp: datetime
    phase: str = "scaffold"
    message: str = "Road understanding pipeline not trained yet (Phase 2)"


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

    model_config = {"from_attributes": True}


class SafetyEventResponse(BaseModel):
    id: UUID
    vehicle_id: UUID
    driver_id: UUID
    event_type: str
    severity: str
    timestamp: datetime
    latitude: float | None = None
    longitude: float | None = None
    telemetry_snapshot: dict[str, Any] | None = None
    video_clip_url: str | None = None
    xai_explanation: str | None = None
    acknowledged: bool = False

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str
    vehicle_id: UUID | None = None
    conversation_id: UUID | None = None


class FleetOverviewResponse(BaseModel):
    vehicle_count: int = 0
    active_alerts: int = 0
    average_risk: float = 0.0
    online_vehicles: int = 0


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


class XAIExplainResponse(BaseModel):
    explanation: str
    method: str
    heatmap_url: str | None = None
    shap_values: dict[str, Any] | None = None
    phase: str = "scaffold"
