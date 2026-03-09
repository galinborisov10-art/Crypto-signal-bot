"""
Step 7A: Scenario Pattern Detector

Detects WHAT pattern the market is making WITHOUT computing entry zones.
Returns pattern type + probability score only.

Patterns:
- ROLLBACK: BOS/MSS detected → market retracing to structure break
- PULLBACK: Trend with OB/BSL/SSL → retracement in trend direction
- CONTINUATION: Displacement detected → continuation setup
- REVERSAL: Liquidity sweep (BSL/SSL) → reversal setup

Author: galinborisov10-art
Date: 2026-03-09
"""

import logging
from typing import Dict, List, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from timeframe_contract import TimeframeHierarchy

from entry_scenarios import (
    _detect_triggers_weighted,
    _evaluate_trigger_strength,
    _validate_rollback_behavior,
    _validate_reversal_behavior,
    _check_confirmation_layer,
    _safe_get,
    _get_ob_center,
    get_recency_threshold,
)
from entry_scenario_config import (
    BASE_PROBABILITY,
    PROBABILITY_CONTRIBUTIONS,
    MIN_PROBABILITY_THRESHOLDS,
    ROLLBACK_DISTANCE,
    PULLBACK_DISTANCE,
    CONTINUATION_DISTANCE,
    POI_QUALITY,
    REVERSAL_SETTINGS,
)

logger = logging.getLogger(__name__)

# Scenario priority for deterministic tie-breaking (lower = higher priority)
PATTERN_PRIORITY = {
    'REVERSAL': 1,
    'ROLLBACK': 2,
    'PULLBACK': 3,
    'CONTINUATION': 4,
}


def detect_scenario_pattern(
    current_price: float,
    bias: str,
    ict_components: Dict,
    timeframe: str,
    tf_hierarchy: Optional['TimeframeHierarchy'] = None
) -> Tuple[Optional[str], float]:
    """
    Detect the most probable market pattern WITHOUT computing entry zones.

    Args:
        current_price: Current market price
        bias: Market bias ('BULLISH' or 'BEARISH')
        ict_components: ICT analysis components (order_blocks, fvgs, liquidity_zones, etc.)
        timeframe: Trading timeframe
        tf_hierarchy: Optional timeframe hierarchy for multi-timeframe context

    Returns:
        Tuple[Optional[str], float]: (pattern_name, probability) or (None, 0.0)
    """
    logger.info("=" * 60)
    logger.info("🔍 Step 7A: Scenario Pattern Detection")
    logger.info("=" * 60)

    # Detect triggers (common for all patterns)
    triggers, trigger_score = _detect_triggers_weighted(
        current_price, ict_components, bias, timeframe
    )
    trigger_strength = _evaluate_trigger_strength(trigger_score)
    logger.info(f"   Triggers: {triggers} (score: {trigger_score}, strength: {trigger_strength})")

    # Score all patterns
    pattern_scores: Dict[str, float] = {}

    # --- ROLLBACK ---
    rollback_prob = _score_rollback_pattern(
        current_price=current_price,
        bias=bias,
        ict_components=ict_components,
        triggers=triggers,
        trigger_score=trigger_score,
        timeframe=timeframe,
    )
    if rollback_prob > 0:
        pattern_scores['ROLLBACK'] = rollback_prob
        logger.info(f"   ROLLBACK probability: {rollback_prob:.3f}")
    else:
        logger.info(f"   ROLLBACK: not detected")

    # --- PULLBACK (REQUIRES OB or BSL/SSL) ---
    pullback_prob = _score_pullback_pattern(
        current_price=current_price,
        bias=bias,
        ict_components=ict_components,
        triggers=triggers,
        trigger_score=trigger_score,
    )
    if pullback_prob > 0:
        pattern_scores['PULLBACK'] = pullback_prob
        logger.info(f"   PULLBACK probability: {pullback_prob:.3f}")
    else:
        logger.info(f"   PULLBACK: not detected (missing OB or BSL/SSL)")

    # --- CONTINUATION (REQUIRES OB or BSL/SSL) ---
    continuation_prob = _score_continuation_pattern(
        current_price=current_price,
        bias=bias,
        ict_components=ict_components,
        triggers=triggers,
        trigger_score=trigger_score,
        timeframe=timeframe,
    )
    if continuation_prob > 0:
        pattern_scores['CONTINUATION'] = continuation_prob
        logger.info(f"   CONTINUATION probability: {continuation_prob:.3f}")
    else:
        logger.info(f"   CONTINUATION: not detected (missing OB or BSL/SSL, or no displacement)")

    # --- REVERSAL ---
    reversal_prob = _score_reversal_pattern(
        current_price=current_price,
        bias=bias,
        ict_components=ict_components,
        triggers=triggers,
        trigger_score=trigger_score,
        timeframe=timeframe,
    )
    if reversal_prob > 0:
        pattern_scores['REVERSAL'] = reversal_prob
        logger.info(f"   REVERSAL probability: {reversal_prob:.3f}")
    else:
        logger.info(f"   REVERSAL: not detected")

    if not pattern_scores:
        logger.warning("⚠️ No pattern detected - no valid ICT structure found")
        return None, 0.0

    # Select best pattern with deterministic tie-breaking
    best_pattern = max(
        pattern_scores,
        key=lambda k: (
            pattern_scores[k],
            -PATTERN_PRIORITY.get(k, 999),
        )
    )
    best_prob = pattern_scores[best_pattern]

    # Apply minimum probability threshold
    threshold = MIN_PROBABILITY_THRESHOLDS.get(best_pattern, 0.40)
    if best_prob < threshold:
        logger.warning(
            f"⚠️ Best pattern {best_pattern} probability {best_prob:.3f} "
            f"< threshold {threshold:.3f} → no valid pattern"
        )
        return None, 0.0

    logger.info("=" * 60)
    logger.info(f"🏆 DETECTED PATTERN: {best_pattern} (probability: {best_prob:.3f})")
    logger.info("=" * 60)
    return best_pattern, best_prob


