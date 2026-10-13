from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import (
    AttributeDefinition,
    Brand,
    Category,
    CategoryAttribute,
    Industry,
    Product,
    ProductAttributeValue,
    ProductHighlight,
    ProductIndustry,
    RelatedProduct,
    Series,
    User,
)
from api.schemas.admin import ProductAdminOut, ProductCreate, ProductUpdate
from api.services.admin_crud import ensure_name_free, flush_or_conflict
from api.services.attribute_values import display_value, row_columns, value_columns
from api.services.audit import compute_changes, record_audit
from api.services.slugs import slug_taken, unique_slug

NESTED_FIELDS = ("features", "applications", "attributes", "industry_ids", "related_ids")


def unprocessable(message: str) -> HTTPException:
    return HTTPException(422, message)


# ------------------------------------------------------------------ reading


async def load_state(db: AsyncSession, product: Product) -> dict[str, Any]:
    """The product's nested data, read with plain queries (no lazy loading in async code)."""
    highlights = (
        await db.execute(
            select(ProductHighlight)
            .where(ProductHighlight.product_id == product.id)
            .order_by(ProductHighlight.sort_order, ProductHighlight.id)
        )
    ).scalars().all()
    attribute_rows = (
        await db.execute(
            select(ProductAttributeValue, AttributeDefinition)
            .join(AttributeDefinition, AttributeDefinition.id == ProductAttributeValue.attribute_id)
            .where(ProductAttributeValue.product_id == product.id)
        )
    ).all()
    industry_ids = (
        await db.execute(
            select(ProductIndustry.industry_id)
            .where(ProductIndustry.product_id == product.id)
            .order_by(ProductIndustry.industry_id)
        )
    ).scalars().all()
    related_ids = (
        await db.execute(
            select(RelatedProduct.related_product_id)
            .where(RelatedProduct.product_id == product.id)
            .order_by(RelatedProduct.sort_order)
        )
    ).scalars().all()
    return {
        "features": [h.text for h in highlights if h.kind == "feature"],
        "applications": [h.text for h in highlights if h.kind == "application"],
        "attributes": {d.key: row_columns(v) for v, d in attribute_rows},
        "industry_ids": list(industry_ids),
        "related_ids": list(related_ids),
    }


def to_out(product: Product, state: dict[str, Any]) -> ProductAdminOut:
    out = ProductAdminOut.model_validate(product)
    out.features = state["features"]
    out.applications = state["applications"]
    out.attributes = {key: display_value(cols) for key, cols in state["attributes"].items()}
    out.industry_ids = state["industry_ids"]
    out.related_ids = state["related_ids"]
    return out


# ------------------------------------------------------------------ validation


async def resolve_references(
    db: AsyncSession, *, category_id: int, series_id: int | None, brand_id: int | None,
    status: str, summary: str | None,
) -> tuple[Category, int | None]:
    category = await db.get(Category, category_id)
    if category is None:
        raise unprocessable("Category not found")

    if series_id is not None:
        series = await db.get(Series, series_id)
        if series is None:
            raise unprocessable("Series not found")
        if brand_id is not None and brand_id != series.brand_id:
            raise unprocessable("That series belongs to a different brand")
        brand_id = series.brand_id  # the series decides the brand
    elif brand_id is not None and await db.get(Brand, brand_id) is None:
        raise unprocessable("Brand not found")

    if status == "published" and not (summary and summary.strip()):
        raise unprocessable("A product needs a summary before it can be published")
    return category, brand_id


