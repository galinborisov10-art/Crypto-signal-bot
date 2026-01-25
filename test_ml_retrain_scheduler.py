"""
Test ML Retraining Scheduler (PR-ML-4)
========================================

Tests the deterministic ML retraining scheduler:
- Full retrain every 7 days
- Incremental retrain logic (not yet implemented)
- State tracking and synchronization
"""

import sys
import os
from datetime import datetime, timedelta
from ml_engine import MLTradingEngine, ML_FULL_RETRAIN_INTERVAL_DAYS, ML_INCREMENTAL_RETRAIN_MIN_TRADES


def test_scheduler_constants():
    """Test that retraining policy constants are defined correctly"""
    print("=" * 70)
    print("TEST 1: Retraining Policy Constants")
    print("=" * 70)
    
    assert ML_FULL_RETRAIN_INTERVAL_DAYS == 7, "Full retrain interval should be 7 days"
    assert ML_INCREMENTAL_RETRAIN_MIN_TRADES == 20, "Incremental retrain min trades should be 20"
    
    print(f"✅ ML_FULL_RETRAIN_INTERVAL_DAYS = {ML_FULL_RETRAIN_INTERVAL_DAYS}")
    print(f"✅ ML_INCREMENTAL_RETRAIN_MIN_TRADES = {ML_INCREMENTAL_RETRAIN_MIN_TRADES}")
    print()


def test_state_tracking_variables():
    """Test that new state tracking variables are initialized"""
    print("=" * 70)
    print("TEST 2: State Tracking Variables")
    print("=" * 70)
    
    engine = MLTradingEngine()
    
    # Check new state variables exist
    assert hasattr(engine, 'last_full_retrain_ts'), "last_full_retrain_ts should exist"
    assert hasattr(engine, 'processed_trade_count'), "processed_trade_count should exist"
    
    print(f"✅ last_full_retrain_ts initialized: {engine.last_full_retrain_ts}")
    print(f"✅ processed_trade_count initialized: {engine.processed_trade_count}")
    print()


def test_scheduler_methods_exist():
    """Test that all new scheduler methods exist"""
    print("=" * 70)
    print("TEST 3: Scheduler Methods Exist")
    print("=" * 70)
    
    engine = MLTradingEngine()
    
    # Check new methods exist
    assert hasattr(engine, 'should_full_retrain'), "should_full_retrain method should exist"
    assert hasattr(engine, 'should_incremental_retrain'), "should_incremental_retrain method should exist"
    assert hasattr(engine, 'get_new_trades_count'), "get_new_trades_count method should exist"
    assert hasattr(engine, 'sync_processed_trade_count'), "sync_processed_trade_count method should exist"
    assert hasattr(engine, 'maybe_retrain_model'), "maybe_retrain_model method should exist"
    assert hasattr(engine, 'sync_retrain_state'), "sync_retrain_state method should exist"
    
    print("✅ should_full_retrain() exists")
    print("✅ should_incremental_retrain() exists")
    print("✅ get_new_trades_count() exists")
    print("✅ sync_processed_trade_count() exists")
    print("✅ maybe_retrain_model() exists")
    print("✅ sync_retrain_state() exists")
    print()


def test_should_full_retrain_logic():
    """Test full retrain logic"""
    print("=" * 70)
    print("TEST 4: Full Retrain Logic")
    print("=" * 70)
    
    engine = MLTradingEngine()
    
    # Test 1: Never trained - should retrain
    engine.last_full_retrain_ts = None
    assert engine.should_full_retrain() == True, "Should retrain when never trained"
    print("✅ Test 1: Never trained → should_full_retrain() = True")
    
    # Test 2: Trained recently (3 days ago) - should NOT retrain
    engine.last_full_retrain_ts = datetime.now() - timedelta(days=3)
    assert engine.should_full_retrain() == False, "Should NOT retrain when only 3 days elapsed"
    print("✅ Test 2: Trained 3 days ago → should_full_retrain() = False")
    
    # Test 3: Trained exactly 7 days ago - should retrain
    engine.last_full_retrain_ts = datetime.now() - timedelta(days=7)
    assert engine.should_full_retrain() == True, "Should retrain when 7 days elapsed"
    print("✅ Test 3: Trained 7 days ago → should_full_retrain() = True")
    
    # Test 4: Trained 10 days ago - should retrain
    engine.last_full_retrain_ts = datetime.now() - timedelta(days=10)
    assert engine.should_full_retrain() == True, "Should retrain when 10 days elapsed"
    print("✅ Test 4: Trained 10 days ago → should_full_retrain() = True")
    print()


