"""
Test script for PR #113 fixes:
1. ALLOWED_USERS initialization
2. Health button in main menu
3. Multi-pair market swing analysis

Tests verify the changes are present and correctly structured.
"""

import sys
import os

# Set dummy environment variables for testing
os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token_12345'
os.environ['OWNER_CHAT_ID'] = '7003238836'

def test_allowed_users_fix():
    """Test that ALLOWED_USERS has defensive fallback"""
    print("\n🔍 Testing ALLOWED_USERS initialization fix...")
    
    try:
        # Read bot.py to check the fix
        with open('bot.py', 'r') as f:
            content = f.read()
        
        # Check for the defensive fallback pattern
        if '7003238836,  # Hardcoded owner ID as fallback' in content:
            print("  ✅ ALLOWED_USERS contains hardcoded fallback owner ID")
        else:
            print("  ❌ ALLOWED_USERS missing hardcoded fallback")
            return False
        
        if "int(os.getenv('OWNER_CHAT_ID'" in content:
            print("  ✅ ALLOWED_USERS includes environment variable")
        else:
            print("  ❌ ALLOWED_USERS missing environment variable")
            return False
        
        print("  ✅ Fix #1: ALLOWED_USERS initialization - PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing ALLOWED_USERS: {e}")
        return False


def test_health_button():
    """Test that Health button is in main keyboard"""
    print("\n🔍 Testing Health button addition...")
    
    try:
        # Read bot.py to check the button
        with open('bot.py', 'r') as f:
            content = f.read()
        
        # Check for Health button in keyboard
        if 'KeyboardButton("🏥 Health")' in content:
            print("  ✅ Health button added to main keyboard")
        else:
            print("  ❌ Health button missing from main keyboard")
            return False
        
        # Check for button handler
        if 'elif text == "🏥 Health":' in content:
            print("  ✅ Health button handler exists")
        else:
            print("  ❌ Health button handler missing")
            return False
        
        if 'await health_cmd(update, context)' in content:
            print("  ✅ Health button calls health_cmd")
        else:
            print("  ❌ Health button doesn't call health_cmd")
            return False
        
        print("  ✅ Fix #2: Health button - PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing Health button: {e}")
        return False


def test_multi_pair_swing_analysis():
    """Test that market_swing_analysis supports multiple pairs"""
    print("\n🔍 Testing multi-pair swing analysis...")
    
    try:
        # Read bot.py to check the changes
        with open('bot.py', 'r') as f:
            content = f.read()
        
        # Check for updated market_swing_analysis
        if 'symbols_to_analyze = list(SYMBOLS.values())' in content:
            print("  ✅ market_swing_analysis iterates all SYMBOLS")
        else:
            print("  ❌ market_swing_analysis doesn't iterate all symbols")
            return False
        
        # Check for swing detection helper function
        if 'async def detect_market_swing_state' in content:
            print("  ✅ detect_market_swing_state helper function exists")
        else:
            print("  ❌ detect_market_swing_state helper function missing")
            return False
        
        # Check helper uses fetch_json
        if 'await fetch_json(f"https://api.binance.com/api/v3/klines?symbol={symbol}' in content:
            print("  ✅ Helper function uses fetch_json for data")
        else:
            print("  ❌ Helper function doesn't use fetch_json")
            return False
        
        # Check for swing state detection logic
        if 'BULLISH' in content and 'BEARISH' in content and 'NEUTRAL' in content:
            print("  ✅ Swing state detection logic present")
        else:
            print("  ❌ Swing state detection logic incomplete")
            return False
        
        print("  ✅ Fix #3: Multi-pair swing analysis - PASSED")
        return True
        
    except Exception as e:
        print(f"  ❌ Error testing multi-pair analysis: {e}")
        return False


def test_code_compiles():
    """Test that bot.py compiles without syntax errors"""
    print("\n🔍 Testing bot.py compilation...")
    
    try:
        import py_compile
        py_compile.compile('bot.py', doraise=True)
        print("  ✅ bot.py compiles without syntax errors")
        return True
    except py_compile.PyCompileError as e:
        print(f"  ❌ Syntax error in bot.py: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error compiling bot.py: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("PR #113 - Fix Access Control + Health Button + Multi-Pair")
    print("=" * 60)
    
    results = []
    
    # Test 1: ALLOWED_USERS fix
    results.append(test_allowed_users_fix())
    
    # Test 2: Health button
    results.append(test_health_button())
    
    # Test 3: Multi-pair swing analysis
    results.append(test_multi_pair_swing_analysis())
    
    # Test 4: Code compilation
    results.append(test_code_compiles())
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"✅ ALL TESTS PASSED ({passed}/{total})")
        print("\n🎉 PR #113 changes verified successfully!")
        return 0
    else:
        print(f"❌ SOME TESTS FAILED ({passed}/{total} passed)")
        print("\n⚠️  Please review the failures above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
