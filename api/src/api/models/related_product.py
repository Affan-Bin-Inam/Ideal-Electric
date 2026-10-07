from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.base import Base


class RelatedProduct(Base):
    __tablename__ = "related_products"
    __table_args__ = (
        CheckConstraint("product_id <> related_product_id", name="no_self_relation"),
    )

    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    related_product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True, index=True
    )
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")