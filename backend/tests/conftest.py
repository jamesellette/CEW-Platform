"""Shared test fixtures for CEW Platform tests."""
import pytest
from orchestrator import orchestrator


@pytest.fixture(autouse=True)
def force_simulation_mode():
    """Force simulation mode for all tests to ensure consistent behavior."""
    original_docker_available = orchestrator._docker_available
    original_docker_client = orchestrator._docker_client
    orchestrator._docker_available = False
    orchestrator._docker_client = None
    yield
    orchestrator._docker_available = original_docker_available
    orchestrator._docker_client = original_docker_client
