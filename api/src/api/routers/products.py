from __future__ import annotations

import math
from decimal import Decimal, InvalidOperation
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.orm import joinedload, selectinload

from api.deps import DbSession
from api.models import (
    AttributeDefinition,
    Category,
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
    IndustryOut,
    ProductCard,
    ProductDetail,
    ProductPage,
    SeriesBrief,
    SpecOut,
)

router = APIRouter(tags=["products"])

SortKey = Literal["relevance", "featured", "name", "newest"]


def attribute_condition(definition: AttributeDefinition, value: str):
    """Build the WHERE fragment that matches one attribute filter."""
    cond = ProductAttributeValue.attribute_id == definition.id
    match definition.data_type:
        case "multi_choice":
            cond = cond & ProductAttributeValue.value_choices.contains([value])
        case "single_choice" | "text":
            cond = cond & (ProductAttributeValue.value_text == value)
        case "boolean":
            cond = cond & (ProductAttributeValue.value_bool == (value.lower() in ("true", "1", "yes")))
        case "number":
            try:
                cond = cond & (ProductAttributeValue.value_number == Decimal(value))
            except InvalidOperation:
                raise HTTPException(400, f"'{value}' is not a valid number for '{definition.key}'")
    return cond


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
    q: str | None = Query(None, min_length=2, max_length=100),
    category: str | None = None,
    series: str | None = None,
    industry: str | None = None,
    featured: bool | None = None,
    attr: list[str] = Query(default=[]),
    sort: SortKey | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=48),
):
    conditions = [Product.status == "published"]

    if category:
        cat = (
            await db.execute(
                select(Category).where(Category.slug == category, Category.status == "published")
            )
        ).scalar_one_or_none()
        if cat is None:
            raise HTTPException(404, "Category not found")
        child_ids = (
            await db.execute(select(Category.id).where(Category.parent_id == cat.id))
        ).scalars().all()
        conditions.append(Product.category_id.in_([cat.id, *child_ids]))

    if series:
        conditions.append(Product.series_id.in_(select(Series.id).where(Series.slug == series)))

    if industry:
        conditions.append(
            Product.id.in_(
                select(ProductIndustry.product_id)
                .join(Industry, Industry.id == ProductIndustry.industry_id)
                .where(Industry.slug == industry)
            )
        )

    if featured is not None:
        conditions.append(Product.is_featured == featured)

    if attr:
        parsed = []
        for raw in attr:
            key, sep, value = raw.partition(":")
            if not sep or not value:
                raise HTTPException(400, f"Invalid attr '{raw}', expected key:value")
            parsed.append((key, value))
        definitions = {
            d.key: d
            for d in (
                await db.execute(
                    select(AttributeDefinition).where(
                        AttributeDefinition.key.in_({k for k, _ in parsed}),
                        AttributeDefinition.is_filterable.is_(True),
                    )
                )
            ).scalars()
        }
        for key, value in parsed:
            definition = definitions.get(key)
            if definition is None:
                raise HTTPException(400, f"Unknown or non-filterable attribute '{key}'")
            conditions.append(
                select(ProductAttributeValue.product_id)
                .where(
                    ProductAttributeValue.product_id == Product.id,
                    attribute_condition(definition, value),
                )
                .exists()
            )

    rank = None
    if q:
        ts_query = func.websearch_to_tsquery(literal_column("'english'"), q)
        text_match = Product.search_vector.bool_op("@@")(ts_query)
        typo_match = func.word_similarity(q, Product.name) > 0.3
        conditions.append(or_(text_match, typo_match))
        rank = func.ts_rank(Product.search_vector, ts_query) + func.word_similarity(q, Product.name)

    effective_sort = sort or ("relevance" if q else "featured")
    if effective_sort == "relevance" and rank is not None:
        order = [rank.desc(), Product.name]
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