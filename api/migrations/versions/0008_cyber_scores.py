"""Historique des scores de sécurité par hôte.

Revision: 0008
"""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'cyber_scores',
        sa.Column('id',         sa.String(36),  primary_key=True),
        sa.Column('host_id',    sa.String(36),  sa.ForeignKey('cyber_hosts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('score',      sa.Integer(),   nullable=False),
        sa.Column('grade',      sa.String(2),   nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_scores_host', 'cyber_scores', ['host_id', 'created_at'])


def downgrade() -> None:
    op.drop_table('cyber_scores')
