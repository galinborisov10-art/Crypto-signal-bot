"""
Unit tests for Signal State Machine (ESB v1.0 §3.1–§3.2)

This test suite validates:
- All valid state transitions
- All invalid state transitions  
- Terminal state behavior
- Error message format
- State immutability on error

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

from signal_state_machine import (
    SignalState,
    SignalStateMachine,
    StateTransitionError,
    ALLOWED_TRANSITIONS
)


class TestSignalStateEnum:
    """Test SignalState enum definitions per ESB §3.1"""
    
    def test_enum_values(self):
        """Verify all 8 mandatory states exist with correct values"""
        assert SignalState.PENDING.value == "pending"
        assert SignalState.VALIDATED.value == "validated"
        assert SignalState.ALLOCATED.value == "allocated"
        assert SignalState.EXECUTING.value == "executing"
        assert SignalState.ACTIVE.value == "active"
        assert SignalState.COMPLETED.value == "completed"
        assert SignalState.FAILED.value == "failed"
        assert SignalState.CANCELLED.value == "cancelled"
    
    def test_enum_count(self):
        """Verify exactly 8 states are defined"""
        assert len(SignalState) == 8


class TestAllowedTransitions:
    """Test ALLOWED_TRANSITIONS table per ESB §3.2.2"""
    
    def test_pending_transitions(self):
        """PENDING -> VALIDATED or CANCELLED only"""
        assert set(ALLOWED_TRANSITIONS[SignalState.PENDING]) == {
            SignalState.VALIDATED,
            SignalState.CANCELLED
        }
    
    def test_validated_transitions(self):
        """VALIDATED -> ALLOCATED or CANCELLED only"""
        assert set(ALLOWED_TRANSITIONS[SignalState.VALIDATED]) == {
            SignalState.ALLOCATED,
            SignalState.CANCELLED
        }
    
    def test_allocated_transitions(self):
        """ALLOCATED -> EXECUTING or CANCELLED only"""
        assert set(ALLOWED_TRANSITIONS[SignalState.ALLOCATED]) == {
            SignalState.EXECUTING,
            SignalState.CANCELLED
        }
    
    def test_executing_transitions(self):
        """EXECUTING -> ACTIVE or FAILED only"""
        assert set(ALLOWED_TRANSITIONS[SignalState.EXECUTING]) == {
            SignalState.ACTIVE,
            SignalState.FAILED
        }
    
    def test_active_transitions(self):
        """ACTIVE -> COMPLETED or FAILED only"""
        assert set(ALLOWED_TRANSITIONS[SignalState.ACTIVE]) == {
            SignalState.COMPLETED,
            SignalState.FAILED
        }
    
    def test_completed_no_transitions(self):
        """COMPLETED is terminal - no outgoing transitions"""
        assert ALLOWED_TRANSITIONS[SignalState.COMPLETED] == []
    
    def test_failed_no_transitions(self):
        """FAILED is terminal - no outgoing transitions"""
        assert ALLOWED_TRANSITIONS[SignalState.FAILED] == []
    
    def test_cancelled_no_transitions(self):
        """CANCELLED is terminal - no outgoing transitions"""
        assert ALLOWED_TRANSITIONS[SignalState.CANCELLED] == []


class TestSignalStateMachineInit:
    """Test SignalStateMachine initialization"""
    
    def test_default_initial_state(self):
        """Default initial state should be PENDING"""
        fsm = SignalStateMachine()
        assert fsm.state == SignalState.PENDING
    
    def test_custom_initial_state(self):
        """Should accept custom initial state"""
        fsm = SignalStateMachine(initial_state=SignalState.VALIDATED)
        assert fsm.state == SignalState.VALIDATED
    
    def test_state_property_read_only(self):
        """State property should be read-only"""
        fsm = SignalStateMachine()
        try:
            fsm.state = SignalState.ACTIVE
            assert False, "Should not allow direct state assignment"
        except AttributeError:
            pass  # Expected behavior


class TestValidTransitions:
    """Test all valid state transitions per ESB §3.2.2"""
    
    # Parameterized test data for all valid transitions
    valid_transitions = [
        # From PENDING
        (SignalState.PENDING, SignalState.VALIDATED),
        (SignalState.PENDING, SignalState.CANCELLED),
        # From VALIDATED
        (SignalState.VALIDATED, SignalState.ALLOCATED),
        (SignalState.VALIDATED, SignalState.CANCELLED),
        # From ALLOCATED
        (SignalState.ALLOCATED, SignalState.EXECUTING),
        (SignalState.ALLOCATED, SignalState.CANCELLED),
        # From EXECUTING
        (SignalState.EXECUTING, SignalState.ACTIVE),
        (SignalState.EXECUTING, SignalState.FAILED),
        # From ACTIVE
        (SignalState.ACTIVE, SignalState.COMPLETED),
        (SignalState.ACTIVE, SignalState.FAILED),
    ]
    
    def test_valid_transitions_parameterized(self):
        """Test each valid transition succeeds and updates state"""
        for from_state, to_state in self.valid_transitions:
            fsm = SignalStateMachine(initial_state=from_state)
            fsm.transition(to_state)
            assert fsm.state == to_state, \
                f"Failed transition {from_state.value} -> {to_state.value}"
    
    def test_pending_to_validated(self):
        """PENDING -> VALIDATED should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.PENDING)
        fsm.transition(SignalState.VALIDATED)
        assert fsm.state == SignalState.VALIDATED
    
    def test_pending_to_cancelled(self):
        """PENDING -> CANCELLED should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.PENDING)
        fsm.transition(SignalState.CANCELLED)
        assert fsm.state == SignalState.CANCELLED
    
    def test_validated_to_allocated(self):
        """VALIDATED -> ALLOCATED should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.VALIDATED)
        fsm.transition(SignalState.ALLOCATED)
        assert fsm.state == SignalState.ALLOCATED
    
    def test_validated_to_cancelled(self):
        """VALIDATED -> CANCELLED should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.VALIDATED)
        fsm.transition(SignalState.CANCELLED)
        assert fsm.state == SignalState.CANCELLED
    
    def test_allocated_to_executing(self):
        """ALLOCATED -> EXECUTING should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.ALLOCATED)
        fsm.transition(SignalState.EXECUTING)
        assert fsm.state == SignalState.EXECUTING
    
    def test_allocated_to_cancelled(self):
        """ALLOCATED -> CANCELLED should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.ALLOCATED)
        fsm.transition(SignalState.CANCELLED)
        assert fsm.state == SignalState.CANCELLED
    
    def test_executing_to_active(self):
        """EXECUTING -> ACTIVE should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.EXECUTING)
        fsm.transition(SignalState.ACTIVE)
        assert fsm.state == SignalState.ACTIVE
    
    def test_executing_to_failed(self):
        """EXECUTING -> FAILED should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.EXECUTING)
        fsm.transition(SignalState.FAILED)
        assert fsm.state == SignalState.FAILED
    
    def test_active_to_completed(self):
        """ACTIVE -> COMPLETED should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.ACTIVE)
        fsm.transition(SignalState.COMPLETED)
        assert fsm.state == SignalState.COMPLETED
    
    def test_active_to_failed(self):
        """ACTIVE -> FAILED should succeed"""
        fsm = SignalStateMachine(initial_state=SignalState.ACTIVE)
        fsm.transition(SignalState.FAILED)
        assert fsm.state == SignalState.FAILED


