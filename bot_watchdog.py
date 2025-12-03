#!/usr/bin/env python3
"""
Bot Watchdog - Наблюдава бота и го рестартира при зависване
Работи на всеки 2 минути
"""

import os
import sys
import time
import logging
import subprocess
import requests
from datetime import datetime, timedelta

# Настройки
WORKSPACE = "/workspaces/Crypto-signal-bot"
BOT_PID_FILE = f"{WORKSPACE}/bot.pid"
WATCHDOG_LOG = f"{WORKSPACE}/watchdog.log"
BOT_LOG = f"{WORKSPACE}/bot.log"
BOT_MANAGER = f"{WORKSPACE}/bot-manager.sh"
CHECK_INTERVAL = 120  # 2 минути
TELEGRAM_BOT_TOKEN = "8349449826:AAFNmP0i-DlERin8Z7HVir4awGTpa5n8vUM"
OWNER_CHAT_ID = 7003238836

# Логване
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(WATCHDOG_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_bot_pid():
    """Вземи PID от файл"""
    try:
        if os.path.exists(BOT_PID_FILE):
            with open(BOT_PID_FILE, 'r') as f:
                return int(f.read().strip())
        return None
    except Exception as e:
        logger.error(f"Грешка при четене на PID: {e}")
        return None


def is_process_running(pid):
    """Провери дали процесът работи"""
    try:
        result = subprocess.run(
            ["ps", "-p", str(pid)],
            capture_output=True,
            timeout=5
        )
        return result.returncode == 0
    except Exception as e:
        logger.error(f"Грешка при проверка на процес: {e}")
        return False


def check_bot_responding():
    """Провери дали ботът отговаря на Telegram API"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if data.get('ok'):
                logger.debug("✅ Bot API отговаря")
                return True
        
        logger.warning(f"⚠️ Bot API не отговаря: {response.status_code}")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Грешка при проверка на API: {e}")
        return False


def check_recent_activity():
    """Провери дали има скорошна активност в логовете"""
    try:
        if not os.path.exists(BOT_LOG):
            return False
        
        # Вземи последните 50 реда
        with open(BOT_LOG, 'r') as f:
            lines = f.readlines()
            recent_lines = lines[-50:] if len(lines) > 50 else lines
        
        if not recent_lines:
            return False
        
        # Вземи последния timestamp
        for line in reversed(recent_lines):
            if line.strip():
                # Парсирай timestamp (формат: 2025-11-23 17:10:20,631)
                try:
                    timestamp_str = ' '.join(line.split()[:2])
                    last_activity = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S,%f')
                    
                    # Ако има активност в последните 10 минути
                    time_diff = datetime.now() - last_activity
                    if time_diff.total_seconds() < 600:  # 10 минути
                        logger.debug(f"✅ Скорошна активност: {time_diff.total_seconds():.0f}s ago")
                        return True
                    else:
                        logger.warning(f"⚠️ Няма активност от {time_diff.total_seconds():.0f}s")
                        return False
                except Exception:
                    continue
        
        return False
    except Exception as e:
        logger.error(f"Грешка при проверка на активност: {e}")
        return False


def restart_bot():
    """Рестартирай бота"""
    logger.warning("🔄 Рестартиране на бота...")
    
    try:
        result = subprocess.run(
            [BOT_MANAGER, "restart"],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        if result.returncode == 0:
            logger.info("✅ Ботът е успешно рестартиран")
            
            # Изпрати известие
            try:
                send_telegram_notification("⚠️ Ботът беше автоматично рестартиран от Watchdog поради липса на отговор.")
            except:
                pass
            
            return True
        else:
            logger.error(f"❌ Грешка при рестарт: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Изключение при рестарт: {e}")
        return False


def send_telegram_notification(message):
    """Изпрати известие до owner"""
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        data = {
            'chat_id': OWNER_CHAT_ID,
            'text': f"🤖 <b>Watchdog Alert</b>\n\n{message}",
            'parse_mode': 'HTML'
        }
        requests.post(url, json=data, timeout=10)
    except Exception as e:
        logger.error(f"Грешка при изпращане на известие: {e}")


def watchdog_check():
    """Главна проверка на watchdog"""
    logger.info("=" * 60)
    logger.info("🔍 WATCHDOG CHECK")
    logger.info("=" * 60)
    
    # 1. Провери PID файл
    bot_pid = get_bot_pid()
    if not bot_pid:
        logger.warning("⚠️ Няма PID файл - стартирам бота")
        restart_bot()
        return
    
    logger.info(f"📍 Bot PID: {bot_pid}")
    
    # 2. Провери дали процесът работи
    if not is_process_running(bot_pid):
        logger.warning(f"⚠️ Процес {bot_pid} НЕ работи - стартирам бота")
        restart_bot()
        return
    
    logger.info("✅ Процесът работи")
    
    # 3. Провери дали има скорошна активност
    if not check_recent_activity():
        logger.warning("⚠️ Няма скорошна активност в логовете")
        
        # 4. Провери Telegram API
        if not check_bot_responding():
            logger.error("❌ Ботът НЕ отговаря на API - рестартирам")
            restart_bot()
            return
    
    logger.info("✅ Всичко е наред")
    logger.info("=" * 60)


def continuous_watchdog():
    """Непрекъснат watchdog мониторинг"""
    logger.info("🐕 Стартиране на Bot Watchdog")
    logger.info(f"⏰ Интервал: {CHECK_INTERVAL // 60} минути")
    logger.info(f"📁 Лог файл: {WATCHDOG_LOG}")
    logger.info("")
    
    while True:
        try:
            watchdog_check()
            logger.info(f"⏳ Следваща проверка след {CHECK_INTERVAL // 60} минути...")
            logger.info("")
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("\n🛑 Спиране на watchdog...")
            break
        except Exception as e:
            logger.error(f"❌ Неочаквана грешка: {e}")
            time.sleep(60)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        # Еднократна проверка
        watchdog_check()
    else:
        # Непрекъснат мониторинг
        continuous_watchdog()
