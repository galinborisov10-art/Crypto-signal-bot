# System Architecture Documentation
## Crypto Signal Bot - Complete System Overview

**Version:** 2.0.0  
**Analysis Date:** January 17, 2026  
**Total Python Files:** 142  
**Core Bot Size:** 18,507 lines (bot.py), 802 KB  
**Repository:** galinborisov10-art/Crypto-signal-bot

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Component Breakdown](#component-breakdown)
3. [Data Flow Diagrams](#data-flow-diagrams)
4. [Entry Points & Initialization](#entry-points--initialization)
5. [Async Tasks & Background Jobs](#async-tasks--background-jobs)
6. [External Dependencies](#external-dependencies)
7. [File Structure](#file-structure)

---

## System Overview

This is a production cryptocurrency trading signal bot that generates ICT (Inner Circle Trader) methodology-based trading signals for BTC, ETH, XRP, SOL, BNB, and ADA. The system:

- **Generates 16 signals per day** (average) across multiple timeframes (1h, 2h, 4h, 1d)
- **Uses 15+ ICT patterns** for confluence-based signal generation
- **Confidence scoring:** 0-100% based on weighted pattern analysis
- **Automatic position tracking** with checkpoint monitoring at 25%, 50%, 75%, 85% profit targets
- **Real-time alerts** via Telegram for 80% TP achievement and final outcomes
- **Multi-timeframe analysis** with HTF (Higher Timeframe) bias confirmation
- **ML-enhanced confidence** scoring with ±20% adjustments
- **Comprehensive monitoring** with health checks, daily reports, and diagnostics

### Current System Status (As of Analysis)

✅ **Working Components:**
- Signal generation (16/day average)
- Telegram integration (messages delivered successfully)
- ICT pattern detection (all 15+ patterns operational)
- Chart generation (if enabled)
- Daily/weekly/monthly reports
- Health monitoring system

❌ **Broken Components:**
- Position tracking (0 DB records despite signals being sent)
- Checkpoint alerts (never trigger - depends on position tracking)
- Trading journal logging (inconsistent threshold causes data loss)

---

## Component Breakdown

### Core Engine (3 files, ~24,000 lines)

#### **bot.py** (18,507 lines)
- **Purpose:** Main orchestrator - Telegram bot, scheduler, command handlers, signal routing
- **Key Responsibilities:**
  - Telegram bot initialization and command handling (70+ commands)
  - APScheduler setup for automated jobs (1h/2h/4h/1d signals, monitoring, reports)
  - Position management coordination
  - Signal deduplication and caching
  - User interaction and notifications
  - Health monitoring coordination
- **Critical Functions:**
  - `main()` (line 17253): Entry point
  - `auto_signal_job()` (line 11258): Scheduled signal generation
  - `open_position()` (line 11482): Position tracking (currently broken)
  - `monitor_positions_job()` (line 11512+): Checkpoint monitoring
  
#### **ict_signal_engine.py** (5,563 lines)
- **Purpose:** ICT trading strategy implementation and signal generation
- **Key Responsibilities:**
  - Generate trading signals using ICT methodology
  - Detect 15+ ICT patterns (OB, FVG, liquidity, structure breaks, etc.)
  - Calculate confidence scores (0-100%)
  - Determine entry zones, stop loss, and take profit levels
  - Multi-timeframe confluence analysis
  - ML confidence optimization
- **Critical Functions:**
  - `generate_signal()` (line 642): Main signal generation entry point
  - `_detect_ict_components()` (line 1592): Pattern detection hub
  - `_calculate_signal_confidence()` (line 2983): Confidence scoring
  - `_calculate_ict_compliant_entry_zone()` (line 2293): Entry determination
  - `_calculate_sl_price()` (line 2796): Stop loss calculation
  - `_calculate_tp_with_min_rr()` (line 2696): Take profit calculation

#### **position_manager.py** (718 lines)
- **Purpose:** Position lifecycle management with database operations
- **Key Responsibilities:**
  - Open/close trading positions
  - Track checkpoint progress (25%, 50%, 75%, 85%)
  - Calculate P&L
  - Maintain position history
  - Support partial closes
- **Critical Functions:**
  - `open_position()`: Create new position in DB
  - `get_open_positions()`: Retrieve active positions
  - `update_checkpoint_triggered()`: Mark checkpoints
  - `close_position()`: Close position with outcome
- **Database:** positions.db (SQLite)
  - `open_positions` table (currently 0 records ❌)
  - `checkpoint_alerts` table (currently 0 records ❌)
  - `position_history` table (currently 0 records ❌)

---

### Signal Generation & Analysis (12 files, ~7,000 lines)

#### Pattern Detectors

1. **order_block_detector.py** (728 lines)
   - Detects bullish/bearish order blocks (last candle before structure break)
   - Identifies mitigation blocks (partially filled order blocks)
   - Provides confidence weighting: 15% of total signal confidence

2. **fvg_detector.py** (604 lines)
   - Fair Value Gap detection (price imbalances)
   - Bullish FVG: Gap between candle high and next candle low
   - Bearish FVG: Gap between candle low and next candle high
   - Confidence weighting: 10%

3. **liquidity_map.py** (318 lines)
   - Maps liquidity pools and zones
   - Detects liquidity sweeps (stop hunts)
   - Confidence weighting: 20% for zones

4. **ict_whale_detector.py** (350 lines)
   - Detects institutional order blocks
   - High-volume whale accumulation/distribution zones
   - Confidence weighting: 25% (highest individual weight)

5. **breaker_block_detector.py** (181 lines)
   - Identifies breaker blocks (failed order blocks that break and reverse)
   - Confidence weighting: 5%

6. **sibi_ssib_detector.py** (210 lines)
   - Sell Side Imbalance Buy Side (SIBI) detection
   - Buy Side Imbalance Sell Side (BSIB) detection
   - Support/resistance imbalances
   - Confidence weighting: 5%

7. **ilp_detector.py** (521 lines)
   - Internal Liquidity Pool detection
   - Intra-structure liquidity zones
   - Used for entry refinement

8. **fibonacci_analyzer.py** (363 lines)
   - Calculates Fibonacci retracement levels
   - Determines structure-aware TP targets
   - Supports TP1/TP2/TP3 placement at Fib levels

9. **zone_explainer.py** (741 lines)
   - Generates human-readable explanations for detected zones
   - Converts technical data into Telegram-friendly messages
   - Provides reasoning for signal components

#### Multi-Timeframe Analysis

10. **mtf_analyzer.py** (814 lines)
    - Multi-timeframe data fetching and analysis
    - HTF (Higher Timeframe) bias determination
    - MTF confluence calculation (requires 50%+ alignment)
    - Timeframe hierarchy validation (PR #4)

11. **trade_reanalysis_engine.py** (754 lines)
    - Re-analyzes active trades at checkpoints
    - Compares original signal vs current market state
    - Generates recommendations (HOLD, PARTIAL_CLOSE, CLOSE_NOW, MOVE_SL)
    - Used by checkpoint monitoring system

---

### LuxAlgo Integration (4 files, ~3,000 lines)

12. **luxalgo_sr_mtf.py** (604 lines)
    - Support/Resistance detection using LuxAlgo methodology
    - Multi-timeframe S/R analysis
    - Integrates with ICT patterns for confluence

13. **luxalgo_ict_analysis.py** (985 lines)
    - Unified ICT analysis with LuxAlgo enhancements
    - Combines both methodologies for stronger signals

14. **luxalgo_ict_concepts.py** (517 lines)
    - Core LuxAlgo ICT concept implementations
    - Algorithmic pattern recognition

15. **luxalgo_chart_generator.py** (523 lines)
    - Generates charts with LuxAlgo indicators
    - Visual representation of detected patterns

---

### Chart Generation & Visualization (4 files, ~1,500 lines)

16. **chart_generator.py** (847 lines)
    - Main chart generation for signals
    - Annotates ICT patterns on price charts
    - PNG output for Telegram delivery
    - Configuration: `SEND_CHARTS` flag (bot.py line ~350)

17. **chart_annotator.py** (211 lines)
    - Annotates detected patterns on charts
    - Color-codes different ICT components

18. **graph_engine.py** (475 lines)
    - Core graphing engine
    - matplotlib-based chart rendering

19. **visualization_config.py** (67 lines)
    - Chart styling configuration
    - Color schemes, fonts, layout settings

---

### Machine Learning (3 files, ~1,800 lines)

20. **ml_engine.py** (805 lines)
    - Machine learning model training
    - Feature extraction from ICT signals
    - Model persistence and loading
    - Trains on trading journal data (confidence ≥ 65%)

21. **ml_predictor.py** (532 lines)
    - Real-time ML predictions for signal quality
    - Confidence adjustment: ±20% based on ML model
    - Feature: historical pattern success rates

22. **journal_backtest.py** (623 lines)
    - Backtests signals from trading journal
    - Calculates historical performance
    - ML training data validation

---

### Reports & Analytics (2 files, ~1,600 lines)

23. **daily_reports.py** (771 lines)
    - Daily performance summaries
    - Signal statistics (count, avg confidence, win rate)
    - Scheduled: 08:00 BG time (bot.py line 17479)

24. **system_diagnostics.py** (990 lines)
    - System health monitoring
    - Component status checks
    - Diagnostic message generation
    - Database integrity validation

---

### Telegram Integration (3 files, ~700 lines)

25. **telegram_bot.py** (203 lines)
    - Telegram bot wrapper utilities
    - Message formatting helpers

26. **telegram_formatter_bg.py** (438 lines)
    - Bulgarian language formatter
    - Localized message templates

27. **diagnostic_messages.py** (315 lines)
    - Diagnostic alert messages
    - Health check notifications

---

### Real-Time Monitoring (3 files, ~1,500 lines)

28. **real_time_monitor.py** (895 lines)
    - 24/7 position monitoring
    - Price tracking every 30 seconds
    - 80% TP alert triggering
    - WIN/LOSS final notifications
    - Uses ICT80AlertHandler for re-analysis

29. **ict_80_alert_handler.py** (258 lines)
    - Handles 80% threshold alerts
    - Re-analyzes signal at 80% profit
    - Generates recommendations based on current market state

30. **bot_watchdog.py** (215 lines)
    - Monitors bot health
    - Auto-restart on failures
    - Uptime tracking

---

### Fundamental Analysis (3 files, ~800 lines)

31. **fundamental/sentiment_analyzer.py** (~300 lines)
    - News sentiment analysis
    - Filters signals based on market sentiment
    - Used in `_check_news_sentiment_before_signal()` (ict_signal_engine.py line 5222)

32. **fundamental/btc_correlator.py** (~200 lines)
    - BTC correlation analysis for altcoins
    - Altcoin signal filtering based on BTC dominance

33. **fundamental/__init__.py**
    - Package initialization

---

### Security & Access Control (5 files, ~1,000 lines)

34. **security/auth.py** (~300 lines)
    - User authentication
    - Access level management

35. **security/rate_limiter.py** (~200 lines)
    - Rate limiting for API calls
    - Prevents abuse

36. **security/security_monitor.py** (~300 lines)
    - Security event monitoring
    - Intrusion detection

37. **security/token_manager.py** (~150 lines)
    - API token management
    - Token rotation

38. **security/__init__.py**
    - Package initialization

---

### ICT Enhancements (4 files, ~800 lines)

39. **ict_enhancement/ict_enhancer.py** (~300 lines)
    - ICT pattern enhancement utilities
    - Advanced pattern detection

40. **ict_enhancement/breaker_detector.py** (~250 lines)
    - Enhanced breaker block detection
    - Alternative to base breaker_block_detector.py

41. **ict_enhancement/hqpo_detector.py** (~200 lines)
    - High Quality Price Objective (HQPO) detection
    - Premium/discount array analysis

42. **ict_enhancement/__init__.py**
    - Package initialization

---

### Utilities (6 files, ~1,000 lines)

43. **utils/market_data_fetcher.py** (~300 lines)
    - Binance API integration
    - OHLCV data fetching
    - Rate limiting and retry logic

44. **utils/market_helper.py** (~200 lines)
    - Market data processing helpers
    - Timeframe conversions

45. **utils/fundamental_helper.py** (~150 lines)
    - Fundamental data utilities

46. **utils/news_cache.py** (~150 lines)
    - News data caching
    - Cache: `news_cache.json`

47. **utils/trade_id_generator.py** (~100 lines)
    - Generates unique trade IDs
    - Format: `BTC_1h_20260117_1234`

48. **utils/__init__.py**
    - Package initialization

---

### Configuration (3 files, ~500 lines)

49. **config/trading_config.py** (~300 lines)
    - Trading strategy configuration
    - Risk management parameters
    - Timeframe settings

50. **config/config_loader.py** (~150 lines)
    - Configuration file loading
    - Environment variable management

51. **config/__init__.py**
    - Package initialization

---

### Caching & Storage (4 files, ~600 lines)

52. **cache_manager.py** (292 lines)
    - Centralized cache management
    - LRU caches for backtest, market data, ML

53. **signal_cache.py** (211 lines)
    - Signal deduplication cache
    - Prevents duplicate signal sends

54. **signal_helpers.py** (104 lines)
    - Signal utility functions
    - Signal formatting helpers

55. **risk_management.py** (226 lines)
    - Risk calculation utilities
    - Position sizing (if implemented)

---

### Admin & Automation (4 files, ~1,200 lines)

56. **admin/admin_module.py** (~500 lines)
    - Admin command handlers
    - System control commands

57. **admin/diagnostics.py** (~400 lines)
    - Admin diagnostic tools
    - System inspection utilities

58. **auto_fixer.py** (424 lines)
    - Automatic issue detection and repair
    - Self-healing capabilities

59. **auto_updater.py** (318 lines)
    - Automatic bot updates
    - Version management

---

### Legacy & Experimental (7 files, ~3,000 lines)

60-66. **legacy_backtest/** (3 files)
    - Old backtesting implementations
    - Experimental hybrid backtest

67-73. **ict_enhancement/** (additional experimental detectors)

---

### Testing Infrastructure (50+ files, ~15,000 lines)

74-142. **test_*.py** (50+ test files)
    - Unit tests for all major components
    - Integration tests
    - Validation scripts
    - Manual testing utilities

**Key Test Files:**
- `test_imports.py`: Module import validation
- `test_pr*.py`: PR-specific test suites
- `test_signal_*.py`: Signal generation tests
- `test_ml*.py`: ML component tests
- `test_backtest*.py`: Backtesting validation

---

## Data Flow Diagrams

### Signal Generation Flow (Working ✅)

```
┌─────────────────────────────────────────────────────────────────┐
│ APScheduler Trigger (every 1h/2h/4h/1d)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ auto_signal_job(timeframe, bot_instance)                       │
│ bot.py:11258                                                    │
│                                                                  │
│ For each symbol in SYMBOLS_TO_MONITOR:                         │
│   - BTCUSDT, ETHUSDT, XRPUSDT, SOLUSDT, BNBUSDT, ADAUSDT       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Fetch Multi-Timeframe Data                                     │
│ mtf_analyzer.fetch_mtf_data()                                   │
│                                                                  │
│ Timeframes fetched:                                             │
│   - Current TF (e.g., 1h)                                       │
│   - MTF (e.g., 4h)                                              │
│   - HTF (e.g., 1d)                                              │
│   - LTF (e.g., 15m if applicable)                              │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ ict_signal_engine.generate_signal()                            │
│ ict_signal_engine.py:642                                        │
│                                                                  │
│ 12-Step Generation Pipeline:                                    │
│ 1. Validate MTF data                                            │
│ 2. Detect ICT components (15+ patterns)                        │
│ 3. Determine market bias (BULLISH/BEARISH/NEUTRAL)             │
│ 4. Check structure breaks                                       │
│ 5. Check displacement                                           │
│ 6. Analyze MTF confluence                                       │
│ 7. Calculate entry zone                                         │
│ 8. Calculate stop loss                                          │
│ 9. Calculate take profit (TP1/TP2/TP3)                         │
│ 10. Calculate confidence score (0-100%)                         │
│ 11. Apply ML optimization (±20%)                                │
│ 12. Generate ICTSignal object                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Confidence Threshold Check                                      │
│                                                                  │
│ Is confidence ≥ 60%? (inferred threshold for Telegram)         │
│   NO  → Discard signal                                          │
│   YES → Continue                                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Deduplication Check                                             │
│ signal_cache.check_duplicate()                                  │
│                                                                  │
│ Checks against SENT_SIGNALS_CACHE (bot.py:389):                │
│   - Same symbol + timeframe + direction                         │
│   - Price proximity: 0.2%-0.5% tolerance                       │
│   - Confidence similarity: 3%-5% tolerance                      │
│   - Time window: 90-120 minutes                                 │
│                                                                  │
│ If duplicate detected → Discard                                 │
│ If unique → Continue                                             │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Chart Generation (Optional)                                     │
│                                                                  │
│ If SEND_CHARTS enabled (bot.py:~350):                          │
│   chart_generator.create_chart(signal)                          │
│   - Annotate ICT patterns                                       │
│   - Generate PNG file                                            │
│                                                                  │
│ If disabled → Skip                                               │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Send to Telegram                                                │
│ bot.send_message()                                              │
│                                                                  │
│ Message includes:                                                │
│   - Symbol + Timeframe                                           │
│   - Signal type (BUY/SELL)                                      │
│   - Entry price                                                  │
│   - SL price                                                     │
│   - TP1/TP2/TP3 prices                                          │
│   - Confidence %                                                 │
│   - Risk:Reward ratio                                            │
│   - ICT components detected                                     │
│   - Chart (if enabled)                                           │
│                                                                  │
│ Sent to: OWNER_CHAT_ID (7003238836)                            │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Journal Logging (CONDITIONAL)                                   │
│ bot.py:11199                                                    │
│                                                                  │
│ If confidence ≥ 65%:                                            │
│   log_trade_to_journal(signal)                                  │
│   → Saves to trading_journal.json (NOT FOUND ❌)               │
│   → Used for ML training                                        │
│                                                                  │
│ If confidence < 65%:                                            │
│   ❌ NOT LOGGED (ISSUE: Data loss for 60-64% signals)         │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Position Tracking (BROKEN ❌)                                  │
│ bot.py:11480-11500                                              │
│                                                                  │
│ If AUTO_POSITION_TRACKING_ENABLED (line 398 = True):           │
│   If POSITION_MANAGER_AVAILABLE:                                │
│     If position_manager_global is not None:                     │
│       position_manager.open_position(signal)                    │
│       → INSERT into positions.db                                │
│                                                                  │
│ ISSUE: Function appears never called or fails silently         │
│ Evidence: 0 records in open_positions table                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Add to Real-Time Monitor (BROKEN ❌)                           │
│                                                                  │
│ real_time_monitor.add_signal()                                  │
│ → Tracks signal for 80% TP alerts                              │
│                                                                  │
│ ISSUE: Depends on position tracking working                    │
└─────────────────────────────────────────────────────────────────┘
```

**Result:** Signal successfully sent to Telegram, but position tracking and monitoring fail.

---

### Position Monitoring Flow (Broken ❌)

```
┌─────────────────────────────────────────────────────────────────┐
│ APScheduler Trigger (every 1 minute)                            │
│ bot.py:18037                                                    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ monitor_positions_job(bot)                                      │
│ bot.py:11512+                                                   │
│                                                                  │
│ If CHECKPOINT_MONITORING_ENABLED (line 401 = True):            │
│   Continue                                                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ position_manager.get_open_positions()                           │
│ position_manager.py                                             │
│                                                                  │
│ Query: SELECT * FROM open_positions WHERE status = 'OPEN'      │
│                                                                  │
│ Result: [] (empty list) ❌                                     │
│ Evidence: 0 records in database                                │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ Checkpoint Monitoring Loop                                      │
│                                                                  │
│ For each position in open_positions:                            │
│   (NEVER EXECUTES - list is empty)                             │
│                                                                  │
│   Should do:                                                     │
│   1. Fetch current price                                        │
│   2. Calculate % to TP                                          │
│   3. Check if checkpoint reached (25%, 50%, 75%, 85%)          │
│   4. If checkpoint reached and not triggered:                   │
│      - Re-analyze with trade_reanalysis_engine                  │
│      - Generate recommendation                                   │
│      - Send alert to Telegram                                    │
│      - Update checkpoint_alerts table                           │
│      - Mark checkpoint as triggered                             │
└─────────────────────────────────────────────────────────────────┘
```

**Result:** Checkpoint monitoring never triggers because no positions exist in database.

---

### Real-Time 80% Alert Flow (Broken ❌)

```
┌─────────────────────────────────────────────────────────────────┐
│ Real-Time Monitor Background Task                               │
│ real_time_monitor.start_monitoring()                            │
│ real_time_monitor.py                                            │
│                                                                  │
│ Infinite loop (every 30 seconds):                               │
│   Check all monitored_signals                                   │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ monitored_signals Dictionary                                    │
│                                                                  │
│ Populated by: real_time_monitor.add_signal()                   │
│ Called from: bot.py after position tracking                    │
│                                                                  │
│ ISSUE: Never populated because position tracking broken        │
│ Current state: {} (empty dict)                                 │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│ 80% Alert Check                                                 │
│                                                                  │
│ For each signal in monitored_signals:                           │
│   (NEVER EXECUTES - dict is empty)                             │
│                                                                  │
│   Should do:                                                     │
│   1. Fetch current price from Binance                           │
│   2. Calculate % progress to TP                                 │
│   3. If 75% ≤ progress ≤ 85%:                                  │
│      - Trigger ict_80_handler                                   │
│      - Re-analyze signal                                        │
│      - Send 80% alert to Telegram                               │
│      - Remove from monitoring                                    │
└─────────────────────────────────────────────────────────────────┘
```

**Result:** 80% alerts never trigger because monitored_signals is empty.

---

## Entry Points & Initialization

### Main Entry Point

**File:** bot.py  
**Function:** `main()` at line 17253  
**Trigger:** `python3 bot.py` or systemd service

### Initialization Sequence (Lines 17253-18450)

```
STEP 1: Global Object Creation (Lines 127-174)
├─ ICTSignalEngine initialized → ict_engine_global
├─ ICT80AlertHandler initialized → ict_80_handler_global
├─ TradeReanalysisEngine initialized → reanalysis_engine_global
└─ PositionManager initialized → position_manager_global
   ❓ QUESTION: Does this succeed? Need diagnostic logging

STEP 2: Telegram Bot Setup (Lines 17275-17387)
├─ ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
├─ Register 70+ command handlers:
│  ├─ /signal → signal_cmd
│  ├─ /market → market_cmd
│  ├─ /news → news_cmd
│  ├─ /daily → daily_report_cmd
│  ├─ /positions → position_list_cmd
│  ├─ /ml_status → ml_status_cmd
│  └─ ... (60+ more commands)
└─ Configure bot_data storage

STEP 3: Scheduler Initialization (Lines 17432-18288)
├─ Create AsyncIOScheduler (Bulgaria timezone)
├─ Schedule AUTO SIGNAL JOBS:
│  ├─ 1H signals: Every hour at :05 (line 17989)
│  ├─ 2H signals: Every 2 hours at :07 (line 18000)
│  ├─ 4H signals: Every 4 hours at :10 (line 18012)
│  └─ 1D signals: Daily at 09:15 UTC (line 18024)
│
├─ Schedule POSITION MONITORING:
│  └─ Every 1 minute (line 18037) → monitor_positions_job()
│
├─ Schedule HEALTH MONITORING:
│  ├─ Journal health: Every 6 hours (line 18087)
│  ├─ ML health: Daily at 10:00 (line 18124)
│  ├─ Daily report check: Daily at 09:00 (line 18161)
│  ├─ Position monitor health: Every hour (line 18198)
│  ├─ Scheduler health: Every 12 hours (line 18235)
│  └─ Disk space: Daily at 02:00 (line 18272)
│
├─ Schedule REPORTS:
│  ├─ Daily report: 08:00 BG time (line 17479)
│  ├─ Weekly report: Mondays 08:00 (line 17566)
│  ├─ Monthly report: 1st of month 08:00 (line 17632)
│  ├─ Daily backtest: 02:00 UTC (line 17701)
│  └─ Scheduled backtest report: 20:00 UTC (line 17851)
│
└─ scheduler.start() (line 18288)

STEP 4: Real-Time Monitor Setup (Lines 18295-18319)
├─ Create RealTimePositionMonitor instance
├─ Pass bot, ict_80_handler, owner_chat_id
├─ Create async task: monitor_task = loop.create_task(...)
└─ Start monitoring (every 30 seconds)

STEP 5: Startup Tasks (Lines 18436-18449)
├─ Schedule reports (after 5 seconds)
├─ Enable auto alerts (after 10 seconds)
├─ Send startup notification (after 0.5 seconds) ✅ IMMEDIATE
├─ End startup mode timer (after 300 seconds = 5 minutes)
└─ Keepalive ping (every 1800 seconds = 30 minutes)

STEP 6: Bot Polling Start (Line 18500+)
└─ application.run_polling()
   → Bot enters event loop, processing Telegram updates
```

**Startup Grace Period:**
- First 5 minutes (300 seconds): Suppresses duplicate startup signals
- Prevents alert spam during initialization
- Controlled by `STARTUP_GRACE_PERIOD_SECONDS` (line 395)

---

## Async Tasks & Background Jobs

### Scheduler Jobs (APScheduler)

| Job Name | Frequency | Function | Line | Purpose |
|----------|-----------|----------|------|---------|
| **1H Auto Signals** | Every 1h at :05 | `auto_signal_job('1h', bot)` | 17989 | Generate 1h timeframe signals |
| **2H Auto Signals** | Every 2h at :07 | `auto_signal_job('2h', bot)` | 18000 | Generate 2h timeframe signals |
| **4H Auto Signals** | Every 4h at :10 | `auto_signal_job('4h', bot)` | 18012 | Generate 4h timeframe signals |
| **1D Auto Signals** | Daily at 09:15 UTC | `auto_signal_job('1d', bot)` | 18024 | Generate 1d timeframe signals |
| **Position Monitoring** | Every 1 minute | `monitor_positions_job(bot)` | 18037 | Check checkpoints (25%/50%/75%/85%) |
| **80% Alerts** | Every 1 minute | `check_80_percent_alerts(bot)` | 12194 | Check 80% TP threshold |
| **Active Signals Check** | Every 15 minutes | `check_active_signals()` | 11245 | Track signal progress |
| **Journal Monitoring** | 24/7 continuous | `monitor_active_trades(context)` | 12137 | Monitor journal-based trades |
| **Journal Health** | Every 6 hours | `check_journal_health(...)` | 18087 | Validate journal integrity |
| **ML Health** | Daily at 10:00 | `check_ml_health(...)` | 18124 | Check ML model status |
| **Daily Report Check** | Daily at 09:00 | `check_daily_report_sent(...)` | 18161 | Ensure daily report delivered |
| **Position Monitor Health** | Every 1 hour | `check_position_monitor_health(...)` | 18198 | Validate position tracking |
| **Scheduler Health** | Every 12 hours | `check_scheduler_health(...)` | 18235 | Monitor scheduler status |
| **Disk Space Check** | Daily at 02:00 | `check_disk_space(...)` | 18272 | Prevent storage issues |
| **Daily Report** | Daily at 08:00 BG | `send_daily_report(...)` | 17479 | Performance summary |
| **Weekly Report** | Mon at 08:00 BG | `send_weekly_report(...)` | 17566 | Weekly performance |
| **Monthly Report** | 1st at 08:00 BG | `send_monthly_report(...)` | 17632 | Monthly performance |
| **Daily Backtest** | Daily at 02:00 UTC | `run_daily_backtest(...)` | 17701 | Backtest validation |
| **Backtest Report** | Daily at 20:00 UTC | `send_scheduled_backtest_report(...)` | 17851 | Backtest results |
| **Keepalive Ping** | Every 30 minutes | `keepalive_ping(...)` | 18449 | Prevent connection timeout |

---

### Async Background Tasks

| Task Name | Start Location | Purpose | Status |
|-----------|----------------|---------|--------|
| **Real-Time Monitor** | bot.py:18310 | Continuous price monitoring, 80% alerts | Running but empty ❌ |
| **Telegram Polling** | bot.py:18500+ | Process Telegram updates | Working ✅ |
| **Scheduler Event Loop** | bot.py:18288 | Run scheduled jobs | Working ✅ |

---

## External Dependencies

### APIs

| Service | Endpoint | Purpose | Rate Limits |
|---------|----------|---------|-------------|
| **Binance API** | `https://api.binance.com/api/v3` | Price data, OHLCV candles | 1200 requests/minute |
| **Telegram Bot API** | `https://api.telegram.org/bot{token}` | Send messages, receive commands | No strict limit |

### Python Packages (requirements.txt)

```
python-telegram-bot==20.x
APScheduler==3.x
pandas
numpy
matplotlib
scikit-learn
requests
sqlite3 (built-in)
```

### Environment Variables (.env)

```
TELEGRAM_BOT_TOKEN=<required>
OWNER_CHAT_ID=7003238836
BOT_BASE_PATH=<optional>
```

---

## File Structure

```
Crypto-signal-bot/
├── bot.py (18,507 lines) ⭐ MAIN ORCHESTRATOR
├── ict_signal_engine.py (5,563 lines) ⭐ SIGNAL GENERATION
├── position_manager.py (718 lines) ⭐ POSITION TRACKING
├── real_time_monitor.py (895 lines) ⭐ MONITORING
│
├── Pattern Detectors/
│   ├── order_block_detector.py
│   ├── fvg_detector.py
│   ├── liquidity_map.py
│   ├── ict_whale_detector.py
│   ├── breaker_block_detector.py
│   ├── sibi_ssib_detector.py
│   └── ilp_detector.py
│
├── Analysis Engines/
│   ├── mtf_analyzer.py
│   ├── trade_reanalysis_engine.py
│   ├── fibonacci_analyzer.py
│   └── zone_explainer.py
│
├── LuxAlgo Integration/
│   ├── luxalgo_sr_mtf.py
│   ├── luxalgo_ict_analysis.py
│   ├── luxalgo_ict_concepts.py
│   └── luxalgo_chart_generator.py
│
├── Charts & Visualization/
│   ├── chart_generator.py
│   ├── chart_annotator.py
│   ├── graph_engine.py
│   └── visualization_config.py
│
├── Machine Learning/
│   ├── ml_engine.py
│   ├── ml_predictor.py
│   └── journal_backtest.py
│
├── Reports & Diagnostics/
│   ├── daily_reports.py
│   ├── system_diagnostics.py
│   └── diagnostic_messages.py
│
├── Telegram/
│   ├── telegram_bot.py
│   ├── telegram_formatter_bg.py
│   └── (command handlers in bot.py)
│
├── Monitoring/
│   ├── real_time_monitor.py
│   ├── ict_80_alert_handler.py
│   └── bot_watchdog.py
│
├── Fundamental/
│   ├── __init__.py
│   ├── sentiment_analyzer.py
│   └── btc_correlator.py
│
├── Security/
│   ├── __init__.py
│   ├── auth.py
│   ├── rate_limiter.py
│   ├── security_monitor.py
│   └── token_manager.py
│
├── ICT Enhancements/
│   ├── __init__.py
│   ├── ict_enhancer.py
│   ├── breaker_detector.py
│   └── hqpo_detector.py
│
├── Utils/
│   ├── __init__.py
│   ├── market_data_fetcher.py
│   ├── market_helper.py
│   ├── fundamental_helper.py
│   ├── news_cache.py
│   └── trade_id_generator.py
│
├── Config/
│   ├── __init__.py
│   ├── trading_config.py
│   └── config_loader.py
│
├── Caching/
│   ├── cache_manager.py
│   ├── signal_cache.py
│   ├── signal_helpers.py
│   └── risk_management.py
│
├── Admin/
│   ├── admin_module.py
│   └── diagnostics.py
│
├── Automation/
│   ├── auto_fixer.py
│   ├── auto_updater.py
│   └── bot_watchdog.py
│
├── Legacy/
│   └── legacy_backtest/ (old implementations)
│
├── Tests/ (50+ files)
│   ├── test_*.py (unit tests)
│   ├── tests/ (integration tests)
│   └── validate_*.py (validation scripts)
│
├── Data Files/
│   ├── positions.db (SQLite) ❌ 0 records
│   ├── sent_signals_cache.json ✅
│   ├── news_cache.json ✅
│   ├── trading_journal.json ❌ NOT FOUND
│   ├── signal_cache.json ❌ NOT FOUND
│   └── bot_stats.json ❌ NOT FOUND
│
└── Documentation/ (100+ markdown files)
    ├── README.md
    ├── TRADING_STRATEGY.md
    ├── PR*_*.md (PR summaries)
    ├── IMPLEMENTATION_*.md
    └── ... (extensive docs)
```

---

## Component Interaction Summary

```
USER (Telegram)
    │
    ▼
┌─────────────────────┐
│   bot.py (Main)     │ ◄─── Telegram Commands
│   - Command Handler │
│   - Scheduler       │
│   - Orchestration   │
└──────────┬──────────┘
           │
           ├─────────► ICTSignalEngine ───► Pattern Detectors (7 files)
           │                              ├─► MTF Analyzer
           │                              ├─► ML Predictor
           │                              └─► Fibonacci Analyzer
           │
           ├─────────► ChartGenerator ────► chart_annotator
           │                              └─► graph_engine
           │
           ├─────────► PositionManager ───► positions.db (SQLite)
           │                              └─► TradeReanalysisEngine
           │
           ├─────────► RealTimeMonitor ───► ICT80AlertHandler
           │                              └─► Binance API (price data)
           │
           ├─────────► DailyReports ──────► SystemDiagnostics
           │
           └─────────► Telegram Bot ─────► User Notifications
```

---

## Summary of Issues

### Critical (System Broken)
1. **Position tracking:** 0 records in `open_positions` table despite signals being sent
2. **Checkpoint alerts:** Never trigger (depends on #1)
3. **Real-time monitor:** Empty monitored_signals dict (depends on #1)

### High (Data Integrity)
4. **Threshold mismatch:** Telegram sends at ~60%, Journal logs at ≥65% → 50% data loss
5. **Missing JSON files:** trading_journal.json, signal_cache.json, bot_stats.json not found

### Medium (Operational)
6. **Import test failures:** f-string format errors in multiple modules
7. **Database query error:** "no such table: positions" when should be "open_positions"

---

## Next Steps

See companion documents:
- **CORE_MODULES_REFERENCE.md** - Function-level documentation
- **TRADING_STRATEGY_EXPLAINED.md** - ICT methodology in plain English
- **CONFIGURATION_REFERENCE.md** - All config variables
- **DATA_STRUCTURES.md** - Schemas and formats
- **ISSUE_ANALYSIS.md** - Root cause analysis
- **FUNCTION_DEPENDENCY_MAP.md** - Call graphs
- **REMEDIATION_ROADMAP.md** - Fix plan

---

**Document Version:** 1.0  
**Last Updated:** January 17, 2026  
**Analyst:** AI System Documentation Generator