async def resolve_attributes(
    db: AsyncSession, category: Category, requested: dict[str, Any]
) -> dict[str, tuple[AttributeDefinition, dict[str, Any]]]:
    """Check each attribute belongs to the category (or its parent) and the value fits it."""
    category_ids = [category.id] + ([category.parent_id] if category.parent_id else [])
    rows = (
        await db.execute(
            select(AttributeDefinition)
            .join(CategoryAttribute, CategoryAttribute.attribute_id == AttributeDefinition.id)
            .where(CategoryAttribute.category_id.in_(category_ids))
        )
    ).scalars().all()
    applicable = {d.key: d for d in rows}

    resolved = {}
    for key, value in requested.items():
        definition = applicable.get(key)
        if definition is None:
            raise unprocessable(f"'{key}' is not an attribute of this category")
        try:
            resolved[key] = (definition, value_columns(definition, value))
        except ValueError as error:
            raise unprocessable(str(error))
    return resolved


async def resolve_ids(db: AsyncSession, model, ids: list[int], label: str) -> list[int]:
    unique = list(dict.fromkeys(ids))
    if unique:
        found = set((await db.execute(select(model.id).where(model.id.in_(unique)))).scalars())
        missing = [i for i in unique if i not in found]
        if missing:
            raise unprocessable(f"Unknown {label}: {missing}")
    return unique


# ------------------------------------------------------------------ writing nested data


async def replace_highlights(db: AsyncSession, product_id: int, kind: str, texts: list[str]) -> None:
    await db.execute(
        delete(ProductHighlight).where(
            ProductHighlight.product_id == product_id, ProductHighlight.kind == kind
        )
    )
    for position, text in enumerate(texts):
        db.add(ProductHighlight(product_id=product_id, kind=kind, text=text, sort_order=position))


async def replace_attributes(
    db: AsyncSession, product_id: int, resolved: dict[str, tuple[AttributeDefinition, dict[str, Any]]]
) -> None:
    await db.execute(
        delete(ProductAttributeValue).where(ProductAttributeValue.product_id == product_id)
    )
    for definition, columns in resolved.values():
        db.add(ProductAttributeValue(product_id=product_id, attribute_id=definition.id, **columns))


async def replace_industries(db: AsyncSession, product_id: int, industry_ids: list[int]) -> None:
    await db.execute(delete(ProductIndustry).where(ProductIndustry.product_id == product_id))
    for industry_id in industry_ids:
        db.add(ProductIndustry(product_id=product_id, industry_id=industry_id))


async def replace_related(db: AsyncSession, product_id: int, related_ids: list[int]) -> None:
    await db.execute(delete(RelatedProduct).where(RelatedProduct.product_id == product_id))
    for position, related_id in enumerate(related_ids):
        db.add(RelatedProduct(product_id=product_id, related_product_id=related_id, sort_order=position))


# ------------------------------------------------------------------ create and update


async def create_product(db: AsyncSession, user: User, body: ProductCreate) -> ProductAdminOut:
    data = body.model_dump()
    nested = {name: data.pop(name) for name in NESTED_FIELDS}
    requested_slug = data.pop("slug")

    category, brand_id = await resolve_references(
        db, category_id=data["category_id"], series_id=data["series_id"],
        brand_id=data["brand_id"], status=data["status"], summary=data["summary"],
    )
    attributes = await resolve_attributes(db, category, nested["attributes"])
    industry_ids = await resolve_ids(db, Industry, nested["industry_ids"], "industries")
    related_ids = await resolve_ids(db, Product, nested["related_ids"], "products")
    await ensure_name_free(db, Product, data["name"], label="product")

    if requested_slug:
        if await slug_taken(db, Product, requested_slug):
            raise HTTPException(409, "That slug is already in use")
        slug = requested_slug
    else:
        slug = await unique_slug(db, Product, data["name"])

    data["brand_id"] = brand_id
    product = Product(**data, slug=slug)
    db.add(product)
    await flush_or_conflict(db, "product")

    await replace_highlights(db, product.id, "feature", nested["features"])
    await replace_highlights(db, product.id, "application", nested["applications"])
    await replace_attributes(db, product.id, attributes)
    await replace_industries(db, product.id, industry_ids)
    await replace_related(db, product.id, related_ids)

    record_audit(db, user, "create", "product", product.id, f"Created product '{product.name}'")
    await db.commit()
    await db.refresh(product)
    return to_out(product, await load_state(db, product))


