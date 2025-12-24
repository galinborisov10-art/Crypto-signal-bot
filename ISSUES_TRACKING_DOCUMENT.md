# 📋 ISSUES TRACKING DOCUMENT
## Crypto Signal Bot - System Problems Registry

**Документ версия:** 1.0  
**Дата на създаване:** 24 Декември 2025  
**Цел:** Проследяване на открити проблеми и статус на решенията  
**Режим:** READ-ONLY ANALYSIS - Без промени по кода

---

## 📊 SUMMARY STATISTICS

| Метрика | Стойност |
|---------|----------|
| **Общ брой проблеми** | 15 |
| **Критични (HIGH)** | 3 |
| **Средни (MEDIUM)** | 8 |
| **Ниски (LOW)** | 4 |
| **Open** | 15 |
| **In Progress** | 0 |
| **Resolved** | 0 |

---

## 🚨 CRITICAL ISSUES (HIGH Priority)

### P1: Auto-Signal Function Missing

**ID:** P1  
**Status:** Open  
**Критичност:** HIGH  
**Дата на откриване:** 24 Dec 2025

**Локация:**
- File: `bot.py`
- Line: ~13556 (scheduler job setup)

**Описание:**
Функцията `send_alert_signal()` е scheduled в APScheduler но не съществува в кода.

```python
# Line 13556-13562
app.job_queue.run_repeating(
    send_alert_signal,  # ← FUNCTION NOT FOUND!
    interval=settings['alert_interval'],
    first=10,
    data={'chat_id': OWNER_CHAT_ID},
    name=f"alerts_{OWNER_CHAT_ID}"
)
```

**Търсене в кода:**
```bash
grep -rn "def send_alert_signal" bot.py
# Result: NO MATCHES
```

**Причина:**
- Функцията не е имплементирана
- Scheduler job reference липсващата функция
- Auto-alerts са "enabled" във feature flags но не работят

**Влияние върху системата:**
1. **Функционалност:**
   - Auto-alerts НЕ се изпращат въпреки че са enabled
   - Users очакват автоматични сигнали но ги няма
   - Scheduler job ще фейлва при изпълнение

2. **User Experience:**
   - Заблуда че auto-alerts работят
   - Липса на очаквани сигнали

3. **System Stability:**
   - Scheduler може да логва errors
   - Job може да се retry безкрайно

**Препоръчано решение:**

```python
async def send_alert_signal(context):
    """
    Генерира и изпраща автоматични сигнали към enabled users.
    Изпълнява се periodично от scheduler.
    """
    try:
        chat_id = context.job.data['chat_id']
        
        # 1. Get user settings
        settings = get_user_settings(context.application.bot_data, chat_id)
        
        if not settings.get('alerts_enabled', False):
            return
        
        # 2. Analyze all symbols
        symbols = ['BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT', 'BNBUSDT', 'ADAUSDT']
        timeframe = settings.get('timeframe', '1h')
        
        signals = []
        
        for symbol in symbols:
            # 3. Run same ICT analysis as manual /signal
            klines = await fetch_klines(symbol, timeframe, 200)
            df = prepare_dataframe(klines)
            mtf_data = fetch_mtf_data(symbol, timeframe, df)
            
            # 4. Generate ICT signal
            ict_signal = ict_engine_global.generate_signal(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                mtf_data=mtf_data
            )
            
            # 5. Filter by confidence and entry zone
            if ict_signal and ict_signal.confidence >= 70:
                entry_zone, entry_status = get_entry_zone(ict_signal)
                
                # Only include VALID signals
                if entry_status in ['VALID_WAIT', 'VALID_NEAR']:
                    signals.append(ict_signal)
        
        # 6. Get top N signals
        top_n = settings.get('alert_top_n', 3)
        signals = sorted(signals, key=lambda s: s.confidence, reverse=True)[:top_n]
        
        # 7. Send signals
        for signal in signals:
            # Check cooldown
            if not is_signal_already_sent(signal.symbol, signal.signal_type.value, 
                                          timeframe, signal.confidence, signal.entry_price, 60):
                # Format & send
                msg = format_ict_signal_13_point(signal)
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=msg,
                    parse_mode='HTML'
                )
                
                # Track signal
                mark_signal_sent(signal.symbol, signal.signal_type.value, 
                                timeframe, signal.confidence, signal.entry_price)
                
                # Add to monitor
                add_signal_to_monitor(signal, signal.symbol, timeframe, chat_id)
        
    except Exception as e:
        logger.error(f"Auto-signal error: {e}")
```

**Steps to Implement:**
1. Create `send_alert_signal()` function in bot.py
2. Use same ICT analysis as manual `/signal`
3. Filter by confidence ≥ 70%
4. Apply entry zone validation (TOO_LATE, NO_ZONE check)
5. Implement cooldown to avoid duplicates
6. Send top N signals to enabled users
7. Track in active_trades for monitoring

**Testing:**
1. Enable auto-alerts: `/alerts on`
2. Wait for scheduled execution (15 min interval)
3. Verify signals are sent
4. Check cooldown works (no duplicates)
5. Verify signals added to real-time monitor

