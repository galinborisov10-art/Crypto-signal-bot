#!/bin/bash

# ===============================================
# BOT SERVICE - Systemd-style service за Codespace
# ===============================================

SCRIPT_DIR="/workspaces/Crypto-signal-bot"
PID_FILE="$SCRIPT_DIR/bot.pid"
LOG_FILE="$SCRIPT_DIR/bot-service.log"

start_bot() {
    echo "🚀 Starting Crypto Signal Bot..." | tee -a $LOG_FILE
    
    # Провери дали вече работи
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            echo "⚠️  Bot already running (PID: $PID)" | tee -a $LOG_FILE
            return 1
        else
            echo "🧹 Cleaning stale PID file" | tee -a $LOG_FILE
            rm -f $PID_FILE
        fi
    fi
    
    # Стартирай с supervisor
    cd $SCRIPT_DIR
    nohup bash supervisor.sh >> $LOG_FILE 2>&1 &
    echo $! > $PID_FILE
    
    echo "✅ Bot started with PID: $(cat $PID_FILE)" | tee -a $LOG_FILE
}

stop_bot() {
    echo "🛑 Stopping Crypto Signal Bot..." | tee -a $LOG_FILE
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        
        # Убий процеса
        kill $PID 2>/dev/null
        
        # Изчакай до 10 секунди
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                break
            fi
            sleep 1
        done
        
        # Force kill ако не е спрял
        if ps -p $PID > /dev/null 2>&1; then
            echo "⚠️  Force killing bot..." | tee -a $LOG_FILE
            kill -9 $PID 2>/dev/null
        fi
        
        rm -f $PID_FILE
        echo "✅ Bot stopped" | tee -a $LOG_FILE
    else
        echo "ℹ️  Bot is not running" | tee -a $LOG_FILE
    fi
    
    # Убий всички Python bot процеси
    pkill -f "python.*bot.py"
}

restart_bot() {
    echo "🔄 Restarting Crypto Signal Bot..." | tee -a $LOG_FILE
    stop_bot
    sleep 2
    start_bot
}

status_bot() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat $PID_FILE)
        if ps -p $PID > /dev/null 2>&1; then
            echo "✅ Bot is running (PID: $PID)"
            
            # Покажи uptime
            ps -p $PID -o etime= | xargs echo "⏱️  Uptime:"
            
            # Покажи memory usage
            ps -p $PID -o %mem= | xargs echo "💾 Memory:"
            
            return 0
        else
            echo "❌ Bot is not running (stale PID file)"
            return 1
        fi
    else
        echo "❌ Bot is not running"
        return 1
    fi
}

case "$1" in
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        status_bot
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
