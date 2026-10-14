from __future__ import annotations

from sqlalchemy import CheckConstraint, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from api.base import Base, TimestampMixin

# One row per section. The set is fixed: admins edit, hide and reorder, never create or delete.
SECTION_KEYS = (
    "hero",
    "featured_categories",
    "featured_products",
    "industries",
    "why_choose_us",
    "inquiry_cta",
)


class HomepageSection(TimestampMixin, Base):
    __tablename__ = "homepage_sections"
    __table_args__ = (
        CheckConstraint(
            "key IN (" + ", ".join(f"'{k}'" for k in SECTION_KEYS) + ")", name="key"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(40), unique=True)
    heading: Mapped[str | None] = mapped_column(String(200))
    subheading: Mapped[str | None] = mapped_column(String(400))
    cta_label: Mapped[str | None] = mapped_column(String(60))
    cta_url: Mapped[str | None] = mapped_column(String(300))
    # Hero image. SET NULL means deleting the media asset empties this link instead of failing.
    image_id: Mapped[int | None] = mapped_column(ForeignKey("media_assets.id", ondelete="SET NULL"))
    # Used by why_choose_us: a short list of {title, text, icon}, always edited as a whole.
    items: Mapped[list[dict]] = mapped_column(
        JSONB, default=list, server_default=text("'[]'::jsonb")
    )
    is_visible: Mapped[bool] = mapped_column(default=True, server_default="true")
    sort_order: Mapped[int] = mapped_column(default=0, server_default="0")
    is_placeholder: Mapped[bool] = mapped_column(default=True, server_default="true")