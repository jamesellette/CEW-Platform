"""
Multi-User Lab Sessions module for CEW Training Platform.
Provides collaborative training support with team-based exercises,
Red Team vs Blue Team scenarios, and real-time collaboration.
"""
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class TeamRole(str, Enum):
    """Roles within a team-based exercise."""
    RED_TEAM = "red_team"      # Offensive/attack team
    BLUE_TEAM = "blue_team"    # Defensive team
    WHITE_TEAM = "white_team"  # Observers/referees
    PURPLE_TEAM = "purple_team"  # Combined attack/defense
    OBSERVER = "observer"      # Read-only access


class SessionType(str, Enum):
    """Types of multi-user sessions."""
    COLLABORATIVE = "collaborative"  # Team working together
    COMPETITIVE = "competitive"      # Red vs Blue
    TRAINING = "training"           # Instructor-led
    ASSESSMENT = "assessment"       # Formal evaluation


class ParticipantStatus(str, Enum):
    """Status of a participant in a session."""
    INVITED = "invited"
    JOINED = "joined"
    ACTIVE = "active"
    IDLE = "idle"
    LEFT = "left"


@dataclass
class SessionParticipant:
    """Represents a participant in a multi-user session."""
    participant_id: str
    username: str
    display_name: str
    team_role: TeamRole
    status: ParticipantStatus = ParticipantStatus.INVITED
    joined_at: Optional[datetime] = None
    last_activity_at: Optional[datetime] = None
    assigned_containers: list[str] = field(default_factory=list)
    permissions: dict = field(default_factory=dict)
    score: int = 0

    def to_dict(self) -> dict:
        return {
            "participant_id": self.participant_id,
            "username": self.username,
            "display_name": self.display_name,
            "team_role": self.team_role.value,
            "status": self.status.value,
            "joined_at": self.joined_at.isoformat() if self.joined_at else None,
            "last_activity_at": (
                self.last_activity_at.isoformat() if self.last_activity_at else None
            ),
            "assigned_containers": self.assigned_containers,
            "permissions": self.permissions,
            "score": self.score
        }


@dataclass
class TeamInfo:
    """Information about a team in a session."""
    team_id: str
    name: str
    role: TeamRole
    color: str
    members: list[str] = field(default_factory=list)  # participant_ids
    score: int = 0
    objectives_completed: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "team_id": self.team_id,
            "name": self.name,
            "role": self.role.value,
            "color": self.color,
            "member_count": len(self.members),
            "score": self.score,
            "objectives_completed": self.objectives_completed
        }


@dataclass
class ChatMessage:
    """A chat message in a session."""
    message_id: str
    session_id: str
    sender_username: str
    sender_display_name: str
    team_role: Optional[TeamRole]
    content: str
    is_team_only: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "session_id": self.session_id,
            "sender_username": self.sender_username,
            "sender_display_name": self.sender_display_name,
            "team_role": self.team_role.value if self.team_role else None,
            "content": self.content,
            "is_team_only": self.is_team_only,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class SessionObjective:
    """An objective in a multi-user session."""
    objective_id: str
    name: str
    description: str
    points: int
    team_role: Optional[TeamRole] = None  # None = any team can complete
    completed_by: Optional[str] = None  # team_id
    completed_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "objective_id": self.objective_id,
            "name": self.name,
            "description": self.description,
            "points": self.points,
            "team_role": self.team_role.value if self.team_role else None,
            "completed_by": self.completed_by,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class MultiUserSession:
    """Represents a multi-user lab session."""
    session_id: str
    name: str
    description: str
    lab_id: str
    scenario_id: str
    session_type: SessionType
    host_username: str
    max_participants: int = 10
    participants: dict[str, SessionParticipant] = field(default_factory=dict)
    teams: dict[str, TeamInfo] = field(default_factory=dict)
    objectives: list[SessionObjective] = field(default_factory=list)
    chat_messages: list[ChatMessage] = field(default_factory=list)
    is_active: bool = True
    is_locked: bool = False  # Prevent new joins
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    settings: dict = field(default_factory=dict)

    def to_dict(self, include_chat: bool = False) -> dict:
        result = {
            "session_id": self.session_id,
            "name": self.name,
            "description": self.description,
            "lab_id": self.lab_id,
            "scenario_id": self.scenario_id,
            "session_type": self.session_type.value,
            "host_username": self.host_username,
            "max_participants": self.max_participants,
            "participant_count": len(self.participants),
            "participants": [p.to_dict() for p in self.participants.values()],
            "teams": [t.to_dict() for t in self.teams.values()],
            "objectives": [o.to_dict() for o in self.objectives],
            "is_active": self.is_active,
            "is_locked": self.is_locked,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "ended_at": self.ended_at.isoformat() if self.ended_at else None,
            "created_at": self.created_at.isoformat(),
            "settings": self.settings
        }
        if include_chat:
            result["chat_messages"] = [m.to_dict() for m in self.chat_messages[-100:]]
        return result

    def get_team_scores(self) -> dict[str, int]:
        """Get current scores for all teams."""
        return {team_id: team.score for team_id, team in self.teams.items()}

    def get_active_participants(self) -> list[SessionParticipant]:
        """Get list of active participants."""
        return [
            p for p in self.participants.values()
            if p.status in [ParticipantStatus.ACTIVE, ParticipantStatus.IDLE]
        ]


