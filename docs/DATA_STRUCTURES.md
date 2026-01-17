# Data Structures Reference
## Complete Data Format Documentation

**Version:** 2.0.0  
**Documentation Date:** January 17, 2026  
**Repository:** galinborisov10-art/Crypto-signal-bot  
**Related Docs:** [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md) | [TRADING_STRATEGY_EXPLAINED.md](TRADING_STRATEGY_EXPLAINED.md)

---

## Table of Contents
1. [ICTSignal Object](#ictsignal-object)
2. [Database Schema](#database-schema)
3. [JSON Files](#json-files)
4. [Data Flow Diagrams](#data-flow-diagrams)
5. [Message Formats](#message-formats)
6. [Cache Structures](#cache-structures)

---

## ICTSignal Object

### Complete Structure

**Location:** ict_signal_engine.py lines 177-284  
**Type:** Python `@dataclass`  
**Purpose:** Unified trading signal with complete ICT analysis

```python
@dataclass
class ICTSignal:
    """Complete ICT Trading Signal"""
    
    # ============================================
    # CORE IDENTIFICATION
    # ============================================
    timestamp: datetime              # Signal generation time
    symbol: str                      # Trading pair (e.g., "BTCUSDT")
    timeframe: str                   # Primary timeframe ("1h", "2h", "4h", "1d")
    
    # ============================================
    # SIGNAL CLASSIFICATION
    # ============================================
    signal_type: SignalType          # BUY/SELL/HOLD/STRONG_BUY/STRONG_SELL
    signal_strength: SignalStrength  # 1-5 (WEAK to EXTREME)
    confidence: float                # 0-100% confidence score
    
    # ============================================
    # PRICE LEVELS
    # ============================================
    entry_price: float               # Recommended entry price
    sl_price: float                  # Stop loss price
    tp_prices: List[float]           # [TP1, TP2, TP3] targets
    risk_reward_ratio: float         # Calculated RR ratio
    
    # ============================================
    # ICT PATTERN COMPONENTS
    # ============================================
    whale_blocks: List[Dict]         # Whale order blocks (high volume zones)
    liquidity_zones: List[Dict]      # Liquidity pools
    liquidity_sweeps: List[Dict]     # Detected liquidity sweeps
    order_blocks: List[Dict]         # Standard order blocks
    fair_value_gaps: List[Dict]      # FVG imbalances
    internal_liquidity: List[Dict]   # ILP pools
    breaker_blocks: List[Dict]       # Breaker blocks (failed OBs)
    mitigation_blocks: List[Dict]    # Mitigated order blocks
    sibi_ssib_zones: List[Dict]      # Sell-side/Buy-side imbalance zones
    
    # ============================================
    # ADDITIONAL ANALYSIS COMPONENTS
    # ============================================
    fibonacci_data: Dict             # Fibonacci retracement/extension levels
    luxalgo_sr: Dict                 # LuxAlgo support/resistance
    luxalgo_ict: Dict                # LuxAlgo ICT analysis
    luxalgo_combined: Dict           # Combined LuxAlgo analysis
    
    # ============================================
    # MARKET STRUCTURE ANALYSIS
    # ============================================
    bias: MarketBias                 # BULLISH/BEARISH/NEUTRAL/RANGING
    structure_broken: bool           # Whether BOS occurred
    displacement_detected: bool      # Fast price movement detected
    mtf_confluence: int              # Multi-timeframe confluence count (0-3)
    htf_bias: str                    # Higher timeframe bias
    mtf_structure: str               # MTF structure status
    mtf_consensus_data: Dict         # MTF consensus breakdown
    
    # ============================================
    # ENTRY ZONE DETAILS (PR #8)
    # ============================================
    entry_zone: Dict                 # Entry zone details (high/low/type)
    entry_status: str                # "VALID_WAIT"/"VALID_NEAR"/"INVALID"
    distance_penalty: bool           # Confidence reduced due to distance
    
    # ============================================
    # TIMEFRAME HIERARCHY (PR #4)
    # ============================================
    timeframe_hierarchy: Dict        # TF roles (Structure/Confirmation/Entry)
    
    # ============================================
    # EXPLANATIONS & WARNINGS
    # ============================================
    reasoning: str                   # Human-readable explanation
    warnings: List[str]              # Caveats and risk warnings
    zone_explanations: Dict[str, List[str]]  # Zone-specific explanations
```

---

### Field Details

#### Core Fields

**timestamp**
- **Type:** `datetime` object
- **Example:** `datetime(2026, 1, 17, 14, 30, 15, tzinfo=timezone.utc)`
- **Purpose:** Exact signal generation time (UTC)
- **Used in:** Deduplication, logging, time-based analysis

**symbol**
- **Type:** `str`
- **Example:** `"BTCUSDT"`
- **Purpose:** Trading pair identifier
- **Validation:** Must be in `SYMBOLS` dictionary

**timeframe**
- **Type:** `str`
- **Example:** `"1h"`, `"2h"`, `"4h"`, `"1d"`
- **Purpose:** Primary analysis timeframe
- **Used in:** MTF analysis, scheduler job routing

---

#### Signal Classification

**signal_type**
- **Type:** `SignalType` enum
- **Values:**
  - `SignalType.BUY` - Standard long signal
  - `SignalType.SELL` - Standard short signal
  - `SignalType.HOLD` - No trade (informational only)
  - `SignalType.STRONG_BUY` - High-conviction long
  - `SignalType.STRONG_SELL` - High-conviction short
- **Example:** `SignalType.BUY`
- **Used in:** Signal filtering, Telegram formatting

**signal_strength**
- **Type:** `SignalStrength` enum (1-5)
- **Values:**
  - `SignalStrength.WEAK = 1` (confidence 40-54%)
  - `SignalStrength.MODERATE = 2` (confidence 55-64%)
  - `SignalStrength.STRONG = 3` (confidence 65-74%)
  - `SignalStrength.VERY_STRONG = 4` (confidence 75-84%)
  - `SignalStrength.EXTREME = 5` (confidence 85-100%)
- **Purpose:** Visual signal quality indicator

**confidence**
- **Type:** `float`
- **Range:** `0.0` to `100.0`
- **Example:** `72.5`
- **Calculation:** Weighted sum of ICT pattern detections
- **Thresholds:**
  - `≥60%` - Send to Telegram
  - `≥65%` - Log to trading journal
  - `≥75%` - Very strong signal
  - `≥85%` - Extreme confidence

---

#### Price Levels

**entry_price**
- **Type:** `float`
- **Example:** `50000.0` (for BTCUSDT)
- **Calculation:** Center of entry zone (ICT-compliant)
- **Used in:** Position opening, Telegram display

**sl_price**
- **Type:** `float`
- **Example:** `49500.0`
- **Calculation:**
  - LONG: Below recent swing low / order block low
  - SHORT: Above recent swing high / order block high
- **Safety:** Always beyond entry zone

**tp_prices**
- **Type:** `List[float]` (exactly 3 targets)
- **Example:** `[51000.0, 51500.0, 52500.0]`
- **Calculation:** Structure-aware targets (PR #8)
  - TP1: 1.0-1.5 RR (conservative)
  - TP2: 2.0-2.5 RR (moderate)
  - TP3: 3.0-4.0 RR (ambitious)
- **Used in:** Partial close recommendations, checkpoint monitoring

**risk_reward_ratio**
- **Type:** `float`
- **Example:** `3.25`
- **Calculation:** `(TP3 - entry) / (entry - SL)`
- **Minimum:** `1.0` (enforced by signal generation)

---

#### ICT Pattern Components

**whale_blocks**
- **Type:** `List[Dict]`
- **Structure:**
  ```python
  {
      'price': 49800.0,
      'volume': 1250000,
      'type': 'BULLISH',
      'strength': 'HIGH',
      'timeframe': '4h',
      'timestamp': '2026-01-17T10:00:00'
  }
  ```
- **Detection:** ict_whale_detector.py
- **Purpose:** High-volume institutional zones

**liquidity_zones**
- **Type:** `List[Dict]`
- **Structure:**
  ```python
  {
      'price': 50200.0,
      'type': 'SELL_SIDE',  # or 'BUY_SIDE'
      'strength': 0.85,
      'volume': 850000,
      'swept': False
  }
  ```
- **Detection:** liquidity_map.py
- **Purpose:** Identify stop-loss clusters

**order_blocks**
- **Type:** `List[Dict]`
- **Structure:**
  ```python
  {
      'high': 50100.0,
      'low': 49900.0,
      'type': 'BULLISH',  # Last down candle before reversal
      'touched': False,
      'mitigation_level': 50000.0,
      'timeframe': '1h'
  }
  ```
- **Detection:** order_block_detector.py
- **Purpose:** Institutional re-entry zones

**fair_value_gaps**
- **Type:** `List[Dict]`
- **Structure:**
  ```python
  {
      'high': 50500.0,
      'low': 50300.0,
      'type': 'BULLISH',  # Gap up
      'filled': False,
      'fill_percentage': 0.0,
      'timeframe': '2h'
  }
  ```
- **Detection:** fvg_detector.py
- **Purpose:** Price imbalances (gaps)

**breaker_blocks**
- **Type:** `List[Dict]`
- **Structure:**
  ```python
  {
      'original_ob': {...},  # Original order block that failed
      'break_price': 50100.0,
      'new_bias': 'BEARISH',
      'timestamp': '2026-01-17T12:00:00'
  }
  ```
- **Detection:** breaker_block_detector.py
- **Purpose:** Failed order blocks (reverse polarity)

---

#### Market Analysis Fields

**bias**
- **Type:** `MarketBias` enum
- **Values:**
  - `MarketBias.BULLISH` - Uptrend
  - `MarketBias.BEARISH` - Downtrend
  - `MarketBias.NEUTRAL` - Ranging/unclear
  - `MarketBias.RANGING` - Defined range
- **Used in:** Signal filtering, Telegram display

**structure_broken**
- **Type:** `bool`
- **Purpose:** Whether Break of Structure (BOS) occurred
- **True if:** Recent high/low exceeded previous high/low

**displacement_detected**
- **Type:** `bool`
- **Purpose:** Fast price movement (candle bodies > 70% of total range)
- **Significance:** Often precedes strong moves

**mtf_confluence**
- **Type:** `int`
- **Range:** `0` to `3`
- **Meaning:**
  - `0` - No MTF agreement (low confidence)
  - `1` - 1 higher timeframe agrees
  - `2` - 2 higher timeframes agree
  - `3` - All higher timeframes agree (strongest)
- **Requirement:** Minimum 50% agreement for signals

**htf_bias**
- **Type:** `str`
- **Values:** `"BULLISH"`, `"BEARISH"`, `"NEUTRAL"`
- **Purpose:** Higher timeframe directional bias
- **Used in:** Signal filtering (must align with signal direction)

---

#### Entry Zone Details (PR #8)

**entry_zone**
- **Type:** `Dict`
- **Structure:**
  ```python
  {
      'high': 50100.0,
      'low': 49900.0,
      'type': 'ORDER_BLOCK',  # or 'FVG', 'LIQUIDITY', 'WHALE_BLOCK'
      'distance_pct': 0.5,    # Distance from current price
      'directional': True     # Below price for LONG, above for SHORT
  }
  ```
- **Purpose:** ICT-compliant entry zone (not single price)

**entry_status**
- **Type:** `str`
- **Values:**
  - `"VALID_WAIT"` - Entry zone valid, price not near yet
  - `"VALID_NEAR"` - Entry zone valid, price approaching
  - `"INVALID"` - Entry zone directionally wrong
- **Purpose:** Signal readiness indicator

---

### Serialization

**Method:** `to_dict()` (line 257)

**Example JSON:**
```json
{
  "timestamp": "2026-01-17T14:30:15+00:00",
  "symbol": "BTCUSDT",
  "timeframe": "1h",
  "signal_type": "BUY",
  "signal_strength": 3,
  "entry_price": 50000.0,
  "sl_price": 49500.0,
  "tp_prices": [51000.0, 51500.0, 52500.0],
  "confidence": 72.5,
  "risk_reward_ratio": 3.3,
  "whale_blocks_count": 2,
  "liquidity_zones_count": 3,
  "order_blocks_count": 1,
  "fvgs_count": 1,
  "bias": "BULLISH",
  "structure_broken": true,
  "displacement_detected": false,
  "mtf_confluence": 2,
  "htf_bias": "BULLISH",
  "mtf_structure": "BULLISH",
  "reasoning": "Strong bullish setup with HTF alignment...",
  "warnings": ["Price near resistance", "Volume declining"]
}
```

---

### Where Used

**Creation:**
- ict_signal_engine.py:642 - `generate_signal()` method

**Consumption:**
- bot.py:11147 - `format_standardized_signal()` (Telegram formatting)
- bot.py:11169 - `ChartGenerator.generate()` (chart annotation)
- bot.py:11185 - `record_signal()` (stats tracking)
- bot.py:11213 - `log_trade_to_journal()` (ML training data)
- position_manager.py:145 - `open_position()` (DB storage)

---

## Database Schema

### Database File

**Location:** `{BASE_PATH}/positions.db`  
**Type:** SQLite 3  
**Created by:** init_positions_db.py (line 41)  
**Current state:** ✅ EXISTS (0 records)

---

### Table 1: open_positions

**Purpose:** Track currently active trading positions

**Schema:**
```sql
CREATE TABLE open_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    
    -- Position details
    symbol TEXT NOT NULL,              -- "BTCUSDT"
    timeframe TEXT NOT NULL,           -- "1h", "2h", "4h", "1d"
    signal_type TEXT NOT NULL,         -- "BUY" or "SELL"
    entry_price REAL NOT NULL,         -- Entry price
    tp1_price REAL NOT NULL,           -- Take profit 1
    tp2_price REAL,                    -- Take profit 2 (optional)
    tp3_price REAL,                    -- Take profit 3 (optional)
    sl_price REAL NOT NULL,            -- Stop loss
    current_size REAL DEFAULT 1.0,     -- 1.0 = 100%, 0.5 = 50% after partial close
    
    -- Original signal data (JSON serialized ICTSignal)
    original_signal_json TEXT NOT NULL,
    
    -- Timestamps
    opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked_at TIMESTAMP,
    
    -- Checkpoint tracking (0 = not triggered, 1 = triggered)
    checkpoint_25_triggered INTEGER DEFAULT 0,
    checkpoint_50_triggered INTEGER DEFAULT 0,
    checkpoint_75_triggered INTEGER DEFAULT 0,
    checkpoint_85_triggered INTEGER DEFAULT 0,
    
    -- Status
    status TEXT DEFAULT 'OPEN',        -- 'OPEN', 'PARTIAL', 'CLOSED'
    
    -- Metadata
    source TEXT,                       -- 'AUTO', 'MANUAL'
    notes TEXT
);
```

**Field Details:**

- **id:** Auto-incrementing unique identifier
- **symbol:** Must match `SYMBOLS` dictionary keys
- **signal_type:** `"BUY"` or `"SELL"` (stored as string)
- **current_size:** Tracks partial closes (1.0 = full size, 0.5 = half closed)
- **original_signal_json:** Serialized `ICTSignal` object (complete signal data)
- **checkpoint_X_triggered:** Boolean flags (0/1) for each checkpoint
- **status:**
  - `'OPEN'` - Active, full size
  - `'PARTIAL'` - Partially closed
  - `'CLOSED'` - Fully closed (moved to position_history)

**Indexes:**
```sql
CREATE INDEX idx_open_positions_status ON open_positions(status);
CREATE INDEX idx_open_positions_symbol ON open_positions(symbol);
```

**Current state:** ❌ 0 records (broken position tracking)

**Example Row:**
```sql
INSERT INTO open_positions VALUES (
    1,                          -- id
    'BTCUSDT',                  -- symbol
    '1h',                       -- timeframe
    'BUY',                      -- signal_type
    50000.0,                    -- entry_price
    51000.0,                    -- tp1_price
    51500.0,                    -- tp2_price
    52500.0,                    -- tp3_price
    49500.0,                    -- sl_price
    1.0,                        -- current_size
    '{"timestamp": "...", ...}',-- original_signal_json
    '2026-01-17 14:30:15',      -- opened_at
    NULL,                       -- last_checked_at
    0, 0, 0, 0,                 -- checkpoints (all false)
    'OPEN',                     -- status
    'AUTO',                     -- source
    NULL                        -- notes
);
```

---

### Table 2: checkpoint_alerts

**Purpose:** Log trade re-analysis results at each checkpoint

**Schema:**
```sql
CREATE TABLE checkpoint_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER NOT NULL,
    checkpoint_level TEXT NOT NULL,     -- '25%', '50%', '75%', '85%'
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    trigger_price REAL NOT NULL,
    
    -- Re-analysis results
    original_confidence REAL,           -- Signal's original confidence
    current_confidence REAL,            -- Re-calculated confidence
    confidence_delta REAL,              -- Change in confidence
    htf_bias_changed INTEGER DEFAULT 0, -- 0/1 boolean
    structure_broken INTEGER DEFAULT 0, -- 0/1 boolean
    valid_components_count INTEGER,     -- # of still-valid ICT patterns
    current_rr_ratio REAL,              -- Current risk/reward
    
    -- Recommendation
    recommendation TEXT NOT NULL,       -- 'HOLD', 'PARTIAL_CLOSE', 'CLOSE_NOW', 'MOVE_SL'
    reasoning TEXT,                     -- Human-readable explanation
    warnings TEXT,                      -- Risk warnings
    
    -- Action taken
    action_taken TEXT DEFAULT 'ALERTED',-- 'NONE', 'ALERTED', 'AUTO_CLOSED', 'PARTIAL_CLOSED'
    
    FOREIGN KEY (position_id) REFERENCES open_positions(id)
);
```

**Field Details:**

- **checkpoint_level:** `"25%"`, `"50%"`, `"75%"`, `"85%"`
- **trigger_price:** Price when checkpoint was reached
- **confidence_delta:** Positive = improving, Negative = deteriorating
- **recommendation:**
  - `'HOLD'` - Trade still valid, continue
  - `'PARTIAL_CLOSE'` - Take partial profits
  - `'CLOSE_NOW'` - Exit immediately
  - `'MOVE_SL'` - Move SL to breakeven
- **action_taken:** What bot did after alert

**Indexes:**
```sql
CREATE INDEX idx_checkpoint_alerts_position 
    ON checkpoint_alerts(position_id);
```

**Current state:** ❌ 0 records (depends on open_positions)

**Example Row:**
```sql
INSERT INTO checkpoint_alerts VALUES (
    1,                          -- id
    1,                          -- position_id
    '50%',                      -- checkpoint_level
    '2026-01-17 15:00:00',      -- triggered_at
    50500.0,                    -- trigger_price
    72.5,                       -- original_confidence
    68.0,                       -- current_confidence
    -4.5,                       -- confidence_delta
    0,                          -- htf_bias_changed
    0,                          -- structure_broken
    8,                          -- valid_components_count
    2.5,                        -- current_rr_ratio
    'HOLD',                     -- recommendation
    'Confidence slightly lower but HTF bias intact',
    'Volume decreasing',        -- warnings
    'ALERTED'                   -- action_taken
);
```

---

### Table 3: position_history

**Purpose:** Archive closed positions with P&L and statistics

**Schema:**
```sql
CREATE TABLE position_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    position_id INTEGER NOT NULL,
    
    -- Position summary
    symbol TEXT NOT NULL,
    timeframe TEXT NOT NULL,
    signal_type TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,
    
    -- P&L
    profit_loss_percent REAL,          -- e.g., 2.5 for +2.5%
    profit_loss_usd REAL,              -- If position size known
    
    -- Outcome
    outcome TEXT,                      -- 'TP1', 'TP2', 'TP3', 'SL', 'MANUAL_CLOSE', 'EARLY_EXIT'
    
    -- Timestamps
    opened_at TIMESTAMP,
    closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    duration_hours REAL,               -- Time in position
    
    -- Stats
    checkpoints_triggered INTEGER DEFAULT 0,
    recommendations_received INTEGER DEFAULT 0,
    
    FOREIGN KEY (position_id) REFERENCES open_positions(id)
);
```

**Field Details:**

- **profit_loss_percent:** `(exit_price - entry_price) / entry_price * 100`
- **outcome:**
  - `'TP1'`, `'TP2'`, `'TP3'` - Hit take profit target
  - `'SL'` - Stop loss hit
  - `'MANUAL_CLOSE'` - User closed manually
  - `'EARLY_EXIT'` - Closed before TP/SL
- **duration_hours:** `(closed_at - opened_at)` in hours

**Indexes:**
```sql
CREATE INDEX idx_position_history_closed_at 
    ON position_history(closed_at DESC);
```

**Current state:** ❌ 0 records

**Example Row:**
```sql
INSERT INTO position_history VALUES (
    1,                          -- id
    1,                          -- position_id
    'BTCUSDT',                  -- symbol
    '1h',                       -- timeframe
    'BUY',                      -- signal_type
    50000.0,                    -- entry_price
    51500.0,                    -- exit_price
    3.0,                        -- profit_loss_percent (+3%)
    NULL,                       -- profit_loss_usd
    'TP2',                      -- outcome
    '2026-01-17 14:30:15',      -- opened_at
    '2026-01-17 18:45:30',      -- closed_at
    4.25,                       -- duration_hours
    2,                          -- checkpoints_triggered (25%, 50%)
    2                           -- recommendations_received
);
```

---

## JSON Files

### trading_journal.json

**Location:** `{BASE_PATH}/trading_journal.json`  
**Current state:** ❌ NOT FOUND  
**Purpose:** ML training data - signals and outcomes

**Complete Format:**
```json
{
  "trades": [
    {
      "id": "trade_001",
      "timestamp": "2026-01-17T14:30:15Z",
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "signal_type": "BUY",
      
      "entry_price": 50000.0,
      "tp_prices": [51000.0, 51500.0, 52500.0],
      "sl_price": 49500.0,
      "confidence": 72.5,
      "risk_reward_ratio": 3.3,
      
      "ict_analysis": {
        "bias": "BULLISH",
        "htf_bias": "BULLISH",
        "structure_broken": true,
        "displacement_detected": false,
        "mtf_confluence": 2,
        "mtf_consensus_data": {
          "4h": "BULLISH",
          "1d": "BULLISH",
          "1w": "NEUTRAL"
        },
        
        "patterns_detected": {
          "order_blocks": 1,
          "fair_value_gaps": 1,
          "liquidity_zones": 3,
          "whale_blocks": 2,
          "breaker_blocks": 0
        },
        
        "entry_zone": {
          "high": 50100.0,
          "low": 49900.0,
          "type": "ORDER_BLOCK"
        }
      },
      
      "outcome": null,
      "exit_price": null,
      "profit_loss_percent": null,
      "closed_at": null
    }
  ],
  
  "metadata": {
    "total_trades": 156,
    "wins": 98,
    "losses": 58,
    "win_rate": 62.82,
    "avg_confidence": 71.5,
    "last_updated": "2026-01-17T21:00:00Z",
    "version": "2.0"
  }
}
```

**Written by:** bot.py:11213 - `log_trade_to_journal()` function  
**Threshold:** Only signals with `confidence >= 65%` ⚠️ (causes data loss)

**Read by:**
- ml_engine.py - Model training (learn from outcomes)
- Backtest system - Historical analysis

**Issue:** Missing 60-64% confidence signals (see [CONFIGURATION_REFERENCE.md](CONFIGURATION_REFERENCE.md#critical-signal-threshold-inconsistency))

---

### signal_cache.json

**Location:** `{BASE_PATH}/signal_cache.json` (alternative name)  
**Current state:** ❌ NOT FOUND (functionality exists in sent_signals_cache.json)  
**Purpose:** Deduplication cache (alternative implementation)

**Note:** Functionality merged into `sent_signals_cache.json`

---

### sent_signals_cache.json

**Location:** `{BASE_PATH}/sent_signals_cache.json`  
**Current state:** ✅ EXISTS  
**Purpose:** Persistent deduplication cache across bot restarts

**Format:**
```json
{
  "BTCUSDT_BUY_4h": {
    "timestamp": "2026-01-14T16:37:43.121268",
    "last_checked": "2026-01-14T16:37:45.123456",
    "entry_price": 50000.0,
    "confidence": 85
  },
  "ETHUSDT_SELL_1h": {
    "timestamp": "2026-01-14T16:41:40.666362",
    "entry_price": 3500.0,
    "confidence": 90
  },
  "XRPUSDT_BUY_2h": {
    "timestamp": "2026-01-15T10:00:00.000000",
    "entry_price": 0.65,
    "confidence": 70
  }
}
```

**Key Structure:** `"{SYMBOL}_{SIGNAL_TYPE}_{TIMEFRAME}"`

**Field Details:**
- **timestamp:** When signal was first sent (ISO 8601 format)
- **last_checked:** Last time this cache entry was validated (optional)
- **entry_price:** Entry price of cached signal
- **confidence:** Signal confidence score

**Cleanup:**
- Old entries (>24h) automatically removed on next cache access
- Invalid entries (missing fields) removed during validation

**Used in:**
- signal_cache.py - `is_signal_duplicate()` function
- bot.py:11070 - Persistent deduplication check

**Related:** In-memory `SENT_SIGNALS_CACHE` dictionary (bot.py:389)

---

### news_cache.json

**Location:** `{BASE_PATH}/news_cache.json`  
**Current state:** ✅ EXISTS  
**Purpose:** Cache news sentiment data to reduce API calls

**Format:**
```json
{
  "BTC": {
    "sentiment": "POSITIVE",
    "sentiment_score": 0.75,
    "articles_analyzed": 12,
    "top_headlines": [
      "Bitcoin surges past $50k on institutional demand",
      "Major bank announces BTC custody services"
    ],
    "sources": ["CoinDesk", "Bloomberg", "Reuters"],
    "last_updated": "2026-01-17T20:00:00Z",
    "ttl_seconds": 7200
  },
  "ETH": {
    "sentiment": "NEUTRAL",
    "sentiment_score": 0.52,
    "articles_analyzed": 8,
    "top_headlines": [
      "Ethereum network upgrade scheduled for Q2"
    ],
    "sources": ["CoinTelegraph", "Decrypt"],
    "last_updated": "2026-01-17T19:30:00Z",
    "ttl_seconds": 7200
  }
}
```

**Field Details:**
- **sentiment:** `"POSITIVE"`, `"NEUTRAL"`, `"NEGATIVE"`
- **sentiment_score:** 0.0-1.0 (0 = very bearish, 1 = very bullish)
- **ttl_seconds:** Time-to-live before refresh (default: 7200 = 2 hours)

**Used in:**
- utils/news_cache.py - News fetching and caching
- Fundamental analysis integration (if enabled)

**Refresh:** Every 2 hours or on manual /news command

---

### bot_stats.json

**Location:** `{BASE_PATH}/bot_stats.json`  
**Current state:** ❌ NOT FOUND  
**Purpose:** Win-rate tracking and signal performance

**Expected Format:**
```json
{
  "signals": [
    {
      "id": "sig_20260117_001",
      "symbol": "BTCUSDT",
      "timeframe": "1h",
      "signal_type": "BUY",
      "confidence": 72.5,
      "entry_price": 50000.0,
      "tp_price": 51500.0,
      "sl_price": 49500.0,
      "timestamp": "2026-01-17T14:30:15Z",
      "outcome": "WIN",
      "exit_price": 51500.0,
      "profit_percent": 3.0,
      "duration_hours": 4.25
    }
  ],
  
  "statistics": {
    "total_signals": 156,
    "wins": 98,
    "losses": 58,
    "win_rate": 62.82,
    "avg_profit": 3.2,
    "avg_loss": -1.8,
    "profit_factor": 1.78,
    "best_timeframe": "4h",
    "best_symbol": "BTCUSDT"
  },
  
  "by_timeframe": {
    "1h": {"total": 60, "wins": 35, "win_rate": 58.33},
    "2h": {"total": 40, "wins": 26, "win_rate": 65.00},
    "4h": {"total": 36, "wins": 25, "win_rate": 69.44},
    "1d": {"total": 20, "wins": 12, "win_rate": 60.00}
  },
  
  "by_symbol": {
    "BTCUSDT": {"total": 45, "wins": 30, "win_rate": 66.67},
    "ETHUSDT": {"total": 38, "wins": 22, "win_rate": 57.89},
    "XRPUSDT": {"total": 25, "wins": 16, "win_rate": 64.00}
  },
  
  "metadata": {
    "first_signal": "2026-01-01T00:00:00Z",
    "last_signal": "2026-01-17T14:30:15Z",
    "bot_version": "2.0.0",
    "last_updated": "2026-01-17T21:00:00Z"
  }
}
```

**Written by:** bot.py:11185 - `record_signal()` function

**Read by:**
- /stats command - Display statistics to users
- Daily/weekly reports - Performance summaries

**Issue:** File never created (initialization missing)

---

### daily_reports.json

**Location:** `{BASE_PATH}/daily_reports.json`  
**Current state:** ✅ EXISTS  
**Purpose:** Store generated daily/weekly/monthly reports

**Format:**
```json
{
  "daily_reports": [
    {
      "date": "2026-01-17",
      "signals_generated": 18,
      "signals_sent": 16,
      "high_confidence_signals": 8,
      "positions_opened": 0,
      "positions_closed": 0,
      "api_calls": 2456,
      "errors": 0,
      "cache_hit_rate": 0.84,
      "generated_at": "2026-01-17T23:00:00Z"
    }
  ],
  "weekly_reports": [],
  "monthly_reports": []
}
```

**Written by:** admin/admin_module.py - Report generation functions

**Read by:**
- /report command - Display latest reports
- Health monitoring system

---

## Data Flow Diagrams

### Complete Signal Flow

```
┌─────────────────────────────────────────────────────────────┐
│ 1. SIGNAL GENERATION (ict_signal_engine.py)                │
│    • Fetch market data (Binance API)                       │
│    • Detect ICT patterns (15+ detectors)                   │
│    • Calculate confidence (weighted scoring)               │
│    • Create ICTSignal object                               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. CONFIDENCE FILTERING (bot.py:11100+)                    │
│    • Check: confidence >= 60%                              │
│    • If FAIL: Discard signal (too weak)                    │
│    • If PASS: Continue to deduplication                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. DEDUPLICATION CHECK (signal_cache.py)                   │
│    • Check sent_signals_cache.json                         │
│    • Compare: symbol, type, timeframe, price, confidence   │
│    • Use proximity thresholds (±0.5%, ±5%, 2h window)      │
│    • If DUPLICATE: Skip signal                             │
│    • If UNIQUE: Continue to Telegram delivery              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. TELEGRAM DELIVERY (bot.py:11154+)                       │
│    ✅ Send message to user (all confidence >= 60%)         │
│    • Format: format_standardized_signal()                  │
│    • Include: price levels, confidence, reasoning          │
│    • Send chart (if CHART_VISUALIZATION_AVAILABLE)         │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. UPDATE CACHE (signal_cache.py)                          │
│    • Add to sent_signals_cache.json                        │
│    • Timestamp signal                                      │
│    • Prevent duplicates for 24 hours                       │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. STATS RECORDING (bot.py:11185)                          │
│    • Call record_signal()                                  │
│    • ❌ Write to bot_stats.json (FILE NOT FOUND)           │
│    • Track signal performance                              │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. JOURNAL LOGGING (bot.py:11199) ⚠️ THRESHOLD ISSUE      │
│    • Check: confidence >= 65% (INCONSISTENT!)              │
│    • If PASS: log_trade_to_journal()                       │
│    • ❌ Write to trading_journal.json (FILE NOT FOUND)     │
│    • PURPOSE: ML training data                             │
│    • ISSUE: 60-64% signals NOT LOGGED (50% data loss)      │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│ 8. POSITION TRACKING (bot.py:11482) ❌ BROKEN              │
│    • Check: AUTO_POSITION_TRACKING_ENABLED == True         │
│    • Call: position_manager.open_position()                │
│    • ❌ NEVER EXECUTES (unreachable code)                  │
│    • Should: INSERT into positions.db                      │
│    • Result: 0 DB records despite signals sent             │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (if position tracking worked...)
┌─────────────────────────────────────────────────────────────┐
│ 9. REAL-TIME MONITORING (real_time_monitor.py)             │
│    • Every 60 seconds: check open positions                │
│    • Compare current price vs entry/SL/TP                  │
│    • Detect checkpoints: 25%, 50%, 75%, 85%                │
│    • ❌ NEVER RUNS (no positions to monitor)               │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (if checkpoints detected...)
┌─────────────────────────────────────────────────────────────┐
│ 10. CHECKPOINT RE-ANALYSIS (trade_reanalysis_engine.py)    │
│     • Re-run ICT analysis at checkpoint                    │
│     • Compare: original vs current confidence              │
│     • Recommendation: HOLD, PARTIAL_CLOSE, CLOSE_NOW       │
│     • Alert sent to Telegram                               │
│     • ❌ NEVER RUNS (depends on step 9)                    │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼ (if TP/SL hit...)
┌─────────────────────────────────────────────────────────────┐
│ 11. POSITION CLOSURE (position_manager.py)                 │
│     • Calculate P&L                                        │
│     • INSERT into position_history                         │
│     • Send final outcome alert                             │
│     • ❌ NEVER RUNS (no positions to close)                │
└─────────────────────────────────────────────────────────────┘
```

**Summary:**
- ✅ Steps 1-5: **WORKING** (signal generation & delivery)
- ⚠️ Steps 6-7: **PARTIAL** (files not found, threshold issue)
- ❌ Steps 8-11: **BROKEN** (position tracking never happens)

---

### Data Loss Points

```
100 signals generated
    │
    ├─ 40% filtered (confidence < 60%)
    │  └─ ❌ Discarded (expected behavior)
    │
    └─ 60% pass threshold (confidence >= 60%)
       │
       ├─ 10% deduplicated (already sent recently)
       │  └─ ❌ Discarded (expected behavior)
       │
       └─ 50% sent to Telegram ✅
          │
          ├─ 25% in 60-64% range
          │  ├─ ✅ User receives signal
          │  ├─ ✅ Cached in sent_signals_cache.json
          │  ├─ ❌ NOT logged to bot_stats.json (file missing)
          │  ├─ ❌ NOT logged to trading_journal.json (fails 65% threshold)
          │  └─ ❌ NOT tracked in positions.db (broken code)
          │
          └─ 25% in 65-100% range
             ├─ ✅ User receives signal
             ├─ ✅ Cached in sent_signals_cache.json
             ├─ ❌ NOT logged to bot_stats.json (file missing)
             ├─ ⚠️ NOT logged to trading_journal.json (file doesn't exist)
             └─ ❌ NOT tracked in positions.db (broken code)

RESULT: 100% of signals delivered, 0% tracked in database
```

---

## Message Formats

### Telegram Signal Message

**Generated by:** bot.py - `format_standardized_signal()` function

**Format:**
```
🔔 CRYPTO SIGNAL (AUTO)

📊 BTCUSDT | 1h
🎯 BUY SIGNAL
💪 Confidence: 72.5% (STRONG)

━━━━━━━━━━━━━━━━━━━
💰 ENTRY ZONE:
   $49,900 - $50,100
   Current: $50,000

🛡️ STOP LOSS:
   $49,500 (-1.0%)

🎯 TAKE PROFIT:
   TP1: $51,000 (+2.0%)
   TP2: $51,500 (+3.0%)
   TP3: $52,500 (+5.0%)

📈 RISK/REWARD: 1:3.3

━━━━━━━━━━━━━━━━━━━
📋 ICT ANALYSIS:
   • Bias: BULLISH
   • HTF Bias: BULLISH
   • Structure: BROKEN ✅
   • MTF Confluence: 2/3

🔍 PATTERNS DETECTED:
   • Order Blocks: 1
   • FVG: 1
   • Liquidity Zones: 3
   • Whale Blocks: 2

💡 REASONING:
Strong bullish setup with HTF alignment.
Entry zone at previous order block.
Price above key liquidity zones.

⚠️ WARNINGS:
• Price near resistance
• Volume declining

━━━━━━━━━━━━━━━━━━━
⏰ Signal Time: 14:30 UTC
```

---

### Checkpoint Alert Message

**Generated by:** bot.py - Checkpoint monitoring system

**Format:**
```
📊 CHECKPOINT ALERT - 50%

Position #12 | BTCUSDT 1h BUY
Entry: $50,000 → Current: $50,500
Profit: +1.0% (50% to TP1)

━━━━━━━━━━━━━━━━━━━
🔄 RE-ANALYSIS:

Original: 72.5% confidence
Current: 68.0% confidence
Change: -4.5% ⚠️

Market Structure:
• HTF Bias: BULLISH (unchanged)
• Structure: INTACT
• Valid Patterns: 8/10

━━━━━━━━━━━━━━━━━━━
💡 RECOMMENDATION: HOLD

REASONING:
Confidence slightly lower but HTF bias
remains bullish. Structure intact.
Recommend continuing to TP1.

⚠️ WARNINGS:
• Volume decreasing
• Approaching resistance

━━━━━━━━━━━━━━━━━━━
⏰ Alert Time: 15:00 UTC
```

---

## Cache Structures

### LRU Cache (bot.py:443-587)

**Purpose:** In-memory caching with automatic eviction

**Structure:**
```python
class LRUCacheDict:
    """LRU Cache with TTL"""
    
    def __init__(self, max_size=100, ttl_seconds=300):
        self.max_size = max_size          # Max items
        self.ttl_seconds = ttl_seconds    # Time to live
        self._cache = OrderedDict()       # Ordered storage
        self._lock = Lock()               # Thread safety
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
```

**Features:**
- **LRU Eviction:** Least recently used item removed when full
- **TTL Expiration:** Items expire after ttl_seconds
- **Thread-safe:** Multiple coroutines can access safely
- **Dict-compatible:** Can use as regular Python dictionary

**Usage:**
```python
# Get from cache (raises KeyError if missing/expired)
result = CACHE['market']['BTCUSDT_1h_klines']

# Set in cache
CACHE['market']['BTCUSDT_1h_klines'] = klines_data

# Check existence
if 'BTCUSDT_1h_klines' in CACHE['market']:
    ...

# Get statistics
stats = CACHE['market'].get_stats()
# Returns: {'size': 45, 'hits': 230, 'misses': 45, 'hit_rate': 0.84}
```

---

### Cache Instances

**Backtest Cache:**
```python
CACHE['backtest'] = LRUCacheDict(max_size=50, ttl_seconds=300)
```
- **Stores:** Backtest results for symbol/timeframe/parameters
- **Key format:** `"BTCUSDT_1h_params_hash"`
- **Purpose:** Avoid re-running same backtest

**Market Data Cache:**
```python
CACHE['market'] = LRUCacheDict(max_size=100, ttl_seconds=180)
```
- **Stores:** Klines, price data, order book
- **Key format:** `"BTCUSDT_1h_klines"`, `"ETHUSDT_price"`
- **Purpose:** Reduce Binance API calls

**ML Performance Cache:**
```python
CACHE['ml_performance'] = LRUCacheDict(max_size=50, ttl_seconds=300)
```
- **Stores:** ML model predictions
- **Key format:** `"ml_pred_BTCUSDT_1h"`
- **Purpose:** Expensive model inference caching

---

## Summary

**Working Data Flows:**
- ✅ Signal generation → Telegram delivery
- ✅ Deduplication (persistent cache)
- ✅ News caching
- ✅ LRU caching (market data, backtest, ML)

**Broken Data Flows:**
- ❌ Signal → positions.db (unreachable code)
- ❌ Position → checkpoint monitoring (no positions)
- ❌ Checkpoint → re-analysis (depends on monitoring)
- ❌ Position → history (no closures)

**Data Loss Issues:**
- ❌ bot_stats.json not created (no statistics)
- ❌ trading_journal.json not created (no ML data)
- ⚠️ 60-64% signals not journaled (threshold inconsistency)

**Files Status:**
- ✅ sent_signals_cache.json (working)
- ✅ news_cache.json (working)
- ✅ daily_reports.json (working)
- ✅ positions.db (exists but empty)
- ❌ bot_stats.json (missing)
- ❌ trading_journal.json (missing)

---

**Documentation Version:** 1.0  
**Last Updated:** January 17, 2026  
**Word Count:** ~5,200 words
