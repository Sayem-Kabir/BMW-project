"""Spec Phase 13 — partial index for unacked safety events + notes."""

from __future__ import annotations

from alembic import op

revision = "006_perf_indexes_13"
down_revision = "005_notifications_12"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Matches fleet dashboard query pattern: open alerts only
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_safety_events_unacked
        ON safety_events (severity, created_at DESC)
        WHERE acknowledged = FALSE
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_safety_events_vehicle_unacked
        ON safety_events (vehicle_id, created_at DESC)
        WHERE acknowledged = FALSE
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_safety_events_vehicle_unacked")
    op.execute("DROP INDEX IF EXISTS idx_safety_events_unacked")
