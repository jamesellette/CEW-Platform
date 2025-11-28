from fastapi.testclient import TestClient
from main import app, db, active_scenarios

client = TestClient(app)


def test_health_check():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "healthy"}


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


def test_create_scenario_real_rf_blocked():
    db.clear()
    scenario_data = {
        "name": "RF Test",
        "constraints": {"allow_real_rf": True}
    }
    r = client.post("/scenarios", json=scenario_data)
    assert r.status_code == 400
    assert "Real RF transmission disabled" in r.json()["detail"]


def test_update_scenario():
    db.clear()
    # Create a scenario first
    scenario_data = {
        "name": "Original Name",
        "description": "Original description"
    }
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    # Update the scenario
    update_data = {
        "name": "Updated Name",
        "description": "Updated description"
    }
    r = client.put(f"/scenarios/{scenario_id}", json=update_data)
    assert r.status_code == 200
    assert r.json()["name"] == "Updated Name"
    assert r.json()["description"] == "Updated description"


def test_update_scenario_partial():
    db.clear()
    # Create a scenario first
    scenario_data = {
        "name": "Original Name",
        "description": "Original description"
    }
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    # Update only the name
    update_data = {"name": "Only Name Updated"}
    r = client.put(f"/scenarios/{scenario_id}", json=update_data)
    assert r.status_code == 200
    assert r.json()["name"] == "Only Name Updated"
    assert r.json()["description"] == "Original description"


def test_update_scenario_not_found():
    db.clear()
    update_data = {"name": "Updated Name"}
    r = client.put("/scenarios/nonexistent-id", json=update_data)
    assert r.status_code == 404


def test_update_scenario_external_network_blocked():
    db.clear()
    # Create a scenario first
    scenario_data = {"name": "Test Scenario"}
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    # Try to update with external network enabled
    update_data = {"constraints": {"allow_external_network": True}}
    r = client.put(f"/scenarios/{scenario_id}", json=update_data)
    assert r.status_code == 400
    assert "External network access disabled" in r.json()["detail"]


def test_delete_scenario():
    db.clear()
    # Create a scenario first
    scenario_data = {"name": "To Be Deleted"}
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    # Delete the scenario
    r = client.delete(f"/scenarios/{scenario_id}")
    assert r.status_code == 200
    assert r.json()["message"] == "Scenario deleted successfully"

    # Verify it's deleted
    r = client.get(f"/scenarios/{scenario_id}")
    assert r.status_code == 404


def test_delete_scenario_not_found():
    db.clear()
    r = client.delete("/scenarios/nonexistent-id")
    assert r.status_code == 404


# ============ Scenario Export/Import Tests ============

def test_export_scenario_json():
    db.clear()
    # Create a scenario first
    scenario_data = {
        "name": "Export Test",
        "description": "A scenario to export"
    }
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    # Export as JSON
    r = client.get(f"/scenarios/{scenario_id}/export?format=json")
    assert r.status_code == 200
    assert "application/json" in r.headers["content-type"]
    assert "Export Test" in r.text


def test_export_scenario_yaml():
    db.clear()
    # Create a scenario first
    scenario_data = {
        "name": "YAML Export Test",
        "description": "A scenario to export as YAML"
    }
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    # Export as YAML
    r = client.get(f"/scenarios/{scenario_id}/export?format=yaml")
    assert r.status_code == 200
    assert "application/x-yaml" in r.headers["content-type"]
    assert "YAML Export Test" in r.text


def test_export_scenario_not_found():
    db.clear()
    r = client.get("/scenarios/nonexistent-id/export")
    assert r.status_code == 404


def test_import_scenario_json():
    db.clear()
    import_data = {
        "content": '{"name": "Imported Scenario", "description": "From JSON"}',
        "format": "json"
    }
    r = client.post("/scenarios/import", json=import_data)
    assert r.status_code == 200
    assert r.json()["name"] == "Imported Scenario"
    assert r.json()["id"] is not None


def test_import_scenario_yaml():
    db.clear()
    import_data = {
        "content": "name: YAML Imported\ndescription: From YAML",
        "format": "yaml"
    }
    r = client.post("/scenarios/import", json=import_data)
    assert r.status_code == 200
    assert r.json()["name"] == "YAML Imported"


def test_import_scenario_invalid_json():
    db.clear()
    import_data = {
        "content": "not valid json{",
        "format": "json"
    }
    r = client.post("/scenarios/import", json=import_data)
    assert r.status_code == 400
    assert "Invalid JSON" in r.json()["detail"]


