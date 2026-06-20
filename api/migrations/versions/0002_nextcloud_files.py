"""Nextcloud sync state — table nextcloud_files.

Revision: 0002
"""
from alembic import op
import sqlalchemy as sa

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'nextcloud_files',
        sa.Column('path',      sa.Text(),     primary_key=True),   # chemin relatif NC
        sa.Column('etag',      sa.String(64), nullable=False),     # détection de changement
        sa.Column('chunks',    sa.Integer(),  nullable=False, server_default='0'),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table('nextcloud_files')
