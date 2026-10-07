from __future__ import annotations

from sqlalchemy import CheckConstraint, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from api.base import Base, TimestampMixin


class Industry(TimestampMixin, Base):
    __tablename__ = "industries"
    __table_args__ = (
        UniqueConstraint("name", name="uq_industries_name"),
        CheckConstraint(
            "status IN ('draft', 'published', 'archived')",
            name="status",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    slug: Mapped[str] = mapped_column(String(140), unique=True, index=True)
    summary: Mapped[str | None] = mapped_column(String(300))
    description: Mapped[str | None] = mapped_column(Text)
    icon: Mapped[str | None] = mapped_column(String(60))
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    seo_title: Mapped[str | None] = mapped_column(String(160))
    seo_description: Mapped[str | None] = mapped_column(String(320))
    is_placeholder: Mapped[bool] = mapped_column(default=False, server_default="false")