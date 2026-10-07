from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.base import Base, TimestampMixin

if TYPE_CHECKING:
    from api.models.product import Product


class ProductHighlight(TimestampMixin, Base):
    __tablename__ = "product_highlights"
    __table_args__ = (
        CheckConstraint("kind IN ('feature', 'application')", name="kind"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[str] = mapped_column(String(20))
    text: Mapped[str] = mapped_column(String(300))
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")

    product: Mapped["Product"] = relationship(back_populates="highlights")