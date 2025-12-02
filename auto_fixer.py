#!/usr/bin/env python3
"""
Автоматичен мониторинг и отстраняване на грешки
Работи на всеки 15 минути
"""

import os
import re
import sys
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Настройки
WORKSPACE = "/workspaces/Crypto-signal-bot"
LOG_FILE = f"{WORKSPACE}/bot.log"
FIXER_LOG = f"{WORKSPACE}/auto_fixer.log"
BOT_MANAGER = f"{WORKSPACE}/bot-manager.sh"
CHECK_INTERVAL = 15 * 60  # 15 минути

# Логване
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(FIXER_LOG),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def get_bot_pid():
    """Проверява дали ботът работи"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "python3.*bot.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return int(result.stdout.strip().split()[0])
        return None
    except Exception as e:
        logger.error(f"Грешка при проверка на PID: {e}")
        return None


def check_missing_modules():
    """Проверява за липсващи Python модули"""
    required_modules = [
        'telegram',
        'apscheduler',
        'mplfinance',
        'ta',
        'pandas',
        'numpy',
        'requests'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            missing.append(module)
    
    return missing


def check_syntax_errors():
    """Проверява bot.py за syntax errors (IndentationError, SyntaxError и т.н.)"""
    bot_file = f"{WORKSPACE}/bot.py"
    
    if not os.path.exists(bot_file):
        logger.error(f"❌ Файлът {bot_file} не съществува!")
        return None
    
    try:
        # Компилирай файла за проверка на синтаксис
        result = subprocess.run(
            ["python3", "-m", "py_compile", bot_file],
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            logger.info("✅ Синтаксисът на bot.py е валиден")
            return None
        else:
            error_msg = result.stderr.strip()
            logger.error(f"❌ SYNTAX ERROR в bot.py:\n{error_msg}")
            
            # Опитай се да извлечеш номера на реда и типа грешка
            match = re.search(r'File "([^"]+)", line (\d+)', error_msg)
            if match:
                line_num = int(match.group(2))
                
                # Определи типа грешка
                if 'IndentationError' in error_msg:
                    error_type = 'IndentationError'
                elif 'SyntaxError' in error_msg:
                    error_type = 'SyntaxError'
                else:
                    error_type = 'UnknownSyntaxError'
                
                return {
                    'type': error_type,
                    'line': line_num,
                    'message': error_msg
                }
            
            return {'type': 'UnknownError', 'message': error_msg}
            
    except Exception as e:
        logger.error(f"❌ Грешка при проверка на синтаксис: {e}")
        return None


def fix_syntax_error(error_info):
    """Опитва се да поправи автоматично syntax errors"""
    if not error_info:
        return False
    
    bot_file = f"{WORKSPACE}/bot.py"
    error_type = error_info.get('type')
    line_num = error_info.get('line')
    
    logger.warning(f"🔧 Опит за автоматично поправяне на {error_type} на ред {line_num}")
    
    try:
        # Прочети файла
        with open(bot_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        if line_num and 0 < line_num <= len(lines):
            # Провери за дублирани редове около грешката
            context_start = max(0, line_num - 5)
            context_end = min(len(lines), line_num + 5)
            context = lines[context_start:context_end]
            
            # Намери дублирани редове
            seen = {}
            duplicates = []
            for i, line in enumerate(context):
                line_stripped = line.strip()
                if line_stripped and line_stripped in seen:
                    actual_idx = context_start + i
                    duplicates.append(actual_idx)
                    logger.warning(f"   Намерен дубликат на ред {actual_idx}: {line_stripped[:50]}")
                seen[line_stripped] = context_start + i
            
            # Премахни дубликати
            if duplicates:
                logger.info(f"🔧 Премахване на {len(duplicates)} дублирани реда...")
                for idx in reversed(sorted(duplicates)):
                    del lines[idx]
                
                # Запази поправения файл
                with open(bot_file, 'w', encoding='utf-8') as f:
                    f.writelines(lines)
                
                logger.info("✅ Дубликатите са премахнати!")
                
                # Провери отново синтаксиса
                verification = check_syntax_errors()
                if verification is None:
                    logger.info("✅ Синтаксисът е коригиран успешно!")
                    return True
                else:
                    logger.warning("⚠️ Все още има синтаксисни грешки")
                    return False
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Грешка при поправяне на синтаксис: {e}")
        return False


def install_missing_modules(modules):
    """Инсталира липсващи модули"""
    if not modules:
        return True
    
    logger.warning(f"🔧 Инсталиране на липсващи модули: {', '.join(modules)}")
    
    try:
        # Подготви команда
        if 'telegram' in modules:
            modules.remove('telegram')
            modules.append('python-telegram-bot==20.7')
        
        cmd = ["pip", "install", "-q"] + modules
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        
        if result.returncode == 0:
            logger.info(f"✅ Успешно инсталирани: {', '.join(modules)}")
            return True
        else:
            logger.error(f"❌ Грешка при инсталация: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Изключение при инсталация: {e}")
        return False


def analyze_logs():
    """Анализира логовете за грешки"""
    if not os.path.exists(LOG_FILE):
        return {}
    
    problems = {
        'conflicts': 0,
        'forbidden_errors': 0,
        'module_errors': 0,
        'connection_errors': 0,
        'recent_errors': []
    }
    
    try:
        # Четене на последните 500 реда
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            recent_lines = lines[-500:] if len(lines) > 500 else lines
        
        for line in recent_lines:
            # 409 Conflict
            if re.search(r'409.*Conflict', line, re.I):
                problems['conflicts'] += 1
            
            # 403 Forbidden
            if re.search(r'403.*Forbidden', line, re.I):
                problems['forbidden_errors'] += 1
            
            # Module errors
            if re.search(r'ModuleNotFoundError|No module named', line):
                problems['module_errors'] += 1
                # Извличане на името на модула
                match = re.search(r"No module named '([^']+)'", line)
                if match:
                    problems['recent_errors'].append(f"Missing module: {match.group(1)}")
            
            # Connection errors
            if re.search(r'ConnectionError|TimeoutError|Network is unreachable', line, re.I):
                problems['connection_errors'] += 1
            
            # Други ERROR линии
            if 'ERROR' in line and len(problems['recent_errors']) < 5:
                problems['recent_errors'].append(line.strip()[-200:])
        
        return problems
    except Exception as e:
        logger.error(f"Грешка при анализ на логове: {e}")
        return problems


def fix_conflicts():
    """Отстранява конфликти при множество инстанции"""
    logger.warning("🔧 Откриване на множество инстанции...")
    
    try:
        # Намери всички процеси
        result = subprocess.run(
            ["pgrep", "-f", "python3.*bot.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        pids = result.stdout.strip().split('\n') if result.stdout else []
        pids = [p for p in pids if p]
        
        if len(pids) > 1:
            logger.warning(f"⚠️ Намерени {len(pids)} инстанции. Спиране на всички...")
            subprocess.run(["pkill", "-9", "-f", "python3.*bot.py"], timeout=10)
            time.sleep(3)
            
            # Рестартиране
            subprocess.run([BOT_MANAGER, "start"], timeout=30)
            logger.info("✅ Ботът е рестартиран с една инстанция")
            return True
        
        return False
    except Exception as e:
        logger.error(f"❌ Грешка при отстраняване на конфликти: {e}")
        return False


def restart_bot():
    """Рестартира бота"""
    logger.warning("🔄 Рестартиране на бота...")
    
    try:
        result = subprocess.run(
            [BOT_MANAGER, "restart"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            logger.info("✅ Ботът е успешно рестартиран")
            return True
        else:
            logger.error(f"❌ Грешка при рестарт: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"❌ Изключение при рестарт: {e}")
        return False


def auto_fix():
    """Главна функция за автоматично отстраняване на грешки"""
    logger.info("=" * 60)
    logger.info("🔍 АВТОМАТИЧНА ПРОВЕРКА")
    logger.info("=" * 60)
    
    fixed_issues = []
    
    # 0. КРИТИЧНО: Проверка за syntax errors ПЪРВО!
    logger.info("🔍 Проверка на синтаксис...")
    syntax_error = check_syntax_errors()
    if syntax_error:
        logger.error(f"❌ КРИТИЧНА ГРЕШКА: {syntax_error['type']} на ред {syntax_error.get('line', 'N/A')}")
        logger.warning("🔧 Опит за автоматично поправяне...")
        
        if fix_syntax_error(syntax_error):
            fixed_issues.append(f"Поправен {syntax_error['type']}")
            logger.info("✅ Синтаксисът е коригиран! Продължаване с проверки...")
        else:
            logger.error("❌ НЕ МОЖЕ ДА ПОПРАВИ СИНТАКСИСА АВТОМАТИЧНО!")
            logger.error("   Моля, поправи ръчно грешката в bot.py")
            return
    else:
        logger.info("✅ Синтаксисът е валиден")
    
    # 1. Проверка дали ботът работи
    bot_pid = get_bot_pid()
    if not bot_pid:
        logger.warning("⚠️ Ботът НЕ работи!")
        if restart_bot():
            fixed_issues.append("Стартиран неработещ бот")
        else:
            logger.error("❌ Не може да стартира бота")
            return
    else:
        logger.info(f"✅ Ботът работи (PID: {bot_pid})")
    
    # 2. Проверка за липсващи модули
    missing = check_missing_modules()
    if missing:
        logger.warning(f"⚠️ Липсващи модули: {', '.join(missing)}")
        if install_missing_modules(missing):
            fixed_issues.append(f"Инсталирани модули: {', '.join(missing)}")
            restart_bot()
        else:
            logger.error("❌ Не може да инсталира модули")
    else:
        logger.info("✅ Всички модули са налични")
    
    # 3. Анализ на логове
    problems = analyze_logs()
    
    # 4. Отстраняване на конфликти
    if problems['conflicts'] > 5:
        logger.warning(f"⚠️ Множество 409 конфликти: {problems['conflicts']}")
        if fix_conflicts():
            fixed_issues.append("Отстранени 409 конфликти")
    
    # 5. Проверка за connection errors
    if problems['connection_errors'] > 10:
        logger.warning(f"⚠️ Множество connection errors: {problems['connection_errors']}")
        if restart_bot():
            fixed_issues.append("Рестартиран поради connection errors")
    
    # 6. Проверка за 403 грешки
    if problems['forbidden_errors'] > 3:
        logger.warning(f"⚠️ 403 Forbidden грешки: {problems['forbidden_errors']}")
        logger.warning("   Може да е грешен OWNER_CHAT_ID в bot.py")
    
    # 7. Резултат
    logger.info("")
    logger.info("📊 РЕЗУЛТАТ:")
    logger.info(f"   409 Conflicts: {problems['conflicts']}")
    logger.info(f"   403 Forbidden: {problems['forbidden_errors']}")
    logger.info(f"   Module Errors: {problems['module_errors']}")
    logger.info(f"   Connection Errors: {problems['connection_errors']}")
    
    if fixed_issues:
        logger.info("")
        logger.info("🔧 ОТСТРАНЕНИ ПРОБЛЕМИ:")
        for issue in fixed_issues:
            logger.info(f"   ✅ {issue}")
    else:
        logger.info("")
        logger.info("✅ Няма проблеми за отстраняване")
    
    if problems['recent_errors']:
        logger.info("")
        logger.info("⚠️ ПОСЛЕДНИ ГРЕШКИ:")
        for error in problems['recent_errors'][:3]:
            logger.info(f"   {error}")
    
    logger.info("=" * 60)


def continuous_monitor():
    """Непрекъснат мониторинг на всеки 15 минути"""
    logger.info("🚀 Стартиране на автоматичен мониторинг")
    logger.info(f"⏰ Интервал: {CHECK_INTERVAL // 60} минути")
    logger.info(f"📁 Лог файл: {FIXER_LOG}")
    logger.info("")
    
    while True:
        try:
            auto_fix()
            logger.info(f"⏳ Следваща проверка след {CHECK_INTERVAL // 60} минути...")
            logger.info("")
            time.sleep(CHECK_INTERVAL)
        except KeyboardInterrupt:
            logger.info("\n🛑 Спиране на мониторинга...")
            break
        except Exception as e:
            logger.error(f"❌ Неочаквана грешка: {e}")
            time.sleep(60)  # Изчакай 1 минута при грешка


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        # Еднократна проверка
        auto_fix()
    else:
        # Непрекъснат мониторинг
        continuous_monitor()
