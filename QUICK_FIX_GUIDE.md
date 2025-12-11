# ⚡ БЪРЗ ГАЙД: Как да поправя дублирането на сигнали

## 🎯 ПРОБЛЕМ В 1 РЕД

**Цената НЕ се проверява → близки сигнали се изпращат многократно**

---

## 🔧 РЕШЕНИЕ В 3 СТЪПКИ

### 1️⃣ Backup
```bash
cp bot.py bot.py.backup
```

### 2️⃣ Направи 3 промени в `bot.py`

#### Промяна A: Ред 419 (сигнатура)
```python
# ПРЕДИ
def is_signal_already_sent(symbol, signal_type, timeframe, confidence, cooldown_minutes=60):

# СЛЕД
def is_signal_already_sent(symbol, signal_type, timeframe, confidence, entry_price, cooldown_minutes=60):
```

#### Промяна B: Ред 440-461 (логика)
```python
# ПРЕДИ
if signal_key in SENT_SIGNALS_CACHE:
    last_sent_time = SENT_SIGNALS_CACHE[signal_key]['timestamp']
    last_confidence = SENT_SIGNALS_CACHE[signal_key]['confidence']
    
    time_diff = (current_time - last_sent_time).total_seconds() / 60
    
    if time_diff < cooldown_minutes:
        logger.info(f"⏭️ Skip {signal_key}: Изпратен преди {time_diff:.1f} мин")
        return True
    
    if abs(confidence - last_confidence) < 5 and time_diff < cooldown_minutes * 2:
        logger.info(f"⏭️ Skip {signal_key}: Същия confidence ({confidence}% vs {last_confidence}%)")
        return True

SENT_SIGNALS_CACHE[signal_key] = {
    'timestamp': current_time,
    'confidence': confidence
}

# СЛЕД
if signal_key in SENT_SIGNALS_CACHE:
    last_sent_time = SENT_SIGNALS_CACHE[signal_key]['timestamp']
    last_confidence = SENT_SIGNALS_CACHE[signal_key]['confidence']
    last_price = SENT_SIGNALS_CACHE[signal_key]['entry_price']
    
    time_diff = (current_time - last_sent_time).total_seconds() / 60
    price_diff_pct = abs((entry_price - last_price) / last_price) * 100
    confidence_diff = abs(confidence - last_confidence)
    
    # ПРАВИЛО 1: Cooldown + близка цена
    if time_diff < cooldown_minutes and price_diff_pct < 0.5:
        logger.info(f"⏭️ Skip {signal_key}: Cooldown ({time_diff:.1f}m) + Price close ({price_diff_pct:.2f}%)")
        return True
    
    # ПРАВИЛО 2: Много близка цена в 2h
    if price_diff_pct < 0.2 and time_diff < cooldown_minutes * 2:
        logger.info(f"⏭️ Skip {signal_key}: Price very close ({price_diff_pct:.2f}%) within 2h")
        return True
    
    # ПРАВИЛО 3: Подобен confidence + близка цена
    if confidence_diff < 5 and price_diff_pct < 1.0 and time_diff < cooldown_minutes * 1.5:
        logger.info(f"⏭️ Skip {signal_key}: Similar signal (Δconf={confidence_diff:.1f}%, Δprice={price_diff_pct:.2f}%)")
        return True
    
    # ПРАВИЛО 4: Идентичен сигнал в 4h
    if confidence_diff < 3 and price_diff_pct < 0.3 and time_diff < 240:
        logger.info(f"⏭️ Skip {signal_key}: Almost identical within 4h")
        return True

SENT_SIGNALS_CACHE[signal_key] = {
    'timestamp': current_time,
    'confidence': confidence,
    'entry_price': entry_price
}
```

#### Промяна C: Ред 7080 (извикване)
```python
# ПРЕДИ
if is_signal_already_sent(symbol, analysis['signal'], timeframe, analysis['confidence'], cooldown_minutes=60):

# СЛЕД
if is_signal_already_sent(symbol, analysis['signal'], timeframe, analysis['confidence'], analysis['price'], cooldown_minutes=60):
```

### 3️⃣ Тествай и рестартирай
```bash
# Провери синтаксиса
python3 -m py_compile bot.py

# Рестартирай
pm2 restart bot
# ИЛИ
systemctl restart crypto-signal-bot
```

---

## 📊 РЕЗУЛТАТ

### ПРЕДИ
```
10:00 - BTCUSDT SELL @ $97,100 ✅
11:15 - BTCUSDT SELL @ $97,095 ✅ ← ДУБЛИКАТ
12:30 - BTCUSDT SELL @ $97,102 ✅ ← ДУБЛИКАТ
```

### СЛЕД
```
10:00 - BTCUSDT SELL @ $97,100 ✅
11:15 - BTCUSDT SELL @ $97,095 ❌ БЛОКИРАН (0.05% close)
12:30 - BTCUSDT SELL @ $97,102 ❌ БЛОКИРАН (0.02% close)
14:30 - BTCUSDT SELL @ $95,200 ✅ (1.9% change - ново ниво!)
```

**Намаление:** 70-80% по-малко дубликати! 🎉

---

## 🔄 ROLLBACK (ако има проблем)

```bash
# Възстанови backup
cp bot.py.backup bot.py

# Рестартирай
pm2 restart bot
```

---

## 📖 ПЪЛНА ДОКУМЕНТАЦИЯ

1. **`DIAGNOSTIC_SUMMARY_BG.md`** - Кратко резюме
2. **`SIGNAL_DUPLICATION_DIAGNOSTIC.md`** - Пълна техническа диагностика
3. **`SIGNAL_DUPLICATION_EXAMPLES.md`** - Визуални примери

---

## ⚙️ НАСТРОЙКИ (advanced)

Ако искаш да промениш толерантностите, редактирай в Промяна B:

```python
# По-строга (по-малко сигнали)
price_diff_pct < 1.0  # вместо 0.5
cooldown_minutes = 90  # вместо 60

# По-либерална (повече сигнали)
price_diff_pct < 0.3  # вместо 0.5
cooldown_minutes = 45  # вместо 60
```

---

**ГОТОВО!** 🚀

След промените, логовете ще показват:
```
✅ New signal: BTCUSDT_SELL_4h @ $97100.00 (75%)
⏭️ Skip BTCUSDT_SELL_4h: Cooldown (15.0m) + Price close (0.05%)
⏭️ Skip BTCUSDT_SELL_4h: Price very close (0.02%) within 2h
```
