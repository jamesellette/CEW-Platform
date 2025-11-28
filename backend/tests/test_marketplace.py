"""Tests for marketplace functionality."""
import pytest
from fastapi.testclient import TestClient
from main import app
from marketplace import (
    marketplace, TemplateMarketplace, TemplateCategory, DifficultyLevel,
    TemplateStatus, ScenarioTemplate
)


client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_marketplace():
    """Reset marketplace state before each test (keep built-in templates)."""
    # Save built-in templates
    builtin_ids = [tid for tid in marketplace._templates.keys() if tid.startswith("builtin-")]
    builtin_templates = {tid: marketplace._templates[tid] for tid in builtin_ids}

    # Clear and restore
    marketplace._templates.clear()
    marketplace._templates.update(builtin_templates)

    yield

    # Reset again after test
    marketplace._templates.clear()
    marketplace._templates.update(builtin_templates)


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


class TestMarketplaceCore:
    """Tests for the TemplateMarketplace class."""

    def test_built_in_templates_exist(self):
        """Test that built-in templates are initialized."""
        assert "builtin-network-defense" in marketplace._templates
        assert "builtin-incident-response" in marketplace._templates
        assert "builtin-cyber-warfare" in marketplace._templates

    def test_create_template(self):
        """Test creating a new template."""
        template = marketplace.create_template(
            name="Test Template",
            description="A test template",
            author="testuser",
            category=TemplateCategory.NETWORK_DEFENSE,
            difficulty=DifficultyLevel.BEGINNER,
            tags=["test", "demo"]
        )

        assert template.template_id is not None
        assert template.name == "Test Template"
        assert template.status == TemplateStatus.DRAFT
        assert template.author == "testuser"

    def test_add_version(self):
        """Test adding a version to a template."""
        template = marketplace.create_template(
            name="Version Test",
            description="Test versioning",
            author="testuser",
            category=TemplateCategory.FORENSICS,
            difficulty=DifficultyLevel.INTERMEDIATE
        )

        version = marketplace.add_version(
            template_id=template.template_id,
            version="1.0.0",
            changelog="Initial release",
            scenario_data={"name": "Test", "topology": {}},
            created_by="testuser"
        )

        assert version is not None
        assert version.version == "1.0.0"
        assert template.get_current_version() == "1.0.0"

    def test_add_version_invalid_format(self):
        """Test that invalid version format is rejected."""
        template = marketplace.create_template(
            name="Version Test",
            description="Test versioning",
            author="testuser",
            category=TemplateCategory.FORENSICS,
            difficulty=DifficultyLevel.INTERMEDIATE
        )

        with pytest.raises(ValueError, match="must be in format"):
            marketplace.add_version(
                template_id=template.template_id,
                version="v1",
                changelog="Bad version",
                scenario_data={},
                created_by="testuser"
            )

    def test_submit_for_review(self):
        """Test submitting template for review."""
        template = marketplace.create_template(
            name="Review Test",
            description="Test review process",
            author="testuser",
            category=TemplateCategory.AWARENESS,
            difficulty=DifficultyLevel.BEGINNER
        )

        # Add a version first (required)
        marketplace.add_version(
            template_id=template.template_id,
            version="1.0.0",
            changelog="Initial",
            scenario_data={"name": "Test"},
            created_by="testuser"
        )

        updated = marketplace.submit_for_review(template.template_id)
        assert updated.status == TemplateStatus.PENDING_REVIEW

    def test_submit_without_version_fails(self):
        """Test that submitting without versions fails."""
        template = marketplace.create_template(
            name="No Version",
            description="No version added",
            author="testuser",
            category=TemplateCategory.OTHER,
            difficulty=DifficultyLevel.BEGINNER
        )

        with pytest.raises(ValueError, match="at least one version"):
            marketplace.submit_for_review(template.template_id)

    def test_approve_template(self):
        """Test approving a template."""
        template = marketplace.create_template(
            name="Approve Test",
            description="Test approval",
            author="testuser",
            category=TemplateCategory.MALWARE_ANALYSIS,
            difficulty=DifficultyLevel.ADVANCED
        )

        marketplace.add_version(
            template_id=template.template_id,
            version="1.0.0",
            changelog="Initial",
            scenario_data={"name": "Test"},
            created_by="testuser"
        )

        marketplace.submit_for_review(template.template_id)
        approved = marketplace.approve_template(template.template_id)

        assert approved.status == TemplateStatus.PUBLISHED

    def test_add_review(self):
        """Test adding a review to a published template."""
        # Use built-in published template
        review = marketplace.add_review(
            template_id="builtin-network-defense",
            username="reviewer",
            rating=5,
            title="Great template",
            comment="Very helpful for learning"
        )

        assert review is not None
        assert review.rating == 5

    def test_review_rating_validation(self):
        """Test that invalid ratings are rejected."""
        with pytest.raises(ValueError, match="between 1 and 5"):
            marketplace.add_review(
                template_id="builtin-network-defense",
                username="badreviewer",
                rating=10,
                title="Bad rating",
                comment="Invalid"
            )

    def test_duplicate_review_rejected(self):
        """Test that duplicate reviews are rejected."""
        marketplace.add_review(
            template_id="builtin-incident-response",
            username="onereviewer",
            rating=4,
            title="First review",
            comment="Good"
        )

        with pytest.raises(ValueError, match="already reviewed"):
            marketplace.add_review(
                template_id="builtin-incident-response",
                username="onereviewer",
                rating=5,
                title="Second review",
                comment="Another"
            )

    def test_download_template(self):
        """Test downloading a template."""
        result = marketplace.download_template("builtin-network-defense")

        assert result is not None
        assert "scenario_data" in result
        assert result["version"] == "1.0.0"

    def test_download_increments_count(self):
        """Test that download count increases."""
        template = marketplace.get_template("builtin-cyber-warfare")
        initial_count = template.download_count

        marketplace.download_template("builtin-cyber-warfare")

        assert template.download_count == initial_count + 1

    def test_list_templates(self):
        """Test listing templates with filters."""
        templates = marketplace.list_templates(
            category=TemplateCategory.NETWORK_DEFENSE
        )

        assert len(templates) >= 1
        assert all(t.category == TemplateCategory.NETWORK_DEFENSE for t in templates)

    def test_get_categories(self):
        """Test getting categories with counts."""
        categories = marketplace.get_categories()

        assert len(categories) == len(TemplateCategory)
        assert any(c["count"] > 0 for c in categories)

    def test_get_statistics(self):
        """Test getting marketplace statistics."""
        stats = marketplace.get_statistics()

        assert "total_templates" in stats
        assert "published_templates" in stats
        assert stats["published_templates"] >= 3  # Built-in templates


