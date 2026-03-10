"""
ICT Signal Pipeline V2 - Liquidity Detector

Detects:
  - Liquidity pools (equal highs/lows, session highs/lows)
  - Liquidity sweeps (wick beyond pool + fast rejection)

Author: galinborisov10-art
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional

from ict_config import LIQUIDITY

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Equal highs / lows helpers
# ─────────────────────────────────────────────

def find_equal_highs(swing_highs: List[Dict],
                     tolerance_pct: float = LIQUIDITY['equal_level_tolerance']) -> List[Dict]:
    """
    Find clusters of swing highs that are within ``tolerance_pct`` of each other.

    These clusters represent buy-side liquidity (resting stop orders above).

    Args:
        swing_highs:    List from detect_swing_points (kind='high').
        tolerance_pct:  Price tolerance to consider two highs "equal" (default 0.3%).

    Returns:
        List of liquidity pool dicts:
        {type: 'BUY_SIDE_LIQUIDITY', price: float, strength: float, candles_ago: int}
    """
    pools: List[Dict] = []
    used = set()

    for i, sh_i in enumerate(swing_highs):
        if i in used:
            continue
        cluster = [sh_i]
        for j, sh_j in enumerate(swing_highs):
            if j <= i or j in used:
                continue
            diff = abs(sh_i['price'] - sh_j['price']) / max(sh_i['price'], 1e-9)
            if diff <= tolerance_pct:
                cluster.append(sh_j)
                used.add(j)

        if len(cluster) >= 2:
            avg_price = float(np.mean([c['price'] for c in cluster]))
            # More touches → stronger liquidity
            strength  = 1.0 + (len(cluster) - 2) * 0.5
            strength  = min(strength, 2.0)
            oldest    = max(c['candles_ago'] for c in cluster)
            pools.append({
                'type':        'BUY_SIDE_LIQUIDITY',
                'price':       avg_price,
                'strength':    strength,
                'candles_ago': oldest,
                'touch_count': len(cluster),
            })

    return pools


def find_equal_lows(swing_lows: List[Dict],
                    tolerance_pct: float = LIQUIDITY['equal_level_tolerance']) -> List[Dict]:
    """
    Find clusters of swing lows that are within ``tolerance_pct`` of each other.

    These clusters represent sell-side liquidity (resting stop orders below).

    Args:
        swing_lows:     List from detect_swing_points (kind='low').
        tolerance_pct:  Price tolerance (default 0.3%).

    Returns:
        List of liquidity pool dicts:
        {type: 'SELL_SIDE_LIQUIDITY', price: float, strength: float, candles_ago: int}
    """
    pools: List[Dict] = []
    used = set()

    for i, sl_i in enumerate(swing_lows):
        if i in used:
            continue
        cluster = [sl_i]
        for j, sl_j in enumerate(swing_lows):
            if j <= i or j in used:
                continue
            diff = abs(sl_i['price'] - sl_j['price']) / max(sl_i['price'], 1e-9)
            if diff <= tolerance_pct:
                cluster.append(sl_j)
                used.add(j)

        if len(cluster) >= 2:
            avg_price = float(np.mean([c['price'] for c in cluster]))
            strength  = 1.0 + (len(cluster) - 2) * 0.5
            strength  = min(strength, 2.0)
            oldest    = max(c['candles_ago'] for c in cluster)
            pools.append({
                'type':        'SELL_SIDE_LIQUIDITY',
                'price':       avg_price,
                'strength':    strength,
                'candles_ago': oldest,
                'touch_count': len(cluster),
            })

    return pools


# ─────────────────────────────────────────────
# Session highs / lows
# ─────────────────────────────────────────────

def _session_levels(df: pd.DataFrame, lookback: int = LIQUIDITY['session_lookback']) -> List[Dict]:
    """
    Add session high and session low as liquidity pools.

    The session is defined as the last ``lookback`` candles.

    Returns:
        Two pool dicts: session BSL (high) and SSL (low).
    """
    window = df.iloc[-lookback:]
    session_high = float(window['high'].max())
    session_low  = float(window['low'].min())

    high_idx = int(window['high'].values.argmax())
    low_idx  = int(window['low'].values.argmin())

    n = len(df)

    return [
        {
            'type':        'BUY_SIDE_LIQUIDITY',
            'price':       session_high,
            'strength':    1.5,
            'candles_ago': lookback - high_idx - 1,
            'touch_count': 1,
        },
        {
            'type':        'SELL_SIDE_LIQUIDITY',
            'price':       session_low,
            'strength':    1.5,
            'candles_ago': lookback - low_idx - 1,
            'touch_count': 1,
        },
    ]


# ─────────────────────────────────────────────
# Liquidity pool aggregation
# ─────────────────────────────────────────────

def find_liquidity_pools(df: pd.DataFrame,
                         swing_highs: Optional[List[Dict]] = None,
                         swing_lows:  Optional[List[Dict]] = None) -> List[Dict]:
    """
    Find all liquidity pools in the DataFrame.

    Combines:
      - Equal highs (buy-side liquidity)
      - Equal lows (sell-side liquidity)
      - Session high/low

    Args:
        df:           OHLCV DataFrame.
        swing_highs:  Pre-computed swing highs (will be computed if None).
        swing_lows:   Pre-computed swing lows  (will be computed if None).

    Returns:
        Combined list of liquidity pool dicts.
    """
    if swing_highs is None or swing_lows is None:
        from market_structure_detector import detect_swing_points
        window = 3
        swing_highs = detect_swing_points(df['high'], window=window, kind='high')
        swing_lows  = detect_swing_points(df['low'],  window=window, kind='low')

    pools: List[Dict] = []
    pools.extend(find_equal_highs(swing_highs))
    pools.extend(find_equal_lows(swing_lows))
    pools.extend(_session_levels(df))

    logger.info(f"   → Liquidity pools found: {len(pools)}")
    return pools


# ─────────────────────────────────────────────
# Liquidity sweeps
# ─────────────────────────────────────────────

def detect_sweeps(df: pd.DataFrame, pools: List[Dict]) -> List[Dict]:
    """
    Detect liquidity sweeps — price wicks into a pool with fast rejection.

    Sweep criteria:
      - Wick extends into (or beyond by <= 0.5%) the pool level.
      - The next 1-2 candles close back inside (opposite direction).

    Args:
        df:    OHLCV DataFrame.
        pools: Liquidity pools from find_liquidity_pools().

    Returns:
        List of sweep dicts (newest first):
        {
          type: 'BSL_SWEEP'|'SSL_SWEEP',
          sweep_price: float,
          rejection_candle_idx: int,
          strength: 0-100,
          candles_ago: int,
        }
    """
    highs  = df['high'].values
    lows   = df['low'].values
    closes = df['close'].values
    n      = len(df)
    tol    = LIQUIDITY['sweep_wick_tolerance']
    rej_max = LIQUIDITY['sweep_rejection_bars']

    sweeps: List[Dict] = []

    for pool in pools:
        price  = pool['price']
        p_type = pool['type']

        for i in range(1, n - rej_max):
            # BSL sweep: wick touches/exceeds BSL, then price rejects down
            if p_type == 'BUY_SIDE_LIQUIDITY':
                if highs[i] >= price * (1 - tol):
                    # Look for rejection in next 1-2 candles
                    for k in range(1, rej_max + 1):
                        if i + k < n and closes[i + k] < price:
                            wick_size = highs[i] - closes[i]
                            # Use fixed 14-candle lookback for consistent ATR approximation
                            lookback_start = max(0, i - 14)
                            atr_approx = float(np.mean(
                                highs[lookback_start:i] - lows[lookback_start:i]
                            ) + 1e-9)
                            strength = min(100, int((wick_size / atr_approx) * 50))
                            sweeps.append({
                                'type':                 'BSL_SWEEP',
                                'sweep_price':          float(highs[i]),
                                'rejection_candle_idx': i + k,
                                'strength':             strength,
                                'candles_ago':          n - 1 - (i + k),
                                'pool_price':           price,
                            })
                            break

            # SSL sweep: wick touches/goes below SSL, then price rejects up
            elif p_type == 'SELL_SIDE_LIQUIDITY':
                if lows[i] <= price * (1 + tol):
                    for k in range(1, rej_max + 1):
                        if i + k < n and closes[i + k] > price:
                            wick_size = closes[i] - lows[i]
                            # Use fixed 14-candle lookback for consistent ATR approximation
                            lookback_start = max(0, i - 14)
                            atr_approx = float(np.mean(
                                highs[lookback_start:i] - lows[lookback_start:i]
                            ) + 1e-9)
                            strength = min(100, int((wick_size / atr_approx) * 50))
                            sweeps.append({
                                'type':                 'SSL_SWEEP',
                                'sweep_price':          float(lows[i]),
                                'rejection_candle_idx': i + k,
                                'strength':             strength,
                                'candles_ago':          n - 1 - (i + k),
                                'pool_price':           price,
                            })
                            break

    sweeps.sort(key=lambda x: x['candles_ago'])
    logger.info(f"   → Liquidity sweeps detected: {len(sweeps)}")
    return sweeps


# ─────────────────────────────────────────────
# Convenience wrapper
# ─────────────────────────────────────────────

def analyze_liquidity(df: pd.DataFrame,
                      swing_highs: Optional[List[Dict]] = None,
                      swing_lows:  Optional[List[Dict]] = None) -> Dict:
    """
    Run the complete liquidity analysis and return a summary dict.

    Returns:
        {
          'pools':   [...],
          'sweeps':  [...],
        }
    """
    pools  = find_liquidity_pools(df, swing_highs=swing_highs, swing_lows=swing_lows)
    sweeps = detect_sweeps(df, pools)

    return {'pools': pools, 'sweeps': sweeps}
