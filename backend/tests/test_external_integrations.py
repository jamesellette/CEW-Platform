"""Tests for external tools integration."""

import pytest
from datetime import datetime

from external_integrations import (
    ExternalIntegrations, IntegrationType, IntegrationStatus,
    LogLevel, external_integrations
)


class TestIntegrationManagement:
    """Tests for integration management."""
    
    @pytest.fixture
    def integrations(self):
        """Create a fresh integrations manager."""
        return ExternalIntegrations()
    
    def test_create_integration(self, integrations):
        """Test creating an integration."""
        config = integrations.create_integration(
            integration_type=IntegrationType.SPLUNK,
            name="Splunk SIEM",
            created_by="admin",
            config={"host": "splunk.example.com", "port": 8089}
        )
        
        assert config.integration_id is not None
        assert config.integration_type == IntegrationType.SPLUNK
        assert config.name == "Splunk SIEM"
        assert config.enabled is True
        assert config.status == IntegrationStatus.DISCONNECTED
    
    def test_get_integration(self, integrations):
        """Test retrieving an integration."""
        config = integrations.create_integration(
            integration_type=IntegrationType.ELASTICSEARCH,
            name="ELK Stack",
            created_by="admin"
        )
        
        retrieved = integrations.get_integration(config.integration_id)
        assert retrieved is not None
        assert retrieved.name == "ELK Stack"
    
    def test_list_integrations(self, integrations):
        """Test listing integrations."""
        integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk 1", "admin"
        )
        integrations.create_integration(
            IntegrationType.ELASTICSEARCH, "ELK", "admin"
        )
        integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk 2", "admin", enabled=False
        )
        
        # List all
        all_integrations = integrations.list_integrations()
        assert len(all_integrations) == 3
        
        # Filter by type
        splunk_only = integrations.list_integrations(
            integration_type=IntegrationType.SPLUNK
        )
        assert len(splunk_only) == 2
        
        # Filter enabled only
        enabled_only = integrations.list_integrations(enabled_only=True)
        assert len(enabled_only) == 2
    
    def test_update_integration(self, integrations):
        """Test updating an integration."""
        config = integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk", "admin"
        )
        
        updated = integrations.update_integration(
            config.integration_id,
            name="Splunk SIEM Updated",
            enabled=False,
            config={"api_key": "secret"}
        )
        
        assert updated.name == "Splunk SIEM Updated"
        assert updated.enabled is False
        assert "api_key" in updated.config
    
    def test_delete_integration(self, integrations):
        """Test deleting an integration."""
        config = integrations.create_integration(
            IntegrationType.MININET, "Mininet", "admin"
        )
        
        assert integrations.delete_integration(config.integration_id) is True
        assert integrations.get_integration(config.integration_id) is None
        assert integrations.delete_integration(config.integration_id) is False
    
    def test_test_integration(self, integrations):
        """Test integration connectivity test."""
        config = integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk", "admin",
            config={"host": "localhost"}
        )
        
        result = integrations.test_integration(config.integration_id)
        
        assert result["success"] is True
        assert result["integration_id"] == config.integration_id
        
        # Check status updated
        updated = integrations.get_integration(config.integration_id)
        assert updated.status == IntegrationStatus.CONNECTED
        assert updated.last_connected is not None


