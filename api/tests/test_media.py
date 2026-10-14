import io

from PIL import Image
from sqlalchemy import text

from api.config import settings
from api.db import engine
from api.services.storage import storage

MEDIA = "/api/v1/admin/media"
PDF = b"%PDF-1.4\n1 0 obj\n<< >>\nendobj\ntrailer\n<< >>\n%%EOF\n"


def png_bytes(width=2000, height=1000, color="red") -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, "PNG")
    return buffer.getvalue()


async def upload(client, content: bytes, name="photo.png", alt=None):
    files = {"file": (name, content, "application/octet-stream")}
    return await client.post(MEDIA, files=files, data={"alt_text": alt} if alt else None)


async def scalar(sql: str, **params):
    async with engine.connect() as conn:
        return (await conn.execute(text(sql), params)).scalar_one()


async def lookup(table: str, slug: str) -> int:
    return await scalar(f"SELECT id FROM {table} WHERE slug = :s", s=slug)


async def count_assets() -> int:
    return await scalar("SELECT count(*) FROM media_assets")


# ------------------------------------------------------------------ uploads


async def test_image_upload_creates_three_webp_sizes(admin_client):
    response = await upload(admin_client, png_bytes(2000, 1000), alt="A red test image")
    assert response.status_code == 201, response.text
    body = response.json()
    assert (body["kind"], body["width"], body["height"]) == ("image", 2000, 1000)
    assert body["alt_text"] == "A red test image"

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT variants->>'thumb' AS thumb, variants->>'medium' AS medium, "
                     "variants->>'large' AS large FROM media_assets")
            )
        ).one()
    for key, width in ((row.thumb, 320), (row.medium, 800), (row.large, 1600)):
        with Image.open(storage.root / key) as image:
            assert image.format == "WEBP"
            assert image.width == width


async def test_small_images_are_never_upscaled(admin_client):
    assert (await upload(admin_client, png_bytes(200, 100))).status_code == 201
    async with engine.connect() as conn:
        key = (await conn.execute(text("SELECT variants->>'large' FROM media_assets"))).scalar_one()
    with Image.open(storage.root / key) as image:
        assert image.width == 200


async def test_invalid_uploads_are_rejected_and_nothing_is_stored(admin_client):
    gif = io.BytesIO()
    Image.new("P", (10, 10)).save(gif, "GIF")
    bomb = io.BytesIO()
    Image.new("1", (9000, 9000)).save(bomb, "PNG")  # tiny file, 81 million pixels

    cases = {
        "not an image": (b"just some text", 422),
        "gif": (gif.getvalue(), 422),
        "pixel bomb": (bomb.getvalue(), 422),
        "too large": (b"x" * (settings.max_image_bytes + 1), 413),
    }
    for label, (content, expected) in cases.items():
        response = await upload(admin_client, content)
        assert response.status_code == expected, label
    assert await count_assets() == 0


async def test_pdf_upload_and_broken_pdfs(admin_client):
    response = await upload(admin_client, PDF, name="rates.pdf")
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["kind"] == "document"
    assert body["mime_type"] == "application/pdf"
    assert body["url"].startswith("/media/documents/")

    assert (await upload(admin_client, b"%PDF-1.4 truncated", name="x.pdf")).status_code == 422
    assert (await upload(admin_client, b"plain text", name="x.pdf")).status_code == 422


async def test_filenames_are_sanitised_and_never_used_in_paths(admin_client):
    response = await upload(admin_client, PDF, name="../../evil.pdf")
    assert response.status_code == 201
    body = response.json()
    assert body["original_filename"] == "evil.pdf"
    assert "evil" not in body["url"]


async def test_alt_text_can_be_edited_and_files_listed_by_kind(admin_client):
    image = (await upload(admin_client, png_bytes(400, 300), name="busbar.png")).json()
    await upload(admin_client, PDF, name="rates.pdf")

    patched = await admin_client.patch(f"{MEDIA}/{image['id']}", json={"alt_text": "A copper bus bar"})
    assert patched.status_code == 200
    assert patched.json()["alt_text"] == "A copper bus bar"

    assert (await admin_client.get(MEDIA)).json()["total"] == 2
    assert (await admin_client.get(MEDIA, params={"kind": "document"})).json()["total"] == 1
    assert (await admin_client.get(MEDIA, params={"q": "busbar"})).json()["total"] == 1


async def test_only_staff_can_upload(client, make_user, login):
    assert (await upload(client, PDF, name="x.pdf")).status_code == 401
    await make_user(email="sales@example.com", role="sales")
    await login(email="sales@example.com")
    assert (await upload(client, PDF, name="x.pdf")).status_code == 403


# ------------------------------------------------------------------ deleting


async def test_unused_files_can_be_deleted_and_disappear_from_disk(admin_client):
    asset = (await upload(admin_client, png_bytes(900, 600))).json()
    async with engine.connect() as conn:
        key = (await conn.execute(text("SELECT variants->>'thumb' FROM media_assets"))).scalar_one()
    assert (storage.root / key).exists()

    assert (await admin_client.delete(f"{MEDIA}/{asset['id']}")).status_code == 204
    assert not (storage.root / key).exists()
    assert await count_assets() == 0


