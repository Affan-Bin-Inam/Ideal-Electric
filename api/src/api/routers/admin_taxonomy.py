from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select

from api.deps import CurrentUser, DbSession, require_role, verify_origin
from api.models import Brand, Industry, Product, ProductIndustry, Series
from api.schemas.admin import (
    BrandAdminOut,
    BrandUpdate,
    IndustryAdminOut,
    IndustryCreate,
    IndustryUpdate,
    SeriesAdminOut,
    SeriesCreate,
    SeriesUpdate,
)
from api.services.admin_crud import (
    count_rows,
    create_entity,
    delete_entity,
    get_or_404,
    update_entity,
    with_count,
)

router = APIRouter(
    prefix="/admin",
    tags=["admin: taxonomy"],
    dependencies=[Depends(verify_origin), Depends(require_role("editor"))],
)


# ------------------------------------------------------------------ series


@router.get("/series", response_model=list[SeriesAdminOut])
async def list_series(db: DbSession):
    rows = (
        await db.execute(select(Series).order_by(Series.brand_id, Series.sort_order, Series.name))
    ).scalars().all()
    counts = dict(
        (
            await db.execute(
                select(Product.series_id, func.count())
                .where(Product.series_id.is_not(None))
                .group_by(Product.series_id)
            )
        ).all()
    )
    return [with_count(SeriesAdminOut, r, counts.get(r.id, 0)) for r in rows]


@router.get("/series/{series_id}", response_model=SeriesAdminOut)
async def get_series(series_id: int, db: DbSession):
    obj = await get_or_404(db, Series, series_id, "series")
    return with_count(SeriesAdminOut, obj, await count_rows(db, Product, Product.series_id == obj.id))


@router.post("/series", response_model=SeriesAdminOut, status_code=201)
async def create_series(body: SeriesCreate, user: CurrentUser, db: DbSession):
    if await db.get(Brand, body.brand_id) is None:
        raise HTTPException(422, "Brand not found")
    obj = await create_entity(
        db, user, Series, body.model_dump(), entity_type="series", label="series",
        name_scope=(Series.brand_id == body.brand_id,),
    )
    return with_count(SeriesAdminOut, obj, 0)


@router.patch("/series/{series_id}", response_model=SeriesAdminOut)
async def update_series(series_id: int, body: SeriesUpdate, user: CurrentUser, db: DbSession):
    obj = await get_or_404(db, Series, series_id, "series")
    obj = await update_entity(
        db, user, Series, obj, body.model_dump(exclude_unset=True),
        entity_type="series", label="series", name_scope=(Series.brand_id == obj.brand_id,),
    )
    return with_count(SeriesAdminOut, obj, await count_rows(db, Product, Product.series_id == obj.id))


@router.delete("/series/{series_id}", status_code=204)
async def delete_series(series_id: int, user: CurrentUser, db: DbSession):
    obj = await get_or_404(db, Series, series_id, "series")
    in_use = [(await count_rows(db, Product, Product.series_id == obj.id), "products")]
    await delete_entity(db, user, Series, obj, entity_type="series", label="series", in_use=in_use)
    return Response(status_code=204)


# ------------------------------------------------------------------ industries


@router.get("/industries", response_model=list[IndustryAdminOut])
async def list_industries(db: DbSession):
    rows = (
        await db.execute(select(Industry).order_by(Industry.sort_order, Industry.name))
    ).scalars().all()
    counts = dict(
        (
            await db.execute(
                select(ProductIndustry.industry_id, func.count()).group_by(ProductIndustry.industry_id)
            )
        ).all()
    )
    return [with_count(IndustryAdminOut, r, counts.get(r.id, 0)) for r in rows]


@router.get("/industries/{industry_id}", response_model=IndustryAdminOut)
async def get_industry(industry_id: int, db: DbSession):
    obj = await get_or_404(db, Industry, industry_id, "industry")
    count = await count_rows(db, ProductIndustry, ProductIndustry.industry_id == obj.id)
    return with_count(IndustryAdminOut, obj, count)


@router.post("/industries", response_model=IndustryAdminOut, status_code=201)
async def create_industry(body: IndustryCreate, user: CurrentUser, db: DbSession):
    obj = await create_entity(
        db, user, Industry, body.model_dump(), entity_type="industry", label="industry"
    )
    return with_count(IndustryAdminOut, obj, 0)


@router.patch("/industries/{industry_id}", response_model=IndustryAdminOut)
async def update_industry(industry_id: int, body: IndustryUpdate, user: CurrentUser, db: DbSession):
    obj = await get_or_404(db, Industry, industry_id, "industry")
    obj = await update_entity(
        db, user, Industry, obj, body.model_dump(exclude_unset=True),
        entity_type="industry", label="industry",
    )
    count = await count_rows(db, ProductIndustry, ProductIndustry.industry_id == obj.id)
    return with_count(IndustryAdminOut, obj, count)


@router.delete("/industries/{industry_id}", status_code=204)
async def delete_industry(industry_id: int, user: CurrentUser, db: DbSession):
    obj = await get_or_404(db, Industry, industry_id, "industry")
    in_use = [
        (await count_rows(db, ProductIndustry, ProductIndustry.industry_id == obj.id), "products")
    ]
    await delete_entity(
        db, user, Industry, obj, entity_type="industry", label="industry", in_use=in_use
    )
    return Response(status_code=204)


# ------------------------------------------------------------------ brands (list and edit only)


@router.get("/brands", response_model=list[BrandAdminOut])
async def list_brands(db: DbSession):
    rows = (await db.execute(select(Brand).order_by(Brand.sort_order, Brand.name))).scalars().all()
    counts = dict(
        (
            await db.execute(
                select(Product.brand_id, func.count())
                .where(Product.brand_id.is_not(None))
                .group_by(Product.brand_id)
            )
        ).all()
    )
    return [with_count(BrandAdminOut, r, counts.get(r.id, 0)) for r in rows]


@router.get("/brands/{brand_id}", response_model=BrandAdminOut)
async def get_brand(brand_id: int, db: DbSession):
    obj = await get_or_404(db, Brand, brand_id, "brand")
    return with_count(BrandAdminOut, obj, await count_rows(db, Product, Product.brand_id == obj.id))


@router.patch("/brands/{brand_id}", response_model=BrandAdminOut)
async def update_brand(brand_id: int, body: BrandUpdate, user: CurrentUser, db: DbSession):
    obj = await get_or_404(db, Brand, brand_id, "brand")
    obj = await update_entity(
        db, user, Brand, obj, body.model_dump(exclude_unset=True),
        entity_type="brand", label="brand",
    )
    return with_count(BrandAdminOut, obj, await count_rows(db, Product, Product.brand_id == obj.id))