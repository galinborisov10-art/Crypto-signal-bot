#!/usr/bin/env python3
"""
Test: Universal 5% Max Entry Distance Validation

This test validates that entry distance validation uses a universal 5% maximum
for ALL timeframes (15m, 30m, 1h, 2h, 4h, 6h, 8h, 12h, 1d, 3d, 1w).

Entry distance measures SIGNAL FRESHNESS, not trade duration.
A signal with 20% entry distance is equally stale on any timeframe.
"""

import sys
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test_entry_distance_validation():
    """
    Test that entry distance validation applies universal 5% max to all timeframes.
    
    Expected behavior:
    - > 5%: TOO_FAR → REJECT SIGNAL (all timeframes)
    - 3% - 5%: VALID_WAIT (buffer zone - needs pullback)
    - 0.5% - 3%: VALID_NEAR (optimal entry zone)
    - < 0.5%: TOO_LATE (very close, warning only)
    """
    from ict_signal_engine import ICTSignalEngine
    
    logger.info("=" * 80)
    logger.info("TEST: Universal 5% Max Entry Distance Validation")
    logger.info("=" * 80)
    
    # Initialize engine
    engine = ICTSignalEngine()
    
    # Test scenarios for different timeframes
    # Focus on the critical behavior: Universal 5% max rejection
    test_scenarios = [
        # Scenario structure: (timeframe, current_price, entry_price, direction, expected_status, description)
        
        # === TOO_FAR scenarios (> 5%) - should be REJECTED on ALL timeframes ===
        # This is the CRITICAL test - these MUST all be rejected regardless of timeframe
        ('1h', 100.0, 106.0, 'BEARISH', 'TOO_FAR', '6% away - REJECT on 1h'),
        ('4h', 100.0, 107.5, 'BEARISH', 'TOO_FAR', '7.5% away - REJECT on 4h (was 7.5% limit before)'),
        ('1d', 100.0, 110.0, 'BEARISH', 'TOO_FAR', '10% away - REJECT on 1d (was 10% limit before)'),
        ('15m', 100.0, 107.0, 'BEARISH', 'TOO_FAR', '7% away - REJECT on 15m'),
        ('12h', 100.0, 108.0, 'BEARISH', 'TOO_FAR', '8% away - REJECT on 12h'),
        ('3d', 100.0, 109.0, 'BEARISH', 'TOO_FAR', '9% away - REJECT on 3d'),
        ('1w', 100.0, 120.5, 'BEARISH', 'TOO_FAR', '20.5% away - REJECT on 1w (like XRPUSDT 4h)'),
        
        # === VALID_WAIT scenarios - buffer zone (apply buffer adjustment) ===
        ('1h', 100.0, 104.5, 'BEARISH', 'VALID_WAIT', '4.5% away - buffer zone on 1h'),
        ('4h', 100.0, 104.0, 'BEARISH', 'VALID_WAIT', '4% away - buffer zone on 4h'),
        
        # === VALID_NEAR scenarios - optimal zone ===
        ('1h', 100.0, 102.0, 'BEARISH', 'VALID_NEAR', '2% away - optimal on 1h'),
        ('4h', 100.0, 102.5, 'BEARISH', 'VALID_NEAR', '2.5% away - optimal on 4h'),
        ('1d', 100.0, 101.5, 'BEARISH', 'VALID_NEAR', '1.5% away - optimal on 1d'),
        
        # === Test BULLISH direction as well ===
        ('4h', 100.0, 94.0, 'BULLISH', 'TOO_FAR', '6% below - REJECT on 4h (BULLISH)'),
        ('1d', 100.0, 89.0, 'BULLISH', 'TOO_FAR', '11% below - REJECT on 1d (BULLISH, was 10% limit)'),
        ('4h', 100.0, 98.0, 'BULLISH', 'VALID_NEAR', '2% below - optimal on 4h (BULLISH)'),
    ]
    
    passed = 0
    failed = 0
    
    for timeframe, current_price, entry_price, direction, expected_status, description in test_scenarios:
        logger.info("")
        logger.info(f"Test: {description}")
        logger.info(f"  Timeframe: {timeframe}, Direction: {direction}")
        logger.info(f"  Current: ${current_price:.2f}, Entry: ${entry_price:.2f}")
        
        # Calculate distance percentage
        if direction == 'BEARISH':
            distance_pct = (entry_price - current_price) / current_price
        else:  # BULLISH
            distance_pct = (current_price - entry_price) / current_price
        
        logger.info(f"  Distance: {distance_pct*100:.1f}%")
        
        # Create mock zones for testing
        if direction == 'BEARISH':
            # For BEARISH, entry should be ABOVE current price
            fvg_zones = [{
                'low': entry_price - 0.5,
                'high': entry_price + 0.5,
                'center': entry_price,
                'type': 'bearish',
                'quality': 80
            }]
        else:  # BULLISH
            # For BULLISH, entry should be BELOW current price
            fvg_zones = [{
                'low': entry_price - 0.5,
                'high': entry_price + 0.5,
                'center': entry_price,
                'type': 'bullish',
                'quality': 80
            }]
        
        order_blocks = []
        sr_levels = {'support_zones': [], 'resistance_zones': []}
        
        try:
            # Call the function
            entry_zone, status = engine._calculate_ict_compliant_entry_zone(
                current_price=current_price,
                direction=direction,
                fvg_zones=fvg_zones,
                order_blocks=order_blocks,
                sr_levels=sr_levels,
                timeframe=timeframe
            )
            
            # Validate result
            if status == expected_status:
                logger.info(f"  ✅ PASS - Got expected status: {status}")
                passed += 1
                
                # Additional validation for TOO_FAR
                if expected_status == 'TOO_FAR':
                    if entry_zone is None:
                        logger.info(f"     ✅ Correctly returned None for entry_zone")
                    else:
                        logger.warning(f"     ⚠️ Expected None for entry_zone but got: {entry_zone}")
                        
            else:
                logger.error(f"  ❌ FAIL - Expected {expected_status}, got {status}")
                failed += 1
                
        except Exception as e:
            logger.error(f"  ❌ FAIL - Exception: {e}")
            failed += 1
    
    # Summary
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"TEST SUMMARY: {passed} passed, {failed} failed out of {len(test_scenarios)} tests")
    logger.info("=" * 80)
    
    if failed == 0:
        logger.info("✅ ALL TESTS PASSED - Universal 5% max is correctly applied to all timeframes")
        return True
    else:
        logger.error(f"❌ {failed} TESTS FAILED - See above for details")
        return False


