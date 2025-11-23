#!/bin/bash

# 🔄 Автоматичен Backup Script
# Създава ежедневни backups на важни файлове

BACKUP_DIR="/workspaces/Crypto-signal-bot/admin/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Създай backup директория ако не съществува
mkdir -p "$BACKUP_DIR"

echo "🔄 Стартиране на backup процес..."

# Backup на bot_stats.json
if [ -f "/workspaces/Crypto-signal-bot/bot_stats.json" ]; then
    cp /workspaces/Crypto-signal-bot/bot_stats.json "$BACKUP_DIR/bot_stats_$DATE.json"
    echo "✅ bot_stats.json backup създаден"
fi

# Backup на credentials.json
if [ -f "/workspaces/Crypto-signal-bot/admin/credentials.json" ]; then
    cp /workspaces/Crypto-signal-bot/admin/credentials.json "$BACKUP_DIR/credentials_$DATE.json"
    echo "✅ credentials.json backup създаден"
fi

# Backup на admin_password.json
if [ -f "/workspaces/Crypto-signal-bot/admin/admin_password.json" ]; then
    cp /workspaces/Crypto-signal-bot/admin/admin_password.json "$BACKUP_DIR/admin_password_$DATE.json"
    echo "✅ admin_password.json backup създаден"
fi

# Изтрий backups по-стари от 30 дни
find "$BACKUP_DIR" -name "*.json" -type f -mtime +30 -delete
echo "🗑️ Стари backups изтрити (>30 дни)"

echo "✅ Backup процес завършен!"
