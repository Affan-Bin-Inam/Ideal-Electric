from __future__ import annotations

from typing import Any

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import User
from api.services.audit import compute_changes, record_audit
from api.services.slugs import slug_taken, unique_slug


async def get_or_404(db: AsyncSession, model, entity_id: int, label: str):
    obj = await db.get(model, entity_id)
    if obj is None:
        raise HTTPException(404, f"{label.capitalize()} not found")
    return obj


async def count_rows(db: AsyncSession, model, *conditions) -> int:
    stmt = select(func.count()).select_from(model).where(*conditions)
    return (await db.execute(stmt)).scalar_one()


def with_count(schema, obj, count: int):
    out = schema.model_validate(obj)
    out.product_count = count
    return out


async def ensure_name_free(
    db: AsyncSession, model, name: str, *scope, label: str, exclude_id: int | None = None
) -> None:
    """Names are compared case-insensitively within `scope` (for example, the same parent)."""
    stmt = select(model.id).where(func.lower(model.name) == name.lower(), *scope)
    if exclude_id is not None:
        stmt = stmt.where(model.id != exclude_id)
    if (await db.execute(stmt)).first() is not None:
        raise HTTPException(409, f"A {label} with this name already exists")


async def flush_or_conflict(db: AsyncSession, label: str) -> None:
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, f"Conflicts with an existing {label} (name or slug)")


async def create_entity(
    db: AsyncSession, user: User, model, data: dict[str, Any], *,
    entity_type: str, label: str, name_scope: tuple = (),
):
    await ensure_name_free(db, model, data["name"], *name_scope, label=label)

    requested = data.pop("slug", None)
    if requested:
        if await slug_taken(db, model, requested):
            raise HTTPException(409, "That slug is already in use")
        slug = requested
    else:
        slug = await unique_slug(db, model, data["name"])

    obj = model(**data, slug=slug)
    db.add(obj)
    await flush_or_conflict(db, label)
    record_audit(db, user, "create", entity_type, obj.id, f"Created {label} '{obj.name}'")
    await db.commit()
    await db.refresh(obj)  # load the values the database generated (ids, timestamps)
    return obj


async def update_entity(
    db: AsyncSession, user: User, model, obj, updates: dict[str, Any], *,
    entity_type: str, label: str, name_scope: tuple = (),
):
    if "name" in updates:
        await ensure_name_free(
            db, model, updates["name"], *name_scope, label=label, exclude_id=obj.id
        )
    if "slug" in updates and updates["slug"] != obj.slug:
        if await slug_taken(db, model, updates["slug"], exclude_id=obj.id):
            raise HTTPException(409, "That slug is already in use")

    changes = compute_changes(obj, updates)
    if not changes:
        return obj

    for field, value in updates.items():
        setattr(obj, field, value)
    await flush_or_conflict(db, label)
    record_audit(
        db, user, "update", entity_type, obj.id, f"Updated {label} '{obj.name}'", changes
    )
    await db.commit()
    await db.refresh(obj)
    return obj


async def delete_entity(
    db: AsyncSession, user: User, model, obj, *,
    entity_type: str, label: str, in_use: list[tuple[int, str]],
) -> None:
    for number, what in in_use:
        if number:
            raise HTTPException(
                409,
                f"This {label} is in use ({what}: {number}). "
                f"Reassign them first, or archive the {label} instead.",
            )
    record_audit(
        db, user, "delete", entity_type, obj.id,
        f"Deleted {label} '{obj.name}'", {"slug": obj.slug},
    )
    # A direct DELETE: the ORM would otherwise try to load related collections first.
    await db.execute(delete(model).where(model.id == obj.id))
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(409, f"This {label} is still referenced elsewhere")