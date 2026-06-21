"""Module cybersécurité : inventaire d'hôtes + findings d'audit.

Revision: 0007
"""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'cyber_hosts',
        sa.Column('id',         sa.String(36),  primary_key=True),
        sa.Column('label',      sa.String(64),  nullable=False, unique=True),
        sa.Column('hostname',   sa.String(255), nullable=False),
        sa.Column('port',       sa.Integer(),   nullable=False, server_default='22'),
        sa.Column('username',   sa.String(64),  nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        'cyber_findings',
        sa.Column('id',             sa.String(36),  primary_key=True),
        sa.Column('host_id',        sa.String(36),  sa.ForeignKey('cyber_hosts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('check',          sa.String(64),  nullable=False),
        sa.Column('severity',       sa.String(16),  nullable=False),   # info|low|medium|high|critical
        sa.Column('title',          sa.Text(),      nullable=False),
        sa.Column('detail',         sa.Text(),      nullable=True),
        sa.Column('recommendation', sa.Text(),      nullable=True),
        sa.Column('remediation',    sa.Text(),      nullable=True),    # commande SSH proposée
        sa.Column('created_at',     sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_findings_host', 'cyber_findings', ['host_id'])


def downgrade() -> None:
    op.drop_table('cyber_findings')
    op.drop_table('cyber_hosts')
