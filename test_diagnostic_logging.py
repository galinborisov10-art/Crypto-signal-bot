#!/usr/bin/env python3
"""
Test Diagnostic Logging for ICT Signal Engine
Verifies that step-level diagnostic logs are working correctly
"""

import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Configure logging to see the diagnostic output
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Import the ICT Signal Engine
from ict_signal_engine import ICTSignalEngine

def create_test_data():
    """Create sample OHLCV data for testing"""
    dates = pd.date_range(start='2025-01-01', periods=100, freq='1H')
    np.random.seed(42)
    
    # Simulate price data with a trend
    base_price = 50000
    prices = []
    current = base_price
    
    for i in range(100):
        # Add some volatility
        change = np.random.randn() * 100
        current += change
        prices.append(current)
    
    # Create dataframe
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 50) for p in prices],
        'low': [p - abs(np.random.randn() * 50) for p in prices],
        'close': [p + np.random.randn() * 30 for p in prices],
        'volume': [1000000 + np.random.randn() * 200000 for _ in prices]
    })
    
    return df

def test_diagnostic_logging():
    """Test the diagnostic logging output"""
    print("=" * 80)
    print("🧪 Testing ICT Signal Engine Diagnostic Logging")
    print("=" * 80)
    print()
    
    # Create test data
    df = create_test_data()
    
    # Initialize engine
    engine = ICTSignalEngine()
    
    # Generate signal (this should produce diagnostic logs)
    print("Generating signal for BTCUSDT...")
    print()
    
    signal = engine.generate_signal(df, symbol="BTCUSDT", timeframe="1H")
    
    print()
    print("=" * 80)
    print("📊 Test Results")
    print("=" * 80)
    
    if signal:
        print(f"✅ Signal Generated: {signal.signal_type.value}")
        print(f"   Confidence: {signal.confidence:.1f}%")
        
        if signal.signal_type.value != "HOLD":
            print(f"   Entry: ${signal.entry_price:.2f}")
            print(f"   SL: ${signal.sl_price:.2f}")
            print(f"   TP1: ${signal.tp_prices[0]:.2f}" if signal.tp_prices else "   TP1: N/A")
            print(f"   RR: {signal.risk_reward_ratio:.2f}")
        else:
            print(f"   Bias: {signal.bias.value if hasattr(signal, 'bias') else 'N/A'}")
            print(f"   Reason: {signal.reasoning if hasattr(signal, 'reasoning') else 'N/A'}")
    else:
        print("ℹ️  No signal generated (blocked)")
    
    print()
    print("=" * 80)
    print("✅ Diagnostic Logging Test Complete")
    print("=" * 80)
    print()
    print("📝 Check the logs above to verify:")
    print("   1. Step 7: Bias determination with score breakdown")
    print("   2. Step 7b: Early exit reason (if applicable)")
    print("   3. Step 8: Entry zone validation")
    print("   4. Step 9: SL/TP calculation")
    print("   5. Step 10: RR validation")
    print("   6. Step 11: Confidence checks")
    print("   7. Step 12: Final signal generation")
    print()

if __name__ == "__main__":
    test_diagnostic_logging()
