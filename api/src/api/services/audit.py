from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from api.models import AuditLog, User


def compute_changes(obj: Any, updates: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Fields whose new value differs from the current one, as {field: {from, to}}."""
    return {
        field: {"from": getattr(obj, field), "to": value}
        for field, value in updates.items()
        if getattr(obj, field) != value
    }


def record_audit(
    db: AsyncSession,
    user: User,
    action: str,
    entity_type: str,
    entity_id: int | None,
    summary: str,
    changes: dict | None = None,
) -> None:
    """Stage an audit row in the caller's transaction, so the change and its record commit together."""
    db.add(
        AuditLog(
            user_id=user.id,
            actor_email=user.email,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary[:300],
            changes=changes,
        )
    )