class TestMitreAttack:
    """Tests for MITRE ATT&CK integration."""
    
    @pytest.fixture
    def integrations(self):
        return ExternalIntegrations()
    
    def test_get_technique(self, integrations):
        """Test getting a MITRE ATT&CK technique."""
        technique = integrations.get_technique("T1059")
        
        assert technique is not None
        assert technique.technique_id == "T1059"
        assert technique.name == "Command and Scripting Interpreter"
        assert technique.tactic == "Execution"
    
    def test_list_techniques(self, integrations):
        """Test listing techniques."""
        all_techniques = integrations.list_techniques()
        assert len(all_techniques) > 0
        
        # Filter by tactic
        execution = integrations.list_techniques(tactic="Execution")
        assert all(t.tactic == "Execution" for t in execution)
        
        # Filter by platform
        windows = integrations.list_techniques(platform="Windows")
        assert all("Windows" in t.platforms for t in windows)
        
        # Search
        ssh = integrations.list_techniques(search="SSH")
        assert len(ssh) > 0
        assert any("SSH" in t.name for t in ssh)
    
    def test_get_tactics(self, integrations):
        """Test getting tactics list."""
        tactics = integrations.get_tactics()
        
        assert len(tactics) == 14
        assert "Execution" in tactics
        assert "Impact" in tactics
    
    def test_create_attack_mapping(self, integrations):
        """Test creating an ATT&CK mapping."""
        mapping = integrations.create_attack_mapping(
            scenario_id="scenario-123",
            scenario_name="Network Attack Scenario",
            techniques=["T1059", "T1046", "T1021"],
            created_by="instructor",
            notes="Basic attack chain"
        )
        
        assert mapping.mapping_id is not None
        assert mapping.scenario_id == "scenario-123"
        assert len(mapping.techniques) == 3
    
    def test_create_mapping_validates_techniques(self, integrations):
        """Test that invalid techniques are filtered out."""
        mapping = integrations.create_attack_mapping(
            scenario_id="scenario-123",
            scenario_name="Test",
            techniques=["T1059", "INVALID", "T1046"],
            created_by="instructor"
        )
        
        assert len(mapping.techniques) == 2
        assert "INVALID" not in mapping.techniques
    
    def test_get_attack_mapping(self, integrations):
        """Test retrieving an ATT&CK mapping."""
        mapping = integrations.create_attack_mapping(
            scenario_id="scenario-123",
            scenario_name="Test",
            techniques=["T1059"],
            created_by="admin"
        )
        
        retrieved = integrations.get_attack_mapping(mapping.mapping_id)
        assert retrieved is not None
        assert retrieved.scenario_id == "scenario-123"
    
    def test_get_mapping_for_scenario(self, integrations):
        """Test getting mapping by scenario ID."""
        integrations.create_attack_mapping(
            scenario_id="scenario-456",
            scenario_name="Test Scenario",
            techniques=["T1059", "T1046"],
            created_by="admin"
        )
        
        mapping = integrations.get_mapping_for_scenario("scenario-456")
        assert mapping is not None
        assert mapping.scenario_name == "Test Scenario"
    
    def test_list_attack_mappings(self, integrations):
        """Test listing ATT&CK mappings."""
        integrations.create_attack_mapping(
            "s1", "Scenario 1", ["T1059"], "admin"
        )
        integrations.create_attack_mapping(
            "s2", "Scenario 2", ["T1046"], "instructor"
        )
        
        all_mappings = integrations.list_attack_mappings()
        assert len(all_mappings) == 2
        
        admin_mappings = integrations.list_attack_mappings(created_by="admin")
        assert len(admin_mappings) == 1
    
    def test_update_attack_mapping(self, integrations):
        """Test updating an ATT&CK mapping."""
        mapping = integrations.create_attack_mapping(
            "s1", "Scenario", ["T1059"], "admin"
        )
        
        updated = integrations.update_attack_mapping(
            mapping.mapping_id,
            techniques=["T1059", "T1046", "T1021"],
            notes="Updated mapping"
        )
        
        assert len(updated.techniques) == 3
        assert updated.notes == "Updated mapping"
    
    def test_delete_attack_mapping(self, integrations):
        """Test deleting an ATT&CK mapping."""
        mapping = integrations.create_attack_mapping(
            "s1", "Scenario", ["T1059"], "admin"
        )
        
        assert integrations.delete_attack_mapping(mapping.mapping_id) is True
        assert integrations.get_attack_mapping(mapping.mapping_id) is None
    
    def test_get_mapping_details(self, integrations):
        """Test getting detailed mapping with technique info."""
        mapping = integrations.create_attack_mapping(
            "s1", "Attack Scenario",
            ["T1059", "T1046", "T1021", "T1486"],
            "admin"
        )
        
        details = integrations.get_mapping_details(mapping.mapping_id)
        
        assert details is not None
        assert len(details["techniques"]) == 4
        assert len(details["tactics_covered"]) > 1
        assert "coverage_percentage" in details


