"""
ICT Signal Pipeline V2 - Candidate Generator

Generates entry candidates for 6 ICT scenarios:
  1. liquidity_sweep_continuation
  2. pullback_continuation
  3. breaker_continuation
  4. pullback
  5. rollback
  6. reversal

Author: galinborisov10-art
"""

import logging
from typing import List, Dict, Optional

from ict_config import CANDIDATES

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Individual scenario checks
# ─────────────────────────────────────────────

def check_liquidity_sweep_continuation(
    current_price: float,
    htf_bias: str,
    sweeps: List[Dict],
    order_blocks: List[Dict],
    fvgs: List[Dict],
) -> Optional[Dict]:
    """
    Scenario 1: Liquidity sweep → immediate rejection → continuation in HTF direction.

    Conditions:
    - Recent sweep (<= 12 candles ago)
    - Rejection confirmed (captured in sweep.strength)
    - HTF bias supports trade direction

    Returns:
        Candidate dict or None.
    """
    max_age = CANDIDATES['sweep_max_candles_ago']

    for sweep in sweeps:
        if sweep['candles_ago'] > max_age:
            continue

        # SSL sweep → BUY candidate (price swept lows, rejected up)
        if sweep['type'] == 'SSL_SWEEP' and htf_bias in ('BULLISH', 'NEUTRAL'):
            poi = _nearest_bullish_poi(current_price, order_blocks, fvgs)
            entry_zone = _poi_to_zone(poi, current_price) if poi else _fallback_zone('BUY', current_price)
            confirmations = _base_confirmations('BUY', htf_bias)
            confirmations.append('SSL_SWEEP_DETECTED')
            return {
                'scenario':      'liquidity_sweep_continuation',
                'direction':     'BUY',
                'entry_zone':    entry_zone,
                'poi_type':      poi['type'] if poi else 'SWEEP_LOW',
                'poi_strength':  poi.get('strength', 50) if poi else sweep['strength'],
                'confirmations': confirmations,
                'sweep':         sweep,
            }

        # BSL sweep → SELL candidate
        if sweep['type'] == 'BSL_SWEEP' and htf_bias in ('BEARISH', 'NEUTRAL'):
            poi = _nearest_bearish_poi(current_price, order_blocks, fvgs)
            entry_zone = _poi_to_zone(poi, current_price) if poi else _fallback_zone('SELL', current_price)
            confirmations = _base_confirmations('SELL', htf_bias)
            confirmations.append('BSL_SWEEP_DETECTED')
            return {
                'scenario':      'liquidity_sweep_continuation',
                'direction':     'SELL',
                'entry_zone':    entry_zone,
                'poi_type':      poi['type'] if poi else 'SWEEP_HIGH',
                'poi_strength':  poi.get('strength', 50) if poi else sweep['strength'],
                'confirmations': confirmations,
                'sweep':         sweep,
            }

    return None


def check_pullback_continuation(
    current_price: float,
    htf_bias: str,
    order_blocks: List[Dict],
    fvgs: List[Dict],
    bos: Optional[Dict],
) -> Optional[Dict]:
    """
    Scenario 2: Pullback to OB/FVG in trend direction (near zone, 0-3%).

    Conditions:
    - HTF bias is clear (BULLISH or BEARISH)
    - Price is within 0-3% of a valid OB or FVG
    - BOS detected (optional but adds confirmation)

    Returns:
        Candidate dict or None.
    """
    near_pct = CANDIDATES['pullback_near_zone_pct']

    if htf_bias == 'BULLISH':
        poi = _nearest_bullish_poi_in_range(current_price, order_blocks, fvgs, 0, near_pct)
        if poi:
            entry_zone = _poi_to_zone(poi, current_price)
            confirmations = _base_confirmations('BUY', htf_bias)
            if bos and bos['direction'] == 'BULLISH':
                confirmations.append('BOS_DETECTED')
            return {
                'scenario':      'pullback_continuation',
                'direction':     'BUY',
                'entry_zone':    entry_zone,
                'poi_type':      poi['type'],
                'poi_strength':  poi.get('strength', 50),
                'confirmations': confirmations,
            }

    elif htf_bias == 'BEARISH':
        poi = _nearest_bearish_poi_in_range(current_price, order_blocks, fvgs, 0, near_pct)
        if poi:
            entry_zone = _poi_to_zone(poi, current_price)
            confirmations = _base_confirmations('SELL', htf_bias)
            if bos and bos['direction'] == 'BEARISH':
                confirmations.append('BOS_DETECTED')
            return {
                'scenario':      'pullback_continuation',
                'direction':     'SELL',
                'entry_zone':    entry_zone,
                'poi_type':      poi['type'],
                'poi_strength':  poi.get('strength', 50),
                'confirmations': confirmations,
            }

    return None


