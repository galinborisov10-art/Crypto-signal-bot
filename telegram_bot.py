"""
Telegram Bot Module - Wrapper for bot functionality

This module provides a clean interface to the telegram bot functionality
while maintaining backward compatibility with the existing bot.py structure.
"""

import logging
import sys
import os
from typing import Optional
from telegram.ext import Application

# Import bot.py file directly (not the bot/ package)
# We need to import it as a module from the file system
import importlib.util

# Get the path to bot.py
_bot_path = os.path.join(os.path.dirname(__file__), 'bot.py')

# Load bot.py as a module
_spec = importlib.util.spec_from_file_location("bot_module", _bot_path)
bot = importlib.util.module_from_spec(_spec)
sys.modules['bot_module'] = bot
_spec.loader.exec_module(bot)

logger = logging.getLogger(__name__)


def get_bot_application() -> Optional[Application]:
    """
    Get the configured Telegram bot application instance.
    
    Returns:
        Application: Configured telegram bot application
    """
    try:
        from telegram.ext import ApplicationBuilder
        from httpx import Limits
        
        app = (
            ApplicationBuilder()
            .token(bot.TELEGRAM_BOT_TOKEN)
            .get_updates_pool_timeout(3600)
            .get_updates_read_timeout(3600)
            .get_updates_write_timeout(3600)
            .get_updates_connect_timeout(60)
            .pool_timeout(3600)
            .read_timeout(3600)
            .write_timeout(3600)
            .connect_timeout(60)
            .connection_pool_size(100)
            .get_updates_connection_pool_size(100)
            .http_version("1.1")
            .build()
        )
        
        logger.info("✅ Telegram bot application created successfully")
        return app
        
    except Exception as e:
        logger.error(f"❌ Error creating bot application: {e}")
        return None


def register_handlers(app: Application) -> None:
    """
    Register all command and callback handlers for the bot.
    
    Args:
        app: The telegram Application instance
    """
    from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters
    
    try:
        # Register all command handlers from bot module
        app.add_handler(CommandHandler("start", bot.start_cmd))
        app.add_handler(CommandHandler("ml_menu", bot.ml_menu_cmd))
        app.add_handler(CommandHandler("help", bot.help_cmd))
        app.add_handler(CommandHandler("version", bot.version_cmd))
        app.add_handler(CommandHandler("v", bot.version_cmd))
        app.add_handler(CommandHandler("market", bot.market_cmd))
        app.add_handler(CommandHandler("signal", bot.signal_cmd))
        app.add_handler(CommandHandler("ict", bot.ict_cmd))
        app.add_handler(CommandHandler("news", bot.news_cmd))
        app.add_handler(CommandHandler("breaking", bot.breaking_cmd))
        app.add_handler(CommandHandler("task", bot.task_cmd))
        app.add_handler(CommandHandler("dailyreport", bot.dailyreport_cmd))
        app.add_handler(CommandHandler("workspace", bot.workspace_cmd))
        app.add_handler(CommandHandler("restart", bot.restart_cmd))
        app.add_handler(CommandHandler("autonews", bot.autonews_cmd))
        app.add_handler(CommandHandler("settings", bot.settings_cmd))
        app.add_handler(CommandHandler("timeframe", bot.timeframe_cmd))
        app.add_handler(CommandHandler("alerts", bot.alerts_cmd))
        app.add_handler(CommandHandler("stats", bot.stats_cmd))
        app.add_handler(CommandHandler("journal", bot.journal_cmd))
        app.add_handler(CommandHandler("risk", bot.risk_cmd))
        app.add_handler(CommandHandler("explain", bot.explain_cmd))
        app.add_handler(CommandHandler("toggle_ict", bot.toggle_ict_command))
        
        # Admin commands
        app.add_handler(CommandHandler("admin_login", bot.admin_login_cmd))
        app.add_handler(CommandHandler("admin_setpass", bot.admin_setpass_cmd))
        app.add_handler(CommandHandler("admin_daily", bot.admin_daily_cmd))
        app.add_handler(CommandHandler("admin_weekly", bot.admin_weekly_cmd))
        app.add_handler(CommandHandler("admin_monthly", bot.admin_monthly_cmd))
        app.add_handler(CommandHandler("admin_docs", bot.admin_docs_cmd))
        app.add_handler(CommandHandler("update", bot.auto_update_cmd))
        app.add_handler(CommandHandler("auto_update", bot.auto_update_cmd))
        app.add_handler(CommandHandler("test", bot.test_system_cmd))
        
        # User access management
        app.add_handler(CommandHandler("approve", bot.approve_user_cmd))
        app.add_handler(CommandHandler("block", bot.block_user_cmd))
        app.add_handler(CommandHandler("users", bot.list_users_cmd))
        
        # ML, backtesting, reports
        app.add_handler(CommandHandler("backtest", bot.backtest_cmd))
        app.add_handler(CommandHandler("ml_status", bot.ml_status_cmd))
        app.add_handler(CommandHandler("ml_train", bot.ml_train_cmd))
        app.add_handler(CommandHandler("daily_report", bot.daily_report_cmd))
        app.add_handler(CommandHandler("weekly_report", bot.weekly_report_cmd))
        app.add_handler(CommandHandler("monthly_report", bot.monthly_report_cmd))
        app.add_handler(CommandHandler("reports", bot.reports_cmd))
        
        # Short aliases
        app.add_handler(CommandHandler("m", bot.market_cmd))
        app.add_handler(CommandHandler("s", bot.signal_cmd))
        app.add_handler(CommandHandler("n", bot.news_cmd))
        app.add_handler(CommandHandler("b", bot.breaking_cmd))
        app.add_handler(CommandHandler("t", bot.task_cmd))
        app.add_handler(CommandHandler("w", bot.workspace_cmd))
        app.add_handler(CommandHandler("j", bot.journal_cmd))
        
        # Callback handlers
        app.add_handler(CallbackQueryHandler(bot.signal_callback, pattern='^tf_'))
        app.add_handler(CallbackQueryHandler(bot.signal_callback, pattern='^signal_'))
        app.add_handler(CallbackQueryHandler(bot.signal_callback, pattern='^back_to_menu$'))
        app.add_handler(CallbackQueryHandler(bot.signal_callback, pattern='^back_to_signal_menu$'))
        app.add_handler(CallbackQueryHandler(bot.timeframe_callback, pattern='^timeframe_'))
        app.add_handler(CallbackQueryHandler(bot.reports_callback, pattern='^report_'))
        
        # Message handler
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, bot.button_handler))
        
        logger.info("✅ All bot handlers registered successfully")
        
    except Exception as e:
        logger.error(f"❌ Error registering handlers: {e}")
        raise


def initialize_bot() -> Optional[Application]:
    """
    Initialize and configure the telegram bot application.
    
    Returns:
        Application: Fully configured and ready bot application, or None on error
    """
    try:
        logger.info("🤖 Initializing Telegram Bot...")
        
        # Create application
        app = get_bot_application()
        if not app:
            logger.error("❌ Failed to create bot application")
            return None
        
        # Register all handlers
        register_handlers(app)
        
        logger.info("✅ Telegram bot initialized successfully")
        return app
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize bot: {e}")
        return None


__all__ = ['get_bot_application', 'register_handlers', 'initialize_bot']
