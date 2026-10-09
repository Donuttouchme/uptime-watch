"""worker and results

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Existing monitors become due at once (CONTEXT.md: Due).
    op.add_column(
        "monitors",
        sa.Column(
            "next_check_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_monitors_next_check_at", "monitors", ["next_check_at"])
    op.create_check_constraint(
        "ck_monitors_interval_range", "monitors", "interval_seconds BETWEEN 30 AND 86400"
    )
    op.create_check_constraint("ck_monitors_name_not_empty", "monitors", "char_length(name) >= 1")

    op.create_table(
        "results",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "monitor_id",
            sa.Integer(),
            sa.ForeignKey("monitors.id", ondelete="CASCADE", name="fk_results_monitor_id_monitors"),
            nullable=False,
        ),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("up", sa.Boolean(), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("response_time_ms", sa.Integer(), nullable=True),
        sa.Column("error", sa.String(200), nullable=True),
        # NULL passes a CHECK, so both only apply when a response arrived.
        sa.CheckConstraint("status_code BETWEEN 100 AND 599", name="ck_results_status_code_range"),
        sa.CheckConstraint("response_time_ms >= 0", name="ck_results_response_time_not_negative"),
    )
    op.create_index(
        "ix_results_monitor_id_checked_at",
        "results",
        ["monitor_id", sa.text("checked_at DESC")],
    )


def downgrade() -> None:
    op.drop_table("results")
    op.drop_constraint("ck_monitors_name_not_empty", "monitors", type_="check")
    op.drop_constraint("ck_monitors_interval_range", "monitors", type_="check")
    op.drop_index("ix_monitors_next_check_at", table_name="monitors")
    op.drop_column("monitors", "next_check_at")
