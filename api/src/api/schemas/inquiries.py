from __future__ import annotations

import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from api.schemas.catalogue import ORMModel

InquiryStatus = Literal["new", "contacted", "quoted", "closed", "spam"]
PHONE_PATTERN = re.compile(r"^\+?\d{10,15}$")
EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class InquiryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    phone: str = Field(min_length=7, max_length=30)
    email: str | None = Field(default=None, max_length=254)
    company: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    message: str | None = Field(default=None, max_length=2000)
    product_slug: str | None = Field(default=None, max_length=220)
    selected_options: dict[str, list[str]] = Field(default_factory=dict)
    source_page: str | None = Field(default=None, max_length=300)
    turnstile_token: str | None = Field(default=None, max_length=2048)
    website: str = Field(default="", max_length=200)  # honeypot: hidden in the real form

    @field_validator("name", "company", "city", "message", mode="before")
    @classmethod
    def strip_text(cls, value):
        return value.strip() if isinstance(value, str) else value

    @field_validator("phone")
    @classmethod
    def normalise_phone(cls, value: str) -> str:
        cleaned = re.sub(r"[\s\-().]", "", value)
        if not PHONE_PATTERN.match(cleaned):
            raise ValueError("Enter a valid phone or WhatsApp number")
        return cleaned

    @field_validator("email")
    @classmethod
    def check_email(cls, value: str | None) -> str | None:
        if value is None or value == "":
            return None
        value = value.strip().lower()
        if not EMAIL_PATTERN.match(value):
            raise ValueError("Enter a valid email address")
        return value


class NoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=2000)


class NoteOut(ORMModel):
    id: int
    author_email: str
    body: str
    created_at: datetime


class InquiryUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: InquiryStatus = None
    assigned_to_id: int | None = None


class InquiryRow(BaseModel):
    id: int
    name: str
    phone: str
    company: str | None
    product_name: str | None
    status: str
    assigned_to_email: str | None
    created_at: datetime


class InquiryPage(BaseModel):
    items: list[InquiryRow]
    total: int
    page: int
    page_size: int
    pages: int


class InquiryDetail(BaseModel):
    id: int
    name: str
    company: str | None
    email: str | None
    phone: str
    whatsapp_url: str
    city: str | None
    message: str | None
    product_id: int | None
    product_name: str | None
    selected_options: dict | None
    source_page: str | None
    status: str
    assigned_to_id: int | None
    assigned_to_email: str | None
    created_at: datetime
    updated_at: datetime
    notes: list[NoteOut]