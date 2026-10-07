from __future__ import annotations

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from api.base import Base


class CategoryAttribute(Base):
    __tablename__ = "category_attributes"

    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
    )
    attribute_id: Mapped[int] = mapped_column(
        ForeignKey("attribute_definitions.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    is_required: Mapped[bool] = mapped_column(default=False, server_default="false")