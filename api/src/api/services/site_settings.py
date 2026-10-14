from __future__ import annotations

from typing import Any

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import SiteSettings, User
from api.services.audit import compute_changes, record_audit

PLACEHOLDERS = {
    "company_name": "Ideal Electric",
    "phone_primary": "+92-XXX-XXXXXXX",
    "email_sales": None,
    "address_line": "Address to be confirmed",
    "city": "Pakistan",
}

async def update_site_settings(
    db: AsyncSession, user: User, updates: dict[str, Any]
) -> SiteSettings:
    row = await get_site_settings(db)
    changes = compute_changes(row, updates)
    if not changes:
        return row

    for field, value in updates.items():
        setattr(row, field, value)
    record_audit(
        db, user, "update", "site_settings", row.id, "Updated site settings", changes
    )
    await db.commit()
    await db.refresh(row)  # reload updated_at, which the database generates
    return row

async def get_site_settings(db: AsyncSession) -> SiteSettings:
    row = await db.get(SiteSettings, 1)
    if row is not None:
        return row
    # ON CONFLICT DO NOTHING: two first requests arriving together can't crash each other
    await db.execute(
        insert(SiteSettings).values(id=1, **PLACEHOLDERS).on_conflict_do_nothing()
    )
    await db.commit()
    return await db.get(SiteSettings, 1)