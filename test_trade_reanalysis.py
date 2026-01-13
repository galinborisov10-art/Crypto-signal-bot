"""
Test suite for Trade Re-analysis Engine

Tests:
1. Checkpoint price calculation (BUY and SELL)
2. Recommendation logic (all decision matrix scenarios)
3. Engine initialization
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from trade_reanalysis_engine import (
    TradeReanalysisEngine,
    RecommendationType,
    CheckpointAnalysis
)
from ict_signal_engine import ICTSignal, SignalType, SignalStrength, MarketBias
from datetime import datetime, timezone


def test_checkpoint_calculation():
    """Test 1: Verify checkpoint price calculation for BUY and SELL signals"""
    print("=" * 60)
    print("TEST 1: Checkpoint Price Calculation")
    print("=" * 60)
    
    engine = TradeReanalysisEngine()
    
    # Test BUY signal
    print("\n📈 BUY Signal Test:")
    print("   Entry: $45,000, TP1: $46,500, SL: $44,500")
    
    buy_checkpoints = engine.calculate_checkpoint_prices(
        signal_type="BUY",
        entry_price=45000,
        tp1_price=46500,
        sl_price=44500
    )
    
    expected_buy = {
        "25%": 45375.00,
        "50%": 45750.00,
        "75%": 46125.00,
        "85%": 46275.00
    }
    
    buy_passed = True
    for level, expected_price in expected_buy.items():
        actual_price = buy_checkpoints[level]
        match = abs(actual_price - expected_price) < 0.01
        status = "✅" if match else "❌"
        print(f"   {status} {level}: ${actual_price:.2f} (expected ${expected_price:.2f})")
        if not match:
            buy_passed = False
    
    # Test SELL signal
    print("\n📉 SELL Signal Test:")
    print("   Entry: $50,000, TP1: $48,000, SL: $50,500")
    
    sell_checkpoints = engine.calculate_checkpoint_prices(
        signal_type="SELL",
        entry_price=50000,
        tp1_price=48000,
        sl_price=50500
    )
    
    expected_sell = {
        "25%": 49500.00,
        "50%": 49000.00,
        "75%": 48500.00,
        "85%": 48300.00
    }
    
    sell_passed = True
    for level, expected_price in expected_sell.items():
        actual_price = sell_checkpoints[level]
        match = abs(actual_price - expected_price) < 0.01
        status = "✅" if match else "❌"
        print(f"   {status} {level}: ${actual_price:.2f} (expected ${expected_price:.2f})")
        if not match:
            sell_passed = False
    
    if buy_passed and sell_passed:
        print("\n✅ PASSED: Checkpoint calculation correct for BUY and SELL\n")
        return True
    else:
        print("\n❌ FAILED: Checkpoint calculation errors detected\n")
        return False


def test_recommendation_logic():
    """Test 2: Verify recommendation logic follows decision matrix"""
    print("=" * 60)
    print("TEST 2: Recommendation Logic")
    print("=" * 60)
    
    engine = TradeReanalysisEngine()
    test_results = []
    
    # Create mock original signal
    original_signal = ICTSignal(
        timestamp=datetime.now(timezone.utc),
        symbol="BTCUSDT",
        timeframe="1h",
        signal_type=SignalType.BUY,
        signal_strength=SignalStrength.STRONG,
        entry_price=45000,
        sl_price=44500,
        tp_prices=[46500, 47500, 49000],
        confidence=75.0,
        risk_reward_ratio=3.0,
        bias=MarketBias.BULLISH,
        htf_bias="BULLISH"
    )
    
    # Test Case 1: Minor drop, early checkpoint → HOLD
    analysis1 = CheckpointAnalysis(
        checkpoint_level="25%",
        checkpoint_price=45375,
        current_price=45400,
        distance_to_tp=2.4,
        distance_to_sl=2.0,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=70.0,
        confidence_delta=-5.0,
        htf_bias_changed=False,
        structure_broken=False,
        current_rr_ratio=2.2
    )
    rec1, reason1 = engine._determine_recommendation(analysis1, "25%")
    test1_pass = (rec1 == RecommendationType.HOLD)
    test_results.append(("Minor drop, early checkpoint: HOLD", test1_pass))
    print(f"   {'✅' if test1_pass else '❌'} Minor drop, early checkpoint: {rec1.value}")
    
    # Test Case 2: Improved confidence at 50% → MOVE_SL
    analysis2 = CheckpointAnalysis(
        checkpoint_level="50%",
        checkpoint_price=45750,
        current_price=45800,
        distance_to_tp=1.5,
        distance_to_sl=2.9,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=85.0,
        confidence_delta=+10.0,
        htf_bias_changed=False,
        structure_broken=False,
        current_rr_ratio=1.8
    )
    rec2, reason2 = engine._determine_recommendation(analysis2, "50%")
    test2_pass = (rec2 == RecommendationType.MOVE_SL)
    test_results.append(("Improved confidence at 50%: MOVE_SL", test2_pass))
    print(f"   {'✅' if test2_pass else '❌'} Improved confidence at 50%: {rec2.value}")
    
    # Test Case 3: Moderate drop at 75% → PARTIAL_CLOSE
    analysis3 = CheckpointAnalysis(
        checkpoint_level="75%",
        checkpoint_price=46125,
        current_price=46150,
        distance_to_tp=0.75,
        distance_to_sl=3.7,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=55.0,
        confidence_delta=-20.0,
        htf_bias_changed=False,
        structure_broken=False,
        current_rr_ratio=0.9
    )
    rec3, reason3 = engine._determine_recommendation(analysis3, "75%")
    test3_pass = (rec3 == RecommendationType.PARTIAL_CLOSE)
    test_results.append(("Moderate drop at 75%: PARTIAL_CLOSE", test3_pass))
    print(f"   {'✅' if test3_pass else '❌'} Moderate drop at 75%: {rec3.value}")
    
    # Test Case 4: Large confidence drop → CLOSE_NOW
    analysis4 = CheckpointAnalysis(
        checkpoint_level="50%",
        checkpoint_price=45750,
        current_price=45800,
        distance_to_tp=1.5,
        distance_to_sl=2.9,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=40.0,
        confidence_delta=-35.0,
        htf_bias_changed=False,
        structure_broken=False,
        current_rr_ratio=1.5
    )
    rec4, reason4 = engine._determine_recommendation(analysis4, "50%")
    test4_pass = (rec4 == RecommendationType.CLOSE_NOW)
    test_results.append(("Large confidence drop: CLOSE_NOW", test4_pass))
    print(f"   {'✅' if test4_pass else '❌'} Large confidence drop: {rec4.value}")
    
    # Test Case 5: HTF bias changed → CLOSE_NOW
    analysis5 = CheckpointAnalysis(
        checkpoint_level="50%",
        checkpoint_price=45750,
        current_price=45800,
        distance_to_tp=1.5,
        distance_to_sl=2.9,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=70.0,
        confidence_delta=-5.0,
        htf_bias_changed=True,
        structure_broken=False,
        current_rr_ratio=1.5
    )
    rec5, reason5 = engine._determine_recommendation(analysis5, "50%")
    test5_pass = (rec5 == RecommendationType.CLOSE_NOW)
    test_results.append(("HTF bias changed: CLOSE_NOW", test5_pass))
    print(f"   {'✅' if test5_pass else '❌'} HTF bias changed: {rec5.value}")
    
    # Test Case 6: Structure broken → CLOSE_NOW
    analysis6 = CheckpointAnalysis(
        checkpoint_level="50%",
        checkpoint_price=45750,
        current_price=45800,
        distance_to_tp=1.5,
        distance_to_sl=2.9,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=70.0,
        confidence_delta=-5.0,
        htf_bias_changed=False,
        structure_broken=True,
        current_rr_ratio=1.5
    )
    rec6, reason6 = engine._determine_recommendation(analysis6, "50%")
    test6_pass = (rec6 == RecommendationType.CLOSE_NOW)
    test_results.append(("Structure broken: CLOSE_NOW", test6_pass))
    print(f"   {'✅' if test6_pass else '❌'} Structure broken: {rec6.value}")
    
    # Test Case 7: Low R:R at 85% → PARTIAL_CLOSE
    analysis7 = CheckpointAnalysis(
        checkpoint_level="85%",
        checkpoint_price=46275,
        current_price=46300,
        distance_to_tp=0.43,
        distance_to_sl=4.0,
        original_signal=original_signal,
        original_confidence=75.0,
        current_confidence=72.0,
        confidence_delta=-3.0,
        htf_bias_changed=False,
        structure_broken=False,
        current_rr_ratio=0.3
    )
    rec7, reason7 = engine._determine_recommendation(analysis7, "85%")
    test7_pass = (rec7 == RecommendationType.PARTIAL_CLOSE)
    test_results.append(("Low R:R at 85%: PARTIAL_CLOSE", test7_pass))
    print(f"   {'✅' if test7_pass else '❌'} Low R:R at 85%: {rec7.value}")
    
    # Summary
    passed = sum(1 for _, result in test_results if result)
    total = len(test_results)
    
    if passed == total:
        print(f"\n✅ PASSED: {passed}/{total} test cases\n")
        return True
    else:
        print(f"\n❌ FAILED: {passed}/{total} test cases passed\n")
        return False


def test_engine_initialization():
    """Test 3: Verify engine initializes correctly"""
    print("=" * 60)
    print("TEST 3: Engine Initialization")
    print("=" * 60)
    
    try:
        engine = TradeReanalysisEngine()
        
        # Check attributes
        has_checkpoints = hasattr(engine, 'checkpoint_levels')
        correct_levels = engine.checkpoint_levels == [0.25, 0.50, 0.75, 0.85]
        has_methods = (
            hasattr(engine, 'calculate_checkpoint_prices') and
            hasattr(engine, 'reanalyze_at_checkpoint') and
            hasattr(engine, '_determine_recommendation')
        )
        
        print(f"   {'✅' if has_checkpoints else '❌'} Engine initialized successfully")
        print(f"   {'✅' if correct_levels else '❌'} Checkpoint levels: {engine.checkpoint_levels}")
        print(f"   {'✅' if has_methods else '❌'} All methods present")
        
        if has_checkpoints and correct_levels and has_methods:
            print("\n✅ PASSED: Engine initialization\n")
            return True
        else:
            print("\n❌ FAILED: Engine initialization\n")
            return False
            
    except Exception as e:
        print(f"   ❌ Error: {e}")
        print("\n❌ FAILED: Engine initialization\n")
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 60)
    print("TRADE RE-ANALYSIS ENGINE - TEST SUITE")
    print("=" * 60 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Checkpoint Calculation", test_checkpoint_calculation()))
    results.append(("Recommendation Logic", test_recommendation_logic()))
    results.append(("Engine Initialization", test_engine_initialization()))
    
    # Summary
    print("=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    passed_count = sum(1 for _, passed in results if passed)
    total_count = len(results)
    
    print("\n" + "=" * 60)
    print(f"TOTAL: {passed_count}/{total_count} tests passed")
    
    if passed_count == total_count:
        print("🎉 ALL TESTS PASSED!")
    else:
        print("⚠️ SOME TESTS FAILED")
    
    print("=" * 60 + "\n")
    
    return passed_count == total_count


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
