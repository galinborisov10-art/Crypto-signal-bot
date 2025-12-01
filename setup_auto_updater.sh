#!/bin/bash

# ============================================
# AUTO-UPDATER CRON SETUP
# ============================================
# Настройва cron job за автоматичен daily update

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
UPDATER_SCRIPT="$SCRIPT_DIR/auto_updater.py"

echo "🔧 Setting up auto-updater cron job..."

# Make updater executable
chmod +x "$UPDATER_SCRIPT"

# Setup cron job (runs daily at 04:00)
CRON_CMD="0 4 * * * cd $SCRIPT_DIR && python3 auto_updater.py >> $SCRIPT_DIR/auto_updater.log 2>&1"

# Check if cron job already exists
if crontab -l 2>/dev/null | grep -q "auto_updater.py"; then
    echo "✅ Cron job already exists"
else
    # Add to crontab
    (crontab -l 2>/dev/null; echo "$CRON_CMD") | crontab -
    echo "✅ Cron job added: Daily at 04:00"
fi

echo ""
echo "📋 Current cron jobs:"
crontab -l | grep "auto_updater"

echo ""
echo "💡 Commands:"
echo "   python3 auto_updater.py    - Run update manually"
echo "   crontab -l                 - View cron jobs"
echo "   crontab -e                 - Edit cron jobs"
echo ""
