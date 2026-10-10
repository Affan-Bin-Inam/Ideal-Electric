from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models import RefreshToken, User
from api.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)

LOCKOUT_THRESHOLD = 5
LOCKOUT_MINUTES = 15

# Checked against when the email doesn't exist, so "unknown email" takes as long
# as "wrong password" and timing doesn't reveal which accounts exist.
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class InvalidCredentials(Exception):
    """Deliberately vague: callers never learn which part was wrong."""


async def authenticate(db: AsyncSession, email: str, password: str) -> User:
    now = datetime.now(UTC)
    user = (
        await db.execute(select(User).where(User.email == email.strip().lower()))
    ).scalar_one_or_none()

    if user is None or not user.is_active or (user.locked_until and user.locked_until > now):
        verify_password(password, _DUMMY_HASH)
        raise InvalidCredentials

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= LOCKOUT_THRESHOLD:
            user.locked_until = now + timedelta(minutes=LOCKOUT_MINUTES)
            user.failed_login_count = 0
        await db.commit()  # must persist the failure even though we raise next
        raise InvalidCredentials

    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = now
    if password_needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    return user


async def issue_tokens(
    db: AsyncSession, user: User, family_id: uuid.UUID | None = None
) -> tuple[str, str]:
    """Create an access token and a new refresh token. The caller commits."""
    refresh = generate_refresh_token()
    db.add(
        RefreshToken(
            user_id=user.id,
            family_id=family_id or uuid.uuid4(),
            token_hash=hash_token(refresh),
            expires_at=datetime.now(UTC) + timedelta(days=settings.refresh_token_days),
        )
    )
    return create_access_token(user.id), refresh


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(UTC))
    )


async def rotate_refresh_token(db: AsyncSession, plain_token: str) -> tuple[User, str, str]:
    now = datetime.now(UTC)
    row = (
        await db.execute(
            select(RefreshToken)
            .where(RefreshToken.token_hash == hash_token(plain_token))
            .with_for_update()
        )
    ).scalar_one_or_none()

    if row is None:
        raise InvalidCredentials

    if row.revoked_at is not None:
        # A token that was already rotated is being used again: assume it was stolen
        # and end every session in this family.
        await _revoke_family(db, row.family_id)
        await db.commit()
        raise InvalidCredentials

    if row.expires_at <= now:
        raise InvalidCredentials

    user = await db.get(User, row.user_id)
    if user is None or not user.is_active:
        raise InvalidCredentials

    row.revoked_at = now
    access, refresh = await issue_tokens(db, user, family_id=row.family_id)
    await db.commit()
    return user, access, refresh


async def revoke_session(db: AsyncSession, plain_token: str) -> None:
    row = (
        await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == hash_token(plain_token))
        )
    ).scalar_one_or_none()
    if row is not None:
        await _revoke_family(db, row.family_id)