#!/bin/bash
# Keep Codespace Alive Script
# Прави периодични операции за да не спре Codespace

echo "🚀 Starting Codespace Keep-Alive..."

while true; do
    # Текущо време
    current_time=$(date '+%Y-%m-%d %H:%M:%S')
    
    # Dummy операции
    echo "[$current_time] ✅ Codespace is alive" >> /tmp/codespace_keepalive.log
    
    # Git fetch за активност
    cd /workspaces/Crypto-signal-bot
    git fetch --quiet 2>/dev/null || true
    
    # Провери статус на бота
    if ps aux | grep -q "[p]ython3 bot.py"; then
        echo "[$current_time] 🤖 Bot is running" >> /tmp/codespace_keepalive.log
    else
        echo "[$current_time] ⚠️  Bot is NOT running" >> /tmp/codespace_keepalive.log
    fi
    
    # Запази log файла (за да се запише на диска)
    tail -100 /tmp/codespace_keepalive.log > /tmp/codespace_keepalive_tmp.log
    mv /tmp/codespace_keepalive_tmp.log /tmp/codespace_keepalive.log
    
    # Чакай 5 минути
    sleep 300
done
