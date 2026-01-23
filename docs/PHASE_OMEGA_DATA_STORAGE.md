# Phase Ω: Data Flow Matrix

**Analysis Date:** 2026-01-23  
**Analysis Type:** Forensic Data Storage Audit (Read-Only)  
**Scope:** All data persistence, caching, and state management  
**Method:** File:line tracing of write/read operations

---

## Data Storage Overview

The Crypto-signal-bot uses a hybrid storage architecture combining:
- **JSON files** for human-readable structured data
- **SQLite database** for relational position tracking
- **Pickle files** for binary ML model serialization
- **In-memory caches** for performance optimization

**Total Storage Footprint:** ~5-50MB (varies with trade history)

**Critical Finding:** 4 read/write mismatches identified where data consumers read from different sources than producers write to.

---

## Data Sources

### Primary Data Sources (Write Operations)

| Source | File Path | Writer | Write Frequency | Size |
|--------|-----------|--------|-----------------|------|
| **Signal Cache** | `sent_signals_cache.json` | `signal_cache.py:86-87` | Per signal generated | ~50-500KB |
| **Trading Journal** | `trading_journal.json` | `bot.py` (journal append) | Per trade logged | ~1-10MB |
| **Daily Reports** | `daily_reports.json` | `daily_reports.py:317-318` | Daily (24h) | ~500KB-2MB |
| **Bot Statistics** | `bot_stats.json` | `bot.py` (stats update) | Per signal | ~100-500KB |
| **Position Database** | `positions.db` | `position_manager.py:283+` | Per position change | ~100KB-1MB |
| **ML Models** | `models/ml_model.pkl` | `ml_engine.py:240-241` | Every 7 days or 20 signals | ~500KB-5MB |
| **ML Performance** | `models/ml_performance.json` | `ml_engine.py:309-311` | Per training cycle | ~10-50KB |
| **Backtest Results** | `backtest_results/{symbol}_{tf}.json` | `legacy_backtest/ict_backtest_simulator.py:391-392` | Per backtest run | ~50-200KB each |
| **Backtest Aggregate** | `ict_backtest_results.json` | `legacy_backtest/ict_backtest_simulator.py:558-565` | Per backtest run | ~1-5MB |
| **Backtest Archive** | `backtest_archive/YYYY-MM-DD/` | `legacy_backtest/ict_backtest_simulator.py:398-437` | Daily | ~10-50MB total |

---

## Data Structures

### Signal Cache (`sent_signals_cache.json`)

**Purpose:** Deduplication of signals to prevent spam  
**Retention:** 7 days (168 hours)  
**Structure:**
```json
{
  "BTCUSDT_1h_LONG_2026-01-23": {
    "timestamp": 1737648000,
    "last_checked": 1737648000,
    "entry_price": 100000.0,
    "confidence": 75.5
  }
}
```

**Key:** `{symbol}_{timeframe}_{direction}_{date}`

**Write Operations:**
- **File:** `signal_cache.py:86-87`
- **Function:** `save_sent_signals()`
- **Triggers:**
  - Line 127: First signal for key
  - Line 144: Invalid entry price detected
  - Line 158: New signal passes entry difference check
  - Line 169: Duplicate detected (updates last_checked)

**Read Operations:**
- **File:** `signal_cache.py:45-46`
- **Function:** `load_sent_signals()`
- **Triggers:**
  - Line 114: `is_signal_duplicate()` check
  - bot.py startup: Cache validation

**Cleanup:**
- **File:** `signal_cache.py:52-57`
- **Function:** `load_sent_signals()` (during load)
- **Logic:** Deletes entries older than 168 hours
- **⚠️ ISSUE H3:** No check against active positions in `positions.db`

---

### Trading Journal (`trading_journal.json`)

