"""
Scheduled Exercises module for CEW Training Platform.
Provides calendar-based exercise scheduling, automatic provisioning,
recurring schedules, and notification support.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class ScheduleStatus(str, Enum):
    """Status of a scheduled exercise."""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    RUNNING = "running"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class RecurrenceType(str, Enum):
    """Types of schedule recurrence."""
    NONE = "none"
    DAILY = "daily"
    WEEKLY = "weekly"
    BIWEEKLY = "biweekly"
    MONTHLY = "monthly"


class NotificationType(str, Enum):
    """Types of notifications."""
    SCHEDULE_CREATED = "schedule_created"
    REMINDER_24H = "reminder_24h"
    REMINDER_1H = "reminder_1h"
    EXERCISE_STARTED = "exercise_started"
    EXERCISE_ENDED = "exercise_ended"
    SCHEDULE_CANCELLED = "schedule_cancelled"


@dataclass
class Notification:
    """A notification for a scheduled exercise."""
    notification_id: str
    schedule_id: str
    notification_type: NotificationType
    recipient_username: str
    title: str
    message: str
    is_read: bool = False
    sent_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "notification_id": self.notification_id,
            "schedule_id": self.schedule_id,
            "notification_type": self.notification_type.value,
            "recipient_username": self.recipient_username,
            "title": self.title,
            "message": self.message,
            "is_read": self.is_read,
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class RecurrenceSettings:
    """Settings for recurring schedules."""
    recurrence_type: RecurrenceType
    interval: int = 1  # e.g., every 2 weeks
    days_of_week: list[int] = field(default_factory=list)  # 0=Mon, 6=Sun
    end_date: Optional[datetime] = None
    max_occurrences: Optional[int] = None
    occurrences_count: int = 0

    def to_dict(self) -> dict:
        return {
            "recurrence_type": self.recurrence_type.value,
            "interval": self.interval,
            "days_of_week": self.days_of_week,
            "end_date": self.end_date.isoformat() if self.end_date else None,
            "max_occurrences": self.max_occurrences,
            "occurrences_count": self.occurrences_count
        }


@dataclass
class ScheduledExercise:
    """A scheduled exercise."""
    schedule_id: str
    title: str
    description: str
    scenario_id: str
    scenario_name: str
    created_by: str
    start_time: datetime
    end_time: datetime
    status: ScheduleStatus = ScheduleStatus.DRAFT
    participants: list[str] = field(default_factory=list)  # usernames
    notifications_enabled: bool = True
    auto_provision: bool = True
    auto_teardown: bool = True
    recurrence: Optional[RecurrenceSettings] = None
    lab_id: Optional[str] = None  # Assigned when exercise starts
    parent_schedule_id: Optional[str] = None  # For recurring instances
    notes: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "title": self.title,
            "description": self.description,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "created_by": self.created_by,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_minutes": int((self.end_time - self.start_time).total_seconds() / 60),
            "status": self.status.value,
            "participants": self.participants,
            "participant_count": len(self.participants),
            "notifications_enabled": self.notifications_enabled,
            "auto_provision": self.auto_provision,
            "auto_teardown": self.auto_teardown,
            "recurrence": self.recurrence.to_dict() if self.recurrence else None,
            "lab_id": self.lab_id,
            "parent_schedule_id": self.parent_schedule_id,
            "notes": self.notes,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def is_upcoming(self) -> bool:
        """Check if the exercise is upcoming."""
        now = datetime.now(timezone.utc)
        return self.start_time > now and self.status == ScheduleStatus.SCHEDULED

    def is_in_progress(self) -> bool:
        """Check if the exercise is currently running."""
        now = datetime.now(timezone.utc)
        return self.start_time <= now <= self.end_time and self.status == ScheduleStatus.RUNNING

    def get_next_occurrence(self) -> Optional[datetime]:
        """Calculate the next occurrence for recurring schedules."""
        if not self.recurrence or self.recurrence.recurrence_type == RecurrenceType.NONE:
            return None

        if self.recurrence.max_occurrences:
            if self.recurrence.occurrences_count >= self.recurrence.max_occurrences:
                return None

        base_time = self.start_time
        interval = self.recurrence.interval

        if self.recurrence.recurrence_type == RecurrenceType.DAILY:
            next_time = base_time + timedelta(days=interval)
        elif self.recurrence.recurrence_type == RecurrenceType.WEEKLY:
            next_time = base_time + timedelta(weeks=interval)
        elif self.recurrence.recurrence_type == RecurrenceType.BIWEEKLY:
            next_time = base_time + timedelta(weeks=2 * interval)
        elif self.recurrence.recurrence_type == RecurrenceType.MONTHLY:
            # Approximate monthly recurrence
            next_time = base_time + timedelta(days=30 * interval)
        else:
            return None

        if self.recurrence.end_date and next_time > self.recurrence.end_date:
            return None

        return next_time


class ExerciseScheduler:
    """
    Manages scheduled exercises for the training platform.
    Supports calendar-based scheduling, recurrence, and notifications.
    """

    def __init__(self):
        self._schedules: dict[str, ScheduledExercise] = {}
        self._notifications: dict[str, Notification] = {}
        self._user_notifications: dict[str, list[str]] = {}  # username -> notification_ids

    # ============ Schedule Management ============

    def create_schedule(
        self,
        title: str,
        description: str,
        scenario_id: str,
        scenario_name: str,
        created_by: str,
        start_time: datetime,
        end_time: datetime,
        participants: list[str] = None,
        notifications_enabled: bool = True,
        auto_provision: bool = True,
        auto_teardown: bool = True,
        recurrence: RecurrenceSettings = None,
        notes: str = ""
    ) -> ScheduledExercise:
        """Create a new scheduled exercise."""
        # Validate times
        if end_time <= start_time:
            raise ValueError("End time must be after start time")

        if start_time < datetime.now(timezone.utc):
            raise ValueError("Start time must be in the future")

        schedule_id = str(uuid.uuid4())
        schedule = ScheduledExercise(
            schedule_id=schedule_id,
            title=title,
            description=description,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            created_by=created_by,
            start_time=start_time,
            end_time=end_time,
            status=ScheduleStatus.SCHEDULED,
            participants=participants or [],
            notifications_enabled=notifications_enabled,
            auto_provision=auto_provision,
            auto_teardown=auto_teardown,
            recurrence=recurrence,
            notes=notes
        )

        self._schedules[schedule_id] = schedule

        # Send creation notifications
        if notifications_enabled:
            self._send_schedule_notifications(schedule, NotificationType.SCHEDULE_CREATED)

        logger.info(f"Created schedule {schedule_id}: {title}")
        return schedule

    def get_schedule(self, schedule_id: str) -> Optional[ScheduledExercise]:
        """Get a schedule by ID."""
        return self._schedules.get(schedule_id)

    def update_schedule(
        self,
        schedule_id: str,
        title: str = None,
        description: str = None,
        start_time: datetime = None,
        end_time: datetime = None,
        participants: list[str] = None,
        notifications_enabled: bool = None,
        auto_provision: bool = None,
        auto_teardown: bool = None,
        notes: str = None
    ) -> Optional[ScheduledExercise]:
        """Update a scheduled exercise."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None

        if schedule.status not in [ScheduleStatus.DRAFT, ScheduleStatus.SCHEDULED]:
            raise ValueError("Cannot update a schedule that is running or completed")

        if title is not None:
            schedule.title = title
        if description is not None:
            schedule.description = description
        if start_time is not None:
            if start_time < datetime.now(timezone.utc):
                raise ValueError("Start time must be in the future")
            schedule.start_time = start_time
        if end_time is not None:
            schedule.end_time = end_time
        if participants is not None:
            schedule.participants = participants
        if notifications_enabled is not None:
            schedule.notifications_enabled = notifications_enabled
        if auto_provision is not None:
            schedule.auto_provision = auto_provision
        if auto_teardown is not None:
            schedule.auto_teardown = auto_teardown
        if notes is not None:
            schedule.notes = notes

        # Validate times
        if schedule.end_time <= schedule.start_time:
            raise ValueError("End time must be after start time")

        schedule.updated_at = datetime.now(timezone.utc)
        return schedule

    def cancel_schedule(self, schedule_id: str) -> Optional[ScheduledExercise]:
        """Cancel a scheduled exercise."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None

        if schedule.status == ScheduleStatus.RUNNING:
            raise ValueError("Cannot cancel a running exercise")

        schedule.status = ScheduleStatus.CANCELLED
        schedule.updated_at = datetime.now(timezone.utc)

        # Send cancellation notifications
        if schedule.notifications_enabled:
            self._send_schedule_notifications(schedule, NotificationType.SCHEDULE_CANCELLED)

        logger.info(f"Cancelled schedule {schedule_id}")
        return schedule

    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a scheduled exercise."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return False

        if schedule.status == ScheduleStatus.RUNNING:
            raise ValueError("Cannot delete a running exercise")

        del self._schedules[schedule_id]
        logger.info(f"Deleted schedule {schedule_id}")
        return True

    # ============ Schedule Lifecycle ============

    def start_exercise(self, schedule_id: str, lab_id: str) -> Optional[ScheduledExercise]:
        """Mark an exercise as started and assign lab."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None

        if schedule.status != ScheduleStatus.SCHEDULED:
            raise ValueError("Can only start scheduled exercises")

        schedule.status = ScheduleStatus.RUNNING
        schedule.lab_id = lab_id
        schedule.updated_at = datetime.now(timezone.utc)

        # Send start notifications
        if schedule.notifications_enabled:
            self._send_schedule_notifications(schedule, NotificationType.EXERCISE_STARTED)

        logger.info(f"Started exercise {schedule_id} with lab {lab_id}")
        return schedule

    def complete_exercise(self, schedule_id: str) -> Optional[ScheduledExercise]:
        """Mark an exercise as completed."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None

        schedule.status = ScheduleStatus.COMPLETED
        schedule.updated_at = datetime.now(timezone.utc)

        # Send completion notifications
        if schedule.notifications_enabled:
            self._send_schedule_notifications(schedule, NotificationType.EXERCISE_ENDED)

        # Handle recurrence
        if schedule.recurrence and schedule.recurrence.recurrence_type != RecurrenceType.NONE:
            self._create_next_occurrence(schedule)

        logger.info(f"Completed exercise {schedule_id}")
        return schedule

    def fail_exercise(self, schedule_id: str, reason: str = "") -> Optional[ScheduledExercise]:
        """Mark an exercise as failed."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None

        schedule.status = ScheduleStatus.FAILED
        if reason:
            schedule.notes = f"Failed: {reason}"
        schedule.updated_at = datetime.now(timezone.utc)

        logger.info(f"Exercise {schedule_id} failed: {reason}")
        return schedule

    def _create_next_occurrence(self, schedule: ScheduledExercise) -> Optional[ScheduledExercise]:
        """Create the next occurrence for a recurring schedule."""
        next_start = schedule.get_next_occurrence()
        if not next_start:
            return None

        duration = schedule.end_time - schedule.start_time
        next_end = next_start + duration

        schedule.recurrence.occurrences_count += 1

        next_schedule = ScheduledExercise(
            schedule_id=str(uuid.uuid4()),
            title=schedule.title,
            description=schedule.description,
            scenario_id=schedule.scenario_id,
            scenario_name=schedule.scenario_name,
            created_by=schedule.created_by,
            start_time=next_start,
            end_time=next_end,
            status=ScheduleStatus.SCHEDULED,
            participants=schedule.participants.copy(),
            notifications_enabled=schedule.notifications_enabled,
            auto_provision=schedule.auto_provision,
            auto_teardown=schedule.auto_teardown,
            recurrence=schedule.recurrence,
            parent_schedule_id=schedule.schedule_id,
            notes=schedule.notes
        )

        self._schedules[next_schedule.schedule_id] = next_schedule

        if schedule.notifications_enabled:
            self._send_schedule_notifications(next_schedule, NotificationType.SCHEDULE_CREATED)

        logger.info(
            f"Created next occurrence {next_schedule.schedule_id} for {schedule.schedule_id}"
        )
        return next_schedule

    # ============ Participant Management ============

    def add_participant(self, schedule_id: str, username: str) -> Optional[ScheduledExercise]:
        """Add a participant to a schedule."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None

        if username not in schedule.participants:
            schedule.participants.append(username)
            schedule.updated_at = datetime.now(timezone.utc)

            # Send notification to new participant
            if schedule.notifications_enabled:
                self._create_notification(
                    schedule=schedule,
                    notification_type=NotificationType.SCHEDULE_CREATED,
                    recipient=username
                )

        return schedule

    def remove_participant(self, schedule_id: str, username: str) -> Optional[ScheduledExercise]:
        """Remove a participant from a schedule."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None

        if username in schedule.participants:
            schedule.participants.remove(username)
            schedule.updated_at = datetime.now(timezone.utc)

        return schedule

    # ============ Queries ============

    def list_schedules(
        self,
        status: ScheduleStatus = None,
        created_by: str = None,
        participant: str = None,
        from_date: datetime = None,
        to_date: datetime = None
    ) -> list[ScheduledExercise]:
        """List schedules with optional filters."""
        schedules = list(self._schedules.values())

        if status:
            schedules = [s for s in schedules if s.status == status]

        if created_by:
            schedules = [s for s in schedules if s.created_by == created_by]

        if participant:
            schedules = [s for s in schedules if participant in s.participants]

        if from_date:
            schedules = [s for s in schedules if s.start_time >= from_date]

        if to_date:
            schedules = [s for s in schedules if s.start_time <= to_date]

        # Sort by start time
        schedules.sort(key=lambda s: s.start_time)
        return schedules

    def get_upcoming_schedules(self, days: int = 7) -> list[ScheduledExercise]:
        """Get schedules starting within the specified number of days."""
        now = datetime.now(timezone.utc)
        end_date = now + timedelta(days=days)

        return [
            s for s in self._schedules.values()
            if s.status == ScheduleStatus.SCHEDULED
            and now <= s.start_time <= end_date
        ]

    def get_schedules_needing_start(self) -> list[ScheduledExercise]:
        """Get scheduled exercises that should be started now."""
        now = datetime.now(timezone.utc)

        return [
            s for s in self._schedules.values()
            if s.status == ScheduleStatus.SCHEDULED
            and s.start_time <= now
            and s.auto_provision
        ]

    def get_schedules_needing_end(self) -> list[ScheduledExercise]:
        """Get running exercises that should be ended now."""
        now = datetime.now(timezone.utc)

        return [
            s for s in self._schedules.values()
            if s.status == ScheduleStatus.RUNNING
            and s.end_time <= now
            and s.auto_teardown
        ]

    def get_user_schedules(self, username: str) -> list[ScheduledExercise]:
        """Get all schedules for a user (as creator or participant)."""
        return [
            s for s in self._schedules.values()
            if s.created_by == username or username in s.participants
        ]

    def get_calendar_view(
        self,
        year: int,
        month: int,
        username: str = None
    ) -> dict[str, list[dict]]:
        """Get schedules organized by date for calendar view."""
        schedules = list(self._schedules.values())

        if username:
            schedules = [
                s for s in schedules
                if s.created_by == username or username in s.participants
            ]

        # Filter to month
        start_of_month = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end_of_month = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end_of_month = datetime(year, month + 1, 1, tzinfo=timezone.utc)

        schedules = [
            s for s in schedules
            if start_of_month <= s.start_time < end_of_month
        ]

        # Group by date
        calendar: dict[str, list[dict]] = {}
        for schedule in schedules:
            date_str = schedule.start_time.strftime("%Y-%m-%d")
            if date_str not in calendar:
                calendar[date_str] = []
            calendar[date_str].append({
                "schedule_id": schedule.schedule_id,
                "title": schedule.title,
                "start_time": schedule.start_time.isoformat(),
                "end_time": schedule.end_time.isoformat(),
                "status": schedule.status.value,
                "scenario_name": schedule.scenario_name
            })

        return calendar

    # ============ Notifications ============

    def _send_schedule_notifications(
        self,
        schedule: ScheduledExercise,
        notification_type: NotificationType
    ):
        """Send notifications to all participants."""
        recipients = [schedule.created_by] + schedule.participants
        recipients = list(set(recipients))  # Remove duplicates

        for recipient in recipients:
            self._create_notification(schedule, notification_type, recipient)

    def _create_notification(
        self,
        schedule: ScheduledExercise,
        notification_type: NotificationType,
        recipient: str
    ) -> Notification:
        """Create a notification for a user."""
        title_map = {
            NotificationType.SCHEDULE_CREATED: f"New exercise scheduled: {schedule.title}",
            NotificationType.REMINDER_24H: f"Exercise tomorrow: {schedule.title}",
            NotificationType.REMINDER_1H: f"Exercise starting soon: {schedule.title}",
            NotificationType.EXERCISE_STARTED: f"Exercise started: {schedule.title}",
            NotificationType.EXERCISE_ENDED: f"Exercise completed: {schedule.title}",
            NotificationType.SCHEDULE_CANCELLED: f"Exercise cancelled: {schedule.title}",
        }

        message_map = {
            NotificationType.SCHEDULE_CREATED: (
                f"You have been added to '{schedule.title}' "
                f"starting on {schedule.start_time.strftime('%Y-%m-%d %H:%M')} UTC"
            ),
            NotificationType.REMINDER_24H: (
                f"'{schedule.title}' starts tomorrow at "
                f"{schedule.start_time.strftime('%H:%M')} UTC"
            ),
            NotificationType.REMINDER_1H: (
                f"'{schedule.title}' starts in 1 hour"
            ),
            NotificationType.EXERCISE_STARTED: (
                f"'{schedule.title}' has started. Join now!"
            ),
            NotificationType.EXERCISE_ENDED: (
                f"'{schedule.title}' has ended"
            ),
            NotificationType.SCHEDULE_CANCELLED: (
                f"'{schedule.title}' scheduled for "
                f"{schedule.start_time.strftime('%Y-%m-%d %H:%M')} UTC has been cancelled"
            ),
        }

        notification = Notification(
            notification_id=str(uuid.uuid4()),
            schedule_id=schedule.schedule_id,
            notification_type=notification_type,
            recipient_username=recipient,
            title=title_map.get(notification_type, "Exercise notification"),
            message=message_map.get(notification_type, ""),
            sent_at=datetime.now(timezone.utc)
        )

        self._notifications[notification.notification_id] = notification

        if recipient not in self._user_notifications:
            self._user_notifications[recipient] = []
        self._user_notifications[recipient].append(notification.notification_id)

        logger.info(f"Created {notification_type.value} notification for {recipient}")
        return notification

    def get_user_notifications(
        self,
        username: str,
        unread_only: bool = False,
        limit: int = 50
    ) -> list[Notification]:
        """Get notifications for a user."""
        notification_ids = self._user_notifications.get(username, [])
        notifications = [
            self._notifications[nid]
            for nid in notification_ids
            if nid in self._notifications
        ]

        if unread_only:
            notifications = [n for n in notifications if not n.is_read]

        # Sort by creation time (newest first)
        notifications.sort(key=lambda n: n.created_at, reverse=True)

        return notifications[:limit]

    def mark_notification_read(
        self,
        notification_id: str
    ) -> Optional[Notification]:
        """Mark a notification as read."""
        notification = self._notifications.get(notification_id)
        if notification:
            notification.is_read = True
        return notification

    def mark_all_notifications_read(self, username: str) -> int:
        """Mark all notifications for a user as read."""
        notification_ids = self._user_notifications.get(username, [])
        count = 0
        for nid in notification_ids:
            if nid in self._notifications:
                self._notifications[nid].is_read = True
                count += 1
        return count

    def get_unread_count(self, username: str) -> int:
        """Get count of unread notifications for a user."""
        notification_ids = self._user_notifications.get(username, [])
        return sum(
            1 for nid in notification_ids
            if nid in self._notifications and not self._notifications[nid].is_read
        )


# Global scheduler instance
exercise_scheduler = ExerciseScheduler()
