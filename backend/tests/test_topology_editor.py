"""Tests for topology editor functionality."""
import pytest
from fastapi.testclient import TestClient
from main import app
from topology_editor import (
    topology_editor, TopologyEditor, NodeType, ConnectionType,
    ValidationSeverity
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_topology_editor():
    """Reset topology editor state before each test."""
    topology_editor._topologies.clear()
    yield
    topology_editor._topologies.clear()


def get_admin_token():
    """Helper to get admin auth token."""
    response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    return response.json()["access_token"]


def get_instructor_token():
    """Helper to get instructor auth token."""
    response = client.post("/auth/login", json={
        "username": "instructor",
        "password": "instructor123"
    })
    return response.json()["access_token"]


def get_trainee_token():
    """Helper to get trainee auth token."""
    response = client.post("/auth/login", json={
        "username": "trainee",
        "password": "trainee123"
    })
    return response.json()["access_token"]


class TestTopologyEditor:
    """Tests for the TopologyEditor class."""

    def test_create_topology(self):
        """Test creating a topology."""
        topology = topology_editor.create_topology(
            name="Test Topology",
            description="A test topology",
            created_by="admin"
        )

        assert topology.topology_id is not None
        assert topology.name == "Test Topology"
        assert len(topology.nodes) == 0

    def test_add_node(self):
        """Test adding a node to topology."""
        topology = topology_editor.create_topology(
            name="Test",
            description="Test",
            created_by="admin"
        )

        node = topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Router1",
            node_type=NodeType.ROUTER,
            x=100,
            y=200,
            ip_addresses=["192.168.1.1"]
        )

        assert node is not None
        assert node.name == "Router1"
        assert node.node_type == NodeType.ROUTER

    def test_update_node(self):
        """Test updating a node."""
        topology = topology_editor.create_topology(
            name="Test",
            description="Test",
            created_by="admin"
        )

        node = topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Server1",
            node_type=NodeType.SERVER,
            x=100,
            y=100
        )

        updated = topology_editor.update_node(
            topology_id=topology.topology_id,
            node_id=node.node_id,
            name="Server2",
            ip_addresses=["10.0.0.1"]
        )

        assert updated.name == "Server2"
        assert "10.0.0.1" in updated.ip_addresses

    def test_delete_node(self):
        """Test deleting a node."""
        topology = topology_editor.create_topology(
            name="Test",
            description="Test",
            created_by="admin"
        )

        node = topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Server",
            node_type=NodeType.SERVER,
            x=100,
            y=100
        )

        result = topology_editor.delete_node(
            topology.topology_id, node.node_id
        )

        assert result is True
        assert len(topology.nodes) == 0

    def test_add_connection(self):
        """Test adding a connection."""
        topology = topology_editor.create_topology(
            name="Test",
            description="Test",
            created_by="admin"
        )

        node1 = topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Router",
            node_type=NodeType.ROUTER,
            x=100,
            y=100
        )

        node2 = topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Server",
            node_type=NodeType.SERVER,
            x=200,
            y=100
        )

        connection = topology_editor.add_connection(
            topology_id=topology.topology_id,
            source_node_id=node1.node_id,
            target_node_id=node2.node_id,
            connection_type=ConnectionType.ETHERNET,
            bandwidth="1Gbps"
        )

        assert connection is not None
        assert connection.source_node_id == node1.node_id
        assert connection.bandwidth == "1Gbps"

    def test_add_connection_invalid_node(self):
        """Test adding connection with invalid node fails."""
        topology = topology_editor.create_topology(
            name="Test",
            description="Test",
            created_by="admin"
        )

        node = topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Router",
            node_type=NodeType.ROUTER,
            x=100,
            y=100
        )

        with pytest.raises(ValueError, match="not found"):
            topology_editor.add_connection(
                topology_id=topology.topology_id,
                source_node_id=node.node_id,
                target_node_id="invalid-id"
            )

    def test_add_subnet(self):
        """Test adding a subnet."""
        topology = topology_editor.create_topology(
            name="Test",
            description="Test",
            created_by="admin"
        )

        subnet = topology_editor.add_subnet(
            topology_id=topology.topology_id,
            name="Internal",
            cidr="192.168.1.0/24",
            gateway="192.168.1.1"
        )

        assert subnet is not None
        assert subnet.cidr == "192.168.1.0/24"

    def test_validate_topology_empty(self):
        """Test validating an empty topology."""
        topology = topology_editor.create_topology(
            name="Empty",
            description="Empty topology",
            created_by="admin"
        )

        issues = topology_editor.validate_topology(topology.topology_id)

        # Should have warning about no nodes
        assert any(i.severity == ValidationSeverity.WARNING for i in issues)

    def test_validate_topology_isolated_node(self):
        """Test validating topology with isolated node."""
        topology = topology_editor.create_topology(
            name="Test",
            description="Test",
            created_by="admin"
        )

        topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Isolated1",
            node_type=NodeType.SERVER,
            x=100,
            y=100
        )

        topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Isolated2",
            node_type=NodeType.SERVER,
            x=200,
            y=100
        )

        issues = topology_editor.validate_topology(topology.topology_id)

        # Should have warnings about isolated nodes
        assert any("isolated" in i.message.lower() for i in issues)

    def test_validate_topology_duplicate_names(self):
        """Test validating topology with duplicate node names."""
        topology = topology_editor.create_topology(
            name="Test",
            description="Test",
            created_by="admin"
        )

        topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Server",
            node_type=NodeType.SERVER,
            x=100,
            y=100
        )

        topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Server",
            node_type=NodeType.SERVER,
            x=200,
            y=100
        )

        issues = topology_editor.validate_topology(topology.topology_id)

        assert any(
            i.severity == ValidationSeverity.ERROR and "duplicate" in i.message.lower()
            for i in issues
        )

    def test_validate_topology_invalid_ip(self):
        """Test validating topology with invalid IP."""
        topology = topology_editor.create_topology(
            name="Test",
            description="Test",
            created_by="admin"
        )

        topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Server",
            node_type=NodeType.SERVER,
            x=100,
            y=100,
            ip_addresses=["999.999.999.999"]
        )

        issues = topology_editor.validate_topology(topology.topology_id)

        assert any(
            i.severity == ValidationSeverity.ERROR and "invalid ip" in i.message.lower()
            for i in issues
        )

    def test_export_json(self):
        """Test exporting to JSON."""
        topology = topology_editor.create_topology(
            name="Export Test",
            description="Test",
            created_by="admin"
        )

        topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Router",
            node_type=NodeType.ROUTER,
            x=100,
            y=100
        )

        json_content = topology_editor.export_json(topology.topology_id)

        assert json_content is not None
        assert "Export Test" in json_content
        assert "Router" in json_content

    def test_export_yaml(self):
        """Test exporting to YAML."""
        topology = topology_editor.create_topology(
            name="Export Test",
            description="Test",
            created_by="admin"
        )

        yaml_content = topology_editor.export_yaml(topology.topology_id)

        assert yaml_content is not None
        assert "Export Test" in yaml_content

    def test_export_graphviz(self):
        """Test exporting to Graphviz DOT."""
        topology = topology_editor.create_topology(
            name="Graph Test",
            description="Test",
            created_by="admin"
        )

        node1 = topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Router",
            node_type=NodeType.ROUTER,
            x=100,
            y=100
        )

        node2 = topology_editor.add_node(
            topology_id=topology.topology_id,
            name="Server",
            node_type=NodeType.SERVER,
            x=200,
            y=100
        )

        topology_editor.add_connection(
            topology_id=topology.topology_id,
            source_node_id=node1.node_id,
            target_node_id=node2.node_id
        )

        dot_content = topology_editor.export_graphviz(topology.topology_id)

        assert dot_content is not None
        assert "digraph" in dot_content
        assert "Graph Test" in dot_content

    def test_import_json(self):
        """Test importing from JSON."""
        json_content = '''
        {
            "description": "Imported topology",
            "nodes": [
                {
                    "node_id": "node-1",
                    "name": "Router1",
                    "node_type": "router",
                    "position": {"x": 100, "y": 100}
                }
            ],
            "connections": [],
            "subnets": []
        }
        '''

        topology = topology_editor.import_json(
            json_content=json_content,
            name="Imported",
            created_by="admin"
        )

        assert topology is not None
        assert len(topology.nodes) == 1

    def test_clone_topology(self):
        """Test cloning a topology."""
        original = topology_editor.create_topology(
            name="Original",
            description="Original topology",
            created_by="admin"
        )

        topology_editor.add_node(
            topology_id=original.topology_id,
            name="Router",
            node_type=NodeType.ROUTER,
            x=100,
            y=100
        )

        clone = topology_editor.clone_topology(
            topology_id=original.topology_id,
            new_name="Clone",
            created_by="admin"
        )

        assert clone is not None
        assert clone.name == "Clone"
        assert len(clone.nodes) == 1
        assert clone.topology_id != original.topology_id