**Purpose:** Source of truth for all trade history  
**Retention:** Indefinite (manual cleanup required)  
**Structure:**
```json
{
  "trades": [
    {
      "id": "BTCUSDT_1h_20260123_150000",
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "direction": "LONG",
      "entry_price": 100000.0,
      "sl_price": 97000.0,
      "tp_prices": [109000.0, 106000.0, 115000.0],
      "confidence": 75.5,
      "timestamp": 1737648000,
      "status": "active",
      "conditions": {...},
      "ml_features": {...}
    }
  ]
}
```

**Write Operations:**
- **File:** `bot.py` (multiple locations in trade logging functions)
- **Append-only:** New trades added to `trades` array
- **⚠️ ISSUE C3:** No file locking - race condition risk with ML training reads

**Read Operations:**
1. **Daily Reports** - `daily_reports.py:33-40`
   ```python
   with open(self.journal_path, 'r') as f:
       journal = json.load(f)
       return journal.get('trades', [])
   ```

2. **ML Training** - `ml_engine.py:177-180`
   ```python
   with open(self.trading_journal_path, 'r') as f:
       journal = json.load(f)
   ```

3. **Backtest Validation** - `journal_backtest.py:233-274`

**⚠️ MISMATCH M1:** Daily reports fall back to `bot_stats.json` if journal empty, creating dual source-of-truth confusion.

---

### Daily Reports (`daily_reports.json`)

**Purpose:** Daily performance snapshots  
**Retention:** Indefinite (archive recommended)  
**Structure:**
```json
{
  "2026-01-23": {
    "date": "2026-01-23",
    "total_signals": 12,
    "active_trades": 3,
    "closed_trades": 9,
    "win_rate": 66.7,
    "total_pnl": 1250.50,
    "best_trade": {...},
    "worst_trade": {...}
  }
}
```

**Write Operations:**
- **File:** `daily_reports.py:317-318`
- **Function:** `_save_report()`
- **Process:**
  1. Read existing reports
  2. Append new day's report
  3. Write entire object back

**Data Sources (Read Before Write):**
- **Primary:** `trading_journal.json` - `daily_reports.py:33-40`
- **Fallback:** `bot_stats.json` - `daily_reports.py:45-51`

**⚠️ MISMATCH M1:** Dual data sources create inconsistency risk

---

### Position Database (`positions.db`)

**Purpose:** SQLite database for active position tracking  
**Retention:** Active positions only (closed positions removed)  
**Schema:**
```sql
CREATE TABLE positions (
    id INTEGER PRIMARY KEY,
    signal_id TEXT UNIQUE,
    symbol TEXT,
    timeframe TEXT,
    direction TEXT,
    entry_price REAL,
    sl_price REAL,
    tp1_price REAL,
    tp2_price REAL,
    tp3_price REAL,
    confidence REAL,
    status TEXT,
    entry_timestamp INTEGER,
    checkpoint_25_triggered INTEGER DEFAULT 0,
    checkpoint_50_triggered INTEGER DEFAULT 0,
    checkpoint_75_triggered INTEGER DEFAULT 0,
    checkpoint_85_triggered INTEGER DEFAULT 0
);

CREATE TABLE checkpoint_alerts (
    id INTEGER PRIMARY KEY,
    signal_id TEXT,
    checkpoint_level REAL,
    checkpoint_price REAL,
    recommendation TEXT,
    confidence_at_checkpoint REAL,
    timestamp INTEGER,
    FOREIGN KEY (signal_id) REFERENCES positions(signal_id)
);
```

**Write Operations:**
- **New Position:** `position_manager.py:163-225` - `add_position()`
- **Update Checkpoint:** `position_manager.py:304-345` - `update_checkpoint_triggered()`
- **Log Alert:** `position_manager.py:392-416` - `log_checkpoint_alert()`
- **Close Position:** `position_manager.py:442-479` - `close_position()`

