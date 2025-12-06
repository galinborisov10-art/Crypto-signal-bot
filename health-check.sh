#!/bin/bash
# Проверява дали ботът работи с правилната версия

echo "🔍 HEALTH CHECK - Crypto Signal Bot"
echo "===================================="

# Check bot service
if systemctl is-active --quiet crypto-bot; then
  echo "✅ Bot service: RUNNING"
else
  echo "❌ Bot service: NOT RUNNING"
  exit 1
fi

# Check Python version
PYTHON_VERSION=$(python3 --version)
echo "🐍 Python: $PYTHON_VERSION"

# Check python-telegram-bot version
PTB_VERSION=$(pip show python-telegram-bot | grep Version | awk '{print $2}')
echo "📦 python-telegram-bot: $PTB_VERSION"

# Check bot version
if [ -f VERSION ]; then
  BOT_VERSION=$(cat VERSION)
  echo "🤖 Bot Version: $BOT_VERSION"
fi

# Check deployment info
if [ -f .deployment-info ]; then
  echo "📊 Deployment Info:"
  cat .deployment-info
fi

echo "===================================="
echo "✅ Health check completed!"
