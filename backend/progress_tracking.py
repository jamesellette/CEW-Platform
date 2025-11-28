"""
Trainee Progress Tracking module for CEW Training Platform.
Tracks exercise completion, skill assessments, and generates progress reports.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class CompletionStatus(str, Enum):
    """Status of an exercise or objective."""
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class SkillLevel(str, Enum):
    """Skill proficiency levels."""
    NOVICE = "novice"
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class Objective:
    """Represents a learning objective within an exercise.

    Note: This class is defined for future exercise template integration.
    """
    objective_id: str
    name: str
    description: str
    points: int = 0
    required: bool = True
    hints: list[str] = field(default_factory=list)


@dataclass
class ExerciseProgress:
    """Tracks a trainee's progress on a specific exercise."""
    progress_id: str
    exercise_id: str
    exercise_name: str
    username: str
    scenario_id: str
    status: CompletionStatus = CompletionStatus.NOT_STARTED
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    objectives_completed: list = field(default_factory=list)
    objectives_total: int = 0
    score: float = 0.0
    max_score: float = 100.0
    time_spent_seconds: float = 0.0
    hints_used: int = 0
    attempts: int = 0
    notes: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "progress_id": self.progress_id,
            "exercise_id": self.exercise_id,
            "exercise_name": self.exercise_name,
            "username": self.username,
            "scenario_id": self.scenario_id,
            "status": self.status.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "objectives_completed": self.objectives_completed,
            "objectives_total": self.objectives_total,
            "completion_percentage": self.get_completion_percentage(),
            "score": self.score,
            "max_score": self.max_score,
            "score_percentage": self.get_score_percentage(),
            "time_spent_seconds": self.time_spent_seconds,
            "hints_used": self.hints_used,
            "attempts": self.attempts,
            "notes": self.notes
        }

    def get_completion_percentage(self) -> float:
        """Get the percentage of objectives completed."""
        if self.objectives_total == 0:
            return 0.0
        return (len(self.objectives_completed) / self.objectives_total) * 100

    def get_score_percentage(self) -> float:
        """Get the score as a percentage."""
        if self.max_score == 0:
            return 0.0
        return (self.score / self.max_score) * 100


@dataclass
class SkillAssessment:
    """Tracks a trainee's skill level in a specific area."""
    assessment_id: str
    username: str
    skill_name: str
    skill_category: str
    level: SkillLevel = SkillLevel.NOVICE
    experience_points: int = 0
    exercises_completed: int = 0
    last_assessed_at: Optional[datetime] = None
    notes: str = ""

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "assessment_id": self.assessment_id,
            "username": self.username,
            "skill_name": self.skill_name,
            "skill_category": self.skill_category,
            "level": self.level.value,
            "experience_points": self.experience_points,
            "exercises_completed": self.exercises_completed,
            "last_assessed_at": (
                self.last_assessed_at.isoformat() if self.last_assessed_at else None
            ),
            "notes": self.notes
        }


@dataclass
class TraineeProfile:
    """Comprehensive profile of a trainee's progress."""
    username: str
    display_name: str
    total_exercises_completed: int = 0
    total_exercises_started: int = 0
    total_score: float = 0.0
    total_time_spent_seconds: float = 0.0
    skills: dict = field(default_factory=dict)  # skill_name -> SkillAssessment
    badges: list = field(default_factory=list)
    created_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "username": self.username,
            "display_name": self.display_name,
            "total_exercises_completed": self.total_exercises_completed,
            "total_exercises_started": self.total_exercises_started,
            "total_score": self.total_score,
            "total_time_spent_seconds": self.total_time_spent_seconds,
            "total_time_spent_hours": round(self.total_time_spent_seconds / 3600, 2),
            "skills": {k: v.to_dict() for k, v in self.skills.items()},
            "badges": self.badges,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_activity_at": self.last_activity_at.isoformat() if self.last_activity_at else None
        }


@dataclass
class Badge:
    """Achievement badge for gamification."""
    badge_id: str
    name: str
    description: str
    icon: str
    criteria: str
    points: int = 0


