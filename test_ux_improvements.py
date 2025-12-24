#!/usr/bin/env python3
"""
Test UX Improvements: Caching, Timeout, Performance Tracking

This test validates that the new UX improvement features work correctly.
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
import sys
import os

# Add current directory to path and import from bot.py specifically
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import bot module directly
import importlib.util
spec = importlib.util.spec_from_file_location("bot_module", "bot.py")
bot_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot_module)

def test_cache_functions():
    """Test caching system"""
    print("Testing cache functions...")
    
    # Use functions from bot_module
    get_cached = bot_module.get_cached
    set_cache = bot_module.set_cache
    CACHE = bot_module.CACHE
    CACHE_TTL = bot_module.CACHE_TTL
    
    # Test 1: Empty cache returns None
    result = get_cached('backtest', '30d')
    assert result is None, "Empty cache should return None"
    print("✅ Test 1: Empty cache returns None")
    
    # Test 2: Set and get from cache
    test_data = {'test': 'data', 'value': 123}
    set_cache('backtest', '30d', test_data)
    result = get_cached('backtest', '30d')
    assert result == test_data, "Cache should return the stored data"
    print("✅ Test 2: Cache set and get works")
    
    # Test 3: Cache expiration
    # Temporarily set short TTL
    original_ttl = CACHE_TTL['backtest']
    CACHE_TTL['backtest'] = 1  # 1 second
    
    set_cache('backtest', 'expire_test', {'data': 'expires'})
    time.sleep(1.5)  # Wait for expiration
    result = get_cached('backtest', 'expire_test')
    assert result is None, "Expired cache should return None"
    print("✅ Test 3: Cache expiration works")
    
    # Restore original TTL
    CACHE_TTL['backtest'] = original_ttl
    
    # Test 4: Multiple cache types
    set_cache('ml_performance', '60d', {'ml': 'data'})
    set_cache('market', 'BTCUSDT_4h', {'market': 'data'})
    
    assert get_cached('ml_performance', '60d') is not None
    assert get_cached('market', 'BTCUSDT_4h') is not None
    print("✅ Test 4: Multiple cache types work")
    
    print("✅ All cache tests passed!\n")


async def test_timeout_decorator():
    """Test timeout protection"""
    print("Testing timeout decorator...")
    
    with_timeout = bot_module.with_timeout
    
    # Test 1: Function completes within timeout
    @with_timeout(seconds=2)
    async def fast_function():
        await asyncio.sleep(0.5)
        return "success"
    
    result = await fast_function()
    assert result == "success", "Fast function should complete successfully"
    print("✅ Test 1: Function completes within timeout")
    
    # Test 2: Function times out
    @with_timeout(seconds=1)
    async def slow_function():
        await asyncio.sleep(3)
        return "should not reach here"
    
    try:
        await slow_function()
        assert False, "Should have raised TimeoutError"
    except TimeoutError as e:
        assert "timed out after 1 seconds" in str(e)
        print("✅ Test 2: Timeout protection works")
    
    print("✅ All timeout tests passed!\n")


async def test_performance_tracking():
    """Test performance metrics tracking"""
    print("Testing performance tracking...")
    
    track_metric = bot_module.track_metric
    get_metrics_summary = bot_module.get_metrics_summary
    
    # Test 1: Track metrics
    track_metric("test_operation", 1.5)
    track_metric("test_operation", 2.0)
    track_metric("test_operation", 1.8)
    
    summary = get_metrics_summary()
    assert "test_operation" in summary
    assert summary["test_operation"]["count"] == 3
    assert summary["test_operation"]["avg"] > 0
    print("✅ Test 1: Metrics tracking works")
    
    # Test 2: Calculate statistics correctly
    stats = summary["test_operation"]
    assert stats["min"] == 1.5
    assert stats["max"] == 2.0
    assert abs(stats["avg"] - 1.7666) < 0.01  # Average of 1.5, 2.0, 1.8
    print("✅ Test 2: Statistics calculated correctly")
    
    print("✅ All performance tracking tests passed!\n")


def test_error_formatter():
    """Test user-friendly error formatting"""
    print("Testing error formatter...")
    
    format_user_error = bot_module.format_user_error
    
    # Test different error types
    errors = [
        (TimeoutError("Operation timed out"), "Операцията отне твърде дълго време"),
        (FileNotFoundError("File not found"), "Няма данни за анализ"),
        (ValueError("Invalid value"), "Невалидни данни"),
    ]
    
    for error, expected_msg in errors:
        result = format_user_error(error, "Test Operation")
        assert expected_msg in result, f"Error message should contain: {expected_msg}"
        assert "Test Operation" in result, "Should include operation name"
    
    print("✅ Error formatter tests passed!\n")


async def test_async_backtest_helper():
    """Test async backtest wrapper (without actually running backtest)"""
    print("Testing async backtest helper structure...")
    
    # Just verify the function exists and has correct signature
    run_backtest_async = bot_module.run_backtest_async
    import inspect
    
    assert asyncio.iscoroutinefunction(run_backtest_async), "Should be async function"
    
    sig = inspect.signature(run_backtest_async)
    params = list(sig.parameters.keys())
    assert 'days' in params, "Should have 'days' parameter"
    assert 'symbol' in params, "Should have 'symbol' parameter"
    assert 'timeframe' in params, "Should have 'timeframe' parameter"
    
    print("✅ Async backtest helper structure validated!\n")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("🧪 TESTING UX IMPROVEMENTS")
    print("=" * 60)
    print()
    
    try:
        # Synchronous tests
        test_cache_functions()
        test_error_formatter()
        
        # Asynchronous tests
        await test_timeout_decorator()
        await test_performance_tracking()
        await test_async_backtest_helper()
        
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("Summary:")
        print("  ✅ Caching system works correctly")
        print("  ✅ Timeout protection functional")
        print("  ✅ Performance metrics tracking active")
        print("  ✅ Error formatting user-friendly")
        print("  ✅ Async backtest helper properly structured")
        print()
        print("🎉 UX improvements are ready for deployment!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