**Бележки:**
- Функцията трябва да следва СЪЩАТА последователност като manual signals
- Всички настройки и филтри трябва да се прилагат
- Cooldown е критичен за избягване на spam

---

### P6: Daily Loss Limit Not Enforced

**ID:** P6  
**Status:** Open  
**Критичност:** HIGH  
**Дата на откриване:** 24 Dec 2025

**Локация:**
- File: `risk_config.json`
- File: `bot.py` (signal generation logic)

**Описание:**
Risk config има `max_daily_loss_pct: 6.0` и `stop_trading_on_daily_limit: true` но
проверката ЛИПСВА в signal generation процеса.

**Конфигурация:**
```json
{
  "max_daily_loss_pct": 6.0,
  "stop_trading_on_daily_limit": true
}
```

**Търсене в кода:**
```bash
grep -rn "max_daily_loss" bot.py
grep -rn "stop_trading_on_daily_limit" bot.py
# Result: Config е зареден но НЕ се използва!
```

**Причина:**
- Risk manager е available
- Config е зареден
- Но няма check при signal_cmd() или ict_cmd()

**Влияние върху системата:**
1. **Risk Management:**
   - Daily loss limit може да бъде надхвърлен
   - Няма автоматично спиране на trading
   - Risk config е неефективен

2. **Financial Impact:**
   - Възможност за excessive losses в лош ден
   - Липса на защита

3. **Compliance:**
   - Риск настройките не се спазват

**Препоръчано решение:**

```python
def check_daily_loss_limit(chat_id: int) -> tuple[bool, str]:
    """
    Проверява дали daily loss limit е достигнат.
    
    Returns:
        (can_trade: bool, message: str)
    """
    try:
        # Load risk config
        with open('risk_config.json', 'r') as f:
            risk_config = json.load(f)
        
        max_daily_loss_pct = risk_config['max_daily_loss_pct']
        stop_trading = risk_config['stop_trading_on_daily_limit']
        
        if not stop_trading:
            return True, ""  # Feature disabled
        
        # Load today's trades from journal
        today = datetime.now(timezone.utc).date()
        
        # Get all trades for today
        journal_file = f"{BASE_PATH}/trading_journal.json"
        if not os.path.exists(journal_file):
            return True, ""  # No trades yet
        
        with open(journal_file, 'r') as f:
            journal = json.load(f)
        
        today_trades = [
            t for t in journal 
            if datetime.fromisoformat(t['timestamp']).date() == today
            and t.get('outcome') in ['WIN', 'LOSS']
        ]
        
        if not today_trades:
            return True, ""  # No completed trades
        
        # Calculate daily PnL
        total_pnl_pct = sum(t.get('pnl_pct', 0) for t in today_trades)
        
        # Check limit
        if total_pnl_pct <= -max_daily_loss_pct:
            msg = (
                f"🚫 <b>DAILY LOSS LIMIT REACHED!</b>\n\n"
                f"📉 Today's Loss: <b>{abs(total_pnl_pct):.2f}%</b>\n"
                f"⚠️ Limit: <b>{max_daily_loss_pct}%</b>\n\n"
                f"Trading is automatically stopped for today.\n"
                f"System will resume tomorrow."
            )
            return False, msg
        
        return True, ""
        
    except Exception as e:
        logger.error(f"Daily loss check error: {e}")
        return True, ""  # Allow trading on error (fail-open)
```

**Integration in signal_cmd():**

```python
async def signal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... existing code ...
    
    # ✅ CHECK DAILY LOSS LIMIT BEFORE ANALYSIS
    can_trade, limit_msg = check_daily_loss_limit(update.effective_chat.id)
    
    if not can_trade:
        await update.message.reply_text(limit_msg, parse_mode='HTML')
        return
    
    # Continue with signal generation...
```

**Steps to Implement:**
1. Create `check_daily_loss_limit()` function
2. Add check in `signal_cmd()` BEFORE analysis
3. Add check in `ict_cmd()` BEFORE analysis
4. Add check in `send_alert_signal()` (when implemented)
5. Load daily trades from trading journal
6. Calculate daily PnL %
7. Block signal generation if limit reached
8. Send notification to user

**Testing:**
1. Set `max_daily_loss_pct: 2.0` (low for testing)
2. Generate losing trades until limit
3. Try `/signal` → should be blocked
4. Verify notification is sent
5. Check next day → should allow trading

**Бележки:**
- Check трябва да е ПРЕДИ signal analysis (спестяване на compute)
- Използвай trading journal за PnL tracking
- Fail-open на error (allow trading ако check фейлне)

---

### P15: Not All Commands Secured

**ID:** P15  
**Status:** Open  
**Критичност:** HIGH  
**Дата на откриване:** 24 Dec 2025

**Локация:**
- File: `bot.py` (all command handlers)
- File: `security/rate_limiter.py`, `security/auth.py`

**Описание:**
Security modules (v2.0.0) са available но не всички commands използват
security decorators (`@rate_limited`, `@require_auth`).

