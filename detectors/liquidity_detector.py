"""
💧 LIQUIDITY DETECTOR V2
Buy-Side and Sell-Side liquidity zone detection for the V2 pipeline.

Detects areas where stop-loss clusters exist (liquidity pools):
- BSL (Buy-Side Liquidity): Above equal highs / swing highs
- SSL (Sell-Side Liquidity): Below equal lows / swing lows

Author: galinborisov10-art
Version: 2.0
"""

import uuid
import logging
import pandas as pd
import numpy as np
from typing import List, Optional
from datetime import datetime

from models.component import Component, ComponentType, ComponentPolarity, ComponentStatus

logger = logging.getLogger(__name__)

_SWING_LOOKBACK = 5   # candles each side to qualify as swing high/low


class LiquidityDetectorV2:
    """
    V2 Liquidity Zone Detector

    Identifies liquidity pools by detecting:
    1. Equal highs / swing highs  → BSL zones (above)
    2. Equal lows / swing lows    → SSL zones (below)

    Args:
        equal_level_tolerance_pct: % tolerance for "equal" levels (default 0.15%)
        min_touches: Minimum touches to form a liquidity zone (default 2)
        min_strength: Minimum strength score (default 25.0)
        swing_lookback: Candles each side for swing detection (default 5)
        max_zone_age: Maximum zone age in candles (default 200)
    """

    def __init__(
        self,
        equal_level_tolerance_pct: float = 0.15,
        min_touches: int = 2,
        min_strength: float = 25.0,
        swing_lookback: int = _SWING_LOOKBACK,
        max_zone_age: int = 200,
    ):
        self.tolerance_pct = equal_level_tolerance_pct
        self.min_touches = min_touches
        self.min_strength = min_strength
        self.swing_lookback = swing_lookback
        self.max_zone_age = max_zone_age
        logger.info(
            f"LiquidityDetectorV2 initialized "
            f"(tolerance={equal_level_tolerance_pct}%, min_touches={min_touches})"
        )

    def detect(self, df: pd.DataFrame, timeframe: str = "1H") -> List[Component]:
        """
        Detect liquidity zones in OHLCV data.

        Args:
            df: OHLCV DataFrame
            timeframe: Chart timeframe label

        Returns:
            List of Component objects representing liquidity zones
        """
        if df is None or len(df) < 20:
            logger.warning("LiquidityDetectorV2: insufficient data")
            return []

        bsl_zones = self._detect_bsl(df, timeframe)
        ssl_zones = self._detect_ssl(df, timeframe)
        all_zones = bsl_zones + ssl_zones

        active = [z for z in all_zones if z.strength >= self.min_strength]
        logger.debug(
            f"LiquidityDetectorV2: {len(bsl_zones)} BSL + {len(ssl_zones)} SSL zones on {timeframe}"
        )
        return active

    def _detect_bsl(self, df: pd.DataFrame, timeframe: str) -> List[Component]:
        """Detect Buy-Side Liquidity zones (above swing highs / equal highs)"""
        zones: List[Component] = []
        lb = self.swing_lookback
        current_idx = len(df) - 1

        for i in range(lb, current_idx - lb):
            if current_idx - i > self.max_zone_age:
                continue
            high_i = float(df["high"].iloc[i])

            # Qualify as swing high
            if not all(df["high"].iloc[i] >= df["high"].iloc[i - lb: i]) and \
               not all(df["high"].iloc[i] >= df["high"].iloc[i + 1: i + lb + 1]):
                continue

            # Count how many other highs are at the same level
            tolerance = high_i * (self.tolerance_pct / 100.0)
            touches = sum(
                1 for j in range(max(0, i - 50), min(len(df), i + 50))
                if j != i and abs(float(df["high"].iloc[j]) - high_i) <= tolerance
            )

            if touches >= self.min_touches - 1:
                strength = min(100.0, 30.0 + touches * 15.0)
                zone = self._build_zone(
                    df, i, ComponentPolarity.BULLISH, high_i, timeframe, strength
                )
                if zone:
                    zones.append(zone)

        return zones

    def _detect_ssl(self, df: pd.DataFrame, timeframe: str) -> List[Component]:
        """Detect Sell-Side Liquidity zones (below swing lows / equal lows)"""
        zones: List[Component] = []
        lb = self.swing_lookback
        current_idx = len(df) - 1

        for i in range(lb, current_idx - lb):
            if current_idx - i > self.max_zone_age:
                continue
            low_i = float(df["low"].iloc[i])

            # Qualify as swing low
            if not all(df["low"].iloc[i] <= df["low"].iloc[i - lb: i]) and \
               not all(df["low"].iloc[i] <= df["low"].iloc[i + 1: i + lb + 1]):
                continue

            tolerance = low_i * (self.tolerance_pct / 100.0)
            touches = sum(
                1 for j in range(max(0, i - 50), min(len(df), i + 50))
                if j != i and abs(float(df["low"].iloc[j]) - low_i) <= tolerance
            )

            if touches >= self.min_touches - 1:
                strength = min(100.0, 30.0 + touches * 15.0)
                zone = self._build_zone(
                    df, i, ComponentPolarity.BEARISH, low_i, timeframe, strength
                )
                if zone:
                    zones.append(zone)

        return zones

    def _build_zone(
        self,
        df: pd.DataFrame,
        i: int,
        polarity: ComponentPolarity,
        price_level: float,
        timeframe: str,
        strength: float,
    ) -> Optional[Component]:
        """Build a Component for a liquidity zone"""
        tolerance = price_level * (self.tolerance_pct / 100.0)
        price_high = price_level + tolerance
        price_low = price_level - tolerance

        ts = df.index[i] if hasattr(df.index[i], "to_pydatetime") else datetime.utcnow()
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()

        # Check if zone is already swept
        current_close = float(df["close"].iloc[-1])
        status = ComponentStatus.ACTIVE
        if polarity == ComponentPolarity.BULLISH and current_close > price_high:
            status = ComponentStatus.MITIGATED
        elif polarity == ComponentPolarity.BEARISH and current_close < price_low:
            status = ComponentStatus.MITIGATED

        return Component(
            component_id=str(uuid.uuid4()),
            component_type=ComponentType.LIQUIDITY_ZONE,
            polarity=polarity,
            price_high=price_high,
            price_low=price_low,
            price_mid=price_level,
            strength=strength,
            candle_index=i,
            timestamp=ts,
            timeframe=timeframe,
            status=status,
        )
