# Trading Journal Auto-Initialization

## 📝 Overview

The `trading_journal.json` file is **automatically created** when the bot starts. It does NOT need to be tracked in Git because it contains dynamic runtime data.

## 🔄 Auto-Creation

**When:** Bot startup (via `main()` function in `bot.py`)

**Function:** `load_journal()` → Creates empty journal if file doesn't exist

**Default Structure:**
```json
{
  "metadata": {
    "created": "YYYY-MM-DD",
    "version": "1.0",
    "total_trades": 0,
    "last_updated": "ISO-8601 timestamp"
  },
  "trades": [],
  "patterns": {
    "successful_conditions": {},
    "failed_conditions": {},
    "best_timeframes": {},
    "best_symbols": {}
  },
  "ml_insights": {
    "accuracy_by_confidence": {},
    "accuracy_by_timeframe": {},
    "accuracy_by_symbol": {},
    "optimal_entry_zones": {}
  }
}
```

## 📂 File Location

**Path:** `{BASE_PATH}/trading_journal.json`

**BASE_PATH Detection:**
1. Environment variable: `BOT_BASE_PATH` (if set)
2. `/root/Crypto-signal-bot` (server)
3. `/workspaces/Crypto-signal-bot` (Codespace)
4. Current directory (fallback)

## ✅ Verification

Check logs on bot startup:
```
✅ Trading journal initialized: /path/to/trading_journal.json
📊 Journal contains 0 trades
```

## 🔒 Why Not in Git?

The journal file is excluded from Git (via `.gitignore`) because:
- Contains dynamic runtime data
- Grows with each trade
- Different on each environment (server vs dev)
- Auto-created if missing

## 🚨 Important

If you need to reset the journal:
1. Stop the bot
2. Delete `trading_journal.json`
3. Restart the bot
4. New empty journal will be created

---

**See Also:**
- `bot.py` - `load_journal()` function (line 2637)
- `bot.py` - `save_journal()` function (line 2671)
- `bot.py` - Journal initialization in `main()` (line ~11305)
