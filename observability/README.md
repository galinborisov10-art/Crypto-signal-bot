# ESB v1.0 §3.5 - Observability Layer

## Overview

The observability layer provides **passive, read-only metrics and structured logging** for signal lifecycle events. It has **zero behavioral impact** on the FSM, invariants, or audit logic.

## Design Principles

1. **Passive Only** - Observability never influences business logic or state transitions
2. **Fire-and-Forget** - All hooks are non-blocking and never throw exceptions
3. **No Dependencies** - Business logic does NOT depend on observability
4. **Fully Optional** - Observability can be completely removed without affecting functionality
5. **No Global State** - All components are instance-based
6. **No Circular Imports** - Observability only imports from FSM, never the reverse

## Components

### 1. MetricsCollector (`metrics.py`)

Provides counters, gauges, and histograms for signal lifecycle metrics.

**Counters:**
- `signals_created_total` - Total signals created
- `signals_rejected_total` - Total signals rejected
- `signals_expired_total` - Total signals expired
- `signals_cancelled_total` - Total signals cancelled

**Gauges:**
- `signals_in_state{state}` - Current count of signals in each state

**Histograms:**
- `state_transition_latency_ms{from,to}` - Time spent in transition
- `dispatch_to_ack_latency_ms` - Dispatch to acknowledgment latency

### 2. StructuredLogger (`structured_logger.py`)

Emits JSON-formatted log entries for each state transition.

**Log Entry Format:**
```json
{
  "phase": 3,
  "signal_id": "sig-123",
  "from_state": "pending",
  "to_state": "validated",
  "actor": "system",
  "reason": "validation passed",
  "timestamp": "2026-01-22T12:00:00.000000+00:00",
  "metadata": {}
}
```

### 3. ObservabilityHooks (`hooks.py`)

Provides side-effect-only hooks that coordinate metrics and logging.

**Available Hooks:**
- `on_signal_created(signal_id)` - Called when signal is created
- `on_signal_rejected(signal_id, reason)` - Called when signal is rejected
- `on_signal_expired(signal_id)` - Called when signal expires
- `on_signal_cancelled(signal_id)` - Called when signal is cancelled
- `on_state_transition(...)` - Called on successful state transition
- `on_dispatch_acknowledged(signal_id, latency_ms)` - Called when dispatch is acknowledged

## Usage Example

```python
from signal_state_machine import SignalState, SignalStateMachine
from observability import ObservabilityHooks

# Create FSM and observability hooks
fsm = SignalStateMachine()
hooks = ObservabilityHooks()

# Signal lifecycle with observability
signal_id = "test-signal-123"

# Step 1: Signal created
hooks.on_signal_created(signal_id)

# Step 2: Transition with observability
from_state = fsm.state
fsm.transition(SignalState.VALIDATED)
to_state = fsm.state

hooks.on_state_transition(
    signal_id=signal_id,
    from_state=from_state,
    to_state=to_state,
    actor="system",
    reason="validation passed",
    transition_latency_ms=12.5
)

# Get metrics snapshot (for debugging only)
snapshot = hooks.metrics.get_metrics_snapshot()
print(snapshot['counters'])
print(snapshot['gauges'])

# Get logs (for debugging only)
logs = hooks.logger.get_logs(signal_id=signal_id)
for log in logs:
    print(f"{log['from_state']} -> {log['to_state']}")
```

## Testing

Run the test suite to verify zero behavioral impact:

```bash
python3 -m pytest tests/test_observability.py -v
```

All 29 tests verify:
- ✅ Observability does NOT mutate state
- ✅ Observability does NOT affect transitions
- ✅ Hooks can be called safely
- ✅ No circular dependencies
- ✅ Metrics and logs are passive only

## Integration Verification

Run existing Phase 3 tests to verify no behavioral changes:

```bash
python3 -m pytest tests/test_signal_state_machine.py tests/test_signal_state_invariants.py tests/test_signal_state_audit.py -v
```

All 124 existing tests pass, confirming zero behavioral impact.

## Definition of Done

✅ Zero behavioral changes  
✅ Zero Phase 2 diffs  
✅ Observability is fully optional and removable  
✅ Phase 3 remains deterministic  
✅ No global state  
✅ No circular imports  
✅ Hooks are fire-and-forget  
✅ Metrics never influence logic  
✅ Structured logs are passive only  

## File Structure

```
observability/
├── __init__.py          # Module exports (16 lines)
├── metrics.py           # MetricsCollector class (125 lines)
├── structured_logger.py # StructuredLogger class (98 lines)
├── hooks.py             # ObservabilityHooks class (140 lines)
└── README.md            # This file

tests/
└── test_observability.py # Test suite (480 lines, 29 tests)
```

## Compliance

This implementation strictly follows ESB v1.0 §3.5:

- **NO** modifications to FSM, invariants, or audit modules
- **NO** modifications to Phase 2 code
- **NO** business logic in observability layer
- **NO** decisions or conditionals affecting behavior
- **NO** return value changes
- **YES** side-effect-only hooks
- **YES** passive metrics and logs only
