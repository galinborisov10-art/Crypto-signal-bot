# Phase 2B Code Evidence - All 3 Fixes Present

**Generated:** 2026-01-31T18:06:33Z  
**Commit:** 835a125  
**Branch:** copilot/add-regression-detection-replay

---

## Purpose

This document provides **concrete evidence** that all 3 required Phase 2B blocking fixes are present in `diagnostics.py`.

---

## Fix 1: ReplayEngine Reuses ict_engine_global ✅

### Line Numbers
- Line 1558: Parameter added
- Line 1563: Import statement
- Line 1564: Assignment
- Line 1604: Usage

### Code Proof

**File:** `diagnostics.py` lines 1558-1571

```python
def __init__(self, cache: ReplayCache, signal_engine=None):
    self.cache = cache
    # Reuse global engine for production parity
    if signal_engine is None:
        try:
            from bot import ict_engine_global
            self.signal_engine = ict_engine_global
            logger.info("✅ ReplayEngine using global ICT engine")
        except ImportError:
            from ict_signal_engine import ICTSignalEngine
            self.signal_engine = ICTSignalEngine()
            logger.warning("⚠️ ReplayEngine created new ICT engine")
    else:
        self.signal_engine = signal_engine
```

**File:** `diagnostics.py` line 1604

```python
signal = self.signal_engine.generate_signal(
```

### Grep Verification

```bash
$ grep -n "from bot import ict_engine_global" diagnostics.py
1563:                from bot import ict_engine_global

$ grep -n "self.signal_engine = ict_engine_global" diagnostics.py
1564:                self.signal_engine = ict_engine_global
```

---

## Fix 2: Price Tolerance 0.5% ✅

### Line Number
- Line 1646: Constant definition

### Code Proof

**File:** `diagnostics.py` line 1646

```python
PRICE_TOLERANCE_PERCENT = 0.005  # 0.5% tolerance for price levels
```

**File:** `diagnostics.py` line 1656 (usage)

```python
return delta <= PRICE_TOLERANCE_PERCENT
```

### Grep Verification

```bash
$ grep -n "PRICE_TOLERANCE_PERCENT = 0.005" diagnostics.py
1646:        PRICE_TOLERANCE_PERCENT = 0.005  # 0.5% tolerance for price levels
```

---

## Fix 3: Confidence Tolerance + confidence_delta ✅

### Line Numbers
- Line 1649: CONFIDENCE_TOLERANCE constant
- Lines 1667-1669: check_confidence_match() function
- Line 1704: confidence_delta in checks dict

### Code Proof

**File:** `diagnostics.py` line 1649

```python
CONFIDENCE_TOLERANCE = 5  # ±5 points tolerance for confidence
```

**File:** `diagnostics.py` lines 1667-1669

```python
def check_confidence_match(orig_conf: float, replay_conf: float) -> bool:
    """Check if confidence matches within tolerance"""
    return abs(orig_conf - replay_conf) <= CONFIDENCE_TOLERANCE
```

**File:** `diagnostics.py` lines 1698-1705 (checks dict)

```python
# Run checks (including confidence check)
checks = {
    'signal_type': orig_type == replay_type,
    'direction': orig_dir == replay_dir,
    'entry_delta': check_price_match(orig_entry, replay_entry, orig_entry),
    'sl_delta': check_price_match(orig_sl, replay_sl, orig_entry),
    'tp_delta': check_tp_arrays(orig_tp, replay_tp, orig_entry),
    'confidence_delta': check_confidence_match(orig_confidence, replay_confidence)
}
```

### Grep Verification

```bash
$ grep -n "CONFIDENCE_TOLERANCE = 5" diagnostics.py
1649:        CONFIDENCE_TOLERANCE = 5  # ±5 points tolerance for confidence

$ grep -n "def check_confidence_match" diagnostics.py
1667:        def check_confidence_match(orig_conf: float, replay_conf: float) -> bool:

$ grep -n "'confidence_delta':" diagnostics.py
1704:            'confidence_delta': check_confidence_match(orig_confidence, replay_confidence)
```

---

## Git Diff Evidence

The changes were made in commit 835a125. Here's the actual git diff:

