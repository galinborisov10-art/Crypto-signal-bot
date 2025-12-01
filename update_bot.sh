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
if git diff --name-only "$CURRENT_COMMIT" "$LATEST_COMMIT" | grep -q "requirements.txt"; then
    echo -e "${YELLOW}  ⚠️ requirements.txt е променен - обновяване на dependencies...${NC}"
    pip3 install -r requirements.txt --upgrade
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Dependencies обновени успешно${NC}"
    else
        echo -e "${RED}  ✗ Грешка при обновяване на dependencies${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}  ✓ requirements.txt не е променен${NC}"
fi
echo ""

# Стъпка 4: Рестартиране на PM2
echo -e "${YELLOW}🔄 Рестартиране на бота с PM2...${NC}"

# Проверка дали PM2 е инсталиран
if ! command -v pm2 &> /dev/null; then
    echo -e "${RED}  ✗ PM2 не е инсталиран!${NC}"
    echo -e "${YELLOW}  💡 Инсталирайте PM2: npm install -g pm2${NC}"
    exit 1
fi

# Проверка дали ботът е стартиран с PM2
if pm2 list | grep -q "crypto-bot"; then
    echo -e "${YELLOW}  ⟳ Рестартиране на crypto-bot...${NC}"
    pm2 restart crypto-bot
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Бот рестартиран успешно${NC}"
    else
        echo -e "${RED}  ✗ Грешка при рестартиране${NC}"
        exit 1
    fi
else
    echo -e "${YELLOW}  🚀 Стартиране на бота за първи път...${NC}"
    if [ -f "ecosystem.config.js" ]; then
        pm2 start ecosystem.config.js
    else
        pm2 start bot.py --name crypto-bot --interpreter python3
    fi
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}  ✓ Бот стартиран успешно${NC}"
    else
        echo -e "${RED}  ✗ Грешка при стартиране${NC}"
        exit 1
    fi
fi
echo ""

# Стъпка 5: Проверка на статуса
echo -e "${YELLOW}📊 Статус на бота:${NC}"
pm2 status crypto-bot
echo ""

# Стъпка 6: Показване на логове (последните 20 реда)
echo -e "${YELLOW}📜 Последни логове:${NC}"
pm2 logs crypto-bot --lines 20 --nostream
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