**Read Operations:**
- **Get Position:** `position_manager.py:227-260` - `get_position()`
- **Get Active Positions:** `position_manager.py:262-281` - `get_active_positions()`
- **Check Checkpoints:** `position_manager.py:357-390` - `get_checkpoint_status()`

**⚠️ ISSUE H3:** Signal cache cleanup doesn't query `positions.db` to verify trade is inactive before deletion.

---

### ML Model Artifacts

**Location:** `models/` directory  
**Files:**
1. `ml_model.pkl` - Serialized RandomForest/Ensemble model
2. `ml_scaler.pkl` - Feature scaler (StandardScaler)
3. `ml_performance.json` - Training metrics history
4. `ml_feature_importance.json` - Feature weights

**Write Operations:**

**ml_engine.py:240-241** - Model save after training:
```python
joblib.dump(self.model, self.model_path)
joblib.dump(self.scaler, self.scaler_path)
```

**ml_engine.py:306-311** - Metrics save:
```python
with open(self.feature_importance_path, 'w') as f:
    json.dump(self.feature_importance, f, indent=2)

with open(self.performance_path, 'w') as f:
    json.dump(self.performance_history, f, indent=2)
```

**Read Operations:**

**ml_engine.py:280-286** - Model load on init:
```python
self.model = joblib.load(self.model_path)
self.scaler = joblib.load(self.scaler_path)
```

**ml_engine.py:315-318** - Metrics load:
```python
with open(self.performance_path, 'r') as f:
    self.performance_history = json.load(f)
```

**Training Data Source:**
- Reads from `trading_journal.json` - **ml_engine.py:177-180**
- **⚠️ ISSUE C3:** Concurrent read during journal write (no locking)

---

### Backtest Results

**Multi-Location Storage:**

1. **Individual Results:** `backtest_results/{symbol}_{timeframe}_backtest.json`
   - **Writer:** `legacy_backtest/ict_backtest_simulator.py:367-394`
   - **Format:** One file per symbol+timeframe combination
   - **Size:** ~50-200KB each

2. **Aggregate Results:** `ict_backtest_results.json`
   - **Writer:** `legacy_backtest/ict_backtest_simulator.py:558-565`
   - **Format:** All results combined
   - **Size:** ~1-5MB

3. **Archived Results:** `backtest_archive/YYYY-MM-DD/`
   - **Archiver:** `legacy_backtest/ict_backtest_simulator.py:398-437`
   - **Retention:** 30 days (`cleanup_old_archives()` - lines 441-481)

**⚠️ ISSUE H4:** Duplication between individual files and aggregate creates desync risk.

**Structure Example:**
```json
{
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "period": "2026-01-01 to 2026-01-23",
  "total_signals": 45,
  "winning_trades": 28,
  "losing_trades": 17,
  "win_rate": 62.2,
  "profit_factor": 1.85,
  "total_pnl_pct": 12.5,
  "trades": [...]
}
```

---

## Data Flow Patterns

### Signal Generation Flow

```
┌─────────────────────────────────────────────┐
│  1. Scheduler Trigger (auto_signal_job)    │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  2. Parallel Symbol+TF Analysis             │
│     - Fetch klines from Binance             │
│     - Generate ICT signals                  │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  3. Signal Validation                       │
│     - 12-step ICT pipeline                  │
│     - ML confidence adjustment              │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  4. Deduplication Check                     │
│     READ: sent_signals_cache.json           │
│     - Check if signal exists                │
│     - Validate entry price difference       │
└────────────────┬────────────────────────────┘
                 │
                 ├─ DUPLICATE → Update last_checked
                 │                  └─ WRITE: cache
                 │
                 └─ NEW SIGNAL ────────────────┐
                                                │
┌───────────────────────────────────────────────▼──┐
│  5. Signal Storage                              │
│     WRITE: sent_signals_cache.json (line 127)   │
│     WRITE: positions.db (add_position)          │
│     APPEND: trading_journal.json (optional)     │
└───────────────────────────┬─────────────────────┘
                            │
┌───────────────────────────▼─────────────────────┐
│  6. Telegram Delivery                           │
│     - Format message                            │
│     - Send to user                              │
└─────────────────────────────────────────────────┘
```

