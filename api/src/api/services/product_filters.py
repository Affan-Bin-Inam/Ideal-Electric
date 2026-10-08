from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Annotated

from fastapi import Depends, HTTPException, Query
from sqlalchemy import func, literal_column, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from api.models import (
    AttributeDefinition,
    Category,
    Industry,
    Product,
    ProductAttributeValue,
    ProductIndustry,
    Series,
)


class ProductFilters:
    """Query-string filters shared by the product list and the facets endpoint."""

    def __init__(
        self,
        q: str | None = Query(None, min_length=2, max_length=100),
        category: str | None = None,
        series: str | None = None,
        industry: str | None = None,
        featured: bool | None = None,
        attr: list[str] = Query(default=[]),
    ):
        self.q = q
        self.category = category
        self.series = series
        self.industry = industry
        self.featured = featured
        self.attr = attr


Filters = Annotated[ProductFilters, Depends()]


class ResolvedFilters:
    """Filters turned into SQL conditions, kept in groups so facets can leave one group out."""

    def __init__(self) -> None:
        self.base: list = [Product.status == "published"]
        self.series_condition = None
        self.attr_conditions: dict[str, list] = {}
        self.rank = None
        self.category: Category | None = None
        self.attribute_scope_ids: list[int] = []

    def conditions(self, *, skip_series: bool = False, skip_attr: str | None = None) -> list:
        result = list(self.base)
        if self.series_condition is not None and not skip_series:
            result.append(self.series_condition)
        for key, conds in self.attr_conditions.items():
            if key != skip_attr:
                result.extend(conds)
        return result


def attribute_condition(definition: AttributeDefinition, value: str):
    """An EXISTS clause: 'this product has a matching value for this attribute'."""
    pav = aliased(ProductAttributeValue)  # a fresh alias per filter, so clauses never clash
    cond = pav.attribute_id == definition.id
    match definition.data_type:
        case "multi_choice":
            cond = cond & pav.value_choices.contains([value])
        case "single_choice" | "text":
            cond = cond & (pav.value_text == value)
        case "boolean":
            cond = cond & (pav.value_bool == (value.lower() in ("true", "1", "yes")))
        case "number":
            try:
                cond = cond & (pav.value_number == Decimal(value))
            except InvalidOperation:
                raise HTTPException(400, f"'{value}' is not a valid number for '{definition.key}'")
    return select(pav.product_id).where(pav.product_id == Product.id, cond).exists()


async def resolve_filters(db: AsyncSession, f: ProductFilters) -> ResolvedFilters:
    r = ResolvedFilters()

    if f.category:
        category = (
            await db.execute(
                select(Category).where(Category.slug == f.category, Category.status == "published")
            )
        ).scalar_one_or_none()
        if category is None:
            raise HTTPException(404, "Category not found")
        child_ids = (
            await db.execute(select(Category.id).where(Category.parent_id == category.id))
        ).scalars().all()
        r.category = category
        r.base.append(Product.category_id.in_([category.id, *child_ids]))
        # Attributes may be assigned to the category, its children, or its parent.
        r.attribute_scope_ids = [category.id, *child_ids]
        if category.parent_id is not None:
            r.attribute_scope_ids.append(category.parent_id)

    if f.series:
        r.series_condition = Product.series_id.in_(select(Series.id).where(Series.slug == f.series))

    if f.industry:
        r.base.append(
            Product.id.in_(
                select(ProductIndustry.product_id)
                .join(Industry, Industry.id == ProductIndustry.industry_id)
                .where(Industry.slug == f.industry)
            )
        )

    if f.featured is not None:
        r.base.append(Product.is_featured == f.featured)

    if f.attr:
        parsed = []
        for raw in f.attr:
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
            r.attr_conditions.setdefault(key, []).append(attribute_condition(definition, value))

    if f.q:
        ts_query = func.websearch_to_tsquery(literal_column("'english'"), f.q)
        r.base.append(
            or_(
                Product.search_vector.bool_op("@@")(ts_query),
                func.word_similarity(f.q, Product.name) > 0.3,
            )
        )
        r.rank = func.ts_rank(Product.search_vector, ts_query) + func.word_similarity(f.q, Product.name)

    return r