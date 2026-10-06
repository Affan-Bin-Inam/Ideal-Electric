from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.brand import Brand
    from api.models.category import Category
    from api.models.series import Series


class Product(TimestampMixin, Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT")
    )
    brand_id: Mapped[int | None] = mapped_column(
        ForeignKey("brands.id", ondelete="SET NULL")
    )
    series_id: Mapped[int | None] = mapped_column(
        ForeignKey("series.id", ondelete="SET NULL")
    )
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