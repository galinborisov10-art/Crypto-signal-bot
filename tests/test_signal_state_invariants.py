"""
Unit tests for Signal State Invariants (ESB v1.0 §3.3)

This test suite validates:
- Global invariants (valid states, monotonic progression, immutability)
- Terminal state finality
- State-specific invariants (VALIDATED, ALLOCATED, EXECUTING)
- No side effects guarantee
- Deterministic behavior

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


class TestGlobalInvariants:
    """Test global invariants that apply to all states."""
    
    def test_valid_states_pass(self):
        """Valid SignalState enums should pass validation"""
        checker = SignalStateInvariantChecker()
        # Should not raise
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={}
        )
    
    def test_invalid_current_state_type_fails(self):
        """Invalid current_state type should raise StateInvariantError"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="Invalid current_state type"):
            checker.validate(
                current_state="pending",  # Wrong type - should be SignalState enum
                next_state=SignalState.VALIDATED,
                context={}
            )
    
    def test_invalid_next_state_type_fails(self):
        """Invalid next_state type should raise StateInvariantError"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="Invalid next_state type"):
            checker.validate(
                current_state=SignalState.PENDING,
                next_state="validated",  # Wrong type - should be SignalState enum
                context={}
            )
    
    def test_none_context_defaults_to_empty_dict(self):
        """None context should be treated as empty dict and not raise"""
        checker = SignalStateInvariantChecker()
        # Should not raise
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context=None
        )


class TestSignalIdImmutability:
    """Test signal_id immutability invariant."""
    
    def test_valid_signal_id_passes(self):
        """Valid string signal_id should pass"""
        checker = SignalStateInvariantChecker()
        # Should not raise
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={'signal_id': 'test-123'}
        )
    
    def test_invalid_signal_id_type_fails(self):
        """Non-string signal_id should raise StateInvariantError"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="signal_id must be string"):
            checker.validate(
                current_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                context={'signal_id': 123}  # Should be string
            )
    
    def test_missing_signal_id_passes(self):
        """Missing signal_id in context should not raise"""
        checker = SignalStateInvariantChecker()
        # Should not raise
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={}
        )


