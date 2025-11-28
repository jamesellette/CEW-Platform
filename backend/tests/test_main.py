from fastapi.testclient import TestClient
from main import app, db

client = TestClient(app)


def test_list_scenarios_empty():
    db.clear()
    r = client.get("/scenarios")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_create_scenario():
    db.clear()
    scenario_data = {
        "name": "Test Scenario",
        "description": "A test scenario",
        "topology": {},
        "constraints": {}
    }
    r = client.post("/scenarios", json=scenario_data)
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Test Scenario"
    assert data["id"] is not None


def test_get_scenario():
    db.clear()
    # First create a scenario
    scenario_data = {
        "name": "Fetch Test",
        "description": "A scenario to fetch"
    }
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    # Then fetch it
    r = client.get(f"/scenarios/{scenario_id}")
    assert r.status_code == 200
    assert r.json()["name"] == "Fetch Test"


def test_get_scenario_not_found():
    db.clear()
    r = client.get("/scenarios/nonexistent-id")
    assert r.status_code == 404


def test_create_scenario_external_network_blocked():
    db.clear()
    scenario_data = {
        "name": "External Network Test",
        "constraints": {"allow_external_network": True}
    }
    r = client.post("/scenarios", json=scenario_data)
    assert r.status_code == 400
    assert "External network access disabled" in r.json()["detail"]