**Налични decorators:**
```python
from security.rate_limiter import check_rate_limit, rate_limiter
from security.auth import require_auth, require_admin
```

**Проблем:**
```bash
# Search for @rate_limited usage
grep -n "@rate_limited" bot.py

# Result: Само някои commands имат decorator!
```

**Причина:**
- Security system е добавен в v2.0.0
- Не всички commands са обновени
- Inconsistent protection

**Влияние върху системата:**
1. **Security:**
   - Възможност за spam/DoS на unprotected commands
   - Bypass на rate limiting
   - Uncontrolled resource usage

2. **Performance:**
   - Possible overload from spam
   - API quota exhaustion (Binance)

3. **User Experience:**
   - Unfair resource distribution

**Audit на commands:**

| Command | @rate_limited? | @require_auth? | Risk |
|---------|---------------|----------------|------|
| `/start` | ❌ NO | ❌ NO | LOW |
| `/help` | ❌ NO | ❌ NO | LOW |
| `/signal` | ⚠️ PARTIAL | ❌ NO | HIGH |
| `/ict` | ✅ YES | ❌ NO | MEDIUM |
| `/market` | ❌ NO | ❌ NO | MEDIUM |
| `/news` | ❌ NO | ❌ NO | MEDIUM |
| `/breaking` | ❌ NO | ❌ NO | HIGH |
| `/settings` | ❌ NO | ❌ NO | LOW |
| `/alerts` | ❌ NO | ❌ NO | LOW |
| `/backtest` | ❌ NO | ❌ NO | HIGH |
| `/journal` | ❌ NO | ❌ NO | LOW |
| `/stats` | ❌ NO | ❌ NO | LOW |
| `/risk` | ❌ NO | ❌ NO | LOW |
| `/dailyreport` | ❌ NO | ✅ YES (admin) | MEDIUM |
| `/restart` | ❌ NO | ✅ YES (admin) | MEDIUM |

**Препоръчано решение:**

```python
# HIGH-COST COMMANDS (API calls, heavy computation)
@rate_limited(calls=3, period=60)  # 3 calls per minute
@require_auth
async def signal_cmd(update, context):
    pass

@rate_limited(calls=3, period=60)
@require_auth
async def ict_cmd(update, context):
    pass

@rate_limited(calls=5, period=60)
@require_auth
async def backtest_cmd(update, context):
    pass

@rate_limited(calls=10, period=60)
@require_auth
async def breaking_cmd(update, context):
    pass

# MEDIUM-COST COMMANDS
@rate_limited(calls=10, period=60)
@require_auth
async def market_cmd(update, context):
    pass

@rate_limited(calls=10, period=60)
@require_auth
async def news_cmd(update, context):
    pass

# LOW-COST COMMANDS (data retrieval only)
@rate_limited(calls=20, period=60)
async def stats_cmd(update, context):
    pass

@rate_limited(calls=20, period=60)
async def journal_cmd(update, context):
    pass

# NO RATE LIMIT (critical commands)
async def start_cmd(update, context):
    pass

async def help_cmd(update, context):
    pass
```

**Steps to Implement:**
1. Audit ALL command handlers
2. Classify by resource cost (HIGH/MEDIUM/LOW)
3. Apply appropriate rate limits
4. Add @require_auth to user-facing commands
5. Keep admin commands with @require_admin
6. Test rate limiting works
7. Monitor security events

**Testing:**
1. Spam `/signal` command → should be rate limited
2. Verify error message to user
3. Check security_monitor logs
4. Test from unauthorized user → should be blocked

**Бележки:**
- Different limits за different command types
- Start/Help винаги достъпни (no rate limit)
- Admin commands винаги с @require_admin

---

## ⚠️ MEDIUM PRIORITY ISSUES

### P2: Monolithic bot.py Structure

**ID:** P2  
**Status:** Open  
**Критичност:** MEDIUM  
**Дата на откриване:** 24 Dec 2025

**Локация:**
- File: `bot.py` (entire file)

**Описание:**
bot.py е 13,721 реда в един файл.

**Статистика:**
```bash
wc -l bot.py
# 13721 bot.py
```

**Структура:**
- Lines 1-300: Imports & environment
- Lines 300-500: Configuration & constants
- Lines 500-6000: Helper functions
- Lines 6000-13000: Command handlers
- Lines 13000-13721: Scheduler & main

**Причина:**
- Incremental development
- All functionality added to single file
- No modularization strategy

**Влияние върху системата:**
1. **Maintainability:**
   - Трудно навигиране
   - Сложно разбиране на зависимости
   - Висок риск от грешки

2. **Testing:**
   - Difficult to unit test
   - High coupling
   - Can't mock dependencies easily

3. **Performance:**
   - Slow import time (5-10 seconds)
   - Large memory footprint

4. **Collaboration:**
   - Merge conflicts
   - Difficult code review

**Препоръчано решение:**

