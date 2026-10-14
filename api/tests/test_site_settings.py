from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from api.db import engine

PUBLIC_URL = "/api/v1/site-settings"
ADMIN_URL = "/api/v1/admin/site-settings"

# If your verify_origin dependency needs a header on PATCH/POST requests, put it here (copy
# whatever your existing admin tests send) and every mutating call below will use it.
HEADERS: dict[str, str] = {}


async def settings_row_count() -> int:
    async with engine.begin() as conn:
        return (await conn.execute(text("SELECT count(*) FROM site_settings"))).scalar_one()


async def audit_rows():
    async with engine.begin() as conn:
        return (await conn.execute(text("SELECT * FROM audit_logs"))).mappings().all()


# ------------------------------------------------------------------ public read


async def test_public_read_returns_placeholders_and_caches(client):
    response = await client.get(PUBLIC_URL)
    assert response.status_code == 200
    body = response.json()
    assert body["company_name"] == "Ideal Electric"
    assert body["phone_primary"] == "+92-XXX-XXXXXXX"
    assert response.headers["cache-control"] == "public, max-age=300"
    # Internal fields stay out of the public response.
    assert "is_placeholder" not in body
    assert "updated_at" not in body


async def test_first_read_creates_row_and_second_does_not_duplicate(client):
    assert await settings_row_count() == 0
    await client.get(PUBLIC_URL)
    assert await settings_row_count() == 1
    await client.get(PUBLIC_URL)
    assert await settings_row_count() == 1


# ------------------------------------------------------------------ access control


async def test_admin_endpoint_requires_login(client):
    assert (await client.get(ADMIN_URL)).status_code == 401
    response = await client.patch(ADMIN_URL, json={"tagline": "x"}, headers=HEADERS)
    assert response.status_code == 401


async def test_editor_can_read_but_not_change(client, make_user, login):
    await make_user(email="editor@example.com", role="editor")
    await login("editor@example.com")

    assert (await client.get(ADMIN_URL)).status_code == 200
    response = await client.patch(ADMIN_URL, json={"tagline": "x"}, headers=HEADERS)
    assert response.status_code == 403


async def test_admin_read_includes_internal_fields(admin_client):
    body = (await admin_client.get(ADMIN_URL)).json()
    assert body["is_placeholder"] is True
    assert "updated_at" in body


# ------------------------------------------------------------------ updating


async def test_admin_patch_changes_only_the_fields_sent(admin_client):
    response = await admin_client.patch(
        ADMIN_URL,
        json={
            "tagline": "Powering Pakistan",
            "phone_primary": "+92 300 1234567",
            "email_sales": "sales@ideal-electric.pk",
            "whatsapp_number": "923001234567",
            "facebook_url": "https://facebook.com/idealelectric",
        },
        headers=HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["tagline"] == "Powering Pakistan"
    assert body["phone_primary"] == "+92 300 1234567"
    assert body["whatsapp_number"] == "923001234567"
    # Untouched fields keep their values.
    assert body["company_name"] == "Ideal Electric"

    # The public endpoint sees the change too.
    public = (await admin_client.get(PUBLIC_URL)).json()
    assert public["tagline"] == "Powering Pakistan"


async def test_patch_can_clear_an_optional_field(admin_client):
    await admin_client.patch(ADMIN_URL, json={"tagline": "Temporary"}, headers=HEADERS)
    response = await admin_client.patch(ADMIN_URL, json={"tagline": None}, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["tagline"] is None


async def test_patch_can_mark_settings_as_final(admin_client):
    response = await admin_client.patch(
        ADMIN_URL, json={"is_placeholder": False}, headers=HEADERS
    )
    assert response.json()["is_placeholder"] is False


# ------------------------------------------------------------------ validation


@pytest.mark.parametrize(
    "payload",
    [
        {"email_sales": "not-an-email"},
        {"phone_primary": "call me maybe"},
        {"whatsapp_number": "+92 300 1234567"},  # digits only, no plus or spaces
        {"facebook_url": "ftp://example.org/page"},
        {"company_name": "x"},  # too short
        {"company_name": None},  # NOT NULL column: omit it, but null is rejected
        {"unknown_field": "value"},  # extra="forbid"
    ],
)
async def test_invalid_payloads_are_rejected(admin_client, payload):
    response = await admin_client.patch(ADMIN_URL, json=payload, headers=HEADERS)
    assert response.status_code == 422


# ------------------------------------------------------------------ audit log


async def test_update_writes_an_audit_entry(admin_client):
    await admin_client.patch(
        ADMIN_URL, json={"phone_primary": "+92 300 1234567"}, headers=HEADERS
    )
    rows = await audit_rows()
    assert len(rows) == 1
    # Loose on purpose: check that the entity type and the new value appear somewhere in the
    # row. Tighten this to specific columns once you know your audit table's column names.
    assert "site_settings" in rows[0].values()
    assert "+92 300 1234567" in str(dict(rows[0]))


async def test_update_with_no_real_change_writes_no_audit_entry(admin_client):
    await admin_client.patch(ADMIN_URL, json={"tagline": "Same"}, headers=HEADERS)
    before = len(await audit_rows())
    await admin_client.patch(ADMIN_URL, json={"tagline": "Same"}, headers=HEADERS)
    assert len(await audit_rows()) == before


# ------------------------------------------------------------------ singleton


async def test_database_refuses_a_second_row(client):
    await client.get(PUBLIC_URL)  # creates row 1
    with pytest.raises(IntegrityError):
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO site_settings (id, company_name) VALUES (2, 'Second')")
            )