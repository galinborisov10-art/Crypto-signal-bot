"""
ESB v1.0 §3.5 - Observability module.

Provides passive metrics and structured logging for signal lifecycle events.
Zero behavioral impact on FSM, invariants, or audit logic.
"""

from .metrics import MetricsCollector
from .structured_logger import StructuredLogger
from .hooks import ObservabilityHooks

__all__ = [
    'MetricsCollector',
    'StructuredLogger',
    'ObservabilityHooks',
]
