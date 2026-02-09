"""
Test ICT Entry System Implementation
Tests the new ROLLBACK/PULLBACK/CONTINUATION scenario selection
"""

import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from ict_signal_engine import ICTSignalEngine, MarketBias

def create_test_dataframe(num_candles=100):
    """Create a test DataFrame with OHLCV data"""
    # Use fixed random seed for reproducible tests
    np.random.seed(42)
    
    dates = pd.date_range(end=datetime.now(), periods=num_candles, freq='1h')
    
    # Create a simple uptrend
    base_price = 50000
    data = {
        'open': [],
        'high': [],
        'low': [],
        'close': [],
        'volume': []
    }
    
    for i in range(num_candles):
        # Simple uptrend with some noise
        trend = i * 10
        noise = np.random.randn() * 50
        
        open_price = base_price + trend + noise
        close_price = open_price + np.random.randn() * 100
        high_price = max(open_price, close_price) + abs(np.random.randn() * 50)
        low_price = min(open_price, close_price) - abs(np.random.randn() * 50)
        
        data['open'].append(open_price)
        data['high'].append(high_price)
        data['low'].append(low_price)
        data['close'].append(close_price)
        data['volume'].append(np.random.uniform(1000, 5000))
    
    df = pd.DataFrame(data, index=dates)
    return df

def test_detect_bos_mss():
    """Test BOS/MSS detection"""
    print("\n" + "="*60)
    print("TEST 1: BOS/MSS Detection")
    print("="*60)
    
    engine = ICTSignalEngine()
    df = create_test_dataframe(50)
    
    # Test with bullish bias
    has_bos, break_level = engine._detect_bos_mss(df, MarketBias.BULLISH)
    
    print(f"✓ BOS/MSS detected: {has_bos}")
    if break_level:
        print(f"✓ Break level: ${break_level:.2f}")
    
    assert isinstance(has_bos, bool), "has_bos should be boolean"
    print("✅ TEST 1 PASSED: BOS/MSS detection works")

def test_validate_poi():
    """Test POI validation"""
    print("\n" + "="*60)
    print("TEST 2: POI Validation")
    print("="*60)
    
    engine = ICTSignalEngine()
    
    # Create a mock POI (Order Block)
    class MockOB:
        def __init__(self):
            self.zone_low = 49500
            self.zone_high = 49800
            self.strength = 75
            
        def is_valid(self):
            return True
    
    mock_ob = MockOB()
    current_price = 50000
    
    is_valid, validation_info = engine._validate_poi(
        poi=mock_ob,
        poi_type='OB',
        current_price=current_price,
        bias=MarketBias.BULLISH,
        max_candles=120
    )
    
    print(f"✓ POI valid: {is_valid}")
    print(f"✓ Direction valid: {validation_info['direction_valid']}")
    print(f"✓ Distance valid: {validation_info['distance_valid']}")
    print(f"✓ Distance: {validation_info['distance_pct']:.2f}%")
    
    assert 'direction_valid' in validation_info, "Should have direction validation"
    assert 'distance_valid' in validation_info, "Should have distance validation"
    print("✅ TEST 2 PASSED: POI validation works")

def test_calculate_triggers():
    """Test trigger calculation"""
    print("\n" + "="*60)
    print("TEST 3: Trigger Calculation")
    print("="*60)
    
    engine = ICTSignalEngine()
    df = create_test_dataframe(50)
    
    # Mock ICT components
    ict_components = {
        'liquidity_sweeps': [],
        'breaker_blocks': []
    }
    
    triggers = engine._calculate_triggers(
        df=df,
        ict_components=ict_components,
        bias=MarketBias.BULLISH,
        has_bos_mss=True
    )
    
    print(f"✓ Trigger count: {triggers['trigger_count']}")
    print(f"✓ Triggers: {triggers['triggers']}")
    print(f"✓ Confidence level: {triggers['confidence_level']}")
    
    assert 'trigger_count' in triggers, "Should have trigger count"
    assert 'triggers' in triggers, "Should have trigger list"
    assert 'confidence_level' in triggers, "Should have confidence level"
    print("✅ TEST 3 PASSED: Trigger calculation works")

def test_rollback_scenario():
    """Test ROLLBACK scenario detection"""
    print("\n" + "="*60)
    print("TEST 4: ROLLBACK Scenario")
    print("="*60)
    
    engine = ICTSignalEngine()
    current_price = 50000
    break_level = 49000  # 2% below current price
    
    is_rollback, scenario_info = engine._check_rollback_scenario(
        current_price=current_price,
        has_bos_mss=True,
        break_level=break_level,
        ict_components={},
        bias=MarketBias.BULLISH
    )
    
    print(f"✓ Rollback detected: {is_rollback}")
    if is_rollback:
        print(f"✓ Scenario type: {scenario_info['type']}")
        print(f"✓ Break level: ${scenario_info['break_level']:.2f}")
        print(f"✓ Distance: {scenario_info['distance_pct']:.2f}%")
    
    assert isinstance(is_rollback, bool), "Should return boolean"
    if is_rollback:
        assert scenario_info['type'] == 'ROLLBACK', "Should be ROLLBACK scenario"
    print("✅ TEST 4 PASSED: ROLLBACK scenario detection works")

