"""
API Rate Limiting & Throttling Module

Implements per-user and endpoint-specific rate limiting for resource protection.
"""

from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from collections import defaultdict
import time
import asyncio
from functools import wraps


class RateLimitTier(Enum):
    """Rate limit tiers for different user types."""
    ANONYMOUS = "anonymous"
    TRAINEE = "trainee"
    INSTRUCTOR = "instructor"
    ADMIN = "admin"


class ThrottleAction(Enum):
    """Actions when rate limit is exceeded."""
    REJECT = "reject"  # Return 429
    DELAY = "delay"    # Add artificial delay
    WARN = "warn"      # Allow but warn


@dataclass
class RateLimitRule:
    """A rate limiting rule."""
    rule_id: str
    name: str
    requests_per_minute: int
    requests_per_hour: int
    requests_per_day: int
    burst_limit: int = 10  # Max requests in a short burst
    burst_window_seconds: int = 10
    action_on_exceed: ThrottleAction = ThrottleAction.REJECT
    delay_seconds: float = 1.0  # Delay when action is DELAY
    enabled: bool = True
    
    def to_dict(self) -> dict:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "requests_per_day": self.requests_per_day,
            "burst_limit": self.burst_limit,
            "burst_window_seconds": self.burst_window_seconds,
            "action_on_exceed": self.action_on_exceed.value,
            "delay_seconds": self.delay_seconds,
            "enabled": self.enabled
        }


@dataclass
class RequestRecord:
    """Record of a single request."""
    timestamp: float
    endpoint: str
    ip_address: str
    user_id: Optional[str] = None


@dataclass
class UserRateLimitState:
    """State for tracking a user's rate limit."""
    user_id: str
    tier: RateLimitTier
    requests: List[RequestRecord] = field(default_factory=list)
    warnings_issued: int = 0
    blocked_until: Optional[datetime] = None
    total_requests_today: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)
    
    def clean_old_requests(self, max_age_seconds: int = 86400):
        """Remove requests older than max_age_seconds."""
        cutoff = time.time() - max_age_seconds
        self.requests = [r for r in self.requests if r.timestamp > cutoff]
    
    def count_requests_in_window(self, window_seconds: int) -> int:
        """Count requests within a time window."""
        cutoff = time.time() - window_seconds
        return sum(1 for r in self.requests if r.timestamp > cutoff)
    
    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "tier": self.tier.value,
            "requests_last_minute": self.count_requests_in_window(60),
            "requests_last_hour": self.count_requests_in_window(3600),
            "requests_today": self.total_requests_today,
            "warnings_issued": self.warnings_issued,
            "blocked_until": self.blocked_until.isoformat() if self.blocked_until else None
        }


@dataclass
class EndpointRateLimitConfig:
    """Rate limit configuration for a specific endpoint."""
    endpoint_pattern: str
    requests_per_minute: Optional[int] = None  # Override default
    requests_per_hour: Optional[int] = None
    burst_limit: Optional[int] = None
    exempt_tiers: List[RateLimitTier] = field(default_factory=list)
    enabled: bool = True
    
    def to_dict(self) -> dict:
        return {
            "endpoint_pattern": self.endpoint_pattern,
            "requests_per_minute": self.requests_per_minute,
            "requests_per_hour": self.requests_per_hour,
            "burst_limit": self.burst_limit,
            "exempt_tiers": [t.value for t in self.exempt_tiers],
            "enabled": self.enabled
        }


@dataclass 
class RateLimitViolation:
    """Record of a rate limit violation."""
    violation_id: str
    user_id: str
    ip_address: str
    endpoint: str
    rule_violated: str
    timestamp: datetime
    action_taken: ThrottleAction
    requests_count: int
    limit_value: int
    
    def to_dict(self) -> dict:
        return {
            "violation_id": self.violation_id,
            "user_id": self.user_id,
            "ip_address": self.ip_address,
            "endpoint": self.endpoint,
            "rule_violated": self.rule_violated,
            "timestamp": self.timestamp.isoformat(),
            "action_taken": self.action_taken.value,
            "requests_count": self.requests_count,
            "limit_value": self.limit_value
        }


@dataclass
class UsageStats:
    """Usage statistics for analytics."""
    total_requests: int = 0
    total_blocked: int = 0
    total_delayed: int = 0
    requests_by_endpoint: Dict[str, int] = field(default_factory=dict)
    requests_by_user: Dict[str, int] = field(default_factory=dict)
    requests_by_tier: Dict[str, int] = field(default_factory=dict)
    peak_requests_per_minute: int = 0
    last_reset: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "total_blocked": self.total_blocked,
            "total_delayed": self.total_delayed,
            "requests_by_endpoint": dict(self.requests_by_endpoint),
            "requests_by_user": dict(self.requests_by_user),
            "requests_by_tier": dict(self.requests_by_tier),
            "peak_requests_per_minute": self.peak_requests_per_minute,
            "last_reset": self.last_reset.isoformat()
        }


