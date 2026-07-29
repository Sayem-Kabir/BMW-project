"""Optional TimescaleDB continuous aggregates — Spec Phase 13."""

from __future__ import annotations

from alembic import op

revision = "008_timescale_cagg_13"
down_revision = "007_password_reset_gdpr"
branch_labels = None
depends_on = None

_CAGG_SQL = """
CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_hourly
WITH (timescaledb.continuous) AS
SELECT
  time_bucket('1 hour', time) AS bucket,
  vehicle_id,
  avg(speed_kmh) AS avg_speed_kmh,
  avg(battery_soc_pct) AS avg_battery_soc_pct,
  avg(rpm) AS avg_rpm,
  count(*) AS samples
FROM vehicle_telemetry
GROUP BY bucket, vehicle_id
WITH NO DATA;
"""


def upgrade() -> None:
    conn = op.get_bind()
    try:
        conn.exec_driver_sql(
            "SELECT 1 FROM pg_extension WHERE extname = 'timescaledb' LIMIT 1"
        )
        row = conn.exec_driver_sql(
            "SELECT 1 FROM pg_extension WHERE extname = 'timescaledb' LIMIT 1"
        ).fetchone()
        if not row:
            return
        conn.exec_driver_sql(_CAGG_SQL)
        conn.exec_driver_sql(
            """
            SELECT add_continuous_aggregate_policy(
              'telemetry_hourly',
              start_offset => INTERVAL '3 days',
              end_offset => INTERVAL '1 hour',
              schedule_interval => INTERVAL '1 hour'
            );
            """
        )
        conn.exec_driver_sql(
            """
            CREATE MATERIALIZED VIEW IF NOT EXISTS telemetry_daily
            WITH (timescaledb.continuous) AS
            SELECT
              time_bucket('1 day', time) AS bucket,
              vehicle_id,
              avg(speed_kmh) AS avg_speed_kmh,
              avg(battery_soc_pct) AS avg_battery_soc_pct,
              count(*) AS samples
            FROM vehicle_telemetry
            GROUP BY bucket, vehicle_id
            WITH NO DATA;
            """
        )
        conn.exec_driver_sql(
            """
            SELECT add_continuous_aggregate_policy(
              'telemetry_daily',
              start_offset => INTERVAL '30 days',
              end_offset => INTERVAL '1 day',
              schedule_interval => INTERVAL '1 day'
            );
            """
        )
    except Exception:
        # Plain Postgres / missing hypertable — skip silently
        pass


def downgrade() -> None:
    conn = op.get_bind()
    try:
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS telemetry_daily CASCADE;")
        conn.exec_driver_sql("DROP MATERIALIZED VIEW IF EXISTS telemetry_hourly CASCADE;")
    except Exception:
        pass
