#!/bin/bash

# 🔙 ROLLBACK TO STABLE VERSION
# Returns bot to commit 1f163c3 (pre-scenario system)

echo "🔙 Starting rollback to stable version (1f163c3)..."

# Navigate to bot directory
BOT_DIR="/root/Crypto-signal-bot"
cd "$BOT_DIR" || exit 1

# Stop the bot service first
echo "⏹️  Stopping bot service..."
systemctl stop crypto-bot

# Create backup branch (safety net)
echo "💾 Creating backup branch..."
BACKUP_BRANCH="backup-before-reset-$(date +%Y%m%d-%H%M%S)"
git branch "$BACKUP_BRANCH"
echo "✅ Backup created: $BACKUP_BRANCH"

# Verify commit exists
if ! git cat-file -e 1f163c3^{commit} 2>/dev/null; then
    echo "❌ ERROR: Commit 1f163c3 not found!"
    echo "📋 Available recent commits:"
    git log --oneline -20
    exit 1
fi

# Show what will be lost
echo ""
echo "⚠️  COMMITS THAT WILL BE REMOVED:"
git log --oneline 1f163c3..HEAD
echo ""

# Confirmation (optional - remove for full automation)
read -p "❓ Continue with rollback? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
    echo "❌ Rollback cancelled"
    systemctl start crypto-bot
    exit 0
fi

# Perform the rollback
echo "🔄 Performing hard reset to 1f163c3..."
git reset --hard 1f163c3

# Clear Python cache
echo "🗑️  Clearing Python cache..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true

# Force push to GitHub
echo "📤 Force pushing to GitHub..."
git push --force origin main

# Restart bot service
echo "🚀 Restarting bot service..."
systemctl daemon-reload
systemctl start crypto-bot
sleep 3

# Check status
echo ""
echo "✅ Rollback complete!"
echo ""
echo "📊 Service status:"
systemctl status crypto-bot --no-pager
echo ""
echo "📋 Check logs: journalctl -u crypto-bot -f"
echo "💾 Backup branch: $BACKUP_BRANCH"
echo "🔄 To restore backup: git reset --hard $BACKUP_BRANCH"
