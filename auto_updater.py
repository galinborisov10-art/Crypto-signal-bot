#!/usr/bin/env python3
"""
🤖 AUTO-UPDATER & SELF-HEALING BOT
Автоматично обновяване и самокоригиращ се бот
"""

import os
import sys
import subprocess
import logging
import asyncio
from datetime import datetime
import json
from pathlib import Path

# Telegram imports
try:
    from telegram import Bot
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    print("⚠️ Telegram module not available - notifications disabled")

# =====================================
# CONFIGURATION
# =====================================
BOT_DIR = Path(__file__).parent
LOG_FILE = BOT_DIR / "auto_updater.log"
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8349449826:AAFNmP0i-DlERin8Z7HVir4awGTpa5n8vUM")
OWNER_CHAT_ID = 7003238836

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# =====================================
# TELEGRAM NOTIFICATION
# =====================================
async def send_telegram_notification(message: str, silent: bool = False):
    """Изпраща Telegram нотификация към owner"""
    if not TELEGRAM_AVAILABLE:
        logger.warning("Telegram not available - skipping notification")
        return
    
    try:
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=message,
            parse_mode='HTML',
            disable_notification=silent
        )
        logger.info(f"✅ Telegram notification sent")
    except Exception as e:
        logger.error(f"❌ Telegram notification failed: {e}")

# =====================================
# GIT OPERATIONS
# =====================================
def git_pull():
    """Pull latest changes from GitHub"""
    try:
        logger.info("📥 Checking for updates from GitHub...")
        
        # Get current commit
        current_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=BOT_DIR
        ).decode().strip()
        
        # Fetch updates
        subprocess.run(["git", "fetch", "origin"], cwd=BOT_DIR, check=True)
        
        # Get latest commit
        latest_commit = subprocess.check_output(
            ["git", "rev-parse", "origin/main"],
            cwd=BOT_DIR
        ).decode().strip()
        
        if current_commit == latest_commit:
            logger.info("✅ Already up to date")
            return False, "Already up to date"
        
        # Pull changes
        subprocess.run(["git", "pull", "origin", "main"], cwd=BOT_DIR, check=True)
        
        # Get commit message
        commit_msg = subprocess.check_output(
            ["git", "log", "-1", "--pretty=format:%s"],
            cwd=BOT_DIR
        ).decode().strip()
        
        logger.info(f"✅ Updated to: {commit_msg}")
        return True, commit_msg
        
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Git pull failed: {e}")
        return False, f"Error: {e}"

# =====================================
# DEPENDENCY CHECK
# =====================================
def check_and_install_dependencies():
    """Проверява и инсталира липсващи dependencies"""
    try:
        logger.info("📦 Checking dependencies...")
        
        # Check if venv exists
        venv_python = BOT_DIR / "venv" / "bin" / "python"
        if venv_python.exists():
            pip_cmd = [str(venv_python), "-m", "pip"]
            logger.info("🐍 Using venv Python")
        else:
            pip_cmd = ["pip3"]
            logger.info("🐍 Using system Python")
        
        # Install requirements
        requirements = BOT_DIR / "requirements.txt"
        if requirements.exists():
            result = subprocess.run(
                pip_cmd + ["install", "-r", str(requirements), "--quiet"],
                cwd=BOT_DIR,
                capture_output=True
            )
            
            if result.returncode == 0:
                logger.info("✅ Dependencies OK")
                return True
            else:
                logger.warning(f"⚠️ Dependency install warning: {result.stderr.decode()}")
                return True  # Don't fail on warnings
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Dependency check failed: {e}")
        return False

# =====================================
# BOT HEALTH CHECK
# =====================================
def check_bot_health():
    """Проверява дали ботът работи"""
    try:
        result = subprocess.run(
            ["pgrep", "-f", "bot.py"],
            capture_output=True
        )
        
        if result.returncode == 0:
            pid = result.stdout.decode().strip()
            logger.info(f"✅ Bot is running (PID: {pid})")
            return True
        else:
            logger.warning("⚠️ Bot is NOT running")
            return False
            
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False

