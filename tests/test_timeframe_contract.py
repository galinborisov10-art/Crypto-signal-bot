"""
Tests for Timeframe Contract Validation
Tests the TimeframeContract hierarchy, ComponentTimeframeValidator, and scenario integrity.

Tests cover:
1. Valid components → no errors
2. Invalid components → correct errors reported
3. Wrong timeframe components → timeframe errors reported
4. PULLBACK with SIGNAL_TF POI → valid
5. PULLBACK with HTF_BIAS_TF POI → error (cross-TF contamination)
6. CONTINUATION with CONFIRMATION_TF displacement → valid
7. CONTINUATION with wrong TF displacement → error
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from timeframe_contract import TimeframeContract, SignalMode, TimeframeHierarchy
from component_tf_validator import ComponentTimeframeValidator, CrossTimeframeContaminationDetector


# ─────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────

def make_ob(zone_low, zone_high, timeframe, ob_type='BULLISH'):
    """Build a minimal order-block dict."""
    return {
        'type': ob_type,
        'zone_low': zone_low,
        'zone_high': zone_high,
        'timeframe': timeframe,
    }


def make_fvg(bottom, top, timeframe, is_bullish=True):
    """Build a minimal FVG dict."""
    return {
        'is_bullish': is_bullish,
        'bottom': bottom,
        'top': top,
        'timeframe': timeframe,
    }


def make_liquidity_zone(price_level, timeframe, zone_type='BSL'):
    """Build a minimal liquidity zone dict."""
    return {
        'zone_type': zone_type,
        'price_level': price_level,
        'timeframe': timeframe,
    }


def make_liquidity_sweep(price, timestamp='2025-01-01T00:00:00', sweep_type='BSL'):
    """Build a minimal liquidity sweep dict."""
    return {
        'price': price,
        'timestamp': timestamp,
        'sweep_type': sweep_type,
    }


# ─────────────────────────────────────────────
#  1.  TimeframeContract hierarchy tests
# ─────────────────────────────────────────────

def test_manual_hierarchies():
    """All manual timeframe hierarchies match the contract table."""
    expected = {
        '15m': ('15m', '30m', '1h',  '1h'),
        '30m': ('30m', '1h',  '2h',  '2h'),
        '1h':  ('1h',  '2h',  '4h',  '4h'),
        '2h':  ('2h',  '4h',  '1d',  '1d'),
        '4h':  ('4h',  '1d',  '1d',  '1d'),
        '1d':  ('1d',  '1d',  '1d',  '1d'),
    }
    for tf, (sig, conf, struct, htf) in expected.items():
        h = TimeframeContract.get_hierarchy(tf, SignalMode.MANUAL)
        assert h is not None, f"No hierarchy for MANUAL {tf}"
        assert h.signal_tf       == sig,    f"MANUAL {tf} signal_tf: expected {sig}, got {h.signal_tf}"
        assert h.confirmation_tf == conf,   f"MANUAL {tf} confirmation_tf: expected {conf}, got {h.confirmation_tf}"
        assert h.structure_tf    == struct, f"MANUAL {tf} structure_tf: expected {struct}, got {h.structure_tf}"
        assert h.htf_bias_tf     == htf,    f"MANUAL {tf} htf_bias_tf: expected {htf}, got {h.htf_bias_tf}"
    print("✅ test_manual_hierarchies PASSED")


def test_automatic_hierarchies():
    """All automatic timeframe hierarchies match the contract table."""
    expected = {
        '1h': ('1h', '2h', '4h', '4h'),
        '2h': ('2h', '4h', '1d', '1d'),
        '4h': ('4h', '1d', '1d', '1d'),
        '1d': ('1d', '1d', '1d', '1d'),
    }
    for tf, (sig, conf, struct, htf) in expected.items():
        h = TimeframeContract.get_hierarchy(tf, SignalMode.AUTOMATIC)
        assert h is not None, f"No hierarchy for AUTOMATIC {tf}"
        assert h.signal_tf       == sig,    f"AUTO {tf} signal_tf mismatch"
        assert h.confirmation_tf == conf,   f"AUTO {tf} confirmation_tf mismatch"
        assert h.structure_tf    == struct, f"AUTO {tf} structure_tf mismatch"
        assert h.htf_bias_tf     == htf,    f"AUTO {tf} htf_bias_tf mismatch"
    print("✅ test_automatic_hierarchies PASSED")


def test_unsupported_timeframe_returns_none():
    """Unsupported timeframes return None, not an exception."""
    assert TimeframeContract.get_hierarchy('5m',  SignalMode.MANUAL)     is None
    assert TimeframeContract.get_hierarchy('3m',  SignalMode.MANUAL)     is None
    assert TimeframeContract.get_hierarchy('15m', SignalMode.AUTOMATIC)  is None
    assert TimeframeContract.get_hierarchy('30m', SignalMode.AUTOMATIC)  is None
    print("✅ test_unsupported_timeframe_returns_none PASSED")


def test_htf_bias_equals_structure_tf():
    """htf_bias_tf must always equal structure_tf (contract invariant)."""
    for tf in TimeframeContract.get_supported_manual_timeframes():
        h = TimeframeContract.get_hierarchy(tf, SignalMode.MANUAL)
        assert h.htf_bias_tf == h.structure_tf, (
            f"MANUAL {tf}: htf_bias_tf ({h.htf_bias_tf}) != structure_tf ({h.structure_tf})"
        )
    for tf in TimeframeContract.get_supported_automatic_timeframes():
        h = TimeframeContract.get_hierarchy(tf, SignalMode.AUTOMATIC)
        assert h.htf_bias_tf == h.structure_tf, (
            f"AUTO {tf}: htf_bias_tf ({h.htf_bias_tf}) != structure_tf ({h.structure_tf})"
        )
    print("✅ test_htf_bias_equals_structure_tf PASSED")


def test_signal_tf_matches_input():
    """signal_tf field must equal the timeframe passed to get_hierarchy."""
    for tf in TimeframeContract.get_supported_manual_timeframes():
        h = TimeframeContract.get_hierarchy(tf, SignalMode.MANUAL)
        assert h.signal_tf == tf, f"MANUAL {tf}: signal_tf mismatch ({h.signal_tf})"
    print("✅ test_signal_tf_matches_input PASSED")


def test_all_hierarchy_timeframes_valid():
    """Every TF produced by the contract must itself be a recognised timeframe."""
    valid_tfs = set(TimeframeContract.get_all_supported_timeframes())
    for tf in TimeframeContract.get_supported_manual_timeframes():
        h = TimeframeContract.get_hierarchy(tf, SignalMode.MANUAL)
        for field in ('signal_tf', 'confirmation_tf', 'structure_tf', 'htf_bias_tf'):
            val = getattr(h, field)
            assert val in valid_tfs, f"MANUAL {tf}.{field} = {val!r} not in supported TFs"
    print("✅ test_all_hierarchy_timeframes_valid PASSED")


# ─────────────────────────────────────────────
#  2.  Component Data Validation
# ─────────────────────────────────────────────

def test_valid_order_block():
    """Valid OB should pass validation with no errors."""
    ob = make_ob(49000.0, 49200.0, '1h')
    result = ComponentTimeframeValidator.validate_order_block(ob, '1h', 'BULLISH')
    assert result.is_valid, f"Expected valid OB, errors: {result.errors}"
    print("✅ test_valid_order_block PASSED")


def test_order_block_wrong_timeframe():
    """OB from wrong timeframe must fail with TF mismatch error."""
    ob = make_ob(49000.0, 49200.0, '4h')   # comes from 4h, expected on 1h
    result = ComponentTimeframeValidator.validate_order_block(ob, '1h', 'BULLISH')
    assert not result.is_valid, "Expected invalid OB due to TF mismatch"
    assert any('TF mismatch' in e for e in result.errors), f"Expected TF mismatch error, got: {result.errors}"
    print("✅ test_order_block_wrong_timeframe PASSED")


def test_order_block_zero_values():
    """OB with zero zone values must fail."""
    ob = make_ob(0, 49200.0, '1h')
    result = ComponentTimeframeValidator.validate_order_block(ob, '1h', 'BULLISH')
    assert not result.is_valid, "Expected invalid OB due to zero zone_low"
    print("✅ test_order_block_zero_values PASSED")


def test_order_block_inverted_bounds():
    """OB where high <= low must fail."""
    ob = make_ob(49200.0, 49000.0, '1h')   # inverted: high < low
    result = ComponentTimeframeValidator.validate_order_block(ob, '1h', 'BULLISH')
    assert not result.is_valid, "Expected invalid OB due to inverted bounds"
    print("✅ test_order_block_inverted_bounds PASSED")


def test_valid_fvg():
    """Valid FVG should pass validation."""
    fvg = make_fvg(48900.0, 49100.0, '1h')
    result = ComponentTimeframeValidator.validate_fvg(fvg, '1h', 'BULLISH')
    assert result.is_valid, f"Expected valid FVG, errors: {result.errors}"
    print("✅ test_valid_fvg PASSED")


def test_fvg_wrong_timeframe():
    """FVG from wrong timeframe must fail."""
    fvg = make_fvg(48900.0, 49100.0, '4h')
    result = ComponentTimeframeValidator.validate_fvg(fvg, '1h', 'BULLISH')
    assert not result.is_valid, "Expected invalid FVG due to TF mismatch"
    assert any('TF mismatch' in e for e in result.errors), f"Expected TF mismatch, got: {result.errors}"
    print("✅ test_fvg_wrong_timeframe PASSED")


def test_fvg_zero_values():
    """FVG with zero bottom must fail."""
    fvg = make_fvg(0, 49100.0, '1h')
    result = ComponentTimeframeValidator.validate_fvg(fvg, '1h', 'BULLISH')
    assert not result.is_valid, "Expected invalid FVG due to zero bottom"
    print("✅ test_fvg_zero_values PASSED")


def test_valid_liquidity_zone():
    """Valid liquidity zone should pass validation."""
    zone = make_liquidity_zone(50000.0, '1h', 'BSL')
    result = ComponentTimeframeValidator.validate_liquidity_zone(zone, '1h', 'BULLISH')
    assert result.is_valid, f"Expected valid liquidity zone, errors: {result.errors}"
    print("✅ test_valid_liquidity_zone PASSED")


def test_liquidity_zone_wrong_timeframe():
    """Liquidity zone from wrong timeframe must fail."""
    zone = make_liquidity_zone(50000.0, '4h', 'BSL')
    result = ComponentTimeframeValidator.validate_liquidity_zone(zone, '1h', 'BULLISH')
    assert not result.is_valid, "Expected invalid liquidity zone due to TF mismatch"
    assert any('TF mismatch' in e for e in result.errors), f"Expected TF mismatch, got: {result.errors}"
    print("✅ test_liquidity_zone_wrong_timeframe PASSED")


def test_liquidity_zone_zero_price():
    """Liquidity zone with zero price must fail."""
    zone = make_liquidity_zone(0, '1h', 'BSL')
    result = ComponentTimeframeValidator.validate_liquidity_zone(zone, '1h', 'BULLISH')
    assert not result.is_valid, "Expected invalid liquidity zone due to zero price"
    print("✅ test_liquidity_zone_zero_price PASSED")


def test_valid_liquidity_sweep():
    """Valid liquidity sweep should pass validation."""
    sweep = make_liquidity_sweep(50000.0)
    result = ComponentTimeframeValidator.validate_liquidity_sweep(sweep, '1h', 'BULLISH')
    assert result.is_valid, f"Expected valid sweep, errors: {result.errors}"
    print("✅ test_valid_liquidity_sweep PASSED")


def test_liquidity_sweep_zero_price():
    """Sweep with zero price must fail."""
    sweep = make_liquidity_sweep(0)
    result = ComponentTimeframeValidator.validate_liquidity_sweep(sweep, '1h', 'BULLISH')
    assert not result.is_valid, "Expected invalid sweep due to zero price"
    print("✅ test_liquidity_sweep_zero_price PASSED")


# ─────────────────────────────────────────────
#  3.  Scenario Integrity (cross-TF contamination)
# ─────────────────────────────────────────────

def test_pullback_signal_tf_poi_no_contamination():
    """PULLBACK with SIGNAL_TF Order Block → no contamination."""
    h = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
    components = {
        'order_blocks': [make_ob(49000.0, 49200.0, h.signal_tf)],
        'fvgs': [],
    }
    issues = CrossTimeframeContaminationDetector.check_entry_scoring_contamination(
        components, h.signal_tf, h.structure_tf, h.htf_bias_tf
    )
    assert len(issues) == 0, f"Expected no contamination, got: {issues}"
    print("✅ test_pullback_signal_tf_poi_no_contamination PASSED")


def test_pullback_htf_bias_tf_poi_detected_as_contamination():
    """PULLBACK with HTF_BIAS_TF Order Block → contamination detected."""
    h = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
    # OB comes from htf_bias_tf (4h), not signal_tf (1h)
    components = {
        'order_blocks': [make_ob(49000.0, 49200.0, h.htf_bias_tf)],
        'fvgs': [],
    }
    issues = CrossTimeframeContaminationDetector.check_entry_scoring_contamination(
        components, h.signal_tf, h.structure_tf, h.htf_bias_tf
    )
    assert len(issues) > 0, "Expected contamination to be detected for HTF OB in entry"
    print("✅ test_pullback_htf_bias_tf_poi_detected_as_contamination PASSED")


def test_no_contamination_when_components_empty():
    """Empty component lists produce no contamination issues."""
    h = TimeframeContract.get_hierarchy('4h', SignalMode.MANUAL)
    components = {'order_blocks': [], 'fvgs': []}
    issues = CrossTimeframeContaminationDetector.check_entry_scoring_contamination(
        components, h.signal_tf, h.structure_tf, h.htf_bias_tf
    )
    assert len(issues) == 0, f"Expected no issues for empty components, got: {issues}"
    print("✅ test_no_contamination_when_components_empty PASSED")


def test_fvg_from_wrong_tf_detected_as_contamination():
    """FVG from structure_tf used in entry scoring → contamination."""
    h = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
    components = {
        'order_blocks': [],
        'fvgs': [make_fvg(48900.0, 49100.0, h.structure_tf)],  # 4h FVG in 1h entry
    }
    issues = CrossTimeframeContaminationDetector.check_entry_scoring_contamination(
        components, h.signal_tf, h.structure_tf, h.htf_bias_tf
    )
    assert len(issues) > 0, "Expected contamination for structure_tf FVG in entry"
    print("✅ test_fvg_from_wrong_tf_detected_as_contamination PASSED")


# ─────────────────────────────────────────────
#  4.  validate_component_list helper
# ─────────────────────────────────────────────

def test_validate_component_list_filters_wrong_tf():
    """validate_component_list rejects components with wrong timeframe."""
    obs = [
        make_ob(49000.0, 49200.0, '1h'),   # correct
        make_ob(47000.0, 47500.0, '4h'),   # wrong TF
    ]
    valid, rejected = ComponentTimeframeValidator.validate_component_list(
        obs, 'Order Block', '1h', 'BULLISH'
    )
    assert len(valid) == 1,    f"Expected 1 valid OB, got {len(valid)}"
    assert rejected == 1,      f"Expected 1 rejected OB, got {rejected}"
    print("✅ test_validate_component_list_filters_wrong_tf PASSED")


def test_validate_component_list_all_valid():
    """validate_component_list keeps all components when all valid."""
    obs = [
        make_ob(49000.0, 49200.0, '4h'),
        make_ob(48000.0, 48500.0, '4h'),
    ]
    valid, rejected = ComponentTimeframeValidator.validate_component_list(
        obs, 'Order Block', '4h', 'BEARISH'
    )
    assert len(valid) == 2, f"Expected 2 valid OBs, got {len(valid)}"
    assert rejected == 0,   f"Expected 0 rejected OBs, got {rejected}"
    print("✅ test_validate_component_list_all_valid PASSED")


# ─────────────────────────────────────────────
#  5.  validate_timeframe_contract script
# ─────────────────────────────────────────────

def test_validate_timeframe_contract_script():
    """The validate_timeframe_contract.py script returns exit code 0."""
    import subprocess
    result = subprocess.run(
        ['python3', 'validate_timeframe_contract.py'],
        capture_output=True, text=True
    )
    assert result.returncode == 0, (
        f"validate_timeframe_contract.py exited with {result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    print("✅ test_validate_timeframe_contract_script PASSED")


# ─────────────────────────────────────────────
#  Runner
# ─────────────────────────────────────────────

def run_all_tests():
    tests = [
        # Hierarchy
        test_manual_hierarchies,
        test_automatic_hierarchies,
        test_unsupported_timeframe_returns_none,
        test_htf_bias_equals_structure_tf,
        test_signal_tf_matches_input,
        test_all_hierarchy_timeframes_valid,
        # Component data validation
        test_valid_order_block,
        test_order_block_wrong_timeframe,
        test_order_block_zero_values,
        test_order_block_inverted_bounds,
        test_valid_fvg,
        test_fvg_wrong_timeframe,
        test_fvg_zero_values,
        test_valid_liquidity_zone,
        test_liquidity_zone_wrong_timeframe,
        test_liquidity_zone_zero_price,
        test_valid_liquidity_sweep,
        test_liquidity_sweep_zero_price,
        # Scenario integrity
        test_pullback_signal_tf_poi_no_contamination,
        test_pullback_htf_bias_tf_poi_detected_as_contamination,
        test_no_contamination_when_components_empty,
        test_fvg_from_wrong_tf_detected_as_contamination,
        # Component list helper
        test_validate_component_list_filters_wrong_tf,
        test_validate_component_list_all_valid,
        # Validation script
        test_validate_timeframe_contract_script,
    ]

    passed = 0
    failed = 0

    print("\n" + "=" * 70)
    print("TIMEFRAME CONTRACT TEST SUITE")
    print("=" * 70)

    for test_fn in tests:
        try:
            test_fn()
            passed += 1
        except AssertionError as exc:
            print(f"❌ {test_fn.__name__} FAILED: {exc}")
            failed += 1
        except Exception as exc:
            print(f"❌ {test_fn.__name__} ERROR: {exc}")
            failed += 1

    print("\n" + "=" * 70)
    print(f"RESULTS: {passed} passed, {failed} failed out of {len(tests)} tests")
    print("=" * 70)

    if failed > 0:
        sys.exit(1)
    print("🎉 ALL TESTS PASSED")


if __name__ == "__main__":
    run_all_tests()
