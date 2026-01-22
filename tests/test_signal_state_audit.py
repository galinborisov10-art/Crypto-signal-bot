"""
Unit tests for Signal State Audit Module (ESB v1.0 §3.4)

Minimal contract proofs:
- Append-only behavior
- Event immutability
- Deterministic hashing
- Hash chaining correctness
- Tampering detection

Author: ESB v1.0 Implementation
Date: 2026-01-22
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime, timezone
from signal_state_machine import SignalState
from signal_state_audit import (
    AuditEvent,
    SignalAuditLogger,
    compute_event_hash,
    verify_event_chain
)


class TestAuditEventImmutability:
    """Contract: Events are immutable after creation."""
    
    def test_event_is_frozen(self):
        """Frozen dataclass prevents modification."""
        event = AuditEvent(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=datetime.now(timezone.utc),
            actor="system",
            reason="test",
            event_hash="hash"
        )
        
        with pytest.raises(AttributeError):
            event.signal_id = "modified"
    
    def test_structural_validation_only(self):
        """Only structural validation, no business semantics."""
        # Should accept empty strings (business semantics not enforced)
        event = AuditEvent(
            signal_id="",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=datetime.now(timezone.utc),
            actor="",
            reason="",
            event_hash="hash"
        )
        assert event.signal_id == ""
        assert event.actor == ""
    
    @pytest.mark.parametrize("invalid_state,field_name", [
        ("not_a_state", "prev_state"),
        (None, "prev_state"),
        ("invalid", "next_state"),
        (123, "next_state"),
    ])
    def test_rejects_invalid_state_types(self, invalid_state, field_name):
        """Structural validation: states must be SignalState."""
        kwargs = {
            "signal_id": "test",
            "prev_state": SignalState.PENDING,
            "next_state": SignalState.VALIDATED,
            "timestamp": datetime.now(timezone.utc),
            "actor": "test",
            "reason": "test",
            "event_hash": "hash"
        }
        kwargs[field_name] = invalid_state
        
        with pytest.raises(ValueError, match="must be SignalState"):
            AuditEvent(**kwargs)


class TestDeterministicHashing:
    """Contract: Hash computation is deterministic."""
    
    def test_same_inputs_same_hash(self):
        """Identical inputs produce identical hash."""
        ts = datetime(2026, 1, 22, 12, 0, 0, tzinfo=timezone.utc)
        
        hash1 = compute_event_hash(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=ts,
            actor="system",
            reason="test",
            metadata={},
            previous_hash="GENESIS"
        )
        
        hash2 = compute_event_hash(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=ts,
            actor="system",
            reason="test",
            metadata={},
            previous_hash="GENESIS"
        )
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest
    
    @pytest.mark.parametrize("field,value1,value2", [
        ("signal_id", "test-123", "test-456"),
        ("actor", "system", "dispatcher"),
        ("prev_state", SignalState.PENDING, SignalState.VALIDATED),
        ("next_state", SignalState.VALIDATED, SignalState.ALLOCATED),
        ("previous_hash", "GENESIS", "different_hash"),
    ])
    def test_different_inputs_different_hash(self, field, value1, value2):
        """Different inputs produce different hashes."""
        ts = datetime.now(timezone.utc)
        
        base_kwargs = {
            "signal_id": "test-123",
            "prev_state": SignalState.PENDING,
            "next_state": SignalState.VALIDATED,
            "timestamp": ts,
            "actor": "system",
            "reason": "test",
            "metadata": {},
            "previous_hash": "GENESIS"
        }
        
        kwargs1 = {**base_kwargs, field: value1}
        kwargs2 = {**base_kwargs, field: value2}
        
        hash1 = compute_event_hash(**kwargs1)
        hash2 = compute_event_hash(**kwargs2)
        
        assert hash1 != hash2


class TestAppendOnlyLogger:
    """Contract: Logger is append-only, maintains hash chain."""
    
    def test_append_single_event(self):
        """Events are appended to log."""
        logger = SignalAuditLogger()
        
        event = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        assert logger.get_event_count() == 1
        assert event.signal_id == "test-123"
    
    def test_hash_chain_maintained(self):
        """Each event chains to previous hash."""
        logger = SignalAuditLogger()
        
        e1 = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="first"
        )
        
        e2 = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            actor="system",
            reason="second"
        )
        
        # Verify e2 hash depends on e1 hash
        expected_hash = compute_event_hash(
            signal_id=e2.signal_id,
            prev_state=e2.prev_state,
            next_state=e2.next_state,
            timestamp=e2.timestamp,
            actor=e2.actor,
            reason=e2.reason,
            metadata=e2.metadata,
            previous_hash=e1.event_hash
        )
        
        assert e2.event_hash == expected_hash
    
    def test_get_events_by_signal_id(self):
        """Filter events by signal_id."""
        logger = SignalAuditLogger()
        
        logger.append_event(
            signal_id="sig-1",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        logger.append_event(
            signal_id="sig-2",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        events = logger.get_events(signal_id="sig-1")
        assert len(events) == 1
        assert events[0].signal_id == "sig-1"


class TestChainVerification:
    """Contract: Verification detects tampering, raises only for invalid types."""
    
    def test_valid_chain_returns_true(self):
        """Valid chain verification succeeds."""
        logger = SignalAuditLogger()
        
        logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            actor="system",
            reason="test"
        )
        
        events = logger.get_events()
        assert verify_event_chain(events) is True
    
    def test_empty_chain_is_valid(self):
        """Empty chain is valid."""
        assert verify_event_chain([]) is True
    
    def test_tampered_event_returns_false(self):
        """Tampered event fails verification (returns False, does not raise)."""
        logger = SignalAuditLogger()
        
        event = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        # Create tampered event (different data, same hash)
        tampered = AuditEvent(
            signal_id="tampered-id",
            prev_state=event.prev_state,
            next_state=event.next_state,
            timestamp=event.timestamp,
            actor=event.actor,
            reason=event.reason,
            metadata=event.metadata,
            event_hash=event.event_hash
        )
        
        # Should return False, not raise
        assert verify_event_chain([tampered]) is False
    
    @pytest.mark.parametrize("invalid_input", [
        "not a list",
        123,
        None,
        {"events": []},
    ])
    def test_raises_type_error_for_invalid_input(self, invalid_input):
        """Raises TypeError for non-list input."""
        with pytest.raises(TypeError, match="events must be list"):
            verify_event_chain(invalid_input)
    
    def test_raises_value_error_for_non_audit_event(self):
        """Raises ValueError for non-AuditEvent in list."""
        logger = SignalAuditLogger()
        
        event = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        with pytest.raises(ValueError, match="is not AuditEvent"):
            verify_event_chain([event, "not an event"])
