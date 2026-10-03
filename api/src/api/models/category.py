from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from api.base import Base, TimestampMixin


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint("parent_id", "name", name="uq_categories_parent_name"),
        CheckConstraint("parent_id <> id", name="no_self_parent"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="RESTRICT")
    )
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    seo_title: Mapped[str | None] = mapped_column(String(160))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    is_placeholder: Mapped[bool] = mapped_column(default=False, server_default="false")

    parent: Mapped[Category | None] = relationship(
        remote_side=[id], back_populates="children"
    )
    children: Mapped[list[Category]] = relationship(
        back_populates="parent", cascade="all"
    )