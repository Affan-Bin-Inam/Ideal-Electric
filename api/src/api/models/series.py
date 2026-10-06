from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.brand import Brand


class Series(TimestampMixin, Base):
    __tablename__ = "series"
    __table_args__ = (
        UniqueConstraint("brand_id", "name", name="uq_series_brand_name"),
        UniqueConstraint("id", "brand_id", name="uq_series_id_brand_id"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    brand_id: Mapped[int] = mapped_column(ForeignKey("brands.id", ondelete="RESTRICT"))
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    is_placeholder: Mapped[bool] = mapped_column(default=False, server_default="false")

    brand: Mapped["Brand"] = relationship(back_populates="series")