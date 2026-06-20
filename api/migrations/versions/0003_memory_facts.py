"""Mémoire long terme durable — table memory_facts.

Revision: 0003
"""
from alembic import op
import sqlalchemy as sa

revision = '0003'
down_revision = '0002'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'memory_facts',
        sa.Column('id',         sa.String(36),  primary_key=True),
        sa.Column('text',       sa.Text(),      nullable=False),
        sa.Column('kind',       sa.String(32),  nullable=False, server_default='fact'),
        sa.Column('session_id', sa.String(36),  nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_memory_facts_created_at', 'memory_facts', ['created_at'])


def downgrade() -> None:
    op.drop_table('memory_facts')
