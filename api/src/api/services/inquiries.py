from __future__ import annotations

import hashlib
import hmac
from datetime import timedelta
from typing import Any

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models import AttributeDefinition, Inquiry, Product, ProductAttributeValue

MAX_PER_HOUR = 5


def hash_ip(ip: str | None) -> str:
    """A keyed hash: enough to rate-limit one connection, without storing the address itself."""
    return hmac.new(
        settings.secret_key.encode(), (ip or "unknown").encode(), hashlib.sha256
    ).hexdigest()


def whatsapp_number(phone: str) -> str:
    """wa.me wants the international number without '+'. Numbers starting with 0 are treated
    as Pakistani national format."""
    digits = phone.lstrip("+")
    if phone.startswith("+"):
        return digits
    if digits.startswith("00"):
        return digits[2:]
    if digits.startswith("0"):
        return "92" + digits[1:]
    return digits


async def too_many_recent(db: AsyncSession, ip_hash: str) -> bool:
    recent = (
        await db.execute(
            select(func.count())
            .select_from(Inquiry)
            .where(Inquiry.ip_hash == ip_hash, Inquiry.created_at > func.now() - timedelta(hours=1))
        )
    ).scalar_one()
    return recent >= MAX_PER_HOUR


async def resolve_product_options(
    db: AsyncSession, product_slug: str | None, selected: dict[str, list[str]]
) -> tuple[Product | None, dict[str, Any]]:
    """Find the published product and check the chosen options against that product's own values."""
    if not product_slug:
        if selected:
            raise HTTPException(422, "Options can only be chosen for a product")
        return None, {}

    product = (
        await db.execute(
            select(Product).where(Product.slug == product_slug, Product.status == "published")
        )
    ).scalar_one_or_none()
    if product is None:
        return None, {}  # a stale page: keep the inquiry, just without the product link
    if not selected:
        return product, {}

    rows = (
        await db.execute(
            select(ProductAttributeValue, AttributeDefinition)
            .join(AttributeDefinition, AttributeDefinition.id == ProductAttributeValue.attribute_id)
            .where(
                ProductAttributeValue.product_id == product.id,
                AttributeDefinition.is_inquiry_option.is_(True),
            )
        )
    ).all()
    allowed: dict[str, list[str]] = {}
    for row, definition in rows:
        if definition.data_type == "multi_choice":
            allowed[definition.key] = list(row.value_choices or [])
        elif definition.data_type == "single_choice" and row.value_text:
            allowed[definition.key] = [row.value_text]

    for key, values in selected.items():
        if key not in allowed:
            raise HTTPException(422, f"'{key}' is not an option for this product")
        if not values or any(v not in allowed[key] for v in values):
            raise HTTPException(422, f"Invalid choice for '{key}'")
    return product, selected