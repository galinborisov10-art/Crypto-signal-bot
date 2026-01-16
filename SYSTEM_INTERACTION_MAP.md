# SYSTEM INTERACTION MAP - PR #123 Real-World System Diagnostic

**Generated:** 2026-01-16  
**Purpose:** Visualize how all components interact in the Crypto Signal Bot system

---

## 1. FILE DEPENDENCY TREE

```
bot.py (18,507 lines) - MAIN CONTROLLER
├─ Imports & Dependencies:
│  ├─ ict_signal_engine.py (17 ICT detectors)
│  ├─ ml_engine.py (ML enhancement)
│  ├─ ml_predictor.py (Fallback predictions)
│  ├─ position_manager.py (DB operations)
│  ├─ real_time_monitor.py (Position tracking)
│  ├─ ict_80_alert_handler.py (Re-analysis)
│  ├─ chart_generator.py (Visualization)
│  ├─ telegram_formatter_bg.py (Message formatting)
│  ├─ system_diagnostics.py (Health checks)
│  └─ daily_reports.py (Report generation)
│
├─ Data Files (Read/Write):
│  ├─ ✅ sent_signals_cache.json (WRITE - duplicate detection)
│  ├─ ❌ bot_stats.json (WRITE - MISSING FILE)
│  ├─ ❌ trading_journal.json (WRITE - MISSING FILE)
│  ├─ 🟡 positions.db (WRITE - empty database)
│  ├─ 🟡 "bot. log" (WRITE - minimal activity)
│  └─ ✅ daily_reports.json (READ - exists)
│
└─ External APIs:
   ├─ Binance API (price data, klines)
   ├─ Telegram API (send messages, photos)
   └─ (Optional) News APIs, Fear & Greed Index

ict_signal_engine.py
├─ Imports 17 ICT Detector Modules:
│  ├─ order_block_detector.py
│  ├─ fvg_detector.py
│  ├─ liquidity_map.py
│  ├─ breaker_block_detector.py
│  ├─ sibi_ssib_detector.py
│  ├─ ilp_detector.py
│  ├─ smz_mapper.py
│  ├─ mtf_analyzer.py
│  ├─ ict_whale_detector.py
│  ├─ fibonacci_analyzer.py
│  ├─ luxalgo_ict_analysis.py
│  ├─ luxalgo_ict_concepts.py
│  ├─ luxalgo_sr_mtf.py
│  ├─ luxalgo_chart_generator.py
│  └─ (3 more modules)
│
├─ Optionally Uses:
│  └─ ml_engine.py (confidence enhancement)
│
└─ Returns: ICTSignal object to bot.py

ml_engine.py
├─ Reads:
│  └─ ❌ trading_journal.json (MISSING - can't train)
│
├─ Writes:
│  ├─ ❌ ml_model.pkl (MISSING)
│  ├─ ❌ ml_ensemble.pkl (MISSING)
│  └─ ❌ ml_scaler.pkl (MISSING)
│
└─ Uses: scikit-learn, pandas

position_manager.py
├─ Database: positions.db
│  ├─ CREATE open_positions
│  ├─ CREATE checkpoint_alerts
│  └─ CREATE position_history
│
└─ Methods:
   ├─ create_position() - Insert to open_positions
   ├─ update_checkpoint() - Update checkpoint flags
   └─ close_position() - Move to position_history

real_time_monitor.py
├─ Imports:
│  ├─ position_manager.py (DB access)
│  └─ ict_80_alert_handler.py (Re-analysis)
│
├─ Reads:
│  └─ positions.db (open_positions table)
│
├─ External API:
│  └─ Binance (current price, klines)
│
├─ Telegram:
│  └─ bot.send_message() (checkpoint alerts)
│
└─ Loop: Check prices every 60 seconds

system_diagnostics.py
├─ Reads:
│  ├─ "bot.log" (expects no space) ⚠️
│  ├─ trading_journal.json
│  └─ Other system files
│
└─ Returns: Diagnostic reports with issues

chart_generator.py
├─ Uses: matplotlib, mplfinance
├─ Annotates: ICT zones, levels
└─ Returns: Chart image file
```

---

## 2. DATA FLOW DIAGRAM

### Complete Signal Lifecycle:

