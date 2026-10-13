import pytest_asyncio
from sqlalchemy import text

from api.db import async_session_factory, engine
from api.seed import seed

PRODUCTS = "/api/v1/admin/products"


@pytest_asyncio.fixture
async def seeded():
    async with engine.begin() as conn:
        await conn.execute(
            text("TRUNCATE brands, categories, industries, attribute_definitions, products "
                 "RESTART IDENTITY CASCADE")
        )
    async with async_session_factory() as session:
        async with session.begin():
            await seed(session)


async def scalar(sql: str, **params):
    async with engine.connect() as conn:
        return (await conn.execute(text(sql), params)).scalar_one()


async def lookup(table: str, slug: str) -> int:
    return await scalar(f"SELECT id FROM {table} WHERE slug = :s", s=slug)


async def audit_rows():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT action, entity_type, summary FROM audit_logs ORDER BY id")
        )
        return result.all()


async def payload(**overrides):
    body = {
        "name": "Yachica Test Selector",
        "category_id": await lookup("categories", "selector-switches"),
        "series_id": await lookup("series", "yachica"),
        "summary": "A test selector switch.",
        "features": ["3 pole", "Ratings: 32, 50 A"],
        "applications": ["Testing"],
        "attributes": {
            "poles": "3", "current_ratings": ["32", "50"], "switch_positions": "0-1-2-3-4",
        },
    }
    body.update(overrides)
    return body


