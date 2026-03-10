"""
ICT Signal Pipeline V2 - Entry Calculator

Calculates ICT-compliant entry zones, stop-loss, and take-profit levels.

Author: galinborisov10-art
"""

import logging
from typing import Dict, List, Optional

from ict_config import ATR_BUFFERS, RISK_REWARD

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Entry zone
# ─────────────────────────────────────────────

def calculate_entry_zone(candidate: Dict) -> Dict:
    """
    Return the entry zone from the candidate, resolving preferred entry price.

    The 'preferred' entry is the edge of the POI closest to current price,
    giving a tighter stop-loss.

    Args:
        candidate: Candidate dict from candidate_generator.

    Returns:
        Entry zone dict: {min, max, preferred}
    """
    zone = candidate.get('entry_zone', {})
    if not zone:
        return {'min': 0.0, 'max': 0.0, 'preferred': 0.0}
    return zone


# ─────────────────────────────────────────────
# Stop-Loss
# ─────────────────────────────────────────────

def calculate_sl(entry: float, poi: Dict, atr: float, poi_type: str,
                 direction: str) -> float:
    """
    Calculate ICT-compliant stop-loss placement.

    ATR buffers (from ict_config.ATR_BUFFERS):
    - OB long:     SL = OB.low  - (0.30 * ATR)
    - OB short:    SL = OB.high + (0.30 * ATR)
    - FVG long:    SL = FVG.bottom - (0.30 * ATR)
    - FVG short:   SL = FVG.top    + (0.30 * ATR)
    - Sweep long:  SL = sweep_wick_low  - (0.25 * ATR)
    - Sweep short: SL = sweep_wick_high + (0.25 * ATR)

    Args:
        entry:     Entry price.
        poi:       POI dict (OB, FVG, etc.).
        atr:       ATR(14) for the instrument.
        poi_type:  'BULLISH_OB', 'BEARISH_OB', 'BULLISH_FVG', 'BEARISH_FVG',
                   'BREAKER', 'SWEEP_LOW', 'SWEEP_HIGH', or 'CHOCH_LEVEL'.
        direction: 'BUY' or 'SELL'.

    Returns:
        Stop-loss price as float.
    """
    try:
        if poi_type in ('BULLISH_OB', 'BREAKER') and direction == 'BUY':
            poi_low = poi.get('low', entry - atr)
            return poi_low - ATR_BUFFERS['ob_long'] * atr

        elif poi_type == 'BEARISH_OB' and direction == 'SELL':
            poi_high = poi.get('high', entry + atr)
            return poi_high + ATR_BUFFERS['ob_short'] * atr

        elif poi_type == 'BULLISH_FVG' and direction == 'BUY':
            poi_bottom = poi.get('bottom', entry - atr)
            return poi_bottom - ATR_BUFFERS['fvg_long'] * atr

        elif poi_type == 'BEARISH_FVG' and direction == 'SELL':
            poi_top = poi.get('top', entry + atr)
            return poi_top + ATR_BUFFERS['fvg_short'] * atr

        elif poi_type == 'SWEEP_LOW' and direction == 'BUY':
            sweep_low = poi.get('sweep_price', entry - atr)
            return sweep_low - ATR_BUFFERS['sweep_long'] * atr

        elif poi_type == 'SWEEP_HIGH' and direction == 'SELL':
            sweep_high = poi.get('sweep_price', entry + atr)
            return sweep_high + ATR_BUFFERS['sweep_short'] * atr

        elif poi_type == 'CHOCH_LEVEL':
            level = poi.get('level', entry)
            if direction == 'BUY':
                return level - ATR_BUFFERS['ob_long'] * atr
            return level + ATR_BUFFERS['ob_short'] * atr

        else:
            # Generic fallback: 1 ATR beyond entry
            if direction == 'BUY':
                return entry - atr
            return entry + atr

    except Exception as exc:
        logger.warning(f"⚠️ calculate_sl error ({poi_type}): {exc}")
        if direction == 'BUY':
            return entry - atr
        return entry + atr


# ─────────────────────────────────────────────
# Take-Profit
# ─────────────────────────────────────────────