def check_breaker_continuation(
    current_price: float,
    htf_bias: str,
    breaker_blocks: List[Dict],
    bos: Optional[Dict],
) -> Optional[Dict]:
    """
    Scenario 3: Retest of breaker block after OB was violated.

    Conditions:
    - Valid breaker block within reachable range
    - HTF bias supports entry direction
    - Rejection at breaker (implied by breaker block type)

    Returns:
        Candidate dict or None.
    """
    near_pct = CANDIDATES['pullback_near_zone_pct']

    for bb in breaker_blocks:
        dist = abs(current_price - (bb['high'] + bb['low']) / 2) / max(current_price, 1e-9)
        if dist > near_pct * 2:
            continue

        # Bullish breaker: original bearish OB broken upward → support retest
        if bb['original_ob_type'] == 'BEARISH_OB' and htf_bias in ('BULLISH', 'NEUTRAL'):
            entry_zone = {'min': bb['low'], 'max': bb['high'],
                          'preferred': (bb['low'] + bb['high']) / 2}
            confirmations = _base_confirmations('BUY', htf_bias)
            confirmations.append('BREAKER_BLOCK')
            if bos and bos['direction'] == 'BULLISH':
                confirmations.append('BOS_DETECTED')
            return {
                'scenario':      'breaker_continuation',
                'direction':     'BUY',
                'entry_zone':    entry_zone,
                'poi_type':      'BREAKER',
                'poi_strength':  60,
                'confirmations': confirmations,
                'breaker':       bb,
            }

        # Bearish breaker: original bullish OB broken downward → resistance retest
        if bb['original_ob_type'] == 'BULLISH_OB' and htf_bias in ('BEARISH', 'NEUTRAL'):
            entry_zone = {'min': bb['low'], 'max': bb['high'],
                          'preferred': (bb['low'] + bb['high']) / 2}
            confirmations = _base_confirmations('SELL', htf_bias)
            confirmations.append('BREAKER_BLOCK')
            if bos and bos['direction'] == 'BEARISH':
                confirmations.append('BOS_DETECTED')
            return {
                'scenario':      'breaker_continuation',
                'direction':     'SELL',
                'entry_zone':    entry_zone,
                'poi_type':      'BREAKER',
                'poi_strength':  60,
                'confirmations': confirmations,
                'breaker':       bb,
            }

    return None


