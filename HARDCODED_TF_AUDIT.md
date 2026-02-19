# HARDCODED TIMEFRAME AUDIT

**Date:** 2026-02-19  
**Objective:** Identify and eliminate ALL hardcoded timeframe logic to ensure single source of truth through timeframe_contract.py

---

## 🔍 AUDIT FINDINGS

### Critical Issues Found

#### 1. **ict_signal_engine.py - Line 3017-3025: Legacy MTF Hierarchy**

**Location:** `_calculate_mtf_consensus()` method

**Current Code:**
```python
# Legacy: Dynamic MTF hierarchy based on entry timeframe
MTF_HIERARCHY = {
    '5m':  ['5m', '15m', '30m', '1h'],
    '15m': ['15m', '30m', '1h', '4h'],
    '30m': ['30m', '1h', '2h', '4h'],
    '1h':  ['1h', '2h', '4h', '1d'],
    '2h':  ['2h', '4h', '1d'],
    '4h':  ['4h', '1d'],
    '1d':  ['1d', '1w']
}
```

**Problem:** 
- Hardcoded TF mapping duplicates contract logic
- Used as fallback when contract not available
- Should ALWAYS use contract or fail explicitly

**Fix Required:**
- Remove entire MTF_HIERARCHY dictionary
- Make contract usage mandatory (no fallback)
- Add clear error if contract unavailable

---

#### 2. **ict_signal_engine.py - Line 276: TP Multiplier TF Logic**

**Location:** `get_tp_multipliers_by_timeframe()` function

**Current Code:**
```python
if tf in ['15m', '30m', '1h', '2h', '3h']:
    return (1.0, 3.0, 5.0)
elif tf in ['4h', '6h', '8h', '12h', '1d', '3d', '1w']:
    return (2.0, 4.0, 6.0)
```

**Problem:**
- Hardcoded TF classification for TP calculation
- Not using TF contract metadata
- Fixed TF lists may drift from contract

**Fix Required:**
- Move TF classification to timeframe_contract.py
- Add `get_tf_category()` method (short_term, medium_term, long_term)
- Use contract for TP multiplier logic

---

#### 3. **ict_signal_engine.py - Line 4059: SL Buffer TF Logic**

**Location:** `_calculate_sl_tp()` method

**Current Code:**
```python
buffer_pct = 0.002 if timeframe in ['15m', '30m', '1h'] else 0.003
```

**Problem:**
- Hardcoded TF check for buffer calculation
- Not using contract TF metadata
- Should use TF category from contract

**Fix Required:**
- Use `TimeframeContract.get_tf_category()` instead
- Make buffer calculation contract-based

---

#### 4. **ict_signal_engine.py - Lines 213, 218: ATR Multiplier Dictionaries**

**Current Code:**
```python
'15m': 0.003, '30m': 0.004, '1h': 0.005, ...
'15m': 0.001, '30m': 0.0015, '1h': 0.002, ...
```

**Problem:**
- Hardcoded TF-specific ATR multipliers
- Static configuration outside contract

**Fix Required:**
- Move to timeframe_contract.py as TF metadata
- Access via contract API

---

#### 5. **ict_signal_engine.py - Line 4048: MIN_SL_DISTANCE Dictionary**

**Current Code:**
```python
MIN_SL_DISTANCE = {
    '15m': 0.005,
    '30m': 0.0075,
    '1h': 0.010,
    '2h': 0.0125,
    '4h': 0.020,
    '1d': 0.030
}
```

**Problem:**
- Hardcoded TF-specific SL distances
- Should be in contract metadata

**Fix Required:**
- Move to timeframe_contract.py
- Access via `TimeframeContract.get_min_sl_distance(tf)`

---

#### 6. **bot.py - Multiple Hardcoded TF Lists**

**Locations:** Various functions

**Current Code:**
```python
all_timeframes = ['1m', '5m', '15m', '1h', '2h', '3h', '4h', '1d', '1w']
mtf_timeframes = ['5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w']
valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '3h', '4h', '1d', '1w']
key_timeframes = ['1m', '15m', '1h', '4h', '1d']
timeframes_to_check = ['1h', '2h', '4h', '1d']
```

**Problem:**
- Multiple duplicate TF lists
- No single source of truth
- May drift from contract

**Fix Required:**
- Use `TimeframeContract.get_supported_timeframes()`
- Remove all hardcoded lists

---

## 📊 SUMMARY

### Total Issues: 6 Categories

| Location | Type | Severity | Lines |
|----------|------|----------|-------|
| ict_signal_engine.py | MTF Hierarchy | CRITICAL | 3017-3025 |
| ict_signal_engine.py | TP Multipliers | HIGH | 276-283 |
| ict_signal_engine.py | SL Buffer | HIGH | 4059 |
| ict_signal_engine.py | ATR Multipliers | MEDIUM | 213, 218 |
| ict_signal_engine.py | MIN_SL_DISTANCE | MEDIUM | 4048-4054 |
| bot.py | TF Lists | MEDIUM | Multiple |

---

## 🎯 FIX PRIORITY

### Phase 1: CRITICAL (Must Fix Immediately)
1. ✅ Remove MTF_HIERARCHY dictionary (lines 3017-3025)
2. ✅ Make contract usage mandatory in MTF consensus

### Phase 2: HIGH (Next)
3. ✅ Add TF category system to contract
4. ✅ Fix TP multiplier logic to use contract
5. ✅ Fix SL buffer logic to use contract

### Phase 3: MEDIUM (Cleanup)
6. ✅ Move ATR multipliers to contract metadata
7. ✅ Move MIN_SL_DISTANCE to contract metadata
8. ✅ Replace bot.py TF lists with contract calls

---

## ✅ SUCCESS CRITERIA

1. **Zero hardcoded TF arrays** in ict_signal_engine.py
2. **All TF logic** goes through timeframe_contract.py
3. **No fallback** to legacy TF hierarchies
4. **Contract is mandatory** - fail explicitly if unavailable
5. **All tests pass** with contract-only logic

---

## 📝 IMPLEMENTATION NOTES

**Approach:**
- Small, incremental fixes
- One category at a time
- Test after each change
- Document with log evidence

**Testing:**
- Test with multiple TF combinations
- Verify debug logs show contract usage
- Confirm no hardcoded TF references in logs

**Validation:**
- Grep for hardcoded TF patterns
- Code review each change
- Regression testing

---

**Status:** Audit Complete - Ready for Systematic Fixes  
**Next:** Implement Phase 1 fixes
