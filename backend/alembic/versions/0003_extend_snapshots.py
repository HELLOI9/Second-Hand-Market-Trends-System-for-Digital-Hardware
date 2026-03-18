"""
Add extended fields to price_snapshots: area, seller, image_url, publish_time, crawled_at
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime


revision = "0003_extend_snapshots"
down_revision = "0002_seed_hardware"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("price_snapshots", sa.Column("area", sa.String(100), nullable=True))
    op.add_column("price_snapshots", sa.Column("seller", sa.String(100), nullable=True))
    op.add_column("price_snapshots", sa.Column("image_url", sa.Text(), nullable=True))
    op.add_column("price_snapshots", sa.Column("publish_time", sa.DateTime(), nullable=True))
    op.add_column(
        "price_snapshots",
        sa.Column("crawled_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_column("price_snapshots", "crawled_at")
    op.drop_column("price_snapshots", "publish_time")
    op.drop_column("price_snapshots", "image_url")
    op.drop_column("price_snapshots", "seller")
    op.drop_column("price_snapshots", "area")
