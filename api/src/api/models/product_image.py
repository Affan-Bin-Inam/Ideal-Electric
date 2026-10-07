from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.media_asset import MediaAsset
    from api.models.product import Product


class ProductImage(TimestampMixin, Base):
    __tablename__ = "product_images"
    __table_args__ = (
        UniqueConstraint("product_id", "asset_id", name="uq_product_images_product_asset"),
        Index(
            "uq_product_images_one_primary",
            "product_id",
            unique=True,
            postgresql_where=text("is_primary"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id", ondelete="CASCADE"))
    asset_id: Mapped[int] = mapped_column(ForeignKey("media_assets.id", ondelete="RESTRICT"))
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    is_primary: Mapped[bool] = mapped_column(default=False, server_default="false")
    alt_override: Mapped[str | None] = mapped_column(String(300))

    product: Mapped["Product"] = relationship(back_populates="images")
    asset: Mapped["MediaAsset"] = relationship()