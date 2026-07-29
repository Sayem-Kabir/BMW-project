"""Spec Phase 11C — safety event feedback columns for retrain export."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "004_event_feedback_11"
down_revision = "003_auth_rbac"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "safety_events",
        sa.Column("feedback_label", sa.String(length=40), nullable=True),
    )
    op.add_column(
        "safety_events",
        sa.Column("feedback_note", sa.Text(), nullable=True),
    )
    op.add_column(
        "safety_events",
        sa.Column("feedback_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_safety_events_feedback",
        "safety_events",
        ["feedback_label"],
    )


def downgrade() -> None:
    op.drop_index("idx_safety_events_feedback", table_name="safety_events")
    op.drop_column("safety_events", "feedback_at")
    op.drop_column("safety_events", "feedback_note")
    op.drop_column("safety_events", "feedback_label")