def find_next_structure_target(entry: float, direction: str,
                               swing_highs: List[Dict],
                               swing_lows: List[Dict],
                               pools: List[Dict]) -> Optional[float]:
    """
    Find the nearest significant structure target in the trade direction.

    Checks:
    1. Nearest swing high/low in trade direction.
    2. Clustered liquidity pool in trade direction.

    Args:
        entry:       Entry price.
        direction:   'BUY' or 'SELL'.
        swing_highs: Swing high dicts (sorted newest first).
        swing_lows:  Swing low dicts (sorted newest first).
        pools:       Liquidity pool dicts.

    Returns:
        Target price or None.
    """
    targets: List[float] = []

    if direction == 'BUY':
        # Look for swing highs above entry
        for sh in swing_highs:
            if sh['price'] > entry:
                targets.append(sh['price'])
        # BSL pools above entry
        for pool in pools:
            if pool['type'] == 'BUY_SIDE_LIQUIDITY' and pool['price'] > entry:
                targets.append(pool['price'])
    else:
        # Look for swing lows below entry
        for sl in swing_lows:
            if sl['price'] < entry:
                targets.append(sl['price'])
        # SSL pools below entry
        for pool in pools:
            if pool['type'] == 'SELL_SIDE_LIQUIDITY' and pool['price'] < entry:
                targets.append(pool['price'])

    if not targets:
        return None

    # Nearest target in trade direction
    if direction == 'BUY':
        return min(targets)  # Closest resistance above
    else:
        return max(targets)  # Closest support below


def calculate_tp(entry: float, sl: float, direction: str,
                 swing_highs: List[Dict], swing_lows: List[Dict],
                 pools: List[Dict], min_rr: float = RISK_REWARD['minimum']) -> Optional[float]:
    """
    Calculate ICT-compliant take-profit.

    Finds the nearest structure target that satisfies the minimum RR ratio.
    Returns None if no valid target found.

    Args:
        entry:       Entry price.
        sl:          Stop-loss price.
        direction:   'BUY' or 'SELL'.
        swing_highs: Swing high list.
        swing_lows:  Swing low list.
        pools:       Liquidity pool list.
        min_rr:      Minimum acceptable RR ratio (default 2.5).

    Returns:
        Take-profit price or None.
    """
    risk = abs(entry - sl)
    if risk <= 0:
        return None

    all_targets: List[float] = []

    if direction == 'BUY':
        for sh in swing_highs:
            if sh['price'] > entry:
                all_targets.append(sh['price'])
        for pool in pools:
            if pool['type'] == 'BUY_SIDE_LIQUIDITY' and pool['price'] > entry:
                all_targets.append(pool['price'])
    else:
        for swing_low_pt in swing_lows:
            if swing_low_pt['price'] < entry:
                all_targets.append(swing_low_pt['price'])
        for pool in pools:
            if pool['type'] == 'SELL_SIDE_LIQUIDITY' and pool['price'] < entry:
                all_targets.append(pool['price'])

    # Filter targets that meet minimum RR
    valid_targets = []
    for tp_candidate in all_targets:
        reward = abs(tp_candidate - entry)
        rr     = reward / risk
        if rr >= min_rr:
            valid_targets.append((tp_candidate, rr))

    if not valid_targets:
        logger.info(f"   ❌ No TP target with RR >= {min_rr}")
        return None

    # Choose the nearest qualifying target
    if direction == 'BUY':
        best = min(valid_targets, key=lambda x: x[0])
    else:
        best = max(valid_targets, key=lambda x: x[0])

    tp, rr = best
    logger.info(f"   → TP: {tp:.4f}  RR: {rr:.2f}")
    return float(tp)


# ─────────────────────────────────────────────
# Convenience wrapper
# ─────────────────────────────────────────────

def calculate_entry_sl_tp(
    candidate: Dict,
    atr: float,
    structure: Dict,
    liquidity: Dict,
) -> Optional[Dict]:
    """
    Calculate entry, stop-loss, and take-profit for a candidate.

    Returns None if no valid TP can be found (RR < minimum).

    Args:
        candidate: Candidate dict.
        atr:       ATR(14) value.
        structure: Output from analyze_market_structure().
        liquidity: Output from analyze_liquidity().

    Returns:
        Dict {entry, sl, tp, rr} or None.
    """
    entry_zone = calculate_entry_zone(candidate)
    entry      = entry_zone.get('preferred', 0.0)
    if not entry:
        return None

    direction  = candidate['direction']
    poi_type   = candidate.get('poi_type', '')

    # Build a POI dict for SL calculation
    sweep  = candidate.get('sweep', {})
    choch  = candidate.get('choch', {})
    breaker = candidate.get('breaker', {})
    poi    = sweep or choch or breaker or entry_zone

    sl = calculate_sl(entry, poi, atr, poi_type, direction)

    swing_highs = structure.get('swing_highs', [])
    swing_lows  = structure.get('swing_lows', [])
    pools       = liquidity.get('pools', [])

    tp = calculate_tp(entry, sl, direction, swing_highs, swing_lows, pools)

    if tp is None:
        return None

    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    rr     = round(reward / max(risk, 1e-9), 2)

    return {'entry': entry, 'sl': sl, 'tp': tp, 'rr': rr}
