"""
Tests for compliance reporting functionality.
"""
import pytest
from datetime import datetime, timedelta, timezone

from compliance_reporting import (
    ComplianceManager,
    NISTFunction,
    NISTCategory,
    CertificationType,
    ComplianceStatus,
    ReportFormat
)


@pytest.fixture
def compliance_mgr():
    """Create a fresh compliance manager for each test."""
    return ComplianceManager()


class TestNISTReference:
    """Tests for NIST Framework reference data."""
    
    def test_get_nist_reference(self, compliance_mgr):
        """Test getting NIST reference data."""
        reference = compliance_mgr.get_nist_reference()
        
        assert "identify" in reference
        assert "protect" in reference
        assert "detect" in reference
        assert "respond" in reference
        assert "recover" in reference
        
        # Check structure
        assert "description" in reference["identify"]
        assert "categories" in reference["identify"]
    
    def test_get_nist_functions(self, compliance_mgr):
        """Test getting NIST functions."""
        functions = compliance_mgr.get_nist_functions()
        
        assert len(functions) == 5
        func_values = [f["value"] for f in functions]
        assert "identify" in func_values
        assert "protect" in func_values
    
    def test_get_nist_categories(self, compliance_mgr):
        """Test getting NIST categories."""
        categories = compliance_mgr.get_nist_categories()
        
        assert len(categories) > 0
        assert all("value" in c for c in categories)
        assert all("name" in c for c in categories)
        assert all("function" in c for c in categories)
    
    def test_get_nist_categories_filtered(self, compliance_mgr):
        """Test getting NIST categories filtered by function."""
        categories = compliance_mgr.get_nist_categories(NISTFunction.PROTECT)
        
        assert len(categories) > 0
        assert all(c["function"] == "protect" for c in categories)


class TestNISTMappings:
    """Tests for NIST mapping management."""
    
    def test_create_nist_mapping(self, compliance_mgr):
        """Test creating a NIST mapping."""
        mapping = compliance_mgr.create_nist_mapping(
            scenario_id="scenario-1",
            scenario_name="Test Scenario",
            nist_function=NISTFunction.PROTECT,
            nist_categories=[NISTCategory.PR_AT, NISTCategory.PR_AC],
            subcategories=["PR.AT-1", "PR.AT-2"],
            description="Test mapping",
            learning_objectives=["Objective 1"],
            created_by="admin"
        )
        
        assert mapping.mapping_id is not None
        assert mapping.scenario_id == "scenario-1"
        assert mapping.nist_function == NISTFunction.PROTECT
        assert len(mapping.nist_categories) == 2
    
    def test_get_nist_mapping(self, compliance_mgr):
        """Test getting a NIST mapping by ID."""
        mapping = compliance_mgr.create_nist_mapping(
            scenario_id="scenario-1",
            scenario_name="Test",
            nist_function=NISTFunction.DETECT,
            nist_categories=[NISTCategory.DE_AE],
            subcategories=[],
            description="Test",
            learning_objectives=[],
            created_by="admin"
        )
        
        retrieved = compliance_mgr.get_nist_mapping(mapping.mapping_id)
        
        assert retrieved is not None
        assert retrieved.mapping_id == mapping.mapping_id
    
    def test_get_mapping_for_scenario(self, compliance_mgr):
        """Test getting mapping for a specific scenario."""
        compliance_mgr.create_nist_mapping(
            scenario_id="scenario-xyz",
            scenario_name="Test",
            nist_function=NISTFunction.RESPOND,
            nist_categories=[NISTCategory.RS_AN],
            subcategories=[],
            description="Test",
            learning_objectives=[],
            created_by="admin"
        )
        
        mapping = compliance_mgr.get_mapping_for_scenario("scenario-xyz")
        
        assert mapping is not None
        assert mapping.scenario_id == "scenario-xyz"
    
    def test_list_nist_mappings(self, compliance_mgr):
        """Test listing NIST mappings."""
        compliance_mgr.create_nist_mapping(
            scenario_id="s1", scenario_name="S1",
            nist_function=NISTFunction.IDENTIFY,
            nist_categories=[NISTCategory.ID_AM],
            subcategories=[], description="", learning_objectives=[],
            created_by="admin"
        )
        compliance_mgr.create_nist_mapping(
            scenario_id="s2", scenario_name="S2",
            nist_function=NISTFunction.PROTECT,
            nist_categories=[NISTCategory.PR_AT],
            subcategories=[], description="", learning_objectives=[],
            created_by="admin"
        )
        
        all_mappings = compliance_mgr.list_nist_mappings()
        assert len(all_mappings) == 2
        
        identify_mappings = compliance_mgr.list_nist_mappings(
            nist_function=NISTFunction.IDENTIFY
        )
        assert len(identify_mappings) == 1
    
    def test_update_nist_mapping(self, compliance_mgr):
        """Test updating a NIST mapping."""
        mapping = compliance_mgr.create_nist_mapping(
            scenario_id="s1", scenario_name="S1",
            nist_function=NISTFunction.DETECT,
            nist_categories=[NISTCategory.DE_AE],
            subcategories=[], description="Original",
            learning_objectives=[], created_by="admin"
        )
        
        updated = compliance_mgr.update_nist_mapping(
            mapping_id=mapping.mapping_id,
            description="Updated description",
            subcategories=["DE.AE-1"]
        )
        
        assert updated is not None
        assert updated.description == "Updated description"
        assert "DE.AE-1" in updated.subcategories
    
    def test_delete_nist_mapping(self, compliance_mgr):
        """Test deleting a NIST mapping."""
        mapping = compliance_mgr.create_nist_mapping(
            scenario_id="s1", scenario_name="S1",
            nist_function=NISTFunction.RECOVER,
            nist_categories=[NISTCategory.RC_RP],
            subcategories=[], description="",
            learning_objectives=[], created_by="admin"
        )
        
        result = compliance_mgr.delete_nist_mapping(mapping.mapping_id)
        assert result is True
        
        assert compliance_mgr.get_nist_mapping(mapping.mapping_id) is None


