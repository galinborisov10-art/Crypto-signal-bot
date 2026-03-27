"""
🔀 BREAKER BLOCK DETECTOR V2
Detects breaker blocks (breached order blocks with flipped polarity) for V2 pipeline.

A breaker block is formed when price breaks through an order block, flipping
the zone from support to resistance (or vice versa).

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


class BreakerDetectorV2:
    """
    V2 Breaker Block Detector

    Takes a list of order block ComponentV2 objects (from OrderBlockDetectorV2)
    and identifies which ones have been breached, converting them to breaker blocks
    with flipped polarity.

    Args:
        breach_threshold_pct: % beyond OB boundary to confirm breach (default 0.1%)
        strength_retention: Fraction of OB strength retained in breaker (default 0.75)
        min_strength: Minimum strength for a breaker block (default 25.0)
    """

    def __init__(
        self,
        breach_threshold_pct: float = 0.1,
        strength_retention: float = 0.75,
        min_strength: float = 25.0,
    ):
        self.breach_threshold_pct = breach_threshold_pct
        self.strength_retention = strength_retention
        self.min_strength = min_strength
        logger.info(
            f"BreakerDetectorV2 initialized "
            f"(breach={breach_threshold_pct}%, retention={strength_retention})"
        )

    def detect(
        self,
        df: pd.DataFrame,
        order_blocks: List[ComponentV2],
        timeframe: str = "1H",
    ) -> List[ComponentV2]:
        """
        Detect breaker blocks from existing order blocks.

        Args:
            df: OHLCV DataFrame
            order_blocks: List of OB ComponentV2 objects from OrderBlockDetectorV2
            timeframe: Chart timeframe label

        Returns:
            List of ComponentV2 objects representing breaker blocks
        """
        if not order_blocks or df is None or len(df) < 5:
            return []

        breakers: List[ComponentV2] = []

        for ob in order_blocks:
            if ob.component_type != ComponentType.ORDER_BLOCK:
                continue

            breach = self._find_breach(df, ob)
            if breach is None:
                continue

            breaker = self._build_breaker(ob, breach, timeframe)
            if breaker and breaker.strength >= self.min_strength:
                breakers.append(breaker)

        logger.debug(
            f"BreakerDetectorV2: {len(breakers)} breaker blocks detected on {timeframe}"
        )
        return breakers

    def _find_breach(
        self, df: pd.DataFrame, ob: ComponentV2
    ) -> Optional[dict]:
        """
        Check if an order block has been breached.

        Returns dict with breach info or None.
        """
        threshold = self.breach_threshold_pct / 100.0
        start = ob.candle_index + 1

        if ob.polarity == ComponentPolarity.BULLISH:
            # Bullish OB breached when price closes below the bottom
            breach_level = ob.price_low * (1.0 - threshold)
            for i in range(start, len(df)):
                if float(df["close"].iloc[i]) < breach_level:
                    return {
                        "breach_index": i,
                        "breach_price": float(df["close"].iloc[i]),
                        "new_polarity": ComponentPolarity.BEARISH,
                    }
        else:
            # Bearish OB breached when price closes above the top
            breach_level = ob.price_high * (1.0 + threshold)
            for i in range(start, len(df)):
                if float(df["close"].iloc[i]) > breach_level:
                    return {
                        "breach_index": i,
                        "breach_price": float(df["close"].iloc[i]),
                        "new_polarity": ComponentPolarity.BULLISH,
                    }

        return None

    def _build_breaker(
        self, ob: ComponentV2, breach: dict, timeframe: str
    ) -> ComponentV2:
        """Build a breaker block ComponentV2 from a breached OB"""
        new_polarity: ComponentPolarity = breach["new_polarity"]
        strength = ob.strength * self.strength_retention

        return ComponentV2(
            component_id=str(uuid.uuid4()),
            component_type=ComponentType.BREAKER_BLOCK,
            polarity=new_polarity,
            price_high=ob.price_high,
            price_low=ob.price_low,
            price_mid=ob.price_mid,
            strength=strength,
            candle_index=breach["breach_index"],
            timestamp=ob.timestamp,
            timeframe=timeframe,
            status=ComponentStatus.ACTIVE,
            volume_ratio=ob.volume_ratio,
            displacement_pct=ob.displacement_pct,
            metadata={
                "original_ob_id": ob.component_id,
                "breach_price": breach["breach_price"],
                "original_polarity": ob.polarity.value,
            },
        )
