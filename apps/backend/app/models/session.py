import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DriverSession(Base):
    __tablename__ = "driver_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vehicles.id"), nullable=False
    )
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    alertness_score_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    alertness_score_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    drowsy_events: Mapped[int] = mapped_column(Integer, default=0)
    yawn_events: Mapped[int] = mapped_column(Integer, default=0)
    phone_events: Mapped[int] = mapped_column(Integer, default=0)
    seatbelt_events: Mapped[int] = mapped_column(Integer, default=0)
    headpose_events: Mapped[int] = mapped_column(Integer, default=0)
    total_frames_analyzed: Mapped[int] = mapped_column(Integer, default=0)

    vehicle = relationship("Vehicle", back_populates="sessions")
    driver = relationship("Driver", back_populates="sessions")
    safety_events = relationship("SafetyEvent", back_populates="session")
