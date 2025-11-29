"""Tests for progress tracking functionality."""
import pytest
from fastapi.testclient import TestClient
from main import app, db
from progress_tracking import (
    progress_tracker, ProgressTracker, CompletionStatus, SkillLevel,
    ExerciseProgress, TraineeProfile, BADGES
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_progress_tracker():
    """Reset progress tracker state before each test."""
    progress_tracker._profiles.clear()
    progress_tracker._progress.clear()
    progress_tracker._user_progress.clear()
    yield
    progress_tracker._profiles.clear()
    progress_tracker._progress.clear()
    progress_tracker._user_progress.clear()


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


class TestProgressTracker:
    """Tests for the ProgressTracker class."""

    def test_get_or_create_profile(self):
        """Test creating a trainee profile."""
        profile = progress_tracker.get_or_create_profile("testuser", "Test User")

        assert profile.username == "testuser"
        assert profile.display_name == "Test User"
        assert profile.total_exercises_completed == 0

    def test_start_exercise(self):
        """Test starting an exercise."""
        progress = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex1",
            exercise_name="Test Exercise",
            scenario_id="scenario1",
            objectives_total=5,
            max_score=100.0
        )

        assert progress.exercise_id == "ex1"
        assert progress.username == "testuser"
        assert progress.status == CompletionStatus.IN_PROGRESS
        assert progress.objectives_total == 5
        assert progress.attempts == 1

    def test_complete_objective(self):
        """Test completing an objective."""
        progress = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex1",
            exercise_name="Test Exercise",
            scenario_id="scenario1"
        )

        result = progress_tracker.complete_objective(
            progress_id=progress.progress_id,
            objective_id="obj1",
            points_earned=20
        )

        assert "obj1" in result.objectives_completed
        assert result.score == 20

    def test_complete_exercise(self):
        """Test completing an exercise."""
        progress = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex1",
            exercise_name="Test Exercise",
            scenario_id="scenario1"
        )

        result = progress_tracker.complete_exercise(
            progress_id=progress.progress_id,
            final_score=85,
            notes="Great job!"
        )

        assert result.status == CompletionStatus.COMPLETED
        assert result.score == 85
        assert result.notes == "Great job!"

        # Check profile was updated
        profile = progress_tracker.get_profile("testuser")
        assert profile.total_exercises_completed == 1

    def test_fail_exercise(self):
        """Test failing an exercise."""
        progress = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex1",
            exercise_name="Test Exercise",
            scenario_id="scenario1"
        )

        result = progress_tracker.fail_exercise(
            progress_id=progress.progress_id,
            notes="Need more practice"
        )

        assert result.status == CompletionStatus.FAILED
        assert result.notes == "Need more practice"

    def test_add_hint_used(self):
        """Test recording hint usage."""
        progress = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex1",
            exercise_name="Test Exercise",
            scenario_id="scenario1"
        )

        progress_tracker.add_hint_used(progress.progress_id)
        progress_tracker.add_hint_used(progress.progress_id)

        assert progress.hints_used == 2

    def test_assess_skill(self):
        """Test skill assessment."""
        assessment = progress_tracker.assess_skill(
            username="testuser",
            skill_name="Packet Analysis",
            skill_category="network_security",
            experience_gained=100
        )

        assert assessment.skill_name == "Packet Analysis"
        assert assessment.experience_points == 100
        assert assessment.level == SkillLevel.BEGINNER

    def test_skill_level_progression(self):
        """Test skill level progression based on experience."""
        # Start with novice
        assessment = progress_tracker.assess_skill(
            username="testuser",
            skill_name="Test Skill",
            skill_category="test",
            experience_gained=10
        )
        assert assessment.level == SkillLevel.NOVICE

        # Progress to beginner (50+)
        assessment = progress_tracker.assess_skill(
            username="testuser",
            skill_name="Test Skill",
            skill_category="test",
            experience_gained=50
        )
        assert assessment.level == SkillLevel.BEGINNER

        # Progress to intermediate (200+)
        assessment = progress_tracker.assess_skill(
            username="testuser",
            skill_name="Test Skill",
            skill_category="test",
            experience_gained=150
        )
        assert assessment.level == SkillLevel.INTERMEDIATE

    def test_first_exercise_badge(self):
        """Test awarding first exercise badge."""
        progress = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex1",
            exercise_name="Test Exercise",
            scenario_id="scenario1"
        )

        progress_tracker.complete_exercise(progress.progress_id, final_score=50)

        profile = progress_tracker.get_profile("testuser")
        assert "first_exercise" in profile.badges

    def test_no_hints_badge(self):
        """Test awarding no hints badge."""
        progress = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex1",
            exercise_name="Test Exercise",
            scenario_id="scenario1"
        )

        progress_tracker.complete_exercise(progress.progress_id, final_score=50)

        profile = progress_tracker.get_profile("testuser")
        assert "no_hints" in profile.badges

    def test_perfectionist_badge(self):
        """Test awarding perfectionist badge for 100% score."""
        progress = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex1",
            exercise_name="Test Exercise",
            scenario_id="scenario1",
            max_score=100.0
        )

        progress_tracker.complete_exercise(progress.progress_id, final_score=100)

        profile = progress_tracker.get_profile("testuser")
        assert "perfectionist" in profile.badges

    def test_get_progress_report(self):
        """Test generating progress report."""
        # Complete some exercises
        progress1 = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex1",
            exercise_name="Exercise 1",
            scenario_id="scenario1"
        )
        progress_tracker.complete_exercise(progress1.progress_id, final_score=80)

        progress2 = progress_tracker.start_exercise(
            username="testuser",
            exercise_id="ex2",
            exercise_name="Exercise 2",
            scenario_id="scenario1"
        )
        progress_tracker.complete_exercise(progress2.progress_id, final_score=90)

        report = progress_tracker.get_progress_report("testuser")

        assert report["summary"]["exercises_completed"] == 2
        assert report["summary"]["average_score"] == 85.0

    def test_get_leaderboard(self):
        """Test leaderboard generation."""
        # Create profiles with different scores
        p1 = progress_tracker.start_exercise(
            username="user1",
            exercise_id="ex1",
            exercise_name="Exercise 1",
            scenario_id="scenario1"
        )
        progress_tracker.complete_exercise(p1.progress_id, final_score=100)

        p2 = progress_tracker.start_exercise(
            username="user2",
            exercise_id="ex1",
            exercise_name="Exercise 1",
            scenario_id="scenario1"
        )
        progress_tracker.complete_exercise(p2.progress_id, final_score=50)

        leaderboard = progress_tracker.get_leaderboard("score", limit=10)

        assert len(leaderboard) == 2
        assert leaderboard[0]["username"] == "user1"
        assert leaderboard[1]["username"] == "user2"


