"""
Scenario Templates Marketplace module for CEW Training Platform.
Provides template sharing, versioning, ratings, and community contributions.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid
import re

logger = logging.getLogger(__name__)


class TemplateCategory(str, Enum):
    """Categories for scenario templates."""
    NETWORK_DEFENSE = "network_defense"
    INCIDENT_RESPONSE = "incident_response"
    PENETRATION_TESTING = "penetration_testing"
    MALWARE_ANALYSIS = "malware_analysis"
    FORENSICS = "forensics"
    CYBER_WARFARE = "cyber_warfare"
    ELECTRONIC_WARFARE = "electronic_warfare"
    AWARENESS = "awareness"
    OTHER = "other"


class DifficultyLevel(str, Enum):
    """Difficulty levels for templates."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


class TemplateStatus(str, Enum):
    """Status of a template in the marketplace."""
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    PUBLISHED = "published"
    DEPRECATED = "deprecated"
    REJECTED = "rejected"


@dataclass
class TemplateVersion:
    """Represents a version of a template."""
    version: str
    changelog: str
    scenario_data: dict
    created_at: datetime
    created_by: str

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "changelog": self.changelog,
            "scenario_data": self.scenario_data,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }


@dataclass
class TemplateReview:
    """Represents a user review of a template."""
    review_id: str
    template_id: str
    username: str
    rating: int  # 1-5 stars
    title: str
    comment: str
    helpful_votes: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "template_id": self.template_id,
            "username": self.username,
            "rating": self.rating,
            "title": self.title,
            "comment": self.comment,
            "helpful_votes": self.helpful_votes,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class ScenarioTemplate:
    """Represents a scenario template in the marketplace."""
    template_id: str
    name: str
    description: str
    author: str
    category: TemplateCategory
    difficulty: DifficultyLevel
    status: TemplateStatus = TemplateStatus.DRAFT
    tags: list[str] = field(default_factory=list)
    versions: list[TemplateVersion] = field(default_factory=list)
    reviews: list[TemplateReview] = field(default_factory=list)
    download_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    estimated_duration_minutes: int = 30
    prerequisites: list[str] = field(default_factory=list)
    learning_objectives: list[str] = field(default_factory=list)

    def to_dict(self, include_reviews: bool = False, include_versions: bool = False) -> dict:
        result = {
            "template_id": self.template_id,
            "name": self.name,
            "description": self.description,
            "author": self.author,
            "category": self.category.value,
            "difficulty": self.difficulty.value,
            "status": self.status.value,
            "tags": self.tags,
            "download_count": self.download_count,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "estimated_duration_minutes": self.estimated_duration_minutes,
            "prerequisites": self.prerequisites,
            "learning_objectives": self.learning_objectives,
            "current_version": self.get_current_version(),
            "version_count": len(self.versions),
            "review_count": len(self.reviews),
            "average_rating": self.get_average_rating()
        }
        if include_reviews:
            result["reviews"] = [r.to_dict() for r in self.reviews]
        if include_versions:
            result["versions"] = [v.to_dict() for v in self.versions]
        return result

    def get_current_version(self) -> Optional[str]:
        """Get the current (latest) version string."""
        if not self.versions:
            return None
        return self.versions[-1].version

    def get_average_rating(self) -> float:
        """Calculate average rating from reviews."""
        if not self.reviews:
            return 0.0
        total = sum(r.rating for r in self.reviews)
        return round(total / len(self.reviews), 2)