class TestLogForwarding:
    """Tests for log forwarding."""
    
    @pytest.fixture
    def integrations(self):
        return ExternalIntegrations()
    
    def test_create_forwarding_rule(self, integrations):
        """Test creating a forwarding rule."""
        integration = integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk", "admin"
        )
        
        rule = integrations.create_forwarding_rule(
            name="Forward all errors",
            integration_id=integration.integration_id,
            log_levels=[LogLevel.ERROR, LogLevel.CRITICAL],
            source_filter="^cew_.*"
        )
        
        assert rule.rule_id is not None
        assert rule.name == "Forward all errors"
        assert len(rule.log_levels) == 2
    
    def test_list_forwarding_rules(self, integrations):
        """Test listing forwarding rules."""
        integration = integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk", "admin"
        )
        
        rule1 = integrations.create_forwarding_rule(
            "Rule 1", integration.integration_id
        )
        rule2 = integrations.create_forwarding_rule(
            "Rule 2", integration.integration_id
        )
        # Disable rule2
        integrations.update_forwarding_rule(rule2.rule_id, enabled=False)
        
        all_rules = integrations.list_forwarding_rules()
        assert len(all_rules) == 2
        
        enabled_rules = integrations.list_forwarding_rules(enabled_only=True)
        assert len(enabled_rules) == 1
    
    def test_update_forwarding_rule(self, integrations):
        """Test updating a forwarding rule."""
        integration = integrations.create_integration(
            IntegrationType.ELASTICSEARCH, "ELK", "admin"
        )
        
        rule = integrations.create_forwarding_rule(
            "Test Rule", integration.integration_id
        )
        
        updated = integrations.update_forwarding_rule(
            rule.rule_id,
            enabled=False,
            log_levels=[LogLevel.CRITICAL],
            batch_size=50
        )
        
        assert updated.enabled is False
        assert len(updated.log_levels) == 1
        assert updated.batch_size == 50
    
    def test_delete_forwarding_rule(self, integrations):
        """Test deleting a forwarding rule."""
        integration = integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk", "admin"
        )
        
        rule = integrations.create_forwarding_rule(
            "Test", integration.integration_id
        )
        
        assert integrations.delete_forwarding_rule(rule.rule_id) is True
        assert integrations.get_forwarding_rule(rule.rule_id) is None
    
    def test_forward_log(self, integrations):
        """Test forwarding a log entry."""
        integration = integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk", "admin"
        )
        
        integrations.create_forwarding_rule(
            "Forward errors",
            integration.integration_id,
            log_levels=[LogLevel.ERROR, LogLevel.WARNING]
        )
        
        # Forward matching log
        count = integrations.forward_log(
            level=LogLevel.ERROR,
            source="cew_auth",
            message="Authentication failed",
            metadata={"user": "test"}
        )
        
        assert count == 1
        
        # Forward non-matching log (different level)
        count = integrations.forward_log(
            level=LogLevel.DEBUG,
            source="cew_auth",
            message="Debug message"
        )
        
        assert count == 0
    
    def test_forward_log_with_source_filter(self, integrations):
        """Test log forwarding with source filter."""
        integration = integrations.create_integration(
            IntegrationType.ELASTICSEARCH, "ELK", "admin"
        )
        
        integrations.create_forwarding_rule(
            "Forward auth logs",
            integration.integration_id,
            log_levels=[LogLevel.INFO, LogLevel.ERROR],
            source_filter="^cew_auth.*"
        )
        
        # Matching source
        count = integrations.forward_log(
            LogLevel.INFO, "cew_auth_service", "Login attempt"
        )
        assert count == 1
        
        # Non-matching source
        count = integrations.forward_log(
            LogLevel.INFO, "cew_other_service", "Some message"
        )
        assert count == 0
    
    def test_get_log_buffer(self, integrations):
        """Test getting the log buffer."""
        integration = integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk", "admin"
        )
        
        integrations.create_forwarding_rule(
            "Forward all",
            integration.integration_id,
            log_levels=[LogLevel.INFO]
        )
        
        integrations.forward_log(LogLevel.INFO, "source1", "Message 1")
        integrations.forward_log(LogLevel.INFO, "source2", "Message 2")
        
        buffer = integrations.get_log_buffer()
        assert len(buffer) == 2
    
    def test_clear_log_buffer(self, integrations):
        """Test clearing the log buffer."""
        integration = integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk", "admin"
        )
        
        integrations.create_forwarding_rule(
            "Forward all",
            integration.integration_id
        )
        
        integrations.forward_log(LogLevel.INFO, "test", "Message")
        assert len(integrations.get_log_buffer()) > 0
        
        integrations.clear_log_buffer()
        assert len(integrations.get_log_buffer()) == 0


