"""
Rate Limiter Module
Implements rate limiting to prevent spam and DDoS attacks
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiting system with auto-ban functionality
    
    Features:
    - Per-minute limit (default: 20 requests)
    - Per-hour limit (default: 100 requests)
    - Auto-ban after 3 violations (default: 60 minutes)
    - Suspicious activity tracking
    """
    
    def __init__(
        self,
        max_requests_per_minute: int = 20,
        max_requests_per_hour: int = 100,
        ban_duration_minutes: int = 60
    ):
        self.max_requests_per_minute = max_requests_per_minute
        self.max_requests_per_hour = max_requests_per_hour
        self.ban_duration_minutes = ban_duration_minutes
        
        # Track requests per user
        self.requests_minute: Dict[int, List[float]] = defaultdict(list)
        self.requests_hour: Dict[int, List[float]] = defaultdict(list)
        
        # Banned users
        self.banned_users: Dict[int, float] = {}  # user_id: ban_until_timestamp
        
        # Suspicious activity counter
        self.suspicious_users: Dict[int, int] = defaultdict(int)
        
        logger.info(f"✅ Rate Limiter initialized: {max_requests_per_minute}/min, {max_requests_per_hour}/hour")
    
    def is_allowed(self, user_id: int) -> bool:
        """
        Check if user is allowed to make request
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if allowed, False if rate limited or banned
        """
        current_time = time.time()
        
        # Check if banned
        if self.is_banned(user_id):
            logger.warning(f"🚫 User {user_id} is banned, request denied")
            return False
        
        # Cleanup old requests
        self._cleanup_old_requests(user_id, current_time)
        
        # Check minute limit (20 requests)
        minute_requests = len(self.requests_minute[user_id])
        if minute_requests >= self.max_requests_per_minute:
            logger.warning(f"⚠️ User {user_id} exceeded minute limit: {minute_requests}/{self.max_requests_per_minute}")
            self._mark_suspicious(user_id, "MINUTE_LIMIT")
            return False
        
        # Check hour limit (100 requests)
        hour_requests = len(self.requests_hour[user_id])
        if hour_requests >= self.max_requests_per_hour:
            logger.warning(f"⚠️ User {user_id} exceeded hour limit: {hour_requests}/{self.max_requests_per_hour}")
            self._mark_suspicious(user_id, "HOUR_LIMIT")
            return False
        
        # Record request
        self.requests_minute[user_id].append(current_time)
        self.requests_hour[user_id].append(current_time)
        
        return True
    
    def _cleanup_old_requests(self, user_id: int, current_time: float):
        """
        Remove old request timestamps
        
        Args:
            user_id: Telegram user ID
            current_time: Current timestamp
        """
        # Remove requests older than 1 minute
        minute_cutoff = current_time - 60
        self.requests_minute[user_id] = [
            ts for ts in self.requests_minute[user_id] if ts > minute_cutoff
        ]
        
        # Remove requests older than 1 hour
        hour_cutoff = current_time - 3600
        self.requests_hour[user_id] = [
            ts for ts in self.requests_hour[user_id] if ts > hour_cutoff
        ]
    
    def _mark_suspicious(self, user_id: int, reason: str):
        """
        Mark user as suspicious, auto-ban after 3 violations
        
        Args:
            user_id: Telegram user ID
            reason: Reason for marking as suspicious
        """
        self.suspicious_users[user_id] += 1
        violations = self.suspicious_users[user_id]
        
        logger.warning(f"⚠️ User {user_id} marked suspicious ({reason}): Violation #{violations}")
        
        # Auto-ban after 3 violations
        if violations >= 3:
            self.ban_user(user_id, self.ban_duration_minutes)
            logger.error(f"🔒 User {user_id} AUTO-BANNED after {violations} violations")
    
    def ban_user(self, user_id: int, duration_minutes: int = None):
        """
        Ban user for specified duration
        
        Args:
            user_id: Telegram user ID
            duration_minutes: Ban duration in minutes (default: ban_duration_minutes)
        """
        if duration_minutes is None:
            duration_minutes = self.ban_duration_minutes
        
        ban_until = time.time() + (duration_minutes * 60)
        self.banned_users[user_id] = ban_until
        
        logger.error(f"🔒 User {user_id} BANNED for {duration_minutes} minutes")
    
    def unban_user(self, user_id: int):
        """
        Manually unban user
        
        Args:
            user_id: Telegram user ID
        """
        if user_id in self.banned_users:
            del self.banned_users[user_id]
            
            # Reset suspicious counter
            if user_id in self.suspicious_users:
                del self.suspicious_users[user_id]
            
            logger.info(f"✅ User {user_id} UNBANNED")
    
    def is_banned(self, user_id: int) -> bool:
        """
        Check if user is currently banned
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            True if banned, False otherwise
        """
        if user_id not in self.banned_users:
            return False
        
        current_time = time.time()
        ban_until = self.banned_users[user_id]
        
        # Check if ban expired
        if current_time >= ban_until:
            # Auto-unban
            self.unban_user(user_id)
            logger.info(f"✅ User {user_id} ban expired, auto-unbanned")
            return False
        
        return True
    
    def get_ban_time_remaining(self, user_id: int) -> int:
        """
        Get remaining ban time in seconds
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Remaining seconds (0 if not banned)
        """
        if not self.is_banned(user_id):
            return 0
        
        current_time = time.time()
        ban_until = self.banned_users[user_id]
        
        return int(ban_until - current_time)
    
    def get_user_stats(self, user_id: int) -> dict:
        """
        Get user statistics
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with user stats
        """
        current_time = time.time()
        self._cleanup_old_requests(user_id, current_time)
        
        return {
            'requests_last_minute': len(self.requests_minute[user_id]),
            'requests_last_hour': len(self.requests_hour[user_id]),
            'violations': self.suspicious_users.get(user_id, 0),
            'is_banned': self.is_banned(user_id),
            'ban_time_remaining': self.get_ban_time_remaining(user_id)
        }


# Global instance
rate_limiter = RateLimiter(
    max_requests_per_minute=20,
    max_requests_per_hour=100,
    ban_duration_minutes=60
)


def check_rate_limit(user_id: int) -> bool:
    """
    Helper function to check rate limit
    
    Args:
        user_id: Telegram user ID
        
    Returns:
        True if allowed, False if rate limited
    """
    return rate_limiter.is_allowed(user_id)
