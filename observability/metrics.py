"""
observability/metrics.py

ESB v1.0 §3.5 - Metrics emission for signal lifecycle events.
Passive, read-only observability with zero behavioral impact.
"""

from typing import Dict, Optional
from signal_state_machine import SignalState


class MetricsCollector:
    """
    ESB v1.0 §3.5 - Passive metrics collector.
    
    Emits counters, gauges, and histograms for signal lifecycle events.
    Does NOT influence any business logic or state transitions.
    """
    
    def __init__(self):
        """Initialize in-memory metrics storage."""
        # Counters
        self._signals_created_total = 0
        self._signals_rejected_total = 0
        self._signals_expired_total = 0
        self._signals_cancelled_total = 0
        
        # Gauges (per-state signal counts)
        self._signals_in_state: Dict[SignalState, int] = {
            state: 0 for state in SignalState
        }
        
        # Histograms (store samples for later aggregation)
        self._state_transition_latency_samples = []
        self._dispatch_to_ack_latency_samples = []
    
    def increment_signals_created(self) -> None:
        """Increment signals_created_total counter."""
        self._signals_created_total += 1
    
    def increment_signals_rejected(self) -> None:
        """Increment signals_rejected_total counter."""
        self._signals_rejected_total += 1
    
    def increment_signals_expired(self) -> None:
        """Increment signals_expired_total counter."""
        self._signals_expired_total += 1
    
    def increment_signals_cancelled(self) -> None:
        """Increment signals_cancelled_total counter."""
        self._signals_cancelled_total += 1
    
    def set_signals_in_state(self, state: SignalState, count: int) -> None:
        """
        Set gauge value for signals_in_state{state}.
        
        Args:
            state: Signal state
            count: Current count of signals in this state
        """
        self._signals_in_state[state] = count
    
    def increment_signals_in_state(self, state: SignalState) -> None:
        """Increment gauge for signals entering a state."""
        self._signals_in_state[state] += 1
    
    def decrement_signals_in_state(self, state: SignalState) -> None:
        """Decrement gauge for signals leaving a state."""
        self._signals_in_state[state] = max(0, self._signals_in_state[state] - 1)
    
    def record_state_transition_latency(
        self,
        from_state: SignalState,
        to_state: SignalState,
        latency_ms: float
    ) -> None:
        """
        Record state transition latency histogram sample.
        
        Args:
            from_state: Source state
            to_state: Target state
            latency_ms: Transition latency in milliseconds
        """
        self._state_transition_latency_samples.append({
            'from': from_state.value,
            'to': to_state.value,
            'latency_ms': latency_ms
        })
    
    def record_dispatch_to_ack_latency(self, latency_ms: float) -> None:
        """
        Record dispatch-to-acknowledgment latency histogram sample.
        
        Args:
            latency_ms: Latency in milliseconds
        """
        self._dispatch_to_ack_latency_samples.append(latency_ms)
    
    def get_metrics_snapshot(self) -> Dict:
        """
        Get current metrics snapshot (for testing/debugging only).
        
        IMPORTANT: This method is for observability only.
        Business logic MUST NOT read these values.
        
        Returns:
            Dict with current metric values
        """
        return {
            'counters': {
                'signals_created_total': self._signals_created_total,
                'signals_rejected_total': self._signals_rejected_total,
                'signals_expired_total': self._signals_expired_total,
                'signals_cancelled_total': self._signals_cancelled_total,
            },
            'gauges': {
                f'signals_in_state_{state.value}': count
                for state, count in self._signals_in_state.items()
            },
            'histograms': {
                'state_transition_latency_samples': len(self._state_transition_latency_samples),
                'dispatch_to_ack_latency_samples': len(self._dispatch_to_ack_latency_samples),
            }
        }
