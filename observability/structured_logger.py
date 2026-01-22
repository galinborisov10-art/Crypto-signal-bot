"""
observability/structured_logger.py

ESB v1.0 §3.5 - Structured logging for signal lifecycle events.
Passive, read-only observability with zero behavioral impact.
"""

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from signal_state_machine import SignalState


class StructuredLogger:
    """
    ESB v1.0 §3.5 - Structured logger for signal state transitions.
    
    Emits JSON-formatted log entries for observability.
    Does NOT influence any business logic or state transitions.
    """
    
    def __init__(self):
        """Initialize in-memory log storage."""
        self._logs = []
    
    def log_transition(
        self,
        *,
        signal_id: str,
        from_state: SignalState,
        to_state: SignalState,
        actor: str,
        reason: str,
        timestamp: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log a signal state transition.
        
        ESB v1.0 §3.5:
        - Passive observation only
        - No interpretation or scoring
        - No behavioral impact
        
        Args:
            signal_id: Unique signal identifier
            from_state: Source state
            to_state: Target state
            actor: Entity performing transition
            reason: Justification for transition
            timestamp: Event timestamp (defaults to now UTC)
            metadata: Optional additional context
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        if metadata is None:
            metadata = {}
        
        log_entry = {
            'phase': 3,  # ESB Phase 3
            'signal_id': signal_id,
            'from_state': from_state.value,
            'to_state': to_state.value,
            'actor': actor,
            'reason': reason,
            'timestamp': timestamp.isoformat(),
            'metadata': metadata
        }
        
        # Store in-memory (in production, this would emit to logging backend)
        self._logs.append(log_entry)
    
    def get_logs(self, signal_id: Optional[str] = None) -> list:
        """
        Retrieve logged entries (for testing/debugging only).
        
        IMPORTANT: This method is for observability only.
        Business logic MUST NOT read these values.
        
        Args:
            signal_id: Optional filter by signal_id
            
        Returns:
            List of log entries
        """
        if signal_id is None:
            return list(self._logs)
        
        return [log for log in self._logs if log['signal_id'] == signal_id]
    
    def get_log_count(self) -> int:
        """Get total number of log entries."""
        return len(self._logs)
    
    def clear_logs(self) -> None:
        """Clear all logs (for testing only)."""
        self._logs.clear()