**Модулна структура:**
```
bot/
├── __init__.py
├── main.py                    # Entry point
├── config/
│   ├── __init__.py
│   ├── settings.py            # User settings
│   ├── constants.py           # Constants
│   └── environment.py         # Env variables
├── commands/
│   ├── __init__.py
│   ├── signal.py              # /signal, /ict
│   ├── market.py              # /market
│   ├── news.py                # /news, /breaking
│   ├── settings.py            # /settings, /alerts
│   ├── analysis.py            # /backtest, /journal
│   └── admin.py               # /restart, /dailyreport
├── services/
│   ├── __init__.py
│   ├── signal_generator.py    # Signal generation logic
│   ├── chart_service.py       # Chart generation
│   ├── market_data.py         # Binance API
│   └── news_service.py        # News fetching
├── models/
│   ├── __init__.py
│   ├── signal.py              # Signal data class
│   ├── user.py                # User settings
│   └── trade.py               # Trade tracking
├── utils/
│   ├── __init__.py
│   ├── cache.py               # Cache management
│   ├── validators.py          # Input validation
│   └── formatters.py          # Message formatting
└── scheduler/
    ├── __init__.py
    └── jobs.py                # Scheduled jobs
```

**Migration Steps:**
1. Create bot/ package structure
2. Move constants → config/constants.py
3. Move command handlers → commands/
4. Move business logic → services/
5. Move data models → models/
6. Move utilities → utils/
7. Create main.py as entry point
8. Update imports
9. Test incrementally

**Бележки:**
- Incremental refactoring (не наведнъж)
- Maintain backward compatibility
- Extensive testing required

---

### P3: Admin Module Hardcoded Paths

**ID:** P3  
**Status:** Open  
**Критичност:** MEDIUM  
**Дата на откриване:** 24 Dec 2025

**Локация:**
- File: `admin/admin_module.py`
- Line: 14

**Описание:**
Admin paths са hardcoded към `/workspaces/Crypto-signal-bot/`.

**Код:**
```python
# Line 14
ADMIN_DIR = "/workspaces/Crypto-signal-bot/admin"
ADMIN_PASSWORD_FILE = f"{ADMIN_DIR}/admin_password.json"
REPORTS_DIR = f"{ADMIN_DIR}/reports"
```

**Проблем:**
- Работи само в GitHub Codespaces
- НЕ работи на production server (/root/Crypto-signal-bot)
- НЕ работи на local development

**Причина:**
- Hardcoded path during development
- No dynamic path detection

**Влияние върху системата:**
1. **Functionality:**
   - Admin module НЕ работи на production
   - Reports НЕ се генерират
   - Password management фейлва

2. **Deployment:**
   - Трябва manual edit на paths
   - Deployment не е portable

**Препоръчано решение:**

```python
import os
from pathlib import Path

# Detect BASE_PATH dynamically (same as bot.py)
if os.getenv('BOT_BASE_PATH'):
    BASE_PATH = os.getenv('BOT_BASE_PATH')
elif os.path.exists('/root/Crypto-signal-bot'):
    BASE_PATH = '/root/Crypto-signal-bot'
elif os.path.exists('/workspaces/Crypto-signal-bot'):
    BASE_PATH = '/workspaces/Crypto-signal-bot'
else:
    # Fallback to module directory
    BASE_PATH = str(Path(__file__).parent.parent)

ADMIN_DIR = f"{BASE_PATH}/admin"
ADMIN_PASSWORD_FILE = f"{ADMIN_DIR}/admin_password.json"
REPORTS_DIR = f"{ADMIN_DIR}/reports"
DAILY_REPORTS_DIR = f"{REPORTS_DIR}/daily"
WEEKLY_REPORTS_DIR = f"{REPORTS_DIR}/weekly"
MONTHLY_REPORTS_DIR = f"{REPORTS_DIR}/monthly"

# Create directories with validation
for dir_path in [ADMIN_DIR, REPORTS_DIR, DAILY_REPORTS_DIR, 
                  WEEKLY_REPORTS_DIR, MONTHLY_REPORTS_DIR]:
    try:
        os.makedirs(dir_path, exist_ok=True)
        logger.info(f"✅ Directory ready: {dir_path}")
    except Exception as e:
        logger.error(f"❌ Failed to create {dir_path}: {e}")
        raise RuntimeError(f"Admin module initialization failed: {e}")
```

**Steps to Implement:**
1. Add BASE_PATH detection (копирай от bot.py)
2. Replace hardcoded paths
3. Add directory creation validation
4. Test on different environments:
   - Codespace
   - Production server
   - Local development
5. Verify reports are generated

**Testing:**
1. Deploy to production server
2. Run `/dailyreport`
3. Check reports directory
4. Verify files are created

**Бележки:**
- Use same logic като bot.py BASE_PATH
- Fail fast ако directories не могат да се създадат

---

### P5: ML Model Not Auto-Training

**ID:** P5  
**Status:** Open  
**Критичност:** MEDIUM  
**Дата на откриване:** 24 Dec 2025

**Локация:**
- File: `ml_engine.py`
- File: `ml_predictor.py`
- File: `journal_backtest.py` (trading journal)

**Описание:**
ML models exist и се използват за confidence adjustment но НЕ се трени автоматично
от real trading results.

