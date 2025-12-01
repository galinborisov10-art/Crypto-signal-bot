#!/bin/bash

# ============================================
# DEPENDENCY INSTALLER & CHECKER
# ============================================
# Автоматично инсталира и проверява dependencies

echo "🔍 Проверка на dependencies..."

# Директория на проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

# Цветове
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Проверка дали има requirements.txt
if [ ! -f "requirements.txt" ]; then
    echo -e "${RED}❌ requirements.txt не е намерен!${NC}"
    exit 1
fi

# Функция за проверка дали модул е инсталиран
check_module() {
    python3 -c "import $1" 2>/dev/null
    return $?
}

# Инсталация на dependencies
echo -e "${YELLOW}📦 Инсталиране на dependencies...${NC}"
pip3 install -r requirements.txt --upgrade --quiet

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Всички dependencies са инсталирани успешно!${NC}"
else
    echo -e "${RED}❌ Грешка при инсталация на dependencies${NC}"
    exit 1
fi

# Проверка на критични модули
echo ""
echo -e "${YELLOW}🔍 Проверка на критични модули...${NC}"

CRITICAL_MODULES=(
    "telegram"
    "requests"
    "pandas"
    "numpy"
    "matplotlib"
    "sklearn"
    "apscheduler"
    "bs4"
    "feedparser"
)

MISSING_MODULES=()

for module in "${CRITICAL_MODULES[@]}"; do
    if check_module "$module"; then
        echo -e "${GREEN}  ✓ $module${NC}"
    else
        echo -e "${RED}  ✗ $module - ЛИПСВА${NC}"
        MISSING_MODULES+=("$module")
    fi
done

# Резултат
echo ""
if [ ${#MISSING_MODULES[@]} -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}✅ Всички модули са налични!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}❌ Липсващи модули: ${MISSING_MODULES[*]}${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "💡 Опитайте:"
    echo "   pip3 install ${MISSING_MODULES[*]}"
    exit 1
fi
