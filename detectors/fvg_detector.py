"""
⚡ FAIR VALUE GAP DETECTOR V2
FVG / Imbalance detection for the V2 pipeline.

Improvements over V1:
- Returns ComponentV2 objects for unified interface
- Standalone module with no engine dependency
- Configurable minimum gap size

Author: galinborisov10-art
Version: 2.0
"""

import uuid
import logging
import pandas as pd
from typing import List, Optional
from datetime import datetime

from models.component import ComponentV2, ComponentType, ComponentPolarity, ComponentStatus

logger = logging.getLogger(__name__)


class FVGDetectorV2:
    """
    V2 Fair Value Gap (FVG) Detector

    Detects price imbalances (gaps) using the standard three-candle pattern:
    - Bullish FVG: candle[i-1].high < candle[i+1].low  (gap up)
    - Bearish FVG: candle[i-1].low  > candle[i+1].high (gap down)

    Args:
        min_gap_pct: Minimum gap size as percentage of price (default 0.1%)
        min_strength: Minimum strength score to keep FVG (default 20.0)
        max_fvg_age: Maximum FVG age in candles (default 150)
    """

    def __init__(
        self,
        min_gap_pct: float = 0.1,
        min_strength: float = 20.0,
        max_fvg_age: int = 150,
    ):
        self.min_gap_pct = min_gap_pct
        self.min_strength = min_strength
        self.max_fvg_age = max_fvg_age
        logger.info(
            f"FVGDetectorV2 initialized (min_gap={min_gap_pct}%, min_strength={min_strength})"
        )

    def detect(self, df: pd.DataFrame, timeframe: str = "1H") -> List[ComponentV2]:
        """
        Detect FVGs in OHLCV data.

        Args:
            df: OHLCV DataFrame
            timeframe: Chart timeframe label

        Returns:
            List of ComponentV2 objects representing FVGs
        """
        if df is None or len(df) < 5:
            logger.warning("FVGDetectorV2: insufficient data")
            return []

        components: List[ComponentV2] = []
        current_idx = len(df) - 1

        for i in range(1, current_idx - 1):
            age = current_idx - i
            if age > self.max_fvg_age:
                continue

            fvg = self._check_fvg(df, i, timeframe)
            if fvg and fvg.strength >= self.min_strength:
                components.append(fvg)

        components = self._update_fill_status(components, df)
        logger.debug(f"FVGDetectorV2: detected {len(components)} FVGs on {timeframe}")
        return components

    def _check_fvg(
        self, df: pd.DataFrame, i: int, timeframe: str
    ) -> Optional[ComponentV2]:
        """Check candle i for FVG pattern"""
        prev_high = float(df["high"].iloc[i - 1])
        prev_low = float(df["low"].iloc[i - 1])
        next_high = float(df["high"].iloc[i + 1])
        next_low = float(df["low"].iloc[i + 1])
        mid_close = float(df["close"].iloc[i])

        # Bullish FVG: gap between candle[i-1].high and candle[i+1].low
        if prev_high < next_low:
            gap_size = next_low - prev_high
            gap_pct = (gap_size / prev_high) * 100 if prev_high > 0 else 0
            if gap_pct >= self.min_gap_pct:
                strength = min(100.0, gap_pct * 30.0)
                return self._build_component(
                    df, i, ComponentPolarity.BULLISH,
                    prev_high, next_low, strength, timeframe
                )

        # Bearish FVG: gap between candle[i+1].high and candle[i-1].low
        if next_high < prev_low:
            gap_size = prev_low - next_high
            gap_pct = (gap_size / next_high) * 100 if next_high > 0 else 0
            if gap_pct >= self.min_gap_pct:
                strength = min(100.0, gap_pct * 30.0)
                return self._build_component(
                    df, i, ComponentPolarity.BEARISH,
                    next_high, prev_low, strength, timeframe
                )

        return None

    def _build_component(
        self,
        df: pd.DataFrame,
        i: int,
        polarity: ComponentPolarity,
        price_low: float,
        price_high: float,
        strength: float,
        timeframe: str,
    ) -> ComponentV2:
        """Build a ComponentV2 for an FVG"""
        ts = df.index[i] if hasattr(df.index[i], "to_pydatetime") else datetime.utcnow()
        if hasattr(ts, "to_pydatetime"):
            ts = ts.to_pydatetime()

        return ComponentV2(
            component_id=str(uuid.uuid4()),
            component_type=ComponentType.FAIR_VALUE_GAP,
            polarity=polarity,
            price_high=price_high,
            price_low=price_low,
            price_mid=(price_high + price_low) / 2.0,
            strength=strength,
            candle_index=i,
            timestamp=ts,
            timeframe=timeframe,
            status=ComponentStatus.ACTIVE,
            displacement_pct=(price_high - price_low) / price_low * 100 if price_low > 0 else 0,
        )

    def _update_fill_status(
        self, components: List[ComponentV2], df: pd.DataFrame
    ) -> List[ComponentV2]:
        """Remove fully filled FVGs"""
        current_close = float(df["close"].iloc[-1])
        active = []
        for comp in components:
            if comp.polarity == ComponentPolarity.BULLISH:
                # FVG invalidated if price drops below it
                if current_close < comp.price_low:
                    comp.status = ComponentStatus.INVALIDATED
                elif comp.contains_price(current_close):
                    comp.touch_count += 1
                    comp.status = ComponentStatus.TESTED
                    active.append(comp)
                else:
                    active.append(comp)
            else:
                # Bearish FVG invalidated if price rises above it
                if current_close > comp.price_high:
                    comp.status = ComponentStatus.INVALIDATED
                elif comp.contains_price(current_close):
                    comp.touch_count += 1
                    comp.status = ComponentStatus.TESTED
                    active.append(comp)
                else:
                    active.append(comp)
        return active