async def update_product(
    db: AsyncSession, user: User, product: Product, body: ProductUpdate
) -> ProductAdminOut:
    updates = body.model_dump(exclude_unset=True)
    nested = {name: updates.pop(name) for name in NESTED_FIELDS if name in updates}
    state = await load_state(db, product)

    category_id = updates.get("category_id", product.category_id)
    series_id = updates.get("series_id", product.series_id)
    category, brand_id = await resolve_references(
        db, category_id=category_id, series_id=series_id,
        brand_id=updates.get("brand_id", product.brand_id),
        status=updates.get("status", product.status),
        summary=updates.get("summary", product.summary),
    )
    if "series_id" in updates or "brand_id" in updates:
        updates["series_id"] = series_id
        updates["brand_id"] = brand_id

    # Attributes are re-checked when they are sent, or when the category changes, because
    # the new category may not use the attributes the product already has.
    new_attributes = None
    if "attributes" in nested or category_id != product.category_id:
        requested = (
            nested["attributes"]
            if "attributes" in nested
            else {key: display_value(cols) for key, cols in state["attributes"].items()}
        )
        new_attributes = await resolve_attributes(db, category, requested)

    new_industries = None
    if "industry_ids" in nested:
        new_industries = await resolve_ids(db, Industry, nested["industry_ids"], "industries")
    new_related = None
    if "related_ids" in nested:
        if product.id in nested["related_ids"]:
            raise unprocessable("A product cannot be related to itself")
        new_related = await resolve_ids(db, Product, nested["related_ids"], "products")

    if "name" in updates:
        await ensure_name_free(db, Product, updates["name"], label="product", exclude_id=product.id)
    if "slug" in updates and updates["slug"] != product.slug:
        if await slug_taken(db, Product, updates["slug"], exclude_id=product.id):
            raise HTTPException(409, "That slug is already in use")

    # Work out exactly what changed, so the audit entry and the writes stay minimal.
    changes = compute_changes(product, updates)
    updates = {field: value for field, value in updates.items() if field in changes}

    if "features" in nested and nested["features"] != state["features"]:
        changes["features"] = {"from": state["features"], "to": nested["features"]}
    if "applications" in nested and nested["applications"] != state["applications"]:
        changes["applications"] = {"from": state["applications"], "to": nested["applications"]}
    if new_industries is not None and sorted(new_industries) != sorted(state["industry_ids"]):
        changes["industry_ids"] = {"from": state["industry_ids"], "to": new_industries}
    if new_related is not None and new_related != state["related_ids"]:
        changes["related_ids"] = {"from": state["related_ids"], "to": new_related}

    attributes_changed = False
    if new_attributes is not None:
        old = state["attributes"]
        for key in sorted(set(old) | set(new_attributes)):
            old_value = display_value(old[key]) if key in old else None
            new_value = display_value(new_attributes[key][1]) if key in new_attributes else None
            if old_value != new_value:
                changes[f"attribute:{key}"] = {"from": old_value, "to": new_value}
                attributes_changed = True

    if not changes:
        return to_out(product, state)

    for field, value in updates.items():
        setattr(product, field, value)
    if not updates:
        product.updated_at = func.now()  # only nested data changed; still bump the timestamp
    if "features" in changes:
        await replace_highlights(db, product.id, "feature", nested["features"])
    if "applications" in changes:
        await replace_highlights(db, product.id, "application", nested["applications"])
    if attributes_changed:
        await replace_attributes(db, product.id, new_attributes)
    if "industry_ids" in changes:
        await replace_industries(db, product.id, new_industries)
    if "related_ids" in changes:
        await replace_related(db, product.id, new_related)

    await flush_or_conflict(db, "product")
    record_audit(
        db, user, "update", "product", product.id, f"Updated product '{product.name}'", changes
    )
    await db.commit()
    await db.refresh(product)
    return to_out(product, await load_state(db, product))