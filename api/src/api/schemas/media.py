from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

DocType = Literal["datasheet", "rate_list", "certificate", "manual", "brochure", "other"]
Access = Literal["public", "on_request"]


class MediaOut(BaseModel):
    id: int
    kind: str
    original_filename: str
    mime_type: str
    size_bytes: int
    width: int | None
    height: int | None
    alt_text: str | None
    is_placeholder: bool
    url: str
    thumb_url: str | None
    created_at: datetime


class MediaPage(BaseModel):
    items: list[MediaOut]
    total: int
    page: int
    page_size: int
    pages: int


class MediaUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alt_text: str | None = Field(default=None, max_length=300)
    is_placeholder: bool = None


class GalleryItem(BaseModel):
    asset_id: int
    is_primary: bool = False
    alt_override: str | None = Field(default=None, max_length=300)


class GalleryReplace(BaseModel):
    images: list[GalleryItem] = Field(max_length=20)


class GalleryItemOut(BaseModel):
    asset_id: int
    sort_order: int
    is_primary: bool
    alt_override: str | None
    alt_text: str | None
    thumb_url: str
    large_url: str


class DocumentItem(BaseModel):
    asset_id: int
    title: str = Field(min_length=1, max_length=200)
    doc_type: DocType = "rate_list"
    access: Access = "public"


class DocumentsReplace(BaseModel):
    documents: list[DocumentItem] = Field(max_length=20)


class DocumentItemOut(BaseModel):
    asset_id: int
    sort_order: int
    title: str
    doc_type: str
    access: str
    url: str
    original_filename: str