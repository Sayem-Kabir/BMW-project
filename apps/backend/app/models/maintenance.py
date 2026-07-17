import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class MaintenancePrediction(Base):
    __tablename__ = "maintenance_predictions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False, index=True
    )
    component: Mapped[str] = mapped_column(String(50), nullable=False)
    health_score: Mapped[float] = mapped_column(Float, nullable=False)
    anomaly_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    predicted_replacement_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    predicted_remaining_km: Mapped[int | None] = mapped_column(Integer, nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    shap_explanation: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    ml_model_version: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    vehicle = relationship("Vehicle", back_populates="maintenance_predictions")
