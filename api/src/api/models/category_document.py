from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.media_asset import MediaAsset


class CategoryDocument(TimestampMixin, Base):
    __tablename__ = "category_documents"
    __table_args__ = (
        CheckConstraint(
            "doc_type IN ('datasheet', 'rate_list', 'certificate', 'manual', 'brochure', 'other')",
            name="doc_type",
        ),
        CheckConstraint("access IN ('public', 'on_request')", name="access"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    asset_id: Mapped[int] = mapped_column(ForeignKey("media_assets.id", ondelete="RESTRICT"))
    title: Mapped[str] = mapped_column(String(200))
    doc_type: Mapped[str] = mapped_column(String(30), default="rate_list", server_default="rate_list")
    access: Mapped[str] = mapped_column(String(20), default="public", server_default="public")
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")

    asset: Mapped["MediaAsset"] = relationship()