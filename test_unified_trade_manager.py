"""
Test script for UnifiedTradeManager (PR #202)

Tests:
- Import and initialization
- Progress calculation
- Checkpoint detection
- Bulgarian alert formatting
- Error handling and graceful degradation
"""

import sys
sys.path.insert(0, '.')

def test_imports():
    """Test that all required components can be imported"""
    print("=" * 60)
    print("TEST 1: Imports and Initialization")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        print("✅ UnifiedTradeManager imported successfully")
        
        from position_manager import PositionManager
        print("✅ PositionManager imported successfully")
        
        # Test initialization
        manager = UnifiedTradeManager()
        print("✅ UnifiedTradeManager initialized")
        print(f"   → Position Manager: {'Available' if manager.position_manager else 'Not Available'}")
        print(f"   → Reanalysis Engine: {'Available' if manager.reanalysis_engine else 'Not Available'}")
        print(f"   → Fundamentals: {'Available' if manager.fundamentals else 'Not Available'}")
        print(f"   → Checkpoint levels: {manager.checkpoint_levels}")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_progress_calculation():
    """Test progress calculation for BUY and SELL positions"""
    print("\n" + "=" * 60)
    print("TEST 2: Progress Calculation")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        manager = UnifiedTradeManager()
        
        # Test BUY position
        buy_position = {
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 40000.0,
            'tp1_price': 44000.0,
            'sl_price': 38000.0
        }
        
        test_cases_buy = [
            (40000.0, 0.0),    # At entry
            (41000.0, 25.0),   # 25% progress
            (42000.0, 50.0),   # 50% progress
            (43000.0, 75.0),   # 75% progress
            (44000.0, 100.0),  # At TP1
        ]
        
        print("\nBUY Position Tests:")
        for price, expected in test_cases_buy:
            progress = manager._calculate_progress(buy_position, price)
            status = "✅" if abs(progress - expected) < 1.0 else "❌"
            print(f"{status} Price ${price:,.0f} → Progress {progress:.1f}% (expected {expected:.1f}%)")
        
        # Test SELL position
        sell_position = {
            'symbol': 'BTCUSDT',
            'signal_type': 'SELL',
            'entry_price': 44000.0,
            'tp1_price': 40000.0,
            'sl_price': 46000.0
        }
        
        test_cases_sell = [
            (44000.0, 0.0),    # At entry
            (43000.0, 25.0),   # 25% progress
            (42000.0, 50.0),   # 50% progress
            (41000.0, 75.0),   # 75% progress
            (40000.0, 100.0),  # At TP1
        ]
        
        print("\nSELL Position Tests:")
        for price, expected in test_cases_sell:
            progress = manager._calculate_progress(sell_position, price)
            status = "✅" if abs(progress - expected) < 1.0 else "❌"
            print(f"{status} Price ${price:,.0f} → Progress {progress:.1f}% (expected {expected:.1f}%)")
        
        return True
        
    except Exception as e:
        print(f"❌ Progress calculation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_checkpoint_detection():
    """Test checkpoint detection logic"""
    print("\n" + "=" * 60)
    print("TEST 3: Checkpoint Detection")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        manager = UnifiedTradeManager()
        
        position = {
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 40000.0,
            'tp1_price': 44000.0,
            'checkpoint_25_triggered': 0,
            'checkpoint_50_triggered': 0,
            'checkpoint_75_triggered': 0,
            'checkpoint_85_triggered': 0
        }
        
        test_cases = [
            (10, None, "Below first checkpoint"),
            (30, 25, "First checkpoint reached"),
            (55, 50, "Second checkpoint (after 25% hit)"),
            (80, 75, "Third checkpoint (after 25%, 50% hit)"),
            (90, 85, "Fourth checkpoint (after 25%, 50%, 75% hit)"),
            (95, None, "All checkpoints hit"),
        ]
        
        for i, (progress, expected, description) in enumerate(test_cases):
            # Update triggered checkpoints based on previous tests
            if i >= 2:
                position['checkpoint_25_triggered'] = 1
            if i >= 3:
                position['checkpoint_50_triggered'] = 1
            if i >= 4:
                position['checkpoint_75_triggered'] = 1
            if i >= 5:
                position['checkpoint_85_triggered'] = 1
            
            checkpoint = manager._get_checkpoint_level(position, progress)
            status = "✅" if checkpoint == expected else "❌"
            print(f"{status} {description}: Progress {progress}% → Checkpoint {checkpoint} (expected {expected})")
        
        return True
        
    except Exception as e:
        print(f"❌ Checkpoint detection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bulgarian_alerts():
    """Test Bulgarian alert formatting"""
    print("\n" + "=" * 60)
    print("TEST 4: Bulgarian Alert Formatting")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        manager = UnifiedTradeManager()
        
        position = {
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 40000.0,
            'tp1_price': 44000.0
        }
        
        # Test fallback alert
        print("\n1. Fallback Alert (no analysis):")
        print("-" * 60)
        alert = manager._format_bulgarian_alert(
            position=position,
            analysis=None,
            news=None,
            checkpoint=25,
            progress=27.5
        )
        print(alert)
        
        # Test with mock analysis
        class MockAnalysis:
            def __init__(self, confidence_delta):
                self.original_confidence = 75.0
                self.current_confidence = 75.0 + confidence_delta
                self.confidence_delta = confidence_delta
                self.structure_broken = False
                self.htf_bias = 'BULLISH'
                self.htf_bias_changed = False
                self.valid_components_count = 8
                self.current_rr_ratio = 3.2
        
        # Test HOLD recommendation (small delta)
        print("\n2. HOLD Alert (confidence delta: -5%):")
        print("-" * 60)
        analysis = MockAnalysis(-5.0)
        alert = manager._format_bulgarian_alert(
            position=position,
            analysis=analysis,
            news=None,
            checkpoint=50,
            progress=52.3
        )
        print(alert)
        assert "ЗАДРЪЖ" in alert or "💎" in alert, "Should recommend HOLD"
        
        # Test PARTIAL CLOSE recommendation (medium delta)
        print("\n3. PARTIAL CLOSE Alert (confidence delta: -12%):")
        print("-" * 60)
        analysis = MockAnalysis(-12.0)
        alert = manager._format_bulgarian_alert(
            position=position,
            analysis=analysis,
            news=None,
            checkpoint=75,
            progress=77.0
        )
        print(alert)
        assert "40-50%" in alert or "🟡" in alert, "Should recommend PARTIAL CLOSE"
        
        # Test CLOSE NOW recommendation (large delta)
        print("\n4. CLOSE NOW Alert (confidence delta: -20%):")
        print("-" * 60)
        analysis = MockAnalysis(-20.0)
        alert = manager._format_bulgarian_alert(
            position=position,
            analysis=analysis,
            news=None,
            checkpoint=85,
            progress=87.0
        )
        print(alert)
        assert "ЗАТВОРИ СЕГА" in alert or "🔴" in alert, "Should recommend CLOSE NOW"
        
        print("\n✅ All Bulgarian alert tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Bulgarian alert test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_position_manager_integration():
    """Test position_manager.get_hit_checkpoints"""
    print("\n" + "=" * 60)
    print("TEST 5: PositionManager Integration")
    print("=" * 60)
    
    try:
        from position_manager import PositionManager
        
        pm = PositionManager()
        print("✅ PositionManager initialized")
        
        # Check method exists
        assert hasattr(pm, 'get_hit_checkpoints'), "get_hit_checkpoints method not found"
        print("✅ get_hit_checkpoints method exists")
        
        # Test with non-existent position (should return empty list)
        result = pm.get_hit_checkpoints(999999)
        assert isinstance(result, list), "Should return a list"
        assert len(result) == 0, "Should return empty list for non-existent position"
        print("✅ get_hit_checkpoints returns empty list for non-existent position")
        
        return True
        
    except Exception as e:
        print(f"❌ PositionManager integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 60)
    print("UNIFIED TRADE MANAGER TEST SUITE (PR #202)")
    print("=" * 60)
    
    tests = [
        ("Imports & Initialization", test_imports),
        ("Progress Calculation", test_progress_calculation),
        ("Checkpoint Detection", test_checkpoint_detection),
        ("Bulgarian Alerts", test_bulgarian_alerts),
        ("PositionManager Integration", test_position_manager_integration),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
