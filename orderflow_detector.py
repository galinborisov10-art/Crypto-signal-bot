"""
ICT Signal Pipeline V2 - Orderflow Detector

Detects institutional orderflow footprints:
  - Order Blocks (OB)
  - Breaker Blocks
  - Fair Value Gaps (FVG)
  - ATR calculation

Author: galinborisov10-art
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional

from ict_config import STRUCTURE, CANDIDATES

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# ATR
# ─────────────────────────────────────────────

def calculate_atr(df: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate Average True Range (ATR) using Wilder's smoothing.

    Args:
        df:     OHLCV DataFrame.
        period: Smoothing period (default 14).

    Returns:
        ATR as a float.  Returns a fallback value if data is insufficient.
    """
    try:
        high  = df['high']
        low   = df['low']
        close = df['close']

        prev_close = close.shift(1)
        tr = pd.concat([
            high - low,
            (high - prev_close).abs(),
            (low  - prev_close).abs(),
        ], axis=1).max(axis=1)

        atr = float(tr.rolling(period, min_periods=period // 2).mean().iloc[-1])
        return atr if not np.isnan(atr) else float((high - low).mean())
    except Exception as exc:
        logger.warning(f"⚠️ calculate_atr error: {exc}")
        return float((df['high'] - df['low']).mean())


# ─────────────────────────────────────────────
# Average body size helper
# ─────────────────────────────────────────────

def _avg_body_size(df: pd.DataFrame, period: int = 20) -> float:
    """Return average candle body size over the last ``period`` candles."""
    bodies = (df['close'] - df['open']).abs()
    return float(bodies.rolling(period, min_periods=5).mean().iloc[-1])


# ─────────────────────────────────────────────
# Order Blocks
# ─────────────────────────────────────────────

def detect_order_blocks(df: pd.DataFrame, atr: Optional[float] = None) -> List[Dict]:
    """
    Detect Order Blocks (OB) — the last opposite-direction candle(s) before
    a significant impulse move.

    An impulse candle has a body >= ``STRUCTURE['impulse_atr_multiplier']``
    times the average body size.

    Args:
        df:  OHLCV DataFrame (minimum 20 candles recommended).
        atr: Pre-calculated ATR (calculated if not provided).

    Returns:
        List of OB dicts (newest first):
        {
          high, low, type: 'BULLISH_OB'|'BEARISH_OB',
          strength: 0-100, candles_ago: int, index: int
        }
    """
    if atr is None:
        atr = calculate_atr(df)

    multiplier  = STRUCTURE['impulse_atr_multiplier']
    avg_body    = _avg_body_size(df)
    impulse_min = avg_body * multiplier

    closes = df['close'].values
    opens  = df['open'].values
    highs  = df['high'].values
    lows   = df['low'].values
    n      = len(df)
    obs: List[Dict] = []

    for i in range(1, n - 1):
        body = abs(closes[i] - opens[i])
        if body < impulse_min:
            continue

        # Bullish impulse → look for bearish OB just before it
        if closes[i] > opens[i]:  # Bullish impulse candle
            ob_idx = i - 1
            if ob_idx >= 0 and closes[ob_idx] < opens[ob_idx]:  # Bearish preceding candle
                strength = min(100, int((body / max(atr, 1e-9)) * 20))
                obs.append({
                    'high':       float(highs[ob_idx]),
                    'low':        float(lows[ob_idx]),
                    'type':       'BULLISH_OB',
                    'strength':   strength,
                    'candles_ago': n - 1 - ob_idx,
                    'index':      ob_idx,
                })

        # Bearish impulse → look for bullish OB just before it
        elif closes[i] < opens[i]:  # Bearish impulse candle
            ob_idx = i - 1
            if ob_idx >= 0 and closes[ob_idx] > opens[ob_idx]:  # Bullish preceding candle
                strength = min(100, int((body / max(atr, 1e-9)) * 20))
                obs.append({
                    'high':       float(highs[ob_idx]),
                    'low':        float(lows[ob_idx]),
                    'type':       'BEARISH_OB',
                    'strength':   strength,
                    'candles_ago': n - 1 - ob_idx,
                    'index':      ob_idx,
                })

    # Remove duplicates keeping highest strength for overlapping candle indices
    seen: Dict[int, Dict] = {}
    for ob in obs:
        idx = ob['index']
        if idx not in seen or ob['strength'] > seen[idx]['strength']:
            seen[idx] = ob

    result = sorted(seen.values(), key=lambda x: x['index'], reverse=True)
    logger.info(f"   → Order blocks detected: {len(result)}")
    return result


# ─────────────────────────────────────────────
# Breaker Blocks
# ─────────────────────────────────────────────

def detect_breaker_blocks(df: pd.DataFrame, order_blocks: List[Dict]) -> List[Dict]:
    """
    Detect Breaker Blocks — OBs that have been violated (price closed beyond
    them) and are now waiting for a retest from the opposite side.

    Args:
        df:           OHLCV DataFrame.
        order_blocks: List from detect_order_blocks().

    Returns:
        List of breaker dicts (newest first):
        {
          high, low, type: 'BREAKER',
          original_ob_type: str, candles_ago: int
        }
    """
    closes = df['close'].values
    n      = len(closes)
    breakers: List[Dict] = []

    for ob in order_blocks:
        ob_idx = ob['index']
        # Only consider OBs that have subsequent candles
        if ob_idx >= n - 1:
            continue

        # Check if price closed beyond the OB after it was formed
        future_closes = closes[ob_idx + 1:]

        if ob['type'] == 'BULLISH_OB':
            # Price closed below OB low → bullish OB becomes bearish breaker
            violated_indices = np.where(future_closes < ob['low'])[0]
            if len(violated_indices) > 0:
                breach_abs = ob_idx + 1 + int(violated_indices[0])
                breakers.append({
                    'high':             ob['high'],
                    'low':              ob['low'],
                    'type':             'BREAKER',
                    'original_ob_type': ob['type'],
                    'candles_ago':      n - 1 - breach_abs,
                    'index':            breach_abs,
                })

        elif ob['type'] == 'BEARISH_OB':
            # Price closed above OB high → bearish OB becomes bullish breaker
            violated_indices = np.where(future_closes > ob['high'])[0]
            if len(violated_indices) > 0:
                breach_abs = ob_idx + 1 + int(violated_indices[0])
                breakers.append({
                    'high':             ob['high'],
                    'low':              ob['low'],
                    'type':             'BREAKER',
                    'original_ob_type': ob['type'],
                    'candles_ago':      n - 1 - breach_abs,
                    'index':            breach_abs,
                })

    breakers.sort(key=lambda x: x['index'], reverse=True)
    logger.info(f"   → Breaker blocks detected: {len(breakers)}")
    return breakers


# ─────────────────────────────────────────────
# Fair Value Gaps
# ─────────────────────────────────────────────

def detect_fvg(df: pd.DataFrame, atr: Optional[float] = None) -> List[Dict]:
    """
    Detect Fair Value Gaps (FVG) — 3-candle imbalance patterns.

    Bullish FVG:  candle[i-1].low  > candle[i+1].high  (gap up)
    Bearish FVG:  candle[i-1].high < candle[i+1].low   (gap down)

    The gap must be >= ``CANDIDATES['fvg_min_size_atr_mult']`` * ATR(14).

    Args:
        df:  OHLCV DataFrame.
        atr: Pre-calculated ATR.

    Returns:
        List of FVG dicts (newest first):
        {top, bottom, type: 'BULLISH_FVG'|'BEARISH_FVG', size, candles_ago, index}
    """
    if atr is None:
        atr = calculate_atr(df)

    min_size   = atr * CANDIDATES['fvg_min_size_atr_mult']
    highs      = df['high'].values
    lows       = df['low'].values
    n          = len(df)
    fvgs: List[Dict] = []

    for i in range(1, n - 1):
        # Bullish FVG: prior low > next high
        if lows[i - 1] > highs[i + 1]:
            gap_size = lows[i - 1] - highs[i + 1]
            if gap_size >= min_size:
                fvgs.append({
                    'top':        float(lows[i - 1]),
                    'bottom':     float(highs[i + 1]),
                    'type':       'BULLISH_FVG',
                    'size':       float(gap_size),
                    'candles_ago': n - 1 - i,
                    'index':      i,
                })

        # Bearish FVG: prior high < next low
        elif highs[i - 1] < lows[i + 1]:
            gap_size = lows[i + 1] - highs[i - 1]
            if gap_size >= min_size:
                fvgs.append({
                    'top':        float(lows[i + 1]),
                    'bottom':     float(highs[i - 1]),
                    'type':       'BEARISH_FVG',
                    'size':       float(gap_size),
                    'candles_ago': n - 1 - i,
                    'index':      i,
                })

    fvgs.sort(key=lambda x: x['index'], reverse=True)
    logger.info(f"   → FVGs detected: {len(fvgs)}")
    return fvgs


# ─────────────────────────────────────────────
# Convenience wrapper
# ─────────────────────────────────────────────

def analyze_orderflow(df: pd.DataFrame) -> Dict:
    """
    Run the complete orderflow analysis and return a summary dict.

    Returns:
        {
          'atr':             float,
          'order_blocks':    [...],
          'breaker_blocks':  [...],
          'fvgs':            [...],
        }
    """
    atr            = calculate_atr(df)
    order_blocks   = detect_order_blocks(df, atr=atr)
    breaker_blocks = detect_breaker_blocks(df, order_blocks)
    fvgs           = detect_fvg(df, atr=atr)

    return {
        'atr':            atr,
        'order_blocks':   order_blocks,
        'breaker_blocks': breaker_blocks,
        'fvgs':           fvgs,
    }
