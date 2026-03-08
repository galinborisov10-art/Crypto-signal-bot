"""
Unit Tests for Entry Zone Selection
Tests the select_entry_zone_for_scenario() function.

Author: galinborisov10-art
Date: 2026-03-08
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from entry_scenarios import select_entry_zone_for_scenario


def test_continuation_entry_zone_with_ob():
    """Test CONTINUATION scenario entry zone extraction when OB is present"""
    print("=" * 60)
    print("TEST 1: CONTINUATION Entry Zone with OB")
    print("=" * 60)
    
    # Mock scenario data as returned by _score_continuation_scenario
    scenario_data = {
        'scenario': 'CONTINUATION',
        'eligible': True,
        'entry_zone': {
            'center': 49500.0,
            'low': 49450.0,
            'high': 49550.0,
            'source': 'CONTINUATION',
            'quality': 75,
            'distance_pct': 1.0,
            'distance_price': 500.0
        },
        'probability': 0.82,
        'triggers': ['DISPLACEMENT', 'MSS/BOS'],
        'trigger_strength': 'HIGH'
    }
    
    ict_components = {
        'order_blocks': [
            {'type': 'BULLISH', 'zone_low': 49400.0, 'zone_high': 49600.0, 'strength': 80}
        ],
        'displacement': {'detected': True, 'strength': 0.85}
    }
    
    entry_zone = select_entry_zone_for_scenario(
        scenario_name='CONTINUATION',
        scenario_data=scenario_data,
        ict_components=ict_components,
        current_price=50000.0
    )
    
    assert entry_zone is not None, "❌ Expected entry zone"
    assert entry_zone['center'] == 49500.0, f"❌ Expected center 49500.0, got {entry_zone['center']}"
    assert entry_zone['source'] == 'CONTINUATION', f"❌ Expected source CONTINUATION, got {entry_zone['source']}"
    assert 'low' in entry_zone, "❌ Missing low field"
    assert 'high' in entry_zone, "❌ Missing high field"
    assert 'quality' in entry_zone, "❌ Missing quality field"
    
    print(f"✅ Entry zone extracted successfully")
    print(f"   • Center: ${entry_zone['center']:.2f}")
    print(f"   • Range: ${entry_zone['low']:.2f} - ${entry_zone['high']:.2f}")
    print(f"   • Source: {entry_zone['source']}")
    print(f"   • Quality: {entry_zone['quality']}")
    print("✅ TEST 1 PASSED\n")


def test_rollback_entry_zone_with_break_level():
    """Test ROLLBACK scenario entry zone extraction with break level"""
    print("=" * 60)
    print("TEST 2: ROLLBACK Entry Zone with Break Level")
    print("=" * 60)
    
    # Mock scenario data as returned by _score_rollback_scenario
    scenario_data = {
        'scenario': 'ROLLBACK',
        'eligible': True,
        'entry_zone': {
            'center': 49500.0,
            'low': 49450.25,
            'high': 49549.75,
            'source': 'ROLLBACK_BOS',
            'quality': 85,
            'distance_pct': 1.0,
            'distance_price': 500.0
        },
        'probability': 0.88,
        'triggers': ['MSS/BOS', 'LIQUIDITY_SWEEP'],
        'trigger_strength': 'HIGH'
    }
    
    ict_components = {
        'structure_break': {
            'type': 'BOS',
            'break_level': 49500.0,
            'strength': 85,
            'retested': False
        }
    }
    
    entry_zone = select_entry_zone_for_scenario(
        scenario_name='ROLLBACK',
        scenario_data=scenario_data,
        ict_components=ict_components,
        current_price=50000.0
    )
    
    assert entry_zone is not None, "❌ Expected entry zone"
    assert entry_zone['center'] == 49500.0, f"❌ Expected center 49500.0, got {entry_zone['center']}"
    assert 'ROLLBACK' in entry_zone['source'], f"❌ Expected ROLLBACK source, got {entry_zone['source']}"
    assert entry_zone['quality'] == 85, f"❌ Expected quality 85, got {entry_zone['quality']}"
    
    print(f"✅ Entry zone extracted successfully")
    print(f"   • Center: ${entry_zone['center']:.2f}")
    print(f"   • Range: ${entry_zone['low']:.2f} - ${entry_zone['high']:.2f}")
    print(f"   • Source: {entry_zone['source']}")
    print(f"   • Quality: {entry_zone['quality']}")
    print("✅ TEST 2 PASSED\n")


def test_reversal_entry_zone_with_sweep():
    """Test REVERSAL scenario entry zone extraction with sweep"""
    print("=" * 60)
    print("TEST 3: REVERSAL Entry Zone with Sweep")
    print("=" * 60)
    
    # Mock scenario data as returned by _score_reversal_scenario
    scenario_data = {
        'scenario': 'REVERSAL',
        'eligible': True,
        'entry_zone': {
            'center': 49800.0,
            'low': 49750.0,
            'high': 49850.0,
            'source': 'REVERSAL_POI',
            'quality': 80,
            'distance_pct': 0.4,
            'distance_price': 200.0
        },
        'probability': 0.75,
        'triggers': ['LIQUIDITY_SWEEP', 'MSS/BOS', 'DISPLACEMENT'],
        'trigger_strength': 'HIGH'
    }
    
    ict_components = {
        'liquidity_sweeps': [
            {'candles_ago': 2, 'type': 'BSL', 'price': 49700.0}
        ],
        'structure_break': {
            'type': 'CHOCH',
            'break_level': 49800.0,
            'direction': 'BEARISH'
        },
        'displacement': {'detected': True, 'strength': 0.70}
    }
    
    entry_zone = select_entry_zone_for_scenario(
        scenario_name='REVERSAL',
        scenario_data=scenario_data,
        ict_components=ict_components,
        current_price=50000.0
    )
    
    assert entry_zone is not None, "❌ Expected entry zone"
    assert entry_zone['center'] == 49800.0, f"❌ Expected center 49800.0, got {entry_zone['center']}"
    assert 'REVERSAL' in entry_zone['source'], f"❌ Expected REVERSAL source, got {entry_zone['source']}"
    assert entry_zone['quality'] == 80, f"❌ Expected quality 80, got {entry_zone['quality']}"
    
    print(f"✅ Entry zone extracted successfully")
    print(f"   • Center: ${entry_zone['center']:.2f}")
    print(f"   • Range: ${entry_zone['low']:.2f} - ${entry_zone['high']:.2f}")
    print(f"   • Source: {entry_zone['source']}")
    print(f"   • Quality: {entry_zone['quality']}")
    print("✅ TEST 3 PASSED\n")


def test_pullback_entry_zone_with_poi():
    """Test PULLBACK scenario entry zone extraction with POI"""
    print("=" * 60)
    print("TEST 4: PULLBACK Entry Zone with POI")
    print("=" * 60)
    
    # Mock scenario data as returned by _score_pullback_scenario
    scenario_data = {
        'scenario': 'PULLBACK',
        'eligible': True,
        'entry_zone': {
            'center': 49100.0,
            'low': 49050.0,
            'high': 49150.0,
            'source': 'PULLBACK_OB',
            'quality': 85,
            'distance_pct': 1.8,
            'distance_price': 900.0
        },
        'probability': 0.80,
        'triggers': ['MSS/BOS'],
        'trigger_strength': 'MEDIUM',
        'poi_type': 'OB'
    }
    
    ict_components = {
        'order_blocks': [
            {
                'type': 'BULLISH',
                'zone_low': 49000.0,
                'zone_high': 49200.0,
                'strength': 85
            }
        ]
    }
    
    entry_zone = select_entry_zone_for_scenario(
        scenario_name='PULLBACK',
        scenario_data=scenario_data,
        ict_components=ict_components,
        current_price=50000.0
    )
    
    assert entry_zone is not None, "❌ Expected entry zone"
    assert entry_zone['center'] == 49100.0, f"❌ Expected center 49100.0, got {entry_zone['center']}"
    assert 'PULLBACK' in entry_zone['source'], f"❌ Expected PULLBACK source, got {entry_zone['source']}"
    assert entry_zone['quality'] == 85, f"❌ Expected quality 85, got {entry_zone['quality']}"
    
    print(f"✅ Entry zone extracted successfully")
    print(f"   • Center: ${entry_zone['center']:.2f}")
    print(f"   • Range: ${entry_zone['low']:.2f} - ${entry_zone['high']:.2f}")
    print(f"   • Source: {entry_zone['source']}")
    print(f"   • Quality: {entry_zone['quality']}")
    print("✅ TEST 4 PASSED\n")


def run_all_tests():
    """Run all entry zone selection tests"""
    print("\n" + "=" * 60)
    print("🧪 ENTRY ZONE SELECTION TESTS")
    print("=" * 60 + "\n")
    
    tests = [
        test_continuation_entry_zone_with_ob,
        test_rollback_entry_zone_with_break_level,
        test_reversal_entry_zone_with_sweep,
        test_pullback_entry_zone_with_poi
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"❌ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ TEST ERROR: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"RESULTS: {passed} passed, {failed} failed")
    print("=" * 60)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
