from __future__ import annotations

from typing import get_args

from sqlalchemy import text

from api.db import async_session_factory, engine
from api.models import MediaAsset
from api.models.homepage_section import SECTION_KEYS
from api.schemas.homepage import SectionKey

PUBLIC = "/api/v1/homepage"
ADMIN = "/api/v1/admin/homepage"


def section(body, key):
    return next((s for s in body["sections"] if s["key"] == key), None)


async def make_asset(kind="image") -> int:
    async with async_session_factory() as session:
        asset = MediaAsset(
            storage_key=f"test/{kind}.webp", original_filename=f"{kind}.webp",
            mime_type="image/webp", size_bytes=1000, kind=kind, width=1600, height=900,
            alt_text="Hero", variants={
                "thumb": "test/t.webp", "medium": "test/m.webp", "large": "test/l.webp"
            } if kind == "image" else {},
        )
        session.add(asset)
        await session.commit()
        return asset.id


async def make_product(admin_client, name, *, featured, status="published"):
    category = (
        await admin_client.post("/api/v1/admin/categories", json={"name": f"Cat {name}"})
    ).json()
    response = await admin_client.post(
        "/api/v1/admin/products",
        json={
            "name": name,
            "category_id": category["id"],
            "status": status,
            "is_featured": featured,
            "summary": f"Summary for {name}",
        },
    )
    assert response.status_code == 201, response.text


# ------------------------------------------------------------------ keys


def test_schema_keys_match_model_keys():
    assert get_args(SectionKey) == SECTION_KEYS


# ------------------------------------------------------------------ public


async def test_public_homepage_creates_sections_and_caches(client):
    response = await client.get(PUBLIC)
    assert response.status_code == 200
    assert response.headers["cache-control"] == "public, max-age=60"
    keys = [s["key"] for s in response.json()["sections"]]
    # Featured categories, products and industries are empty, so they are left out.
    assert keys == ["hero", "why_choose_us", "inquiry_cta"]
    async with engine.begin() as conn:
        count = (await conn.execute(text("SELECT count(*) FROM homepage_sections"))).scalar_one()
    assert count == len(SECTION_KEYS)


async def test_featured_products_section_appears_with_published_featured_only(admin_client):
    await make_product(admin_client, "Shown", featured=True)
    await make_product(admin_client, "Not featured", featured=False)
    await make_product(admin_client, "Draft", featured=True, status="draft")
    body = (await admin_client.get(PUBLIC)).json()
    names = [p["name"] for p in section(body, "featured_products")["products"]]
    assert names == ["Shown"]


async def test_featured_categories_only_published_and_featured(admin_client):
    url = "/api/v1/admin/categories"
    await admin_client.post(url, json={"name": "Shown", "status": "published", "is_featured": True})
    await admin_client.post(url, json={"name": "Plain", "status": "published"})
    await admin_client.post(url, json={"name": "Draft", "is_featured": True})
    body = (await admin_client.get(PUBLIC)).json()
    names = [c["name"] for c in section(body, "featured_categories")["categories"]]
    assert names == ["Shown"]


async def test_hidden_section_is_not_public(admin_client):
    await admin_client.patch(f"{ADMIN}/inquiry_cta", json={"is_visible": False})
    body = (await admin_client.get(PUBLIC)).json()
    assert section(body, "inquiry_cta") is None


# ------------------------------------------------------------------ access control


async def test_admin_endpoints_require_login(client):
    assert (await client.get(ADMIN)).status_code == 401
    assert (await client.patch(f"{ADMIN}/hero", json={"heading": "x"})).status_code == 401
    assert (await client.put(f"{ADMIN}/order", json={"keys": list(SECTION_KEYS)})).status_code == 401


async def test_editor_can_edit_homepage(client, make_user, login):
    await make_user(email="editor@example.com", role="editor")
    await login("editor@example.com")
    response = await client.patch(f"{ADMIN}/hero", json={"heading": "Editor heading"})
    assert response.status_code == 200
    assert response.json()["heading"] == "Editor heading"


# ------------------------------------------------------------------ updating


async def test_admin_list_is_in_display_order(admin_client):
    body = (await admin_client.get(ADMIN)).json()
    assert [s["key"] for s in body] == list(SECTION_KEYS)


async def test_patch_changes_only_the_fields_sent(admin_client):
    await admin_client.get(ADMIN)
    before = {s["key"]: s for s in (await admin_client.get(ADMIN)).json()}["hero"]
    response = await admin_client.patch(f"{ADMIN}/hero", json={"heading": "New heading"})
    body = response.json()
    assert body["heading"] == "New heading"
    assert body["subheading"] == before["subheading"]
    assert body["cta_url"] == before["cta_url"]


