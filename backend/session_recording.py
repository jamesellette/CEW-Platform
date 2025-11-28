"""
Session Recording module for CEW Training Platform.
Records trainee actions, terminal sessions, and events during lab exercises
for later playback and assessment.
"""
import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

logger = logging.getLogger(__name__)

# Maximum events per session to prevent memory bloat
MAX_EVENTS_PER_SESSION = 10000
# Maximum output size to store per event (10KB)
MAX_OUTPUT_SIZE = 10000


class EventType(str, Enum):
    """Types of events that can be recorded."""
    # Lab lifecycle events
    LAB_STARTED = "lab_started"
    LAB_STOPPED = "lab_stopped"
    LAB_PAUSED = "lab_paused"
    LAB_RESUMED = "lab_resumed"

    # Container events
    CONTAINER_STARTED = "container_started"
    CONTAINER_STOPPED = "container_stopped"
    CONTAINER_RESTARTED = "container_restarted"
    CONTAINER_EXEC = "container_exec"

    # Terminal/command events
    TERMINAL_INPUT = "terminal_input"
    TERMINAL_OUTPUT = "terminal_output"
    COMMAND_EXECUTED = "command_executed"

    # Network events
    NETWORK_PACKET = "network_packet"
    NETWORK_CONNECTION = "network_connection"

    # User interaction events
    USER_ACTION = "user_action"
    FILE_UPLOAD = "file_upload"
    FILE_DOWNLOAD = "file_download"

    # Assessment events
    OBJECTIVE_STARTED = "objective_started"
    OBJECTIVE_COMPLETED = "objective_completed"
    HINT_REQUESTED = "hint_requested"

    # System events
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RecordingState(str, Enum):
    """State of a recording session."""
    IDLE = "idle"
    RECORDING = "recording"
    PAUSED = "paused"
    STOPPED = "stopped"


@dataclass
class RecordedEvent:
    """Represents a single recorded event."""
    event_id: str
    timestamp: datetime
    event_type: EventType
    session_id: str
    lab_id: str
    username: str
    container_id: Optional[str] = None
    hostname: Optional[str] = None
    data: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "event_type": self.event_type.value,
            "session_id": self.session_id,
            "lab_id": self.lab_id,
            "username": self.username,
            "container_id": self.container_id,
            "hostname": self.hostname,
            "data": self.data
        }


@dataclass
class RecordingSession:
    """Represents a recording session for a lab exercise."""
    session_id: str
    lab_id: str
    scenario_id: str
    scenario_name: str
    username: str
    state: RecordingState = RecordingState.IDLE
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    paused_at: Optional[datetime] = None
    total_pause_duration: float = 0.0  # seconds
    events: deque = field(default_factory=lambda: deque(maxlen=MAX_EVENTS_PER_SESSION))
    metadata: dict = field(default_factory=dict)

    def to_dict(self, include_events: bool = False) -> dict:
        """Convert to dictionary for serialization."""
        result = {
            "session_id": self.session_id,
            "lab_id": self.lab_id,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "username": self.username,
            "state": self.state.value,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "stopped_at": self.stopped_at.isoformat() if self.stopped_at else None,
            "event_count": len(self.events),
            "duration_seconds": self.get_duration(),
            "metadata": self.metadata
        }
        if include_events:
            result["events"] = [e.to_dict() for e in self.events]
        return result

    def get_duration(self) -> float:
        """Get the total recording duration in seconds (excluding pauses)."""
        if not self.started_at:
            return 0.0

        end_time = self.stopped_at or datetime.now(timezone.utc)
        total = (end_time - self.started_at).total_seconds()
        return max(0.0, total - self.total_pause_duration)