def check_pullback(
    current_price: float,
    htf_bias: str,
    order_blocks: List[Dict],
    fvgs: List[Dict],
) -> Optional[Dict]:
    """
    Scenario 4: Deeper retracement to major OB (3-8% from current price).

    Conditions:
    - Valid OB in the 3-8% zone
    - May not require HTF alignment (standalone entry)

    Returns:
        Candidate dict or None.
    """
    min_pct = CANDIDATES['pullback_deep_zone_min']
    max_pct = CANDIDATES['pullback_deep_zone_max']

    all_pois = order_blocks + fvgs

    for poi in all_pois:
        poi_mid = _poi_midpoint(poi)
        dist = abs(current_price - poi_mid) / max(current_price, 1e-9)
        if not (min_pct <= dist <= max_pct):
            continue

        # BUY: bullish OB/FVG below current price
        if poi_mid < current_price and poi['type'] in ('BULLISH_OB', 'BULLISH_FVG'):
            entry_zone = _poi_to_zone(poi, current_price)
            confirmations = ['DEEP_PULLBACK']
            if htf_bias == 'BULLISH':
                confirmations.append('HTF_BULLISH')
            return {
                'scenario':      'pullback',
                'direction':     'BUY',
                'entry_zone':    entry_zone,
                'poi_type':      poi['type'],
                'poi_strength':  poi.get('strength', 50),
                'confirmations': confirmations,
            }

        # SELL: bearish OB/FVG above current price
        if poi_mid > current_price and poi['type'] in ('BEARISH_OB', 'BEARISH_FVG'):
            entry_zone = _poi_to_zone(poi, current_price)
            confirmations = ['DEEP_PULLBACK']
            if htf_bias == 'BEARISH':
                confirmations.append('HTF_BEARISH')
            return {
                'scenario':      'pullback',
                'direction':     'SELL',
                'entry_zone':    entry_zone,
                'poi_type':      poi['type'],
                'poi_strength':  poi.get('strength', 50),
                'confirmations': confirmations,
            }

    return None


def check_rollback(
    current_price: float,
    htf_bias: str,
    order_blocks: List[Dict],
    fvgs: List[Dict],
    bos: Optional[Dict],
) -> Optional[Dict]:
    """
    Scenario 5: Short-term counter-move within structure (scalp).

    Conditions:
    - Small retracement (< 3%) to nearest OB/FVG
    - Continuation signs (BOS or HTF bias)
    - Similar to pullback_continuation but looser alignment requirement

    Returns:
        Candidate dict or None.
    """
    near_pct = CANDIDATES['pullback_near_zone_pct']

    # Find the very nearest OB/FVG regardless of direction
    all_pois = order_blocks + fvgs
    nearest = None
    nearest_dist = float('inf')

    for poi in all_pois:
        poi_mid = _poi_midpoint(poi)
        dist = abs(current_price - poi_mid) / max(current_price, 1e-9)
        if dist < near_pct and dist < nearest_dist:
            nearest = poi
            nearest_dist = dist

    if not nearest:
        return None

    poi_mid  = _poi_midpoint(nearest)
    direction = 'BUY' if poi_mid < current_price else 'SELL'

    # Filter: direction should at least not contradict HTF
    if direction == 'BUY' and htf_bias == 'BEARISH':
        return None
    if direction == 'SELL' and htf_bias == 'BULLISH':
        return None

    entry_zone    = _poi_to_zone(nearest, current_price)
    confirmations = ['ROLLBACK']
    if bos:
        confirmations.append('BOS_DETECTED')
    if htf_bias in ('BULLISH', 'BEARISH'):
        confirmations.append(f'HTF_{htf_bias}')

    return {
        'scenario':      'rollback',
        'direction':     direction,
        'entry_zone':    entry_zone,
        'poi_type':      nearest['type'],
        'poi_strength':  nearest.get('strength', 40),
        'confirmations': confirmations,
    }