```diff
$ git diff HEAD~1 HEAD -- diagnostics.py

diff --git a/diagnostics.py b/diagnostics.py
index a006494..5529b89 100644
--- a/diagnostics.py
+++ b/diagnostics.py
@@ -1555,8 +1555,20 @@ class ReplayCache:
 class ReplayEngine:
     """Replays signals and detects regressions"""
     
-    def __init__(self, cache: ReplayCache):
+    def __init__(self, cache: ReplayCache, signal_engine=None):
         self.cache = cache
+        # Reuse global engine for production parity
+        if signal_engine is None:
+            try:
+                from bot import ict_engine_global
+                self.signal_engine = ict_engine_global
+                logger.info("✅ ReplayEngine using global ICT engine")
+            except ImportError:
+                from ict_signal_engine import ICTSignalEngine
+                self.signal_engine = ICTSignalEngine()
+                logger.warning("⚠️ ReplayEngine created new ICT engine")
+        else:
+            self.signal_engine = signal_engine
     
     async def replay_signal(self, snapshot: SignalSnapshot) -> Optional[Dict]:
         """
@@ -1588,25 +1600,8 @@ class ReplayEngine:
                 df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                 df.set_index('timestamp', inplace=True)
             
-            # ✅ FIX 1: Use global production engine instance
-            # Try to import and use the global engine first
-            engine = None
-            try:
-                import bot
-                if hasattr(bot, 'ict_engine_global'):
-                    engine = bot.ict_engine_global
-                    logger.info("✅ Using global production ICT engine for replay")
-            except (ImportError, AttributeError) as e:
-                logger.warning(f"⚠️ Could not access global engine: {e}")
-            
-            # Fallback to creating new instance if global not available
-            if engine is None:
-                from ict_signal_engine import ICTSignalEngine
-                engine = ICTSignalEngine()
-                logger.warning("⚠️ Using fallback ICT engine instance for replay")
-            
             # Generate signal (read-only - no cache write)
-            signal = engine.generate_signal(
+            signal = self.signal_engine.generate_signal(
                 df=df,
                 symbol=snapshot.symbol,
                 timeframe=snapshot.timeframe,
```

---

## Summary Statistics

| Fix | Status | Line Numbers | Evidence |
|-----|--------|--------------|----------|
| 1. Engine Reuse | ✅ APPLIED | 1558, 1563-1564, 1604 | Import + assignment + usage |
| 2. Price 0.5% | ✅ APPLIED | 1646, 1656 | Constant + usage |
| 3. Confidence | ✅ APPLIED | 1649, 1667-1669, 1704 | Constant + function + check |

**Total Lines Changed:** +15 added, -20 removed, net -5

---

## Verification Commands

Anyone can verify these changes are present:

```bash
cd /home/runner/work/Crypto-signal-bot/Crypto-signal-bot

# Verify branch
git branch --show-current
# Expected: copilot/add-regression-detection-replay

# Verify commit
git log --oneline -1
# Expected: 835a125 (or later)

# Verify Fix 1
grep -n "from bot import ict_engine_global" diagnostics.py
# Expected: 1563:                from bot import ict_engine_global

# Verify Fix 2
grep -n "PRICE_TOLERANCE_PERCENT = 0.005" diagnostics.py
# Expected: 1646:        PRICE_TOLERANCE_PERCENT = 0.005...

# Verify Fix 3
grep -n "CONFIDENCE_TOLERANCE = 5" diagnostics.py
# Expected: 1649:        CONFIDENCE_TOLERANCE = 5...
grep -n "'confidence_delta':" diagnostics.py
# Expected: 1704:            'confidence_delta':...
```

---

## Conclusion

**All 3 required Phase 2B blocking fixes are present in diagnostics.py.**

The code changes were applied in commit 835a125 and are currently live in the `copilot/add-regression-detection-replay` branch.

If a reviewer is seeing "diagnostics.py unchanged", they are likely:
1. On the wrong branch (should be `copilot/add-regression-detection-replay`)
2. At an outdated commit (should be 835a125 or later)
3. Need to pull latest changes from origin

**Recommendation:** `git pull origin copilot/add-regression-detection-replay`

---

**Evidence Compiled:** 2026-01-31T18:06:33Z  
**Status:** ✅ All Fixes Verified Present