class TestMarketplaceEndpoints:
    """Tests for marketplace API endpoints."""

    def test_list_templates_endpoint(self):
        token = get_trainee_token()

        response = client.get(
            "/marketplace/templates",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3  # Built-in templates

    def test_get_template_endpoint(self):
        token = get_trainee_token()

        response = client.get(
            "/marketplace/templates/builtin-network-defense",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Network Defense Basics"
        assert "reviews" in data
        assert "versions" in data

    def test_get_template_not_found(self):
        token = get_trainee_token()

        response = client.get(
            "/marketplace/templates/nonexistent",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    def test_create_template_endpoint(self):
        token = get_instructor_token()

        response = client.post(
            "/marketplace/templates",
            json={
                "name": "New Template",
                "description": "A new template for testing",
                "category": "network_defense",
                "difficulty": "beginner",
                "tags": ["test"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "New Template"
        assert data["status"] == "draft"

    def test_create_template_trainee_forbidden(self):
        token = get_trainee_token()

        response = client.post(
            "/marketplace/templates",
            json={
                "name": "Trainee Template",
                "description": "Should fail",
                "category": "network_defense",
                "difficulty": "beginner"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403

    def test_add_version_endpoint(self):
        token = get_admin_token()

        # Create template first
        create_response = client.post(
            "/marketplace/templates",
            json={
                "name": "Version Test",
                "description": "Testing versions",
                "category": "forensics",
                "difficulty": "intermediate"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        template_id = create_response.json()["template_id"]

        # Add version
        response = client.post(
            f"/marketplace/templates/{template_id}/versions",
            json={
                "version": "1.0.0",
                "changelog": "Initial release",
                "scenario_data": {"name": "Test Scenario", "topology": {}}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.0.0"

    def test_submit_for_review_endpoint(self):
        token = get_admin_token()

        # Create and add version
        create_response = client.post(
            "/marketplace/templates",
            json={
                "name": "Submit Test",
                "description": "Testing submission",
                "category": "incident_response",
                "difficulty": "advanced"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        template_id = create_response.json()["template_id"]

        client.post(
            f"/marketplace/templates/{template_id}/versions",
            json={
                "version": "1.0.0",
                "changelog": "Initial",
                "scenario_data": {"name": "Test"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        # Submit for review
        response = client.post(
            f"/marketplace/templates/{template_id}/submit",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "pending_review"

    def test_approve_template_endpoint(self):
        token = get_admin_token()

        # Create, version, and submit
        create_response = client.post(
            "/marketplace/templates",
            json={
                "name": "Approve Test",
                "description": "Testing approval",
                "category": "cyber_warfare",
                "difficulty": "expert"
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        template_id = create_response.json()["template_id"]

        client.post(
            f"/marketplace/templates/{template_id}/versions",
            json={
                "version": "1.0.0",
                "changelog": "Initial",
                "scenario_data": {"name": "Test"}
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        client.post(
            f"/marketplace/templates/{template_id}/submit",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Approve
        response = client.post(
            f"/marketplace/templates/{template_id}/approve",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "published"

    def test_add_review_endpoint(self):
        token = get_trainee_token()

        response = client.post(
            "/marketplace/templates/builtin-cyber-warfare/reviews",
            json={
                "rating": 5,
                "title": "Excellent training",
                "comment": "Very realistic scenarios"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["rating"] == 5

    def test_download_template_endpoint(self):
        token = get_trainee_token()

        response = client.post(
            "/marketplace/templates/builtin-network-defense/download",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "scenario_data" in data
        assert data["template_id"] == "builtin-network-defense"

    def test_get_categories_endpoint(self):
        token = get_trainee_token()

        response = client.get(
            "/marketplace/categories",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 9  # Number of categories

    def test_get_statistics_endpoint(self):
        token = get_admin_token()

        response = client.get(
            "/marketplace/statistics",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "total_templates" in data
        assert "published_templates" in data

    def test_get_popular_templates_endpoint(self):
        token = get_trainee_token()

        response = client.get(
            "/marketplace/templates/popular",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_recent_templates_endpoint(self):
        token = get_trainee_token()

        response = client.get(
            "/marketplace/templates/recent",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_filter_by_category(self):
        token = get_trainee_token()

        response = client.get(
            "/marketplace/templates?category=cyber_warfare",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(t["category"] == "cyber_warfare" for t in data)

    def test_filter_by_difficulty(self):
        token = get_trainee_token()

        response = client.get(
            "/marketplace/templates?difficulty=beginner",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert all(t["difficulty"] == "beginner" for t in data)

    def test_get_my_templates_endpoint(self):
        token = get_admin_token()

        # Create a template first
        client.post(
            "/marketplace/templates",
            json={
                "name": "My Template",
                "description": "Testing my templates",
                "category": "awareness",
                "difficulty": "beginner"
            },
            headers={"Authorization": f"Bearer {token}"}
        )

        response = client.get(
            "/marketplace/my-templates",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert any(t["name"] == "My Template" for t in data)

    def test_vote_helpful_endpoint(self):
        token = get_trainee_token()
        admin_token = get_admin_token()

        # Add a review first
        review_response = client.post(
            "/marketplace/templates/builtin-incident-response/reviews",
            json={
                "rating": 4,
                "title": "Helpful review",
                "comment": "Good content"
            },
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        review_id = review_response.json()["review_id"]

        # Vote helpful
        response = client.post(
            f"/marketplace/templates/builtin-incident-response/reviews/{review_id}/helpful",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        assert response.json()["helpful_votes"] == 1
