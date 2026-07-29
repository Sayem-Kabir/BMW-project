-- Spec Phase 13 — TimescaleDB continuous aggregates (optional)
-- Run after Timescale extension + vehicle_telemetry hypertable exist.
-- Safe to skip when extension is unavailable (local SQLite/plain Postgres).

-- Hourly rollups for dashboard charts
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

SELECT add_continuous_aggregate_policy(
  'telemetry_hourly',
  start_offset => INTERVAL '3 days',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour'
);

-- Daily rollups
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

SELECT add_continuous_aggregate_policy(
  'telemetry_daily',
  start_offset => INTERVAL '30 days',
  end_offset => INTERVAL '1 day',
  schedule_interval => INTERVAL '1 day'
);

-- Refresh manually for demos:
-- CALL refresh_continuous_aggregate('telemetry_hourly', NULL, NULL);
