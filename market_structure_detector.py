"""
ICT Signal Pipeline V2 - Market Structure Detector

Detects Higher Timeframe (HTF) bias, swing points, Break of Structure (BOS),
and Change of Character (CHoCH) from OHLCV DataFrames.

Author: galinborisov10-art
"""

import logging
import numpy as np
import pandas as pd
from typing import List, Dict, Optional

from ict_config import STRUCTURE

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Swing point detection
# ─────────────────────────────────────────────

def detect_swing_points(series: pd.Series, window: int = 3, kind: str = 'high') -> List[Dict]:
    """
    Detect swing highs or swing lows in a price series.

    A swing high is a candle whose value is strictly greater than the
    ``window`` candles on each side.  A swing low is the mirror image.

    Args:
        series: Price series (e.g. df['high'] or df['low']).
        window: Number of candles on each side to compare (default 3).
        kind:   'high' for swing highs, 'low' for swing lows.

    Returns:
        List of dicts: {'index': int, 'price': float, 'candles_ago': int}
        Most-recent swing first.
    """
    values = series.values
    n = len(values)
    swings: List[Dict] = []

    for i in range(window, n - window):
        left  = values[i - window: i]
        right = values[i + 1: i + window + 1]
        val   = values[i]

        if kind == 'high':
            if val > left.max() and val > right.max():
                swings.append({'index': i, 'price': float(val), 'candles_ago': n - 1 - i})
        else:  # 'low'
            if val < left.min() and val < right.min():
                swings.append({'index': i, 'price': float(val), 'candles_ago': n - 1 - i})

    # Most-recent first
    swings.sort(key=lambda x: x['index'], reverse=True)
    return swings


# ─────────────────────────────────────────────
# HTF bias
# ─────────────────────────────────────────────

def detect_htf_bias(df: pd.DataFrame) -> str:
    """
    Determine higher timeframe trend direction from OHLCV data.

    Algorithm:
    1. Detect swing highs and swing lows (3-candle window).
    2. Check last ``STRUCTURE['swing_lookback']`` swings for HH/HL or LH/LL.
    3. Use 20/50/200 SMA confluence as secondary confirmation.

    Args:
        df: OHLCV DataFrame (columns: open, high, low, close, volume).

    Returns:
        'BULLISH', 'BEARISH', or 'NEUTRAL'
    """
    try:
        window   = STRUCTURE['swing_window']
        lookback = STRUCTURE['swing_lookback']

        swing_highs = detect_swing_points(df['high'], window=window, kind='high')
        swing_lows  = detect_swing_points(df['low'],  window=window, kind='low')

        bias_score = 0  # positive = bullish, negative = bearish

        # --- Swing pattern check ---
        recent_highs = [s['price'] for s in swing_highs[:lookback]]
        recent_lows  = [s['price'] for s in swing_lows[:lookback]]

        if len(recent_highs) >= 2:
            if all(recent_highs[i] > recent_highs[i + 1] for i in range(len(recent_highs) - 1)):
                bias_score += 2  # Higher highs
            elif all(recent_highs[i] < recent_highs[i + 1] for i in range(len(recent_highs) - 1)):
                bias_score -= 2  # Lower highs

        if len(recent_lows) >= 2:
            if all(recent_lows[i] > recent_lows[i + 1] for i in range(len(recent_lows) - 1)):
                bias_score += 2  # Higher lows
            elif all(recent_lows[i] < recent_lows[i + 1] for i in range(len(recent_lows) - 1)):
                bias_score -= 2  # Lower lows

        # --- SMA confluence ---
        close = df['close']
        if len(close) >= 200:
            sma20  = close.rolling(20).mean().iloc[-1]
            sma50  = close.rolling(50).mean().iloc[-1]
            sma200 = close.rolling(200).mean().iloc[-1]
            current = float(close.iloc[-1])

            if current > sma20 > sma50 > sma200:
                bias_score += 1
            elif current < sma20 < sma50 < sma200:
                bias_score -= 1
            elif current > sma50 > sma200:
                bias_score += 0.5
            elif current < sma50 < sma200:
                bias_score -= 0.5

        if bias_score >= 2:
            bias = 'BULLISH'
        elif bias_score <= -2:
            bias = 'BEARISH'
        else:
            bias = 'NEUTRAL'

        logger.info(f"   → HTF Bias: {bias} (score={bias_score:.1f})")
        return bias

    except Exception as exc:
        logger.warning(f"⚠️ detect_htf_bias error: {exc}")
        return 'NEUTRAL'


# ─────────────────────────────────────────────
# Break of Structure
# ─────────────────────────────────────────────

