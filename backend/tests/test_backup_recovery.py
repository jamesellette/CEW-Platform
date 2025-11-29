"""Tests for backup and disaster recovery."""

import pytest
from datetime import datetime, timedelta

from backup_recovery import (
    BackupManager, BackupType, BackupStatus, RestoreStatus,
    CompressionType, backup_manager
)


class TestBackupManager:
    """Tests for the BackupManager class."""
    
    @pytest.fixture
    def manager(self):
        """Create a fresh backup manager for each test."""
        return BackupManager()
    
    def test_create_backup(self, manager):
        """Test creating a basic backup."""
        metadata = manager.create_backup(
            backup_type=BackupType.SCENARIOS,
            created_by="admin",
            description="Test backup",
            data={"scenarios": [{"id": "1", "name": "Test"}]}
        )
        
        assert metadata.backup_id is not None
        assert metadata.backup_type == BackupType.SCENARIOS
        assert metadata.created_by == "admin"
        assert metadata.status == BackupStatus.COMPLETED
        assert metadata.size_bytes > 0
        assert metadata.checksum is not None
    
    def test_create_full_backup(self, manager):
        """Test creating a full system backup."""
        metadata = manager.create_full_backup(
            created_by="admin",
            scenarios={"s1": {"name": "Scenario 1"}},
            users=[{"username": "user1", "role": "trainee"}],
            audit_logs=[{"action": "login", "user": "user1"}],
            config={"setting1": "value1"}
        )
        
        assert metadata.backup_type == BackupType.FULL
        assert "full" in metadata.tags
        assert "system" in metadata.tags
    
    def test_create_scenario_backup(self, manager):
        """Test creating a scenarios backup."""
        metadata = manager.create_scenario_backup(
            created_by="instructor",
            scenarios={"s1": {"name": "Test Scenario"}}
        )
        
        assert metadata.backup_type == BackupType.SCENARIOS
        assert "scenarios" in metadata.tags
    
    def test_get_backup(self, manager):
        """Test retrieving a backup."""
        metadata = manager.create_backup(
            backup_type=BackupType.CONFIG,
            created_by="admin",
            data={"config": {"key": "value"}}
        )
        
        backup = manager.get_backup(metadata.backup_id)
        assert backup is not None
        assert backup.metadata.backup_id == metadata.backup_id
        assert "config" in backup.data
    
    def test_list_backups(self, manager):
        """Test listing backups."""
        # Create multiple backups
        manager.create_backup(
            backup_type=BackupType.SCENARIOS,
            created_by="admin",
            data={}
        )
        manager.create_backup(
            backup_type=BackupType.CONFIG,
            created_by="instructor",
            data={}
        )
        manager.create_backup(
            backup_type=BackupType.SCENARIOS,
            created_by="admin",
            data={}
        )
        
        # List all
        all_backups = manager.list_backups()
        assert len(all_backups) == 3
        
        # Filter by type
        scenario_backups = manager.list_backups(backup_type=BackupType.SCENARIOS)
        assert len(scenario_backups) == 2
        
        # Filter by creator
        admin_backups = manager.list_backups(created_by="admin")
        assert len(admin_backups) == 2
    
    def test_delete_backup(self, manager):
        """Test deleting a backup."""
        metadata = manager.create_backup(
            backup_type=BackupType.CONFIG,
            created_by="admin",
            data={}
        )
        
        assert manager.delete_backup(metadata.backup_id) is True
        assert manager.get_backup(metadata.backup_id) is None
        assert manager.delete_backup(metadata.backup_id) is False
    
    def test_verify_backup(self, manager):
        """Test backup verification."""
        metadata = manager.create_backup(
            backup_type=BackupType.CONFIG,
            created_by="admin",
            data={"important": "data"}
        )
        
        result = manager.verify_backup(metadata.backup_id)
        assert result["valid"] is True
        assert "checksum" in result
    
    def test_verify_nonexistent_backup(self, manager):
        """Test verifying a nonexistent backup."""
        result = manager.verify_backup("nonexistent")
        assert result["valid"] is False
        assert "Backup not found" in result["error"]
    
    def test_restore_backup(self, manager):
        """Test restoring from a backup."""
        metadata = manager.create_backup(
            backup_type=BackupType.FULL,
            created_by="admin",
            data={"scenarios": {"s1": "data"}}
        )
        
        restore_point = manager.restore_backup(
            backup_id=metadata.backup_id,
            created_by="admin"
        )
        
        assert restore_point.restore_id is not None
        assert restore_point.backup_id == metadata.backup_id
        assert restore_point.status == RestoreStatus.COMPLETED
        assert restore_point.items_restored > 0
    
    def test_restore_nonexistent_backup(self, manager):
        """Test restoring from nonexistent backup."""
        restore_point = manager.restore_backup(
            backup_id="nonexistent",
            created_by="admin"
        )
        
        assert restore_point.status == RestoreStatus.FAILED
        assert "not found" in restore_point.error_message
    
    def test_list_restore_points(self, manager):
        """Test listing restore points."""
        metadata = manager.create_backup(
            backup_type=BackupType.CONFIG,
            created_by="admin",
            data={}
        )
        
        manager.restore_backup(metadata.backup_id, "admin")
        manager.restore_backup(metadata.backup_id, "admin")
        
        points = manager.list_restore_points()
        assert len(points) == 2
        
        # Filter by backup
        points = manager.list_restore_points(backup_id=metadata.backup_id)
        assert len(points) == 2


