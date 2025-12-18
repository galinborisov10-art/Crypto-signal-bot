# 🎯 Unified ICT Analysis Guide

## Overview

This guide documents the **Unified ICT Analysis System** that ensures ALL ICT signals (manual AND automatic) follow the SAME analysis sequence across ALL timeframes from 1 week down to 1 minute.

---

## 📊 Supported Timeframes

The system supports analysis on the following timeframes:

```python
SUPPORTED_TIMEFRAMES = [
    '1w',   # 1 week (Ultra HTF) ✅
    '1d',   # 1 day (HTF)
    '4h',   # 4 hours (MTF)
    '3h',   # 3 hours
    '2h',   # 2 hours
    '1h',   # 1 hour (Entry TF)
    '30m',  # 30 minutes
    '15m',  # 15 minutes
    '5m',   # 5 minutes
    '1m'    # 1 minute (LTF)
]
```

**Note:** All timeframes follow the EXACT SAME analysis sequence.

---

## 🔄 12-Step Unified Analysis Sequence

Every signal, regardless of timeframe or trigger type (manual `/signal` or automatic backtest), follows this mandatory sequence:

### Step 1: HTF Bias (1D → 4H Fallback)
```python
htf_bias = _get_htf_bias_with_fallback(symbol, mtf_data)
```
- **Primary:** Try 1D timeframe bias
- **Fallback:** If 1D unavailable or insufficient data → use 4H
- **Default:** NEUTRAL if both fail

### Step 2: MTF Structure (4H)
```python
mtf_analysis = _analyze_mtf_confluence(df, mtf_data, symbol)
```
- Analyzes multi-timeframe structure
- Identifies confluence across timeframes
- Returns structure type (BULLISH/BEARISH/RANGING)

### Step 3: Entry Model (Current TF)
```python
# Prepares entry analysis for current timeframe
```
- Uses the timeframe specified in signal request
- Applies ICT entry models

### Step 4: Liquidity Map (Fresh → Cache Fallback)
```python
liquidity_zones = _get_liquidity_zones_with_fallback(symbol, timeframe)
```
- **Primary:** Try fresh liquidity mapping
- **Fallback:** Use cached liquidity zones if fresh mapping fails
- **Default:** Empty list if both fail

### Step 5-7: ICT Components Detection
```python
ict_components = _detect_ict_components(df, timeframe)
bias = _determine_market_bias(df, ict_components, mtf_analysis)
structure_broken = _check_structure_break(df)
displacement_detected = _check_displacement(df)
```

Detects:
- **Order Blocks (OB):** Institutional entry zones
- **Fair Value Gaps (FVG):** Price imbalances
- **Whale Blocks:** Large order zones
- **Internal Liquidity Pools (ILP):** Hidden liquidity
- **Breaker Blocks:** Failed order blocks
- **Mitigation Blocks:** Partially filled OBs
- **SIBI/SSIB Zones:** Institutional levels
- **Liquidity Sweeps:** Stop hunts
- **Market Manipulation:** ICT manipulation patterns

### Step 8: Entry Calculation
```python
entry_setup = _identify_entry_setup(df, ict_components, bias)
entry_price = _calculate_entry_price(df, entry_setup, bias)
```
- Identifies optimal entry zone
- Calculates precise entry price
- Considers OB/FVG alignment

### Step 9: SL/TP Calculation + Validation
```python
sl_price = _calculate_sl_price(df, entry_setup, entry_price, bias)

# ✅ MANDATORY SL VALIDATION
if order_block:
    sl_price = _validate_sl_position(sl_price, order_block, bias)

# ✅ GUARANTEED RR ≥ 3.0
tp_prices = _calculate_tp_with_min_rr(entry_price, sl_price, liquidity_zones, min_rr=3.0)
```

**Critical Requirements:**
- **BULLISH:** SL MUST be BELOW Order Block bottom
- **BEARISH:** SL MUST be ABOVE Order Block top
- **TP1:** GUARANTEED Risk/Reward ≥ 1:3
- **TP2/TP3:** Aligned with liquidity zones or extended levels

### Step 10: RR Guarantee Check
```python
risk = abs(entry_price - sl_price)
reward = abs(tp_prices[0] - entry_price)
risk_reward_ratio = reward / risk

if risk_reward_ratio < 3.0:
    # Auto-adjust TP1 to guarantee 3.0 RR
    tp_prices[0] = entry_price + (risk * 3.0)  # BULLISH
    # OR
    tp_prices[0] = entry_price - (risk * 3.0)  # BEARISH
```

### Step 11: ML Optimization
```python
# ML prediction and confidence adjustment
ml_features = _extract_ml_features(...)
# Apply ML Engine or ML Predictor
# Adjust confidence based on ML prediction
```

