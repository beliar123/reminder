"""add persistent reminder fields

Revision ID: a1b2c3d4e5f6
Revises: 21faa2667d11
Create Date: 2026-04-26 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = '21faa2667d11'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('events', sa.Column('remind_interval', sa.Integer(), nullable=True))
    op.add_column('events', sa.Column('remind_max_attempts', sa.Integer(), nullable=True))
    op.add_column('event_history', sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='1'))
    op.add_column('event_history', sa.Column('next_nag_at', sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f('ix_event_history_next_nag_at'), 'event_history', ['next_nag_at'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_event_history_next_nag_at'), table_name='event_history')
    op.drop_column('event_history', 'next_nag_at')
    op.drop_column('event_history', 'attempt_count')
    op.drop_column('events', 'remind_max_attempts')
    op.drop_column('events', 'remind_interval')