class TestTrainingRecords:
    """Tests for training record management."""
    
    def test_start_training_record(self, compliance_mgr):
        """Test starting a training record."""
        record = compliance_mgr.start_training_record(
            username="trainee1",
            scenario_id="scenario-1",
            scenario_name="Test Scenario",
            exercise_id="ex-1",
            exercise_name="Exercise 1"
        )
        
        assert record.record_id is not None
        assert record.username == "trainee1"
        assert record.scenario_id == "scenario-1"
        assert record.started_at is not None
        assert record.completed_at is None
    
    def test_complete_training_record(self, compliance_mgr):
        """Test completing a training record."""
        record = compliance_mgr.start_training_record(
            username="trainee1",
            scenario_id="scenario-1",
            scenario_name="Test Scenario"
        )
        
        completed = compliance_mgr.complete_training_record(
            record_id=record.record_id,
            score=85.0,
            passed=True,
            notes="Good work"
        )
        
        assert completed is not None
        assert completed.completed_at is not None
        assert completed.score == 85.0
        assert completed.passed is True
        assert completed.duration_minutes >= 0
    
    def test_verify_training_record(self, compliance_mgr):
        """Test verifying a training record."""
        record = compliance_mgr.start_training_record(
            username="trainee1",
            scenario_id="scenario-1",
            scenario_name="Test"
        )
        compliance_mgr.complete_training_record(record.record_id)
        
        verified = compliance_mgr.verify_training_record(
            record_id=record.record_id,
            verified_by="instructor1"
        )
        
        assert verified is not None
        assert verified.verified_by == "instructor1"
        assert verified.verified_at is not None
    
    def test_get_user_training_records(self, compliance_mgr):
        """Test getting user's training records."""
        # Create multiple records
        for i in range(3):
            record = compliance_mgr.start_training_record(
                username="trainee1",
                scenario_id=f"scenario-{i}",
                scenario_name=f"Scenario {i}"
            )
            compliance_mgr.complete_training_record(record.record_id)
        
        records = compliance_mgr.get_user_training_records("trainee1")
        
        assert len(records) == 3
    
    def test_get_user_training_hours(self, compliance_mgr):
        """Test calculating user's training hours."""
        # Create and complete records with known durations
        record = compliance_mgr.start_training_record(
            username="trainee1",
            scenario_id="scenario-1",
            scenario_name="Test"
        )
        compliance_mgr.complete_training_record(record.record_id)
        
        hours = compliance_mgr.get_user_training_hours("trainee1")
        
        assert "username" in hours
        assert "total_hours" in hours
        assert "total_records" in hours
        assert "by_category" in hours


