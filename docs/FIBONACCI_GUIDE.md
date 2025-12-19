# 📐 Fibonacci Analysis Guide

## Overview

The Fibonacci Analyzer is a powerful tool integrated into the ICT Signal Engine that uses Fibonacci retracement and extension levels to optimize trade entries and take profit targets.

## Key Features

### 1. Fibonacci Retracement Levels

Standard Fibonacci retracement levels used:
- **23.6%** - Minor retracement
- **38.2%** - Moderate retracement
- **50.0%** - Half retracement (psychological level)
- **61.8%** - Golden ratio retracement
- **78.6%** - Deep retracement

### 2. Fibonacci Extension Levels

Extension levels for take profit targets:
- **127.2%** - First extension target
- **141.4%** - Square root of 2 extension
- **161.8%** - Golden ratio extension
- **200.0%** - Double extension
- **261.8%** - Extended target

### 3. OTE (Optimal Trade Entry) Zone

The OTE zone is a critical ICT concept representing the **optimal entry area** between:
- **62% retracement** (lower bound)
- **79% retracement** (upper bound)

This zone represents where institutional traders typically enter positions after a pullback.

## Integration with ICT Signal Engine

### Automatic Analysis

Called automatically in `_detect_ict_components()`.

### Confidence Boosting

When price is in the OTE zone, signal confidence increases by **+10%**.

### TP Optimization

Take profit levels are aligned with Fibonacci extension levels.

**Priority Order for TP Calculation:**
1. ✅ **Guaranteed TP1** at 3:1 Risk/Reward (minimum)
2. 💎 **Fibonacci Extensions** (if available)
3. 🎯 **Liquidity Zones** (fallback)
4. 📊 **Structural Levels** (5R, 8R - final fallback)

## Best Practices

### Lookback Period
- **Default: 50 candles** - Works well for most timeframes
- **1H/4H: 50-100 candles** - Captures significant swings
- **1D: 30-50 candles** - Avoids too long history

### OTE Zone Entry
- ✅ **Wait for price in OTE zone** before entry
- ✅ **Confirm with other ICT concepts** (Order Blocks, FVGs)
- ✅ **Higher confidence** when all align

## See Also

- [13-Point Output Format](13_POINT_OUTPUT.md)
- [LuxAlgo Integration](LUXALGO_INTEGRATION.md)
