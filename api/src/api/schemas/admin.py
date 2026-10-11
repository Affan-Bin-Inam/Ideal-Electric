from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from api.schemas.catalogue import ORMModel

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
Status = Literal["draft", "published", "archived"]

# Update models: columns that can't be NULL are typed without "| None". The None defaults are
# never validated or used, because endpoints read only the fields a client actually sent, so an
# explicit null for those fields is rejected while omitting them is fine. extra="forbid" turns
# attempts to change fields that can't change into an error, not a silent no-op.


# ------------------------------------------------------------------ categories


class CategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140, pattern=SLUG_PATTERN)
    parent_id: int | None = None
    description: str | None = None
    sort_order: int = 0
    status: Status = "draft"
    seo_title: str | None = Field(default=None, max_length=160)
    seo_description: str | None = Field(default=None, max_length=320)


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default=None, min_length=2, max_length=120)
    slug: str = Field(default=None, max_length=140, pattern=SLUG_PATTERN)
    parent_id: int | None = None
    description: str | None = None
    sort_order: int = None
    status: Status = None
    seo_title: str | None = Field(default=None, max_length=160)
    seo_description: str | None = Field(default=None, max_length=320)
    is_placeholder: bool = None


class CategoryAdminOut(ORMModel):
    id: int
    parent_id: int | None
    name: str
    slug: str
    description: str | None
    sort_order: int
    status: str
    seo_title: str | None
    seo_description: str | None
    is_placeholder: bool
    created_at: datetime
    updated_at: datetime
    product_count: int = 0


# ------------------------------------------------------------------ series


class SeriesCreate(BaseModel):
    brand_id: int
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140, pattern=SLUG_PATTERN)
    description: str | None = None
    sort_order: int = 0
    status: Status = "draft"


class SeriesUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")  # brand_id can't change, and the API says so
    name: str = Field(default=None, min_length=2, max_length=120)
    slug: str = Field(default=None, max_length=140, pattern=SLUG_PATTERN)
    description: str | None = None
    sort_order: int = None
    status: Status = None
    is_placeholder: bool = None


class SeriesAdminOut(ORMModel):
    id: int
    brand_id: int
    name: str
    slug: str
    description: str | None
    sort_order: int
    status: str
    is_placeholder: bool
    created_at: datetime
    updated_at: datetime
    product_count: int = 0


# ------------------------------------------------------------------ industries


class IndustryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    slug: str | None = Field(default=None, max_length=140, pattern=SLUG_PATTERN)
    summary: str | None = Field(default=None, max_length=300)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=60)
    sort_order: int = 0
    status: Status = "draft"
    seo_title: str | None = Field(default=None, max_length=160)
    seo_description: str | None = Field(default=None, max_length=320)


class IndustryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default=None, min_length=2, max_length=120)
    slug: str = Field(default=None, max_length=140, pattern=SLUG_PATTERN)
    summary: str | None = Field(default=None, max_length=300)
    description: str | None = None
    icon: str | None = Field(default=None, max_length=60)
    sort_order: int = None
    status: Status = None
    seo_title: str | None = Field(default=None, max_length=160)
    seo_description: str | None = Field(default=None, max_length=320)
    is_placeholder: bool = None


class IndustryAdminOut(ORMModel):
    id: int
    name: str
    slug: str
    summary: str | None
    description: str | None
    icon: str | None
    sort_order: int
    status: str
    seo_title: str | None
    seo_description: str | None
    is_placeholder: bool
    created_at: datetime
    updated_at: datetime
    product_count: int = 0


# ------------------------------------------------------------------ brands (edit only)


class BrandUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default=None, min_length=2, max_length=120)
    description: str | None = None
    seo_title: str | None = Field(default=None, max_length=160)
    seo_description: str | None = Field(default=None, max_length=320)
    is_placeholder: bool = None


class BrandAdminOut(ORMModel):
    id: int
    name: str
    slug: str
    description: str | None
    status: str
    seo_title: str | None
    seo_description: str | None
    is_placeholder: bool
    created_at: datetime
    updated_at: datetime
    product_count: int = 0