# Predefined badges
BADGES = {
    "first_exercise": Badge(
        badge_id="first_exercise",
        name="First Steps",
        description="Complete your first training exercise",
        icon="🎯",
        criteria="Complete 1 exercise",
        points=10
    ),
    "quick_learner": Badge(
        badge_id="quick_learner",
        name="Quick Learner",
        description="Complete an exercise in under 10 minutes",
        icon="⚡",
        criteria="Complete exercise in < 600 seconds",
        points=25
    ),
    "perfectionist": Badge(
        badge_id="perfectionist",
        name="Perfectionist",
        description="Achieve a perfect score on any exercise",
        icon="💯",
        criteria="100% score on any exercise",
        points=50
    ),
    "dedicated": Badge(
        badge_id="dedicated",
        name="Dedicated Learner",
        description="Complete 10 exercises",
        icon="📚",
        criteria="Complete 10 exercises",
        points=100
    ),
    "no_hints": Badge(
        badge_id="no_hints",
        name="Self-Reliant",
        description="Complete an exercise without using any hints",
        icon="🧠",
        criteria="Complete exercise with 0 hints",
        points=30
    ),
    "expert": Badge(
        badge_id="expert",
        name="Domain Expert",
        description="Reach Expert level in any skill",
        icon="🏆",
        criteria="Achieve expert skill level",
        points=200
    ),
}


# Skill categories and definitions
SKILL_CATEGORIES = {
    "network_security": {
        "name": "Network Security",
        "skills": [
            "Packet Analysis",
            "Firewall Configuration",
            "Intrusion Detection",
            "Network Reconnaissance",
            "Traffic Analysis"
        ]
    },
    "system_security": {
        "name": "System Security",
        "skills": [
            "Linux Administration",
            "Windows Security",
            "Privilege Escalation",
            "Log Analysis",
            "Vulnerability Assessment"
        ]
    },
    "cyber_warfare": {
        "name": "Cyber Warfare",
        "skills": [
            "Attack Detection",
            "Incident Response",
            "Threat Hunting",
            "Defense Strategies",
            "Counter-Intelligence"
        ]
    },
    "electronic_warfare": {
        "name": "Electronic Warfare",
        "skills": [
            "Signal Analysis",
            "RF Fundamentals",
            "Spectrum Management",
            "Electronic Attack",
            "Electronic Protection"
        ]
    }
}


