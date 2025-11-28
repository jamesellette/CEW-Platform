"""
Orchestrator module for CEW Training Platform.
Manages the lifecycle of isolated lab environments using Docker containers.

SAFETY NOTICE: This module is designed for air-gapped training environments only.
All containers are created with network isolation enabled by default.
External network access and real RF transmission are blocked.
"""
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional
import uuid

logger = logging.getLogger(__name__)


class LabStatus(str, Enum):
    """Status of a lab session."""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


@dataclass
class ContainerInfo:
    """Information about a running container."""
    container_id: str
    node_id: str
    hostname: str
    image: str
    ip_address: Optional[str] = None
    status: str = "created"


@dataclass
class NetworkInfo:
    """Information about a created network."""
    network_id: str
    name: str
    subnet: str
    isolated: bool = True


@dataclass
class LabEnvironment:
    """Represents an active lab environment."""
    lab_id: str
    scenario_id: str
    scenario_name: str
    activated_by: str
    status: LabStatus = LabStatus.PENDING
    containers: list[ContainerInfo] = field(default_factory=list)
    networks: list[NetworkInfo] = field(default_factory=list)
    started_at: Optional[datetime] = None
    error_message: Optional[str] = None


class Orchestrator:
    """
    Orchestrates the creation and management of isolated lab environments.

    In the current prototype, this is a simulation layer that tracks lab state
    without actually creating Docker containers. In production, this would
    interface with the Docker API to create real isolated environments.
    """

    def __init__(self):
        self._labs: dict[str, LabEnvironment] = {}
        self._lock = asyncio.Lock()
        self._docker_available = self._check_docker()

    def _check_docker(self) -> bool:
        """Check if Docker is available."""
        # In production, this would check for Docker daemon
        # For now, we operate in simulation mode
        return False

    async def create_lab(
        self,
        scenario_id: str,
        scenario_name: str,
        topology: dict,
        constraints: dict,
        activated_by: str
    ) -> LabEnvironment:
        """
        Create a new lab environment for a scenario.

        Args:
            scenario_id: Unique identifier of the scenario
            scenario_name: Human-readable name of the scenario
            topology: Topology definition with nodes and networks
            constraints: Safety constraints for the lab
            activated_by: Username of the user activating the lab

        Returns:
            LabEnvironment object representing the created lab

        Raises:
            ValueError: If constraints are violated or topology is invalid
        """
        # Validate safety constraints
        self._validate_constraints(constraints)

        lab_id = str(uuid.uuid4())

        async with self._lock:
            # Check if scenario is already active
            for lab in self._labs.values():
                if lab.scenario_id == scenario_id and lab.status == LabStatus.RUNNING:
                    raise ValueError(
                        f"Scenario {scenario_id} already has an active lab session"
                    )

            # Create lab environment
            lab = LabEnvironment(
                lab_id=lab_id,
                scenario_id=scenario_id,
                scenario_name=scenario_name,
                activated_by=activated_by,
                status=LabStatus.STARTING
            )
            self._labs[lab_id] = lab

        try:
            # Create networks first
            networks = topology.get("networks", [])
            for net_def in networks:
                network = await self._create_network(net_def)
                lab.networks.append(network)

            # Create containers
            nodes = topology.get("nodes", [])
            for node_def in nodes:
                container = await self._create_container(node_def, lab.networks)
                lab.containers.append(container)

            # Update status
            lab.status = LabStatus.RUNNING
            lab.started_at = datetime.now(timezone.utc)

            logger.info(
                f"Lab {lab_id} created for scenario '{scenario_name}' "
                f"with {len(lab.containers)} containers and {len(lab.networks)} networks"
            )

            return lab

        except Exception as e:
            lab.status = LabStatus.FAILED
            lab.error_message = str(e)
            logger.error(f"Failed to create lab {lab_id}: {e}")
            raise

    async def _create_network(self, net_def: dict) -> NetworkInfo:
        """Create an isolated network."""
        network_id = f"cew-net-{uuid.uuid4().hex[:12]}"
        name = net_def.get("name", "unnamed-network")
        subnet = net_def.get("subnet", "10.0.0.0/24")
        isolated = net_def.get("isolated", True)

        if not isolated:
            raise ValueError(
                f"Network '{name}' must be isolated for safety. "
                "Set 'isolated: true' in network definition."
            )

        if self._docker_available:
            # In production: Create actual Docker network
            # docker_client.networks.create(
            #     name=network_id,
            #     driver="bridge",
            #     internal=True,  # No external access
            #     ipam=IPAMConfig(pool_configs=[IPAMPool(subnet=subnet)])
            # )
            pass

        logger.debug(f"Created network {name} ({network_id}) with subnet {subnet}")
        return NetworkInfo(
            network_id=network_id,
            name=name,
            subnet=subnet,
            isolated=isolated
        )

    async def _create_container(
        self,
        node_def: dict,
        networks: list[NetworkInfo]
    ) -> ContainerInfo:
        """Create a container for a node."""
        container_id = f"cew-{uuid.uuid4().hex[:12]}"
        node_id = node_def.get("id", str(uuid.uuid4()))
        hostname = node_def.get("hostname", f"node-{node_id}")
        image = node_def.get("image", "ubuntu:22.04")
        ip_address = node_def.get("ip")

        if self._docker_available:
            # In production: Create actual Docker container
            # container = docker_client.containers.create(
            #     image=image,
            #     hostname=hostname,
            #     name=container_id,
            #     network_mode="none",  # Will attach to isolated networks
            #     cap_drop=["ALL"],  # Drop all capabilities for security
            #     read_only=True,  # Read-only filesystem
            #     mem_limit="512m",
            #     cpu_quota=50000,  # Limit CPU
            # )
            pass

        logger.debug(f"Created container {hostname} ({container_id}) from {image}")
        return ContainerInfo(
            container_id=container_id,
            node_id=node_id,
            hostname=hostname,
            image=image,
            ip_address=ip_address,
            status="running" if self._docker_available else "simulated"
        )

    def _validate_constraints(self, constraints: dict) -> None:
        """Validate safety constraints."""
        if constraints.get("allow_external_network", False):
            raise ValueError(
                "External network access is not allowed. "
                "Set 'allow_external_network: false' in constraints."
            )

        if constraints.get("allow_real_rf", False):
            raise ValueError(
                "Real RF transmission is not allowed in prototype. "
                "Set 'allow_real_rf: false' in constraints."
            )

    async def stop_lab(self, lab_id: str) -> LabEnvironment:
        """
        Stop and clean up a lab environment.

        Args:
            lab_id: Unique identifier of the lab to stop

        Returns:
            Updated LabEnvironment object

        Raises:
            ValueError: If lab is not found
        """
        async with self._lock:
            lab = self._labs.get(lab_id)
            if not lab:
                raise ValueError(f"Lab {lab_id} not found")

            if lab.status not in [LabStatus.RUNNING, LabStatus.STARTING]:
                raise ValueError(f"Lab {lab_id} is not running (status: {lab.status})")

            lab.status = LabStatus.STOPPING

        try:
            # Stop containers
            for container in lab.containers:
                await self._stop_container(container)

            # Remove networks
            for network in lab.networks:
                await self._remove_network(network)

            lab.status = LabStatus.STOPPED
            logger.info(f"Lab {lab_id} stopped successfully")

        except Exception as e:
            lab.status = LabStatus.FAILED
            lab.error_message = str(e)
            logger.error(f"Error stopping lab {lab_id}: {e}")
            raise

        return lab

    async def _stop_container(self, container: ContainerInfo) -> None:
        """Stop and remove a container."""
        if self._docker_available:
            # In production: Stop actual Docker container
            # docker_client.containers.get(container.container_id).stop()
            # docker_client.containers.get(container.container_id).remove()
            pass

        container.status = "stopped"
        logger.debug(f"Stopped container {container.hostname}")

    async def _remove_network(self, network: NetworkInfo) -> None:
        """Remove a network."""
        if self._docker_available:
            # In production: Remove actual Docker network
            # docker_client.networks.get(network.network_id).remove()
            pass

        logger.debug(f"Removed network {network.name}")

    async def kill_all_labs(self, activated_by: str) -> list[str]:
        """
        Emergency kill switch - stop all running labs immediately.

        Args:
            activated_by: Username of the user activating the kill switch

        Returns:
            List of lab IDs that were stopped
        """
        stopped_labs = []

        async with self._lock:
            running_labs = [
                lab for lab in self._labs.values()
                if lab.status in [LabStatus.RUNNING, LabStatus.STARTING]
            ]

        for lab in running_labs:
            try:
                await self.stop_lab(lab.lab_id)
                stopped_labs.append(lab.lab_id)
                logger.warning(
                    f"Kill switch: Stopped lab {lab.lab_id} "
                    f"(scenario: {lab.scenario_name}) by {activated_by}"
                )
            except Exception as e:
                logger.error(f"Kill switch: Failed to stop lab {lab.lab_id}: {e}")

        return stopped_labs

    def get_lab(self, lab_id: str) -> Optional[LabEnvironment]:
        """Get a lab by ID."""
        return self._labs.get(lab_id)

    def get_labs_for_scenario(self, scenario_id: str) -> list[LabEnvironment]:
        """Get all labs for a scenario."""
        return [
            lab for lab in self._labs.values()
            if lab.scenario_id == scenario_id
        ]

    def get_active_labs(self) -> list[LabEnvironment]:
        """Get all currently active labs."""
        return [
            lab for lab in self._labs.values()
            if lab.status == LabStatus.RUNNING
        ]

    def get_all_labs(self) -> list[LabEnvironment]:
        """Get all labs (active and stopped)."""
        return list(self._labs.values())


# Global orchestrator instance
orchestrator = Orchestrator()
