"""Shared test fixtures for CEW Platform tests."""
import pytest
from orchestrator import orchestrator
from rate_limiting import rate_limiter


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


@pytest.fixture(autouse=True)
def disable_rate_limiting():
    """Disable rate limiting during tests to avoid test interference."""
    original_enabled = rate_limiter._enabled
    rate_limiter.set_enabled(False)
    yield
    rate_limiter.set_enabled(original_enabled)

