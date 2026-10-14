from __future__ import annotations

from fastapi import APIRouter, Response

from api.deps import DbSession
from api.schemas.admin import SiteSettingsPublic
from api.services.site_settings import get_site_settings

router = APIRouter(prefix="/site-settings", tags=["site settings"])


@router.get("", response_model=SiteSettingsPublic)
async def read_site_settings(db: DbSession, response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    return await get_site_settings(db)