class TemplateMarketplace:
    """
    Manages the scenario templates marketplace.
    Provides publishing, versioning, and community features.
    """

    def __init__(self):
        self._templates: dict[str, ScenarioTemplate] = {}
        self._initialize_built_in_templates()

    def _initialize_built_in_templates(self):
        """Initialize with built-in templates."""
        # Network Defense Template
        network_defense = ScenarioTemplate(
            template_id="builtin-network-defense",
            name="Network Defense Basics",
            description=(
                "Learn fundamental network defense concepts including "
                "firewall configuration, intrusion detection, and log analysis."
            ),
            author="CEW Platform Team",
            category=TemplateCategory.NETWORK_DEFENSE,
            difficulty=DifficultyLevel.BEGINNER,
            status=TemplateStatus.PUBLISHED,
            tags=["firewall", "ids", "logging", "basics"],
            estimated_duration_minutes=45,
            prerequisites=["Basic networking knowledge", "Linux command line basics"],
            learning_objectives=[
                "Configure basic firewall rules",
                "Understand intrusion detection concepts",
                "Analyze network logs for anomalies"
            ]
        )
        network_defense.versions.append(TemplateVersion(
            version="1.0.0",
            changelog="Initial release",
            scenario_data={
                "name": "Network Defense Basics",
                "description": "Learn network defense fundamentals",
                "topology": {
                    "nodes": [
                        {"id": "firewall", "type": "router", "image": "alpine:latest"},
                        {"id": "ids", "type": "server", "image": "alpine:latest"},
                        {"id": "target", "type": "server", "image": "alpine:latest"}
                    ],
                    "networks": [
                        {"id": "external", "subnet": "192.168.1.0/24"},
                        {"id": "internal", "subnet": "10.0.0.0/24"}
                    ]
                },
                "constraints": {
                    "air_gap": True,
                    "max_containers": 5
                }
            },
            created_at=datetime.now(timezone.utc),
            created_by="system"
        ))
        self._templates[network_defense.template_id] = network_defense

        # Incident Response Template
        incident_response = ScenarioTemplate(
            template_id="builtin-incident-response",
            name="Incident Response Fundamentals",
            description=(
                "Practice incident response procedures including detection, "
                "containment, eradication, and recovery phases."
            ),
            author="CEW Platform Team",
            category=TemplateCategory.INCIDENT_RESPONSE,
            difficulty=DifficultyLevel.INTERMEDIATE,
            status=TemplateStatus.PUBLISHED,
            tags=["incident", "response", "containment", "forensics"],
            estimated_duration_minutes=60,
            prerequisites=["Network Defense Basics", "Security fundamentals"],
            learning_objectives=[
                "Identify indicators of compromise",
                "Execute containment procedures",
                "Document incident timeline",
                "Perform basic forensic analysis"
            ]
        )
        incident_response.versions.append(TemplateVersion(
            version="1.0.0",
            changelog="Initial release",
            scenario_data={
                "name": "Incident Response Fundamentals",
                "description": "Learn incident response procedures",
                "topology": {
                    "nodes": [
                        {"id": "siem", "type": "server", "image": "alpine:latest"},
                        {"id": "compromised", "type": "server", "image": "alpine:latest"},
                        {"id": "forensic", "type": "workstation", "image": "alpine:latest"}
                    ],
                    "networks": [
                        {"id": "corp", "subnet": "10.0.0.0/24"}
                    ]
                },
                "constraints": {
                    "air_gap": True,
                    "max_containers": 6
                }
            },
            created_at=datetime.now(timezone.utc),
            created_by="system"
        ))
        self._templates[incident_response.template_id] = incident_response

        # Cyber Warfare Template
        cyber_warfare = ScenarioTemplate(
            template_id="builtin-cyber-warfare",
            name="Cyber Warfare Operations",
            description=(
                "Advanced cyber warfare scenario covering offensive and "
                "defensive operations in a military context."
            ),
            author="CEW Platform Team",
            category=TemplateCategory.CYBER_WARFARE,
            difficulty=DifficultyLevel.ADVANCED,
            status=TemplateStatus.PUBLISHED,
            tags=["military", "offensive", "defensive", "operations"],
            estimated_duration_minutes=90,
            prerequisites=["Incident Response", "Network Defense", "Penetration Testing"],
            learning_objectives=[
                "Understand cyber warfare doctrine",
                "Execute coordinated cyber operations",
                "Defend against nation-state attacks",
                "Apply rules of engagement"
            ]
        )
        cyber_warfare.versions.append(TemplateVersion(
            version="1.0.0",
            changelog="Initial release",
            scenario_data={
                "name": "Cyber Warfare Operations",
                "description": "Advanced cyber warfare training",
                "topology": {
                    "nodes": [
                        {"id": "c2", "type": "server", "image": "alpine:latest"},
                        {"id": "red-team", "type": "workstation", "image": "alpine:latest"},
                        {"id": "blue-team", "type": "workstation", "image": "alpine:latest"},
                        {"id": "target-network", "type": "server", "image": "alpine:latest"}
                    ],
                    "networks": [
                        {"id": "red", "subnet": "10.1.0.0/24"},
                        {"id": "blue", "subnet": "10.2.0.0/24"},
                        {"id": "target", "subnet": "192.168.0.0/24"}
                    ]
                },
                "constraints": {
                    "air_gap": True,
                    "max_containers": 10
                }
            },
            created_at=datetime.now(timezone.utc),
            created_by="system"
        ))
        self._templates[cyber_warfare.template_id] = cyber_warfare

    # ============ Template Management ============

    def create_template(
        self,
        name: str,
        description: str,
        author: str,
        category: TemplateCategory,
        difficulty: DifficultyLevel,
        tags: list[str] = None,
        estimated_duration_minutes: int = 30,
        prerequisites: list[str] = None,
        learning_objectives: list[str] = None
    ) -> ScenarioTemplate:
        """Create a new template (as draft)."""
        template_id = str(uuid.uuid4())
        template = ScenarioTemplate(
            template_id=template_id,
            name=name,
            description=description,
            author=author,
            category=category,
            difficulty=difficulty,
            status=TemplateStatus.DRAFT,
            tags=tags or [],
            estimated_duration_minutes=estimated_duration_minutes,
            prerequisites=prerequisites or [],
            learning_objectives=learning_objectives or []
        )
        self._templates[template_id] = template
        logger.info(f"Created template {template_id}: {name}")
        return template

    def get_template(self, template_id: str) -> Optional[ScenarioTemplate]:
        """Get a template by ID."""
        return self._templates.get(template_id)

    def update_template(
        self,
        template_id: str,
        name: str = None,
        description: str = None,
        category: TemplateCategory = None,
        difficulty: DifficultyLevel = None,
        tags: list[str] = None,
        estimated_duration_minutes: int = None,
        prerequisites: list[str] = None,
        learning_objectives: list[str] = None
    ) -> Optional[ScenarioTemplate]:
        """Update template metadata."""
        template = self._templates.get(template_id)
        if not template:
            return None

        if name is not None:
            template.name = name
        if description is not None:
            template.description = description
        if category is not None:
            template.category = category
        if difficulty is not None:
            template.difficulty = difficulty
        if tags is not None:
            template.tags = tags
        if estimated_duration_minutes is not None:
            template.estimated_duration_minutes = estimated_duration_minutes
        if prerequisites is not None:
            template.prerequisites = prerequisites
        if learning_objectives is not None:
            template.learning_objectives = learning_objectives

        template.updated_at = datetime.now(timezone.utc)
        return template

    def delete_template(self, template_id: str) -> bool:
        """Delete a template."""
        if template_id in self._templates:
            # Don't allow deleting built-in templates
            if template_id.startswith("builtin-"):
                return False
            del self._templates[template_id]
            logger.info(f"Deleted template {template_id}")
            return True
        return False

    # ============ Version Management ============

    def add_version(
        self,
        template_id: str,
        version: str,
        changelog: str,
        scenario_data: dict,
        created_by: str
    ) -> Optional[TemplateVersion]:
        """Add a new version to a template."""
        template = self._templates.get(template_id)
        if not template:
            return None

        # Validate version format (semver-like)
        if not re.match(r'^\d+\.\d+\.\d+$', version):
            raise ValueError("Version must be in format X.Y.Z")

        # Check version doesn't exist
        existing_versions = [v.version for v in template.versions]
        if version in existing_versions:
            raise ValueError(f"Version {version} already exists")

        new_version = TemplateVersion(
            version=version,
            changelog=changelog,
            scenario_data=scenario_data,
            created_at=datetime.now(timezone.utc),
            created_by=created_by
        )
        template.versions.append(new_version)
        template.updated_at = datetime.now(timezone.utc)

        logger.info(f"Added version {version} to template {template_id}")
        return new_version

    def get_version(
        self,
        template_id: str,
        version: str = None
    ) -> Optional[TemplateVersion]:
        """Get a specific version or the latest version."""
        template = self._templates.get(template_id)
        if not template or not template.versions:
            return None

        if version is None:
            return template.versions[-1]

        for v in template.versions:
            if v.version == version:
                return v
        return None

    # ============ Publishing Workflow ============

    def submit_for_review(self, template_id: str) -> Optional[ScenarioTemplate]:
        """Submit a template for review before publishing."""
        template = self._templates.get(template_id)
        if not template:
            return None

        if template.status not in [TemplateStatus.DRAFT, TemplateStatus.REJECTED]:
            raise ValueError("Only draft or rejected templates can be submitted")

        if not template.versions:
            raise ValueError("Template must have at least one version")

        template.status = TemplateStatus.PENDING_REVIEW
        template.updated_at = datetime.now(timezone.utc)
        logger.info(f"Template {template_id} submitted for review")
        return template

    def approve_template(self, template_id: str) -> Optional[ScenarioTemplate]:
        """Approve and publish a template (admin only)."""
        template = self._templates.get(template_id)
        if not template:
            return None

        if template.status != TemplateStatus.PENDING_REVIEW:
            raise ValueError("Only pending templates can be approved")

        template.status = TemplateStatus.PUBLISHED
        template.updated_at = datetime.now(timezone.utc)
        logger.info(f"Template {template_id} approved and published")
        return template

    def reject_template(
        self,
        template_id: str,
        reason: str
    ) -> Optional[ScenarioTemplate]:
        """Reject a template (admin only)."""
        template = self._templates.get(template_id)
        if not template:
            return None

        if template.status != TemplateStatus.PENDING_REVIEW:
            raise ValueError("Only pending templates can be rejected")

        template.status = TemplateStatus.REJECTED
        template.updated_at = datetime.now(timezone.utc)
        # Store rejection reason in description for now
        logger.info(f"Template {template_id} rejected: {reason}")
        return template

    def deprecate_template(self, template_id: str) -> Optional[ScenarioTemplate]:
        """Mark a template as deprecated."""
        template = self._templates.get(template_id)
        if not template:
            return None

        template.status = TemplateStatus.DEPRECATED
        template.updated_at = datetime.now(timezone.utc)
        logger.info(f"Template {template_id} deprecated")
        return template

    # ============ Reviews & Ratings ============

    def add_review(
        self,
        template_id: str,
        username: str,
        rating: int,
        title: str,
        comment: str
    ) -> Optional[TemplateReview]:
        """Add a review to a template."""
        template = self._templates.get(template_id)
        if not template:
            return None

        if template.status != TemplateStatus.PUBLISHED:
            raise ValueError("Can only review published templates")

        if not 1 <= rating <= 5:
            raise ValueError("Rating must be between 1 and 5")

        # Check if user already reviewed
        for review in template.reviews:
            if review.username == username:
                raise ValueError("User has already reviewed this template")

        review = TemplateReview(
            review_id=str(uuid.uuid4()),
            template_id=template_id,
            username=username,
            rating=rating,
            title=title,
            comment=comment
        )
        template.reviews.append(review)
        template.updated_at = datetime.now(timezone.utc)

        logger.info(f"Added review from {username} to template {template_id}")
        return review

    def vote_helpful(
        self,
        template_id: str,
        review_id: str
    ) -> Optional[TemplateReview]:
        """Vote a review as helpful."""
        template = self._templates.get(template_id)
        if not template:
            return None

        for review in template.reviews:
            if review.review_id == review_id:
                review.helpful_votes += 1
                return review
        return None

    # ============ Search & Discovery ============

    def list_templates(
        self,
        category: TemplateCategory = None,
        difficulty: DifficultyLevel = None,
        status: TemplateStatus = None,
        tags: list[str] = None,
        author: str = None,
        search_query: str = None
    ) -> list[ScenarioTemplate]:
        """List templates with optional filters."""
        results = list(self._templates.values())

        if category:
            results = [t for t in results if t.category == category]

        if difficulty:
            results = [t for t in results if t.difficulty == difficulty]

        if status:
            results = [t for t in results if t.status == status]
        else:
            # By default, only show published templates
            results = [t for t in results if t.status == TemplateStatus.PUBLISHED]

        if tags:
            results = [
                t for t in results
                if any(tag in t.tags for tag in tags)
            ]

        if author:
            results = [t for t in results if t.author == author]

        if search_query:
            query_lower = search_query.lower()
            results = [
                t for t in results
                if query_lower in t.name.lower() or query_lower in t.description.lower()
            ]

        return results

    def get_popular_templates(self, limit: int = 10) -> list[ScenarioTemplate]:
        """Get most downloaded templates."""
        published = [
            t for t in self._templates.values()
            if t.status == TemplateStatus.PUBLISHED
        ]
        published.sort(key=lambda t: t.download_count, reverse=True)
        return published[:limit]

    def get_top_rated_templates(self, limit: int = 10) -> list[ScenarioTemplate]:
        """Get highest rated templates."""
        published = [
            t for t in self._templates.values()
            if t.status == TemplateStatus.PUBLISHED and t.reviews
        ]
        published.sort(key=lambda t: t.get_average_rating(), reverse=True)
        return published[:limit]

    def get_recent_templates(self, limit: int = 10) -> list[ScenarioTemplate]:
        """Get most recently updated templates."""
        published = [
            t for t in self._templates.values()
            if t.status == TemplateStatus.PUBLISHED
        ]
        published.sort(key=lambda t: t.updated_at, reverse=True)
        return published[:limit]

    # ============ Download / Use Template ============

    def download_template(
        self,
        template_id: str,
        version: str = None
    ) -> Optional[dict]:
        """Download/use a template to create a scenario."""
        template = self._templates.get(template_id)
        if not template:
            return None

        if template.status != TemplateStatus.PUBLISHED:
            raise ValueError("Can only download published templates")

        version_obj = self.get_version(template_id, version)
        if not version_obj:
            return None

        # Increment download count
        template.download_count += 1

        logger.info(
            f"Template {template_id} v{version_obj.version} downloaded "
            f"(total: {template.download_count})"
        )

        return {
            "template_id": template_id,
            "version": version_obj.version,
            "scenario_data": version_obj.scenario_data
        }

    def get_categories(self) -> list[dict]:
        """Get all template categories with counts."""
        category_counts = {}
        for template in self._templates.values():
            if template.status == TemplateStatus.PUBLISHED:
                cat = template.category.value
                category_counts[cat] = category_counts.get(cat, 0) + 1

        return [
            {
                "category": cat.value,
                "name": cat.value.replace("_", " ").title(),
                "count": category_counts.get(cat.value, 0)
            }
            for cat in TemplateCategory
        ]

    def get_statistics(self) -> dict:
        """Get marketplace statistics."""
        all_templates = list(self._templates.values())
        published = [t for t in all_templates if t.status == TemplateStatus.PUBLISHED]
        pending = [t for t in all_templates if t.status == TemplateStatus.PENDING_REVIEW]

        total_downloads = sum(t.download_count for t in all_templates)
        total_reviews = sum(len(t.reviews) for t in all_templates)

        return {
            "total_templates": len(all_templates),
            "published_templates": len(published),
            "pending_templates": len(pending),
            "total_downloads": total_downloads,
            "total_reviews": total_reviews,
            "categories": len(TemplateCategory)
        }


# Global marketplace instance
marketplace = TemplateMarketplace()
