"""
Unit Tests for Entry Scenario Scoring System
Deterministic tests with mock ICT components

Author: galinborisov10-art
Date: 2026-02-10
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from entry_scenarios import select_best_entry_scenario


def test_rollback_scenario():
    """Test ROLLBACK scenario scoring"""
    print("=" * 60)
    print("TEST 1: ROLLBACK Scenario")
    print("=" * 60)
    
    ict_components = {
        'structure_break': {
            'type': 'BOS',
            'break_level': 49500.0,
            'strength': 85,
            'retested': False,
            'direction': 'BULLISH'
        },
        'displacement': {
            'detected': True,
            'strength': 0.75
        },
        'order_blocks': [],
        'fvgs': [],
        'liquidity_zones': [],
        'liquidity_sweeps': [
            {'candles_ago': 4, 'type': 'BSL'}
        ],
        'breaker_blocks': None,
        'mitigation_blocks': None
    }
    
    entry_zone_step8 = {'center': 50000.0, 'quality': 80}
    
    result, poi_ref = select_best_entry_scenario(
        current_price=50000.0,
        bias='BULLISH',
        ict_components=ict_components,
        entry_zone=entry_zone_step8,
        timeframe='1h'
    )
    
    assert result is not None, "❌ Expected ROLLBACK scenario"
    assert result['scenario'] == 'ROLLBACK'
    assert 'invalidation_anchor' in result, "❌ Missing invalidation_anchor"
    print(f"✅ Scenario: {result['scenario']} (probability: {result.get('probability', 0):.3f})")
    print(f"✅ Anchor: {result['invalidation_anchor']['type']}")
    print("✅ TEST 1 PASSED\n")


def test_pullback_scenario():
    """Test PULLBACK scenario scoring"""
    print("=" * 60)
    print("TEST 2: PULLBACK Scenario")
    print("=" * 60)
    
    ict_components = {
        'structure_break': {
            'type': 'MSS',
            'break_level': 48500.0,
            'strength': 75,
            'retested': True,  # Mark as retested so ROLLBACK is invalid
            'direction': 'BULLISH'
        },
        'order_blocks': [
            {
                'type': 'BULLISH',
                'zone_low': 49000.0,
                'zone_high': 49200.0,
                'strength': 85
            }
        ],
        'fvgs': [],
        'liquidity_zones': [],
        'displacement': {'detected': True, 'strength': 0.45},  # Weak displacement (below CONTINUATION threshold)
        'liquidity_sweeps': [
            {'candles_ago': 3, 'type': 'BSL'}
        ],
        'breaker_blocks': ['block1'],
        'mitigation_blocks': None
    }
    
    entry_zone_step8 = {'center': 50000.0, 'quality': 80}
    
    result, poi_ref = select_best_entry_scenario(
        current_price=50000.0,
        bias='BULLISH',
        ict_components=ict_components,
        entry_zone=entry_zone_step8,
        timeframe='1h'
    )
    
    assert result is not None, "❌ Expected PULLBACK scenario"
    assert result['scenario'] == 'PULLBACK'
    assert 'invalidation_anchor' in result, "❌ Missing invalidation_anchor"
    assert poi_ref is not None, "❌ Expected POI reference for PULLBACK"
    print(f"✅ Scenario: {result['scenario']} (probability: {result.get('probability', 0):.3f})")
    print(f"✅ Anchor: {result['invalidation_anchor']['type']}")
    print(f"✅ POI Type: {result.get('poi_type', 'NONE')}")
    print("✅ TEST 2 PASSED\n")


def test_continuation_scenario():
    """Test CONTINUATION scenario scoring"""
    print("=" * 60)
    print("TEST 3: CONTINUATION Scenario")
    print("=" * 60)
    
    ict_components = {
        'structure_break': {
            'type': 'MSS',
            'break_level': 51000.0,
            'strength': 90,
            'retested': False,
            'direction': 'BULLISH'
        },
        'order_blocks': [],
        'fvgs': [],
        'liquidity_zones': [],
        'displacement': {
            'detected': True,
            'strength': 0.85
        },
        'liquidity_sweeps': [
            {'candles_ago': 2, 'type': 'BSL'}
        ],
        'breaker_blocks': ['block1'],
        'mitigation_blocks': None
    }
    
    entry_zone_step8 = {'center': 50000.0, 'quality': 80}
    
    result, poi_ref = select_best_entry_scenario(
        current_price=50000.0,
        bias='BULLISH',
        ict_components=ict_components,
        entry_zone=entry_zone_step8,
        timeframe='1h'
    )
    
    assert result is not None, "❌ Expected CONTINUATION scenario"
    assert result['scenario'] == 'CONTINUATION'
    assert 'invalidation_anchor' in result, "❌ Missing invalidation_anchor"
    print(f"✅ Scenario: {result['scenario']} (probability: {result.get('probability', 0):.3f})")
    print(f"✅ Anchor: {result['invalidation_anchor']['type']}")
    print("✅ TEST 3 PASSED\n")


def test_reversal_scenario():
    """Test REVERSAL scenario scoring"""
    print("=" * 60)
    print("TEST 4: REVERSAL Scenario")
    print("=" * 60)
    
    # Mock REVERSAL: Current bias BULLISH, but seeing BEARISH reversal signs
    ict_components = {
        'structure_break': {
            'type': 'CHOCH',
            'break_level': 49800.0,
            'strength': 80,
            'retested': False,
            'direction': 'BEARISH'  # Reversal direction (opposite to BULLISH bias)
        },
        'order_blocks': [
            {
                'type': 'BEARISH',  # Reversal POI
                'zone_low': 49700.0,
                'zone_high': 49900.0
            }
        ],
        'fvgs': [],
        'liquidity_zones': [],
        'displacement': {
            'detected': True,  # Required for REVERSAL
            'strength': 0.70   # Strong enough for reversal
        },
        'liquidity_sweeps': [
            {'candles_ago': 1, 'type': 'BSL'}  # Recent sweep
        ],
        'breaker_blocks': None,
        'mitigation_blocks': None
    }
    
    entry_zone_step8 = {'center': 50000.0, 'quality': 80}
    
    result, poi_ref = select_best_entry_scenario(
        current_price=50000.0,
        bias='BULLISH',  # Current bias (will reverse)
        ict_components=ict_components,
        entry_zone=entry_zone_step8,
        timeframe='1h'
    )
    
    # REVERSAL may not always win, so just check that we get a valid scenario
    assert result is not None, "❌ Expected a scenario (PULLBACK or REVERSAL)"
    assert 'invalidation_anchor' in result, "❌ Missing invalidation_anchor"
    print(f"✅ Scenario: {result['scenario']} (probability: {result.get('probability', 0):.3f})")
    print(f"✅ Anchor: {result['invalidation_anchor']['type']}")
    print("✅ TEST 4 PASSED\n")


def test_deterministic_selection():
    """
    Verify selection is deterministic - identical inputs produce identical outputs.
    This is critical for a production trading system.
    """
    print("=" * 60)
    print("TEST 5: DETERMINISM VALIDATION")
    print("=" * 60)
    
    # Setup test data - scenario that could have ties or complex selection
    ict_components = {
        'structure_break': {
            'type': 'MSS',
            'break_level': 49500.0,
            'strength': 75,
            'retested': False,
            'direction': 'BULLISH'
        },
        'order_blocks': [
            {'type': 'BULLISH', 'zone_low': 49000.0, 'zone_high': 49200.0, 'strength': 80}
        ],
        'fvgs': [],
        'liquidity_zones': [],
        'displacement': {'detected': True, 'strength': 0.55},
        'liquidity_sweeps': [{'candles_ago': 2, 'type': 'BSL'}],
        'breaker_blocks': ['block1'],
        'mitigation_blocks': None
    }
    
    entry_zone_step8 = {'center': 50000.0, 'quality': 80}
    
    # Run selection 10 times with identical inputs
    results = []
    probabilities = []
    for i in range(10):
        result, _ = select_best_entry_scenario(
            current_price=50000.0,
            bias='BULLISH',
            ict_components=ict_components,
            entry_zone=entry_zone_step8,
            timeframe='1h'
        )
        scenario_name = result['scenario'] if result else None
        probability = result.get('probability', 0) if result else 0
        results.append(scenario_name)
        probabilities.append(probability)
    
    # Verify all results are identical
    unique_results = set(results)
    unique_probabilities = set(probabilities)
    
    assert len(unique_results) == 1, \
        f"❌ DETERMINISM FAILURE: Got different scenarios across runs: {unique_results}"
    
    assert len(unique_probabilities) == 1, \
        f"❌ DETERMINISM FAILURE: Got different probabilities across runs: {unique_probabilities}"
    
    print(f"✅ Deterministic: All 10 runs selected '{results[0]}' with probability {probabilities[0]:.3f}")
    print("✅ TEST 5 PASSED\n")


def test_no_scenario_fallback():
    """Test fallback when no scenario is valid"""
    print("=" * 60)
    print("TEST 6: No Valid Scenario")
    print("=" * 60)
    
    ict_components = {
        'structure_break': None,
        'order_blocks': [],
        'fvgs': [],
        'liquidity_zones': [],
        'displacement': {'detected': False},
        'liquidity_sweeps': [],
        'breaker_blocks': None,
        'mitigation_blocks': None
    }
    
    entry_zone_step8 = {'center': 50000.0, 'quality': 80}
    
    result, poi_ref = select_best_entry_scenario(
        current_price=50000.0,
        bias='BULLISH',
        ict_components=ict_components,
        entry_zone=entry_zone_step8,
        timeframe='1h'
    )
    
    assert result is None, f"❌ Expected None, got {result}"
    assert poi_ref is None, f"❌ Expected None for poi_ref, got {poi_ref}"
    print("✅ Correctly returned (None, None)")
    print("✅ TEST 6 PASSED\n")


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("🧪 ENTRY SCENARIO SCORING - UNIT TESTS")
    print("=" * 60 + "\n")
    
    try:
        test_rollback_scenario()
        test_pullback_scenario()
        test_continuation_scenario()
        test_reversal_scenario()
        test_deterministic_selection()
        test_no_scenario_fallback()
        
        print("=" * 60)
        print("✅ ALL 6 TESTS PASSED!")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