**ML Integration:**
- Uses SAME ML features for ALL timeframes
- Adjusts confidence based on historical performance
- Can override signal direction if confidence delta > threshold

### Step 12: Final Confidence Scoring
```python
signal_strength = _calculate_signal_strength(...)
signal_type = _determine_signal_type(bias, signal_strength, confidence)
reasoning = _generate_reasoning(...)
warnings = _generate_warnings(...)
```

---

## ✅ Mandatory Signal Elements

Every generated signal MUST contain:

```python
signal = {
    'entry_price': float,      # ✅ Exact entry price (REQUIRED)
    'sl_price': float,         # ✅ SL below/above OB (REQUIRED, VALIDATED)
    'tp_prices': List[float],  # ✅ [TP1, TP2, TP3] (TP1 REQUIRED, RR ≥ 3.0)
    'risk_reward_ratio': float,# ✅ Actual RR (GUARANTEED ≥ 3.0)
    'confidence': float,       # ✅ 0-100% confidence score
    'signal_type': SignalType, # ✅ BUY/SELL/STRONG_BUY/STRONG_SELL
    'timeframe': str,          # ✅ Current timeframe
    'htf_bias': str,           # ✅ HTF bias from 1D or 4H
    'bias': MarketBias,        # ✅ Current TF bias
    # ... ICT components ...
}
```

---

## 🔒 SL Validation Rules

### BULLISH Signal (BUY/STRONG_BUY)
```
Order Block:  [══════════]  <- OB top
              [          ]
              [══════════]  <- OB bottom
                    ↓
                   SL  ← MUST be BELOW OB bottom
```

**Validation:**
```python
if sl_price >= ob_bottom:
    sl_price = ob_bottom * 0.998  # Force 0.2% below
```

### BEARISH Signal (SELL/STRONG_SELL)
```
                   SL  ← MUST be ABOVE OB top
                    ↑
Order Block:  [══════════]  <- OB top
              [          ]
              [══════════]  <- OB bottom
```

**Validation:**
```python
if sl_price <= ob_top:
    sl_price = ob_top * 1.002  # Force 0.2% above
```

---

## 💰 TP Calculation with Guaranteed RR

### Minimum RR 1:3
```python
risk = abs(entry - sl)
tp1 = entry + (risk * 3.0)  # LONG
tp1 = entry - (risk * 3.0)  # SHORT
```

### Liquidity-Aligned TPs
```python
# TP2 & TP3 aligned with liquidity zones if available
for liq_zone in liquidity_zones:
    if direction == 'LONG' and liq_price > tp1:
        tp_levels.append(liq_price)
    elif direction == 'SHORT' and liq_price < tp1:
        tp_levels.append(liq_price)
```

### Extended TPs (No Liquidity)
```python
tp2 = entry + (risk * 5)  # 5R
tp3 = entry + (risk * 8)  # 8R
```

---

## 🤖 ML Integration

### Feature Extraction
ML features are IDENTICAL across ALL timeframes:

```python
ml_features = {
    # Neutral Indicators
    'rsi': float,
    'volume_ratio': float,
    'volatility': float,
    'bb_position': float,
    
    # ICT Metrics
    'num_order_blocks': int,
    'num_fvgs': int,
    'num_whale_blocks': int,
    'num_liquidity_zones': int,
    'liquidity_strength': float,
    
    # Structure
    'structure_broken': bool,
    'displacement_detected': bool,
    'ict_confidence': float,
    
    # MTF
    'mtf_confluence': int,
    'htf_bias_aligned': bool
}
```

### ML Application
```python
# Step 1: Extract features
ml_features = _extract_ml_features(df, ict_components, ...)

# Step 2: ML Prediction (if trained)
if ml_engine:
    ml_signal, ml_confidence, ml_mode = ml_engine.predict_signal(...)
    ml_adjustment = ml_confidence - base_confidence

# Step 3: Apply adjustment (clamped to limits)
final_confidence = base_confidence + ml_adjustment
```

---

## 📋 Usage Examples

### Example 1: Manual Signal (Any Timeframe)
```python
from ict_signal_engine import ICTSignalEngine

engine = ICTSignalEngine()

# Works for 1w, 1d, 4h, 1h, 15m, 5m, 1m, etc.
signal = engine.generate_signal(
    df=df_price_data,
    symbol='BTCUSDT',
    timeframe='15m',  # Any supported timeframe
    mtf_data={
        '1d': df_1d,
        '4h': df_4h
    }
)

if signal:
    print(f"Entry: {signal.entry_price}")
    print(f"SL: {signal.sl_price}")
    print(f"TP1: {signal.tp_prices[0]} (RR: {signal.risk_reward_ratio:.2f})")
```

