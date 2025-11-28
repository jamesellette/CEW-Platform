"""
Enhanced Network Topology Editor module for CEW Training Platform.
Provides visual topology building, validation, and multi-format export/import.
"""
import logging
import json
import yaml
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    """Types of network nodes."""
    ROUTER = "router"
    SWITCH = "switch"
    FIREWALL = "firewall"
    SERVER = "server"
    WORKSTATION = "workstation"
    ATTACKER = "attacker"
    TARGET = "target"
    IDS = "ids"
    GATEWAY = "gateway"
    CUSTOM = "custom"


class ConnectionType(str, Enum):
    """Types of network connections."""
    ETHERNET = "ethernet"
    FIBER = "fiber"
    WIRELESS = "wireless"
    VPN = "vpn"
    SERIAL = "serial"


class ValidationSeverity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class Position:
    """2D position for visual representation."""
    x: float
    y: float

    def to_dict(self) -> dict:
        return {"x": self.x, "y": self.y}


@dataclass
class NetworkNode:
    """Represents a node in the network topology."""
    node_id: str
    name: str
    node_type: NodeType
    position: Position
    image: str = "alpine:latest"
    ip_addresses: list[str] = field(default_factory=list)
    properties: dict = field(default_factory=dict)
    ports: list[str] = field(default_factory=list)
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "node_id": self.node_id,
            "name": self.name,
            "node_type": self.node_type.value,
            "position": self.position.to_dict(),
            "image": self.image,
            "ip_addresses": self.ip_addresses,
            "properties": self.properties,
            "ports": self.ports,
            "labels": self.labels
        }


@dataclass
class NetworkConnection:
    """Represents a connection between nodes."""
    connection_id: str
    source_node_id: str
    target_node_id: str
    source_port: Optional[str] = None
    target_port: Optional[str] = None
    connection_type: ConnectionType = ConnectionType.ETHERNET
    bandwidth: Optional[str] = None  # e.g., "1Gbps"
    latency: Optional[int] = None  # ms
    properties: dict = field(default_factory=dict)
    labels: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "connection_id": self.connection_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "source_port": self.source_port,
            "target_port": self.target_port,
            "connection_type": self.connection_type.value,
            "bandwidth": self.bandwidth,
            "latency": self.latency,
            "properties": self.properties,
            "labels": self.labels
        }


@dataclass
class NetworkSubnet:
    """Represents a network subnet/segment."""
    subnet_id: str
    name: str
    cidr: str
    vlan_id: Optional[int] = None
    gateway: Optional[str] = None
    dns_servers: list[str] = field(default_factory=list)
    properties: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "subnet_id": self.subnet_id,
            "name": self.name,
            "cidr": self.cidr,
            "vlan_id": self.vlan_id,
            "gateway": self.gateway,
            "dns_servers": self.dns_servers,
            "properties": self.properties
        }


@dataclass
class ValidationIssue:
    """A validation issue found in a topology."""
    issue_id: str
    severity: ValidationSeverity
    message: str
    node_id: Optional[str] = None
    connection_id: Optional[str] = None
    suggestion: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "issue_id": self.issue_id,
            "severity": self.severity.value,
            "message": self.message,
            "node_id": self.node_id,
            "connection_id": self.connection_id,
            "suggestion": self.suggestion
        }


@dataclass
class Topology:
    """Represents a complete network topology."""
    topology_id: str
    name: str
    description: str
    nodes: dict[str, NetworkNode] = field(default_factory=dict)
    connections: dict[str, NetworkConnection] = field(default_factory=dict)
    subnets: dict[str, NetworkSubnet] = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)
    created_by: str = ""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "topology_id": self.topology_id,
            "name": self.name,
            "description": self.description,
            "nodes": [n.to_dict() for n in self.nodes.values()],
            "connections": [c.to_dict() for c in self.connections.values()],
            "subnets": [s.to_dict() for s in self.subnets.values()],
            "node_count": len(self.nodes),
            "connection_count": len(self.connections),
            "subnet_count": len(self.subnets),
            "metadata": self.metadata,
            "created_by": self.created_by,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    def to_scenario_topology(self) -> dict:
        """Convert to scenario topology format for lab deployment."""
        return {
            "nodes": [
                {
                    "id": node.name,
                    "type": node.node_type.value,
                    "image": node.image,
                    "ip_addresses": node.ip_addresses,
                    "ports": node.ports,
                    **node.properties
                }
                for node in self.nodes.values()
            ],
            "networks": [
                {
                    "id": subnet.name,
                    "subnet": subnet.cidr,
                    "gateway": subnet.gateway,
                    "vlan_id": subnet.vlan_id
                }
                for subnet in self.subnets.values()
            ],
            "connections": [
                {
                    "from": conn.source_node_id,
                    "to": conn.target_node_id,
                    "type": conn.connection_type.value
                }
                for conn in self.connections.values()
            ]
        }