---

### Position Monitoring Flow

```
┌─────────────────────────────────────────────┐
│  1. Price Update (real-time or periodic)    │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  2. Checkpoint Detection                    │
│     READ: positions.db (active positions)   │
│     - Calculate current P/L %               │
│     - Check if crossed 25/50/75/85% levels  │
└────────────────┬────────────────────────────┘
                 │
                 ├─ NO CHECKPOINT → Continue monitoring
                 │
                 └─ CHECKPOINT HIT ────────────┐
                                                │
┌───────────────────────────────────────────────▼──┐
│  3. Re-analysis Trigger                         │
│     - Fetch current market data                 │
│     - Run full 12-step ICT validation           │
│     - Compare confidence: now vs entry          │
└───────────────────────────┬─────────────────────┘
                            │
┌───────────────────────────▼─────────────────────┐
│  4. Recommendation Generation                   │
│     - Apply decision matrix (6 rules)           │
│     - Determine: HOLD/PARTIAL_CLOSE/CLOSE_NOW   │
│     /MOVE_SL                                    │
└───────────────────────────┬─────────────────────┘
                            │
┌───────────────────────────▼─────────────────────┐
│  5. Storage & Alert                             │
│     WRITE: positions.db (update checkpoint flag)│
│     WRITE: checkpoint_alerts table              │
│     SEND: Telegram advisory message             │
└─────────────────────────────────────────────────┘
```

---

### Daily Report Generation Flow

```
┌─────────────────────────────────────────────┐
│  1. Daily Trigger (24h scheduler)           │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  2. Data Collection                         │
│     READ: trading_journal.json (primary)    │
│     READ: bot_stats.json (fallback)         │
│     - Extract trades for last 24h           │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  3. Metrics Calculation                     │
│     - Win rate                              │
│     - Total P/L                             │
│     - Active vs closed trades               │
│     - Best/worst trades                     │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  4. Report Storage                          │
│     READ: daily_reports.json (existing)     │
│     APPEND: New day's report                │
│     WRITE: daily_reports.json (updated)     │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  5. Telegram Delivery                       │
│     - Format daily summary                  │
│     - Send to owner                         │
└─────────────────────────────────────────────┘
```

---

### ML Training Flow

```
┌─────────────────────────────────────────────┐
│  1. Training Trigger                        │
│     - Time-based: Every 7 days              │
│     - Event-based: Every 20 signals         │
│     - Manual: /retrain_ml command           │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  2. Data Loading                            │
│     READ: trading_journal.json ⚠️ NO LOCK   │
│     - Extract trades array                  │
│     - Filter by status (closed trades)      │
│     - Minimum 50 trades required            │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  3. Feature Extraction                      │
│     - Extract ML features from conditions   │
│     - 6 basic + 9 extended = 15 features    │
│     - Validate feature schema ⚠️ ISSUE H5   │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  4. Model Training                          │
│     - Train/test split (80/20)              │
│     - Ensemble: RF + GB (if ≥100 samples)   │
│     - Fallback: Single RF (if <100)         │
└────────────────┬────────────────────────────┘
                 │
┌────────────────▼────────────────────────────┐
│  5. Model Persistence                       │
│     WRITE: models/ml_model.pkl              │
│     WRITE: models/ml_scaler.pkl             │
│     WRITE: models/ml_performance.json       │
│     WRITE: models/ml_feature_importance.json│
└─────────────────────────────────────────────┘
```

---

## Cache Management

### In-Memory Caches

**Signal Cache (signal_cache.py):**
- **Type:** In-memory dict, synced to `sent_signals_cache.json`
- **Lifetime:** Process lifetime
- **Sync Strategy:** Load on startup, save after each modification
- **Cleanup:** 7-day TTL, executed during load operation

