import uuid
from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DriverScore(Base):
    __tablename__ = "driver_scores"

    date: Mapped[date] = mapped_column(Date, primary_key=True)
    driver_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), primary_key=True
    )
    safety_score: Mapped[int] = mapped_column(Integer, nullable=False)
    harsh_braking_count: Mapped[int] = mapped_column(Integer, default=0)
    rapid_acceleration_count: Mapped[int] = mapped_column(Integer, default=0)
    speeding_events: Mapped[int] = mapped_column(Integer, default=0)
    drowsiness_events: Mapped[int] = mapped_column(Integer, default=0)
    phone_usage_events: Mapped[int] = mapped_column(Integer, default=0)
    no_seatbelt_events: Mapped[int] = mapped_column(Integer, default=0)
    total_distance_km: Mapped[float] = mapped_column(Float, default=0.0)
    total_drive_time_minutes: Mapped[int] = mapped_column(Integer, default=0)

    driver = relationship("Driver", back_populates="scores")
