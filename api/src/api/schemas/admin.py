from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, EmailStr

from api.schemas.catalogue import ORMModel

SLUG_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
Status = Literal["draft", "published", "archived"]

# Update models: columns that can't be NULL are typed without "| None". The None defaults are
# never validated or used, because endpoints read only the fields a client actually sent, so an
# explicit null for those fields is rejected while omitting them is fine. extra="forbid" turns
# attempts to change fields that can't change into an error, not a silent no-op.
Url300 = Annotated[str, StringConstraints(max_length=300, pattern=r"^https?://\S+$")]
Phone = Annotated[str, StringConstraints(pattern=r"^\+?[0-9][0-9\s\-()]{5,28}$")]

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

    # ------------------------------------------------------------------ products

Text300 = Annotated[str, StringConstraints(min_length=1, max_length=300)]
AttrValue = str | bool | float | list[str]


class ProductCreate(BaseModel):
    name: str = Field(min_length=2, max_length=200)
    slug: str | None = Field(default=None, max_length=220, pattern=SLUG_PATTERN)
    category_id: int
    series_id: int | None = None
    brand_id: int | None = None
    model_code: str | None = Field(default=None, max_length=80)
    summary: str | None = Field(default=None, max_length=300)
    description: str | None = None
    status: Status = "draft"
    is_featured: bool = False
    sort_order: int = 0
    seo_title: str | None = Field(default=None, max_length=160)
    seo_description: str | None = Field(default=None, max_length=320)
    features: list[Text300] = Field(default_factory=list)
    applications: list[Text300] = Field(default_factory=list)
    attributes: dict[str, AttrValue] = Field(default_factory=dict)
    industry_ids: list[int] = Field(default_factory=list)
    related_ids: list[int] = Field(default_factory=list)


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str = Field(default=None, min_length=2, max_length=200)
    slug: str = Field(default=None, max_length=220, pattern=SLUG_PATTERN)
    category_id: int = None
    series_id: int | None = None
    brand_id: int | None = None
    model_code: str | None = Field(default=None, max_length=80)
    summary: str | None = Field(default=None, max_length=300)
    description: str | None = None
    status: Status = None
    is_featured: bool = None
    sort_order: int = None
    seo_title: str | None = Field(default=None, max_length=160)
    seo_description: str | None = Field(default=None, max_length=320)
    is_placeholder: bool = None
    features: list[Text300] = None
    applications: list[Text300] = None
    attributes: dict[str, AttrValue] = None
    industry_ids: list[int] = None
    related_ids: list[int] = None


class ProductAdminOut(ORMModel):
    id: int
    name: str
    slug: str
    category_id: int
    series_id: int | None
    brand_id: int | None
    model_code: str | None
    summary: str | None
    description: str | None
    status: str
    is_featured: bool
    sort_order: int
    seo_title: str | None
    seo_description: str | None
    is_placeholder: bool
    created_at: datetime
    updated_at: datetime
    features: list[str] = Field(default_factory=list)
    applications: list[str] = Field(default_factory=list)
    attributes: dict[str, str | bool | list[str]] = Field(default_factory=dict)
    industry_ids: list[int] = Field(default_factory=list)
    related_ids: list[int] = Field(default_factory=list)


class ProductAdminRow(BaseModel):
    id: int
    name: str
    slug: str
    status: str
    is_featured: bool
    is_placeholder: bool
    category_name: str
    series_name: str | None
    updated_at: datetime


class ProductAdminPage(BaseModel):
    items: list[ProductAdminRow]
    total: int
    page: int
    page_size: int
    pages: int

#-----------------------------------------------------siteSetting

class SiteSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    company_name: str = Field(default=None, min_length=2, max_length=160)
    tagline: str | None = Field(default=None, max_length=200)
    about_short: str | None = None
    phone_primary: Phone | None = None
    phone_secondary: Phone | None = None
    email_sales: EmailStr | None = None
    whatsapp_number: str | None = Field(default=None, pattern=r"^[0-9]{8,15}$")
    address_line: str | None = Field(default=None, max_length=300)
    city: str | None = Field(default=None, max_length=100)
    google_maps_url: Url300 | None = None
    business_hours: str | None = Field(default=None, max_length=300)
    facebook_url: Url300 | None = None
    linkedin_url: Url300 | None = None
    instagram_url: Url300 | None = None
    default_meta_title: str | None = Field(default=None, max_length=160)
    default_meta_description: str | None = Field(default=None, max_length=320)
    is_placeholder: bool = None


class SiteSettingsPublic(ORMModel):
    company_name: str
    tagline: str | None
    about_short: str | None
    phone_primary: str | None
    phone_secondary: str | None
    email_sales: str | None
    whatsapp_number: str | None
    address_line: str | None
    city: str | None
    google_maps_url: str | None
    business_hours: str | None
    facebook_url: str | None
    linkedin_url: str | None
    instagram_url: str | None
    default_meta_title: str | None
    default_meta_description: str | None


class SiteSettingsAdminOut(SiteSettingsPublic):
    is_placeholder: bool
    updated_at: datetime