class RateLimiter:
    """
    Rate limiter with per-user and endpoint-specific limits.
    
    Features:
    - Per-user rate limits based on tier
    - Endpoint-specific overrides
    - Burst protection
    - Usage analytics
    - Configurable actions (reject, delay, warn)
    """
    
    # Default rate limits by tier (requests per minute/hour/day)
    DEFAULT_LIMITS = {
        RateLimitTier.ANONYMOUS: RateLimitRule(
            rule_id="anonymous_default",
            name="Anonymous User Limit",
            requests_per_minute=10,
            requests_per_hour=100,
            requests_per_day=500,
            burst_limit=5,
            burst_window_seconds=5
        ),
        RateLimitTier.TRAINEE: RateLimitRule(
            rule_id="trainee_default",
            name="Trainee User Limit",
            requests_per_minute=60,
            requests_per_hour=1000,
            requests_per_day=10000,
            burst_limit=20,
            burst_window_seconds=10
        ),
        RateLimitTier.INSTRUCTOR: RateLimitRule(
            rule_id="instructor_default",
            name="Instructor User Limit",
            requests_per_minute=120,
            requests_per_hour=3000,
            requests_per_day=30000,
            burst_limit=50,
            burst_window_seconds=10
        ),
        RateLimitTier.ADMIN: RateLimitRule(
            rule_id="admin_default",
            name="Admin User Limit",
            requests_per_minute=300,
            requests_per_hour=10000,
            requests_per_day=100000,
            burst_limit=100,
            burst_window_seconds=10
        )
    }
    
    def __init__(self):
        # User state tracking
        self._user_states: Dict[str, UserRateLimitState] = {}
        
        # IP-based tracking for anonymous users
        self._ip_states: Dict[str, UserRateLimitState] = {}
        
        # Custom tier rules (can override defaults)
        self._tier_rules: Dict[RateLimitTier, RateLimitRule] = dict(self.DEFAULT_LIMITS)
        
        # Endpoint-specific configs
        self._endpoint_configs: Dict[str, EndpointRateLimitConfig] = {}
        
        # Violation history
        self._violations: List[RateLimitViolation] = []
        self._max_violations_stored = 10000
        
        # Usage stats
        self._stats = UsageStats()
        
        # Global enable flag
        self._enabled = True
        
        # Block duration for repeated violations
        self._block_duration_minutes = 15
        self._violations_before_block = 10
        
        # Initialize default endpoint configs
        self._init_default_endpoint_configs()
    
    def _init_default_endpoint_configs(self):
        """Initialize default endpoint-specific rate limits."""
        # Auth endpoints - stricter limits to prevent brute force
        self._endpoint_configs["/auth/login"] = EndpointRateLimitConfig(
            endpoint_pattern="/auth/login",
            requests_per_minute=5,
            requests_per_hour=30,
            burst_limit=3
        )
        
        # Kill switch - very limited
        self._endpoint_configs["/kill-switch"] = EndpointRateLimitConfig(
            endpoint_pattern="/kill-switch",
            requests_per_minute=2,
            requests_per_hour=10,
            burst_limit=1,
            exempt_tiers=[RateLimitTier.ADMIN]
        )
        
        # Lab creation - resource intensive
        self._endpoint_configs["/scenarios/*/activate"] = EndpointRateLimitConfig(
            endpoint_pattern="/scenarios/*/activate",
            requests_per_minute=5,
            requests_per_hour=30,
            burst_limit=2
        )
        
        # Download endpoints
        self._endpoint_configs["/marketplace/templates/*/download"] = EndpointRateLimitConfig(
            endpoint_pattern="/marketplace/templates/*/download",
            requests_per_minute=10,
            requests_per_hour=100,
            burst_limit=5
        )
        
        # Health check - exempt from limits
        self._endpoint_configs["/health"] = EndpointRateLimitConfig(
            endpoint_pattern="/health",
            enabled=False  # No rate limiting on health checks
        )
    
    def _get_user_state(self, user_id: str, tier: RateLimitTier) -> UserRateLimitState:
        """Get or create user rate limit state."""
        if user_id not in self._user_states:
            self._user_states[user_id] = UserRateLimitState(
                user_id=user_id,
                tier=tier
            )
        state = self._user_states[user_id]
        state.tier = tier  # Update tier in case it changed
        return state
    
    def _get_ip_state(self, ip_address: str) -> UserRateLimitState:
        """Get or create IP-based rate limit state for anonymous users."""
        if ip_address not in self._ip_states:
            self._ip_states[ip_address] = UserRateLimitState(
                user_id=f"ip:{ip_address}",
                tier=RateLimitTier.ANONYMOUS
            )
        return self._ip_states[ip_address]
    
    def _match_endpoint_config(self, endpoint: str) -> Optional[EndpointRateLimitConfig]:
        """Find matching endpoint config (supports wildcards)."""
        # Exact match first
        if endpoint in self._endpoint_configs:
            return self._endpoint_configs[endpoint]
        
        # Wildcard matching
        for pattern, config in self._endpoint_configs.items():
            if "*" in pattern:
                # Simple wildcard matching
                parts = pattern.split("*")
                if len(parts) == 2:
                    prefix, suffix = parts
                    if endpoint.startswith(prefix) and endpoint.endswith(suffix):
                        return config
        
        return None
    
    def _get_effective_limits(
        self, 
        tier: RateLimitTier, 
        endpoint: str
    ) -> RateLimitRule:
        """Get effective rate limits considering endpoint overrides."""
        base_rule = self._tier_rules.get(tier, self.DEFAULT_LIMITS[RateLimitTier.TRAINEE])
        endpoint_config = self._match_endpoint_config(endpoint)
        
        if not endpoint_config or not endpoint_config.enabled:
            return base_rule
        
        # Check if tier is exempt
        if tier in endpoint_config.exempt_tiers:
            # Return very high limits for exempt tiers
            return RateLimitRule(
                rule_id=f"exempt_{tier.value}",
                name="Exempt",
                requests_per_minute=99999,
                requests_per_hour=999999,
                requests_per_day=9999999,
                burst_limit=9999
            )
        
        # Apply endpoint overrides
        return RateLimitRule(
            rule_id=f"{base_rule.rule_id}_{endpoint}",
            name=f"{base_rule.name} (endpoint override)",
            requests_per_minute=endpoint_config.requests_per_minute or base_rule.requests_per_minute,
            requests_per_hour=endpoint_config.requests_per_hour or base_rule.requests_per_hour,
            requests_per_day=base_rule.requests_per_day,
            burst_limit=endpoint_config.burst_limit or base_rule.burst_limit,
            burst_window_seconds=base_rule.burst_window_seconds,
            action_on_exceed=base_rule.action_on_exceed,
            delay_seconds=base_rule.delay_seconds
        )
    
    def _record_violation(
        self,
        state: UserRateLimitState,
        ip_address: str,
        endpoint: str,
        rule_name: str,
        action: ThrottleAction,
        count: int,
        limit: int
    ) -> RateLimitViolation:
        """Record a rate limit violation."""
        import uuid
        violation = RateLimitViolation(
            violation_id=str(uuid.uuid4()),
            user_id=state.user_id,
            ip_address=ip_address,
            endpoint=endpoint,
            rule_violated=rule_name,
            timestamp=datetime.utcnow(),
            action_taken=action,
            requests_count=count,
            limit_value=limit
        )
        
        self._violations.append(violation)
        
        # Trim old violations if needed
        if len(self._violations) > self._max_violations_stored:
            self._violations = self._violations[-self._max_violations_stored:]
        
        # Update stats
        if action == ThrottleAction.REJECT:
            self._stats.total_blocked += 1
        elif action == ThrottleAction.DELAY:
            self._stats.total_delayed += 1
        
        # Increment warnings for potential blocking
        state.warnings_issued += 1
        
        # Block user if too many violations
        if state.warnings_issued >= self._violations_before_block:
            state.blocked_until = datetime.utcnow() + timedelta(
                minutes=self._block_duration_minutes
            )
        
        return violation
    
    def _update_stats(
        self,
        endpoint: str,
        user_id: str,
        tier: RateLimitTier
    ):
        """Update usage statistics."""
        self._stats.total_requests += 1
        
        # Track by endpoint
        if endpoint not in self._stats.requests_by_endpoint:
            self._stats.requests_by_endpoint[endpoint] = 0
        self._stats.requests_by_endpoint[endpoint] += 1
        
        # Track by user
        if user_id not in self._stats.requests_by_user:
            self._stats.requests_by_user[user_id] = 0
        self._stats.requests_by_user[user_id] += 1
        
        # Track by tier
        tier_key = tier.value
        if tier_key not in self._stats.requests_by_tier:
            self._stats.requests_by_tier[tier_key] = 0
        self._stats.requests_by_tier[tier_key] += 1
    
    async def check_rate_limit(
        self,
        endpoint: str,
        ip_address: str,
        user_id: Optional[str] = None,
        user_role: Optional[str] = None
    ) -> dict:
        """
        Check if a request should be allowed.
        
        Returns:
            dict with:
            - allowed: bool
            - action: str (allow, reject, delay, warn)
            - delay_seconds: float (if action is delay)
            - reason: str (if not allowed)
            - remaining: dict with remaining limits
        """
        if not self._enabled:
            return {"allowed": True, "action": "allow", "remaining": {}}
        
        # Check endpoint config
        endpoint_config = self._match_endpoint_config(endpoint)
        if endpoint_config and not endpoint_config.enabled:
            return {"allowed": True, "action": "allow", "remaining": {}}
        
        # Determine tier
        tier = RateLimitTier.ANONYMOUS
        if user_role:
            tier_map = {
                "admin": RateLimitTier.ADMIN,
                "instructor": RateLimitTier.INSTRUCTOR,
                "trainee": RateLimitTier.TRAINEE
            }
            tier = tier_map.get(user_role.lower(), RateLimitTier.TRAINEE)
        
        # Get state
        if user_id:
            state = self._get_user_state(user_id, tier)
        else:
            state = self._get_ip_state(ip_address)
        
        # Check if blocked
        if state.blocked_until and datetime.utcnow() < state.blocked_until:
            return {
                "allowed": False,
                "action": "reject",
                "reason": f"Temporarily blocked until {state.blocked_until.isoformat()}",
                "blocked_until": state.blocked_until.isoformat(),
                "remaining": {}
            }
        elif state.blocked_until:
            # Block expired, reset
            state.blocked_until = None
            state.warnings_issued = 0
        
        # Clean old requests
        state.clean_old_requests()
        
        # Get effective limits
        limits = self._get_effective_limits(tier, endpoint)
        
        # Check burst limit
        burst_count = state.count_requests_in_window(limits.burst_window_seconds)
        if burst_count >= limits.burst_limit:
            violation = self._record_violation(
                state, ip_address, endpoint,
                "burst_limit", limits.action_on_exceed,
                burst_count, limits.burst_limit
            )
            
            if limits.action_on_exceed == ThrottleAction.REJECT:
                return {
                    "allowed": False,
                    "action": "reject",
                    "reason": f"Burst limit exceeded ({burst_count}/{limits.burst_limit})",
                    "violation_id": violation.violation_id,
                    "remaining": {}
                }
            elif limits.action_on_exceed == ThrottleAction.DELAY:
                return {
                    "allowed": True,
                    "action": "delay",
                    "delay_seconds": limits.delay_seconds,
                    "reason": "Request throttled due to burst",
                    "remaining": {}
                }
        
        # Check per-minute limit
        minute_count = state.count_requests_in_window(60)
        if minute_count >= limits.requests_per_minute:
            violation = self._record_violation(
                state, ip_address, endpoint,
                "per_minute", limits.action_on_exceed,
                minute_count, limits.requests_per_minute
            )
            
            if limits.action_on_exceed == ThrottleAction.REJECT:
                return {
                    "allowed": False,
                    "action": "reject",
                    "reason": f"Rate limit exceeded ({minute_count}/{limits.requests_per_minute} per minute)",
                    "violation_id": violation.violation_id,
                    "retry_after_seconds": 60 - (time.time() - state.requests[0].timestamp) if state.requests else 60,
                    "remaining": {}
                }
            elif limits.action_on_exceed == ThrottleAction.DELAY:
                return {
                    "allowed": True,
                    "action": "delay",
                    "delay_seconds": limits.delay_seconds,
                    "reason": "Request throttled",
                    "remaining": {}
                }
        
        # Check per-hour limit
        hour_count = state.count_requests_in_window(3600)
        if hour_count >= limits.requests_per_hour:
            violation = self._record_violation(
                state, ip_address, endpoint,
                "per_hour", limits.action_on_exceed,
                hour_count, limits.requests_per_hour
            )
            
            if limits.action_on_exceed == ThrottleAction.REJECT:
                return {
                    "allowed": False,
                    "action": "reject",
                    "reason": f"Hourly rate limit exceeded ({hour_count}/{limits.requests_per_hour})",
                    "violation_id": violation.violation_id,
                    "remaining": {}
                }
        
        # Check daily limit
        day_count = state.count_requests_in_window(86400)
        if day_count >= limits.requests_per_day:
            violation = self._record_violation(
                state, ip_address, endpoint,
                "per_day", ThrottleAction.REJECT,
                day_count, limits.requests_per_day
            )
            return {
                "allowed": False,
                "action": "reject",
                "reason": f"Daily rate limit exceeded ({day_count}/{limits.requests_per_day})",
                "violation_id": violation.violation_id,
                "remaining": {}
            }
        
        # Record this request
        state.requests.append(RequestRecord(
            timestamp=time.time(),
            endpoint=endpoint,
            ip_address=ip_address,
            user_id=user_id
        ))
        state.total_requests_today += 1
        
        # Update stats
        self._update_stats(endpoint, user_id or f"ip:{ip_address}", tier)
        
        # Calculate remaining
        remaining = {
            "per_minute": limits.requests_per_minute - minute_count - 1,
            "per_hour": limits.requests_per_hour - hour_count - 1,
            "per_day": limits.requests_per_day - day_count - 1,
            "burst": limits.burst_limit - burst_count - 1
        }
        
        return {
            "allowed": True,
            "action": "allow",
            "remaining": remaining
        }
    
    def set_tier_limits(self, tier: RateLimitTier, rule: RateLimitRule):
        """Set custom rate limits for a tier."""
        self._tier_rules[tier] = rule
    
    def set_endpoint_config(self, endpoint: str, config: EndpointRateLimitConfig):
        """Set endpoint-specific rate limit config."""
        self._endpoint_configs[endpoint] = config
    
    def get_endpoint_configs(self) -> List[dict]:
        """Get all endpoint configurations."""
        return [c.to_dict() for c in self._endpoint_configs.values()]
    
    def get_tier_rules(self) -> Dict[str, dict]:
        """Get all tier rules."""
        return {tier.value: rule.to_dict() for tier, rule in self._tier_rules.items()}
    
    def get_user_state(self, user_id: str) -> Optional[dict]:
        """Get rate limit state for a user."""
        state = self._user_states.get(user_id)
        if state:
            state.clean_old_requests()
            return state.to_dict()
        return None
    
    def get_violations(
        self,
        user_id: Optional[str] = None,
        limit: int = 100
    ) -> List[dict]:
        """Get violation history."""
        violations = self._violations
        if user_id:
            violations = [v for v in violations if v.user_id == user_id]
        return [v.to_dict() for v in violations[-limit:]]
    
    def get_statistics(self) -> dict:
        """Get usage statistics."""
        return self._stats.to_dict()
    
    def reset_user_state(self, user_id: str):
        """Reset rate limit state for a user."""
        if user_id in self._user_states:
            del self._user_states[user_id]
    
    def reset_ip_state(self, ip_address: str):
        """Reset rate limit state for an IP."""
        if ip_address in self._ip_states:
            del self._ip_states[ip_address]
    
    def unblock_user(self, user_id: str) -> bool:
        """Unblock a blocked user."""
        state = self._user_states.get(user_id)
        if state:
            state.blocked_until = None
            state.warnings_issued = 0
            return True
        return False
    
    def block_user(self, user_id: str, duration_minutes: int = 60):
        """Manually block a user."""
        if user_id in self._user_states:
            state = self._user_states[user_id]
        else:
            state = UserRateLimitState(
                user_id=user_id,
                tier=RateLimitTier.TRAINEE
            )
            self._user_states[user_id] = state
        
        state.blocked_until = datetime.utcnow() + timedelta(minutes=duration_minutes)
    
    def set_enabled(self, enabled: bool):
        """Enable or disable rate limiting globally."""
        self._enabled = enabled
    
    def is_enabled(self) -> bool:
        """Check if rate limiting is enabled."""
        return self._enabled
    
    def reset_statistics(self):
        """Reset usage statistics."""
        self._stats = UsageStats()
    
    def get_top_users(self, limit: int = 10) -> List[dict]:
        """Get top users by request count."""
        sorted_users = sorted(
            self._stats.requests_by_user.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {"user_id": user_id, "request_count": count}
            for user_id, count in sorted_users
        ]
    
    def get_top_endpoints(self, limit: int = 10) -> List[dict]:
        """Get top endpoints by request count."""
        sorted_endpoints = sorted(
            self._stats.requests_by_endpoint.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        
        return [
            {"endpoint": endpoint, "request_count": count}
            for endpoint, count in sorted_endpoints
        ]


# Global rate limiter instance
rate_limiter = RateLimiter()
