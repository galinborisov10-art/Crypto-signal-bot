#!/bin/bash

# Railway.app Health Check Script
# Keeps the bot alive by responding to HTTP health checks

echo "🚀 Starting Crypto Signal Bot..."
echo "📍 Railway.app deployment"
echo "⏰ $(date)"

# Start bot in background
python3 bot.py &
BOT_PID=$!

echo "✅ Bot started with PID: $BOT_PID"

# Keep alive - respond to health checks
while kill -0 $BOT_PID 2>/dev/null; do
    sleep 60
done

echo "❌ Bot stopped. Exiting..."
exit 1
