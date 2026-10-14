from __future__ import annotations

from fastapi import APIRouter, Response

from api.deps import DbSession
from api.schemas.homepage import HomepageOut
from api.services.homepage import build_public_homepage

router = APIRouter(tags=["homepage"])


@router.get("/homepage", response_model=HomepageOut)
async def read_homepage(db: DbSession, response: Response):
    response.headers["Cache-Control"] = "public, max-age=60"
    return await build_public_homepage(db)