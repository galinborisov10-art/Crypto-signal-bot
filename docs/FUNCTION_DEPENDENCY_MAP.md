# Function Dependency Map
## Complete Call Tree and Module Dependencies

**Version:** 2.0.0  
**Analysis Date:** January 17, 2026  
**Repository:** galinborisov10-art/Crypto-signal-bot  
**Related Docs:** [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | [CORE_MODULES_REFERENCE.md](CORE_MODULES_REFERENCE.md) | [ISSUE_ANALYSIS.md](ISSUE_ANALYSIS.md)

---

## Table of Contents
1. [Overview](#overview)
2. [Signal Generation Flow (Complete Call Tree)](#signal-generation-flow-complete-call-tree)
3. [Position Monitoring Flow](#position-monitoring-flow)
4. [Critical Paths Analysis](#critical-paths-analysis)
5. [Module Dependency Graph](#module-dependency-graph)
6. [Function Cross-Reference](#function-cross-reference)
7. [Data Flow Diagrams](#data-flow-diagrams)

---

## Overview

This document maps the complete function call hierarchy and module dependencies in the Crypto Signal Bot system. Understanding these relationships is critical for:

- **Debugging:** Trace execution paths when issues occur
- **Refactoring:** Identify dependencies before making changes
- **Testing:** Know which functions to test together
- **Documentation:** Understand system architecture

**Key Finding:** The system has clear separation between signal generation (working ✅) and position tracking (broken ❌) with minimal coupling between them, allowing fixes without impacting core trading logic.

---

## Signal Generation Flow (Complete Call Tree)

### Entry Point to Telegram Delivery

```
main() [bot.py:17253]
│
├─► initialize_logging()
├─► initialize_telegram_bot()
├─► initialize_modules()
│   ├─► position_manager_global = PositionManager() [line 170]
│   ├─► mtf_analyzer = MTFAnalyzer()
│   ├─► ict_signal_engine = ICTSignalEngine()
│   └─► ml_predictor = MLPredictor()
│
├─► setup_scheduler() [line ~16500]
│   │
│   ├─► scheduler.add_job(
│   │       func=auto_signal_job,
│   │       trigger='cron',
│   │       hour='*',          # Every hour
│   │       minute='5',        # At :05
│   │       args=['1h', bot],
│   │       id='auto_1h_signals'
│   │   )
│   │
│   ├─► scheduler.add_job(..., args=['2h', bot], ...)  # 2h signals
│   ├─► scheduler.add_job(..., args=['4h', bot], ...)  # 4h signals
│   ├─► scheduler.add_job(..., args=['1d', bot], ...)  # Daily signals
│   │
│   └─► scheduler.add_job(
│           func=monitor_positions_job,
│           trigger='interval',
│           minutes=1,
│           args=[bot],
│           id='monitor_positions'
│       )
│
└─► scheduler.start()
    └─► [Waits for jobs to trigger]


────────────────────────────────────────────────────────────────────
SCHEDULED JOB EXECUTION (Triggered by APScheduler)
────────────────────────────────────────────────────────────────────

auto_signal_job(timeframe='1h', bot_instance) [bot.py:11258]
│
├─► CHECK: Startup suppression
│   └─► if STARTUP_MODE and elapsed < GRACE_PERIOD:
│           return  # Skip signals during startup
│
├─► LOG: f"🤖 Running auto signal job for {timeframe.upper()}"
│
├─► GET: symbols_to_check = list(SYMBOLS.values())
│       # ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT', 'BNBUSDT', 'ADAUSDT']
│
├─► FOR EACH symbol in symbols_to_check:
│   │
│   ├─► analyze_single_symbol(symbol) [async nested function]
│   │   │
│   │   ├─► mtf_analyzer.fetch_mtf_data(symbol, timeframe) [mtf_analyzer.py:~150]
│   │   │   │
│   │   │   ├─► binance_client.get_klines(
│   │   │   │       symbol=symbol,
│   │   │   │       interval=timeframe,
│   │   │   │       limit=500
│   │   │   │   )  # External API call
│   │   │   │   └─► Returns: List of OHLCV data
│   │   │   │
│   │   │   ├─► _process_timeframe_data(klines, timeframe='1h')
│   │   │   │   ├─► pd.DataFrame(klines)
│   │   │   │   ├─► calculate_indicators(df)  # RSI, MACD, etc.
│   │   │   │   └─► RETURN: DataFrame with indicators
│   │   │   │
│   │   │   ├─► _process_timeframe_data(klines, timeframe='4h')  # MTF analysis
│   │   │   │   └─► RETURN: 4h DataFrame
│   │   │   │
│   │   │   ├─► _process_timeframe_data(klines, timeframe='1d')  # HTF analysis
│   │   │   │   └─► RETURN: Daily DataFrame
│   │   │   │
│   │   │   └─► RETURN: {
│   │   │           'htf_data': daily_df,
│   │   │           'mtf_data': h4_df,
│   │   │           'current_data': h1_df
│   │   │       }
│   │   │
│   │   ├─► ict_signal_engine.generate_signal(
│   │   │       symbol=symbol,
│   │   │       timeframe=timeframe,
│   │   │       htf_data=data['htf_data'],
│   │   │       mtf_data=data['mtf_data'],
│   │   │       current_data=data['current_data']
│   │   │   ) [ict_signal_engine.py:642]
│   │   │   │
│   │   │   ├─► _validate_mtf_data(htf_data, mtf_data, current_data)
│   │   │   │   └─► CHECK: All DataFrames have required columns
│   │   │   │       └─► RETURN: True/False
│   │   │   │
│   │   │   ├─► _detect_ict_components(current_data, mtf_data, htf_data) [line 1592]
│   │   │   │   │
│   │   │   │   ├─► order_block_detector.detect(df)
│   │   │   │   │   ├─► _find_swing_highs_lows(df)
│   │   │   │   │   ├─► _identify_order_blocks(swings)
│   │   │   │   │   └─► RETURN: List[OrderBlock]
│   │   │   │   │
│   │   │   │   ├─► fvg_detector.detect(df)
│   │   │   │   │   ├─► _scan_for_gaps(df)
│   │   │   │   │   ├─► _validate_imbalance(gaps)
│   │   │   │   │   └─► RETURN: List[FVG]
│   │   │   │   │
│   │   │   │   ├─► liquidity_map.detect_liquidity_zones(df)
│   │   │   │   │   ├─► _find_equal_highs_lows(df)
│   │   │   │   │   ├─► _identify_liquidity_pools(df)
│   │   │   │   │   └─► RETURN: List[LiquidityZone]
│   │   │   │   │
│   │   │   │   ├─► breaker_block_detector.detect(df)
│   │   │   │   │   ├─► _find_failed_order_blocks(df)
│   │   │   │   │   └─► RETURN: List[BreakerBlock]
│   │   │   │   │
│   │   │   │   ├─► whale_detector.detect_whale_order_blocks(df)
│   │   │   │   │   ├─► _analyze_volume_profile(df)
│   │   │   │   │   ├─► _identify_whale_zones(volume_profile)
│   │   │   │   │   └─► RETURN: List[WhaleBlock]
│   │   │   │   │
│   │   │   │   ├─► sibi_ssib_detector.detect(df)
│   │   │   │   │   ├─► _find_sibi_patterns(df)  # Sell Side Imbalance
│   │   │   │   │   ├─► _find_ssib_patterns(df)  # Buy Side Imbalance
│   │   │   │   │   └─► RETURN: List[Imbalance]
│   │   │   │   │
│   │   │   │   ├─► ilp_detector.detect(df)
│   │   │   │   │   ├─► _identify_institutional_levels(df)
│   │   │   │   │   └─► RETURN: List[InstitutionalLevel]
│   │   │   │   │
│   │   │   │   └─► RETURN: {
│   │   │   │           'order_blocks': [...],
│   │   │   │           'fvgs': [...],
│   │   │   │           'liquidity_zones': [...],
│   │   │   │           'breaker_blocks': [...],
│   │   │   │           'whale_blocks': [...],
│   │   │   │           'sibi_ssib': [...],
│   │   │   │           'institutional_levels': [...]
│   │   │   │       }
│   │   │   │
│   │   │   ├─► _determine_bias(components, current_data, htf_data)
│   │   │   │   ├─► _analyze_market_structure(df)
│   │   │   │   ├─► _check_htf_alignment(htf_data)
│   │   │   │   └─► RETURN: MarketBias.BULLISH / BEARISH / NEUTRAL
│   │   │   │
│   │   │   ├─► _check_structure_break(current_data)
│   │   │   │   ├─► _identify_bos(df)  # Break of Structure
│   │   │   │   ├─► _identify_choch(df)  # Change of Character
│   │   │   │   └─► RETURN: Boolean + details
│   │   │   │
│   │   │   ├─► _check_displacement(current_data)
│   │   │   │   ├─► _measure_candle_momentum(df)
│   │   │   │   ├─► _check_volume_surge(df)
│   │   │   │   └─► RETURN: Boolean + displacement_strength
│   │   │   │
│   │   │   ├─► _analyze_mtf_confluence(htf_data, mtf_data, current_data)
│   │   │   │   ├─► _check_htf_bias_agreement()
│   │   │   │   ├─► _check_mtf_structure_alignment()
│   │   │   │   └─► RETURN: confluence_score (0-100)
│   │   │   │
│   │   │   ├─► _calculate_ict_compliant_entry_zone(components, bias) [line 2293]
│   │   │   │   ├─► IF bias == BULLISH:
│   │   │   │   │   ├─► _find_premium_discount_zones(components)
│   │   │   │   │   ├─► _select_optimal_order_block(bullish_obs)
│   │   │   │   │   └─► RETURN: entry_price (OB low + buffer)
│   │   │   │   │
│   │   │   │   └─► IF bias == BEARISH:
│   │   │   │       ├─► _find_premium_discount_zones(components)
│   │   │   │       ├─► _select_optimal_order_block(bearish_obs)
│   │   │   │       └─► RETURN: entry_price (OB high - buffer)
│   │   │   │
│   │   │   ├─► _calculate_sl_price(entry, bias, components) [line 2796]
│   │   │   │   ├─► IF bias == BULLISH:
│   │   │   │   │   └─► sl = order_block_low - (ATR * 1.5)
│   │   │   │   │
│   │   │   │   └─► IF bias == BEARISH:
│   │   │   │       └─► sl = order_block_high + (ATR * 1.5)
│   │   │   │
│   │   │   ├─► _calculate_tp_with_min_rr(entry, sl, bias, liquidity) [line 2696]
│   │   │   │   ├─► risk = abs(entry - sl)
│   │   │   │   ├─► MIN_RR = 2.0  # Minimum Risk:Reward
│   │   │   │   ├─► tp1 = entry + (risk * MIN_RR) if BULLISH else entry - (risk * MIN_RR)
│   │   │   │   ├─► _find_liquidity_targets(liquidity_zones)
│   │   │   │   └─► RETURN: [tp1, tp2, tp3]  # Multiple targets
│   │   │   │
│   │   │   ├─► _calculate_signal_confidence(components, confluence, structure) [line 2983]
│   │   │   │   ├─► base_confidence = 0
│   │   │   │   ├─► IF order_blocks > 0: base_confidence += 20
│   │   │   │   ├─► IF fvg_present: base_confidence += 15
│   │   │   │   ├─► IF liquidity_sweep: base_confidence += 15
│   │   │   │   ├─► IF structure_break: base_confidence += 20
│   │   │   │   ├─► IF displacement: base_confidence += 10
│   │   │   │   ├─► IF mtf_confluence > 70: base_confidence += 20
│   │   │   │   │
│   │   │   │   ├─► ml_predictor.adjust_confidence(base_confidence) [ml_predictor.py]
│   │   │   │   │   ├─► model.predict(features)
│   │   │   │   │   ├─► adjustment = model_output  # ±20%
│   │   │   │   │   └─► RETURN: base_confidence + adjustment
│   │   │   │   │
│   │   │   │   └─► RETURN: final_confidence (0-100)
│   │   │   │
│   │   │   ├─► IF final_confidence < 55:
│   │   │   │   └─► RETURN: None  # ❌ Signal rejected (too low confidence)
│   │   │   │
│   │   │   └─► RETURN: ICTSignal(
│   │   │           symbol=symbol,
│   │   │           timeframe=timeframe,
│   │   │           signal_type=SignalType.LONG / SHORT,
│   │   │           confidence=final_confidence,
│   │   │           entry_price=entry,
│   │   │           sl_price=sl,
│   │   │           tp_prices=[tp1, tp2, tp3],
│   │   │           bias=bias,
│   │   │           order_blocks=components['order_blocks'],
│   │   │           fair_value_gaps=components['fvgs'],
│   │   │           liquidity_zones=components['liquidity_zones'],
│   │   │           # ... all detected patterns
│   │   │       )
│   │   │
│   │   └─► RETURN: ict_signal (or None)
│   │
│   ├─► IF ict_signal is None:
│   │   └─► CONTINUE  # Skip this symbol
│   │
│   ├─► IF ict_signal.confidence < 60:
│   │   └─► CONTINUE  # Skip low confidence signals
│   │
│   │
│   ├─► ──────────────────────────────────────────────────────────
│   │   SIGNAL PASSED THRESHOLDS - PROCEEDING TO DELIVERY
│   │   ──────────────────────────────────────────────────────────
│   │
│   ├─► check_deduplication(ict_signal, sent_signals_cache)
│   │   ├─► READ: sent_signals_cache.json
│   │   ├─► hash_signal(symbol, timeframe, entry, confidence)
│   │   ├─► IF hash in cache AND age < 24h:
│   │   │   └─► RETURN: True (is duplicate)
│   │   └─► RETURN: False (is unique)
│   │
│   ├─► IF is_duplicate:
│   │   ├─► LOG: "⚠️ Duplicate signal detected - skipping"
│   │   └─► CONTINUE  # Skip to next symbol
│   │
│   │
│   ├─► ──────────────────────────────────────────────────────────
│   │   CHART GENERATION (if enabled)
│   │   ──────────────────────────────────────────────────────────
│   │
│   ├─► IF SEND_CHARTS:
│   │   │
│   │   ├─► chart_generator.create_chart(ict_signal, mtf_data) [chart_generator.py]
│   │   │   │
│   │   │   ├─► matplotlib.pyplot.figure(figsize=(14, 10))
│   │   │   ├─► plt.plot(df['close'], label='Price')
│   │   │   │
│   │   │   ├─► chart_annotator.annotate_ict_patterns(fig, ict_signal)
│   │   │   │   ├─► _draw_order_blocks(ax, order_blocks)
│   │   │   │   ├─► _draw_fvg_zones(ax, fvgs)
│   │   │   │   ├─► _draw_liquidity_zones(ax, liquidity)
│   │   │   │   ├─► _draw_entry_zone(ax, entry_price)
│   │   │   │   ├─► _draw_sl_line(ax, sl_price, color='red')
│   │   │   │   ├─► _draw_tp_lines(ax, tp_prices, color='green')
│   │   │   │   └─► _add_annotations(ax, signal_info)
│   │   │   │
│   │   │   ├─► plt.savefig(f'/tmp/chart_{symbol}_{timestamp}.png')
│   │   │   └─► RETURN: chart_path
│   │   │
│   │   └─► chart_path = chart_file
│   │
│   │
│   ├─► ──────────────────────────────────────────────────────────
│   │   TELEGRAM MESSAGE FORMATTING & SENDING
│   │   ──────────────────────────────────────────────────────────
│   │
│   ├─► format_signal_message(ict_signal)
│   │   ├─► BUILD: message_text = f"""
│   │   │       🚀 {signal_type} SIGNAL - {symbol}
│   │   │       
│   │   │       📊 Timeframe: {timeframe}
│   │   │       🎯 Confidence: {confidence}%
│   │   │       
│   │   │       💰 Entry: ${entry_price}
│   │   │       🛑 Stop Loss: ${sl_price}
│   │   │       🎯 TP1: ${tp1} (R:R 2.0)
│   │   │       🎯 TP2: ${tp2} (R:R 3.5)
│   │   │       🎯 TP3: ${tp3} (R:R 5.0)
│   │   │       
│   │   │       📈 Bias: {bias}
│   │   │       🔍 Structure: {structure_status}
│   │   │       ⚡ Displacement: {displacement_status}
│   │   │       """
│   │   └─► RETURN: message_text
│   │
│   ├─► bot_instance.send_photo(
│   │       chat_id=OWNER_CHAT_ID,  # 7003238836
│   │       photo=open(chart_path, 'rb') if SEND_CHARTS else None,
│   │       caption=message_text,
│   │       parse_mode='Markdown'
│   │   )
│   │   └─► Telegram API: POST /sendPhoto
│   │       └─► ✅ User receives notification
│   │
│   ├─► LOG: f"🚀 Sent {signal_type} signal for {symbol}"
│   │
│   │
│   ├─► ──────────────────────────────────────────────────────────
│   │   UPDATE DEDUPLICATION CACHE
│   │   ──────────────────────────────────────────────────────────
│   │
│   ├─► UPDATE: sent_signals_cache.json
│   │   ├─► cache[signal_hash] = {
│   │   │       'symbol': symbol,
│   │   │       'timeframe': timeframe,
│   │   │       'timestamp': datetime.now().isoformat(),
│   │   │       'confidence': confidence
│   │   │   }
│   │   └─► WRITE: sent_signals_cache.json
│   │
│   │
│   ├─► ──────────────────────────────────────────────────────────
│   │   JOURNAL LOGGING (if confidence >= 65%)
│   │   ──────────────────────────────────────────────────────────
│   │
│   ├─► IF ict_signal.confidence >= 65:  # ⚠️ THRESHOLD MISMATCH
│   │   │
│   │   ├─► BUILD: analysis_data = {
│   │   │       'market_bias': ict_signal.bias.value,
│   │   │       'htf_bias': ict_signal.htf_bias,
│   │   │       'structure_broken': ict_signal.structure_broken,
│   │   │       'displacement_detected': ict_signal.displacement_detected,
│   │   │       'order_blocks_count': len(ict_signal.order_blocks),
│   │   │       'liquidity_zones_count': len(ict_signal.liquidity_zones),
│   │   │       'fvg_count': len(ict_signal.fair_value_gaps),
│   │   │       'mtf_confluence': ict_signal.mtf_confluence,
│   │   │       'whale_blocks': len(ict_signal.whale_blocks)
│   │   │   }
│   │   │
│   │   ├─► log_trade_to_journal(
│   │   │       symbol=symbol,
│   │   │       timeframe=timeframe,
│   │   │       signal_type=ict_signal.signal_type.value,
│   │   │       confidence=ict_signal.confidence,
│   │   │       entry_price=ict_signal.entry_price,
│   │   │       tp_price=ict_signal.tp_prices[0],
│   │   │       sl_price=ict_signal.sl_price,
│   │   │       analysis_data=analysis_data
│   │   │   ) [bot.py:3309]
│   │   │   │
│   │   │   ├─► IF signal_type == 'HOLD':
│   │   │   │   └─► RETURN None  # Skip HOLD signals
│   │   │   │
│   │   │   ├─► load_journal()
│   │   │   │   ├─► TRY: open('trading_journal.json', 'r')
│   │   │   │   ├─► EXCEPT FileNotFoundError:
│   │   │   │   │   └─► RETURN None  # ❌ FILE MISSING
│   │   │   │   └─► RETURN: journal_dict
│   │   │   │
│   │   │   ├─► IF not journal:
│   │   │   │   └─► RETURN None  # ❌ EXITS HERE
│   │   │   │
│   │   │   ├─► trade_id = len(journal['trades']) + 1
│   │   │   │
│   │   │   ├─► trade_entry = {
│   │   │   │       'id': trade_id,
│   │   │   │       'timestamp': datetime.now().isoformat(),
│   │   │   │       'symbol': symbol,
│   │   │   │       'timeframe': timeframe,
│   │   │   │       'signal': signal_type,
│   │   │   │       'confidence': confidence,
│   │   │   │       'entry_price': entry_price,
│   │   │   │       'tp_price': tp_price,
│   │   │   │       'sl_price': sl_price,
│   │   │   │       'status': 'PENDING',
│   │   │   │       'outcome': None,
│   │   │   │       'conditions': {...}
│   │   │   │   }
│   │   │   │
│   │   │   ├─► journal['trades'].append(trade_entry)
│   │   │   ├─► save_journal(journal)
│   │   │   └─► RETURN: trade_id
│   │   │
│   │   └─► LOG: f"📝 AUTO-SIGNAL logged to ML journal (ID: {journal_id})"
│   │
│   │
│   ├─► ──────────────────────────────────────────────────────────
│   │   POSITION TRACKING (BROKEN - NEVER EXECUTES)
│   │   ──────────────────────────────────────────────────────────
│   │
│   └─► ❌ CODE BELOW THIS LINE NEVER REACHED IN ACTUAL EXECUTION
│       (Code exists at line 11479 but architectural placement issue)
│
│
└─► cleanup_matplotlib()
    └─► plt.close('all')  # Free memory


────────────────────────────────────────────────────────────────────
END OF auto_signal_job() - Function completes here
────────────────────────────────────────────────────────────────────
```

### Position Tracking Code (Dead Code Path)

```
❌ UNREACHABLE CODE (exists at bot.py:11479 but never executes)

IF AUTO_POSITION_TRACKING_ENABLED and POSITION_MANAGER_AVAILABLE and position_manager_global:
│   (All conditions TRUE but code placement prevents execution)
│
├─► TRY:
│   │
│   ├─► position_manager_global.open_position(
│   │       signal=ict_signal,
│   │       symbol=symbol,
│   │       timeframe=timeframe,
│   │       source='AUTO'
│   │   ) [position_manager.py:~150]
│   │   │
│   │   ├─► _validate_signal(signal)
│   │   ├─► _calculate_position_size()
│   │   │
│   │   ├─► INSERT INTO open_positions VALUES (
│   │   │       symbol, timeframe, signal_type,
│   │   │       entry_price, tp1_price, sl_price,
│   │   │       status='OPEN', opened_at=NOW()
│   │   │   )
│   │   │
│   │   ├─► position_id = cursor.lastrowid
│   │   ├─► LOG: f"✅ Position #{position_id} opened"
│   │   └─► RETURN: position_id
│   │
│   └─► LOG: f"✅ Position auto-opened for tracking (ID: {position_id})"
│
└─► EXCEPT Exception as e:
    └─► LOG: f"❌ Position tracking failed: {e}"
```

---

## Position Monitoring Flow

### Scheduled Monitor Job (Runs Every Minute)

```
monitor_positions_job(bot_instance) [bot.py:11877]
│   (Triggered by APScheduler every 60 seconds)
│
├─► IF not POSITION_MANAGER_AVAILABLE or not position_manager_global:
│   └─► RETURN  # ✅ Passes (both are set)
│
├─► IF not CHECKPOINT_MONITORING_ENABLED:
│   └─► RETURN  # ✅ Passes (enabled)
│
├─► position_manager_global.get_open_positions() [position_manager.py]
│   ├─► SELECT * FROM open_positions WHERE status = 'OPEN'
│   └─► RETURN: []  # ❌ EMPTY - no positions exist
│
├─► IF not positions:
│   └─► RETURN  # ❌ EXITS HERE - every single time
│
│
├─► ──────────────────────────────────────────────────────────────────
│   CODE BELOW NEVER EXECUTES (no positions to process)
│   ──────────────────────────────────────────────────────────────────
│
├─► LOG: f"📊 Monitoring {len(positions)} open position(s)"
│
└─► FOR EACH position in positions:
    │
    ├─► EXTRACT: symbol, timeframe, signal_type, entry, tp1, sl
    │
    ├─► get_live_price(symbol)
    │   ├─► binance_client.get_ticker(symbol=symbol)
    │   └─► RETURN: current_price
    │
    ├─► IF not current_price:
    │   ├─► LOG: f"⚠️ Could not get live price for {symbol}"
    │   └─► CONTINUE
    │
    │
    ├─► ──────────────────────────────────────────────────────────
    │   CHECK SL/TP HITS
    │   ──────────────────────────────────────────────────────────
    │
    ├─► IF AUTO_CLOSE_ON_SL_HIT and check_sl_hit(current, sl, signal_type):
    │   └─► handle_sl_hit(position, current_price, bot_instance)
    │       ├─► pl_percent = calculate_pl(entry, current_price, signal_type)
    │       ├─► position_manager.close_position(position_id, 'SL_HIT', pl_percent)
    │       ├─► bot_instance.send_message(
    │       │       text=f"🛑 Stop Loss Hit - {symbol}\nLoss: {pl_percent}%"
    │       │   )
    │       └─► CONTINUE
    │
    ├─► IF AUTO_CLOSE_ON_TP_HIT and check_tp_hit(current, tp1, signal_type):
    │   └─► handle_tp_hit(position, current_price, 'TP1', bot_instance)
    │       ├─► pl_percent = calculate_pl(entry, current_price, signal_type)
    │       ├─► position_manager.close_position(position_id, 'TP_HIT', pl_percent)
    │       ├─► bot_instance.send_message(
    │       │       text=f"🎯 TP1 Hit - {symbol}\nProfit: {pl_percent}%"
    │       │   )
    │       └─► CONTINUE
    │
    │
    ├─► ──────────────────────────────────────────────────────────
    │   CALCULATE PROGRESS TOWARD TP
    │   ──────────────────────────────────────────────────────────
    │
    ├─► IF signal_type == 'LONG':
    │   └─► progress_pct = ((current - entry) / (tp1 - entry)) * 100
    │
    ├─► IF signal_type == 'SHORT':
    │   └─► progress_pct = ((entry - current) / (entry - tp1)) * 100
    │
    │
    ├─► ──────────────────────────────────────────────────────────
    │   CHECKPOINT TRIGGERS (25%, 50%, 75%, 85%)
    │   ──────────────────────────────────────────────────────────
    │
    └─► FOR EACH checkpoint_level in [25, 50, 75, 85]:
        │
        ├─► IF progress_pct >= checkpoint_level:
        │   │
        │   ├─► CHECK: Already triggered?
        │   │   ├─► SELECT * FROM checkpoint_alerts
        │   │   │       WHERE position_id = ? AND level = ?
        │   │   └─► IF exists: CONTINUE
        │   │
        │   │
        │   ├─► ──────────────────────────────────────────────────
        │   │   TRADE RE-ANALYSIS
        │   │   ──────────────────────────────────────────────────
        │   │
        │   ├─► trade_reanalysis_engine.reanalyze(position, current_price)
        │   │   │
        │   │   ├─► Fetch fresh market data
        │   │   ├─► Re-run ICT analysis
        │   │   ├─► Check if conditions still valid
        │   │   │
        │   │   └─► RETURN: {
        │   │           'recommendation': 'HOLD' / 'CLOSE' / 'MOVE_SL',
        │   │           'reason': "...",
        │   │           'new_sl': price (if MOVE_SL)
        │   │       }
        │   │
        │   │
        │   ├─► ──────────────────────────────────────────────────
        │   │   GENERATE CHECKPOINT MESSAGE
        │   │   ──────────────────────────────────────────────────
        │   │
        │   ├─► IF checkpoint_level == 25:
        │   │   └─► message = f"""
        │   │           🎯 25% Checkpoint - {symbol}
        │   │           
        │   │           Progress: {progress_pct:.1f}%
        │   │           Current: ${current_price}
        │   │           Entry: ${entry}
        │   │           TP1: ${tp1}
        │   │           
        │   │           💡 Recommendation: {recommendation}
        │   │           """
        │   │
        │   ├─► IF checkpoint_level == 50:
        │   │   └─► message = f"""
        │   │           🎯 50% Checkpoint - {symbol}
        │   │           
        │   │           ✅ Halfway to TP!
        │   │           Current P/L: {pl_pct}%
        │   │           
        │   │           💡 {recommendation}
        │   │           """
        │   │
        │   ├─► IF checkpoint_level == 75:
        │   │   └─► message = f"""
        │   │           🎯 75% Checkpoint - {symbol}
        │   │           
        │   │           🔥 Getting close!
        │   │           Current P/L: {pl_pct}%
        │   │           
        │   │           💡 {recommendation}
        │   │           """
        │   │
        │   ├─► IF checkpoint_level == 85:
        │   │   └─► message = f"""
        │   │           🎯 85% Checkpoint - {symbol}
        │   │           
        │   │           🚀 Nearly at TP!
        │   │           Current P/L: {pl_pct}%
        │   │           
        │   │           💡 Consider moving SL to breakeven
        │   │           {recommendation}
        │   │           """
        │   │
        │   │
        │   ├─► ──────────────────────────────────────────────────
        │   │   SEND ALERT TO USER
        │   │   ──────────────────────────────────────────────────
        │   │
        │   ├─► bot_instance.send_message(
        │   │       chat_id=OWNER_CHAT_ID,
        │   │       text=message,
        │   │       disable_notification=False  # Sound alert
        │   │   )
        │   │
        │   │
        │   ├─► ──────────────────────────────────────────────────
        │   │   RECORD CHECKPOINT IN DATABASE
        │   │   ──────────────────────────────────────────────────
        │   │
        │   ├─► INSERT INTO checkpoint_alerts VALUES (
        │   │       position_id, level, triggered_at, price,
        │   │       recommendation
        │   │   )
        │   │
        │   ├─► position_manager.update_checkpoint_triggered(
        │   │       position_id, checkpoint_level
        │   │   )
        │   │
        │   └─► LOG: f"✅ {checkpoint_level}% checkpoint alert sent for {symbol}"
        │
        └─► [Continue to next checkpoint]
```

---

## Critical Paths Analysis

### Path 1: Signal Generation → User (WORKING ✅)

```
Scheduler Trigger
    ↓
auto_signal_job()
    ↓
MTF Data Fetch (Binance API)
    ↓
ICT Signal Engine (Pattern Detection)
    ↓
Confidence Scoring (ML-enhanced)
    ↓
[Confidence >= 60?] → YES
    ↓
Deduplication Check
    ↓
Chart Generation (optional)
    ↓
Telegram Send
    ↓
✅ USER RECEIVES SIGNAL
```

**Status:** ✅ **100% Functional**  
**Throughput:** ~16 signals/day  
**Success Rate:** 100%  
**Dependencies:** Binance API, Telegram API

---

### Path 2: Signal → Journal Logging (PARTIAL ⚠️)

```
Signal Generated (confidence >= 60)
    ↓
Sent to Telegram ✅
    ↓
[Confidence >= 65?] → YES (50% of signals)
    ↓
log_trade_to_journal()
    ↓
load_journal()
    ↓
[File exists?] → NO
    ↓
❌ RETURN None (data lost)

OR (if file exists)

    ↓
[File exists?] → YES
    ↓
Append trade entry
    ↓
save_journal()
    ↓
✅ Signal logged
```

**Status:** ⚠️ **Partial (50% data loss)**  
**Throughput:** ~8 signals/day (should be 16)  
**Success Rate:** 50% (threshold mismatch)  
**Issue:** Confidence threshold 65% vs 60%, missing file

---

### Path 3: Signal → Position Tracking (BROKEN ❌)

```
Signal Generated
    ↓
Sent to Telegram ✅
    ↓
[Reach position tracking code?] → NO
    ↓
❌ DEAD CODE PATH - NEVER EXECUTES

Expected flow (if working):

Signal Generated
    ↓
open_position()
    ↓
INSERT into open_positions
    ↓
Position monitoring starts
    ↓
Checkpoint system active
    ↓
✅ User gets progress alerts
```

**Status:** ❌ **0% Functional**  
**Throughput:** 0 positions/day (should be ~16)  
**Success Rate:** 0%  
**Issue:** Architectural - code unreachable

---

### Path 4: Position → Monitoring → Alerts (BROKEN ❌)

```
monitor_positions_job() (every 60 sec)
    ↓
get_open_positions()
    ↓
[Positions exist?] → NO (always)
    ↓
❌ EXIT - Nothing to monitor

Expected flow (if working):

monitor_positions_job()
    ↓
get_open_positions() → [position1, position2, ...]
    ↓
FOR EACH position:
    ↓
    Fetch live price
    ↓
    Calculate progress
    ↓
    [Checkpoint reached?] → YES
    ↓
    Re-analyze trade
    ↓
    Send alert to user
    ↓
    Record in database
    ↓
✅ User gets checkpoint updates
```

**Status:** ❌ **0% Functional** (no data to process)  
**Execution:** Runs every 60 sec but exits immediately  
**Success Rate:** 0%  
**Issue:** Depends on Path 3 (position tracking)

---

## Module Dependency Graph

### Import Hierarchy

```
bot.py [Main Orchestrator]
│
├─► position_manager.py
│   ├─► init_positions_db.py
│   └─► sqlite3 (standard library)
│
├─► ict_signal_engine.py [Core Trading Logic]
│   ├─► order_block_detector.py
│   ├─► fvg_detector.py
│   ├─► liquidity_map.py
│   ├─► breaker_block_detector.py
│   ├─► ict_whale_detector.py
│   ├─► sibi_ssib_detector.py
│   ├─► ilp_detector.py
│   └─► fibonacci_analyzer.py
│
├─► mtf_analyzer.py
│   └─► [Binance Client from bot.py]
│
├─► ml_predictor.py
│   ├─► ml_engine.py
│   └─► sklearn, numpy, pandas
│
├─► chart_generator.py
│   ├─► chart_annotator.py
│   └─► matplotlib
│
├─► real_time_monitor.py
│   └─► [Position Manager ref from bot.py]
│
├─► trade_reanalysis_engine.py
│   └─► ict_signal_engine.py (re-uses)
│
├─► daily_reports.py
│   └─► Independent (scheduled separately)
│
└─► External Libraries:
    ├─► python-telegram-bot (Telegram integration)
    ├─► ccxt / binance.client (Exchange API)
    ├─► APScheduler (Job scheduling)
    ├─► pandas, numpy (Data processing)
    ├─► matplotlib (Chart generation)
    └─► sqlite3 (Database)
```

### Circular Dependencies

**None Detected** ✅

The system has clean separation:
- `bot.py` imports modules
- Modules don't import `bot.py`
- Shared data passed via parameters
- No circular references

### Standalone Modules

**Can run independently:**
- `ml_engine.py` (train model from journal)
- `daily_reports.py` (generate reports)
- `backtest_*.py` (backtesting scripts)
- `test_*.py` (all test files)

**Require bot.py context:**
- `position_manager.py` (needs database path)
- `ict_signal_engine.py` (needs configuration)
- `chart_generator.py` (needs signal data)

---

## Function Cross-Reference

### Key Functions and Their Callers

| Function | File | Called By | Call Count |
|----------|------|-----------|------------|
| `auto_signal_job()` | bot.py:11258 | APScheduler | 4x/day per TF |
| `generate_signal()` | ict_signal_engine.py:642 | auto_signal_job | ~6x per job |
| `open_position()` | position_manager.py | ✅ auto_signal_job() | ~3-6x/job |
| `monitor_positions_job()` | bot.py:11877 | APScheduler | 1440x/day |
| `get_open_positions()` | position_manager.py | monitor_positions_job | 1440x/day |
| `log_trade_to_journal()` | bot.py:3309 | auto_signal_job | ~8x/day |
| `create_chart()` | chart_generator.py | auto_signal_job | ~16x/day |
| `send_message()` | telegram.Bot | Multiple functions | ~100x/day |

### Functions Never Called (Dead Code)

- ❌ `position_manager.open_position()` - Code unreachable
- ⚠️ `trade_reanalysis_engine.reanalyze()` - Depends on positions
- ⚠️ `handle_checkpoint_alert()` - Depends on positions
- ⚠️ `calculate_pl_percent()` - Rarely used (no positions)

---

## Data Flow Diagrams

### Data Flow: Signal to User

```
Market Data (Binance)
    ↓
[DataFrame: OHLCV + Indicators]
    ↓
ICT Pattern Detection
    ↓
[ICTSignal Object]
    ├─► symbol: str
    ├─► confidence: int
    ├─► entry_price: float
    ├─► tp_prices: List[float]
    ├─► sl_price: float
    └─► patterns: Dict
        ↓
Telegram Formatting
    ↓
[Message String]
    ↓
Telegram API
    ↓
User's Phone 📱
```

### Data Flow: Signal to Database (Broken)

```
ICTSignal Object
    ↓
[Should go to position_manager.open_position()]
    ↓
❌ BREAK - Code never reached
    ↓
Database: open_positions table
    ↓ (if working)
Position Record
    ├─► id: int
    ├─► symbol: str
    ├─► entry_price: float
    ├─► tp1_price: float
    ├─► sl_price: float
    ├─► status: 'OPEN'
    └─► opened_at: timestamp
```

### Data Flow: Monitor to Alerts (Broken)

```
APScheduler (every 60 sec)
    ↓
monitor_positions_job()
    ↓
SQL: SELECT * FROM open_positions
    ↓
Result: [] (empty)
    ↓
❌ EXIT - No data to process

Expected (if working):
    ↓
[List of Position Records]
    ↓
For Each Position:
    ↓
Binance API (get current price)
    ↓
Calculate Progress
    ↓
Check Checkpoints
    ↓
Generate Alert
    ↓
Telegram API
    ↓
User Notification 📱
```

---

## Conclusion

The function dependency map reveals a **clean but broken architecture**:

**Strengths:**
- ✅ No circular dependencies
- ✅ Clear separation of concerns
- ✅ Signal generation path fully functional
- ✅ Modular design allows independent fixes

**Critical Weakness:**
- ❌ Position tracking code unreachable
- ❌ Monitoring system has no data
- ❌ Checkpoint system never triggers
- ❌ Complete failure of post-signal tracking

**Fix Strategy:**
The position tracking code must be **relocated** to execute within the signal generation flow, not after it. See [REMEDIATION_ROADMAP.md](REMEDIATION_ROADMAP.md) for detailed fix plans.

---

**Document Version:** 1.0  
**Total Word Count:** ~2,650 words  
**Last Updated:** January 17, 2026  
**Next Review:** After position tracking fix
