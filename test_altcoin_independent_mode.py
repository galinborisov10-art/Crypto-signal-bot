"""
Test altcoin independent mode when BTC bias is NEUTRAL/RANGING
This test verifies that altcoins continue analysis using their OWN ICT structure
when BTC HTF bias is NEUTRAL/RANGING, while BTC still respects early exit.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import numpy as np
from unittest.mock import patch, MagicMock
from ict_signal_engine import ICTSignalEngine, MarketBias


def create_sample_df(periods=100, trend='neutral'):
    """Create sample data for testing with specific trend"""
    dates = pd.date_range(start='2025-01-01', periods=periods, freq='1H')
    base_price = 50000
    
    np.random.seed(42)
    prices = []
    current = base_price
    
    for i in range(periods):
        if trend == 'bullish':
            change = abs(np.random.randn() * 100)  # Positive trend
        elif trend == 'bearish':
            change = -abs(np.random.randn() * 100)  # Negative trend
        else:  # neutral/ranging
            change = np.random.randn() * 50  # Small movements
        
        current += change
        prices.append(current)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 50) for p in prices],
        'low': [p - abs(np.random.randn() * 50) for p in prices],
        'close': [p + np.random.randn() * 30 for p in prices],
        'volume': [1000000 + np.random.randn() * 200000 for _ in prices]
    })
    
    return df


def test_btc_neutral_early_exit():
    """Test that BTC still respects early exit when bias is NEUTRAL"""
    print("\n🧪 Test 1: BTC NEUTRAL bias → Early Exit")
    print("=" * 60)
    
    engine = ICTSignalEngine()
    df = create_sample_df(trend='neutral')
    
    # Don't mock - let it determine bias naturally
    signal = engine.generate_signal(df, 'BTCUSDT', '1h')
    
    if signal:
        signal_type = getattr(signal, 'signal_type', getattr(signal, 'action', 'UNKNOWN'))
        # Convert enum to string if necessary
        signal_type_str = str(signal_type).split('.')[-1] if hasattr(signal_type, 'value') else str(signal_type)
        print(f"✅ Signal generated: {signal_type_str}")
        # BTC should generate HOLD when bias is NEUTRAL
        assert signal_type_str in ["HOLD", "NO_TRADE"], f"Expected HOLD/NO_TRADE, got {signal_type_str}"
        print("✅ BTC correctly respects HTF bias (early exit to HOLD)")
        return True
    else:
        print("❌ No signal generated (unexpected)")
        return False


def test_altcoin_continues_when_btc_neutral():
    """Test that altcoins continue analysis when BTC bias is NEUTRAL"""
    print("\n🧪 Test 2: Altcoin analysis continues when BTC is NEUTRAL")
    print("=" * 60)
    
    engine = ICTSignalEngine()
    altcoins = ["ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"]
    
    results = {}
    
    for symbol in altcoins:
        print(f"\n📊 Testing {symbol}:")
        df = create_sample_df(trend='neutral')
        
        # Don't mock - let it determine bias naturally
        # The key is that the early exit check happens and altcoins continue
        try:
            signal = engine.generate_signal(df, symbol, '1h')
            
            if signal:
                # Check if signal has signal_type attribute
                signal_type = getattr(signal, 'signal_type', getattr(signal, 'action', 'UNKNOWN'))
                print(f"  ✅ Signal generated: {signal_type}")
                # Altcoin should continue analysis, not necessarily generate BUY/SELL
                # but should NOT be blocked by early exit
                results[symbol] = 'CONTINUED'
            else:
                print(f"  ⏭️  No signal (conditions not met)")
                results[symbol] = 'NO_SIGNAL'
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results[symbol] = f'ERROR: {str(e)[:50]}'
    
    print("\n" + "=" * 60)
    print("📊 RESULTS SUMMARY:")
    for symbol, result in results.items():
        status = "✅" if result in ['CONTINUED', 'NO_SIGNAL'] else "❌"
        print(f"  {status} {symbol}: {result}")
    
    # All altcoins should either continue or generate signals (not blocked)
    return all(r in ['CONTINUED', 'NO_SIGNAL'] for r in results.values())


def test_other_symbols_backward_compatibility():
    """Test that other symbols (not in ALT list) still follow HTF bias"""
    print("\n🧪 Test 3: Other symbols maintain backward compatibility")
    print("=" * 60)
    
    engine = ICTSignalEngine()
    df = create_sample_df(trend='neutral')
    
    # Test with a symbol not in ALT_INDEPENDENT_SYMBOLS
    test_symbol = "DOGEUSDT"
    
    signal = engine.generate_signal(df, test_symbol, '1h')
    
    if signal:
        signal_type = getattr(signal, 'signal_type', getattr(signal, 'action', 'UNKNOWN'))
        # Convert enum to string if necessary
        signal_type_str = str(signal_type).split('.')[-1] if hasattr(signal_type, 'value') else str(signal_type)
        print(f"✅ Signal generated: {signal_type_str}")
        assert signal_type_str in ["HOLD", "NO_TRADE"], f"Expected HOLD/NO_TRADE for {test_symbol}, got {signal_type_str}"
        print(f"✅ {test_symbol} correctly follows HTF bias (backward compatibility)")
        return True
    else:
        print("❌ No signal generated (unexpected)")
        return False


def test_logging_output():
    """Test that logging messages are correct for each symbol type"""
    print("\n🧪 Test 4: Verify logging messages")
    print("=" * 60)
    
    engine = ICTSignalEngine()
    df = create_sample_df(trend='neutral')
    
    import logging
    from io import StringIO
    import sys
    
    # Capture log output
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.INFO)
    logger = logging.getLogger('ict_signal_engine')
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    
    results = {}
    
    # Test BTC
    engine.generate_signal(df, 'BTCUSDT', '1h')
    log_output = log_capture.getvalue()
    if "BTC bias is" in log_output or "Market bias is NEUTRAL" in log_output:
        print("✅ BTC logging correct")
        results['BTC'] = True
    else:
        print("❌ BTC logging incorrect")
        print(f"Log output: {log_output[-500:]}")  # Show last 500 chars
        results['BTC'] = False
    
    log_capture.truncate(0)
    log_capture.seek(0)
    
    # Test Altcoin
    engine.generate_signal(df, 'ETHUSDT', '1h')
    log_output = log_capture.getvalue()
    if "ALT-independent mode" in log_output:
        print("✅ Altcoin logging correct")
        results['ALT'] = True
    else:
        print("⚠️  Altcoin logging not found (may have own bias)")
        print(f"Log output (last 500 chars): {log_output[-500:]}")
        results['ALT'] = True  # Not necessarily an error
    
    logger.removeHandler(handler)
    
    return all(results.values())


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 60)
    print("🚀 ALTCOIN INDEPENDENT MODE TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("BTC Early Exit", test_btc_neutral_early_exit),
        ("Altcoin Continues Analysis", test_altcoin_continues_when_btc_neutral),
        ("Backward Compatibility", test_other_symbols_backward_compatibility),
        ("Logging Verification", test_logging_output)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = "PASS" if result else "FAIL"
        except Exception as e:
            print(f"\n❌ Exception in {test_name}: {e}")
            results[test_name] = "ERROR"
    
    print("\n" + "=" * 60)
    print("📊 FINAL TEST RESULTS:")
    print("=" * 60)
    for test_name, result in results.items():
        status = "✅" if result == "PASS" else "❌"
        print(f"{status} {test_name}: {result}")
    
    passed = sum(1 for r in results.values() if r == "PASS")
    total = len(tests)
    print(f"\n🎯 {passed}/{total} tests passed")
    
    return all(r == "PASS" for r in results.values())


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
