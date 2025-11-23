#!/bin/bash

# ===============================================
# SUPERVISOR SCRIPT - Автоматичен restart при crash
# ===============================================

LOG_FILE="/workspaces/Crypto-signal-bot/supervisor.log"
BOT_FILE="/workspaces/Crypto-signal-bot/bot.py"
MAX_RETRIES=999999  # Безкрайни рестарти

echo "🚀 Supervisor started at $(date)" >> $LOG_FILE

retry_count=0

while [ $retry_count -lt $MAX_RETRIES ]; do
    echo "▶️  Starting bot (attempt $((retry_count + 1)))..." >> $LOG_FILE
    
    # Стартирай бота
    cd /workspaces/Crypto-signal-bot
    python3 $BOT_FILE
    
    # Ако бота спре, запиши причината
    exit_code=$?
    echo "⚠️  Bot stopped with exit code $exit_code at $(date)" >> $LOG_FILE
    
    # Изчакай 5 секунди преди рестарт
    echo "⏳ Waiting 5 seconds before restart..." >> $LOG_FILE
    sleep 5
    
    retry_count=$((retry_count + 1))
done

echo "❌ Max retries reached. Stopping supervisor." >> $LOG_FILE
