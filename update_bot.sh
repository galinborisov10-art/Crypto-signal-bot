#!/bin/bash

# ============================================
# UPDATE BOT - Server-side Update Script
# ============================================
# Този скрипт pull-ва последната версия от GitHub,
# инсталира dependencies и рестартира бота с PM2

set -e  # Exit on error

# Цветове
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Лого
echo -e "${BLUE}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   🔄 CRYPTO BOT AUTO-UPDATE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${NC}"

# Определяне на директорията на проекта
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

echo -e "${YELLOW}📂 Работна директория: ${PROJECT_DIR}${NC}"
echo ""

# Стъпка 1: Backup на конфигурация
echo -e "${YELLOW}💾 Създаване на backup...${NC}"
mkdir -p backups
BACKUP_FILE="backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz"
tar -czf "$BACKUP_FILE" \
    bot_stats.json \
    trading_journal.json \
    daily_reports.json \
    news_cache.json \
    admin/credentials.json \
    2>/dev/null || echo "  ⚠️ Някои файлове не са намерени"

if [ -f "$BACKUP_FILE" ]; then
    echo -e "${GREEN}  ✓ Backup създаден: $BACKUP_FILE${NC}"
else
    echo -e "${YELLOW}  ⚠️ Backup не е създаден (може да няма файлове)${NC}"
fi
echo ""

# Стъпка 2: Git Pull
echo -e "${YELLOW}📥 Pulling latest changes from GitHub...${NC}"
git fetch origin
CURRENT_COMMIT=$(git rev-parse HEAD)
LATEST_COMMIT=$(git rev-parse origin/main)

if [ "$CURRENT_COMMIT" == "$LATEST_COMMIT" ]; then
    echo -e "${GREEN}  ✓ Вече сте на последната версия!${NC}"
else
    git pull origin main
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Успешно обновяване от GitHub${NC}"
        NEW_VERSION=$(git log -1 --pretty=format:"%h - %s")
        echo -e "${BLUE}  📝 Последен commit: $NEW_VERSION${NC}"
    else
        echo -e "${RED}  ✗ Грешка при git pull${NC}"
        exit 1
    fi
fi
echo ""

# Стъпка 3: Проверка за промени в requirements.txt
echo -e "${YELLOW}📦 Проверка на dependencies...${NC}"

# Проверка за venv
if [ -d "venv" ]; then
    echo -e "${BLUE}  🐍 Намерен virtual environment - активиране...${NC}"
    source venv/bin/activate
    PIP_CMD="pip"
else
    echo -e "${YELLOW}  ⚠️ Няма venv - използване на system pip${NC}"
    PIP_CMD="pip3 --break-system-packages"
fi

if git diff --name-only "$CURRENT_COMMIT" "$LATEST_COMMIT" | grep -q "requirements.txt"; then
    echo -e "${YELLOW}  ⚠️ requirements.txt е променен - обновяване на dependencies...${NC}"
    $PIP_CMD install -r requirements.txt --upgrade
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Dependencies обновени успешно${NC}"
    else
        echo -e "${RED}  ✗ Грешка при обновяване на dependencies${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}  ✓ requirements.txt не е променен${NC}"
    # Все пак инсталирай ако липсват
    $PIP_CMD install -r requirements.txt --quiet 2>/dev/null || true
fi
echo ""

# Стъпка 4: Рестартиране на PM2/Manual
echo -e "${YELLOW}🔄 Рестартиране на бота...${NC}"

# Проверка дали PM2 е инсталиран
if command -v pm2 &> /dev/null && pm2 list | grep -q "crypto-bot"; then
    echo -e "${YELLOW}  ⟳ Рестартиране с PM2...${NC}"
    pm2 restart crypto-bot
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Бот рестартиран успешно${NC}"
    else
        echo -e "${RED}  ✗ Грешка при рестартиране${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}  ⟳ Manual рестартиране...${NC}"
    pkill -f bot.py || true
    sleep 2
    
    if [ -d "venv" ]; then
        nohup venv/bin/python bot.py > bot.log 2>&1 &
        echo -e "${GREEN}  ✓ Бот стартиран с venv/bin/python${NC}"
    else
        nohup python3 bot.py > bot.log 2>&1 &
        echo -e "${GREEN}  ✓ Бот стартиран с python3${NC}"
    fi
    
    sleep 3
    if pgrep -f "bot.py" > /dev/null; then
        echo -e "${GREEN}  ✓ Бот работи успешно${NC}"
    else
        echo -e "${RED}  ✗ Бот не стартира - проверете bot.log${NC}"
        exit 1
    fi
fi
echo ""

# Стъпка 5: Проверка на статуса
echo -e "${YELLOW}📊 Статус на бота:${NC}"
if command -v pm2 &> /dev/null && pm2 list | grep -q "crypto-bot"; then
    pm2 status crypto-bot
else
    if pgrep -f "bot.py" > /dev/null; then
        PID=$(pgrep -f "bot.py")
        echo -e "${GREEN}  ✓ Bot running (PID: $PID)${NC}"
    else
        echo -e "${RED}  ✗ Bot не работи${NC}"
    fi
fi
echo ""

# Стъпка 6: Показване на логове (последните 20 реда)
echo -e "${YELLOW}📜 Последни логове:${NC}"
if command -v pm2 &> /dev/null && pm2 list | grep -q "crypto-bot"; then
    pm2 logs crypto-bot --lines 20 --nostream
else
    if [ -f "bot.log" ]; then
        tail -20 bot.log
    else
        echo -e "${YELLOW}  ⚠️ Няма логове${NC}"
    fi
fi
echo ""

# Финален резултат
echo -e "${GREEN}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   ✅ UPDATE ЗАВЪРШЕН УСПЕШНО!"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "${NC}"

echo -e "${BLUE}💡 Полезни команди:${NC}"
echo "   pm2 logs crypto-bot    - Преглед на логове"
echo "   pm2 restart crypto-bot - Рестартиране"
echo "   pm2 stop crypto-bot    - Спиране"
echo "   pm2 monit             - Мониторинг в реално време"
echo ""

exit 0
