"""
Compliance Reporting module for CEW Training Platform.

Provides functionality for:
- NIST Cybersecurity Framework mapping
- Training hour tracking for certifications
- Exportable compliance reports
- Integration with HR/training management systems

This module helps organizations track and report on their cybersecurity
training compliance requirements.
"""
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional


class NISTFunction(str, Enum):
    """NIST Cybersecurity Framework Core Functions."""
    IDENTIFY = "identify"
    PROTECT = "protect"
    DETECT = "detect"
    RESPOND = "respond"
    RECOVER = "recover"


class NISTCategory(str, Enum):
    """NIST Framework Categories (subset of commonly used ones)."""
    # Identify
    ID_AM = "ID.AM"  # Asset Management
    ID_BE = "ID.BE"  # Business Environment
    ID_GV = "ID.GV"  # Governance
    ID_RA = "ID.RA"  # Risk Assessment
    ID_RM = "ID.RM"  # Risk Management Strategy
    ID_SC = "ID.SC"  # Supply Chain Risk Management
    # Protect
    PR_AC = "PR.AC"  # Identity Management & Access Control
    PR_AT = "PR.AT"  # Awareness and Training
    PR_DS = "PR.DS"  # Data Security
    PR_IP = "PR.IP"  # Information Protection Processes
    PR_MA = "PR.MA"  # Maintenance
    PR_PT = "PR.PT"  # Protective Technology
    # Detect
    DE_AE = "DE.AE"  # Anomalies and Events
    DE_CM = "DE.CM"  # Security Continuous Monitoring
    DE_DP = "DE.DP"  # Detection Processes
    # Respond
    RS_RP = "RS.RP"  # Response Planning
    RS_CO = "RS.CO"  # Communications
    RS_AN = "RS.AN"  # Analysis
    RS_MI = "RS.MI"  # Mitigation
    RS_IM = "RS.IM"  # Improvements
    # Recover
    RC_RP = "RC.RP"  # Recovery Planning
    RC_IM = "RC.IM"  # Improvements
    RC_CO = "RC.CO"  # Communications


class CertificationType(str, Enum):
    """Common cybersecurity certification types."""
    CEH = "ceh"  # Certified Ethical Hacker
    CISSP = "cissp"  # Certified Information Systems Security Professional
    COMPTIA_SECURITY = "comptia_security"  # CompTIA Security+
    COMPTIA_CYSA = "comptia_cysa"  # CompTIA CySA+
    OSCP = "oscp"  # Offensive Security Certified Professional
    CISM = "cism"  # Certified Information Security Manager
    GIAC = "giac"  # GIAC Security Certifications
    INTERNAL = "internal"  # Internal/Organization-specific
    CUSTOM = "custom"  # Custom certification


class ComplianceStatus(str, Enum):
    """Status of compliance requirements."""
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    PENDING = "pending"
    EXPIRED = "expired"


class ReportFormat(str, Enum):
    """Export formats for compliance reports."""
    JSON = "json"
    CSV = "csv"
    PDF = "pdf"


@dataclass
class NISTMapping:
    """Maps a scenario or exercise to NIST Framework categories."""
    mapping_id: str
    scenario_id: str
    scenario_name: str
    nist_function: NISTFunction
    nist_categories: list[NISTCategory]
    subcategories: list[str]  # e.g., ["PR.AT-1", "PR.AT-2"]
    description: str
    learning_objectives: list[str]
    created_by: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "mapping_id": self.mapping_id,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "nist_function": self.nist_function.value,
            "nist_categories": [c.value for c in self.nist_categories],
            "subcategories": self.subcategories,
            "description": self.description,
            "learning_objectives": self.learning_objectives,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


@dataclass
class TrainingRecord:
    """Records a user's training activity."""
    record_id: str
    username: str
    scenario_id: str
    scenario_name: str
    exercise_id: Optional[str]
    exercise_name: Optional[str]
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_minutes: float = 0.0
    score: Optional[float] = None
    passed: bool = False
    nist_categories: list[NISTCategory] = field(default_factory=list)
    certification_credits: dict[str, float] = field(default_factory=dict)
    notes: str = ""
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "record_id": self.record_id,
            "username": self.username,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "exercise_id": self.exercise_id,
            "exercise_name": self.exercise_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "duration_minutes": self.duration_minutes,
            "score": self.score,
            "passed": self.passed,
            "nist_categories": [c.value for c in self.nist_categories],
            "certification_credits": self.certification_credits,
            "notes": self.notes,
            "verified_by": self.verified_by,
            "verified_at": self.verified_at.isoformat() if self.verified_at else None
        }


