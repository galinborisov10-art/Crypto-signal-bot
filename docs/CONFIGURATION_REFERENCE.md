# Configuration Reference
## Complete System Configuration Guide

**Version:** 2.0.0  
**Documentation Date:** January 17, 2026  
**Repository:** galinborisov10-art/Crypto-signal-bot  
**Related Docs:** [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | [CORE_MODULES_REFERENCE.md](CORE_MODULES_REFERENCE.md) | [TRADING_STRATEGY_EXPLAINED.md](TRADING_STRATEGY_EXPLAINED.md)

---

## Table of Contents
1. [Core Settings](#core-settings)
2. [Symbols & Timeframes](#symbols--timeframes)
3. [Thresholds & Scoring](#thresholds--scoring)
4. [API Keys & Credentials](#api-keys--credentials)
5. [File Paths](#file-paths)
6. [Scheduler Configuration](#scheduler-configuration)
7. [Deduplication Settings](#deduplication-settings)
8. [Performance & Caching](#performance--caching)
9. [Advanced Settings](#advanced-settings)

---

## Core Settings

### AUTO_POSITION_TRACKING_ENABLED

**Location:** bot.py line 398  
**Type:** Boolean  
**Current Value:** `True`  
**Purpose:** Automatically create database position records when auto-signals are generated

**Used in:**
- bot.py:11482 - `if AUTO_POSITION_TRACKING_ENABLED:` (conditional check before opening position)
- position_manager.py - Position creation and tracking system

**Impact if changed:**
- `True`: Every auto-signal with confidence ≥60% creates a position in `positions.db` for monitoring
- `False`: Signals are sent to Telegram but NOT tracked in database (no checkpoint alerts)

**Related variables:**
- `CHECKPOINT_MONITORING_ENABLED`
- `POSITION_MONITORING_INTERVAL_SECONDS`

**Current issues:** ❌ **BROKEN** - Despite being `True`, position tracking never happens due to unreachable code at line 11482 (never executes after signal delivery)

---

### AUTO_CLOSE_ON_SL_HIT

**Location:** bot.py line 399  
**Type:** Boolean  
**Current Value:** `True`  
**Purpose:** Automatically close positions when stop loss price is hit

**Used in:**
- real_time_monitor.py - Real-time price monitoring
- position_manager.py:close_position() - Position closure logic

**Impact if changed:**
- `True`: Position auto-closed and marked as "SL" in history when SL hit
- `False`: Manual close required, only alert sent to Telegram

**Related variables:**
- `AUTO_CLOSE_ON_TP_HIT`
- `AUTO_POSITION_TRACKING_ENABLED` (must be True for this to work)

**Current issues:** ⚠️ **DEPENDS ON BROKEN FEATURE** - Can't auto-close if positions aren't tracked (see AUTO_POSITION_TRACKING_ENABLED)

---

### AUTO_CLOSE_ON_TP_HIT

**Location:** bot.py line 400  
**Type:** Boolean  
**Current Value:** `True`  
**Purpose:** Automatically close positions when take profit targets are hit

**Used in:**
- real_time_monitor.py - TP monitoring logic
- position_manager.py:close_position() - Marks position as "TP1/TP2/TP3"

**Impact if changed:**
- `True`: Position auto-closed when any TP is hit (default: TP3 = full close)
- `False`: Manual management required, alerts sent at each TP level

**Related variables:**
- `AUTO_CLOSE_ON_SL_HIT`
- `CHECKPOINT_MONITORING_ENABLED`

**Current issues:** ⚠️ **DEPENDS ON BROKEN FEATURE** - Requires position tracking to be working

---

### CHECKPOINT_MONITORING_ENABLED

**Location:** bot.py line 401  
**Type:** Boolean  
**Current Value:** `True`  
**Purpose:** Enable checkpoint alerts at 25%, 50%, 75%, 85% of profit target progression

**Used in:**
- bot.py:11512+ - `monitor_positions_job()` scheduler job
- trade_reanalysis_engine.py - Re-analysis at checkpoints
- real_time_monitor.py - Checkpoint detection

**Impact if changed:**
- `True`: Trade re-analysis runs at each checkpoint, recommendations sent via Telegram
- `False`: No intermediate alerts, only final outcome (TP/SL hit)

**Related variables:**
- `AUTO_POSITION_TRACKING_ENABLED` (must be True)
- `POSITION_MONITORING_INTERVAL_SECONDS`

**Current issues:** ❌ **NOT WORKING** - No positions in database means checkpoints never trigger

**Checkpoint Details:**
```
25% - Early validation (bias check, structure intact?)
50% - Mid-trade analysis (consider partial close?)
75% - High-probability zone (move SL to breakeven?)
85% - Near completion (prepare for exit)
```

---

### POSITION_MONITORING_INTERVAL_SECONDS

**Location:** bot.py line 402  
**Type:** Integer  
**Current Value:** `60`  
**Purpose:** How often (in seconds) the position monitoring job runs

**Used in:**
- bot.py:17970+ - APScheduler job registration:
  ```python
  scheduler.add_job(
      monitor_positions_job,
      'interval',
      seconds=POSITION_MONITORING_INTERVAL_SECONDS,
      args=[application.bot]
  )
  ```

**Impact if changed:**
- Lower values (e.g., 30): More responsive checkpoint detection, higher CPU usage
- Higher values (e.g., 120): Less CPU usage, delayed checkpoint alerts

**Related variables:**
- `CHECKPOINT_MONITORING_ENABLED`
- `AUTO_POSITION_TRACKING_ENABLED`

**Current issues:** ✅ Working (job runs every 60s, but finds 0 positions)

---

### STARTUP_MODE & STARTUP_GRACE_PERIOD_SECONDS

**Location:** bot.py lines 393, 395  
**Type:** Boolean, Integer  
**Current Values:** `STARTUP_MODE = True`, `STARTUP_GRACE_PERIOD_SECONDS = 300`  
**Purpose:** Prevent duplicate signals for 5 minutes after bot startup

**Used in:**
- bot.py:11269-11279 - Auto-signal suppression check:
  ```python
  if STARTUP_MODE and STARTUP_TIME:
      elapsed = (datetime.now() - STARTUP_TIME).total_seconds()
      
      if elapsed < STARTUP_GRACE_PERIOD_SECONDS:
          logger.info(f"🛑 Startup mode - suppressing auto-signals")
          return
      else:
          STARTUP_MODE = False
  ```
- bot.py:11236 - Timer-based startup mode termination

**Impact if changed:**
- Increase `STARTUP_GRACE_PERIOD_SECONDS`: Longer suppression window (prevents more duplicates on restart)
- Decrease to 0: No startup suppression (may send duplicates if restarting mid-cycle)

**Related variables:**
- `SENT_SIGNALS_CACHE` (in-memory deduplication)
- Signal cache system (persistent deduplication)

**Current issues:** ✅ Working (PR #112 fix ensures mode ends after grace period)

---

### SEND_CHARTS

**Location:** ❌ NOT FOUND as explicit variable  
**Type:** Conditional based on module availability  
**Current Value:** Determined by `CHART_VISUALIZATION_AVAILABLE` (line 180)  
**Purpose:** Enable/disable chart generation and sending with signals

**Used in:**
- bot.py:11167-11181 - Chart generation for auto-signals:
  ```python
  if CHART_VISUALIZATION_AVAILABLE:
      try:
          generator = ChartGenerator()
          chart_bytes = generator.generate(df, ict_signal, symbol, timeframe)
          
          if chart_bytes:
              await context.bot.send_photo(
                  chat_id=chat_id,
                  photo=BytesIO(chart_bytes),
                  caption=f"📊 {symbol} ({timeframe})",
                  parse_mode='HTML'
              )
      except Exception as e:
          logger.warning(f"⚠️ Chart generation failed: {e}")
  ```

**Impact if changed:**
- To disable charts: Remove chart_generator.py import or set `CHART_VISUALIZATION_AVAILABLE = False`
- To enable: Ensure chart_generator.py and chart_annotator.py are imported successfully

**Related variables:**
- `CHART_VISUALIZATION_AVAILABLE` (line 180)

**Current issues:** ✅ Working (charts sent if module is available)

---

## Symbols & Timeframes

### SYMBOLS

**Location:** bot.py lines 359-366  
**Type:** Dictionary  
**Current Value:**
```python
SYMBOLS = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT',
    'XRP': 'XRPUSDT',
    'SOL': 'SOLUSDT',
    'BNB': 'BNBUSDT',
    'ADA': 'ADAUSDT',
}
```

**Purpose:** Supported cryptocurrency pairs for analysis and trading

**Used in:**
- bot.py:11283 - `for symbol in SYMBOLS.values()` (auto-signal generation)
- ict_signal_engine.py:299-300 - Altcoin independent mode detection
- All signal generation and analysis functions

**Impact if changed:**
- Add new symbol: Must be supported by Binance API
- Remove symbol: That crypto will no longer generate signals

**Related variables:**
- `ALT_INDEPENDENT_SYMBOLS` in ict_signal_engine.py (ETHUSDT, SOLUSDT, BNBUSDT, ADAUSDT, XRPUSDT)

**Current issues:** ✅ Working (all 6 symbols active)

**Trading Volume (as of Jan 2026):**
- BTCUSDT: ~$2.5B daily
- ETHUSDT: ~$800M daily
- Others: ~$100M-$300M daily

---

### TIMEFRAMES

**Location:** bot.py line 11023  
**Type:** List  
**Current Value:** `['1h', '2h', '4h', '1d']`  
**Purpose:** Auto-signal analysis timeframes

**Used in:**
- bot.py:11023 - `timeframes_to_check = ['1h', '2h', '4h', '1d']`
- bot.py:17900+ - Scheduler job registration (one job per timeframe)

**Scheduler Configuration:**
```python
# Line 17900+
scheduler.add_job(auto_signal_job, 'interval', hours=1, args=['1h', bot])
scheduler.add_job(auto_signal_job, 'interval', hours=2, args=['2h', bot])
scheduler.add_job(auto_signal_job, 'interval', hours=4, args=['4h', bot])
scheduler.add_job(auto_signal_job, 'interval', hours=24, args=['1d', bot])
```

**Impact if changed:**
- Add '15m': More frequent signals (may increase noise)
- Remove '1d': No daily swing analysis
- Add '1w': Weekly position trading (requires new scheduler job)

**Related variables:**
- `SWING_KLINES_LIMIT` (number of candles fetched per timeframe)

**Current issues:** ✅ Working (4 timeframes generating signals)

**Average Signals Per Day:**
- 1h: ~8 signals/day
- 2h: ~4 signals/day
- 4h: ~3 signals/day
- 1d: ~1 signal/day
- **Total:** ~16 signals/day (with deduplication)

---

## Thresholds & Scoring

### ⚠️ CRITICAL: Signal Threshold Inconsistency

**Problem:** Two different thresholds exist for the same signal flow, causing **data loss**.

#### Telegram Send Threshold

**Location:** bot.py:11125-11126 (inferred from log message)  
**Type:** Integer (percentage)  
**Inferred Value:** `60`  
**Purpose:** Minimum confidence to send signal to Telegram

**Code:**
```python
# Line 11125
if not all_good_signals:
    logger.info("⚠️ Няма сигнали с увереност ≥60% (или всички вече изпратени)")
    return
```

**Effect:** All signals with `confidence >= 60` are collected and sent to users via Telegram.

---

#### Journal Log Threshold

**Location:** bot.py:11199  
**Type:** Integer (percentage)  
**Explicit Value:** `65`  
**Purpose:** Minimum confidence to log trade to `trading_journal.json` for ML training

**Code:**
```python
# Line 11199
if ict_signal.confidence >= 65:
    try:
        analysis_data = {
            'market_bias': ict_signal.bias.value,
            'htf_bias': ict_signal.htf_bias,
            # ... more analysis data
        }
        
        journal_id = log_trade_to_journal(
            symbol=symbol,
            timeframe=timeframe,
            signal_type=ict_signal.signal_type.value,
            confidence=ict_signal.confidence,
            entry_price=ict_signal.entry_price,
            tp_price=ict_signal.tp_prices[0],
            sl_price=ict_signal.sl_price,
            analysis_data=analysis_data
        )
```

**Effect:** Only signals with `confidence >= 65` are written to the trading journal.

---

#### THE ISSUE: 60-64% Data Loss

**Scenario:**
1. Signal generated with confidence = 62%
2. ✅ Signal SENT to Telegram (passes 60% threshold)
3. ❌ Signal NOT LOGGED to journal (fails 65% threshold)
4. **Result:** User receives signal, but ML system has no record of it

**Impact:**
- **~50% data loss** for signals in 60-64% range
- ML training dataset incomplete
- Backtest accuracy reduced (missing real-world signal data)
- Win-rate statistics incomplete

**Signals Affected (estimated daily):**
- Total signals/day: ~16
- Signals 60-64%: ~8 (50% of total)
- Signals ≥65%: ~8 (logged to journal)
- **Lost signals:** 8/day = ~240/month

**Recommended Fix:**
```python
# Change line 11199 from:
if ict_signal.confidence >= 65:

# To:
if ict_signal.confidence >= 60:  # Match Telegram threshold
```

**Related variables:**
- `STATS_FILE` (bot_stats.json) - Also affected by threshold inconsistency
- ML training dataset in ml_engine.py

**Current issues:** ❌ **CRITICAL BUG** - Data loss for 60-64% confidence signals

---

### ML Confidence Adjustment

**Location:** ict_signal_engine.py (lines vary by ML integration)  
**Type:** Float (percentage adjustment)  
**Range:** ±20%  
**Purpose:** Adjust ICT confidence score based on ML model predictions

**Used in:**
- ict_signal_engine.py - ML confidence optimization
- ml_predictor.py - Machine learning prediction integration

**Impact if changed:**
- Higher range (±30%): More aggressive ML influence (may override ICT analysis)
- Lower range (±10%): More conservative, ICT patterns dominate

**Related variables:**
- `ML_PREDICTOR_AVAILABLE` (flag for ML system availability)
- `ML_ENGINE_AVAILABLE`

**Current issues:** ✅ Working (when ML model is trained)

---

### Signal Proximity Thresholds

**Location:** bot.py lines 419-429  
**Type:** Multiple float values (percentages)  
**Purpose:** Define how similar two signals must be to be considered duplicates

**All Variables:**

```python
# Price proximity levels
PRICE_PROXIMITY_TIGHT = 0.2      # 0.2% difference = very close
PRICE_PROXIMITY_NORMAL = 0.5     # 0.5% difference = close
PRICE_PROXIMITY_LOOSE = 1.0      # 1.0% difference = somewhat close
PRICE_PROXIMITY_IDENTICAL = 0.3  # 0.3% difference = identical

# Confidence similarity
CONFIDENCE_SIMILARITY_STRICT = 3  # ±3% = identical confidence
CONFIDENCE_SIMILARITY_NORMAL = 5  # ±5% = similar confidence

# Time windows for deduplication
TIME_WINDOW_EXTENDED = 120       # 2 hours (minutes)
TIME_WINDOW_LONG = 240           # 4 hours (minutes)
TIME_WINDOW_MEDIUM = 90          # 1.5 hours (minutes)
```

**Used in:**
- signal_cache.py - Persistent deduplication system
- bot.py - In-memory duplicate detection

**Impact if changed:**
- Tighter thresholds (lower %): More signals get through (more duplicates)
- Looser thresholds (higher %): Fewer signals (may block valid signals)

**Related variables:**
- `SENT_SIGNALS_CACHE` (in-memory cache)
- `sent_signals_cache.json` (persistent cache)

**Current issues:** ✅ Working (effective deduplication)

---

### Swing Analysis Thresholds

**Location:** bot.py lines 369-372  
**Type:** Multiple integer/float values  
**Purpose:** Determine market structure in ranging markets

**All Variables:**

```python
SWING_KLINES_LIMIT = 100        # Candles to fetch for swing analysis
SWING_MIN_CANDLES = 20          # Minimum candles for valid analysis
SWING_UPPER_THRESHOLD = 0.66    # Price in upper 33% = bullish context
SWING_LOWER_THRESHOLD = 0.33    # Price in lower 33% = bearish context
```

**Used in:**
- ict_signal_engine.py - Swing high/low detection
- PR #115 swing analysis system

**Logic:**
```
Price Range: $45,000 - $50,000 (range = $5,000)

Upper 33% zone: $48,333 - $50,000
Middle 33% zone: $46,666 - $48,333
Lower 33% zone: $45,000 - $46,666

If current price = $49,000 (upper zone):
  → Bullish context (price > SWING_UPPER_THRESHOLD)
  → Prefer LONG signals near support
```

**Impact if changed:**
- Increase `SWING_KLINES_LIMIT` to 200: More historical context, slower analysis
- Change thresholds to 0.70/0.30: Wider neutral zone (less directional bias)

**Related variables:**
- `DEFAULT_SWING_RR_RATIO = 3.5` (risk/reward for ranging markets)

**Current issues:** ✅ Working (PR #115 implementation)

---

## API Keys & Credentials

### TELEGRAM_BOT_TOKEN

**Location:** bot.py line 286 (with security fallback)  
**Type:** String (secure token)  
**Source:** `.env` file → `TELEGRAM_BOT_TOKEN` environment variable  
**Purpose:** Authenticate bot with Telegram API

**Code:**
```python
# Lines 285-292
if SECURITY_MODULES_AVAILABLE:
    TELEGRAM_BOT_TOKEN = get_secure_token()  # Encrypted storage
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ Failed to get bot token from SecureTokenManager!")
        TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')  # Fallback
else:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
```

**Security Features:**
- Encrypted storage via `security/token_manager.py`
- Fallback to environment variable if security module unavailable
- Never logged or printed

**Usage:**
- bot.py:17800+ - Bot initialization:
  ```python
  application = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
  ```

**Impact if changed:**
- Invalid token: Bot cannot start (raises ValueError at line 341)
- New token: Must update .env and restart bot

**Related variables:**
- `SECURITY_MODULES_AVAILABLE` (line 277)

**Current issues:** ✅ Working (token securely managed)

---

### OWNER_CHAT_ID

**Location:** bot.py line 294  
**Type:** Integer  
**Current Value:** `7003238836`  
**Purpose:** Primary admin user ID for bot commands and alerts

**Code:**
```python
OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID', '7003238836'))
```

**Used in:**
- Access control (bot.py:301-304) - Hardcoded fallback to prevent lockout
- Auto-signal delivery
- Admin command authorization
- Report generation

**Impact if changed:**
- Change to new ID: Transfer ownership to another Telegram user
- Must update `.env` file

**Related variables:**
- `ALLOWED_USERS` set (lines 301-304)
- `ALLOWED_USERS_FILE` (allowed_users.json)

**Current issues:** ✅ Working

---

### Binance API Configuration

**Location:** bot.py lines 333-336, 342  
**Type:** String URLs  
**Purpose:** Binance public API endpoints (no authentication required)

**All Endpoints:**

```python
# Line 333
BINANCE_PRICE_URL = os.getenv('BINANCE_PRICE_URL', 
    "https://api.binance.com/api/v3/ticker/price")

# Line 334
BINANCE_24H_URL = os.getenv('BINANCE_24H_URL', 
    "https://api.binance.com/api/v3/ticker/24hr")

# Line 335
BINANCE_KLINES_URL = os.getenv('BINANCE_KLINES_URL', 
    "https://api.binance.com/api/v3/klines")

# Line 342
BINANCE_DEPTH_URL = "https://api.binance.com/api/v3/depth"
```

**Rate Limits:**
- **Weight limit:** 1200 requests/minute
- **Order limit:** 10 requests/second
- **IP limit:** 6000 requests/minute

**Used in:**
- Market data fetching (price, volume, klines)
- Order book depth analysis
- 24-hour statistics

**Impact if changed:**
- Use different exchange: Change URLs to Binance US, Kraken, etc.
- Use proxy: Add proxy configuration to requests

**Related variables:**
- None (hardcoded fallbacks ensure API availability)

**Current issues:** ✅ Working (public API, no auth needed)

---

## File Paths

All file paths use `BASE_PATH` auto-detection system (lines 44-57):

```python
# Priority order:
1. Explicit env var: BOT_BASE_PATH
2. Server: /root/Crypto-signal-bot
3. Codespace: /workspaces/Crypto-signal-bot
4. Fallback: Current directory
```

---

### Database Files

#### positions.db

**Location:** `{BASE_PATH}/positions.db`  
**Defined in:** position_manager.py line 42  
**Purpose:** SQLite database for position tracking

**Schema:** See [DATA_STRUCTURES.md](DATA_STRUCTURES.md) for complete schema

**Tables:**
- `open_positions` - Active positions (OPEN, PARTIAL)
- `checkpoint_alerts` - Re-analysis records
- `position_history` - Closed positions with P&L

**Current state:** ✅ EXISTS (0 records - never populated)

**Impact if deleted:**
- Position tracking resets
- Checkpoint history lost
- Auto-recreated on next bot start (via init_positions_db.py)

**Related variables:**
- `AUTO_POSITION_TRACKING_ENABLED`
- `CHECKPOINT_MONITORING_ENABLED`

---

### JSON Files

#### bot_stats.json

**Location:** `{BASE_PATH}/bot_stats.json`  
**Defined in:** bot.py line 345  
**Purpose:** Win-rate tracking and signal performance statistics

**Current state:** ❌ NOT FOUND (should contain signal history)

**Expected format:**
```json
{
  "total_signals": 156,
  "win_count": 98,
  "loss_count": 58,
  "win_rate": 62.82,
  "signals": [
    {
      "id": "sig_001",
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "confidence": 72.5,
      "outcome": "WIN",
      "timestamp": "2026-01-15T14:30:00"
    }
  ],
  "last_updated": "2026-01-17T21:00:00"
}
```

**Used in:**
- bot.py - Win-rate calculation
- /stats command - Display statistics to users

**Related variables:**
- Journal threshold issue affects data completeness

**Current issues:** ❌ NOT FOUND (file should exist but doesn't)

---

#### trading_journal.json

**Location:** `{BASE_PATH}/trading_journal.json`  
**Defined in:** Inferred from log_trade_to_journal() function  
**Purpose:** ML training data - trade analysis and outcomes

**Current state:** ❌ NOT FOUND

**Expected format:** See [DATA_STRUCTURES.md](DATA_STRUCTURES.md) for complete format

**Written by:** bot.py:11213 - `log_trade_to_journal()` call  
**Threshold:** Only signals with confidence ≥65% (causes data loss)

**Read by:**
- ml_engine.py - Model training
- Backtest system - Historical analysis

**Related variables:**
- Journal log threshold (65%)

**Current issues:** ❌ NOT FOUND + threshold inconsistency

---

#### sent_signals_cache.json

**Location:** `{BASE_PATH}/sent_signals_cache.json`  
**Purpose:** Persistent deduplication cache

**Current state:** ✅ EXISTS

**Format:**
```json
{
  "BTCUSDT_BUY_4h": {
    "timestamp": "2026-01-14T16:37:43.121268",
    "entry_price": 50000.0,
    "confidence": 85
  },
  "ETHUSDT_SELL_1h": {
    "timestamp": "2026-01-14T16:41:40.666362",
    "entry_price": 3500.0,
    "confidence": 90
  }
}
```

**Used in:**
- signal_cache.py - Persistent deduplication
- bot.py - Fallback to in-memory cache if file unavailable

**Cleanup:** Old entries (>24h) automatically removed

**Related variables:**
- `SENT_SIGNALS_CACHE` (in-memory equivalent)

**Current issues:** ✅ Working

---

#### news_cache.json

**Location:** `{BASE_PATH}/news_cache.json`  
**Purpose:** Cache news sentiment data

**Current state:** ✅ EXISTS

**Format:**
```json
{
  "BTC": {
    "sentiment": "POSITIVE",
    "score": 0.75,
    "articles": 12,
    "last_updated": "2026-01-17T20:00:00"
  }
}
```

**Used in:**
- utils/news_cache.py - News sentiment integration
- Fundamental analysis (if enabled)

**TTL:** 2 hours (refreshed automatically)

**Current issues:** ✅ Working

---

#### allowed_users.json

**Location:** `{BASE_PATH}/allowed_users.json`  
**Defined in:** bot.py line 307  
**Purpose:** Authorized user list for bot access

**Current state:** ✅ EXISTS

**Format:**
```json
[7003238836, 123456789, 987654321]
```

**Used in:**
- bot.py:310-315 - Load authorized users on startup
- Access control system

**Impact:**
- Add user ID: Grant bot access
- Remove user ID: Revoke access (except owner)

**Current issues:** ✅ Working

---

## Scheduler Configuration

### Timezone

**Location:** APScheduler initialization (bot.py:17850+)  
**Type:** pytz timezone  
**Current Value:** `'Europe/Sofia'` (Bulgaria, UTC+2/+3)  
**Purpose:** Schedule jobs in Bulgarian local time

**Impact if changed:**
- Change to 'UTC': All scheduled times shift
- Daily reports would run at different clock time

**Related variables:**
- `DAILY_REPORT_MISFIRE_GRACE_TIME`

---

### Job Frequencies

**Location:** bot.py lines 17900-17980  
**Type:** APScheduler job configuration  
**Purpose:** Define how often each job runs

**All Scheduler Jobs:**

```python
# Auto-signal jobs (4 timeframes)
scheduler.add_job(auto_signal_job, 'interval', hours=1, args=['1h', bot])
scheduler.add_job(auto_signal_job, 'interval', hours=2, args=['2h', bot])
scheduler.add_job(auto_signal_job, 'interval', hours=4, args=['4h', bot])
scheduler.add_job(auto_signal_job, 'interval', hours=24, args=['1d', bot])

# Position monitoring (every 60 seconds)
scheduler.add_job(monitor_positions_job, 'interval', 
                  seconds=POSITION_MONITORING_INTERVAL_SECONDS, args=[bot])

# Daily report (every day at 23:00 BG time)
scheduler.add_job(generate_daily_report_job, 'cron', 
                  hour=23, minute=0, args=[bot])

# Weekly report (Mondays at 10:00 BG time)
scheduler.add_job(generate_weekly_report_job, 'cron', 
                  day_of_week='mon', hour=10, minute=0, args=[bot])

# Monthly report (1st day of month at 09:00 BG time)
scheduler.add_job(generate_monthly_report_job, 'cron', 
                  day=1, hour=9, minute=0, args=[bot])
```

**Impact if changed:**
- More frequent auto-signals: Higher Binance API usage (risk hitting rate limits)
- Less frequent monitoring: Delayed checkpoint alerts

**Related variables:**
- `POSITION_MONITORING_INTERVAL_SECONDS`
- `STARTUP_GRACE_PERIOD_SECONDS`

---

### Startup Grace Period

**Location:** bot.py line 415  
**Type:** Integer (seconds)  
**Current Value:** `10`  
**Purpose:** Delay before checking for missed scheduler jobs on startup

**Code:**
```python
STARTUP_CHECK_DELAY_SECONDS = 10  # Wait 10s after startup
```

**Used in:**
- Report generation system - Check if daily report was missed

**Impact if changed:**
- Lower value (5s): Faster startup check, may miss job registration
- Higher value (30s): Ensures all jobs registered before check

**Related variables:**
- `DAILY_REPORT_MISFIRE_GRACE_TIME = 3600` (1 hour grace for missed jobs)

---

## Deduplication Settings

### SENT_SIGNALS_CACHE

**Location:** bot.py line 389  
**Type:** Dictionary (in-memory)  
**Current Value:** `{}`  
**Purpose:** Track sent signals to prevent duplicates within same session

**Structure:**
```python
{
    "BTCUSDT_BUY_4h": {
        'timestamp': datetime,
        'confidence': 75,
        'entry_price': 97100
    }
}
```

**Used in:**
- bot.py - In-memory duplicate detection (fallback if persistent cache fails)
- Cleared on bot restart (persistent cache in sent_signals_cache.json survives)

**Related variables:**
- `sent_signals_cache.json` (persistent storage)
- Signal proximity thresholds

**Current issues:** ✅ Working (used as fallback to persistent cache)

---

## Performance & Caching

### LRU Cache Configuration

**Location:** bot.py lines 590-600  
**Type:** LRUCacheDict instances  
**Purpose:** Cache expensive operations with automatic eviction

**All Cache Instances:**

```python
CACHE = {
    'backtest': LRUCacheDict(max_size=50, ttl_seconds=300),
    'market': LRUCacheDict(max_size=100, ttl_seconds=180),
    'ml_performance': LRUCacheDict(max_size=50, ttl_seconds=300)
}

CACHE_TTL = {
    'backtest': 300,      # 5 minutes
    'market': 180,        # 3 minutes
    'ml_performance': 300 # 5 minutes
}
```

**Cache Behavior:**
- **LRU Eviction:** Oldest item removed when max_size reached
- **TTL Expiration:** Items expire after ttl_seconds
- **Thread-safe:** Uses threading.Lock for concurrent access

**Used in:**
- Backtest results caching (avoid re-running same parameters)
- Market data caching (reduce Binance API calls)
- ML performance caching (expensive model predictions)

**Impact if changed:**
- Increase max_size: More memory usage, better hit rate
- Decrease TTL: More fresh data, more API calls

**Cache Statistics:**
```python
cache_stats = CACHE['market'].get_stats()
# Returns: {
#   'size': 45,
#   'max_size': 100,
#   'hits': 230,
#   'misses': 45,
#   'hit_rate': 0.84
# }
```

**Related variables:**
- `MAX_ASYNC_WORKERS = 3` (line 606)

---

### Thread Pool Configuration

**Location:** bot.py line 606  
**Type:** Integer  
**Current Value:** `3`  
**Purpose:** Maximum concurrent background tasks

**Code:**
```python
MAX_ASYNC_WORKERS = 3  # Background thread pool size
```

**Used in:**
- Parallel signal analysis (6 symbols × 4 timeframes = 24 tasks)
- With 3 workers: ~8 batches, ~30-40s total time

**Impact if changed:**
- Increase to 6: Faster analysis (~15-20s), higher CPU usage
- Decrease to 1: Sequential processing (~2-3 minutes)

**Related variables:**
- `MAX_METRICS_HISTORY = 100` (metrics storage)

---

## Advanced Settings

### Debug Mode

**Location:** bot.py line 614  
**Type:** Boolean  
**Current Value:** `False`  
**Purpose:** Enable verbose logging for troubleshooting

**Impact if changed:**
- `True`: Detailed logs (signal analysis, cache hits, API calls)
- `False`: Production logging (errors and important events only)

**Related variables:**
- Logging configuration (lines 34-38)

---

### Access Control

**Location:** bot.py lines 301-330  
**Type:** Set, Dictionary, String  
**Purpose:** Restrict bot usage to authorized users

**Variables:**

```python
# Line 301-304
ALLOWED_USERS = {
    7003238836,  # Hardcoded owner (emergency fallback)
    int(os.getenv('OWNER_CHAT_ID', '7003238836'))
}

# Line 307
ALLOWED_USERS_FILE = f"{BASE_PATH}/allowed_users.json"

# Line 320
ACCESS_ATTEMPTS = {}  # Track unauthorized access attempts

# Line 330
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH', 
    hashlib.sha256("8109".encode()).hexdigest())
```

**Security Features:**
- Hardcoded owner ID prevents lockout
- Failed access attempts logged
- Admin password hashed (never stored plaintext)

**Impact if changed:**
- Add to ALLOWED_USERS: Grant bot access
- Change ADMIN_PASSWORD_HASH: New admin password

**Related variables:**
- `ACCESS_DENIED_MESSAGE` (line 323)

---

## Summary of Critical Issues

| Issue | Severity | Location | Impact |
|-------|----------|----------|--------|
| Position tracking broken | ❌ Critical | bot.py:11482 | No DB records, checkpoints never trigger |
| Threshold inconsistency (60% vs 65%) | ❌ Critical | bot.py:11199 | 50% data loss for ML training |
| trading_journal.json missing | ❌ Critical | Not created | No ML training data |
| bot_stats.json missing | ⚠️ High | Not created | No win-rate statistics |

**Recommended Fixes:**
1. Fix position tracking code path (unreachable code issue)
2. Align thresholds to 60% (or 65% for both)
3. Ensure trading_journal.json created on first write
4. Initialize bot_stats.json on startup

---

**Documentation Version:** 1.0  
**Last Updated:** January 17, 2026  
**Word Count:** ~4,800 words
