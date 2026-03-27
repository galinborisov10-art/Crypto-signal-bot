"""
📦 ORDER BLOCK DETECTOR V2
Institutional Order Block detection for the V2 pipeline.

Improvements over V1:
- Modular design - standalone detector, no engine dependency
- Returns ComponentV2 objects for unified interface
- Configurable via constructor parameters
- Clean separation of detection logic

Author: galinborisov10-art
Version: 2.0
"""

import uuid
import logging
import pandas as pd
import numpy as np
from typing import List, Optional, Dict, Any
from datetime import datetime

from models.component import ComponentV2, ComponentType, ComponentPolarity, ComponentStatus

logger = logging.getLogger(__name__)


class OrderBlockDetectorV2:
    """
    V2 Order Block Detector

    Detects institutional order blocks (bullish and bearish) from OHLCV data.
    An order block is the last bearish candle before a bullish move (bullish OB)
    or the last bullish candle before a bearish move (bearish OB).

    Args:
        min_displacement_pct: Minimum price displacement to confirm OB (default 0.3%)
        min_strength: Minimum strength score to keep OB (default 30.0)
        volume_lookback: Candles to use for average volume calculation (default 20)
        max_ob_age: Maximum OB age in candles (default 200)
    """

    def __init__(
        self,
        min_displacement_pct: float = 0.3,
        min_strength: float = 30.0,
        volume_lookback: int = 20,
        max_ob_age: int = 200,
    ):
        self.min_displacement_pct = min_displacement_pct
        self.min_strength = min_strength
        self.volume_lookback = volume_lookback
        self.max_ob_age = max_ob_age
        logger.info(
            "OrderBlockDetectorV2 initialized "
            f"(min_disp={min_displacement_pct}%, min_strength={min_strength})"
        )

    def detect(
        self, df: pd.DataFrame, timeframe: str = "1H"
    ) -> List[ComponentV2]:
        """
        Detect order blocks in OHLCV data.

        Args:
            df: OHLCV DataFrame with columns [open, high, low, close, volume]
            timeframe: Chart timeframe label

        Returns:
            List of ComponentV2 objects representing order blocks
        """
        if df is None or len(df) < 10:
            logger.warning("OrderBlockDetectorV2: insufficient data")
            return []

        components: List[ComponentV2] = []
        avg_volume = df["volume"].rolling(self.volume_lookback).mean()
        current_idx = len(df) - 1

        for i in range(3, current_idx - 1):
            # Bullish OB: bearish candle followed by strong bullish displacement
            bullish = self._check_bullish_ob(df, i, avg_volume)
            if bullish:
                ob = self._build_component(
                    df, i, ComponentPolarity.BULLISH, bullish, timeframe, current_idx
                )
                if ob and ob.strength >= self.min_strength:
                    components.append(ob)

            # Bearish OB: bullish candle followed by strong bearish displacement
            bearish = self._check_bearish_ob(df, i, avg_volume)
            if bearish:
                ob = self._build_component(
                    df, i, ComponentPolarity.BEARISH, bearish, timeframe, current_idx
                )
                if ob and ob.strength >= self.min_strength:
                    components.append(ob)

        # Remove mitigated OBs
        components = self._update_mitigation(components, df)
        logger.debug(f"OrderBlockDetectorV2: detected {len(components)} OBs on {timeframe}")
        return components

    def _check_bullish_ob(
        self, df: pd.DataFrame, i: int, avg_volume: pd.Series
    ) -> Optional[Dict[str, Any]]:
        """Check if candle i is a bullish order block origin"""
        o, h, l, c = (
            df["open"].iloc[i],
            df["high"].iloc[i],
            df["low"].iloc[i],
            df["close"].iloc[i],
        )
        # Must be bearish candle
        if c >= o:
            return None

        # Look ahead for bullish displacement
        displacement = 0.0
        for j in range(i + 1, min(i + 8, len(df))):
            fut_high = df["high"].iloc[j]
            if h > 0:
                displacement = max(displacement, (fut_high - h) / h * 100)
            if displacement >= self.min_displacement_pct:
                vol_ratio = (
                    df["volume"].iloc[i] / avg_volume.iloc[i]
                    if avg_volume.iloc[i] > 0
                    else 1.0
                )
                return {"displacement_pct": displacement, "volume_ratio": vol_ratio}

        return None

    def _check_bearish_ob(
        self, df: pd.DataFrame, i: int, avg_volume: pd.Series
    ) -> Optional[Dict[str, Any]]:
        """Check if candle i is a bearish order block origin"""
        o, h, l, c = (
            df["open"].iloc[i],
            df["high"].iloc[i],
            df["low"].iloc[i],
            df["close"].iloc[i],
        )
        # Must be bullish candle
        if c <= o:
            return None

        # Look ahead for bearish displacement
        displacement = 0.0
        for j in range(i + 1, min(i + 8, len(df))):
            fut_low = df["low"].iloc[j]
            if l > 0:
                displacement = max(displacement, (l - fut_low) / l * 100)
            if displacement >= self.min_displacement_pct:
                vol_ratio = (
                    df["volume"].iloc[i] / avg_volume.iloc[i]
                    if avg_volume.iloc[i] > 0
                    else 1.0
                )
                return {"displacement_pct": displacement, "volume_ratio": vol_ratio}

        return None

    def _build_component(
        self,
        df: pd.DataFrame,
        i: int,
        polarity: ComponentPolarity,
        info: Dict[str, Any],
        timeframe: str,
        current_idx: int,
    ) -> Optional[ComponentV2]:
        """Build a ComponentV2 from detection info"""
        if current_idx - i > self.max_ob_age:
            return None

        price_high = float(df["high"].iloc[i])
        price_low = float(df["low"].iloc[i])
        price_mid = (price_high + price_low) / 2.0

        # Strength: composite of displacement and volume
        displacement_pct = info.get("displacement_pct", 0.0)
        volume_ratio = info.get("volume_ratio", 1.0)
        strength = min(100.0, displacement_pct * 20.0 + (volume_ratio - 1.0) * 15.0)

        ts = df.index[i] if hasattr(df.index[i], "to_pydatetime") else datetime.utcnow()
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()

        return ComponentV2(
            component_id=str(uuid.uuid4()),
            component_type=ComponentType.ORDER_BLOCK,
            polarity=polarity,
            price_high=price_high,
            price_low=price_low,
            price_mid=price_mid,
            strength=strength,
            candle_index=i,
            timestamp=ts,
            timeframe=timeframe,
            status=ComponentStatus.ACTIVE,
            volume_ratio=volume_ratio,
            displacement_pct=displacement_pct,
        )

    def _update_mitigation(
        self, components: List[ComponentV2], df: pd.DataFrame
    ) -> List[ComponentV2]:
        """Mark fully mitigated OBs and remove invalidated ones"""
        current_close = float(df["close"].iloc[-1])
        active = []
        for comp in components:
            if comp.polarity == ComponentPolarity.BULLISH:
                if current_close < comp.price_low:
                    comp.status = ComponentStatus.INVALIDATED
                elif comp.price_low <= current_close <= comp.price_high:
                    comp.touch_count += 1
                    comp.status = ComponentStatus.TESTED
                    active.append(comp)
                else:
                    active.append(comp)
            else:  # BEARISH
                if current_close > comp.price_high:
                    comp.status = ComponentStatus.INVALIDATED
                elif comp.price_low <= current_close <= comp.price_high:
                    comp.touch_count += 1
                    comp.status = ComponentStatus.TESTED
                    active.append(comp)
                else:
                    active.append(comp)
        return active
