"""Tests for WebSocket real-time monitoring functionality."""
import pytest
from fastapi.testclient import TestClient
from main import app, db
from websocket_manager import ConnectionManager, LabMonitor
from auth import get_user_from_token


client = TestClient(app)


def get_admin_token():
    """Helper to get admin auth token."""
    response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    return response.json()["access_token"]


def get_trainee_token():
    """Helper to get trainee auth token."""
    response = client.post("/auth/login", json={
        "username": "trainee",
        "password": "trainee123"
    })
    return response.json()["access_token"]


class TestGetUserFromToken:
    """Tests for the get_user_from_token function."""

    def test_valid_admin_token(self):
        token = get_admin_token()
        user = get_user_from_token(token)
        assert user is not None
        assert user.username == "admin"
        assert user.role == "admin"

    def test_valid_trainee_token(self):
        token = get_trainee_token()
        user = get_user_from_token(token)
        assert user is not None
        assert user.username == "trainee"
        assert user.role == "trainee"

    def test_invalid_token(self):
        user = get_user_from_token("invalid_token")
        assert user is None

    def test_empty_token(self):
        user = get_user_from_token("")
        assert user is None


class TestConnectionManager:
    """Tests for the ConnectionManager class."""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    def test_get_connected_labs_empty(self, manager):
        assert manager.get_connected_labs() == []

    def test_get_connection_count_empty(self, manager):
        assert manager.get_connection_count() == 0


class TestLabMonitor:
    """Tests for the LabMonitor class."""

    @pytest.fixture
    def manager(self):
        return ConnectionManager()

    @pytest.fixture
    def monitor(self, manager):
        return LabMonitor(manager)

    def test_monitor_initial_state(self, monitor):
        assert monitor._running is False
        assert monitor._task is None

    @pytest.mark.asyncio
    async def test_monitor_start_stop(self, monitor):
        await monitor.start()
        assert monitor._running is True
        assert monitor._task is not None

        await monitor.stop()
        assert monitor._running is False


class TestWebSocketEndpoints:
    """Tests for WebSocket-related HTTP endpoints."""

    def test_ws_status_endpoint(self):
        db.clear()
        token = get_admin_token()

        r = client.get(
            "/ws/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 200
        data = r.json()
        assert "connected_labs" in data
        assert "total_connections" in data
        assert isinstance(data["connected_labs"], list)
        assert isinstance(data["total_connections"], int)

    def test_ws_status_requires_auth(self):
        r = client.get("/ws/status")
        # Expecting 401 (Unauthorized) or 403 (Forbidden)
        assert r.status_code in [401, 403]

    def test_ws_status_requires_admin_or_instructor(self):
        token = get_trainee_token()
        r = client.get(
            "/ws/status",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert r.status_code == 403


class TestWebSocketConnection:
    """Tests for WebSocket connections."""

    def test_websocket_requires_token(self):
        """Test that WebSocket requires authentication token."""
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect("/ws/labs/test-lab"):
                pass

    def test_websocket_rejects_invalid_token(self):
        """Test that WebSocket rejects invalid tokens."""
        from starlette.websockets import WebSocketDisconnect
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                "/ws/labs/test-lab?token=invalid_token"
            ):
                pass

    def test_websocket_rejects_trainee(self):
        """Test that WebSocket rejects trainee role."""
        from starlette.websockets import WebSocketDisconnect
        token = get_trainee_token()
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                f"/ws/labs/test-lab?token={token}"
            ):
                pass

    def test_websocket_rejects_nonexistent_lab(self):
        """Test that WebSocket rejects nonexistent lab."""
        from starlette.websockets import WebSocketDisconnect
        token = get_admin_token()
        with pytest.raises(WebSocketDisconnect):
            with client.websocket_connect(
                f"/ws/labs/nonexistent-lab?token={token}"
            ):
                pass