class TestLabSnapshots:
    """Tests for lab snapshots."""
    
    @pytest.fixture
    def manager(self):
        return BackupManager()
    
    def test_create_lab_snapshot(self, manager):
        """Test creating a lab snapshot."""
        snapshot = manager.create_lab_snapshot(
            lab_id="lab-123",
            scenario_id="scenario-456",
            created_by="admin",
            status="running",
            containers=[
                {"id": "c1", "image": "alpine", "status": "running"}
            ],
            networks=[
                {"id": "n1", "name": "lab-net", "subnet": "10.0.0.0/24"}
            ],
            environment={"VAR1": "value1"},
            notes="Test snapshot"
        )
        
        assert snapshot.snapshot_id is not None
        assert snapshot.lab_id == "lab-123"
        assert snapshot.scenario_id == "scenario-456"
        assert len(snapshot.containers) == 1
        assert len(snapshot.networks) == 1
    
    def test_get_lab_snapshot(self, manager):
        """Test retrieving a lab snapshot."""
        snapshot = manager.create_lab_snapshot(
            lab_id="lab-123",
            scenario_id="scenario-456",
            created_by="admin",
            status="running",
            containers=[],
            networks=[]
        )
        
        retrieved = manager.get_lab_snapshot(snapshot.snapshot_id)
        assert retrieved is not None
        assert retrieved.lab_id == "lab-123"
    
    def test_list_lab_snapshots(self, manager):
        """Test listing lab snapshots."""
        manager.create_lab_snapshot(
            lab_id="lab-1", scenario_id="s1", created_by="admin",
            status="running", containers=[], networks=[]
        )
        manager.create_lab_snapshot(
            lab_id="lab-2", scenario_id="s1", created_by="admin",
            status="stopped", containers=[], networks=[]
        )
        manager.create_lab_snapshot(
            lab_id="lab-1", scenario_id="s2", created_by="instructor",
            status="running", containers=[], networks=[]
        )
        
        # List all
        all_snapshots = manager.list_lab_snapshots()
        assert len(all_snapshots) == 3
        
        # Filter by lab
        lab1_snapshots = manager.list_lab_snapshots(lab_id="lab-1")
        assert len(lab1_snapshots) == 2
        
        # Filter by scenario
        s1_snapshots = manager.list_lab_snapshots(scenario_id="s1")
        assert len(s1_snapshots) == 2
    
    def test_delete_lab_snapshot(self, manager):
        """Test deleting a lab snapshot."""
        snapshot = manager.create_lab_snapshot(
            lab_id="lab-123", scenario_id="s1", created_by="admin",
            status="running", containers=[], networks=[]
        )
        
        assert manager.delete_lab_snapshot(snapshot.snapshot_id) is True
        assert manager.get_lab_snapshot(snapshot.snapshot_id) is None
        assert manager.delete_lab_snapshot(snapshot.snapshot_id) is False
    
    def test_restore_lab_snapshot(self, manager):
        """Test restoring from a lab snapshot."""
        snapshot = manager.create_lab_snapshot(
            lab_id="lab-123",
            scenario_id="scenario-456",
            created_by="admin",
            status="running",
            containers=[{"id": "c1"}],
            networks=[{"id": "n1"}],
            environment={"VAR": "value"}
        )
        
        result = manager.restore_lab_snapshot(
            snapshot_id=snapshot.snapshot_id,
            created_by="admin"
        )
        
        assert result is not None
        assert result["lab_id"] == "lab-123"
        assert result["scenario_id"] == "scenario-456"
        assert len(result["containers"]) == 1
        assert "restored_at" in result


