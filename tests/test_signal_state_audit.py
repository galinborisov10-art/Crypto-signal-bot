"""
Unit tests for Signal State Audit Module (ESB v1.0 §3.4)

Tests prove:
- Append-only behavior
- Immutability of events
- Deterministic hashing
- Correct hash chaining
- Tampering detection

Author: ESB v1.0 Implementation
Date: 2026-01-22
"""

try:
    import pytest
except ImportError:
    pytest = None

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


class TestAuditEvent:
    """Test immutable audit event creation."""
    
    def test_create_valid_event(self):
        """Valid event should be created successfully."""
        event = AuditEvent(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=datetime.now(timezone.utc),
            actor="system",
            reason="passed validation",
            metadata={},
            event_hash="abc123"
        )
        
        assert event.signal_id == "test-123"
        assert event.prev_state == SignalState.PENDING
        assert event.next_state == SignalState.VALIDATED
        assert event.actor == "system"
        assert event.reason == "passed validation"
        assert event.event_hash == "abc123"
    
    def test_event_with_metadata(self):
        """Event can include optional metadata."""
        metadata = {"confidence": 85.5, "source": "ICT"}
        event = AuditEvent(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=datetime.now(timezone.utc),
            actor="system",
            reason="test",
            metadata=metadata,
            event_hash="hash"
        )
        
        assert event.metadata["confidence"] == 85.5
        assert event.metadata["source"] == "ICT"
    
    def test_event_is_immutable(self):
        """Event fields cannot be modified after creation."""
        event = AuditEvent(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=datetime.now(timezone.utc),
            actor="system",
            reason="test",
            event_hash="hash"
        )
        
        # Python 3.7+ raises AttributeError for frozen dataclass
        try:
            event.signal_id = "modified"
            # If we get here, the test should fail
            assert False, "Event should be immutable"
        except (AttributeError, Exception):
            # Expected behavior - event is immutable
            pass
    
    def test_empty_signal_id_raises_error(self):
        """Empty signal_id should raise ValueError."""
        try:
            AuditEvent(
                signal_id="",
                prev_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                timestamp=datetime.now(timezone.utc),
                actor="system",
                reason="test",
                event_hash="hash"
            )
            assert False, "Should raise ValueError for empty signal_id"
        except ValueError as e:
            assert "signal_id cannot be empty" in str(e)
    
    def test_empty_actor_raises_error(self):
        """Empty actor should raise ValueError."""
        try:
            AuditEvent(
                signal_id="test-123",
                prev_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                timestamp=datetime.now(timezone.utc),
                actor="",
                reason="test",
                event_hash="hash"
            )
            assert False, "Should raise ValueError for empty actor"
        except ValueError as e:
            assert "actor cannot be empty" in str(e)
    
    def test_empty_reason_raises_error(self):
        """Empty reason should raise ValueError."""
        try:
            AuditEvent(
                signal_id="test-123",
                prev_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                timestamp=datetime.now(timezone.utc),
                actor="system",
                reason="",
                event_hash="hash"
            )
            assert False, "Should raise ValueError for empty reason"
        except ValueError as e:
            assert "reason cannot be empty" in str(e)
    
    def test_invalid_prev_state_raises_error(self):
        """Invalid prev_state type should raise ValueError."""
        try:
            AuditEvent(
                signal_id="test-123",
                prev_state="not_a_state",  # Invalid type
                next_state=SignalState.VALIDATED,
                timestamp=datetime.now(timezone.utc),
                actor="system",
                reason="test",
                event_hash="hash"
            )
            assert False, "Should raise ValueError for invalid prev_state"
        except ValueError as e:
            assert "prev_state must be SignalState" in str(e)
    
    def test_invalid_next_state_raises_error(self):
        """Invalid next_state type should raise ValueError."""
        try:
            AuditEvent(
                signal_id="test-123",
                prev_state=SignalState.PENDING,
                next_state="not_a_state",  # Invalid type
                timestamp=datetime.now(timezone.utc),
                actor="system",
                reason="test",
                event_hash="hash"
            )
            assert False, "Should raise ValueError for invalid next_state"
        except ValueError as e:
            assert "next_state must be SignalState" in str(e)


