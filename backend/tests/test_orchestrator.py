"""Tests for the orchestrator module."""
import pytest
from orchestrator import (
    orchestrator, LabStatus,
    ContainerHealth, ResourceLimits
)


@pytest.fixture(autouse=True)
def reset_orchestrator():
    """Reset orchestrator state before each test."""
    orchestrator._labs.clear()
    yield
    orchestrator._labs.clear()


@pytest.mark.asyncio
async def test_create_lab_basic():
    """Test creating a basic lab environment."""
    lab = await orchestrator.create_lab(
        scenario_id="test-scenario-1",
        scenario_name="Test Scenario",
        topology={
            "nodes": [
                {"id": "node-1", "hostname": "attacker", "image": "ubuntu:22.04"}
            ],
            "networks": [
                {"name": "test-net", "subnet": "10.0.0.0/24", "isolated": True}
            ]
        },
        constraints={"allow_external_network": False},
        activated_by="testuser"
    )

    assert lab.lab_id is not None
    assert lab.scenario_id == "test-scenario-1"
    assert lab.scenario_name == "Test Scenario"
    assert lab.activated_by == "testuser"
    assert lab.status == LabStatus.RUNNING
    assert len(lab.containers) == 1
    assert len(lab.networks) == 1


@pytest.mark.asyncio
async def test_create_lab_multiple_nodes():
    """Test creating a lab with multiple nodes and networks."""
    lab = await orchestrator.create_lab(
        scenario_id="test-scenario-2",
        scenario_name="Multi-Node Test",
        topology={
            "nodes": [
                {"id": "node-1", "hostname": "attacker", "image": "kali:latest", "ip": "10.0.0.10"},
                {"id": "node-2", "hostname": "target", "image": "ubuntu:22.04", "ip": "10.0.0.20"},
                {"id": "node-3", "hostname": "router", "image": "vyos:latest", "ip": "10.0.0.1"}
            ],
            "networks": [
                {"name": "lab-net", "subnet": "10.0.0.0/24", "isolated": True},
                {"name": "dmz-net", "subnet": "10.0.1.0/24", "isolated": True}
            ]
        },
        constraints={"allow_external_network": False},
        activated_by="instructor"
    )

    assert lab.status == LabStatus.RUNNING
    assert len(lab.containers) == 3
    assert len(lab.networks) == 2

    # Verify container details
    hostnames = [c.hostname for c in lab.containers]
    assert "attacker" in hostnames
    assert "target" in hostnames
    assert "router" in hostnames


@pytest.mark.asyncio
async def test_create_lab_external_network_blocked():
    """Test that external network access is blocked."""
    with pytest.raises(ValueError, match="External network access is not allowed"):
        await orchestrator.create_lab(
            scenario_id="test-blocked",
            scenario_name="Blocked Scenario",
            topology={"nodes": [], "networks": []},
            constraints={"allow_external_network": True},
            activated_by="testuser"
        )


@pytest.mark.asyncio
async def test_create_lab_real_rf_blocked():
    """Test that real RF transmission is blocked."""
    with pytest.raises(ValueError, match="Real RF transmission is not allowed"):
        await orchestrator.create_lab(
            scenario_id="test-rf-blocked",
            scenario_name="RF Blocked Scenario",
            topology={"nodes": [], "networks": []},
            constraints={"allow_real_rf": True},
            activated_by="testuser"
        )


@pytest.mark.asyncio
async def test_create_lab_non_isolated_network_blocked():
    """Test that non-isolated networks are blocked."""
    with pytest.raises(ValueError, match="must be isolated"):
        await orchestrator.create_lab(
            scenario_id="test-non-isolated",
            scenario_name="Non-Isolated Scenario",
            topology={
                "nodes": [],
                "networks": [
                    {"name": "unsafe-net", "subnet": "10.0.0.0/24", "isolated": False}
                ]
            },
            constraints={},
            activated_by="testuser"
        )


@pytest.mark.asyncio
async def test_stop_lab():
    """Test stopping a lab."""
    # Create a lab first
    lab = await orchestrator.create_lab(
        scenario_id="test-stop",
        scenario_name="Stop Test",
        topology={
            "nodes": [{"id": "n1", "hostname": "node1", "image": "ubuntu:22.04"}],
            "networks": [{"name": "net1", "subnet": "10.0.0.0/24", "isolated": True}]
        },
        constraints={},
        activated_by="testuser"
    )
    lab_id = lab.lab_id

    # Stop the lab
    stopped_lab = await orchestrator.stop_lab(lab_id)
    assert stopped_lab.status == LabStatus.STOPPED
    assert all(c.status == "stopped" for c in stopped_lab.containers)


@pytest.mark.asyncio
async def test_stop_lab_not_found():
    """Test stopping a non-existent lab."""
    with pytest.raises(ValueError, match="not found"):
        await orchestrator.stop_lab("nonexistent-lab-id")


