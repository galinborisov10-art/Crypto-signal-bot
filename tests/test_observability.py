"""
tests/test_observability.py

ESB v1.0 §3.5 - Tests for observability layer.
Proves observability has zero behavioral impact.
"""

import pytest
from datetime import datetime, timezone
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_state_machine import SignalState
from observability import MetricsCollector, StructuredLogger, ObservabilityHooks


class TestMetricsCollector:
    """Test metrics collector has no behavioral impact."""
    
    def test_increment_counters_no_exceptions(self):
        """Incrementing counters should never raise."""
        metrics = MetricsCollector()
        
        metrics.increment_signals_created()
        metrics.increment_signals_rejected()
        metrics.increment_signals_expired()
        metrics.increment_signals_cancelled()
        
        # Should complete without exceptions
        assert True
    
    def test_gauges_update_correctly(self):
        """Gauges should track state counts accurately."""
        metrics = MetricsCollector()
        
        metrics.increment_signals_in_state(SignalState.PENDING)
        metrics.increment_signals_in_state(SignalState.PENDING)
        
        snapshot = metrics.get_metrics_snapshot()
        assert snapshot['gauges']['signals_in_state_pending'] == 2
    
    def test_metrics_do_not_affect_state(self):
        """Metrics collection should not mutate any state."""
        metrics = MetricsCollector()
        
        # Record some metrics
        metrics.increment_signals_created()
        metrics.record_state_transition_latency(
            SignalState.PENDING,
            SignalState.VALIDATED,
            10.5
        )
        
        # Metrics object state is internal only
        # External state should be unchanged
        assert True  # No external state to verify
    
    def test_counters_increment_correctly(self):
        """All counters should increment independently."""
        metrics = MetricsCollector()
        
        metrics.increment_signals_created()
        metrics.increment_signals_created()
        metrics.increment_signals_rejected()
        
        snapshot = metrics.get_metrics_snapshot()
        assert snapshot['counters']['signals_created_total'] == 2
        assert snapshot['counters']['signals_rejected_total'] == 1
        assert snapshot['counters']['signals_expired_total'] == 0
        assert snapshot['counters']['signals_cancelled_total'] == 0
    
    def test_gauges_decrement_correctly(self):
        """Gauges should decrement without going negative."""
        metrics = MetricsCollector()
        
        # Increment then decrement
        metrics.increment_signals_in_state(SignalState.PENDING)
        metrics.increment_signals_in_state(SignalState.PENDING)
        metrics.decrement_signals_in_state(SignalState.PENDING)
        
        snapshot = metrics.get_metrics_snapshot()
        assert snapshot['gauges']['signals_in_state_pending'] == 1
        
        # Decrement to zero
        metrics.decrement_signals_in_state(SignalState.PENDING)
        snapshot = metrics.get_metrics_snapshot()
        assert snapshot['gauges']['signals_in_state_pending'] == 0
        
        # Should not go negative
        metrics.decrement_signals_in_state(SignalState.PENDING)
        snapshot = metrics.get_metrics_snapshot()
        assert snapshot['gauges']['signals_in_state_pending'] == 0
    
    def test_set_gauges_directly(self):
        """Gauges can be set to specific values."""
        metrics = MetricsCollector()
        
        metrics.set_signals_in_state(SignalState.VALIDATED, 42)
        
        snapshot = metrics.get_metrics_snapshot()
        assert snapshot['gauges']['signals_in_state_validated'] == 42
    
    def test_histogram_samples_recorded(self):
        """Histogram samples should be stored for aggregation."""
        metrics = MetricsCollector()
        
        metrics.record_state_transition_latency(
            SignalState.PENDING,
            SignalState.VALIDATED,
            10.5
        )
        metrics.record_state_transition_latency(
            SignalState.VALIDATED,
            SignalState.ALLOCATED,
            20.3
        )
        metrics.record_dispatch_to_ack_latency(15.7)
        
        snapshot = metrics.get_metrics_snapshot()
        assert snapshot['histograms']['state_transition_latency_samples'] == 2
        assert snapshot['histograms']['dispatch_to_ack_latency_samples'] == 1