class SessionRecorder:
    """
    Manages session recording for training exercises.
    Records events, terminal I/O, and provides playback functionality.
    """

    def __init__(self):
        self._sessions: dict[str, RecordingSession] = {}
        self._lab_sessions: dict[str, str] = {}  # lab_id -> session_id
        self._lock = asyncio.Lock()

    async def start_recording(
        self,
        lab_id: str,
        scenario_id: str,
        scenario_name: str,
        username: str,
        metadata: Optional[dict] = None
    ) -> RecordingSession:
        """
        Start a new recording session for a lab.

        Args:
            lab_id: Unique identifier of the lab
            scenario_id: Unique identifier of the scenario
            scenario_name: Human-readable scenario name
            username: Username of the trainee
            metadata: Optional additional metadata

        Returns:
            RecordingSession object
        """
        async with self._lock:
            # Check if lab already has an active recording
            if lab_id in self._lab_sessions:
                existing_session = self._sessions.get(self._lab_sessions[lab_id])
                if existing_session and existing_session.state == RecordingState.RECORDING:
                    raise ValueError(f"Lab {lab_id} already has an active recording")

            session_id = str(uuid.uuid4())
            session = RecordingSession(
                session_id=session_id,
                lab_id=lab_id,
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                username=username,
                state=RecordingState.RECORDING,
                started_at=datetime.now(timezone.utc),
                metadata=metadata or {}
            )

            self._sessions[session_id] = session
            self._lab_sessions[lab_id] = session_id

            # Record the session start event
            await self._record_event(
                session,
                EventType.LAB_STARTED,
                data={"scenario_name": scenario_name}
            )

            logger.info(
                f"Started recording session {session_id} for lab {lab_id} "
                f"(user: {username}, scenario: {scenario_name})"
            )

            return session

    async def stop_recording(self, session_id: str) -> RecordingSession:
        """
        Stop a recording session.

        Args:
            session_id: Unique identifier of the session

        Returns:
            Updated RecordingSession object
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            if session.state == RecordingState.STOPPED:
                raise ValueError(f"Session {session_id} is already stopped")

            # Record the session stop event
            await self._record_event(session, EventType.LAB_STOPPED)

            session.state = RecordingState.STOPPED
            session.stopped_at = datetime.now(timezone.utc)

            # Clean up lab mapping
            if session.lab_id in self._lab_sessions:
                del self._lab_sessions[session.lab_id]

            logger.info(
                f"Stopped recording session {session_id} "
                f"(duration: {session.get_duration():.1f}s, events: {len(session.events)})"
            )

            return session

    async def pause_recording(self, session_id: str) -> RecordingSession:
        """Pause a recording session."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            if session.state != RecordingState.RECORDING:
                raise ValueError(f"Session {session_id} is not recording")

            session.state = RecordingState.PAUSED
            session.paused_at = datetime.now(timezone.utc)

            await self._record_event(session, EventType.LAB_PAUSED)

            logger.info(f"Paused recording session {session_id}")
            return session

    async def resume_recording(self, session_id: str) -> RecordingSession:
        """Resume a paused recording session."""
        async with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                raise ValueError(f"Session {session_id} not found")

            if session.state != RecordingState.PAUSED:
                raise ValueError(f"Session {session_id} is not paused")

            # Calculate pause duration
            if session.paused_at:
                pause_duration = (
                    datetime.now(timezone.utc) - session.paused_at
                ).total_seconds()
                session.total_pause_duration += pause_duration

            session.state = RecordingState.RECORDING
            session.paused_at = None

            await self._record_event(session, EventType.LAB_RESUMED)

            logger.info(f"Resumed recording session {session_id}")
            return session

    async def record_event(
        self,
        lab_id: str,
        event_type: EventType,
        container_id: Optional[str] = None,
        hostname: Optional[str] = None,
        data: Optional[dict] = None
    ) -> Optional[RecordedEvent]:
        """
        Record an event for a lab's active session.

        Args:
            lab_id: Lab identifier
            event_type: Type of event to record
            container_id: Optional container identifier
            hostname: Optional container hostname
            data: Optional event data

        Returns:
            RecordedEvent if recording is active, None otherwise
        """
        session_id = self._lab_sessions.get(lab_id)
        if not session_id:
            return None

        session = self._sessions.get(session_id)
        if not session or session.state != RecordingState.RECORDING:
            return None

        return await self._record_event(
            session,
            event_type,
            container_id=container_id,
            hostname=hostname,
            data=data
        )

    async def record_terminal_input(
        self,
        lab_id: str,
        container_id: str,
        hostname: str,
        command: str
    ) -> Optional[RecordedEvent]:
        """Record terminal input (command)."""
        return await self.record_event(
            lab_id,
            EventType.TERMINAL_INPUT,
            container_id=container_id,
            hostname=hostname,
            data={"command": command}
        )

    async def record_terminal_output(
        self,
        lab_id: str,
        container_id: str,
        hostname: str,
        output: str,
        exit_code: Optional[int] = None
    ) -> Optional[RecordedEvent]:
        """Record terminal output."""
        return await self.record_event(
            lab_id,
            EventType.TERMINAL_OUTPUT,
            container_id=container_id,
            hostname=hostname,
            data={
                "output": output[:MAX_OUTPUT_SIZE],
                "exit_code": exit_code
            }
        )

    async def record_command(
        self,
        lab_id: str,
        container_id: str,
        hostname: str,
        command: str,
        output: str,
        exit_code: int,
        duration_ms: int
    ) -> Optional[RecordedEvent]:
        """Record a complete command execution."""
        return await self.record_event(
            lab_id,
            EventType.COMMAND_EXECUTED,
            container_id=container_id,
            hostname=hostname,
            data={
                "command": command,
                "output": output[:MAX_OUTPUT_SIZE],
                "exit_code": exit_code,
                "duration_ms": duration_ms
            }
        )

    async def record_user_action(
        self,
        lab_id: str,
        action: str,
        details: Optional[dict] = None
    ) -> Optional[RecordedEvent]:
        """Record a user action."""
        return await self.record_event(
            lab_id,
            EventType.USER_ACTION,
            data={"action": action, "details": details or {}}
        )

    async def record_objective_completed(
        self,
        lab_id: str,
        objective_id: str,
        objective_name: str,
        score: Optional[float] = None
    ) -> Optional[RecordedEvent]:
        """Record objective completion."""
        return await self.record_event(
            lab_id,
            EventType.OBJECTIVE_COMPLETED,
            data={
                "objective_id": objective_id,
                "objective_name": objective_name,
                "score": score
            }
        )

    async def _record_event(
        self,
        session: RecordingSession,
        event_type: EventType,
        container_id: Optional[str] = None,
        hostname: Optional[str] = None,
        data: Optional[dict] = None
    ) -> RecordedEvent:
        """Internal method to record an event."""
        event = RecordedEvent(
            event_id=str(uuid.uuid4()),
            timestamp=datetime.now(timezone.utc),
            event_type=event_type,
            session_id=session.session_id,
            lab_id=session.lab_id,
            username=session.username,
            container_id=container_id,
            hostname=hostname,
            data=data or {}
        )
        session.events.append(event)
        return event

    def get_session(self, session_id: str) -> Optional[RecordingSession]:
        """Get a recording session by ID."""
        return self._sessions.get(session_id)

    def get_session_for_lab(self, lab_id: str) -> Optional[RecordingSession]:
        """Get the active recording session for a lab."""
        session_id = self._lab_sessions.get(lab_id)
        if session_id:
            return self._sessions.get(session_id)
        return None

    def get_sessions_for_user(self, username: str) -> list[RecordingSession]:
        """Get all recording sessions for a user."""
        return [
            session for session in self._sessions.values()
            if session.username == username
        ]

    def get_all_sessions(self) -> list[RecordingSession]:
        """Get all recording sessions."""
        return list(self._sessions.values())

    def get_session_events(
        self,
        session_id: str,
        event_types: Optional[list[EventType]] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 1000
    ) -> list[RecordedEvent]:
        """
        Get events from a recording session with filtering.

        Args:
            session_id: Session identifier
            event_types: Optional filter by event types
            start_time: Optional filter by start time
            end_time: Optional filter by end time
            limit: Maximum number of events to return

        Returns:
            List of RecordedEvent objects
        """
        session = self._sessions.get(session_id)
        if not session:
            return []

        events = list(session.events)

        # Apply filters
        if event_types:
            events = [e for e in events if e.event_type in event_types]

        if start_time:
            events = [e for e in events if e.timestamp >= start_time]

        if end_time:
            events = [e for e in events if e.timestamp <= end_time]

        return events[:limit]

    def get_session_summary(self, session_id: str) -> dict:
        """
        Get a summary of a recording session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session summary
        """
        session = self._sessions.get(session_id)
        if not session:
            return {}

        # Count events by type
        event_counts = {}
        for event in session.events:
            event_type = event.event_type.value
            event_counts[event_type] = event_counts.get(event_type, 0) + 1

        # Get command stats
        commands = [
            e for e in session.events
            if e.event_type == EventType.COMMAND_EXECUTED
        ]

        successful_commands = len([
            c for c in commands
            if c.data.get("exit_code") == 0
        ])

        return {
            "session_id": session.session_id,
            "scenario_name": session.scenario_name,
            "username": session.username,
            "state": session.state.value,
            "duration_seconds": session.get_duration(),
            "total_events": len(session.events),
            "event_counts": event_counts,
            "commands_executed": len(commands),
            "successful_commands": successful_commands,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "stopped_at": session.stopped_at.isoformat() if session.stopped_at else None
        }

    def get_playback_events(
        self,
        session_id: str,
        speed: float = 1.0
    ) -> list[dict]:
        """
        Get events formatted for playback with relative timestamps.

        Args:
            session_id: Session identifier
            speed: Playback speed multiplier (1.0 = real-time)

        Returns:
            List of events with delay_ms for playback timing
        """
        session = self._sessions.get(session_id)
        if not session or not session.events:
            return []

        events = list(session.events)
        playback_events = []

        start_time = events[0].timestamp

        for event in events:
            elapsed_ms = (event.timestamp - start_time).total_seconds() * 1000
            adjusted_delay = elapsed_ms / speed

            playback_events.append({
                **event.to_dict(),
                "delay_ms": int(adjusted_delay),
                "elapsed_ms": int(elapsed_ms)
            })

        return playback_events


# Global session recorder instance
session_recorder = SessionRecorder()
