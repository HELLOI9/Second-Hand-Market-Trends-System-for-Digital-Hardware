"""P0 features: editable hardware pool, alerts, crawl runs

Revision ID: 0007_p0_features
Revises: 0006_drop_search_keywords
Create Date: 2026-05-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from app.core.hardware_pool import HARDWARE_POOL


revision = "0007_p0_features"
down_revision = "0006_drop_search_keywords"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "hardware_items",
        sa.Column("search_keywords", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
    )
    op.add_column("hardware_items", sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("hardware_items", sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))
    op.add_column("hardware_items", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))

    hardware_table = sa.table(
        "hardware_items",
        sa.column("name", sa.String),
        sa.column("search_keywords", postgresql.ARRAY(sa.Text())),
    )
    conn = op.get_bind()
    for item in HARDWARE_POOL:
        keywords = item.get("search_keywords") or [item["name"]]
        if not isinstance(keywords, list):
            keywords = [keywords]
        conn.execute(
            hardware_table.update()
            .where(hardware_table.c.name == item["name"])
            .values(search_keywords=keywords),
        )

    op.create_table(
        "price_alerts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("scope_type", sa.String(16), nullable=False),
        sa.Column("scope_value", sa.Text()),
        sa.Column("rule_type", sa.String(20), nullable=False),
        sa.Column("threshold", sa.Float()),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("channel_target", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_fired_at", sa.DateTime()),
        sa.Column("cooldown_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_price_alerts_scope", "price_alerts", ["scope_type", "scope_value", "is_active"])
    op.create_index("ix_price_alerts_target", "price_alerts", ["channel", "channel_target"])

    op.create_table(
        "crawl_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("started_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("ended_at", sa.DateTime()),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("success", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("details_json", sa.Text()),
    )
    op.create_index("ix_crawl_runs_started_at", "crawl_runs", ["started_at"])


def downgrade() -> None:
    op.drop_index("ix_crawl_runs_started_at", table_name="crawl_runs")
    op.drop_table("crawl_runs")
    op.drop_index("ix_price_alerts_target", table_name="price_alerts")
    op.drop_index("ix_price_alerts_scope", table_name="price_alerts")
    op.drop_table("price_alerts")
    op.drop_column("hardware_items", "updated_at")
    op.drop_column("hardware_items", "created_at")
    op.drop_column("hardware_items", "is_active")
    op.drop_column("hardware_items", "search_keywords")
