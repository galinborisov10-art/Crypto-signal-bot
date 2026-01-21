# Confidence Threshold Implementation (ESB v1.0 §2.2)

## Overview

This document describes the **Confidence Threshold Evaluator**, a deterministic module that evaluates whether a signal's confidence meets the minimum threshold for execution eligibility.

## Thresholds

The following fixed thresholds are defined per signal direction:

| Direction | Threshold |
|-----------|-----------|
| BUY | 60.0 |
| SELL | 60.0 |
| STRONG_BUY | 70.0 |
| STRONG_SELL | 70.0 |

## Evaluation Rules

1. **Prerequisite**: Signal must have already passed Entry Gating (`ENTRY_ALLOWED == True`)
2. **Input**: Signal context dictionary with `direction` and `raw_confidence` fields
3. **Logic**: `raw_confidence >= threshold[direction]`
4. **Output**: Boolean (`True` = eligible, `False` = blocked)

### Hard Blocking Conditions

The evaluator returns `False` (HARD BLOCK) if:
- `direction` field is missing or `None`
- `raw_confidence` field is missing or `None`
- `direction` is not one of: `BUY`, `SELL`, `STRONG_BUY`, `STRONG_SELL`
- `raw_confidence < threshold[direction]`

## Usage Example

```python
from confidence_threshold_evaluator import evaluate_confidence_threshold

# Example 1: BUY signal with sufficient confidence
signal_context = {
    'direction': 'BUY',
    'raw_confidence': 65.0
}

if evaluate_confidence_threshold(signal_context):
    print("Signal eligible for execution")
else:
    print("Signal blocked due to low confidence")

# Output: "Signal eligible for execution"


# Example 2: STRONG_BUY signal with insufficient confidence
signal_context = {
    'direction': 'STRONG_BUY',
    'raw_confidence': 68.0
}

if evaluate_confidence_threshold(signal_context):
    print("Signal eligible for execution")
else:
    print("Signal blocked due to low confidence")

# Output: "Signal blocked due to low confidence"
```

## Behavioral Guarantees

The Confidence Threshold Evaluator provides the following guarantees:

### 1. Deterministic Output
- Same input → same output (always)
- No randomness or external state dependencies

### 2. Signal Immutability
- Input `signal_context` is **never modified**
- Function is side-effect free

### 3. Independence from Execution Context
- Does NOT access execution-related fields:
  - `position_size`
  - `leverage`
  - `account_balance`
  - `entry_price`
  - `sl_price`
  - `tp_prices`

### 4. Hard Pass/Fail Logic
- No soft logic or fallbacks
- One threshold fail = HARD BLOCK
- No partial eligibility

### 5. Always Returns Boolean
- Return type is **always** `bool`
- Never returns `None`, exceptions, or other types

## Integration with Entry Gating

This module is designed to work in tandem with Entry Gating:

```python
from entry_gating_evaluator import evaluate_entry_gating
from confidence_threshold_evaluator import evaluate_confidence_threshold

# Step 1: Check Entry Gating
if not evaluate_entry_gating(signal_context):
    print("Signal blocked by Entry Gating")
    return

# Step 2: Check Confidence Threshold (only if entry gating passed)
if not evaluate_confidence_threshold(signal_context):
    print("Signal blocked due to low confidence")
    return

# Signal is eligible for execution
print("Signal passed all checks - eligible for execution")
```

## Testing

Comprehensive tests are provided in `tests/test_confidence_threshold.py`:

- ✅ All 4 thresholds (BUY, SELL, STRONG_BUY, STRONG_SELL)
- ✅ Edge cases (0, threshold ± 0.01, 100)
- ✅ Missing/invalid fields
- ✅ Signal immutability
- ✅ Deterministic behavior
- ✅ Independence from execution context

Run tests:
```bash
# Using pytest (if installed)
pytest tests/test_confidence_threshold.py -v

# Using Python directly
python3 tests/test_confidence_threshold.py
```

## ESB Compliance

This implementation strictly follows ESB v1.0 §2.2:
- ✅ Fixed thresholds (no dynamic tuning)
- ✅ Deterministic evaluation
- ✅ Hard blocking logic
- ✅ No soft constraints
- ✅ Independent from execution context
- ✅ Evaluated only after Entry Gating passes

## Modification Policy

**These thresholds are FIXED per ESB v1.0 and should NOT be modified without explicit ESB version update.**

Any changes to thresholds require:
1. Update to ESB document
2. Version bump (e.g., ESB v1.1)
3. Regression testing
4. Documentation update

---

**Document Version**: 1.0  
**ESB Reference**: v1.0 §2.2  
**Last Updated**: 2026-01-21
