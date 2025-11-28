"""Tests for authentication and audit logging."""
from fastapi.testclient import TestClient
from main import app
from auth import users_db, UserRole
from audit import clear_audit_logs

client = TestClient(app)


def setup_function():
    """Clear audit logs before each test."""
    clear_audit_logs()


def test_login_success():
    """Test successful login with default admin user."""
    response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials():
    """Test login with invalid credentials."""
    response = client.post("/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


def test_login_nonexistent_user():
    """Test login with nonexistent user."""
    response = client.post("/auth/login", json={
        "username": "nonexistent",
        "password": "password"
    })
    assert response.status_code == 401


def test_get_current_user():
    """Test getting current user info."""
    # First login to get token
    login_response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]

    # Get user info
    response = client.get("/auth/me", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "admin"
    assert data["role"] == UserRole.ADMIN


def test_get_current_user_no_token():
    """Test getting current user without token."""
    response = client.get("/auth/me")
    assert response.status_code == 401  # Unauthorized when no token


def test_get_current_user_invalid_token():
    """Test getting current user with invalid token."""
    response = client.get("/auth/me", headers={
        "Authorization": "Bearer invalid_token"
    })
    assert response.status_code == 401


def test_register_user_as_admin():
    """Test registering a new user as admin."""
    # Login as admin
    login_response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]

    # Register new user
    response = client.post(
        "/auth/register",
        json={
            "username": "newuser",
            "password": "newpass123",
            "email": "new@example.com",
            "role": UserRole.TRAINEE
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "newuser"
    assert data["role"] == UserRole.TRAINEE

    # Clean up
    if "newuser" in users_db:
        del users_db["newuser"]


def test_register_user_as_trainee_forbidden():
    """Test that trainees cannot register new users."""
    # Login as trainee
    login_response = client.post("/auth/login", json={
        "username": "trainee",
        "password": "trainee123"
    })
    token = login_response.json()["access_token"]

    # Try to register - should be forbidden
    response = client.post(
        "/auth/register",
        json={
            "username": "anotheruser",
            "password": "pass123",
            "role": UserRole.TRAINEE
        },
        headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 403


def test_audit_logs_as_admin():
    """Test viewing audit logs as admin."""
    clear_audit_logs()

    # Login as admin to generate audit entry
    login_response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]

    # Get audit logs
    response = client.get("/audit/logs", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200
    logs = response.json()
    assert isinstance(logs, list)
    # Should have at least the login entry
    assert len(logs) >= 1


def test_audit_logs_as_instructor():
    """Test viewing audit logs as instructor."""
    # Login as instructor
    login_response = client.post("/auth/login", json={
        "username": "instructor",
        "password": "instructor123"
    })
    token = login_response.json()["access_token"]

    # Get audit logs
    response = client.get("/audit/logs", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 200


def test_audit_logs_as_trainee_forbidden():
    """Test that trainees cannot view audit logs."""
    # Login as trainee
    login_response = client.post("/auth/login", json={
        "username": "trainee",
        "password": "trainee123"
    })
    token = login_response.json()["access_token"]

    # Try to get audit logs - should be forbidden
    response = client.get("/audit/logs", headers={
        "Authorization": f"Bearer {token}"
    })
    assert response.status_code == 403


def test_failed_login_audit():
    """Test that failed logins are audited."""
    clear_audit_logs()

    # Attempt failed login
    client.post("/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })

    # Login as admin to check audit logs
    login_response = client.post("/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_response.json()["access_token"]

    # Get audit logs
    response = client.get("/audit/logs", headers={
        "Authorization": f"Bearer {token}"
    })
    logs = response.json()

    # Should have a failed login entry
    failed_logins = [log for log in logs if log["action"] == "failed_login"]
    assert len(failed_logins) >= 1
