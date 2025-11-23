#!/bin/bash
# Auto-start скрипт за Codespaces
# Добави този скрипт в ~/.bashrc или създай като startup script

# Проверява дали ботът работи и го стартира ако не
check_and_start_bot() {
    BOT_DIR="/workspaces/Crypto-signal-bot"
    
    if [ ! -d "$BOT_DIR" ]; then
        return 0
    fi
    
    # Провери дали ботът работи
    if pgrep -f "python3.*bot.py" > /dev/null; then
        echo "✅ Crypto Bot вече работи"
        return 0
    fi
    
    # Стартирай бота
    echo "🚀 Стартирам Crypto Bot..."
    cd "$BOT_DIR"
    ./bot-manager.sh start
}

# Изпълни проверката
check_and_start_bot
