# ICT Signal Engine Diagnostic Logging Guide

## Overview

This document describes the step-level diagnostic logging added to the ICT 12-step signal generation pipeline to identify exactly where and why signals fall back to HOLD.

## Implementation Summary

**File Modified**: `ict_signal_engine.py`

**Changes Made**: Added `logger.info()` statements at each decision point in the pipeline

**Logic Changes**: **NONE** - Pure observability changes only

## Logging Format

### Standard Format
Each step follows this format:

```
🔍 Step {N}: {Description}
   → {Metric}: {Value}
   → {Calculation breakdown}
✅ PASSED Step {N}: {reason}
or
❌ BLOCKED at Step {N}: {reason}
```

## Step-by-Step Logging Details

### Step 1-6: Initialization
Basic logging already exists for:
- Step 1: HTF Bias
- Step 2: MTF Structure
- Step 3: Entry Model
- Step 4: Liquidity Map
- Steps 5-6: ICT Components detection

### Step 7: Bias Determination
**NEW DIAGNOSTIC LOGGING:**

```python
logger.info("🔍 Step 7: Bias Determination")
logger.info("   → Bias Calculation Breakdown:")
logger.info(f"      • OB Score: {ob_score} (Bullish: {bullish_obs}, Bearish: {bearish_obs})")
logger.info(f"      • FVG Score: {fvg_score} (Bullish: {bullish_fvgs}, Bearish: {bearish_fvgs})")
logger.info(f"      • MTF Bias: {mtf_bias_str}")
logger.info(f"      • Structure Broken: {structure_broken}")
logger.info(f"      • Displacement Detected: {displacement_detected}")
logger.info(f"   → Final Bias: {bias.value}")
```

**Example Output:**
```
2026-01-12 12:00:00 - INFO - 🔍 Step 7: Bias Determination
2026-01-12 12:00:00 - INFO -    → Bias Calculation Breakdown:
2026-01-12 12:00:00 - INFO -       • OB Score: -3 (Bullish: 0, Bearish: 3)
2026-01-12 12:00:00 - INFO -       • FVG Score: 0 (Bullish: 0, Bearish: 0)
2026-01-12 12:00:00 - INFO -       • MTF Bias: NEUTRAL
2026-01-12 12:00:00 - INFO -       • Structure Broken: False
2026-01-12 12:00:00 - INFO -       • Displacement Detected: False
2026-01-12 12:00:00 - INFO -    → Final Bias: RANGING
```

### Step 7b: Early Exit Check
**NEW DIAGNOSTIC LOGGING:**

```python
if bias in [MarketBias.NEUTRAL, MarketBias.RANGING]:
    logger.info("🔍 Step 7b: Early Exit Check")
    logger.info(f"   → Bias is {bias.value} (not directional)")
    logger.info(f"❌ BLOCKED at Step 7b: {symbol} bias is {bias.value} (early exit)")
    logger.info(f"✅ Generating HOLD signal (blocked_at_step: 7b, reason: {bias.value} bias)")
```

**Example Output:**
```
2026-01-12 12:00:00 - INFO - 🔍 Step 7b: Early Exit Check
2026-01-12 12:00:00 - INFO -    → Bias is RANGING (not directional)
2026-01-12 12:00:00 - INFO - ❌ BLOCKED at Step 7b: BTCUSDT bias is RANGING (early exit)
2026-01-12 12:00:00 - INFO - ✅ Generating HOLD signal (blocked_at_step: 7b, reason: RANGING bias)
```

### Step 8: Entry Zone Validation
**NEW DIAGNOSTIC LOGGING:**

```python
logger.info("🔍 Step 8: Entry Zone Validation")
logger.info(f"   → Current Price: ${current_price:.2f}")
logger.info("   → Available ICT Components:")
logger.info(f"      • Order Blocks: {len(order_blocks)}")
logger.info(f"      • FVG Zones: {len(fvg_zones)}")
logger.info(f"      • S/R Levels: {sr_count}")
logger.info(f"   → Entry Zone Status: {entry_status}")
if entry_zone:
    logger.info(f"      • Zone Center: ${entry_zone['center']:.2f}")
    logger.info(f"      • Source: {entry_zone['source']}")
```

