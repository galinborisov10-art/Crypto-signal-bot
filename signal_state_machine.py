"""
Signal State Machine for ESB v1.0 Phase 3

This module implements a finite state machine for signal lifecycle management
per ESB v1.0 §3.1–§3.2. It provides state definitions, transition rules, and
enforcement logic without business logic, logging, or metrics.

Author: ESB v1.0 Implementation
Date: 2026-01-22
"""

from enum import Enum


class SignalState(Enum):
    """
    ESB v1.0 §3.1 - Signal Lifecycle States
    
    Defines the 8 mandatory states for signal lifecycle management.
    Each state represents a distinct phase in the signal processing pipeline.
    """
    
    PENDING = "pending"        # ESB §3.1: equivalent to CREATED, initial state
    VALIDATED = "validated"    # ESB §3.1: signal passed validation checks
    ALLOCATED = "allocated"    # ESB §3.1: capital/resources allocated
    EXECUTING = "executing"    # ESB §3.1: execution in progress
    ACTIVE = "active"          # ESB §3.1: position is active/live
    COMPLETED = "completed"    # ESB §3.1: terminal state - successful completion
    FAILED = "failed"          # ESB §3.1: terminal state - execution failed
    CANCELLED = "cancelled"    # ESB §3.1: terminal state - signal cancelled


# ESB v1.0 §3.2.2 - Explicit Allowed Transitions
ALLOWED_TRANSITIONS = {
    SignalState.PENDING:    [SignalState.VALIDATED, SignalState.CANCELLED],
    SignalState.VALIDATED:  [SignalState.ALLOCATED, SignalState.CANCELLED],
    SignalState.ALLOCATED:  [SignalState.EXECUTING, SignalState.CANCELLED],
    SignalState.EXECUTING:  [SignalState.ACTIVE, SignalState.FAILED],
    SignalState.ACTIVE:     [SignalState.COMPLETED, SignalState.FAILED],
    SignalState.COMPLETED:  [],  # terminal state - no outgoing transitions
    SignalState.FAILED:     [],  # terminal state - no outgoing transitions
    SignalState.CANCELLED:  []   # terminal state - no outgoing transitions
}


class StateTransitionError(Exception):
    """
    Raised on invalid signal state transitions.
    
    Per ESB v1.0 §3.2.2, invalid transitions must raise an error
    and leave the state machine unchanged.
    """
    pass


class SignalStateMachine:
    """
    ESB v1.0 §3.2 - State Transition Logic
    
    Implements a finite state machine for signal lifecycle management.
    Enforces allowed transitions per ESB v1.0 §3.2.2 without side effects,
    logging, metrics, or business logic.
    
    The state machine guarantees:
    - Only allowed transitions succeed
    - Invalid transitions raise StateTransitionError
    - State remains unchanged on error
    - No implicit state changes
    """
    
    def __init__(self, initial_state: SignalState = SignalState.PENDING):
        """
        Initialize state machine with a starting state.
        
        Args:
            initial_state: The initial state for the machine.
                          Defaults to SignalState.PENDING per ESB §3.1.
        """
        self._state = initial_state
    
    @property
    def state(self) -> SignalState:
        """
        Read-only access to current state.
        
        Returns:
            The current state of the signal.
        """
        return self._state
    
    def transition(self, to_state: SignalState) -> None:
        """
        Attempt state transition.
        
        Per ESB §3.2.2:
        - Invalid transitions raise StateTransitionError
        - State MUST remain unchanged on error
        - No side effects occur during transition
        
        Args:
            to_state: Target state to transition to.
            
        Raises:
            StateTransitionError: If transition is not allowed per
                                 ALLOWED_TRANSITIONS table.
        """
        if to_state not in ALLOWED_TRANSITIONS[self._state]:
            raise StateTransitionError(
                f"Invalid transition: {self._state.value} -> {to_state.value}"
            )
        self._state = to_state
