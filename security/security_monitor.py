"""
Security Monitor Module
Monitors and logs security events, assesses threat levels
"""

import logging
from datetime import datetime
from collections import defaultdict
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class SecurityMonitor:
    """
    Security Monitoring System
    
    Features:
    - Log all security events
    - Assess threat level (LOW/MEDIUM/HIGH/CRITICAL)
    - Track suspicious activity
    - Generate security reports
    """
    
    def __init__(self, admin_notify_func=None):
        self.admin_notify = admin_notify_func
        self.suspicious_events: Dict[str, List[dict]] = defaultdict(list)
        self.threat_level = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
        
        logger.info("✅ Security Monitor initialized")
    
    def log_event(self, event_type: str, user_id: int, details: str):
        """
        Log security event
        
        Event types:
        - RATE_LIMIT_EXCEEDED
        - AUTO_BAN
        - UNAUTHORIZED_ACCESS
        - SUSPICIOUS_ACTIVITY
        - USER_BLACKLISTED
        - ADMIN_ACTION
        
        Args:
            event_type: Type of security event
            user_id: Telegram user ID
            details: Event details
        """
        event = {
            'timestamp': datetime.now(),
            'type': event_type,
            'user_id': user_id,
            'details': details
        }
        
        self.suspicious_events[event_type].append(event)
        
        # Log to file
        logger.warning(f"🔒 Security Event: {event_type} | User {user_id} | {details}")
        
        # Assess threat level
        self._assess_threat_level()
    
    def _assess_threat_level(self):
        """
        Assess current threat level based on recent events
        
        Threat levels:
        - LOW: < 20 events/hour
        - MEDIUM: 20-50 events/hour
        - HIGH: 50-100 events/hour
        - CRITICAL: > 100 events/hour
        """
        # Count events in last hour
        now = datetime.now()
        recent_events = 0
        
        for event_list in self.suspicious_events.values():
            for event in event_list:
                time_diff = (now - event['timestamp']).total_seconds()
                if time_diff < 3600:  # Last hour
                    recent_events += 1
        
        old_level = self.threat_level
        
        if recent_events > 100:
            self.threat_level = "CRITICAL"
        elif recent_events > 50:
            self.threat_level = "HIGH"
        elif recent_events > 20:
            self.threat_level = "MEDIUM"
        else:
            self.threat_level = "LOW"
        
        # Log if level changed
        if self.threat_level != old_level:
            logger.warning(f"⚠️ Threat level changed: {old_level} → {self.threat_level}")
            
            # Notify admins if threat is HIGH or CRITICAL
            if self.threat_level in ["HIGH", "CRITICAL"]:
                message = f"🚨 Security Alert: Threat level is now {self.threat_level}\n"
                message += f"Recent events: {recent_events} in last hour"
                # TODO: Implement admin notification when admin_notify function is provided
    
    async def _notify_admins(self, message: str):
        """
        Notify admins of security events
        
        Args:
            message: Message to send to admins
        """
        if self.admin_notify:
            try:
                await self.admin_notify(message)
                logger.info("✅ Admin notification sent")
            except Exception as e:
                logger.error(f"❌ Failed to notify admins: {e}")
    
    def get_security_report(self) -> str:
        """
        Generate security report
        
        Returns:
            Formatted security report
        """
        report = "━━━━━━━━━━━━━━━━━━━━\n"
        report += "🔒 **SECURITY REPORT**\n"
        report += "━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Threat level
        threat_emoji = {
            "LOW": "🟢",
            "MEDIUM": "🟡",
            "HIGH": "🟠",
            "CRITICAL": "🔴"
        }
        
        report += f"**Threat Level:** {threat_emoji.get(self.threat_level, '⚪')} {self.threat_level}\n\n"
        
        # Count events in last hour
        now = datetime.now()
        events_last_hour = 0
        events_last_day = 0
        
        for event_list in self.suspicious_events.values():
            for event in event_list:
                time_diff = (now - event['timestamp']).total_seconds()
                if time_diff < 3600:
                    events_last_hour += 1
                if time_diff < 86400:
                    events_last_day += 1
        
        report += f"**Events (Last Hour):** {events_last_hour}\n"
        report += f"**Events (Last 24h):** {events_last_day}\n\n"
        
        # Event breakdown
        report += "**Event Breakdown:**\n"
        
        event_counts = {}
        for event_type, event_list in self.suspicious_events.items():
            # Count events in last 24 hours
            count_24h = sum(
                1 for event in event_list
                if (now - event['timestamp']).total_seconds() < 86400
            )
            if count_24h > 0:
                event_counts[event_type] = count_24h
        
        if event_counts:
            for event_type, count in sorted(event_counts.items(), key=lambda x: x[1], reverse=True):
                report += f"• {event_type}: {count}\n"
        else:
            report += "• No recent events\n"
        
        report += "\n━━━━━━━━━━━━━━━━━━━━"
        
        return report
    
    def get_user_events(self, user_id: int, limit: int = 10) -> List[dict]:
        """
        Get recent events for a specific user
        
        Args:
            user_id: Telegram user ID
            limit: Maximum number of events to return
            
        Returns:
            List of recent events for the user
        """
        user_events = []
        
        for event_list in self.suspicious_events.values():
            for event in event_list:
                if event['user_id'] == user_id:
                    user_events.append(event)
        
        # Sort by timestamp (newest first)
        user_events.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return user_events[:limit]
    
    def clear_old_events(self, days: int = 7):
        """
        Clear events older than specified days
        
        Args:
            days: Number of days to keep events
        """
        now = datetime.now()
        cutoff_seconds = days * 86400
        
        cleared_count = 0
        
        for event_type in list(self.suspicious_events.keys()):
            event_list = self.suspicious_events[event_type]
            
            # Filter out old events
            new_list = [
                event for event in event_list
                if (now - event['timestamp']).total_seconds() < cutoff_seconds
            ]
            
            cleared_count += len(event_list) - len(new_list)
            
            if new_list:
                self.suspicious_events[event_type] = new_list
            else:
                del self.suspicious_events[event_type]
        
        if cleared_count > 0:
            logger.info(f"🗑️ Cleared {cleared_count} old security events")
        
        # Re-assess threat level
        self._assess_threat_level()
    
    def get_stats(self) -> dict:
        """
        Get security statistics
        
        Returns:
            Dictionary with security stats
        """
        now = datetime.now()
        
        total_events = sum(len(events) for events in self.suspicious_events.values())
        
        events_last_hour = 0
        events_last_day = 0
        
        for event_list in self.suspicious_events.values():
            for event in event_list:
                time_diff = (now - event['timestamp']).total_seconds()
                if time_diff < 3600:
                    events_last_hour += 1
                if time_diff < 86400:
                    events_last_day += 1
        
        return {
            'threat_level': self.threat_level,
            'total_events': total_events,
            'events_last_hour': events_last_hour,
            'events_last_day': events_last_day,
            'event_types': len(self.suspicious_events)
        }


# Global instance
security_monitor = SecurityMonitor()


def log_security_event(event_type: str, user_id: int, details: str):
    """
    Helper to log security event
    
    Args:
        event_type: Type of security event
        user_id: Telegram user ID
        details: Event details
    """
    security_monitor.log_event(event_type, user_id, details)
