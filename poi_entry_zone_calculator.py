"""
Step 7B: POI Entry Zone Calculator

Given a detected pattern, selects ONE POI and extracts BOTH:
  - entry_zone: the structural zone to enter from
  - invalidation_anchor: the structural boundary for SL placement

CRITICAL RULE: entry_zone and invalidation_anchor MUST come from the SAME POI.

Mandatory POI Requirements:
  - PULLBACK   → REQUIRES OB or BSL/SSL (FVG alone insufficient for SL)
  - CONTINUATION → REQUIRES OB or BSL/SSL (FVG alone insufficient for SL)
  - ROLLBACK   → Structure break level (both entry and anchor from break)
  - REVERSAL   → Liquidity sweep zone (both entry and anchor from sweep)

Author: galinborisov10-art
Date: 2026-03-09
"""

import logging
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from entry_scenarios import (
    _safe_get,
    _get_ob_center,
    _create_safe_poi_data,
    _create_invalidation_anchor,
)
from entry_scenario_config import (
    ROLLBACK_DISTANCE,
    PULLBACK_DISTANCE,
    CONTINUATION_DISTANCE,
    REVERSAL_DISTANCE,
    POI_QUALITY,
    POSITION_SIZE,
)

logger = logging.getLogger(__name__)

# ── Rollback constants ──────────────────────────────────────────────────────
# Default buffer when no explicit break_level is stored in structure_break
ROLLBACK_DEFAULT_BUFFER = 0.01   # 1% retracement zone from current price

# ── Reversal anchor buffer ─────────────────────────────────────────────────
# How far beyond the sweep price to place the invalidation anchor
REVERSAL_ANCHOR_BUFFER_PCT = 0.002  # 0.2% beyond sweep price


def calculate_entry_zone_from_poi(
    pattern_name: str,
    current_price: float,
    bias: str,
    ict_components: Dict,
    timeframe: str,
) -> Optional[Dict]:
    """
    Given a detected pattern, calculate the entry zone and invalidation anchor
    from a single, consistent POI.

    Args:
        pattern_name: 'ROLLBACK', 'PULLBACK', 'CONTINUATION', or 'REVERSAL'
        current_price: Current market price
        bias: Market bias ('BULLISH' or 'BEARISH')
        ict_components: ICT analysis components
        timeframe: Trading timeframe

    Returns:
        Dict with keys:
            'entry_zone': {center, low, high, source, quality, distance_pct, distance_price}
            'invalidation_anchor': {type, price, source_type, source_data}
            'poi_type': str
            'poi_data': dict
            'scenario': str (same as pattern_name)
            'probability': float (carried from Step 7A)
            'position_size_advisory': int
            'reasoning': str
        OR None if no valid POI available.
    """
    logger.info(f"🎯 Step 7B: Entry Zone from POI for {pattern_name}")

    if pattern_name == 'PULLBACK':
        return _calculate_pullback_entry_zone(current_price, bias, ict_components)
    elif pattern_name == 'CONTINUATION':
        return _calculate_continuation_entry_zone(current_price, bias, ict_components, timeframe)
    elif pattern_name == 'ROLLBACK':
        return _calculate_rollback_entry_zone(current_price, bias, ict_components)
    elif pattern_name == 'REVERSAL':
        return _calculate_reversal_entry_zone(current_price, bias, ict_components)
    else:
        logger.error(f"❌ Unknown pattern: {pattern_name}")
        return None


# ============================================================
# PULLBACK ENTRY ZONE (REQUIRES OB or BSL/SSL)
# ============================================================

def _calculate_pullback_entry_zone(
    current_price: float,
    bias: str,
    ict_components: Dict,
) -> Optional[Dict]:
    """
    Calculate entry zone for PULLBACK pattern.
    REQUIRES OB or BSL/SSL - returns None if neither is available.
    Entry and invalidation anchor come from the SAME structural POI.
    """
    is_bullish = bias.upper() == 'BULLISH'
    is_bearish = bias.upper() == 'BEARISH'

    obs = ict_components.get('order_blocks', [])
    liq_zones = ict_components.get('liquidity_zones', [])
    poi_candidates = []

    # Collect OB candidates (structural boundary, preferred)
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
                    poi_candidates.append({
                        'type': 'OB',
                        'price': ob_center,
                        'low': (ob.zone_low if hasattr(ob, 'zone_low')
                                else (_safe_get(ob, 'zone_low') if isinstance(ob, dict) else None)),
                        'high': (ob.zone_high if hasattr(ob, 'zone_high')
                                 else (_safe_get(ob, 'zone_high') if isinstance(ob, dict) else None)),
                        'distance_pct': distance_pct,
                        'quality': quality,
                        '_ref': ob,
                    })

        if is_bearish and 'BEARISH' in ob_type and ob_center > current_price:
            distance_pct = abs(ob_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                quality = float(_safe_get(ob, 'strength', 70))
                if quality >= POI_QUALITY['min_acceptable']:
                    poi_candidates.append({
                        'type': 'OB',
                        'price': ob_center,
                        'low': (ob.zone_low if hasattr(ob, 'zone_low')
                                else (_safe_get(ob, 'zone_low') if isinstance(ob, dict) else None)),
                        'high': (ob.zone_high if hasattr(ob, 'zone_high')
                                 else (_safe_get(ob, 'zone_high') if isinstance(ob, dict) else None)),
                        'distance_pct': distance_pct,
                        'quality': quality,
                        '_ref': ob,
                    })

    # Collect BSL/SSL candidates (liquidity boundary)
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
                    poi_candidates.append({
                        'type': 'BSL',
                        'price': liq_price,
                        'low': liq_price * 0.999,
                        'high': liq_price * 1.001,
                        'distance_pct': distance_pct,
                        'quality': quality,
                        '_ref': liq,
                    })

        if is_bearish and 'SSL' in liq_type and liq_price > current_price:
            distance_pct = abs(liq_price - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                quality = float(_safe_get(liq, 'confidence', 0.7)) * 100
                if quality >= POI_QUALITY['min_acceptable']:
                    poi_candidates.append({
                        'type': 'SSL',
                        'price': liq_price,
                        'low': liq_price * 0.999,
                        'high': liq_price * 1.001,
                        'distance_pct': distance_pct,
                        'quality': quality,
                        '_ref': liq,
                    })

    # CRITICAL: PULLBACK requires OB or BSL/SSL
    if not poi_candidates:
        logger.error(
            "❌ PULLBACK requires OB or BSL/SSL - none found. "
            "Cannot create pullback without structural POI for SL."
        )
        return None

    # Select best POI: highest quality, then closest
    best_poi = max(poi_candidates, key=lambda x: (x['quality'], -x['distance_pct']))
    poi_ref = best_poi.pop('_ref', None)

    # Build entry zone and invalidation anchor from the SAME POI
    buffer = PULLBACK_DISTANCE['buffer_pct']
    entry_center = best_poi['price']
    entry_low = best_poi['low'] or (entry_center * (1 - buffer))
    entry_high = best_poi['high'] or (entry_center * (1 + buffer))

    entry_zone = {
        'center': entry_center,
        'low': entry_low * (1 - buffer) if best_poi['low'] else entry_center * (1 - buffer),
        'high': entry_high * (1 + buffer) if best_poi['high'] else entry_center * (1 + buffer),
        'source': f"PULLBACK_{best_poi['type']}",
        'quality': best_poi['quality'],
        'distance_pct': best_poi['distance_pct'],
        'distance_price': abs(entry_center - current_price),
    }

    # Invalidation anchor comes from SAME POI as entry zone
    invalidation_anchor = _create_invalidation_anchor(
        poi_type=best_poi['type'],
        poi_object=poi_ref,
        best_poi=best_poi,
        bias=bias,
    )

    poi_data = _create_safe_poi_data(best_poi['type'], poi_ref)

    logger.info(
        f"   ✅ PULLBACK entry zone: ${entry_center:.4f} "
        f"(from {best_poi['type']}, distance {best_poi['distance_pct']:.1f}%)"
    )
    logger.info(
        f"   ✅ Invalidation anchor: {invalidation_anchor['type']} "
        f"@ ${invalidation_anchor['price']:.4f} (SAME POI: {best_poi['type']})"
    )

    return {
        'scenario': 'PULLBACK',
        'entry_zone': entry_zone,
        'invalidation_anchor': invalidation_anchor,
        'poi_type': best_poi['type'],
        'poi_data': poi_data,
        'position_size_advisory': POSITION_SIZE['PULLBACK'],
        'reasoning': (
            f"Pullback to {best_poi['type']} @ ${entry_center:.2f} "
            f"({best_poi['distance_pct']:.1f}% away). "
            f"SL at {invalidation_anchor['type']} @ ${invalidation_anchor['price']:.2f} (same POI)."
        ),
    }


# ============================================================
# CONTINUATION ENTRY ZONE (REQUIRES OB or BSL/SSL)
# ============================================================

def _calculate_continuation_entry_zone(
    current_price: float,
    bias: str,
    ict_components: Dict,
    timeframe: str,
) -> Optional[Dict]:
    """
    Calculate entry zone for CONTINUATION pattern.
    REQUIRES OB or BSL/SSL near the displacement - returns None if not available.
    Entry and invalidation anchor come from the SAME structural POI.
    """
    is_bullish = bias.upper() == 'BULLISH'
    obs = ict_components.get('order_blocks', [])
    liq_zones = ict_components.get('liquidity_zones', [])

    check_range_pct = CONTINUATION_DISTANCE['poi_check_range_pct'] * 100
    poi_candidates = []

    # Collect OBs near current price (displacement zone)
    for ob in obs:
        ob_type = str(
            ob.type if hasattr(ob, 'type') else
            (_safe_get(ob, 'type', '') if isinstance(ob, dict) else '')
        ).upper()
        ob_center = _get_ob_center(ob)
        if ob_center <= 0:
            continue

        bias_match = (is_bullish and 'BULLISH' in ob_type) or (not is_bullish and 'BEARISH' in ob_type)
        if not bias_match:
            continue

        distance_pct = abs(ob_center - current_price) / current_price * 100
        if distance_pct <= check_range_pct:
            quality = float(_safe_get(ob, 'strength', 70))
            if quality >= POI_QUALITY['min_acceptable']:
                poi_candidates.append({
                    'type': 'OB',
                    'price': ob_center,
                    'low': (ob.zone_low if hasattr(ob, 'zone_low')
                            else (_safe_get(ob, 'zone_low') if isinstance(ob, dict) else None)),
                    'high': (ob.zone_high if hasattr(ob, 'zone_high')
                             else (_safe_get(ob, 'zone_high') if isinstance(ob, dict) else None)),
                    'distance_pct': distance_pct,
                    'quality': quality,
                    '_ref': ob,
                })

    # Collect BSL/SSL near current price
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

        bias_match = (is_bullish and 'BSL' in liq_type) or (not is_bullish and 'SSL' in liq_type)
        if not bias_match:
            continue

        distance_pct = abs(liq_price - current_price) / current_price * 100
        if distance_pct <= check_range_pct:
            quality = float(_safe_get(liq, 'confidence', 0.7)) * 100
            if quality >= POI_QUALITY['min_acceptable']:
                poi_candidates.append({
                    'type': 'BSL' if is_bullish else 'SSL',
                    'price': liq_price,
                    'low': liq_price * 0.999,
                    'high': liq_price * 1.001,
                    'distance_pct': distance_pct,
                    'quality': quality,
                    '_ref': liq,
                })

    # CRITICAL: CONTINUATION requires OB or BSL/SSL
    if not poi_candidates:
        logger.error(
            "❌ CONTINUATION requires OB or BSL/SSL - none found near displacement. "
            "Cannot create continuation without structural POI for SL."
        )
        return None

    # Select best POI: highest quality, then closest
    best_poi = max(poi_candidates, key=lambda x: (x['quality'], -x['distance_pct']))
    poi_ref = best_poi.pop('_ref', None)

    # Entry is a small retracement from current price to the OB/BSL/SSL zone
    retracement = CONTINUATION_DISTANCE['retracement_pct']
    entry_center = current_price * (1 - retracement) if is_bullish else current_price * (1 + retracement)
    # Snap to POI center if it's closer than the calculated retracement
    if abs(best_poi['price'] - current_price) / current_price < retracement * 2:
        entry_center = best_poi['price']

    buffer = CONTINUATION_DISTANCE['buffer_pct']
    entry_zone = {
        'center': entry_center,
        'low': entry_center * (1 - buffer),
        'high': entry_center * (1 + buffer),
        'source': f"CONTINUATION_{best_poi['type']}",
        'quality': best_poi['quality'],
        'distance_pct': abs(entry_center - current_price) / current_price * 100,
        'distance_price': abs(entry_center - current_price),
    }

    # Invalidation anchor from SAME POI as entry zone
    invalidation_anchor = _create_invalidation_anchor(
        poi_type=best_poi['type'],
        poi_object=poi_ref,
        best_poi=best_poi,
        bias=bias,
    )

    poi_data = _create_safe_poi_data(best_poi['type'], poi_ref)

    logger.info(
        f"   ✅ CONTINUATION entry zone: ${entry_center:.4f} "
        f"(from {best_poi['type']}, retracement {retracement*100:.1f}%)"
    )
    logger.info(
        f"   ✅ Invalidation anchor: {invalidation_anchor['type']} "
        f"@ ${invalidation_anchor['price']:.4f} (SAME POI: {best_poi['type']})"
    )

    # Dynamic position size based on trigger count
    triggers = ict_components.get('_detected_triggers', [])
    if len(triggers) >= 3:
        position_size = POSITION_SIZE['CONTINUATION']['3_triggers']
    else:
        position_size = POSITION_SIZE['CONTINUATION']['2_triggers']

    return {
        'scenario': 'CONTINUATION',
        'entry_zone': entry_zone,
        'invalidation_anchor': invalidation_anchor,
        'poi_type': best_poi['type'],
        'poi_data': poi_data,
        'position_size_advisory': position_size,
        'reasoning': (
            f"Continuation via {best_poi['type']} @ ${entry_center:.2f}. "
            f"SL at {invalidation_anchor['type']} @ ${invalidation_anchor['price']:.2f} (same POI)."
        ),
    }


# ============================================================
# ROLLBACK ENTRY ZONE (Structure break level)
# ============================================================

def _calculate_rollback_entry_zone(
    current_price: float,
    bias: str,
    ict_components: Dict,
) -> Optional[Dict]:
    """
    Calculate entry zone for ROLLBACK pattern.
    Uses structure break level for both entry and invalidation anchor.
    """
    sb = ict_components.get('structure_break')
    is_bullish = bias.upper() == 'BULLISH'

    # Get break level: prefer 'break_level', fall back to 'price'
    break_level = None
    if sb:
        break_level = sb.get('break_level') or sb.get('price')

    if not break_level:
        # No explicit break level: use current price as break zone with a small buffer
        # This allows ROLLBACK to work even when break_level isn't stored
        logger.warning("   ⚠️ ROLLBACK: no break_level in structure_break - estimating from current price")
        # Estimate: price recently broke a level nearby, use ROLLBACK_DEFAULT_BUFFER retracement zone
        if is_bullish:
            break_level = current_price * (1 - ROLLBACK_DEFAULT_BUFFER)
        else:
            break_level = current_price * (1 + ROLLBACK_DEFAULT_BUFFER)

    # Distance check
    distance_pct = abs(break_level - current_price) / current_price * 100
    if distance_pct < ROLLBACK_DISTANCE['min_pct'] * 100:
        logger.debug(f"   ROLLBACK: too close to break level ({distance_pct:.2f}%)")
        return None
    if distance_pct > ROLLBACK_DISTANCE['max_pct'] * 100:
        logger.debug(f"   ROLLBACK: too far from break level ({distance_pct:.2f}%)")
        return None

    # Bias alignment check
    if is_bullish and break_level >= current_price:
        logger.debug("   ROLLBACK: BULLISH but break_level above current price")
        return None
    if not is_bullish and break_level <= current_price:
        logger.debug("   ROLLBACK: BEARISH but break_level below current price")
        return None

    buffer = ROLLBACK_DISTANCE['buffer_pct']
    entry_zone = {
        'center': break_level,
        'low': break_level * (1 - buffer),
        'high': break_level * (1 + buffer),
        'source': f"ROLLBACK_{sb.get('type', 'BOS') if sb else 'BOS'}",
        'quality': int(sb.get('strength', 60)) if sb else 60,
        'distance_pct': distance_pct,
        'distance_price': abs(break_level - current_price),
    }

    # Invalidation anchor: swing beyond the break level (same POI = the break level itself)
    anchor_price = break_level * (0.995 if is_bullish else 1.005)
    invalidation_anchor = {
        'type': 'SWING_LOW' if is_bullish else 'SWING_HIGH',
        'price': float(anchor_price),
        'source_type': 'STRUCTURE_BREAK',
        'source_data': {
            'break_level': float(break_level),
            'type': sb.get('type', 'BOS') if sb else 'BOS',
        },
    }

    logger.info(
        f"   ✅ ROLLBACK entry zone: ${break_level:.4f} "
        f"(structure break, distance {distance_pct:.1f}%)"
    )
    logger.info(
        f"   ✅ Invalidation anchor: {invalidation_anchor['type']} "
        f"@ ${invalidation_anchor['price']:.4f} (SAME POI: break level)"
    )

    return {
        'scenario': 'ROLLBACK',
        'entry_zone': entry_zone,
        'invalidation_anchor': invalidation_anchor,
        'poi_type': 'STRUCTURE_BREAK',
        'poi_data': {
            'type': sb.get('type', 'BOS') if sb else 'BOS',
            'break_level': float(break_level),
        },
        'position_size_advisory': POSITION_SIZE['ROLLBACK'],
        'reasoning': (
            f"Rollback to structure break @ ${break_level:.2f} "
            f"({distance_pct:.1f}% from current). "
            f"SL beyond break level @ ${anchor_price:.2f} (same POI)."
        ),
    }


# ============================================================
# REVERSAL ENTRY ZONE (Liquidity sweep zone)
# ============================================================

def _calculate_reversal_entry_zone(
    current_price: float,
    bias: str,
    ict_components: Dict,
) -> Optional[Dict]:
    """
    Calculate entry zone for REVERSAL pattern.
    Uses liquidity sweep zone for both entry and invalidation anchor.
    """
    sweeps = ict_components.get('liquidity_sweeps', [])
    sb = ict_components.get('structure_break')
    is_bullish = bias.upper() == 'BULLISH'

    if not sweeps:
        logger.debug("   REVERSAL: no sweeps available for entry zone")
        return None

    # Get the most recent sweep
    best_sweep = sweeps[0]
    sweep_price = (
        best_sweep.price if hasattr(best_sweep, 'price') else
        (best_sweep.get('price', 0) if isinstance(best_sweep, dict) else 0)
    )
    if not sweep_price:
        logger.debug("   REVERSAL: sweep has no price")
        return None

    distance_pct = abs(sweep_price - current_price) / current_price * 100

    # Try structure break level if sweep is too far
    break_level = sb.get('break_level') or sb.get('price') if sb else None
    entry_price = sweep_price
    entry_type = 'SWEEP'

    if break_level and REVERSAL_DISTANCE['min_pct'] * 100 <= abs(break_level - current_price) / current_price * 100 <= REVERSAL_DISTANCE['max_pct'] * 100:
        entry_price = break_level
        entry_type = 'BREAK_LEVEL'
        distance_pct = abs(break_level - current_price) / current_price * 100

    buffer = REVERSAL_DISTANCE['buffer_pct']
    entry_zone = {
        'center': entry_price,
        'low': entry_price * (1 - buffer),
        'high': entry_price * (1 + buffer),
        'source': f"REVERSAL_{entry_type}",
        'quality': 70,
        'distance_pct': distance_pct,
        'distance_price': abs(entry_price - current_price),
    }

    # Invalidation anchor: beyond the sweep level (same POI = the sweep zone)
    anchor_price = sweep_price * (1 - REVERSAL_ANCHOR_BUFFER_PCT if is_bullish else 1 + REVERSAL_ANCHOR_BUFFER_PCT)
    invalidation_anchor = {
        'type': 'LIQUIDITY_LOW' if is_bullish else 'LIQUIDITY_HIGH',
        'price': float(anchor_price),
        'source_type': 'LIQUIDITY_SWEEP',
        'source_data': {
            'sweep_price': float(sweep_price),
            'entry_type': entry_type,
        },
    }

    logger.info(
        f"   ✅ REVERSAL entry zone: ${entry_price:.4f} "
        f"(from {entry_type}, distance {distance_pct:.1f}%)"
    )
    logger.info(
        f"   ✅ Invalidation anchor: {invalidation_anchor['type']} "
        f"@ ${invalidation_anchor['price']:.4f} (SAME POI: sweep level)"
    )

    return {
        'scenario': 'REVERSAL',
        'entry_zone': entry_zone,
        'invalidation_anchor': invalidation_anchor,
        'poi_type': 'LIQUIDITY_SWEEP',
        'poi_data': {
            'sweep_price': float(sweep_price),
            'entry_type': entry_type,
        },
        'position_size_advisory': POSITION_SIZE.get('REVERSAL', 75),
        'reasoning': (
            f"Reversal from sweep @ ${entry_price:.2f} "
            f"({distance_pct:.1f}% from current). "
            f"SL beyond sweep @ ${anchor_price:.2f} (same POI)."
        ),
    }