def detect_bos(df: pd.DataFrame, swing_highs: List[Dict], swing_lows: List[Dict],
               htf_bias: str) -> Optional[Dict]:
    """
    Detect the most recent Break of Structure (BOS).

    Bullish BOS:  latest close above a recent swing high.
    Bearish BOS:  latest close below a recent swing low.

    Args:
        df:           OHLCV DataFrame.
        swing_highs:  List from detect_swing_points (kind='high').
        swing_lows:   List from detect_swing_points (kind='low').
        htf_bias:     'BULLISH', 'BEARISH', or 'NEUTRAL'.

    Returns:
        Dict or None:
        {type: 'BOS', level: float, candles_ago: int, direction: 'BULLISH'|'BEARISH'}
    """
    try:
        close = df['close']
        current_close = float(close.iloc[-1])

        # Bullish BOS: close above previous swing high
        if htf_bias != 'BEARISH' and swing_highs:
            for sh in swing_highs[:5]:
                if current_close > sh['price'] and sh['candles_ago'] > 0:
                    return {
                        'type':       'BOS',
                        'level':      sh['price'],
                        'candles_ago': sh['candles_ago'],
                        'direction':  'BULLISH',
                    }

        # Bearish BOS: close below previous swing low
        if htf_bias != 'BULLISH' and swing_lows:
            for sl in swing_lows[:5]:
                if current_close < sl['price'] and sl['candles_ago'] > 0:
                    return {
                        'type':       'BOS',
                        'level':      sl['price'],
                        'candles_ago': sl['candles_ago'],
                        'direction':  'BEARISH',
                    }

        return None

    except Exception as exc:
        logger.warning(f"⚠️ detect_bos error: {exc}")
        return None


# ─────────────────────────────────────────────
# Change of Character
# ─────────────────────────────────────────────

def detect_choch(df: pd.DataFrame, swing_highs: List[Dict], swing_lows: List[Dict],
                 htf_bias: str) -> Optional[Dict]:
    """
    Detect a Change of Character (CHoCH) — structure break against current bias.

    Bullish CHoCH (after bearish bias): close breaks above recent swing high.
    Bearish CHoCH (after bullish bias): close breaks below recent swing low.

    Args:
        df:           OHLCV DataFrame.
        swing_highs:  List from detect_swing_points (kind='high').
        swing_lows:   List from detect_swing_points (kind='low').
        htf_bias:     Current HTF bias.

    Returns:
        Dict or None:
        {type: 'CHoCH', level: float, candles_ago: int, direction: 'BULLISH'|'BEARISH'}
    """
    try:
        current_close = float(df['close'].iloc[-1])

        # Bearish bias → bullish CHoCH
        if htf_bias == 'BEARISH' and swing_highs:
            for sh in swing_highs[:5]:
                if current_close > sh['price'] and sh['candles_ago'] > 0:
                    return {
                        'type':       'CHoCH',
                        'level':      sh['price'],
                        'candles_ago': sh['candles_ago'],
                        'direction':  'BULLISH',
                    }

        # Bullish bias → bearish CHoCH
        if htf_bias == 'BULLISH' and swing_lows:
            for sl in swing_lows[:5]:
                if current_close < sl['price'] and sl['candles_ago'] > 0:
                    return {
                        'type':       'CHoCH',
                        'level':      sl['price'],
                        'candles_ago': sl['candles_ago'],
                        'direction':  'BEARISH',
                    }

        return None

    except Exception as exc:
        logger.warning(f"⚠️ detect_choch error: {exc}")
        return None


# ─────────────────────────────────────────────
# Convenience wrapper
# ─────────────────────────────────────────────

def analyze_market_structure(df: pd.DataFrame) -> Dict:
    """
    Run the complete market structure analysis and return a summary dict.

    Returns:
        {
          'htf_bias':    'BULLISH'|'BEARISH'|'NEUTRAL',
          'swing_highs': [...],
          'swing_lows':  [...],
          'bos':         dict or None,
          'choch':       dict or None,
        }
    """
    window = STRUCTURE['swing_window']

    swing_highs = detect_swing_points(df['high'], window=window, kind='high')
    swing_lows  = detect_swing_points(df['low'],  window=window, kind='low')

    htf_bias = detect_htf_bias(df)

    bos   = detect_bos(df, swing_highs, swing_lows, htf_bias)
    choch = detect_choch(df, swing_highs, swing_lows, htf_bias)

    logger.info(f"   → BOS: {bos}")
    logger.info(f"   → CHoCH: {choch}")

    return {
        'htf_bias':    htf_bias,
        'swing_highs': swing_highs,
        'swing_lows':  swing_lows,
        'bos':         bos,
        'choch':       choch,
    }