class TestBackupSchedules:
    """Tests for backup scheduling."""
    
    @pytest.fixture
    def manager(self):
        return BackupManager()
    
    def test_create_daily_schedule(self, manager):
        """Test creating a daily backup schedule."""
        schedule = manager.create_schedule(
            backup_type=BackupType.SCENARIOS,
            created_by="admin",
            frequency="daily",
            time_of_day="02:00",
            retention_days=7,
            max_backups=7
        )
        
        assert schedule.schedule_id is not None
        assert schedule.backup_type == BackupType.SCENARIOS
        assert schedule.frequency == "daily"
        assert schedule.time_of_day == "02:00"
        assert schedule.enabled is True
        assert schedule.next_run is not None
    
    def test_create_weekly_schedule(self, manager):
        """Test creating a weekly backup schedule."""
        schedule = manager.create_schedule(
            backup_type=BackupType.FULL,
            created_by="admin",
            frequency="weekly",
            time_of_day="03:00",
            day_of_week=0,  # Monday
            retention_days=30,
            max_backups=4
        )
        
        assert schedule.frequency == "weekly"
        assert schedule.day_of_week == 0
    
    def test_create_monthly_schedule(self, manager):
        """Test creating a monthly backup schedule."""
        schedule = manager.create_schedule(
            backup_type=BackupType.FULL,
            created_by="admin",
            frequency="monthly",
            time_of_day="04:00",
            day_of_month=1,
            retention_days=365,
            max_backups=12
        )
        
        assert schedule.frequency == "monthly"
        assert schedule.day_of_month == 1
    
    def test_list_schedules(self, manager):
        """Test listing backup schedules."""
        manager.create_schedule(
            backup_type=BackupType.SCENARIOS,
            created_by="admin",
            frequency="daily",
            time_of_day="02:00"
        )
        manager.create_schedule(
            backup_type=BackupType.FULL,
            created_by="admin",
            frequency="weekly",
            time_of_day="03:00",
            day_of_week=0
        )
        
        schedules = manager.list_schedules()
        assert len(schedules) == 2
    
    def test_update_schedule(self, manager):
        """Test updating a backup schedule."""
        schedule = manager.create_schedule(
            backup_type=BackupType.CONFIG,
            created_by="admin",
            frequency="daily",
            time_of_day="02:00"
        )
        
        updated = manager.update_schedule(
            schedule_id=schedule.schedule_id,
            enabled=False,
            time_of_day="04:00",
            retention_days=14
        )
        
        assert updated.enabled is False
        assert updated.time_of_day == "04:00"
        assert updated.retention_days == 14
    
    def test_delete_schedule(self, manager):
        """Test deleting a backup schedule."""
        schedule = manager.create_schedule(
            backup_type=BackupType.CONFIG,
            created_by="admin",
            frequency="daily",
            time_of_day="02:00"
        )
        
        assert manager.delete_schedule(schedule.schedule_id) is True
        assert manager.get_schedule(schedule.schedule_id) is None
        assert manager.delete_schedule(schedule.schedule_id) is False
    
    def test_run_scheduled_backup(self, manager):
        """Test running a scheduled backup."""
        schedule = manager.create_schedule(
            backup_type=BackupType.SCENARIOS,
            created_by="admin",
            frequency="daily",
            time_of_day="02:00"
        )
        
        def data_provider(backup_type):
            return {"scenarios": {"s1": "data"}}
        
        metadata = manager.run_scheduled_backup(
            schedule_id=schedule.schedule_id,
            data_provider=data_provider
        )
        
        assert metadata is not None
        assert metadata.status == BackupStatus.COMPLETED
        assert "scheduled" in metadata.tags
        
        # Check schedule was updated
        updated_schedule = manager.get_schedule(schedule.schedule_id)
        assert updated_schedule.last_run is not None


class TestBackupExportImport:
    """Tests for backup export and import."""
    
    @pytest.fixture
    def manager(self):
        return BackupManager()
    
    def test_export_backup_json(self, manager):
        """Test exporting a backup as JSON."""
        metadata = manager.create_backup(
            backup_type=BackupType.CONFIG,
            created_by="admin",
            data={"setting": "value"}
        )
        
        exported = manager.export_backup(metadata.backup_id, format="json")
        assert exported is not None
        assert "setting" in exported
        assert "metadata" in exported
    
    def test_export_backup_yaml(self, manager):
        """Test exporting a backup as YAML."""
        metadata = manager.create_backup(
            backup_type=BackupType.CONFIG,
            created_by="admin",
            data={"setting": "value"}
        )
        
        exported = manager.export_backup(metadata.backup_id, format="yaml")
        assert exported is not None
        assert "setting:" in exported
    
    def test_import_backup_json(self, manager):
        """Test importing a backup from JSON."""
        # First create and export
        original = manager.create_backup(
            backup_type=BackupType.SCENARIOS,
            created_by="admin",
            description="Original backup",
            data={"scenarios": {"s1": "data"}}
        )
        
        exported = manager.export_backup(original.backup_id)
        
        # Import to new manager
        new_manager = BackupManager()
        imported = new_manager.import_backup(exported, format="json", created_by="import_user")
        
        assert imported is not None
        assert imported.backup_type == BackupType.SCENARIOS
        assert "imported" in imported.tags
    
    def test_import_invalid_content(self, manager):
        """Test importing invalid content."""
        with pytest.raises(ValueError):
            manager.import_backup("invalid json", format="json")