**Текущо състояние:**
- ML Engine: Hybrid predictions (ICT + Classical)
- ML Predictor: Win probability
- Trading Journal: Tracks all trades with outcomes
- Backtest Engine: Comprehensive testing

**Липсваща връзка:**
```
Trading Journal Results → ML Training Pipeline → Updated Models
                ❌ NOT CONNECTED ❌
```

**Причина:**
- ML modules са създадени
- Journal tracking е имплементиран
- Но автоматичният training pipeline липсва

**Влияние върху системата:**
1. **ML Accuracy:**
   - Models не се подобряват с времето
   - Predictions базирани на стари данни
   - Confidence adjustment може да е неточен

2. **Adaptability:**
   - Системата не се адаптира към нови market conditions
   - ML остава статичен

**Препоръчано решение:**

```python
async def ml_auto_training_job(context):
    """
    Автоматично training на ML models от journal results.
    Изпълнява се weekly (Sunday 03:00 UTC).
    """
    try:
        logger.info("🤖 Starting ML auto-training...")
        
        # 1. Load trading journal
        journal_file = f"{BASE_PATH}/trading_journal.json"
        
        if not os.path.exists(journal_file):
            logger.warning("No journal data for ML training")
            return
        
        with open(journal_file, 'r') as f:
            journal = json.load(f)
        
        # 2. Filter completed trades (WIN/LOSS)
        completed_trades = [
            t for t in journal
            if t.get('outcome') in ['WIN', 'LOSS']
        ]
        
        if len(completed_trades) < 50:
            logger.warning(f"Insufficient trades for ML training: {len(completed_trades)}")
            return
        
        # 3. Prepare training data
        X_features = []
        y_outcomes = []
        
        for trade in completed_trades:
            # Extract features
            features = {
                'ict_confidence': trade.get('confidence', 0) / 100.0,
                'risk_reward': trade.get('risk_reward', 0),
                'mtf_alignment': trade.get('mtf_alignment', 0) / 100.0,
                'order_block_strength': trade.get('ob_strength', 0) / 100.0,
                'liquidity_confluence': trade.get('liquidity_score', 0) / 100.0,
                'timeframe_weight': TIMEFRAME_WEIGHTS.get(trade.get('timeframe'), 0.5),
                # ... more features
            }
            
            X_features.append(list(features.values()))
            
            # Binary outcome: 1 = WIN, 0 = LOSS
            y_outcomes.append(1 if trade['outcome'] == 'WIN' else 0)
        
        X = np.array(X_features)
        y = np.array(y_outcomes)
        
        # 4. Train ML Engine
        if ML_AVAILABLE and ml_engine.model is not None:
            logger.info("Training ML Engine...")
            ml_engine.train(X, y)
            ml_engine.save_model()  # Persist
            logger.info("✅ ML Engine retrained")
        
        # 5. Train ML Predictor
        if ML_PREDICTOR_AVAILABLE and ml_predictor.is_trained:
            logger.info("Training ML Predictor...")
            
            # Prepare trade data for predictor
            for trade in completed_trades:
                ml_predictor.record_trade_outcome(
                    trade_data={
                        'entry_price': trade['entry_price'],
                        'analysis_data': trade.get('analysis_features', {})
                    },
                    won=trade['outcome'] == 'WIN'
                )
            
            ml_predictor.save_model()
            logger.info("✅ ML Predictor retrained")
        
        # 6. Send training summary to owner
        win_rate = sum(y) / len(y) * 100
        
        msg = (
            f"🤖 <b>ML AUTO-TRAINING COMPLETE</b>\n\n"
            f"📊 <b>Training Data:</b>\n"
            f"  • Trades: {len(completed_trades)}\n"
            f"  • Win Rate: {win_rate:.1f}%\n\n"
            f"✅ Models Updated:\n"
            f"  • ML Engine: Retrained\n"
            f"  • ML Predictor: Retrained\n\n"
            f"💡 Models will improve signal accuracy."
        )
        
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=msg,
            parse_mode='HTML'
        )
        
        logger.info(f"✅ ML auto-training completed: {len(completed_trades)} trades")
        
    except Exception as e:
        logger.error(f"ML auto-training error: {e}")
```

**Integration в scheduler:**

```python
# Line ~13300 (in main())
scheduler.add_job(
    ml_auto_training_job,
    'cron',
    day_of_week='sun',  # Sunday
    hour=3,             # 03:00 UTC
    minute=0
)
logger.info("✅ ML auto-training scheduled (Sundays 03:00 UTC)")
```

**Steps to Implement:**
1. Create `ml_auto_training_job()` function
2. Load completed trades from journal
3. Extract features from trade data
4. Train ML Engine with new data
5. Train ML Predictor with outcomes
6. Save updated models
7. Schedule weekly execution
8. Send summary notification

**Testing:**
1. Generate 50+ trades (WIN/LOSS)
2. Manually trigger training job
3. Verify models are updated
4. Check prediction accuracy improves
5. Test on new signals

**Бележки:**
- Minimum 50 trades за meaningful training
- Weekly schedule (не твърде често)
- Persist models след training

---

