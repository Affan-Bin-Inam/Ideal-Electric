"""enforce series belongs to product brand

Revision ID: 630f107870ca
Revises: 7d1210087e0d
Create Date: 2026-10-06 06:56:48.385940

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '630f107870ca'
down_revision: Union[str, Sequence[str], None] = '7d1210087e0d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_unique_constraint('uq_series_id_brand_id', 'series', ['id', 'brand_id'])
    op.drop_constraint(op.f('fk_products_series_id_series'), 'products', type_='foreignkey')
    op.create_foreign_key('fk_products_series_brand_consistency', 'products', 'series', ['series_id', 'brand_id'], ['id', 'brand_id'], ondelete='SET NULL')
    op.create_check_constraint(
        'series_requires_brand',
        'products',
        'series_id IS NULL OR brand_id IS NOT NULL',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_products_series_requires_brand', 'products', type_='check')
    op.drop_constraint('fk_products_series_brand_consistency', 'products', type_='foreignkey')
    op.create_foreign_key(op.f('fk_products_series_id_series'), 'products', 'series', ['series_id'], ['id'], ondelete='SET NULL')
    op.drop_constraint('uq_series_id_brand_id', 'series', type_='unique')