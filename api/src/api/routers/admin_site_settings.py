from __future__ import annotations

from fastapi import APIRouter, Depends

from api.deps import CurrentUser, DbSession, require_role, verify_origin
from api.schemas.admin import SiteSettingsAdminOut, SiteSettingsUpdate
from api.services.site_settings import get_site_settings, update_site_settings

router = APIRouter(
    prefix="/admin/site-settings",
    tags=["admin: site settings"],
    dependencies=[Depends(verify_origin), Depends(require_role("editor"))],
)


@router.get("", response_model=SiteSettingsAdminOut)
async def get_settings(db: DbSession):
    return await get_site_settings(db)


# require_role() with no roles means admins only. Editors can read the settings but not
# change company contact details.
@router.patch("", response_model=SiteSettingsAdminOut, dependencies=[Depends(require_role())])
async def update_settings(body: SiteSettingsUpdate, user: CurrentUser, db: DbSession):
    return await update_site_settings(db, user, body.model_dump(exclude_unset=True))