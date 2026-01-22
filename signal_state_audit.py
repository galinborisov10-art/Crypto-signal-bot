"""
Signal State Audit Module for ESB v1.0 Phase 3.4

This module implements an immutable, append-only audit log for signal state
transitions per ESB v1.0 §3.4. It provides cryptographic hash chaining for
auditability and tamper detection.

Author: ESB v1.0 Implementation
Date: 2026-01-22
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from signal_state_machine import SignalState
import hashlib
import json


@dataclass(frozen=True)
class AuditEvent:
    """
    ESB v1.0 §3.4 - Immutable audit event for signal state transitions.
    
    All fields are frozen to enforce immutability.
    Events are append-only and cannot be modified after creation.
    """
    signal_id: str
    prev_state: SignalState
    next_state: SignalState
    timestamp: datetime
    actor: str
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    event_hash: str = ""
    
    def __post_init__(self):
        """Validate event fields after creation."""
        if not self.signal_id:
            raise ValueError("signal_id cannot be empty")
        if not self.actor:
            raise ValueError("actor cannot be empty")
        if not self.reason:
            raise ValueError("reason cannot be empty")
        if not isinstance(self.prev_state, SignalState):
            raise ValueError(f"prev_state must be SignalState, got {type(self.prev_state)}")
        if not isinstance(self.next_state, SignalState):
            raise ValueError(f"next_state must be SignalState, got {type(self.next_state)}")


def compute_event_hash(
    *,
    signal_id: str,
    prev_state: SignalState,
    next_state: SignalState,
    timestamp: datetime,
    actor: str,
    reason: str,
    metadata: Dict[str, Any],
    previous_hash: str
) -> str:
    """
    ESB v1.0 §3.4 - Compute deterministic hash for audit event.
    
    Hash is computed as:
    SHA256(previous_hash + serialized_event_data)
    
    Args:
        previous_hash: Hash of previous event in chain (or "GENESIS")
        All other args: Event payload fields
        
    Returns:
        Hexadecimal hash string
    """
    # Serialize event data deterministically
    event_data = {
        'signal_id': signal_id,
        'prev_state': prev_state.value,
        'next_state': next_state.value,
        'timestamp': timestamp.isoformat(),
        'actor': actor,
        'reason': reason,
        'metadata': metadata
    }
    
    # Convert to JSON with sorted keys for determinism
    payload = json.dumps(event_data, sort_keys=True)
    
    # Compute hash: previous_hash + payload
    hash_input = previous_hash + payload
    
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()


class SignalAuditLogger:
    """
    ESB v1.0 §3.4 - Append-only audit logger for signal state transitions.
    
    Maintains an immutable event log with cryptographic hash chaining.
    All operations are in-memory (no I/O).
    """
    
    GENESIS_HASH = "GENESIS"
    
    def __init__(self):
        """Initialize empty audit log."""
        self._events: List[AuditEvent] = []
    
    def append_event(
        self,
        *,
        signal_id: str,
        prev_state: SignalState,
        next_state: SignalState,
        actor: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None
    ) -> AuditEvent:
        """
        Append a new audit event to the log.
        
        ESB v1.0 §3.4:
        - Events are append-only
        - Events are immutable
        - Hash chain is maintained
        
        Args:
            signal_id: Unique signal identifier
            prev_state: State before transition
            next_state: State after transition
            actor: Entity performing transition
            reason: Justification for transition
            metadata: Optional additional context
            timestamp: Event timestamp (defaults to UTC now)
            
        Returns:
            Created AuditEvent (immutable)
        """
        if metadata is None:
            metadata = {}
        
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)
        
        # Get previous hash for chain
        previous_hash = self._get_last_hash()
        
        # Compute event hash
        event_hash = compute_event_hash(
            signal_id=signal_id,
            prev_state=prev_state,
            next_state=next_state,
            timestamp=timestamp,
            actor=actor,
            reason=reason,
            metadata=metadata,
            previous_hash=previous_hash
        )
        
        # Create immutable event
        event = AuditEvent(
            signal_id=signal_id,
            prev_state=prev_state,
            next_state=next_state,
            timestamp=timestamp,
            actor=actor,
            reason=reason,
            metadata=metadata,
            event_hash=event_hash
        )
        
        # Append to log (event is immutable, so safe to store)
        self._events.append(event)
        
        return event
    
    def _get_last_hash(self) -> str:
        """Get hash of last event, or GENESIS if log is empty."""
        if not self._events:
            return self.GENESIS_HASH
        return self._events[-1].event_hash
    
    def get_events(self, signal_id: Optional[str] = None) -> List[AuditEvent]:
        """
        Retrieve audit events.
        
        Args:
            signal_id: Optional filter by signal_id
            
        Returns:
            List of audit events (immutable)
        """
        if signal_id is None:
            return list(self._events)  # Return copy to prevent external mutation
        
        return [e for e in self._events if e.signal_id == signal_id]
    
    def get_event_count(self) -> int:
        """Get total number of audit events."""
        return len(self._events)


def verify_event_chain(events: List[AuditEvent]) -> bool:
    """
    ESB v1.0 §3.4 - Verify integrity of audit event chain.
    
    Recomputes all hashes and validates chain consistency.
    Detects tampering or corruption.
    
    Args:
        events: List of audit events to verify
        
    Returns:
        True if chain is valid, False if tampered/corrupted
        
    Raises:
        TypeError: If events is not a list
        ValueError: If events contains non-AuditEvent items
    """
    if not isinstance(events, list):
        raise TypeError(f"events must be list, got {type(events)}")
    
    if not events:
        return True  # Empty chain is valid
    
    # Validate all items are AuditEvents
    for i, event in enumerate(events):
        if not isinstance(event, AuditEvent):
            raise ValueError(f"Event at index {i} is not AuditEvent: {type(event)}")
    
    # Verify chain
    previous_hash = SignalAuditLogger.GENESIS_HASH
    
    for event in events:
        # Recompute expected hash
        expected_hash = compute_event_hash(
            signal_id=event.signal_id,
            prev_state=event.prev_state,
            next_state=event.next_state,
            timestamp=event.timestamp,
            actor=event.actor,
            reason=event.reason,
            metadata=event.metadata,
            previous_hash=previous_hash
        )
        
        # Check if stored hash matches expected
        if event.event_hash != expected_hash:
            return False  # Tampering detected
        
        # Update previous hash for next iteration
        previous_hash = event.event_hash
    
    return True  # Chain is valid
