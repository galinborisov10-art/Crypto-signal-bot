"""
Test script to verify replay capture hook integration
Tests that signals are captured when generated
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_capture_hook_integration():
    """Test that capture hook is properly integrated"""
    print("\n" + "=" * 60)
    print("TEST: Replay Capture Hook Integration")
    print("=" * 60 + "\n")
    
    try:
        # Import the capture function
        from diagnostics import capture_signal_for_replay, ReplayCache
        
        # Clear any existing cache
        cache = ReplayCache()
        cache.clear_cache()
        print("✅ Cache cleared for test")
        
        # Simulate a signal being generated
        timestamps = pd.date_range(start='2024-01-01', periods=100, freq='15min')
        df = pd.DataFrame({
            'open': np.random.uniform(40000, 45000, 100),
            'high': np.random.uniform(40000, 45000, 100),
            'low': np.random.uniform(40000, 45000, 100),
            'close': np.random.uniform(40000, 45000, 100),
            'volume': np.random.uniform(1000, 5000, 100)
        }, index=timestamps)
        
        # Create signal data matching the format used in bot.py
        signal_data = {
            'symbol': 'BTCUSDT',
            'timeframe': '15m',
            'signal_type': 'LONG',
            'direction': 'LONG',
            'entry_price': 45000.0,
            'stop_loss': 44500.0,
            'take_profit': [45500.0, 46000.0],
            'confidence': 75,
            'timestamp': datetime.now().isoformat()
        }
        
        print("📊 Simulating signal generation...")
        print(f"   Symbol: {signal_data['symbol']}")
        print(f"   Timeframe: {signal_data['timeframe']}")
        print(f"   Type: {signal_data['signal_type']}")
        print(f"   Entry: ${signal_data['entry_price']}")
        
        # Call capture function (as bot.py does)
        try:
            capture_signal_for_replay(signal_data, df)
            print("✅ Capture function executed successfully")
        except Exception as e:
            print(f"❌ Capture function failed: {e}")
            return False
        
        # Verify signal was captured
        signals = cache.load_signals()
        print(f"\n📈 Cache status: {len(signals)} signal(s) captured")
        
        if len(signals) == 0:
            print("❌ No signals in cache - capture hook failed!")
            return False
        
        # Verify signal data
        captured = signals[0]
        print(f"\n✅ Signal captured successfully!")
        print(f"   Symbol: {captured.symbol}")
        print(f"   Timeframe: {captured.timeframe}")
        print(f"   Type: {captured.original_signal['signal_type']}")
        print(f"   Klines: {len(captured.klines_snapshot)} rows")
        
        # Verify all required fields are present
        required_fields = ['symbol', 'timeframe', 'signal_type', 'direction', 
                          'entry_price', 'stop_loss', 'take_profit', 'confidence']
        missing_fields = [f for f in required_fields if f not in captured.original_signal]
        
        if missing_fields:
            print(f"❌ Missing fields in captured signal: {missing_fields}")
            return False
        
        print(f"✅ All required fields present in captured signal")
        
        # Clean up
        cache.clear_cache()
        print("\n✅ Test cache cleared")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_capture_hook_in_bot_code():
    """Verify capture hooks exist in bot.py"""
    print("\n" + "=" * 60)
    print("TEST: Verify Capture Hooks in bot.py")
    print("=" * 60 + "\n")
    
    try:
        with open('bot.py', 'r') as f:
            bot_code = f.read()
        
        # Check for capture hooks
        checks = {
            'Import statement': 'from diagnostics import capture_signal_for_replay',
            'Signal data creation': "'signal_type':",
            'Capture function call': 'capture_signal_for_replay(signal_data, df)',
            'Error handling': 'Replay capture failed (non-critical)',
        }
        
        results = []
        for check_name, check_pattern in checks.items():
            found = check_pattern in bot_code
            status = "✅" if found else "❌"
            print(f"{status} {check_name}: {'Found' if found else 'Missing'}")
            results.append(found)
        
        # Count occurrences
        capture_calls = bot_code.count('capture_signal_for_replay(signal_data, df)')
        print(f"\n📊 Capture hooks found: {capture_calls}")
        print(f"   Expected: 2 (send_alert_signal + signal_cmd)")
        
        if capture_calls >= 2:
            print("✅ Both capture hooks are present")
        else:
            print(f"❌ Missing capture hooks (found {capture_calls}, expected 2)")
            results.append(False)
        
        if all(results):
            print("\n✅ All checks passed!")
            return True
        else:
            print("\n❌ Some checks failed")
            return False
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("PHASE 2B: REPLAY CAPTURE HOOK TESTS")
    print("=" * 60)
    
    results = []
    
    # Test 1: Code verification
    results.append(("Code Integration", test_capture_hook_in_bot_code()))
    
    # Test 2: Functional test
    results.append(("Capture Functionality", test_capture_hook_integration()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Replay capture hook is working correctly.")
        return 0
    else:
        print(f"\n⚠️ {total - passed} test(s) failed.")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