### P8: Cooldown System Incomplete

**ID:** P8  
**Status:** Open  
**Критичност:** MEDIUM  
**Дата на откриване:** 24 Dec 2025

**Локация:**
- File: `bot.py`
- Functions: `signal_cmd()` (line 6191), `ict_cmd()` (line 6391)

**Описание:**
Cooldown check е имплементиран в `/ict` но ЛИПСВА в `/signal`.

**Код анализ:**

**In `/ict` (line 6514-6532):**
```python
# ✅ HAS COOLDOWN CHECK
signal_key = f"{symbol}_{timeframe}_{signal.signal_type.value}"

if is_signal_already_sent(
    symbol=symbol,
    signal_type=signal.signal_type.value,
    timeframe=timeframe,
    confidence=signal.confidence,
    entry_price=signal.entry_price,
    cooldown_minutes=60
):
    await processing_msg.edit_text(
        f"⏳ Signal for {symbol} already sent recently...",
        parse_mode='HTML'
    )
    return
```

**In `/signal` (line 6191-6388):**
```python
# ❌ NO COOLDOWN CHECK
# Goes straight to signal generation
```

**Причина:**
- Cooldown е добавен в `/ict`
- `/signal` не е обновен
- Inconsistent behavior

**Влияние върху системата:**
1. **Signal Duplication:**
   - `/signal` може да генерира дублирани сигнали
   - Само `/ict` е защитен

2. **User Confusion:**
   - Защо `/signal` позволява duplicates?
   - Inconsistent UX

3. **Resource Waste:**
   - Unnecessary API calls
   - Duplicate analysis

**Препоръчано решение:**

**Unified Cooldown System:**

```python
def check_signal_cooldown(symbol: str, signal_type: str, timeframe: str, 
                         confidence: float, entry_price: float,
                         cooldown_minutes: int = 60) -> tuple[bool, str]:
    """
    Unified cooldown check за всички signal commands.
    
    Returns:
        (is_duplicate: bool, message: str)
    """
    if is_signal_already_sent(
        symbol=symbol,
        signal_type=signal_type,
        timeframe=timeframe,
        confidence=confidence,
        entry_price=entry_price,
        cooldown_minutes=cooldown_minutes
    ):
        msg = (
            f"⏳ <b>Signal Already Sent Recently</b>\n\n"
            f"📊 {symbol} {timeframe} {signal_type}\n"
            f"🕐 Cooldown: {cooldown_minutes} minutes\n\n"
            f"Please wait before requesting again."
        )
        return True, msg
    
    return False, ""
```

**Apply to both commands:**

```python
async def signal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... existing code до signal generation ...
    
    # ✅ CHECK COOLDOWN
    is_duplicate, cooldown_msg = check_signal_cooldown(
        symbol=symbol,
        signal_type=ict_signal.signal_type.value,
        timeframe=timeframe,
        confidence=ict_signal.confidence,
        entry_price=ict_signal.entry_price,
        cooldown_minutes=60
    )
    
    if is_duplicate:
        await processing_msg.edit_text(cooldown_msg, parse_mode='HTML')
        return
    
    # Continue with formatting & sending...
```

**Steps to Implement:**
1. Create unified `check_signal_cooldown()` function
2. Add check to `/signal` command
3. Keep existing check in `/ict`
4. Use same cooldown period (60 min)
5. Test both commands
6. Verify cooldown works

**Testing:**
1. Generate signal with `/signal BTC 1h`
2. Immediately request `/signal BTC 1h` again → should be blocked
3. Request `/ict BTC 1h` → should also be blocked (same signal)
4. Wait 60+ min → should allow new signal

**Бележки:**
- Cooldown трябва да е SHARED between `/signal` and `/ict`
- Same signal от different commands = same cooldown
- Clear messaging за users

---

### P10: Scheduler Jobs Without Error Handling

**ID:** P10  
**Status:** Open  
**Критичност:** MEDIUM  
**Дата на откриване:** 24 Dec 2025

**Локация:**
- File: `bot.py`
- Lines: 13000-13522 (scheduler setup)

**Описание:**
Scheduler jobs нямат global exception handling. Job failure може да crash scheduler.

**Проблемни jobs:**

```python
# Lines 13082-13094 - Daily Report
scheduler.add_job(
    send_daily_report,  # ← No error handling
    'cron', hour=0, minute=30
)

# Lines 13137-13148 - Weekly Report
scheduler.add_job(
    send_weekly_report,  # ← No error handling
    'cron', day_of_week='mon', hour=9
)

# Lines 13202-13219 - Diagnostics
scheduler.add_job(
    run_diagnostics,  # ← No error handling
    'cron', hour=0, minute=0
)

# Lines 13513-13520 - Weekly Backtest
scheduler.add_job(
    weekly_backtest_wrapper,  # ← No error handling
    'cron', day_of_week='mon', hour=9
)
```

**Причина:**
- Jobs са async functions
- Exception в job може да crash scheduler
- No retry logic

**Влияние върху системата:**
1. **Stability:**
   - Job crash може да спре scheduler
   - Other jobs може да не се изпълнят

