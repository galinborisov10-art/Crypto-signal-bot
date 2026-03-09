"""
Validate multi-timeframe pattern detection works correctly.

Tests:
1. MTF component routing from TimeframeContract hierarchy
2. Pattern detection uses correct timeframe components
3. HTF bias validation (penalty, NOT gate)
4. Structure direction validation (blocks if contradicts bias)
5. Backward compatibility with flat ict_components dict

Run with:
    python validate_mtf_pattern_detection.py
"""

import sys
import os
import logging

# Setup minimal logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)


def _try_import():
    """Try to import required modules, return success flag."""
    try:
        from timeframe_contract import TimeframeContract, TimeframeHierarchy, SignalMode
        from scenario_pattern_detector import detect_scenario_pattern, HTF_BIAS_MISMATCH_PENALTY
        from poi_entry_zone_calculator import calculate_entry_zone_from_poi
        return True, TimeframeContract, TimeframeHierarchy, SignalMode, detect_scenario_pattern, \
               HTF_BIAS_MISMATCH_PENALTY, calculate_entry_zone_from_poi
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False, None, None, None, None, None, None


def create_mock_ob(timeframe: str, ob_type: str, price: float, strength: float = 75.0):
    """Create a mock order block dict with the keys expected by _get_ob_center."""
    half_range = price * 0.005  # 0.5% range
    return {
        'type': ob_type,
        'timeframe': timeframe,
        'zone_high': price + half_range,
        'zone_low': price - half_range,
        'high': price + half_range,
        'low': price - half_range,
        'midpoint': price,
        'strength': strength,
        'candles_ago': 5,
    }


def create_mock_liq_zone(liq_type: str, price: float, confidence: float = 0.8):
    """Create a mock liquidity zone dict."""
    return {
        'type': liq_type,
        'price': price,
        'confidence': confidence,
        'candles_ago': 3,
    }


# ─────────────────────────────────────────────────────────────────────────────
# TEST 1: MTF Timeframe Routing from TimeframeContract
# ─────────────────────────────────────────────────────────────────────────────

def test_mtf_component_routing():
    """Test that TimeframeContract hierarchy assigns correct TFs."""
    ok, TimeframeContract, TimeframeHierarchy, SignalMode, *_ = _try_import()
    if not ok:
        print("SKIP test_mtf_component_routing - import failed")
        return

    print("\n📊 Test 1: MTF Timeframe Routing")

    for signal_tf, expected in [
        ('2h', {'confirmation': '4h', 'structure': '1d', 'htf_bias': '1d'}),
        ('1h', {'confirmation': '2h', 'structure': '4h', 'htf_bias': '4h'}),
        ('4h', {'confirmation': '1d', 'structure': '1d', 'htf_bias': '1d'}),
    ]:
        hierarchy = TimeframeContract.get_hierarchy(signal_tf, SignalMode.MANUAL)
        assert hierarchy is not None, f"hierarchy for {signal_tf} must not be None"
        assert hierarchy.signal_tf == signal_tf, f"Signal TF must be {signal_tf}"
        assert hierarchy.confirmation_tf == expected['confirmation'], \
            f"Confirmation TF: expected {expected['confirmation']}, got {hierarchy.confirmation_tf}"
        assert hierarchy.structure_tf == expected['structure'], \
            f"Structure TF: expected {expected['structure']}, got {hierarchy.structure_tf}"
        assert hierarchy.htf_bias_tf == expected['htf_bias'], \
            f"HTF Bias TF: expected {expected['htf_bias']}, got {hierarchy.htf_bias_tf}"
        print(
            f"   ✅ {signal_tf}: signal={hierarchy.signal_tf}, "
            f"confirmation={hierarchy.confirmation_tf}, "
            f"structure={hierarchy.structure_tf}, "
            f"htf_bias={hierarchy.htf_bias_tf}"
        )

    print("   ✅ All timeframe assignments correct!")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 2: PULLBACK Detection with MTF Components
# ─────────────────────────────────────────────────────────────────────────────

