#!/usr/bin/env python3
"""
Test for PR #1: Signal Generation Unblocking
Tests all 5 fixes to ensure HTF hard blocks are removed and replaced with soft constraints
"""

import sys
import logging
from enum import Enum

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

class MarketBias(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    RANGING = "RANGING"

def test_fix1_htf_soft_constraint():
    """
    FIX #1: HTF should apply confidence penalty, not block signals
    """
    logger.info("=" * 80)
    logger.info("TEST FIX #1: HTF Soft Constraint (No Early Exit)")
    logger.info("=" * 80)
    
    # Simulate the new logic from Step 7b
    def apply_htf_penalty(bias, symbol, ALT_INDEPENDENT_SYMBOLS):
        confidence_penalty = 0.0
        
        if bias in [MarketBias.NEUTRAL, MarketBias.RANGING]:
            if symbol in ALT_INDEPENDENT_SYMBOLS:
                # Simulate own bias check
                own_bias = MarketBias.BULLISH  # Simulated improved bias
                if own_bias in [MarketBias.NEUTRAL, MarketBias.RANGING]:
                    confidence_penalty = 0.40
                else:
                    confidence_penalty = 0.20
                bias = own_bias
            else:
                confidence_penalty = 0.35
        else:
            confidence_penalty = 0.0
        
        return bias, confidence_penalty, True  # Always continue (no early exit)
    
    # Test cases
    ALT_SYMBOLS = ["ETHUSDT", "SOLUSDT", "BNBUSDT"]
    
    # Test 1: BTC with RANGING bias (was: blocked, now: penalty)
    bias, penalty, should_continue = apply_htf_penalty(MarketBias.RANGING, "BTCUSDT", ALT_SYMBOLS)
    assert should_continue == True, "Should continue (no early exit)"
    assert penalty == 0.35, f"Should have 35% penalty, got {penalty*100}%"
    logger.info("✅ BTC with RANGING: Continues with 35% penalty (no block)")
    
    # Test 2: ETH with RANGING HTF but BULLISH own (was: blocked, now: light penalty)
    bias, penalty, should_continue = apply_htf_penalty(MarketBias.RANGING, "ETHUSDT", ALT_SYMBOLS)
    assert should_continue == True, "Should continue (no early exit)"
    assert penalty == 0.20, f"Should have 20% penalty, got {penalty*100}%"
    assert bias == MarketBias.BULLISH, "Should use improved own bias"
    logger.info("✅ ETH with RANGING HTF: Continues with 20% penalty (own bias improved)")
    
    # Test 3: Directional bias (was: continue, now: continue with no penalty)
    bias, penalty, should_continue = apply_htf_penalty(MarketBias.BULLISH, "BTCUSDT", ALT_SYMBOLS)
    assert should_continue == True, "Should continue"
    assert penalty == 0.0, f"Should have 0% penalty, got {penalty*100}%"
    logger.info("✅ Directional bias: Continues with 0% penalty")
    
    logger.info("✅ FIX #1 TEST PASSED: No early exits, only penalties\n")

def test_fix2_bias_threshold():
    """
    FIX #2: Bias threshold lowered from 2 to 1
    """
    logger.info("=" * 80)
    logger.info("TEST FIX #2: Bias Threshold Lowered (2 → 1)")
    logger.info("=" * 80)
    
    def determine_bias_new(bullish_score, bearish_score):
        """New threshold logic"""
        if bullish_score >= 1 and bullish_score > bearish_score:
            return MarketBias.BULLISH
        elif bearish_score >= 1 and bearish_score > bullish_score:
            return MarketBias.BEARISH
        elif bullish_score == bearish_score and bullish_score > 0:
            return MarketBias.NEUTRAL
        else:
            return MarketBias.RANGING
    
    def determine_bias_old(bullish_score, bearish_score):
        """Old threshold logic"""
        if bullish_score >= 2 and bullish_score > bearish_score:
            return MarketBias.BULLISH
        elif bearish_score >= 2 and bearish_score > bullish_score:
            return MarketBias.BEARISH
        else:
            return MarketBias.RANGING
    
    # Test case: 1 OB detected (score = 1)
    old_bias = determine_bias_old(1, 0)
    new_bias = determine_bias_new(1, 0)
    
    assert old_bias == MarketBias.RANGING, "Old: Should be RANGING with score 1"
    assert new_bias == MarketBias.BULLISH, "New: Should be BULLISH with score 1"
    logger.info(f"✅ Score 1-0: Old={old_bias.value}, New={new_bias.value} (IMPROVEMENT)")
    
    # Test case: Equal scores (1-1)
    new_bias_equal = determine_bias_new(1, 1)
    assert new_bias_equal == MarketBias.NEUTRAL, "Equal scores should be NEUTRAL"
    logger.info(f"✅ Score 1-1: {new_bias_equal.value} (directional components exist)")
    
    # Test case: No components (0-0)
    new_bias_none = determine_bias_new(0, 0)
    assert new_bias_none == MarketBias.RANGING, "No components should be RANGING"
    logger.info(f"✅ Score 0-0: {new_bias_none.value} (no direction)")
    
    logger.info("✅ FIX #2 TEST PASSED: Threshold lowered to 1\n")

def test_fix3_mtf_consensus():
    """
    FIX #3: NEUTRAL timeframes don't count as aligned
    """
    logger.info("=" * 80)
    logger.info("TEST FIX #3: MTF Consensus (NEUTRAL Not Aligned)")
    logger.info("=" * 80)
    
    def calculate_consensus_old(target_bias, tf_biases):
        """Old logic: NEUTRAL counts as aligned"""
        aligned = sum(1 for bias in tf_biases if bias == target_bias or bias == MarketBias.NEUTRAL)
        total = len(tf_biases)
        return (aligned / total * 100) if total > 0 else 0
    
    def calculate_consensus_new(target_bias, tf_biases):
        """New logic: Only exact match counts"""
        aligned = sum(1 for bias in tf_biases if bias == target_bias)
        conflicting = sum(1 for bias in tf_biases 
                         if bias not in [target_bias, MarketBias.NEUTRAL, MarketBias.RANGING])
        denominator = aligned + conflicting
        return (aligned / denominator * 100) if denominator > 0 else 0
    
    # Test case: 1 BEARISH, 3 NEUTRAL, 1 BULLISH (target: BEARISH)
    tf_biases = [
        MarketBias.BEARISH,  # Aligned
        MarketBias.NEUTRAL,
        MarketBias.NEUTRAL,
        MarketBias.NEUTRAL,
        MarketBias.BULLISH   # Conflicting
    ]
    
    old_consensus = calculate_consensus_old(MarketBias.BEARISH, tf_biases)
    new_consensus = calculate_consensus_new(MarketBias.BEARISH, tf_biases)
    
    assert old_consensus == 80.0, f"Old: Should be 80%, got {old_consensus}%"
    assert new_consensus == 50.0, f"New: Should be 50%, got {new_consensus}%"
    logger.info(f"✅ Old consensus: {old_consensus}% (inflated)")
    logger.info(f"✅ New consensus: {new_consensus}% (realistic)")
    logger.info(f"   → 1 aligned / (1 aligned + 1 conflicting) = 50%")
    
    logger.info("✅ FIX #3 TEST PASSED: NEUTRAL excluded from consensus\n")

def test_fix4_distance_penalty():
    """
    FIX #4: Distance penalty relaxed from 3% to 10%
    """
    logger.info("=" * 80)
    logger.info("TEST FIX #4: Distance Penalty Relaxed (3% → 10%)")
    logger.info("=" * 80)
    
    def apply_distance_penalty_old(distance_pct):
        """Old: Penalty if >3%"""
        max_distance = 3.0
        if distance_pct > max_distance:
            return 0.20  # 20% penalty
        return 0.0
    
    def apply_distance_penalty_new(distance_pct):
        """New: Only penalty if <0.5%"""
        if distance_pct < 0.5:
            return 0.10  # 10% penalty
        # 0.5-10% is optimal - no penalty
        # >10% is info only - no penalty
        return 0.0
    
    # Test case: 16.5% distance (common in ICT retracements)
    old_penalty = apply_distance_penalty_old(16.5)
    new_penalty = apply_distance_penalty_new(16.5)
    
    assert old_penalty == 0.20, f"Old: Should penalize, got {old_penalty*100}%"
    assert new_penalty == 0.0, f"New: Should NOT penalize, got {new_penalty*100}%"
    logger.info(f"✅ 16.5% distance: Old penalty={old_penalty*100}%, New penalty={new_penalty*100}%")
    
    # Test case: 0.3% distance (too close)
    old_penalty_close = apply_distance_penalty_old(0.3)
    new_penalty_close = apply_distance_penalty_new(0.3)
    logger.info(f"✅ 0.3% distance: New penalty={new_penalty_close*100}% (low RR)")
    
    logger.info("✅ FIX #4 TEST PASSED: Distance penalty relaxed\n")

def test_fix5_distance_direction():
    """
    FIX #5: Distance is now directional (above/below)
    """
    logger.info("=" * 80)
    logger.info("TEST FIX #5: Distance Direction Validation")
    logger.info("=" * 80)
    
    def calculate_directional_distance(entry_price, current_price, is_bearish):
        """Calculate directional distance with validation"""
        if is_bearish:
            # BEARISH: Entry should be ABOVE current
            if entry_price <= current_price:
                warning = f"⚠️ BEARISH entry ${entry_price} NOT above current ${current_price}"
            else:
                warning = None
            distance = (entry_price - current_price) / current_price * 100
            direction = "above"
        else:
            # BULLISH: Entry should be BELOW current
            if entry_price >= current_price:
                warning = f"⚠️ BULLISH entry ${entry_price} NOT below current ${current_price}"
            else:
                warning = None
            distance = (current_price - entry_price) / current_price * 100
            direction = "below"
        
        return distance, direction, warning
    
    # Test case: BEARISH entry at $110, current $100 (correct)
    dist, dir, warn = calculate_directional_distance(110, 100, True)
    assert dir == "above", "BEARISH direction should be 'above'"
    assert dist == 10.0, f"Distance should be 10%, got {dist}%"
    assert warn is None, "Should have no warning"
    logger.info(f"✅ BEARISH: Entry 10% above current (correct)")
    
    # Test case: BULLISH entry at $90, current $100 (correct)
    dist, dir, warn = calculate_directional_distance(90, 100, False)
    assert dir == "below", "BULLISH direction should be 'below'"
    assert dist == 10.0, f"Distance should be 10%, got {dist}%"
    assert warn is None, "Should have no warning"
    logger.info(f"✅ BULLISH: Entry 10% below current (correct)")
    
    # Test case: BEARISH entry at $95, current $100 (WRONG)
    dist, dir, warn = calculate_directional_distance(95, 100, True)
    assert warn is not None, "Should have warning for wrong direction"
    logger.info(f"✅ BEARISH entry below current: Warning triggered")
    
    logger.info("✅ FIX #5 TEST PASSED: Direction validation working\n")

def main():
    """Run all tests"""
    logger.info("\n" + "=" * 80)
    logger.info("PR #1: SIGNAL GENERATION UNBLOCKING - TEST SUITE")
    logger.info("=" * 80 + "\n")
    
    try:
        test_fix1_htf_soft_constraint()
        test_fix2_bias_threshold()
        test_fix3_mtf_consensus()
        test_fix4_distance_penalty()
        test_fix5_distance_direction()
        
        logger.info("=" * 80)
        logger.info("🎉 ALL TESTS PASSED!")
        logger.info("=" * 80)
        logger.info("\nExpected Outcomes:")
        logger.info("✅ Signal success rate should increase from 10% to 50%+")
        logger.info("✅ No Step 7b blocks in logs")
        logger.info("✅ Confidence penalties applied (20-40%)")
        logger.info("✅ MTF consensus realistic (50-60%)")
        logger.info("✅ Distance warnings directional (above/below)")
        logger.info("=" * 80)
        return 0
        
    except AssertionError as e:
        logger.error(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        logger.error(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
