# Alert Systems Integration Examples

## Example 1: Manual Integration After Signal Generation

Add this code after generating a signal to allow users to manually add it to monitoring:

```python
# In signal_cmd or ict_cmd function, after sending signal message

# Add inline keyboard for trade confirmation
keyboard = [
    [
        InlineKeyboardButton("✅ I took this trade", callback_data=f"confirm_trade_{signal_id}"),
        InlineKeyboardButton("❌ Skip", callback_data="skip_trade")
    ]
]
reply_markup = InlineKeyboardMarkup(keyboard)

await update.message.reply_text(
    "📊 <b>Track this trade?</b>\n"
    "Confirm if you took this trade to enable 80% alerts and final outcome tracking.",
    reply_markup=reply_markup,
    parse_mode='HTML'
)
```

Then add a callback handler:

```python
async def confirm_trade_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle trade confirmation callback"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "skip_trade":
        await query.edit_message_text("Trade not tracked.")
        return
    
    # Extract signal_id from callback_data
    signal_id = query.data.replace("confirm_trade_", "")
    
    # Get signal from context or cache
    signal = context.user_data.get(f'signal_{signal_id}')
    
    if not signal:
        await query.edit_message_text("❌ Signal not found or expired.")
        return
    
    # Add to active trades
    trade_id = await add_to_active_trades(
        signal=signal,
        user_chat_id=query.from_user.id
    )
    
    await query.edit_message_text(
        f"✅ <b>Trade Added to Monitoring</b>\n\n"
        f"🆔 Trade ID: {trade_id[:8]}\n"
        f"📊 Symbol: {signal['symbol']}\n"
        f"🎯 Type: {signal['type']}\n\n"
        f"You will receive:\n"
        f"• 80% alert when price reaches 80% to TP\n"
        f"• Final alert when trade closes (WIN/LOSS)\n"
        f"• Results logged to trading journal\n\n"
        f"View status: /active_trades",
        parse_mode='HTML'
    )

# Register the callback handler
app.add_handler(CallbackQueryHandler(confirm_trade_callback, pattern='^confirm_trade_|^skip_trade$'))
```

## Example 2: Automatic Integration (Auto-add all signals)

Add this code right after signal generation to automatically track all signals:

```python
# After generating a signal (in signal_cmd or ict_cmd)

# Prepare signal data for tracking
signal_data = {
    'symbol': symbol,
    'type': 'LONG' if signal_type in ['BUY', 'STRONG_BUY'] else 'SHORT',
    'entry': entry_price,
    'tp': tp_price,
    'sl': sl_price,
    'timeframe': timeframe,
    'ml_mode': True,
    'ml_confidence': confidence
}

# Add to active trades
trade_id = await add_to_active_trades(
    signal=signal_data,
    user_chat_id=update.effective_user.id
)

logger.info(f"✅ Auto-added trade to monitoring: {trade_id}")

# Optionally notify user
await update.message.reply_text(
    "📊 <b>Auto-Tracking Enabled</b>\n\n"
    f"This trade is now being monitored.\n"
    f"You'll receive 80% alerts and final outcome.\n\n"
    f"View status: /active_trades",
    parse_mode='HTML'
)
```

## Example 3: Integration with ICT Signal Engine

Add this in the ICT signal generation function (around line 5661 in bot.py):

```python
# After adding to real-time monitor
if real_time_monitor_global and ict_signal.signal_type.value in ['BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL']:
    signal_id = f"{symbol}_{ict_signal.signal_type.value}_{int(datetime.now(timezone.utc).timestamp())}"
    
    # Add to real-time monitor (existing code)
    real_time_monitor_global.add_signal(...)
    
    # ALSO add to active trades for 80% alerts
    signal_data = {
        'symbol': symbol,
        'type': 'LONG' if ict_signal.signal_type.value in ['BUY', 'STRONG_BUY'] else 'SHORT',
        'entry': ict_signal.entry_price,
        'tp': ict_signal.tp_prices[0],
        'sl': ict_signal.sl_price,
        'timeframe': timeframe,
        'ml_mode': False,
        'ml_confidence': ict_signal.confidence
    }
    
    trade_id = await add_to_active_trades(
        signal=signal_data,
        user_chat_id=update.effective_user.id
    )
    
    logger.info(f"✅ ICT signal added to active trades: {trade_id}")
```

## Example 4: Testing the System

### Test 80% Alerts

```python
# Create a test trade
test_signal = {
    'symbol': 'BTCUSDT',
    'type': 'LONG',
    'entry': 50000,
    'tp': 51000,  # $1000 profit target
    'sl': 49500,  # $500 stop loss
    'timeframe': '4h'
}

trade_id = await add_to_active_trades(
    signal=test_signal,
    user_chat_id=OWNER_CHAT_ID
)

# Monitor current price
# When price reaches 50800 (80% of 51000 - 50000 = 800), alert will trigger
```

### Test Manual Trade Closure

```bash
# In Telegram
/active_trades  # Check active trades
/close_trade BTCUSDT TP  # Close at Take Profit
/close_trade ETHUSDT SL  # Close at Stop Loss
```

### Test Journal Logging

