"""Fathom webhook tests."""

import json

import pytest


@pytest.mark.asyncio
async def test_fathom_webhook_processes(client, api_headers):
    intake = {
        "name": "Bob Client",
        "email": "client@example.com",
        "enquiry_type": "superyacht",
        "message": "Superyacht outfitting with NDA.",
    }
    create = await client.post("/api/v1/enquiries", json=intake, headers=api_headers)
    enquiry_id = create.json()["enquiry_id"]

    payload = {
        "id": "rec_test_123",
        "title": "Brief call — Bob Client",
        "recording_start_time": "2026-08-31T10:00:00Z",
        "default_summary": {"markdown_formatted": "Discussed superyacht tableware and NDA."},
        "calendar_invitees": [{"name": "Bob Client", "email": "client@example.com"}],
    }
    resp = await client.post(
        "/api/v1/webhooks/fathom",
        content=json.dumps(payload),
        headers={"Content-Type": "application/json"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert data["status"] in ("accepted", "processed")
    assert data.get("enquiry_id") == enquiry_id or data.get("status") == "accepted"

    status_resp = await client.get(f"/api/v1/enquiries/{enquiry_id}", headers=api_headers)
    assert status_resp.status_code == 200


@pytest.mark.asyncio
async def test_fathom_signature_rejection(client, monkeypatch):
    monkeypatch.setenv("FATHOM_MOCK", "false")
    monkeypatch.setenv("FATHOM_WEBHOOK_SECRET", "whsec_testsecret")

    from crm_enquiries.config import get_settings

    get_settings.cache_clear()

    payload = {"id": "rec_bad", "calendar_invitees": []}
    resp = await client.post(
        "/api/v1/webhooks/fathom",
        content=json.dumps(payload),
        headers={
            "Content-Type": "application/json",
            "webhook-id": "msg_1",
            "webhook-timestamp": "1234567890",
            "webhook-signature": "v1,invalidsignature",
        },
    )
    assert resp.status_code == 401

    get_settings.cache_clear()