class TestTopologyEditorEndpoints:
    """Tests for topology editor API endpoints."""

    def test_create_topology_endpoint(self):
        token = get_admin_token()

        response = client.post(
            "/topology-editor",
            json={
                "name": "API Test",
                "description": "Testing API"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "API Test"

    def test_create_topology_trainee_forbidden(self):
        token = get_trainee_token()

        response = client.post(
            "/topology-editor",
            json={
                "name": "Test",
                "description": "Test"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    def test_list_topologies_endpoint(self):
        token = get_admin_token()

        # Create a topology
        client.post(
            "/topology-editor",
            json={"name": "Test", "description": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/topology-editor",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_topology_endpoint(self):
        token = get_admin_token()

        # Create a topology
        create_response = client.post(
            "/topology-editor",
            json={"name": "Test", "description": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        topology_id = create_response.json()["topology_id"]

        response = client.get(
            f"/topology-editor/{topology_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["topology_id"] == topology_id

    def test_add_node_endpoint(self):
        token = get_admin_token()

        # Create a topology
        create_response = client.post(
            "/topology-editor",
            json={"name": "Test", "description": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        topology_id = create_response.json()["topology_id"]

        response = client.post(
            f"/topology-editor/{topology_id}/nodes",
            json={
                "name": "Router",
                "node_type": "router",
                "x": 100,
                "y": 200,
                "ip_addresses": ["192.168.1.1"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Router"

    def test_add_connection_endpoint(self):
        token = get_admin_token()

        # Create topology with nodes
        create_response = client.post(
            "/topology-editor",
            json={"name": "Test", "description": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        topology_id = create_response.json()["topology_id"]

        node1 = client.post(
            f"/topology-editor/{topology_id}/nodes",
            json={"name": "Router", "node_type": "router", "x": 100, "y": 100},
            headers={"Authorization": f"Bearer {token}"}
        ).json()

        node2 = client.post(
            f"/topology-editor/{topology_id}/nodes",
            json={"name": "Server", "node_type": "server", "x": 200, "y": 100},
            headers={"Authorization": f"Bearer {token}"}
        ).json()

        response = client.post(
            f"/topology-editor/{topology_id}/connections",
            json={
                "source_node_id": node1["node_id"],
                "target_node_id": node2["node_id"],
                "connection_type": "ethernet"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

    def test_validate_topology_endpoint(self):
        token = get_admin_token()

        # Create topology
        create_response = client.post(
            "/topology-editor",
            json={"name": "Test", "description": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        topology_id = create_response.json()["topology_id"]

        response = client.get(
            f"/topology-editor/{topology_id}/validate",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "valid" in response.json()
        assert "issues" in response.json()

    def test_export_topology_json(self):
        token = get_admin_token()

        # Create topology
        create_response = client.post(
            "/topology-editor",
            json={"name": "Export", "description": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        topology_id = create_response.json()["topology_id"]

        response = client.get(
            f"/topology-editor/{topology_id}/export?format=json",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "Export" in response.text

    def test_export_topology_graphviz(self):
        token = get_admin_token()

        # Create topology
        create_response = client.post(
            "/topology-editor",
            json={"name": "Graph", "description": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        topology_id = create_response.json()["topology_id"]

        response = client.get(
            f"/topology-editor/{topology_id}/export?format=graphviz",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "digraph" in response.text

    def test_import_topology_endpoint(self):
        token = get_admin_token()

        json_content = '''{"nodes": [], "connections": [], "subnets": []}'''

        response = client.post(
            "/topology-editor/import",
            json={
                "name": "Imported",
                "content": json_content,
                "format": "json"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Imported"

    def test_clone_topology_endpoint(self):
        token = get_admin_token()

        # Create topology
        create_response = client.post(
            "/topology-editor",
            json={"name": "Original", "description": "Test"},
            headers={"Authorization": f"Bearer {token}"}
        )
        topology_id = create_response.json()["topology_id"]

        response = client.post(
            f"/topology-editor/{topology_id}/clone?new_name=Clone",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["name"] == "Clone"

    def test_get_node_types_endpoint(self):
        token = get_admin_token()

        response = client.get(
            "/topology-editor/node-types",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 5  # At least 5 node types

    def test_get_connection_types_endpoint(self):
        token = get_admin_token()

        response = client.get(
            "/topology-editor/connection-types",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3  # At least 3 connection types
