"""
Signal State Invariants for ESB v1.0 Phase 3.3

This module implements invariant enforcement and state contracts as a meta-layer
on top of the Signal State Machine per ESB v1.0 §3.3. It provides pure,
side-effect-free validation checks that enforce state contracts.

Author: ESB v1.0 Implementation
Date: 2026-01-22
"""

from typing import Any, Dict, Optional
from signal_state_machine import SignalState


class StateInvariantError(Exception):
    """
    Raised when an invariant is violated.
    
    Per ESB v1.0 §3.3, invariants must be enforced before transitions
    and violations must result in explicit errors.
    """
    pass


class SignalStateInvariantChecker:
    """
    ESB v1.0 §3.3 - Signal State Invariants
    
    Validates state contracts and invariants before transitions.
    All checks are pure functions with no side effects.
    
    This checker enforces:
    - Global invariants (apply to all states)
    - State-specific invariants (apply to specific target states)
    - Monotonic progression (no backward transitions)
    - Terminal state finality (no transitions from terminal states)
    """
    
    def validate(
        self,
        *,
        current_state: SignalState,
        next_state: SignalState,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Validates all applicable invariants for a state transition.
        
        Per ESB §3.3:
        - Invariants must hold before AND after transitions
        - Violations raise StateInvariantError
        - No state mutations allowed
        
        Args:
            current_state: Current signal state
            next_state: Target signal state
            context: Read-only context dict with optional fields:
                - signal_id: str (immutable)
                - phase2_passed: bool
                - execution_allowed: bool
                - dispatch_timestamp: datetime
                - terminal_reached: bool
                
        Raises:
            StateInvariantError: If any invariant is violated
        """
        if context is None:
            context = {}
        
        # Global invariants (order matters: check terminal states before monotonic progression)
        self._check_valid_states(current_state, next_state)
        self._check_terminal_state_finality(current_state, context)
        self._check_monotonic_progression(current_state, next_state)
        self._check_signal_id_immutability(context)
        
        # State-specific invariants
        self._check_validated_invariants(next_state, context)
        self._check_allocated_invariants(next_state, context)
        self._check_executing_invariants(next_state, context)
    
    def _check_valid_states(
        self, 
        current_state: SignalState, 
        next_state: SignalState
    ) -> None:
        """
        Verify both states are valid SignalState enum values.
        
        Per ESB §3.3: State must be a valid SignalState.
        """
        if not isinstance(current_state, SignalState):
            raise StateInvariantError(
                f"Invalid current_state type: {type(current_state)}"
            )
        if not isinstance(next_state, SignalState):
            raise StateInvariantError(
                f"Invalid next_state type: {type(next_state)}"
            )
    
    def _check_monotonic_progression(
        self,
        current_state: SignalState,
        next_state: SignalState
    ) -> None:
        """
        ESB §3.3: No backward transitions allowed.
        States must progress forward in the lifecycle.
        
        Monotonic progression means states can only move forward,
        with special cases for CANCELLED (from any non-terminal) and
        FAILED (from EXECUTING or ACTIVE).
        """
        # Define state ordering (lower index = earlier in lifecycle)
        state_order = [
            SignalState.PENDING,
            SignalState.VALIDATED,
            SignalState.ALLOCATED,
            SignalState.EXECUTING,
            SignalState.ACTIVE,
            # Terminal states (no ordering between them)
            SignalState.COMPLETED,
            SignalState.FAILED,
            SignalState.CANCELLED
        ]
        
        # Allow transitions to CANCELLED from any non-terminal state
        if next_state == SignalState.CANCELLED:
            return
        
        # Allow transitions to FAILED from EXECUTING or ACTIVE
        if next_state == SignalState.FAILED:
            if current_state in [SignalState.EXECUTING, SignalState.ACTIVE]:
                return
            # FAILED from other states is a backward transition
            raise StateInvariantError(
                f"Backward transition not allowed: "
                f"{current_state.value} -> {next_state.value}"
            )
        
        # For other transitions, enforce monotonic progression
        try:
            current_idx = state_order.index(current_state)
            next_idx = state_order.index(next_state)
            
            if next_idx <= current_idx:
                raise StateInvariantError(
                    f"Backward transition not allowed: "
                    f"{current_state.value} -> {next_state.value}"
                )
        except ValueError as e:
            raise StateInvariantError(f"State ordering error: {e}")
    
    def _check_signal_id_immutability(self, context: Dict[str, Any]) -> None:
        """
        ESB §3.3: signal_id must be immutable once set.
        
        This check verifies that if signal_id is provided in context,
        it is a valid string type. The actual immutability tracking
        would be handled by the caller.
        """
        if 'signal_id' in context:
            if not isinstance(context['signal_id'], str):
                raise StateInvariantError(
                    f"signal_id must be string, got {type(context['signal_id'])}"
                )
    
    def _check_terminal_state_finality(
        self,
        current_state: SignalState,
        context: Dict[str, Any]
    ) -> None:
        """
        ESB §3.3: Terminal states cannot transition further.
        
        Once a signal reaches a terminal state (COMPLETED, FAILED, CANCELLED),
        no further transitions are allowed.
        """
        terminal_states = [
            SignalState.COMPLETED,
            SignalState.FAILED,
            SignalState.CANCELLED
        ]
        
        if current_state in terminal_states:
            raise StateInvariantError(
                f"Terminal state {current_state.value} cannot transition"
            )
        
        # Check context flag if provided
        if context.get('terminal_reached', False):
            raise StateInvariantError(
                "Cannot transition after terminal state reached"
            )
    
    def _check_validated_invariants(
        self,
        next_state: SignalState,
        context: Dict[str, Any]
    ) -> None:
        """
        ESB §3.3: VALIDATED state requires phase2_passed=True.
        
        A signal can only transition to VALIDATED if it has successfully
        passed Phase 2 validation checks.
        """
        if next_state == SignalState.VALIDATED:
            if 'phase2_passed' in context:
                if not context['phase2_passed']:
                    raise StateInvariantError(
                        "Cannot transition to VALIDATED: phase2_passed=False"
                    )
    
    def _check_allocated_invariants(
        self,
        next_state: SignalState,
        context: Dict[str, Any]
    ) -> None:
        """
        ESB §3.3: ALLOCATED state requires execution_allowed=True.
        
        A signal can only transition to ALLOCATED if execution is allowed,
        meaning resources can be reserved for execution.
        """
        if next_state == SignalState.ALLOCATED:
            if 'execution_allowed' in context:
                if not context['execution_allowed']:
                    raise StateInvariantError(
                        "Cannot transition to ALLOCATED: execution_allowed=False"
                    )
    
    def _check_executing_invariants(
        self,
        next_state: SignalState,
        context: Dict[str, Any]
    ) -> None:
        """
        ESB §3.3: EXECUTING state requires dispatch_timestamp.
        
        A signal can only transition to EXECUTING if a dispatch timestamp
        has been set, indicating when execution was initiated.
        """
        if next_state == SignalState.EXECUTING:
            if 'dispatch_timestamp' in context:
                if context['dispatch_timestamp'] is None:
                    raise StateInvariantError(
                        "Cannot transition to EXECUTING: "
                        "dispatch_timestamp is None"
                    )
