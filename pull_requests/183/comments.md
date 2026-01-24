## ❌ NOT APPROVED - Critical scope violations detected

This PR changes ML model behavior, which violates the strict scope requirement of **"validation only, no ML changes"**.

---

### 🔴 **Critical Issues**

#### **Issue 1: Training feature extraction CHANGED (FORBIDDEN)**

**Before (6 features):**
```python
features = [
    conditions.get('rsi', 50),                    # 1
    conditions.get('price_change_pct', 0),        # 2 ❌ REMOVED
    conditions.get('volume_ratio', 1),            # 3
    conditions.get('volatility', 5),              # 4
    conditions.get('bb_position', 0.5),           # 5 ❌ REMOVED
    conditions.get('ict_confidence', 0.5),        # 6 ❌ REMOVED
]
```

**After (7 features):**
```python
features = [
    conditions.get('rsi', 50),
    conditions.get('confidence', 50),             # NEW
    conditions.get('volume_ratio', 1),
    conditions.get('trend_strength', 0),          # NEW
    conditions.get('volatility', 5),
]
# + timeframe encoding (NEW)
# + signal_type encoding (NEW)
```

**Impact:**
- ❌ Feature space changed from 6D → 7D
- ❌ 3 features removed: `price_change_pct`, `bb_position`, `ict_confidence`
- ❌ 4 features added: `confidence`, `trend_strength`, `timeframe`, `signal_type`
- ❌ **ALL existing trained models become INVALID**
- ❌ This is an ML MODEL CHANGE, not validation

---

#### **Issue 2: New method added `get_ml_prediction()` (lines 147-253)**

```python
def get_ml_prediction(self, analysis: dict) -> dict:
    """Get ML prediction for signal."""
    # ... 106 lines of NEW ML logic ...
```

**Problems:**
- This method did NOT exist before
- Adds new ML prediction interface
- Includes new `_extract_features()` helper (lines 220-246)
- **Scope violation:** Only validation allowed, NO new methods

---

#### **Issue 3: Feature encoding logic added (lines 408-415)**

```python
# Encode categorical features
timeframe_map = {'1h': 1, '2h': 2, '4h': 4, '1d': 24}
timeframe_encoded = timeframe_map.get(conditions.get('timeframe', '4h'), 4)
features.append(timeframe_encoded)

signal_map = {'BUY': 1, 'STRONG_BUY': 2, 'SELL': -1, 'STRONG_SELL': -2}
signal_encoded = signal_map.get(conditions.get('signal_type', 'BUY'), 1)
features.append(signal_encoded)
```

**This is ML LOGIC, not schema validation!**

---

### ✅ **What SHOULD be in this PR (validation ONLY):**

```python
def train_model(self):
    """Train ML model from trading journal"""
    # ... existing code ...
    
    valid_trades = 0
    invalid_trades = 0
    
    for trade in trades:
        conditions = trade.get('conditions', {})
        
        # ✅ SANITY GATE: Validate schema (KEEP THIS)
        is_valid, missing_features = _validate_ml_features(conditions)
        
        if not is_valid:
            invalid_trades += 1
            logger.debug(f"⚠️ Skipping trade (invalid schema): {', '.join(missing_features)}")
            continue
        
        valid_trades += 1
        
        # ✅ KEEP EXISTING FEATURE EXTRACTION UNCHANGED
        features = [
            conditions.get('rsi', 50),                    # KEEP
            conditions.get('price_change_pct', 0),        # KEEP (don't remove)
            conditions.get('volume_ratio', 1),            # KEEP
            conditions.get('volatility', 5),              # KEEP
            conditions.get('bb_position', 0.5),           # KEEP (don't remove)
            conditions.get('ict_confidence', 0.5),        # KEEP (don't remove)
        ]
        # ❌ NO encoding logic here
        
        # ... rest of existing code unchanged ...
```

---

### 📋 **Required Corrections**

1. **REVERT training feature extraction to original 6 features**
   - Restore: `price_change_pct`, `bb_position`, `ict_confidence`
   - Remove: `confidence`, `trend_strength`, categorical encodings

2. **REMOVE `get_ml_prediction()` method entirely**
   - Lines 147-253 should be deleted
   - Validation belongs in existing methods only

3. **REMOVE feature encoding logic**
   - Delete `timeframe_map` and `signal_map` from training
   - Validation checks values exist, does NOT transform them

4. **KEEP schema validation**
   - ✅ Keep: `REQUIRED_ML_FEATURES`, `FEATURE_TYPES`, `VALID_*` constants
   - ✅ Keep: `_validate_ml_features()` function
   - ✅ Keep: Validation guard in `train_model()` (skip invalid trades)
   - ✅ Keep: Logging of validation results

---

### 🎯 **Scope Reminder**

**This PR MUST be:**
- ✅ Schema validation ONLY (sanity gate)
- ❌ NO ML model changes
- ❌ NO feature extraction changes
- ❌ NO new methods
- ❌ NO encoding logic

**Goal:** Prevent training/prediction mismatch by validating that required features exist and have correct types. NOT to change what features are used or how they're processed.

---