```
┌──────────────────────────────────────────────────────────────┐
│                    USER INTERACTION                           │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
                 User sends /signal BTCUSDT 1h
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                   BOT.PY (Main Controller)                    │
│                                                                │
│  1. Validate input (symbol, timeframe)                        │
│  2. Fetch market data from Binance API                        │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│               ICT_SIGNAL_ENGINE.PY                            │
│                                                                │
│  3. Run 17 ICT component detectors:                           │
│     • Order Blocks                                            │
│     • Fair Value Gaps                                         │
│     • Liquidity Zones                                         │
│     • Breaker Blocks                                          │
│     • Displacement                                            │
│     • Market Structure                                        │
│     • MTF Confluence                                          │
│     • (10 more...)                                            │
│                                                                │
│  4. Calculate base confidence (0-100%)                        │
│  5. Return ICTSignal object                                   │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                    ML_ENGINE.PY (Optional)                    │
│                                                                │
│  6. IF models exist:                                          │
│     • Enhance confidence based on history                     │
│     • Adjust TP/SL based on ML predictions                    │
│                                                                │
│  7. Return enhanced ICTSignal                                 │
└──────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌──────────────────────────────────────────────────────────────┐
│                   BOT.PY (Signal Processing)                  │
│                                                                │
│  8. Check duplicate (sent_signals_cache.json) ✅              │
│  9. Check confidence threshold (>= 60%?) ❓                   │
└──────────────────────────────────────────────────────────────┘
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
┌─────────────────────┐   ┌─────────────────────────┐
│  TELEGRAM SEND      │   │  DATA PERSISTENCE       │
│                     │   │                         │
│ 10. Format message  │   │ 12. ❌ bot_stats.json   │
│ 11. Send to user ❓ │   │ 13. ❌ trading_journal  │
│                     │   │ 14. 🟡 positions.db     │
└─────────────────────┘   └─────────────────────────┘
                                      │
                                      ▼
                          ❌ BREAKING POINT
                          (Files don't exist/
                           DB write fails)
                                      │
                                      ▼
                     ┌─────────────────────────────┐
                     │  MONITORING IMPOSSIBLE      │
                     │                             │
                     │  • Monitor has no data      │
                     │  • No checkpoints trigger   │
                     │  • No alerts sent           │
                     └─────────────────────────────┘
```

---

## 3. COMPONENT INTERACTION MATRIX

| Component | Calls | Called By | Reads | Writes | External API |
|-----------|-------|-----------|-------|--------|--------------|
| **bot.py** | All modules | User (Telegram) | Cache, logs | Cache, journal*, stats*, DB* | Binance, Telegram |
| **ict_signal_engine.py** | 17 detectors, ml_engine* | bot.py | - | - | - |
| **ml_engine.py** | sklearn | bot.py, ict_engine | journal* | models* | - |
| **ml_predictor.py** | sklearn | bot.py | models* | - | - |
| **position_manager.py** | sqlite3 | bot.py, monitor | positions.db | positions.db | - |
| **real_time_monitor.py** | position_manager, ict_80 | bot.py (async) | positions.db | checkpoint_alerts | Binance |
| **ict_80_alert_handler.py** | ict_engine | real_time_monitor | - | - | Binance |
| **chart_generator.py** | matplotlib | bot.py | - | chart files | - |
| **system_diagnostics.py** | - | bot.py | logs, journal* | - | - |
| **daily_reports.py** | - | bot.py | journal*, stats* | daily_reports.json | - |

**Legend:**
- `*` = File missing or empty (critical issue)
- `-` = None

---

## 4. CRITICAL INTEGRATION POINTS

### Point 1: Signal → Telegram

**Flow:** `bot.py` → `format message` → `bot.send_message()`

**Status:** ❓ UNKNOWN (no logs)

**Dependencies:**
- Telegram Bot Token
- Chat ID
- Network connection

**Failure Mode:** Silent (no error logs)

---

### Point 2: Signal → Journal

**Flow:** `bot.py` → `log_trade_to_journal()` → `trading_journal.json`