async def create_one(client, **overrides) -> dict:
    response = await client.post(PRODUCTS, json=await payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


async def test_sales_cannot_use_the_product_admin(client, make_user, login):
    await make_user(email="sales@example.com", role="sales")
    await login(email="sales@example.com")
    assert (await client.get(PRODUCTS)).status_code == 403


async def test_create_product_with_everything(admin_client, seeded):
    industrial = await lookup("industries", "industrial")
    sibling = await lookup("products", "yachica-selector-switch-2-pole")
    brand = await lookup("brands", "ideal-electric")

    body = await create_one(admin_client, industry_ids=[industrial], related_ids=[sibling])

    assert body["slug"] == "yachica-test-selector"
    assert body["brand_id"] == brand  # the series decided the brand
    assert body["status"] == "draft"
    assert body["features"] == ["3 pole", "Ratings: 32, 50 A"]
    assert body["applications"] == ["Testing"]
    assert body["attributes"] == {
        "poles": "3", "current_ratings": ["32", "50"], "switch_positions": "0-1-2-3-4",
    }
    assert body["industry_ids"] == [industrial]
    assert body["related_ids"] == [sibling]

    rows = await audit_rows()
    assert [(r.action, r.entity_type) for r in rows] == [("create", "product")]


async def test_attributes_must_belong_to_the_products_category(admin_client, seeded):
    response = await admin_client.post(
        PRODUCTS, json=await payload(attributes={"wattage": ["5"]})
    )
    assert response.status_code == 422
    assert "not an attribute of this category" in response.json()["detail"]


async def test_attribute_values_must_be_valid_options(admin_client, seeded):
    for attributes in ({"poles": "9"}, {"current_ratings": ["33"]}, {"current_ratings": []}):
        response = await admin_client.post(PRODUCTS, json=await payload(attributes=attributes))
        assert response.status_code == 422, attributes


async def test_series_must_belong_to_the_same_brand(admin_client, seeded):
    async with engine.begin() as conn:
        other = (
            await conn.execute(
                text("INSERT INTO brands (name, slug) VALUES ('Other Co', 'other-co') RETURNING id")
            )
        ).scalar_one()
    response = await admin_client.post(PRODUCTS, json=await payload(brand_id=other))
    assert response.status_code == 422
    assert "different brand" in response.json()["detail"]


async def test_publishing_requires_a_summary(admin_client, seeded):
    response = await admin_client.post(
        PRODUCTS, json=await payload(status="published", summary=None)
    )
    assert response.status_code == 422


async def test_unknown_references_are_rejected(admin_client, seeded):
    for overrides in (
        {"category_id": 99999}, {"series_id": 99999},
        {"industry_ids": [99999]}, {"related_ids": [99999]},
    ):
        response = await admin_client.post(PRODUCTS, json=await payload(**overrides))
        assert response.status_code == 422, overrides

    created = await create_one(admin_client)
    own = await admin_client.patch(f"{PRODUCTS}/{created['id']}", json={"related_ids": [created["id"]]})
    assert own.status_code == 422


async def test_duplicate_names_are_rejected(admin_client, seeded):
    response = await admin_client.post(PRODUCTS, json=await payload(name="libra gold mcb, 1 pole"))
    assert response.status_code == 409


async def test_patch_updates_scalars_and_nested_data_and_audits_each_change(admin_client, seeded):
    created = await create_one(admin_client)
    response = await admin_client.patch(
        f"{PRODUCTS}/{created['id']}",
        json={
            "summary": "Updated summary.",
            "features": ["Only feature"],
            "attributes": {
                "poles": "4", "current_ratings": ["75"], "switch_positions": "0-1-2-3-4",
            },
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["summary"] == "Updated summary."
    assert body["features"] == ["Only feature"]
    assert body["attributes"]["poles"] == "4"
    assert body["slug"] == created["slug"]  # renaming and editing never changes the URL

    async with engine.connect() as conn:
        keys = (
            await conn.execute(
                text(
                    "SELECT array_agg(k ORDER BY k) FROM audit_logs a, "
                    "jsonb_object_keys(a.changes) k WHERE a.action = 'update'"
                )
            )
        ).scalar_one()
    assert keys == ["attribute:current_ratings", "attribute:poles", "features", "summary"]


async def test_omitted_lists_are_untouched_and_empty_lists_clear(admin_client, seeded):
    created = await create_one(admin_client)
    url = f"{PRODUCTS}/{created['id']}"

    await admin_client.patch(url, json={"summary": "A different summary."})
    after = (await admin_client.get(url)).json()
    assert after["features"] == created["features"]
    assert after["attributes"] == created["attributes"]

    cleared = (await admin_client.patch(url, json={"features": []})).json()
    assert cleared["features"] == []
    assert cleared["applications"] == created["applications"]


async def test_moving_category_requires_valid_attributes(admin_client, seeded):
    created = await create_one(admin_client)
    url = f"{PRODUCTS}/{created['id']}"
    downlights = await lookup("categories", "led-downlights")

    rejected = await admin_client.patch(url, json={"category_id": downlights})
    assert rejected.status_code == 422  # poles and ratings don't apply to downlights

    moved = await admin_client.patch(
        url, json={"category_id": downlights, "attributes": {"wattage": ["5"]}}
    )
    assert moved.status_code == 200, moved.text
    assert moved.json()["attributes"] == {"wattage": ["5"]}


async def test_listing_and_filters(admin_client, seeded):
    everything = (await admin_client.get(PRODUCTS, params={"page_size": 100})).json()
    assert everything["total"] == 51

    selectors = await lookup("categories", "selector-switches")
    assert (await admin_client.get(PRODUCTS, params={"category_id": selectors})).json()["total"] == 7
    assert (await admin_client.get(PRODUCTS, params={"q": "cesco"})).json()["total"] == 6
    assert (await admin_client.get(PRODUCTS, params={"status": "draft"})).json()["total"] == 0

    await create_one(admin_client)
    assert (await admin_client.get(PRODUCTS, params={"status": "draft"})).json()["total"] == 1


async def test_drafts_are_invisible_until_published(admin_client, seeded):
    created = await create_one(admin_client)
    public = f"/api/v1/products/{created['slug']}"
    assert (await admin_client.get(public)).status_code == 404

    published = await admin_client.patch(f"{PRODUCTS}/{created['id']}", json={"status": "published"})
    assert published.status_code == 200, published.text
    assert (await admin_client.get(public)).status_code == 200


async def test_editors_cannot_delete_products(client, make_user, login, seeded):
    await make_user(email="editor@example.com", role="editor")
    await login(email="editor@example.com")
    product_id = await lookup("products", "copper-bus-bar")
    assert (await client.delete(f"{PRODUCTS}/{product_id}")).status_code == 403


async def test_admin_delete_removes_children_too(admin_client, seeded):
    sibling = await lookup("products", "yachica-selector-switch-2-pole")
    created = await create_one(admin_client, related_ids=[sibling])
    assert (await admin_client.delete(f"{PRODUCTS}/{created['id']}")).status_code == 204

    pid = created["id"]
    assert await scalar("SELECT count(*) FROM product_highlights WHERE product_id = :p", p=pid) == 0
    assert await scalar(
        "SELECT count(*) FROM product_attribute_values WHERE product_id = :p", p=pid) == 0
    assert await scalar(
        "SELECT count(*) FROM related_products WHERE product_id = :p OR related_product_id = :p",
        p=pid) == 0
    assert [r.action for r in await audit_rows()] == ["create", "delete"]


async def test_patch_without_real_changes_writes_no_audit_entry(admin_client, seeded):
    created = await create_one(admin_client)
    response = await admin_client.patch(
        f"{PRODUCTS}/{created['id']}",
        json={"summary": created["summary"], "features": created["features"]},
    )
    assert response.status_code == 200
    assert [r.action for r in await audit_rows()] == ["create"]