class TestInvalidTransitions:
    """Test invalid state transitions raise StateTransitionError per ESB §3.2.2"""
    
    # Sample invalid transitions for comprehensive coverage
    invalid_transitions = [
        # From PENDING (cannot skip to ALLOCATED, EXECUTING, ACTIVE, COMPLETED, FAILED)
        (SignalState.PENDING, SignalState.PENDING),
        (SignalState.PENDING, SignalState.ALLOCATED),
        (SignalState.PENDING, SignalState.EXECUTING),
        (SignalState.PENDING, SignalState.ACTIVE),
        (SignalState.PENDING, SignalState.COMPLETED),
        (SignalState.PENDING, SignalState.FAILED),
        # From VALIDATED (cannot skip or go backward)
        (SignalState.VALIDATED, SignalState.PENDING),
        (SignalState.VALIDATED, SignalState.VALIDATED),
        (SignalState.VALIDATED, SignalState.EXECUTING),
        (SignalState.VALIDATED, SignalState.ACTIVE),
        (SignalState.VALIDATED, SignalState.COMPLETED),
        (SignalState.VALIDATED, SignalState.FAILED),
        # From ALLOCATED (cannot skip or go backward)
        (SignalState.ALLOCATED, SignalState.PENDING),
        (SignalState.ALLOCATED, SignalState.VALIDATED),
        (SignalState.ALLOCATED, SignalState.ALLOCATED),
        (SignalState.ALLOCATED, SignalState.ACTIVE),
        (SignalState.ALLOCATED, SignalState.COMPLETED),
        (SignalState.ALLOCATED, SignalState.FAILED),
        # From EXECUTING (cannot go backward or skip)
        (SignalState.EXECUTING, SignalState.PENDING),
        (SignalState.EXECUTING, SignalState.VALIDATED),
        (SignalState.EXECUTING, SignalState.ALLOCATED),
        (SignalState.EXECUTING, SignalState.EXECUTING),
        (SignalState.EXECUTING, SignalState.COMPLETED),
        (SignalState.EXECUTING, SignalState.CANCELLED),
        # From ACTIVE (cannot go backward or skip)
        (SignalState.ACTIVE, SignalState.PENDING),
        (SignalState.ACTIVE, SignalState.VALIDATED),
        (SignalState.ACTIVE, SignalState.ALLOCATED),
        (SignalState.ACTIVE, SignalState.EXECUTING),
        (SignalState.ACTIVE, SignalState.ACTIVE),
        (SignalState.ACTIVE, SignalState.CANCELLED),
        # Terminal states (tested separately but included for completeness)
        (SignalState.COMPLETED, SignalState.PENDING),
        (SignalState.FAILED, SignalState.PENDING),
        (SignalState.CANCELLED, SignalState.PENDING),
    ]
    
    def test_invalid_transitions_parameterized(self):
        """Test each invalid transition raises StateTransitionError"""
        for from_state, to_state in self.invalid_transitions:
            fsm = SignalStateMachine(initial_state=from_state)
            try:
                fsm.transition(to_state)
                assert False, \
                    f"Expected StateTransitionError for {from_state.value} -> {to_state.value}"
            except StateTransitionError:
                pass  # Expected behavior
    
    def test_pending_to_allocated_invalid(self):
        """PENDING -> ALLOCATED should raise StateTransitionError"""
        fsm = SignalStateMachine(initial_state=SignalState.PENDING)
        try:
            fsm.transition(SignalState.ALLOCATED)
            assert False, "Should raise StateTransitionError"
        except StateTransitionError:
            pass
    
    def test_validated_to_executing_invalid(self):
        """VALIDATED -> EXECUTING should raise StateTransitionError"""
        fsm = SignalStateMachine(initial_state=SignalState.VALIDATED)
        try:
            fsm.transition(SignalState.EXECUTING)
            assert False, "Should raise StateTransitionError"
        except StateTransitionError:
            pass
    
    def test_allocated_to_active_invalid(self):
        """ALLOCATED -> ACTIVE should raise StateTransitionError"""
        fsm = SignalStateMachine(initial_state=SignalState.ALLOCATED)
        try:
            fsm.transition(SignalState.ACTIVE)
            assert False, "Should raise StateTransitionError"
        except StateTransitionError:
            pass
    
    def test_executing_to_completed_invalid(self):
        """EXECUTING -> COMPLETED should raise StateTransitionError"""
        fsm = SignalStateMachine(initial_state=SignalState.EXECUTING)
        try:
            fsm.transition(SignalState.COMPLETED)
            assert False, "Should raise StateTransitionError"
        except StateTransitionError:
            pass