# =====================================
# BOT RESTART
# =====================================
def restart_bot():
    """Рестартира бота"""
    try:
        logger.info("🔄 Restarting bot...")
        
        # Kill existing process
        subprocess.run(["pkill", "-f", "bot.py"], check=False)
        
        # Wait a bit
        import time
        time.sleep(3)
        
        # Check for venv
        venv_python = BOT_DIR / "venv" / "bin" / "python"
        if venv_python.exists():
            python_cmd = str(venv_python)
            logger.info("🐍 Using venv Python")
        else:
            python_cmd = "python3"
            logger.info("🐍 Using system Python")
        
        # Start bot in background
        log_file = BOT_DIR / "bot.log"
        with open(log_file, "w") as f:
            subprocess.Popen(
                [python_cmd, "bot.py"],
                cwd=BOT_DIR,
                stdout=f,
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        # Wait and check
        time.sleep(5)
        if check_bot_health():
            logger.info("✅ Bot restarted successfully")
            return True
        else:
            logger.error("❌ Bot failed to start")
            return False
            
    except Exception as e:
        logger.error(f"❌ Restart failed: {e}")
        return False

# =====================================
# AUTO-FIX PROBLEMS
# =====================================
def auto_fix_common_issues():
    """Автоматично поправя чести проблеми"""
    issues_fixed = []
    
    try:
        # 1. Check bot.log for errors
        log_file = BOT_DIR / "bot.log"
        if log_file.exists():
            with open(log_file, 'r') as f:
                last_lines = f.readlines()[-50:]  # Last 50 lines
                log_text = ''.join(last_lines)
                
                # Check for module not found
                if "ModuleNotFoundError" in log_text:
                    logger.warning("🔧 Detected ModuleNotFoundError - reinstalling dependencies")
                    check_and_install_dependencies()
                    issues_fixed.append("Reinstalled dependencies")
                
                # Check for connection errors
                if "ConnectionError" in log_text or "TimeoutError" in log_text:
                    logger.warning("🔧 Detected connection error - restarting bot")
                    restart_bot()
                    issues_fixed.append("Restarted bot (connection issues)")
        
        # 2. Check if bot is stuck (no recent logs)
        if log_file.exists():
            import time
            log_age = time.time() - log_file.stat().st_mtime
            if log_age > 3600:  # No logs for 1 hour
                logger.warning("🔧 Bot logs are stale - restarting")
                restart_bot()
                issues_fixed.append("Restarted bot (stale logs)")
        
        # 3. Check disk space
        result = subprocess.run(
            ["df", "-h", str(BOT_DIR)],
            capture_output=True,
            text=True
        )
        if "100%" in result.stdout or "99%" in result.stdout:
            logger.warning("🔧 Disk space critical - cleaning old logs")
            # Clean old backups
            backup_dir = BOT_DIR / "backups"
            if backup_dir.exists():
                old_backups = sorted(backup_dir.glob("*.tar.gz"))
                if len(old_backups) > 10:
                    for backup in old_backups[:-10]:  # Keep only last 10
                        backup.unlink()
                        logger.info(f"🗑️ Deleted old backup: {backup.name}")
                    issues_fixed.append("Cleaned old backups")
        
        return issues_fixed
        
    except Exception as e:
        logger.error(f"❌ Auto-fix failed: {e}")
        return issues_fixed

# =====================================
# MAIN UPDATE PROCESS
# =====================================
async def run_auto_update():
    """Основен update процес"""
    logger.info("=" * 60)
    logger.info("🚀 AUTO-UPDATE PROCESS STARTED")
    logger.info(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 60)
    
    report_lines = ["<b>🤖 AUTO-UPDATE REPORT</b>\n"]
    report_lines.append(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # 1. Git Pull
    updated, message = git_pull()
    if updated:
        report_lines.append(f"✅ <b>Updated from GitHub:</b>\n   {message}\n")
    else:
        report_lines.append(f"ℹ️ {message}\n")
    
    # 2. Check dependencies
    if updated:
        if check_and_install_dependencies():
            report_lines.append("✅ Dependencies checked\n")
        else:
            report_lines.append("⚠️ Dependency check failed\n")
    
    # 3. Auto-fix issues
    issues_fixed = auto_fix_common_issues()
    if issues_fixed:
        report_lines.append(f"🔧 <b>Auto-fixed:</b>\n")
        for issue in issues_fixed:
            report_lines.append(f"   • {issue}\n")
    
    # 4. Check bot health
    bot_healthy = check_bot_health()
    if bot_healthy:
        report_lines.append("✅ Bot is running\n")
    else:
        report_lines.append("⚠️ Bot is NOT running - attempting restart\n")
        if restart_bot():
            report_lines.append("✅ Bot restarted successfully\n")
        else:
            report_lines.append("❌ Bot restart FAILED\n")
    
    # 5. Restart if updated
    if updated:
        report_lines.append("\n🔄 Restarting bot with new code...\n")
        if restart_bot():
            report_lines.append("✅ Bot restarted with updates\n")
        else:
            report_lines.append("❌ Restart failed\n")
    
    # Send notification
    report = ''.join(report_lines)
    logger.info(report)
    await send_telegram_notification(report, silent=False)
    
    logger.info("=" * 60)
    logger.info("✅ AUTO-UPDATE PROCESS COMPLETED")
    logger.info("=" * 60)

# =====================================
# ENTRY POINT
# =====================================
if __name__ == "__main__":
    asyncio.run(run_auto_update())
