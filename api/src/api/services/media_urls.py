from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models import CategoryDocument, MediaAsset, ProductImage
from api.schemas.catalogue import DocumentPublic, ImageOut, ProductCard
from api.services.storage import storage


def image_out(asset: MediaAsset, alt: str) -> ImageOut:
    variants = asset.variants
    return ImageOut(
        thumb_url=storage.url(variants["thumb"]),
        medium_url=storage.url(variants["medium"]),
        large_url=storage.url(variants["large"]),
        alt=alt,
    )


async def load_gallery(db: AsyncSession, product_id: int, product_name: str) -> list[ImageOut]:
    rows = (
        await db.execute(
            select(ProductImage, MediaAsset)
            .join(MediaAsset, MediaAsset.id == ProductImage.asset_id)
            .where(ProductImage.product_id == product_id)
            .order_by(ProductImage.is_primary.desc(), ProductImage.sort_order, ProductImage.id)
        )
    ).all()
    return [
        image_out(asset, link.alt_override or asset.alt_text or product_name) for link, asset in rows
    ]


async def attach_primary_images(db: AsyncSession, pairs: list[tuple[int, ProductCard]]) -> None:
    """Give each card its primary image using one query for the whole page."""
    if not pairs:
        return
    ids = [product_id for product_id, _ in pairs]
    rows = (
        await db.execute(
            select(ProductImage, MediaAsset)
            .join(MediaAsset, MediaAsset.id == ProductImage.asset_id)
            .where(ProductImage.product_id.in_(ids))
            .order_by(ProductImage.is_primary.desc(), ProductImage.sort_order, ProductImage.id)
        )
    ).all()
    first: dict[int, tuple[ProductImage, MediaAsset]] = {}
    for link, asset in rows:
        first.setdefault(link.product_id, (link, asset))
    for product_id, card in pairs:
        if product_id in first:
            link, asset = first[product_id]
            card.image = image_out(asset, link.alt_override or asset.alt_text or card.name)


async def load_public_documents(db: AsyncSession, category_id: int) -> list[DocumentPublic]:
    rows = (
        await db.execute(
            select(CategoryDocument, MediaAsset)
            .join(MediaAsset, MediaAsset.id == CategoryDocument.asset_id)
            .where(CategoryDocument.category_id == category_id)
            .order_by(CategoryDocument.sort_order, CategoryDocument.id)
        )
    ).all()
    return [
        DocumentPublic(
            title=doc.title,
            doc_type=doc.doc_type,
            access=doc.access,
            # An "on request" document is listed, but its link is never exposed.
            url=storage.url(asset.storage_key) if doc.access == "public" else None,
        )
        for doc, asset in rows
    ]