class TestMonotonicProgression:
    """Test that backward transitions are forbidden."""
    
    @pytest.mark.parametrize("current_state,next_state", [
        # Backward transitions
        (SignalState.VALIDATED, SignalState.PENDING),
        (SignalState.ALLOCATED, SignalState.PENDING),
        (SignalState.ALLOCATED, SignalState.VALIDATED),
        (SignalState.EXECUTING, SignalState.PENDING),
        (SignalState.EXECUTING, SignalState.VALIDATED),
        (SignalState.EXECUTING, SignalState.ALLOCATED),
        (SignalState.ACTIVE, SignalState.PENDING),
        (SignalState.ACTIVE, SignalState.VALIDATED),
        (SignalState.ACTIVE, SignalState.ALLOCATED),
        (SignalState.ACTIVE, SignalState.EXECUTING),
        # Self-transitions (also backward since index is same)
        (SignalState.PENDING, SignalState.PENDING),
        (SignalState.VALIDATED, SignalState.VALIDATED),
        (SignalState.ALLOCATED, SignalState.ALLOCATED),
        (SignalState.EXECUTING, SignalState.EXECUTING),
        (SignalState.ACTIVE, SignalState.ACTIVE),
    ])
    def test_backward_transition_fails(self, current_state, next_state):
        """Backward and self-transitions should raise StateInvariantError"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="Backward transition not allowed"):
            checker.validate(
                current_state=current_state,
                next_state=next_state,
                context={}
            )
    
    @pytest.mark.parametrize("current_state,next_state", [
        # Forward transitions
        (SignalState.PENDING, SignalState.VALIDATED),
        (SignalState.VALIDATED, SignalState.ALLOCATED),
        (SignalState.ALLOCATED, SignalState.EXECUTING),
        (SignalState.EXECUTING, SignalState.ACTIVE),
        (SignalState.ACTIVE, SignalState.COMPLETED),
    ])
    def test_forward_transition_passes(self, current_state, next_state):
        """Forward transitions should pass validation"""
        checker = SignalStateInvariantChecker()
        # Should not raise
        checker.validate(
            current_state=current_state,
            next_state=next_state,
            context={}
        )
    
    @pytest.mark.parametrize("current_state", [
        SignalState.PENDING,
        SignalState.VALIDATED,
        SignalState.ALLOCATED,
    ])
    def test_cancelled_allowed_from_non_terminal(self, current_state):
        """CANCELLED transitions allowed from any non-terminal state"""
        checker = SignalStateInvariantChecker()
        # Should not raise
        checker.validate(
            current_state=current_state,
            next_state=SignalState.CANCELLED,
            context={}
        )
    
    @pytest.mark.parametrize("current_state", [
        SignalState.EXECUTING,
        SignalState.ACTIVE,
    ])
    def test_failed_allowed_from_executing_and_active(self, current_state):
        """FAILED transitions allowed from EXECUTING and ACTIVE"""
        checker = SignalStateInvariantChecker()
        # Should not raise
        checker.validate(
            current_state=current_state,
            next_state=SignalState.FAILED,
            context={}
        )
    
    @pytest.mark.parametrize("current_state", [
        SignalState.PENDING,
        SignalState.VALIDATED,
        SignalState.ALLOCATED,
    ])
    def test_failed_not_allowed_from_early_states(self, current_state):
        """FAILED transitions not allowed from early states"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="Backward transition not allowed"):
            checker.validate(
                current_state=current_state,
                next_state=SignalState.FAILED,
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
    
    @pytest.mark.parametrize("terminal_state,next_state", [
        (SignalState.COMPLETED, SignalState.PENDING),
        (SignalState.COMPLETED, SignalState.VALIDATED),
        (SignalState.COMPLETED, SignalState.ACTIVE),
        (SignalState.FAILED, SignalState.PENDING),
        (SignalState.FAILED, SignalState.EXECUTING),
        (SignalState.CANCELLED, SignalState.PENDING),
        (SignalState.CANCELLED, SignalState.ACTIVE),
    ])
    def test_terminal_states_block_all_transitions(self, terminal_state, next_state):
        """Terminal states should block transitions to any state"""
        checker = SignalStateInvariantChecker()
        with pytest.raises(StateInvariantError, match="Terminal state.*cannot transition"):
            checker.validate(
                current_state=terminal_state,
                next_state=next_state,
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
    
    def test_terminal_reached_false_allows_transition(self):
        """Context flag terminal_reached=False should allow transitions"""
        checker = SignalStateInvariantChecker()
        # Should not raise
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={'terminal_reached': False}
        )


class TestStateSpecificInvariants:
    """Test invariants for specific states."""
    
    def test_validated_requires_phase2_passed_true(self):
        """VALIDATED state requires phase2_passed=True when provided"""
        checker = SignalStateInvariantChecker()
        
        # Should fail with phase2_passed=False
        with pytest.raises(StateInvariantError, match="phase2_passed=False"):
            checker.validate(
                current_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                context={'phase2_passed': False}
            )
    
    def test_validated_passes_with_phase2_passed_true(self):
        """VALIDATED state should pass with phase2_passed=True"""
        checker = SignalStateInvariantChecker()
        
        # Should pass with phase2_passed=True
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={'phase2_passed': True}
        )
    
    def test_validated_passes_without_phase2_passed_context(self):
        """VALIDATED state should pass when phase2_passed not in context"""
        checker = SignalStateInvariantChecker()
        
        # Should pass when phase2_passed not provided
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={}
        )
    
    def test_allocated_requires_execution_allowed_true(self):
        """ALLOCATED state requires execution_allowed=True when provided"""
        checker = SignalStateInvariantChecker()
        
        # Should fail with execution_allowed=False
        with pytest.raises(StateInvariantError, match="execution_allowed=False"):
            checker.validate(
                current_state=SignalState.VALIDATED,
                next_state=SignalState.ALLOCATED,
                context={'execution_allowed': False}
            )
    
    def test_allocated_passes_with_execution_allowed_true(self):
        """ALLOCATED state should pass with execution_allowed=True"""
        checker = SignalStateInvariantChecker()
        
        # Should pass with execution_allowed=True
        checker.validate(
            current_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            context={'execution_allowed': True}
        )
    
    def test_allocated_passes_without_execution_allowed_context(self):
        """ALLOCATED state should pass when execution_allowed not in context"""
        checker = SignalStateInvariantChecker()
        
        # Should pass when execution_allowed not provided
        checker.validate(
            current_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            context={}
        )
    
    def test_executing_requires_dispatch_timestamp_not_none(self):
        """EXECUTING state requires dispatch_timestamp to be not None when provided"""
        checker = SignalStateInvariantChecker()
        
        # Should fail with dispatch_timestamp=None
        with pytest.raises(StateInvariantError, match="dispatch_timestamp is None"):
            checker.validate(
                current_state=SignalState.ALLOCATED,
                next_state=SignalState.EXECUTING,
                context={'dispatch_timestamp': None}
            )
    
    def test_executing_passes_with_valid_dispatch_timestamp(self):
        """EXECUTING state should pass with valid dispatch_timestamp"""
        checker = SignalStateInvariantChecker()
        
        # Should pass with valid datetime
        checker.validate(
            current_state=SignalState.ALLOCATED,
            next_state=SignalState.EXECUTING,
            context={'dispatch_timestamp': datetime.now()}
        )
    
    def test_executing_passes_with_any_truthy_dispatch_timestamp(self):
        """EXECUTING state should pass with any truthy dispatch_timestamp value"""
        checker = SignalStateInvariantChecker()
        
        # Should pass with string timestamp
        checker.validate(
            current_state=SignalState.ALLOCATED,
            next_state=SignalState.EXECUTING,
            context={'dispatch_timestamp': '2026-01-22T10:00:00Z'}
        )
        
        # Should pass with integer timestamp
        checker.validate(
            current_state=SignalState.ALLOCATED,
            next_state=SignalState.EXECUTING,
            context={'dispatch_timestamp': 1234567890}
        )
    
    def test_executing_passes_without_dispatch_timestamp_context(self):
        """EXECUTING state should pass when dispatch_timestamp not in context"""
        checker = SignalStateInvariantChecker()
        
        # Should pass when dispatch_timestamp not provided
        checker.validate(
            current_state=SignalState.ALLOCATED,
            next_state=SignalState.EXECUTING,
            context={}
        )
    
    def test_non_target_states_ignore_their_invariants(self):
        """State-specific invariants should only apply to their target state"""
        checker = SignalStateInvariantChecker()
        
        # VALIDATED-specific invariant should not affect transition to ALLOCATED
        checker.validate(
            current_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            context={'phase2_passed': False}  # This is for VALIDATED, not ALLOCATED
        )
        
        # ALLOCATED-specific invariant should not affect transition to EXECUTING
        checker.validate(
            current_state=SignalState.ALLOCATED,
            next_state=SignalState.EXECUTING,
            context={'execution_allowed': False}  # This is for ALLOCATED, not EXECUTING
        )


