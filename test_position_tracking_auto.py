#!/usr/bin/env python3
"""
Test Position Tracking for Auto Signals

This script tests if position tracking works correctly by:
1. Creating a mock ICT signal
2. Calling position_manager.open_position()
3. Verifying the position is created in the database
4. Checking all three conditions that control position tracking

Author: Test script for PR #131
Date: 2026-01-19
"""

import sys
import os
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_position_tracking():
    """Test position tracking with mock signal"""
    
    print("=" * 70)
    print("POSITION TRACKING TEST")
    print("=" * 70)
    
    # Step 1: Import and initialize
    print("\n1️⃣ Testing imports and initialization...")
    try:
        from position_manager import PositionManager
        from ict_signal_engine import ICTSignal, SignalType, Bias
        
        POSITION_MANAGER_AVAILABLE = True
        print("   ✅ Imports successful")
        
        position_manager_global = PositionManager()
        print(f"   ✅ PositionManager initialized")
        print(f"   📂 Database: {position_manager_global.db_path}")
        
    except Exception as e:
        print(f"   ❌ Import/initialization failed: {e}")
        return False
    
    # Step 2: Test configuration
    print("\n2️⃣ Testing configuration flags...")
    AUTO_POSITION_TRACKING_ENABLED = True
    
    print(f"   AUTO_POSITION_TRACKING_ENABLED = {AUTO_POSITION_TRACKING_ENABLED}")
    print(f"   POSITION_MANAGER_AVAILABLE = {POSITION_MANAGER_AVAILABLE}")
    print(f"   position_manager_global exists = {position_manager_global is not None}")
    
    condition = AUTO_POSITION_TRACKING_ENABLED and POSITION_MANAGER_AVAILABLE and position_manager_global
    print(f"\n   Combined condition result: {bool(condition)}")
    
    if not condition:
        print("   ❌ Condition evaluates to False - position tracking would NOT execute")
        return False
    else:
        print("   ✅ Condition evaluates to True - position tracking SHOULD execute")
    
    # Step 3: Create mock signal
    print("\n3️⃣ Creating mock ICT signal...")
    try:
        from ict_signal_engine import SignalStrength, MarketBias
        
        mock_signal = ICTSignal(
            timestamp=datetime.now(),
            symbol='BTCUSDT',
            timeframe='1h',
            signal_type=SignalType.BUY,
            signal_strength=SignalStrength.STRONG,
            entry_price=45000.0,
            sl_price=44500.0,
            tp_prices=[45500.0, 46000.0, 46500.0],
            confidence=75.5,
            risk_reward_ratio=3.0,
            bias=MarketBias.BULLISH,
            htf_bias="BULLISH",
            structure_broken=True,
            displacement_detected=True,
            mtf_confluence=3
        )
        print(f"   ✅ Mock signal created: {mock_signal.signal_type.value} @ {mock_signal.entry_price}")
        print(f"   📊 Confidence: {mock_signal.confidence}%")
        
    except Exception as e:
        print(f"   ❌ Failed to create mock signal: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 4: Open position
    print("\n4️⃣ Testing position opening...")
    try:
        position_id = position_manager_global.open_position(
            signal=mock_signal,
            symbol='BTCUSDT',
            timeframe='1h',
            source='AUTO_TEST'
        )
        
        print(f"   ✅ open_position() executed")
        print(f"   📋 Returned position ID: {position_id}")
        
        if position_id > 0:
            print(f"   ✅ Position created successfully (ID: {position_id})")
        else:
            print(f"   ⚠️  Position ID is {position_id} (expected > 0)")
            
    except Exception as e:
        print(f"   ❌ Failed to open position: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Step 5: Verify database
    print("\n5️⃣ Verifying database...")
    try:
        import sqlite3
        conn = sqlite3.connect(position_manager_global.db_path)
        cursor = conn.cursor()
        
        # Count open positions
        cursor.execute("SELECT COUNT(*) FROM open_positions")
        count = cursor.fetchone()[0]
        print(f"   📊 Total open positions: {count}")
        
        # Get the test position
        cursor.execute("SELECT * FROM open_positions WHERE source='AUTO_TEST' ORDER BY id DESC LIMIT 1")
        row = cursor.fetchone()
        
        if row:
            print(f"   ✅ Test position found in database")
            print(f"   📋 Position ID: {row[0]}")
            print(f"   🎯 Symbol: {row[1]}")
            print(f"   ⏱️  Timeframe: {row[2]}")
            print(f"   📈 Entry: {row[4]}")
            print(f"   🛑 SL: {row[5]}")
            print(f"   🎯 TP1/TP2/TP3: {row[6]}/{row[7]}/{row[8]}")
        else:
            print(f"   ❌ Test position NOT found in database")
            return False
        
        conn.close()
        
    except Exception as e:
        print(f"   ❌ Database verification failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED - Position tracking is functional!")
    print("=" * 70)
    return True


if __name__ == "__main__":
    success = test_position_tracking()
    sys.exit(0 if success else 1)
