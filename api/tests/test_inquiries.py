import pytest
from sqlalchemy import text

from api.db import engine
from api.main import app
from api.services.turnstile import get_turnstile_verifier

SUBMIT = "/api/v1/inquiries"
INBOX = "/api/v1/admin/inquiries"


def set_captcha(result: bool):
    async def fake(token, remote_ip=None):
        return result

    app.dependency_overrides[get_turnstile_verifier] = lambda: fake


@pytest.fixture(autouse=True)
def captcha():
    set_captcha(True)
    yield
    app.dependency_overrides.pop(get_turnstile_verifier, None)


def inquiry(**overrides):
    body = {"name": "Ali Traders", "phone": "0300 123 4567", "turnstile_token": "token"}
    body.update(overrides)
    return body


async def count_inquiries() -> int:
    async with engine.connect() as conn:
        return (await conn.execute(text("SELECT count(*) FROM inquiries"))).scalar_one()


async def inquiry_ids() -> list[int]:
    async with engine.connect() as conn:
        rows = await conn.execute(text("SELECT id FROM inquiries ORDER BY id"))
        return [r.id for r in rows]


async def audit_rows():
    async with engine.connect() as conn:
        result = await conn.execute(
            text("SELECT action, entity_type, summary FROM audit_logs ORDER BY id")
        )
        return result.all()


# ------------------------------------------------------------------ public form


async def test_general_inquiry_is_stored_with_a_normalised_phone(client):
    response = await client.post(
        SUBMIT, json=inquiry(phone="+92 300 123-4567", source_page="/products")
    )
    assert response.status_code == 201
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT phone, status, product_id, length(ip_hash) AS hash_length, source_page "
                     "FROM inquiries")
            )
        ).one()
    assert row.phone == "+923001234567"
    assert row.status == "new"
    assert row.product_id is None
    assert row.hash_length == 64  # a hash, not the address
    assert row.source_page == "/products"


async def test_product_inquiry_keeps_a_name_snapshot_and_the_chosen_options(client, seeded):
    response = await client.post(
        SUBMIT,
        json=inquiry(product_slug="libra-gold-mcb-1-pole", selected_options={"current_ratings": ["32"]}),
    )
    assert response.status_code == 201
    async with engine.connect() as conn:
        row = (
            await conn.execute(
                text("SELECT product_id, product_name_snapshot, "
                     "selected_options->'current_ratings'->>0 AS rating FROM inquiries")
            )
        ).one()
    assert row.product_id is not None
    assert row.product_name_snapshot == "Libra Gold MCB, 1 Pole"
    assert row.rating == "32"


async def test_options_must_belong_to_the_product(client, seeded):
    product = "libra-gold-mcb-1-pole"
    for options in ({"current_ratings": ["33"]}, {"poles": ["1"]}, {"nonsense": ["x"]}):
        response = await client.post(
            SUBMIT, json=inquiry(product_slug=product, selected_options=options)
        )
        assert response.status_code == 422, options
    no_product = await client.post(SUBMIT, json=inquiry(selected_options={"current_ratings": ["32"]}))
    assert no_product.status_code == 422
    assert await count_inquiries() == 0


async def test_unknown_product_becomes_a_general_inquiry(client, seeded):
    response = await client.post(SUBMIT, json=inquiry(product_slug="no-such-product"))
    assert response.status_code == 201
    async with engine.connect() as conn:
        product_id = (await conn.execute(text("SELECT product_id FROM inquiries"))).scalar_one()
    assert product_id is None


async def test_form_validation(client):
    for overrides in (
        {"phone": None}, {"phone": "abc"}, {"phone": "12345"},
        {"email": "not-an-email"}, {"name": "A"},
    ):
        body = inquiry()
        body.update(overrides)
        if overrides.get("phone", "") is None:
            del body["phone"]
        response = await client.post(SUBMIT, json=body)
        assert response.status_code == 422, overrides
    assert await count_inquiries() == 0


async def test_honeypot_looks_like_success_but_stores_nothing(client):
    response = await client.post(SUBMIT, json=inquiry(website="http://spam.example"))
    assert response.status_code == 201
    assert await count_inquiries() == 0


async def test_rate_limit_stops_the_sixth_inquiry(client):
    for _ in range(5):
        assert (await client.post(SUBMIT, json=inquiry())).status_code == 201
    assert (await client.post(SUBMIT, json=inquiry())).status_code == 429
    assert await count_inquiries() == 5