### Example 2: Backtest (Automatic Signals)
```python
# Backtest uses SAME generate_signal() method
for timestamp, df_window in backtest_data:
    signal = engine.generate_signal(
        df=df_window,
        symbol='BTCUSDT',
        timeframe='1h',
        mtf_data=mtf_windows
    )
    
    if signal:
        # Signal has SAME guarantees as manual signals
        assert signal.risk_reward_ratio >= 3.0
        assert signal.entry_price > 0
        # ... execute trade ...
```

### Example 3: Multi-Timeframe Analysis
```python
# Same engine, different timeframes
timeframes = ['1w', '1d', '4h', '1h', '15m']

for tf in timeframes:
    signal = engine.generate_signal(df, 'BTCUSDT', tf, mtf_data)
    if signal:
        print(f"{tf}: {signal.signal_type.value} @ {signal.entry_price}")
```

---

## 🛡️ Safety Guarantees

### 1. RR Never Below 3.0
```python
if risk_reward_ratio < 3.0:
    # Auto-adjust TP1
    tp_prices[0] = entry + (risk * 3.0)
    risk_reward_ratio = 3.0
```

### 2. SL Always Validated
```python
# ALWAYS runs validation
sl_price = _validate_sl_position(sl_price, order_block, bias)
```

### 3. HTF Bias Fallback
```python
# 1D → 4H → NEUTRAL
htf_bias = _get_htf_bias_with_fallback(symbol, mtf_data)
```

### 4. Liquidity Cache Fallback
```python
# Fresh → Cache → Empty
liquidity_zones = _get_liquidity_zones_with_fallback(symbol, timeframe)
```

---

## 🔍 Troubleshooting

### Issue: No Signal Generated
**Possible Causes:**
1. Confidence < minimum threshold
2. RR < minimum (should auto-adjust)
3. No valid entry setup found
4. Insufficient data (< 50 candles)

**Solution:**
- Check logs for specific rejection reason
- Verify data quality
- Adjust config thresholds if needed

### Issue: Wrong SL Position
**Should NOT happen** - SL validation is automatic.

If it does:
1. Check Order Block detection
2. Verify `_validate_sl_position()` is called
3. Review OB structure (zone_low/zone_high)

### Issue: RR Below 3.0
**Should NOT happen** - RR guarantee is automatic.

If it does:
1. Check `_calculate_tp_with_min_rr()` logic
2. Verify Step 10 RR check is running
3. Review logs for adjustment messages

### Issue: Different Results for Same TF
**Expected if:**
- Data changed (new candles)
- Cache expired
- ML model updated

**Unexpected if:**
- Same input data
- Same timestamp
- Cache should be identical

---

## 📚 API Reference

### Main Method
```python
ICTSignalEngine.generate_signal(
    df: pd.DataFrame,           # OHLCV data
    symbol: str,                # e.g., 'BTCUSDT'
    timeframe: str = "1H",      # Any supported TF
    mtf_data: Optional[Dict] = None  # {tf: df}
) -> Optional[ICTSignal]
```

### New Validation Methods
```python
_validate_sl_position(sl_price, order_block, direction) -> float
_get_htf_bias_with_fallback(symbol, mtf_data) -> str
_get_liquidity_zones_with_fallback(symbol, timeframe) -> List
_calculate_tp_with_min_rr(entry, sl, liq_zones, min_rr=3.0) -> List[float]
```

### ICTSignal Object
```python
@dataclass
class ICTSignal:
    timestamp: datetime
    symbol: str
    timeframe: str
    signal_type: SignalType
    signal_strength: SignalStrength
    entry_price: float
    sl_price: float
    tp_prices: List[float]
    confidence: float
    risk_reward_ratio: float
    # ... ICT components ...
    htf_bias: str
    bias: MarketBias
    reasoning: str
    warnings: List[str]
```

---

## ✅ Testing

Run the unified tests:
```bash
python3 tests/test_unified_ict_analysis.py
```

Expected output:
```
🎯 UNIFIED ICT ANALYSIS TESTS
============================================================
✅ PASS: All Timeframes
✅ PASS: SL Validation
✅ PASS: RR Guarantee
✅ PASS: Unified Sequence

✅ ALL TESTS PASSED!
```

---

## 🔄 Version History

- **v2.0** (2025-12-18): Unified ICT Analysis System
  - 12-step unified sequence
  - Support for 1w-1m timeframes
  - Guaranteed RR ≥ 3.0
  - SL validation below/above OB
  - HTF bias fallback
  - Liquidity cache fallback

---

## 📞 Support

For issues or questions:
1. Check logs for detailed error messages
2. Run tests to verify installation
3. Review this guide for proper usage
4. Check GitHub issues

---

**Last Updated:** 2025-12-18  
**Author:** galinborisov10-art  
**License:** Private
