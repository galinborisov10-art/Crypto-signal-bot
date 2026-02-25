# 🎯 Timeframe Contract

## Overview

The **Timeframe Contract** defines a deterministic, hierarchical mapping between the signal entry timeframe and the higher timeframes used for confirmation, structure analysis, and HTF bias. It is the single source of truth for all ICT component detection in this bot.

**Key principle:** every component is detected on exactly one timeframe, and that timeframe is always determined by the contract — never hardcoded elsewhere.

---

## Timeframe Hierarchy Tables

### MANUAL Signals (Available TFs: 15m, 30m, 1h, 2h, 4h, 1d)

| Signal TF | SIGNAL_TF | CONFIRMATION_TF | STRUCTURE_TF | HTF_BIAS_TF |
|-----------|-----------|-----------------|--------------|-------------|
| **15m**   | 15m       | 30m             | 1h           | 1h          |
| **30m**   | 30m       | 1h              | 2h           | 2h          |
| **1h**    | 1h        | 2h              | 4h           | 4h          |
| **2h**    | 2h        | 4h              | 1d           | 1d          |
| **4h**    | 4h        | 1d              | 1d           | 1d          |
| **1d**    | 1d        | 1d              | 1d           | 1d          |

### AUTO Signals (Available TFs: 1h, 2h, 4h, 1d)

| Signal TF | SIGNAL_TF | CONFIRMATION_TF | STRUCTURE_TF | HTF_BIAS_TF |
|-----------|-----------|-----------------|--------------|-------------|
| **1h**    | 1h        | 2h              | 4h           | 4h          |
| **2h**    | 2h        | 4h              | 1d           | 1d          |
| **4h**    | 4h        | 1d              | 1d           | 1d          |
| **1d**    | 1d        | 1d              | 1d           | 1d          |

---

## Component-to-Timeframe Mapping

| Component           | Required Timeframe  | Rule                                        |
|---------------------|---------------------|---------------------------------------------|
| Order Blocks        | SIGNAL_TF           | `component.timeframe == signal_tf`          |
| FVG                 | SIGNAL_TF           | `component.timeframe == signal_tf`          |
| Liquidity Zones     | SIGNAL_TF           | `component.timeframe == signal_tf`          |
| BSL / SSL           | SIGNAL_TF           | `component.timeframe == signal_tf`          |
| Structure Break     | STRUCTURE_TF        | `component.timeframe == structure_tf`       |
| Displacement        | CONFIRMATION_TF     | detected on confirmation timeframe          |
| Whale Blocks        | CONFIRMATION_TF     | detected on confirmation timeframe          |
| HTF Bias            | HTF_BIAS_TF         | directional bias only, must NOT contaminate entry |

**Critical rule:** HTF Bias components (OBs/FVGs from `HTF_BIAS_TF`) inform directional bias only. They must **not** be used as entry Points of Interest (POIs).

---

## Validation Rules

### Timeframe Correctness

- `signal_tf` must match the input timeframe exactly.
- `htf_bias_tf` must always equal `structure_tf`.
- Unsupported timeframes must return `None` (never raise).

### Component Data

**Order Blocks:**
- `zone_low < zone_high` (or `bottom < top`)
- `zone_low != 0` and `zone_high != 0`
- `timeframe` present and matches expected

**FVG:**
- `bottom < top`
- `bottom != 0` and `top != 0`
- `timeframe` present and matches expected

**Liquidity Zones:**
- `price_level != 0` (or `price` / `level` fallback)
- `timeframe` present and matches expected

**Liquidity Sweeps:**
- `price != 0`
- `timestamp` present
- `timeframe` optional (warning if missing, not rejected)

### Scenario Integrity

| Scenario      | Component Used         | Expected TF       | Violation if …                          |
|---------------|------------------------|-------------------|-----------------------------------------|
| PULLBACK      | Order Blocks / FVG     | SIGNAL_TF         | OB/FVG from `htf_bias_tf` used as POI  |
| CONTINUATION  | Displacement           | CONFIRMATION_TF   | Displacement from wrong TF              |
| REVERSAL      | Structure Break        | STRUCTURE_TF      | Structure break from wrong TF           |
| ROLLBACK      | Structure Break        | STRUCTURE_TF      | Structure break from wrong TF           |

---

## Implementation

### Source files

| File | Role |
|------|------|
| `timeframe_contract.py` | Single source of truth: `TimeframeContract`, `TimeframeHierarchy`, `SignalMode` |
| `component_tf_validator.py` | Per-component validation: `ComponentTimeframeValidator`, `CrossTimeframeContaminationDetector` |
| `validate_timeframe_contract.py` | CI validation script (runs all hierarchy checks) |
| `validate_component_flow.py` | Validates component flow end-to-end |
| `tests/test_timeframe_contract.py` | Unit tests for hierarchy, component validation and scenario integrity |

### Key classes

```python
from timeframe_contract import TimeframeContract, SignalMode

# Get hierarchy for a signal timeframe
hierarchy = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
# hierarchy.signal_tf       → '1h'
# hierarchy.confirmation_tf → '2h'
# hierarchy.structure_tf    → '4h'
# hierarchy.htf_bias_tf     → '4h'
```

```python
from component_tf_validator import ComponentTimeframeValidator

# Validate a single Order Block
result = ComponentTimeframeValidator.validate_order_block(ob, expected_tf='1h', expected_bias='BULLISH')
if not result.is_valid:
    print(result.errors)

# Filter a list, returning only valid components
valid_obs, rejected = ComponentTimeframeValidator.validate_component_list(
    obs, 'Order Block', expected_tf='1h', expected_bias='BULLISH'
)
```

```python
from component_tf_validator import CrossTimeframeContaminationDetector

issues = CrossTimeframeContaminationDetector.check_entry_scoring_contamination(
    components, signal_tf='1h', structure_tf='4h', htf_bias_tf='4h'
)
# issues == [] means no contamination
```

---

## Correct vs Incorrect Usage

### ✅ Correct — SIGNAL_TF Order Block as POI

```python
# 1h signal → Order Block must come from 1h
order_block = {
    'type': 'BULLISH',
    'zone_low': 49000,
    'zone_high': 49200,
    'timeframe': '1h'   # ✅ matches signal_tf
}
```

### ❌ Incorrect — HTF Order Block as POI (contamination)

```python
# 1h signal → HTF_BIAS_TF is 4h; using a 4h OB as entry POI is wrong
order_block = {
    'type': 'BULLISH',
    'zone_low': 49000,
    'zone_high': 49200,
    'timeframe': '4h'   # ❌ htf_bias_tf component in entry scoring
}
```

---

## How to Run Validation

```bash
# Run the contract validation script
python3 validate_timeframe_contract.py

# Run component flow validation
python3 validate_component_flow.py

# Run the full test suite
python3 tests/test_timeframe_contract.py

# Run all validations together
python3 run_all_validations.py
```

---

## Invariants

1. `htf_bias_tf == structure_tf` — enforced in `TimeframeHierarchy.__post_init__`
2. No hardcoded timeframe overrides — all routing goes through `TimeframeContract.get_hierarchy()`
3. No implicit inheritance — each signal computes its own hierarchy independently
4. Components carry a `timeframe` field set at detection time
5. Entry scoring uses only `signal_tf` components (validated by `CrossTimeframeContaminationDetector`)
