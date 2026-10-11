from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, DbSession, require_role, verify_origin
from api.models import Category, Product
from api.schemas.admin import CategoryAdminOut, CategoryCreate, CategoryUpdate
from api.services.admin_crud import (
    count_rows,
    create_entity,
    delete_entity,
    get_or_404,
    update_entity,
    with_count,
)

router = APIRouter(
    prefix="/admin/categories",
    tags=["admin: categories"],
    dependencies=[Depends(verify_origin), Depends(require_role("editor"))],
)


def sibling_scope(parent_id: int | None) -> tuple:
    """Names must be unique among siblings. At the top level the database constraint can't
    help, because NULL parents never compare equal, so we check it here."""
    if parent_id is None:
        return (Category.parent_id.is_(None),)
    return (Category.parent_id == parent_id,)


async def validate_parent(
    db: AsyncSession, parent_id: int | None, *, category_id: int | None = None,
    has_children: bool = False,
) -> None:
    if parent_id is None:
        return
    if parent_id == category_id:
        raise HTTPException(422, "A category cannot be its own parent")
    parent = await db.get(Category, parent_id)
    if parent is None:
        raise HTTPException(422, "Parent category not found")
    if parent.parent_id is not None:
        raise HTTPException(422, "Categories can only be nested two levels deep")
    if has_children:
        raise HTTPException(422, "A category with subcategories cannot become a subcategory")


@router.get("", response_model=list[CategoryAdminOut])
async def list_categories(db: DbSession):
    rows = (
        await db.execute(
            select(Category).order_by(
                Category.parent_id.nulls_first(), Category.sort_order, Category.name
            )
        )
    ).scalars().all()
    counts = dict(
        (await db.execute(select(Product.category_id, func.count()).group_by(Product.category_id))).all()
    )
    return [with_count(CategoryAdminOut, c, counts.get(c.id, 0)) for c in rows]


@router.get("/{category_id}", response_model=CategoryAdminOut)
async def get_category(category_id: int, db: DbSession):
    category = await get_or_404(db, Category, category_id, "category")
    count = await count_rows(db, Product, Product.category_id == category.id)
    return with_count(CategoryAdminOut, category, count)


@router.post("", response_model=CategoryAdminOut, status_code=201)
async def create_category(body: CategoryCreate, user: CurrentUser, db: DbSession):
    await validate_parent(db, body.parent_id)
    category = await create_entity(
        db, user, Category, body.model_dump(),
        entity_type="category", label="category", name_scope=sibling_scope(body.parent_id),
    )
    return with_count(CategoryAdminOut, category, 0)


@router.patch("/{category_id}", response_model=CategoryAdminOut)
async def update_category(category_id: int, body: CategoryUpdate, user: CurrentUser, db: DbSession):
    category = await get_or_404(db, Category, category_id, "category")
    updates = body.model_dump(exclude_unset=True)

    new_parent = updates.get("parent_id")
    if new_parent is not None and new_parent != category.parent_id:
        has_children = await count_rows(db, Category, Category.parent_id == category.id) > 0
        await validate_parent(db, new_parent, category_id=category.id, has_children=has_children)

    target_parent = updates.get("parent_id", category.parent_id)
    category = await update_entity(
        db, user, Category, category, updates,
        entity_type="category", label="category", name_scope=sibling_scope(target_parent),
    )
    count = await count_rows(db, Product, Product.category_id == category.id)
    return with_count(CategoryAdminOut, category, count)


@router.delete("/{category_id}", status_code=204)
async def delete_category(category_id: int, user: CurrentUser, db: DbSession):
    category = await get_or_404(db, Category, category_id, "category")
    in_use = [
        (await count_rows(db, Category, Category.parent_id == category.id), "subcategories"),
        (await count_rows(db, Product, Product.category_id == category.id), "products"),
    ]
    await delete_entity(
        db, user, Category, category, entity_type="category", label="category", in_use=in_use
    )
    return Response(status_code=204)