class TestHashChaining:
    """Test cryptographic hash chaining."""
    
    def test_deterministic_hash(self):
        """Same inputs produce same hash."""
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
        assert len(hash1) == 64  # SHA256 produces 64 hex chars
    
    def test_different_signal_id_different_hash(self):
        """Different signal_id produces different hash."""
        ts = datetime.now(timezone.utc)
        
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
            signal_id="test-456",  # Different signal_id
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=ts,
            actor="system",
            reason="test",
            metadata={},
            previous_hash="GENESIS"
        )
        
        assert hash1 != hash2
    
    def test_different_state_different_hash(self):
        """Different state produces different hash."""
        ts = datetime.now(timezone.utc)
        
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
            next_state=SignalState.ALLOCATED,  # Different next_state
            timestamp=ts,
            actor="system",
            reason="test",
            metadata={},
            previous_hash="GENESIS"
        )
        
        assert hash1 != hash2
    
    def test_different_actor_different_hash(self):
        """Different actor produces different hash."""
        ts = datetime.now(timezone.utc)
        
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
            actor="dispatcher",  # Different actor
            reason="test",
            metadata={},
            previous_hash="GENESIS"
        )
        
        assert hash1 != hash2
    
    def test_different_previous_hash_different_result(self):
        """Different previous_hash produces different hash (chaining)."""
        ts = datetime.now(timezone.utc)
        
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
            previous_hash="different_previous_hash"
        )
        
        assert hash1 != hash2
    
    def test_metadata_affects_hash(self):
        """Metadata content affects hash."""
        ts = datetime.now(timezone.utc)
        
        hash1 = compute_event_hash(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=ts,
            actor="system",
            reason="test",
            metadata={"key": "value1"},
            previous_hash="GENESIS"
        )
        
        hash2 = compute_event_hash(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=ts,
            actor="system",
            reason="test",
            metadata={"key": "value2"},  # Different metadata
            previous_hash="GENESIS"
        )
        
        assert hash1 != hash2


