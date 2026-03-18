"""
数据库初始迁移：建表
生成时间：2026-03-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "hardware_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False, unique=True),
        sa.Column("category", sa.String(50), nullable=False),
        sa.Column("search_keywords", sa.Text(), nullable=False),
    )

    op.create_table(
        "price_snapshots",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hardware_id", sa.Integer(), sa.ForeignKey("hardware_items.id"), nullable=False),
        sa.Column("price", sa.Float(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("item_url", sa.Text()),
        sa.Column("snapshot_date", sa.Date(), nullable=False, index=True),
    )

    op.create_table(
        "daily_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("hardware_id", sa.Integer(), sa.ForeignKey("hardware_items.id"), nullable=False),
        sa.Column("stat_date", sa.Date(), nullable=False, index=True),
        sa.Column("median_price", sa.Float(), nullable=False),
        sa.Column("avg_price", sa.Float(), nullable=False),
        sa.Column("min_price", sa.Float(), nullable=False),
        sa.Column("max_price", sa.Float(), nullable=False),
        sa.Column("sample_count", sa.Integer(), nullable=False),
        sa.Column("price_level", sa.Enum("low", "normal", "high", name="pricelevel"), nullable=False),
    )

    # 唯一约束：同一硬件同一天只有一条聚合记录
    op.create_unique_constraint("uq_daily_stats_hardware_date", "daily_stats", ["hardware_id", "stat_date"])


def downgrade() -> None:
    op.drop_table("daily_stats")
    op.drop_table("price_snapshots")
    op.drop_table("hardware_items")
    op.execute("DROP TYPE IF EXISTS pricelevel")
