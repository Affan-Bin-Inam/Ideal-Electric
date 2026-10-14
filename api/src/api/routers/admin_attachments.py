from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, DbSession, require_role, verify_origin
from api.models import Category, CategoryDocument, MediaAsset, Product, ProductImage
from api.schemas.media import (
    DocumentItemOut,
    DocumentsReplace,
    GalleryItemOut,
    GalleryReplace,
)
from api.services.admin_crud import get_or_404
from api.services.audit import record_audit
from api.services.storage import storage

router = APIRouter(
    prefix="/admin",
    tags=["admin: attachments"],
    dependencies=[Depends(verify_origin), Depends(require_role("editor"))],
)


async def load_assets(db: AsyncSession, ids: list[int], kind: str) -> dict[int, MediaAsset]:
    if not ids:
        return {}
    found = {
        a.id: a
        for a in (await db.execute(select(MediaAsset).where(MediaAsset.id.in_(ids)))).scalars()
    }
    missing = [i for i in ids if i not in found]
    if missing:
        raise HTTPException(422, f"Unknown files: {missing}")
    wrong = [i for i, a in found.items() if a.kind != kind]
    if wrong:
        raise HTTPException(422, f"Files {wrong} are not of kind '{kind}'")
    return found


# ------------------------------------------------------------------ product galleries


async def gallery_state(db: AsyncSession, product_id: int) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(ProductImage)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order, ProductImage.id)
        )
    ).scalars().all()
    return [
        {"asset_id": r.asset_id, "primary": r.is_primary, "alt_override": r.alt_override}
        for r in rows
    ]


async def gallery_out(db: AsyncSession, product_id: int) -> list[GalleryItemOut]:
    rows = (
        await db.execute(
            select(ProductImage, MediaAsset)
            .join(MediaAsset, MediaAsset.id == ProductImage.asset_id)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.sort_order, ProductImage.id)
        )
    ).all()
    return [
        GalleryItemOut(
            asset_id=asset.id, sort_order=link.sort_order, is_primary=link.is_primary,
            alt_override=link.alt_override, alt_text=asset.alt_text,
            thumb_url=storage.url(asset.variants["thumb"]),
            large_url=storage.url(asset.variants["large"]),
        )
        for link, asset in rows
    ]


@router.get("/products/{product_id}/images", response_model=list[GalleryItemOut])
async def get_product_images(product_id: int, db: DbSession):
    await get_or_404(db, Product, product_id, "product")
    return await gallery_out(db, product_id)


@router.put("/products/{product_id}/images", response_model=list[GalleryItemOut])
async def set_product_images(
    product_id: int, body: GalleryReplace, user: CurrentUser, db: DbSession
):
    product = await get_or_404(db, Product, product_id, "product")
    items = body.images
    ids = [item.asset_id for item in items]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "An image can only appear once in a gallery")
    if sum(1 for item in items if item.is_primary) > 1:
        raise HTTPException(422, "Only one image can be primary")
    await load_assets(db, ids, "image")

    primary_index = next((n for n, item in enumerate(items) if item.is_primary), 0)
    new_state = [
        {"asset_id": item.asset_id, "primary": n == primary_index, "alt_override": item.alt_override}
        for n, item in enumerate(items)
    ]
    before = await gallery_state(db, product.id)
    if before != new_state:
        await db.execute(delete(ProductImage).where(ProductImage.product_id == product.id))
        for position, entry in enumerate(new_state):
            db.add(
                ProductImage(
                    product_id=product.id, asset_id=entry["asset_id"], sort_order=position,
                    is_primary=entry["primary"], alt_override=entry["alt_override"],
                )
            )
        product.updated_at = func.now()
        record_audit(
            db, user, "update", "product", product.id,
            f"Updated gallery of product '{product.name}'",
            {"images": {"from": before, "to": new_state}},
        )
        await db.commit()
    return await gallery_out(db, product.id)


# ------------------------------------------------------------------ category documents


async def documents_state(db: AsyncSession, category_id: int) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(CategoryDocument)
            .where(CategoryDocument.category_id == category_id)
            .order_by(CategoryDocument.sort_order, CategoryDocument.id)
        )
    ).scalars().all()
    return [
        {"asset_id": r.asset_id, "title": r.title, "doc_type": r.doc_type, "access": r.access}
        for r in rows
    ]


async def documents_out(db: AsyncSession, category_id: int) -> list[DocumentItemOut]:
    rows = (
        await db.execute(
            select(CategoryDocument, MediaAsset)
            .join(MediaAsset, MediaAsset.id == CategoryDocument.asset_id)
            .where(CategoryDocument.category_id == category_id)
            .order_by(CategoryDocument.sort_order, CategoryDocument.id)
        )
    ).all()
    return [
        DocumentItemOut(
            asset_id=asset.id, sort_order=doc.sort_order, title=doc.title,
            doc_type=doc.doc_type, access=doc.access, url=storage.url(asset.storage_key),
            original_filename=asset.original_filename,
        )
        for doc, asset in rows
    ]


@router.get("/categories/{category_id}/documents", response_model=list[DocumentItemOut])
async def get_category_documents(category_id: int, db: DbSession):
    await get_or_404(db, Category, category_id, "category")
    return await documents_out(db, category_id)


@router.put("/categories/{category_id}/documents", response_model=list[DocumentItemOut])
async def set_category_documents(
    category_id: int, body: DocumentsReplace, user: CurrentUser, db: DbSession
):
    category = await get_or_404(db, Category, category_id, "category")
    items = body.documents
    ids = [item.asset_id for item in items]
    if len(set(ids)) != len(ids):
        raise HTTPException(422, "A file can only be attached once to a category")
    await load_assets(db, ids, "document")

    new_state = [
        {"asset_id": i.asset_id, "title": i.title, "doc_type": i.doc_type, "access": i.access}
        for i in items
    ]
    before = await documents_state(db, category.id)
    if before != new_state:
        await db.execute(delete(CategoryDocument).where(CategoryDocument.category_id == category.id))
        for position, entry in enumerate(new_state):
            db.add(CategoryDocument(category_id=category.id, sort_order=position, **entry))
        category.updated_at = func.now()
        record_audit(
            db, user, "update", "category", category.id,
            f"Updated documents of category '{category.name}'",
            {"documents": {"from": before, "to": new_state}},
        )
        await db.commit()
    return await documents_out(db, category.id)