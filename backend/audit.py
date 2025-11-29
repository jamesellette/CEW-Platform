"""
Audit logging module for CEW Training Platform.
Tracks user actions for security and compliance.
"""
from collections import deque
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel
import uuid


class AuditAction:
    """Audit action types."""
    LOGIN = "login"
    LOGOUT = "logout"
    CREATE_SCENARIO = "create_scenario"
    UPDATE_SCENARIO = "update_scenario"
    DELETE_SCENARIO = "delete_scenario"
    VIEW_SCENARIO = "view_scenario"
    VIEW_TOPOLOGY = "view_topology"
    CREATE_USER = "create_user"
    UPDATE_USER = "update_user"
    DELETE_USER = "delete_user"
    FAILED_LOGIN = "failed_login"
    ACCESS_DENIED = "access_denied"
    ACTIVATE_SCENARIO = "activate_scenario"
    DEACTIVATE_SCENARIO = "deactivate_scenario"
    KILL_SWITCH = "kill_switch"
    LAB_RECOVERY = "lab_recovery"


class AuditLog(BaseModel):
    """Audit log entry model."""
    id: str
    timestamp: datetime
    username: Optional[str]
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[str] = None
    ip_address: Optional[str] = None
    success: bool = True


# In-memory audit log store using deque for O(1) removal (replace with database in production)
MAX_AUDIT_LOGS = 1000
audit_logs: deque[AuditLog] = deque(maxlen=MAX_AUDIT_LOGS)


def log_action(
    action: str,
    username: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    details: Optional[str] = None,
    ip_address: Optional[str] = None,
    success: bool = True
) -> AuditLog:
    """Log an audit event."""
    entry = AuditLog(
        id=str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc),
        username=username,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        details=details,
        ip_address=ip_address,
        success=success
    )
    audit_logs.append(entry)
    return entry


def get_audit_logs(
    username: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100
) -> list[AuditLog]:
    """Retrieve audit logs with optional filtering."""
    filtered = list(audit_logs)

    if username:
        filtered = [log for log in filtered if log.username == username]

    if action:
        filtered = [log for log in filtered if log.action == action]

    # Return most recent entries first
    filtered.reverse()

    return filtered[:limit]


def clear_audit_logs():
    """Clear all audit logs (for testing only)."""
    audit_logs.clear()
