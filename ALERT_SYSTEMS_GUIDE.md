# Alert Systems Guide

## Overview

This guide explains the 80% Alert and Final Alert systems that monitor active trades and log results to `trading_journal.json`.

## Features

### 1. 80% Alert System

Automatically monitors active trades and sends alerts when price reaches 80% of the distance to Take Profit.

**How it works:**
- Runs every 1 minute via APScheduler
- Checks all active trades in the `active_trades` list
- Calculates progress toward TP for each trade
- Sends one-time Telegram alert when 80% threshold is reached
- Recommends taking 50% partial profit and moving SL to breakeven

**Alert format:**
```
📊 80% ALERT - BTCUSDT
━━━━━━━━━━━━━━━━━━━━━━━

🎯 Your LONG trade has reached 80% to TP!

📍 Entry: 50,000.00
📈 Current: 51,200.00
🎯 TP: 51,500.00
🛑 SL: 49,000.00

📊 Progress: 80.0% to TP

💡 Recommendation:
Consider taking 50% partial profit to secure gains.
Move SL to breakeven for remaining position.

⏰ 2025-12-23 15:30 UTC
```

### 2. Final Alert System

Sends final notifications when trades close (TP or SL hit) and logs results to `trading_journal.json`.

**How it works:**
- Triggered when a trade closes (manually or automatically)
- Calculates P/L percentage and absolute P/L
- Determines outcome (WIN/LOSS)
- Sends Telegram notification with results
- Logs complete trade data to journal
- Updates overall statistics (win rate, total trades, etc.)

**Alert format (WIN):**
```
✅ BTCUSDT CLOSED - WIN
━━━━━━━━━━━━━━━━━━━━━━━

📍 Entry: 50,000.00
📍 Exit: 51,500.00 (TP)
💰 P/L: +3.00% ($150.00)
⏱️ Duration: 8.5 hours

📊 80% Alert: ✅ Triggered at 51,200.00

⏰ 2025-12-23 18:30 UTC
```

**Alert format (LOSS):**
```
❌ BTCUSDT CLOSED - LOSS
━━━━━━━━━━━━━━━━━━━━━━━

📍 Entry: 50,000.00
📍 Exit: 49,000.00 (SL)
💰 P/L: -2.00% ($-100.00)
⏱️ Duration: 2.3 hours

⏰ 2025-12-23 12:18 UTC
```

## Commands

### `/active_trades`

View all active trades currently being monitored.

**Usage:**
```
/active_trades
```

**Output:**
```
📊 Active Trades (2)
━━━━━━━━━━━━━━━━━━━━━━━

1. BTCUSDT LONG
   Entry: 50,000.00
   Current: 50,800.00
   Progress: 53.3% to TP
   80% Alert: ⏳ Monitoring

2. ETHUSDT SHORT
   Entry: 3,000.00
   Current: 2,920.00
   Progress: 80.0% to TP
   80% Alert: ✅ Alerted

⏰ 2025-12-23 15:45 UTC
```

### `/close_trade`

Manually close an active trade (for manual trade management).

**Usage:**
```
/close_trade BTCUSDT TP
/close_trade ETHUSDT SL
```

**Parameters:**
- `SYMBOL` - Trading pair (e.g., BTCUSDT, ETHUSDT)
- `TARGET` - Exit target: `TP` (Take Profit) or `SL` (Stop Loss)

**Output:**
```
✅ Trade closed manually: BTCUSDT at TP
```

This will:
1. Send final alert notification
2. Log trade to `trading_journal.json`
3. Update statistics
4. Remove trade from active monitoring

## Trading Journal Structure

Trades are logged to `trading_journal.json` with the following structure:

