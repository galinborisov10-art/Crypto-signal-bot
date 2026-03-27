"""
📡 HTF BIAS ENGINE V2
Determines the Higher Timeframe (HTF) directional bias.

Used in STEP 1 of the V2 pipeline to establish macro market direction
before any trade setups are evaluated.

Bias categories:
- BULLISH: Clear uptrend structure
- BEARISH: Clear downtrend structure
- RANGING: No clear direction (no trade)

Author: galinborisov10-art
Version: 2.0
"""

import logging
import pandas as pd
import numpy as np
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

_BIAS_BULLISH = "BULLISH"
_BIAS_BEARISH = "BEARISH"
_BIAS_RANGING = "RANGING"


class HTFBiasEngine:
    """
    V2 Higher Timeframe Bias Engine

    Determines market bias using swing structure analysis:
    - Higher Highs + Higher Lows → BULLISH
    - Lower Highs + Lower Lows  → BEARISH
    - Mixed / unclear           → RANGING

    Args:
        swing_lookback: Candles each side to confirm swing point (default 5)
        min_swing_count: Minimum swings needed for bias (default 3)
        ema_fast: Fast EMA period for trend confirmation (default 20)
        ema_slow: Slow EMA period for trend confirmation (default 50)
    """

    def __init__(
        self,
        swing_lookback: int = 5,
        min_swing_count: int = 3,
        ema_fast: int = 20,
        ema_slow: int = 50,
    ):
        self.swing_lookback = swing_lookback
        self.min_swing_count = min_swing_count
        self.ema_fast = ema_fast
        self.ema_slow = ema_slow
        logger.info("HTFBiasEngine initialized")

    def determine_bias(
        self, df: pd.DataFrame, symbol: str = "", timeframe: str = "4H"
    ) -> Dict[str, Any]:
        """
        Determine the HTF bias from OHLCV data.

        Args:
            df: OHLCV DataFrame (should be HTF data, e.g. 4H or Daily)
            symbol: Trading pair for logging
            timeframe: Timeframe label

        Returns:
            dict with keys:
                bias (str): 'BULLISH' | 'BEARISH' | 'RANGING'
                confidence (float): 0-100
                swing_highs (list): Detected swing high prices
                swing_lows (list): Detected swing low prices
                ema_aligned (bool): Whether EMAs confirm bias
        """
        if df is None or len(df) < max(self.ema_slow + 5, 20):
            logger.warning(f"HTFBiasEngine: insufficient data for {symbol} {timeframe}")
            return self._ranging_result()

        swing_highs = self._find_swing_highs(df)
        swing_lows = self._find_swing_lows(df)
        ema_aligned, ema_direction = self._check_ema(df)

        bias = self._classify_bias(swing_highs, swing_lows, ema_direction)
        confidence = self._calculate_confidence(
            swing_highs, swing_lows, ema_aligned, bias
        )

        logger.debug(
            f"HTFBiasEngine: {symbol} {timeframe} → {bias} "
            f"(conf={confidence:.1f}%, ema_aligned={ema_aligned})"
        )
        return {
            "bias": bias,
            "confidence": confidence,
            "swing_highs": [float(p) for p in swing_highs],
            "swing_lows": [float(p) for p in swing_lows],
            "ema_aligned": ema_aligned,
        }

    def _find_swing_highs(self, df: pd.DataFrame) -> list:
        """Find swing high price levels"""
        lb = self.swing_lookback
        highs = []
        for i in range(lb, len(df) - lb):
            if df["high"].iloc[i] == df["high"].iloc[i - lb: i + lb + 1].max():
                highs.append(float(df["high"].iloc[i]))
        return highs[-self.min_swing_count * 2:]

    def _find_swing_lows(self, df: pd.DataFrame) -> list:
        """Find swing low price levels"""
        lb = self.swing_lookback
        lows = []
        for i in range(lb, len(df) - lb):
            if df["low"].iloc[i] == df["low"].iloc[i - lb: i + lb + 1].min():
                lows.append(float(df["low"].iloc[i]))
        return lows[-self.min_swing_count * 2:]

    def _check_ema(self, df: pd.DataFrame):
        """Check if fast EMA is above/below slow EMA"""
        try:
            ema_f = df["close"].ewm(span=self.ema_fast, adjust=False).mean()
            ema_s = df["close"].ewm(span=self.ema_slow, adjust=False).mean()
            last_f = float(ema_f.iloc[-1])
            last_s = float(ema_s.iloc[-1])
            if last_f > last_s:
                return True, _BIAS_BULLISH
            elif last_f < last_s:
                return True, _BIAS_BEARISH
            else:
                return False, _BIAS_RANGING
        except Exception:
            return False, _BIAS_RANGING

    def _classify_bias(
        self, swing_highs: list, swing_lows: list, ema_direction: str
    ) -> str:
        """Classify HTF bias from swing structure"""
        if len(swing_highs) < 2 or len(swing_lows) < 2:
            return ema_direction if ema_direction != _BIAS_RANGING else _BIAS_RANGING

        hh = swing_highs[-1] > swing_highs[-2]  # Higher High
        hl = swing_lows[-1] > swing_lows[-2]    # Higher Low
        lh = swing_highs[-1] < swing_highs[-2]  # Lower High
        ll = swing_lows[-1] < swing_lows[-2]    # Lower Low

        if hh and hl:
            return _BIAS_BULLISH
        if lh and ll:
            return _BIAS_BEARISH
        # Mixed structure
        if ema_direction in (_BIAS_BULLISH, _BIAS_BEARISH):
            return ema_direction
        return _BIAS_RANGING

    def _calculate_confidence(
        self,
        swing_highs: list,
        swing_lows: list,
        ema_aligned: bool,
        bias: str,
    ) -> float:
        """Estimate confidence in the bias (0-100)"""
        score = 40.0
        if ema_aligned:
            score += 25.0
        if len(swing_highs) >= 3 and len(swing_lows) >= 3:
            score += 20.0
        if bias != _BIAS_RANGING:
            score += 15.0
        return min(100.0, score)

    def _ranging_result(self) -> Dict[str, Any]:
        return {
            "bias": _BIAS_RANGING,
            "confidence": 0.0,
            "swing_highs": [],
            "swing_lows": [],
            "ema_aligned": False,
        }