**Status:** 🔴 **BROKEN** (file doesn't exist)

**Code:** bot.py:3309

**Failure Impact:**
- ❌ No ML training data
- ❌ No historical analysis
- ❌ Reports can't generate
- ❌ Statistics incomplete

---

### Point 3: Signal → Database

**Flow:** `bot.py` → `position_manager.create_position()` → `positions.db`

**Status:** 🔴 **BROKEN** (DB empty despite code)

**Code:** bot.py:11479-11520

**Failure Impact:**
- ❌ No position tracking
- ❌ Monitor has nothing to check
- ❌ No checkpoints trigger
- ❌ No alerts sent

---

### Point 4: Database → Monitor

**Flow:** `real_time_monitor` → `position_manager.get_open_positions()` → `positions.db`

**Status:** 🔴 **BROKEN** (no data to monitor)

**Code:** real_time_monitor.py:start_monitoring()

**Failure Impact:**
- ❌ Monitor runs empty or doesn't run
- ❌ Price checks don't occur
- ❌ Checkpoint detection impossible

---

### Point 5: Monitor → Alerts

**Flow:** `real_time_monitor` → `detect checkpoint` → `bot.send_message()`

**Status:** 🔴 **BROKEN** (no checkpoints to detect)

**Failure Impact:**
- ❌ No 25/50/75/80% alerts
- ❌ No position completion notifications
- ❌ User gets initial signal but no follow-up

---

## 5. SINGLE POINTS OF FAILURE (SPOF)

### SPOF #1: trading_journal.json

**Impact if Missing/Corrupt:**
- ❌ ML training impossible
- ❌ Reports fail
- ❌ Historical analysis breaks
- ❌ Diagnostics fail

**Mitigation:** Auto-create on startup

---

### SPOF #2: Binance API

**Impact if Down:**
- ❌ No price data → No signals
- ❌ No monitoring → No checkpoints
- ❌ System completely non-functional

**Mitigation:** Implement fallback API or error handling

---

### SPOF #3: Telegram API

**Impact if Down:**
- ❌ Can't send signals
- ❌ Can't send alerts
- ❌ No user interaction

**Mitigation:** Queue messages, retry logic

---

### SPOF #4: positions.db

**Impact if Corrupt:**
- ❌ Position tracking breaks
- ❌ Historical data lost
- ❌ Monitoring stops

**Mitigation:** Regular backups, WAL mode

---

## 6. BOTTLENECKS

### Bottleneck #1: Signal Generation

**Location:** ict_signal_engine.py

**Duration:** ~2-5 seconds (17 detectors)

**Impact:** 
- Slow user response
- Rate limiting on auto-signals

**Mitigation:** Cache, parallelization

---

### Bottleneck #2: Database Writes

**Location:** position_manager.py

**Duration:** ~10-50ms per write

**Impact:**
- If write fails → tracking stops
- No atomic multi-table writes

**Mitigation:** Transactions, error handling

---

### Bottleneck #3: Real-Time Monitor Loop

**Location:** real_time_monitor.py

**Duration:** Runs every 60s

**Impact:**
- If crashes → no more alerts
- Single thread blocks on errors

**Mitigation:** Error recovery, health checks

---

## 7. DATA LIFECYCLE

### Signal Cache (sent_signals_cache.json):

```
CREATE:  Signal generated → Write cache entry
READ:    Duplicate check → Read cache
UPDATE:  last_checked timestamp
DELETE:  Manual cleanup (no auto-expiry)
SIZE:    705 bytes (5 entries)
```

### Trading Journal (trading_journal.json):

```
CREATE:  ❌ Never (file missing)
READ:    ML training, reports, diagnostics
APPEND:  New trades (if working)
SIZE:    ❌ 0 (doesn't exist)
```

### Positions Database (positions.db):

```
CREATE:  On first run (schema exists)
INSERT:  ❌ Never (0 records)
UPDATE:  Checkpoints, status changes
DELETE:  Move to position_history
SIZE:    44KB (schema only, no data)
```

### ML Models (ml_*.pkl):

```
CREATE:  ❌ Never (files missing)
READ:    Signal enhancement, predictions
UPDATE:  Retraining (if triggered)
SIZE:    ❌ 0 (don't exist)
```

---

## 8. ASYNC TASK ORCHESTRATION

### Main Event Loop (bot.py):

```
Application.run_polling()
  │
  ├─ Command Handlers (sync)
  │  ├─ /signal → signal_cmd()
  │  ├─ /health → health_cmd()
  │  └─ /dailyreport → dailyreport_cmd()
  │
  ├─ Background Tasks (async)
  │  ├─ real_time_monitor.start_monitoring()  ❓
  │  ├─ Scheduler jobs ❓
  │  └─ Health monitors ❓
  │
  └─ Callback Handlers
     └─ Button clicks, inline queries
```

**Status:**
- ✅ Command handlers registered
- ❓ Background tasks unknown (no logs)
- ❓ Scheduler unknown (no logs)

---

## 9. CONFIGURATION DEPENDENCIES

### Environment Variables:

```
TELEGRAM_BOT_TOKEN     - Required ✅
OWNER_CHAT_ID         - Required ✅
BINANCE_API_KEY       - Optional (public endpoints)
BINANCE_SECRET_KEY    - Optional (public endpoints)

AUTO_POSITION_TRACKING_ENABLED   - ❓ Unknown
REAL_TIME_MONITOR_ENABLED        - ❓ Unknown
POSITION_MANAGER_AVAILABLE       - ❓ Unknown
```

**Need to verify:** Configuration flags that control tracking

---

## 10. SUMMARY INTERACTION FLOW

### Working Path:
```
User → Telegram → bot.py → ict_engine → Signal → Cache ✅
```

### Broken Path:
```
Signal → Journal (❌ BREAKS)
       → Database (❌ BREAKS)
       → Monitor (🟡 NO DATA)
       → Alerts (❌ NEVER)
```

### Root Cause Chain:
```
Missing Files (journal, stats)
  ↓
Write Operations Fail
  ↓
Database Remains Empty
  ↓
Monitor Has No Data
  ↓
No Checkpoints Detected
  ↓
No Alerts Sent
```

---

**End of System Interaction Map**
