from __future__ import annotations

import asyncio
import math

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy import delete, func, select

from api.config import settings
from api.deps import CurrentUser, DbSession, require_role, verify_origin
from api.models import CategoryDocument, MediaAsset, ProductImage
from api.schemas.media import MediaOut, MediaPage, MediaUpdate
from api.services.admin_crud import count_rows, get_or_404
from api.services.audit import compute_changes, record_audit
from api.services.media import create_asset, media_out
from api.services.storage import storage

router = APIRouter(
    prefix="/admin/media",
    tags=["admin: media"],
    dependencies=[Depends(verify_origin), Depends(require_role("editor"))],
)


@router.post("", response_model=MediaOut, status_code=201)
async def upload_media(
    user: CurrentUser,
    db: DbSession,
    file: UploadFile = File(...),
    alt_text: str | None = Form(None),
):
    if alt_text is not None and len(alt_text) > 300:
        raise HTTPException(422, "Alt text is limited to 300 characters")
    # Read at most one byte past the biggest allowed size, so a huge upload can't fill memory.
    data = await file.read(settings.max_document_bytes + 1)
    asset = await create_asset(
        db, user, data=data, filename=file.filename or "upload", alt_text=alt_text or None
    )
    return media_out(asset)


@router.get("", response_model=MediaPage)
async def list_media(
    db: DbSession,
    kind: str | None = Query(None, pattern="^(image|document)$"),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    conditions = []
    if kind:
        conditions.append(MediaAsset.kind == kind)
    if q:
        conditions.append(MediaAsset.original_filename.icontains(q, autoescape=True))
    total = (
        await db.execute(select(func.count()).select_from(MediaAsset).where(*conditions))
    ).scalar_one()
    rows = (
        await db.execute(
            select(MediaAsset)
            .where(*conditions)
            .order_by(MediaAsset.created_at.desc(), MediaAsset.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).scalars().all()
    return MediaPage(
        items=[media_out(a) for a in rows],
        total=total, page=page, page_size=page_size, pages=math.ceil(total / page_size),
    )


@router.get("/{asset_id}", response_model=MediaOut)
async def get_media(asset_id: int, db: DbSession):
    return media_out(await get_or_404(db, MediaAsset, asset_id, "file"))


@router.patch("/{asset_id}", response_model=MediaOut)
async def update_media(asset_id: int, body: MediaUpdate, user: CurrentUser, db: DbSession):
    asset = await get_or_404(db, MediaAsset, asset_id, "file")
    updates = body.model_dump(exclude_unset=True)
    changes = compute_changes(asset, updates)
    if changes:
        for field, value in updates.items():
            setattr(asset, field, value)
        record_audit(
            db, user, "update", "media", asset.id, f"Updated file '{asset.original_filename}'", changes
        )
        await db.commit()
        await db.refresh(asset)
    return media_out(asset)


@router.delete("/{asset_id}", status_code=204)
async def delete_media(asset_id: int, user: CurrentUser, db: DbSession):
    asset = await get_or_404(db, MediaAsset, asset_id, "file")
    in_use = [
        (await count_rows(db, ProductImage, ProductImage.asset_id == asset.id), "product galleries"),
        (await count_rows(db, CategoryDocument, CategoryDocument.asset_id == asset.id), "category documents"),
    ]
    for number, what in in_use:
        if number:
            raise HTTPException(409, f"This file is in use ({what}: {number}). Remove it there first.")

    keys = {asset.storage_key, *asset.variants.values()}
    record_audit(
        db, user, "delete", "media", asset.id,
        f"Deleted file '{asset.original_filename}'", {"storage_key": asset.storage_key},
    )
    await db.execute(delete(MediaAsset).where(MediaAsset.id == asset.id))
    await db.commit()
    for key in keys:  # only after the database change is safely committed
        await asyncio.to_thread(storage.delete, key)
    return Response(status_code=204)