**Success Case:**
```
2026-01-12 12:00:00 - INFO - 🔍 Step 8: Entry Zone Validation
2026-01-12 12:00:00 - INFO -    → Current Price: $50000.00
2026-01-12 12:00:00 - INFO -    → Available ICT Components:
2026-01-12 12:00:00 - INFO -       • Order Blocks: 3
2026-01-12 12:00:00 - INFO -       • FVG Zones: 2
2026-01-12 12:00:00 - INFO -       • S/R Levels: 4
2026-01-12 12:00:00 - INFO -    → Entry Zone Status: VALID_NEAR
2026-01-12 12:00:00 - INFO -       • Zone Center: $49800.00
2026-01-12 12:00:00 - INFO -       • Source: ORDER_BLOCK
2026-01-12 12:00:00 - INFO - ✅ PASSED Step 8: Entry zone validated (VALID_NEAR)
```

**Failure Case:**
```
2026-01-12 12:00:00 - INFO - 🔍 Step 8: Entry Zone Validation
2026-01-12 12:00:00 - INFO -    → Entry Zone Status: TOO_LATE
2026-01-12 12:00:00 - INFO - ❌ BLOCKED at Step 8: Entry zone validation failed (TOO_LATE)
2026-01-12 12:00:00 - INFO - ✅ Generating NO_TRADE (blocked_at_step: 8, reason: Price already passed entry zone)
```

### Step 9: SL/TP Calculation
**NEW DIAGNOSTIC LOGGING:**

```python
logger.info("🔍 Step 9: SL/TP Calculation & Validation")
logger.info(f"   → Calculated SL: ${sl_price:.2f}")
logger.info("   → Validating SL against Order Block")
logger.info(f"      • OB Range: ${ob.zone_low:.2f} - ${ob.zone_high:.2f}")
logger.info(f"   → SL validated: ${sl_price:.2f}")
logger.info(f"   → TP Levels: {tp_prices}")
logger.info("✅ PASSED Step 9: SL/TP calculated and validated")
```

**Example Output:**
```
2026-01-12 12:00:00 - INFO - 🔍 Step 9: SL/TP Calculation & Validation
2026-01-12 12:00:00 - INFO -    → Calculated SL: $49200.00
2026-01-12 12:00:00 - INFO -    → Validating SL against Order Block
2026-01-12 12:00:00 - INFO -       • OB Range: $49300.00 - $49500.00
2026-01-12 12:00:00 - INFO -    → SL validated: $49200.00
2026-01-12 12:00:00 - INFO -    → TP Levels: ['$51600.00', '$53400.00', '$56200.00']
2026-01-12 12:00:00 - INFO - ✅ PASSED Step 9: SL/TP calculated and validated
```

### Step 10: Risk/Reward Validation
**NEW DIAGNOSTIC LOGGING:**

```python
logger.info("🔍 Step 10: Risk/Reward Validation")
logger.info(f"   → Risk: ${risk:.2f}")
logger.info(f"   → Reward (TP1): ${reward:.2f}")
logger.info(f"   → RR Ratio: {risk_reward_ratio:.2f}")
logger.info(f"   → Minimum Required: {min_risk_reward:.2f}")
logger.info(f"✅ PASSED Step 10: RR validated ({rr:.2f} ≥ {min:.2f})")
```

**Example Output:**
```
2026-01-12 12:00:00 - INFO - 🔍 Step 10: Risk/Reward Validation
2026-01-12 12:00:00 - INFO -    → Risk: $800.00
2026-01-12 12:00:00 - INFO -    → Reward (TP1): $2600.00
2026-01-12 12:00:00 - INFO -    → RR Ratio: 3.25
2026-01-12 12:00:00 - INFO -    → Minimum Required: 3.00
2026-01-12 12:00:00 - INFO - ✅ PASSED Step 10: RR validated (3.25 ≥ 3.00)
```

