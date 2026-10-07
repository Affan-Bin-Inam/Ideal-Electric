from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, ForeignKeyConstraint, String, Text, Computed, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import TSVECTOR

from api.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.brand import Brand
    from api.models.category import Category
    from api.models.series import Series
    from api.models.product_highlight import ProductHighlight
    from api.models.product_image import ProductImage
    from api.models.product_attribute_value import ProductAttributeValue


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="status",
        ),
        CheckConstraint(
            "series_id IS NULL OR brand_id IS NOT NULL",
            name="series_requires_brand",
        ),
        ForeignKeyConstraint(
            ["series_id", "brand_id"],
            ["series.id", "series.brand_id"],
            name="fk_products_series_brand_consistency",
            ondelete="SET NULL",
        ),
        Index("ix_products_search_vector", "search_vector", postgresql_using="gin"),
        Index(
            "ix_products_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
        Index("ix_products_category_status_sort", "category_id", "status", "sort_order"),
        Index("ix_products_series_id", "series_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT")
    )
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL")
    )
    series_id: Mapped[int | None] = mapped_column()
    name: Mapped[str] = mapped_column(String(200))
    slug: Mapped[str] = mapped_column(String(220), unique=True, index=True)
    model_code: Mapped[str | None] = mapped_column(String(80))
    summary: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    is_featured: Mapped[bool] = mapped_column(default=False, server_default="false")
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    seo_title: Mapped[str | None] = mapped_column(String(160))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    is_placeholder: Mapped[bool] = mapped_column(default=False, server_default="false")

    category: Mapped["Category"] = relationship()
    brand: Mapped["Brand | None"] = relationship()
    series: Mapped["Series | None"] = relationship()

    search_vector: Mapped[str] = mapped_column(
    TSVECTOR,
    Computed(
        "to_tsvector('english', coalesce(name, '') || ' ' || "
        "coalesce(summary, '') || ' ' || coalesce(description, ''))",
        persisted=True,
            ),
    )

    highlights: Mapped[list["ProductHighlight"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductHighlight.sort_order",
    )

    images: Mapped[list["ProductImage"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="ProductImage.sort_order",
    )

    attribute_values: Mapped[list["ProductAttributeValue"]] = relationship(
        back_populates="product",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )