"""
Step 7A: Scenario Pattern Detector

Detects WHAT pattern the market is making WITHOUT computing entry zones.
Returns pattern type + probability score only.

Uses multi-timeframe ICT analysis according to the Timeframe Contract:
  - Entry POIs (OB/FVG/BSL/SSL): from signal_tf
  - Structure (BOS/MSS/Displacement): from structure_tf
  - HTF Bias: from htf_bias_tf

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

# HTF bias mismatch penalty: if HTF bias is known and contradicts signal bias,
# reduce probability by this factor (not a gate - still emits signal with lower confidence)
HTF_BIAS_MISMATCH_PENALTY = 0.80  # -20%


def detect_scenario_pattern(
    current_price: float,
    bias: str,
    mtf_components: Dict,
    signal_tf: str,
    tf_hierarchy: Optional['TimeframeHierarchy'] = None,
    # Backward-compat alias (ignored when mtf_components is an MTF dict)
    ict_components: Optional[Dict] = None,
    timeframe: Optional[str] = None,
) -> Tuple[Optional[str], float]:
    """
    Detect the most probable market pattern WITHOUT computing entry zones.

    Uses multi-timeframe component routing per Timeframe Contract:
      - Entry POIs  → signal_tf components
      - Structure   → structure_tf components
      - HTF Bias    → htf_bias_tf components

    Args:
        current_price: Current market price
        bias: Market bias ('BULLISH' or 'BEARISH')
        mtf_components: {timeframe: {components}} dict; or flat legacy dict
        signal_tf: Entry timeframe key used for entry POIs
        tf_hierarchy: Optional timeframe hierarchy from TimeframeContract

    Returns:
        Tuple[Optional[str], float]: (pattern_name, probability) or (None, 0.0)
    """
    logger.info("=" * 60)
    logger.info("🔍 Step 7A: Scenario Pattern Detection (MTF)")
    logger.info("=" * 60)

    # ── Resolve component dicts per timeframe ─────────────────────────────
    # If mtf_components is a flat dict (legacy/backward-compat), treat it as signal_tf components
    has_mtf_structure = _is_mtf_dict(mtf_components, signal_tf)

    if has_mtf_structure and tf_hierarchy:
        signal_comps = mtf_components.get(signal_tf, {})
        structure_comps = mtf_components.get(tf_hierarchy.structure_tf, {})
        htf_bias_comps = mtf_components.get(tf_hierarchy.htf_bias_tf, structure_comps)
        confirmation_comps = mtf_components.get(tf_hierarchy.confirmation_tf, {})
        _effective_tf = signal_tf
        logger.info(
            f"   MTF routing: signal={signal_tf}, "
            f"structure={tf_hierarchy.structure_tf}, "
            f"htf_bias={tf_hierarchy.htf_bias_tf}"
        )
    else:
        # Flat dict (legacy) - use for all components
        signal_comps = mtf_components
        structure_comps = mtf_components
        htf_bias_comps = mtf_components
        confirmation_comps = mtf_components
        _effective_tf = signal_tf or timeframe or '1h'
        logger.debug("   Flat ict_components dict - no MTF separation")

    # Extract HTF bias for penalty check
    htf_bias_str = str(htf_bias_comps.get('bias', 'NEUTRAL')).upper()

    # Detect triggers from signal_tf components (common for all patterns)
    triggers, trigger_score = _detect_triggers_weighted(
        current_price, signal_comps, bias, _effective_tf
    )
    # Also check structure triggers from structure_tf
    struct_triggers, struct_trigger_score = _detect_triggers_weighted(
        current_price, structure_comps, bias, _effective_tf
    )
    # Merge triggers (deduplicated)
    all_triggers = list(set(triggers + struct_triggers))
    trigger_strength = _evaluate_trigger_strength(trigger_score + struct_trigger_score)
    logger.info(f"   Triggers: {all_triggers} (score: {trigger_score + struct_trigger_score}, strength: {trigger_strength})")

    # Score all patterns
    pattern_scores: Dict[str, float] = {}

    # --- ROLLBACK ---
    rollback_prob = _score_rollback_pattern(
        current_price=current_price,
        bias=bias,
        signal_comps=signal_comps,
        structure_comps=structure_comps,
        htf_bias_str=htf_bias_str,
        triggers=all_triggers,
        trigger_score=trigger_score + struct_trigger_score,
        timeframe=_effective_tf,
        tf_hierarchy=tf_hierarchy,
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
        signal_comps=signal_comps,
        structure_comps=structure_comps,
        htf_bias_str=htf_bias_str,
        triggers=all_triggers,
        trigger_score=trigger_score,
        tf_hierarchy=tf_hierarchy,
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
        signal_comps=signal_comps,
        structure_comps=structure_comps,
        htf_bias_str=htf_bias_str,
        triggers=all_triggers,
        trigger_score=trigger_score + struct_trigger_score,
        timeframe=_effective_tf,
        tf_hierarchy=tf_hierarchy,
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
        signal_comps=signal_comps,
        structure_comps=structure_comps,
        htf_bias_str=htf_bias_str,
        triggers=all_triggers,
        trigger_score=trigger_score + struct_trigger_score,
        timeframe=_effective_tf,
        tf_hierarchy=tf_hierarchy,
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
# INTERNAL HELPERS
# ============================================================

def _is_mtf_dict(d: Dict, signal_tf: str) -> bool:
    """Return True if d is keyed by timeframe strings (MTF dict), not component names."""
    if not d:
        return False
    # An MTF dict has timeframe strings as keys (e.g. '1h', '2h', '4h', '1d')
    tf_like = {'1m', '5m', '15m', '30m', '1h', '2h', '3h', '4h', '6h', '8h', '12h', '1d', '3d', '1w'}
    first_key = next(iter(d))
    return first_key in tf_like or (signal_tf and signal_tf in d)


def _apply_htf_bias_penalty(probability: float, htf_bias_str: str, bias: str, pattern: str, tf_hierarchy: Optional['TimeframeHierarchy'] = None) -> float:
    """
    Apply -20% penalty when HTF bias is known and contradicts the signal bias.
    This is a SOFT check - it reduces probability but does NOT block the signal.
    """
    if htf_bias_str in ('NEUTRAL', 'RANGING', '') or htf_bias_str == 'UNKNOWN':
        return probability

    bias_upper = bias.upper()
    if htf_bias_str == bias_upper:
        return probability  # Aligned - no penalty

    # Mismatch: HTF contradicts signal bias
    htf_tf = tf_hierarchy.htf_bias_tf if tf_hierarchy else 'HTF'
    logger.debug(
        f"   {pattern}: HTF bias mismatch (signal={bias_upper}, "
        f"HTF {htf_tf}={htf_bias_str}) → applying -20% penalty"
    )
    return probability * HTF_BIAS_MISMATCH_PENALTY


# ============================================================
# PATTERN SCORING FUNCTIONS
# ============================================================

def _score_rollback_pattern(
    current_price: float,
    bias: str,
    signal_comps: Dict,
    structure_comps: Dict,
    htf_bias_str: str,
    triggers: List[str],
    trigger_score: int,
    timeframe: str,
    tf_hierarchy: Optional['TimeframeHierarchy'] = None,
) -> float:
    """
    Score ROLLBACK pattern: BOS/MSS detected → market retracing to structure break.
    Uses structure_tf for BOS/MSS, signal_tf for entry POIs.
    """
    # ✅ Structure from structure_tf
    sb = structure_comps.get('structure_break')

    # Requires structure break on structure_tf
    if not sb or not sb.get('type'):
        return 0.0

    # ✅ Structure direction must match bias (HARD block - structure contradicts bias)
    sb_direction = sb.get('direction', '').upper()
    bias_upper = bias.upper()
    if sb_direction and sb_direction != bias_upper:
        structure_tf_label = tf_hierarchy.structure_tf if tf_hierarchy else 'structure_tf'
        logger.debug(
            f"   ROLLBACK: Structure direction mismatch "
            f"(structure_tf={structure_tf_label}, direction={sb_direction} != bias={bias_upper})"
        )
        return 0.0

    # Validate behavioral requirements using signal_tf context
    is_eligible, reason = _validate_rollback_behavior(
        structure_break=sb,
        current_price=current_price,
        ict_components=signal_comps,
        timeframe=timeframe,
    )
    if not is_eligible:
        logger.debug(f"   ROLLBACK behavior invalid: {reason}")
        return 0.0

    # Calculate probability
    structure_strength = sb.get('strength', 50)
    displacement = structure_comps.get('displacement', {})
    displacement_strength = displacement.get('strength', 0) if displacement.get('detected') else 0

    # Use break_level if available, else estimate distance from current price
    break_level = sb.get('break_level') or sb.get('price')
    if break_level and break_level > 0:
        distance_pct = abs(break_level - current_price) / current_price * 100
        if distance_pct < ROLLBACK_DISTANCE['min_pct'] * 100:
            return 0.0
        if distance_pct > ROLLBACK_DISTANCE['max_pct'] * 100:
            return 0.0
    else:
        distance_pct = 2.0

    from entry_scenarios import _calculate_probability_rollback
    probability = _calculate_probability_rollback(
        structure_strength=structure_strength,
        displacement_strength=displacement_strength,
        triggers=triggers,
        distance_pct=distance_pct,
    )

    # ✅ HTF Bias alignment check (-20% penalty, NOT a gate)
    probability = _apply_htf_bias_penalty(probability, htf_bias_str, bias, 'ROLLBACK', tf_hierarchy)
    return probability


def _score_pullback_pattern(
    current_price: float,
    bias: str,
    signal_comps: Dict,
    structure_comps: Dict,
    htf_bias_str: str,
    triggers: List[str],
    trigger_score: int,
    tf_hierarchy: Optional['TimeframeHierarchy'] = None,
) -> float:
    """
    Score PULLBACK pattern: trend retracement to OB or BSL/SSL on signal_tf.
    REQUIRES OB or BSL/SSL (FVG alone is insufficient per ICT principles).
    """
    is_bullish = bias.upper() == 'BULLISH'
    is_bearish = bias.upper() == 'BEARISH'

    # ✅ Entry POIs from signal_tf
    obs = signal_comps.get('order_blocks', [])
    liq_zones = signal_comps.get('liquidity_zones', [])

    best_quality = 0.0
    best_distance = None
    found_structural_poi = False

    # Check Order Blocks from signal_tf
    for ob in obs:
        ob_type = str(
            ob.type if hasattr(ob, 'type') else
            (_safe_get(ob, 'type', '') if isinstance(ob, dict) else '')
        ).upper()
        ob_center = _get_ob_center(ob)
        if ob_center <= 0:
            continue

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

    # Check BSL/SSL from signal_tf
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

    # CRITICAL: PULLBACK requires OB or BSL/SSL from signal_tf
    if not found_structural_poi:
        logger.debug("   PULLBACK: no OB or BSL/SSL found on signal_tf (FVG alone insufficient for SL placement)")
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

    # Confirmation modifier using structure_tf data
    sb = structure_comps.get('structure_break')
    disp = structure_comps.get('displacement', {})
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

    # ✅ HTF Bias alignment check (-20% penalty, NOT a gate)
    probability = _apply_htf_bias_penalty(probability, htf_bias_str, bias, 'PULLBACK', tf_hierarchy)
    return probability


def _score_continuation_pattern(
    current_price: float,
    bias: str,
    signal_comps: Dict,
    structure_comps: Dict,
    htf_bias_str: str,
    triggers: List[str],
    trigger_score: int,
    timeframe: str,
    tf_hierarchy: Optional['TimeframeHierarchy'] = None,
) -> float:
    """
    Score CONTINUATION pattern: momentum continuation after displacement.
    Displacement is checked from structure_tf; OBs from signal_tf.
    REQUIRES OB or BSL/SSL near the displacement.
    """
    # ✅ Displacement from structure_tf
    if 'DISPLACEMENT' not in triggers and 'MSS/BOS' not in triggers:
        return 0.0

    disp = structure_comps.get('displacement', {})
    displacement_detected = disp.get('detected', False)
    displacement_strength = disp.get('strength', 0.0)

    if not displacement_detected:
        return 0.0

    is_bullish = bias.upper() == 'BULLISH'

    # ✅ Entry POIs from signal_tf
    obs = signal_comps.get('order_blocks', [])
    liq_zones = signal_comps.get('liquidity_zones', [])

    # CRITICAL: CONTINUATION requires OB or BSL/SSL near the current displacement zone
    found_structural_poi = False
    check_range_pct = CONTINUATION_DISTANCE['poi_check_range_pct'] * 100

    for ob in obs:
        ob_type = str(
            ob.type if hasattr(ob, 'type') else
            (_safe_get(ob, 'type', '') if isinstance(ob, dict) else '')
        ).upper()
        ob_center = _get_ob_center(ob)
        if ob_center <= 0:
            continue

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
            "   CONTINUATION: no OB or BSL/SSL near displacement on signal_tf "
            "(FVG alone insufficient for SL placement)"
        )
        return 0.0

    # Compute clear path (no OB directly ahead) using signal_tf OBs
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

    structure_present = 'MSS/BOS' in triggers
    from entry_scenarios import _calculate_probability_continuation
    probability = _calculate_probability_continuation(
        displacement_strength=displacement_strength,
        triggers=triggers,
        structure_present=structure_present,
        clear_path=clear_path,
    )

    # ✅ HTF Bias alignment check (-20% penalty, NOT a gate)
    probability = _apply_htf_bias_penalty(probability, htf_bias_str, bias, 'CONTINUATION', tf_hierarchy)
    return probability


def _score_reversal_pattern(
    current_price: float,
    bias: str,
    signal_comps: Dict,
    structure_comps: Dict,
    htf_bias_str: str,
    triggers: List[str],
    trigger_score: int,
    timeframe: str,
    tf_hierarchy: Optional['TimeframeHierarchy'] = None,
) -> float:
    """
    Score REVERSAL pattern: liquidity sweep followed by structure flip.
    Sweep + MSS/CHOCH from signal_tf; displacement from structure_tf.
    """
    # ✅ Sweeps from signal_tf; structure from structure_tf
    sweeps = signal_comps.get('liquidity_sweeps', [])
    sb = structure_comps.get('structure_break')
    disp = structure_comps.get('displacement', {})

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

    # Require structure flip (MSS/CHOCH) from structure_tf
    structure_flip = False
    if REVERSAL_SETTINGS.get('require_structure_flip', True):
        if not sb or sb.get('type') not in ['MSS', 'CHOCH']:
            logger.debug("   REVERSAL: no MSS/CHOCH structure flip on structure_tf")
            return 0.0
        structure_flip = True

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

    # ✅ HTF Bias alignment check (-20% penalty, NOT a gate)
    # For REVERSAL, HTF mismatch is expected (we're reversing against HTF), so smaller penalty
    if htf_bias_str not in ('NEUTRAL', 'RANGING', '', 'UNKNOWN'):
        bias_upper = bias.upper()
        if htf_bias_str == bias_upper:
            # Reversal aligned with HTF - unusual, small boost
            pass
        else:
            # Reversal against HTF - this is normal for REVERSAL, apply smaller penalty
            probability = probability * 0.90  # Only -10% for REVERSAL (vs -20% for trend patterns)
            htf_tf = tf_hierarchy.htf_bias_tf if tf_hierarchy else 'HTF'
            logger.debug(
                f"   REVERSAL: trading against HTF bias ({htf_tf}={htf_bias_str}) "
                f"→ -10% probability (normal for REVERSAL)"
            )

    return probability

