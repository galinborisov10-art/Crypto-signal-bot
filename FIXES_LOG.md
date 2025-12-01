# 🔧 Fixes Log

## 2025-12-01: PTBDeprecationWarning Fix

### ❌ Проблем:
```
/root/Crypto-signal-bot/bot.py:7737: PTBDeprecationWarning: 
Deprecated since version 20.6: Setting timeouts via `Application.run_polling` 
is deprecated. Please use `ApplicationBuilder.get_updates_*_timeout` instead.
```

### 📋 Стар код (ГРЕШЕН):
```python
app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

# ...

app.run_polling(
    drop_pending_updates=True, 
    allowed_updates=Update.ALL_TYPES,
    pool_timeout=30,        # ❌ Deprecated
    read_timeout=30,        # ❌ Deprecated
    write_timeout=30,       # ❌ Deprecated
    connect_timeout=30      # ❌ Deprecated
)
```

### ✅ Нов код (ПРАВИЛЕН):
```python
app = (
    ApplicationBuilder()
    .token(TELEGRAM_BOT_TOKEN)
    .get_updates_pool_timeout(30)      # ✅ Правилно място
    .get_updates_read_timeout(30)      # ✅ Правилно място
    .get_updates_write_timeout(30)     # ✅ Правилно място
    .get_updates_connect_timeout(30)   # ✅ Правилно място
    .build()
)

# ...

app.run_polling(
    drop_pending_updates=True, 
    allowed_updates=Update.ALL_TYPES
)
```

### 📝 Какво се промени:
- Timeouts се местят от `run_polling()` в `ApplicationBuilder()`
- Премахва се deprecation warning
- Бота работи по същия начин, но без предупреждения

### 🔗 Commit: `9834c05`

---

## 2025-12-01: update_bot.sh - venv Support

### ❌ Проблем:
```
ModuleNotFoundError: No module named 'telegram'
error: externally-managed-environment
```

### ✅ Решение:
- Добавена автоматична детекция на `venv/`
- Скриптът активира venv ако съществува
- Използва `venv/bin/python` вместо `python3`
- Fallback към system pip с `--break-system-packages`

### 🔗 Commit: `6687228`

---
