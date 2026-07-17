"""initial_schema

Revision ID: 001_initial
Revises:
Create Date: 2026-07-17
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.create_table(
        "organizations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(100), nullable=True),
        sa.Column("role", sa.String(50), nullable=False, server_default="fleet_manager"),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "vehicles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("vin", sa.String(17), unique=True, nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("year", sa.Integer(), nullable=True),
        sa.Column("fuel_type", sa.String(20), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE")),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "drivers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("license_number", sa.String(50), nullable=True),
        sa.Column("org_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("organizations.id", ondelete="CASCADE")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("ix_drivers_email", "drivers", ["email"], unique=True)

    op.create_table(
        "vehicle_telemetry",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=True),
        sa.Column("speed_kmh", sa.Float(), nullable=True),
        sa.Column("rpm", sa.Integer(), nullable=True),
        sa.Column("oil_temp_c", sa.Float(), nullable=True),
        sa.Column("coolant_temp_c", sa.Float(), nullable=True),
        sa.Column("battery_soc_pct", sa.Float(), nullable=True),
        sa.Column("battery_health_pct", sa.Float(), nullable=True),
        sa.Column("tire_pressure_fl", sa.Float(), nullable=True),
        sa.Column("tire_pressure_fr", sa.Float(), nullable=True),
        sa.Column("tire_pressure_rl", sa.Float(), nullable=True),
        sa.Column("tire_pressure_rr", sa.Float(), nullable=True),
        sa.Column("brake_pedal_pct", sa.Float(), nullable=True),
        sa.Column("steering_angle_deg", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("time", "vehicle_id"),
    )

    # Convert to TimescaleDB hypertable when the extension is available
    op.execute(
        """
        DO $$
        BEGIN
          IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'timescaledb') THEN
            PERFORM create_hypertable('vehicle_telemetry', 'time', if_not_exists => TRUE);
          END IF;
        EXCEPTION WHEN OTHERS THEN
          RAISE NOTICE 'TimescaleDB hypertable skipped: %', SQLERRM;
        END $$;
        """
    )

    op.create_table(
        "driver_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("alertness_score_avg", sa.Float(), nullable=True),
        sa.Column("alertness_score_min", sa.Float(), nullable=True),
        sa.Column("drowsy_events", sa.Integer(), server_default="0"),
        sa.Column("yawn_events", sa.Integer(), server_default="0"),
        sa.Column("phone_events", sa.Integer(), server_default="0"),
        sa.Column("seatbelt_events", sa.Integer(), server_default="0"),
        sa.Column("headpose_events", sa.Integer(), server_default="0"),
        sa.Column("total_frames_analyzed", sa.Integer(), server_default="0"),
    )

    op.create_table(
        "safety_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("driver_sessions.id"), nullable=True),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("severity", sa.String(20), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("telemetry_snapshot", postgresql.JSONB(), nullable=True),
        sa.Column("video_clip_url", sa.String(500), nullable=True),
        sa.Column("xai_explanation", sa.Text(), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("acknowledged_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_safety_events_vehicle", "safety_events", ["vehicle_id", "timestamp"])
    op.create_index("idx_safety_events_severity", "safety_events", ["severity", "acknowledged"])

    op.create_table(
        "maintenance_predictions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=False),
        sa.Column("component", sa.String(50), nullable=False),
        sa.Column("health_score", sa.Float(), nullable=False),
        sa.Column("anomaly_score", sa.Float(), nullable=True),
        sa.Column("predicted_replacement_date", sa.Date(), nullable=True),
        sa.Column("predicted_remaining_km", sa.Integer(), nullable=True),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("shap_explanation", postgresql.JSONB(), nullable=True),
        sa.Column("ml_model_version", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_index("idx_maintenance_vehicle", "maintenance_predictions", ["vehicle_id", "component"])

    op.create_table(
        "driver_scores",
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=False),
        sa.Column("safety_score", sa.Integer(), nullable=False),
        sa.Column("harsh_braking_count", sa.Integer(), server_default="0"),
        sa.Column("rapid_acceleration_count", sa.Integer(), server_default="0"),
        sa.Column("speeding_events", sa.Integer(), server_default="0"),
        sa.Column("drowsiness_events", sa.Integer(), server_default="0"),
        sa.Column("phone_usage_events", sa.Integer(), server_default="0"),
        sa.Column("no_seatbelt_events", sa.Integer(), server_default="0"),
        sa.Column("total_distance_km", sa.Float(), server_default="0"),
        sa.Column("total_drive_time_minutes", sa.Integer(), server_default="0"),
        sa.PrimaryKeyConstraint("date", "driver_id"),
    )

    op.create_table(
        "assistant_conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("vehicle_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("vehicles.id"), nullable=True),
        sa.Column("driver_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("drivers.id"), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.Column("messages", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
    )


def downgrade() -> None:
    op.drop_table("assistant_conversations")
    op.drop_table("driver_scores")
    op.drop_index("idx_maintenance_vehicle", table_name="maintenance_predictions")
    op.drop_table("maintenance_predictions")
    op.drop_index("idx_safety_events_severity", table_name="safety_events")
    op.drop_index("idx_safety_events_vehicle", table_name="safety_events")
    op.drop_table("safety_events")
    op.drop_table("driver_sessions")
    op.drop_table("vehicle_telemetry")
    op.drop_index("ix_drivers_email", table_name="drivers")
    op.drop_table("drivers")
    op.drop_table("vehicles")
    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")
    op.drop_table("organizations")
