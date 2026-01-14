#!/usr/bin/env python3
"""
Test script for PR #112 fixes
Validates the three bug fixes for PR #111 implementation
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_bug1_persistent_cache():
    """Test Bug #1: Persistent cache integration"""
    print("\n" + "="*60)
    print("TEST 1: Persistent Cache Integration")
    print("="*60)
    
    try:
        from signal_cache import is_signal_duplicate
        print("✅ signal_cache.py imported successfully")
        
        # Test the cache functionality
        base_path = os.path.dirname(os.path.abspath(__file__))
        
        # First signal - should NOT be duplicate
        is_dup, reason = is_signal_duplicate(
            symbol='ETHUSDT',
            signal_type='SELL',
            timeframe='1h',
            entry_price=3500.0,
            confidence=90,
            cooldown_minutes=60,
            base_path=base_path
        )
        
        assert not is_dup, "First signal should not be duplicate"
        assert "New signal" in reason, f"Expected 'New signal' in reason, got: {reason}"
        print(f"✅ First signal correctly identified as new: {reason}")
        
        # Second signal - SHOULD be duplicate
        is_dup2, reason2 = is_signal_duplicate(
            symbol='ETHUSDT',
            signal_type='SELL',
            timeframe='1h',
            entry_price=3505.0,  # Within 0.5% of 3500
            confidence=90,
            cooldown_minutes=60,
            base_path=base_path
        )
        
        assert is_dup2, "Second signal should be duplicate"
        assert "Duplicate" in reason2, f"Expected 'Duplicate' in reason, got: {reason2}"
        print(f"✅ Second signal correctly identified as duplicate: {reason2}")
        
        # Check cache file exists
        cache_file = os.path.join(base_path, 'sent_signals_cache.json')
        assert os.path.exists(cache_file), "Cache file should exist"
        print(f"✅ Cache file created: {cache_file}")
        
        # Verify cache content
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
            assert 'ETHUSDT_SELL_1h' in cache_data, "Cache should contain ETHUSDT_SELL_1h"
            print(f"✅ Cache contains expected data: {list(cache_data.keys())}")
        
        print("\n✅ TEST 1 PASSED: Persistent cache works correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 1 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bug2_startup_timer_function():
    """Test Bug #2: Startup mode timer function exists"""
    print("\n" + "="*60)
    print("TEST 2: Startup Mode Timer Function")
    print("="*60)
    
    try:
        # Check if the function is defined in bot.py
        with open('bot.py', 'r') as f:
            bot_content = f.read()
        
        # Check for timer function
        assert 'async def end_startup_mode_timer' in bot_content, \
            "end_startup_mode_timer function not found in bot.py"
        print("✅ end_startup_mode_timer function exists in bot.py")
        
        # Check for timer documentation
        assert 'PR #112' in bot_content and 'Startup mode never ends' in bot_content, \
            "Timer function should have PR #112 documentation"
        print("✅ Timer function has correct PR #112 documentation")
        
        # Check for timer scheduling in main
        assert 'app.job_queue.run_once(\n            end_startup_mode_timer,' in bot_content or \
               'app.job_queue.run_once(end_startup_mode_timer,' in bot_content, \
            "Timer should be scheduled in main function"
        print("✅ Timer is scheduled in main function")
        
        # Check for STARTUP_GRACE_PERIOD_SECONDS usage
        assert 'when=STARTUP_GRACE_PERIOD_SECONDS' in bot_content, \
            "Timer should use STARTUP_GRACE_PERIOD_SECONDS"
        print("✅ Timer uses correct grace period constant")
        
        # Check for logging
        assert '⏰ Startup mode timer scheduled' in bot_content, \
            "Timer scheduling should be logged"
        print("✅ Timer scheduling is logged")
        
        print("\n✅ TEST 2 PASSED: Startup mode timer implemented correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 2 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bug3_health_command():
    """Test Bug #3: Health command works"""
    print("\n" + "="*60)
    print("TEST 3: Health Command Implementation")
    print("="*60)
    
    try:
        # Test imports
        from system_diagnostics import run_full_health_check
        print("✅ system_diagnostics.run_full_health_check imported")
        
        from diagnostic_messages import format_health_summary
        print("✅ diagnostic_messages.format_health_summary imported")
        
        # Verify functions are callable
        assert callable(run_full_health_check), "run_full_health_check should be callable"
        print("✅ run_full_health_check is callable")
        
        assert callable(format_health_summary), "format_health_summary should be callable"
        print("✅ format_health_summary is callable")
        
        # Check format_health_summary signature
        import inspect
        sig = inspect.signature(format_health_summary)
        params = list(sig.parameters.keys())
        assert 'health_report' in params, "format_health_summary should accept health_report parameter"
        print(f"✅ format_health_summary has correct signature: {params}")
        
        # Test format_health_summary with mock data
        mock_report = {
            'summary': {
                'status': 'OK',
                'healthy': 5,
                'warning': 1,
                'critical': 0
            },
            'components': {
                'trading_journal': {
                    'status': 'HEALTHY',
                    'issues': []
                },
                'ml_model': {
                    'status': 'WARNING',
                    'issues': [{'problem': 'Test warning'}]
                }
            }
        }
        
        result = format_health_summary(mock_report)
        assert isinstance(result, str), "format_health_summary should return string"
        assert '🏥' in result, "Result should contain health emoji"
        assert 'SYSTEM HEALTH DIAGNOSTIC' in result, "Result should contain title"
        print("✅ format_health_summary returns correctly formatted output")
        
        print("\n✅ TEST 3 PASSED: Health command implementation is correct")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 3 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_send_alert_signal_uses_persistent_cache():
    """Test that send_alert_signal function uses persistent cache"""
    print("\n" + "="*60)
    print("TEST 4: send_alert_signal Uses Persistent Cache")
    print("="*60)
    
    try:
        with open('bot.py', 'r') as f:
            bot_content = f.read()
        
        # Find the send_alert_signal function
        assert 'async def send_alert_signal' in bot_content, \
            "send_alert_signal function not found"
        print("✅ send_alert_signal function exists")
        
        # Extract the function (rough approximation)
        start = bot_content.find('async def send_alert_signal')
        # Find next function definition
        next_func = bot_content.find('\nasync def ', start + 1)
        if next_func == -1:
            next_func = len(bot_content)
        
        func_content = bot_content[start:next_func]
        
        # Check for persistent cache usage
        assert 'if SIGNAL_CACHE_AVAILABLE:' in func_content, \
            "send_alert_signal should check SIGNAL_CACHE_AVAILABLE"
        print("✅ send_alert_signal checks SIGNAL_CACHE_AVAILABLE")
        
        assert 'is_signal_duplicate(' in func_content, \
            "send_alert_signal should call is_signal_duplicate"
        print("✅ send_alert_signal calls is_signal_duplicate")
        
        assert 'base_path=BASE_PATH' in func_content, \
            "send_alert_signal should pass base_path to is_signal_duplicate"
        print("✅ send_alert_signal passes base_path parameter")
        
        # Check for fallback
        assert 'is_signal_already_sent(' in func_content, \
            "send_alert_signal should have fallback to is_signal_already_sent"
        print("✅ send_alert_signal has fallback to in-memory cache")
        
        print("\n✅ TEST 4 PASSED: send_alert_signal uses persistent cache correctly")
        return True
        
    except Exception as e:
        print(f"\n❌ TEST 4 FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "="*60)
    print("PR #112 FIX VALIDATION TESTS")
    print("="*60)
    
    results = []
    
    # Run all tests
    results.append(("Persistent Cache Integration", test_bug1_persistent_cache()))
    results.append(("Startup Mode Timer", test_bug2_startup_timer_function()))
    results.append(("Health Command", test_bug3_health_command()))
    results.append(("send_alert_signal Cache Usage", test_send_alert_signal_uses_persistent_cache()))
    
    # Print summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("\n" + "="*60)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("="*60)
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! PR #112 fixes are working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Please review the errors above.")
        return 1


if __name__ == '__main__':
    exit(main())