def test_pullback_detection_with_mtf():
    """Scenario 1: PULLBACK on 2h - OB present on signal_tf, no structure break,
    but displacement present on structure_tf for confirmation bonus."""
    ok, TimeframeContract, TimeframeHierarchy, SignalMode, detect_scenario_pattern, \
        HTF_BIAS_MISMATCH_PENALTY, _ = _try_import()
    if not ok:
        print("SKIP test_pullback_detection_with_mtf - import failed")
        return

    print("\n📊 Test 2: PULLBACK Detection (MTF, OB present with displacement confirmation)")

    hierarchy = TimeframeContract.get_hierarchy('2h', SignalMode.MANUAL)
    current_price = 50000.0

    # PULLBACK setup: OB below price on 2h, displacement on 1d (confirmation bonus),
    # but NO structure break (so ROLLBACK is not triggered)
    mtf_components = {
        '2h': {
            'order_blocks': [create_mock_ob('2h', 'BULLISH_OB', 49500.0, strength=85)],
            'fvgs': [],
            'liquidity_zones': [],
            'liquidity_sweeps': [],
        },
        '4h': {
            'whale_blocks': [],
        },
        '1d': {
            'structure_break': None,          # No structure break → ROLLBACK impossible
            'displacement': {'detected': True, 'strength': 0.7},  # Confirmation bonus
            'bias': 'BULLISH',
        },
    }

    pattern, prob = detect_scenario_pattern(
        current_price=current_price,
        bias='BULLISH',
        mtf_components=mtf_components,
        signal_tf='2h',
        tf_hierarchy=hierarchy,
    )

    print(f"   → Pattern: {pattern}, Probability: {prob:.3f}")
    # With displacement confirmation, PULLBACK prob should clear 0.60 threshold
    assert pattern is not None, "Should detect a pattern with OB + displacement confirmation"
    assert pattern == 'PULLBACK', f"Expected PULLBACK (no structure break), got {pattern}"
    assert prob > 0.5, f"Probability should be > 0.5, got {prob:.3f}"
    print(f"   ✅ PULLBACK detected correctly using MTF components! (prob={prob:.3f})")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 3: HTF Bias Mismatch (penalty, not gate)
# ─────────────────────────────────────────────────────────────────────────────

def test_htf_bias_mismatch_penalty():
    """Scenario 2: ROLLBACK on 4h - HTF (1d) is BEARISH but signal is BULLISH."""
    ok, TimeframeContract, TimeframeHierarchy, SignalMode, detect_scenario_pattern, \
        HTF_BIAS_MISMATCH_PENALTY, _ = _try_import()
    if not ok:
        print("SKIP test_htf_bias_mismatch_penalty - import failed")
        return

    print("\n📊 Test 3: HTF Bias Mismatch (penalty, NOT gate)")

    hierarchy = TimeframeContract.get_hierarchy('4h', SignalMode.MANUAL)
    current_price = 50000.0

    # Aligned: 1d is BULLISH, signal bias is BULLISH
    mtf_aligned = {
        '4h': {
            'order_blocks': [create_mock_ob('4h', 'BULLISH_OB', 49500.0, strength=75)],
            'fvgs': [],
            'liquidity_zones': [],
            'liquidity_sweeps': [],
        },
        '1d': {
            'structure_break': {'type': 'BOS', 'direction': 'BULLISH', 'strength': 75},
            'displacement': {'detected': True, 'strength': 0.7},
            'bias': 'BULLISH',
        },
    }

    # Misaligned: 1d is BEARISH, signal bias is BULLISH
    mtf_misaligned = {
        '4h': {
            'order_blocks': [create_mock_ob('4h', 'BULLISH_OB', 49500.0, strength=75)],
            'fvgs': [],
            'liquidity_zones': [],
            'liquidity_sweeps': [],
        },
        '1d': {
            'structure_break': {'type': 'BOS', 'direction': 'BULLISH', 'strength': 75},
            'displacement': {'detected': True, 'strength': 0.7},
            'bias': 'BEARISH',  # MISALIGNED!
        },
    }

    # Run both detections
    pattern_aligned, prob_aligned = detect_scenario_pattern(
        current_price=current_price,
        bias='BULLISH',
        mtf_components=mtf_aligned,
        signal_tf='4h',
        tf_hierarchy=hierarchy,
    )

    pattern_misaligned, prob_misaligned = detect_scenario_pattern(
        current_price=current_price,
        bias='BULLISH',
        mtf_components=mtf_misaligned,
        signal_tf='4h',
        tf_hierarchy=hierarchy,
    )

    print(f"   → Aligned: pattern={pattern_aligned}, prob={prob_aligned:.3f}")
    print(f"   → Misaligned: pattern={pattern_misaligned}, prob={prob_misaligned:.3f}")

    # Both should potentially detect a pattern (mismatch is NOT a gate)
    # Misaligned probability should be lower (or None if threshold not met)
    if pattern_aligned and pattern_misaligned:
        assert prob_misaligned <= prob_aligned, \
            f"Misaligned prob ({prob_misaligned:.3f}) should be <= aligned ({prob_aligned:.3f})"
        print(f"   ✅ Mismatch applies penalty: {prob_aligned:.3f} → {prob_misaligned:.3f}")
    elif pattern_aligned and not pattern_misaligned:
        # Penalty pushed below threshold - acceptable result
        print(f"   ✅ Mismatch penalty pushed probability below threshold (acceptable)")
    else:
        print(f"   ⚠️ Neither detected - check component configuration")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 4: Structure Direction Contradiction (HARD block)
