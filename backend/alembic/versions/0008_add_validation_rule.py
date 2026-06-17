"""Add per-hardware validation_rule for LLM filtering

Revision ID: 0008_add_validation_rule
Revises: 0007_p0_features
Create Date: 2026-06-17
"""

from alembic import op
import sqlalchemy as sa


revision = "0008_add_validation_rule"
down_revision = "0007_p0_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("hardware_items", sa.Column("validation_rule", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("hardware_items", "validation_rule")