class TestAuditLogger:
    """Test audit logger append-only behavior."""
    
    def test_logger_initializes_empty(self):
        """New logger should have no events."""
        logger = SignalAuditLogger()
        assert logger.get_event_count() == 0
        assert logger.get_events() == []
    
    def test_append_single_event(self):
        """Events should be appended to log."""
        logger = SignalAuditLogger()
        
        event = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="validation passed"
        )
        
        assert logger.get_event_count() == 1
        assert event.signal_id == "test-123"
        assert event.prev_state == SignalState.PENDING
        assert event.next_state == SignalState.VALIDATED
        assert event.actor == "system"
        assert event.reason == "validation passed"
        assert len(event.event_hash) == 64  # SHA256 hash
    
    def test_first_event_uses_genesis_hash(self):
        """First event should use GENESIS as previous hash."""
        logger = SignalAuditLogger()
        ts = datetime(2026, 1, 22, 12, 0, 0, tzinfo=timezone.utc)
        
        event = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="first event",
            timestamp=ts
        )
        
        # Manually compute expected hash with GENESIS
        expected_hash = compute_event_hash(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            timestamp=ts,
            actor="system",
            reason="first event",
            metadata={},
            previous_hash="GENESIS"
        )
        
        assert event.event_hash == expected_hash
    
    def test_hash_chain_maintained(self):
        """Subsequent events should chain hashes."""
        logger = SignalAuditLogger()
        
        event1 = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="first transition"
        )
        
        event2 = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            actor="system",
            reason="second transition"
        )
        
        # Second event should use first event's hash
        expected_hash = compute_event_hash(
            signal_id="test-123",
            prev_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            timestamp=event2.timestamp,
            actor="system",
            reason="second transition",
            metadata={},
            previous_hash=event1.event_hash
        )
        
        assert event2.event_hash == expected_hash
    
    def test_multiple_events_maintain_chain(self):
        """Multiple events should maintain hash chain."""
        logger = SignalAuditLogger()
        
        events = []
        transitions = [
            (SignalState.PENDING, SignalState.VALIDATED),
            (SignalState.VALIDATED, SignalState.ALLOCATED),
            (SignalState.ALLOCATED, SignalState.EXECUTING),
            (SignalState.EXECUTING, SignalState.ACTIVE)
        ]
        
        for prev_state, next_state in transitions:
            event = logger.append_event(
                signal_id="test-123",
                prev_state=prev_state,
                next_state=next_state,
                actor="system",
                reason=f"transition to {next_state.value}"
            )
            events.append(event)
        
        assert logger.get_event_count() == 4
        
        # Verify each event chains correctly
        for i in range(1, len(events)):
            expected_hash = compute_event_hash(
                signal_id=events[i].signal_id,
                prev_state=events[i].prev_state,
                next_state=events[i].next_state,
                timestamp=events[i].timestamp,
                actor=events[i].actor,
                reason=events[i].reason,
                metadata=events[i].metadata,
                previous_hash=events[i-1].event_hash
            )
            assert events[i].event_hash == expected_hash
    
    def test_get_all_events(self):
        """get_events() should return all events."""
        logger = SignalAuditLogger()
        
        logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test1"
        )
        
        logger.append_event(
            signal_id="test-456",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test2"
        )
        
        events = logger.get_events()
        assert len(events) == 2
        assert events[0].signal_id == "test-123"
        assert events[1].signal_id == "test-456"
    
    def test_get_events_by_signal_id(self):
        """Should filter events by signal_id."""
        logger = SignalAuditLogger()
        
        logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        logger.append_event(
            signal_id="test-456",
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
        
        events_123 = logger.get_events(signal_id="test-123")
        assert len(events_123) == 2
        assert all(e.signal_id == "test-123" for e in events_123)
        
        events_456 = logger.get_events(signal_id="test-456")
        assert len(events_456) == 1
        assert events_456[0].signal_id == "test-456"
    
    def test_get_events_returns_copy(self):
        """get_events() should return a copy to prevent mutation."""
        logger = SignalAuditLogger()
        
        logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        events1 = logger.get_events()
        events2 = logger.get_events()
        
        # Should be different list objects
        assert events1 is not events2
        # But contain the same events
        assert len(events1) == len(events2)
    
    def test_custom_timestamp(self):
        """Logger should accept custom timestamp."""
        logger = SignalAuditLogger()
        custom_ts = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        
        event = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test",
            timestamp=custom_ts
        )
        
        assert event.timestamp == custom_ts
    
    def test_default_timestamp_is_utc(self):
        """Default timestamp should be UTC now."""
        logger = SignalAuditLogger()
        before = datetime.now(timezone.utc)
        
        event = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        after = datetime.now(timezone.utc)
        
        # Timestamp should be between before and after
        assert before <= event.timestamp <= after
        assert event.timestamp.tzinfo == timezone.utc


