from typing import Annotated
from urllib.parse import urlsplit

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.db import get_db
from api.models import User
from api.security import decode_access_token

DbSession = Annotated[AsyncSession, Depends(get_db)]

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


def verify_origin(request: Request) -> None:
    """CSRF defence: state-changing requests must come from a site we trust."""
    if request.method in SAFE_METHODS:
        return
    origin = request.headers.get("origin")
    if origin is None:
        referer = request.headers.get("referer")
        if referer is None:
            return  # not a browser request, so there are no ambient cookies to abuse
        parts = urlsplit(referer)
        origin = f"{parts.scheme}://{parts.netloc}"
    if origin not in settings.allowed_origins:
        raise HTTPException(status_code=403, detail="Origin not allowed")


async def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get("access_token")
    payload = decode_access_token(token) if token else None
    if payload is None:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        user_id = int(payload["sub"])
    except ValueError:
        raise HTTPException(status_code=401, detail="Not authenticated")
    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Not authenticated")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_role(*roles: str):
    """Allow the listed roles. Admins always pass."""

    async def checker(user: CurrentUser) -> User:
        if user.role != "admin" and user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return user

    return checker