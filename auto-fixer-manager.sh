#!/bin/bash
# Auto-Fixer Manager - Управление на автоматичния мониторинг

WORKSPACE="/workspaces/Crypto-signal-bot"
FIXER_SCRIPT="$WORKSPACE/auto_fixer.py"
PID_FILE="$WORKSPACE/auto_fixer.pid"
LOG_FILE="$WORKSPACE/auto_fixer.log"

start() {
    # Проверка дали вече работи
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "⚠️  Auto-fixer вече работи (PID: $PID)"
            return 1
        fi
    fi
    
    # Стартиране във фонов режим
    echo "🚀 Стартиране на auto-fixer..."
    nohup python3 "$FIXER_SCRIPT" >> "$LOG_FILE" 2>&1 &
    NEW_PID=$!
    echo $NEW_PID > "$PID_FILE"
    
    # Проверка дали стартира успешно
    sleep 2
    if ps -p "$NEW_PID" > /dev/null 2>&1; then
        echo "✅ Auto-fixer стартиран (PID: $NEW_PID)"
        echo "📁 Логове: $LOG_FILE"
        return 0
    else
        echo "❌ Грешка при стартиране"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️  Auto-fixer не работи (няма PID файл)"
        return 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ! ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️  Auto-fixer не работи (невалиден PID)"
        rm -f "$PID_FILE"
        return 1
    fi
    
    echo "🛑 Спиране на auto-fixer (PID: $PID)..."
    kill "$PID" 2>/dev/null
    sleep 2
    
    # Force kill ако е нужно
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "⚠️  Принудително спиране..."
        kill -9 "$PID" 2>/dev/null
        sleep 1
    fi
    
    rm -f "$PID_FILE"
    echo "✅ Auto-fixer спрян"
    return 0
}

restart() {
    echo "🔄 Рестартиране на auto-fixer..."
    stop
    sleep 2
    start
}

status() {
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "📊 AUTO-FIXER STATUS"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ Статус: РАБОТИ"
            echo "🆔 PID: $PID"
            
            # CPU и Memory
            PS_INFO=$(ps -p "$PID" -o %cpu,%mem,etime --no-headers)
            CPU=$(echo "$PS_INFO" | awk '{print $1}')
            MEM=$(echo "$PS_INFO" | awk '{print $2}')
            UPTIME=$(echo "$PS_INFO" | awk '{print $3}')
            
            echo "💻 CPU: ${CPU}%"
            echo "🧠 Memory: ${MEM}%"
            echo "⏱️  Uptime: $UPTIME"
            
            # Последни проверки от лога
            if [ -f "$LOG_FILE" ]; then
                echo ""
                echo "📝 ПОСЛЕДНИ ПРОВЕРКИ:"
                echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
                grep -E "АВТОМАТИЧНА ПРОВЕРКА|ОТСТРАНЕНИ ПРОБЛЕМИ|Няма проблеми" "$LOG_FILE" | tail -10
            fi
        else
            echo "❌ Статус: НЕ РАБОТИ (невалиден PID)"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ Статус: НЕ РАБОТИ (няма PID файл)"
    fi
    
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -n 50 "$LOG_FILE"
    else
        echo "❌ Няма log файл"
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
    logs)
        logs
        ;;
    *)
        echo "Употреба: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "  start   - Стартира auto-fixer"
        echo "  stop    - Спира auto-fixer"
        echo "  restart - Рестартира auto-fixer"
        echo "  status  - Показва статус"
        echo "  logs    - Показва логове"
        exit 1
        ;;
esac