def check_reversal(
    current_price: float,
    htf_bias: str,
    choch: Optional[Dict],
    sweeps: List[Dict],
    order_blocks: List[Dict],
    bos: Optional[Dict],
) -> Optional[Dict]:
    """
    Scenario 6: Reversal after CHoCH + liquidity sweep.

    Conditions:
    - CHoCH detected (structure break against prior bias)
    - Liquidity sweep in opposite direction
    - MSS (market structure shift) confirmation (BOS after CHoCH)
    - High conviction required

    Returns:
        Candidate dict or None.
    """
    if not choch:
        return None

    choch_dir = choch['direction']  # Direction of the reversal move

    # Need a supporting sweep
    supporting_sweep_type = 'SSL_SWEEP' if choch_dir == 'BULLISH' else 'BSL_SWEEP'
    has_sweep = any(s['type'] == supporting_sweep_type and s['candles_ago'] <= 20
                    for s in sweeps)
    if not has_sweep:
        return None

    direction = 'BUY' if choch_dir == 'BULLISH' else 'SELL'

    # Find first OB after CHoCH in the new direction
    poi = None
    if direction == 'BUY':
        bullish_obs = [ob for ob in order_blocks if ob['type'] == 'BULLISH_OB'
                       and ob['candles_ago'] <= choch['candles_ago']]
        poi = bullish_obs[0] if bullish_obs else None
    else:
        bearish_obs = [ob for ob in order_blocks if ob['type'] == 'BEARISH_OB'
                       and ob['candles_ago'] <= choch['candles_ago']]
        poi = bearish_obs[0] if bearish_obs else None

    entry_zone = _poi_to_zone(poi, current_price) if poi else _fallback_zone(direction, current_price)
    confirmations = ['CHOCH_DETECTED', f'{supporting_sweep_type}_DETECTED']
    if bos:
        confirmations.append('MSS_CONFIRMED')

    return {
        'scenario':      'reversal',
        'direction':     direction,
        'entry_zone':    entry_zone,
        'poi_type':      poi['type'] if poi else 'CHOCH_LEVEL',
        'poi_strength':  poi.get('strength', 55) if poi else 55,
        'confirmations': confirmations,
        'choch':         choch,
    }


# ─────────────────────────────────────────────
# Main generator
# ─────────────────────────────────────────────

def generate_candidates(
    current_price: float,
    htf_bias: str,
    structure: Dict,
    orderflow: Dict,
    liquidity: Dict,
) -> List[Dict]:
    """
    Generate all valid ICT entry candidates.

    Runs all 6 scenario checks and returns a non-empty list of candidates
    (or an empty list if nothing qualifies).

    Args:
        current_price: Latest close price.
        htf_bias:      'BULLISH', 'BEARISH', or 'NEUTRAL'.
        structure:     Output from analyze_market_structure().
        orderflow:     Output from analyze_orderflow().
        liquidity:     Output from analyze_liquidity().

    Returns:
        List of candidate dicts.
    """
    order_blocks   = orderflow.get('order_blocks', [])
    breaker_blocks = orderflow.get('breaker_blocks', [])
    fvgs           = orderflow.get('fvgs', [])
    sweeps         = liquidity.get('sweeps', [])
    bos            = structure.get('bos')
    choch          = structure.get('choch')

    candidates: List[Dict] = []

    for name, check_fn, args in [
        ('liquidity_sweep_continuation', check_liquidity_sweep_continuation,
         (current_price, htf_bias, sweeps, order_blocks, fvgs)),
        ('pullback_continuation',        check_pullback_continuation,
         (current_price, htf_bias, order_blocks, fvgs, bos)),
        ('breaker_continuation',         check_breaker_continuation,
         (current_price, htf_bias, breaker_blocks, bos)),
        ('pullback',                     check_pullback,
         (current_price, htf_bias, order_blocks, fvgs)),
        ('rollback',                     check_rollback,
         (current_price, htf_bias, order_blocks, fvgs, bos)),
        ('reversal',                     check_reversal,
         (current_price, htf_bias, choch, sweeps, order_blocks, bos)),
    ]:
        try:
            candidate = check_fn(*args)
            if candidate:
                logger.info(f"   ✅ Candidate: {name} ({candidate['direction']})")
                candidates.append(candidate)
            else:
                logger.debug(f"   — No candidate for {name}")
        except Exception as exc:
            logger.warning(f"   ⚠️ Error in {name}: {exc}")

    logger.info(f"   → Total candidates: {len(candidates)}")
    return candidates


# ─────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────

def _poi_midpoint(poi: Dict) -> float:
    """Return the midpoint of an OB or FVG."""
    if 'high' in poi and 'low' in poi:
        return (poi['high'] + poi['low']) / 2
    if 'top' in poi and 'bottom' in poi:
        return (poi['top'] + poi['bottom']) / 2
    return poi.get('price', 0.0)


