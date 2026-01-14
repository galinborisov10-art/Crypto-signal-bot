#!/usr/bin/env python3
"""
Test Critical Fixes for Trading Journal, Position Monitor, and Daily Reports

This test verifies:
1. ICTSignal has 'bias' attribute (not 'market_bias')
2. ICTSignal has 'mtf_confluence' attribute (not 'mtf_confluence_score')
3. Position monitor wrapper function exists
4. Daily report scheduler has misfire_grace_time
"""

import sys
import ast
import re

def test_ict_signal_attributes():
    """Verify ICTSignal class has correct attributes"""
    print("🧪 Testing ICTSignal attributes...")
    
    try:
        from ict_signal_engine import ICTSignal
        
        # Check if bias attribute exists
        assert hasattr(ICTSignal, '__annotations__'), "ICTSignal should have annotations"
        annotations = ICTSignal.__annotations__
        
        assert 'bias' in annotations, "ICTSignal should have 'bias' attribute"
        print("  ✅ ICTSignal has 'bias' attribute")
        
        assert 'mtf_confluence' in annotations, "ICTSignal should have 'mtf_confluence' attribute"
        print("  ✅ ICTSignal has 'mtf_confluence' attribute")
        
        # Verify market_bias doesn't exist
        assert 'market_bias' not in annotations, "ICTSignal should NOT have 'market_bias' attribute"
        print("  ✅ ICTSignal does NOT have 'market_bias' (correct)")
        
        return True
    except Exception as e:
        print(f"  ❌ ICTSignal test failed: {e}")
        return False