```json
{
  "trades": [
    {
      "timestamp": "2025-12-23T10:00:00+00:00",
      "symbol": "BTCUSDT",
      "timeframe": "4h",
      "signal_type": "LONG",
      "entry": 50000,
      "tp": 51500,
      "sl": 49000,
      "outcome": "WIN",
      "exit_price": 51500,
      "profit_loss_pct": 3.0,
      "duration_hours": 8.5,
      "ml_mode": true,
      "ml_confidence": 85,
      "alerts_80": [
        {
          "timestamp": "2025-12-23T14:00:00+00:00",
          "price": 51200,
          "pct_to_tp": 80.0,
          "recommendation": "Consider taking partial profit (50%)"
        }
      ],
      "final_alerts": [
        {
          "timestamp": "2025-12-23T18:30:00+00:00",
          "outcome": "WIN",
          "exit_price": 51500,
          "pnl_pct": 3.0,
          "pnl_usd": 150.0,
          "duration_hours": 8.5,
          "hit_target": "TP"
        }
      ],
      "conditions": {
        "ml_mode": true,
        "ict_score": 8
      }
    }
  ],
  "statistics": {
    "total_trades": 1,
    "wins": 1,
    "losses": 0,
    "win_rate": 100.0,
    "last_updated": "2025-12-23T18:30:00+00:00"
  }
}
```

## Functions

### `add_to_active_trades(signal, user_chat_id)`

Adds a signal to active trades monitoring.

**Parameters:**
- `signal` - Signal dictionary with entry, tp, sl, symbol, type
- `user_chat_id` - User's Telegram chat ID

**Returns:**
- `trade_id` - Unique trade identifier

**Example:**
```python
trade_id = await add_to_active_trades(
    signal={
        'symbol': 'BTCUSDT',
        'type': 'LONG',
        'entry': 50000,
        'tp': 51500,
        'sl': 49000,
        'timeframe': '4h'
    },
    user_chat_id=7003238836
)
```

### `check_80_percent_alerts(bot)`

Monitors all active trades and sends 80% alerts.

**Parameters:**
- `bot` - Telegram Bot instance

**Runs:** Every 1 minute via scheduler

### `send_final_alert(trade, exit_price, hit_target, bot)`

Sends final alert when trade closes.

**Parameters:**
- `trade` - Active trade dictionary
- `exit_price` - Price at which trade closed
- `hit_target` - 'TP' or 'SL'
- `bot` - Telegram Bot instance

### `save_trade_to_journal(trade)`

Saves completed trade to `trading_journal.json`.

**Parameters:**
- `trade` - Completed trade dictionary with outcome

### `update_trade_statistics()`

Updates overall trading statistics in journal.

## Integration Points

### Automatic Trade Addition

To automatically add trades to monitoring when signals are generated, call `add_to_active_trades()` after signal confirmation:

```python
# After user confirms they took the signal
trade_id = await add_to_active_trades(
    signal=signal_data,
    user_chat_id=user_chat_id
)
logger.info(f"✅ Trade {trade_id} added to monitoring")
```

### Manual Trade Closure

Users can manually close trades using `/close_trade` command:

```
/close_trade BTCUSDT TP
```

This is useful for:
- Manual trade management
- Closing trades early
- Testing the alert system

## Configuration

### 80% Alert Threshold

The 80% threshold is calculated as:

**For LONG trades:**
```
threshold_80 = entry + (tp - entry) * 0.8
```

**For SHORT trades:**
```
threshold_80 = entry - (entry - tp) * 0.8
```

### Monitoring Interval

80% alerts are checked every **1 minute** via APScheduler.

### Position Size

Default position size for P/L calculation is **$1000**. This can be customized in the trade data:

```python
trade = {
    'position_size': 2000,  # $2000 position
    # ... other fields
}
```

## Benefits

1. **Automated Monitoring** - No need to manually check trades
2. **Risk Management** - 80% alert helps secure partial profits
3. **Complete History** - All trades logged to journal
4. **Statistics Tracking** - Automatic win rate and performance stats
5. **Telegram Integration** - Real-time notifications
6. **ML Integration** - Trade data used for ML training

## Notes

- Trades are automatically removed from monitoring after closure
- 80% alerts are sent only once per trade
- Journal data is used for ML model training
- Statistics update automatically after each trade
- Position size defaults to $1000 if not specified