async def test_failed_captcha_stores_nothing(client):
    set_captcha(False)
    response = await client.post(SUBMIT, json=inquiry())
    assert response.status_code == 400
    assert await count_inquiries() == 0


# ------------------------------------------------------------------ sales inbox


async def test_inbox_needs_a_staff_login(client, make_user, login):
    assert (await client.get(INBOX)).status_code == 401
    await make_user(email="sales@example.com", role="sales")
    await login(email="sales@example.com")
    assert (await client.get(INBOX)).status_code == 200


async def test_inbox_lists_filters_and_searches(admin_client):
    await admin_client.post(SUBMIT, json=inquiry(name="Ali Traders"))
    await admin_client.post(SUBMIT, json=inquiry(name="Bilal Electric"))
    first, second = await inquiry_ids()

    assert (await admin_client.get(INBOX)).json()["total"] == 2
    await admin_client.patch(f"{INBOX}/{first}", json={"status": "contacted"})
    assert (await admin_client.get(INBOX, params={"status": "new"})).json()["total"] == 1
    found = (await admin_client.get(INBOX, params={"q": "bilal"})).json()
    assert found["total"] == 1 and found["items"][0]["id"] == second


async def test_detail_includes_a_whatsapp_reply_link(admin_client):
    await admin_client.post(SUBMIT, json=inquiry(phone="03001234567"))
    await admin_client.post(SUBMIT, json=inquiry(phone="+923001234567"))
    first, second = await inquiry_ids()
    for inquiry_id in (first, second):
        detail = (await admin_client.get(f"{INBOX}/{inquiry_id}")).json()
        assert detail["whatsapp_url"] == "https://wa.me/923001234567"


async def test_status_and_assignment_changes_are_audited_without_personal_data(admin_client):
    await admin_client.post(SUBMIT, json=inquiry())
    (inquiry_id,) = await inquiry_ids()
    async with engine.connect() as conn:
        admin_id = (await conn.execute(text("SELECT id FROM users"))).scalar_one()

    response = await admin_client.patch(
        f"{INBOX}/{inquiry_id}", json={"status": "contacted", "assigned_to_id": admin_id}
    )
    assert response.status_code == 200
    detail = response.json()
    assert detail["status"] == "contacted"
    assert detail["assigned_to_email"] == "admin@example.com"

    rows = await audit_rows()
    assert [(r.action, r.entity_type) for r in rows] == [("update", "inquiry")]
    assert "Ali" not in rows[0].summary and "0300" not in rows[0].summary

    assert (await admin_client.patch(f"{INBOX}/{inquiry_id}", json={"status": "bogus"})).status_code == 422
    assert (
        await admin_client.patch(f"{INBOX}/{inquiry_id}", json={"assigned_to_id": 99999})
    ).status_code == 422


async def test_notes_are_added_to_the_inquiry(admin_client):
    await admin_client.post(SUBMIT, json=inquiry())
    (inquiry_id,) = await inquiry_ids()
    response = await admin_client.post(f"{INBOX}/{inquiry_id}/notes", json={"body": "Called, will quote."})
    assert response.status_code == 201
    notes = response.json()["notes"]
    assert len(notes) == 1
    assert notes[0]["body"] == "Called, will quote."
    assert notes[0]["author_email"] == "admin@example.com"


# ------------------------------------------------------------------ deleting


async def test_sales_staff_cannot_delete_inquiries(client, make_user, login):
    await client.post(SUBMIT, json=inquiry())
    (inquiry_id,) = await inquiry_ids()
    await make_user(email="sales@example.com", role="sales")
    await login(email="sales@example.com")
    assert (await client.delete(f"{INBOX}/{inquiry_id}")).status_code == 403
    assert await count_inquiries() == 1


async def test_admin_can_delete_an_inquiry_and_its_notes(admin_client):
    await admin_client.post(SUBMIT, json=inquiry())
    (inquiry_id,) = await inquiry_ids()
    await admin_client.post(f"{INBOX}/{inquiry_id}/notes", json={"body": "A note"})

    assert (await admin_client.delete(f"{INBOX}/{inquiry_id}")).status_code == 204
    assert await count_inquiries() == 0
    async with engine.connect() as conn:
        notes = (await conn.execute(text("SELECT count(*) FROM inquiry_notes"))).scalar_one()
    assert notes == 0
    assert [r.action for r in await audit_rows()] == ["delete"]