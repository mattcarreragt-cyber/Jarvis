"""Agenda : tâches planifiées + notifications.

Revision: 0004
"""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'scheduled_tasks',
        sa.Column('id',            sa.String(36),  primary_key=True),
        sa.Column('label',         sa.Text(),      nullable=False),
        sa.Column('kind',          sa.String(16),  nullable=False),   # reminder | prompt
        sa.Column('payload',       sa.Text(),      nullable=False),   # texte du rappel / message à router
        sa.Column('schedule_kind', sa.String(16),  nullable=False),   # once | daily | interval
        sa.Column('time_of_day',   sa.String(5),   nullable=True),    # "HH:MM" (daily)
        sa.Column('interval_sec',  sa.Integer(),   nullable=True),    # interval
        sa.Column('next_run',      sa.DateTime(timezone=True), nullable=False),
        sa.Column('enabled',       sa.Boolean(),   nullable=False, server_default=sa.true()),
        sa.Column('last_run',      sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at',    sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_tasks_next_run', 'scheduled_tasks', ['next_run'])

    op.create_table(
        'notifications',
        sa.Column('id',         sa.String(36),  primary_key=True),
        sa.Column('text',       sa.Text(),      nullable=False),
        sa.Column('source',     sa.String(64),  nullable=True),     # label de la tâche
        sa.Column('read',       sa.Boolean(),   nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_notif_created_at', 'notifications', ['created_at'])


def downgrade() -> None:
    op.drop_table('notifications')
    op.drop_table('scheduled_tasks')