# ============================================================
# PATTERN SCORING FUNCTIONS
# ============================================================

def _score_rollback_pattern(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
    timeframe: str,
) -> float:
    """
    Score ROLLBACK pattern: BOS/MSS with market retracing to structure break.
    Returns probability (0.0 = not valid, >0.0 = valid).
    """
    sb = ict_components.get('structure_break')

    # Requires structure break
    if not sb or not sb.get('type'):
        return 0.0

    # Validate behavioral requirements
    is_eligible, reason = _validate_rollback_behavior(
        structure_break=sb,
        current_price=current_price,
        ict_components=ict_components,
        timeframe=timeframe,
    )
    if not is_eligible:
        logger.debug(f"   ROLLBACK behavior invalid: {reason}")
        return 0.0

    # Check bias alignment with structure direction
    sb_direction = sb.get('direction', '').upper()
    bias_upper = bias.upper()
    if sb_direction and sb_direction != bias_upper:
        logger.debug(f"   ROLLBACK: structure direction {sb_direction} != bias {bias_upper}")
        return 0.0

    # Calculate probability
    structure_strength = sb.get('strength', 50)
    displacement = ict_components.get('displacement', {})
    displacement_strength = displacement.get('strength', 0) if displacement.get('detected') else 0

    # Use break_level if available, else estimate distance from current price
    break_level = sb.get('break_level') or sb.get('price')
    if break_level and break_level > 0:
        distance_pct = abs(break_level - current_price) / current_price * 100
        # Distance check
        if distance_pct < ROLLBACK_DISTANCE['min_pct'] * 100:
            return 0.0
        if distance_pct > ROLLBACK_DISTANCE['max_pct'] * 100:
            return 0.0
    else:
        # No break_level in structure_break - use a default 2% distance for scoring
        distance_pct = 2.0

    from entry_scenarios import _calculate_probability_rollback
    probability = _calculate_probability_rollback(
        structure_strength=structure_strength,
        displacement_strength=displacement_strength,
        triggers=triggers,
        distance_pct=distance_pct,
    )
    return probability