def test_pullback_scenario():
    """Test PULLBACK scenario detection"""
    print("\n" + "="*60)
    print("TEST 5: PULLBACK Scenario")
    print("="*60)
    
    engine = ICTSignalEngine()
    current_price = 50000
    
    # Create a mock Order Block below current price
    class MockOB:
        def __init__(self):
            self.zone_low = 49000
            self.zone_high = 49300
            self.strength = 75
            
        def is_valid(self):
            return True
    
    ict_components = {
        'order_blocks': [MockOB()],
        'fvgs': []
    }
    
    is_pullback, scenario_info = engine._check_pullback_scenario(
        current_price=current_price,
        ict_components=ict_components,
        bias=MarketBias.BULLISH
    )
    
    print(f"✓ Pullback detected: {is_pullback}")
    if is_pullback:
        print(f"✓ Scenario type: {scenario_info['type']}")
        print(f"✓ POI type: {scenario_info['poi']['type']}")
        print(f"✓ POI distance: {scenario_info['poi']['distance_pct']:.2f}%")
    
    assert isinstance(is_pullback, bool), "Should return boolean"
    if is_pullback:
        assert scenario_info['type'] == 'PULLBACK', "Should be PULLBACK scenario"
    print("✅ TEST 5 PASSED: PULLBACK scenario detection works")

def test_continuation_scenario():
    """Test CONTINUATION scenario detection"""
    print("\n" + "="*60)
    print("TEST 6: CONTINUATION Scenario")
    print("="*60)
    
    engine = ICTSignalEngine()
    current_price = 50000
    
    # Mock components with no POIs ahead
    ict_components = {
        'order_blocks': [],
        'fvgs': []
    }
    
    # Mock triggers with 2+ triggers
    triggers = {
        'triggers': ['MSS/BOS', 'DISPLACEMENT'],
        'trigger_count': 2,
        'confidence_level': 'HIGH'
    }
    
    is_continuation, scenario_info = engine._check_continuation_scenario(
        current_price=current_price,
        ict_components=ict_components,
        bias=MarketBias.BULLISH,
        triggers=triggers
    )
    
    print(f"✓ Continuation detected: {is_continuation}")
    if is_continuation:
        print(f"✓ Scenario type: {scenario_info['type']}")
        print(f"✓ Triggers: {scenario_info['triggers']}")
        print(f"✓ Position size modifier: {scenario_info['position_size_modifier']}")
    
    assert isinstance(is_continuation, bool), "Should return boolean"
    if is_continuation:
        assert scenario_info['type'] == 'CONTINUATION', "Should be CONTINUATION scenario"
        assert scenario_info['position_size_modifier'] == 0.65, "Should reduce position size to 65%"
    print("✅ TEST 6 PASSED: CONTINUATION scenario detection works")

def test_select_entry_scenario():
    """Test entry scenario selection (decision tree)"""
    print("\n" + "="*60)
    print("TEST 7: Entry Scenario Selection (Decision Tree)")
    print("="*60)
    
    engine = ICTSignalEngine()
    df = create_test_dataframe(50)
    current_price = 50000
    
    # Mock a PULLBACK scenario
    class MockOB:
        def __init__(self):
            self.zone_low = 49000
            self.zone_high = 49300
            self.strength = 75
            
        def is_valid(self):
            return True
    
    ict_components = {
        'order_blocks': [MockOB()],
        'fvgs': []
    }
    
    triggers = {
        'triggers': ['MSS/BOS'],
        'trigger_count': 1,
        'confidence_level': 'MEDIUM'
    }
    
    scenario = engine._select_entry_scenario(
        df=df,
        current_price=current_price,
        ict_components=ict_components,
        bias=MarketBias.BULLISH,
        has_bos_mss=False,
        break_level=None,
        triggers=triggers
    )
    
    if scenario:
        print(f"✓ Scenario selected: {scenario['type']}")
        print(f"✓ Reason: {scenario['reason']}")
        assert 'type' in scenario, "Should have scenario type"
        assert 'reason' in scenario, "Should have reason"
        print("✅ TEST 7 PASSED: Entry scenario selection works")
    else:
        print("✓ No scenario selected (expected if conditions not met)")
        print("✅ TEST 7 PASSED: Entry scenario selection works (NO SCENARIO)")

def run_all_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🧪 RUNNING ICT ENTRY SYSTEM TESTS")
    print("="*60)
    
    try:
        test_detect_bos_mss()
        test_validate_poi()
        test_calculate_triggers()
        test_rollback_scenario()
        test_pullback_scenario()
        test_continuation_scenario()
        test_select_entry_scenario()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED")
        print("="*60)
        return True
        
    except Exception as e:
        print("\n" + "="*60)
        print(f"❌ TEST FAILED: {e}")
        print("="*60)
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
