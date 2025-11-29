"""Tests for API rate limiting and throttling."""

import pytest
import asyncio
from datetime import datetime, timedelta
import time

from rate_limiting import (
    RateLimiter, RateLimitTier, RateLimitRule, ThrottleAction,
    EndpointRateLimitConfig, rate_limiter
)


class TestRateLimiter:
    """Tests for the RateLimiter class."""
    
    @pytest.fixture
    def limiter(self):
        """Create a fresh rate limiter for each test."""
        return RateLimiter()
    
    @pytest.mark.asyncio
    async def test_basic_allow(self, limiter):
        """Test that requests within limits are allowed."""
        result = await limiter.check_rate_limit(
            endpoint="/api/test",
            ip_address="192.168.1.1",
            user_id="user1",
            user_role="trainee"
        )
        
        assert result["allowed"] is True
        assert result["action"] == "allow"
        assert "remaining" in result
        assert result["remaining"]["per_minute"] > 0
    
    @pytest.mark.asyncio
    async def test_anonymous_limits(self, limiter):
        """Test that anonymous users have stricter limits."""
        # Anonymous users should be limited
        for _ in range(10):
            await limiter.check_rate_limit(
                endpoint="/api/test",
                ip_address="192.168.1.1"
            )
        
        # 11th request should be blocked (default anonymous limit is 10/min)
        result = await limiter.check_rate_limit(
            endpoint="/api/test",
            ip_address="192.168.1.1"
        )
        
        assert result["allowed"] is False
        assert result["action"] == "reject"
        # Could be burst or rate limit exceeded
        assert "limit exceeded" in result["reason"].lower()
    
    @pytest.mark.asyncio
    async def test_tier_based_limits(self, limiter):
        """Test different limits for different tiers."""
        # Admin should have higher limits
        admin_state = limiter._get_user_state("admin_user", RateLimitTier.ADMIN)
        trainee_state = limiter._get_user_state("trainee_user", RateLimitTier.TRAINEE)
        
        admin_rule = limiter._tier_rules[RateLimitTier.ADMIN]
        trainee_rule = limiter._tier_rules[RateLimitTier.TRAINEE]
        
        assert admin_rule.requests_per_minute > trainee_rule.requests_per_minute
        assert admin_rule.requests_per_hour > trainee_rule.requests_per_hour
    
    @pytest.mark.asyncio
    async def test_burst_protection(self, limiter):
        """Test burst limit protection."""
        # Set a low burst limit for testing
        limiter.set_tier_limits(RateLimitTier.TRAINEE, RateLimitRule(
            rule_id="test_trainee",
            name="Test Trainee",
            requests_per_minute=100,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_limit=3,
            burst_window_seconds=5
        ))
        
        # Make 3 requests quickly (should be allowed)
        for _ in range(3):
            result = await limiter.check_rate_limit(
                endpoint="/api/test",
                ip_address="192.168.1.1",
                user_id="burst_user",
                user_role="trainee"
            )
            assert result["allowed"] is True
        
        # 4th request should hit burst limit
        result = await limiter.check_rate_limit(
            endpoint="/api/test",
            ip_address="192.168.1.1",
            user_id="burst_user",
            user_role="trainee"
        )
        
        assert result["allowed"] is False
        assert "burst" in result["reason"].lower()
    
    @pytest.mark.asyncio
    async def test_endpoint_specific_limits(self, limiter):
        """Test endpoint-specific rate limits."""
        # Login endpoint should have stricter limits
        login_config = limiter._endpoint_configs.get("/auth/login")
        assert login_config is not None
        assert login_config.requests_per_minute == 5
        
        # Make 5 login attempts
        for _ in range(5):
            await limiter.check_rate_limit(
                endpoint="/auth/login",
                ip_address="192.168.1.2",
                user_id="login_user",
                user_role="trainee"
            )
        
        # 6th attempt should be blocked
        result = await limiter.check_rate_limit(
            endpoint="/auth/login",
            ip_address="192.168.1.2",
            user_id="login_user",
            user_role="trainee"
        )
        
        assert result["allowed"] is False
    
    @pytest.mark.asyncio
    async def test_exempt_tiers(self, limiter):
        """Test that admin is exempt from kill-switch limits."""
        # Configure kill-switch to allow many admin requests
        for _ in range(5):
            result = await limiter.check_rate_limit(
                endpoint="/kill-switch",
                ip_address="192.168.1.3",
                user_id="admin_user",
                user_role="admin"
            )
            assert result["allowed"] is True
    
    @pytest.mark.asyncio
    async def test_health_endpoint_exempt(self, limiter):
        """Test that health check endpoint is exempt from limits."""
        # Health endpoint should always be allowed
        for _ in range(100):
            result = await limiter.check_rate_limit(
                endpoint="/health",
                ip_address="192.168.1.4"
            )
            assert result["allowed"] is True
    
    @pytest.mark.asyncio
    async def test_violation_recording(self, limiter):
        """Test that violations are recorded."""
        # Trigger a violation
        for _ in range(15):
            await limiter.check_rate_limit(
                endpoint="/api/test",
                ip_address="192.168.1.5"
            )
        
        violations = limiter.get_violations()
        assert len(violations) > 0
        
        violation = violations[-1]
        assert "violation_id" in violation
        assert "timestamp" in violation
        assert "action_taken" in violation
    
    @pytest.mark.asyncio
    async def test_user_blocking(self, limiter):
        """Test manual user blocking."""
        limiter.block_user("bad_user", duration_minutes=60)
        
        result = await limiter.check_rate_limit(
            endpoint="/api/test",
            ip_address="192.168.1.6",
            user_id="bad_user",
            user_role="trainee"
        )
        
        assert result["allowed"] is False
        assert "blocked" in result["reason"].lower()
    
    @pytest.mark.asyncio
    async def test_user_unblocking(self, limiter):
        """Test unblocking a user."""
        limiter.block_user("blocked_user", duration_minutes=60)
        assert limiter.unblock_user("blocked_user") is True
        
        result = await limiter.check_rate_limit(
            endpoint="/api/test",
            ip_address="192.168.1.7",
            user_id="blocked_user",
            user_role="trainee"
        )
        
        assert result["allowed"] is True
    
    @pytest.mark.asyncio
    async def test_statistics_tracking(self, limiter):
        """Test that usage statistics are tracked."""
        # Make some requests
        for i in range(5):
            await limiter.check_rate_limit(
                endpoint=f"/api/endpoint{i}",
                ip_address="192.168.1.8",
                user_id="stats_user",
                user_role="trainee"
            )
        
        stats = limiter.get_statistics()
        assert stats["total_requests"] == 5
        assert "stats_user" in stats["requests_by_user"]
        assert stats["requests_by_user"]["stats_user"] == 5
    
    @pytest.mark.asyncio
    async def test_top_users(self, limiter):
        """Test getting top users by request count."""
        # Make requests from different users
        for _ in range(10):
            await limiter.check_rate_limit(
                endpoint="/api/test",
                ip_address="192.168.1.9",
                user_id="heavy_user",
                user_role="trainee"
            )
        
        for _ in range(5):
            await limiter.check_rate_limit(
                endpoint="/api/test",
                ip_address="192.168.1.10",
                user_id="light_user",
                user_role="trainee"
            )
        
        top_users = limiter.get_top_users(limit=5)
        assert len(top_users) >= 2
        assert top_users[0]["user_id"] == "heavy_user"
        assert top_users[0]["request_count"] == 10
    
    @pytest.mark.asyncio
    async def test_top_endpoints(self, limiter):
        """Test getting top endpoints by request count."""
        for _ in range(10):
            await limiter.check_rate_limit(
                endpoint="/api/popular",
                ip_address="192.168.1.11",
                user_id="user1",
                user_role="trainee"
            )
        
        for _ in range(3):
            await limiter.check_rate_limit(
                endpoint="/api/rare",
                ip_address="192.168.1.11",
                user_id="user1",
                user_role="trainee"
            )
        
        top_endpoints = limiter.get_top_endpoints(limit=5)
        assert len(top_endpoints) >= 2
        assert top_endpoints[0]["endpoint"] == "/api/popular"
    
    @pytest.mark.asyncio
    async def test_disable_rate_limiting(self, limiter):
        """Test that rate limiting can be disabled."""
        limiter.set_enabled(False)
        assert limiter.is_enabled() is False
        
        # All requests should be allowed when disabled
        for _ in range(1000):
            result = await limiter.check_rate_limit(
                endpoint="/api/test",
                ip_address="192.168.1.12"
            )
            assert result["allowed"] is True
        
        limiter.set_enabled(True)
    
    @pytest.mark.asyncio
    async def test_reset_user_state(self, limiter):
        """Test resetting user state."""
        # Make requests to build up state
        for _ in range(5):
            await limiter.check_rate_limit(
                endpoint="/api/test",
                ip_address="192.168.1.13",
                user_id="reset_user",
                user_role="trainee"
            )
        
        state = limiter.get_user_state("reset_user")
        assert state is not None
        assert state["requests_last_minute"] == 5
        
        # Reset state
        limiter.reset_user_state("reset_user")
        state = limiter.get_user_state("reset_user")
        assert state is None
    
    @pytest.mark.asyncio
    async def test_get_tier_rules(self, limiter):
        """Test getting tier rules."""
        rules = limiter.get_tier_rules()
        
        assert "admin" in rules
        assert "instructor" in rules
        assert "trainee" in rules
        assert "anonymous" in rules
        
        assert rules["admin"]["requests_per_minute"] > rules["trainee"]["requests_per_minute"]
    
    @pytest.mark.asyncio
    async def test_get_endpoint_configs(self, limiter):
        """Test getting endpoint configurations."""
        configs = limiter.get_endpoint_configs()
        
        # Should have default configs
        assert len(configs) > 0
        
        # Find login config
        login_config = next(
            (c for c in configs if c["endpoint_pattern"] == "/auth/login"),
            None
        )
        assert login_config is not None
        assert login_config["requests_per_minute"] == 5
    
    @pytest.mark.asyncio
    async def test_custom_endpoint_config(self, limiter):
        """Test setting custom endpoint config."""
        limiter.set_endpoint_config(
            "/api/custom",
            EndpointRateLimitConfig(
                endpoint_pattern="/api/custom",
                requests_per_minute=2,
                burst_limit=1
            )
        )
        
        # First request allowed
        result = await limiter.check_rate_limit(
            endpoint="/api/custom",
            ip_address="192.168.1.14",
            user_id="custom_user",
            user_role="trainee"
        )
        assert result["allowed"] is True
        
        # Second request hits burst limit
        result = await limiter.check_rate_limit(
            endpoint="/api/custom",
            ip_address="192.168.1.14",
            user_id="custom_user",
            user_role="trainee"
        )
        assert result["allowed"] is False
    
    @pytest.mark.asyncio
    async def test_wildcard_endpoint_matching(self, limiter):
        """Test wildcard matching for endpoints."""
        # The download endpoint uses wildcard
        download_config = limiter._match_endpoint_config(
            "/marketplace/templates/abc123/download"
        )
        assert download_config is not None
        assert download_config.requests_per_minute == 10
    
    @pytest.mark.asyncio
    async def test_remaining_limits_in_response(self, limiter):
        """Test that remaining limits are returned."""
        result = await limiter.check_rate_limit(
            endpoint="/api/test",
            ip_address="192.168.1.15",
            user_id="remaining_user",
            user_role="trainee"
        )
        
        assert "remaining" in result
        remaining = result["remaining"]
        assert "per_minute" in remaining
        assert "per_hour" in remaining
        assert "per_day" in remaining
        assert "burst" in remaining
        assert remaining["per_minute"] >= 0
    
    @pytest.mark.asyncio
    async def test_reset_statistics(self, limiter):
        """Test resetting statistics."""
        # Generate some stats
        await limiter.check_rate_limit(
            endpoint="/api/test",
            ip_address="192.168.1.16",
            user_id="stats_reset_user",
            user_role="trainee"
        )
        
        stats = limiter.get_statistics()
        assert stats["total_requests"] > 0
        
        # Reset
        limiter.reset_statistics()
        stats = limiter.get_statistics()
        assert stats["total_requests"] == 0
    
    @pytest.mark.asyncio
    async def test_violations_for_user(self, limiter):
        """Test getting violations for a specific user."""
        # Trigger violations for specific user
        for _ in range(15):
            await limiter.check_rate_limit(
                endpoint="/api/test",
                ip_address="192.168.1.17"
            )
        
        # Get violations for that IP
        violations = limiter.get_violations(user_id="ip:192.168.1.17")
        assert len(violations) > 0
        assert all(v["user_id"] == "ip:192.168.1.17" for v in violations)


