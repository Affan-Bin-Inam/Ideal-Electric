import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


async def slug_taken(db: AsyncSession, model, slug: str, exclude_id: int | None = None) -> bool:
    stmt = select(model.id).where(model.slug == slug)
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    return (await db.execute(stmt)).first() is not None


async def unique_slug(db: AsyncSession, model, text: str, exclude_id: int | None = None) -> str:
    base = slugify(text)[:120] or "item"
    candidate, n = base, 2
    while await slug_taken(db, model, candidate, exclude_id):
        candidate = f"{base}-{n}"
        n += 1
    return candidate