```python
# After closing a trade, check trading_journal.json
import json

with open('trading_journal.json', 'r') as f:
    journal = json.load(f)

# Check latest trade
latest_trade = journal['trades'][-1]
print(f"Latest trade: {latest_trade['symbol']}")
print(f"Outcome: {latest_trade['outcome']}")
print(f"P/L: {latest_trade['profit_loss_pct']}%")

# Check statistics
stats = journal.get('statistics', {})
print(f"Win rate: {stats.get('win_rate', 0)}%")
```

## Example 5: Integration with Existing Real-Time Monitor

Since the bot already has a `real_time_monitor_global`, you can choose to:

**Option A: Use both systems**
- Real-time monitor for price tracking
- Active trades for 80% alerts and journal logging

**Option B: Merge into real-time monitor**
- Add 80% alert logic to `real_time_monitor.py`
- Call journal functions from there

**Option C: Use active trades only**
- Disable real-time monitor
- Use active trades for all monitoring

**Recommended: Option A** - Keep both for redundancy and different purposes.

## Example 6: Custom Alert Thresholds

To customize the 80% threshold, modify the `check_80_percent_alerts()` function:

```python
# Change 0.8 to different values:
threshold_80 = entry + (distance_to_tp * 0.75)  # 75% alert
threshold_80 = entry + (distance_to_tp * 0.9)   # 90% alert

# Or add multiple thresholds:
thresholds = [0.5, 0.75, 0.9]  # 50%, 75%, 90% alerts
```

## Example 7: Position Size Calculation

Add position size to trades for accurate P/L:

```python
signal_data = {
    'symbol': 'BTCUSDT',
    'type': 'LONG',
    'entry': 50000,
    'tp': 51500,
    'sl': 49000,
    'timeframe': '4h',
    'position_size': 2000  # $2000 position
}

# P/L will be calculated as:
# pnl_usd = 2000 * (pnl_pct / 100)
```

## Example 8: Notifications for Other Users

To send alerts to multiple users:

```python
# Add multiple users to trade
trade = {
    'symbol': 'BTCUSDT',
    'type': 'LONG',
    'entry': 50000,
    'tp': 51500,
    'sl': 49000,
    'user_chat_id': OWNER_CHAT_ID,
    'notify_users': [user_id_1, user_id_2, user_id_3]  # Additional users to notify
}

# In check_80_percent_alerts(), send to all users:
for user_id in [trade['user_chat_id']] + trade.get('notify_users', []):
    await bot.send_message(chat_id=user_id, text=message, parse_mode='HTML')
```

## Example 9: Custom Journal Structure

To add custom fields to journal entries:

```python
# In save_trade_to_journal()
journal_entry = {
    'timestamp': trade['timestamp'],
    'symbol': trade['symbol'],
    # ... existing fields ...
    
    # Add custom fields:
    'strategy': trade.get('signal_data', {}).get('strategy', 'ICT'),
    'risk_reward': trade.get('signal_data', {}).get('risk_reward', 0),
    'market_condition': trade.get('signal_data', {}).get('market_condition', 'unknown'),
    'notes': trade.get('notes', ''),
    'tags': trade.get('tags', [])
}
```

## Example 10: Dashboard Integration

Create a simple dashboard to view statistics:

```python
async def dashboard_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show trading dashboard"""
    journal_path = os.path.join(BASE_PATH, 'trading_journal.json')
    
    if not os.path.exists(journal_path):
        await update.message.reply_text("No trading data available.")
        return
    
    with open(journal_path, 'r') as f:
        journal = json.load(f)
    
    stats = journal.get('statistics', {})
    trades = journal.get('trades', [])
    
    # Recent trades
    recent = trades[-5:] if len(trades) > 0 else []
    
    message = (
        "📊 <b>TRADING DASHBOARD</b>\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📈 <b>Overall Statistics</b>\n"
        f"Total Trades: {stats.get('total_trades', 0)}\n"
        f"Wins: {stats.get('wins', 0)} ✅\n"
        f"Losses: {stats.get('losses', 0)} ❌\n"
        f"Win Rate: {stats.get('win_rate', 0):.1f}%\n\n"
        f"🕒 <b>Active Trades</b>\n"
        f"Monitoring: {len(active_trades)}\n\n"
    )
    
    if recent:
        message += "📜 <b>Recent Trades</b>\n"
        for trade in recent:
            emoji = "✅" if trade.get('outcome') in ['WIN', 'SUCCESS'] else "❌"
            message += (
                f"{emoji} {trade['symbol']} "
                f"{trade.get('profit_loss_pct', 0):+.1f}%\n"
            )
    
    message += f"\n⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
    
    await update.message.reply_text(message, parse_mode='HTML')

# Register command
app.add_handler(CommandHandler("dashboard", dashboard_cmd))
```

## Summary

These examples show how to integrate the alert systems into your workflow. Choose the approach that best fits your needs:

1. **Manual confirmation** - Users confirm each trade
2. **Automatic** - All signals auto-tracked
3. **Hybrid** - Auto-track high-confidence signals only
4. **Custom** - Build your own logic

The system is flexible and can be customized to match your trading strategy and risk management approach.
