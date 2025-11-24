#!/bin/bash
# Automatic Startup Script for Codespace
# Стартира бота и keep-alive автоматично

echo "🚀 =========================================="
echo "🚀 Crypto Signal Bot - Auto Startup"
echo "🚀 =========================================="

# Чакай network да е готов
sleep 2

# Стартирай бота ако не е вече стартиран
if ! ps aux | grep -q "[p]ython3 bot.py"; then
    echo "🤖 Starting bot..."
    cd /workspaces/Crypto-signal-bot
    nohup python3 bot.py > /tmp/bot.log 2>&1 &
    sleep 3
    echo "✅ Bot started (PID: $!)"
else
    echo "✅ Bot is already running"
fi

# Стартирай keep-alive ако не е вече стартиран
if ! ps aux | grep -q "[k]eep_codespace_alive.sh"; then
    echo "🔄 Starting keep-alive..."
    cd /workspaces/Crypto-signal-bot
    nohup ./keep_codespace_alive.sh > /tmp/keepalive_output.log 2>&1 &
    sleep 2
    echo "✅ Keep-alive started (PID: $!)"
else
    echo "✅ Keep-alive is already running"
fi

echo ""
echo "📊 Status:"
echo "=========================================="
ps aux | grep -E "(python3 bot.py|keep_codespace_alive)" | grep -v grep
echo "=========================================="
echo ""
echo "✅ All systems operational!"
echo "📝 Bot logs: tail -f /tmp/bot.log"
echo "📝 Keep-alive logs: tail -f /tmp/codespace_keepalive.log"