class TestBackupStatistics:
    """Tests for backup statistics."""
    
    @pytest.fixture
    def manager(self):
        return BackupManager()
    
    def test_get_statistics(self, manager):
        """Test getting backup statistics."""
        # Create various backups
        manager.create_backup(BackupType.SCENARIOS, "admin", data={"s": 1})
        manager.create_backup(BackupType.CONFIG, "admin", data={"c": 1})
        manager.create_backup(BackupType.SCENARIOS, "admin", data={"s": 2})
        
        # Create a snapshot
        manager.create_lab_snapshot(
            lab_id="lab1", scenario_id="s1", created_by="admin",
            status="running", containers=[], networks=[]
        )
        
        # Create a schedule
        manager.create_schedule(
            BackupType.FULL, "admin", "daily", "02:00"
        )
        
        stats = manager.get_statistics()
        
        assert stats["total_backups"] == 3
        assert stats["total_size_bytes"] > 0
        assert stats["by_type"]["scenarios"] == 2
        assert stats["by_type"]["config"] == 1
        assert stats["total_snapshots"] == 1
        assert stats["active_schedules"] == 1
    
    def test_cleanup_expired_backups(self, manager):
        """Test cleaning up expired backups."""
        # Create a backup with 0 day retention (immediately expired)
        metadata = manager.create_backup(
            backup_type=BackupType.CONFIG,
            created_by="admin",
            data={},
            retention_days=0
        )
        
        # Force the creation time to be in the past
        backup = manager.get_backup(metadata.backup_id)
        backup.metadata.created_at = datetime.utcnow() - timedelta(days=1)
        
        # Cleanup
        count = manager.cleanup_expired_backups()
        assert count == 1
        assert manager.get_backup(metadata.backup_id) is None


class TestGlobalBackupManager:
    """Tests for the global backup manager instance."""
    
    def test_global_instance_exists(self):
        """Test that global backup manager is available."""
        assert backup_manager is not None
        assert isinstance(backup_manager, BackupManager)
    
    def test_global_instance_works(self):
        """Test that global backup manager functions."""
        metadata = backup_manager.create_backup(
            backup_type=BackupType.CONFIG,
            created_by="global_test",
            data={"test": "data"}
        )
        
        assert metadata.status == BackupStatus.COMPLETED
        
        # Cleanup
        backup_manager.delete_backup(metadata.backup_id)


class TestDataclassSerialization:
    """Tests for dataclass serialization."""
    
    def test_backup_metadata_to_dict(self):
        """Test BackupMetadata serialization."""
        from backup_recovery import BackupMetadata
        
        metadata = BackupMetadata(
            backup_id="test-id",
            backup_type=BackupType.FULL,
            created_at=datetime.utcnow(),
            created_by="admin",
            description="Test",
            status=BackupStatus.COMPLETED,
            size_bytes=1024,
            compressed=True,
            compression_type=CompressionType.GZIP,
            checksum="abc123",
            tags=["test"]
        )
        
        d = metadata.to_dict()
        assert d["backup_id"] == "test-id"
        assert d["backup_type"] == "full"
        assert d["status"] == "completed"
        assert d["compression_type"] == "gzip"
    
    def test_lab_snapshot_to_dict(self):
        """Test LabSnapshot serialization."""
        from backup_recovery import LabSnapshot
        
        snapshot = LabSnapshot(
            snapshot_id="snap-123",
            lab_id="lab-456",
            scenario_id="scenario-789",
            created_at=datetime.utcnow(),
            created_by="admin",
            status="running",
            containers=[{"id": "c1"}],
            networks=[{"id": "n1"}],
            notes="Test snapshot"
        )
        
        d = snapshot.to_dict()
        assert d["snapshot_id"] == "snap-123"
        assert d["lab_id"] == "lab-456"
        assert len(d["containers"]) == 1
    
    def test_restore_point_to_dict(self):
        """Test RestorePoint serialization."""
        from backup_recovery import RestorePoint
        
        point = RestorePoint(
            restore_id="restore-123",
            backup_id="backup-456",
            created_at=datetime.utcnow(),
            created_by="admin",
            status=RestoreStatus.COMPLETED,
            items_restored=10
        )
        
        d = point.to_dict()
        assert d["restore_id"] == "restore-123"
        assert d["status"] == "completed"
        assert d["items_restored"] == 10
