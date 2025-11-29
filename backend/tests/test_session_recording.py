"""Tests for session recording functionality."""
import pytest
from fastapi.testclient import TestClient
from main import app, db, active_scenarios, lab_to_scenario
from orchestrator import orchestrator
from session_recording import (
    session_recorder, SessionRecorder, RecordingSession, RecordedEvent,
    EventType, RecordingState
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_recorder():
    """Reset session recorder state before each test."""
    session_recorder._sessions.clear()
    session_recorder._lab_sessions.clear()
    yield
    session_recorder._sessions.clear()
    session_recorder._lab_sessions.clear()


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


class TestSessionRecorder:
    """Tests for the SessionRecorder class."""

    @pytest.mark.asyncio
    async def test_start_recording(self):
        """Test starting a recording session."""
        session = await session_recorder.start_recording(
            lab_id="test-lab",
            scenario_id="test-scenario",
            scenario_name="Test Scenario",
            username="testuser"
        )

        assert session.session_id is not None
        assert session.lab_id == "test-lab"
        assert session.scenario_id == "test-scenario"
        assert session.scenario_name == "Test Scenario"
        assert session.username == "testuser"
        assert session.state == RecordingState.RECORDING
        assert session.started_at is not None

    @pytest.mark.asyncio
    async def test_start_recording_duplicate_lab(self):
        """Test that starting a duplicate recording for same lab fails."""
        await session_recorder.start_recording(
            lab_id="test-lab",
            scenario_id="scenario1",
            scenario_name="Scenario 1",
            username="user1"
        )

        with pytest.raises(ValueError, match="already has an active recording"):
            await session_recorder.start_recording(
                lab_id="test-lab",
                scenario_id="scenario2",
                scenario_name="Scenario 2",
                username="user2"
            )

    @pytest.mark.asyncio
    async def test_stop_recording(self):
        """Test stopping a recording session."""
        session = await session_recorder.start_recording(
            lab_id="test-lab",
            scenario_id="test-scenario",
            scenario_name="Test Scenario",
            username="testuser"
        )

        stopped = await session_recorder.stop_recording(session.session_id)

        assert stopped.state == RecordingState.STOPPED
        assert stopped.stopped_at is not None
        assert stopped.get_duration() >= 0

    @pytest.mark.asyncio
    async def test_stop_recording_not_found(self):
        """Test stopping a non-existent recording."""
        with pytest.raises(ValueError, match="not found"):
            await session_recorder.stop_recording("nonexistent")

    @pytest.mark.asyncio
    async def test_pause_and_resume_recording(self):
        """Test pausing and resuming a recording."""
        session = await session_recorder.start_recording(
            lab_id="test-lab",
            scenario_id="test-scenario",
            scenario_name="Test Scenario",
            username="testuser"
        )

        # Pause
        paused = await session_recorder.pause_recording(session.session_id)
        assert paused.state == RecordingState.PAUSED

        # Resume
        resumed = await session_recorder.resume_recording(session.session_id)
        assert resumed.state == RecordingState.RECORDING

    @pytest.mark.asyncio
    async def test_record_event(self):
        """Test recording an event."""
        session = await session_recorder.start_recording(
            lab_id="test-lab",
            scenario_id="test-scenario",
            scenario_name="Test Scenario",
            username="testuser"
        )

        event = await session_recorder.record_event(
            lab_id="test-lab",
            event_type=EventType.COMMAND_EXECUTED,
            container_id="container1",
            hostname="node1",
            data={"command": "ls -la"}
        )

        assert event is not None
        assert event.event_type == EventType.COMMAND_EXECUTED
        assert event.container_id == "container1"
        assert event.hostname == "node1"
        assert event.data["command"] == "ls -la"

    @pytest.mark.asyncio
    async def test_record_event_no_session(self):
        """Test recording event when no session exists."""
        event = await session_recorder.record_event(
            lab_id="nonexistent-lab",
            event_type=EventType.COMMAND_EXECUTED,
            data={"command": "ls"}
        )

        assert event is None

    @pytest.mark.asyncio
    async def test_record_terminal_input(self):
        """Test recording terminal input."""
        await session_recorder.start_recording(
            lab_id="test-lab",
            scenario_id="test-scenario",
            scenario_name="Test Scenario",
            username="testuser"
        )

        event = await session_recorder.record_terminal_input(
            lab_id="test-lab",
            container_id="container1",
            hostname="node1",
            command="whoami"
        )

        assert event is not None
        assert event.event_type == EventType.TERMINAL_INPUT
        assert event.data["command"] == "whoami"

    @pytest.mark.asyncio
    async def test_record_command(self):
        """Test recording a complete command execution."""
        await session_recorder.start_recording(
            lab_id="test-lab",
            scenario_id="test-scenario",
            scenario_name="Test Scenario",
            username="testuser"
        )

        event = await session_recorder.record_command(
            lab_id="test-lab",
            container_id="container1",
            hostname="node1",
            command="whoami",
            output="root",
            exit_code=0,
            duration_ms=50
        )

        assert event is not None
        assert event.event_type == EventType.COMMAND_EXECUTED
        assert event.data["command"] == "whoami"
        assert event.data["output"] == "root"
        assert event.data["exit_code"] == 0
        assert event.data["duration_ms"] == 50

    @pytest.mark.asyncio
    async def test_get_session_summary(self):
        """Test getting session summary."""
        session = await session_recorder.start_recording(
            lab_id="test-lab",
            scenario_id="test-scenario",
            scenario_name="Test Scenario",
            username="testuser"
        )

        # Record some events
        await session_recorder.record_command(
            lab_id="test-lab",
            container_id="c1",
            hostname="node1",
            command="ls",
            output="file1",
            exit_code=0,
            duration_ms=10
        )

        await session_recorder.record_command(
            lab_id="test-lab",
            container_id="c1",
            hostname="node1",
            command="cat /etc/passwd",
            output="error",
            exit_code=1,
            duration_ms=20
        )

        summary = session_recorder.get_session_summary(session.session_id)

        assert summary["session_id"] == session.session_id
        assert summary["commands_executed"] == 2
        assert summary["successful_commands"] == 1

    @pytest.mark.asyncio
    async def test_get_playback_events(self):
        """Test getting events for playback."""
        session = await session_recorder.start_recording(
            lab_id="test-lab",
            scenario_id="test-scenario",
            scenario_name="Test Scenario",
            username="testuser"
        )

        await session_recorder.record_event(
            lab_id="test-lab",
            event_type=EventType.USER_ACTION,
            data={"action": "clicked button"}
        )

        await session_recorder.stop_recording(session.session_id)

        events = session_recorder.get_playback_events(session.session_id)

        assert len(events) >= 2  # At least LAB_STARTED and LAB_STOPPED
        assert "delay_ms" in events[0]
        assert "elapsed_ms" in events[0]


class TestRecordingEndpoints:
    """Tests for recording API endpoints."""

    def test_start_recording_endpoint(self):
        db.clear()
        active_scenarios.clear()
        lab_to_scenario.clear()
        orchestrator._labs.clear()

        token = get_admin_token()
        response = client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert data["lab_id"] == "test-lab-123"
        assert data["state"] == "recording"

    def test_stop_recording_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start recording first
        start_response = client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = start_response.json()["session_id"]

        # Stop recording
        response = client.post(
            f"/recordings/{session_id}/stop",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["state"] == "stopped"

    def test_pause_resume_recording_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start recording
        start_response = client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = start_response.json()["session_id"]

        # Pause
        pause_response = client.post(
            f"/recordings/{session_id}/pause",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert pause_response.status_code == 200
        assert pause_response.json()["state"] == "paused"

        # Resume
        resume_response = client.post(
            f"/recordings/{session_id}/resume",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert resume_response.status_code == 200
        assert resume_response.json()["state"] == "recording"

    def test_record_event_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start recording
        client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Record event
        response = client.post(
            "/recordings/labs/test-lab-123/events",
            json={
                "event_type": "user_action",
                "data": {"action": "clicked button"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "user_action"

    def test_record_command_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start recording
        client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Record command
        response = client.post(
            "/recordings/labs/test-lab-123/commands",
            json={
                "container_id": "container1",
                "hostname": "node1",
                "command": "ls -la",
                "output": "total 0",
                "exit_code": 0,
                "duration_ms": 50
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["event_type"] == "command_executed"
        assert data["data"]["command"] == "ls -la"

    def test_list_recordings_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start a recording
        client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/recordings",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_get_recording_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start recording
        start_response = client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = start_response.json()["session_id"]

        response = client.get(
            f"/recordings/{session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == session_id

    def test_get_recording_not_found(self):
        token = get_admin_token()
        response = client.get(
            "/recordings/nonexistent-session",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_get_recording_summary_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start recording
        start_response = client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = start_response.json()["session_id"]

        response = client.get(
            f"/recordings/{session_id}/summary",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "duration_seconds" in data

    def test_get_recording_events_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start recording
        start_response = client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = start_response.json()["session_id"]

        response = client.get(
            f"/recordings/{session_id}/events",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_playback_data_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start recording
        start_response = client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = start_response.json()["session_id"]

        # Stop recording first (required for playback)
        client.post(
            f"/recordings/{session_id}/stop",
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            f"/recordings/{session_id}/playback?speed=2.0",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "session" in data
        assert "events" in data
        assert data["playback_speed"] == 2.0

    def test_get_current_recording_endpoint(self):
        db.clear()
        token = get_admin_token()

        # Start recording
        client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/recordings/labs/test-lab-123/current",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["lab_id"] == "test-lab-123"

    def test_get_current_recording_not_found(self):
        token = get_admin_token()
        response = client.get(
            "/recordings/labs/nonexistent-lab/current",
            headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 404

    def test_trainee_can_record_events(self):
        db.clear()
        admin_token = get_admin_token()
        trainee_token = get_trainee_token()

        # Admin starts recording
        client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Trainee can record events
        response = client.post(
            "/recordings/labs/test-lab-123/events",
            json={
                "event_type": "user_action",
                "data": {"action": "trainee action"}
            },
            headers={"Authorization": f"Bearer {trainee_token}"}
        )

        assert response.status_code == 200

    def test_trainee_cannot_start_recording(self):
        trainee_token = get_trainee_token()

        response = client.post(
            "/recordings/start",
            json={
                "lab_id": "test-lab-123",
                "scenario_id": "scenario-456",
                "scenario_name": "Test Scenario"
            },
            headers={"Authorization": f"Bearer {trainee_token}"}
        )

        assert response.status_code == 403
