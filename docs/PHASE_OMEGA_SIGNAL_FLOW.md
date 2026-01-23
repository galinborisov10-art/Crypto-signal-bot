# Phase Ω: Signal Lifecycle Trace

**Analysis Date:** 2026-01-23  
**Analysis Type:** Forensic Code Audit (Read-Only)  
**Scope:** bot.py, ict_signal_engine.py, telegram message delivery

---

## Signal Flow Overview

### Complete Signal Path (Generation → Telegram)

```
[SCHEDULER/COMMAND TRIGGER]
    ↓
ict_engine.generate_signal() [ict_signal_engine.py:672]
    ↓
Returns: ICTSignal | NO_TRADE dict | None
    ↓
[DEDUPLICATION] is_signal_duplicate() / is_signal_already_sent()
    ↓
[COOLDOWN CHECK] check_signal_cooldown() (60min default)
    ↓
[FORMAT] format_ict_signal_13_point() / format_no_trade_message()
    ↓
context.bot.send_message() → Telegram
```

**Entry Points:** 8 distinct call sites in bot.py (lines 7936, 8276, 8633, 11056, 11316, 11993, 12846, 15355)

---

## Signal Generation

### Primary Signal Generator

**File:** `ict_signal_engine.py`  
**Method:** `generate_signal(df, symbol, timeframe, mtf_data=None)`  
**Lines:** 672-1656 (985 lines)

#### Function Signature
```python
def generate_signal(
    self,
    df: pd.DataFrame,
    symbol: str,
    timeframe: str = "1H",
    mtf_data: Optional[Dict[str, pd.DataFrame]] = None
) -> Optional[ICTSignal]:
```

#### Return Values (3 distinct types)

1. **ICTSignal object** (lines 1585-1623)
   - Contains: entry_price, sl_price, tp_price, confidence, bias, signal_type
   - Full ICT analysis with 13-point output
   - Returned when all validation gates pass

2. **Dict with type='NO_TRADE'** (multiple exit points)
   - Contains: type, blocked_at_step, reason, symbol, timeframe, diagnostics
   - Returned when direction unclear or criteria unmet
   - Examples: Lines 800, 852, 894, 940, 1003, 1078, 1145, 1195, 1281, 1353

3. **None** (failure cases)
   - Line 1512: Execution eligibility failure (§2.3)
   - Line 1539: Risk admission failure (§2.4)
   - Line 1564: Cached signal returned earlier
   - Line 698: Insufficient data (<50 bars)

#### Processing Steps (12-step unified sequence)

**Lines 704-782:** Steps 1-7 (HTF bias, MTF structure, TF hierarchy, liquidity, ICT components, bias determination)  
**Lines 783-1350:** Steps 8-10 (Entry zone calculation, SL/TP levels)  
**Lines 1351-1570:** Steps 11-12 (Confidence scoring, final validation)

---

## Signal Processing Pipeline

### Call Site #1: Scheduled Auto-Signals (PRIMARY PATH)

**File:** `bot.py`  
**Function:** `send_alert_signal(context)`  
**Line:** 11017  
**Trigger:** APScheduler job (every 60-300 seconds, configurable)

**Nested Function:** `analyze_single_pair(symbol, timeframe)` (line 11028)  
**Invocation:** Line 11056 → `ict_signal = ict_engine.generate_signal(df, symbol, timeframe, mtf_data)`