class TopologyEditor:
    """
    Enhanced network topology editor with visual building,
    validation, and multi-format export/import capabilities.
    """

    def __init__(self):
        self._topologies: dict[str, Topology] = {}

    # ============ Topology Management ============

    def create_topology(
        self,
        name: str,
        description: str,
        created_by: str,
        metadata: dict = None
    ) -> Topology:
        """Create a new topology."""
        topology_id = str(uuid.uuid4())
        topology = Topology(
            topology_id=topology_id,
            name=name,
            description=description,
            created_by=created_by,
            metadata=metadata or {}
        )
        self._topologies[topology_id] = topology
        logger.info(f"Created topology {topology_id}: {name}")
        return topology

    def get_topology(self, topology_id: str) -> Optional[Topology]:
        """Get a topology by ID."""
        return self._topologies.get(topology_id)

    def update_topology(
        self,
        topology_id: str,
        name: str = None,
        description: str = None,
        metadata: dict = None
    ) -> Optional[Topology]:
        """Update topology metadata."""
        topology = self._topologies.get(topology_id)
        if not topology:
            return None

        if name is not None:
            topology.name = name
        if description is not None:
            topology.description = description
        if metadata is not None:
            topology.metadata = metadata

        topology.updated_at = datetime.now(timezone.utc)
        return topology

    def delete_topology(self, topology_id: str) -> bool:
        """Delete a topology."""
        if topology_id in self._topologies:
            del self._topologies[topology_id]
            logger.info(f"Deleted topology {topology_id}")
            return True
        return False

    def list_topologies(self, created_by: str = None) -> list[Topology]:
        """List topologies with optional filter."""
        topologies = list(self._topologies.values())
        if created_by:
            topologies = [t for t in topologies if t.created_by == created_by]
        return topologies

    def clone_topology(
        self,
        topology_id: str,
        new_name: str,
        created_by: str
    ) -> Optional[Topology]:
        """Clone an existing topology."""
        original = self._topologies.get(topology_id)
        if not original:
            return None

        new_id = str(uuid.uuid4())
        clone = Topology(
            topology_id=new_id,
            name=new_name,
            description=f"Clone of {original.name}",
            created_by=created_by,
            metadata=original.metadata.copy()
        )

        # Clone nodes with new IDs
        node_id_map = {}
        for old_id, node in original.nodes.items():
            new_node_id = str(uuid.uuid4())
            node_id_map[old_id] = new_node_id
            clone.nodes[new_node_id] = NetworkNode(
                node_id=new_node_id,
                name=node.name,
                node_type=node.node_type,
                position=Position(x=node.position.x, y=node.position.y),
                image=node.image,
                ip_addresses=node.ip_addresses.copy(),
                properties=node.properties.copy(),
                ports=node.ports.copy(),
                labels=node.labels.copy()
            )

        # Clone connections with updated node references
        for old_id, conn in original.connections.items():
            new_conn_id = str(uuid.uuid4())
            clone.connections[new_conn_id] = NetworkConnection(
                connection_id=new_conn_id,
                source_node_id=node_id_map.get(conn.source_node_id, conn.source_node_id),
                target_node_id=node_id_map.get(conn.target_node_id, conn.target_node_id),
                source_port=conn.source_port,
                target_port=conn.target_port,
                connection_type=conn.connection_type,
                bandwidth=conn.bandwidth,
                latency=conn.latency,
                properties=conn.properties.copy(),
                labels=conn.labels.copy()
            )

        # Clone subnets
        for old_id, subnet in original.subnets.items():
            new_subnet_id = str(uuid.uuid4())
            clone.subnets[new_subnet_id] = NetworkSubnet(
                subnet_id=new_subnet_id,
                name=subnet.name,
                cidr=subnet.cidr,
                vlan_id=subnet.vlan_id,
                gateway=subnet.gateway,
                dns_servers=subnet.dns_servers.copy(),
                properties=subnet.properties.copy()
            )

        self._topologies[new_id] = clone
        logger.info(f"Cloned topology {topology_id} to {new_id}")
        return clone

    # ============ Node Management ============

    def add_node(
        self,
        topology_id: str,
        name: str,
        node_type: NodeType,
        x: float,
        y: float,
        image: str = "alpine:latest",
        ip_addresses: list[str] = None,
        properties: dict = None,
        ports: list[str] = None,
        labels: dict[str, str] = None
    ) -> Optional[NetworkNode]:
        """Add a node to a topology."""
        topology = self._topologies.get(topology_id)
        if not topology:
            return None

        node_id = str(uuid.uuid4())
        node = NetworkNode(
            node_id=node_id,
            name=name,
            node_type=node_type,
            position=Position(x=x, y=y),
            image=image,
            ip_addresses=ip_addresses or [],
            properties=properties or {},
            ports=ports or [],
            labels=labels or {}
        )
        topology.nodes[node_id] = node
        topology.updated_at = datetime.now(timezone.utc)
        return node

    def update_node(
        self,
        topology_id: str,
        node_id: str,
        name: str = None,
        node_type: NodeType = None,
        x: float = None,
        y: float = None,
        image: str = None,
        ip_addresses: list[str] = None,
        properties: dict = None,
        ports: list[str] = None,
        labels: dict[str, str] = None
    ) -> Optional[NetworkNode]:
        """Update a node in a topology."""
        topology = self._topologies.get(topology_id)
        if not topology or node_id not in topology.nodes:
            return None

        node = topology.nodes[node_id]
        if name is not None:
            node.name = name
        if node_type is not None:
            node.node_type = node_type
        if x is not None:
            node.position.x = x
        if y is not None:
            node.position.y = y
        if image is not None:
            node.image = image
        if ip_addresses is not None:
            node.ip_addresses = ip_addresses
        if properties is not None:
            node.properties = properties
        if ports is not None:
            node.ports = ports
        if labels is not None:
            node.labels = labels

        topology.updated_at = datetime.now(timezone.utc)
        return node

    def delete_node(self, topology_id: str, node_id: str) -> bool:
        """Delete a node and its connections from a topology."""
        topology = self._topologies.get(topology_id)
        if not topology or node_id not in topology.nodes:
            return False

        # Remove connections involving this node
        connections_to_remove = [
            conn_id for conn_id, conn in topology.connections.items()
            if conn.source_node_id == node_id or conn.target_node_id == node_id
        ]
        for conn_id in connections_to_remove:
            del topology.connections[conn_id]

        del topology.nodes[node_id]
        topology.updated_at = datetime.now(timezone.utc)
        return True

    def move_node(
        self,
        topology_id: str,
        node_id: str,
        x: float,
        y: float
    ) -> Optional[NetworkNode]:
        """Move a node to a new position."""
        return self.update_node(topology_id, node_id, x=x, y=y)

    # ============ Connection Management ============

    def add_connection(
        self,
        topology_id: str,
        source_node_id: str,
        target_node_id: str,
        connection_type: ConnectionType = ConnectionType.ETHERNET,
        source_port: str = None,
        target_port: str = None,
        bandwidth: str = None,
        latency: int = None,
        properties: dict = None,
        labels: dict[str, str] = None
    ) -> Optional[NetworkConnection]:
        """Add a connection between nodes."""
        topology = self._topologies.get(topology_id)
        if not topology:
            return None

        # Validate nodes exist
        if source_node_id not in topology.nodes:
            raise ValueError(f"Source node {source_node_id} not found")
        if target_node_id not in topology.nodes:
            raise ValueError(f"Target node {target_node_id} not found")

        connection_id = str(uuid.uuid4())
        connection = NetworkConnection(
            connection_id=connection_id,
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            source_port=source_port,
            target_port=target_port,
            connection_type=connection_type,
            bandwidth=bandwidth,
            latency=latency,
            properties=properties or {},
            labels=labels or {}
        )
        topology.connections[connection_id] = connection
        topology.updated_at = datetime.now(timezone.utc)
        return connection

    def update_connection(
        self,
        topology_id: str,
        connection_id: str,
        connection_type: ConnectionType = None,
        source_port: str = None,
        target_port: str = None,
        bandwidth: str = None,
        latency: int = None,
        properties: dict = None,
        labels: dict[str, str] = None
    ) -> Optional[NetworkConnection]:
        """Update a connection."""
        topology = self._topologies.get(topology_id)
        if not topology or connection_id not in topology.connections:
            return None

        conn = topology.connections[connection_id]
        if connection_type is not None:
            conn.connection_type = connection_type
        if source_port is not None:
            conn.source_port = source_port
        if target_port is not None:
            conn.target_port = target_port
        if bandwidth is not None:
            conn.bandwidth = bandwidth
        if latency is not None:
            conn.latency = latency
        if properties is not None:
            conn.properties = properties
        if labels is not None:
            conn.labels = labels

        topology.updated_at = datetime.now(timezone.utc)
        return conn

    def delete_connection(self, topology_id: str, connection_id: str) -> bool:
        """Delete a connection."""
        topology = self._topologies.get(topology_id)
        if not topology or connection_id not in topology.connections:
            return False

        del topology.connections[connection_id]
        topology.updated_at = datetime.now(timezone.utc)
        return True

    # ============ Subnet Management ============

    def add_subnet(
        self,
        topology_id: str,
        name: str,
        cidr: str,
        vlan_id: int = None,
        gateway: str = None,
        dns_servers: list[str] = None,
        properties: dict = None
    ) -> Optional[NetworkSubnet]:
        """Add a subnet to a topology."""
        topology = self._topologies.get(topology_id)
        if not topology:
            return None

        subnet_id = str(uuid.uuid4())
        subnet = NetworkSubnet(
            subnet_id=subnet_id,
            name=name,
            cidr=cidr,
            vlan_id=vlan_id,
            gateway=gateway,
            dns_servers=dns_servers or [],
            properties=properties or {}
        )
        topology.subnets[subnet_id] = subnet
        topology.updated_at = datetime.now(timezone.utc)
        return subnet

    def update_subnet(
        self,
        topology_id: str,
        subnet_id: str,
        name: str = None,
        cidr: str = None,
        vlan_id: int = None,
        gateway: str = None,
        dns_servers: list[str] = None,
        properties: dict = None
    ) -> Optional[NetworkSubnet]:
        """Update a subnet."""
        topology = self._topologies.get(topology_id)
        if not topology or subnet_id not in topology.subnets:
            return None

        subnet = topology.subnets[subnet_id]
        if name is not None:
            subnet.name = name
        if cidr is not None:
            subnet.cidr = cidr
        if vlan_id is not None:
            subnet.vlan_id = vlan_id
        if gateway is not None:
            subnet.gateway = gateway
        if dns_servers is not None:
            subnet.dns_servers = dns_servers
        if properties is not None:
            subnet.properties = properties

        topology.updated_at = datetime.now(timezone.utc)
        return subnet

    def delete_subnet(self, topology_id: str, subnet_id: str) -> bool:
        """Delete a subnet."""
        topology = self._topologies.get(topology_id)
        if not topology or subnet_id not in topology.subnets:
            return False

        del topology.subnets[subnet_id]
        topology.updated_at = datetime.now(timezone.utc)
        return True

    # ============ Validation ============

    def validate_topology(self, topology_id: str) -> list[ValidationIssue]:
        """Validate a topology and return any issues."""
        topology = self._topologies.get(topology_id)
        if not topology:
            return [ValidationIssue(
                issue_id=str(uuid.uuid4()),
                severity=ValidationSeverity.ERROR,
                message="Topology not found"
            )]

        issues = []

        # Check for empty topology
        if not topology.nodes:
            issues.append(ValidationIssue(
                issue_id=str(uuid.uuid4()),
                severity=ValidationSeverity.WARNING,
                message="Topology has no nodes",
                suggestion="Add at least one node to the topology"
            ))

        # Check for isolated nodes (no connections)
        connected_nodes = set()
        for conn in topology.connections.values():
            connected_nodes.add(conn.source_node_id)
            connected_nodes.add(conn.target_node_id)

        for node_id, node in topology.nodes.items():
            if node_id not in connected_nodes and len(topology.nodes) > 1:
                issues.append(ValidationIssue(
                    issue_id=str(uuid.uuid4()),
                    severity=ValidationSeverity.WARNING,
                    message=f"Node '{node.name}' is isolated (no connections)",
                    node_id=node_id,
                    suggestion="Connect this node to the network or remove it"
                ))

        # Check for duplicate node names
        names = [n.name for n in topology.nodes.values()]
        duplicates = [name for name in names if names.count(name) > 1]
        for dup in set(duplicates):
            issues.append(ValidationIssue(
                issue_id=str(uuid.uuid4()),
                severity=ValidationSeverity.ERROR,
                message=f"Duplicate node name: '{dup}'",
                suggestion="Each node should have a unique name"
            ))

        # Validate IP addresses
        ip_pattern = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$'
        )
        for node in topology.nodes.values():
            for ip in node.ip_addresses:
                # Strip CIDR notation if present
                ip_only = ip.split('/')[0]
                if not ip_pattern.match(ip_only):
                    issues.append(ValidationIssue(
                        issue_id=str(uuid.uuid4()),
                        severity=ValidationSeverity.ERROR,
                        message=f"Invalid IP address '{ip}' on node '{node.name}'",
                        node_id=node.node_id,
                        suggestion="Use valid IPv4 address format (e.g., 192.168.1.1)"
                    ))

        # Validate subnet CIDR
        cidr_pattern = re.compile(
            r'^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}'
            r'(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)/(?:[0-9]|[1-2][0-9]|3[0-2])$'
        )
        for subnet in topology.subnets.values():
            if not cidr_pattern.match(subnet.cidr):
                issues.append(ValidationIssue(
                    issue_id=str(uuid.uuid4()),
                    severity=ValidationSeverity.ERROR,
                    message=f"Invalid CIDR notation '{subnet.cidr}' for subnet '{subnet.name}'",
                    suggestion="Use valid CIDR format (e.g., 192.168.1.0/24)"
                ))

        # Check for self-connections
        for conn_id, conn in topology.connections.items():
            if conn.source_node_id == conn.target_node_id:
                issues.append(ValidationIssue(
                    issue_id=str(uuid.uuid4()),
                    severity=ValidationSeverity.WARNING,
                    message="Node connected to itself (loopback)",
                    connection_id=conn_id,
                    suggestion="Remove self-connection unless intentional"
                ))

        return issues

    # ============ Export ============

    def export_json(self, topology_id: str, pretty: bool = True) -> Optional[str]:
        """Export topology to JSON format."""
        topology = self._topologies.get(topology_id)
        if not topology:
            return None

        indent = 2 if pretty else None
        return json.dumps(topology.to_dict(), indent=indent)

    def export_yaml(self, topology_id: str) -> Optional[str]:
        """Export topology to YAML format."""
        topology = self._topologies.get(topology_id)
        if not topology:
            return None

        return yaml.dump(topology.to_dict(), default_flow_style=False, allow_unicode=True)

    def export_graphviz(self, topology_id: str) -> Optional[str]:
        """Export topology to Graphviz DOT format."""
        topology = self._topologies.get(topology_id)
        if not topology:
            return None

        lines = [
            f'digraph "{topology.name}" {{',
            '    rankdir=TB;',
            '    node [shape=box, style=filled];',
            ''
        ]

        # Node type colors
        colors = {
            NodeType.ROUTER: "lightblue",
            NodeType.SWITCH: "lightgreen",
            NodeType.FIREWALL: "orange",
            NodeType.SERVER: "lightyellow",
            NodeType.WORKSTATION: "white",
            NodeType.ATTACKER: "lightcoral",
            NodeType.TARGET: "lightpink",
            NodeType.IDS: "lightcyan",
            NodeType.GATEWAY: "lightgray",
            NodeType.CUSTOM: "white"
        }

        # Add nodes
        for node in topology.nodes.values():
            color = colors.get(node.node_type, "white")
            label = f"{node.name}\\n({node.node_type.value})"
            if node.ip_addresses:
                label += f"\\n{node.ip_addresses[0]}"
            lines.append(f'    "{node.node_id}" [label="{label}", fillcolor="{color}"];')

        lines.append('')

        # Add connections
        for conn in topology.connections.values():
            style = "solid"
            if conn.connection_type == ConnectionType.WIRELESS:
                style = "dashed"
            elif conn.connection_type == ConnectionType.VPN:
                style = "dotted"

            label = conn.connection_type.value
            if conn.bandwidth:
                label += f"\\n{conn.bandwidth}"

            lines.append(
                f'    "{conn.source_node_id}" -> "{conn.target_node_id}" '
                f'[label="{label}", style="{style}", dir=none];'
            )

        lines.append('}')
        return '\n'.join(lines)

    def export_scenario(self, topology_id: str) -> Optional[dict]:
        """Export topology for scenario deployment."""
        topology = self._topologies.get(topology_id)
        if not topology:
            return None
        return topology.to_scenario_topology()

    # ============ Import ============

    def import_json(
        self,
        json_content: str,
        name: str,
        created_by: str
    ) -> Optional[Topology]:
        """Import topology from JSON format."""
        try:
            data = json.loads(json_content)
            return self._import_from_dict(data, name, created_by)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")

    def import_yaml(
        self,
        yaml_content: str,
        name: str,
        created_by: str
    ) -> Optional[Topology]:
        """Import topology from YAML format."""
        try:
            data = yaml.safe_load(yaml_content)
            return self._import_from_dict(data, name, created_by)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")

    def _import_from_dict(
        self,
        data: dict,
        name: str,
        created_by: str
    ) -> Topology:
        """Import topology from dictionary data."""
        topology = self.create_topology(
            name=name,
            description=data.get("description", ""),
            created_by=created_by,
            metadata=data.get("metadata", {})
        )

        # Import nodes
        node_id_map = {}
        for node_data in data.get("nodes", []):
            old_id = node_data.get("node_id", str(uuid.uuid4()))
            node = self.add_node(
                topology_id=topology.topology_id,
                name=node_data.get("name", "Unnamed"),
                node_type=NodeType(node_data.get("node_type", "custom")),
                x=node_data.get("position", {}).get("x", 0),
                y=node_data.get("position", {}).get("y", 0),
                image=node_data.get("image", "alpine:latest"),
                ip_addresses=node_data.get("ip_addresses", []),
                properties=node_data.get("properties", {}),
                ports=node_data.get("ports", []),
                labels=node_data.get("labels", {})
            )
            node_id_map[old_id] = node.node_id

        # Import connections
        for conn_data in data.get("connections", []):
            source_id = node_id_map.get(
                conn_data.get("source_node_id"),
                conn_data.get("source_node_id")
            )
            target_id = node_id_map.get(
                conn_data.get("target_node_id"),
                conn_data.get("target_node_id")
            )
            if source_id in topology.nodes and target_id in topology.nodes:
                self.add_connection(
                    topology_id=topology.topology_id,
                    source_node_id=source_id,
                    target_node_id=target_id,
                    connection_type=ConnectionType(
                        conn_data.get("connection_type", "ethernet")
                    ),
                    source_port=conn_data.get("source_port"),
                    target_port=conn_data.get("target_port"),
                    bandwidth=conn_data.get("bandwidth"),
                    latency=conn_data.get("latency"),
                    properties=conn_data.get("properties", {}),
                    labels=conn_data.get("labels", {})
                )

        # Import subnets
        for subnet_data in data.get("subnets", []):
            self.add_subnet(
                topology_id=topology.topology_id,
                name=subnet_data.get("name", "Unnamed"),
                cidr=subnet_data.get("cidr", "10.0.0.0/24"),
                vlan_id=subnet_data.get("vlan_id"),
                gateway=subnet_data.get("gateway"),
                dns_servers=subnet_data.get("dns_servers", []),
                properties=subnet_data.get("properties", {})
            )

        return topology


# Global topology editor instance
topology_editor = TopologyEditor()
