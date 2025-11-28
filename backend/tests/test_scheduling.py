"""Tests for scheduling functionality."""
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from main import app
from scheduling import (
    exercise_scheduler, ExerciseScheduler, ScheduleStatus, RecurrenceType,
    RecurrenceSettings, NotificationType
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_scheduler():
    """Reset scheduler state before each test."""
    exercise_scheduler._schedules.clear()
    exercise_scheduler._notifications.clear()
    exercise_scheduler._user_notifications.clear()
    yield
    exercise_scheduler._schedules.clear()
    exercise_scheduler._notifications.clear()
    exercise_scheduler._user_notifications.clear()


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


def future_time(hours: int = 1) -> datetime:
    """Get a datetime in the future."""
    return datetime.now(timezone.utc) + timedelta(hours=hours)


def future_time_str(hours: int = 1) -> str:
    """Get a datetime string in the future."""
    return future_time(hours).isoformat()


class TestExerciseScheduler:
    """Tests for the ExerciseScheduler class."""

    def test_create_schedule(self):
        """Test creating a schedule."""
        start = future_time(1)
        end = future_time(2)

        schedule = exercise_scheduler.create_schedule(
            title="Test Exercise",
            description="A test exercise",
            scenario_id="scenario-123",
            scenario_name="Test Scenario",
            created_by="admin",
            start_time=start,
            end_time=end
        )

        assert schedule.schedule_id is not None
        assert schedule.title == "Test Exercise"
        assert schedule.status == ScheduleStatus.SCHEDULED

    def test_create_schedule_past_time_fails(self):
        """Test that scheduling in the past fails."""
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(hours=1)

        with pytest.raises(ValueError, match="must be in the future"):
            exercise_scheduler.create_schedule(
                title="Past Exercise",
                description="Test",
                scenario_id="scenario-123",
                scenario_name="Test",
                created_by="admin",
                start_time=past,
                end_time=future
            )

    def test_create_schedule_invalid_times_fails(self):
        """Test that end time before start time fails."""
        start = future_time(2)
        end = future_time(1)

        with pytest.raises(ValueError, match="after start time"):
            exercise_scheduler.create_schedule(
                title="Invalid Exercise",
                description="Test",
                scenario_id="scenario-123",
                scenario_name="Test",
                created_by="admin",
                start_time=start,
                end_time=end
            )

    def test_add_participant(self):
        """Test adding a participant."""
        schedule = exercise_scheduler.create_schedule(
            title="Test",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=future_time(1),
            end_time=future_time(2)
        )

        updated = exercise_scheduler.add_participant(
            schedule.schedule_id, "trainee"
        )

        assert "trainee" in updated.participants

    def test_remove_participant(self):
        """Test removing a participant."""
        schedule = exercise_scheduler.create_schedule(
            title="Test",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=future_time(1),
            end_time=future_time(2),
            participants=["trainee"]
        )

        updated = exercise_scheduler.remove_participant(
            schedule.schedule_id, "trainee"
        )

        assert "trainee" not in updated.participants

    def test_start_exercise(self):
        """Test starting an exercise."""
        schedule = exercise_scheduler.create_schedule(
            title="Test",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=future_time(1),
            end_time=future_time(2)
        )

        updated = exercise_scheduler.start_exercise(
            schedule.schedule_id, "lab-123"
        )

        assert updated.status == ScheduleStatus.RUNNING
        assert updated.lab_id == "lab-123"

    def test_complete_exercise(self):
        """Test completing an exercise."""
        schedule = exercise_scheduler.create_schedule(
            title="Test",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=future_time(1),
            end_time=future_time(2)
        )
        exercise_scheduler.start_exercise(schedule.schedule_id, "lab-123")

        updated = exercise_scheduler.complete_exercise(schedule.schedule_id)

        assert updated.status == ScheduleStatus.COMPLETED

    def test_cancel_schedule(self):
        """Test cancelling a schedule."""
        schedule = exercise_scheduler.create_schedule(
            title="Test",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=future_time(1),
            end_time=future_time(2)
        )

        updated = exercise_scheduler.cancel_schedule(schedule.schedule_id)

        assert updated.status == ScheduleStatus.CANCELLED

    def test_recurring_schedule(self):
        """Test creating a recurring schedule."""
        recurrence = RecurrenceSettings(
            recurrence_type=RecurrenceType.WEEKLY,
            interval=1,
            max_occurrences=4
        )

        schedule = exercise_scheduler.create_schedule(
            title="Weekly Exercise",
            description="Recurring test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=future_time(1),
            end_time=future_time(2),
            recurrence=recurrence
        )

        assert schedule.recurrence is not None
        assert schedule.recurrence.recurrence_type == RecurrenceType.WEEKLY

    def test_get_next_occurrence(self):
        """Test getting next occurrence for recurring schedule."""
        start = future_time(1)
        recurrence = RecurrenceSettings(
            recurrence_type=RecurrenceType.DAILY,
            interval=1
        )

        schedule = exercise_scheduler.create_schedule(
            title="Daily Exercise",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=start,
            end_time=future_time(2),
            recurrence=recurrence
        )

        next_occurrence = schedule.get_next_occurrence()

        assert next_occurrence is not None
        assert next_occurrence > start

    def test_notifications_created(self):
        """Test that notifications are created for schedules."""
        schedule = exercise_scheduler.create_schedule(
            title="Test",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=future_time(1),
            end_time=future_time(2),
            participants=["trainee"],
            notifications_enabled=True
        )

        # Check admin got notification
        admin_notifications = exercise_scheduler.get_user_notifications("admin")
        assert len(admin_notifications) > 0

        # Check trainee got notification
        trainee_notifications = exercise_scheduler.get_user_notifications("trainee")
        assert len(trainee_notifications) > 0

    def test_mark_notification_read(self):
        """Test marking a notification as read."""
        exercise_scheduler.create_schedule(
            title="Test",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=future_time(1),
            end_time=future_time(2),
            notifications_enabled=True
        )

        notifications = exercise_scheduler.get_user_notifications("admin")
        notification_id = notifications[0].notification_id

        exercise_scheduler.mark_notification_read(notification_id)

        updated = exercise_scheduler.get_user_notifications("admin")
        assert any(n.is_read for n in updated)

    def test_get_upcoming_schedules(self):
        """Test getting upcoming schedules."""
        exercise_scheduler.create_schedule(
            title="Upcoming",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=future_time(24),  # Tomorrow
            end_time=future_time(25)
        )

        upcoming = exercise_scheduler.get_upcoming_schedules(days=7)

        assert len(upcoming) == 1

    def test_calendar_view(self):
        """Test calendar view."""
        start = future_time(1)
        exercise_scheduler.create_schedule(
            title="Calendar Test",
            description="Test",
            scenario_id="scenario-123",
            scenario_name="Test",
            created_by="admin",
            start_time=start,
            end_time=future_time(2)
        )

        calendar = exercise_scheduler.get_calendar_view(
            year=start.year,
            month=start.month
        )

        assert len(calendar) >= 1


class TestSchedulingEndpoints:
    """Tests for scheduling API endpoints."""

    def test_create_schedule_endpoint(self):
        token = get_admin_token()

        response = client.post(
            "/schedules",
            json={
                "title": "Test Exercise",
                "description": "A test exercise",
                "scenario_id": "scenario-123",
                "scenario_name": "Test Scenario",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2),
                "participants": ["trainee"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Test Exercise"
        assert data["status"] == "scheduled"

    def test_create_schedule_trainee_forbidden(self):
        token = get_trainee_token()

        response = client.post(
            "/schedules",
            json={
                "title": "Test",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    def test_list_schedules_endpoint(self):
        token = get_admin_token()

        # Create a schedule
        client.post(
            "/schedules",
            json={
                "title": "Test",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/schedules",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_schedule_endpoint(self):
        token = get_admin_token()

        # Create a schedule
        create_response = client.post(
            "/schedules",
            json={
                "title": "Test",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        schedule_id = create_response.json()["schedule_id"]

        response = client.get(
            f"/schedules/{schedule_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["schedule_id"] == schedule_id

    def test_update_schedule_endpoint(self):
        token = get_admin_token()

        # Create a schedule
        create_response = client.post(
            "/schedules",
            json={
                "title": "Original",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        schedule_id = create_response.json()["schedule_id"]

        response = client.put(
            f"/schedules/{schedule_id}",
            json={"title": "Updated"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["title"] == "Updated"

    def test_cancel_schedule_endpoint(self):
        token = get_admin_token()

        # Create a schedule
        create_response = client.post(
            "/schedules",
            json={
                "title": "Test",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        schedule_id = create_response.json()["schedule_id"]

        response = client.post(
            f"/schedules/{schedule_id}/cancel",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "cancelled"

    def test_add_participant_endpoint(self):
        token = get_admin_token()

        # Create a schedule
        create_response = client.post(
            "/schedules",
            json={
                "title": "Test",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        schedule_id = create_response.json()["schedule_id"]

        response = client.post(
            f"/schedules/{schedule_id}/participants/trainee",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert "trainee" in response.json()["participants"]

    def test_get_upcoming_endpoint(self):
        token = get_admin_token()

        # Create a schedule
        client.post(
            "/schedules",
            json={
                "title": "Upcoming",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(24),
                "end_time": future_time_str(25)
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/schedules/upcoming?days=7",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

    def test_get_calendar_endpoint(self):
        token = get_admin_token()
        now = datetime.now(timezone.utc)

        response = client.get(
            f"/schedules/calendar/{now.year}/{now.month}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    def test_get_my_schedules_endpoint(self):
        token = get_admin_token()

        # Create a schedule
        client.post(
            "/schedules",
            json={
                "title": "My Schedule",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/schedules/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_notifications_endpoint(self):
        token = get_admin_token()

        # Create a schedule (generates notification)
        client.post(
            "/schedules",
            json={
                "title": "Test",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/notifications",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert len(response.json()) >= 1

    def test_get_unread_count_endpoint(self):
        token = get_admin_token()

        # Create a schedule (generates notification)
        client.post(
            "/schedules",
            json={
                "title": "Test",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/notifications/unread-count",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["unread_count"] >= 1

    def test_mark_notification_read_endpoint(self):
        token = get_admin_token()

        # Create a schedule (generates notification)
        client.post(
            "/schedules",
            json={
                "title": "Test",
                "description": "Test",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2)
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Get notifications
        notifications = client.get(
            "/notifications",
            headers={"Authorization": f"Bearer {token}"}
        ).json()
        notification_id = notifications[0]["notification_id"]

        response = client.post(
            f"/notifications/{notification_id}/read",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["is_read"] is True

    def test_mark_all_read_endpoint(self):
        token = get_admin_token()

        # Create schedules (generates notifications)
        for i in range(3):
            client.post(
                "/schedules",
                json={
                    "title": f"Test {i}",
                    "description": "Test",
                    "scenario_id": "scenario-123",
                    "scenario_name": "Test",
                    "start_time": future_time_str(i + 1),
                    "end_time": future_time_str(i + 2)
                },
                headers={"Authorization": f"Bearer {token}"}
            )

        response = client.post(
            "/notifications/read-all",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["marked_read"] >= 3

    def test_create_recurring_schedule_endpoint(self):
        token = get_admin_token()

        response = client.post(
            "/schedules",
            json={
                "title": "Weekly Exercise",
                "description": "Recurring",
                "scenario_id": "scenario-123",
                "scenario_name": "Test",
                "start_time": future_time_str(1),
                "end_time": future_time_str(2),
                "recurrence": {
                    "recurrence_type": "weekly",
                    "interval": 1,
                    "max_occurrences": 4
                }
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["recurrence"] is not None
        assert data["recurrence"]["recurrence_type"] == "weekly"