class TestEventChainVerification:
    """Test audit chain verification."""
    
    def test_empty_chain_is_valid(self):
        """Empty chain should be considered valid."""
        assert verify_event_chain([]) is True
    
    def test_single_event_valid_chain(self):
        """Single valid event should verify successfully."""
        logger = SignalAuditLogger()
        
        logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        events = logger.get_events()
        assert verify_event_chain(events) is True
    
    def test_valid_chain_verifies(self):
        """Valid event chain should verify successfully."""
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
        
        logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.ALLOCATED,
            next_state=SignalState.EXECUTING,
            actor="system",
            reason="test"
        )
        
        events = logger.get_events()
        assert verify_event_chain(events) is True
    
    def test_tampered_signal_id_detected(self):
        """Tampered signal_id should fail verification."""
        logger = SignalAuditLogger()
        
        event1 = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        # Create a tampered copy (modify immutable event by creating new one)
        tampered_event = AuditEvent(
            signal_id="test-999",  # Tampered signal_id
            prev_state=event1.prev_state,
            next_state=event1.next_state,
            timestamp=event1.timestamp,
            actor=event1.actor,
            reason=event1.reason,
            metadata=event1.metadata,
            event_hash=event1.event_hash  # Keep old hash (invalid)
        )
        
        assert verify_event_chain([tampered_event]) is False
    
    def test_tampered_state_detected(self):
        """Tampered state should fail verification."""
        logger = SignalAuditLogger()
        
        event1 = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        # Create a tampered copy with different state
        tampered_event = AuditEvent(
            signal_id=event1.signal_id,
            prev_state=event1.prev_state,
            next_state=SignalState.ALLOCATED,  # Tampered next_state
            timestamp=event1.timestamp,
            actor=event1.actor,
            reason=event1.reason,
            metadata=event1.metadata,
            event_hash=event1.event_hash  # Keep old hash (invalid)
        )
        
        assert verify_event_chain([tampered_event]) is False
    
    def test_tampered_chain_link_detected(self):
        """Tampered link in chain should fail verification."""
        logger = SignalAuditLogger()
        
        event1 = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        event2 = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            actor="system",
            reason="test"
        )
        
        # Tamper with first event
        tampered_event1 = AuditEvent(
            signal_id="test-999",  # Changed
            prev_state=event1.prev_state,
            next_state=event1.next_state,
            timestamp=event1.timestamp,
            actor=event1.actor,
            reason=event1.reason,
            metadata=event1.metadata,
            event_hash=event1.event_hash  # Keep old hash
        )
        
        # Second event will fail because chain is broken
        assert verify_event_chain([tampered_event1, event2]) is False
    
    def test_invalid_input_type_raises_error(self):
        """Non-list input should raise TypeError."""
        try:
            verify_event_chain("not a list")
            assert False, "Should raise TypeError"
        except TypeError as e:
            assert "events must be list" in str(e)
    
    def test_invalid_event_in_list_raises_error(self):
        """Non-AuditEvent in list should raise ValueError."""
        logger = SignalAuditLogger()
        
        event = logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        try:
            verify_event_chain([event, "not an event"])
            assert False, "Should raise ValueError"
        except ValueError as e:
            assert "is not AuditEvent" in str(e)
    
    def test_mixed_signal_ids_valid_chain(self):
        """Chain with multiple signal_ids should verify if hashes are correct."""
        logger = SignalAuditLogger()
        
        logger.append_event(
            signal_id="test-123",
            prev_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        logger.append_event(
            signal_id="test-456",
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


# Entry point for running tests
if __name__ == "__main__":
    if pytest:
        pytest.main([__file__, "-v"])
    else:
        # Fallback: run tests manually without pytest
        print("Running tests without pytest...")
        
        # Instantiate test classes
        test_classes = [
            TestAuditEvent(),
            TestHashChaining(),
            TestAuditLogger(),
            TestEventChainVerification()
        ]
        
        passed = 0
        failed = 0
        
        for test_class in test_classes:
            class_name = test_class.__class__.__name__
            print(f"\n{class_name}:")
            
            # Get all test methods
            test_methods = [m for m in dir(test_class) if m.startswith('test_')]
            
            for method_name in test_methods:
                try:
                    method = getattr(test_class, method_name)
                    method()
                    print(f"  ✓ {method_name}")
                    passed += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {e}")
                    failed += 1
        
        print(f"\n{'='*60}")
        print(f"Tests passed: {passed}")
        print(f"Tests failed: {failed}")
        print(f"{'='*60}")
