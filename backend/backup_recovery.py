"""
Backup & Disaster Recovery Module

Provides automated database backups, scenario configuration exports,
lab state snapshots, and one-click restore functionality.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union
import json
import yaml
import gzip
import base64
import hashlib
import uuid
from pathlib import Path
import os


class BackupType(Enum):
    """Types of backups."""
    FULL = "full"              # Complete system backup
    INCREMENTAL = "incremental"  # Changes since last backup
    SCENARIOS = "scenarios"     # Scenarios only
    USERS = "users"            # User data only
    AUDIT = "audit"            # Audit logs only
    CONFIG = "config"          # Configuration only
    LAB_STATE = "lab_state"    # Lab state snapshot


class BackupStatus(Enum):
    """Backup status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    VERIFIED = "verified"


class RestoreStatus(Enum):
    """Restore operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


class CompressionType(Enum):
    """Compression algorithms."""
    NONE = "none"
    GZIP = "gzip"


@dataclass
class BackupMetadata:
    """Metadata for a backup."""
    backup_id: str
    backup_type: BackupType
    created_at: datetime
    created_by: str
    description: str
    status: BackupStatus
    size_bytes: int = 0
    compressed: bool = False
    compression_type: CompressionType = CompressionType.NONE
    checksum: str = ""
    version: str = "1.0"
    items_count: int = 0
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    retention_days: int = 30
    tags: List[str] = field(default_factory=list)
    
    def to_dict(self) -> dict:
        return {
            "backup_id": self.backup_id,
            "backup_type": self.backup_type.value,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "description": self.description,
            "status": self.status.value,
            "size_bytes": self.size_bytes,
            "compressed": self.compressed,
            "compression_type": self.compression_type.value,
            "checksum": self.checksum,
            "version": self.version,
            "items_count": self.items_count,
            "error_message": self.error_message,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retention_days": self.retention_days,
            "tags": self.tags
        }


@dataclass
class BackupData:
    """Container for backup data."""
    metadata: BackupMetadata
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "metadata": self.metadata.to_dict(),
            "data": self.data
        }


@dataclass
class RestorePoint:
    """A restore point in time."""
    restore_id: str
    backup_id: str
    created_at: datetime
    created_by: str
    status: RestoreStatus
    items_restored: int = 0
    items_failed: int = 0
    error_message: Optional[str] = None
    completed_at: Optional[datetime] = None
    rollback_data: Optional[Dict] = None
    
    def to_dict(self) -> dict:
        return {
            "restore_id": self.restore_id,
            "backup_id": self.backup_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status.value,
            "items_restored": self.items_restored,
            "items_failed": self.items_failed,
            "error_message": self.error_message,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None
        }


@dataclass
class LabSnapshot:
    """Snapshot of a lab's state."""
    snapshot_id: str
    lab_id: str
    scenario_id: str
    created_at: datetime
    created_by: str
    status: str
    containers: List[Dict] = field(default_factory=list)
    networks: List[Dict] = field(default_factory=list)
    environment: Dict = field(default_factory=dict)
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "snapshot_id": self.snapshot_id,
            "lab_id": self.lab_id,
            "scenario_id": self.scenario_id,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status,
            "containers": self.containers,
            "networks": self.networks,
            "environment": self.environment,
            "notes": self.notes
        }


@dataclass
class BackupSchedule:
    """Automated backup schedule."""
    schedule_id: str
    backup_type: BackupType
    frequency: str  # daily, weekly, monthly
    time_of_day: str  # HH:MM format
    day_of_week: Optional[int] = None  # 0-6 for weekly
    day_of_month: Optional[int] = None  # 1-31 for monthly
    enabled: bool = True
    retention_days: int = 30
    max_backups: int = 10
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    created_by: str = ""
    
    def to_dict(self) -> dict:
        return {
            "schedule_id": self.schedule_id,
            "backup_type": self.backup_type.value,
            "frequency": self.frequency,
            "time_of_day": self.time_of_day,
            "day_of_week": self.day_of_week,
            "day_of_month": self.day_of_month,
            "enabled": self.enabled,
            "retention_days": self.retention_days,
            "max_backups": self.max_backups,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "created_by": self.created_by
        }