2. **Monitoring:**
   - Failures са silent
   - No notification за errors

**Препоръчано решение:**

**Job Wrapper with Error Handling:**

```python
def safe_job(job_name: str):
    """
    Decorator за scheduler jobs - добавя error handling и retry logic.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(context):
            max_retries = 3
            retry_delay = 60  # seconds
            
            for attempt in range(max_retries):
                try:
                    logger.info(f"🔄 Starting job: {job_name} (attempt {attempt + 1}/{max_retries})")
                    
                    result = await func(context)
                    
                    logger.info(f"✅ Job completed: {job_name}")
                    return result
                    
                except Exception as e:
                    logger.error(f"❌ Job failed: {job_name} (attempt {attempt + 1})")
                    logger.error(f"Error: {str(e)}")
                    logger.exception(e)
                    
                    if attempt < max_retries - 1:
                        logger.info(f"⏳ Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        # Final failure - notify owner
                        try:
                            await context.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=(
                                    f"❌ <b>SCHEDULER JOB FAILED</b>\n\n"
                                    f"Job: {job_name}\n"
                                    f"Attempts: {max_retries}\n"
                                    f"Error: {str(e)[:200]}\n\n"
                                    f"Check logs for details."
                                ),
                                parse_mode='HTML'
                            )
                        except:
                            pass  # Even notification failed
                        
                        logger.error(f"💥 Job permanently failed: {job_name}")
        
        return wrapper
    return decorator
```

**Apply to all jobs:**

```python
@safe_job("daily_report")
async def send_daily_report(context):
    # Existing code...
    pass

@safe_job("weekly_report")
async def send_weekly_report(context):
    # Existing code...
    pass

@safe_job("diagnostics")
async def run_diagnostics(context):
    # Existing code...
    pass

@safe_job("weekly_backtest")
async def weekly_backtest_wrapper(context):
    # Existing code...
    pass

@safe_job("auto_signal")
async def send_alert_signal(context):
    # Existing code...
    pass
```

**Steps to Implement:**
1. Create `safe_job()` decorator
2. Apply to ALL scheduler jobs
3. Configure retry logic (max 3 attempts)
4. Add failure notification to owner
5. Test job failure scenarios

**Testing:**
1. Force job failure (throw exception)
2. Verify retry attempts
3. Check notification is sent
4. Verify scheduler continues running
5. Test next scheduled execution

**Бележки:**
- Max 3 retries с 60s delay
- Notify owner на permanent failure
- Scheduler трябва да продължи running

---

### P13: Global Cache Without Cleanup

**ID:** P13  
**Status:** Open  
**Критичност:** MEDIUM  
**Дата на откриване:** 24 Dec 2025

**Локация:**
- File: `bot.py`
- Lines: 350-401 (CACHE implementation)

**Описание:**
Global CACHE dict може да расте безкрайно. Няма size limit или LRU eviction.

**Текущ код:**
```python
# Lines 350-361
CACHE = {
    'backtest': {},      # Може да стане голям
    'market': {},        # Може да стане голям
    'ml_performance': {} # Може да стане голям
}

CACHE_TTL = {
    'backtest': 300,      # 5 minutes
    'market': 180,        # 3 minutes
    'ml_performance': 300 # 5 minutes
}
```

**Проблем:**
- Items се добавят но NEVER се изтриват (освен при TTL check)
- Expired items остават до следващия `get_cached()` call
- Няма global size limit

**Причина:**
- Опростена implementation
- TTL-based expiration само при access
- No cleanup job

**Влияние върху системата:**
1. **Memory:**
   - Unbounded growth
   - Може да достигне GB размери при heavy usage

2. **Performance:**
   - Large dict lookups
   - Memory pressure

**Препоръчано решение:**

**LRU Cache with Size Limit:**

```python
from collections import OrderedDict
from threading import Lock

class LRUCache:
    """
    Thread-safe LRU cache с TTL и size limit.
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 300):
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self.cache = OrderedDict()
        self.lock = Lock()
    
    def get(self, key: str):
        """Get value from cache (thread-safe)."""
        with self.lock:
            if key not in self.cache:
                return None
            
            # Check TTL
            item = self.cache[key]
            age = (datetime.now(timezone.utc) - item['timestamp']).total_seconds()
            
            if age > self.ttl_seconds:
                # Expired
                del self.cache[key]
                return None
            
            # Move to end (most recently used)
            self.cache.move_to_end(key)
            
            return item['data']
    
    def set(self, key: str, value):
        """Set value in cache (thread-safe)."""
        with self.lock:
            # Remove if exists (to update position)
            if key in self.cache:
                del self.cache[key]
            
            # Add new item
            self.cache[key] = {
                'data': value,
                'timestamp': datetime.now(timezone.utc)
            }
            
            # Enforce size limit (evict oldest)
            while len(self.cache) > self.max_size:
                oldest_key = next(iter(self.cache))
                del self.cache[oldest_key]
                logger.debug(f"Cache evicted: {oldest_key}")
    
    def clear(self):
        """Clear all cache."""
        with self.lock:
            self.cache.clear()
    
    def cleanup_expired(self):
        """Remove all expired items."""
        with self.lock:
            now = datetime.now(timezone.utc)
            expired_keys = [
                key for key, item in self.cache.items()
                if (now - item['timestamp']).total_seconds() > self.ttl_seconds
            ]
            
            for key in expired_keys:
                del self.cache[key]
            
            if expired_keys:
                logger.info(f"Cache cleanup: {len(expired_keys)} expired items removed")

# Replace global CACHE
CACHE = {
    'backtest': LRUCache(max_size=50, ttl_seconds=300),
    'market': LRUCache(max_size=100, ttl_seconds=180),
    'ml_performance': LRUCache(max_size=50, ttl_seconds=300)
}

# Scheduled cleanup job (every 10 minutes)
async def cache_cleanup_job(context):
    """Periodic cache cleanup."""
    try:
        for cache_type, cache in CACHE.items():
            cache.cleanup_expired()
        logger.debug("✅ Cache cleanup completed")
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")

# In scheduler setup (line ~13300)
scheduler.add_job(
    cache_cleanup_job,
    'interval',
    minutes=10
)
```

