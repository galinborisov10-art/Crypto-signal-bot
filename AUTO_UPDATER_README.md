# 🤖 AUTO-UPDATER & SELF-HEALING BOT

## 🎯 Какво прави?

Автоматично **всеки ден** (04:00 сутринта):
- ✅ Проверява за нови updates в GitHub
- ✅ Pull-ва последните промени
- ✅ Инсталира нови dependencies
- ✅ Рестартира бота ако има промени
- ✅ Търси и поправя чести проблеми
- ✅ Изпраща Telegram отчет

## 🔧 Auto-Fix Възможности

Автоматично поправя:
- ❌ **ModuleNotFoundError** → преинсталира dependencies
- ❌ **ConnectionError/TimeoutError** → рестартира бота
- ❌ **Stale logs** (над 1 час без нови) → рестартира бота
- ❌ **Full disk** → трие стари backups (пази последните 10)

## 📦 Инсталация

### На сървъра:

```bash
cd ~/Crypto-signal-bot

# Pull новите файлове
git pull origin main

# Setup cron job (runs daily at 04:00)
bash setup_auto_updater.sh
```

### Ръчно тестване:

```bash
# Activate venv ако имате
source venv/bin/activate

# Run update manually
python3 auto_updater.py
```

## 📋 Конфигурация

### Cron Schedule (Промяна на часа):

```bash
crontab -e

# Примери:
0 4 * * *    # 04:00 всеки ден (DEFAULT)
0 */6 * * *  # Всеки 6 часа
*/30 * * * * # Всеки 30 минути
```

### Telegram Notifications:

Изпраща отчет към `OWNER_CHAT_ID` (7003238836) с:
- ✅ GitHub update статус
- ✅ Dependency check резултат
- ✅ Auto-fix действия
- ✅ Bot health status
- ✅ Restart confirmation

## 📊 Logове

```bash
# View auto-updater logs
tail -f ~/Crypto-signal-bot/auto_updater.log

# View bot logs
tail -f ~/Crypto-signal-bot/bot.log
```

## 🚨 Troubleshooting

### Cron job не работи:

```bash
# Check cron service
sudo systemctl status cron

# View cron logs
grep CRON /var/log/syslog

# Test script manually
cd ~/Crypto-signal-bot
python3 auto_updater.py
```

### Telegram notifications не идват:

- Проверете `TELEGRAM_BOT_TOKEN` в environment variables
- Или edit `auto_updater.py` → `TELEGRAM_TOKEN` на ред 23

## 🎯 Features Summary

| Feature | Description |
|---------|-------------|
| **Daily Auto-Update** | Pull от GitHub всеки ден в 04:00 |
| **Dependency Check** | Auto-install missing packages |
| **Health Monitoring** | Проверява дали ботът работи |
| **Auto-Restart** | Рестартира при updates или проблеми |
| **Self-Healing** | Поправя ModuleNotFound, ConnectionError и др. |
| **Disk Cleanup** | Трие стари backups при full disk |
| **Telegram Reports** | Изпраща status update след всяко action |

## 💡 Example Report

```
🤖 AUTO-UPDATE REPORT
⏰ 2025-12-01 04:00:00

✅ Updated from GitHub:
   Fix PTBDeprecationWarning - move timeouts to ApplicationBuilder

✅ Dependencies checked

🔧 Auto-fixed:
   • Reinstalled dependencies
   • Restarted bot (connection issues)

✅ Bot is running

🔄 Restarting bot with new code...
✅ Bot restarted with updates
```

## 🔒 Security Note

Скриптът използва:
- Git HTTPS (no credentials needed за public repos)
- Existing bot token from environment
- No sensitive data в cron logs

---

**Setup date:** 2025-12-01  
**Version:** 1.0  
**Auto-heal enabled:** ✅
