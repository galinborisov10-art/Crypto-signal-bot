# ML Retraining Scheduler Implementation (PR-ML-4)

## Summary

This PR implements a **strict, policy-based retraining scheduler** for the ML engine that:
1. Enforces FULL retrain every 7 days (time-based, heavy operation)
2. Defines INCREMENTAL retrain condition (20+ new trades, reserved for future implementation)
3. Provides clear priority: FULL > INCREMENTAL > SKIP

**This PR is SCHEDULER ONLY** - it decides WHEN to retrain, not HOW.

---

## Implementation Details

### 1. Constants Added (Lines 98-113)

```python
# ML RETRAINING POLICY (CANONICAL)
ML_FULL_RETRAIN_INTERVAL_DAYS = 7  # Once per week, no more
ML_INCREMENTAL_RETRAIN_MIN_TRADES = 20  # Minimum new trades (not yet implemented)
```

**Location:** After ML policy constants (around line 98 in ml_engine.py)

---

### 2. State Tracking Variables Added (Lines 234-244)

```python
# RETRAINING STATE (NEW - SCHEDULER ONLY)
self.last_full_retrain_ts = None        # Timestamp of last FULL retrain
self.processed_trade_count = 0          # Trades processed (for future incremental logic)
```

**Location:** In `MLTradingEngine.__init__()` method, after performance tracking variables

---

### 3. New Methods Added

#### 3.1 `sync_retrain_state()` (Lines ~960-988)

Syncs retrain state from existing training data:
- Maps `last_training_time` → `last_full_retrain_ts` for compatibility
- Counts total closed trades → `processed_trade_count`

Called at the end of `__init__()` to bootstrap state from existing data.

#### 3.2 `should_full_retrain()` (Lines ~990-1003)

Checks if full retrain should occur (7+ days elapsed).

Returns:
- `True` if never trained OR 7+ days since last full retrain
- `False` otherwise

#### 3.3 `should_incremental_retrain()` (Lines ~1005-1017)

Checks if incremental retrain condition is met (20+ new trades).

**Note:** This is policy-defined but NOT YET IMPLEMENTED.

Returns:
- `True` if condition met (but implementation pending)
- `False` otherwise

#### 3.4 `get_new_trades_count()` (Lines ~1019-1047)

Counts new closed trades since last full retrain.

Reserved for future incremental retrain implementation.

Returns:
- `int`: Number of new closed trades

#### 3.5 `sync_processed_trade_count()` (Lines ~1049-1063)

Syncs processed_trade_count after full retrain.

Sets counter to total closed trades (reset incremental state).

#### 3.6 `maybe_retrain_model()` (Lines ~1065-1117)

**Main deterministic ML retraining scheduler.**

Priority:
1. FULL retrain if 7+ days since last full retrain
2. INCREMENTAL retrain if 20+ new trades (NOT YET IMPLEMENTED)
3. SKIP if neither condition met

Returns:
- `True` if retrain occurred
- `False` otherwise

---

### 4. Updated Methods

#### 4.1 `should_retrain()` (Lines ~1119-1127)

**Updated:** Now delegates to `should_full_retrain()` for consistency.

This is a LEGACY METHOD kept for compatibility.

#### 4.2 `auto_retrain()` (Lines ~1129-1144)

**Updated:** Now uses `maybe_retrain_model()` scheduler instead of directly calling training methods.

This is a LEGACY METHOD updated for consistency.

#### 4.3 `train_model()` (Line ~489)

**Updated:** Now calls `self.record_performance(accuracy, len(X))` to update `last_training_time`.

This ensures that timestamp tracking is consistent with `train_ensemble_model()`.

---

## Constraints Followed

### ✅ Allowed (All Done):
- ✅ Added policy constants (intervals, thresholds)
- ✅ Added state tracking variables (timestamps, counters)
- ✅ Added scheduler methods (decide WHEN to retrain)
- ✅ Added helper methods (condition checks, trade counting)
- ✅ Updated legacy methods for compatibility

