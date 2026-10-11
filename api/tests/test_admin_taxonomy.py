import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from api.db import engine

SERIES = "/api/v1/admin/series"
INDUSTRIES = "/api/v1/admin/industries"
BRANDS = "/api/v1/admin/brands"


async def insert_returning_id(sql: str, params: dict) -> int:
    async with engine.begin() as conn:
        return (await conn.execute(text(sql), params)).scalar_one()


async def add_brand(name="Ideal Electric", slug="ideal-electric") -> int:
    return await insert_returning_id(
        "INSERT INTO brands (name, slug) VALUES (:n, :s) RETURNING id", {"n": name, "s": slug}
    )


async def add_category() -> int:
    return await insert_returning_id(
        "INSERT INTO categories (name, slug) VALUES ('Cat', 'cat') RETURNING id", {}
    )


async def add_product(category_id: int, brand_id=None, series_id=None) -> int:
    return await insert_returning_id(
        "INSERT INTO products (category_id, brand_id, series_id, name, slug) "
        "VALUES (:c, :b, :s, 'P', 'p') RETURNING id",
        {"c": category_id, "b": brand_id, "s": series_id},
    )


async def create_series(client, brand_id: int, name: str):
    return await client.post(SERIES, json={"brand_id": brand_id, "name": name})


# ------------------------------------------------------------------ series


async def test_series_requires_staff_role(client, make_user, login):
    await make_user(email="sales@example.com", role="sales")
    await login(email="sales@example.com")
    assert (await client.get(SERIES)).status_code == 403


async def test_create_series_and_reject_unknown_brand(admin_client):
    brand_id = await add_brand()
    response = await create_series(admin_client, brand_id, "Libra Gold")
    assert response.status_code == 201
    assert response.json()["slug"] == "libra-gold"
    assert (await create_series(admin_client, 9999, "Orphan")).status_code == 422


async def test_series_names_are_unique_per_brand_only(admin_client):
    first_brand = await add_brand("Brand One", "one")
    second_brand = await add_brand("Brand Two", "two")
    assert (await create_series(admin_client, first_brand, "Gold")).status_code == 201
    assert (await create_series(admin_client, first_brand, "gold")).status_code == 409
    other = await create_series(admin_client, second_brand, "Gold")
    assert other.status_code == 201
    assert other.json()["slug"] == "gold-2"


async def test_series_cannot_be_moved_to_another_brand(admin_client):
    first_brand = await add_brand("Brand One", "one")
    second_brand = await add_brand("Brand Two", "two")
    series = (await create_series(admin_client, first_brand, "Gold")).json()
    response = await admin_client.patch(f"{SERIES}/{series['id']}", json={"brand_id": second_brand})
    assert response.status_code == 422


async def test_series_in_use_cannot_be_deleted(admin_client):
    brand_id = await add_brand()
    category_id = await add_category()
    series = (await create_series(admin_client, brand_id, "Gold")).json()
    await add_product(category_id, brand_id, series["id"])
    response = await admin_client.delete(f"{SERIES}/{series['id']}")
    assert response.status_code == 409
    assert "archive" in response.json()["detail"]


async def test_database_itself_refuses_to_delete_a_series_in_use(admin_client):
    brand_id = await add_brand()
    category_id = await add_category()
    series = (await create_series(admin_client, brand_id, "Gold")).json()
    await add_product(category_id, brand_id, series["id"])
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(text("DELETE FROM series WHERE id = :id"), {"id": series["id"]})


async def test_unused_series_can_be_deleted(admin_client):
    brand_id = await add_brand()
    series = (await create_series(admin_client, brand_id, "Gold")).json()
    assert (await admin_client.delete(f"{SERIES}/{series['id']}")).status_code == 204
    assert (await admin_client.get(f"{SERIES}/{series['id']}")).status_code == 404


# ------------------------------------------------------------------ industries


async def test_create_industry_with_generated_slug_and_no_duplicates(admin_client):
    response = await admin_client.post(INDUSTRIES, json={"name": "Oil & Gas"})
    assert response.status_code == 201
    assert response.json()["slug"] == "oil-gas"
    assert (await admin_client.post(INDUSTRIES, json={"name": "oil & gas"})).status_code == 409


async def test_industry_in_use_cannot_be_deleted(admin_client):
    industry = (await admin_client.post(INDUSTRIES, json={"name": "Mining"})).json()
    product_id = await add_product(await add_category())
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO product_industries (product_id, industry_id) VALUES (:p, :i)"),
            {"p": product_id, "i": industry["id"]},
        )
    response = await admin_client.delete(f"{INDUSTRIES}/{industry['id']}")
    assert response.status_code == 409


async def test_clearing_the_placeholder_flag_is_audited(admin_client):
    industry_id = await insert_returning_id(
        "INSERT INTO industries (name, slug, is_placeholder) "
        "VALUES ('Retail', 'retail', true) RETURNING id",
        {},
    )
    response = await admin_client.patch(f"{INDUSTRIES}/{industry_id}", json={"is_placeholder": False})
    assert response.status_code == 200
    assert response.json()["is_placeholder"] is False
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT changes->'is_placeholder'->>'from' AS old "
                    "FROM audit_logs WHERE action = 'update'"
                )
            )
        ).one()
    assert row.old == "true"


# ------------------------------------------------------------------ brands


async def test_brand_can_be_edited_but_not_created_or_deleted_here(admin_client):
    brand_id = await add_brand()
    response = await admin_client.patch(f"{BRANDS}/{brand_id}", json={"description": "Importer"})
    assert response.status_code == 200
    assert response.json()["description"] == "Importer"
    assert (await admin_client.post(BRANDS, json={"name": "Another"})).status_code == 405
    assert (await admin_client.delete(f"{BRANDS}/{brand_id}")).status_code == 405