def test_bot_uses_correct_attributes():
    """Verify bot.py uses bias instead of market_bias"""
    print("\n🧪 Testing bot.py uses correct ICTSignal attributes...")
    
    try:
        with open('bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for incorrect usage
        market_bias_matches = re.findall(r'ict_signal\.market_bias', content)
        if market_bias_matches:
            print(f"  ❌ Found {len(market_bias_matches)} uses of 'ict_signal.market_bias' (should be 'bias')")
            return False
        else:
            print("  ✅ No incorrect 'ict_signal.market_bias' usage found")
        
        # Check for correct usage
        bias_matches = re.findall(r'ict_signal\.bias\.value', content)
        if bias_matches:
            print(f"  ✅ Found {len(bias_matches)} correct uses of 'ict_signal.bias.value'")
        
        # Check for mtf_confluence_score (incorrect)
        mtf_conf_score_matches = re.findall(r'ict_signal\.mtf_confluence_score', content)
        if mtf_conf_score_matches:
            print(f"  ❌ Found {len(mtf_conf_score_matches)} uses of 'ict_signal.mtf_confluence_score' (should be 'mtf_confluence')")
            return False
        else:
            print("  ✅ No incorrect 'ict_signal.mtf_confluence_score' usage found")
        
        return True
    except Exception as e:
        print(f"  ❌ bot.py attribute test failed: {e}")
        return False


def test_position_monitor_wrapper():
    """Verify position monitor has async wrapper instead of lambda"""
    print("\n🧪 Testing position monitor wrapper function...")
    
    try:
        with open('bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for incorrect lambda usage
        lambda_monitor = re.search(r'lambda:.*asyncio\.create_task\(monitor_positions_job', content)
        if lambda_monitor:
            print("  ❌ Found lambda usage for position monitor (should use wrapper)")
            return False
        else:
            print("  ✅ No lambda usage for position monitor found")
        
        # Check for wrapper function
        wrapper_def = re.search(r'async def position_monitor_wrapper\(\):', content)
        if wrapper_def:
            print("  ✅ Found position_monitor_wrapper() function")
        else:
            print("  ⚠️ position_monitor_wrapper() function not found")
            return False
        
        # Check wrapper is used in scheduler
        wrapper_usage = re.search(r'scheduler\.add_job\(\s*position_monitor_wrapper', content, re.MULTILINE)
        if wrapper_usage:
            print("  ✅ position_monitor_wrapper is used in scheduler")
        else:
            print("  ❌ position_monitor_wrapper is NOT used in scheduler")
            return False
        
        return True
    except Exception as e:
        print(f"  ❌ Position monitor wrapper test failed: {e}")
        return False


def test_daily_report_misfire_grace_time():
    """Verify daily report has misfire_grace_time parameter"""
    print("\n🧪 Testing daily report misfire_grace_time...")
    
    try:
        with open('bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find send_daily_auto_report scheduler call
        # Look for the scheduler.add_job section
        pattern = r'scheduler\.add_job\(\s*send_daily_auto_report.*?\)'
        matches = re.findall(pattern, content, re.DOTALL)
        
        if not matches:
            print("  ❌ send_daily_auto_report scheduler call not found")
            return False
        
        # Check if misfire_grace_time is present
        for match in matches:
            if 'misfire_grace_time' in match:
                print("  ✅ Found misfire_grace_time parameter")
                
                # Extract the value
                grace_time_match = re.search(r'misfire_grace_time\s*=\s*(\d+)', match)
                if grace_time_match:
                    grace_time = int(grace_time_match.group(1))
                    print(f"  ✅ misfire_grace_time set to {grace_time} seconds ({grace_time/60:.0f} minutes)")
                    
                    if grace_time >= 3600:  # At least 1 hour
                        print("  ✅ Grace time is adequate (>= 1 hour)")
                    else:
                        print(f"  ⚠️ Grace time might be too short: {grace_time/60:.0f} minutes")
                
                # Check for coalesce
                if 'coalesce' in match:
                    print("  ✅ Found coalesce parameter")
                else:
                    print("  ⚠️ coalesce parameter not found")
                
                # Check for max_instances
                if 'max_instances' in match:
                    print("  ✅ Found max_instances parameter")
                else:
                    print("  ⚠️ max_instances parameter not found")
                
                return True
        
        print("  ❌ misfire_grace_time parameter not found in send_daily_auto_report scheduler")
        return False
        
    except Exception as e:
        print(f"  ❌ Daily report misfire test failed: {e}")
        return False


def test_market_submenu_implementation():
    """Verify market button submenu is implemented"""
    print("\n🧪 Testing market button submenu implementation...")
    
    try:
        with open('bot.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for market_callback function
        if 'async def market_callback' in content:
            print("  ✅ Found market_callback() function")
        else:
            print("  ❌ market_callback() function not found")
            return False
        
        # Check for swing analysis function
        if 'async def generate_swing_trading_analysis' in content:
            print("  ✅ Found generate_swing_trading_analysis() function")
        else:
            print("  ❌ generate_swing_trading_analysis() function not found")
            return False
        
        # Check for language support
        if 'def format_swing_analysis_bg' in content and 'def format_swing_analysis_en' in content:
            print("  ✅ Found multi-language support (BG/EN)")
        else:
            print("  ⚠️ Multi-language support functions not found")
        
        # Check for callback handler registration
        if "CallbackQueryHandler(market_callback, pattern='^market_')" in content:
            print("  ✅ Found market callback handler registration")
        else:
            print("  ❌ Market callback handler not registered")
            return False
        
        # Check for InlineKeyboardMarkup in market_cmd
        if 'InlineKeyboardMarkup(market_keyboard)' in content:
            print("  ✅ Market submenu keyboard implemented")
        else:
            print("  ⚠️ Market submenu keyboard not found")
        
        return True
    except Exception as e:
        print(f"  ❌ Market submenu test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 CRITICAL FIXES VERIFICATION TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Test 1: ICTSignal attributes
    results.append(("ICTSignal Attributes", test_ict_signal_attributes()))
    
    # Test 2: bot.py uses correct attributes
    results.append(("bot.py Correct Attributes", test_bot_uses_correct_attributes()))
    
    # Test 3: Position monitor wrapper
    results.append(("Position Monitor Wrapper", test_position_monitor_wrapper()))
    
    # Test 4: Daily report misfire grace time
    results.append(("Daily Report Misfire Grace", test_daily_report_misfire_grace_time()))
    
    # Test 5: Market submenu
    results.append(("Market Submenu Implementation", test_market_submenu_implementation()))
    
    # Print summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("=" * 60)
    print(f"Result: {passed}/{total} tests passed")
    print("=" * 60)
    
    if passed == total:
        print("\n🎉 All tests passed! Critical fixes are working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the fixes.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
