"""
Add composite index on price_snapshots(hardware_id, snapshot_date) for faster queries.
"""

from alembic import op

revision = "0004_add_composite_index"
down_revision = "0003_extend_snapshots"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_snapshots_hw_date", "price_snapshots", ["hardware_id", "snapshot_date"])


def downgrade() -> None:
    op.drop_index("ix_snapshots_hw_date", table_name="price_snapshots")