def test_import_scenario_missing_name():
    db.clear()
    import_data = {
        "content": '{"description": "No name field"}',
        "format": "json"
    }
    r = client.post("/scenarios/import", json=import_data)
    assert r.status_code == 400
    assert "must have a name" in r.json()["detail"]


# ============ Topology Template Tests ============

def test_list_topologies():
    r = client.get("/topologies")
    assert r.status_code == 200
    templates = r.json()
    assert isinstance(templates, list)
    # Should have at least the sample topologies
    assert len(templates) >= 3
    # Verify structure
    for t in templates:
        assert "filename" in t
        assert "name" in t
        assert "description" in t
        assert "node_count" in t
        assert "networks" in t


def test_get_topology_basic_lab():
    r = client.get("/topologies/basic_lab.json")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Basic Lab Network"
    assert "nodes" in data
    assert "networks" in data
    assert data["constraints"]["allow_external_network"] is False


def test_get_topology_enterprise():
    r = client.get("/topologies/enterprise_network.json")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "Multi-Segment Enterprise Network"
    assert len(data["nodes"]) >= 5


def test_get_topology_rf_ew():
    r = client.get("/topologies/rf_ew_training.json")
    assert r.status_code == 200
    data = r.json()
    assert "rf_environment" in data
    assert data["constraints"]["allow_real_rf"] is False


def test_get_topology_not_found():
    r = client.get("/topologies/nonexistent.json")
    assert r.status_code == 404


def test_get_topology_path_traversal_blocked():
    # Test various path traversal attempts
    r = client.get("/topologies/..%2Fmain.py")
    assert r.status_code in [400, 404]  # Either blocked or not found is acceptable

    r = client.get("/topologies/test..json")
    assert r.status_code == 400  # Blocked because it contains ..

    # The actual path traversal protection is in the code
    # This verifies the endpoint doesn't expose parent directories


# ============ Kill Switch / Activation Tests ============

def get_admin_token():
    """Helper to get admin auth token."""
    response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    return response.json()["access_token"]


def test_activate_scenario():
    db.clear()
    active_scenarios.clear()

    # Create a scenario first
    scenario_data = {"name": "Activation Test"}
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    # Activate as admin
    token = get_admin_token()
    r = client.post(
        f"/scenarios/{scenario_id}/activate",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "active"


def test_activate_scenario_already_active():
    db.clear()
    active_scenarios.clear()

    # Create and activate a scenario
    scenario_data = {"name": "Already Active Test"}
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    token = get_admin_token()
    client.post(
        f"/scenarios/{scenario_id}/activate",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Try to activate again
    r = client.post(
        f"/scenarios/{scenario_id}/activate",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 400
    assert "already active" in r.json()["detail"]


def test_deactivate_scenario():
    db.clear()
    active_scenarios.clear()

    # Create and activate a scenario
    scenario_data = {"name": "Deactivation Test"}
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    token = get_admin_token()
    client.post(
        f"/scenarios/{scenario_id}/activate",
        headers={"Authorization": f"Bearer {token}"}
    )

    # Deactivate
    r = client.post(
        f"/scenarios/{scenario_id}/deactivate",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "inactive"


def test_kill_switch():
    db.clear()
    active_scenarios.clear()

    # Create and activate multiple scenarios
    token = get_admin_token()

    for i in range(3):
        scenario_data = {"name": f"Kill Switch Test {i}"}
        create_response = client.post("/scenarios", json=scenario_data)
        scenario_id = create_response.json()["id"]
        client.post(
            f"/scenarios/{scenario_id}/activate",
            headers={"Authorization": f"Bearer {token}"}
        )

    # Kill switch
    r = client.post(
        "/kill-switch",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert r.json()["deactivated_count"] == 3


def test_list_active_scenarios():
    db.clear()
    active_scenarios.clear()

    # Create and activate a scenario
    scenario_data = {"name": "Active List Test"}
    create_response = client.post("/scenarios", json=scenario_data)
    scenario_id = create_response.json()["id"]

    token = get_admin_token()
    client.post(
        f"/scenarios/{scenario_id}/activate",
        headers={"Authorization": f"Bearer {token}"}
    )

    # List active scenarios
    r = client.get(
        "/scenarios/active",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert r.status_code == 200
    assert len(r.json()) == 1
    assert r.json()[0]["scenario_name"] == "Active List Test"