def test_no_timeframe_based_limits():
    """
    Verify that the code no longer contains timeframe-based distance limits.
    """
    logger.info("")
    logger.info("=" * 80)
    logger.info("TEST: No Timeframe-Based Limits in Code")
    logger.info("=" * 80)
    
    import inspect
    from ict_signal_engine import ICTSignalEngine
    
    # Get source code of the function
    source = inspect.getsource(ICTSignalEngine._calculate_ict_compliant_entry_zone)
    
    # Check for old timeframe-based limit patterns
    issues = []
    
    if "if timeframe in ['15m', '30m', '1h', '2h']:" in source:
        issues.append("Found old short-term timeframe check")
    
    if "if timeframe in ['4h', '6h', '8h', '12h']:" in source:
        issues.append("Found old medium-term timeframe check")
    
    if "max_distance_pct = 0.075" in source:
        issues.append("Found old 7.5% limit")
    
    if "max_distance_pct = 0.100" in source:
        issues.append("Found old 10% limit")
    
    # Verify new universal limit exists
    if "max_distance_pct = 0.050" not in source:
        issues.append("Missing universal 5% limit")
    
    if "# 5% UNIVERSAL MAX" not in source and "5% UNIVERSAL" not in source:
        issues.append("Missing comment about universal max")
    
    if issues:
        logger.error("❌ FAIL - Found timeframe-based limit remnants:")
        for issue in issues:
            logger.error(f"  - {issue}")
        return False
    else:
        logger.info("✅ PASS - No timeframe-based limits found, universal 5% max confirmed")
        return True


if __name__ == '__main__':
    logger.info("\n")
    logger.info("╔" + "═" * 78 + "╗")
    logger.info("║" + " " * 15 + "ENTRY DISTANCE VALIDATION TEST SUITE" + " " * 27 + "║")
    logger.info("║" + " " * 21 + "Universal 5% Max for All Timeframes" + " " * 22 + "║")
    logger.info("╚" + "═" * 78 + "╝")
    logger.info("")
    
    test1_passed = test_entry_distance_validation()
    test2_passed = test_no_timeframe_based_limits()
    
    logger.info("")
    logger.info("=" * 80)
    if test1_passed and test2_passed:
        logger.info("✅ ALL TEST SUITES PASSED")
        logger.info("=" * 80)
        sys.exit(0)
    else:
        logger.error("❌ SOME TESTS FAILED")
        logger.info("=" * 80)
        sys.exit(1)
