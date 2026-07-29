-- Spec Phase 10 exit criteria — EXPLAIN ANALYZE helpers for top dashboard queries.
-- Run against a populated DB (after seed). Aim: index scans, not seq scans on large tables.

-- Fleet alerts (unacked first pattern)
EXPLAIN ANALYZE
SELECT id, severity, event_type, timestamp
FROM safety_events
WHERE acknowledged = FALSE
ORDER BY timestamp DESC
LIMIT 50;

-- Org-scoped vehicles
EXPLAIN ANALYZE
SELECT id, name, status, org_id
FROM vehicles
WHERE org_id = '00000000-0000-4000-8000-000000000010';

-- Driver weekly scores
EXPLAIN ANALYZE
SELECT *
FROM driver_scores
WHERE driver_id = '00000000-0000-4000-8000-000000000001'
ORDER BY created_at DESC
LIMIT 30;

-- Audit log by org
EXPLAIN ANALYZE
SELECT *
FROM audit_log
WHERE org_id = '00000000-0000-4000-8000-000000000010'
ORDER BY created_at DESC
LIMIT 50;

-- Recommended indexes (idempotent-ish; skip if already present)
CREATE INDEX IF NOT EXISTS idx_safety_events_unacked
  ON safety_events (timestamp DESC)
  WHERE acknowledged = FALSE;

CREATE INDEX IF NOT EXISTS idx_vehicles_org
  ON vehicles (org_id);

CREATE INDEX IF NOT EXISTS idx_driver_scores_driver_created
  ON driver_scores (driver_id, created_at DESC);

-- audit_log already has idx_audit_log_org from migration 003