class MultiUserSessionManager:
    """
    Manages multi-user lab sessions for collaborative training.
    Supports team-based exercises, competitive scenarios, and real-time collaboration.
    """

    def __init__(self):
        self._sessions: dict[str, MultiUserSession] = {}
        self._user_sessions: dict[str, list[str]] = {}  # username -> session_ids
        self._lab_sessions: dict[str, str] = {}  # lab_id -> session_id

    # ============ Session Management ============

    def create_session(
        self,
        name: str,
        description: str,
        lab_id: str,
        scenario_id: str,
        session_type: SessionType,
        host_username: str,
        max_participants: int = 10,
        settings: dict = None
    ) -> MultiUserSession:
        """Create a new multi-user session."""
        # Check if lab already has a session
        if lab_id in self._lab_sessions:
            raise ValueError(f"Lab {lab_id} already has an active session")

        session_id = str(uuid.uuid4())
        session = MultiUserSession(
            session_id=session_id,
            name=name,
            description=description,
            lab_id=lab_id,
            scenario_id=scenario_id,
            session_type=session_type,
            host_username=host_username,
            max_participants=max_participants,
            settings=settings or {}
        )

        # Create default teams for competitive sessions
        if session_type == SessionType.COMPETITIVE:
            self._create_default_teams(session)

        self._sessions[session_id] = session
        self._lab_sessions[lab_id] = session_id

        # Add host as participant
        self.add_participant(
            session_id=session_id,
            username=host_username,
            display_name=host_username,
            team_role=(
                TeamRole.WHITE_TEAM if session_type == SessionType.COMPETITIVE
                else TeamRole.PURPLE_TEAM
            )
        )

        logger.info(f"Created multi-user session {session_id}: {name}")
        return session

    def _create_default_teams(self, session: MultiUserSession):
        """Create default Red/Blue teams for competitive sessions."""
        red_team = TeamInfo(
            team_id=str(uuid.uuid4()),
            name="Red Team",
            role=TeamRole.RED_TEAM,
            color="#dc3545"
        )
        blue_team = TeamInfo(
            team_id=str(uuid.uuid4()),
            name="Blue Team",
            role=TeamRole.BLUE_TEAM,
            color="#007bff"
        )
        white_team = TeamInfo(
            team_id=str(uuid.uuid4()),
            name="White Team",
            role=TeamRole.WHITE_TEAM,
            color="#6c757d"
        )
        session.teams[red_team.team_id] = red_team
        session.teams[blue_team.team_id] = blue_team
        session.teams[white_team.team_id] = white_team

    def get_session(self, session_id: str) -> Optional[MultiUserSession]:
        """Get a session by ID."""
        return self._sessions.get(session_id)

    def get_session_for_lab(self, lab_id: str) -> Optional[MultiUserSession]:
        """Get the session for a lab."""
        session_id = self._lab_sessions.get(lab_id)
        if session_id:
            return self._sessions.get(session_id)
        return None

    def list_sessions(
        self,
        session_type: SessionType = None,
        active_only: bool = True
    ) -> list[MultiUserSession]:
        """List sessions with optional filters."""
        sessions = list(self._sessions.values())

        if active_only:
            sessions = [s for s in sessions if s.is_active]

        if session_type:
            sessions = [s for s in sessions if s.session_type == session_type]

        return sessions

    def start_session(self, session_id: str) -> Optional[MultiUserSession]:
        """Start a session (begin the exercise)."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        session.started_at = datetime.now(timezone.utc)
        session.is_locked = True

        # Update all participants to active
        for participant in session.participants.values():
            if participant.status == ParticipantStatus.JOINED:
                participant.status = ParticipantStatus.ACTIVE

        logger.info(f"Started session {session_id}")
        return session

    def end_session(self, session_id: str) -> Optional[MultiUserSession]:
        """End a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        session.is_active = False
        session.ended_at = datetime.now(timezone.utc)

        # Clean up mappings
        if session.lab_id in self._lab_sessions:
            del self._lab_sessions[session.lab_id]

        # Update participant status
        for participant in session.participants.values():
            participant.status = ParticipantStatus.LEFT

        logger.info(f"Ended session {session_id}")
        return session

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        # Clean up mappings
        if session.lab_id in self._lab_sessions:
            del self._lab_sessions[session.lab_id]

        for username in list(self._user_sessions.keys()):
            if session_id in self._user_sessions[username]:
                self._user_sessions[username].remove(session_id)

        del self._sessions[session_id]
        logger.info(f"Deleted session {session_id}")
        return True

    # ============ Participant Management ============

    def add_participant(
        self,
        session_id: str,
        username: str,
        display_name: str,
        team_role: TeamRole,
        permissions: dict = None
    ) -> Optional[SessionParticipant]:
        """Add a participant to a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        if session.is_locked:
            raise ValueError("Session is locked, cannot add participants")

        if len(session.participants) >= session.max_participants:
            raise ValueError("Session is full")

        # Check if user already in session
        for p in session.participants.values():
            if p.username == username:
                raise ValueError(f"User {username} is already in the session")

        participant_id = str(uuid.uuid4())
        participant = SessionParticipant(
            participant_id=participant_id,
            username=username,
            display_name=display_name,
            team_role=team_role,
            status=ParticipantStatus.INVITED,
            permissions=permissions or {}
        )

        session.participants[participant_id] = participant

        # Track user sessions
        if username not in self._user_sessions:
            self._user_sessions[username] = []
        self._user_sessions[username].append(session_id)

        # Add to team if competitive
        if session.session_type == SessionType.COMPETITIVE:
            for team in session.teams.values():
                if team.role == team_role:
                    team.members.append(participant_id)
                    break

        logger.info(f"Added participant {username} to session {session_id}")
        return participant

    def join_session(
        self,
        session_id: str,
        username: str
    ) -> Optional[SessionParticipant]:
        """Mark a participant as joined."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        for participant in session.participants.values():
            if participant.username == username:
                participant.status = ParticipantStatus.JOINED
                participant.joined_at = datetime.now(timezone.utc)
                participant.last_activity_at = datetime.now(timezone.utc)
                return participant

        return None

    def leave_session(
        self,
        session_id: str,
        username: str
    ) -> Optional[SessionParticipant]:
        """Mark a participant as left."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        for participant in session.participants.values():
            if participant.username == username:
                participant.status = ParticipantStatus.LEFT
                return participant

        return None

    def remove_participant(
        self,
        session_id: str,
        participant_id: str
    ) -> bool:
        """Remove a participant from a session."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        if participant_id not in session.participants:
            return False

        participant = session.participants[participant_id]

        # Remove from team
        for team in session.teams.values():
            if participant_id in team.members:
                team.members.remove(participant_id)

        # Remove from user sessions
        if participant.username in self._user_sessions:
            if session_id in self._user_sessions[participant.username]:
                self._user_sessions[participant.username].remove(session_id)

        del session.participants[participant_id]
        logger.info(f"Removed participant {participant_id} from session {session_id}")
        return True

    def update_participant_activity(
        self,
        session_id: str,
        username: str
    ) -> Optional[SessionParticipant]:
        """Update participant's last activity timestamp."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        for participant in session.participants.values():
            if participant.username == username:
                participant.last_activity_at = datetime.now(timezone.utc)
                if participant.status == ParticipantStatus.IDLE:
                    participant.status = ParticipantStatus.ACTIVE
                return participant

        return None

    def get_user_sessions(self, username: str) -> list[MultiUserSession]:
        """Get all sessions for a user."""
        session_ids = self._user_sessions.get(username, [])
        return [
            self._sessions[sid] for sid in session_ids
            if sid in self._sessions
        ]

    # ============ Team Management ============

    def create_team(
        self,
        session_id: str,
        name: str,
        role: TeamRole,
        color: str = "#6c757d"
    ) -> Optional[TeamInfo]:
        """Create a custom team in a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        team_id = str(uuid.uuid4())
        team = TeamInfo(
            team_id=team_id,
            name=name,
            role=role,
            color=color
        )
        session.teams[team_id] = team
        return team

    def assign_to_team(
        self,
        session_id: str,
        participant_id: str,
        team_id: str
    ) -> bool:
        """Assign a participant to a team."""
        session = self._sessions.get(session_id)
        if not session:
            return False

        if participant_id not in session.participants:
            return False

        if team_id not in session.teams:
            return False

        participant = session.participants[participant_id]
        target_team = session.teams[team_id]

        # Remove from current team
        for team in session.teams.values():
            if participant_id in team.members:
                team.members.remove(participant_id)

        # Add to new team
        target_team.members.append(participant_id)
        participant.team_role = target_team.role

        return True

    def update_team_score(
        self,
        session_id: str,
        team_id: str,
        points: int
    ) -> Optional[TeamInfo]:
        """Update a team's score."""
        session = self._sessions.get(session_id)
        if not session or team_id not in session.teams:
            return None

        session.teams[team_id].score += points
        return session.teams[team_id]

    # ============ Objectives ============

    def add_objective(
        self,
        session_id: str,
        name: str,
        description: str,
        points: int,
        team_role: TeamRole = None
    ) -> Optional[SessionObjective]:
        """Add an objective to a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        objective = SessionObjective(
            objective_id=str(uuid.uuid4()),
            name=name,
            description=description,
            points=points,
            team_role=team_role
        )
        session.objectives.append(objective)
        return objective

    def complete_objective(
        self,
        session_id: str,
        objective_id: str,
        team_id: str
    ) -> Optional[SessionObjective]:
        """Mark an objective as completed by a team."""
        session = self._sessions.get(session_id)
        if not session or team_id not in session.teams:
            return None

        for objective in session.objectives:
            if objective.objective_id == objective_id:
                if objective.completed_by:
                    raise ValueError("Objective already completed")

                # Check if team role matches
                team = session.teams[team_id]
                if objective.team_role and objective.team_role != team.role:
                    raise ValueError(f"Objective is for {objective.team_role.value} only")

                objective.completed_by = team_id
                objective.completed_at = datetime.now(timezone.utc)

                # Update team score
                team.score += objective.points
                team.objectives_completed.append(objective_id)

                return objective

        return None

    # ============ Chat ============

    def send_message(
        self,
        session_id: str,
        sender_username: str,
        sender_display_name: str,
        content: str,
        is_team_only: bool = False
    ) -> Optional[ChatMessage]:
        """Send a chat message in a session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        # Find sender's team role
        team_role = None
        for participant in session.participants.values():
            if participant.username == sender_username:
                team_role = participant.team_role
                break

        message = ChatMessage(
            message_id=str(uuid.uuid4()),
            session_id=session_id,
            sender_username=sender_username,
            sender_display_name=sender_display_name,
            team_role=team_role,
            content=content,
            is_team_only=is_team_only
        )
        session.chat_messages.append(message)

        # Keep only last 1000 messages
        if len(session.chat_messages) > 1000:
            session.chat_messages = session.chat_messages[-1000:]

        return message

    def get_messages(
        self,
        session_id: str,
        username: str,
        limit: int = 50,
        after: str = None
    ) -> list[ChatMessage]:
        """Get chat messages for a user (filtered by team visibility)."""
        session = self._sessions.get(session_id)
        if not session:
            return []

        # Find user's team role
        user_role = None
        for participant in session.participants.values():
            if participant.username == username:
                user_role = participant.team_role
                break

        messages = session.chat_messages

        # Filter by team visibility
        filtered = []
        for msg in messages:
            if not msg.is_team_only:
                filtered.append(msg)
            elif msg.team_role == user_role:
                filtered.append(msg)
            elif user_role == TeamRole.WHITE_TEAM:
                # White team can see all messages
                filtered.append(msg)

        # Filter by after message ID
        if after:
            after_idx = None
            for i, msg in enumerate(filtered):
                if msg.message_id == after:
                    after_idx = i
                    break
            if after_idx is not None:
                filtered = filtered[after_idx + 1:]

        return filtered[-limit:]

    # ============ Container Assignment ============

    def assign_container(
        self,
        session_id: str,
        participant_id: str,
        container_id: str
    ) -> bool:
        """Assign a container to a participant."""
        session = self._sessions.get(session_id)
        if not session or participant_id not in session.participants:
            return False

        participant = session.participants[participant_id]
        if container_id not in participant.assigned_containers:
            participant.assigned_containers.append(container_id)
        return True

    def unassign_container(
        self,
        session_id: str,
        participant_id: str,
        container_id: str
    ) -> bool:
        """Remove a container assignment from a participant."""
        session = self._sessions.get(session_id)
        if not session or participant_id not in session.participants:
            return False

        participant = session.participants[participant_id]
        if container_id in participant.assigned_containers:
            participant.assigned_containers.remove(container_id)
        return True

    def get_container_owner(
        self,
        session_id: str,
        container_id: str
    ) -> Optional[SessionParticipant]:
        """Get the participant assigned to a container."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        for participant in session.participants.values():
            if container_id in participant.assigned_containers:
                return participant
        return None


# Global multi-user session manager instance
multi_user_manager = MultiUserSessionManager()
