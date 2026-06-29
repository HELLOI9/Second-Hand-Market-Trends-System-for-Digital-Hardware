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
        sa.column("search_keywords", sa.Text),
    )
    rows = [
        {
            "name": item["name"],
            "category": item["category"],
            "search_keywords": " ".join(item["search_keywords"])
            if isinstance(item.get("search_keywords"), list)
            else item.get("search_keywords", item["name"]),
        }
        for item in HARDWARE_POOL
    ]
    op.bulk_insert(hardware_table, rows)


def downgrade() -> None:
    op.execute("DELETE FROM hardware_items")