@dataclass
class CertificationRequirement:
    """Defines requirements for maintaining a certification."""
    requirement_id: str
    certification_type: CertificationType
    certification_name: str
    hours_required: float
    period_months: int  # Period over which hours must be completed
    categories_required: list[NISTCategory] = field(default_factory=list)
    min_categories: int = 0  # Minimum number of categories to cover
    description: str = ""
    active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "requirement_id": self.requirement_id,
            "certification_type": self.certification_type.value,
            "certification_name": self.certification_name,
            "hours_required": self.hours_required,
            "period_months": self.period_months,
            "categories_required": [c.value for c in self.categories_required],
            "min_categories": self.min_categories,
            "description": self.description,
            "active": self.active,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class UserCertificationTracker:
    """Tracks a user's progress toward certification requirements."""
    tracker_id: str
    username: str
    requirement_id: str
    certification_name: str
    start_date: datetime
    end_date: datetime
    hours_completed: float = 0.0
    hours_required: float = 0.0
    categories_covered: list[NISTCategory] = field(default_factory=list)
    status: ComplianceStatus = ComplianceStatus.PENDING
    training_records: list[str] = field(default_factory=list)  # record_ids
    last_updated: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "tracker_id": self.tracker_id,
            "username": self.username,
            "requirement_id": self.requirement_id,
            "certification_name": self.certification_name,
            "start_date": self.start_date.isoformat(),
            "end_date": self.end_date.isoformat(),
            "hours_completed": self.hours_completed,
            "hours_required": self.hours_required,
            "categories_covered": [c.value for c in self.categories_covered],
            "status": self.status.value,
            "training_records": self.training_records,
            "last_updated": self.last_updated.isoformat(),
            "progress_percent": min(100, (self.hours_completed / self.hours_required * 100)) if self.hours_required > 0 else 0
        }


@dataclass
class ComplianceReport:
    """Generated compliance report."""
    report_id: str
    report_type: str  # "individual", "team", "organization"
    title: str
    generated_by: str
    generated_at: datetime
    period_start: datetime
    period_end: datetime
    data: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    format: ReportFormat = ReportFormat.JSON

    def to_dict(self) -> dict:
        return {
            "report_id": self.report_id,
            "report_type": self.report_type,
            "title": self.title,
            "generated_by": self.generated_by,
            "generated_at": self.generated_at.isoformat(),
            "period_start": self.period_start.isoformat(),
            "period_end": self.period_end.isoformat(),
            "data": self.data,
            "summary": self.summary,
            "format": self.format.value
        }


