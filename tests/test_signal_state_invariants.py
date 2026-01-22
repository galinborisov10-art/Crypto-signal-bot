"""
Unit tests for Signal State Invariants (ESB v1.0 §3.3)

This test suite validates contract enforcement only, not FSM logic.
Tests prove that invariants are checked correctly without duplicating
FSM transition validation.

Author: ESB v1.0 Implementation
Date: 2026-01-22
"""

import pytest
import sys
import os
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_state_machine import SignalState
from signal_state_invariants import (
    SignalStateInvariantChecker,
    StateInvariantError
)


class TestTypeValidation:
    """Test that only valid SignalState types are accepted."""
    
    @pytest.mark.parametrize("current_state,next_state", [
        (SignalState.PENDING, SignalState.VALIDATED),
        (SignalState.VALIDATED, SignalState.ALLOCATED),
        (SignalState.ALLOCATED, SignalState.EXECUTING),
    ])
    def test_valid_state_types_pass(self, current_state, next_state):
        """Valid SignalState enums should pass type validation"""
        checker = SignalStateInvariantChecker()
        # Should not raise
        checker.validate(
            current_state=current_state,
            next_state=next_state,
            context={}
        )
    
    @pytest.mark.parametrize("invalid_current", [
        "pending",
        None,
        123,
        {"state": "pending"}
    ])
    def test_invalid_current_state_type_fails(self, invalid_current):
        """Invalid current_state type should raise StateInvariantError"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="Invalid current_state type"):
            checker.validate(
                current_state=invalid_current,
                next_state=SignalState.VALIDATED,
                context={}
            )
    
    @pytest.mark.parametrize("invalid_next", [
        "validated",
        None,
        456,
        ["validated"]
    ])
    def test_invalid_next_state_type_fails(self, invalid_next):
        """Invalid next_state type should raise StateInvariantError"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="Invalid next_state type"):
            checker.validate(
                current_state=SignalState.PENDING,
                next_state=invalid_next,
                context={}
            )


class TestTerminalStateFinality:
    """Test that terminal states cannot transition."""
    
    @pytest.mark.parametrize("terminal_state", [
        SignalState.COMPLETED,
        SignalState.FAILED,
        SignalState.CANCELLED,
    ])
    def test_terminal_state_cannot_transition(self, terminal_state):
        """Terminal states should raise error on any transition attempt"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="Terminal state.*cannot transition"):
            checker.validate(
                current_state=terminal_state,
                next_state=SignalState.PENDING,
                context={}
            )
    
    def test_terminal_reached_flag_prevents_transition(self):
        """Context flag terminal_reached=True should prevent transitions"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="Cannot transition after terminal state reached"):
            checker.validate(
                current_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                context={'terminal_reached': True}
            )


class TestValidatedStateInvariant:
    """Test VALIDATED state contract: phase2_passed=True required."""
    
    def test_validated_passes_with_phase2_passed_true(self):
        """VALIDATED transition should pass with phase2_passed=True"""
        checker = SignalStateInvariantChecker()
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={'phase2_passed': True}
        )
    
    def test_validated_fails_with_phase2_passed_false(self):
        """VALIDATED transition should fail with phase2_passed=False"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="phase2_passed=False"):
            checker.validate(
                current_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                context={'phase2_passed': False}
            )
    
    def test_validated_passes_without_context(self):
        """VALIDATED transition should pass when phase2_passed not in context"""
        checker = SignalStateInvariantChecker()
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={}
        )


class TestAllocatedStateInvariant:
    """Test ALLOCATED state contract: execution_allowed=True required."""
    
    def test_allocated_passes_with_execution_allowed_true(self):
        """ALLOCATED transition should pass with execution_allowed=True"""
        checker = SignalStateInvariantChecker()
        checker.validate(
            current_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            context={'execution_allowed': True}
        )
    
    def test_allocated_fails_with_execution_allowed_false(self):
        """ALLOCATED transition should fail with execution_allowed=False"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="execution_allowed=False"):
            checker.validate(
                current_state=SignalState.VALIDATED,
                next_state=SignalState.ALLOCATED,
                context={'execution_allowed': False}
            )
    
    def test_allocated_passes_without_context(self):
        """ALLOCATED transition should pass when execution_allowed not in context"""
        checker = SignalStateInvariantChecker()
        checker.validate(
            current_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            context={}
        )


class TestExecutingStateInvariant:
    """Test EXECUTING state contract: dispatch_timestamp not None required."""
    
    def test_executing_passes_with_valid_dispatch_timestamp(self):
        """EXECUTING transition should pass with valid dispatch_timestamp"""
        checker = SignalStateInvariantChecker()
        checker.validate(
            current_state=SignalState.ALLOCATED,
            next_state=SignalState.EXECUTING,
            context={'dispatch_timestamp': datetime.now()}
        )
    
    def test_executing_fails_with_none_dispatch_timestamp(self):
        """EXECUTING transition should fail with dispatch_timestamp=None"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="dispatch_timestamp is None"):
            checker.validate(
                current_state=SignalState.ALLOCATED,
                next_state=SignalState.EXECUTING,
                context={'dispatch_timestamp': None}
            )
    
    def test_executing_passes_without_context(self):
        """EXECUTING transition should pass when dispatch_timestamp not in context"""
        checker = SignalStateInvariantChecker()
        checker.validate(
            current_state=SignalState.ALLOCATED,
            next_state=SignalState.EXECUTING,
            context={}
        )


class TestContextImmutability:
    """Test that invariant checks have no side effects."""
    
    def test_context_unchanged_after_validation(self):
        """Context dict should remain unchanged after successful validation"""
        checker = SignalStateInvariantChecker()
        original_context = {
            'phase2_passed': True,
            'signal_id': 'test-123',
            'execution_allowed': True
        }
        context_copy = original_context.copy()
        
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context=original_context
        )
        
        assert original_context == context_copy, "Context was mutated"
    
    def test_context_unchanged_after_validation_failure(self):
        """Context dict should remain unchanged even when validation fails"""
        checker = SignalStateInvariantChecker()
        original_context = {'phase2_passed': False}
        context_copy = original_context.copy()
        
        try:
            checker.validate(
                current_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                context=original_context
            )
        except StateInvariantError:
            pass
        
        assert original_context == context_copy, "Context was mutated on error"


class TestSignalIdImmutability:
    """Test signal_id type validation."""
    
    def test_valid_signal_id_passes(self):
        """Valid string signal_id should pass"""
        checker = SignalStateInvariantChecker()
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={'signal_id': 'test-123'}
        )
    
    @pytest.mark.parametrize("invalid_id", [123, None, [], {}])
    def test_invalid_signal_id_type_fails(self, invalid_id):
        """Non-string signal_id should raise StateInvariantError"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="signal_id must be string"):
            checker.validate(
                current_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                context={'signal_id': invalid_id}
            )
