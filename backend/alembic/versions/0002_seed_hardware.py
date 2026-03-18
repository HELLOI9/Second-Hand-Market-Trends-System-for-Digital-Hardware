"""
初始化固定硬件池数据
"""

from alembic import op
import sqlalchemy as sa

from app.core.hardware_pool import HARDWARE_POOL


revision = "0002_seed_hardware"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    hardware_table = sa.table(
        "hardware_items",
        sa.column("name", sa.String),
        sa.column("category", sa.String),
        sa.column("search_keywords", sa.String),
    )
    op.bulk_insert(hardware_table, HARDWARE_POOL)


def downgrade() -> None:
    op.execute("DELETE FROM hardware_items")
