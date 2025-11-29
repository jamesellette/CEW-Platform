"""
External Tools Integration Module

Provides integration with external cybersecurity and network tools:
- MITRE ATT&CK Framework mapping
- Splunk/ELK log forwarding
- CORE/Mininet network emulation
- GNU Radio SDR integration
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable
import json
import uuid
import re


class IntegrationType(Enum):
    """Types of external integrations."""
    MITRE_ATTACK = "mitre_attack"
    SPLUNK = "splunk"
    ELASTICSEARCH = "elasticsearch"
    MININET = "mininet"
    GNU_RADIO = "gnu_radio"
    CUSTOM = "custom"


class IntegrationStatus(Enum):
    """Integration connection status."""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    ERROR = "error"
    DISABLED = "disabled"


class LogLevel(Enum):
    """Log levels for forwarding."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MitreAttackTechnique:
    """MITRE ATT&CK technique."""
    technique_id: str  # e.g., T1059
    name: str
    tactic: str  # e.g., Execution
    description: str
    platforms: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)
    detection: str = ""
    url: str = ""
    
    def to_dict(self) -> dict:
        return {
            "technique_id": self.technique_id,
            "name": self.name,
            "tactic": self.tactic,
            "description": self.description,
            "platforms": self.platforms,
            "data_sources": self.data_sources,
            "detection": self.detection,
            "url": self.url
        }


@dataclass
class MitreAttackMapping:
    """Mapping of a scenario to MITRE ATT&CK techniques."""
    mapping_id: str
    scenario_id: str
    scenario_name: str
    techniques: List[str]  # List of technique IDs
    created_at: datetime
    created_by: str
    notes: str = ""
    
    def to_dict(self) -> dict:
        return {
            "mapping_id": self.mapping_id,
            "scenario_id": self.scenario_id,
            "scenario_name": self.scenario_name,
            "techniques": self.techniques,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "notes": self.notes
        }


@dataclass
class IntegrationConfig:
    """Configuration for an external integration."""
    integration_id: str
    integration_type: IntegrationType
    name: str
    enabled: bool = True
    config: Dict[str, Any] = field(default_factory=dict)
    status: IntegrationStatus = IntegrationStatus.DISCONNECTED
    last_connected: Optional[datetime] = None
    error_message: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    created_by: str = ""
    
    def to_dict(self) -> dict:
        return {
            "integration_id": self.integration_id,
            "integration_type": self.integration_type.value,
            "name": self.name,
            "enabled": self.enabled,
            "config": {k: v for k, v in self.config.items() if k != "password" and k != "api_key"},
            "status": self.status.value,
            "last_connected": self.last_connected.isoformat() if self.last_connected else None,
            "error_message": self.error_message,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by
        }


@dataclass
class LogForwardingRule:
    """Rule for forwarding logs to external systems."""
    rule_id: str
    name: str
    integration_id: str
    enabled: bool = True
    log_levels: List[LogLevel] = field(default_factory=list)
    source_filter: Optional[str] = None  # Regex pattern
    include_metadata: bool = True
    batch_size: int = 100
    flush_interval_seconds: int = 30
    created_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "integration_id": self.integration_id,
            "enabled": self.enabled,
            "log_levels": [l.value for l in self.log_levels],
            "source_filter": self.source_filter,
            "include_metadata": self.include_metadata,
            "batch_size": self.batch_size,
            "flush_interval_seconds": self.flush_interval_seconds,
            "created_at": self.created_at.isoformat()
        }


@dataclass
class NetworkEmulationConfig:
    """Configuration for network emulation (Mininet/CORE)."""
    config_id: str
    name: str
    topology_id: str
    emulator_type: str  # mininet or core
    controller: str = "default"
    link_params: Dict[str, Any] = field(default_factory=dict)
    host_params: Dict[str, Any] = field(default_factory=dict)
    switch_params: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "config_id": self.config_id,
            "name": self.name,
            "topology_id": self.topology_id,
            "emulator_type": self.emulator_type,
            "controller": self.controller,
            "link_params": self.link_params,
            "host_params": self.host_params,
            "switch_params": self.switch_params
        }


