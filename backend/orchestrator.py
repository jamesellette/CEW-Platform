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

try:
    import docker
    from docker.types import IPAMConfig, IPAMPool
    DOCKER_SDK_AVAILABLE = True
except ImportError:
    DOCKER_SDK_AVAILABLE = False

logger = logging.getLogger(__name__)

# Default resource limits for containers
DEFAULT_MEMORY_LIMIT = "512m"
DEFAULT_CPU_PERIOD = 100000  # microseconds
DEFAULT_CPU_QUOTA = 50000    # 50% of one CPU core
DEFAULT_NETWORK_BANDWIDTH = "10mbit"  # Placeholder for future TC integration


class LabStatus(str, Enum):
    """Status of a lab session."""
    PENDING = "pending"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"


class ContainerHealth(str, Enum):
    """Health status of a container."""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    STARTING = "starting"
    UNKNOWN = "unknown"


@dataclass
class ResourceLimits:
    """Resource limits for a container."""
    memory_limit: str = DEFAULT_MEMORY_LIMIT
    cpu_quota: int = DEFAULT_CPU_QUOTA
    cpu_period: int = DEFAULT_CPU_PERIOD

    @property
    def cpu_percent(self) -> float:
        """Return CPU limit as percentage."""
        return (self.cpu_quota / self.cpu_period) * 100


@dataclass
class ContainerInfo:
    """Information about a running container."""
    container_id: str
    node_id: str
    hostname: str
    image: str
    ip_address: Optional[str] = None
    status: str = "created"
    health: ContainerHealth = ContainerHealth.UNKNOWN
    resource_limits: Optional[ResourceLimits] = None


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
    docker_mode: bool = False  # True if using real Docker


