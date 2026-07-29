"""Spec Phase 12A — notification_preferences + notification_webhooks."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "005_notifications_12"
down_revision = "004_event_feedback_11"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "notification_preferences",
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("email_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("sms_enabled", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("push_enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("critical_only", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("phone_e164", sa.String(20), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "notification_webhooks",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("org_id", sa.UUID(), sa.ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("secret", sa.String(100), nullable=True),
        sa.Column("active", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("notification_webhooks")
    op.drop_table("notification_preferences")
