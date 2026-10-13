from __future__ import annotations

import math

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import CurrentUser, DbSession, require_role, verify_origin
from api.models import Inquiry, InquiryNote, User
from api.schemas.inquiries import (
    InquiryDetail,
    InquiryPage,
    InquiryRow,
    InquiryStatus,
    InquiryUpdate,
    NoteCreate,
    NoteOut,
)
from api.services.admin_crud import get_or_404
from api.services.audit import compute_changes, record_audit
from api.services.inquiries import whatsapp_number

router = APIRouter(
    prefix="/admin/inquiries",
    tags=["admin: inquiries"],
    dependencies=[Depends(verify_origin), Depends(require_role("sales", "editor"))],
)


async def build_detail(db: AsyncSession, inquiry: Inquiry) -> InquiryDetail:
    notes = (
        await db.execute(
            select(InquiryNote)
            .where(InquiryNote.inquiry_id == inquiry.id)
            .order_by(InquiryNote.created_at, InquiryNote.id)
        )
    ).scalars().all()
    assignee = await db.get(User, inquiry.assigned_to_id) if inquiry.assigned_to_id else None
    return InquiryDetail(
        id=inquiry.id,
        name=inquiry.name,
        company=inquiry.company,
        email=inquiry.email,
        phone=inquiry.phone,
        whatsapp_url=f"https://wa.me/{whatsapp_number(inquiry.phone)}",
        city=inquiry.city,
        message=inquiry.message,
        product_id=inquiry.product_id,
        product_name=inquiry.product_name_snapshot,
        selected_options=inquiry.selected_options,
        source_page=inquiry.source_page,
        status=inquiry.status,
        assigned_to_id=inquiry.assigned_to_id,
        assigned_to_email=assignee.email if assignee else None,
        created_at=inquiry.created_at,
        updated_at=inquiry.updated_at,
        notes=[NoteOut.model_validate(n) for n in notes],
    )


@router.get("", response_model=InquiryPage)
async def list_inquiries(
    db: DbSession,
    status: InquiryStatus | None = None,
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
):
    conditions = []
    if status is not None:
        conditions.append(Inquiry.status == status)
    if q:
        conditions.append(
            or_(
                Inquiry.name.icontains(q, autoescape=True),
                Inquiry.phone.icontains(q, autoescape=True),
                Inquiry.company.icontains(q, autoescape=True),
                Inquiry.product_name_snapshot.icontains(q, autoescape=True),
            )
        )
    total = (
        await db.execute(select(func.count()).select_from(Inquiry).where(*conditions))
    ).scalar_one()
    rows = (
        await db.execute(
            select(Inquiry, User.email)
            .outerjoin(User, User.id == Inquiry.assigned_to_id)
            .where(*conditions)
            .order_by(Inquiry.created_at.desc(), Inquiry.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
    ).all()
    return InquiryPage(
        items=[
            InquiryRow(
                id=i.id, name=i.name, phone=i.phone, company=i.company,
                product_name=i.product_name_snapshot, status=i.status,
                assigned_to_email=email, created_at=i.created_at,
            )
            for i, email in rows
        ],
        total=total,
        page=page,
        page_size=page_size,
        pages=math.ceil(total / page_size),
    )


@router.get("/{inquiry_id}", response_model=InquiryDetail)
async def get_inquiry(inquiry_id: int, db: DbSession):
    return await build_detail(db, await get_or_404(db, Inquiry, inquiry_id, "inquiry"))


@router.patch("/{inquiry_id}", response_model=InquiryDetail)
async def update_inquiry(inquiry_id: int, body: InquiryUpdate, user: CurrentUser, db: DbSession):
    inquiry = await get_or_404(db, Inquiry, inquiry_id, "inquiry")
    updates = body.model_dump(exclude_unset=True)

    if updates.get("assigned_to_id") is not None:
        assignee = await db.get(User, updates["assigned_to_id"])
        if assignee is None or not assignee.is_active:
            raise HTTPException(422, "Assignee not found")

    changes = compute_changes(inquiry, updates)
    if changes:
        for field, value in updates.items():
            setattr(inquiry, field, value)
        # The summary uses only the number, never the customer's name or phone.
        record_audit(db, user, "update", "inquiry", inquiry.id, f"Updated inquiry #{inquiry.id}", changes)
        await db.commit()
        await db.refresh(inquiry)
    return await build_detail(db, inquiry)


@router.post("/{inquiry_id}/notes", response_model=InquiryDetail, status_code=201)
async def add_note(inquiry_id: int, body: NoteCreate, user: CurrentUser, db: DbSession):
    inquiry = await get_or_404(db, Inquiry, inquiry_id, "inquiry")
    db.add(
        InquiryNote(inquiry_id=inquiry.id, user_id=user.id, author_email=user.email, body=body.body)
    )
    await db.commit()
    return await build_detail(db, inquiry)


@router.delete("/{inquiry_id}", status_code=204, dependencies=[Depends(require_role())])
async def delete_inquiry(inquiry_id: int, user: CurrentUser, db: DbSession):
    # Admins only: an inquiry holds personal data, so removing it is a deliberate act.
    inquiry = await get_or_404(db, Inquiry, inquiry_id, "inquiry")
    record_audit(db, user, "delete", "inquiry", inquiry.id, f"Deleted inquiry #{inquiry.id}")
    await db.execute(delete(Inquiry).where(Inquiry.id == inquiry.id))
    await db.commit()
    return Response(status_code=204)