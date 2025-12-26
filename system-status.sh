#!/bin/bash
# System Status - Преглед на всички системи

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🤖 CRYPTO SIGNAL BOT - SYSTEM STATUS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 1. BOT
echo "1️⃣ MAIN BOT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
BOT_PID=$(pgrep -f "python3.*bot.py" | head -1)
if [ -n "$BOT_PID" ]; then
    PS_INFO=$(ps -p "$BOT_PID" -o %cpu,%mem,etime --no-headers)
    CPU=$(echo "$PS_INFO" | awk '{print $1}')
    MEM=$(echo "$PS_INFO" | awk '{print $2}')
    UPTIME=$(echo "$PS_INFO" | awk '{print $3}')
    
    echo "✅ Статус: РАБОТИ"
    echo "🆔 PID: $BOT_PID"
    echo "💻 CPU: ${CPU}%"
    echo "🧠 Memory: ${MEM}%"
    echo "⏱️  Uptime: $UPTIME"
else
    echo "❌ Статус: НЕ РАБОТИ"
fi
echo ""

# 2. AUTO-FIXER
echo "2️⃣ AUTO-FIXER (15 min грешки)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
FIXER_PID=$(pgrep -f "python3.*auto_fixer.py" | head -1)
if [ -n "$FIXER_PID" ]; then
    PS_INFO=$(ps -p "$FIXER_PID" -o %cpu,%mem,etime --no-headers)
    CPU=$(echo "$PS_INFO" | awk '{print $1}')
    MEM=$(echo "$PS_INFO" | awk '{print $2}')
    UPTIME=$(echo "$PS_INFO" | awk '{print $3}')
    
    echo "✅ Статус: РАБОТИ"
    echo "🆔 PID: $FIXER_PID"
    echo "💻 CPU: ${CPU}%"
    echo "🧠 Memory: ${MEM}%"
    echo "⏱️  Uptime: $UPTIME"
else
    echo "❌ Статус: НЕ РАБОТИ"
fi
echo ""

# 3. WATCHDOG
echo "3️⃣ WATCHDOG (2 min health check)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
WATCHDOG_PID=$(pgrep -f "python3.*bot_watchdog.py" | head -1)
if [ -n "$WATCHDOG_PID" ]; then
    PS_INFO=$(ps -p "$WATCHDOG_PID" -o %cpu,%mem,etime --no-headers)
    CPU=$(echo "$PS_INFO" | awk '{print $1}')
    MEM=$(echo "$PS_INFO" | awk '{print $2}')
    UPTIME=$(echo "$PS_INFO" | awk '{print $3}')
    
    echo "✅ Статус: РАБОТИ"
    echo "🆔 PID: $WATCHDOG_PID"
    echo "💻 CPU: ${CPU}%"
    echo "🧠 Memory: ${MEM}%"
    echo "⏱️  Uptime: $UPTIME"
else
    echo "❌ Статус: НЕ РАБОТИ"
fi
echo ""

# 4. TELEGRAM CONNECTION
echo "4️⃣ TELEGRAM API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TELEGRAM_CHECK=$(curl -s "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe" | grep -o '"ok":true')
if [ -n "$TELEGRAM_CHECK" ]; then
    echo "✅ Връзка: АКТИВНА"
else
    echo "❌ Връзка: НЯМА"
fi
echo ""

# 5. ПОСЛЕДНА АКТИВНОСТ
echo "5️⃣ ПОСЛЕДНА АКТИВНОСТ"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ -f "/workspaces/Crypto-signal-bot/bot.log" ]; then
    LAST_LOG=$(tail -1 /workspaces/Crypto-signal-bot/bot.log)
    echo "$LAST_LOG" | head -c 200
    echo "..."
else
    echo "❌ Няма log файл"
fi
echo ""
echo ""

# 6. SUMMARY
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

TOTAL=0
RUNNING=0

if [ -n "$BOT_PID" ]; then RUNNING=$((RUNNING+1)); fi
TOTAL=$((TOTAL+1))

if [ -n "$FIXER_PID" ]; then RUNNING=$((RUNNING+1)); fi
TOTAL=$((TOTAL+1))

if [ -n "$WATCHDOG_PID" ]; then RUNNING=$((RUNNING+1)); fi
TOTAL=$((TOTAL+1))

echo "Работещи системи: $RUNNING/$TOTAL"

if [ "$RUNNING" -eq "$TOTAL" ]; then
    echo "🎉 Всички системи работят отлично!"
elif [ "$RUNNING" -gt 0 ]; then
    echo "⚠️ Някои системи не работят"
else
    echo "❌ Няма работещи системи"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