class TestNetworkEmulation:
    """Tests for network emulation configuration."""
    
    @pytest.fixture
    def integrations(self):
        return ExternalIntegrations()
    
    def test_create_emulation_config(self, integrations):
        """Test creating an emulation config."""
        config = integrations.create_emulation_config(
            name="Test Network",
            topology_id="topology-123",
            emulator_type="mininet",
            controller="ryu",
            link_params={"bw": 100, "delay": "2ms"}
        )
        
        assert config.config_id is not None
        assert config.topology_id == "topology-123"
        assert config.emulator_type == "mininet"
        assert config.link_params["bw"] == 100
    
    def test_list_emulation_configs(self, integrations):
        """Test listing emulation configs."""
        integrations.create_emulation_config(
            "Net1", "topo1", "mininet"
        )
        integrations.create_emulation_config(
            "Net2", "topo2", "core"
        )
        integrations.create_emulation_config(
            "Net3", "topo1", "mininet"
        )
        
        all_configs = integrations.list_emulation_configs()
        assert len(all_configs) == 3
        
        # Filter by topology
        topo1_configs = integrations.list_emulation_configs(topology_id="topo1")
        assert len(topo1_configs) == 2
        
        # Filter by emulator type
        mininet_configs = integrations.list_emulation_configs(emulator_type="mininet")
        assert len(mininet_configs) == 2
    
    def test_delete_emulation_config(self, integrations):
        """Test deleting an emulation config."""
        config = integrations.create_emulation_config(
            "Test", "topo1", "mininet"
        )
        
        assert integrations.delete_emulation_config(config.config_id) is True
        assert integrations.get_emulation_config(config.config_id) is None
    
    def test_generate_mininet_script(self, integrations):
        """Test generating a Mininet script."""
        config = integrations.create_emulation_config(
            "Test Network",
            "topology-123",
            "mininet",
            controller="ryu",
            link_params={"bw": 100}
        )
        
        script = integrations.generate_mininet_script(config.config_id)
        
        assert script is not None
        assert "#!/usr/bin/env python" in script
        assert "Mininet" in script
        assert "topology-123" in script
    
    def test_generate_script_wrong_type(self, integrations):
        """Test that script generation fails for non-mininet configs."""
        config = integrations.create_emulation_config(
            "CORE Network",
            "topology-123",
            "core"
        )
        
        script = integrations.generate_mininet_script(config.config_id)
        assert script is None


class TestStatistics:
    """Tests for integration statistics."""
    
    @pytest.fixture
    def integrations(self):
        return ExternalIntegrations()
    
    def test_get_statistics(self, integrations):
        """Test getting integration statistics."""
        # Create some integrations
        splunk = integrations.create_integration(
            IntegrationType.SPLUNK, "Splunk", "admin"
        )
        integrations.test_integration(splunk.integration_id)  # Mark as connected
        
        integrations.create_integration(
            IntegrationType.ELASTICSEARCH, "ELK", "admin"
        )
        
        # Create a mapping
        integrations.create_attack_mapping(
            "s1", "Scenario", ["T1059"], "admin"
        )
        
        # Create a forwarding rule
        integrations.create_forwarding_rule(
            "Rule", splunk.integration_id
        )
        
        # Create emulation config
        integrations.create_emulation_config(
            "Net", "topo1", "mininet"
        )
        
        stats = integrations.get_statistics()
        
        assert stats["total_integrations"] == 2
        assert stats["connected_integrations"] == 1
        assert stats["total_techniques"] > 0
        assert stats["total_mappings"] == 1
        assert stats["total_forwarding_rules"] == 1
        assert stats["active_forwarding_rules"] == 1
        assert stats["total_emulation_configs"] == 1


class TestGlobalInstance:
    """Tests for the global external integrations instance."""
    
    def test_global_instance_exists(self):
        """Test that global instance is available."""
        assert external_integrations is not None
        assert isinstance(external_integrations, ExternalIntegrations)
    
    def test_global_instance_has_techniques(self):
        """Test that global instance has built-in techniques."""
        techniques = external_integrations.list_techniques()
        assert len(techniques) > 0


class TestDataclassSerialization:
    """Tests for dataclass serialization."""
    
    def test_integration_config_to_dict(self):
        """Test IntegrationConfig serialization."""
        from external_integrations import IntegrationConfig
        
        config = IntegrationConfig(
            integration_id="test-123",
            integration_type=IntegrationType.SPLUNK,
            name="Test Splunk",
            config={"host": "localhost", "password": "secret"},
            created_by="admin"
        )
        
        d = config.to_dict()
        assert d["integration_id"] == "test-123"
        assert d["integration_type"] == "splunk"
        # Password should be filtered
        assert "password" not in d["config"]
    
    def test_mitre_attack_technique_to_dict(self):
        """Test MitreAttackTechnique serialization."""
        from external_integrations import MitreAttackTechnique
        
        technique = MitreAttackTechnique(
            technique_id="T1059",
            name="Test Technique",
            tactic="Execution",
            description="Test description",
            platforms=["Windows", "Linux"]
        )
        
        d = technique.to_dict()
        assert d["technique_id"] == "T1059"
        assert d["tactic"] == "Execution"
        assert "Windows" in d["platforms"]
    
    def test_log_forwarding_rule_to_dict(self):
        """Test LogForwardingRule serialization."""
        from external_integrations import LogForwardingRule
        
        rule = LogForwardingRule(
            rule_id="rule-123",
            name="Test Rule",
            integration_id="int-456",
            log_levels=[LogLevel.ERROR, LogLevel.CRITICAL]
        )
        
        d = rule.to_dict()
        assert d["rule_id"] == "rule-123"
        assert "error" in d["log_levels"]
        assert "critical" in d["log_levels"]
