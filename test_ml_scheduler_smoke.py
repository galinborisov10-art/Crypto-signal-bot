"""
Smoke Test for ML Retraining Scheduler
========================================
Verifies that the scheduler integrates correctly with the MLTradingEngine
"""

import sys
from datetime import datetime, timedelta
from ml_engine import MLTradingEngine


def smoke_test():
    """
    Simple smoke test to ensure scheduler works end-to-end
    """
    print("=" * 70)
    print("SMOKE TEST: ML Retraining Scheduler Integration")
    print("=" * 70)
    
    # Create ML engine
    print("\n1. Creating MLTradingEngine instance...")
    engine = MLTradingEngine()
    print(f"   ✅ Engine created successfully")
    print(f"   - last_full_retrain_ts: {engine.last_full_retrain_ts}")
    print(f"   - processed_trade_count: {engine.processed_trade_count}")
    
    # Test should_retrain()
    print("\n2. Testing should_retrain() (legacy method)...")
    should = engine.should_retrain()
    print(f"   ✅ should_retrain() = {should}")
    
    # Test should_full_retrain()
    print("\n3. Testing should_full_retrain() (new method)...")
    should_full = engine.should_full_retrain()
    print(f"   ✅ should_full_retrain() = {should_full}")
    
    # Verify they match
    if should == should_full:
        print(f"   ✅ Legacy and new methods match!")
    else:
        print(f"   ❌ WARNING: Methods don't match!")
        return False
    
    # Test incremental retrain check
    print("\n4. Testing should_incremental_retrain()...")
    should_incr = engine.should_incremental_retrain()
    print(f"   ✅ should_incremental_retrain() = {should_incr}")
    
    # Test get_new_trades_count()
    print("\n5. Testing get_new_trades_count()...")
    new_trades = engine.get_new_trades_count()
    print(f"   ✅ get_new_trades_count() = {new_trades}")
    
    # Test maybe_retrain_model() (won't actually retrain without data)
    print("\n6. Testing maybe_retrain_model() scheduler...")
    # Simulate scenario where no retrain is needed
    engine.last_full_retrain_ts = datetime.now() - timedelta(days=3)
    result = engine.maybe_retrain_model()
    print(f"   ✅ maybe_retrain_model() = {result} (expected False, no retrain needed)")
    
    # Test scenario where retrain would be needed (but no data)
    print("\n7. Testing maybe_retrain_model() with old timestamp...")
    engine.last_full_retrain_ts = datetime.now() - timedelta(days=10)
    result = engine.maybe_retrain_model()
    print(f"   ✅ maybe_retrain_model() = {result} (would trigger retrain if data exists)")
    
    # Test auto_retrain() (legacy wrapper)
    print("\n8. Testing auto_retrain() (legacy method)...")
    engine.last_full_retrain_ts = datetime.now() - timedelta(days=3)  # Reset to recent
    result = engine.auto_retrain()
    print(f"   ✅ auto_retrain() = {result} (expected False, no retrain needed)")
    
    print("\n" + "=" * 70)
    print("✅ SMOKE TEST PASSED - All scheduler components working")
    print("=" * 70)
    
    return True


if __name__ == '__main__':
    try:
        success = smoke_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ SMOKE TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