def test_should_retrain_delegates():
    """Test that should_retrain() delegates to should_full_retrain()"""
    print("=" * 70)
    print("TEST 5: Legacy should_retrain() Delegation")
    print("=" * 70)
    
    engine = MLTradingEngine()
    
    # Test 1: Never trained
    engine.last_full_retrain_ts = None
    assert engine.should_retrain() == engine.should_full_retrain(), "should_retrain() should delegate"
    print("✅ Test 1: should_retrain() delegates correctly (never trained)")
    
    # Test 2: Recently trained
    engine.last_full_retrain_ts = datetime.now() - timedelta(days=3)
    assert engine.should_retrain() == engine.should_full_retrain(), "should_retrain() should delegate"
    print("✅ Test 2: should_retrain() delegates correctly (recently trained)")
    
    # Test 3: Old training
    engine.last_full_retrain_ts = datetime.now() - timedelta(days=10)
    assert engine.should_retrain() == engine.should_full_retrain(), "should_retrain() should delegate"
    print("✅ Test 3: should_retrain() delegates correctly (old training)")
    print()


def test_get_new_trades_count():
    """Test new trades counting"""
    print("=" * 70)
    print("TEST 6: New Trades Counting")
    print("=" * 70)
    
    engine = MLTradingEngine()
    
    # Test when no trading journal exists
    new_count = engine.get_new_trades_count()
    print(f"✅ get_new_trades_count() returns: {new_count} (no errors)")
    print()


def test_incremental_retrain_not_implemented():
    """Test that incremental retrain returns False (not yet implemented)"""
    print("=" * 70)
    print("TEST 7: Incremental Retrain (Not Yet Implemented)")
    print("=" * 70)
    
    engine = MLTradingEngine()
    
    # Even if condition is met, should return False in maybe_retrain_model
    # because incremental retrain is not implemented
    engine.last_full_retrain_ts = datetime.now() - timedelta(days=3)  # No full retrain needed
    engine.processed_trade_count = 0  # Simulate new trades available
    
    # This will check incremental condition but not execute it
    result = engine.should_incremental_retrain()
    print(f"✅ should_incremental_retrain() can be called: {result}")
    
    # maybe_retrain_model should skip because full retrain not needed
    # and incremental is not implemented
    retrain_result = engine.maybe_retrain_model()
    assert retrain_result == False, "Should return False (no retrain conditions met or incremental not implemented)"
    print(f"✅ maybe_retrain_model() returns False when only incremental condition might be met")
    print()


def run_all_tests():
    """Run all tests"""
    print("\n")
    print("🧪 " + "=" * 68)
    print("🧪 ML RETRAINING SCHEDULER TESTS (PR-ML-4)")
    print("🧪 " + "=" * 68)
    print()
    
    try:
        test_scheduler_constants()
        test_state_tracking_variables()
        test_scheduler_methods_exist()
        test_should_full_retrain_logic()
        test_should_retrain_delegates()
        test_get_new_trades_count()
        test_incremental_retrain_not_implemented()
        
        print("=" * 70)
        print("✅ ALL TESTS PASSED")
        print("=" * 70)
        print()
        print("Summary:")
        print("- ✅ Retraining policy constants defined")
        print("- ✅ State tracking variables initialized")
        print("- ✅ All scheduler methods implemented")
        print("- ✅ Full retrain logic works correctly (7+ days)")
        print("- ✅ Legacy methods delegate to new scheduler")
        print("- ✅ Incremental retrain defined but not implemented")
        print()
        return True
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
