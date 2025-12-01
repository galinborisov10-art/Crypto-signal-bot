# 📝 Trading Journal - ML Self-Learning System

## 🎯 Цел

Автоматичен журнал, който записва всеки trade и използва Machine Learning за самообучение на бота. Системата анализира успешни и неуспешни trades, за да подобрява бъдещите сигнали.

**🚀 НОВА ФУНКЦИЯ: 24/7 АВТОМАТИЧЕН МОНИТОРИНГ!**

---

## 🔄 24/7 Автоматична Система

### Как работи непрекъснато:

#### 1. **Автоматично логване на trades** (при всеки сигнал)
- ✅ Ръчни сигнали (`/signal`)
- ✅ Автоматични сигнали (alerts на всеки 5 мин)
- ✅ Callback сигнали (бутони в Telegram)

**Условие:** Confidence ≥ 65%

#### 2. **24/7 Мониторинг на активни trades** (на всеки 2 минути)
```
🔄 Проверка:
├── Всички PENDING trades в журнала
├── Текуща цена от Binance
├── Сравнение с TP/SL нива
└── Автоматично затваряне при удар

⏱️ Интервал: 2 минути
🕐 Работи: 24/7 непрекъснато
```

#### 3. **Автоматично затваряне и ML анализ**
Когато trade удари TP или SL:
- ✅ Обновява статус на WIN/LOSS
- ✅ Записва profit/loss %
- ✅ Извършва ML pattern analysis
- ✅ Изпраща Telegram нотификация
- ✅ Обновява ML insights

#### 4. **Автоматично събиране на ML данни**
Всички сигнали с confidence ≥ 65% автоматично се записват с:
- RSI, MA20, MA50
- Volume ratio
- Volatility
- Trend direction
- BTC correlation (ако е налична)
- News sentiment (ако е наличен)

---

## 📊 Структура на Journal

### 1. Metadata
```json
{
  "created": "2025-11-25",
  "version": "1.0",
  "total_trades": 150,
  "last_updated": "2025-11-25T12:30:00Z"
}
```

### 2. Trades (Всички записани trades)
```json
{
  "id": 1,
  "timestamp": "2025-11-25T10:15:00Z",
  "symbol": "BTCUSDT",
  "timeframe": "4h",
  "signal": "BUY",
  "confidence": 75.5,
  "entry_price": 45000.00,
  "tp_price": 46350.00,
  "sl_price": 44325.00,
  "status": "WIN",
  "outcome": "WIN",
  "profit_loss_pct": 2.8,
  "closed_at": "2025-11-25T14:30:00Z",
  "conditions": {
    "rsi": 45.2,
    "ma_20": 44800,
    "ma_50": 44500,
    "volume_ratio": 1.25,
    "volatility": "MEDIUM",
    "trend": "BULLISH",
    "btc_correlation": {...},
    "sentiment": "POSITIVE"
  },
  "notes": []
}
```

### 3. Patterns (ML анализ на успешни/неуспешни условия)
```json
{
  "successful_conditions": {
    "BTCUSDT_4h_BUY": {
      "count": 12,
      "avg_confidence": 74.5,
      "conditions_summary": [...]
    }
  },
  "failed_conditions": {
    "ETHUSDT_1h_SELL": {
      "count": 5,
      "avg_confidence": 62.0,
      "conditions_summary": [...]
    }
  },
  "best_timeframes": {
    "4h": {"wins": 25, "losses": 10, "total": 35},
    "1h": {"wins": 15, "losses": 12, "total": 27}
  },
  "best_symbols": {
    "BTCUSDT": {"wins": 30, "losses": 8, "total": 38, "total_profit": 45.6},
    "ETHUSDT": {"wins": 20, "losses": 15, "total": 35, "total_profit": 12.3}
  }
}
```

### 4. ML Insights (Извлечени знания за подобряване)
```json
{
  "accuracy_by_confidence": {
    "70-80": {"wins": 45, "total": 60},
    "80-90": {"wins": 35, "total": 40}
  },
  "accuracy_by_timeframe": {...},
  "accuracy_by_symbol": {...},
  "optimal_entry_zones": {...}
}
```

---

## 🔧 Функции

### 1. `load_journal()`
Зарежда trading journal от `trading_journal.json`

### 2. `save_journal(journal)`
Запазва промените в journal

