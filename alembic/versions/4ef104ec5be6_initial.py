"""initial

Revision ID: 4ef104ec5be6
Revises:
Create Date: 2026-04-19 17:10:13.674026

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "4ef104ec5be6"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE category AS ENUM ('birthday', 'anniversary', 'meeting', 'personal')")
    op.execute(
        "CREATE TYPE recurrence AS ENUM "
        "('one_time', 'daily', 'weekly', 'monthly', "
        "'every_6_months', 'yearly', 'every_18_months', 'every_2_years')"
    )

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", sa.Enum("birthday", "anniversary", "meeting", "personal", name="category"), nullable=False),
        sa.Column(
            "recurrence",
            sa.Enum(
                "one_time", "daily", "weekly", "monthly",
                "every_6_months", "yearly", "every_18_months", "every_2_years",
                name="recurrence",
            ),
            nullable=False,
        ),
        sa.Column("next_remind_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_completed", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_events_user_id", "events", ["user_id"])

    op.create_table(
        "event_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.Integer(), sa.ForeignKey("events.id", ondelete="CASCADE"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reminded_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_event_history_event_id", "event_history", ["event_id"])


def downgrade() -> None:
    op.drop_table("event_history")
    op.drop_table("events")
    op.drop_table("users")
    op.execute("DROP TYPE recurrence")
    op.execute("DROP TYPE category")
