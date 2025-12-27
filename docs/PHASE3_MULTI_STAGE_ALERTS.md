# Phase 3: Multi-Stage Alerts System

## 📋 Overview

The Multi-Stage Alerts System provides continuous monitoring with intelligent alerts at multiple trade progression stages (25%, 50%, 75%, 85%, 100%) to provide timely recommendations and improve trade management.

## 🎯 Problem & Solution

### Before (Problem)
The real-time monitor only sent alerts at:
- **80% TP** (75-85% progress)
- **WIN** (TP hit)
- **LOSS** (SL hit)

**Issue:** Users didn't get guidance during the trade journey (0-75% progress). They didn't know:
- When to take partial profits
- If the trade is still valid
- If they should tighten stop loss

### After (Solution)
Now the system sends alerts at 5 different stages:

```
Trade Opened @ $86,500
↓
CONTINUOUS MONITORING (every 30 seconds)
├─ Stage 1: 0-25% progress → EARLY PHASE (no alert)
│
├─ Stage 2: 25-50% progress → HALFWAY ✅
│  └─ Alert: 🟡 "TAKE 30-50% PROFIT" or 💎 "HOLD"
│
├─ Stage 3: 50-75% progress → APPROACHING TARGET ✅
│  └─ Alert: 💎 "HOLD" or 🟡 "TAKE 30%"
│
├─ Stage 4: 75-85% progress → 80% TP ALERT ✅ (existing)
│  └─ Alert: 💎 "HOLD TO TARGET" / 🟡 "TIGHTEN SL" / ❌ "CLOSE NOW"
│
├─ Stage 5: 85-100% progress → FINAL PHASE ✅
│  └─ Alert: ⚠️ "WATCH - liquidity at $X"
│
└─ Stage 6: 100%+ → TP HIT ✅ (existing)
   └─ Alert: 🎉 "WIN! Target reached!"
```

## 🆔 Trade Identification System

Every trade gets a unique, human-readable ID:

**Format:** `#{SYMBOL}-{YYYYMMDD}-{HHMMSS}`

**Examples:**
- `#BTC-20251227-143022` - Bitcoin trade opened on Dec 27, 2025 at 14:30:22
- `#ETH-20251227-150033` - Ethereum trade opened on Dec 27, 2025 at 15:00:33

**Benefits:**
- ✅ Easy to read and reference
- ✅ Sortable by time
- ✅ Unique across all trades
- ✅ Shows which asset at a glance

## 📊 Alert Stages Explained

### Stage 2: Halfway Alert (25-50% progress)

**When:** Trade reaches 25-50% of the way to TP

**Purpose:** First checkpoint - is the trade still valid?

**Alert includes:**
- Current P/L percentage
- ICT re-analysis recommendation
- Confidence score
- Interactive buttons for action

**Example Message (Bulgarian):**
```
💎 ПОЛОВИН ПЪТ! Всичко е наред!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ТРЕЙД: #BTC-20251227-143022
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 BTCUSDT - BUY
⏰ Времева рамка: 4h
📅 Отворен: 27.12.2025 14:30
⏱️ Активен: 2ч 15мин

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Текуща печалба: +1.6%
📊 Прогрес: 48% до целта

💵 Цени:
   Вход: $86,500.00
   Сега: $87,890.00
   Цел (TP): $89,500.00
   SL: $85,200.00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ICT ПРОВЕРКА:
Bullish structure maintained. Order blocks holding.
Fair value gaps being respected.

🎲 ИЗЧИСЛЕНА ВЕРОЯТНОСТ: 78%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 ПРЕПОРЪКА: HOLD 💎

Има отлична вероятност да удариш целта. Продължавам да следя непрекъснато.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Следваща проверка след 2 минути...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

**Interactive Buttons:**
- 🟡 Вземи 50% (Take 50% profit)
- 🟡 Вземи 30% (Take 30% profit)
- 💎 Дръж Всичко (Hold everything)
- 📊 Пълен Анализ (Full analysis)

### Stage 3: Approaching Target Alert (50-75% progress)

**When:** Trade reaches 50-75% of the way to TP

**Purpose:** Second checkpoint - maintain conviction

**Alert includes:**
- Updated P/L
- Fresh ICT re-analysis
- Recommendation (HOLD/PARTIAL_CLOSE)
- Interactive buttons

**Example Message (Bulgarian):**
```
🎯 ПРИБЛИЖАВА ЦЕЛТА! 62% готово

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ТРЕЙД: #BTC-20251227-143022
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 BTCUSDT - BUY
⏰ Времева рамка: 4h
📅 Отворен: 27.12.2025 14:30
⏱️ Активен: 3ч 45мин

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Текуща печалба: +2.8%
📊 Прогрес: 62.0% до целта