class ExternalIntegrations:
    """
    Manages integrations with external cybersecurity tools.
    
    Features:
    - MITRE ATT&CK framework mapping
    - Log forwarding to Splunk/ELK
    - Network emulation with Mininet/CORE
    - SDR simulation with GNU Radio
    """
    
    # MITRE ATT&CK Tactics
    ATTACK_TACTICS = [
        "Reconnaissance",
        "Resource Development",
        "Initial Access",
        "Execution",
        "Persistence",
        "Privilege Escalation",
        "Defense Evasion",
        "Credential Access",
        "Discovery",
        "Lateral Movement",
        "Collection",
        "Command and Control",
        "Exfiltration",
        "Impact"
    ]
    
    def __init__(self):
        # Integration configurations
        self._integrations: Dict[str, IntegrationConfig] = {}
        
        # MITRE ATT&CK data
        self._techniques: Dict[str, MitreAttackTechnique] = {}
        self._mappings: Dict[str, MitreAttackMapping] = {}
        
        # Log forwarding rules
        self._forwarding_rules: Dict[str, LogForwardingRule] = {}
        self._log_buffer: List[Dict] = []
        
        # Network emulation configs
        self._emulation_configs: Dict[str, NetworkEmulationConfig] = {}
        
        # Initialize built-in MITRE ATT&CK techniques
        self._init_attack_techniques()
    
    def _init_attack_techniques(self):
        """Initialize common MITRE ATT&CK techniques."""
        techniques = [
            MitreAttackTechnique(
                technique_id="T1059",
                name="Command and Scripting Interpreter",
                tactic="Execution",
                description="Adversaries may abuse command and script interpreters to execute commands, scripts, or binaries.",
                platforms=["Windows", "Linux", "macOS"],
                data_sources=["Process", "Command"],
                detection="Monitor command-line arguments and script execution",
                url="https://attack.mitre.org/techniques/T1059/"
            ),
            MitreAttackTechnique(
                technique_id="T1059.001",
                name="PowerShell",
                tactic="Execution",
                description="Adversaries may abuse PowerShell commands and scripts for execution.",
                platforms=["Windows"],
                data_sources=["Process", "Script"],
                detection="Monitor PowerShell execution logs",
                url="https://attack.mitre.org/techniques/T1059/001/"
            ),
            MitreAttackTechnique(
                technique_id="T1059.004",
                name="Unix Shell",
                tactic="Execution",
                description="Adversaries may abuse Unix shell commands for execution.",
                platforms=["Linux", "macOS"],
                data_sources=["Process", "Command"],
                detection="Monitor shell command execution",
                url="https://attack.mitre.org/techniques/T1059/004/"
            ),
            MitreAttackTechnique(
                technique_id="T1078",
                name="Valid Accounts",
                tactic="Persistence",
                description="Adversaries may obtain and abuse credentials of existing accounts.",
                platforms=["Windows", "Linux", "macOS", "Cloud"],
                data_sources=["Authentication", "User Account"],
                detection="Monitor for unusual authentication activity",
                url="https://attack.mitre.org/techniques/T1078/"
            ),
            MitreAttackTechnique(
                technique_id="T1110",
                name="Brute Force",
                tactic="Credential Access",
                description="Adversaries may use brute force techniques to gain access to accounts.",
                platforms=["Windows", "Linux", "macOS", "Cloud"],
                data_sources=["Authentication", "User Account"],
                detection="Monitor for multiple failed authentication attempts",
                url="https://attack.mitre.org/techniques/T1110/"
            ),
            MitreAttackTechnique(
                technique_id="T1046",
                name="Network Service Discovery",
                tactic="Discovery",
                description="Adversaries may scan for open ports and services on networked systems.",
                platforms=["Windows", "Linux", "macOS"],
                data_sources=["Network Traffic", "Process"],
                detection="Monitor for port scanning activity",
                url="https://attack.mitre.org/techniques/T1046/"
            ),
            MitreAttackTechnique(
                technique_id="T1021",
                name="Remote Services",
                tactic="Lateral Movement",
                description="Adversaries may use remote services to access internal systems.",
                platforms=["Windows", "Linux", "macOS"],
                data_sources=["Authentication", "Network Traffic"],
                detection="Monitor for unusual remote service connections",
                url="https://attack.mitre.org/techniques/T1021/"
            ),
            MitreAttackTechnique(
                technique_id="T1021.001",
                name="Remote Desktop Protocol",
                tactic="Lateral Movement",
                description="Adversaries may use RDP to connect to remote systems.",
                platforms=["Windows"],
                data_sources=["Network Traffic", "Process"],
                detection="Monitor RDP connections",
                url="https://attack.mitre.org/techniques/T1021/001/"
            ),
            MitreAttackTechnique(
                technique_id="T1021.004",
                name="SSH",
                tactic="Lateral Movement",
                description="Adversaries may use SSH to connect to remote systems.",
                platforms=["Linux", "macOS"],
                data_sources=["Network Traffic", "Process"],
                detection="Monitor SSH connections",
                url="https://attack.mitre.org/techniques/T1021/004/"
            ),
            MitreAttackTechnique(
                technique_id="T1486",
                name="Data Encrypted for Impact",
                tactic="Impact",
                description="Adversaries may encrypt data to disrupt system availability.",
                platforms=["Windows", "Linux", "macOS"],
                data_sources=["File", "Process"],
                detection="Monitor for mass file encryption",
                url="https://attack.mitre.org/techniques/T1486/"
            ),
            MitreAttackTechnique(
                technique_id="T1071",
                name="Application Layer Protocol",
                tactic="Command and Control",
                description="Adversaries may use application layer protocols for C2.",
                platforms=["Windows", "Linux", "macOS"],
                data_sources=["Network Traffic"],
                detection="Monitor for unusual application protocol traffic",
                url="https://attack.mitre.org/techniques/T1071/"
            ),
            MitreAttackTechnique(
                technique_id="T1041",
                name="Exfiltration Over C2 Channel",
                tactic="Exfiltration",
                description="Adversaries may exfiltrate data over the C2 channel.",
                platforms=["Windows", "Linux", "macOS"],
                data_sources=["Network Traffic"],
                detection="Monitor for large data transfers over C2",
                url="https://attack.mitre.org/techniques/T1041/"
            ),
            MitreAttackTechnique(
                technique_id="T1190",
                name="Exploit Public-Facing Application",
                tactic="Initial Access",
                description="Adversaries may exploit vulnerabilities in public-facing applications.",
                platforms=["Windows", "Linux", "macOS", "Cloud"],
                data_sources=["Application Log", "Network Traffic"],
                detection="Monitor for exploitation attempts",
                url="https://attack.mitre.org/techniques/T1190/"
            ),
            MitreAttackTechnique(
                technique_id="T1566",
                name="Phishing",
                tactic="Initial Access",
                description="Adversaries may send phishing messages to gain access.",
                platforms=["Windows", "Linux", "macOS", "Cloud"],
                data_sources=["Email", "Network Traffic"],
                detection="Monitor for suspicious emails and attachments",
                url="https://attack.mitre.org/techniques/T1566/"
            ),
            MitreAttackTechnique(
                technique_id="T1003",
                name="OS Credential Dumping",
                tactic="Credential Access",
                description="Adversaries may attempt to dump credentials from the OS.",
                platforms=["Windows", "Linux", "macOS"],
                data_sources=["Process", "File"],
                detection="Monitor for credential dumping tools",
                url="https://attack.mitre.org/techniques/T1003/"
            )
        ]
        
        for tech in techniques:
            self._techniques[tech.technique_id] = tech
    
    # ============ Integration Management ============
    
    def create_integration(
        self,
        integration_type: IntegrationType,
        name: str,
        created_by: str,
        config: Optional[Dict] = None,
        enabled: bool = True
    ) -> IntegrationConfig:
        """Create a new external integration."""
        integration_id = str(uuid.uuid4())
        
        integration = IntegrationConfig(
            integration_id=integration_id,
            integration_type=integration_type,
            name=name,
            enabled=enabled,
            config=config or {},
            created_by=created_by
        )
        
        self._integrations[integration_id] = integration
        return integration
    
    def get_integration(self, integration_id: str) -> Optional[IntegrationConfig]:
        """Get an integration by ID."""
        return self._integrations.get(integration_id)
    
    def list_integrations(
        self,
        integration_type: Optional[IntegrationType] = None,
        enabled_only: bool = False
    ) -> List[IntegrationConfig]:
        """List integrations."""
        integrations = list(self._integrations.values())
        
        if integration_type:
            integrations = [i for i in integrations if i.integration_type == integration_type]
        
        if enabled_only:
            integrations = [i for i in integrations if i.enabled]
        
        return integrations
    
    def update_integration(
        self,
        integration_id: str,
        name: Optional[str] = None,
        enabled: Optional[bool] = None,
        config: Optional[Dict] = None
    ) -> Optional[IntegrationConfig]:
        """Update an integration."""
        integration = self._integrations.get(integration_id)
        if not integration:
            return None
        
        if name:
            integration.name = name
        if enabled is not None:
            integration.enabled = enabled
        if config:
            integration.config.update(config)
        
        return integration
    
    def delete_integration(self, integration_id: str) -> bool:
        """Delete an integration."""
        if integration_id in self._integrations:
            del self._integrations[integration_id]
            return True
        return False
    
    def test_integration(self, integration_id: str) -> dict:
        """Test integration connectivity."""
        integration = self._integrations.get(integration_id)
        if not integration:
            return {"success": False, "error": "Integration not found"}
        
        # In a real implementation, this would actually test connectivity
        # For the prototype, we simulate a successful connection
        integration.status = IntegrationStatus.CONNECTED
        integration.last_connected = datetime.utcnow()
        integration.error_message = None
        
        return {
            "success": True,
            "integration_id": integration_id,
            "status": integration.status.value,
            "tested_at": datetime.utcnow().isoformat()
        }
    
    # ============ MITRE ATT&CK Integration ============
    
    def get_technique(self, technique_id: str) -> Optional[MitreAttackTechnique]:
        """Get a MITRE ATT&CK technique by ID."""
        return self._techniques.get(technique_id)
    
    def list_techniques(
        self,
        tactic: Optional[str] = None,
        platform: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[MitreAttackTechnique]:
        """List MITRE ATT&CK techniques."""
        techniques = list(self._techniques.values())
        
        if tactic:
            techniques = [t for t in techniques if t.tactic == tactic]
        
        if platform:
            techniques = [t for t in techniques if platform in t.platforms]
        
        if search:
            search_lower = search.lower()
            techniques = [
                t for t in techniques
                if search_lower in t.name.lower() or
                   search_lower in t.description.lower() or
                   search_lower in t.technique_id.lower()
            ]
        
        return techniques
    
    def get_tactics(self) -> List[str]:
        """Get list of MITRE ATT&CK tactics."""
        return self.ATTACK_TACTICS.copy()
    
    def create_attack_mapping(
        self,
        scenario_id: str,
        scenario_name: str,
        techniques: List[str],
        created_by: str,
        notes: str = ""
    ) -> MitreAttackMapping:
        """Create a MITRE ATT&CK mapping for a scenario."""
        mapping_id = str(uuid.uuid4())
        
        # Validate technique IDs
        valid_techniques = [t for t in techniques if t in self._techniques]
        
        mapping = MitreAttackMapping(
            mapping_id=mapping_id,
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            techniques=valid_techniques,
            created_at=datetime.utcnow(),
            created_by=created_by,
            notes=notes
        )
        
        self._mappings[mapping_id] = mapping
        return mapping
    
    def get_attack_mapping(self, mapping_id: str) -> Optional[MitreAttackMapping]:
        """Get an ATT&CK mapping by ID."""
        return self._mappings.get(mapping_id)
    
    def get_mapping_for_scenario(self, scenario_id: str) -> Optional[MitreAttackMapping]:
        """Get ATT&CK mapping for a scenario."""
        for mapping in self._mappings.values():
            if mapping.scenario_id == scenario_id:
                return mapping
        return None
    
    def list_attack_mappings(
        self,
        created_by: Optional[str] = None
    ) -> List[MitreAttackMapping]:
        """List ATT&CK mappings."""
        mappings = list(self._mappings.values())
        
        if created_by:
            mappings = [m for m in mappings if m.created_by == created_by]
        
        return mappings
    
    def update_attack_mapping(
        self,
        mapping_id: str,
        techniques: Optional[List[str]] = None,
        notes: Optional[str] = None
    ) -> Optional[MitreAttackMapping]:
        """Update an ATT&CK mapping."""
        mapping = self._mappings.get(mapping_id)
        if not mapping:
            return None
        
        if techniques is not None:
            mapping.techniques = [t for t in techniques if t in self._techniques]
        if notes is not None:
            mapping.notes = notes
        
        return mapping
    
    def delete_attack_mapping(self, mapping_id: str) -> bool:
        """Delete an ATT&CK mapping."""
        if mapping_id in self._mappings:
            del self._mappings[mapping_id]
            return True
        return False
    
    def get_mapping_details(self, mapping_id: str) -> Optional[dict]:
        """Get detailed mapping with full technique info."""
        mapping = self._mappings.get(mapping_id)
        if not mapping:
            return None
        
        technique_details = []
        tactics_covered = set()
        
        for tech_id in mapping.techniques:
            tech = self._techniques.get(tech_id)
            if tech:
                technique_details.append(tech.to_dict())
                tactics_covered.add(tech.tactic)
        
        return {
            "mapping": mapping.to_dict(),
            "techniques": technique_details,
            "tactics_covered": list(tactics_covered),
            "coverage_percentage": round(
                len(tactics_covered) / len(self.ATTACK_TACTICS) * 100, 1
            )
        }
    
    # ============ Log Forwarding (Splunk/ELK) ============
    
    def create_forwarding_rule(
        self,
        name: str,
        integration_id: str,
        log_levels: Optional[List[LogLevel]] = None,
        source_filter: Optional[str] = None,
        batch_size: int = 100,
        flush_interval: int = 30
    ) -> LogForwardingRule:
        """Create a log forwarding rule."""
        rule_id = str(uuid.uuid4())
        
        rule = LogForwardingRule(
            rule_id=rule_id,
            name=name,
            integration_id=integration_id,
            log_levels=log_levels or [LogLevel.INFO, LogLevel.WARNING, LogLevel.ERROR],
            source_filter=source_filter,
            batch_size=batch_size,
            flush_interval_seconds=flush_interval
        )
        
        self._forwarding_rules[rule_id] = rule
        return rule
    
    def get_forwarding_rule(self, rule_id: str) -> Optional[LogForwardingRule]:
        """Get a forwarding rule by ID."""
        return self._forwarding_rules.get(rule_id)
    
    def list_forwarding_rules(
        self,
        integration_id: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[LogForwardingRule]:
        """List forwarding rules."""
        rules = list(self._forwarding_rules.values())
        
        if integration_id:
            rules = [r for r in rules if r.integration_id == integration_id]
        
        if enabled_only:
            rules = [r for r in rules if r.enabled]
        
        return rules
    
    def update_forwarding_rule(
        self,
        rule_id: str,
        enabled: Optional[bool] = None,
        log_levels: Optional[List[LogLevel]] = None,
        source_filter: Optional[str] = None,
        batch_size: Optional[int] = None
    ) -> Optional[LogForwardingRule]:
        """Update a forwarding rule."""
        rule = self._forwarding_rules.get(rule_id)
        if not rule:
            return None
        
        if enabled is not None:
            rule.enabled = enabled
        if log_levels is not None:
            rule.log_levels = log_levels
        if source_filter is not None:
            rule.source_filter = source_filter
        if batch_size is not None:
            rule.batch_size = batch_size
        
        return rule
    
    def delete_forwarding_rule(self, rule_id: str) -> bool:
        """Delete a forwarding rule."""
        if rule_id in self._forwarding_rules:
            del self._forwarding_rules[rule_id]
            return True
        return False
    
    def forward_log(
        self,
        level: LogLevel,
        source: str,
        message: str,
        metadata: Optional[Dict] = None
    ) -> int:
        """Forward a log entry to configured integrations."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level.value,
            "source": source,
            "message": message,
            "metadata": metadata or {}
        }
        
        # Check matching rules
        forwarded_count = 0
        for rule in self._forwarding_rules.values():
            if not rule.enabled:
                continue
            
            if level not in rule.log_levels:
                continue
            
            if rule.source_filter:
                if not re.match(rule.source_filter, source):
                    continue
            
            # Add to buffer (in real implementation, would forward to integration)
            self._log_buffer.append({
                "rule_id": rule.rule_id,
                "entry": log_entry
            })
            forwarded_count += 1
        
        return forwarded_count
    
    def get_log_buffer(self, limit: int = 100) -> List[Dict]:
        """Get buffered logs (for testing/debugging)."""
        return self._log_buffer[-limit:]
    
    def clear_log_buffer(self):
        """Clear the log buffer."""
        self._log_buffer.clear()
    
    # ============ Network Emulation (Mininet/CORE) ============
    
    def create_emulation_config(
        self,
        name: str,
        topology_id: str,
        emulator_type: str,
        controller: str = "default",
        link_params: Optional[Dict] = None,
        host_params: Optional[Dict] = None,
        switch_params: Optional[Dict] = None
    ) -> NetworkEmulationConfig:
        """Create a network emulation configuration."""
        config_id = str(uuid.uuid4())
        
        config = NetworkEmulationConfig(
            config_id=config_id,
            name=name,
            topology_id=topology_id,
            emulator_type=emulator_type,
            controller=controller,
            link_params=link_params or {"bw": 10, "delay": "5ms"},
            host_params=host_params or {},
            switch_params=switch_params or {"stp": True}
        )
        
        self._emulation_configs[config_id] = config
        return config
    
    def get_emulation_config(self, config_id: str) -> Optional[NetworkEmulationConfig]:
        """Get an emulation config by ID."""
        return self._emulation_configs.get(config_id)
    
    def list_emulation_configs(
        self,
        topology_id: Optional[str] = None,
        emulator_type: Optional[str] = None
    ) -> List[NetworkEmulationConfig]:
        """List emulation configurations."""
        configs = list(self._emulation_configs.values())
        
        if topology_id:
            configs = [c for c in configs if c.topology_id == topology_id]
        
        if emulator_type:
            configs = [c for c in configs if c.emulator_type == emulator_type]
        
        return configs
    
    def delete_emulation_config(self, config_id: str) -> bool:
        """Delete an emulation config."""
        if config_id in self._emulation_configs:
            del self._emulation_configs[config_id]
            return True
        return False
    
    def generate_mininet_script(self, config_id: str) -> Optional[str]:
        """Generate a Mininet Python script from config."""
        config = self._emulation_configs.get(config_id)
        if not config or config.emulator_type != "mininet":
            return None
        
        script = f'''#!/usr/bin/env python
"""
Mininet network emulation script
Generated for topology: {config.topology_id}
"""

from mininet.net import Mininet
from mininet.node import Controller, OVSSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel, info
from mininet.link import TCLink

def create_network():
    """Create the network topology."""
    net = Mininet(controller=Controller, switch=OVSSwitch, link=TCLink)
    
    info('*** Adding controller\\n')
    net.addController('c0')
    
    # Link parameters
    link_params = {config.link_params}
    
    # TODO: Add hosts and switches from topology
    # This would be populated from the actual topology data
    
    info('*** Starting network\\n')
    net.start()
    
    info('*** Running CLI\\n')
    CLI(net)
    
    info('*** Stopping network\\n')
    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    create_network()
'''
        return script
    
    def get_statistics(self) -> dict:
        """Get integration statistics."""
        integrations_by_type = {}
        for integration in self._integrations.values():
            t = integration.integration_type.value
            if t not in integrations_by_type:
                integrations_by_type[t] = 0
            integrations_by_type[t] += 1
        
        connected_count = len([
            i for i in self._integrations.values()
            if i.status == IntegrationStatus.CONNECTED
        ])
        
        return {
            "total_integrations": len(self._integrations),
            "connected_integrations": connected_count,
            "integrations_by_type": integrations_by_type,
            "total_techniques": len(self._techniques),
            "total_mappings": len(self._mappings),
            "total_forwarding_rules": len(self._forwarding_rules),
            "active_forwarding_rules": len([
                r for r in self._forwarding_rules.values() if r.enabled
            ]),
            "total_emulation_configs": len(self._emulation_configs),
            "log_buffer_size": len(self._log_buffer)
        }


# Global external integrations instance
external_integrations = ExternalIntegrations()
