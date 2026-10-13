from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from api.base import Base, TimestampMixin


class InquiryNote(TimestampMixin, Base):
    __tablename__ = "inquiry_notes"

    id: Mapped[int] = mapped_column(primary_key=True)
    inquiry_id: Mapped[int] = mapped_column(
        ForeignKey("inquiries.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    author_email: Mapped[str] = mapped_column(String(254))
    body: Mapped[str] = mapped_column(Text)