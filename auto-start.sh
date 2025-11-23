#!/bin/bash

# ===============================================
# AUTO-START - Автоматично стартиране при login
# ===============================================

echo "🚀 Auto-start script running..."

# Директория на проекта
cd /workspaces/Crypto-signal-bot

# Провери дали bot-service.sh съществува
if [ ! -f "bot-service.sh" ]; then
    echo "❌ bot-service.sh не е намерен!"
    exit 1
fi

# Провери статуса
if ./bot-service.sh status > /dev/null 2>&1; then
    echo "✅ Bot вече работи!"
else
    echo "🔄 Стартирам бота..."
    ./bot-service.sh start
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Текущ статус:"
./bot-service.sh status
echo "━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "💡 Команди:"
echo "   ./bot-service.sh status  - Провери статус"
echo "   ./bot-service.sh restart - Рестартирай"
echo "   ./bot-service.sh stop    - Спри"
echo ""
