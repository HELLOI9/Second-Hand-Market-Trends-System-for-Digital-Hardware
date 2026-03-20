"""Add LLM validation fields to price_snapshots

Revision ID: 0005_add_llm_validation
Revises: 0004_add_composite_index
Create Date: 2026-03-19

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0005_add_llm_validation'
down_revision = '0004_add_composite_index'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('price_snapshots', sa.Column('is_valid', sa.Boolean(), nullable=True))
    op.add_column('price_snapshots', sa.Column('validation_reason', sa.Text(), nullable=True))
    op.create_index('ix_snapshots_is_valid', 'price_snapshots', ['is_valid'])


def downgrade():
    op.drop_index('ix_snapshots_is_valid', table_name='price_snapshots')
    op.drop_column('price_snapshots', 'validation_reason')
    op.drop_column('price_snapshots', 'is_valid')