class TestStateImmutabilityOnError:
    """Test state remains unchanged when invalid transition is attempted"""
    
    def test_state_unchanged_on_invalid_transition(self):
        """State must remain unchanged after StateTransitionError"""
        fsm = SignalStateMachine(initial_state=SignalState.PENDING)
        original_state = fsm.state
        
        try:
            fsm.transition(SignalState.ALLOCATED)  # Invalid
        except StateTransitionError:
            pass
        
        assert fsm.state == original_state, "State changed after invalid transition"
    
    def test_state_unchanged_from_validated(self):
        """State unchanged when invalid transition attempted from VALIDATED"""
        fsm = SignalStateMachine(initial_state=SignalState.VALIDATED)
        
        try:
            fsm.transition(SignalState.ACTIVE)  # Invalid
        except StateTransitionError:
            pass
        
        assert fsm.state == SignalState.VALIDATED
    
    def test_state_unchanged_from_allocated(self):
        """State unchanged when invalid transition attempted from ALLOCATED"""
        fsm = SignalStateMachine(initial_state=SignalState.ALLOCATED)
        
        try:
            fsm.transition(SignalState.COMPLETED)  # Invalid
        except StateTransitionError:
            pass
        
        assert fsm.state == SignalState.ALLOCATED


class TestTerminalStates:
    """Test terminal state behavior per ESB §3.2.2"""
    
    terminal_states = [
        SignalState.COMPLETED,
        SignalState.FAILED,
        SignalState.CANCELLED
    ]
    
    all_states = [
        SignalState.PENDING,
        SignalState.VALIDATED,
        SignalState.ALLOCATED,
        SignalState.EXECUTING,
        SignalState.ACTIVE,
        SignalState.COMPLETED,
        SignalState.FAILED,
        SignalState.CANCELLED
    ]
    
    def test_terminal_states_have_no_transitions(self):
        """Terminal states have empty transition lists"""
        for state in self.terminal_states:
            assert ALLOWED_TRANSITIONS[state] == [], \
                f"{state.value} should have no allowed transitions"
    
    def test_completed_terminal(self):
        """COMPLETED state cannot transition to any state"""
        fsm = SignalStateMachine(initial_state=SignalState.COMPLETED)
        
        for target_state in self.all_states:
            try:
                fsm.transition(target_state)
                assert False, f"COMPLETED -> {target_state.value} should fail"
            except StateTransitionError:
                pass  # Expected
    
    def test_failed_terminal(self):
        """FAILED state cannot transition to any state"""
        fsm = SignalStateMachine(initial_state=SignalState.FAILED)
        
        for target_state in self.all_states:
            try:
                fsm.transition(target_state)
                assert False, f"FAILED -> {target_state.value} should fail"
            except StateTransitionError:
                pass  # Expected
    
    def test_cancelled_terminal(self):
        """CANCELLED state cannot transition to any state"""
        fsm = SignalStateMachine(initial_state=SignalState.CANCELLED)
        
        for target_state in self.all_states:
            try:
                fsm.transition(target_state)
                assert False, f"CANCELLED -> {target_state.value} should fail"
            except StateTransitionError:
                pass  # Expected