@pytest.mark.asyncio
async def test_stop_lab_not_running():
    """Test stopping a lab that's already stopped."""
    # Create and stop a lab
    lab = await orchestrator.create_lab(
        scenario_id="test-double-stop",
        scenario_name="Double Stop Test",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="testuser"
    )
    await orchestrator.stop_lab(lab.lab_id)

    # Try to stop again
    with pytest.raises(ValueError, match="not running"):
        await orchestrator.stop_lab(lab.lab_id)


@pytest.mark.asyncio
async def test_kill_all_labs():
    """Test emergency kill switch."""
    # Create multiple labs
    for i in range(3):
        await orchestrator.create_lab(
            scenario_id=f"test-kill-{i}",
            scenario_name=f"Kill Test {i}",
            topology={"nodes": [], "networks": []},
            constraints={},
            activated_by="testuser"
        )

    # Verify 3 labs are running
    active = orchestrator.get_active_labs()
    assert len(active) == 3

    # Kill all
    stopped = await orchestrator.kill_all_labs("admin")
    assert len(stopped) == 3

    # Verify none are running
    active_after = orchestrator.get_active_labs()
    assert len(active_after) == 0


@pytest.mark.asyncio
async def test_get_lab():
    """Test getting a lab by ID."""
    lab = await orchestrator.create_lab(
        scenario_id="test-get",
        scenario_name="Get Test",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="testuser"
    )

    retrieved = orchestrator.get_lab(lab.lab_id)
    assert retrieved is not None
    assert retrieved.lab_id == lab.lab_id
    assert retrieved.scenario_name == "Get Test"


@pytest.mark.asyncio
async def test_get_lab_not_found():
    """Test getting a non-existent lab."""
    retrieved = orchestrator.get_lab("nonexistent")
    assert retrieved is None


@pytest.mark.asyncio
async def test_get_labs_for_scenario():
    """Test getting labs for a specific scenario."""
    # Create labs for same scenario
    await orchestrator.create_lab(
        scenario_id="scenario-x",
        scenario_name="Scenario X",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="user1"
    )
    lab1 = orchestrator.get_labs_for_scenario("scenario-x")[0]
    await orchestrator.stop_lab(lab1.lab_id)

    # Create another session for same scenario
    await orchestrator.create_lab(
        scenario_id="scenario-x",
        scenario_name="Scenario X",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="user2"
    )

    labs = orchestrator.get_labs_for_scenario("scenario-x")
    assert len(labs) == 2


@pytest.mark.asyncio
async def test_get_all_labs():
    """Test getting all labs."""
    await orchestrator.create_lab(
        scenario_id="test-all-1",
        scenario_name="All Test 1",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="user1"
    )
    await orchestrator.create_lab(
        scenario_id="test-all-2",
        scenario_name="All Test 2",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="user2"
    )

    all_labs = orchestrator.get_all_labs()
    assert len(all_labs) == 2


@pytest.mark.asyncio
async def test_lab_started_at_timestamp():
    """Test that started_at timestamp is set correctly."""
    lab = await orchestrator.create_lab(
        scenario_id="test-timestamp",
        scenario_name="Timestamp Test",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="testuser"
    )

    assert lab.started_at is not None


@pytest.mark.asyncio
async def test_duplicate_scenario_activation_blocked():
    """Test that a scenario can't be activated twice simultaneously."""
    await orchestrator.create_lab(
        scenario_id="duplicate-test",
        scenario_name="Duplicate Test",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="user1"
    )

    with pytest.raises(ValueError, match="already has an active lab session"):
        await orchestrator.create_lab(
            scenario_id="duplicate-test",
            scenario_name="Duplicate Test",
            topology={"nodes": [], "networks": []},
            constraints={},
            activated_by="user2"
        )


# ============ New Docker Integration Tests ============

@pytest.mark.asyncio
async def test_docker_mode_attribute():
    """Test that lab records Docker mode correctly."""
    lab = await orchestrator.create_lab(
        scenario_id="docker-mode-test",
        scenario_name="Docker Mode Test",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="testuser"
    )

    # In test mode, docker_mode should be False (simulation)
    assert lab.docker_mode is False


@pytest.mark.asyncio
async def test_container_health_simulation():
    """Test container health status in simulation mode."""
    lab = await orchestrator.create_lab(
        scenario_id="health-test",
        scenario_name="Health Test",
        topology={
            "nodes": [
                {"id": "n1", "hostname": "node1", "image": "ubuntu:22.04"}
            ],
            "networks": []
        },
        constraints={},
        activated_by="testuser"
    )

    health = await orchestrator.get_container_health(lab.lab_id)
    assert "node1" in health
    assert health["node1"]["health"] == "healthy"
    assert health["node1"]["status"] == "simulated"


@pytest.mark.asyncio
async def test_container_health_not_found():
    """Test container health with invalid lab ID."""
    with pytest.raises(ValueError, match="not found"):
        await orchestrator.get_container_health("nonexistent-lab")


