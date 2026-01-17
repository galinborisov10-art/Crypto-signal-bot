# Core Modules Reference
## Function-Level Documentation for Crypto Signal Bot

**Version:** 2.0.0  
**Documentation Date:** January 17, 2026  
**Repository:** galinborisov10-art/Crypto-signal-bot  
**Related Docs:** [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) | [TRADING_STRATEGY_EXPLAINED.md](TRADING_STRATEGY_EXPLAINED.md)

---

## Table of Contents
1. [bot.py - Main Orchestrator](#botpy---main-orchestrator)
2. [ict_signal_engine.py - Signal Generation](#ict_signal_enginepy---signal-generation)
3. [position_manager.py - Position Lifecycle](#position_managerpy---position-lifecycle)
4. [real_time_monitor.py - 24/7 Monitoring](#real_time_monitorpy---247-monitoring)
5. [chart_generator.py - Chart Visualization](#chart_generatorpy---chart-visualization)
6. [Cross-Reference Guide](#cross-reference-guide)

---

## bot.py - Main Orchestrator
**Lines:** 18,507 | **Size:** 802 KB | **Purpose:** Telegram bot, scheduler, command handlers, signal routing

### Core Application Functions

#### `main()` - Line 17253
**Purpose:** Application entry point and initialization

**Responsibilities:**
- Create Telegram bot application (`ApplicationBuilder`)
- Register 70+ command handlers (`/start`, `/signal`, `/stats`, etc.)
- Setup APScheduler for background jobs
- Initialize position monitoring
- Start health monitoring system
- Configure persistence and error handlers

**Key Code:**
```python
def main():
    # Create application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("signal", signal_cmd))
    application.add_handler(CommandHandler("stats", stats_cmd))
    # ... 70+ more handlers
    
    # Setup scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(auto_signal_job, 'interval', hours=1, args=['1h', application.bot])
    scheduler.add_job(auto_signal_job, 'interval', hours=2, args=['2h', application.bot])
    scheduler.add_job(auto_signal_job, 'interval', hours=4, args=['4h', application.bot])
    scheduler.add_job(auto_signal_job, 'interval', hours=24, args=['1d', application.bot])
    
    # Start monitoring
    scheduler.add_job(monitor_positions_job, 'interval', seconds=60, args=[application.bot])
    scheduler.start()
    
    # Run bot
    application.run_polling()
```

**Called By:** System startup  
**Calls:** All command handlers, scheduler jobs  
**Side Effects:** Starts persistent bot process, opens database connections

---

### Signal Generation Functions

#### `async def auto_signal_job(timeframe: str, bot_instance)` - Line 11258
**Purpose:** Automated signal generation for scheduled timeframes

**Parameters:**
- `timeframe` (str): '1h', '2h', '4h', or '1d'
- `bot_instance`: Telegram bot instance for message sending

**Returns:** None (sends Telegram alerts)

**Workflow:**
```python
async def auto_signal_job(timeframe: str, bot_instance):
    # 1. Check signal cooldown (prevent duplicates)
    if not can_send_signal(timeframe):
        return
    
    # 2. Generate ICT signal for each crypto
    for symbol in ['BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'ADA']:
        signal = ict_engine.generate_signal(
            symbol=symbol,
            timeframe=timeframe,
            exchange='binance'
        )
        
        # 3. Validate signal quality
        if signal and signal.confidence >= 65:
            # 4. Check deduplication cache
            if not is_duplicate_signal(signal):
                # 5. Send alert to users
                await send_alert_signal(signal, bot_instance)
                
                # 6. Open position tracking (CURRENTLY BROKEN ❌)
                await open_position(signal)
                
                # 7. Update cooldown
                update_signal_cooldown(timeframe, symbol)
```

**Called By:** APScheduler (every 1h/2h/4h/24h)  
**Calls:** `ict_engine.generate_signal()`, `send_alert_signal()`, `open_position()`  
**Side Effects:** Sends Telegram messages, updates cache files, creates DB records

**Known Issues:**
- ❌ `open_position()` call fails silently (positions.db remains at 0 records)
- ✅ Signal generation and Telegram delivery work correctly

---

#### `async def send_alert_signal(signal, bot_instance)` - Line 11014
**Purpose:** Broadcast signal alerts to all users with deduplication

**Parameters:**
- `signal` (ICTSignal): Signal object with entry/TP/SL/confidence
- `bot_instance`: Telegram bot instance

**Returns:** None

**Features:**
- Parallel message sending to multiple users
- Signal deduplication via cache
- Chart generation (if enabled)
- Journal logging
- Error handling per user

**Code Flow:**
```python
async def send_alert_signal(signal, bot_instance):
    # 1. Check duplicate cache
    cache_key = f"{signal.symbol}_{signal.timeframe}_{signal.signal_type}"
    if cache_key in sent_signals_cache:
        return
    
    # 2. Format message
    message = format_ict_signal(signal)
    
    # 3. Generate chart (if enabled)
    chart_path = None
    if SEND_CHARTS:
        chart_path = chart_generator.generate(signal)
    
    # 4. Send to all users
    for user_id in allowed_users:
        try:
            if chart_path:
                await bot_instance.send_photo(user_id, chart_path, caption=message)
            else:
                await bot_instance.send_message(user_id, message, parse_mode='HTML')
        except Exception as e:
            logger.error(f"Failed to send to user {user_id}: {e}")
    
    # 5. Add to cache
    sent_signals_cache[cache_key] = datetime.now()
    
    # 6. Log to journal
    journal.log_signal(signal)
```

**Called By:** `auto_signal_job()`, `/signal` command  
**Calls:** `format_ict_signal()`, `chart_generator.generate()`, `journal.log_signal()`  
**Side Effects:** Sends Telegram messages, updates cache, logs to journal

---

#### `async def signal_cmd(update, context)` - Line 5800
**Purpose:** Handle `/signal SYMBOL` command for on-demand analysis

**Parameters:**
- `update`: Telegram update object
- `context`: Telegram context with user message

**Usage Examples:**
- `/signal BTC` - Analyze Bitcoin
- `/signal ETH` - Analyze Ethereum
- `/signal XRP 4h` - Analyze XRP on 4-hour timeframe

**Implementation:**
```python
async def signal_cmd(update, context):
    # 1. Parse command arguments
    if not context.args:
        await update.message.reply_text("Usage: /signal SYMBOL [TIMEFRAME]")
        return
    
    symbol = context.args[0].upper()
    timeframe = context.args[1] if len(context.args) > 1 else '1h'
    
    # 2. Validate symbol
    if symbol not in SUPPORTED_SYMBOLS:
        await update.message.reply_text(f"❌ Unsupported symbol: {symbol}")
        return
    
    # 3. Generate signal
    await update.message.reply_text(f"🔍 Analyzing {symbol} on {timeframe}...")
    
    signal = ict_engine.generate_signal(
        symbol=symbol,
        timeframe=timeframe,
        exchange='binance'
    )
    
    # 4. Send result
    if signal:
        message = format_ict_signal(signal)
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text("⚠️ No valid signal found")
```

**Called By:** User command `/signal`  
**Calls:** `ict_engine.generate_signal()`, `format_ict_signal()`  
**Side Effects:** Generates Telegram response

---

### Position Management Functions (PR #7 - BROKEN ❌)

#### `async def open_position(signal)` - Line 11482
**Purpose:** Create new position in database for tracking

**Parameters:**
- `signal` (ICTSignal): Signal object with all details

**Returns:** None

**Expected Behavior:**
```python
async def open_position(signal):
    # Create position record
    position_manager.open_position(
        symbol=signal.symbol,
        timeframe=signal.timeframe,
        signal_type=signal.signal_type,
        entry_price=signal.entry_price,
        sl_price=signal.sl_price,
        tp_prices=[signal.tp1, signal.tp2, signal.tp3],
        confidence=signal.confidence,
        signal_data=signal.to_dict()
    )
```

**Current Status:** ❌ **BROKEN**  
- Function exists but doesn't create DB records
- `positions.db` has 0 records despite signals being sent
- Root cause: Unknown (requires debugging)

**Impact:**
- Checkpoint monitoring never triggers (depends on DB records)
- 80% TP alerts never sent (depends on position tracking)
- WIN/LOSS notifications don't work

---

#### `async def monitor_positions_job(bot_instance)` - Line 11877
**Purpose:** Monitor open positions every 60 seconds for TP/SL/checkpoint hits

**Parameters:**
- `bot_instance`: Telegram bot for sending alerts

**Returns:** None

**Workflow:**
```python
async def monitor_positions_job(bot_instance):
    # 1. Get all open positions
    positions = position_manager.get_open_positions()
    
    # 2. Check each position
    for position in positions:
        # Fetch current price
        current_price = await fetch_price(position['symbol'])
        
        # Calculate progress
        progress_pct = calculate_progress(
            entry=position['entry_price'],
            current=current_price,
            tp=position['tp1'],
            signal_type=position['signal_type']
        )
        
        # 3. Check for alerts
        if progress_pct >= 80 and not position['checkpoint_80_triggered']:
            await send_80_percent_alert(position, current_price, bot_instance)
            position_manager.update_checkpoint_triggered(position['id'], 80)
        
        # 4. Check TP hit
        if check_tp_hit(position, current_price):
            await send_win_alert(position, current_price, bot_instance)
            position_manager.close_position(position['id'], 'WIN', current_price)
        
        # 5. Check SL hit
        if check_sl_hit(position, current_price):
            await send_loss_alert(position, current_price, bot_instance)
            position_manager.close_position(position['id'], 'LOSS', current_price)
```

**Called By:** APScheduler (every 60 seconds)  
**Calls:** `position_manager.get_open_positions()`, `fetch_price()`, alert functions  
**Side Effects:** Sends Telegram alerts, updates database

**Current Status:** ❌ **NOT WORKING**  
- Reason: `get_open_positions()` returns empty list (DB has 0 records)
- Job runs but has nothing to monitor

---

### Command Handlers

#### `async def start_cmd(update, context)` - Line ~5450
**Purpose:** Welcome message and main menu

**Features:**
- Shows bot capabilities
- Lists available commands
- Displays keyboard with quick actions

---

#### `async def help_cmd(update, context)` - Line ~5500
**Purpose:** Complete command documentation

**Features:**
- Lists all 70+ commands
- Shows usage examples
- Categorizes by function (signals, stats, settings, positions)

---

#### `async def stats_cmd(update, context)` - Line 5642
**Purpose:** Display performance statistics

**Output:**
```
📊 PERFORMANCE STATISTICS

Total Signals: 342
Win Rate: 68.4% (234 wins, 108 losses)
Avg Confidence: 73.2%
Best Performing: BTC (75.3% win rate)
Current Week: 16 signals (12 wins)
```

**Data Source:** `bot_stats.json`  
**Called By:** User command `/stats`

---

#### `async def settings_cmd(update, context)` - Line ~9200
**Purpose:** User preference management

**Configurable Settings:**
- Default TP levels (TP1/TP2/TP3)
- Default SL buffer percentage
- Minimum confidence threshold
- Chart generation on/off
- Notification preferences

---

#### `async def position_list_cmd(update, context)` - Line ~9700
**Purpose:** Show all open positions

**Output:**
```
📈 OPEN POSITIONS (3)

1️⃣ BTC LONG (1h)
   Entry: $42,350
   Current: $43,120 (+1.82%)
   TP1: $43,650 (76% progress)
   SL: $41,800
   Status: 🟢 Approaching TP

2️⃣ ETH SHORT (4h)
   Entry: $2,280
   Current: $2,265 (+0.66%)
   TP1: $2,190 (24% progress)
   SL: $2,350
   Status: 🟡 In Progress
```

**Data Source:** `position_manager.get_open_positions()`  
**Current Status:** ❌ Always shows "No open positions" (DB is empty)

---

### Database Operations

#### `def load_active_signals()` - Line ~8200
**Purpose:** Load active signals from persistent JSON

**Returns:** `List[Dict]` - List of signal dictionaries

**File:** `sent_signals_cache.json`

---

#### `def save_active_signals(signals)` - Line ~8250
**Purpose:** Save active signals to JSON

**Parameters:**
- `signals` (List[Dict]): List of signal dictionaries

**File:** `sent_signals_cache.json`

---

#### `def load_stats()` - Line ~8300
**Purpose:** Load bot statistics

**Returns:** `Dict` - Statistics dictionary

**File:** `bot_stats.json`

---

#### `def save_stats(stats)` - Line ~8350
**Purpose:** Persist statistics to JSON

**Parameters:**
- `stats` (Dict): Statistics dictionary

**File:** `bot_stats.json`

---

### Message Formatting Functions

#### `def format_ict_signal(signal)` - Line ~8750
**Purpose:** Format ICTSignal into Telegram HTML message

**Parameters:**
- `signal` (ICTSignal): Signal object

**Returns:** `str` - HTML-formatted message

**Output Example:**
```html
<b>🚀 BTC STRONG_BUY SIGNAL</b>
⏰ Timeframe: 1h
💎 Confidence: 78.5%

📍 Entry Zone: $42,250 - $42,450
🎯 Take Profit:
   TP1: $43,650 (1:3.2 RR)
   TP2: $44,280 (1:4.8 RR)
   TP3: $45,120 (1:6.3 RR)
🛡️ Stop Loss: $41,800

✅ Bullish Reasons:
• Order Block Support at $42,300
• Bullish FVG filled at $42,150
• Liquidity sweep completed
• HTF bias BULLISH (4h + 1d aligned)
• Whale accumulation detected
• Displacement: 2.3% bullish candle
• MTF Confluence: 75% (3/4 TFs aligned)

⚠️ Warnings:
• Entry 2.1% from current price (wait for pullback)
```

---

#### `def format_standardized_signal(signal, source='AUTO')` - Line ~8850
**Purpose:** Format signal with source badge

**Parameters:**
- `signal` (ICTSignal): Signal object
- `source` (str): 'AUTO' or 'MANUAL'

**Features:**
- Adds source badge (🤖 AUTO or 👤 MANUAL)
- Color-codes confidence (🟢 ≥75%, 🟡 65-75%, 🔴 <65%)
- Consistent formatting across sources

---

## ict_signal_engine.py - Signal Generation
**Lines:** 5,563 | **Purpose:** ICT trading strategy implementation

### Main Entry Point

#### `def generate_signal(symbol, timeframe, exchange='binance')` - Line 642
**Purpose:** Unified 12-step ICT signal generation pipeline

**Parameters:**
- `symbol` (str): 'BTC', 'ETH', 'XRP', 'SOL', 'BNB', 'ADA'
- `timeframe` (str): '1h', '2h', '4h', '1d'
- `exchange` (str): 'binance' (default)

**Returns:** `ICTSignal | None` - Signal object or None if no valid signal

**12-Step Pipeline:**
```python
def generate_signal(symbol, timeframe, exchange='binance'):
    # Step 1: Fetch OHLCV data (500 candles)
    df = fetch_klines(symbol, timeframe, limit=500)
    
    # Step 2: Prepare DataFrame (add ATR, volume ratios)
    df = _prepare_dataframe(df)
    
    # Step 3: Get HTF bias (Higher Timeframe context)
    htf_bias = _get_htf_bias_with_fallback(symbol, timeframe, df)
    
    # Step 4: Detect all ICT components
    ict_components = _detect_ict_components(df, symbol, timeframe)
    
    # Step 5: Determine market bias (BULLISH/BEARISH/NEUTRAL)
    bias = _determine_market_bias(df, ict_components, htf_bias)
    
    # Step 6: Calculate MTF consensus (multi-timeframe alignment)
    mtf_consensus = _calculate_mtf_consensus(symbol, bias)
    if mtf_consensus < 50:  # Minimum 50% alignment required
        return None
    
    # Step 7: Identify entry setup type
    entry_setup = _identify_entry_setup(df, bias, ict_components)
    
    # Step 8: Calculate ICT-compliant entry zone
    entry_zone = _calculate_ict_compliant_entry_zone(
        df, bias, ict_components, entry_setup
    )
    if not entry_zone:
        return None
    
    # Step 9: Calculate Stop Loss
    sl_price = _calculate_sl_price(df, bias, ict_components)
    
    # Step 10: Validate SL position (must be outside Order Block)
    if not _validate_sl_position(sl_price, bias, ict_components):
        return None
    
    # Step 11: Calculate Take Profit levels (TP1/TP2/TP3)
    tp_prices = _calculate_tp_with_min_rr(
        entry_price=entry_zone['entry'],
        sl_price=sl_price,
        bias=bias,
        df=df
    )
    
    # Step 12: Calculate confidence (0-100%)
    confidence = _calculate_signal_confidence(ict_components, mtf_consensus, df)
    
    # Step 13: ML confidence adjustment (±20%)
    if ML_ENABLED:
        ml_adjustment = ml_predictor.predict(signal_features)
        confidence += ml_adjustment
    
    # Step 14: News sentiment filter
    if not _check_news_sentiment_before_signal(symbol):
        return None  # Block signal if negative news
    
    # Step 15: Create ICTSignal object
    signal = ICTSignal(
        symbol=symbol,
        timeframe=timeframe,
        signal_type=_determine_signal_type(bias, confidence),
        entry_price=entry_zone['entry'],
        sl_price=sl_price,
        tp1=tp_prices['tp1'],
        tp2=tp_prices['tp2'],
        tp3=tp_prices['tp3'],
        confidence=confidence,
        reasons=_generate_reasoning(ict_components, bias),
        warnings=_generate_warnings(entry_zone, ict_components),
        ict_components=ict_components
    )
    
    return signal
```

**Called By:** `auto_signal_job()`, `/signal` command  
**Calls:** 40+ helper functions (see subsections)  
**Side Effects:** API calls to Binance, cache reads/writes

---

### ICT Pattern Detection Functions

#### `def _detect_ict_components(df, symbol, timeframe)` - Line 1592
**Purpose:** Detect all 15+ ICT patterns in one pass

**Parameters:**
- `df` (DataFrame): OHLCV data with indicators
- `symbol` (str): Cryptocurrency symbol
- `timeframe` (str): Analysis timeframe

**Returns:** `Dict` - All detected patterns

**Detected Patterns:**
```python
{
    'order_blocks': [...],      # Bullish/Bearish OBs
    'fvgs': [...],              # Fair Value Gaps
    'whale_blocks': [...],      # Institutional blocks
    'liquidity_zones': [...],   # Liquidity pools
    'liquidity_sweeps': [...],  # Stop hunts
    'ilp_zones': [...],         # Internal Liquidity Pools
    'breaker_blocks': [...],    # Broken OBs
    'mitigation_blocks': [...], # Partially filled OBs
    'sibi_ssib_zones': [...],   # Imbalance zones
    'fibonacci_levels': [...],  # Fib retracements
    'luxalgo_sr': [...],        # Support/Resistance
    'structure_break': {...},   # BOS/CHOCH
    'displacement': {...}       # Large candles
}
```

**Implementation:**
```python
def _detect_ict_components(df, symbol, timeframe):
    components = {}
    
    # 1. Order Blocks (15% confidence weight)
    ob_detector = OrderBlockDetector()
    components['order_blocks'] = ob_detector.detect(df)
    
    # 2. Fair Value Gaps (10% weight)
    fvg_detector = FVGDetector()
    components['fvgs'] = fvg_detector.detect(df)
    
    # 3. Whale Blocks (25% weight - highest)
    whale_detector = WhaleDetector()
    components['whale_blocks'] = whale_detector.detect(df)
    
    # 4. Liquidity (20% weight)
    liquidity_mapper = LiquidityMap()
    components['liquidity_zones'] = liquidity_mapper.detect_zones(df)
    components['liquidity_sweeps'] = liquidity_mapper.detect_sweeps(df)
    
    # 5. ILP (Internal Liquidity Pools)
    ilp_detector = ILPDetector()
    components['ilp_zones'] = ilp_detector.detect(df)
    
    # 6. Breaker Blocks (5% weight)
    breaker_detector = BreakerBlockDetector()
    components['breaker_blocks'] = breaker_detector.detect(df)
    
    # 7. Mitigation Blocks
    components['mitigation_blocks'] = ob_detector.detect_mitigation_blocks(df)
    
    # 8. SIBI/SSIB (5% weight)
    sibi_detector = SIBISSIBDetector()
    components['sibi_ssib_zones'] = sibi_detector.detect(df)
    
    # 9. Structure Break (20% weight)
    components['structure_break'] = _check_structure_break(df)
    
    # 10. Displacement (bonus +10%)
    components['displacement'] = _check_displacement(df)
    
    # 11. Fibonacci (for TP calculation)
    fib_analyzer = FibonacciAnalyzer()
    components['fibonacci_levels'] = fib_analyzer.calculate_levels(df)
    
    # 12. LuxAlgo Support/Resistance
    luxalgo = LuxAlgoICTAnalysis()
    components['luxalgo_sr'] = luxalgo.get_sr_levels(df, symbol, timeframe)
    
    return components
```

**Called By:** `generate_signal()`  
**Calls:** All detector classes  
**Side Effects:** None (pure function)

---

### Entry Zone Calculation

#### `def _calculate_ict_compliant_entry_zone(df, bias, ict_components, entry_setup)` - Line 2299
**Purpose:** Calculate entry zone boundaries with ICT compliance

**Parameters:**
- `df` (DataFrame): OHLCV data
- `bias` (str): 'BULLISH' or 'BEARISH'
- `ict_components` (Dict): All detected patterns
- `entry_setup` (str): 'RETRACEMENT', 'RALLY', 'BREAKOUT'

**Returns:** `Dict | None`
```python
{
    'entry': 42350.0,        # Optimal entry price
    'zone_low': 42250.0,     # Zone bottom
    'zone_high': 42450.0,    # Zone top
    'distance_pct': 1.8,     # Distance from current price
    'distance_compliant': True,  # Within 0.5-3.0% range
    'reasoning': 'Order Block support + FVG confluence'
}
```

**Key Logic:**
```python
def _calculate_ict_compliant_entry_zone(df, bias, ict_components, entry_setup):
    current_price = df['close'].iloc[-1]
    
    # 1. Find optimal entry level based on patterns
    if bias == 'BULLISH':
        # Entry must be BELOW current price (wait for pullback)
        entry_candidates = []
        
        # Priority 1: Order Blocks
        for ob in ict_components['order_blocks']:
            if ob['type'] == 'bullish' and ob['bottom'] < current_price:
                entry_candidates.append({
                    'price': ob['bottom'],
                    'confidence': 15,
                    'reason': 'Order Block support'
                })
        
        # Priority 2: FVG midpoint
        for fvg in ict_components['fvgs']:
            if fvg['type'] == 'bullish' and fvg['midpoint'] < current_price:
                entry_candidates.append({
                    'price': fvg['midpoint'],
                    'confidence': 10,
                    'reason': 'FVG confluence'
                })
        
        # Priority 3: Liquidity zones
        for liq in ict_components['liquidity_zones']:
            if liq['type'] == 'bullish' and liq['price'] < current_price:
                entry_candidates.append({
                    'price': liq['price'],
                    'confidence': 20,
                    'reason': 'Liquidity pool'
                })
        
        # 2. Select best entry (highest confluence)
        if not entry_candidates:
            return None
        
        best_entry = max(entry_candidates, key=lambda x: x['confidence'])
        entry_price = best_entry['price']
        
        # 3. Calculate zone boundaries (±0.3% from entry)
        zone_low = entry_price * 0.997
        zone_high = entry_price * 1.003
        
    else:  # BEARISH
        # Entry must be ABOVE current price (wait for rally)
        # ... similar logic, inverted
        pass
    
    # 4. Validate distance from current price
    distance_pct = abs((entry_price - current_price) / current_price) * 100
    distance_compliant = 0.5 <= distance_pct <= 3.0
    
    # 5. Return entry zone
    return {
        'entry': entry_price,
        'zone_low': zone_low,
        'zone_high': zone_high,
        'distance_pct': distance_pct,
        'distance_compliant': distance_compliant,
        'reasoning': best_entry['reason']
    }
```

**Validation Rules:**
- **BULLISH:** Entry < Current Price (Line 2311-2313)
- **BEARISH:** Entry > Current Price (Line 2307-2309)
- **Optimal Distance:** 0.5% - 3.0% from current price (Line 2316-2319)
- **Soft Constraint:** Zones beyond 3% flagged but accepted (Line 2304)

**Called By:** `generate_signal()`  
**Calls:** None (uses pre-detected patterns)  
**Side Effects:** None

---

### Stop Loss & Take Profit

#### `def _calculate_sl_price(df, bias, ict_components)` - Line 2798
**Purpose:** Calculate ICT-compliant stop loss

**Parameters:**
- `df` (DataFrame): OHLCV data
- `bias` (str): 'BULLISH' or 'BEARISH'
- `ict_components` (Dict): Detected patterns

**Returns:** `float` - Stop loss price

**ICT Compliance Rules:**
```python
def _calculate_sl_price(df, bias, ict_components):
    if bias == 'BULLISH':
        # SL must be BELOW Order Block bottom
        ob_bottom = ict_components['order_blocks'][0]['bottom']
        
        # Add buffer (0.2-0.3%)
        sl_price = ob_bottom * 0.997  # -0.3% buffer
        
        # Minimum distance from entry: 3%
        entry_price = ict_components['entry_price']
        min_sl = entry_price * 0.97
        
        return min(sl_price, min_sl)
    
    else:  # BEARISH
        # SL must be ABOVE Order Block top
        ob_top = ict_components['order_blocks'][0]['top']
        sl_price = ob_top * 1.003  # +0.3% buffer
        
        entry_price = ict_components['entry_price']
        min_sl = entry_price * 1.03
        
        return max(sl_price, min_sl)
```

**Key Rules:**
- **BULLISH:** SL < OB bottom (Line 2813-2835)
- **BEARISH:** SL > OB top (Line 2837-2860)
- **Minimum Distance:** 3% from entry (Line 2831, 2856)
- **Buffer:** 0.2-0.3% beyond OB boundary

**Called By:** `generate_signal()`  
**Calls:** None  
**Side Effects:** None

---

#### `def _calculate_tp_with_min_rr(entry_price, sl_price, bias, df)` - Line 2696
**Purpose:** Calculate TP levels with minimum 1:3 risk/reward

**Parameters:**
- `entry_price` (float): Entry price
- `sl_price` (float): Stop loss price
- `bias` (str): 'BULLISH' or 'BEARISH'
- `df` (DataFrame): OHLCV data (for Fibonacci)

**Returns:** `Dict`
```python
{
    'tp1': 43650.0,  # 1:3 RR (mandatory)
    'tp2': 44280.0,  # 1:2 RR (recommended)
    'tp3': 45120.0   # 1:5 RR (stretch target)
}
```

**Implementation:**
```python
def _calculate_tp_with_min_rr(entry_price, sl_price, bias, df):
    # Calculate risk distance
    risk = abs(entry_price - sl_price)
    
    if bias == 'BULLISH':
        # TP = Entry + (Risk × RR)
        tp1 = entry_price + (risk * 3.0)  # 1:3 RR minimum
        tp2 = entry_price + (risk * 2.0)  # 1:2 RR
        tp3 = entry_price + (risk * 5.0)  # 1:5 RR
    else:  # BEARISH
        tp1 = entry_price - (risk * 3.0)
        tp2 = entry_price - (risk * 2.0)
        tp3 = entry_price - (risk * 5.0)
    
    # Optional: Align with Fibonacci levels
    fib_levels = _get_fibonacci_levels(df)
    tp1 = _snap_to_fibonacci(tp1, fib_levels)
    tp2 = _snap_to_fibonacci(tp2, fib_levels)
    tp3 = _snap_to_fibonacci(tp3, fib_levels)
    
    return {'tp1': tp1, 'tp2': tp2, 'tp3': tp3}
```

**Minimum Requirements:**
- **TP1:** 1:3 RR mandatory (Line 2701)
- **TP2:** 1:2 RR recommended
- **TP3:** 1:5 RR for scaling out

**Called By:** `generate_signal()`  
**Calls:** `_get_fibonacci_levels()`, `_snap_to_fibonacci()`  
**Side Effects:** None

---

### Confidence & Strength

#### `def _calculate_signal_confidence(ict_components, mtf_consensus, df)` - Line 2983
**Purpose:** Calculate confidence score (0-100%) based on ICT patterns

**Parameters:**
- `ict_components` (Dict): All detected patterns
- `mtf_consensus` (float): MTF alignment percentage
- `df` (DataFrame): OHLCV data

**Returns:** `float` - Confidence score (0-100)

**Confidence Breakdown:**
```python
def _calculate_signal_confidence(ict_components, mtf_consensus, df):
    confidence = 0.0
    
    # 1. Structure Break (20%)
    if ict_components.get('structure_break'):
        confidence += 20
    
    # 2. Whale Blocks (25% - highest weight)
    if ict_components.get('whale_blocks'):
        num_whale = len(ict_components['whale_blocks'])
        confidence += min(25, num_whale * 12.5)
    
    # 3. Liquidity Zones (20%)
    if ict_components.get('liquidity_zones'):
        num_liq = len(ict_components['liquidity_zones'])
        confidence += min(20, num_liq * 10)
    
    # 4. Order Blocks (15%)
    if ict_components.get('order_blocks'):
        num_ob = len(ict_components['order_blocks'])
        confidence += min(15, num_ob * 7.5)
    
    # 5. FVGs (10%)
    if ict_components.get('fvgs'):
        num_fvg = len(ict_components['fvgs'])
        confidence += min(10, num_fvg * 5)
    
    # 6. MTF Confluence (10%)
    mtf_score = (mtf_consensus / 100) * 10
    confidence += mtf_score
    
    # 7. Displacement Bonus (+10%)
    if ict_components.get('displacement', {}).get('detected'):
        confidence += 10
    
    # 8. Breaker Block Bonus (+5%)
    if ict_components.get('breaker_blocks'):
        confidence += 5
    
    # 9. SIBI/SSIB Bonus (+5%)
    if ict_components.get('sibi_ssib_zones'):
        confidence += 5
    
    # 10. Cap at 100%
    return min(100.0, confidence)
```

**Weighting:**
- Structure Break: 20% (Line 2996-2997)
- Whale Blocks: 25% (Line 2999-3003) **← Highest**
- Liquidity Zones: 20% (Line 3005-3009)
- Order Blocks: 15% (Line 3011-3015)
- FVGs: 10% (Line 3017-3021)
- MTF Confluence: 10% (Line 3023-3027)
- Displacement: +10 bonus (Line 3047-3049)

**Called By:** `generate_signal()`  
**Calls:** None  
**Side Effects:** None

---

### Multi-Timeframe Analysis

#### `def _calculate_mtf_consensus(symbol, bias)` - Line 1840
**Purpose:** Calculate multi-timeframe consensus percentage

**Parameters:**
- `symbol` (str): Cryptocurrency symbol
- `bias` (str): Current timeframe bias

**Returns:** `float` - Consensus percentage (0-100)

**Algorithm:**
```python
def _calculate_mtf_consensus(symbol, bias):
    timeframes = ['1h', '2h', '4h', '1d']
    aligned = 0
    conflicting = 0
    
    for tf in timeframes:
        # Get bias for each timeframe
        tf_bias = _calculate_pure_ict_bias_for_tf(symbol, tf)
        
        if tf_bias == 'NEUTRAL' or tf_bias == 'RANGING':
            continue  # Skip neutral TFs
        
        if tf_bias == bias:
            aligned += 1
        else:
            conflicting += 1
    
    # Consensus = aligned / (aligned + conflicting)
    total = aligned + conflicting
    if total == 0:
        return 0.0
    
    consensus = (aligned / total) * 100
    return consensus
```

**Example:**
- 1h: BULLISH ✅
- 2h: BULLISH ✅
- 4h: NEUTRAL (skipped)
- 1d: BEARISH ❌
- **Consensus:** 2 aligned / (2 aligned + 1 conflicting) = 66.7%

**Minimum Threshold:** 50% required for signal (Line 1345)

**Called By:** `generate_signal()`  
**Calls:** `_calculate_pure_ict_bias_for_tf()`  
**Side Effects:** API calls to fetch other timeframes

---

## position_manager.py - Position Lifecycle
**Lines:** 718 | **Purpose:** Position tracking with database operations

### Class: PositionManager

#### `def __init__(db_path)` - Line 61
**Purpose:** Initialize position manager with database

**Parameters:**
- `db_path` (str): Path to SQLite database (default: `positions.db`)

**Responsibilities:**
- Ensure database exists
- Create tables if missing
- Setup logging

---

#### `def open_position(...)` - Line 145
**Purpose:** Create new position in database

**Parameters:**
```python
def open_position(
    symbol: str,            # 'BTC', 'ETH', etc.
    timeframe: str,         # '1h', '2h', '4h', '1d'
    signal_type: str,       # 'BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL'
    entry_price: float,     # Entry price
    sl_price: float,        # Stop loss price
    tp_prices: List[float], # [TP1, TP2, TP3]
    confidence: float,      # 0-100
    signal_data: Dict       # Full signal object
) -> int:                   # Returns position_id
```

**Database Record:**
```sql
INSERT INTO open_positions (
    symbol, timeframe, signal_type, entry_price, sl_price,
    tp1, tp2, tp3, confidence, signal_data,
    opened_at, status
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
```

**Returns:** `int` - Position ID

**Called By:** `bot.open_position()`  
**Calls:** Database INSERT  
**Side Effects:** Creates DB record

---

#### `def get_open_positions()` - Line 205
**Purpose:** Retrieve all open positions

**Returns:** `List[Dict]` - List of position dictionaries

**Query:**
```sql
SELECT * FROM open_positions 
WHERE status = 'OPEN'
ORDER BY opened_at DESC
```

**Called By:** `monitor_positions_job()`, `/position_list` command  
**Calls:** Database SELECT  
**Side Effects:** None (read-only)

---

#### `def update_checkpoint_triggered(position_id, checkpoint)` - Line 283
**Purpose:** Mark checkpoint as triggered

**Parameters:**
- `position_id` (int): Position ID
- `checkpoint` (int): 25, 50, 75, or 80

**Database Update:**
```sql
UPDATE open_positions 
SET checkpoint_{checkpoint}_triggered = 1,
    checkpoint_{checkpoint}_at = ?
WHERE id = ?
```

**Called By:** `monitor_positions_job()`  
**Calls:** Database UPDATE  
**Side Effects:** Updates DB record

---

#### `def close_position(position_id, outcome, close_price)` - Line 428
**Purpose:** Close position and record outcome

**Parameters:**
- `position_id` (int): Position ID
- `outcome` (str): 'WIN', 'LOSS', 'BREAKEVEN'
- `close_price` (float): Final exit price

**Workflow:**
```python
def close_position(position_id, outcome, close_price):
    # 1. Calculate P&L
    position = get_position_by_id(position_id)
    pnl_pct = calculate_pnl(position, close_price)
    
    # 2. Move to history
    INSERT INTO position_history (
        symbol, timeframe, signal_type, entry_price, close_price,
        sl_price, tp1, tp2, tp3, confidence, outcome, pnl_pct,
        opened_at, closed_at
    )
    SELECT * FROM open_positions WHERE id = position_id
    
    # 3. Delete from open positions
    DELETE FROM open_positions WHERE id = position_id
    
    # 4. Return final record
    return position_history_record
```

**Called By:** `monitor_positions_job()` when TP/SL hit  
**Calls:** Database INSERT + DELETE  
**Side Effects:** Moves record to history

---

#### `def get_position_stats()` - Line 627
**Purpose:** Get aggregate statistics

**Returns:** `Dict`
```python
{
    'total_positions': 234,
    'total_wins': 159,
    'total_losses': 75,
    'win_rate': 67.9,
    'avg_pnl_pct': 4.2,
    'best_trade': 18.5,
    'worst_trade': -3.1,
    'total_pnl': 983.2
}
```

**Query:**
```sql
SELECT 
    COUNT(*) as total,
    SUM(CASE WHEN outcome = 'WIN' THEN 1 ELSE 0 END) as wins,
    SUM(CASE WHEN outcome = 'LOSS' THEN 1 ELSE 0 END) as losses,
    AVG(pnl_pct) as avg_pnl,
    MAX(pnl_pct) as best,
    MIN(pnl_pct) as worst
FROM position_history
```

**Called By:** `/stats` command, daily reports  
**Calls:** Database SELECT  
**Side Effects:** None (read-only)

---

## real_time_monitor.py - 24/7 Monitoring
**Lines:** 895 | **Purpose:** Continuous position monitoring with alerts

### Class: RealTimeMonitor

#### `def __init__(bot, position_manager, ict_engine)` - Line 39
**Purpose:** Initialize real-time monitor

**Parameters:**
- `bot`: Telegram bot instance
- `position_manager`: PositionManager instance
- `ict_engine`: ICTSignalEngine instance

**Setup:**
- 30-second monitoring interval
- 80% TP alert threshold
- Multi-stage alerts (HALFWAY, APPROACHING, FINAL_PHASE)

---

#### `async def start_monitoring()` - Line 138
**Purpose:** Start 24/7 monitoring loop

**Workflow:**
```python
async def start_monitoring():
    while True:
        try:
            # 1. Get all open positions
            positions = position_manager.get_open_positions()
            
            # 2. Check each position
            for position in positions:
                await _check_position(position)
            
            # 3. Wait 30 seconds
            await asyncio.sleep(30)
            
        except Exception as e:
            logger.error(f"Monitoring error: {e}")
            await asyncio.sleep(60)  # Longer delay on error
```

**Called By:** `main()` at startup  
**Calls:** `_check_position()`  
**Side Effects:** Continuous loop, API calls

---

#### `async def _check_position(position)` - Line 157
**Purpose:** Check single position for alerts

**Workflow:**
```python
async def _check_position(position):
    # 1. Fetch current price
    current_price = await _fetch_current_price(position['symbol'])
    
    # 2. Calculate progress
    progress_pct = _calculate_progress(
        entry=position['entry_price'],
        current=current_price,
        tp=position['tp1'],
        signal_type=position['signal_type']
    )
    
    # 3. Check for 80% alert
    if progress_pct >= 80 and not position['checkpoint_80_triggered']:
        await _send_80_percent_alert(position, current_price, progress_pct)
        position_manager.update_checkpoint_triggered(position['id'], 80)
    
    # 4. Check multi-stage alerts (50%, 75%, 85%)
    if MULTI_STAGE_ENABLED:
        await _check_stage_alerts(position, current_price, progress_pct)
    
    # 5. Check TP hit
    if _check_tp_hit(position, current_price):
        await _send_win_alert(position, current_price)
        position_manager.close_position(position['id'], 'WIN', current_price)
    
    # 6. Check SL hit
    if _check_sl_hit(position, current_price):
        await _send_loss_alert(position, current_price)
        position_manager.close_position(position['id'], 'LOSS', current_price)
```

**Called By:** `start_monitoring()`  
**Calls:** Price fetch, alert functions, position_manager  
**Side Effects:** Sends Telegram alerts, updates DB

---

#### `async def _send_80_percent_alert(position, current_price, progress_pct)` - Line 338
**Purpose:** Send 80% TP alert with re-analysis

**Message Example:**
```
🎯 80% TP ALERT - BTC LONG

Entry: $42,350
Current: $43,580 (+2.90%)
Progress: 84% to TP1

📊 RE-ANALYSIS:
✅ Bullish structure still intact
⚠️ Approaching resistance at $43,650
💡 Recommendation: Consider partial close (50%)

Risk Level: LOW
HTF Bias: BULLISH
```

**Re-analysis:**
```python
async def _send_80_percent_alert(position, current_price, progress_pct):
    # 1. Re-analyze market state
    recommendation = await ict_engine.reanalyze_at_80_percent(
        symbol=position['symbol'],
        timeframe=position['timeframe'],
        signal_type=position['signal_type'],
        entry_price=position['entry_price'],
        current_price=current_price
    )
    
    # 2. Format message
    message = f"""
🎯 80% TP ALERT - {position['symbol']} {position['signal_type']}

Entry: ${position['entry_price']:,.2f}
Current: ${current_price:,.2f} ({progress_pct:.1f}%)
Progress: {progress_pct:.0f}% to TP1

📊 RE-ANALYSIS:
{recommendation['summary']}

💡 Recommendation: {recommendation['action']}
Risk Level: {recommendation['risk_level']}
HTF Bias: {recommendation['htf_bias']}
"""
    
    # 3. Send alert
    await bot.send_message(OWNER_CHAT_ID, message, parse_mode='HTML')
```

**Called By:** `_check_position()`  
**Calls:** `ict_engine.reanalyze_at_80_percent()`  
**Side Effects:** Sends Telegram message

---

#### `async def _send_win_alert(position, close_price)` - Line 432
**Purpose:** Send WIN notification

**Message Example:**
```
✅ WIN - BTC LONG

Entry: $42,350
Exit: $43,680 (TP1 hit)
Profit: +3.14% (+1:3.2 RR)

Duration: 4h 23m
Confidence: 78.5%
Timeframe: 1h
```

**Called By:** `_check_position()` when TP hit  
**Calls:** `position_manager.close_position()`  
**Side Effects:** Sends Telegram message, closes position

---

#### `async def _send_loss_alert(position, close_price)` - Line 477
**Purpose:** Send LOSS notification

**Message Example:**
```
❌ LOSS - BTC LONG

Entry: $42,350
Exit: $41,780 (SL hit)
Loss: -1.35% (-1:1 RR)

Duration: 2h 15m
Confidence: 78.5%
Timeframe: 1h
```

**Called By:** `_check_position()` when SL hit  
**Calls:** `position_manager.close_position()`  
**Side Effects:** Sends Telegram message, closes position

---

## chart_generator.py - Chart Visualization
**Lines:** 847 | **Purpose:** Generate annotated ICT charts

### Class: ChartGenerator

#### `def __init__(style='professional')` - Line 54
**Purpose:** Initialize chart generator

**Parameters:**
- `style` (str): 'professional', 'dark', or 'light'

**Features:**
- matplotlib-based rendering
- PNG output
- Pattern annotations
- Color-coded zones

---

#### `def generate(signal, df=None, output_path=None)` - Line 66
**Purpose:** Generate chart for signal

**Parameters:**
- `signal` (ICTSignal): Signal object with patterns
- `df` (DataFrame): OHLCV data (optional, fetched if None)
- `output_path` (str): Save path (optional)

**Returns:** `str` - Path to generated PNG

**Chart Elements:**
```python
def generate(signal, df=None, output_path=None):
    # 1. Fetch data if not provided
    if df is None:
        df = fetch_klines(signal.symbol, signal.timeframe, limit=100)
    
    # 2. Create figure
    fig, (ax_price, ax_volume) = plt.subplots(2, 1, figsize=(14, 10))
    
    # 3. Plot candlesticks
    _plot_candlesticks(ax_price, df)
    
    # 4. Plot ICT patterns
    if signal.ict_components.get('order_blocks'):
        _plot_order_blocks_enhanced(ax_price, signal.ict_components['order_blocks'], df)
    
    if signal.ict_components.get('fvgs'):
        _plot_fvg_zones(ax_price, signal.ict_components['fvgs'])
    
    if signal.ict_components.get('whale_blocks'):
        _plot_whale_blocks_enhanced(ax_price, signal.ict_components['whale_blocks'], df)
    
    if signal.ict_components.get('liquidity_zones'):
        _plot_liquidity_zones_enhanced(ax_price, signal.ict_components['liquidity_zones'], df)
    
    if signal.ict_components.get('breaker_blocks'):
        _plot_breaker_blocks_enhanced(ax_price, signal.ict_components['breaker_blocks'], df)
    
    # 5. Plot entry/TP/SL
    _plot_entry_exit(ax_price, signal)
    
    # 6. Plot volume
    _plot_volume(ax_volume, df)
    
    # 7. Add info box
    _add_info_box(ax_price, signal)
    
    # 8. Apply styling
    _apply_styling(ax_price, ax_volume, df)
    
    # 9. Save
    if output_path is None:
        output_path = f"charts/{signal.symbol}_{signal.timeframe}_{int(time.time())}.png"
    
    plt.savefig(output_path, dpi=150, bbox_inches='tight')
    plt.close()
    
    return output_path
```

**Called By:** `send_alert_signal()`  
**Calls:** All plotting functions  
**Side Effects:** Creates PNG file

---

#### `def _plot_order_blocks_enhanced(ax, order_blocks, df)` - Line 514
**Purpose:** Plot order blocks with labels

**Features:**
- Bullish OBs: Green rectangles
- Bearish OBs: Red rectangles
- Confidence labels
- Mitigation status

---

#### `def _plot_fvg_zones(ax, fvg_zones)` - Line 354
**Purpose:** Plot Fair Value Gaps

**Features:**
- Bullish FVGs: Blue shaded areas
- Bearish FVGs: Orange shaded areas
- Gap size annotations

---

#### `def _plot_liquidity_zones_enhanced(ax, liquidity_zones, df)` - Line 710
**Purpose:** Plot liquidity pools

**Features:**
- Horizontal lines at liquidity levels
- Sweep markers (if swept)
- Strength indicators

---

#### `def _plot_entry_exit(ax, signal)` - Line 466
**Purpose:** Plot entry, TP, and SL levels

**Features:**
```python
def _plot_entry_exit(ax, signal):
    # Entry zone (green/red shaded)
    ax.axhspan(
        signal.entry_zone_low, 
        signal.entry_zone_high,
        alpha=0.2,
        color='green' if signal.signal_type == 'BUY' else 'red',
        label='Entry Zone'
    )
    
    # TP levels (dashed green)
    ax.axhline(signal.tp1, color='green', linestyle='--', linewidth=1, label='TP1')
    ax.axhline(signal.tp2, color='green', linestyle='--', linewidth=0.8, label='TP2')
    ax.axhline(signal.tp3, color='green', linestyle='--', linewidth=0.6, label='TP3')
    
    # SL level (dashed red)
    ax.axhline(signal.sl_price, color='red', linestyle='--', linewidth=1.5, label='SL')
```

---

## Cross-Reference Guide

### Signal Flow
```
User Command /signal BTC
    ↓
bot.signal_cmd() [Line 5800]
    ↓
ict_engine.generate_signal() [Line 642]
    ↓
ict_engine._detect_ict_components() [Line 1592]
    ↓
ict_engine._calculate_signal_confidence() [Line 2983]
    ↓
Return ICTSignal object
    ↓
bot.format_ict_signal() [Line 8750]
    ↓
chart_generator.generate() [Line 66]
    ↓
Send Telegram message with chart
```

### Auto Signal Flow
```
APScheduler triggers every 1h/2h/4h/24h
    ↓
bot.auto_signal_job() [Line 11258]
    ↓
For each symbol (BTC, ETH, XRP, SOL, BNB, ADA):
    ↓
    ict_engine.generate_signal() [Line 642]
        ↓
    Validate confidence ≥ 65%
        ↓
    Check deduplication cache
        ↓
    bot.send_alert_signal() [Line 11014]
        ↓
    bot.open_position() [Line 11482] ← ❌ BROKEN
        ↓
    position_manager.open_position() [Line 145] ← Never receives data
```

### Position Monitoring Flow (NOT WORKING ❌)
```
APScheduler triggers every 60 seconds
    ↓
bot.monitor_positions_job() [Line 11877]
    ↓
position_manager.get_open_positions() [Line 205]
    ↓
Returns empty list [] ← DB has 0 records
    ↓
Nothing to monitor ← STOPS HERE
```

**Expected Flow (if working):**
```
position_manager.get_open_positions()
    ↓
For each position:
    ↓
    real_time_monitor._check_position() [Line 157]
        ↓
    Fetch current price
        ↓
    Calculate progress %
        ↓
    Check if progress ≥ 80%
        ↓
        real_time_monitor._send_80_percent_alert() [Line 338]
            ↓
        position_manager.update_checkpoint_triggered() [Line 283]
    ↓
    Check if TP hit
        ↓
        real_time_monitor._send_win_alert() [Line 432]
            ↓
        position_manager.close_position() [Line 428]
    ↓
    Check if SL hit
        ↓
        real_time_monitor._send_loss_alert() [Line 477]
            ↓
        position_manager.close_position() [Line 428]
```

### Database Operations
```
Signal Generation
    ↓
bot.open_position() [Line 11482]
    ↓
position_manager.open_position() [Line 145]
    ↓
INSERT INTO open_positions (...)
    ↓
Returns position_id
    ↓
[CURRENTLY BROKEN - No records created ❌]

Monitoring Loop (every 60s)
    ↓
position_manager.get_open_positions() [Line 205]
    ↓
SELECT * FROM open_positions WHERE status = 'OPEN'
    ↓
Returns [] (empty because INSERT failed)

Checkpoint Update
    ↓
position_manager.update_checkpoint_triggered() [Line 283]
    ↓
UPDATE open_positions SET checkpoint_80_triggered = 1

Position Close
    ↓
position_manager.close_position() [Line 428]
    ↓
INSERT INTO position_history (...)
DELETE FROM open_positions WHERE id = ?
```

---

## Function Call Matrix

| Caller | Function Called | Purpose |
|--------|-----------------|---------|
| `main()` | `auto_signal_job()` | Schedule signal generation |
| `main()` | `monitor_positions_job()` | Schedule position monitoring |
| `auto_signal_job()` | `generate_signal()` | Generate ICT signal |
| `auto_signal_job()` | `send_alert_signal()` | Broadcast signal |
| `auto_signal_job()` | `open_position()` | Track position ❌ |
| `generate_signal()` | `_detect_ict_components()` | Find all patterns |
| `generate_signal()` | `_calculate_ict_compliant_entry_zone()` | Calculate entry |
| `generate_signal()` | `_calculate_sl_price()` | Calculate SL |
| `generate_signal()` | `_calculate_tp_with_min_rr()` | Calculate TPs |
| `generate_signal()` | `_calculate_signal_confidence()` | Score confidence |
| `send_alert_signal()` | `format_ict_signal()` | Format message |
| `send_alert_signal()` | `chart_generator.generate()` | Create chart |
| `monitor_positions_job()` | `position_manager.get_open_positions()` | Get active positions |
| `monitor_positions_job()` | `real_time_monitor._check_position()` | Check TP/SL |
| `_check_position()` | `_send_80_percent_alert()` | 80% alert |
| `_check_position()` | `_send_win_alert()` | WIN notification |
| `_check_position()` | `_send_loss_alert()` | LOSS notification |
| `_send_80_percent_alert()` | `ict_engine.reanalyze_at_80_percent()` | Re-analyze market |

---

## Known Issues Summary

### ❌ Position Tracking Broken
**Functions Affected:**
- `bot.open_position()` (Line 11482)
- `position_manager.open_position()` (Line 145)

**Symptoms:**
- No records in `positions.db`
- `get_open_positions()` always returns `[]`
- Monitoring loop has nothing to monitor

**Impact:**
- No checkpoint alerts
- No 80% TP alerts
- No WIN/LOSS notifications

---

### ✅ Working Functions
- All signal generation (16/day average)
- ICT pattern detection (all 15+ patterns)
- Confidence scoring (0-100%)
- Telegram message delivery
- Chart generation
- Deduplication
- Command handlers
- Statistics tracking

---

**End of CORE_MODULES_REFERENCE.md**
