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

import pytest
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
    
    @pytest.mark.parametrize("state,expected_value", [
        (SignalState.PENDING, "pending"),
        (SignalState.VALIDATED, "validated"),
        (SignalState.ALLOCATED, "allocated"),
        (SignalState.EXECUTING, "executing"),
        (SignalState.ACTIVE, "active"),
        (SignalState.COMPLETED, "completed"),
        (SignalState.FAILED, "failed"),
        (SignalState.CANCELLED, "cancelled"),
    ])
    def test_enum_values(self, state, expected_value):
        """Verify all 8 mandatory states exist with correct values"""
        assert state.value == expected_value
    
    def test_enum_count(self):
        """Verify exactly 8 states are defined"""
        assert len(SignalState) == 8


class TestAllowedTransitions:
    """Test ALLOWED_TRANSITIONS table per ESB §3.2.2"""
    
    @pytest.mark.parametrize("state,expected_transitions", [
        (SignalState.PENDING, [SignalState.VALIDATED, SignalState.CANCELLED]),
        (SignalState.VALIDATED, [SignalState.ALLOCATED, SignalState.CANCELLED]),
        (SignalState.ALLOCATED, [SignalState.EXECUTING, SignalState.CANCELLED]),
        (SignalState.EXECUTING, [SignalState.ACTIVE, SignalState.FAILED]),
        (SignalState.ACTIVE, [SignalState.COMPLETED, SignalState.FAILED]),
        (SignalState.COMPLETED, []),
        (SignalState.FAILED, []),
        (SignalState.CANCELLED, []),
    ])
    def test_transition_table(self, state, expected_transitions):
        """Verify ALLOWED_TRANSITIONS table is correct for all states"""
        assert set(ALLOWED_TRANSITIONS[state]) == set(expected_transitions)


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
        with pytest.raises(AttributeError):
            fsm.state = SignalState.ACTIVE


class TestValidTransitions:
    """Test all valid state transitions per ESB §3.2.2"""
    
    @pytest.mark.parametrize("from_state,to_state", [
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
    ])
    def test_valid_transitions(self, from_state, to_state):
        """Test each valid transition succeeds and updates state"""
        fsm = SignalStateMachine(initial_state=from_state)
        fsm.transition(to_state)
        assert fsm.state == to_state


class TestInvalidTransitions:
    """Test invalid state transitions raise StateTransitionError per ESB §3.2.2"""
    
    @pytest.mark.parametrize("from_state,to_state", [
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
        # Terminal states cannot transition
        (SignalState.COMPLETED, SignalState.PENDING),
        (SignalState.FAILED, SignalState.PENDING),
        (SignalState.CANCELLED, SignalState.PENDING),
    ])
    def test_invalid_transitions(self, from_state, to_state):
        """Test each invalid transition raises StateTransitionError"""
        fsm = SignalStateMachine(initial_state=from_state)
        with pytest.raises(StateTransitionError):
            fsm.transition(to_state)


class TestStateImmutability:
    """Test state remains unchanged when invalid transition is attempted per ESB §3.2.2"""
    
    @pytest.mark.parametrize("from_state,invalid_to_state", [
        (SignalState.PENDING, SignalState.ALLOCATED),
        (SignalState.VALIDATED, SignalState.ACTIVE),
        (SignalState.ALLOCATED, SignalState.COMPLETED),
    ])
    def test_state_unchanged_on_error(self, from_state, invalid_to_state):
        """State must remain unchanged after StateTransitionError"""
        fsm = SignalStateMachine(initial_state=from_state)
        original_state = fsm.state
        
        with pytest.raises(StateTransitionError):
            fsm.transition(invalid_to_state)
        
        assert fsm.state == original_state


class TestTerminalStates:
    """Test terminal state behavior per ESB §3.2.2"""
    
    @pytest.mark.parametrize("terminal_state", [
        SignalState.COMPLETED,
        SignalState.FAILED,
        SignalState.CANCELLED,
    ])
    def test_terminal_states_no_transitions(self, terminal_state):
        """Terminal states have empty transition lists and cannot transition"""
        # Verify transition table is empty
        assert ALLOWED_TRANSITIONS[terminal_state] == []
        
        # Verify any transition attempt fails
        fsm = SignalStateMachine(initial_state=terminal_state)
        with pytest.raises(StateTransitionError):
            fsm.transition(SignalState.PENDING)


class TestErrorMessages:
    """Test error message format per ESB §3.2.2"""
    
    def test_error_message_format(self):
        """Error message should contain source and target state values"""
        fsm = SignalStateMachine(initial_state=SignalState.PENDING)
        
        with pytest.raises(StateTransitionError) as exc_info:
            fsm.transition(SignalState.ALLOCATED)
        
        error_msg = str(exc_info.value)
        assert "Invalid transition:" in error_msg
        assert "pending" in error_msg
        assert "allocated" in error_msg
        assert "->" in error_msg
