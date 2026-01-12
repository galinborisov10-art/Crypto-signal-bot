#!/usr/bin/env python3
"""
Test Diagnostic Logging - Bullish Scenario
Creates a scenario that passes Step 7 to test later steps
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

def create_bullish_test_data():
    """Create sample OHLCV data with bullish setup"""
    dates = pd.date_range(start='2025-01-01', periods=150, freq='1H')
    np.random.seed(123)
    
    # Simulate price data with a bullish trend
    base_price = 50000
    prices = []
    current = base_price
    
    for i in range(150):
        # Create bullish trend
        if i < 50:
            # Consolidation
            change = np.random.randn() * 50
        elif i < 80:
            # Order Block formation (bearish candles before reversal)
            change = -80 + np.random.randn() * 30
        elif i < 100:
            # Displacement (strong bullish move)
            change = 200 + np.random.randn() * 50
        else:
            # Continuation
            change = 100 + np.random.randn() * 80
        
        current += change
        prices.append(current)
    
    # Create dataframe
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 80) for p in prices],
        'low': [p - abs(np.random.randn() * 80) for p in prices],
        'close': [p + np.random.randn() * 40 for p in prices],
        'volume': [1000000 + abs(np.random.randn() * 300000) for _ in prices]
    })
    
    return df

def test_bullish_scenario():
    """Test diagnostic logging with bullish scenario"""
    print("=" * 80)
    print("🧪 Testing ICT Signal Engine - Bullish Scenario")
    print("=" * 80)
    print()
    
    # Create bullish test data
    df = create_bullish_test_data()
    
    # Initialize engine
    engine = ICTSignalEngine()
    
    # Generate signal (this should produce diagnostic logs for more steps)
    print("Generating signal for ETHUSDT (alt-independent mode)...")
    print()
    
    signal = engine.generate_signal(df, symbol="ETHUSDT", timeframe="1H")
    
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
            print(f"   Reason: Check logs above for blocked_at_step")
    else:
        print("ℹ️  No signal generated (blocked)")
    
    print()
    print("=" * 80)
    print("✅ Diagnostic Logging Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    test_bullish_scenario()