### ❌ Forbidden (None Done):
- ❌ NO changes to `train_model()` logic (only added `record_performance()` call)
- ❌ NO incremental retrain implementation (reserved for PR-ML-5+)
- ❌ NO changes to feature extraction
- ❌ NO changes to confidence logic
- ❌ NO changes to ML policy (ML-2)
- ❌ NO changes to bounds (ML-1)
- ❌ NO new ML techniques or algorithms

---

## Verification

### Test Results

**test_ml_retrain_scheduler.py:** ✅ ALL TESTS PASSED
- ✅ Retraining policy constants defined correctly
- ✅ State tracking variables initialized
- ✅ All scheduler methods implemented and callable
- ✅ Full retrain triggered only when 7+ days elapsed
- ✅ Legacy methods delegate to new scheduler
- ✅ Incremental retrain defined but returns False (not implemented)

**test_ml_scheduler_smoke.py:** ✅ SMOKE TEST PASSED
- ✅ All scheduler components working
- ✅ Legacy methods match new methods
- ✅ Full retrain triggers correctly with old timestamp
- ✅ No retrain when conditions not met

**test_ml_confidence_bounds.py:** ✅ ALL TESTS PASSED
- ✅ No regressions in existing ML confidence bounds functionality

### Behavioral Verification

1. **Full retrain triggered ONLY when 7+ days elapsed**: ✅
   - Tested with various timestamp scenarios
   - Never trained → triggers retrain
   - 3 days ago → no retrain
   - 7 days ago → triggers retrain
   - 10 days ago → triggers retrain

2. **Incremental retrain condition logged but not executed**: ✅
   - Method exists and can be called
   - Returns False (not implemented)
   - Logs "NOT YET IMPLEMENTED" message

3. **`train_model()` unchanged (existing logic preserved)**: ✅
   - Only added `record_performance()` call for timestamp tracking
   - No changes to training algorithm, features, or model

4. **State tracking syncs correctly**: ✅
   - `sync_retrain_state()` properly syncs from existing data
   - `last_full_retrain_ts` syncs with `last_training_time`
   - `processed_trade_count` counts closed trades

5. **Legacy methods work correctly**: ✅
   - `should_retrain()` delegates to `should_full_retrain()`
   - `auto_retrain()` uses `maybe_retrain_model()`
   - Backward compatibility maintained

---

## Files Modified

- **ml_engine.py** (~150 lines added: constants, state, scheduler, helpers)
  - Constants: 2 (lines 106, 109)
  - State variables: 2 (lines 234-244)
  - New methods: 6 (sync_retrain_state, should_full_retrain, should_incremental_retrain, get_new_trades_count, sync_processed_trade_count, maybe_retrain_model)
  - Updated methods: 3 (should_retrain, auto_retrain, train_model)

- **test_ml_retrain_scheduler.py** (NEW, ~200 lines)
  - Comprehensive test suite for scheduler
  
- **test_ml_scheduler_smoke.py** (NEW, ~90 lines)
  - Smoke test for integration verification

**Total:** 1 file modified, 2 test files added, scheduler-only changes

---

## Acceptance Criteria

- [x] `ML_FULL_RETRAIN_INTERVAL_DAYS = 7` constant defined
- [x] `ML_INCREMENTAL_RETRAIN_MIN_TRADES = 20` constant defined
- [x] `last_full_retrain_ts` state variable added
- [x] `processed_trade_count` state variable added
- [x] `maybe_retrain_model()` scheduler method added
- [x] Full retrain triggered only on 7+ days
- [x] Incremental condition checked but not implemented
- [x] Logs clearly state "not yet implemented" for incremental
- [x] `train_model()` unchanged (only added timestamp tracking)
- [x] NO new ML training logic
- [x] NO changes to feature extraction or confidence

---

## Goal Achieved

✅ Established deterministic ML retraining schedule (WHEN) without changing training implementation (HOW).

Incremental retrain implementation deferred to PR-ML-5+ after design decision.