**No other in-memory caches identified** - all other data is file/DB-backed.

---

### File-Based Caches

**sent_signals_cache.json:**
- **Purpose:** Signal deduplication
- **TTL:** 7 days (168 hours)
- **Cleanup Trigger:** During `load_sent_signals()` call
- **Cleanup Logic:**
  ```python
  # signal_cache.py:52-57
  current_time = time.time()
  cache = {k: v for k, v in cache.items() 
           if current_time - v['last_checked'] < 604800}  # 168h * 3600s
  ```
- **⚠️ ISSUE H3:** No validation against `positions.db` - may delete active trades

---

## State Persistence

### Persistent State (Survives Restarts)

| State | Storage | Persistence |
|-------|---------|-------------|
| **Sent signals** | `sent_signals_cache.json` | 7 days |
| **Active positions** | `positions.db` | Until closed |
| **Trade history** | `trading_journal.json` | Indefinite |
| **Daily reports** | `daily_reports.json` | Indefinite |
| **ML models** | `models/*.pkl` | Until retrained |
| **Backtest results** | `backtest_results/*.json` | Indefinite |
| **Backtest archive** | `backtest_archive/YYYY-MM-DD/` | 30 days |

---

### Ephemeral State (Lost on Restart)

| State | Location | Lifetime |
|-------|----------|----------|
| **Scheduler jobs** | APScheduler in-memory | Process lifetime |
| **Telegram bot session** | python-telegram-bot | Process lifetime |
| **ML model in memory** | ml_engine instance | Process lifetime |
| **Signal cache dict** | signal_cache.py module | Process lifetime (synced to file) |

**Recovery on Restart:**
- Scheduler jobs: Re-registered from config in `bot.py` startup
- Telegram session: Reconnects automatically
- ML models: Reloaded from `models/*.pkl` files
- Signal cache: Reloaded from `sent_signals_cache.json`
- Active positions: Reloaded from `positions.db`

---

## Database Operations

### SQLite Database: `positions.db`

**Connection Management:**
- **File:** `position_manager.py:55-78`
- **Connection:** `sqlite3.connect(self.db_path)`
- **Thread Safety:** Not thread-safe (single-connection design)
- **Auto-commit:** No - explicit commit after each operation

**Table Creation:**
- **Trigger:** On PositionManager instantiation
- **File:** `position_manager.py:84-142`
- **Method:** `_create_tables()`

**CRUD Operations:**

| Operation | Function | Lines | SQL Type |
|-----------|----------|-------|----------|
| **CREATE** | `add_position()` | 163-225 | INSERT |
| **READ** | `get_position()` | 227-260 | SELECT |
| **READ ALL** | `get_active_positions()` | 262-281 | SELECT |
| **UPDATE** | `update_checkpoint_triggered()` | 304-345 | UPDATE |
| **DELETE** | `close_position()` | 442-479 | DELETE |
| **INSERT ALERT** | `log_checkpoint_alert()` | 392-416 | INSERT |

**Example Queries:**

**Add Position (Lines 189-224):**
```sql
INSERT OR REPLACE INTO positions (
    signal_id, symbol, timeframe, direction,
    entry_price, sl_price, tp1_price, tp2_price, tp3_price,
    confidence, status, entry_timestamp
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
```

**Update Checkpoint (Lines 318-345):**
```sql
UPDATE positions
SET checkpoint_{level}_triggered = 1
WHERE signal_id = ?
```

**Get Active Positions (Lines 270-279):**
```sql
SELECT * FROM positions WHERE status = 'active'
```

---

## File System Usage

### Directory Structure

