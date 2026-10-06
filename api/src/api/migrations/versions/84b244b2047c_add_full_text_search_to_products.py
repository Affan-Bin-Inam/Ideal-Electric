"""add full text search to products

Revision ID: 84b244b2047c
Revises: 630f107870ca
Create Date: 2026-10-06 07:27:48.901422

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '84b244b2047c'
down_revision: Union[str, Sequence[str], None] = '630f107870ca'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
    op.add_column('products', sa.Column('search_vector', postgresql.TSVECTOR(), sa.Computed("to_tsvector('english', coalesce(name, '') || ' ' || coalesce(summary, '') || ' ' || coalesce(description, ''))", persisted=True), nullable=False))
    op.create_index('ix_products_name_trgm', 'products', ['name'], unique=False, postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.create_index('ix_products_search_vector', 'products', ['search_vector'], unique=False, postgresql_using='gin')
    # ### end Alembic commands ###


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('ix_products_search_vector', table_name='products', postgresql_using='gin')
    op.drop_index('ix_products_name_trgm', table_name='products', postgresql_using='gin', postgresql_ops={'name': 'gin_trgm_ops'})
    op.drop_column('products', 'search_vector')
    # ### end Alembic commands ###
