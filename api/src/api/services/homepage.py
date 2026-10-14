from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.models import Category, Industry, MediaAsset, Product, User
from api.models.homepage_section import SECTION_KEYS, HomepageSection
from api.routers.catalogue import product_counts
from api.schemas.catalogue import CategoryNode, IndustryOut, ProductCard
from api.schemas.homepage import (
    HomepageOut, HomepageSectionAdminOut, HomepageSectionOut, WhyItem,
)
from api.services.audit import compute_changes, record_audit
from api.services.media_urls import attach_primary_images, image_out

FEATURED_LIMIT = 8

# Placeholder content, per the placeholder policy: obviously generic, flagged is_placeholder.
DEFAULTS: dict[str, dict[str, Any]] = {
    "hero": {
        "heading": "Electrical products you can rely on",
        "subheading": "Placeholder text: describe what Ideal Electric supplies and to whom.",
        "cta_label": "Request a quote", "cta_url": "/contact", "items": [], "sort_order": 10,
    },
    "featured_categories": {
        "heading": "Product categories", "subheading": None,
        "cta_label": "View all categories", "cta_url": "/products", "items": [], "sort_order": 20,
    },
    "featured_products": {
        "heading": "Featured products", "subheading": None,
        "cta_label": "Browse the catalogue", "cta_url": "/products", "items": [], "sort_order": 30,
    },
    "industries": {
        "heading": "Industries we serve", "subheading": None,
        "cta_label": None, "cta_url": None, "items": [], "sort_order": 40,
    },
    "why_choose_us": {
        "heading": "Why choose us", "subheading": None, "cta_label": None, "cta_url": None,
        "items": [
            {"title": "Wide product range", "text": "Placeholder text.", "icon": None},
            {"title": "Reliable supply", "text": "Placeholder text.", "icon": None},
            {"title": "Technical support", "text": "Placeholder text.", "icon": None},
        ],
        "sort_order": 50,
    },
    "inquiry_cta": {
        "heading": "Need a quote?",
        "subheading": "Placeholder text: tell visitors how quickly you reply.",
        "cta_label": "Send an inquiry", "cta_url": "/contact", "items": [], "sort_order": 60,
    },
}


async def ensure_sections(db: AsyncSession) -> list[HomepageSection]:
    """Return all sections in display order, creating any that don't exist yet."""
    rows = (await db.execute(select(HomepageSection))).scalars().all()
    missing = [k for k in SECTION_KEYS if k not in {r.key for r in rows}]
    if missing:
        await db.execute(
            insert(HomepageSection)
            .values([{"key": k, **DEFAULTS[k]} for k in missing])
            .on_conflict_do_nothing(index_elements=["key"])
        )
        await db.commit()
        rows = (await db.execute(select(HomepageSection))).scalars().all()
    return sorted(rows, key=lambda r: (r.sort_order, r.id))


# ------------------------------------------------------------------ admin


async def admin_out(db: AsyncSession, section: HomepageSection) -> HomepageSectionAdminOut:
    out = HomepageSectionAdminOut.model_validate(section)
    if section.image_id is not None:
        asset = await db.get(MediaAsset, section.image_id)
        if asset is not None:
            out.image = image_out(asset, asset.alt_text or section.heading or "Ideal Electric")
    return out


async def list_admin_sections(db: AsyncSession) -> list[HomepageSectionAdminOut]:
    return [await admin_out(db, s) for s in await ensure_sections(db)]


async def update_section(
    db: AsyncSession, user: User, key: str, updates: dict[str, Any]
) -> HomepageSectionAdminOut:
    section = next(s for s in await ensure_sections(db) if s.key == key)

    if "image_id" in updates:
        if key != "hero":
            raise HTTPException(422, "Only the hero section has an image")
        if updates["image_id"] is not None:
            asset = await db.get(MediaAsset, updates["image_id"])
            if asset is None or asset.kind != "image":
                raise HTTPException(422, "image_id must be an existing image")
    if "items" in updates and key != "why_choose_us":
        raise HTTPException(422, "Only the why_choose_us section has items")

    changes = compute_changes(section, updates)
    if changes:
        for field, value in updates.items():
            setattr(section, field, value)
        record_audit(
            db, user, "update", "homepage_section", section.id,
            f"Updated homepage section '{key}'", changes,
        )
        await db.commit()
        await db.refresh(section)
    return await admin_out(db, section)