class TestCertificationTracking:
    """Tests for certification requirement and tracking."""
    
    def test_default_requirements_loaded(self, compliance_mgr):
        """Test that default certification requirements are loaded."""
        requirements = compliance_mgr.list_certification_requirements()
        
        assert len(requirements) > 0
    
    def test_create_certification_requirement(self, compliance_mgr):
        """Test creating a certification requirement."""
        requirement = compliance_mgr.create_certification_requirement(
            certification_type=CertificationType.CUSTOM,
            certification_name="Custom Cert",
            hours_required=20.0,
            period_months=12,
            categories_required=[NISTCategory.PR_AT],
            min_categories=1,
            description="Custom certification"
        )
        
        assert requirement.requirement_id is not None
        assert requirement.certification_name == "Custom Cert"
        assert requirement.hours_required == 20.0
    
    def test_enroll_user_in_certification(self, compliance_mgr):
        """Test enrolling a user in certification tracking."""
        requirements = compliance_mgr.list_certification_requirements()
        requirement = requirements[0]
        
        tracker = compliance_mgr.enroll_user_in_certification(
            username="trainee1",
            requirement_id=requirement.requirement_id
        )
        
        assert tracker is not None
        assert tracker.username == "trainee1"
        assert tracker.status == ComplianceStatus.PENDING
        assert tracker.hours_completed == 0
    
    def test_get_user_certification_trackers(self, compliance_mgr):
        """Test getting user's certification trackers."""
        requirements = compliance_mgr.list_certification_requirements()
        
        for req in requirements[:2]:
            compliance_mgr.enroll_user_in_certification(
                username="trainee1",
                requirement_id=req.requirement_id
            )
        
        trackers = compliance_mgr.get_user_certification_trackers("trainee1")
        
        assert len(trackers) == 2
    
    def test_certification_status_updates(self, compliance_mgr):
        """Test that certification status updates with training."""
        # Create a mapping so training gets categories
        compliance_mgr.create_nist_mapping(
            scenario_id="scenario-1",
            scenario_name="Test",
            nist_function=NISTFunction.PROTECT,
            nist_categories=[NISTCategory.PR_AT],
            subcategories=[],
            description="",
            learning_objectives=[],
            created_by="admin"
        )
        
        # Enroll in internal annual training (8 hours)
        requirements = compliance_mgr.list_certification_requirements()
        internal_req = next(
            (r for r in requirements if r.certification_type == CertificationType.INTERNAL),
            None
        )
        
        if internal_req:
            tracker = compliance_mgr.enroll_user_in_certification(
                username="trainee1",
                requirement_id=internal_req.requirement_id
            )
            
            # Start and complete training
            record = compliance_mgr.start_training_record(
                username="trainee1",
                scenario_id="scenario-1",
                scenario_name="Test"
            )
            
            compliance_mgr.complete_training_record(record.record_id)
            
            # Check tracker was updated
            updated_tracker = compliance_mgr.get_user_certification_trackers("trainee1")[0]
            assert updated_tracker.hours_completed > 0


class TestComplianceReports:
    """Tests for compliance report generation."""
    
    def test_generate_individual_report(self, compliance_mgr):
        """Test generating an individual compliance report."""
        # Add some training data
        record = compliance_mgr.start_training_record(
            username="trainee1",
            scenario_id="scenario-1",
            scenario_name="Test"
        )
        compliance_mgr.complete_training_record(record.record_id, score=90, passed=True)
        
        report = compliance_mgr.generate_individual_report(
            username="trainee1",
            generated_by="admin"
        )
        
        assert report.report_id is not None
        assert report.report_type == "individual"
        assert "training_records" in report.data
        assert "total_hours" in report.summary
    
    def test_generate_team_report(self, compliance_mgr):
        """Test generating a team compliance report."""
        # Add training for multiple users
        for user in ["user1", "user2", "user3"]:
            record = compliance_mgr.start_training_record(
                username=user,
                scenario_id="scenario-1",
                scenario_name="Test"
            )
            compliance_mgr.complete_training_record(record.record_id)
        
        report = compliance_mgr.generate_team_report(
            usernames=["user1", "user2", "user3"],
            team_name="Test Team",
            generated_by="admin"
        )
        
        assert report.report_id is not None
        assert report.report_type == "team"
        assert "team_name" in report.data
        assert "members" in report.data
        assert report.summary["team_size"] == 3
    
    def test_list_reports(self, compliance_mgr):
        """Test listing generated reports."""
        # Generate a few reports
        compliance_mgr.generate_individual_report(
            username="user1", generated_by="admin"
        )
        compliance_mgr.generate_individual_report(
            username="user2", generated_by="admin"
        )
        
        reports = compliance_mgr.list_reports()
        
        assert len(reports) == 2
    
    def test_export_report_json(self, compliance_mgr):
        """Test exporting report as JSON."""
        report = compliance_mgr.generate_individual_report(
            username="user1", generated_by="admin"
        )
        
        exported = compliance_mgr.export_report(report.report_id, ReportFormat.JSON)
        
        assert exported is not None
        assert "report_id" in exported
    
    def test_export_report_csv(self, compliance_mgr):
        """Test exporting report as CSV."""
        record = compliance_mgr.start_training_record(
            username="user1",
            scenario_id="scenario-1",
            scenario_name="Test"
        )
        compliance_mgr.complete_training_record(record.record_id)
        
        report = compliance_mgr.generate_individual_report(
            username="user1", generated_by="admin"
        )
        
        exported = compliance_mgr.export_report(report.report_id, ReportFormat.CSV)
        
        assert exported is not None
        assert "Report:" in exported