### 3. `log_trade_to_journal(...)`
Записва нов trade автоматично при всеки `/signal`

**Параметри:**
- `symbol` - Валута (BTCUSDT, ETHUSDT...)
- `timeframe` - Таймфрейм (1h, 4h, 1d...)
- `signal_type` - BUY, SELL, HOLD
- `confidence` - Увереност (0-100%)
- `entry_price` - Входна цена
- `tp_price` - Take Profit цена
- `sl_price` - Stop Loss цена
- `analysis_data` - Технически индикатори (RSI, MA, Volume...)

**Връща:** `trade_id` (уникален номер на trade-а)

### 4. `update_trade_outcome(trade_id, outcome, profit_loss_pct, notes=None)`
Обновява резултата от trade след завършването му

**Параметри:**
- `trade_id` - ID на trade-а
- `outcome` - "WIN" или "LOSS"
- `profit_loss_pct` - % Печалба/Загуба
- `notes` - Опционални бележки

**Автоматично извиква:** `analyze_trade_patterns()` за ML анализ

### 5. `analyze_trade_patterns(journal, trade)`
ML анализ на trade patterns. Извлича:

✅ **Успешни условия** - RSI, MA, Volume ratio, Volatility при успешни trades
❌ **Неуспешни условия** - Комбинации водещи до загуба
📊 **Най-добри timeframes** - Кой таймфрейм дава най-висок win rate
💰 **Най-добри symbols** - Коя валута е най-печеливша

### 6. `get_ml_insights()`
Извлича ML insights за подобряване на сигналите

**Връща структура:**
```python
{
  'total_trades': 150,
  'best_timeframes': {
    '4h': {'win_rate': 71.4, 'total_trades': 35},
    '1h': {'win_rate': 55.6, 'total_trades': 27}
  },
  'best_symbols': {
    'BTCUSDT': {'win_rate': 78.9, 'avg_profit': 1.2, 'total_trades': 38}
  },
  'confidence_accuracy': {
    '70-80': {'accuracy': 75.0, 'total': 60},
    '80-90': {'accuracy': 87.5, 'total': 40}
  },
  'avoid_conditions': [
    {'pattern': 'ETHUSDT_1h_SELL', 'failed_count': 5, 'avg_confidence': 62.0}
  ],
  'recommended_conditions': [
    {'pattern': 'BTCUSDT_4h_BUY', 'success_count': 12, 'avg_confidence': 74.5}
  ]
}
```

### 7. `monitor_active_trades(context)` ⭐ НОВА!
**24/7 автоматичен мониторинг на активни trades**

**Функционалност:**
- Проверява всички PENDING trades
- Извлича текуща цена от Binance
- Сравнява с TP/SL нива
- Автоматично затваря при удар
- Изпраща Telegram нотификация
- Обновява ML insights

**Интервал:** На всеки 2 минути
**Работи:** 24/7 непрекъснато (APScheduler)

**Пример на автоматично затваряне:**
```
✅ Trade #5 HIT TP: BTCUSDT @ $46,350.00 (+3.00%)
📝 Автоматично затворен
🤖 ML анализ завършен
💬 Нотификация изпратена
```

---

## 🚀 Как се използва?

### Автоматично логване (при всеки /signal):
```python
# В signal_cmd() функцията:
if analysis['has_good_trade']:
    # Записва в bot_stats.json
    signal_id = record_signal(...)
    
    # 📝 АВТОМАТИЧНО записва в trading_journal.json
    journal_id = log_trade_to_journal(
        symbol=symbol,
        timeframe=timeframe,
        signal_type=analysis['signal'],
        confidence=final_confidence,
        entry_price=price,
        tp_price=tp_price,
        sl_price=sl_price,
        analysis_data={
            'rsi': analysis.get('rsi'),
            'ma_20': analysis.get('ma_20'),
            'ma_50': analysis.get('ma_50'),
            'volume_ratio': analysis.get('volume_ratio'),
            'volatility': analysis.get('volatility'),
            'trend': analysis.get('trend'),
            'btc_correlation': btc_correlation,
            'sentiment': sentiment
        }
    )
```

### Ръчно обновяване на резултат:
```python
# Когато trade-ът завърши (TP или SL удари)
update_trade_outcome(
    trade_id=5,
    outcome='WIN',
    profit_loss_pct=2.8,
    notes='Perfect entry at support level'
)
```

