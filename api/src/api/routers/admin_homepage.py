from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import CurrentUser, DbSession, require_role, verify_origin
from api.schemas.homepage import (
    HomepageOrder, HomepageSectionAdminOut, HomepageSectionUpdate, SectionKey,
)
from api.services.homepage import list_admin_sections, reorder_sections, update_section

router = APIRouter(
    prefix="/admin/homepage",
    tags=["admin: homepage"],
    dependencies=[Depends(verify_origin), Depends(require_role("editor"))],
)


@router.get("", response_model=list[HomepageSectionAdminOut])
async def list_sections(db: DbSession):
    return await list_admin_sections(db)


# Registered before "/{key}" is irrelevant here (different methods), but keep both together.
@router.put("/order", response_model=list[HomepageSectionAdminOut])
async def set_order(body: HomepageOrder, user: CurrentUser, db: DbSession):
    return await reorder_sections(db, user, body.keys)


@router.patch("/{key}", response_model=HomepageSectionAdminOut)
async def update(key: SectionKey, body: HomepageSectionUpdate, user: CurrentUser, db: DbSession):
    return await update_section(db, user, key, body.model_dump(exclude_unset=True))