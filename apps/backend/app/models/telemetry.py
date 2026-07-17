import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class VehicleTelemetry(Base):
    """Time-series vehicle sensor readings (TimescaleDB hypertable when available)."""

    __tablename__ = "vehicle_telemetry"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    vehicle_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("vehicles.id"),
        primary_key=True,
        nullable=False,
    )
    driver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("drivers.id"), nullable=True
    )
    speed_kmh: Mapped[float | None] = mapped_column(Float, nullable=True)
    rpm: Mapped[int | None] = mapped_column(Integer, nullable=True)
    oil_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    coolant_temp_c: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_soc_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    battery_health_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    tire_pressure_fl: Mapped[float | None] = mapped_column(Float, nullable=True)
    tire_pressure_fr: Mapped[float | None] = mapped_column(Float, nullable=True)
    tire_pressure_rl: Mapped[float | None] = mapped_column(Float, nullable=True)
    tire_pressure_rr: Mapped[float | None] = mapped_column(Float, nullable=True)
    brake_pedal_pct: Mapped[float | None] = mapped_column(Float, nullable=True)
    steering_angle_deg: Mapped[float | None] = mapped_column(Float, nullable=True)
    longitude: Mapped[float | None] = mapped_column(Float, nullable=True)
    latitude: Mapped[float | None] = mapped_column(Float, nullable=True)
