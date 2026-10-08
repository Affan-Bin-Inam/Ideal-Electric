from __future__ import annotations

from fastapi import APIRouter, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import DbSession
from api.models import AttributeDefinition, Category, CategoryAttribute, Industry, Product
from api.schemas.catalogue import (
    AttributeOut,
    CategoryBrief,
    CategoryDetail,
    CategoryNode,
    IndustryOut,
)

router = APIRouter(tags=["catalogue"])


async def product_counts(db: AsyncSession) -> dict[int, int]:
    """Published products per category id, in a single GROUP BY query."""
    result = await db.execute(
        select(Product.category_id, func.count())
        .where(Product.status == "published")
        .group_by(Product.category_id)
    )
    return dict(result.all())


@router.get("/categories", response_model=list[CategoryNode])
async def list_categories(db: DbSession):
    rows = (
        await db.execute(
            select(Category)
            .where(Category.status == "published")
            .order_by(Category.sort_order, Category.name)
        )
    ).scalars().all()
    counts = await product_counts(db)

    nodes = {
        c.id: CategoryNode(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            product_count=counts.get(c.id, 0),
        )
        for c in rows
    }

    roots: list[CategoryNode] = []
    for c in rows:
        node = nodes[c.id]
        if c.parent_id is None:
            roots.append(node)
        elif c.parent_id in nodes:
            parent = nodes[c.parent_id]
            parent.children.append(node)
            parent.product_count += node.product_count
    return roots


@router.get("/categories/{slug}", response_model=CategoryDetail)
async def get_category(slug: str, db: DbSession):
    category = (
        await db.execute(
            select(Category).where(Category.slug == slug, Category.status == "published")
        )
    ).scalar_one_or_none()
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    parent = None
    if category.parent_id is not None:
        parent = (
            await db.execute(
                select(Category).where(
                    Category.id == category.parent_id, Category.status == "published"
                )
            )
        ).scalar_one_or_none()

    children = (
        await db.execute(
            select(Category)
            .where(Category.parent_id == category.id, Category.status == "published")
            .order_by(Category.sort_order, Category.name)
        )
    ).scalars().all()

    counts = await product_counts(db)
    child_nodes = [
        CategoryNode(
            id=c.id,
            name=c.name,
            slug=c.slug,
            description=c.description,
            product_count=counts.get(c.id, 0),
        )
        for c in children
    ]

    # A subcategory also uses the attributes assigned to its parent category.
    category_ids = [category.id] + ([category.parent_id] if category.parent_id else [])
    attribute_rows = (
        await db.execute(
            select(AttributeDefinition)
            .join(CategoryAttribute, CategoryAttribute.attribute_id == AttributeDefinition.id)
            .where(CategoryAttribute.category_id.in_(category_ids))
            .order_by(AttributeDefinition.sort_order)
        )
    ).scalars().all()
    attributes = list({a.id: a for a in attribute_rows}.values())

    return CategoryDetail(
        id=category.id,
        name=category.name,
        slug=category.slug,
        description=category.description,
        seo_title=category.seo_title,
        seo_description=category.seo_description,
        product_count=counts.get(category.id, 0) + sum(n.product_count for n in child_nodes),
        parent=CategoryBrief.model_validate(parent) if parent else None,
        children=child_nodes,
        attributes=[AttributeOut.model_validate(a) for a in attributes],
    )


@router.get("/industries", response_model=list[IndustryOut])
async def list_industries(db: DbSession):
    rows = (
        await db.execute(
            select(Industry)
            .where(Industry.status == "published")
            .order_by(Industry.sort_order, Industry.name)
        )
    ).scalars().all()
    return [IndustryOut.model_validate(r) for r in rows]