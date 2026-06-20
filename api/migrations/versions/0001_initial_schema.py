"""Initial schema — sessions, messages, routing_logs, tool_invocations.

Revision: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'sessions',
        sa.Column('id',         sa.String(36),  primary_key=True),
        sa.Column('created_at', sa.DateTime(),  server_default=sa.func.now(), nullable=False),
        sa.Column('title',      sa.Text(),      nullable=True),
    )

    op.create_table(
        'messages',
        sa.Column('id',         sa.String(36),  primary_key=True),
        sa.Column('session_id', sa.String(36),  sa.ForeignKey('sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('role',       sa.String(16),  nullable=False),   # user | assistant
        sa.Column('content',    sa.Text(),      nullable=False),
        sa.Column('agent',      sa.String(64),  nullable=True),
        sa.Column('created_at', sa.DateTime(),  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_messages_session_id', 'messages', ['session_id'])

    op.create_table(
        'routing_logs',
        sa.Column('id',         sa.String(36),  primary_key=True),
        sa.Column('request_id', sa.String(36),  nullable=False),
        sa.Column('session_id', sa.String(36),  nullable=True),
        sa.Column('intent',     sa.String(64),  nullable=True),
        sa.Column('agent',      sa.String(64),  nullable=False),
        sa.Column('method',     sa.String(16),  nullable=False),   # rules | llm | forced
        sa.Column('score',      sa.Float(),     nullable=True),
        sa.Column('created_at', sa.DateTime(),  server_default=sa.func.now(), nullable=False),
    )

    op.create_table(
        'tool_invocations',
        sa.Column('id',         sa.String(36),  primary_key=True),
        sa.Column('request_id', sa.String(36),  nullable=False),
        sa.Column('tool',       sa.String(64),  nullable=False),
        sa.Column('args',       sa.JSON(),      nullable=True),
        sa.Column('result_ok',  sa.Boolean(),   nullable=False),
        sa.Column('error',      sa.Text(),      nullable=True),
        sa.Column('created_at', sa.DateTime(),  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_tool_invocations_request_id', 'tool_invocations', ['request_id'])


def downgrade() -> None:
    op.drop_table('tool_invocations')
    op.drop_table('routing_logs')
    op.drop_table('messages')
    op.drop_table('sessions')
