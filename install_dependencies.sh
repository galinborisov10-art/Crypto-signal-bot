#!/bin/bash
# =============================================================================
# install_dependencies.sh - Dependency Auto-Installer for Crypto Signal Bot
# =============================================================================
# This script ensures all required dependencies are installed
# Usage: ./install_dependencies.sh
# =============================================================================

set -e

# Get the directory where the script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📦 CRYPTO SIGNAL BOT - DEPENDENCY INSTALLER"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Determine pip command
if command -v pip3 &> /dev/null; then
    PIP_CMD="pip3"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
else
    echo "❌ Python pip is not installed!"
    exit 1
fi

echo "📋 Using: $PIP_CMD"
echo ""

# Install from requirements.txt
echo "📥 Installing dependencies from requirements.txt..."
$PIP_CMD install -r requirements.txt --upgrade

echo ""
echo "🔍 Verifying critical dependencies..."

# List of critical modules to verify
CRITICAL_MODULES=(
    "telegram:python-telegram-bot"
    "feedparser:feedparser"
    "deep_translator:deep-translator"
    "dotenv:python-dotenv"
    "apscheduler:APScheduler"
    "pandas:pandas"
    "numpy:numpy"
    "requests:requests"
    "mplfinance:mplfinance"
    "matplotlib:matplotlib"
    "ta:ta"
)

MISSING_PACKAGES=""

for MODULE_INFO in "${CRITICAL_MODULES[@]}"; do
    MODULE_NAME="${MODULE_INFO%%:*}"
    PACKAGE_NAME="${MODULE_INFO##*:}"
    
    if python3 -c "import $MODULE_NAME" 2>/dev/null; then
        echo "  ✅ $MODULE_NAME"
    else
        echo "  ❌ $MODULE_NAME (installing $PACKAGE_NAME...)"
        $PIP_CMD install "$PACKAGE_NAME" --quiet
        
        # Verify after install
        if python3 -c "import $MODULE_NAME" 2>/dev/null; then
            echo "     ✅ Installed successfully"
        else
            echo "     ❌ Failed to install"
            MISSING_PACKAGES="$MISSING_PACKAGES $PACKAGE_NAME"
        fi
    fi
done

echo ""

if [ -n "$MISSING_PACKAGES" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "⚠️ Some packages failed to install:$MISSING_PACKAGES"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    exit 1
else
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "✅ ALL DEPENDENCIES INSTALLED SUCCESSFULLY!"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
fi