### Step 11: Confidence Validation
**NEW DIAGNOSTIC LOGGING:**

```python
logger.info("🔍 Step 11: Confidence Calculation")
logger.info(f"   → Base Confidence: {base_confidence:.1f}%")
logger.info(f"   → Final Confidence (after ML): {confidence:.1f}%")

logger.info("🔍 Step 11.5: MTF Consensus Validation")
logger.info(f"   → MTF Consensus: {consensus_pct:.1f}%")
logger.info(f"   → Aligned TFs: {aligned}/{total}")
logger.info(f"   → Minimum Required: 50%")
logger.info(f"✅ PASSED Step 11.5: MTF consensus validated ({pct:.1f}% ≥ 50%)")

logger.info("🔍 Step 11.6: Final Confidence Check")
logger.info(f"   → Final Confidence: {confidence:.1f}%")
logger.info(f"   → Minimum Required: {min_confidence}%")
logger.info(f"✅ PASSED Step 11.6: Confidence validated ({conf:.1f}% ≥ {min}%)")
```

**Example Output:**
```
2026-01-12 12:00:00 - INFO - 🔍 Step 11: Confidence Calculation
2026-01-12 12:00:00 - INFO -    → Base Confidence: 68.0%
2026-01-12 12:00:00 - INFO -    → Final Confidence (after ML): 72.0%
2026-01-12 12:00:00 - INFO - 🔍 Step 11.5: MTF Consensus Validation
2026-01-12 12:00:00 - INFO -    → MTF Consensus: 80.0%
2026-01-12 12:00:00 - INFO -    → Aligned TFs: 4/5
2026-01-12 12:00:00 - INFO -    → Minimum Required: 50%
2026-01-12 12:00:00 - INFO - ✅ PASSED Step 11.5: MTF consensus validated (80.0% ≥ 50%)
2026-01-12 12:00:00 - INFO - 🔍 Step 11.6: Final Confidence Check
2026-01-12 12:00:00 - INFO -    → Final Confidence: 72.0%
2026-01-12 12:00:00 - INFO -    → Minimum Required: 60%
2026-01-12 12:00:00 - INFO - ✅ PASSED Step 11.6: Confidence validated (72.0% ≥ 60%)
```

### Step 12: Final Signal Generation
**NEW DIAGNOSTIC LOGGING:**

```python
logger.info("🔍 Step 12: Final Signal Generation")
logger.info(f"   → Signal Type: {signal_type.value}")
logger.info(f"   → Signal Strength: {signal_strength.value}")
logger.info(f"   → Confidence: {confidence:.1f}%")
logger.info("=" * 60)
logger.info("✅ SIGNAL GENERATION COMPLETE")
logger.info(f"   Signal Type: {signal_type.value}")
logger.info(f"   Entry: ${entry_price:.2f}")
logger.info(f"   SL: ${sl_price:.2f}")
logger.info(f"   TP1: ${tp_prices[0]:.2f}")
logger.info(f"   RR: {risk_reward_ratio:.2f}")
logger.info(f"   Confidence: {confidence:.1f}%")
logger.info("=" * 60)
```

**Example Output:**
```
2026-01-12 12:00:00 - INFO - 🔍 Step 12: Final Signal Generation
2026-01-12 12:00:00 - INFO -    → Signal Type: BUY
2026-01-12 12:00:00 - INFO -    → Signal Strength: STRONG
2026-01-12 12:00:00 - INFO -    → Confidence: 72.0%
2026-01-12 12:00:00 - INFO - ============================================================
2026-01-12 12:00:00 - INFO - ✅ SIGNAL GENERATION COMPLETE
2026-01-12 12:00:00 - INFO -    Signal Type: BUY
2026-01-12 12:00:00 - INFO -    Entry: $49800.00
2026-01-12 12:00:00 - INFO -    SL: $49200.00
2026-01-12 12:00:00 - INFO -    TP1: $51600.00
2026-01-12 12:00:00 - INFO -    RR: 3.25
2026-01-12 12:00:00 - INFO -    Confidence: 72.0%
2026-01-12 12:00:00 - INFO - ============================================================
```

