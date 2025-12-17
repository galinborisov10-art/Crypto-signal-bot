#!/bin/bash
# Crypto Signal Bot - Постоянно работещ скрипт

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$SCRIPT_DIR/bot.log"
PID_FILE="$SCRIPT_DIR/bot.pid"

start() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            echo "✅ Ботът вече работи (PID: $PID)"
            return 0
        fi
    fi
    
    echo "🚀 Стартирам бота..."
    cd "$SCRIPT_DIR"
    nohup python3 bot.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"
    sleep 2
    
    if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
        echo "✅ Ботът стартира успешно (PID: $(cat $PID_FILE))"
    else
        echo "❌ Грешка при стартиране"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️ Ботът не работи"
        return 0
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "🛑 Спирам бота (PID: $PID)..."
        kill $PID
        sleep 2
        
        if ps -p $PID > /dev/null 2>&1; then
            echo "⚠️ Принудително спиране..."
            kill -9 $PID
        fi
        
        rm -f "$PID_FILE"
        echo "✅ Ботът е спрян"
    else
        echo "⚠️ Процесът не работи"
        rm -f "$PID_FILE"
    fi
}

restart() {
    echo "🔄 Рестартирам бота..."
    stop
    sleep 1
    start
}

status() {
    if [ ! -f "$PID_FILE" ]; then
        echo "❌ Ботът НЕ работи"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    if ps -p $PID > /dev/null 2>&1; then
        echo "✅ Ботът работи (PID: $PID)"
        echo ""
        echo "📊 Последни логове:"
        tail -n 5 "$LOG_FILE" | grep -E "(🚀|✅|🔔|ERROR)"
        return 0
    else
        echo "❌ Процесът не работи (грешен PID в файла)"
        rm -f "$PID_FILE"
        return 1
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    *)
        echo "Употреба: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac

exit 0