class Orchestrator:
    """
    Orchestrates the creation and management of isolated lab environments.

    This module integrates with the Docker SDK to create real isolated
    container environments. When Docker is not available, it falls back
    to simulation mode for development and testing.
    """

    def __init__(self, docker_client=None):
        """
        Initialize the orchestrator.

        Args:
            docker_client: Optional Docker client for dependency injection.
                          If not provided, will attempt to create one.
        """
        self._labs: dict[str, LabEnvironment] = {}
        self._lock = asyncio.Lock()
        self._docker_client = docker_client
        self._docker_available = self._check_docker()

    def _check_docker(self) -> bool:
        """Check if Docker daemon is available and accessible."""
        if not DOCKER_SDK_AVAILABLE:
            logger.info("Docker SDK not installed, running in simulation mode")
            return False

        try:
            if self._docker_client is None:
                self._docker_client = docker.from_env()
            # Ping the Docker daemon to verify connectivity
            self._docker_client.ping()
            logger.info("Docker daemon available, running in Docker mode")
            return True
        except docker.errors.DockerException as e:
            logger.warning(f"Docker not available: {e}. Running in simulation mode")
            return False

    @property
    def docker_available(self) -> bool:
        """Return whether Docker is available."""
        return self._docker_available

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
                status=LabStatus.STARTING,
                docker_mode=self._docker_available
            )
            self._labs[lab_id] = lab

        try:
            # Create networks first
            networks = topology.get("networks", [])
            for net_def in networks:
                network = await self._create_network(net_def, lab_id)
                lab.networks.append(network)

            # Create containers
            nodes = topology.get("nodes", [])
            resource_limits = self._get_resource_limits(constraints)
            for node_def in nodes:
                container = await self._create_container(
                    node_def, lab.networks, lab_id, resource_limits
                )
                lab.containers.append(container)

            # Start all containers
            if self._docker_available:
                await self._start_containers(lab)

            # Update status
            lab.status = LabStatus.RUNNING
            lab.started_at = datetime.now(timezone.utc)

            mode = "Docker" if self._docker_available else "simulation"
            logger.info(
                f"Lab {lab_id} created for scenario '{scenario_name}' "
                f"with {len(lab.containers)} containers and {len(lab.networks)} networks "
                f"(mode: {mode})"
            )

            return lab

        except Exception as e:
            lab.status = LabStatus.FAILED
            lab.error_message = str(e)
            logger.error(f"Failed to create lab {lab_id}: {e}")
            # Clean up any partially created resources
            await self._cleanup_lab_resources(lab)
            raise

    def _get_resource_limits(self, constraints: dict) -> ResourceLimits:
        """Extract resource limits from constraints or use defaults."""
        resource_config = constraints.get("resources", {})
        return ResourceLimits(
            memory_limit=resource_config.get("memory_limit", DEFAULT_MEMORY_LIMIT),
            cpu_quota=resource_config.get("cpu_quota", DEFAULT_CPU_QUOTA),
            cpu_period=resource_config.get("cpu_period", DEFAULT_CPU_PERIOD)
        )

    async def _create_network(self, net_def: dict, lab_id: str) -> NetworkInfo:
        """Create an isolated network."""
        name = net_def.get("name", "unnamed-network")
        subnet = net_def.get("subnet", "10.0.0.0/24")
        isolated = net_def.get("isolated", True)

        if not isolated:
            raise ValueError(
                f"Network '{name}' must be isolated for safety. "
                "Set 'isolated: true' in network definition."
            )

        # Generate unique network name with lab prefix
        network_name = f"cew-{lab_id[:8]}-{name}"

        if self._docker_available:
            try:
                ipam_config = IPAMConfig(
                    pool_configs=[IPAMPool(subnet=subnet)]
                )
                docker_network = self._docker_client.networks.create(
                    name=network_name,
                    driver="bridge",
                    internal=True,  # No external access - critical for isolation
                    ipam=ipam_config,
                    labels={
                        "cew.lab_id": lab_id,
                        "cew.network_name": name
                    }
                )
                network_id = docker_network.id
                logger.debug(
                    f"Created Docker network {name} ({network_id}) "
                    f"with subnet {subnet}"
                )
            except docker.errors.APIError as e:
                raise RuntimeError(f"Failed to create network '{name}': {e}")
        else:
            network_id = f"cew-net-{uuid.uuid4().hex[:12]}"
            logger.debug(
                f"Simulated network {name} ({network_id}) with subnet {subnet}"
            )

        return NetworkInfo(
            network_id=network_id,
            name=name,
            subnet=subnet,
            isolated=isolated
        )

    async def _create_container(
        self,
        node_def: dict,
        networks: list[NetworkInfo],
        lab_id: str,
        resource_limits: ResourceLimits
    ) -> ContainerInfo:
        """Create a container for a node."""
        node_id = node_def.get("id", str(uuid.uuid4()))
        hostname = node_def.get("hostname", f"node-{node_id}")
        image = node_def.get("image", "ubuntu:22.04")
        ip_address = node_def.get("ip")

        # Generate unique container name with lab prefix
        container_name = f"cew-{lab_id[:8]}-{hostname}"

        if self._docker_available:
            try:
                # Pull image if not available locally
                await self._ensure_image(image)

                # Create container with security constraints
                container = self._docker_client.containers.create(
                    image=image,
                    hostname=hostname,
                    name=container_name,
                    network_mode="none",  # Will attach to isolated networks
                    cap_drop=["ALL"],  # Drop all capabilities for security
                    security_opt=["no-new-privileges"],
                    mem_limit=resource_limits.memory_limit,
                    cpu_period=resource_limits.cpu_period,
                    cpu_quota=resource_limits.cpu_quota,
                    labels={
                        "cew.lab_id": lab_id,
                        "cew.node_id": node_id,
                        "cew.hostname": hostname
                    },
                    detach=True
                )
                container_id = container.id

                # Connect to networks
                for network in networks:
                    await self._connect_container_to_network(
                        container_id, network, ip_address
                    )

                logger.debug(
                    f"Created Docker container {hostname} ({container_id[:12]}) "
                    f"from {image} with limits: {resource_limits.memory_limit} RAM, "
                    f"{resource_limits.cpu_percent:.0f}% CPU"
                )
            except docker.errors.ImageNotFound:
                raise RuntimeError(f"Image '{image}' not found and could not be pulled")
            except docker.errors.APIError as e:
                raise RuntimeError(f"Failed to create container '{hostname}': {e}")
        else:
            container_id = f"cew-{uuid.uuid4().hex[:12]}"
            logger.debug(
                f"Simulated container {hostname} ({container_id}) from {image}"
            )

        return ContainerInfo(
            container_id=container_id,
            node_id=node_id,
            hostname=hostname,
            image=image,
            ip_address=ip_address,
            status="created",
            health=ContainerHealth.STARTING,
            resource_limits=resource_limits
        )

    async def _ensure_image(self, image: str) -> None:
        """Ensure the Docker image is available locally."""
        if not self._docker_available:
            return

        try:
            self._docker_client.images.get(image)
        except docker.errors.ImageNotFound:
            logger.info(f"Pulling image: {image}")
            try:
                self._docker_client.images.pull(image)
            except docker.errors.APIError as e:
                raise RuntimeError(f"Failed to pull image '{image}': {e}")

    async def _connect_container_to_network(
        self,
        container_id: str,
        network: NetworkInfo,
        ip_address: Optional[str]
    ) -> None:
        """Connect a container to a network."""
        if not self._docker_available:
            return

        try:
            docker_network = self._docker_client.networks.get(network.network_id)
            connect_kwargs = {}
            if ip_address:
                connect_kwargs["ipv4_address"] = ip_address
            docker_network.connect(container_id, **connect_kwargs)
        except docker.errors.APIError as e:
            logger.warning(
                f"Failed to connect container to network {network.name}: {e}"
            )

    async def _start_containers(self, lab: LabEnvironment) -> None:
        """Start all containers in a lab."""
        if not self._docker_available:
            return

        for container_info in lab.containers:
            try:
                container = self._docker_client.containers.get(
                    container_info.container_id
                )
                container.start()
                container_info.status = "running"
                container_info.health = ContainerHealth.HEALTHY
            except docker.errors.APIError as e:
                container_info.status = "failed"
                container_info.health = ContainerHealth.UNHEALTHY
                logger.error(
                    f"Failed to start container {container_info.hostname}: {e}"
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
            await self._cleanup_lab_resources(lab)
            lab.status = LabStatus.STOPPED
            logger.info(f"Lab {lab_id} stopped successfully")

        except Exception as e:
            lab.status = LabStatus.FAILED
            lab.error_message = str(e)
            logger.error(f"Error stopping lab {lab_id}: {e}")
            raise

        return lab

    async def _cleanup_lab_resources(self, lab: LabEnvironment) -> None:
        """Clean up all resources for a lab (containers and networks)."""
        # Stop and remove containers first
        for container in lab.containers:
            await self._stop_container(container)

        # Remove networks after containers
        for network in lab.networks:
            await self._remove_network(network)

    async def _stop_container(self, container: ContainerInfo) -> None:
        """Stop and remove a container."""
        if self._docker_available:
            try:
                docker_container = self._docker_client.containers.get(
                    container.container_id
                )
                docker_container.stop(timeout=10)
                docker_container.remove(force=True)
                logger.debug(
                    f"Stopped and removed Docker container {container.hostname}"
                )
            except docker.errors.NotFound:
                logger.debug(
                    f"Container {container.hostname} already removed"
                )
            except docker.errors.APIError as e:
                logger.warning(
                    f"Error stopping container {container.hostname}: {e}"
                )

        container.status = "stopped"
        container.health = ContainerHealth.UNKNOWN

    async def _remove_network(self, network: NetworkInfo) -> None:
        """Remove a network."""
        if self._docker_available:
            try:
                docker_network = self._docker_client.networks.get(network.network_id)
                docker_network.remove()
                logger.debug(f"Removed Docker network {network.name}")
            except docker.errors.NotFound:
                logger.debug(f"Network {network.name} already removed")
            except docker.errors.APIError as e:
                logger.warning(f"Error removing network {network.name}: {e}")

        logger.debug(f"Removed network {network.name}")

    async def get_container_health(self, lab_id: str) -> dict:
        """
        Get health status of all containers in a lab.

        Args:
            lab_id: Unique identifier of the lab

        Returns:
            Dictionary with container health information
        """
        lab = self._labs.get(lab_id)
        if not lab:
            raise ValueError(f"Lab {lab_id} not found")

        health_status = {}
        for container in lab.containers:
            if self._docker_available:
                try:
                    docker_container = self._docker_client.containers.get(
                        container.container_id
                    )
                    attrs = docker_container.attrs
                    state = attrs.get("State", {})

                    # Determine health based on container state
                    if state.get("Running", False):
                        container.health = ContainerHealth.HEALTHY
                        container.status = "running"
                    elif state.get("Dead", False):
                        container.health = ContainerHealth.UNHEALTHY
                        container.status = "dead"
                    elif state.get("Paused", False):
                        container.health = ContainerHealth.UNKNOWN
                        container.status = "paused"
                    else:
                        container.health = ContainerHealth.UNKNOWN
                        container.status = "unknown"

                    health_status[container.hostname] = {
                        "status": container.status,
                        "health": container.health.value,
                        "running": state.get("Running", False),
                        "started_at": state.get("StartedAt"),
                        "exit_code": state.get("ExitCode")
                    }
                except docker.errors.NotFound:
                    container.health = ContainerHealth.UNHEALTHY
                    container.status = "not_found"
                    health_status[container.hostname] = {
                        "status": "not_found",
                        "health": ContainerHealth.UNHEALTHY.value
                    }
                except docker.errors.APIError as e:
                    health_status[container.hostname] = {
                        "status": "error",
                        "health": ContainerHealth.UNKNOWN.value,
                        "error": str(e)
                    }
            else:
                # Simulation mode - all containers are "healthy"
                health_status[container.hostname] = {
                    "status": "simulated",
                    "health": ContainerHealth.HEALTHY.value
                }

        return health_status

    async def restart_unhealthy_containers(self, lab_id: str) -> list[str]:
        """
        Auto-recovery: restart any unhealthy containers in a lab.

        Args:
            lab_id: Unique identifier of the lab

        Returns:
            List of container hostnames that were restarted
        """
        lab = self._labs.get(lab_id)
        if not lab:
            raise ValueError(f"Lab {lab_id} not found")

        if lab.status != LabStatus.RUNNING:
            raise ValueError(f"Lab {lab_id} is not running")

        restarted = []

        if not self._docker_available:
            logger.debug("Auto-recovery skipped in simulation mode")
            return restarted

        for container in lab.containers:
            try:
                docker_container = self._docker_client.containers.get(
                    container.container_id
                )
                if not docker_container.attrs.get("State", {}).get("Running", False):
                    logger.info(
                        f"Restarting unhealthy container {container.hostname}"
                    )
                    docker_container.restart(timeout=10)
                    container.status = "running"
                    container.health = ContainerHealth.HEALTHY
                    restarted.append(container.hostname)
            except docker.errors.NotFound:
                logger.warning(
                    f"Container {container.hostname} not found, cannot restart"
                )
            except docker.errors.APIError as e:
                logger.error(
                    f"Failed to restart container {container.hostname}: {e}"
                )

        return restarted

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

    def get_resource_usage(self, lab_id: str) -> dict:
        """
        Get resource usage for all containers in a lab.

        Args:
            lab_id: Unique identifier of the lab

        Returns:
            Dictionary with resource usage information
        """
        lab = self._labs.get(lab_id)
        if not lab:
            raise ValueError(f"Lab {lab_id} not found")

        usage = {}

        if not self._docker_available:
            # Simulation mode - return placeholder data
            for container in lab.containers:
                usage[container.hostname] = {
                    "cpu_percent": 0.0,
                    "memory_usage_mb": 0.0,
                    "memory_limit_mb": 512.0,
                    "mode": "simulated"
                }
            return usage

        for container in lab.containers:
            try:
                docker_container = self._docker_client.containers.get(
                    container.container_id
                )
                stats = docker_container.stats(stream=False)

                # Calculate CPU percentage with safety checks
                cpu_percent = 0.0
                try:
                    cpu_stats = stats.get("cpu_stats", {})
                    precpu_stats = stats.get("precpu_stats", {})

                    # Handle potential missing or empty stats
                    current_usage = cpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                    prev_usage = precpu_stats.get("cpu_usage", {}).get("total_usage", 0)
                    system_usage = cpu_stats.get("system_cpu_usage", 0)
                    prev_system_usage = precpu_stats.get("system_cpu_usage", 0)

                    cpu_delta = current_usage - prev_usage
                    system_delta = system_usage - prev_system_usage

                    if system_delta > 0 and cpu_delta >= 0:
                        cpu_count = cpu_stats.get("online_cpus", 1)
                        cpu_percent = (cpu_delta / system_delta) * cpu_count * 100.0
                except (KeyError, TypeError, ZeroDivisionError):
                    cpu_percent = 0.0

                # Calculate memory usage with safety checks
                memory_stats = stats.get("memory_stats", {})
                memory_usage = memory_stats.get("usage", 0) / (1024 * 1024)  # MB
                memory_limit = memory_stats.get("limit", 1) / (1024 * 1024)  # MB, default 1 to avoid division by zero

                usage[container.hostname] = {
                    "cpu_percent": round(cpu_percent, 2),
                    "memory_usage_mb": round(memory_usage, 2),
                    "memory_limit_mb": round(memory_limit, 2),
                    "mode": "docker"
                }
            except docker.errors.NotFound:
                usage[container.hostname] = {
                    "status": "not_found"
                }
            except docker.errors.APIError as e:
                usage[container.hostname] = {
                    "status": "error",
                    "error": str(e)
                }

        return usage


# Global orchestrator instance
orchestrator = Orchestrator()