💵 Цени:
   Вход: $86,500.00
   Сега: $88,924.00
   Цел (TP): $89,500.00
   SL: $85,200.00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ICT ПРОВЕРКА:
Price action strong. No reversal signals detected.

🎲 ИЗЧИСЛЕНА ВЕРОЯТНОСТ: 82%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 ПРЕПОРЪКА: HOLD 💎

Продължи да държиш! Целта е на досег.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Следваща проверка след 2 минути...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Stage 4: 80% TP Alert (75-85% progress) - EXISTING

**When:** Trade reaches 75-85% of the way to TP

**Purpose:** Critical decision point - HOLD, tighten SL, or close

**This is the existing alert** - NOT modified by Phase 3!

### Stage 5: Final Phase Alert (85-100% progress)

**When:** Trade reaches 85-100% of the way to TP

**Purpose:** Prepare for target hit - watch liquidity

**Alert includes:**
- Very close to target
- Liquidity warnings
- Distance remaining to TP
- Suggestion to tighten SL to breakeven

**Example Message (Bulgarian):**
```
🚀 ФИНАЛНА ФАЗА! Близо до целта!

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ТРЕЙД: #BTC-20251227-143022
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 BTCUSDT - BUY
⏰ Времева рамка: 4h
📅 Отворен: 27.12.2025 14:30
⏱️ Активен: 5ч 12мин

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 Текуща печалба: +3.3%
📊 Прогрес: 92.0% до целта
📍 Остава: 0.4% до TP

💵 Цени:
   Вход: $86,500.00
   Сега: $89,366.00
   Цел (TP): $89,500.00
   SL: $85,200.00

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ ВНИМАНИЕ:
• Следи за ликвидност около $89,500.00
• Голяма вероятност за удар на целта!
• Размисли за затягане на SL към БЕП

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Продължавам да следя всяка секунда...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## 💻 User Commands

### `/active` or `/active_trades`

Shows all active trades being monitored with:
- Trade ID
- Symbol and direction
- Current P/L percentage
- Progress to target
- Time active

**Example Output (Bulgarian):**
```
📊 АКТИВНИ ТРЕЙДОВЕ (2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

#1. #BTC-20251227-143022
   🟢 BTCUSDT - BUY | ⏰ 4h
   💰 P/L: +2.8% 📈
   📊 Прогрес: 62.0%
   ⏱️ Активен: 3ч 45мин

#2. #ETH-20251227-150033
   🔴 ETHUSDT - SELL | ⏰ 1h
   💰 P/L: +1.2% 📈
   📊 Прогрес: 34.5%
   ⏱️ Активен: 1ч 10мин

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Използвай /details [Trade ID] за детайли
Пример: /details #BTC-20251227-143022

⏰ 27.12.2025 19:15 UTC
```

## ⚙️ Configuration

### Enable/Disable Multi-Stage Alerts

Edit `config/feature_flags.json`:

```json
{
  "fundamental_analysis": {
    "enabled": false,
    "multi_stage_alerts": true,  ← Set to true to enable
    "..."
  },
  "monitoring": {
    "price_check_interval": 30,
    "stage_alert_intervals": {
      "halfway": 120,      ← 2 minutes between halfway checks
      "approaching": 120,  ← 2 minutes between approaching checks
      "final": 30          ← 30 seconds between final phase checks
    }
  }
}
```

**Default:** Multi-stage alerts are **DISABLED** (`false`)

### Alert Intervals

You can customize how often each stage is checked:

- **`halfway`**: Default 120 seconds (2 minutes)
- **`approaching`**: Default 120 seconds (2 minutes)
- **`final`**: Default 30 seconds (faster checks near target)

## 🔧 Technical Implementation

### Files Modified

1. **`utils/trade_id_generator.py`** (NEW)
   - `TradeIDGenerator.generate()` - Generate unique IDs
   - `TradeIDGenerator.parse()` - Parse IDs back to components

2. **`real_time_monitor.py`** (ENHANCED)
   - Added `ALERT_STAGES` constant
   - Enhanced `add_signal()` to include trade_id, opened_at, last_alerted_stage
   - Added `_is_multi_stage_enabled()` - Check feature flag
   - Added `_check_stage_alerts()` - Multi-stage alert logic
   - Added `_get_stage()` - Determine current stage
   - Added `_send_halfway_alert()` - Halfway stage alert
   - Added `_send_approaching_alert()` - Approaching stage alert
   - Added `_send_final_phase_alert()` - Final phase alert
   - Added `_format_halfway_message()` - Format Bulgarian message
   - Added `_format_approaching_message()` - Format Bulgarian message
   - Added `_get_stage_buttons()` - Interactive buttons
   - Added `get_user_trades()` - Get user's active trades

3. **`bot.py`** (ENHANCED)
   - Updated `active_trades_cmd()` to use `real_time_monitor_global.get_user_trades()`
   - Enhanced message formatting with Trade IDs, P/L, duration

4. **`config/feature_flags.json`** (ENHANCED)
   - Added `stage_alert_intervals` section

### Safety Features

✅ **Existing alerts UNCHANGED:**
- `_send_80_percent_alert()` - NOT modified
- `_send_win_alert()` - NOT modified
- `_send_loss_alert()` - NOT modified

✅ **Feature flag control:**
- Multi-stage alerts disabled by default
- Can be instantly disabled if issues arise

✅ **No duplicate alerts:**
- Tracks `last_alerted_stage` per trade
- Only sends alert when stage changes

✅ **Error handling:**
- All new methods wrapped in try/except
- Graceful degradation on errors
- Fallback to existing behavior

## 🧪 Testing

Run tests:
```bash
cd /home/runner/work/Crypto-signal-bot/Crypto-signal-bot
python -m pytest tests/test_multi_stage_alerts.py -v
```

### Test Coverage

✅ Trade ID generation (format, uniqueness)  
✅ Stage detection logic (all 5 stages)  
✅ Multi-stage alert triggering  
✅ No duplicate alerts  
✅ Feature flag control  
✅ User trade filtering  
✅ Message formatting (Bulgarian)  
✅ Backward compatibility  

## 🐛 Troubleshooting

### Multi-stage alerts not working?

1. **Check feature flag:**
   ```bash
   cat config/feature_flags.json | grep multi_stage_alerts
   ```
   Should show `"multi_stage_alerts": true`

2. **Check logs:**
   ```bash
   tail -f bot.log | grep "multi-stage"
   ```

3. **Verify ICT handler:**
   Multi-stage alerts use ICT re-analysis. Make sure ICT engine is loaded.

### Alerts sent multiple times?

This shouldn't happen due to `last_alerted_stage` tracking. If it does:
1. Check logs for `last_alerted_stage` values
2. Report bug with signal_id

### Trade IDs not showing?

Check that `utils/trade_id_generator.py` is imported correctly:
```python
from utils.trade_id_generator import TradeIDGenerator
```

If import fails, Trade ID will fallback to: `#{symbol}-{signal_id[:8]}`

## 📈 Performance Impact

**Minimal:**
- Multi-stage checks only run if feature enabled
- Uses existing 30-second monitoring loop
- No additional API calls (reuses existing price fetches)
- ICT re-analysis only at alert stages (not every check)

**Memory:**
- 3 additional fields per trade (~100 bytes)
- Negligible impact

## 🔒 Security

**No new security risks:**
- Uses existing Telegram bot authentication
- No new API endpoints exposed
- No sensitive data in Trade IDs
- Feature flag provides instant kill switch

## 📝 Future Enhancements

Potential future additions (not in Phase 3):
- [ ] Custom alert thresholds per user
- [ ] SMS/Email alerts in addition to Telegram
- [ ] Trade notes/comments
- [ ] Alert history/replay
- [ ] Machine learning for personalized recommendations

## 🤝 Contributing

When modifying this system:
1. ✅ Always test with feature flag OFF first
2. ✅ Never modify existing alert methods
3. ✅ Add tests for new functionality
4. ✅ Keep Bulgarian message formatting consistent
5. ✅ Update this documentation

## 📞 Support

Issues with multi-stage alerts? Report in GitHub Issues with:
- Trade ID
- Stage where alert was expected
- Feature flag status
- Relevant logs

---

**Phase 3 Multi-Stage Alerts System** - Providing smarter trade guidance at every step! 🚀
