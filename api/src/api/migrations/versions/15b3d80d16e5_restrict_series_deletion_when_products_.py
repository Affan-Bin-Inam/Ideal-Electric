"""restrict series deletion when products use it

Revision ID: 15b3d80d16e5
Revises: c779478eabb0
Create Date: 2026-10-11 17:55:04.749367

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '15b3d80d16e5'
down_revision: Union[str, Sequence[str], None] = 'c779478eabb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint('fk_products_series_brand_consistency', 'products', type_='foreignkey')
    op.create_foreign_key(
        'fk_products_series_brand_consistency', 'products', 'series',
        ['series_id', 'brand_id'], ['id', 'brand_id'], ondelete='RESTRICT',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_products_series_brand_consistency', 'products', type_='foreignkey')
    op.create_foreign_key(
        'fk_products_series_brand_consistency', 'products', 'series',
        ['series_id', 'brand_id'], ['id', 'brand_id'], ondelete='SET NULL',
    )
