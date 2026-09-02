"""Intake and enquiry lifecycle tests."""

import pytest


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_create_enquiry(client, api_headers):
    payload = {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "+44 7700 900123",
        "enquiry_type": "superyacht",
        "message": "We need luxury tableware for a 60m superyacht. NDA required.",
        "company": "Ocean Estates Ltd",
        "terms_accepted": True,
        "newsletter_opt_in": False,
    }
    resp = await client.post("/api/v1/enquiries", json=payload, headers=api_headers)
    assert resp.status_code == 202
    data = resp.json()
    assert "enquiry_id" in data
    assert data["status"] == "draft_pending"


@pytest.mark.asyncio
async def test_create_enquiry_unauthorized(client):
    payload = {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "enquiry_type": "general",
        "message": "Hello",
    }
    resp = await client.post("/api/v1/enquiries", json=payload)
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_enquiry_timeline(client, api_headers):
    payload = {
        "name": "John Doe",
        "email": "john@example.com",
        "enquiry_type": "residential",
        "message": "Residential project enquiry for London penthouse.",
    }
    create = await client.post("/api/v1/enquiries", json=payload, headers=api_headers)
    enquiry_id = create.json()["enquiry_id"]

    resp = await client.get(f"/api/v1/enquiries/{enquiry_id}", headers=api_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["enquiry_id"] == enquiry_id
    assert len(data["timeline"]) >= 3
    event_types = [e["event_type"] for e in data["timeline"]]
    assert "intake" in event_types
    assert "classified" in event_types
    assert "draft_created" in event_types


@pytest.mark.asyncio
async def test_approve_and_send_email(client, api_headers, auth_headers):
    payload = {
        "name": "Alice Brown",
        "email": "alice@example.com",
        "enquiry_type": "aircraft",
        "message": "Private aircraft linen requirements.",
    }
    create = await client.post("/api/v1/enquiries", json=payload, headers=api_headers)
    enquiry_id = create.json()["enquiry_id"]
    flow_id = (await client.get(f"/api/v1/enquiries/{enquiry_id}", headers=api_headers)).json()["flow_id"]

    draft_resp = await client.get(f"/api/v1/enquiries/{enquiry_id}/draft", headers=auth_headers)
    assert draft_resp.status_code == 200
    assert "subject" in draft_resp.json()

    approve_resp = await client.post(
        f"/api/v1/enquiries/{enquiry_id}/approve",
        json={"flow_id": flow_id, "action": "approved", "feedback": "Looks good"},
        headers=auth_headers,
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "responded"