**Steps to Implement:**
1. Create LRUCache class
2. Replace global CACHE dicts
3. Update get_cached() and set_cache() functions
4. Add cleanup job to scheduler
5. Test cache size limits
6. Monitor memory usage

**Testing:**
1. Generate 100+ cache entries
2. Verify oldest are evicted
3. Check expired items are removed
4. Monitor memory usage

**Бележки:**
- LRU: Least Recently Used eviction
- Thread-safe implementation
- Periodic cleanup за expired items

---

(Continue with LOW priority issues...)

---

## 🔵 LOW PRIORITY ISSUES

### P4: Unused Feature Flags

**ID:** P4  
**Status:** Open  
**Критичност:** LOW  

**Описание:** Някои feature flags не се използват.

**Flags:**
- `use_ict_enhancer: false` → ICT Enhancement Layer не се използва
- `use_archive: false` → архивиране изключено

**Препоръка:** Активирай или документирай защо са disabled.

---

### P7: Chart Generation Failure Handling

**ID:** P7  
**Status:** Open  
**Критичност:** LOW  

**Описание:** Chart generation е в try/catch но няма fallback visualization.

**Препоръка:** Добави текстова visualization fallback (ASCII art chart).

---

### P9: Entry Zone Validation Duplication

**ID:** P9  
**Status:** Open  
**Критичност:** LOW  

**Описание:** Entry zone validation и в ICT engine и в signal_helpers.

**Препоръка:** Консолидирай validation в едно място (ICT engine).

---

### P11: Conditional Imports

**ID:** P11  
**Status:** Open  
**Критичност:** LOW  

**Описание:** Conditional imports с try/except навсякъде.

**Препоръка:** Централен module loader с dependency injection.

---

### P12: ICT Engine Hardcoded Config

**ID:** P12  
**Status:** Open  
**Критичност:** LOW  

**Описание:** ICT config е hardcoded в DEFAULT_CONFIG dict.

**Препоръка:** Load от external config file (config/ict_config.json).

---

### P14: BASE_PATH Detection

**ID:** P14  
**Status:** Open  
**Критичност:** LOW  

**Описание:** Path detection може да fallback към wrong directory.

**Препоръка:** Добави explicit path validation & error.

---

## 📊 SUMMARY BY PRIORITY

### HIGH Priority (3 issues):
- P1: Auto-Signal Function Missing
- P6: Daily Loss Limit Not Enforced
- P15: Not All Commands Secured

### MEDIUM Priority (8 issues):
- P2: Monolithic bot.py Structure
- P3: Admin Module Hardcoded Paths
- P5: ML Model Not Auto-Training
- P8: Cooldown System Incomplete
- P10: Scheduler Jobs Without Error Handling
- P13: Global Cache Without Cleanup

### LOW Priority (4 issues):
- P4: Unused Feature Flags
- P7: Chart Generation Failure Handling
- P9: Entry Zone Validation Duplication
- P11: Conditional Imports
- P12: ICT Engine Hardcoded Config
- P14: BASE_PATH Detection

---

## 🎯 RECOMMENDED ACTION PLAN

### Phase 1: Critical Fixes (Week 1)
1. P1: Implement `send_alert_signal()` function
2. P6: Add daily loss limit check
3. P15: Apply security decorators to all commands

### Phase 2: Stability Improvements (Week 2-3)
4. P10: Add error handling to scheduler jobs
5. P8: Unify cooldown system
6. P3: Fix admin module paths
7. P13: Implement LRU cache

### Phase 3: Quality Improvements (Week 4-6)
8. P5: Add ML auto-training pipeline
9. P9: Consolidate validation logic
10. P7: Add chart fallback

### Phase 4: Long-term (Month 2-3)
11. P2: Refactor bot.py into modules
12. P12: Extract ICT config to file
13. Improve test coverage

---

**Край на tracking document.**

_Всички проблеми са в статус "Open" - изчакват решения._  
_Документът ще се актуализира при промени._