async def test_patch_writes_audit_entry(admin_client):
    await admin_client.patch(f"{ADMIN}/hero", json={"heading": "Audited heading"})
    async with engine.begin() as conn:
        rows = (await conn.execute(text("SELECT * FROM audit_logs"))).mappings().all()
    assert len(rows) == 1
    assert "homepage_section" in rows[0].values()


async def test_unknown_section_key_is_rejected(admin_client):
    assert (await admin_client.patch(f"{ADMIN}/nope", json={"heading": "x"})).status_code == 422


async def test_invalid_payloads_are_rejected(admin_client):
    for payload in [
        {"cta_url": "javascript:alert(1)"},
        {"heading": "x" * 201},
        {"is_visible": None},
        {"unknown": 1},
    ]:
        response = await admin_client.patch(f"{ADMIN}/hero", json=payload)
        assert response.status_code == 422, payload


# ------------------------------------------------------------------ hero image


async def test_hero_image_appears_publicly(admin_client):
    asset_id = await make_asset()
    response = await admin_client.patch(f"{ADMIN}/hero", json={"image_id": asset_id})
    assert response.status_code == 200
    assert response.json()["image"]["alt"] == "Hero"
    hero = section((await admin_client.get(PUBLIC)).json(), "hero")
    assert hero["image"]["large_url"].endswith("test/l.webp")


async def test_hero_image_must_be_an_existing_image(admin_client):
    document_id = await make_asset(kind="document")
    for image_id in (document_id, 999999):
        response = await admin_client.patch(f"{ADMIN}/hero", json={"image_id": image_id})
        assert response.status_code == 422


async def test_only_hero_can_have_an_image(admin_client):
    asset_id = await make_asset()
    response = await admin_client.patch(f"{ADMIN}/industries", json={"image_id": asset_id})
    assert response.status_code == 422


async def test_deleting_the_media_asset_clears_the_hero_image(admin_client):
    asset_id = await make_asset()
    await admin_client.patch(f"{ADMIN}/hero", json={"image_id": asset_id})
    async with engine.begin() as conn:
        await conn.execute(text("DELETE FROM media_assets WHERE id = :id"), {"id": asset_id})
    hero = section((await admin_client.get(PUBLIC)).json(), "hero")
    assert hero["image"] is None


# ------------------------------------------------------------------ why choose us


async def test_why_choose_us_items_can_be_replaced(admin_client):
    items = [{"title": "Fast delivery", "text": "Orders ship quickly.", "icon": "truck"}]
    response = await admin_client.patch(f"{ADMIN}/why_choose_us", json={"items": items})
    assert response.status_code == 200
    public = section((await admin_client.get(PUBLIC)).json(), "why_choose_us")
    assert [i["title"] for i in public["items"]] == ["Fast delivery"]


async def test_items_are_validated_and_limited_to_why_choose_us(admin_client):
    ok = {"title": "A", "text": "B"}
    assert (
        await admin_client.patch(f"{ADMIN}/hero", json={"items": [ok]})
    ).status_code == 422
    assert (
        await admin_client.patch(f"{ADMIN}/why_choose_us", json={"items": [ok] * 9})
    ).status_code == 422
    assert (
        await admin_client.patch(f"{ADMIN}/why_choose_us", json={"items": [{"title": ""}]})
    ).status_code == 422


async def test_emptying_items_hides_the_section_publicly(admin_client):
    await admin_client.patch(f"{ADMIN}/why_choose_us", json={"items": []})
    assert section((await admin_client.get(PUBLIC)).json(), "why_choose_us") is None


# ------------------------------------------------------------------ reordering


async def test_sections_can_be_reordered(admin_client):
    new_order = list(reversed(SECTION_KEYS))
    response = await admin_client.put(f"{ADMIN}/order", json={"keys": new_order})
    assert response.status_code == 200
    assert [s["key"] for s in response.json()] == new_order
    public_keys = [s["key"] for s in (await admin_client.get(PUBLIC)).json()["sections"]]
    assert public_keys == ["inquiry_cta", "why_choose_us", "hero"]


async def test_reorder_must_list_every_section_once(admin_client):
    too_few = {"keys": list(SECTION_KEYS)[:-1]}
    duplicated = {"keys": [*SECTION_KEYS[:-1], SECTION_KEYS[0]]}
    for payload in (too_few, duplicated, {"keys": ["hero", "bogus"]}):
        assert (await admin_client.put(f"{ADMIN}/order", json=payload)).status_code == 422