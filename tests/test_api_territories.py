"""Tests for the territories API."""

from app.models.lead import Lead, LeadStatus


def test_list_territories_empty(client):
    resp = client.get("/api/v1/territories")
    assert resp.status_code == 200
    assert resp.json() == []


def test_create_territory(client):
    resp = client.post(
        "/api/v1/territories",
        json={
            "name": "Zona Norte",
            "cities": ["Tigre", "San Isidro"],
            "color": "#ff0000",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["name"] == "Zona Norte"
    assert data["cities"] == ["Tigre", "San Isidro"]
    assert data["color"] == "#ff0000"
    assert data["is_active"] is True


def test_create_territory_validation(client):
    resp = client.post("/api/v1/territories", json={})
    assert resp.status_code == 422


def test_list_territories_with_data(client):
    client.post(
        "/api/v1/territories",
        json={"name": "Zona Sur", "cities": ["Lanus"]},
    )
    resp = client.get("/api/v1/territories")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Zona Sur"
    assert "lead_count" in data[0]


def test_get_territory_by_id(client):
    created = client.post(
        "/api/v1/territories",
        json={"name": "CABA", "cities": ["Buenos Aires"]},
    )
    territory_id = created.json()["id"]

    resp = client.get(f"/api/v1/territories/{territory_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == territory_id
    assert data["name"] == "CABA"
    assert "lead_count" in data
    assert "avg_score" in data


def test_get_territory_not_found(client):
    resp = client.get("/api/v1/territories/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_patch_territory(client):
    created = client.post(
        "/api/v1/territories",
        json={"name": "Original", "cities": ["Rosario"]},
    )
    territory_id = created.json()["id"]

    resp = client.patch(
        f"/api/v1/territories/{territory_id}",
        json={"name": "Updated", "cities": ["Rosario", "Santa Fe"]},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Updated"
    assert data["cities"] == ["Rosario", "Santa Fe"]


def test_patch_territory_not_found(client):
    resp = client.patch(
        "/api/v1/territories/00000000-0000-0000-0000-000000000000",
        json={"name": "Nope"},
    )
    assert resp.status_code == 404


def test_delete_territory(client):
    created = client.post(
        "/api/v1/territories",
        json={"name": "ToDelete", "cities": []},
    )
    territory_id = created.json()["id"]

    resp = client.delete(f"/api/v1/territories/{territory_id}")
    assert resp.status_code == 204

    resp = client.get(f"/api/v1/territories/{territory_id}")
    assert resp.status_code == 404


def test_delete_territory_not_found(client):
    resp = client.delete("/api/v1/territories/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_territory_leads_empty(client):
    created = client.post(
        "/api/v1/territories",
        json={"name": "Empty", "cities": ["Nowhere"]},
    )
    territory_id = created.json()["id"]

    resp = client.get(f"/api/v1/territories/{territory_id}/leads")
    assert resp.status_code == 200
    assert resp.json() == []


def test_territory_leads_with_data(db, client):
    lead = Lead(
        business_name="Cafe Norte",
        city="Tigre",
        status=LeadStatus.NEW,
    )
    db.add(lead)
    db.commit()

    created = client.post(
        "/api/v1/territories",
        json={"name": "Norte", "cities": ["Tigre"]},
    )
    territory_id = created.json()["id"]

    resp = client.get(f"/api/v1/territories/{territory_id}/leads")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) >= 1
    assert any(item["business_name"] == "Cafe Norte" for item in data)


def test_territory_leads_not_found(client):
    resp = client.get("/api/v1/territories/00000000-0000-0000-0000-000000000000/leads")
    assert resp.status_code == 404
