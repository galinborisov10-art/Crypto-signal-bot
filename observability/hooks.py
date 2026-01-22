"""
observability/hooks.py

ESB v1.0 §3.5 - Observability hooks for signal lifecycle events.
Side-effect-only hooks that do NOT influence business logic.
"""

from typing import Optional
from datetime import datetime
from signal_state_machine import SignalState
from .metrics import MetricsCollector
from .structured_logger import StructuredLogger


class ObservabilityHooks:
    """
    ESB v1.0 §3.5 - Observability hooks for signal lifecycle.
    
    Provides side-effect-only hooks for metrics and logging.
    Zero behavioral impact on FSM, invariants, or audit logic.
    """
    
    def __init__(
        self,
        metrics: Optional[MetricsCollector] = None,
        logger: Optional[StructuredLogger] = None
    ):
        """
        Initialize observability hooks.
        
        Args:
            metrics: Metrics collector (optional)
            logger: Structured logger (optional)
        """
        self.metrics = metrics or MetricsCollector()
        self.logger = logger or StructuredLogger()
    
    def on_signal_created(self, signal_id: str) -> None:
        """
        Hook called when a signal is created.
        
        ESB v1.0 §3.5: Passive observation only.
        
        Args:
            signal_id: Unique signal identifier
        """
        self.metrics.increment_signals_created()
        self.metrics.increment_signals_in_state(SignalState.PENDING)
    
    def on_signal_rejected(self, signal_id: str, reason: str) -> None:
        """
        Hook called when a signal is rejected.
        
        Args:
            signal_id: Unique signal identifier
            reason: Rejection reason
        """
        self.metrics.increment_signals_rejected()
    
    def on_signal_expired(self, signal_id: str) -> None:
        """
        Hook called when a signal expires.
        
        Args:
            signal_id: Unique signal identifier
        """
        self.metrics.increment_signals_expired()
    
    def on_signal_cancelled(self, signal_id: str) -> None:
        """
        Hook called when a signal is cancelled.
        
        Args:
            signal_id: Unique signal identifier
        """
        self.metrics.increment_signals_cancelled()
    
    def on_state_transition(
        self,
        *,
        signal_id: str,
        from_state: SignalState,
        to_state: SignalState,
        actor: str,
        reason: str,
        timestamp: Optional[datetime] = None,
        transition_latency_ms: Optional[float] = None
    ) -> None:
        """
        Hook called on successful state transition.
        
        ESB v1.0 §3.5:
        - Emits metrics and structured logs
        - Zero behavioral impact
        - Fire-and-forget
        
        Args:
            signal_id: Unique signal identifier
            from_state: Source state
            to_state: Target state
            actor: Entity performing transition
            reason: Justification for transition
            timestamp: Event timestamp
            transition_latency_ms: Optional transition latency
        """
        # Update gauges
        self.metrics.decrement_signals_in_state(from_state)
        self.metrics.increment_signals_in_state(to_state)
        
        # Record latency if provided
        if transition_latency_ms is not None:
            self.metrics.record_state_transition_latency(
                from_state=from_state,
                to_state=to_state,
                latency_ms=transition_latency_ms
            )
        
        # Emit structured log
        self.logger.log_transition(
            signal_id=signal_id,
            from_state=from_state,
            to_state=to_state,
            actor=actor,
            reason=reason,
            timestamp=timestamp
        )
    
    def on_dispatch_acknowledged(
        self,
        signal_id: str,
        latency_ms: float
    ) -> None:
        """
        Hook called when dispatch is acknowledged.
        
        Args:
            signal_id: Unique signal identifier
            latency_ms: Dispatch-to-ack latency in milliseconds
        """
        self.metrics.record_dispatch_to_ack_latency(latency_ms)