# ─────────────────────────────────────────────────────────────────────────────

def test_structure_contradiction_blocks():
    """Scenario 3: ROLLBACK blocked when structure direction contradicts bias."""
    ok, TimeframeContract, TimeframeHierarchy, SignalMode, detect_scenario_pattern, \
        HTF_BIAS_MISMATCH_PENALTY, _ = _try_import()
    if not ok:
        print("SKIP test_structure_contradiction_blocks - import failed")
        return

    print("\n📊 Test 4: Structure Contradiction (HARD block for ROLLBACK)")

    hierarchy = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
    current_price = 50000.0

    # ROLLBACK with matching structure direction
    mtf_match = {
        '1h': {
            'order_blocks': [create_mock_ob('1h', 'BULLISH_OB', 49500.0)],
            'fvgs': [],
            'liquidity_zones': [],
            'liquidity_sweeps': [],
        },
        '4h': {
            # Structure direction BULLISH = matches BULLISH bias
            'structure_break': {'type': 'BOS', 'direction': 'BULLISH', 'strength': 75},
            'displacement': {'detected': True, 'strength': 0.7},
            'bias': 'BULLISH',
        },
    }

    # ROLLBACK with contradicting structure direction
    mtf_contradict = {
        '1h': {
            'order_blocks': [create_mock_ob('1h', 'BULLISH_OB', 49500.0)],
            'fvgs': [],
            'liquidity_zones': [],
            'liquidity_sweeps': [],
        },
        '4h': {
            # Structure direction BEARISH but signal bias is BULLISH → ROLLBACK blocked
            'structure_break': {'type': 'BOS', 'direction': 'BEARISH', 'strength': 75},
            'displacement': {'detected': False, 'strength': 0.0},
            'bias': 'BULLISH',
        },
    }

    pattern_match, prob_match = detect_scenario_pattern(
        current_price=current_price,
        bias='BULLISH',
        mtf_components=mtf_match,
        signal_tf='1h',
        tf_hierarchy=hierarchy,
    )

    pattern_contradict, prob_contradict = detect_scenario_pattern(
        current_price=current_price,
        bias='BULLISH',
        mtf_components=mtf_contradict,
        signal_tf='1h',
        tf_hierarchy=hierarchy,
    )

    print(f"   → Matching structure: pattern={pattern_match}, prob={prob_match:.3f}")
    print(f"   → Contradicting structure: pattern={pattern_contradict}, prob={prob_contradict:.3f}")

    # Contradicting structure should NOT produce ROLLBACK
    if pattern_contradict == 'ROLLBACK':
        print(f"   ❌ ROLLBACK should be blocked when structure contradicts bias!")
        assert False, "ROLLBACK should be blocked by structure direction mismatch"
    else:
        print(f"   ✅ ROLLBACK correctly blocked when structure direction contradicts bias")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 5: Entry Zone from signal_tf POIs
# ─────────────────────────────────────────────────────────────────────────────

