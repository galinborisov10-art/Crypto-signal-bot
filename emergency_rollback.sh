#!/bin/bash

# 🚨 EMERGENCY ROLLBACK SCRIPT
# Използвай при проблеми с deployment

echo "🚨 EMERGENCY ROLLBACK - Връщане към работеща версия"

# 1. Спри Watchdog (за да спре рестартите)
echo "⏹️ Спиране на Watchdog..."
systemctl stop bot-watchdog 2>/dev/null || pkill -f "bot_watchdog.py" || true

# 2. Спри бота
echo "⏹️ Спиране на бота..."
systemctl stop crypto-bot 2>/dev/null || pkill -f "python.*bot.py" || true

sleep 2

# 3. Rollback към предишен работещ commit
echo "⏮️ Rollback към работещ код..."

# Намери bot директория
if [ -d "/root/Crypto-signal-bot" ]; then
  BOT_DIR="/root/Crypto-signal-bot"
elif [ -d "/home/ubuntu/Crypto-signal-bot" ]; then
  BOT_DIR="/home/ubuntu/Crypto-signal-bot"
elif [ -d "$HOME/Crypto-signal-bot" ]; then
  BOT_DIR="$HOME/Crypto-signal-bot"
else
  echo "❌ Bot directory not found!"
  exit 1
fi

cd "$BOT_DIR"

# Rollback към commit ПРЕДИ оптимизациите
# Това е последния стабилен commit
git reset --hard b72f2b1  # Commit преди async оптимизациите

# 4. Стартирай бота БЕЗ Watchdog (за тестване)
echo "🚀 Стартиране на бота..."
nohup python3 bot.py > bot.log 2>&1 &

sleep 3

# 5. Провери дали работи
if pgrep -f "python.*bot.py" > /dev/null; then
  echo "✅ Бота работи!"
  echo "📋 Логове: tail -f $BOT_DIR/bot.log"
else
  echo "❌ Бота не стартира! Виж логовете:"
  tail -20 bot.log
fi

echo ""
echo "⚠️ Watchdog е спрян!"
echo "За да го стартираш отново: systemctl start bot-watchdog"