```
/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/
├── sent_signals_cache.json
├── trading_journal.json
├── daily_reports.json
├── bot_stats.json
├── positions.db
├── ict_backtest_results.json
├── backtest_results/
│   ├── BTCUSDT_1h_backtest.json
│   ├── BTCUSDT_4h_backtest.json
│   ├── ETHUSDT_1h_backtest.json
│   └── ...
├── backtest_archive/
│   ├── 2026-01-20/
│   ├── 2026-01-21/
│   └── 2026-01-22/
└── models/
    ├── ml_model.pkl
    ├── ml_scaler.pkl
    ├── ml_performance.json
    └── ml_feature_importance.json
```

### File Size Monitoring

**Health Check (bot.py:16785-16791):**
```python
important_files = {
    'trading_journal.json',
    'models/ict_model.pkl',
    'sent_signals_cache.json'
}
```

**Disk Usage Checks:**
- **Warning:** >85% disk usage - `bot.py:16811-16816`
- **Critical:** >95% disk usage

**Log File Monitoring:**
- **File:** `bot.log`
- **Size Check:** Line 16826
- **Warning Threshold:** >500MB

---

## Memory Management

### ML Model Loading

**Lazy Loading:**
- Models loaded only when ML features are enabled
- **File:** `ict_signal_engine.py:137-151`
- **Trigger:** On first signal generation requiring ML

**Memory Footprint:**
- ml_model.pkl: ~500KB-5MB (depends on training samples)
- ml_scaler.pkl: ~10-50KB
- In-memory model object: ~10-50MB (when loaded)

---

### DataFrame Cleanup

**Signal Generation Cleanup:**
- **File:** `bot.py:11139-11147`
- **Method:** Delete DataFrame after signal generation
  ```python
  # Line 11139: Explicit cleanup
  for result in results:
      if result and 'df' in result:
          del result['df']  # Free memory
  ```

**Backtest Cleanup:**
- DataFrames not explicitly deleted - relies on Python garbage collection

---

## Data Integrity

### Validation Checks

**Signal Cache Validation:**
- **File:** `signal_cache.py:190-214`
- **Function:** `validate_and_repair_cache()`
- **Checks:**
  1. File exists and is valid JSON
  2. All entries have required fields
  3. Timestamps are valid integers
  4. Entry prices are valid floats
  5. Confidence values are in 0-100 range

**Position Database Validation:**
- **No explicit validation** - relies on SQLite schema constraints
- **Missing:** Foreign key constraint validation on checkpoint_alerts

**Journal Integrity:**
- **No validation** - assumes valid JSON structure
- **⚠️ RISK C3:** Concurrent writes may corrupt file

---

### Backup Strategies

**Backtest Results:**
- **Automatic archival:** `legacy_backtest/ict_backtest_simulator.py:398-437`
- **Frequency:** Daily
- **Retention:** 30 days
- **Location:** `backtest_archive/YYYY-MM-DD/`

**No other automated backups identified:**
- trading_journal.json: No backup
- positions.db: No backup
- sent_signals_cache.json: No backup
- daily_reports.json: No backup

**Recommendation:** Implement daily backup cron job for critical files.

---

## Synchronization Mechanisms

### File Locking

**Current State:** **NO FILE LOCKING IMPLEMENTED**

**⚠️ CRITICAL ISSUE C3:** `trading_journal.json` accessed concurrently:
- **Writers:** `bot.py` (trade logging)
- **Readers:** `ml_engine.py` (training), `daily_reports.py` (reporting)
- **Risk:** Corrupted JSON during concurrent read/write

**Recommended Fix:**
```python
import fcntl

# ml_engine.py:177-180 (add locking)
with open(self.trading_journal_path, 'r') as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared read lock (auto-released on close)
    journal = json.load(f)

# bot.py journal append (add locking)
with open('trading_journal.json', 'r+') as f:
    fcntl.flock(f.fileno(), fcntl.LOCK_EX)  # Exclusive write lock (auto-released on close)
    journal = json.load(f)
    journal['trades'].append(new_trade)
    f.seek(0)
    f.truncate()  # Truncate first to clear old content
    json.dump(journal, f, indent=2)
```