**Flow:**
1. Fetches klines for symbol/timeframe (lines 11032-11049)
2. Fetches MTF data via `fetch_mtf_data()` (line 11052)
3. Calls `generate_signal()` (line 11056)
4. Checks for NO_TRADE/HOLD signals (lines 11064-11069)
5. **Persistent deduplication** check (lines 11072-11088) [PR #111-112]
6. Formats message (line 11100+)
7. Sends via `context.bot.send_message()` (estimated line 11160+)

**Parallelism:** All symbol/timeframe pairs analyzed concurrently via `asyncio.gather()` (line ~11150)

---

### Call Site #2: Manual Analysis Command

**File:** `bot.py`  
**Function:** `analyze_pair_handler(update, context)`  
**Line:** 8276  
**Trigger:** User command `/analyze [SYMBOL] [TIMEFRAME]`

**Invocation:** Line 8276 → `ict_signal = ict_engine.generate_signal(df, symbol, timeframe, mtf_data)`

**Flow:**
1. Parses user command (lines 8230-8260)
2. Fetches klines + MTF data (lines 8261-8275)
3. Calls `generate_signal()` (line 8276)
4. **Cooldown check** (60-minute cooldown) (line 8280+)
5. Formats NO_TRADE or signal message (lines 8290-8310)
6. Sends via `update.message.reply_text()` (line 8310+)

**Deduplication:** Uses `is_signal_already_sent()` in-memory check (line ~8285)

---

### Call Site #3: Trade Re-Analysis (80% TP Alert)

**File:** `bot.py`  
**Function:** `check_position_status()` nested in `check_active_signals`  
**Line:** 11993  
**Trigger:** Scheduler monitoring active trades

**Invocation:** Line 11993 → `current_signal = ict_engine_global.generate_signal(df, symbol, timeframe, mtf_data)`

**Purpose:** Re-analyzes market conditions when trade reaches 80% TP progress  
**Action:** Determines if bias still holds or if partial exit recommended

---

### Call Site #4: Check Command (Read-Only)

**File:** `bot.py`  
**Function:** `check_analysis_handler(update, context)`  
**Lines:** 7936, 12846  
**Trigger:** User command `/check [SYMBOL] [TIMEFRAME]`

**Invocation:** Lines 7936, 12846 → `ict_signal = ict_engine.generate_signal(...)`

**Flow:** Similar to `/analyze` but includes:
- Detailed ICT component logging (line 12850+)
- Bias calculation breakdown (line 12870+)
- Entry zone diagnostics (line 12890+)

---

## Signal Validation

### Validation Gates (Sequential Filters)

**Location:** `ict_signal_engine.py:generate_signal()`

#### Gate 1: Data Sufficiency
- **Line:** 696-698
- **Check:** `if len(df) < 50: return None`
- **Reason:** Insufficient bars for ICT analysis

#### Gate 2: Entry Gating (§2.1)
- **Lines:** 1489-1497
- **Check:** `evaluate_entry_gating()` from `entry_gating_evaluator.py`
- **Returns:** `NO_TRADE` dict if gate fails
- **Status:** ENTRY_GATING_AVAILABLE = True (line 31)

#### Gate 3: Confidence Threshold (§2.2)
- **Lines:** 1498-1511
- **Check:** `evaluate_confidence_threshold()`
- **Returns:** `None` if confidence < threshold
- **Status:** CONFIDENCE_THRESHOLD_AVAILABLE = True (line 39)

#### Gate 4: Execution Eligibility (§2.3)
- **Lines:** 1513-1538
- **Check:** `evaluate_execution_eligibility()`
- **Returns:** `None` if not eligible
- **Status:** EXECUTION_ELIGIBILITY_AVAILABLE = True (line 45)

#### Gate 5: Risk Admission (§2.4)
- **Lines:** 1540-1563
- **Check:** `evaluate_risk_admission()`
- **Returns:** `None` if risk too high
- **Status:** RISK_ADMISSION_AVAILABLE = True (line 52)

---

## Signal Delivery

### Telegram Sending Functions

#### Primary: send_signal_alert()
**File:** `bot.py`  
**Line:** 2610  
**Type:** Alert processor (TP_HIT, SL_HIT, 80_PERCENT)

**Parameters:** `alert` dict containing:
- `type`: 'TP_HIT' | 'SL_HIT' | '80_PERCENT'
- `signal`: Original signal data
- `current_price`: Current market price
- `profit_pct` / `loss_pct`: P&L calculation

**Delivery:** Line 2604 → Calls `send_signal_alert()` → sends via bot object

---

#### Primary: send_alert_signal()
**File:** `bot.py`  
**Line:** 11017  
**Type:** Scheduled signal generator

**Trigger:** APScheduler job configured in main() (line ~17400+)  
**Frequency:** Every 60-300 seconds (configurable via user settings)

**Flow:**
1. Analyzes all symbols × timeframes in parallel (line 11028+)
2. Filters valid signals (lines 11064-11088)
3. Formats via `format_ict_signal_13_point()` (line ~11100)
4. Sends via `context.bot.send_message(chat_id=OWNER_CHAT_ID, ...)` (line ~11160)

**send_message() Parameters:**
- `chat_id`: OWNER_CHAT_ID (from env)
- `text`: Formatted HTML message
- `parse_mode='HTML'`
- `disable_notification=False` (alerts active)

---

## Signal State Management

### Signal Object Structure

**Class:** `ICTSignal` (dataclass)  
**File:** `ict_signal_engine.py`  
**Lines:** 152-223

**Fields (22 total):**
```python
symbol: str
signal_type: SignalType  # BUY/SELL/HOLD
timeframe: str
entry_price: float
sl_price: float
tp_price: float
confidence: float  # 0-100
bias: MarketBias
timestamp: str
mtf_bias: Optional[str]
htf_structure: Optional[str]
liquidity_sweep: Optional[bool]
order_blocks: List[str]
fvgs: List[str]
imbalance: Optional[str]
market_structure: Optional[str]
displacement: Optional[bool]
premium_discount: Optional[str]
session_context: Optional[str]
risk_reward: Optional[float]
warnings: List[str]
metadata: Dict[str, Any]
```

**State Transitions:** UNKNOWN (no state machine found in code)

---

## Signal Caching

### Cache Layer #1: Internal Signal Cache

**File:** `ict_signal_engine.py`  
**Lines:** 688-694 (read), 1625-1631 (write)

**Manager:** `self.cache_manager` (initialized in `__init__`)  
**Methods:**
- `get_cached_signal(symbol, timeframe)` → Returns cached ICTSignal or None
- `cache_signal(symbol, timeframe, signal)` → Stores signal in cache

**Cache Key:** `f"{symbol}_{timeframe}"`  
**TTL:** UNKNOWN (depends on cache_manager implementation)

**Read Logic (lines 688-694):**
```python
if self.cache_manager:
    cached_signal = self.cache_manager.get_cached_signal(symbol, timeframe)
    if cached_signal:
        return cached_signal  # Early return
```

**Write Logic (lines 1625-1631):**
```python
if self.cache_manager:
    self.cache_manager.cache_signal(symbol, timeframe, result)
```

---

### Cache Layer #2: Persistent Deduplication Cache

**File:** `bot.py` (imports from `signal_cache.py`)  
**Lines:** 11072-11088 (read), ~11140 (write assumed)

**Function:** `is_signal_duplicate(symbol, signal_type, timeframe, entry_price, confidence, cooldown_minutes, base_path)`

**Storage:** File-based JSON cache (`sent_signals_cache.json`)  
**Cooldown:** 60 minutes default (configurable)

**Deduplication Logic:**
1. Checks if similar signal sent within cooldown window
2. Compares: symbol, signal_type, timeframe, entry_price (~0.5% tolerance), confidence
3. Returns: `(is_dup: bool, reason: str)`

**Fallback:** If `SIGNAL_CACHE_AVAILABLE = False`, uses in-memory `is_signal_already_sent()` (line 11090+)

---

## Signal Deduplication

### Deduplication Strategy #1: Persistent Cache (PR #111-112)

**File:** `bot.py`  
**Lines:** 11072-11088

**Implementation:**
```python
if SIGNAL_CACHE_AVAILABLE:
    is_dup, reason = is_signal_duplicate(
        symbol=symbol,
        signal_type=ict_signal.signal_type.value,
        timeframe=timeframe,
        entry_price=ict_signal.entry_price,
        confidence=ict_signal.confidence,
        cooldown_minutes=60,
        base_path=BASE_PATH
    )
    if is_dup:
        logger.info(f"🛑 Signal deduplication: {reason} - skipping")
        return None
```

**Conditions for Duplicate:**
- Same symbol
- Same signal_type (BUY/SELL)
- Same timeframe
- Entry price within 0.5% (assumed, needs verification in signal_cache.py)
- Within 60-minute window

---

### Deduplication Strategy #2: In-Memory Fallback

**File:** `bot.py`  
**Lines:** 11090-11098

**Function:** `is_signal_already_sent(symbol, signal_type, timeframe, confidence, entry_price, cooldown_minutes)`

**Storage:** Module-level dict `sent_signals` (assumed, not visible in viewed lines)  
**Lifetime:** Process lifetime only (lost on bot restart)

---

### Cooldown Check (Manual Commands)

**File:** `bot.py`  
**Line:** ~8280 (in `analyze_pair_handler`)

**Function:** `check_signal_cooldown()` (assumed, not directly visible)

**Purpose:** Prevents spam from manual `/analyze` commands  
**Window:** 60 minutes  
**Scope:** Per-user or global (UNKNOWN)

---

## Signal Lifecycle Hooks

### Pre-Generation Hooks

**UNKNOWN** - No explicit hook system found in code

**Possible Implicit Hooks:**
- MTF data fetch (line 11052 in bot.py)
- Cache check (line 688 in ict_signal_engine.py)

---

### Post-Generation Hooks

**UNKNOWN** - No explicit hook system found in code

**Possible Implicit Hooks:**
- Cache write (line 1625 in ict_signal_engine.py)
- Deduplication registration (line ~11140 in bot.py, assumed)
- Signal logging (multiple logger.info calls throughout)

---

### Monitoring Hooks

**File:** `bot.py`  
**Function:** `check_active_signals()` (scheduler job)  
**Line:** 11156+ (estimated)

**Purpose:** Monitors open positions for TP/SL hits and 80% TP alerts

**Re-Analysis Trigger:** Line 11993 → calls `generate_signal()` again for fresh market read

---

## Error Handling

### generate_signal() Error Paths

**No try/except at top level** - Relies on caller to handle exceptions

**Defensive Returns:**
- Line 698: `return None` for insufficient data
- Lines 800+: `return NO_TRADE dict` for analysis failures
- Lines 1512, 1539, 1564: `return None` for validation failures

---

### send_alert_signal() Error Handling

**File:** `bot.py`  
**Line:** 11017  
**Decorator:** `@safe_job("auto_signal", max_retries=3, retry_delay=60)`

**Behavior:**
- Retries up to 3 times on exception
- 60-second delay between retries
- Logs errors via logger.error()

**Individual Pair Failures:**
- Lines 11028-11098 wrapped in try/except (assumed)
- Failed pairs don't crash entire job
- Continue analyzing remaining pairs

---

### send_signal_alert() Error Handling

**File:** `bot.py`  
**Line:** 2610  
**Top-Level Try/Except:** YES (line 2612 → `try:` ... `except Exception as e:`)

**Error Logging:**
```python
except Exception as e:
    logger.error(f"Error sending signal alert: {e}")
```

**No Retry Logic** - Single attempt only

---

## Performance Analysis

### Computational Complexity

**generate_signal() Execution:**
- **Data Processing:** O(n) where n = dataframe length (~200 bars typical)
- **ICT Component Detection:** O(n) per detector (OB, FVG, liquidity)
- **MTF Analysis:** O(m*n) where m = number of MTF timeframes (typically 2-3)

**Estimated Execution Time:** UNKNOWN (no benchmarks found)

---

### Parallelization

**Scheduler Job (send_alert_signal):**
- Line ~11150: Uses `asyncio.gather()` for parallel analysis
- Analyzes all symbols × timeframes concurrently
- Typical load: 3-5 symbols × 4 timeframes = 12-20 concurrent tasks

**Bottlenecks (Suspected):**
1. Binance API rate limits (kline fetches)
2. Synchronous ICT analysis (not async)
3. Cache lock contention (UNKNOWN)

---

### Memory Management

**File:** `bot.py`  
**Line:** 11022  
**Comment:** "ASYNC OPTIMIZED с memory cleanup"

**Cleanup Strategy:** UNKNOWN (implementation not visible in viewed sections)

**GC Calls:**
- Line 9 imports `gc`
- Usage: UNKNOWN (need to search for `gc.collect()` calls)

---

## Diagnostic Findings

### 🔴 CRITICAL: Multiple Return Types

**File:** `ict_signal_engine.py:generate_signal()`  
**Issue:** Returns 3 different types: `ICTSignal | Dict | None`

**Impact:**
- Callers must handle 3 cases
- Type safety compromised
- Risk of `AttributeError` if caller assumes ICTSignal

**Example Risk (bot.py:11064):**
```python
if not ict_signal or (isinstance(ict_signal, dict) and ict_signal.get('type') == 'NO_TRADE'):
    return None
```
→ Explicit dict check required

---

### 🟡 WARNING: Cache Manager Availability Conditional

**File:** `ict_signal_engine.py`  
**Lines:** 688, 1625

**Issue:** Cache operations wrapped in `if self.cache_manager:`

**Scenario:** If cache_manager is None:
- No caching occurs
- Performance degraded (redundant analysis)
- Duplicate signals possible if persistent deduplication also fails

---

### 🟡 WARNING: Deduplication Dual-Path Complexity

**File:** `bot.py`  
**Lines:** 11072-11098

**Issue:** Two deduplication systems running in parallel:
1. Persistent cache (`is_signal_duplicate`)
2. In-memory fallback (`is_signal_already_sent`)

**Risk:**
- Synchronization issues if both active
- Unclear precedence rules
- Memory leak if in-memory cache unbounded

---

### 🟢 INFO: No Explicit State Machine

**Finding:** Signal state transitions not managed via state machine pattern

**Current State Tracking:**
- Signals stored in journal (positions.db assumed)
- Status inferred from TP/SL hit alerts
- Re-analysis triggered at 80% TP progress

**Implication:** State transitions implicit, harder to audit

---

### 🟢 INFO: Error Handling Inconsistent

**Patterns Found:**
1. `send_alert_signal()`: Decorator-based retry logic (line 11017)
2. `send_signal_alert()`: Try/except with logging (line 2612)
3. `generate_signal()`: No exception handling (relies on caller)

**Recommendation:** Standardize error handling strategy

---

### 🔵 UNKNOWN: Cache TTL Values

**Files:** `ict_signal_engine.py`, `signal_cache.py` (not analyzed)

**Missing Data:**
- Cache expiration time
- LRU vs FIFO eviction
- Max cache size
- Persistence strategy

**Required:** Analyze `cache_manager.py` and `signal_cache.py`

---

### 🔵 UNKNOWN: Telegram API Rate Limits

**File:** `bot.py` (all send_message calls)

**Missing Data:**
- Rate limit enforcement
- Queue system for burst sends
- Backpressure handling

**Required:** Analyze telegram bot framework configuration

---

**END OF FORENSIC ANALYSIS - Phase Ω.1**