class BackupManager:
    """
    Manages backup and disaster recovery operations.
    
    Features:
    - Automated database backups
    - Scenario configuration exports
    - Lab state snapshots
    - One-click restore functionality
    - Backup scheduling
    - Compression and verification
    """
    
    def __init__(self, backup_dir: Optional[str] = None):
        # Backup storage
        self._backups: Dict[str, BackupData] = {}
        self._restore_points: Dict[str, RestorePoint] = {}
        self._lab_snapshots: Dict[str, LabSnapshot] = {}
        self._schedules: Dict[str, BackupSchedule] = {}
        
        # Backup directory (in-memory for prototype, would be filesystem in production)
        self._backup_dir = backup_dir or "/tmp/cew_backups"
        
        # Settings
        self._default_retention_days = 30
        self._max_backup_size_mb = 100
        self._compression_threshold_kb = 100
        
        # Version for backup format
        self._backup_version = "1.0"
    
    def _generate_checksum(self, data: bytes) -> str:
        """Generate SHA-256 checksum for data."""
        return hashlib.sha256(data).hexdigest()
    
    def _compress_data(self, data: bytes) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(data)
    
    def _decompress_data(self, data: bytes) -> bytes:
        """Decompress gzip data."""
        return gzip.decompress(data)
    
    def _serialize_backup(
        self,
        data: Dict,
        compress: bool = True
    ) -> tuple:
        """Serialize backup data and optionally compress."""
        json_data = json.dumps(data, default=str).encode('utf-8')
        
        if compress and len(json_data) > self._compression_threshold_kb * 1024:
            compressed = self._compress_data(json_data)
            checksum = self._generate_checksum(compressed)
            return compressed, len(compressed), True, CompressionType.GZIP, checksum
        
        checksum = self._generate_checksum(json_data)
        return json_data, len(json_data), False, CompressionType.NONE, checksum
    
    def _deserialize_backup(
        self,
        data: bytes,
        compressed: bool,
        compression_type: CompressionType
    ) -> Dict:
        """Deserialize backup data."""
        if compressed and compression_type == CompressionType.GZIP:
            data = self._decompress_data(data)
        return json.loads(data.decode('utf-8'))
    
    def create_backup(
        self,
        backup_type: BackupType,
        created_by: str,
        description: str = "",
        data: Optional[Dict] = None,
        tags: Optional[List[str]] = None,
        retention_days: int = 30
    ) -> BackupMetadata:
        """
        Create a new backup.
        
        Args:
            backup_type: Type of backup
            created_by: Username creating backup
            description: Description of backup
            data: Data to backup (scenarios, users, config, etc.)
            tags: Tags for categorization
            retention_days: Days to retain backup
        
        Returns:
            BackupMetadata for the created backup
        """
        backup_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        # Create metadata
        metadata = BackupMetadata(
            backup_id=backup_id,
            backup_type=backup_type,
            created_at=now,
            created_by=created_by,
            description=description or f"{backup_type.value} backup",
            status=BackupStatus.IN_PROGRESS,
            version=self._backup_version,
            retention_days=retention_days,
            tags=tags or []
        )
        
        try:
            # Prepare backup data
            backup_data = data or {}
            backup_data["_backup_timestamp"] = now.isoformat()
            backup_data["_backup_type"] = backup_type.value
            
            # Serialize and optionally compress
            serialized, size, compressed, comp_type, checksum = self._serialize_backup(
                backup_data
            )
            
            # Update metadata
            metadata.size_bytes = size
            metadata.compressed = compressed
            metadata.compression_type = comp_type
            metadata.checksum = checksum
            metadata.items_count = len(backup_data)
            metadata.status = BackupStatus.COMPLETED
            metadata.completed_at = datetime.utcnow()
            
            # Store backup
            self._backups[backup_id] = BackupData(
                metadata=metadata,
                data=backup_data
            )
            
        except Exception as e:
            metadata.status = BackupStatus.FAILED
            metadata.error_message = str(e)
        
        return metadata
    
    def create_full_backup(
        self,
        created_by: str,
        scenarios: Dict,
        users: List[Dict],
        audit_logs: List[Dict],
        config: Dict,
        description: str = ""
    ) -> BackupMetadata:
        """Create a full system backup."""
        data = {
            "scenarios": scenarios,
            "users": users,
            "audit_logs": audit_logs,
            "config": config
        }
        
        return self.create_backup(
            backup_type=BackupType.FULL,
            created_by=created_by,
            description=description or "Full system backup",
            data=data,
            tags=["full", "system"]
        )
    
    def create_scenario_backup(
        self,
        created_by: str,
        scenarios: Dict,
        description: str = ""
    ) -> BackupMetadata:
        """Create a scenarios-only backup."""
        return self.create_backup(
            backup_type=BackupType.SCENARIOS,
            created_by=created_by,
            description=description or "Scenarios backup",
            data={"scenarios": scenarios},
            tags=["scenarios"]
        )
    
    def get_backup(self, backup_id: str) -> Optional[BackupData]:
        """Get a backup by ID."""
        return self._backups.get(backup_id)
    
    def list_backups(
        self,
        backup_type: Optional[BackupType] = None,
        status: Optional[BackupStatus] = None,
        created_by: Optional[str] = None,
        tags: Optional[List[str]] = None,
        limit: int = 100
    ) -> List[BackupMetadata]:
        """List backups with optional filters."""
        backups = list(self._backups.values())
        
        if backup_type:
            backups = [b for b in backups if b.metadata.backup_type == backup_type]
        
        if status:
            backups = [b for b in backups if b.metadata.status == status]
        
        if created_by:
            backups = [b for b in backups if b.metadata.created_by == created_by]
        
        if tags:
            backups = [
                b for b in backups
                if any(t in b.metadata.tags for t in tags)
            ]
        
        # Sort by creation date (newest first)
        backups.sort(key=lambda x: x.metadata.created_at, reverse=True)
        
        return [b.metadata for b in backups[:limit]]
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup."""
        if backup_id in self._backups:
            del self._backups[backup_id]
            return True
        return False
    
    def verify_backup(self, backup_id: str) -> dict:
        """Verify backup integrity."""
        backup = self._backups.get(backup_id)
        if not backup:
            return {"valid": False, "error": "Backup not found"}
        
        try:
            # Re-serialize and check checksum
            serialized, _, compressed, comp_type, checksum = self._serialize_backup(
                backup.data, compress=backup.metadata.compressed
            )
            
            if checksum == backup.metadata.checksum:
                backup.metadata.status = BackupStatus.VERIFIED
                return {
                    "valid": True,
                    "checksum": checksum,
                    "verified_at": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "valid": False,
                    "error": "Checksum mismatch",
                    "expected": backup.metadata.checksum,
                    "actual": checksum
                }
                
        except Exception as e:
            return {"valid": False, "error": str(e)}
    
    def restore_backup(
        self,
        backup_id: str,
        created_by: str,
        target: Optional[str] = None
    ) -> RestorePoint:
        """
        Restore from a backup.
        
        Args:
            backup_id: ID of backup to restore
            created_by: Username performing restore
            target: Optional target for restore (e.g., specific scenario)
        
        Returns:
            RestorePoint with restore status
        """
        restore_id = str(uuid.uuid4())
        now = datetime.utcnow()
        
        restore_point = RestorePoint(
            restore_id=restore_id,
            backup_id=backup_id,
            created_at=now,
            created_by=created_by,
            status=RestoreStatus.PENDING
        )
        
        backup = self._backups.get(backup_id)
        if not backup:
            restore_point.status = RestoreStatus.FAILED
            restore_point.error_message = "Backup not found"
            self._restore_points[restore_id] = restore_point
            return restore_point
        
        try:
            restore_point.status = RestoreStatus.IN_PROGRESS
            
            # In a real implementation, this would restore data to the database
            # For the prototype, we just track the restore operation
            items_count = len(backup.data)
            
            restore_point.items_restored = items_count
            restore_point.status = RestoreStatus.COMPLETED
            restore_point.completed_at = datetime.utcnow()
            
        except Exception as e:
            restore_point.status = RestoreStatus.FAILED
            restore_point.error_message = str(e)
        
        self._restore_points[restore_id] = restore_point
        return restore_point
    
    def get_restore_point(self, restore_id: str) -> Optional[RestorePoint]:
        """Get a restore point by ID."""
        return self._restore_points.get(restore_id)
    
    def list_restore_points(
        self,
        backup_id: Optional[str] = None,
        status: Optional[RestoreStatus] = None,
        limit: int = 50
    ) -> List[RestorePoint]:
        """List restore points."""
        points = list(self._restore_points.values())
        
        if backup_id:
            points = [p for p in points if p.backup_id == backup_id]
        
        if status:
            points = [p for p in points if p.status == status]
        
        points.sort(key=lambda x: x.created_at, reverse=True)
        return points[:limit]
    
    def create_lab_snapshot(
        self,
        lab_id: str,
        scenario_id: str,
        created_by: str,
        status: str,
        containers: List[Dict],
        networks: List[Dict],
        environment: Optional[Dict] = None,
        notes: str = ""
    ) -> LabSnapshot:
        """Create a snapshot of a lab's state."""
        snapshot_id = str(uuid.uuid4())
        
        snapshot = LabSnapshot(
            snapshot_id=snapshot_id,
            lab_id=lab_id,
            scenario_id=scenario_id,
            created_at=datetime.utcnow(),
            created_by=created_by,
            status=status,
            containers=containers,
            networks=networks,
            environment=environment or {},
            notes=notes
        )
        
        self._lab_snapshots[snapshot_id] = snapshot
        return snapshot
    
    def get_lab_snapshot(self, snapshot_id: str) -> Optional[LabSnapshot]:
        """Get a lab snapshot by ID."""
        return self._lab_snapshots.get(snapshot_id)
    
    def list_lab_snapshots(
        self,
        lab_id: Optional[str] = None,
        scenario_id: Optional[str] = None,
        created_by: Optional[str] = None,
        limit: int = 50
    ) -> List[LabSnapshot]:
        """List lab snapshots."""
        snapshots = list(self._lab_snapshots.values())
        
        if lab_id:
            snapshots = [s for s in snapshots if s.lab_id == lab_id]
        
        if scenario_id:
            snapshots = [s for s in snapshots if s.scenario_id == scenario_id]
        
        if created_by:
            snapshots = [s for s in snapshots if s.created_by == created_by]
        
        snapshots.sort(key=lambda x: x.created_at, reverse=True)
        return snapshots[:limit]
    
    def delete_lab_snapshot(self, snapshot_id: str) -> bool:
        """Delete a lab snapshot."""
        if snapshot_id in self._lab_snapshots:
            del self._lab_snapshots[snapshot_id]
            return True
        return False
    
    def restore_lab_snapshot(
        self,
        snapshot_id: str,
        created_by: str
    ) -> Optional[dict]:
        """
        Restore a lab from a snapshot.
        
        Returns dict with lab configuration to recreate.
        """
        snapshot = self._lab_snapshots.get(snapshot_id)
        if not snapshot:
            return None
        
        return {
            "snapshot_id": snapshot_id,
            "lab_id": snapshot.lab_id,
            "scenario_id": snapshot.scenario_id,
            "containers": snapshot.containers,
            "networks": snapshot.networks,
            "environment": snapshot.environment,
            "restored_at": datetime.utcnow().isoformat(),
            "restored_by": created_by
        }
    
    def create_schedule(
        self,
        backup_type: BackupType,
        created_by: str,
        frequency: str,
        time_of_day: str,
        day_of_week: Optional[int] = None,
        day_of_month: Optional[int] = None,
        retention_days: int = 30,
        max_backups: int = 10
    ) -> BackupSchedule:
        """Create an automated backup schedule."""
        schedule_id = str(uuid.uuid4())
        
        schedule = BackupSchedule(
            schedule_id=schedule_id,
            backup_type=backup_type,
            frequency=frequency,
            time_of_day=time_of_day,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
            retention_days=retention_days,
            max_backups=max_backups,
            created_by=created_by
        )
        
        # Calculate next run time
        schedule.next_run = self._calculate_next_run(schedule)
        
        self._schedules[schedule_id] = schedule
        return schedule
    
    def _calculate_next_run(self, schedule: BackupSchedule) -> datetime:
        """Calculate the next run time for a schedule."""
        now = datetime.utcnow()
        hour, minute = map(int, schedule.time_of_day.split(":"))
        
        if schedule.frequency == "daily":
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_run <= now:
                next_run += timedelta(days=1)
                
        elif schedule.frequency == "weekly":
            next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = schedule.day_of_week - now.weekday()
            if days_ahead <= 0:
                days_ahead += 7
            next_run += timedelta(days=days_ahead)
            
        elif schedule.frequency == "monthly":
            next_run = now.replace(
                day=schedule.day_of_month or 1,
                hour=hour,
                minute=minute,
                second=0,
                microsecond=0
            )
            if next_run <= now:
                # Move to next month
                if next_run.month == 12:
                    next_run = next_run.replace(year=next_run.year + 1, month=1)
                else:
                    next_run = next_run.replace(month=next_run.month + 1)
        else:
            next_run = now + timedelta(days=1)
        
        return next_run
    
    def get_schedule(self, schedule_id: str) -> Optional[BackupSchedule]:
        """Get a backup schedule by ID."""
        return self._schedules.get(schedule_id)
    
    def list_schedules(
        self,
        enabled_only: bool = False
    ) -> List[BackupSchedule]:
        """List backup schedules."""
        schedules = list(self._schedules.values())
        
        if enabled_only:
            schedules = [s for s in schedules if s.enabled]
        
        return schedules
    
    def update_schedule(
        self,
        schedule_id: str,
        enabled: Optional[bool] = None,
        time_of_day: Optional[str] = None,
        retention_days: Optional[int] = None,
        max_backups: Optional[int] = None
    ) -> Optional[BackupSchedule]:
        """Update a backup schedule."""
        schedule = self._schedules.get(schedule_id)
        if not schedule:
            return None
        
        if enabled is not None:
            schedule.enabled = enabled
        if time_of_day:
            schedule.time_of_day = time_of_day
            schedule.next_run = self._calculate_next_run(schedule)
        if retention_days is not None:
            schedule.retention_days = retention_days
        if max_backups is not None:
            schedule.max_backups = max_backups
        
        return schedule
    
    def delete_schedule(self, schedule_id: str) -> bool:
        """Delete a backup schedule."""
        if schedule_id in self._schedules:
            del self._schedules[schedule_id]
            return True
        return False
    
    def run_scheduled_backup(
        self,
        schedule_id: str,
        data_provider: callable
    ) -> Optional[BackupMetadata]:
        """Run a scheduled backup."""
        schedule = self._schedules.get(schedule_id)
        if not schedule or not schedule.enabled:
            return None
        
        # Get data to backup
        data = data_provider(schedule.backup_type)
        
        # Create backup
        metadata = self.create_backup(
            backup_type=schedule.backup_type,
            created_by=f"scheduled:{schedule.schedule_id}",
            description=f"Scheduled {schedule.frequency} backup",
            data=data,
            tags=["scheduled", schedule.frequency],
            retention_days=schedule.retention_days
        )
        
        # Update schedule
        schedule.last_run = datetime.utcnow()
        schedule.next_run = self._calculate_next_run(schedule)
        
        # Clean up old backups if needed
        self._cleanup_old_backups(schedule)
        
        return metadata
    
    def _cleanup_old_backups(self, schedule: BackupSchedule):
        """Remove old backups exceeding retention or max count."""
        # Get backups from this schedule
        scheduled_backups = [
            b for b in self._backups.values()
            if b.metadata.created_by == f"scheduled:{schedule.schedule_id}"
        ]
        
        # Sort by date
        scheduled_backups.sort(key=lambda x: x.metadata.created_at)
        
        # Remove by count if exceeding max
        while len(scheduled_backups) > schedule.max_backups:
            oldest = scheduled_backups.pop(0)
            self.delete_backup(oldest.metadata.backup_id)
        
        # Remove by retention
        cutoff = datetime.utcnow() - timedelta(days=schedule.retention_days)
        for backup in scheduled_backups:
            if backup.metadata.created_at < cutoff:
                self.delete_backup(backup.metadata.backup_id)
    
    def export_backup(
        self,
        backup_id: str,
        format: str = "json"
    ) -> Optional[str]:
        """Export a backup to a string format."""
        backup = self._backups.get(backup_id)
        if not backup:
            return None
        
        export_data = backup.to_dict()
        
        if format == "yaml":
            return yaml.dump(export_data, default_flow_style=False)
        return json.dumps(export_data, indent=2, default=str)
    
    def import_backup(
        self,
        content: str,
        format: str = "json",
        created_by: str = "import"
    ) -> Optional[BackupMetadata]:
        """Import a backup from a string format."""
        try:
            if format == "yaml":
                data = yaml.safe_load(content)
            else:
                data = json.loads(content)
            
            # Extract metadata and backup data
            metadata_dict = data.get("metadata", {})
            backup_data = data.get("data", {})
            
            # Create new backup with imported data
            backup_type = BackupType(metadata_dict.get("backup_type", "full"))
            
            return self.create_backup(
                backup_type=backup_type,
                created_by=created_by,
                description=f"Imported: {metadata_dict.get('description', 'N/A')}",
                data=backup_data,
                tags=["imported"] + metadata_dict.get("tags", [])
            )
            
        except Exception as e:
            raise ValueError(f"Failed to import backup: {e}")
    
    def get_statistics(self) -> dict:
        """Get backup statistics."""
        backups = list(self._backups.values())
        
        total_size = sum(b.metadata.size_bytes for b in backups)
        by_type = {}
        for b in backups:
            t = b.metadata.backup_type.value
            if t not in by_type:
                by_type[t] = 0
            by_type[t] += 1
        
        by_status = {}
        for b in backups:
            s = b.metadata.status.value
            if s not in by_status:
                by_status[s] = 0
            by_status[s] += 1
        
        return {
            "total_backups": len(backups),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "by_type": by_type,
            "by_status": by_status,
            "total_snapshots": len(self._lab_snapshots),
            "total_restore_points": len(self._restore_points),
            "active_schedules": len([s for s in self._schedules.values() if s.enabled])
        }
    
    def cleanup_expired_backups(self) -> int:
        """Remove expired backups based on retention policy."""
        now = datetime.utcnow()
        expired = []
        
        for backup_id, backup in self._backups.items():
            expiry = backup.metadata.created_at + timedelta(
                days=backup.metadata.retention_days
            )
            if now > expiry:
                expired.append(backup_id)
        
        for backup_id in expired:
            self.delete_backup(backup_id)
        
        return len(expired)


# Global backup manager instance
backup_manager = BackupManager()
