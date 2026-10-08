from __future__ import annotations

import math
from collections import Counter
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import joinedload, selectinload

from api.deps import DbSession
from api.models import (
    AttributeDefinition,
    Category,
    CategoryAttribute,
    Industry,
    Product,
    ProductAttributeValue,
    ProductIndustry,
    RelatedProduct,
    Series,
)
from api.schemas.catalogue import (
    BrandBrief,
    CategoryBrief,
    Facet,
    FacetOption,
    FacetSet,
    IndustryOut,
    ProductCard,
    ProductDetail,
    ProductPage,
    SeriesBrief,
    SeriesFacet,
    SpecOut,
    SuggestionOut,
)
from api.services.product_filters import Filters, resolve_filters

router = APIRouter(tags=["products"])

SortKey = Literal["relevance", "featured", "name", "newest"]


def spec_value(definition: AttributeDefinition, row: ProductAttributeValue):
    match definition.data_type:
        case "multi_choice":
            return row.value_choices or []
        case "boolean":
            return row.value_bool
        case "number":
            return format(row.value_number.normalize(), "f")
        case _:
            return row.value_text


@router.get("/products", response_model=ProductPage)
async def list_products(
    db: DbSession,
    filters: Filters,
    sort: SortKey | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=48),
):
    resolved = await resolve_filters(db, filters)
    conditions = resolved.conditions()

    effective_sort = sort or ("relevance" if filters.q else "featured")
    if effective_sort == "relevance" and resolved.rank is not None:
        order = [resolved.rank.desc(), Product.name]
    elif effective_sort == "name":
        order = [Product.name]
    elif effective_sort == "newest":
        order = [Product.created_at.desc(), Product.id.desc()]
    else:
        order = [Product.is_featured.desc(), Product.sort_order, Product.name]

    total = (
        await db.execute(select(func.count()).select_from(Product).where(*conditions))
    ).scalar_one()

    rows = (
        await db.execute(
            select(Product)
            .options(joinedload(Product.category), joinedload(Product.series))
            .where(*conditions)
            .order_by(*order)
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()

    return ProductPage(
        items=[ProductCard.model_validate(p) for p in rows],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


# NOTE: these two routes must stay ABOVE /products/{slug}, or "facets" and "suggest"
# would be captured as product slugs.
@router.get("/products/facets", response_model=FacetSet)
async def product_facets(db: DbSession, filters: Filters):
    resolved = await resolve_filters(db, filters)

    total = (
        await db.execute(select(func.count()).select_from(Product).where(*resolved.conditions()))
    ).scalar_one()

    series_rows = (
        await db.execute(
            select(Series.name, Series.slug, func.count(Product.id))
            .join(Product, Product.series_id == Series.id)
            .where(*resolved.conditions(skip_series=True))
            .group_by(Series.id)
            .order_by(Series.sort_order)
        )
    ).all()

    attributes: list[Facet] = []
    if resolved.category is not None:
        definition_rows = (
            await db.execute(
                select(AttributeDefinition)
                .join(CategoryAttribute, CategoryAttribute.attribute_id == AttributeDefinition.id)
                .where(
                    CategoryAttribute.category_id.in_(resolved.attribute_scope_ids),
                    AttributeDefinition.is_filterable.is_(True),
                )
                .order_by(AttributeDefinition.sort_order)
            )
        ).scalars().all()

        for definition in {d.id: d for d in definition_rows}.values():
            # Count with every filter EXCEPT this attribute's own, so a visitor can
            # still see and tick the other options of the attribute they're filtering on.
            conds = resolved.conditions(skip_attr=definition.key)
            value_rows = (
                await db.execute(
                    select(ProductAttributeValue).where(
                        ProductAttributeValue.attribute_id == definition.id,
                        ProductAttributeValue.product_id.in_(select(Product.id).where(*conds)),
                    )
                )
            ).scalars().all()

            counts: Counter[str] = Counter()
            for row in value_rows:
                match definition.data_type:
                    case "multi_choice":
                        counts.update(row.value_choices or [])
                    case "boolean":
                        counts[str(row.value_bool).lower()] += 1
                    case "number":
                        counts[format(row.value_number.normalize(), "f")] += 1
                    case _:
                        counts[row.value_text] += 1

            if not counts:
                continue
            known = [c for c in (definition.choices or []) if counts[c]]
            extra = sorted(v for v in counts if v not in (definition.choices or []))
            attributes.append(
                Facet(
                    key=definition.key,
                    label=definition.label,
                    unit=definition.unit,
                    data_type=definition.data_type,
                    options=[FacetOption(value=v, count=counts[v]) for v in known + extra],
                )
            )

    return FacetSet(
        total=total,
        series=[SeriesFacet(name=n, slug=s, count=c) for n, s, c in series_rows],
        attributes=attributes,
    )


@router.get("/products/suggest", response_model=list[SuggestionOut])
async def suggest_products(db: DbSession, q: str = Query(..., min_length=2, max_length=60)):
    similarity = func.word_similarity(q, Product.name)
    rows = (
        await db.execute(
            select(Product)
            .options(joinedload(Product.category))
            .where(
                Product.status == "published",
                or_(Product.name.icontains(q, autoescape=True), similarity > 0.4),
            )
            .order_by(similarity.desc(), Product.name)
            .limit(6)
        )
    ).scalars().all()
    return [SuggestionOut(name=p.name, slug=p.slug, category=p.category.name) for p in rows]


@router.get("/products/{slug}", response_model=ProductDetail)
async def get_product(slug: str, db: DbSession):
    product = (
        await db.execute(
            select(Product)
            .options(
                joinedload(Product.category),
                joinedload(Product.brand),
                joinedload(Product.series),
                selectinload(Product.highlights),
            )
            .where(Product.slug == slug, Product.status == "published")
        )
    ).scalar_one_or_none()
    if product is None:
        raise HTTPException(404, "Product not found")

    parent = None
    if product.category.parent_id is not None:
        parent = await db.get(Category, product.category.parent_id)

    spec_rows = (
        await db.execute(
            select(ProductAttributeValue, AttributeDefinition)
            .join(AttributeDefinition, AttributeDefinition.id == ProductAttributeValue.attribute_id)
            .where(ProductAttributeValue.product_id == product.id)
            .order_by(AttributeDefinition.sort_order)
        )
    ).all()

    industries = (
        await db.execute(
            select(Industry)
            .join(ProductIndustry, ProductIndustry.industry_id == Industry.id)
            .where(ProductIndustry.product_id == product.id, Industry.status == "published")
            .order_by(Industry.sort_order)
        )
    ).scalars().all()

    related = (
        await db.execute(
            select(Product)
            .join(RelatedProduct, RelatedProduct.related_product_id == Product.id)
            .options(joinedload(Product.category), joinedload(Product.series))
            .where(RelatedProduct.product_id == product.id, Product.status == "published")
            .order_by(RelatedProduct.sort_order)
        )
    ).scalars().all()

    return ProductDetail(
        id=product.id,
        name=product.name,
        slug=product.slug,
        model_code=product.model_code,
        summary=product.summary,
        description=product.description,
        is_featured=product.is_featured,
        seo_title=product.seo_title,
        seo_description=product.seo_description,
        category=CategoryBrief.model_validate(product.category),
        parent_category=CategoryBrief.model_validate(parent) if parent else None,
        brand=BrandBrief.model_validate(product.brand) if product.brand else None,
        series=SeriesBrief.model_validate(product.series) if product.series else None,
        features=[h.text for h in product.highlights if h.kind == "feature"],
        applications=[h.text for h in product.highlights if h.kind == "application"],
        specifications=[
            SpecOut(
                key=d.key,
                label=d.label,
                group_name=d.group_name,
                unit=d.unit,
                data_type=d.data_type,
                is_inquiry_option=d.is_inquiry_option,
                value=spec_value(d, row),
            )
            for row, d in spec_rows
        ],
        industries=[IndustryOut.model_validate(i) for i in industries],
        related=[ProductCard.model_validate(r) for r in related],
    )