class TestDefaultLimits:
    """Test default rate limit configurations."""
    
    def test_default_tier_limits_exist(self):
        """Test that default tier limits are defined."""
        assert RateLimitTier.ANONYMOUS in RateLimiter.DEFAULT_LIMITS
        assert RateLimitTier.TRAINEE in RateLimiter.DEFAULT_LIMITS
        assert RateLimitTier.INSTRUCTOR in RateLimiter.DEFAULT_LIMITS
        assert RateLimitTier.ADMIN in RateLimiter.DEFAULT_LIMITS
    
    def test_tier_hierarchy(self):
        """Test that tier limits follow hierarchy."""
        limits = RateLimiter.DEFAULT_LIMITS
        
        # Admin > Instructor > Trainee > Anonymous
        assert limits[RateLimitTier.ADMIN].requests_per_minute >= \
               limits[RateLimitTier.INSTRUCTOR].requests_per_minute
        
        assert limits[RateLimitTier.INSTRUCTOR].requests_per_minute >= \
               limits[RateLimitTier.TRAINEE].requests_per_minute
        
        assert limits[RateLimitTier.TRAINEE].requests_per_minute >= \
               limits[RateLimitTier.ANONYMOUS].requests_per_minute


class TestRateLimitRule:
    """Test RateLimitRule dataclass."""
    
    def test_rule_to_dict(self):
        """Test rule serialization."""
        rule = RateLimitRule(
            rule_id="test_rule",
            name="Test Rule",
            requests_per_minute=100,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_limit=20,
            action_on_exceed=ThrottleAction.DELAY
        )
        
        d = rule.to_dict()
        assert d["rule_id"] == "test_rule"
        assert d["name"] == "Test Rule"
        assert d["requests_per_minute"] == 100
        assert d["action_on_exceed"] == "delay"


class TestEndpointRateLimitConfig:
    """Test EndpointRateLimitConfig dataclass."""
    
    def test_config_to_dict(self):
        """Test config serialization."""
        config = EndpointRateLimitConfig(
            endpoint_pattern="/api/test",
            requests_per_minute=50,
            exempt_tiers=[RateLimitTier.ADMIN]
        )
        
        d = config.to_dict()
        assert d["endpoint_pattern"] == "/api/test"
        assert d["requests_per_minute"] == 50
        assert "admin" in d["exempt_tiers"]


class TestGlobalRateLimiter:
    """Test the global rate limiter instance."""
    
    def test_global_instance_exists(self):
        """Test that global rate limiter is available."""
        assert rate_limiter is not None
        assert isinstance(rate_limiter, RateLimiter)
    
    @pytest.mark.asyncio
    async def test_global_instance_works(self):
        """Test that global rate limiter functions."""
        result = await rate_limiter.check_rate_limit(
            endpoint="/api/global_test",
            ip_address="10.0.0.1",
            user_id="global_test_user",
            user_role="admin"
        )
        assert result["allowed"] is True
