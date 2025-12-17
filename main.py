"""
Main entry point for the Crypto Signal Bot

This module serves as the clean entry point for the application,
properly importing and initializing the telegram bot.
"""

import logging
import sys
import os
import importlib.util

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


def main():
    """
    Main entry point for the Crypto Signal Bot application.
    
    Initializes and starts the telegram bot, handling errors gracefully.
    """
    try:
        logger.info("🚀 Starting Crypto Signal Bot...")
        
        # Import bot.py file directly (not the bot/ package)
        # Get the path to bot.py
        bot_path = os.path.join(os.path.dirname(__file__), 'bot.py')
        
        # Load bot.py as a module
        spec = importlib.util.spec_from_file_location("bot_module", bot_path)
        bot_module = importlib.util.module_from_spec(spec)
        sys.modules['bot_module'] = bot_module
        spec.loader.exec_module(bot_module)
        
        # Run the bot's main function which contains all the logic
        bot_module.main()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Fatal error in main: {e}")
        logger.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