class ComplianceManager:
    """
    Manages compliance reporting functionality.
    
    Provides:
    - NIST Framework mapping for scenarios
    - Training hour tracking
    - Certification compliance monitoring
    - Exportable compliance reports
    """

    def __init__(self):
        self._nist_mappings: dict[str, NISTMapping] = {}
        self._training_records: dict[str, TrainingRecord] = {}
        self._certification_requirements: dict[str, CertificationRequirement] = {}
        self._user_trackers: dict[str, UserCertificationTracker] = {}
        self._reports: dict[str, ComplianceReport] = {}
        self._initialize_default_requirements()
        self._initialize_nist_reference()

    def _initialize_default_requirements(self):
        """Initialize default certification requirements."""
        defaults = [
            CertificationRequirement(
                requirement_id="req_cissp_cpe",
                certification_type=CertificationType.CISSP,
                certification_name="CISSP CPE Requirements",
                hours_required=40.0,
                period_months=12,
                categories_required=[],
                min_categories=3,
                description="Annual CPE hours for CISSP maintenance"
            ),
            CertificationRequirement(
                requirement_id="req_ceh_ece",
                certification_type=CertificationType.CEH,
                certification_name="CEH ECE Requirements",
                hours_required=120.0,
                period_months=36,
                categories_required=[NISTCategory.PR_AT, NISTCategory.DE_AE],
                min_categories=2,
                description="EC-Council Continuing Education for CEH"
            ),
            CertificationRequirement(
                requirement_id="req_comptia_ce",
                certification_type=CertificationType.COMPTIA_SECURITY,
                certification_name="CompTIA Security+ CE",
                hours_required=50.0,
                period_months=36,
                categories_required=[],
                min_categories=2,
                description="CompTIA Continuing Education Units"
            ),
            CertificationRequirement(
                requirement_id="req_internal_annual",
                certification_type=CertificationType.INTERNAL,
                certification_name="Annual Security Training",
                hours_required=8.0,
                period_months=12,
                categories_required=[NISTCategory.PR_AT],
                min_categories=1,
                description="Organization annual security awareness requirement"
            )
        ]
        for req in defaults:
            self._certification_requirements[req.requirement_id] = req

    def _initialize_nist_reference(self):
        """Initialize NIST Framework reference data."""
        self._nist_reference = {
            NISTFunction.IDENTIFY: {
                "description": "Develop organizational understanding to manage cybersecurity risk",
                "categories": {
                    NISTCategory.ID_AM: "Asset Management",
                    NISTCategory.ID_BE: "Business Environment",
                    NISTCategory.ID_GV: "Governance",
                    NISTCategory.ID_RA: "Risk Assessment",
                    NISTCategory.ID_RM: "Risk Management Strategy",
                    NISTCategory.ID_SC: "Supply Chain Risk Management"
                }
            },
            NISTFunction.PROTECT: {
                "description": "Develop and implement appropriate safeguards",
                "categories": {
                    NISTCategory.PR_AC: "Identity Management and Access Control",
                    NISTCategory.PR_AT: "Awareness and Training",
                    NISTCategory.PR_DS: "Data Security",
                    NISTCategory.PR_IP: "Information Protection Processes and Procedures",
                    NISTCategory.PR_MA: "Maintenance",
                    NISTCategory.PR_PT: "Protective Technology"
                }
            },
            NISTFunction.DETECT: {
                "description": "Develop and implement activities to identify cybersecurity events",
                "categories": {
                    NISTCategory.DE_AE: "Anomalies and Events",
                    NISTCategory.DE_CM: "Security Continuous Monitoring",
                    NISTCategory.DE_DP: "Detection Processes"
                }
            },
            NISTFunction.RESPOND: {
                "description": "Develop and implement activities to take action on detected events",
                "categories": {
                    NISTCategory.RS_RP: "Response Planning",
                    NISTCategory.RS_CO: "Communications",
                    NISTCategory.RS_AN: "Analysis",
                    NISTCategory.RS_MI: "Mitigation",
                    NISTCategory.RS_IM: "Improvements"
                }
            },
            NISTFunction.RECOVER: {
                "description": "Develop and implement activities to maintain resilience",
                "categories": {
                    NISTCategory.RC_RP: "Recovery Planning",
                    NISTCategory.RC_IM: "Improvements",
                    NISTCategory.RC_CO: "Communications"
                }
            }
        }

    # NIST Mapping Management

    def create_nist_mapping(
        self,
        scenario_id: str,
        scenario_name: str,
        nist_function: NISTFunction,
        nist_categories: list[NISTCategory],
        subcategories: list[str],
        description: str,
        learning_objectives: list[str],
        created_by: str
    ) -> NISTMapping:
        """Create a NIST Framework mapping for a scenario."""
        mapping = NISTMapping(
            mapping_id=str(uuid.uuid4()),
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            nist_function=nist_function,
            nist_categories=nist_categories,
            subcategories=subcategories,
            description=description,
            learning_objectives=learning_objectives,
            created_by=created_by
        )
        self._nist_mappings[mapping.mapping_id] = mapping
        return mapping

    def get_nist_mapping(self, mapping_id: str) -> Optional[NISTMapping]:
        """Get a NIST mapping by ID."""
        return self._nist_mappings.get(mapping_id)

    def get_mapping_for_scenario(self, scenario_id: str) -> Optional[NISTMapping]:
        """Get NIST mapping for a specific scenario."""
        for mapping in self._nist_mappings.values():
            if mapping.scenario_id == scenario_id:
                return mapping
        return None

    def list_nist_mappings(
        self,
        nist_function: Optional[NISTFunction] = None,
        category: Optional[NISTCategory] = None
    ) -> list[NISTMapping]:
        """List NIST mappings with optional filters."""
        mappings = list(self._nist_mappings.values())
        
        if nist_function:
            mappings = [m for m in mappings if m.nist_function == nist_function]
        
        if category:
            mappings = [m for m in mappings if category in m.nist_categories]
        
        return mappings

    def update_nist_mapping(
        self,
        mapping_id: str,
        nist_categories: Optional[list[NISTCategory]] = None,
        subcategories: Optional[list[str]] = None,
        description: Optional[str] = None,
        learning_objectives: Optional[list[str]] = None
    ) -> Optional[NISTMapping]:
        """Update an existing NIST mapping."""
        mapping = self._nist_mappings.get(mapping_id)
        if not mapping:
            return None
        
        if nist_categories is not None:
            mapping.nist_categories = nist_categories
        if subcategories is not None:
            mapping.subcategories = subcategories
        if description is not None:
            mapping.description = description
        if learning_objectives is not None:
            mapping.learning_objectives = learning_objectives
        
        mapping.updated_at = datetime.now(timezone.utc)
        return mapping

    def delete_nist_mapping(self, mapping_id: str) -> bool:
        """Delete a NIST mapping."""
        if mapping_id in self._nist_mappings:
            del self._nist_mappings[mapping_id]
            return True
        return False

    def get_nist_reference(self) -> dict:
        """Get NIST Framework reference data."""
        result = {}
        for func, data in self._nist_reference.items():
            result[func.value] = {
                "description": data["description"],
                "categories": {k.value: v for k, v in data["categories"].items()}
            }
        return result

    def get_nist_functions(self) -> list[dict]:
        """Get list of NIST Functions."""
        return [
            {
                "value": func.value,
                "name": func.value.title(),
                "description": self._nist_reference[func]["description"]
            }
            for func in NISTFunction
        ]

    def get_nist_categories(self, function: Optional[NISTFunction] = None) -> list[dict]:
        """Get list of NIST Categories, optionally filtered by function."""
        categories = []
        for func, data in self._nist_reference.items():
            if function and func != function:
                continue
            for cat, name in data["categories"].items():
                categories.append({
                    "value": cat.value,
                    "name": name,
                    "function": func.value
                })
        return categories

    # Training Record Management

    def start_training_record(
        self,
        username: str,
        scenario_id: str,
        scenario_name: str,
        exercise_id: Optional[str] = None,
        exercise_name: Optional[str] = None
    ) -> TrainingRecord:
        """Start tracking a training session."""
        # Get NIST categories from scenario mapping
        mapping = self.get_mapping_for_scenario(scenario_id)
        nist_categories = mapping.nist_categories if mapping else []
        
        record = TrainingRecord(
            record_id=str(uuid.uuid4()),
            username=username,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            exercise_id=exercise_id,
            exercise_name=exercise_name,
            started_at=datetime.now(timezone.utc),
            nist_categories=nist_categories
        )
        self._training_records[record.record_id] = record
        return record

    def complete_training_record(
        self,
        record_id: str,
        score: Optional[float] = None,
        passed: bool = False,
        notes: str = ""
    ) -> Optional[TrainingRecord]:
        """Complete a training record."""
        record = self._training_records.get(record_id)
        if not record:
            return None
        
        record.completed_at = datetime.now(timezone.utc)
        record.duration_minutes = (
            record.completed_at - record.started_at
        ).total_seconds() / 60.0
        record.score = score
        record.passed = passed
        record.notes = notes
        
        # Calculate certification credits based on duration and categories
        credits = {}
        hours = record.duration_minutes / 60.0
        
        for req in self._certification_requirements.values():
            if req.active:
                # Check if training covers required categories
                if not req.categories_required or any(
                    cat in record.nist_categories for cat in req.categories_required
                ):
                    credits[req.certification_type.value] = hours
        
        record.certification_credits = credits
        
        # Update user certification trackers
        self._update_user_trackers(record)
        
        return record

    def verify_training_record(
        self,
        record_id: str,
        verified_by: str
    ) -> Optional[TrainingRecord]:
        """Verify a training record (instructor/admin)."""
        record = self._training_records.get(record_id)
        if not record:
            return None
        
        record.verified_by = verified_by
        record.verified_at = datetime.now(timezone.utc)
        return record

    def get_training_record(self, record_id: str) -> Optional[TrainingRecord]:
        """Get a training record by ID."""
        return self._training_records.get(record_id)

    def get_user_training_records(
        self,
        username: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        verified_only: bool = False
    ) -> list[TrainingRecord]:
        """Get training records for a user."""
        records = [
            r for r in self._training_records.values()
            if r.username == username
        ]
        
        if start_date:
            records = [r for r in records if r.started_at >= start_date]
        
        if end_date:
            records = [r for r in records if r.started_at <= end_date]
        
        if verified_only:
            records = [r for r in records if r.verified_by is not None]
        
        return sorted(records, key=lambda r: r.started_at, reverse=True)

    def get_user_training_hours(
        self,
        username: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """Calculate total training hours for a user."""
        records = self.get_user_training_records(username, start_date, end_date)
        
        completed_records = [r for r in records if r.completed_at]
        
        total_hours = sum(r.duration_minutes for r in completed_records) / 60.0
        
        # Hours by NIST category
        by_category = {}
        for record in completed_records:
            hours = record.duration_minutes / 60.0
            for cat in record.nist_categories:
                cat_key = cat.value
                by_category[cat_key] = by_category.get(cat_key, 0) + hours
        
        # Hours by NIST function
        by_function = {}
        for cat_key, hours in by_category.items():
            for func in NISTFunction:
                if any(cat_key.startswith(func.value.upper()[:2]) for _ in [1]):
                    by_function[func.value] = by_function.get(func.value, 0) + hours
        
        return {
            "username": username,
            "total_hours": round(total_hours, 2),
            "total_records": len(completed_records),
            "by_category": {k: round(v, 2) for k, v in by_category.items()},
            "by_function": {k: round(v, 2) for k, v in by_function.items()},
            "period": {
                "start": start_date.isoformat() if start_date else None,
                "end": end_date.isoformat() if end_date else None
            }
        }

    # Certification Tracking

    def create_certification_requirement(
        self,
        certification_type: CertificationType,
        certification_name: str,
        hours_required: float,
        period_months: int,
        categories_required: list[NISTCategory] = None,
        min_categories: int = 0,
        description: str = ""
    ) -> CertificationRequirement:
        """Create a certification requirement."""
        requirement = CertificationRequirement(
            requirement_id=str(uuid.uuid4()),
            certification_type=certification_type,
            certification_name=certification_name,
            hours_required=hours_required,
            period_months=period_months,
            categories_required=categories_required or [],
            min_categories=min_categories,
            description=description
        )
        self._certification_requirements[requirement.requirement_id] = requirement
        return requirement

    def get_certification_requirement(
        self, requirement_id: str
    ) -> Optional[CertificationRequirement]:
        """Get a certification requirement by ID."""
        return self._certification_requirements.get(requirement_id)

    def list_certification_requirements(
        self, active_only: bool = True
    ) -> list[CertificationRequirement]:
        """List certification requirements."""
        requirements = list(self._certification_requirements.values())
        if active_only:
            requirements = [r for r in requirements if r.active]
        return requirements

    def enroll_user_in_certification(
        self,
        username: str,
        requirement_id: str
    ) -> Optional[UserCertificationTracker]:
        """Enroll a user in certification tracking."""
        requirement = self._certification_requirements.get(requirement_id)
        if not requirement:
            return None
        
        # Check if already enrolled
        for tracker in self._user_trackers.values():
            if tracker.username == username and tracker.requirement_id == requirement_id:
                if tracker.status not in [ComplianceStatus.EXPIRED, ComplianceStatus.COMPLIANT]:
                    return tracker  # Already tracking
        
        start_date = datetime.now(timezone.utc)
        end_date = start_date + timedelta(days=requirement.period_months * 30)
        
        tracker = UserCertificationTracker(
            tracker_id=str(uuid.uuid4()),
            username=username,
            requirement_id=requirement_id,
            certification_name=requirement.certification_name,
            start_date=start_date,
            end_date=end_date,
            hours_required=requirement.hours_required,
            status=ComplianceStatus.PENDING
        )
        self._user_trackers[tracker.tracker_id] = tracker
        return tracker

    def _update_user_trackers(self, record: TrainingRecord):
        """Update certification trackers when training is completed."""
        for tracker in self._user_trackers.values():
            if tracker.username != record.username:
                continue
            if tracker.status in [ComplianceStatus.EXPIRED, ComplianceStatus.COMPLIANT]:
                continue
            
            # Check if within tracking period
            if not (tracker.start_date <= record.started_at <= tracker.end_date):
                continue
            
            # Add hours
            hours = record.duration_minutes / 60.0
            tracker.hours_completed += hours
            tracker.training_records.append(record.record_id)
            
            # Update categories covered
            for cat in record.nist_categories:
                if cat not in tracker.categories_covered:
                    tracker.categories_covered.append(cat)
            
            # Update status
            tracker.last_updated = datetime.now(timezone.utc)
            tracker.status = self._calculate_tracker_status(tracker)

    def _calculate_tracker_status(
        self, tracker: UserCertificationTracker
    ) -> ComplianceStatus:
        """Calculate the compliance status of a tracker."""
        requirement = self._certification_requirements.get(tracker.requirement_id)
        
        # Check if expired
        if datetime.now(timezone.utc) > tracker.end_date:
            return ComplianceStatus.EXPIRED
        
        # Check hours
        hours_met = tracker.hours_completed >= tracker.hours_required
        
        # Check categories if required
        categories_met = True
        if requirement and requirement.min_categories > 0:
            categories_met = len(tracker.categories_covered) >= requirement.min_categories
        
        if hours_met and categories_met:
            return ComplianceStatus.COMPLIANT
        elif tracker.hours_completed > 0:
            return ComplianceStatus.PARTIAL
        else:
            return ComplianceStatus.PENDING

    def get_user_certification_trackers(
        self,
        username: str,
        status: Optional[ComplianceStatus] = None
    ) -> list[UserCertificationTracker]:
        """Get certification trackers for a user."""
        trackers = [
            t for t in self._user_trackers.values()
            if t.username == username
        ]
        
        if status:
            trackers = [t for t in trackers if t.status == status]
        
        return trackers

    def get_user_compliance_summary(self, username: str) -> dict:
        """Get compliance summary for a user."""
        trackers = self.get_user_certification_trackers(username)
        training_hours = self.get_user_training_hours(username)
        
        by_status = {}
        for tracker in trackers:
            status = tracker.status.value
            by_status[status] = by_status.get(status, 0) + 1
        
        return {
            "username": username,
            "total_certifications": len(trackers),
            "by_status": by_status,
            "total_training_hours": training_hours["total_hours"],
            "certifications": [t.to_dict() for t in trackers]
        }

    # Report Generation

    def generate_individual_report(
        self,
        username: str,
        generated_by: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> ComplianceReport:
        """Generate an individual compliance report."""
        if not period_end:
            period_end = datetime.now(timezone.utc)
        if not period_start:
            period_start = period_end - timedelta(days=365)
        
        training_records = self.get_user_training_records(
            username, period_start, period_end
        )
        training_hours = self.get_user_training_hours(
            username, period_start, period_end
        )
        trackers = self.get_user_certification_trackers(username)
        
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type="individual",
            title=f"Compliance Report - {username}",
            generated_by=generated_by,
            generated_at=datetime.now(timezone.utc),
            period_start=period_start,
            period_end=period_end,
            data={
                "training_records": [r.to_dict() for r in training_records],
                "certification_trackers": [t.to_dict() for t in trackers]
            },
            summary={
                "total_hours": training_hours["total_hours"],
                "total_sessions": len(training_records),
                "hours_by_category": training_hours["by_category"],
                "hours_by_function": training_hours["by_function"],
                "certifications_compliant": sum(
                    1 for t in trackers if t.status == ComplianceStatus.COMPLIANT
                ),
                "certifications_pending": sum(
                    1 for t in trackers if t.status == ComplianceStatus.PENDING
                ),
                "certifications_partial": sum(
                    1 for t in trackers if t.status == ComplianceStatus.PARTIAL
                )
            }
        )
        self._reports[report.report_id] = report
        return report

    def generate_team_report(
        self,
        usernames: list[str],
        team_name: str,
        generated_by: str,
        period_start: Optional[datetime] = None,
        period_end: Optional[datetime] = None
    ) -> ComplianceReport:
        """Generate a team compliance report."""
        if not period_end:
            period_end = datetime.now(timezone.utc)
        if not period_start:
            period_start = period_end - timedelta(days=365)
        
        individual_data = []
        total_hours = 0
        compliant_count = 0
        
        for username in usernames:
            hours = self.get_user_training_hours(username, period_start, period_end)
            trackers = self.get_user_certification_trackers(username)
            
            total_hours += hours["total_hours"]
            compliant_count += sum(
                1 for t in trackers if t.status == ComplianceStatus.COMPLIANT
            )
            
            individual_data.append({
                "username": username,
                "total_hours": hours["total_hours"],
                "certifications": [t.to_dict() for t in trackers]
            })
        
        report = ComplianceReport(
            report_id=str(uuid.uuid4()),
            report_type="team",
            title=f"Team Compliance Report - {team_name}",
            generated_by=generated_by,
            generated_at=datetime.now(timezone.utc),
            period_start=period_start,
            period_end=period_end,
            data={
                "team_name": team_name,
                "members": individual_data
            },
            summary={
                "team_size": len(usernames),
                "total_hours": round(total_hours, 2),
                "average_hours": round(total_hours / len(usernames), 2) if usernames else 0,
                "compliant_certifications": compliant_count
            }
        )
        self._reports[report.report_id] = report
        return report

    def get_report(self, report_id: str) -> Optional[ComplianceReport]:
        """Get a report by ID."""
        return self._reports.get(report_id)

    def list_reports(
        self,
        report_type: Optional[str] = None,
        limit: int = 50
    ) -> list[ComplianceReport]:
        """List generated reports."""
        reports = list(self._reports.values())
        
        if report_type:
            reports = [r for r in reports if r.report_type == report_type]
        
        reports.sort(key=lambda r: r.generated_at, reverse=True)
        return reports[:limit]

    def export_report(self, report_id: str, format: ReportFormat) -> Optional[str]:
        """Export a report in the specified format."""
        report = self._reports.get(report_id)
        if not report:
            return None
        
        if format == ReportFormat.JSON:
            return json.dumps(report.to_dict(), indent=2)
        elif format == ReportFormat.CSV:
            return self._export_to_csv(report)
        else:
            return None  # PDF would require additional libraries

    def _export_to_csv(self, report: ComplianceReport) -> str:
        """Export report to CSV format."""
        lines = [
            f"Report: {report.title}",
            f"Generated: {report.generated_at.isoformat()}",
            f"Period: {report.period_start.isoformat()} to {report.period_end.isoformat()}",
            "",
            "Summary:",
        ]
        
        for key, value in report.summary.items():
            lines.append(f"{key},{value}")
        
        lines.append("")
        lines.append("Training Records:")
        
        if "training_records" in report.data:
            lines.append("Record ID,Scenario,Duration (min),Score,Passed")
            for record in report.data["training_records"]:
                lines.append(
                    f"{record['record_id']},{record['scenario_name']},"
                    f"{record['duration_minutes']},{record.get('score', 'N/A')},"
                    f"{record['passed']}"
                )
        
        return "\n".join(lines)

    def get_statistics(self) -> dict:
        """Get compliance reporting statistics."""
        return {
            "total_nist_mappings": len(self._nist_mappings),
            "total_training_records": len(self._training_records),
            "total_certification_requirements": len(self._certification_requirements),
            "active_trackers": len([
                t for t in self._user_trackers.values()
                if t.status not in [ComplianceStatus.EXPIRED, ComplianceStatus.COMPLIANT]
            ]),
            "generated_reports": len(self._reports),
            "compliance_by_status": {
                status.value: len([
                    t for t in self._user_trackers.values()
                    if t.status == status
                ])
                for status in ComplianceStatus
            }
        }


# Global compliance manager instance
compliance_manager = ComplianceManager()
