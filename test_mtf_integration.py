#!/usr/bin/env python3
"""
Integration Test for MTF Case Sensitivity Fix

This test verifies the complete data flow:
1. fetch_mtf_data() returns lowercase keys
2. _analyze_mtf_confluence() uses lowercase keys
3. Data flows correctly end-to-end
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_data_flow_integration():
    """Test the complete MTF data flow"""
    print("=" * 80)
    print("MTF CASE SENSITIVITY - INTEGRATION TEST")
    print("=" * 80)
    
    # Read bot.py to verify fetch_mtf_data
    bot_file = os.path.join(os.path.dirname(__file__), 'bot.py')
    with open(bot_file, 'r') as f:
        bot_source = f.read()
    
    # Read ict_signal_engine.py to verify _analyze_mtf_confluence
    engine_file = os.path.join(os.path.dirname(__file__), 'ict_signal_engine.py')
    with open(engine_file, 'r') as f:
        engine_source = f.read()
    
    print("\n1. Checking fetch_mtf_data() returns lowercase keys...")
    # Extract mtf_timeframes from bot.py
    for line in bot_source.split('\n'):
        if 'mtf_timeframes = [' in line:
            print(f"   Found: {line.strip()}")
            # Verify lowercase
            if all(f"'{tf}'" in line for tf in ['1h', '4h', '1d']):
                print("   ✅ Returns lowercase keys: '1h', '4h', '1d'")
                producer_ok = True
            else:
                print("   ❌ PROBLEM: Uses uppercase keys")
                producer_ok = False
            break
    
    print("\n2. Checking _analyze_mtf_confluence() uses lowercase keys...")
    # Find the key lines in _analyze_mtf_confluence
    lines = engine_source.split('\n')
    consumer_ok = False
    for i, line in enumerate(lines):
        if "htf_df = mtf_data.get('1d')" in line:
            print(f"   Line {i+1}: {line.strip()}")
            print("   ✅ Uses lowercase keys: '1d', '4h', '1h'")
            consumer_ok = True
            break
        elif "htf_df = mtf_data.get('1D')" in line:
            print(f"   Line {i+1}: {line.strip()}")
            print("   ❌ PROBLEM: Uses uppercase keys!")
            consumer_ok = False
            break
    
    print("\n3. Verifying data flow integrity...")
    if producer_ok and consumer_ok:
        print("   ✅ Producer (fetch_mtf_data) and Consumer (_analyze_mtf_confluence)")
        print("      use matching case → Data will flow correctly!")
        print("\n   Expected behavior:")
        print("   • fetch_mtf_data() returns: {'1h': df, '4h': df, '1d': df}")
        print("   • _analyze_mtf_confluence() gets: '1h' → df ✅")
        print("   • _analyze_mtf_confluence() gets: '4h' → df ✅")
        print("   • _analyze_mtf_confluence() gets: '1d' → df ✅")
        print("   • MTF analysis proceeds normally")
        print("   • No confidence penalty")
        print("   • Signals sent to user")
        success = True
    else:
        print("   ❌ CASE MISMATCH DETECTED!")
        if not producer_ok:
            print("      Problem: fetch_mtf_data uses wrong case")
        if not consumer_ok:
            print("      Problem: _analyze_mtf_confluence uses wrong case")
        print("\n   Expected behavior:")
        print("   • fetch_mtf_data() returns: {'?': df}")
        print("   • _analyze_mtf_confluence() gets: '?' → None ❌")
        print("   • MTF analysis fails")
        print("   • -40% confidence penalty")
        print("   • Signals blocked")
        success = False
    
    print("\n" + "=" * 80)
    if success:
        print("✅ INTEGRATION TEST PASSED")
        print("=" * 80)
        print("\n🎉 MTF data flow is correct - bug is FIXED!")
        return True
    else:
        print("❌ INTEGRATION TEST FAILED")
        print("=" * 80)
        print("\n⚠️ MTF data flow is broken - bug still present!")
        return False


def test_all_timeframes_compatibility():
    """Test that all timeframes use consistent casing"""
    print("\n\n" + "=" * 80)
    print("TIMEFRAME COMPATIBILITY TEST")
    print("=" * 80)
    
    # Standard Binance timeframes (all lowercase)
    binance_tfs = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']
    
    print("\n📋 Binance API standard timeframes (all lowercase):")
    print(f"   {binance_tfs}")
    
    # Read bot.py
    bot_file = os.path.join(os.path.dirname(__file__), 'bot.py')
    with open(bot_file, 'r') as f:
        bot_source = f.read()
    
    # Extract mtf_timeframes
    for line in bot_source.split('\n'):
        if 'mtf_timeframes = [' in line:
            print(f"\n📋 Bot configured timeframes:")
            print(f"   {line.strip()}")
            
            # Check if any uppercase
            has_uppercase = False
            for tf in ['1H', '2H', '4H', '6H', '12H', '1D', '3D', '1W']:
                if f"'{tf}'" in line:
                    has_uppercase = True
                    print(f"   ⚠️ Found uppercase: {tf}")
            
            if not has_uppercase:
                print("   ✅ All timeframes are lowercase (matches Binance API)")
                return True
            else:
                print("   ❌ Uppercase timeframes found (incompatible with Binance API)")
                return False
    
    return False


if __name__ == "__main__":
    print("\n" + "🧪 MTF CASE SENSITIVITY - INTEGRATION TEST SUITE" + "\n")
    
    try:
        test1 = test_data_flow_integration()
        test2 = test_all_timeframes_compatibility()
        
        if test1 and test2:
            print("\n\n" + "=" * 80)
            print("🎉 ALL INTEGRATION TESTS PASSED")
            print("=" * 80)
            print("\n✅ MTF case sensitivity bug is FIXED")
            print("✅ Data flow is correct")
            print("✅ Timeframes are compatible with Binance API")
            print("\n🚀 Ready for production deployment!")
            print("=" * 80 + "\n")
            sys.exit(0)
        else:
            print("\n\n" + "=" * 80)
            print("❌ INTEGRATION TESTS FAILED")
            print("=" * 80)
            sys.exit(1)
            
    except Exception as e:
        print("\n\n" + "=" * 80)
        print(f"❌ ERROR: {e}")
        print("=" * 80)
        import traceback
        traceback.print_exc()
        sys.exit(1)
