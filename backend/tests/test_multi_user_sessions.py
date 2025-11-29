"""Tests for multi-user session functionality."""
import pytest
from fastapi.testclient import TestClient
from main import app
from multi_user_sessions import (
    multi_user_manager, MultiUserSessionManager, TeamRole, SessionType,
    ParticipantStatus, MultiUserSession
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_multi_user_manager():
    """Reset multi-user manager state before each test."""
    multi_user_manager._sessions.clear()
    multi_user_manager._user_sessions.clear()
    multi_user_manager._lab_sessions.clear()
    yield
    multi_user_manager._sessions.clear()
    multi_user_manager._user_sessions.clear()
    multi_user_manager._lab_sessions.clear()


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


class TestMultiUserSessionManager:
    """Tests for the MultiUserSessionManager class."""

    def test_create_session(self):
        """Test creating a multi-user session."""
        session = multi_user_manager.create_session(
            name="Test Session",
            description="A test session",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COLLABORATIVE,
            host_username="testhost"
        )

        assert session.session_id is not None
        assert session.name == "Test Session"
        assert session.host_username == "testhost"
        assert session.is_active is True

    def test_create_competitive_session_creates_teams(self):
        """Test that competitive sessions get default teams."""
        session = multi_user_manager.create_session(
            name="Red vs Blue",
            description="Competitive session",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COMPETITIVE,
            host_username="testhost"
        )

        assert len(session.teams) == 3  # Red, Blue, White
        team_roles = [t.role for t in session.teams.values()]
        assert TeamRole.RED_TEAM in team_roles
        assert TeamRole.BLUE_TEAM in team_roles
        assert TeamRole.WHITE_TEAM in team_roles

    def test_duplicate_lab_session_fails(self):
        """Test that creating a second session for same lab fails."""
        multi_user_manager.create_session(
            name="First Session",
            description="First",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COLLABORATIVE,
            host_username="host1"
        )

        with pytest.raises(ValueError, match="already has an active session"):
            multi_user_manager.create_session(
                name="Second Session",
                description="Second",
                lab_id="lab-123",
                scenario_id="scenario-789",
                session_type=SessionType.COLLABORATIVE,
                host_username="host2"
            )

    def test_add_participant(self):
        """Test adding a participant to a session."""
        session = multi_user_manager.create_session(
            name="Test Session",
            description="Test",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COLLABORATIVE,
            host_username="host"
        )

        participant = multi_user_manager.add_participant(
            session_id=session.session_id,
            username="testuser",
            display_name="Test User",
            team_role=TeamRole.BLUE_TEAM
        )

        assert participant is not None
        assert participant.username == "testuser"
        assert participant.status == ParticipantStatus.INVITED

    def test_add_duplicate_participant_fails(self):
        """Test that adding same user twice fails."""
        session = multi_user_manager.create_session(
            name="Test Session",
            description="Test",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COLLABORATIVE,
            host_username="host"
        )

        multi_user_manager.add_participant(
            session_id=session.session_id,
            username="testuser",
            display_name="Test User",
            team_role=TeamRole.BLUE_TEAM
        )

        with pytest.raises(ValueError, match="already in the session"):
            multi_user_manager.add_participant(
                session_id=session.session_id,
                username="testuser",
                display_name="Test User",
                team_role=TeamRole.RED_TEAM
            )

    def test_join_session(self):
        """Test joining a session."""
        session = multi_user_manager.create_session(
            name="Test Session",
            description="Test",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COLLABORATIVE,
            host_username="host"
        )

        multi_user_manager.add_participant(
            session_id=session.session_id,
            username="testuser",
            display_name="Test User",
            team_role=TeamRole.BLUE_TEAM
        )

        participant = multi_user_manager.join_session(
            session_id=session.session_id,
            username="testuser"
        )

        assert participant.status == ParticipantStatus.JOINED
        assert participant.joined_at is not None

    def test_start_session(self):
        """Test starting a session."""
        session = multi_user_manager.create_session(
            name="Test Session",
            description="Test",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COLLABORATIVE,
            host_username="host"
        )

        updated = multi_user_manager.start_session(session.session_id)

        assert updated.started_at is not None
        assert updated.is_locked is True

    def test_end_session(self):
        """Test ending a session."""
        session = multi_user_manager.create_session(
            name="Test Session",
            description="Test",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COLLABORATIVE,
            host_username="host"
        )

        updated = multi_user_manager.end_session(session.session_id)

        assert updated.is_active is False
        assert updated.ended_at is not None

    def test_send_message(self):
        """Test sending a chat message."""
        session = multi_user_manager.create_session(
            name="Test Session",
            description="Test",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COLLABORATIVE,
            host_username="host"
        )

        message = multi_user_manager.send_message(
            session_id=session.session_id,
            sender_username="host",
            sender_display_name="Host",
            content="Hello team!"
        )

        assert message is not None
        assert message.content == "Hello team!"

    def test_team_only_messages(self):
        """Test team-only message visibility."""
        session = multi_user_manager.create_session(
            name="Competitive",
            description="Test",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COMPETITIVE,
            host_username="host"
        )

        # Add red team member
        multi_user_manager.add_participant(
            session_id=session.session_id,
            username="red_player",
            display_name="Red Player",
            team_role=TeamRole.RED_TEAM
        )

        # Add blue team member
        multi_user_manager.add_participant(
            session_id=session.session_id,
            username="blue_player",
            display_name="Blue Player",
            team_role=TeamRole.BLUE_TEAM
        )

        # Send team-only message from red
        multi_user_manager.send_message(
            session_id=session.session_id,
            sender_username="red_player",
            sender_display_name="Red Player",
            content="Red team secret",
            is_team_only=True
        )

        # Red player should see it
        red_messages = multi_user_manager.get_messages(
            session_id=session.session_id,
            username="red_player"
        )
        assert any(m.content == "Red team secret" for m in red_messages)

        # Blue player should NOT see it
        blue_messages = multi_user_manager.get_messages(
            session_id=session.session_id,
            username="blue_player"
        )
        assert not any(m.content == "Red team secret" for m in blue_messages)

    def test_add_and_complete_objective(self):
        """Test adding and completing an objective."""
        session = multi_user_manager.create_session(
            name="Competitive",
            description="Test",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COMPETITIVE,
            host_username="host"
        )

        # Get a team ID
        team_id = list(session.teams.keys())[0]
        team = session.teams[team_id]
        initial_score = team.score

        # Add objective
        objective = multi_user_manager.add_objective(
            session_id=session.session_id,
            name="Capture the flag",
            description="Find and capture the flag",
            points=100
        )

        # Complete it
        completed = multi_user_manager.complete_objective(
            session_id=session.session_id,
            objective_id=objective.objective_id,
            team_id=team_id
        )

        assert completed.completed_by == team_id
        assert team.score == initial_score + 100

    def test_assign_container(self):
        """Test assigning a container to a participant."""
        session = multi_user_manager.create_session(
            name="Test",
            description="Test",
            lab_id="lab-123",
            scenario_id="scenario-456",
            session_type=SessionType.COLLABORATIVE,
            host_username="host"
        )

        participant = multi_user_manager.add_participant(
            session_id=session.session_id,
            username="testuser",
            display_name="Test User",
            team_role=TeamRole.PURPLE_TEAM
        )

        result = multi_user_manager.assign_container(
            session_id=session.session_id,
            participant_id=participant.participant_id,
            container_id="container-abc"
        )

        assert result is True
        assert "container-abc" in participant.assigned_containers


class TestMultiUserSessionEndpoints:
    """Tests for multi-user session API endpoints."""

    def test_create_session_endpoint(self):
        token = get_admin_token()

        response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "A test session",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative",
                "max_participants": 10
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Session"
        assert data["is_active"] is True

    def test_create_session_trainee_forbidden(self):
        token = get_trainee_token()

        response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    def test_list_sessions_endpoint(self):
        token = get_admin_token()

        # Create a session first
        client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/sessions",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_get_session_endpoint(self):
        token = get_admin_token()

        # Create a session
        create_response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = create_response.json()["session_id"]

        response = client.get(
            f"/sessions/{session_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["session_id"] == session_id

    def test_start_session_endpoint(self):
        token = get_admin_token()

        # Create a session
        create_response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = create_response.json()["session_id"]

        response = client.post(
            f"/sessions/{session_id}/start",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["started_at"] is not None

    def test_end_session_endpoint(self):
        token = get_admin_token()

        # Create a session
        create_response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = create_response.json()["session_id"]

        response = client.post(
            f"/sessions/{session_id}/end",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["is_active"] is False

    def test_add_participant_endpoint(self):
        token = get_admin_token()

        # Create a session
        create_response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "competitive"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = create_response.json()["session_id"]

        response = client.post(
            f"/sessions/{session_id}/participants",
            json={
                "username": "trainee",
                "display_name": "Test Trainee",
                "team_role": "red_team"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["username"] == "trainee"

    def test_join_session_endpoint(self):
        admin_token = get_admin_token()
        trainee_token = get_trainee_token()

        # Create a session and add trainee
        create_response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        session_id = create_response.json()["session_id"]

        client.post(
            f"/sessions/{session_id}/participants",
            json={
                "username": "trainee",
                "display_name": "Trainee",
                "team_role": "purple_team"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        # Trainee joins
        response = client.post(
            f"/sessions/{session_id}/join",
            headers={"Authorization": f"Bearer {trainee_token}"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "joined"

    def test_send_message_endpoint(self):
        token = get_admin_token()

        # Create a session
        create_response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = create_response.json()["session_id"]

        response = client.post(
            f"/sessions/{session_id}/messages",
            json={"content": "Hello everyone!", "is_team_only": False},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["content"] == "Hello everyone!"

    def test_get_messages_endpoint(self):
        token = get_admin_token()

        # Create a session and send messages
        create_response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = create_response.json()["session_id"]

        client.post(
            f"/sessions/{session_id}/messages",
            json={"content": "Message 1"},
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            f"/sessions/{session_id}/messages",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1

    def test_add_objective_endpoint(self):
        token = get_admin_token()

        # Create a session
        create_response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "competitive"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = create_response.json()["session_id"]

        response = client.post(
            f"/sessions/{session_id}/objectives",
            json={
                "name": "Capture Flag",
                "description": "Find the flag file",
                "points": 50
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["points"] == 50

    def test_get_scores_endpoint(self):
        token = get_admin_token()

        # Create a competitive session
        create_response = client.post(
            "/sessions",
            json={
                "name": "Test Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "competitive"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        session_id = create_response.json()["session_id"]

        response = client.get(
            f"/sessions/{session_id}/scores",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "teams" in data
        assert "objectives" in data

    def test_get_my_sessions_endpoint(self):
        token = get_admin_token()

        # Create a session (admin is auto-added as host)
        client.post(
            "/sessions",
            json={
                "name": "My Session",
                "description": "Test",
                "lab_id": "lab-123",
                "scenario_id": "scenario-456",
                "session_type": "collaborative"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/sessions/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
