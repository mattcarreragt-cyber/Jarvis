"""Galerie média — table media_assets.

Revision: 0005
"""
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'media_assets',
        sa.Column('id',         sa.String(36),  primary_key=True),
        sa.Column('kind',       sa.String(16),  nullable=False),   # image | video
        sa.Column('prompt',     sa.Text(),      nullable=True),
        sa.Column('filename',   sa.Text(),      nullable=False),
        sa.Column('subfolder',  sa.Text(),      nullable=False, server_default=''),
        sa.Column('type',       sa.String(16),  nullable=False, server_default='output'),
        sa.Column('base_url',   sa.Text(),      nullable=True),    # ComfyUI source (RunPod) ou null
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_media_created_at', 'media_assets', ['created_at'])


def downgrade() -> None:
    op.drop_table('media_assets')
