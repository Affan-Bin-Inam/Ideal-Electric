from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.base import Base, TimestampMixin


class Inquiry(TimestampMixin, Base):
    __tablename__ = "inquiries"
    __table_args__ = (
        CheckConstraint(
            "status IN ('new', 'contacted', 'quoted', 'closed', 'spam')", name="status"
        ),
        Index("ix_inquiries_status_created", "status", "created_at"),
        Index("ix_inquiries_ip_created", "ip_hash", "created_at"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), index=True
    )
    product_name_snapshot: Mapped[str | None] = mapped_column(String(200))
    selected_options: Mapped[dict | None] = mapped_column(JSONB)
    name: Mapped[str] = mapped_column(String(120))
    company: Mapped[str | None] = mapped_column(String(120))
    email: Mapped[str | None] = mapped_column(String(254))
    phone: Mapped[str] = mapped_column(String(30))
    city: Mapped[str | None] = mapped_column(String(80))
    message: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="new", server_default="new")
    assigned_to_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    source_page: Mapped[str | None] = mapped_column(String(300))
    ip_hash: Mapped[str] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(300))