---

### Database Transactions

**SQLite Auto-commit:** Disabled (explicit commit required)

**Transaction Examples:**

**position_manager.py:216-224:**
```python
cursor.execute("""INSERT OR REPLACE INTO positions ...""")
self.conn.commit()
```

**position_manager.py:341-345:**
```python
cursor.execute("""UPDATE positions SET checkpoint_...""")
self.conn.commit()
```

**No multi-statement transactions** - each operation is atomic

---

## Diagnostic Observations

### 🔴 Critical Read/Write Mismatches

#### **Mismatch 1: Daily Reports Data Source**
- **Writer:** Daily reports don't write to journal
- **Primary Reader:** `daily_reports.py:33-40` reads `trading_journal.json`
- **Fallback Reader:** `daily_reports.py:45-51` reads `bot_stats.json`
- **Issue:** If journal is empty but stats has data, report uses fallback without indication
- **Evidence:** Lines 33-51 in daily_reports.py
- **Impact:** Inconsistent reporting data source
- **Fix Proposal:** Log warning when fallback is used, ensure single source of truth

#### **Mismatch 2: Signal Cache vs Active Positions**
- **Writer:** `signal_cache.py:86-87` writes signals
- **Cleanup:** `signal_cache.py:52-57` deletes entries >7 days old
- **Missing Reader:** No check against `positions.db` before deletion
- **Issue:** Active long-term trades (>7 days) may be deleted from cache
- **Evidence:** Cache cleanup at lines 52-57, no position DB query
- **Impact:** Re-signaling of active trades possible
- **Fix Proposal:** Query `positions.db` before deletion, skip if position active

#### **Mismatch 3: Backtest Storage Duplication**
- **Writer 1:** `legacy_backtest/ict_backtest_simulator.py:391-392` writes individual files
- **Writer 2:** `legacy_backtest/ict_backtest_simulator.py:558-565` writes aggregate
- **Issue:** Two separate write operations, no atomicity guarantee
- **Evidence:** Lines 367-394 (individual) vs 558-565 (aggregate)
- **Impact:** Desynchronization if one write fails
- **Fix Proposal:** Single write operation or transaction-like guarantee

#### **Mismatch 4: ML Feature Extraction**
- **Training:** `ml_engine.py:177-180` reads journal structure
- **Prediction:** `ml_engine.py:64-75` extracts from `analysis` dict
- **Issue:** Feature names must match between training and prediction
- **Evidence:** Journal reads at 177-180, dict extraction at 64-75
- **Impact:** Silent feature mismatch causes poor predictions
- **Fix Proposal:** Schema validation at both training and prediction time

---

### Storage Optimization Opportunities

1. **Signal Cache Compression:** 7-day retention creates ~10,000+ entries, JSON is inefficient
2. **Journal Partitioning:** Single file grows indefinitely, consider monthly partitions
3. **Position DB Indexing:** Add indexes on signal_id, status for faster queries
4. **Backtest Archive Compression:** Compress archived results (30-day retention)
5. **ML Model Versioning:** Keep last 3 model versions for rollback capability

---

### Data Consistency Recommendations

1. **Implement File Locking:** All JSON file access should use `fcntl` locks
2. **Atomic Writes:** Use temp file + rename pattern for JSON updates
3. **Database Constraints:** Add foreign keys between positions and checkpoint_alerts
4. **Backup Strategy:** Daily cron job backing up critical files to `/backups`
5. **Schema Validation:** Add JSON schema validation for all structured files
6. **Single Source of Truth:** Eliminate fallback data sources (e.g., bot_stats.json)

---

**END OF DATA FLOW MATRIX**

**Files Analyzed:** 15+ storage locations  
**Read/Write Operations:** 50+ traced with file:line  
**Critical Mismatches:** 4 identified with fix proposals  
**Optimization Opportunities:** 6 documented
