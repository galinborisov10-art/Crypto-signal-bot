#!/bin/bash
# install_dependencies.sh - Script to detect and install missing critical packages
# Location: /root/Crypto-signal-bot/install_dependencies.sh

set -e

# Configuration
PROJECT_DIR="/root/Crypto-signal-bot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}=========================================="
echo "📦 Crypto Signal Bot - Dependency Installer"
echo -e "==========================================${NC}"

# Navigate to project directory
cd "${PROJECT_DIR}" 2>/dev/null || cd "$(dirname "$0")"
echo "Working directory: $(pwd)"

# Critical packages that must be installed
CRITICAL_PACKAGES=(
    "python-telegram-bot"
    "feedparser"
    "deep-translator"
    "python-dotenv"
    "APScheduler"
    "mplfinance"
    "pandas"
    "numpy"
    "requests"
    "matplotlib"
    "ta"
    "scikit-learn"
    "beautifulsoup4"
    "schedule"
)

# Function to check if a Python package is installed
check_package() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

# Map package names to import names
declare -A IMPORT_NAMES
IMPORT_NAMES["python-telegram-bot"]="telegram"
IMPORT_NAMES["python-dotenv"]="dotenv"
IMPORT_NAMES["APScheduler"]="apscheduler"
IMPORT_NAMES["beautifulsoup4"]="bs4"
IMPORT_NAMES["scikit-learn"]="sklearn"
IMPORT_NAMES["deep-translator"]="deep_translator"

MISSING_PACKAGES=()

echo ""
echo "🔍 Checking critical packages..."
echo ""

for pkg in "${CRITICAL_PACKAGES[@]}"; do
    # Get the import name (use mapping or default to package name with - replaced by _)
    import_name="${IMPORT_NAMES[$pkg]:-${pkg//-/_}}"
    
    if check_package "$import_name"; then
        echo -e "  ✅ ${GREEN}${pkg}${NC} - installed"
    else
        echo -e "  ❌ ${RED}${pkg}${NC} - MISSING"
        MISSING_PACKAGES+=("$pkg")
    fi
done

echo ""

# Install missing packages
if [ ${#MISSING_PACKAGES[@]} -eq 0 ]; then
    echo -e "${GREEN}✅ All critical packages are installed!${NC}"
else
    echo -e "${YELLOW}📥 Installing ${#MISSING_PACKAGES[@]} missing package(s)...${NC}"
    echo ""
    
    for pkg in "${MISSING_PACKAGES[@]}"; do
        echo -e "  Installing ${pkg}..."
        pip install "$pkg" --quiet
        if [ $? -eq 0 ]; then
            echo -e "    ✅ ${GREEN}${pkg}${NC} installed successfully"
        else
            echo -e "    ❌ ${RED}Failed to install ${pkg}${NC}"
        fi
    done
    
    echo ""
fi

# Also install from requirements.txt if it exists
if [ -f "requirements.txt" ]; then
    echo "📋 Installing from requirements.txt..."
    pip install -r requirements.txt --quiet
    echo -e "${GREEN}✅ requirements.txt packages installed${NC}"
fi

echo ""
echo -e "${GREEN}=========================================="
echo "🎉 Dependency installation complete!"
echo -e "==========================================${NC}"

exit 0
