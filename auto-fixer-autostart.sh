#!/bin/bash
# Auto-start скрипт за auto-fixer и watchdog
# Добавя се в .bashrc за автоматично стартиране

WORKSPACE="/workspaces/Crypto-signal-bot"
FIXER_MANAGER="$WORKSPACE/auto-fixer-manager.sh"
WATCHDOG_MANAGER="$WORKSPACE/watchdog-manager.sh"

# Проверка дали auto-fixer работи
if ! pgrep -f "python3.*auto_fixer.py" > /dev/null; then
    # Не работи - стартирай го
    "$FIXER_MANAGER" start > /dev/null 2>&1
fi

# Проверка дали watchdog работи
if ! pgrep -f "python3.*bot_watchdog.py" > /dev/null; then
    # Не работи - стартирай го
    "$WATCHDOG_MANAGER" start > /dev/null 2>&1
fi
