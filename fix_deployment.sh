#!/bin/bash

# 🔧 FIX DEPLOYMENT - Спира ВСИЧКИ процеси и deploy-ва новата версия

echo "🔍 Проверка за активни bot процеси..."

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

echo "📁 Bot directory: $BOT_DIR"

# 1. СПРИ ВСИЧКО
echo ""
echo "⏹️ Спиране на ВСИЧКИ процеси..."

# Systemd service
systemctl stop crypto-bot 2>/dev/null && echo "✅ Systemd service спрян" || echo "⚠️ Няма systemd service"

# Watchdog
systemctl stop bot-watchdog 2>/dev/null && echo "✅ Watchdog спрян" || echo "⚠️ Няма watchdog service"
pkill -f "bot_watchdog.py" 2>/dev/null && echo "✅ Watchdog process убит" || echo "⚠️ Няма watchdog process"

# PM2 (ако има)
if command -v pm2 &> /dev/null; then
  echo "🔍 Намерен PM2!"
  pm2 list
  pm2 stop all 2>/dev/null && echo "✅ PM2 процеси спрени" || echo "⚠️ Няма PM2 процеси"
  pm2 delete all 2>/dev/null && echo "✅ PM2 процеси изтрити" || echo "⚠️ Няма PM2 процеси за изтриване"
else
  echo "⚠️ PM2 не е инсталиран"
fi

# Убий всички Python bot процеси
pkill -9 -f "python.*bot.py" 2>/dev/null && echo "✅ Python bot процеси убити" || echo "⚠️ Няма Python bot процеси"

sleep 3

# Провери дали има още активни процеси
echo ""
echo "🔍 Проверка за останали процеси..."
if pgrep -f "bot.py" > /dev/null; then
  echo "⚠️ ВНИМАНИЕ! Все още има активни процеси:"
  ps aux | grep "[b]ot.py"
  echo ""
  echo "❓ Да ги убия насила? (yes/no)"
  read -r answer
  if [ "$answer" = "yes" ]; then
    pkill -9 -f "bot.py"
    echo "✅ Процесите са убити насила"
  fi
else
  echo "✅ Няма активни процеси"
fi

# 2. PULL LATEST CODE
echo ""
echo "📥 Pulling latest code from GitHub..."
cd "$BOT_DIR"
git fetch origin
git reset --hard origin/main
git pull origin main

# 3. INSTALL DEPENDENCIES
echo ""
echo "📦 Installing dependencies..."
pip3 install -r requirements.txt 2>/dev/null || pip install -r requirements.txt

# 4. START BOT
echo ""
echo "🚀 Starting bot..."

# Опция 1: Systemd (ако има)
if systemctl is-enabled crypto-bot 2>/dev/null; then
  echo "▶️ Стартиране през systemd..."
  systemctl start crypto-bot
  sleep 3
  systemctl status crypto-bot --no-pager
  
  # Стартирай и watchdog
  if systemctl is-enabled bot-watchdog 2>/dev/null; then
    echo "▶️ Стартиране на Watchdog..."
    systemctl start bot-watchdog
  fi
else
  # Опция 2: Директно
  echo "▶️ Стартиране директно..."
  nohup python3 bot.py > bot.log 2>&1 &
  sleep 3
fi

# 5. VERIFY
echo ""
echo "✅ Проверка..."
if pgrep -f "python.*bot.py" > /dev/null; then
  echo "✅ Бота работи!"
  echo ""
  ps aux | grep "[p]ython.*bot.py"
  echo ""
  echo "📋 Логове: tail -f $BOT_DIR/bot.log"
  echo "📊 Status: systemctl status crypto-bot"
else
  echo "❌ Бота НЕ стартира!"
  echo ""
  echo "📋 Последни логове:"
  tail -30 bot.log 2>/dev/null || tail -30 /var/log/crypto-bot.log 2>/dev/null || echo "Няма логове"
fi

echo ""
echo "🎯 Deployment завършен!"
echo "📱 Провери Telegram: /start"