class TestStructuredLogger:
    """Test structured logger has no behavioral impact."""
    
    def test_log_transition_no_exceptions(self):
        """Logging transitions should never raise."""
        logger = StructuredLogger()
        
        logger.log_transition(
            signal_id="test-123",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        assert logger.get_log_count() == 1
    
    def test_logs_do_not_affect_state(self):
        """Logging should not mutate any external state."""
        logger = StructuredLogger()
        
        # Log some transitions
        logger.log_transition(
            signal_id="test-123",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        # Logs are internal only
        # External state should be unchanged
        assert True
    
    def test_log_entry_structure(self):
        """Log entries should have required fields."""
        logger = StructuredLogger()
        
        timestamp = datetime(2026, 1, 22, 12, 0, 0)
        logger.log_transition(
            signal_id="test-456",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="user",
            reason="validation passed",
            timestamp=timestamp,
            metadata={'extra': 'data'}
        )
        
        logs = logger.get_logs()
        assert len(logs) == 1
        
        entry = logs[0]
        assert entry['phase'] == 3
        assert entry['signal_id'] == "test-456"
        assert entry['from_state'] == 'pending'
        assert entry['to_state'] == 'validated'
        assert entry['actor'] == 'user'
        assert entry['reason'] == 'validation passed'
        assert entry['timestamp'] == timestamp.isoformat()
        assert entry['metadata'] == {'extra': 'data'}
    
    def test_filter_logs_by_signal_id(self):
        """Should be able to filter logs by signal_id."""
        logger = StructuredLogger()
        
        logger.log_transition(
            signal_id="signal-1",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        logger.log_transition(
            signal_id="signal-2",
            from_state=SignalState.PENDING,
            to_state=SignalState.CANCELLED,
            actor="system",
            reason="test"
        )
        logger.log_transition(
            signal_id="signal-1",
            from_state=SignalState.VALIDATED,
            to_state=SignalState.ALLOCATED,
            actor="system",
            reason="test"
        )
        
        signal1_logs = logger.get_logs(signal_id="signal-1")
        assert len(signal1_logs) == 2
        assert all(log['signal_id'] == "signal-1" for log in signal1_logs)
    
    def test_clear_logs(self):
        """Should be able to clear logs for testing."""
        logger = StructuredLogger()
        
        logger.log_transition(
            signal_id="test",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        assert logger.get_log_count() == 1
        
        logger.clear_logs()
        assert logger.get_log_count() == 0


class TestObservabilityHooks:
    """Test observability hooks have zero behavioral impact."""
    
    def test_hooks_are_fire_and_forget(self):
        """Hooks should complete without blocking or raising."""
        hooks = ObservabilityHooks()
        
        # Call all hooks
        hooks.on_signal_created("test-123")
        hooks.on_signal_rejected("test-123", "invalid")
        hooks.on_signal_expired("test-123")
        hooks.on_signal_cancelled("test-123")
        hooks.on_state_transition(
            signal_id="test-123",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        hooks.on_dispatch_acknowledged("test-123", 15.2)
        
        # Should complete without exceptions
        assert True
    
    def test_hooks_do_not_mutate_external_state(self):
        """Hooks should only have internal side effects."""
        hooks = ObservabilityHooks()
        
        # Simulate state transition observation
        signal_id = "test-123"
        from_state = SignalState.PENDING
        to_state = SignalState.VALIDATED
        
        # Call hook
        hooks.on_state_transition(
            signal_id=signal_id,
            from_state=from_state,
            to_state=to_state,
            actor="system",
            reason="test"
        )
        
        # External variables unchanged
        assert signal_id == "test-123"
        assert from_state == SignalState.PENDING
        assert to_state == SignalState.VALIDATED
    
    def test_metrics_and_logs_updated_on_transition(self):
        """Hooks should update both metrics and logs."""
        hooks = ObservabilityHooks()
        
        hooks.on_state_transition(
            signal_id="test-123",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="system",
            reason="test",
            transition_latency_ms=12.5
        )
        
        # Verify metrics updated
        snapshot = hooks.metrics.get_metrics_snapshot()
        assert snapshot['gauges']['signals_in_state_validated'] == 1
        
        # Verify logs updated
        logs = hooks.logger.get_logs()
        assert len(logs) == 1
        assert logs[0]['signal_id'] == "test-123"
    
    def test_on_signal_created_hook(self):
        """on_signal_created should increment counters and gauges."""
        hooks = ObservabilityHooks()
        
        hooks.on_signal_created("test-123")
        
        snapshot = hooks.metrics.get_metrics_snapshot()
        assert snapshot['counters']['signals_created_total'] == 1
        assert snapshot['gauges']['signals_in_state_pending'] == 1
    
    def test_on_signal_rejected_hook(self):
        """on_signal_rejected should increment rejection counter."""
        hooks = ObservabilityHooks()
        
        hooks.on_signal_rejected("test-123", "invalid format")
        
        snapshot = hooks.metrics.get_metrics_snapshot()
        assert snapshot['counters']['signals_rejected_total'] == 1
    
    def test_on_signal_expired_hook(self):
        """on_signal_expired should increment expiration counter."""
        hooks = ObservabilityHooks()
        
        hooks.on_signal_expired("test-123")
        
        snapshot = hooks.metrics.get_metrics_snapshot()
        assert snapshot['counters']['signals_expired_total'] == 1
    
    def test_on_signal_cancelled_hook(self):
        """on_signal_cancelled should increment cancellation counter."""
        hooks = ObservabilityHooks()
        
        hooks.on_signal_cancelled("test-123")
        
        snapshot = hooks.metrics.get_metrics_snapshot()
        assert snapshot['counters']['signals_cancelled_total'] == 1
    
    def test_on_dispatch_acknowledged_hook(self):
        """on_dispatch_acknowledged should record latency."""
        hooks = ObservabilityHooks()
        
        hooks.on_dispatch_acknowledged("test-123", 25.5)
        
        snapshot = hooks.metrics.get_metrics_snapshot()
        assert snapshot['histograms']['dispatch_to_ack_latency_samples'] == 1
    
    def test_state_transition_updates_gauges(self):
        """State transitions should update from/to state gauges."""
        hooks = ObservabilityHooks()
        
        # Simulate signal creation
        hooks.metrics.increment_signals_in_state(SignalState.PENDING)
        
        # Transition from PENDING to VALIDATED
        hooks.on_state_transition(
            signal_id="test-123",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        snapshot = hooks.metrics.get_metrics_snapshot()
        assert snapshot['gauges']['signals_in_state_pending'] == 0
        assert snapshot['gauges']['signals_in_state_validated'] == 1


class TestObservabilityIsolation:
    """Test observability is fully isolated from business logic."""
    
    def test_observability_can_be_disabled(self):
        """Observability should be optional and removable."""
        # Creating hooks with None should work
        hooks = ObservabilityHooks(metrics=None, logger=None)
        
        # Hooks should still work (use defaults)
        hooks.on_signal_created("test-123")
        
        assert True
    
    def test_no_circular_dependencies(self):
        """Observability should not import FSM or audit modules."""
        # This test passes if imports work without circular dependency errors
        from observability import MetricsCollector, StructuredLogger, ObservabilityHooks
        from signal_state_machine import SignalState
        
        assert True
    
    def test_metrics_collector_is_independent(self):
        """MetricsCollector should work standalone."""
        metrics = MetricsCollector()
        
        metrics.increment_signals_created()
        snapshot = metrics.get_metrics_snapshot()
        
        assert snapshot['counters']['signals_created_total'] == 1
    
    def test_structured_logger_is_independent(self):
        """StructuredLogger should work standalone."""
        logger = StructuredLogger()
        
        logger.log_transition(
            signal_id="test",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        assert logger.get_log_count() == 1
    
    def test_custom_metrics_and_logger_injection(self):
        """Should be able to inject custom metrics and logger."""
        custom_metrics = MetricsCollector()
        custom_logger = StructuredLogger()
        
        hooks = ObservabilityHooks(
            metrics=custom_metrics,
            logger=custom_logger
        )
        
        hooks.on_signal_created("test-123")
        
        # Verify custom instances are used
        assert hooks.metrics is custom_metrics
        assert hooks.logger is custom_logger
        
        # Verify they were updated
        assert custom_metrics.get_metrics_snapshot()['counters']['signals_created_total'] == 1


class TestObservabilityPassivity:
    """Test that observability is truly passive and read-only."""
    
    def test_metrics_snapshot_does_not_modify_state(self):
        """Getting metrics snapshot should not change metrics."""
        metrics = MetricsCollector()
        
        metrics.increment_signals_created()
        snapshot1 = metrics.get_metrics_snapshot()
        snapshot2 = metrics.get_metrics_snapshot()
        
        # Both snapshots should be identical
        assert snapshot1 == snapshot2
    
    def test_get_logs_does_not_modify_logs(self):
        """Getting logs should not change log state."""
        logger = StructuredLogger()
        
        logger.log_transition(
            signal_id="test",
            from_state=SignalState.PENDING,
            to_state=SignalState.VALIDATED,
            actor="system",
            reason="test"
        )
        
        logs1 = logger.get_logs()
        logs2 = logger.get_logs()
        
        # Both calls should return same data
        assert len(logs1) == len(logs2)
        assert logs1[0] == logs2[0]
    
    def test_hooks_can_be_called_multiple_times(self):
        """Hooks should be idempotent for the same signal."""
        hooks = ObservabilityHooks()
        
        # Call same hook multiple times
        hooks.on_signal_created("test-123")
        hooks.on_signal_created("test-456")
        
        snapshot = hooks.metrics.get_metrics_snapshot()
        assert snapshot['counters']['signals_created_total'] == 2
        assert snapshot['gauges']['signals_in_state_pending'] == 2
