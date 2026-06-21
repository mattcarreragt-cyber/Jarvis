"""Webhooks entrants (déclencheurs externes).

Revision: 0006
"""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'webhooks',
        sa.Column('id',            sa.String(36),  primary_key=True),
        sa.Column('token',         sa.String(48),  nullable=False, unique=True),
        sa.Column('label',         sa.Text(),      nullable=False),
        sa.Column('message',       sa.Text(),      nullable=False),   # prompt routé à l'exécution
        sa.Column('enabled',       sa.Boolean(),   nullable=False, server_default=sa.true()),
        sa.Column('run_count',     sa.Integer(),   nullable=False, server_default='0'),
        sa.Column('last_triggered', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at',    sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_webhooks_token', 'webhooks', ['token'])


def downgrade() -> None:
    op.drop_table('webhooks')
