#!/bin/bash

# 🔧 FIX SYSTEMD SERVICE - Премахва Telegram Conflict error

echo "🔧 Поправка на crypto-bot.service..."

# Backup на стария файл
cp /etc/systemd/system/crypto-bot.service /etc/systemd/system/crypto-bot.service.backup
echo "✅ Backup: /etc/systemd/system/crypto-bot.service.backup"

# Създай новия service файл
cat > /etc/systemd/system/crypto-bot.service << 'EOF'
[Unit]
Description=Crypto Signal Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/Crypto-signal-bot
Environment="PATH=/root/Crypto-signal-bot/venv/bin"

# Убий стари процеси преди старт
ExecStartPre=/bin/sh -c '/usr/bin/pkill -9 -f "python.*bot.py" || true'
ExecStartPre=/bin/sleep 3

# Стартирай бота
ExecStart=/root/Crypto-signal-bot/venv/bin/python3 bot.py

# Убий процеси при спиране
ExecStop=/bin/sh -c '/usr/bin/pkill -9 -f "python.*bot.py" || true'

# Рестарт настройки
Restart=always
RestartSec=5
TimeoutStopSec=10
TimeoutStartSec=30

# Логове
StandardOutput=append:/root/Crypto-signal-bot/bot.log
StandardError=append:/root/Crypto-signal-bot/bot.log

[Install]
WantedBy=multi-user.target
EOF

echo "✅ Нов service файл създаден"

# Reload systemd
systemctl daemon-reload
echo "✅ Systemd daemon-reload"

# Рестартирай службата
systemctl stop crypto-bot
sleep 3
pkill -9 -f "python.*bot.py" 2>/dev/null || true
sleep 2
systemctl start crypto-bot

echo ""
echo "✅ Service поправен и рестартиран!"
echo ""
echo "📋 Проверка:"
ps aux | grep "[p]ython.*bot.py"

echo ""
echo "📊 Статус:"
systemctl status crypto-bot --no-pager -l
