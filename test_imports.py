"""
Test script to verify import structure works correctly.

This script tests that:
1. telegram_bot.py can be imported
2. main.py can be imported  
3. All necessary functions are accessible
4. No import errors occur
"""

import sys
import os

# Set dummy environment variables for testing
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
os.environ['OWNER_CHAT_ID'] = '12345'

def test_telegram_bot_import():
    """Test telegram_bot.py imports correctly"""
    print("Testing telegram_bot.py...")
    try:
        import telegram_bot
        
        # Check required functions exist
        assert hasattr(telegram_bot, 'get_bot_application'), "get_bot_application() not found"
        assert hasattr(telegram_bot, 'register_handlers'), "register_handlers() not found"
        assert hasattr(telegram_bot, 'initialize_bot'), "initialize_bot() not found"
        assert hasattr(telegram_bot, 'bot'), "bot module not accessible"
        
        print("  ✅ telegram_bot.py imported successfully")
        print("  ✅ All required functions available")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_main_import():
    """Test main.py imports correctly"""
    print("\nTesting main.py...")
    try:
        import main
        
        # Check main function exists
        assert hasattr(main, 'main'), "main() function not found"
        assert callable(main.main), "main() is not callable"
        
        print("  ✅ main.py imported successfully")
        print("  ✅ main() function is callable")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def test_integration():
    """Test that modules can work together"""
    print("\nTesting integration...")
    try:
        import telegram_bot
        import main
        
        # Verify bot module is accessible from both
        assert hasattr(telegram_bot.bot, 'main'), "bot.main() not accessible from telegram_bot"
        
        print("  ✅ Integration test passed")
        print("  ✅ bot.main() accessible from telegram_bot module")
        return True
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

if __name__ == "__main__":
    print("=" * 70)
    print("IMPORT STRUCTURE TEST")
    print("=" * 70)
    print()
    
    results = []
    results.append(test_telegram_bot_import())
    results.append(test_main_import())
    results.append(test_integration())
    
    print()
    print("=" * 70)
    if all(results):
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print("\nThe bot can be started using:")
        print("  1. python3 main.py    (new entry point)")
        print("  2. python3 bot.py     (original entry point)")
        sys.exit(0)
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 70)
        sys.exit(1)
