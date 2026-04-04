"""Smoke tests for the leads API."""


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["app"] == "Scouter"


def test_create_lead(client):
    resp = client.post("/api/v1/leads", json={
        "business_name": "Test Cafe",
        "industry": "restaurante",
        "city": "Buenos Aires",
    })
    assert resp.status_code == 201
    data = resp.json()
    assert data["business_name"] == "Test Cafe"
    assert data["status"] == "new"
    assert data["quality"] == "unknown"
    assert data["dedup_hash"] is not None


def test_create_lead_dedup(client):
    payload = {
        "business_name": "Dedup Test",
        "city": "Rosario",
    }
    resp1 = client.post("/api/v1/leads", json=payload)
    resp2 = client.post("/api/v1/leads", json=payload)
    assert resp1.status_code == 201
    assert resp2.status_code == 201
    # Same lead returned (dedup)
    assert resp1.json()["id"] == resp2.json()["id"]


def test_list_leads(client):
    client.post("/api/v1/leads", json={"business_name": "List Test"})
    resp = client.get("/api/v1/leads")
    assert resp.status_code == 200
    data = resp.json()
    assert "items" in data
    assert data["total"] >= 1


def test_get_lead_not_found(client):
    resp = client.get("/api/v1/leads/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_get_lead_detail_includes_contract_fields(client):
    created = client.post("/api/v1/leads", json={"business_name": "Detail Test", "city": "Cordoba"})
    lead_id = created.json()["id"]

    resp = client.get(f"/api/v1/leads/{lead_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == lead_id
    assert data["status"] == "new"
    assert data["quality"] == "unknown"
    assert data["signals"] == []
    assert data["source"] is None


def test_create_lead_validation(client):
    resp = client.post("/api/v1/leads", json={})
    assert resp.status_code == 422


# --- GET /leads/names ---

def test_leads_names_empty(client):
    resp = client.get("/api/v1/leads/names")
    assert resp.status_code == 200
    assert resp.json() == []


def test_leads_names_returns_id_and_business_name(client):
    created = client.post("/api/v1/leads", json={"business_name": "Names Test Cafe"})
    assert created.status_code == 201
    lead_id = created.json()["id"]

    resp = client.get("/api/v1/leads/names")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == lead_id
    assert data[0]["business_name"] == "Names Test Cafe"


def test_leads_names_ordered_by_name(client):
    client.post("/api/v1/leads", json={"business_name": "Zara Bistro"})
    client.post("/api/v1/leads", json={"business_name": "Alpha Cafe"})
    client.post("/api/v1/leads", json={"business_name": "Midtown Diner"})

    resp = client.get("/api/v1/leads/names")
    assert resp.status_code == 200
    names = [item["business_name"] for item in resp.json()]
    assert names == sorted(names)