async def test_files_in_use_cannot_be_deleted(admin_client, seeded):
    product_id = await lookup("products", "copper-bus-bar")
    asset = (await upload(admin_client, png_bytes(900, 600))).json()
    await admin_client.put(
        f"/api/v1/admin/products/{product_id}/images", json={"images": [{"asset_id": asset["id"]}]}
    )
    response = await admin_client.delete(f"{MEDIA}/{asset['id']}")
    assert response.status_code == 409
    assert "in use" in response.json()["detail"]


# ------------------------------------------------------------------ product galleries


async def test_gallery_order_primary_and_public_output(admin_client, seeded):
    product_id = await lookup("products", "copper-bus-bar")
    first = (await upload(admin_client, png_bytes(900, 600))).json()["id"]
    second = (await upload(admin_client, png_bytes(900, 600, "blue"))).json()["id"]

    response = await admin_client.put(
        f"/api/v1/admin/products/{product_id}/images",
        json={"images": [
            {"asset_id": first},
            {"asset_id": second, "is_primary": True, "alt_override": "Blue view"},
        ]},
    )
    assert response.status_code == 200, response.text
    items = response.json()
    assert [i["asset_id"] for i in items] == [first, second]  # the order that was sent
    assert [i["is_primary"] for i in items] == [False, True]

    public = (await admin_client.get("/api/v1/products/copper-bus-bar")).json()
    assert [img["alt"] for img in public["images"]] == ["Blue view", "Copper Bus Bar"]  # primary first

    card = (await admin_client.get("/api/v1/products", params={"category": "copper-bus-bars"})).json()
    assert card["items"][0]["image"]["alt"] == "Blue view"

    thumb = await admin_client.get(public["images"][0]["thumb_url"])
    assert thumb.status_code == 200
    assert thumb.headers["content-type"] == "image/webp"


async def test_gallery_validation(admin_client, seeded):
    product_id = await lookup("products", "copper-bus-bar")
    url = f"/api/v1/admin/products/{product_id}/images"
    image = (await upload(admin_client, png_bytes(900, 600))).json()["id"]
    other = (await upload(admin_client, png_bytes(900, 600, "green"))).json()["id"]
    document = (await upload(admin_client, PDF, name="x.pdf")).json()["id"]

    bad_bodies = {
        "unknown file": {"images": [{"asset_id": 99999}]},
        "a pdf as an image": {"images": [{"asset_id": document}]},
        "duplicate": {"images": [{"asset_id": image}, {"asset_id": image}]},
        "two primaries": {"images": [
            {"asset_id": image, "is_primary": True}, {"asset_id": other, "is_primary": True}]},
    }
    for label, body in bad_bodies.items():
        assert (await admin_client.put(url, json=body)).status_code == 422, label


async def test_the_first_image_is_primary_when_none_is_chosen(admin_client, seeded):
    product_id = await lookup("products", "copper-bus-bar")
    image = (await upload(admin_client, png_bytes(900, 600))).json()["id"]
    response = await admin_client.put(
        f"/api/v1/admin/products/{product_id}/images", json={"images": [{"asset_id": image}]}
    )
    assert response.json()[0]["is_primary"] is True


# ------------------------------------------------------------------ category documents


async def test_category_documents_public_and_on_request(admin_client, seeded):
    category_id = await lookup("categories", "miniature-circuit-breakers")
    rates = (await upload(admin_client, PDF, name="rates.pdf")).json()["id"]
    sheet = (await upload(admin_client, PDF, name="sheet.pdf")).json()["id"]

    response = await admin_client.put(
        f"/api/v1/admin/categories/{category_id}/documents",
        json={"documents": [
            {"asset_id": rates, "title": "Rate list 2025", "doc_type": "rate_list", "access": "public"},
            {"asset_id": sheet, "title": "Datasheet", "doc_type": "datasheet", "access": "on_request"},
        ]},
    )
    assert response.status_code == 200, response.text

    public = (await admin_client.get("/api/v1/categories/miniature-circuit-breakers")).json()
    documents = public["documents"]
    assert [d["title"] for d in documents] == ["Rate list 2025", "Datasheet"]
    assert documents[0]["url"].startswith("/media/documents/")
    assert documents[1]["access"] == "on_request"
    assert documents[1]["url"] is None  # listed, but the link is never exposed

    pdf = await admin_client.get(documents[0]["url"])
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"


async def test_category_document_validation(admin_client, seeded):
    category_id = await lookup("categories", "miniature-circuit-breakers")
    url = f"/api/v1/admin/categories/{category_id}/documents"
    image = (await upload(admin_client, png_bytes(900, 600))).json()["id"]
    pdf = (await upload(admin_client, PDF, name="x.pdf")).json()["id"]

    bad_bodies = {
        "an image as a document": {"documents": [{"asset_id": image, "title": "Photo"}]},
        "bad type": {"documents": [{"asset_id": pdf, "title": "X", "doc_type": "nonsense"}]},
        "empty title": {"documents": [{"asset_id": pdf, "title": ""}]},
    }
    for label, body in bad_bodies.items():
        assert (await admin_client.put(url, json=body)).status_code == 422, label