async def reorder_sections(
    db: AsyncSession, user: User, keys: list[str]
) -> list[HomepageSectionAdminOut]:
    sections = await ensure_sections(db)
    if sorted(keys) != sorted(SECTION_KEYS):
        raise HTTPException(422, "List every section exactly once")
    by_key = {s.key: s for s in sections}
    for position, key in enumerate(keys, start=1):
        by_key[key].sort_order = position * 10
    record_audit(
        db, user, "update", "homepage_section", by_key[keys[0]].id,
        "Reordered homepage sections", {"order": " > ".join(keys)},
    )
    await db.commit()
    return await list_admin_sections(db)


# ------------------------------------------------------------------ public


async def featured_categories(db: AsyncSession) -> list[CategoryNode]:
    rows = (
        await db.execute(
            select(Category)
            .where(Category.status == "published", Category.is_featured.is_(True))
            .order_by(Category.sort_order, Category.name)
            .limit(FEATURED_LIMIT)
        )
    ).scalars().all()
    if not rows:
        return []
    counts = await product_counts(db)
    child_rows = (
        await db.execute(
            select(Category.id, Category.parent_id).where(
                Category.parent_id.in_([c.id for c in rows]), Category.status == "published"
            )
        )
    ).all()
    totals = {c.id: counts.get(c.id, 0) for c in rows}
    for child_id, parent_id in child_rows:
        totals[parent_id] += counts.get(child_id, 0)  # a parent counts its subcategories too
    return [
        CategoryNode(
            id=c.id, name=c.name, slug=c.slug, description=c.description,
            product_count=totals[c.id],
        )
        for c in rows
    ]


async def featured_products(db: AsyncSession) -> list[ProductCard]:
    rows = (
        await db.execute(
            select(Product)
            .options(joinedload(Product.category), joinedload(Product.series))
            .where(Product.status == "published", Product.is_featured.is_(True))
            .order_by(Product.sort_order, Product.name)
            .limit(FEATURED_LIMIT)
        )
    ).scalars().all()
    cards = [ProductCard.model_validate(p) for p in rows]
    await attach_primary_images(db, [(p.id, card) for p, card in zip(rows, cards)])
    return cards


async def published_industries(db: AsyncSession) -> list[IndustryOut]:
    rows = (
        await db.execute(
            select(Industry).where(Industry.status == "published")
            .order_by(Industry.sort_order, Industry.name)
        )
    ).scalars().all()
    return [IndustryOut.model_validate(r) for r in rows]


async def build_public_homepage(db: AsyncSession) -> HomepageOut:
    out: list[HomepageSectionOut] = []
    for s in await ensure_sections(db):
        if not s.is_visible:
            continue
        item = HomepageSectionOut(
            key=s.key, heading=s.heading, subheading=s.subheading,
            cta_label=s.cta_label, cta_url=s.cta_url,
        )
        match s.key:
            case "hero" if s.image_id is not None:
                asset = await db.get(MediaAsset, s.image_id)
                if asset is not None:
                    item.image = image_out(asset, asset.alt_text or s.heading or "Ideal Electric")
            case "featured_categories":
                item.categories = await featured_categories(db)
                if not item.categories:
                    continue
            case "featured_products":
                item.products = await featured_products(db)
                if not item.products:
                    continue
            case "industries":
                item.industries = await published_industries(db)
                if not item.industries:
                    continue
            case "why_choose_us":
                item.items = [WhyItem(**i) for i in s.items]
                if not item.items:
                    continue
        out.append(item)
    return HomepageOut(sections=out)