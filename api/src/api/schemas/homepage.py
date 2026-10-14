from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from api.schemas.catalogue import (
    CategoryNode, ImageOut, IndustryOut, ORMModel, ProductCard,
)

# Keep in sync with SECTION_KEYS in models/homepage_section.py (a test checks this).
SectionKey = Literal[
    "hero", "featured_categories", "featured_products",
    "industries", "why_choose_us", "inquiry_cta",
]

# Relative paths ("/contact") or full http(s) links.
CtaUrl = Annotated[str, StringConstraints(max_length=300, pattern=r"^(/|https?://)\S*$")]


class WhyItem(BaseModel):
    title: str = Field(min_length=1, max_length=80)
    text: str = Field(min_length=1, max_length=300)
    icon: str | None = Field(default=None, max_length=60)


class HomepageSectionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    heading: str | None = Field(default=None, max_length=200)
    subheading: str | None = Field(default=None, max_length=400)
    cta_label: str | None = Field(default=None, max_length=60)
    cta_url: CtaUrl | None = None
    image_id: int | None = None
    items: list[WhyItem] = Field(default=None, max_length=8)
    is_visible: bool = None
    is_placeholder: bool = None


class HomepageOrder(BaseModel):
    model_config = ConfigDict(extra="forbid")
    keys: list[SectionKey]


class HomepageSectionAdminOut(ORMModel):
    key: str
    heading: str | None
    subheading: str | None
    cta_label: str | None
    cta_url: str | None
    image_id: int | None
    image: ImageOut | None = None
    items: list[WhyItem] = Field(default_factory=list)
    is_visible: bool
    sort_order: int
    is_placeholder: bool
    updated_at: datetime


class HomepageSectionOut(BaseModel):
    """One shape for every section. The frontend switches on `key` and reads what it needs."""
    key: str
    heading: str | None
    subheading: str | None
    cta_label: str | None
    cta_url: str | None
    image: ImageOut | None = None
    items: list[WhyItem] = Field(default_factory=list)
    categories: list[CategoryNode] = Field(default_factory=list)
    products: list[ProductCard] = Field(default_factory=list)
    industries: list[IndustryOut] = Field(default_factory=list)


class HomepageOut(BaseModel):
    sections: list[HomepageSectionOut]