class TestErrorMessages:
    """Test error message format per ESB §3.2.2"""
    
    def test_error_message_contains_states(self):
        """Error message should contain source and target state names"""
        fsm = SignalStateMachine(initial_state=SignalState.PENDING)
        
        try:
            fsm.transition(SignalState.ALLOCATED)
        except StateTransitionError as e:
            error_msg = str(e)
            assert "pending" in error_msg, "Error should contain source state"
            assert "allocated" in error_msg, "Error should contain target state"
    
    def test_error_message_format(self):
        """Error message should follow expected format"""
        fsm = SignalStateMachine(initial_state=SignalState.VALIDATED)
        
        try:
            fsm.transition(SignalState.ACTIVE)
        except StateTransitionError as e:
            error_msg = str(e)
            assert "Invalid transition:" in error_msg
            assert "validated" in error_msg
            assert "active" in error_msg
            assert "->" in error_msg
    
    def test_error_message_terminal_state(self):
        """Error message for terminal state transitions"""
        fsm = SignalStateMachine(initial_state=SignalState.COMPLETED)
        
        try:
            fsm.transition(SignalState.PENDING)
        except StateTransitionError as e:
            error_msg = str(e)
            assert "completed" in error_msg
            assert "pending" in error_msg


class TestMultipleTransitions:
    """Test sequences of valid transitions"""
    
    def test_happy_path_to_completed(self):
        """Test complete happy path: PENDING -> ... -> COMPLETED"""
        fsm = SignalStateMachine()
        
        assert fsm.state == SignalState.PENDING
        
        fsm.transition(SignalState.VALIDATED)
        assert fsm.state == SignalState.VALIDATED
        
        fsm.transition(SignalState.ALLOCATED)
        assert fsm.state == SignalState.ALLOCATED
        
        fsm.transition(SignalState.EXECUTING)
        assert fsm.state == SignalState.EXECUTING
        
        fsm.transition(SignalState.ACTIVE)
        assert fsm.state == SignalState.ACTIVE
        
        fsm.transition(SignalState.COMPLETED)
        assert fsm.state == SignalState.COMPLETED
    
    def test_early_cancellation(self):
        """Test early cancellation: PENDING -> VALIDATED -> CANCELLED"""
        fsm = SignalStateMachine()
        
        fsm.transition(SignalState.VALIDATED)
        fsm.transition(SignalState.CANCELLED)
        
        assert fsm.state == SignalState.CANCELLED
    
    def test_execution_failure(self):
        """Test execution failure: ... -> EXECUTING -> FAILED"""
        fsm = SignalStateMachine(initial_state=SignalState.EXECUTING)
        
        fsm.transition(SignalState.FAILED)
        assert fsm.state == SignalState.FAILED
    
    def test_active_failure(self):
        """Test active position failure: ACTIVE -> FAILED"""
        fsm = SignalStateMachine(initial_state=SignalState.ACTIVE)
        
        fsm.transition(SignalState.FAILED)
        assert fsm.state == SignalState.FAILED


# Run tests if executed directly
if __name__ == "__main__":
    if pytest:
        pytest.main([__file__, "-v"])
    else:
        print("pytest not available, running basic tests...")
        # Simple test runner if pytest not available
        import unittest
        loader = unittest.TestLoader()
        suite = loader.loadTestsFromModule(sys.modules[__name__])
        runner = unittest.TextTestRunner(verbosity=2)
        runner.run(suite)
