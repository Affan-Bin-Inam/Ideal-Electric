from sqlalchemy import text

from api.db import engine

CATEGORIES = "/api/v1/admin/categories"


async def create(client, name="Test Category", **extra):
    return await client.post(CATEGORIES, json={"name": name, **extra})


async def audit_rows():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT action, actor_email, entity_type, summary FROM audit_logs ORDER BY id")
        )
        return result.all()


async def add_product(category_id: int, slug: str = "p") -> None:
    async with engine.begin() as conn:
        await conn.execute(
            text("INSERT INTO products (category_id, name, slug) VALUES (:c, 'P', :s)"),
            {"c": category_id, "s": slug},
        )


# ------------------------------------------------------------------ access


async def test_requires_authentication(client):
    assert (await client.get(CATEGORIES)).status_code == 401


async def test_sales_role_is_forbidden(client, make_user, login):
    await make_user(email="sales@example.com", role="sales")
    await login(email="sales@example.com")
    assert (await client.get(CATEGORIES)).status_code == 403
    assert (await create(client)).status_code == 403


async def test_untrusted_origin_is_rejected(admin_client):
    response = await admin_client.post(
        CATEGORIES, json={"name": "Nope"}, headers={"Origin": "https://evil.example"}
    )
    assert response.status_code == 403


# ------------------------------------------------------------------ create


async def test_create_generates_slug_and_writes_audit_entry(admin_client):
    response = await create(admin_client, "Power Tools & More")
    assert response.status_code == 201
    body = response.json()
    assert body["slug"] == "power-tools-more"
    assert body["status"] == "draft"
    assert body["product_count"] == 0

    rows = await audit_rows()
    assert len(rows) == 1
    assert rows[0].action == "create"
    assert rows[0].actor_email == "admin@example.com"
    assert rows[0].entity_type == "category"


async def test_duplicate_names_are_rejected_even_at_top_level(admin_client):
    assert (await create(admin_client, "Lighting")).status_code == 201
    assert (await create(admin_client, "lighting")).status_code == 409


async def test_same_name_under_different_parents_gets_a_unique_slug(admin_client):
    alpha = (await create(admin_client, "Alpha")).json()
    beta = (await create(admin_client, "Beta")).json()
    first = (await create(admin_client, "Accessories", parent_id=alpha["id"])).json()
    second = (await create(admin_client, "Accessories", parent_id=beta["id"])).json()
    assert first["slug"] == "accessories"
    assert second["slug"] == "accessories-2"


async def test_explicit_slug_conflict_and_bad_slug(admin_client):
    await create(admin_client, "One", slug="same")
    assert (await create(admin_client, "Two", slug="same")).status_code == 409
    assert (await create(admin_client, "Three", slug="Not Valid")).status_code == 422


# ------------------------------------------------------------------ hierarchy rules


async def test_nesting_is_limited_to_two_levels(admin_client):
    top = (await create(admin_client, "Top")).json()
    child = (await create(admin_client, "Child", parent_id=top["id"])).json()
    assert (await create(admin_client, "Grandchild", parent_id=child["id"])).status_code == 422


async def test_category_cannot_be_its_own_parent(admin_client):
    top = (await create(admin_client, "Top")).json()
    response = await admin_client.patch(f"{CATEGORIES}/{top['id']}", json={"parent_id": top["id"]})
    assert response.status_code == 422


async def test_category_with_children_cannot_become_a_child(admin_client):
    first = await create(admin_client, "Group A")
    second = await create(admin_client, "Group B")
    assert first.status_code == 201 and second.status_code == 201
    a, b = first.json(), second.json()
    child = await create(admin_client, "Group A child", parent_id=a["id"])
    assert child.status_code == 201
    response = await admin_client.patch(f"{CATEGORIES}/{a['id']}", json={"parent_id": b["id"]})
    assert response.status_code == 422


# ------------------------------------------------------------------ update


async def test_update_records_only_what_changed_and_keeps_the_slug(admin_client):
    created = (await create(admin_client, "Old Name", description="same")).json()
    response = await admin_client.patch(
        f"{CATEGORIES}/{created['id']}", json={"name": "New Name", "description": "same"}
    )
    assert response.status_code == 200
    assert response.json()["name"] == "New Name"
    assert response.json()["slug"] == created["slug"]

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text(
                    "SELECT changes->'name'->>'to' AS new_name, "
                    "(changes->>'description') IS NOT NULL AS has_description "
                    "FROM audit_logs WHERE action = 'update'"
                )
            )
        ).one()
    assert row.new_name == "New Name"
    assert row.has_description is False


async def test_patch_with_no_real_change_writes_no_audit_entry(admin_client):
    created = (await create(admin_client, "Steady")).json()
    response = await admin_client.patch(f"{CATEGORIES}/{created['id']}", json={"name": "Steady"})
    assert response.status_code == 200
    assert len(await audit_rows()) == 1  # only the create


async def test_required_fields_cannot_be_set_to_null(admin_client):
    created = (await create(admin_client, "Needs a name")).json()
    response = await admin_client.patch(f"{CATEGORIES}/{created['id']}", json={"name": None})
    assert response.status_code == 422


async def test_list_includes_drafts_and_product_counts(admin_client):
    created = (await create(admin_client, "Counted")).json()
    await add_product(created["id"])
    listing = (await admin_client.get(CATEGORIES)).json()
    row = next(c for c in listing if c["id"] == created["id"])
    assert row["status"] == "draft"
    assert row["product_count"] == 1


# ------------------------------------------------------------------ delete


async def test_delete_is_blocked_by_subcategories(admin_client):
    top = (await create(admin_client, "Parent")).json()
    await create(admin_client, "Child", parent_id=top["id"])
    response = await admin_client.delete(f"{CATEGORIES}/{top['id']}")
    assert response.status_code == 409
    assert "subcategories" in response.json()["detail"]


async def test_delete_is_blocked_by_products(admin_client):
    created = (await create(admin_client, "Busy")).json()
    await add_product(created["id"])
    response = await admin_client.delete(f"{CATEGORIES}/{created['id']}")
    assert response.status_code == 409
    assert "products" in response.json()["detail"]


async def test_delete_an_empty_category(admin_client):
    created = (await create(admin_client, "Disposable")).json()
    assert (await admin_client.delete(f"{CATEGORIES}/{created['id']}")).status_code == 204
    assert (await admin_client.get(f"{CATEGORIES}/{created['id']}")).status_code == 404
    assert [r.action for r in await audit_rows()] == ["create", "delete"]