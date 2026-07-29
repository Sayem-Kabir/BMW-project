"""Spec leftover — password reset token columns (forgot/reset password)."""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "007_password_reset_gdpr"
down_revision = "006_perf_indexes_13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("password_reset_token", sa.String(128), nullable=True))
    op.add_column(
        "users",
        sa.Column("password_reset_expires", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "password_reset_expires")
    op.drop_column("users", "password_reset_token")