@pytest.mark.asyncio
async def test_resource_usage_simulation():
    """Test resource usage in simulation mode."""
    lab = await orchestrator.create_lab(
        scenario_id="resource-test",
        scenario_name="Resource Test",
        topology={
            "nodes": [
                {"id": "n1", "hostname": "node1", "image": "ubuntu:22.04"}
            ],
            "networks": []
        },
        constraints={},
        activated_by="testuser"
    )

    usage = orchestrator.get_resource_usage(lab.lab_id)
    assert "node1" in usage
    assert usage["node1"]["mode"] == "simulated"
    assert "cpu_percent" in usage["node1"]
    assert "memory_usage_mb" in usage["node1"]


@pytest.mark.asyncio
async def test_resource_usage_not_found():
    """Test resource usage with invalid lab ID."""
    with pytest.raises(ValueError, match="not found"):
        orchestrator.get_resource_usage("nonexistent-lab")


@pytest.mark.asyncio
async def test_restart_unhealthy_containers_simulation():
    """Test auto-recovery in simulation mode."""
    lab = await orchestrator.create_lab(
        scenario_id="recovery-test",
        scenario_name="Recovery Test",
        topology={
            "nodes": [
                {"id": "n1", "hostname": "node1", "image": "ubuntu:22.04"}
            ],
            "networks": []
        },
        constraints={},
        activated_by="testuser"
    )

    # In simulation mode, should return empty list
    restarted = await orchestrator.restart_unhealthy_containers(lab.lab_id)
    assert restarted == []


@pytest.mark.asyncio
async def test_restart_unhealthy_containers_not_found():
    """Test auto-recovery with invalid lab ID."""
    with pytest.raises(ValueError, match="not found"):
        await orchestrator.restart_unhealthy_containers("nonexistent-lab")


@pytest.mark.asyncio
async def test_restart_unhealthy_containers_not_running():
    """Test auto-recovery on stopped lab."""
    lab = await orchestrator.create_lab(
        scenario_id="stopped-recovery-test",
        scenario_name="Stopped Recovery Test",
        topology={"nodes": [], "networks": []},
        constraints={},
        activated_by="testuser"
    )
    await orchestrator.stop_lab(lab.lab_id)

    with pytest.raises(ValueError, match="not running"):
        await orchestrator.restart_unhealthy_containers(lab.lab_id)


@pytest.mark.asyncio
async def test_resource_limits_from_constraints():
    """Test that resource limits are extracted from constraints."""
    lab = await orchestrator.create_lab(
        scenario_id="limits-test",
        scenario_name="Limits Test",
        topology={
            "nodes": [
                {"id": "n1", "hostname": "node1", "image": "ubuntu:22.04"}
            ],
            "networks": []
        },
        constraints={
            "resources": {
                "memory_limit": "1g",
                "cpu_quota": 80000,
                "cpu_period": 100000
            }
        },
        activated_by="testuser"
    )

    assert len(lab.containers) == 1
    container = lab.containers[0]
    assert container.resource_limits is not None
    assert container.resource_limits.memory_limit == "1g"
    assert container.resource_limits.cpu_quota == 80000
    assert container.resource_limits.cpu_percent == 80.0


@pytest.mark.asyncio
async def test_default_resource_limits():
    """Test that default resource limits are applied."""
    lab = await orchestrator.create_lab(
        scenario_id="default-limits-test",
        scenario_name="Default Limits Test",
        topology={
            "nodes": [
                {"id": "n1", "hostname": "node1", "image": "ubuntu:22.04"}
            ],
            "networks": []
        },
        constraints={},
        activated_by="testuser"
    )

    assert len(lab.containers) == 1
    container = lab.containers[0]
    assert container.resource_limits is not None
    assert container.resource_limits.memory_limit == "512m"
    assert container.resource_limits.cpu_quota == 50000
    assert container.resource_limits.cpu_percent == 50.0


def test_resource_limits_cpu_percent():
    """Test ResourceLimits cpu_percent calculation."""
    limits = ResourceLimits(
        memory_limit="1g",
        cpu_quota=25000,
        cpu_period=100000
    )
    assert limits.cpu_percent == 25.0


def test_orchestrator_docker_available_property():
    """Test docker_available property."""
    # Global orchestrator should have the property accessible
    assert isinstance(orchestrator.docker_available, bool)


@pytest.mark.asyncio
async def test_container_health_status_enum():
    """Test that container health status uses proper enum."""
    lab = await orchestrator.create_lab(
        scenario_id="health-enum-test",
        scenario_name="Health Enum Test",
        topology={
            "nodes": [
                {"id": "n1", "hostname": "node1", "image": "ubuntu:22.04"}
            ],
            "networks": []
        },
        constraints={},
        activated_by="testuser"
    )

    container = lab.containers[0]
    assert container.health == ContainerHealth.STARTING