### Извличане на ML insights:
```python
insights = get_ml_insights()

# Провери най-добрите timeframes
for tf, data in insights['best_timeframes'].items():
    print(f"{tf}: {data['win_rate']:.1f}% win rate")

# Избягвай условия с ниска успеваемост
for avoid in insights['avoid_conditions']:
    print(f"Avoid: {avoid['pattern']} (failed {avoid['failed_count']} times)")
```

---

## 📱 Команди

### `/journal` или `/j`
Показва Trading Journal с ML insights:

```
📝 TRADING JOURNAL - ML САМООБУЧЕНИЕ
━━━━━━━━━━━━━━━━━━━━━━━━

📊 Обща статистика:
Общо trades: 150
Завършени: 120
В изчакване: 30

🎯 Резултати:
✅ Успешни: 85 (70.8%)
❌ Неуспешни: 35

⏱️ Най-добри Timeframes:
  4h: 71.4% (35 trades)
  1d: 68.0% (25 trades)
  1h: 55.6% (27 trades)

💰 Най-добри Валути:
  BTCUSDT: 78.9% (avg: +1.20%)
  SOLUSDT: 72.5% (avg: +1.80%)
  ETHUSDT: 57.1% (avg: +0.35%)

🎯 Точност по Confidence:
  80-90%: 87.5% (40 trades)
  70-80%: 75.0% (60 trades)
  60-70%: 55.0% (20 trades)

💡 ML Препоръки (успешни patterns):
  ✅ BTCUSDT_4h_BUY (12 успеха)
  ✅ SOLUSDT_1d_BUY (8 успеха)

⚠️ ML Предупреждения (избягвай):
  ❌ ETHUSDT_1h_SELL (5 неуспеха)
  ❌ XRPUSDT_15m_BUY (4 неуспеха)

📋 Последни 5 Trades:
✅ #150 BTCUSDT BUY (75%) - WIN
✅ #149 SOLUSDT BUY (82%) - WIN
❌ #148 ETHUSDT SELL (68%) - LOSS
⏳ #147 BTCUSDT BUY (72%) - PENDING
✅ #146 ADAUSDT BUY (70%) - WIN

📖 Журналът автоматично се обновява при всеки trade.
🤖 ML системата се учи от всички резултати!
```

---

## 🤖 ML Самообучение

### Как работи?

1. **При всеки нов сигнал:**
   - Записва се trade с всички технически индикатори
   - Status: PENDING

2. **Когато trade завърши:**
   - Обновява се с WIN/LOSS
   - ML анализира кои условия са довели до резултата
   - Обновяват се patterns и insights

3. **ML системата учи:**
   - Кои timeframes дават най-висок win rate
   - Кои валути са най-печеливши
   - Кои технически условия водят до успех
   - Кои комбинации от индикатори да се избягват

4. **Бъдещи сигнали се подобряват:**
   - Confidence се коригира според исторически данни
   - Препоръчват се timeframes/symbols с висок win rate
   - Избягват се известни failing patterns

---

## 📈 Бъдещи подобрения

### Планирани функции:

1. **Автоматично затваряне на trades:**
   - Мониторинг на цената в реално време
   - Автоматично update при TP/SL

2. **Advanced ML модели:**
   - Neural Networks за по-точни предвиждания
   - Feature importance analysis
   - Automated pattern discovery

3. **Risk Management:**
   - Portfolio analysis
   - Max drawdown tracking
   - Position sizing recommendations

4. **Backtesting integration:**
   - Test ML insights върху исторически данни
   - Валидация на patterns

---

## ⚠️ Важни бележки

1. **Файлът `trading_journal.json` НЕ трябва да се изтрива** - съдържа цялата ML история!

2. **Backup регулярно:**
   ```bash
   cp trading_journal.json trading_journal_backup_$(date +%Y%m%d).json
   ```

3. **За production:**
   - Използвай database вместо JSON (PostgreSQL, MongoDB)
   - Добави retention policy (пази последните N месеца)

4. **ML insights стават по-точни с времето** - необходими поне 50-100 trades за надеждна статистика

---

## 📞 Поддръжка

За въпроси и предложения:
- GitHub Issues: https://github.com/galinborisov10-art/Crypto-signal-bot/issues
- Telegram: /task [описание на проблема]

---

**Създадено с ❤️ от GitHub Copilot за автоматично самообучение**
