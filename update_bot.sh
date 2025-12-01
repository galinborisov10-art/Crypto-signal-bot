#!/bin/bash
# update_bot.sh - Script to update, install dependencies, and restart the Crypto Signal Bot
# Location: Can be run from any location

set -e

# Configuration - detect project directory dynamically
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${CRYPTO_BOT_DIR:-$SCRIPT_DIR}"
LOG_FILE="${PROJECT_DIR}/update_bot.log"
TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "[${TIMESTAMP}] $1" | tee -a "${LOG_FILE}"
}

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" | tee -a "${LOG_FILE}"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" | tee -a "${LOG_FILE}"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "${LOG_FILE}"
}

# Start update process
log "=========================================="
log "🚀 Starting bot update process..."
log "=========================================="

# Navigate to project directory
cd "${PROJECT_DIR}" || { log_error "Failed to cd to ${PROJECT_DIR}"; exit 1; }
log_info "Working directory: $(pwd)"

# Step 1: Pull latest changes from GitHub
log_info "Step 1: Pulling latest changes from GitHub..."
git fetch origin main
git reset --hard origin/main
log_info "✅ Git pull completed"

# Step 2: Install dependencies
log_info "Step 2: Installing dependencies..."
if [ -f "install_dependencies.sh" ]; then
    chmod +x install_dependencies.sh
    ./install_dependencies.sh
else
    pip install -r requirements.txt --quiet
fi
log_info "✅ Dependencies installed"

# Step 3: Clean Python caches
log_info "Step 3: Cleaning Python caches..."
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find . -type f -name "*.pyc" -delete 2>/dev/null || true
log_info "✅ Caches cleaned"

# Step 4: Restart bot via PM2
log_info "Step 4: Restarting bot via PM2..."
pm2 stop crypto-bot 2>/dev/null || true
pkill -f "python.*bot.py" 2>/dev/null || true
sleep 2

if [ -f "ecosystem.config.js" ]; then
    pm2 start ecosystem.config.js --update-env
else
    pm2 start bot.py --name crypto-bot --interpreter python3
fi
log_info "✅ Bot restarted"

# Step 5: Verify bot process
log_info "Step 5: Verifying bot process..."
sleep 3
if pm2 list | grep -q "crypto-bot"; then
    if pm2 list | grep "crypto-bot" | grep -q "online"; then
        log_info "✅ Bot is running successfully"
        pm2 logs crypto-bot --lines 10 --nostream 2>&1 | tee -a "${LOG_FILE}"
    else
        log_warn "⚠️ Bot process exists but may not be online"
        pm2 list | tee -a "${LOG_FILE}"
    fi
else
    log_error "❌ Bot process not found in PM2"
    exit 1
fi

log "=========================================="
log "🎉 Update completed successfully!"
log "=========================================="

exit 0