class TestComplianceSummary:
    """Tests for compliance summary functionality."""
    
    def test_get_user_compliance_summary(self, compliance_mgr):
        """Test getting user's compliance summary."""
        # Enroll in some certifications
        requirements = compliance_mgr.list_certification_requirements()
        for req in requirements[:2]:
            compliance_mgr.enroll_user_in_certification(
                username="trainee1",
                requirement_id=req.requirement_id
            )
        
        summary = compliance_mgr.get_user_compliance_summary("trainee1")
        
        assert summary["username"] == "trainee1"
        assert summary["total_certifications"] == 2
        assert "by_status" in summary
    
    def test_get_statistics(self, compliance_mgr):
        """Test getting compliance statistics."""
        # Create some data
        compliance_mgr.create_nist_mapping(
            scenario_id="s1", scenario_name="S1",
            nist_function=NISTFunction.IDENTIFY,
            nist_categories=[NISTCategory.ID_AM],
            subcategories=[], description="",
            learning_objectives=[], created_by="admin"
        )
        
        stats = compliance_mgr.get_statistics()
        
        assert "total_nist_mappings" in stats
        assert "total_training_records" in stats
        assert "total_certification_requirements" in stats
        assert "compliance_by_status" in stats


class TestDataclassSerialization:
    """Tests for dataclass serialization."""
    
    def test_nist_mapping_to_dict(self, compliance_mgr):
        """Test NISTMapping serialization."""
        mapping = compliance_mgr.create_nist_mapping(
            scenario_id="s1", scenario_name="S1",
            nist_function=NISTFunction.DETECT,
            nist_categories=[NISTCategory.DE_CM],
            subcategories=["DE.CM-1"],
            description="Test",
            learning_objectives=["Obj1"],
            created_by="admin"
        )
        
        data = mapping.to_dict()
        
        assert data["mapping_id"] == mapping.mapping_id
        assert data["nist_function"] == "detect"
        assert data["nist_categories"] == ["DE.CM"]
    
    def test_training_record_to_dict(self, compliance_mgr):
        """Test TrainingRecord serialization."""
        record = compliance_mgr.start_training_record(
            username="user1",
            scenario_id="s1",
            scenario_name="S1"
        )
        
        data = record.to_dict()
        
        assert data["record_id"] == record.record_id
        assert data["username"] == "user1"
        assert "started_at" in data
    
    def test_certification_requirement_to_dict(self, compliance_mgr):
        """Test CertificationRequirement serialization."""
        requirement = compliance_mgr.create_certification_requirement(
            certification_type=CertificationType.CUSTOM,
            certification_name="Test Cert",
            hours_required=10.0,
            period_months=6
        )
        
        data = requirement.to_dict()
        
        assert data["certification_type"] == "custom"
        assert data["hours_required"] == 10.0
    
    def test_compliance_report_to_dict(self, compliance_mgr):
        """Test ComplianceReport serialization."""
        report = compliance_mgr.generate_individual_report(
            username="user1",
            generated_by="admin"
        )
        
        data = report.to_dict()
        
        assert data["report_id"] == report.report_id
        assert data["report_type"] == "individual"
        assert "generated_at" in data
