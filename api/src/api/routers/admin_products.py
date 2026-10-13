from __future__ import annotations

import math

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from api.deps import CurrentUser, DbSession, require_role, verify_origin
from api.models import Category, Product
from api.schemas.admin import (
    ProductAdminOut,
    ProductAdminPage,
    ProductAdminRow,
    ProductCreate,
    ProductUpdate,
    Status,
)
from api.services.admin_crud import delete_entity, get_or_404
from api.services.admin_products import create_product, load_state, to_out, update_product

router = APIRouter(
    prefix="/admin/products",
    tags=["admin: products"],
    dependencies=[Depends(verify_origin), Depends(require_role("editor"))],
)


@router.get("", response_model=ProductAdminPage)
async def list_products(
    db: DbSession,
    q: str | None = Query(None, max_length=100),
    category_id: int | None = None,
    status: Status | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    conditions = []
    if q:
        conditions.append(Product.name.icontains(q, autoescape=True))
    if category_id is not None:
        child_ids = (
            await db.execute(select(Category.id).where(Category.parent_id == category_id))
        ).scalars().all()
        conditions.append(Product.category_id.in_([category_id, *child_ids]))
    if status is not None:
        conditions.append(Product.status == status)

    total = (
        await db.execute(select(func.count()).select_from(Product).where(*conditions))
    ).scalar_one()
    rows = (
        await db.execute(
            select(Product)
            .options(joinedload(Product.category), joinedload(Product.series))
            .where(*conditions)
            .order_by(Product.updated_at.desc(), Product.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()

    return ProductAdminPage(
        items=[
            ProductAdminRow(
                id=p.id, name=p.name, slug=p.slug, status=p.status, is_featured=p.is_featured,
                is_placeholder=p.is_placeholder, category_name=p.category.name,
                series_name=p.series.name if p.series else None, updated_at=p.updated_at,
            )
            for p in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get("/{product_id}", response_model=ProductAdminOut)
async def get_product(product_id: int, db: DbSession):
    product = await get_or_404(db, Product, product_id, "product")
    return to_out(product, await load_state(db, product))


@router.post("", response_model=ProductAdminOut, status_code=201)
async def create(body: ProductCreate, user: CurrentUser, db: DbSession):
    return await create_product(db, user, body)


@router.patch("/{product_id}", response_model=ProductAdminOut)
async def update(product_id: int, body: ProductUpdate, user: CurrentUser, db: DbSession):
    product = await get_or_404(db, Product, product_id, "product")
    return await update_product(db, user, product, body)


@router.delete("/{product_id}", status_code=204, dependencies=[Depends(require_role())])
async def delete(product_id: int, user: CurrentUser, db: DbSession):
    # require_role() with no roles means admins only; editors archive instead of deleting.
    product = await get_or_404(db, Product, product_id, "product")
    await delete_entity(
        db, user, Product, product, entity_type="product", label="product", in_use=[]
    )
    return Response(status_code=204)