class ProgressTracker:
    """
    Tracks trainee progress across exercises and skills.
    Provides reports, leaderboards, and achievement tracking.
    """

    def __init__(self):
        self._profiles: dict[str, TraineeProfile] = {}
        self._progress: dict[str, ExerciseProgress] = {}  # progress_id -> ExerciseProgress
        self._user_progress: dict[str, list] = {}  # username -> list of progress_ids

    # ============ Profile Management ============

    def get_or_create_profile(self, username: str, display_name: str = None) -> TraineeProfile:
        """Get or create a trainee profile."""
        if username not in self._profiles:
            self._profiles[username] = TraineeProfile(
                username=username,
                display_name=display_name or username,
                created_at=datetime.now(timezone.utc)
            )
            self._user_progress[username] = []
        return self._profiles[username]

    def get_profile(self, username: str) -> Optional[TraineeProfile]:
        """Get a trainee profile."""
        return self._profiles.get(username)

    def get_all_profiles(self) -> list[TraineeProfile]:
        """Get all trainee profiles."""
        return list(self._profiles.values())

    # ============ Exercise Progress ============

    def start_exercise(
        self,
        username: str,
        exercise_id: str,
        exercise_name: str,
        scenario_id: str,
        objectives_total: int = 0,
        max_score: float = 100.0
    ) -> ExerciseProgress:
        """Start tracking progress for an exercise."""
        profile = self.get_or_create_profile(username)

        progress_id = str(uuid.uuid4())
        progress = ExerciseProgress(
            progress_id=progress_id,
            exercise_id=exercise_id,
            exercise_name=exercise_name,
            username=username,
            scenario_id=scenario_id,
            status=CompletionStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
            objectives_total=objectives_total,
            max_score=max_score,
            attempts=1
        )

        self._progress[progress_id] = progress
        self._user_progress[username].append(progress_id)

        # Update profile stats
        profile.total_exercises_started += 1
        profile.last_activity_at = datetime.now(timezone.utc)

        logger.info(f"Started exercise tracking for {username}: {exercise_name}")
        return progress

    def complete_objective(
        self,
        progress_id: str,
        objective_id: str,
        points_earned: float = 0
    ) -> Optional[ExerciseProgress]:
        """Mark an objective as completed."""
        progress = self._progress.get(progress_id)
        if not progress:
            return None

        if objective_id not in progress.objectives_completed:
            progress.objectives_completed.append(objective_id)
            progress.score += points_earned

        self._update_profile_activity(progress.username)
        return progress

    def complete_exercise(
        self,
        progress_id: str,
        final_score: Optional[float] = None,
        notes: str = ""
    ) -> Optional[ExerciseProgress]:
        """Mark an exercise as completed."""
        progress = self._progress.get(progress_id)
        if not progress:
            return None

        progress.status = CompletionStatus.COMPLETED
        progress.completed_at = datetime.now(timezone.utc)

        if final_score is not None:
            progress.score = min(final_score, progress.max_score)

        if progress.started_at:
            progress.time_spent_seconds = (
                progress.completed_at - progress.started_at
            ).total_seconds()

        progress.notes = notes

        # Update profile
        profile = self.get_profile(progress.username)
        if profile:
            profile.total_exercises_completed += 1
            profile.total_score += progress.score
            profile.total_time_spent_seconds += progress.time_spent_seconds
            profile.last_activity_at = datetime.now(timezone.utc)

            # Check for badge eligibility
            self._check_and_award_badges(progress, profile)

        logger.info(
            f"Completed exercise for {progress.username}: "
            f"{progress.exercise_name} (score: {progress.score})"
        )
        return progress

    def fail_exercise(
        self,
        progress_id: str,
        notes: str = ""
    ) -> Optional[ExerciseProgress]:
        """Mark an exercise as failed."""
        progress = self._progress.get(progress_id)
        if not progress:
            return None

        progress.status = CompletionStatus.FAILED
        progress.completed_at = datetime.now(timezone.utc)
        progress.notes = notes

        if progress.started_at:
            progress.time_spent_seconds = (
                progress.completed_at - progress.started_at
            ).total_seconds()

        self._update_profile_activity(progress.username)
        return progress

    def add_hint_used(self, progress_id: str) -> Optional[ExerciseProgress]:
        """Record that a hint was used."""
        progress = self._progress.get(progress_id)
        if progress:
            progress.hints_used += 1
        return progress

    def get_exercise_progress(self, progress_id: str) -> Optional[ExerciseProgress]:
        """Get exercise progress by ID."""
        return self._progress.get(progress_id)

    def get_user_progress(self, username: str) -> list[ExerciseProgress]:
        """Get all exercise progress for a user."""
        progress_ids = self._user_progress.get(username, [])
        return [self._progress[pid] for pid in progress_ids if pid in self._progress]

    def get_scenario_progress(
        self,
        username: str,
        scenario_id: str
    ) -> list[ExerciseProgress]:
        """Get exercise progress for a specific scenario."""
        user_progress = self.get_user_progress(username)
        return [p for p in user_progress if p.scenario_id == scenario_id]

    # ============ Skill Assessment ============

    def assess_skill(
        self,
        username: str,
        skill_name: str,
        skill_category: str,
        experience_gained: int = 0
    ) -> SkillAssessment:
        """Update skill assessment for a trainee."""
        profile = self.get_or_create_profile(username)

        if skill_name not in profile.skills:
            profile.skills[skill_name] = SkillAssessment(
                assessment_id=str(uuid.uuid4()),
                username=username,
                skill_name=skill_name,
                skill_category=skill_category
            )

        assessment = profile.skills[skill_name]
        assessment.experience_points += experience_gained
        assessment.exercises_completed += 1
        assessment.last_assessed_at = datetime.now(timezone.utc)

        # Update skill level based on experience
        new_level = self._calculate_skill_level(assessment.experience_points)
        if new_level != assessment.level:
            old_level = assessment.level
            assessment.level = new_level
            logger.info(
                f"Skill level up for {username}: "
                f"{skill_name} {old_level.value} -> {new_level.value}"
            )

            # Check for expert badge
            if new_level == SkillLevel.EXPERT:
                self._award_badge(profile, "expert")

        return assessment

    def get_skill_assessment(
        self,
        username: str,
        skill_name: str
    ) -> Optional[SkillAssessment]:
        """Get skill assessment for a user."""
        profile = self.get_profile(username)
        if profile:
            return profile.skills.get(skill_name)
        return None

    def _calculate_skill_level(self, experience: int) -> SkillLevel:
        """Calculate skill level from experience points."""
        if experience >= 1000:
            return SkillLevel.EXPERT
        elif experience >= 500:
            return SkillLevel.ADVANCED
        elif experience >= 200:
            return SkillLevel.INTERMEDIATE
        elif experience >= 50:
            return SkillLevel.BEGINNER
        return SkillLevel.NOVICE

    # ============ Badges & Achievements ============

    def _check_and_award_badges(
        self,
        progress: ExerciseProgress,
        profile: TraineeProfile
    ) -> list[str]:
        """Check and award badges based on exercise completion."""
        awarded = []

        # First exercise badge
        if profile.total_exercises_completed == 1:
            if self._award_badge(profile, "first_exercise"):
                awarded.append("first_exercise")

        # Quick learner badge (under 10 minutes)
        if progress.time_spent_seconds < 600:
            if self._award_badge(profile, "quick_learner"):
                awarded.append("quick_learner")

        # Perfectionist badge (100% score)
        if progress.score >= progress.max_score:
            if self._award_badge(profile, "perfectionist"):
                awarded.append("perfectionist")

        # No hints badge
        if progress.hints_used == 0:
            if self._award_badge(profile, "no_hints"):
                awarded.append("no_hints")

        # Dedicated learner badge (10 exercises)
        if profile.total_exercises_completed >= 10:
            if self._award_badge(profile, "dedicated"):
                awarded.append("dedicated")

        return awarded

    def _award_badge(self, profile: TraineeProfile, badge_id: str) -> bool:
        """Award a badge to a profile if not already awarded."""
        if badge_id in profile.badges:
            return False

        badge = BADGES.get(badge_id)
        if badge:
            profile.badges.append(badge_id)
            profile.total_score += badge.points
            logger.info(f"Badge awarded to {profile.username}: {badge.name}")
            return True
        return False

    def get_available_badges(self) -> list[dict]:
        """Get all available badges."""
        return [
            {
                "badge_id": b.badge_id,
                "name": b.name,
                "description": b.description,
                "icon": b.icon,
                "criteria": b.criteria,
                "points": b.points
            }
            for b in BADGES.values()
        ]

    # ============ Reports & Leaderboards ============

    def get_progress_report(self, username: str) -> dict:
        """Generate a comprehensive progress report for a trainee."""
        profile = self.get_profile(username)
        if not profile:
            return {}

        progress_list = self.get_user_progress(username)
        completed = [p for p in progress_list if p.status == CompletionStatus.COMPLETED]
        in_progress = [p for p in progress_list if p.status == CompletionStatus.IN_PROGRESS]
        failed = [p for p in progress_list if p.status == CompletionStatus.FAILED]

        # Calculate averages
        avg_score = 0.0
        avg_time = 0.0
        if completed:
            avg_score = sum(p.score for p in completed) / len(completed)
            avg_time = sum(p.time_spent_seconds for p in completed) / len(completed)

        return {
            "profile": profile.to_dict(),
            "summary": {
                "exercises_completed": len(completed),
                "exercises_in_progress": len(in_progress),
                "exercises_failed": len(failed),
                "total_attempts": sum(p.attempts for p in progress_list),
                "average_score": round(avg_score, 2),
                "average_time_seconds": round(avg_time, 2),
                "total_hints_used": sum(p.hints_used for p in progress_list)
            },
            "recent_exercises": [p.to_dict() for p in completed[-5:]],
            "skills": {k: v.to_dict() for k, v in profile.skills.items()},
            "badges_earned": [
                BADGES[b].name for b in profile.badges if b in BADGES
            ]
        }

    def get_leaderboard(
        self,
        metric: str = "score",
        limit: int = 10
    ) -> list[dict]:
        """
        Get the leaderboard for a specific metric.

        Args:
            metric: One of 'score', 'exercises', 'time'
            limit: Maximum number of entries to return
        """
        profiles = list(self._profiles.values())

        if metric == "score":
            profiles.sort(key=lambda p: p.total_score, reverse=True)
        elif metric == "exercises":
            profiles.sort(key=lambda p: p.total_exercises_completed, reverse=True)
        elif metric == "time":
            profiles.sort(key=lambda p: p.total_time_spent_seconds, reverse=True)

        return [
            {
                "rank": i + 1,
                "username": p.username,
                "display_name": p.display_name,
                "score": p.total_score,
                "exercises_completed": p.total_exercises_completed,
                "time_spent_hours": round(p.total_time_spent_seconds / 3600, 2),
                "badges": len(p.badges)
            }
            for i, p in enumerate(profiles[:limit])
        ]

    def get_skill_categories(self) -> dict:
        """Get all skill categories and skills."""
        return SKILL_CATEGORIES

    def _update_profile_activity(self, username: str) -> None:
        """Update the last activity timestamp for a profile."""
        profile = self.get_profile(username)
        if profile:
            profile.last_activity_at = datetime.now(timezone.utc)


# Global progress tracker instance
progress_tracker = ProgressTracker()
