from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from api.config import settings
from api.deps import CurrentUser, DbSession, verify_origin
from api.schemas.auth import LoginRequest, UserOut
from api.services.auth import (
    InvalidCredentials,
    authenticate,
    issue_tokens,
    revoke_session,
    rotate_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"], dependencies=[Depends(verify_origin)])

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
REFRESH_PATH = "/api/v1/auth"


def set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    response.set_cookie(
        ACCESS_COOKIE, access,
        max_age=settings.access_token_minutes * 60,
        httponly=True, secure=settings.cookie_secure, samesite="lax", path="/",
    )
    response.set_cookie(
        REFRESH_COOKIE, refresh,
        max_age=settings.refresh_token_days * 86400,
        httponly=True, secure=settings.cookie_secure, samesite="strict", path=REFRESH_PATH,
    )


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(ACCESS_COOKIE, path="/")
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_PATH)


@router.post("/login", response_model=UserOut)
async def login(body: LoginRequest, response: Response, db: DbSession):
    try:
        user = await authenticate(db, body.email, body.password)
    except InvalidCredentials:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    access, refresh = await issue_tokens(db, user)
    await db.commit()
    set_auth_cookies(response, access, refresh)
    return UserOut.model_validate(user)


@router.post("/refresh", response_model=UserOut)
async def refresh_session(request: Request, response: Response, db: DbSession):
    token = request.cookies.get(REFRESH_COOKIE)
    failure = JSONResponse({"detail": "Not authenticated"}, status_code=401)
    if not token:
        return failure
    try:
        user, access, refresh = await rotate_refresh_token(db, token)
    except InvalidCredentials:
        clear_auth_cookies(failure)
        return failure
    set_auth_cookies(response, access, refresh)
    return UserOut.model_validate(user)


@router.post("/logout", status_code=204)
async def logout(request: Request, db: DbSession):
    token = request.cookies.get(REFRESH_COOKIE)
    if token:
        await revoke_session(db, token)
        await db.commit()
    response = Response(status_code=204)
    clear_auth_cookies(response)
    return response


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return UserOut.model_validate(user)