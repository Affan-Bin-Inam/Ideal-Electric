from __future__ import annotations

import asyncio
import io
import re
import uuid
from pathlib import Path

from fastapi import HTTPException
from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models import MediaAsset, User
from api.schemas.media import MediaOut
from api.services.audit import record_audit
from api.services.storage import storage

VARIANT_WIDTHS = {"thumb": 320, "medium": 800, "large": 1600}
ALLOWED_FORMATS = {"JPEG", "PNG", "WEBP"}


class MediaError(Exception):
    """The upload is not acceptable. The message is safe to show the user."""


def sanitize_filename(name: str) -> str:
    """Kept only as a label. It is never used to build a path."""
    base = Path(name.replace("\\", "/")).name
    base = re.sub(r"[^\w.\- ]", "", base).strip(" .")
    return (base or "upload")[:200]


def process_image(data: bytes) -> tuple[int, int, dict[str, bytes]]:
    """Validate an image by its content and render the WebP sizes. CPU-bound: run in a thread."""
    try:
        image = Image.open(io.BytesIO(data))  # reads the header only
        if image.format not in ALLOWED_FORMATS:
            raise MediaError("Only JPEG, PNG and WebP images are accepted")
        if image.width * image.height > settings.max_image_pixels:
            raise MediaError("The image dimensions are too large")
        image = ImageOps.exif_transpose(image)  # honour the camera's rotation, then...
    except MediaError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError):
        raise MediaError("The file is not a valid image")

    has_alpha = image.mode in ("RGBA", "LA", "PA") or (
        image.mode == "P" and "transparency" in image.info
    )
    image = image.convert("RGBA" if has_alpha else "RGB")
    width, height = image.size

    variants: dict[str, bytes] = {}
    for name, target in VARIANT_WIDTHS.items():
        if width > target:  # never upscale
            resized = image.resize((target, round(height * target / width)), Image.LANCZOS)
        else:
            resized = image
        buffer = io.BytesIO()
        resized.save(buffer, "WEBP", quality=82, method=4)  # re-encoding drops EXIF and GPS data
        variants[name] = buffer.getvalue()
    return width, height, variants


def validate_pdf(data: bytes) -> None:
    if not data.startswith(b"%PDF-") or b"%%EOF" not in data[-2048:]:
        raise MediaError("The file is not a complete PDF")


def media_out(asset: MediaAsset) -> MediaOut:
    thumb = storage.url(asset.variants["thumb"]) if asset.kind == "image" else None
    return MediaOut(
        id=asset.id, kind=asset.kind, original_filename=asset.original_filename,
        mime_type=asset.mime_type, size_bytes=asset.size_bytes, width=asset.width,
        height=asset.height, alt_text=asset.alt_text, is_placeholder=asset.is_placeholder,
        url=storage.url(asset.storage_key), thumb_url=thumb, created_at=asset.created_at,
    )


async def create_asset(
    db: AsyncSession, user: User, *, data: bytes, filename: str, alt_text: str | None
) -> MediaAsset:
    if len(data) > settings.max_document_bytes:
        raise HTTPException(413, "The file is too large")
    safe_name = sanitize_filename(filename)
    asset_id = uuid.uuid4().hex

    try:
        # The kind is decided by what the bytes are, never by the extension or declared type.
        if data.startswith(b"%PDF-"):
            validate_pdf(data)
            key = f"documents/{asset_id}.pdf"
            files = {key: data}
            fields = dict(
                kind="document", mime_type="application/pdf", size_bytes=len(data),
                width=None, height=None, variants={}, storage_key=key,
            )
        else:
            if len(data) > settings.max_image_bytes:
                raise HTTPException(413, "The image is too large")
            width, height, rendered = await asyncio.to_thread(process_image, data)
            files = {f"images/{asset_id}/{name}.webp": blob for name, blob in rendered.items()}
            fields = dict(
                kind="image", mime_type="image/webp", size_bytes=len(rendered["large"]),
                width=width, height=height,
                variants={name: f"images/{asset_id}/{name}.webp" for name in rendered},
                storage_key=f"images/{asset_id}/large.webp",
            )
    except MediaError as error:
        raise HTTPException(422, str(error))

    saved: list[str] = []
    for key, blob in files.items():
        await asyncio.to_thread(storage.save, key, blob)
        saved.append(key)

    asset = MediaAsset(
        original_filename=safe_name, alt_text=alt_text, uploaded_by_id=user.id, **fields
    )
    db.add(asset)
    try:
        await db.flush()
        record_audit(db, user, "create", "media", asset.id, f"Uploaded {asset.kind} '{safe_name}'")
        await db.commit()
    except Exception:
        await db.rollback()
        for key in saved:  # don't leave orphan files behind
            await asyncio.to_thread(storage.delete, key)
        raise
    await db.refresh(asset)
    return asset