def _score_pullback_pattern(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
) -> float:
    """
    Score PULLBACK pattern: trend retracement to OB or BSL/SSL.
    REQUIRES OB or BSL/SSL (FVG alone is insufficient per ICT principles).
    Returns probability (0.0 = not valid, >0.0 = valid).
    """
    is_bullish = bias.upper() == 'BULLISH'
    is_bearish = bias.upper() == 'BEARISH'

    obs = ict_components.get('order_blocks', [])
    liq_zones = ict_components.get('liquidity_zones', [])

    best_quality = 0.0
    best_distance = None
    found_structural_poi = False  # OB or BSL/SSL (not FVG)

    # Check Order Blocks
    for ob in obs:
        ob_type = str(
            ob.type if hasattr(ob, 'type') else
            (_safe_get(ob, 'type', '') if isinstance(ob, dict) else '')
        ).upper()
        ob_center = _get_ob_center(ob)
        if ob_center <= 0:
            continue

        # Bias-aligned OB on the retracement side
        if is_bullish and 'BULLISH' in ob_type and ob_center < current_price:
            distance_pct = abs(ob_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                quality = float(_safe_get(ob, 'strength', 70))
                if quality >= POI_QUALITY['min_acceptable']:
                    found_structural_poi = True
                    if quality > best_quality:
                        best_quality = quality
                        best_distance = distance_pct

        if is_bearish and 'BEARISH' in ob_type and ob_center > current_price:
            distance_pct = abs(ob_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                quality = float(_safe_get(ob, 'strength', 70))
                if quality >= POI_QUALITY['min_acceptable']:
                    found_structural_poi = True
                    if quality > best_quality:
                        best_quality = quality
                        best_distance = distance_pct

    # Check Liquidity zones (BSL/SSL only - these are structural boundaries)
    for liq in liq_zones:
        liq_type = (
            liq.type if hasattr(liq, 'type') else
            (_safe_get(liq, 'type', '') if isinstance(liq, dict) else '')
        ).upper()
        liq_price = (
            liq.price if hasattr(liq, 'price') else
            (_safe_get(liq, 'price', 0) if isinstance(liq, dict) else 0)
        )
        if liq_price <= 0:
            continue

        # BULLISH pullback to BSL (below price), BEARISH pullback to SSL (above price)
        if is_bullish and 'BSL' in liq_type and liq_price < current_price:
            distance_pct = abs(liq_price - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                quality = float(_safe_get(liq, 'confidence', 0.7)) * 100
                if quality >= POI_QUALITY['min_acceptable']:
                    found_structural_poi = True
                    if quality > best_quality:
                        best_quality = quality
                        best_distance = distance_pct

        if is_bearish and 'SSL' in liq_type and liq_price > current_price:
            distance_pct = abs(liq_price - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                quality = float(_safe_get(liq, 'confidence', 0.7)) * 100
                if quality >= POI_QUALITY['min_acceptable']:
                    found_structural_poi = True
                    if quality > best_quality:
                        best_quality = quality
                        best_distance = distance_pct

    # CRITICAL: PULLBACK requires OB or BSL/SSL (FVG alone insufficient)
    if not found_structural_poi:
        logger.debug("   PULLBACK: no OB or BSL/SSL found (FVG alone insufficient for SL placement)")
        return 0.0

    # Calculate probability
    structure_present = 'MSS/BOS' in triggers
    from entry_scenarios import _calculate_probability_pullback
    probability = _calculate_probability_pullback(
        poi_quality=best_quality,
        triggers=triggers,
        distance_pct=best_distance or 2.0,
        structure_present=structure_present,
    )

    # Confirmation modifier
    sb = ict_components.get('structure_break')
    disp = ict_components.get('displacement', {})
    confirmation_present = _check_confirmation_layer(
        structure_break=sb,
        displacement=disp,
        sweeps=None,
    )
    if confirmation_present:
        probability += 0.08
    else:
        probability -= 0.08
    probability = max(0.0, min(1.0, probability))

    return probability


def _score_continuation_pattern(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
    timeframe: str,
) -> float:
    """
    Score CONTINUATION pattern: momentum continuation after displacement.
    REQUIRES OB or BSL/SSL near the displacement (FVG alone insufficient per ICT).
    Returns probability (0.0 = not valid, >0.0 = valid).
    """
    # Requires displacement trigger
    if 'DISPLACEMENT' not in triggers and 'MSS/BOS' not in triggers:
        return 0.0

    disp = ict_components.get('displacement', {})
    displacement_detected = disp.get('detected', False)
    displacement_strength = disp.get('strength', 0.0)

    if not displacement_detected:
        return 0.0

    is_bullish = bias.upper() == 'BULLISH'
    obs = ict_components.get('order_blocks', [])
    liq_zones = ict_components.get('liquidity_zones', [])

    # CRITICAL: CONTINUATION requires OB or BSL/SSL near the current displacement zone
    found_structural_poi = False
    check_range_pct = CONTINUATION_DISTANCE['poi_check_range_pct'] * 100  # e.g. 3%

    # Check OBs near current price (within displacement zone)
    for ob in obs:
        ob_type = str(
            ob.type if hasattr(ob, 'type') else
            (_safe_get(ob, 'type', '') if isinstance(ob, dict) else '')
        ).upper()
        ob_center = _get_ob_center(ob)
        if ob_center <= 0:
            continue

        # OB should be in the right zone (behind price in trend direction)
        if is_bullish and 'BULLISH' in ob_type:
            distance_pct = abs(ob_center - current_price) / current_price * 100
            if distance_pct <= check_range_pct:
                quality = float(_safe_get(ob, 'strength', 70))
                if quality >= POI_QUALITY['min_acceptable']:
                    found_structural_poi = True
                    break

        if not is_bullish and 'BEARISH' in ob_type:
            distance_pct = abs(ob_center - current_price) / current_price * 100
            if distance_pct <= check_range_pct:
                quality = float(_safe_get(ob, 'strength', 70))
                if quality >= POI_QUALITY['min_acceptable']:
                    found_structural_poi = True
                    break

    # Check BSL/SSL near current price
    if not found_structural_poi:
        for liq in liq_zones:
            liq_type = (
                liq.type if hasattr(liq, 'type') else
                (_safe_get(liq, 'type', '') if isinstance(liq, dict) else '')
            ).upper()
            liq_price = (
                liq.price if hasattr(liq, 'price') else
                (_safe_get(liq, 'price', 0) if isinstance(liq, dict) else 0)
            )
            if liq_price <= 0:
                continue

            if is_bullish and 'BSL' in liq_type:
                distance_pct = abs(liq_price - current_price) / current_price * 100
                if distance_pct <= check_range_pct:
                    found_structural_poi = True
                    break

            if not is_bullish and 'SSL' in liq_type:
                distance_pct = abs(liq_price - current_price) / current_price * 100
                if distance_pct <= check_range_pct:
                    found_structural_poi = True
                    break

    if not found_structural_poi:
        logger.debug(
            "   CONTINUATION: no OB or BSL/SSL near displacement "
            "(FVG alone insufficient for SL placement)"
        )
        return 0.0

    # Compute clear path (no OB directly ahead)
    clear_path = True
    check_range = CONTINUATION_DISTANCE['poi_check_range_pct']
    for ob in obs:
        ob_center = _get_ob_center(ob)
        if is_bullish and current_price * (1 - check_range) <= ob_center <= current_price:
            clear_path = False
            break
        if not is_bullish and current_price <= ob_center <= current_price * (1 + check_range):
            clear_path = False
            break

    # Calculate probability
    structure_present = 'MSS/BOS' in triggers
    from entry_scenarios import _calculate_probability_continuation
    probability = _calculate_probability_continuation(
        displacement_strength=displacement_strength,
        triggers=triggers,
        structure_present=structure_present,
        clear_path=clear_path,
    )
    return probability


def _score_reversal_pattern(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
    timeframe: str,
) -> float:
    """
    Score REVERSAL pattern: liquidity sweep followed by structure flip.
    Returns probability (0.0 = not valid, >0.0 = valid).
    """
    sweeps = ict_components.get('liquidity_sweeps', [])
    sb = ict_components.get('structure_break')
    disp = ict_components.get('displacement', {})

    # Validate behavioral requirements
    is_eligible, reason = _validate_reversal_behavior(
        sweeps=sweeps,
        structure_break=sb,
        displacement=disp,
        timeframe=timeframe,
    )
    if not is_eligible:
        logger.debug(f"   REVERSAL behavior invalid: {reason}")
        return 0.0

    # Require liquidity sweep trigger
    if REVERSAL_SETTINGS.get('require_sweep', True):
        if 'LIQUIDITY_SWEEP' not in triggers:
            logger.debug("   REVERSAL: no liquidity sweep trigger")
            return 0.0

    # Require structure flip (MSS/CHOCH)
    structure_flip = False
    if REVERSAL_SETTINGS.get('require_structure_flip', True):
        if not sb or sb.get('type') not in ['MSS', 'CHOCH']:
            logger.debug("   REVERSAL: no MSS/CHOCH structure flip")
            return 0.0
        structure_flip = True

    # Calculate probability
    sweep_present = bool(sweeps)
    displacement_strength = disp.get('strength', 0.0) if disp else 0.0

    from entry_scenarios import _calculate_probability_reversal
    probability = _calculate_probability_reversal(
        sweep_present=sweep_present,
        structure_flip=structure_flip,
        displacement_strength=displacement_strength,
        triggers=triggers,
    )

    # Apply confirmation modifier
    confirmation_present = _check_confirmation_layer(
        structure_break=sb,
        displacement=disp,
        sweeps=sweeps,
    )
    if REVERSAL_SETTINGS.get('use_confirmation_modifier', False):
        modifier_pct = REVERSAL_SETTINGS.get('confirmation_modifier_pct', 0.08)
        if confirmation_present:
            probability += modifier_pct
        else:
            probability -= modifier_pct
        probability = max(0.0, min(1.0, probability))

    return probability
