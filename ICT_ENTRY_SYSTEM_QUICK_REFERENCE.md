# ICT Entry System - Quick Reference

## Decision Tree

```
START
  │
  ├─ Has BOS/MSS + distance 1-10% to break level?
  │   YES → ROLLBACK SCENARIO
  │   NO ↓
  │
  ├─ Has valid POI (OB/FVG) + distance 0.5-5%?
  │   YES → PULLBACK SCENARIO
  │   NO ↓
  │
  ├─ No POI in next 3% + 2+ triggers + (displacement OR structure)?
  │   YES → CONTINUATION SCENARIO
  │   NO ↓
  │
  └─ NO VALID SCENARIO → NO TRADE
```

## Scenarios at a Glance

### 🔄 ROLLBACK (Priority 1)
**When:** After structure break (BOS/MSS)
**Setup:** Price returns to break level
**Conditions:**
- ✅ BOS/MSS detected
- ✅ Break level identified
- ✅ Distance: 1% - 10%
- ✅ Price hasn't returned yet

**Entry:** At break level (±0.5%)
**Example:** BTC breaks $50k resistance → ROLLBACK to retest $50k

---

### 📉 PULLBACK (Priority 2)
**When:** Retracement to POI
**Setup:** Price pulls back to support/resistance
**Conditions:**
- ✅ Valid POI found (OB or FVG)
- ✅ POI in correct direction vs bias
- ✅ Distance: 0.5% - 5%
- ✅ POI is unmitigated

**Entry:** At POI level
**Example:** Bullish trend → price pulls back to bullish OB at $49k

---

### ⚡ CONTINUATION (Priority 3)
**When:** Strong momentum, no POI ahead
**Setup:** Aggressive entry with reduced risk
**Conditions:**
- ✅ NO POI in next 2-3%
- ✅ 2+ triggers active
- ✅ Displacement OR structure trigger

**Entry:** Near market (±0.5%)
**Position Size:** Reduced to 65%
**Example:** Strong bullish momentum + displacement → entry near current price

---

### ⛔ NO TRADE
**When:** No scenario matches
**Action:** Return NO_TRADE message
**Reason:** Conditions not met, wait for better setup

---

## Triggers

### Trigger Types
1. **MSS/BOS** - Structure break detected
2. **Liquidity Sweep** - Recent sweep event (last 4h)
3. **Displacement** - Strong momentum candle
4. **Breaker/Mitigation** - Confirmation from breaker blocks

### Trigger Scoring
- **2+ triggers** → HIGH confidence
- **1 trigger** → MEDIUM confidence
- **0 triggers** → LOW confidence (usually rejected)

---

## POI Validation Rules

### ✅ Valid POI Must Have:
1. **Correct Direction**
   - Bullish: POI below current price
   - Bearish: POI above current price

2. **Correct Distance**
   - Minimum: 0.5% from current price
   - Maximum: 5% from current price

3. **Freshness**
   - POI is unmitigated
   - POI is still valid (not swept)

4. **Type Support**
   - Order Block (OB)
   - Fair Value Gap (FVG)
   - BSL/SSL (liquidity levels)

---

## Distance Rules

### ROLLBACK
- **Minimum:** 1% from current price
- **Maximum:** 10% from current price
- **Reject if:** Price already at break level

### PULLBACK
- **Minimum:** 0.5% from current price
- **Maximum:** 5% from current price
- **Reject if:** POI is mitigated

### CONTINUATION
- **Check:** No POI in next 3%
- **Entry:** 0.5-1% from current price
- **Note:** Position size reduced to 65%

---

## Example Output

### ROLLBACK Signal
```json
{
  "scenario": {
    "type": "ROLLBACK",
    "reason": "Структурен retest след BOS/MSS. Очакваме цената да се върне към break level 49000.00 (разстояние 2.0%). Класически ICT rollback setup.",
    "triggers": ["MSS/BOS", "DISPLACEMENT"],
    "trigger_count": 2
  }
}
```

### PULLBACK Signal
```json
{
  "scenario": {
    "type": "PULLBACK",
    "reason": "Pullback към OB зона. Очакваме цената да достигне POI на 49150.00 (разстояние 1.7%). Оптимален ICT entry setup с валидна POI.",
    "triggers": ["MSS/BOS"],
    "trigger_count": 1
  }
}
```

### CONTINUATION Signal
```json
{
  "scenario": {
    "type": "CONTINUATION",
    "reason": "Continuation setup без POI в следващите 3%. Активни triggers: MSS/BOS, DISPLACEMENT. Агресивен entry близо до market (49750.00). ВНИМАНИЕ: Намален position size до 65%.",
    "triggers": ["MSS/BOS", "DISPLACEMENT"],
    "trigger_count": 2
  }
}
```

---

## Code Functions Reference

### Main Functions
```python
# Step 8.1: Entry Scenario Selection
scenario = engine._select_entry_scenario(
    df, current_price, ict_components, bias,
    has_bos_mss, break_level, triggers
)

# Helper Functions
has_bos, break_level = engine._detect_bos_mss(df, bias)
triggers = engine._calculate_triggers(df, ict_components, bias, has_bos_mss)
is_valid, info = engine._validate_poi(poi, 'OB', current_price, bias)

# Scenario Checkers
is_rollback, info = engine._check_rollback_scenario(...)
is_pullback, info = engine._check_pullback_scenario(...)
is_continuation, info = engine._check_continuation_scenario(...)
```

---

## Integration in Pipeline

```
Step 7:  Bias Determination (BULLISH/BEARISH/RANGING)
Step 8:  Entry Zone Validation (FVG/OB/SR)
Step 8.1: *** ENTRY SCENARIO SELECTION *** (NEW)
          ├─ Detect BOS/MSS
          ├─ Calculate Triggers
          ├─ Select Scenario (ROLLBACK/PULLBACK/CONTINUATION)
          └─ Return NO_TRADE if no scenario
Step 9:  SL/TP Calculation & Validation (STRICT OB)
Step 10: Risk/Reward Validation
Step 11: Confidence Calculation
...
```

---

## Key Points

✅ **Minimal Changes:** Only ~700 lines added, no existing functions modified
✅ **Backwards Compatible:** All existing functionality preserved
✅ **ICT Compliant:** True ICT entry models, not custom logic
✅ **Safety First:** NO_TRADE when conditions not met
✅ **Clear Logging:** Bulgarian explanations for each scenario
✅ **Tested:** Comprehensive test suite, all tests passing

---

## Testing

Run the test suite:
```bash
python3 test_ict_entry_system.py
```

Expected output:
```
✅ TEST 1 PASSED: BOS/MSS detection works
✅ TEST 2 PASSED: POI validation works
✅ TEST 3 PASSED: Trigger calculation works
✅ TEST 4 PASSED: ROLLBACK scenario detection works
✅ TEST 5 PASSED: PULLBACK scenario detection works
✅ TEST 6 PASSED: CONTINUATION scenario detection works
✅ TEST 7 PASSED: Entry scenario selection works
✅ ALL TESTS PASSED
```

---

## Notes

- BIAS logic unchanged (HH/HL → bullish, LH/LL → bearish)
- SL/TP logic unchanged (Step 9 validation remains STRICT)
- All existing guards and filters remain active
- Decision tree ensures only ONE scenario is selected
- If no scenario matches → NO_TRADE (not a failure, just wait)