def _poi_to_zone(poi: Dict, current_price: float) -> Dict:
    """Convert a POI (OB or FVG) into an entry zone dict."""
    if 'high' in poi and 'low' in poi:
        lo, hi = poi['low'], poi['high']
    elif 'top' in poi and 'bottom' in poi:
        lo, hi = poi['bottom'], poi['top']
    else:
        lo = hi = poi.get('price', current_price)

    mid = (lo + hi) / 2
    # Preferred = closest edge to current price
    preferred = lo if current_price > mid else hi
    return {'min': lo, 'max': hi, 'preferred': preferred}


def _fallback_zone(direction: str, price: float) -> Dict:
    """Create a minimal fallback entry zone around current price."""
    offset = price * 0.001  # 0.1%
    if direction == 'BUY':
        return {'min': price - offset, 'max': price, 'preferred': price}
    return {'min': price, 'max': price + offset, 'preferred': price}


def _base_confirmations(direction: str, htf_bias: str) -> List[str]:
    """Build base confirmation list based on direction and HTF bias."""
    confirmations = []
    if direction == 'BUY' and htf_bias == 'BULLISH':
        confirmations.append('HTF_BULLISH')
    elif direction == 'SELL' and htf_bias == 'BEARISH':
        confirmations.append('HTF_BEARISH')
    return confirmations


def _nearest_bullish_poi(price: float, obs: List[Dict], fvgs: List[Dict]) -> Optional[Dict]:
    """Find the nearest bullish POI (OB or FVG) below current price."""
    candidates: List[Dict] = []
    for ob in obs:
        if ob['type'] == 'BULLISH_OB' and ob['low'] < price:
            candidates.append(ob)
    for fvg in fvgs:
        if fvg['type'] == 'BULLISH_FVG' and fvg['bottom'] < price:
            candidates.append(fvg)
    if not candidates:
        return None
    return min(candidates, key=lambda x: abs(price - _poi_midpoint(x)))


def _nearest_bearish_poi(price: float, obs: List[Dict], fvgs: List[Dict]) -> Optional[Dict]:
    """Find the nearest bearish POI (OB or FVG) above current price."""
    candidates: List[Dict] = []
    for ob in obs:
        if ob['type'] == 'BEARISH_OB' and ob['high'] > price:
            candidates.append(ob)
    for fvg in fvgs:
        if fvg['type'] == 'BEARISH_FVG' and fvg['top'] > price:
            candidates.append(fvg)
    if not candidates:
        return None
    return min(candidates, key=lambda x: abs(price - _poi_midpoint(x)))


def _nearest_bullish_poi_in_range(price: float, obs: List[Dict], fvgs: List[Dict],
                                   min_pct: float, max_pct: float) -> Optional[Dict]:
    """Find the nearest bullish POI within a distance range from price."""
    candidates: List[Dict] = []
    for poi in obs + fvgs:
        if poi['type'] not in ('BULLISH_OB', 'BULLISH_FVG'):
            continue
        mid  = _poi_midpoint(poi)
        dist = abs(price - mid) / max(price, 1e-9)
        if min_pct <= dist <= max_pct and mid < price:
            candidates.append(poi)
    if not candidates:
        return None
    return min(candidates, key=lambda x: abs(price - _poi_midpoint(x)))


def _nearest_bearish_poi_in_range(price: float, obs: List[Dict], fvgs: List[Dict],
                                   min_pct: float, max_pct: float) -> Optional[Dict]:
    """Find the nearest bearish POI within a distance range from price."""
    candidates: List[Dict] = []
    for poi in obs + fvgs:
        if poi['type'] not in ('BEARISH_OB', 'BEARISH_FVG'):
            continue
        mid  = _poi_midpoint(poi)
        dist = abs(price - mid) / max(price, 1e-9)
        if min_pct <= dist <= max_pct and mid > price:
            candidates.append(poi)
    if not candidates:
        return None
    return min(candidates, key=lambda x: abs(price - _poi_midpoint(x)))
