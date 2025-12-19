# 📊 Telegram /backtest Command

## Overview

The `/backtest` command runs comprehensive ICT backtests directly from Telegram, using the pure ICT Signal Engine without EMA or MACD indicators. Results include 80% TP alert tracking and final WIN/LOSS statistics.

## Usage

### Basic Command
```
/backtest
```
**Default behavior:**
- Tests 5 symbols: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, ADAUSDT
- Tests 3 timeframes: 1h, 4h, 1d
- Tests 30 days of historical data

### Single Symbol
```
/backtest BTCUSDT
```
Tests BTCUSDT across all default timeframes (1h, 4h, 1d) for 30 days.

### Single Symbol + Timeframe
```
/backtest BTCUSDT 1h
```
Tests BTCUSDT on 1h timeframe for 30 days.

### Custom Days
```
/backtest BTCUSDT 1h 60
```
Tests BTCUSDT on 1h timeframe for 60 days.

## Output Format

```
━━━━━━━━━━━━━━━━━━━━
📊 ICT BACKTEST RESULTS
━━━━━━━━━━━━━━━━━━━━

✅ STRATEGY:
   • Engine: ict_backtest.py ✅
   • NO EMA used ✅
   • NO MACD used ✅
   • Pure ICT Signal Engine ✅
   • 80% TP re-analysis ACTIVE ✅

📋 TESTED:
   • Symbols: 5 (BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, ADAUSDT)
   • Timeframes: 3 (1h, 4h, 1d)
   • Period: 30 days

━━━ OVERALL RESULTS ━━━
   📊 Total Trades: 87
   🟢 Wins: 52
   🔴 Losses: 35
   🎯 Win Rate: 59.8%
   💰 Total P/L: +124.50%

━━━ 80% TP ALERTS ━━━
   ⚡ Triggered: 28
   ✅ HOLD: 20 (71%)
   ⚠️ PARTIAL_CLOSE: 6 (21%)
   🔴 CLOSE_NOW: 2 (7%)

━━━ BY SYMBOL ━━━
   BTCUSDT: 18 trades | 61% WR
   ETHUSDT: 21 trades | 62% WR
   BNBUSDT: 15 trades | 53% WR
   SOLUSDT: 19 trades | 63% WR
   ADAUSDT: 14 trades | 57% WR

━━━ BY TIMEFRAME ━━━
   1h: 28 trades | 57% WR
   4h: 32 trades | 62% WR
   1d: 27 trades | 59% WR
```

## Features

### 1. Pure ICT Strategy
- ✅ Uses `ict_backtest.py` engine
- ✅ NO EMA verification
- ✅ NO MACD verification
- ✅ Pure ICT Signal Engine analysis
- ✅ Order Blocks, FVGs, Liquidity, Structure

### 2. 80% TP Alert System
When a trade reaches 80% of the way to TP1, the system re-analyzes:
- **HOLD**: Continue to TP (structure still valid)
- **PARTIAL_CLOSE**: Close 50% of position (warning signs)
- **CLOSE_NOW**: Close entire position (structure broken)

### 3. Multi-Coin & Multi-Timeframe
- Supports any Binance symbol (BTCUSDT, ETHUSDT, etc.)
- Supports timeframes: 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 1d
- Can test multiple simultaneously

### 4. Results Storage
Results are automatically saved to:
```
/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/backtest_results.json
```

Retrieve with: `/backtest_results`

## Strategy Details

### Entry Criteria
1. HTF bias (1D → 4H fallback)
2. MTF structure alignment
3. Order Block or FVG entry
4. Liquidity sweep confirmation
5. Minimum 60% confidence

### Stop Loss
- Positioned below/above Order Block (ICT compliant)
- Validated against structure
- Typical: 0.5-1.5% from entry

### Take Profit
- TP1: Minimum 3:1 Risk/Reward (guaranteed)
- TP2/TP3: Aligned with Fibonacci extensions or liquidity
- Typical RR: 3:1 to 8:1

### 80% TP Alert Logic
When price reaches 80% of distance to TP1:
1. Re-analyze current structure
2. Check for displacement against position
3. Check for liquidity sweep reversal
4. Recommend HOLD, PARTIAL_CLOSE, or CLOSE_NOW

## Performance Metrics

### Overall Statistics
- **Total Trades**: All signals generated and executed
- **Wins**: Trades that hit TP1, TP2, or TP3
- **Losses**: Trades that hit SL
- **Win Rate**: (Wins / Total Trades) × 100
- **Total P/L**: Sum of all trade P/L percentages

### By Symbol
- Shows performance breakdown per trading pair
- Helps identify best-performing assets

### By Timeframe
- Shows performance breakdown per timeframe
- 4H typically has highest win rate
- 1D has fewer trades but higher avg profit
- 1H has most trades but more noise

## Tips for Best Results

### 1. Timeframe Selection
- **1H**: More signals, higher noise, needs tight management
- **4H**: Balance of signals and quality (recommended)
- **1D**: Fewer signals, higher quality, longer hold times

### 2. Period Selection
- **15-30 days**: Good for recent market conditions
- **60-90 days**: More comprehensive statistics
- **>90 days**: May include outdated market regime

### 3. Symbol Selection
- Test majors first: BTCUSDT, ETHUSDT
- High liquidity pairs perform better
- Avoid low-volume altcoins

### 4. Interpreting 80% Alerts
- High HOLD %: Strategy has good continuation
- High PARTIAL_CLOSE %: Markets are choppy
- High CLOSE_NOW %: Consider reviewing entry criteria

## Troubleshooting

### "ICT Backtest not available"
**Solution**: Check that `ict_backtest.py` is present and ICTSignalEngine is working.

### "No results" or very few trades
**Possible causes:**
- Insufficient historical data
- Very strict entry criteria
- Low confidence threshold (60%)

**Solution:**
- Increase period (e.g., 60 days)
- Check if symbol data is available
- Review confidence threshold in code

### Timeout errors
**Cause**: Testing too many combinations or too long period

**Solution:**
- Reduce number of symbols
- Reduce number of timeframes
- Reduce period to 30 days

## See Also

- [ICT Signal Engine](../ICT_INTEGRATION_COMPLETE.md)
- [13-Point Output Format](13_POINT_OUTPUT.md)
- [Fibonacci Guide](FIBONACCI_GUIDE.md)