## Blocked Signal Examples

### Example 1: Blocked at Step 7b (RANGING Bias)
```
2026-01-12 12:00:00 - INFO - 🔍 Step 7: Bias Determination
2026-01-12 12:00:00 - INFO -    → Final Bias: RANGING
2026-01-12 12:00:00 - INFO - 🔍 Step 7b: Early Exit Check
2026-01-12 12:00:00 - INFO - ❌ BLOCKED at Step 7b: BTCUSDT bias is RANGING (early exit)
2026-01-12 12:00:00 - INFO - ✅ Generating HOLD signal (blocked_at_step: 7b, reason: RANGING bias)
```

### Example 2: Blocked at Step 9 (No Order Block)
```
2026-01-12 12:00:00 - INFO - 🔍 Step 9: SL/TP Calculation & Validation
2026-01-12 12:00:00 - INFO - ❌ BLOCKED at Step 9: No Order Block for SL validation
```

### Example 3: Blocked at Step 10 (Insufficient RR)
```
2026-01-12 12:00:00 - INFO - 🔍 Step 10: Risk/Reward Validation
2026-01-12 12:00:00 - INFO -    → RR Ratio: 2.15
2026-01-12 12:00:00 - INFO - ❌ BLOCKED at Step 10: RR 2.15 < 3.0
```

### Example 4: Blocked at Step 11.5 (Low MTF Consensus)
```
2026-01-12 12:00:00 - INFO - 🔍 Step 11.5: MTF Consensus Validation
2026-01-12 12:00:00 - INFO -    → MTF Consensus: 40.0%
2026-01-12 12:00:00 - INFO - ❌ BLOCKED at Step 11.5: MTF consensus 40.0% < 50%
```

### Example 5: Blocked at Step 11.6 (Low Confidence)
```
2026-01-12 12:00:00 - INFO - 🔍 Step 11.6: Final Confidence Check
2026-01-12 12:00:00 - INFO -    → Final Confidence: 55.0%
2026-01-12 12:00:00 - INFO - ❌ BLOCKED at Step 11.6: Confidence 55.0% < 60%
```

## Using the Diagnostic Logs

### Log Analysis Workflow

1. **Run the bot for 1-2 hours** to collect diagnostic data
2. **Extract blocked signals** using grep:
   ```bash
   grep "BLOCKED at Step" bot.log | sort | uniq -c
   ```
3. **Analyze blocked_at_step distribution**:
   ```
   768 ❌ BLOCKED at Step 7b: bias is RANGING
    12 ❌ BLOCKED at Step 9: No Order Block
     5 ❌ BLOCKED at Step 11.5: MTF consensus < 50%
     3 ❌ BLOCKED at Step 11.6: Confidence < 60%
   ```
4. **Identify root cause** from the most common blocker
5. **Create targeted fix** based on data

### Common Blockers and Potential Fixes

| Blocker | Likely Cause | Potential Fix |
|---------|-------------|---------------|
| Step 7b: RANGING bias | Bias calculation too strict | Adjust bias scoring weights |
| Step 9: No OB | OB detection not working | Fix OB detector or relax requirements |
| Step 10: RR < 3.0 | TP too close or SL too wide | Adjust TP calculation logic |
| Step 11.5: MTF < 50% | MTF timeframes not aligned | Review MTF consensus logic |
| Step 11.6: Confidence < 60% | Confidence scoring too conservative | Review confidence calculation |

## Safety Guarantees

✅ **No Logic Changes**: Only `logger.info()` statements added
✅ **No Variable Modifications**: All calculations remain unchanged
✅ **No Threshold Changes**: All minimum requirements unchanged
✅ **No Control Flow Changes**: Decision logic identical
✅ **100% Backwards Compatible**: Existing behavior preserved

## Testing

Run the diagnostic test:
```bash
python3 test_diagnostic_logging.py
```

Expected output includes detailed step-by-step logging showing exactly where signals are blocked.

## Security

**CodeQL Scan**: 0 alerts ✅
**Code Review**: All comments addressed ✅