class TestNoSideEffects:
    """Verify invariant checks have no side effects."""
    
    def test_context_unchanged_after_validation(self):
        """Context dict should remain unchanged after validation"""
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
    
    def test_multiple_validations_same_checker_instance(self):
        """Multiple validations should not affect each other"""
        checker = SignalStateInvariantChecker()
        
        # First validation
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={'phase2_passed': True}
        )
        
        # Second validation with different context
        checker.validate(
            current_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            context={'execution_allowed': True}
        )
        
        # Third validation should not be affected by previous calls
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={}
        )


class TestDeterministicBehavior:
    """Verify invariant checks are deterministic."""
    
    def test_same_inputs_produce_same_result_success(self):
        """Same inputs should always produce same result (no error)"""
        checker = SignalStateInvariantChecker()
        context = {'phase2_passed': True, 'signal_id': 'test-456'}
        
        # Run validation multiple times
        for _ in range(5):
            # Should not raise
            checker.validate(
                current_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                context=context.copy()
            )
    
    def test_same_inputs_produce_same_result_failure(self):
        """Same invalid inputs should always produce same error"""
        checker = SignalStateInvariantChecker()
        context = {'phase2_passed': False}
        
        # Run validation multiple times
        for _ in range(5):
            with pytest.raises(StateInvariantError, match="phase2_passed=False"):
                checker.validate(
                    current_state=SignalState.PENDING,
                    next_state=SignalState.VALIDATED,
                    context=context.copy()
                )
    
    def test_order_of_checks_consistent(self):
        """Error messages should be consistent indicating check order"""
        checker = SignalStateInvariantChecker()
        
        # Invalid state type should be caught before other checks
        with pytest.raises(StateInvariantError, match="Invalid.*type"):
            checker.validate(
                current_state="pending",
                next_state=SignalState.VALIDATED,
                context={'phase2_passed': False}
            )
        
        # Terminal state should be caught before state-specific checks
        with pytest.raises(StateInvariantError, match="Terminal state.*cannot transition"):
            checker.validate(
                current_state=SignalState.COMPLETED,
                next_state=SignalState.VALIDATED,
                context={'phase2_passed': False}
            )


class TestComplexScenarios:
    """Test complex scenarios with multiple context fields."""
    
    def test_multiple_valid_context_fields(self):
        """Multiple valid context fields should all pass"""
        checker = SignalStateInvariantChecker()
        
        context = {
            'signal_id': 'sig-789',
            'phase2_passed': True,
            'execution_allowed': True,
            'dispatch_timestamp': datetime.now(),
            'terminal_reached': False
        }
        
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context=context
        )
    
    def test_one_invalid_field_fails_validation(self):
        """One invalid field should cause validation to fail"""
        checker = SignalStateInvariantChecker()
        
        context = {
            'signal_id': 'sig-789',
            'phase2_passed': False,  # Invalid
            'execution_allowed': True,
        }
        
        with pytest.raises(StateInvariantError, match="phase2_passed=False"):
            checker.validate(
                current_state=SignalState.PENDING,
                next_state=SignalState.VALIDATED,
                context=context
            )
    
    def test_empty_context_allows_all_basic_transitions(self):
        """Empty context should allow transitions that don't require context"""
        checker = SignalStateInvariantChecker()
        
        # All these should pass with empty context
        checker.validate(
            current_state=SignalState.PENDING,
            next_state=SignalState.VALIDATED,
            context={}
        )
        
        checker.validate(
            current_state=SignalState.VALIDATED,
            next_state=SignalState.ALLOCATED,
            context={}
        )
        
        checker.validate(
            current_state=SignalState.ALLOCATED,
            next_state=SignalState.EXECUTING,
            context={}
        )
