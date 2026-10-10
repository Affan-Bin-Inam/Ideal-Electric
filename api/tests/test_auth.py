from datetime import UTC, datetime, timedelta

import jwt
import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from api.config import settings
from api.db import engine
from api.deps import require_role
from api.main import app
from api.security import ALGORITHM, create_access_token

BASE_URL = "http://testserver"
LOGIN = "/api/v1/auth/login"
REFRESH = "/api/v1/auth/refresh"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
REFRESH_PATH = "/api/v1/auth"
PASSWORD = "correct-horse-battery"


async def login(client, email="admin@example.com", password=PASSWORD, **kwargs):
    return await client.post(LOGIN, json={"email": email, "password": password}, **kwargs)


def refresh_cookie(client):
    return client.cookies.get("refresh_token", path=REFRESH_PATH)


def other_client():
    return AsyncClient(transport=ASGITransport(app=app), base_url=BASE_URL)


# ------------------------------------------------------------------ login


async def test_login_returns_user_and_sets_safe_cookies(client, make_user):
    await make_user()
    response = await login(client)
    assert response.status_code == 200
    assert response.json()["email"] == "admin@example.com"
    assert response.json()["role"] == "admin"

    cookies = [c.lower() for c in response.headers.get_list("set-cookie")]
    assert len(cookies) == 2
    assert all("httponly" in c for c in cookies)
    refresh = next(c for c in cookies if c.startswith("refresh_token="))
    assert "path=/api/v1/auth" in refresh
    assert "samesite=strict" in refresh


async def test_me_requires_login(client, make_user):
    await make_user()
    assert (await client.get(ME)).status_code == 401
    await login(client)
    assert (await client.get(ME)).status_code == 200


async def test_wrong_password_and_unknown_email_look_identical(client, make_user):
    await make_user()
    wrong_password = await login(client, password="not-the-password")
    unknown_email = await login(client, email="nobody@example.com")
    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()


async def test_email_is_case_insensitive(client, make_user):
    await make_user()
    assert (await login(client, email="ADMIN@Example.COM")).status_code == 200


async def test_inactive_user_cannot_log_in(client, make_user):
    await make_user(is_active=False)
    assert (await login(client)).status_code == 401


# ------------------------------------------------------------------ lockout


async def test_five_failures_lock_the_account(client, make_user):
    await make_user()
    for _ in range(5):
        assert (await login(client, password="wrong")).status_code == 401

    # Locked: even the correct password is refused, with the same vague message.
    locked = await login(client)
    assert locked.status_code == 401
    assert locked.json()["detail"] == "Invalid email or password"

    # Once the lock expires, the correct password works again.
    async with engine.begin() as conn:
        await conn.execute(text("UPDATE users SET locked_until = now() - interval '1 minute'"))
    assert (await login(client)).status_code == 200


async def test_successful_login_resets_the_failure_counter(client, make_user):
    await make_user()
    for _ in range(3):
        await login(client, password="wrong")
    assert (await login(client)).status_code == 200
    for _ in range(4):
        await login(client, password="wrong")
    # 3 + 4 failures would have locked the account if the counter hadn't been reset.
    assert (await login(client)).status_code == 200


# ------------------------------------------------------------------ refresh tokens


async def test_refresh_issues_a_new_token(client, make_user):
    await make_user()
    await login(client)
    old = refresh_cookie(client)
    response = await client.post(REFRESH)
    assert response.status_code == 200
    new = refresh_cookie(client)
    assert new and new != old


async def test_refresh_without_cookie_is_rejected(client):
    assert (await client.post(REFRESH)).status_code == 401


async def test_reused_refresh_token_revokes_the_whole_family(client, make_user):
    await make_user()
    await login(client)
    stolen = refresh_cookie(client)

    assert (await client.post(REFRESH)).status_code == 200  # legitimate rotation

    async with other_client() as attacker:
        replay = await attacker.post(REFRESH, headers={"Cookie": f"refresh_token={stolen}"})
    assert replay.status_code == 401

    # The reuse was detected, so the legitimate session is ended as well.
    assert (await client.post(REFRESH)).status_code == 401


async def test_logout_revokes_the_session(client, make_user):
    await make_user()
    await login(client)
    old = refresh_cookie(client)

    assert (await client.post(LOGOUT)).status_code == 204
    assert (await client.get(ME)).status_code == 401

    async with other_client() as other:
        replay = await other.post(REFRESH, headers={"Cookie": f"refresh_token={old}"})
    assert replay.status_code == 401


# ------------------------------------------------------------------ CSRF


async def test_untrusted_origin_is_rejected_on_state_changing_requests(client, make_user):
    await make_user()
    bad = await login(client, headers={"Origin": "https://evil.example"})
    assert bad.status_code == 403
    assert "access_token" not in client.cookies

    good = await login(client, headers={"Origin": "http://localhost:3000"})
    assert good.status_code == 200


# ------------------------------------------------------------------ access tokens and roles


@pytest.mark.parametrize("kind", ["expired", "wrong_key", "wrong_type", "garbage"])
async def test_invalid_access_tokens_are_rejected(client, make_user, kind):
    user = await make_user()
    now = datetime.now(UTC)
    claims = {"sub": str(user.id), "type": "access", "iat": now, "exp": now + timedelta(minutes=5)}
    if kind == "expired":
        claims["exp"] = now - timedelta(minutes=1)
        token = jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)
    elif kind == "wrong_key":
        token = jwt.encode(claims, "x" * 40, algorithm=ALGORITHM)
    elif kind == "wrong_type":
        claims["type"] = "refresh"
        token = jwt.encode(claims, settings.secret_key, algorithm=ALGORITHM)
    else:
        token = "not-a-jwt"
    response = await client.get(ME, headers={"Cookie": f"access_token={token}"})
    assert response.status_code == 401


mini_app = FastAPI()


@mini_app.get("/editor-area", dependencies=[Depends(require_role("editor"))])
async def editor_area():
    return {"ok": True}


async def call_editor_area(user_id: int):
    token = create_access_token(user_id)
    async with AsyncClient(transport=ASGITransport(app=mini_app), base_url=BASE_URL) as c:
        return await c.get("/editor-area", headers={"Cookie": f"access_token={token}"})


@pytest.mark.parametrize(("role", "expected"), [("admin", 200), ("editor", 200), ("sales", 403)])
async def test_role_checks(make_user, role, expected):
    user = await make_user(role=role)
    assert (await call_editor_area(user.id)).status_code == expected


async def test_deactivating_a_user_takes_effect_immediately(client, make_user):
    user = await make_user()
    await login(client)
    assert (await client.get(ME)).status_code == 200

    async with engine.begin() as conn:
        await conn.execute(text("UPDATE users SET is_active = false WHERE id = :id"), {"id": user.id})
    # The access token is still cryptographically valid, but the user lookup refuses it.
    assert (await client.get(ME)).status_code == 401