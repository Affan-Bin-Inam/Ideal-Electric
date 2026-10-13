from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from api.deps import DbSession
from api.models import Inquiry
from api.schemas.inquiries import InquiryCreate
from api.services.inquiries import hash_ip, resolve_product_options, too_many_recent
from api.services.turnstile import TurnstileVerifier

router = APIRouter(tags=["inquiries"])


@router.post("/inquiries", status_code=201)
async def submit_inquiry(
    body: InquiryCreate, request: Request, db: DbSession, verify_captcha: TurnstileVerifier
):
    # Cheapest checks first. A filled honeypot gets a normal-looking reply and nothing is stored,
    # so a bot has nothing to learn from.
    if body.website:
        return {"status": "received"}

    ip = request.client.host if request.client else None
    ip_hash = hash_ip(ip)
    if await too_many_recent(db, ip_hash):
        raise HTTPException(
            429, "Too many inquiries from your connection. Please try again later or contact us on WhatsApp."
        )
    if not await verify_captcha(body.turnstile_token, ip):
        raise HTTPException(400, "Verification failed. Please try again.")

    product, options = await resolve_product_options(db, body.product_slug, body.selected_options)
    db.add(
        Inquiry(
            product_id=product.id if product else None,
            product_name_snapshot=product.name if product else None,
            selected_options=options or None,
            name=body.name,
            company=body.company,
            email=body.email,
            phone=body.phone,
            city=body.city,
            message=body.message,
            source_page=body.source_page,
            ip_hash=ip_hash,
            user_agent=(request.headers.get("user-agent") or "")[:300] or None,
        )
    )
    await db.commit()
    return {"status": "received"}