class TestProgressEndpoints:
    """Tests for progress tracking API endpoints."""

    def test_start_exercise_endpoint(self):
        db.clear()
        token = get_trainee_token()

        response = client.post(
            "/progress/exercises/start",
            json={
                "exercise_id": "ex1",
                "exercise_name": "Test Exercise",
                "scenario_id": "scenario1"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "progress_id" in data
        assert data["status"] == "in_progress"

    def test_complete_objective_endpoint(self):
        db.clear()
        token = get_trainee_token()

        # Start exercise
        start_response = client.post(
            "/progress/exercises/start",
            json={
                "exercise_id": "ex1",
                "exercise_name": "Test Exercise",
                "scenario_id": "scenario1"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        progress_id = start_response.json()["progress_id"]

        # Complete objective
        response = client.post(
            f"/progress/exercises/{progress_id}/objectives",
            json={"objective_id": "obj1", "points_earned": 25},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "obj1" in data["objectives_completed"]

    def test_complete_exercise_endpoint(self):
        db.clear()
        token = get_trainee_token()

        # Start exercise
        start_response = client.post(
            "/progress/exercises/start",
            json={
                "exercise_id": "ex1",
                "exercise_name": "Test Exercise",
                "scenario_id": "scenario1"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        progress_id = start_response.json()["progress_id"]

        # Complete exercise
        response = client.post(
            f"/progress/exercises/{progress_id}/complete",
            json={"final_score": 85, "notes": "Good work"},
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["score"] == 85

    def test_record_hint_endpoint(self):
        db.clear()
        token = get_trainee_token()

        # Start exercise
        start_response = client.post(
            "/progress/exercises/start",
            json={
                "exercise_id": "ex1",
                "exercise_name": "Test Exercise",
                "scenario_id": "scenario1"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        progress_id = start_response.json()["progress_id"]

        # Record hint
        response = client.post(
            f"/progress/exercises/{progress_id}/hint",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["hints_used"] == 1

    def test_get_my_progress_endpoint(self):
        db.clear()
        token = get_trainee_token()

        # Start exercise
        client.post(
            "/progress/exercises/start",
            json={
                "exercise_id": "ex1",
                "exercise_name": "Test Exercise",
                "scenario_id": "scenario1"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/progress/me",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_get_my_report_endpoint(self):
        db.clear()
        token = get_trainee_token()

        response = client.get(
            "/progress/me/report",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200

    def test_assess_skill_endpoint(self):
        db.clear()
        token = get_trainee_token()

        response = client.post(
            "/progress/skills/assess",
            json={
                "skill_name": "Packet Analysis",
                "skill_category": "network_security",
                "experience_gained": 50
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["skill_name"] == "Packet Analysis"
        assert data["experience_points"] == 50

    def test_get_leaderboard_endpoint(self):
        db.clear()
        token = get_trainee_token()

        response = client.get(
            "/progress/leaderboard?metric=score",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_badges_endpoint(self):
        db.clear()
        token = get_trainee_token()

        response = client.get(
            "/progress/badges",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) > 0
        assert all("badge_id" in badge for badge in data)

    def test_get_skill_categories_endpoint(self):
        db.clear()
        token = get_trainee_token()

        response = client.get(
            "/progress/skill-categories",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "network_security" in data

    def test_admin_can_view_user_progress(self):
        db.clear()
        admin_token = get_admin_token()
        trainee_token = get_trainee_token()

        # Trainee starts exercise
        client.post(
            "/progress/exercises/start",
            json={
                "exercise_id": "ex1",
                "exercise_name": "Test Exercise",
                "scenario_id": "scenario1"
            },
            headers={"Authorization": f"Bearer {trainee_token}"}
        )

        # Admin views trainee progress
        response = client.get(
            "/progress/users/trainee",
            headers={"Authorization": f"Bearer {admin_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_trainee_cannot_view_other_users(self):
        db.clear()
        trainee_token = get_trainee_token()

        response = client.get(
            "/progress/users/admin",
            headers={"Authorization": f"Bearer {trainee_token}"}
        )

        assert response.status_code == 403

    def test_invalid_leaderboard_metric(self):
        db.clear()
        token = get_trainee_token()

        response = client.get(
            "/progress/leaderboard?metric=invalid",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 400
