"""Drop search_keywords from hardware_items

Revision ID: 0006_drop_search_keywords
Revises: 0005_add_llm_validation
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_drop_search_keywords"
down_revision = "0005_add_llm_validation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("hardware_items", "search_keywords")


def downgrade() -> None:
    op.add_column("hardware_items", sa.Column("search_keywords", sa.Text(), nullable=False, server_default=""))