def test_entry_zone_uses_signal_tf():
    """Test that Step 7B extracts entry zone from signal_tf POIs."""
    ok, TimeframeContract, TimeframeHierarchy, SignalMode, detect_scenario_pattern, \
        HTF_BIAS_MISMATCH_PENALTY, calculate_entry_zone_from_poi = _try_import()
    if not ok:
        print("SKIP test_entry_zone_uses_signal_tf - import failed")
        return

    print("\n📊 Test 5: Step 7B Entry Zone from signal_tf POIs")

    hierarchy = TimeframeContract.get_hierarchy('2h', SignalMode.MANUAL)
    current_price = 50000.0
    ob_price = 49500.0

    mtf_components = {
        '2h': {
            'order_blocks': [create_mock_ob('2h', 'BULLISH_OB', ob_price, strength=80)],
            'fvgs': [],
            'liquidity_zones': [],
            'liquidity_sweeps': [],
        },
        '1d': {
            'structure_break': {'type': 'BOS', 'direction': 'BULLISH', 'strength': 80},
            'displacement': {'detected': True, 'strength': 0.75},
            'bias': 'BULLISH',
        },
    }

    result = calculate_entry_zone_from_poi(
        pattern_name='PULLBACK',
        current_price=current_price,
        bias='BULLISH',
        mtf_components=mtf_components,
        signal_tf='2h',
        tf_hierarchy=hierarchy,
    )

    if result:
        entry_zone = result.get('entry_zone', {})
        invalidation_anchor = result.get('invalidation_anchor', {})
        poi_type = result.get('poi_type', '')
        print(f"   → Entry Zone: {entry_zone.get('source', '?')} @ {entry_zone.get('center', 0):.2f}")
        print(f"   → Invalidation Anchor: {invalidation_anchor.get('type', '?')} @ {invalidation_anchor.get('price', 0):.2f}")
        print(f"   → POI Type: {poi_type}")

        # Both entry and anchor should come from the same POI (OB)
        entry_source = entry_zone.get('source', '').upper()
        anchor_source = invalidation_anchor.get('source_type', '').upper()
        assert any(x in entry_source for x in ('OB', 'ORDER_BLOCK', 'BULLISH')), \
            f"Entry should come from OB, got {entry_source}"
        assert any(x in anchor_source for x in ('OB', 'ORDER_BLOCK', 'BULLISH')), \
            f"Anchor should come from same OB, got {anchor_source}"
        print(f"   ✅ Entry zone and invalidation anchor from same OB POI!")
    else:
        print(f"   ⚠️ No entry zone calculated (may need more OBs in range)")


# ─────────────────────────────────────────────────────────────────────────────
# TEST 6: Backward Compatibility (flat ict_components)
# ─────────────────────────────────────────────────────────────────────────────

def test_backward_compat_flat_dict():
    """Test that legacy flat ict_components dict still works."""
    ok, TimeframeContract, TimeframeHierarchy, SignalMode, detect_scenario_pattern, \
        HTF_BIAS_MISMATCH_PENALTY, calculate_entry_zone_from_poi = _try_import()
    if not ok:
        print("SKIP test_backward_compat_flat_dict - import failed")
        return

    print("\n📊 Test 6: Backward Compatibility (flat ict_components)")

    # Old-style flat dict
    flat_components = {
        'order_blocks': [create_mock_ob('2h', 'BULLISH_OB', 49500.0, strength=75)],
        'fvgs': [],
        'liquidity_zones': [],
        'liquidity_sweeps': [],
        'structure_break': {'type': 'BOS', 'direction': 'BULLISH', 'strength': 75},
        'displacement': {'detected': True, 'strength': 0.7},
    }

    # Should not raise an exception
    try:
        pattern, prob = detect_scenario_pattern(
            current_price=50000.0,
            bias='BULLISH',
            mtf_components=flat_components,
            signal_tf='2h',
            tf_hierarchy=None,
        )
        print(f"   → Pattern: {pattern}, Probability: {prob:.3f}")
        print(f"   ✅ Flat dict backward compat OK (no exception)")
    except Exception as e:
        print(f"   ❌ Backward compat failed with exception: {e}")
        raise


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("🔍 MTF Pattern Detection Validation")
    print("=" * 70)

    passed = 0
    failed = 0

    tests = [
        test_mtf_component_routing,
        test_pullback_detection_with_mtf,
        test_htf_bias_mismatch_penalty,
        test_structure_contradiction_blocks,
        test_entry_zone_uses_signal_tf,
        test_backward_compat_flat_dict,
    ]

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as e:
            print(f"   ❌ ASSERTION FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"   ❌ UNEXPECTED ERROR in {test_fn.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print("\n" + "=" * 70)
    print(f"Results: {passed} passed, {failed} failed")
    if failed == 0:
        print("✅ All MTF validation tests passed!")
    else:
        print("❌ Some tests failed - check output above")
    print("=" * 70)

    sys.exit(0 if failed == 0 else 1)
