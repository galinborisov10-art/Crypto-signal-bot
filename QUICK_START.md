# 🚀 Бърз Старт - Управление на системата

## 📊 Проверка на статуса

```bash
./system-status.sh
```

Показва статуса на всички 3 системи:
- 🤖 Main Bot
- 🔧 Auto-Fixer  
- 🐕 Watchdog

---

## 🛠️ Управление на Bot

```bash
./bot-manager.sh start      # Стартира бота
./bot-manager.sh stop       # Спира бота
./bot-manager.sh restart    # Рестартира бота
./bot-manager.sh status     # Статус
```

---

## 🔧 Управление на Auto-Fixer

```bash
./auto-fixer-manager.sh start      # Стартира auto-fixer
./auto-fixer-manager.sh stop       # Спира auto-fixer
./auto-fixer-manager.sh status     # Статус
./auto-fixer-manager.sh logs       # Логове
```

**Какво прави:** Проверява за грешки на всеки 15 минути и ги отстранява автоматично.

---

## 🐕 Управление на Watchdog

```bash
./watchdog-manager.sh start      # Стартира watchdog
./watchdog-manager.sh stop       # Спира watchdog
./watchdog-manager.sh status     # Статус
./watchdog-manager.sh check      # Еднократна проверка
./watchdog-manager.sh logs       # Логове
```

**Какво прави:** Проверява дали ботът отговаря на всеки 2 минути и го рестартира при нужда.

---

## ⚡ Бързи команди

### Рестарт на всички системи
```bash
./bot-manager.sh restart && \
./auto-fixer-manager.sh restart && \
./watchdog-manager.sh restart
```

### Спиране на всички системи
```bash
./watchdog-manager.sh stop && \
./auto-fixer-manager.sh stop && \
./bot-manager.sh stop
```

### Стартиране на всички системи
```bash
./bot-manager.sh start && \
./auto-fixer-manager.sh start && \
./watchdog-manager.sh start
```

---

## 📝 Логове

```bash
# Bot логове
tail -f bot.log

# Auto-fixer логове
tail -f auto_fixer.log

# Watchdog логове
tail -f watchdog.log
```

---

## 🆘 Проблеми?

### Ботът не работи
```bash
./bot-manager.sh restart
```

### Бутоните не работят
```bash
./watchdog-manager.sh check     # Провери какъв е проблемът
./bot-manager.sh restart        # Рестартирай
```

### Системата е бавна
```bash
./system-status.sh              # Провери CPU/Memory
```

### Всичко е счупено
```bash
# Спри всичко
pkill -9 python3

# Почисти PID файлове
rm -f *.pid

# Стартирай отново
./bot-manager.sh start
./auto-fixer-manager.sh start
./watchdog-manager.sh start
```

---

## ✅ Автоматично стартиране

Всички системи се стартират **автоматично** при:
- Отваряне на терминал
- Рестарт на Codespace
- Login в системата

**Не е нужно ръчно стартиране!**

---

## 📚 Документация

- `BOT_MANAGEMENT.md` - Bot управление
- `AUTO_FIXER_README.md` - Auto-fixer система
- `WATCHDOG_README.md` - Watchdog система
- `INCIDENT_ANALYSIS.md` - Анализ на инциденти

---

## 🎯 Как работи всичко заедно?

```
┌─────────────────────────────────────────┐
│         🤖 TELEGRAM BOT                 │
│   (Основна функционалност)              │
└─────────────────────────────────────────┘
              ↓ наблюдава
┌─────────────────────────────────────────┐
│       🐕 WATCHDOG (2 min)               │
│   Проверява дали отговаря               │
│   → Рестартира при проблем              │
└─────────────────────────────────────────┘
              ↓ подкрепя
┌─────────────────────────────────────────┐
│     🔧 AUTO-FIXER (15 min)              │
│   Проверява за грешки                   │
│   → Отстранява автоматично              │
└─────────────────────────────────────────┘
```

**Резултат:** 99.9% uptime! 🚀
