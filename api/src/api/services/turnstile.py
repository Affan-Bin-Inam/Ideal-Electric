from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Annotated

import httpx
from fastapi import Depends

from api.config import settings

VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"

Verifier = Callable[[str | None, str | None], Awaitable[bool]]


async def verify_turnstile(token: str | None, remote_ip: str | None = None) -> bool:
    """Ask Cloudflare whether this CAPTCHA token is genuine. Fails closed on any problem."""
    if not token:
        return False
    data = {"secret": settings.turnstile_secret_key, "response": token}
    if remote_ip:
        data["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.post(VERIFY_URL, data=data)
        return response.status_code == 200 and response.json().get("success") is True
    except (httpx.HTTPError, ValueError):
        return False


def get_turnstile_verifier() -> Verifier:
    return verify_turnstile


# A dependency, so tests can swap in a fake instead of calling Cloudflare.
TurnstileVerifier = Annotated[Verifier, Depends(get_turnstile_verifier)]