"""
🎯 ENTRY ENGINE V2
Calculates optimal entry price and entry zone from the anchor component.

Corresponds to STEP 9 of the V2 signal pipeline.
Uses the anchor's zone and current price to determine:
- Optimal entry price (OTE - Optimal Trade Entry)
- Entry zone high/low boundaries
- Entry type (limit / market / stop)

Author: galinborisov10-art
Version: 2.0
"""

import logging
from typing import Optional, Dict, Any

from models.component import Component, ComponentPolarity

logger = logging.getLogger(__name__)

# Fibonacci OTE retracement levels (standard ICT)
_OTE_LOW = 0.618
_OTE_HIGH = 0.786


class EntryEngine:
    """
    V2 Entry Calculation Engine

    Determines entry price and entry zone using ICT OTE methodology:
    - Bullish: buy in the 61.8-78.6% retracement of the impulse leg
    - Bearish: sell in the 61.8-78.6% retracement of the impulse leg

    Args:
        ote_low: Lower Fibonacci level for OTE (default 0.618)
        ote_high: Upper Fibonacci level for OTE (default 0.786)
        max_entry_distance_pct: Maximum allowed distance from current price to entry (default 2.0%)
    """

    def __init__(
        self,
        ote_low: float = _OTE_LOW,
        ote_high: float = _OTE_HIGH,
        max_entry_distance_pct: float = 2.0,
    ):
        self.ote_low = ote_low
        self.ote_high = ote_high
        self.max_entry_distance_pct = max_entry_distance_pct
        logger.info(
            f"EntryEngine initialized (OTE {ote_low:.3f}-{ote_high:.3f}, "
            f"max_dist={max_entry_distance_pct}%)"
        )

    def calculate_entry(
        self,
        anchor: Component,
        current_price: float,
        bias: str,
        swing_high: Optional[float] = None,
        swing_low: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate entry parameters from the anchor component.

        Args:
            anchor: The selected anchor Component
            current_price: Latest close price
            bias: 'BULLISH' or 'BEARISH'
            swing_high: Recent swing high for OTE calculation
            swing_low: Recent swing low for OTE calculation

        Returns:
            dict with keys:
                entry_price (float)
                entry_zone_low (float)
                entry_zone_high (float)
                entry_type (str): 'LIMIT' | 'MARKET'
                ote_level (float): OTE midpoint price
            or None if no valid entry found
        """
        if anchor is None or current_price <= 0:
            return None

        if bias == "BULLISH":
            return self._bullish_entry(anchor, current_price, swing_high, swing_low)
        elif bias == "BEARISH":
            return self._bearish_entry(anchor, current_price, swing_high, swing_low)
        return None

    def _bullish_entry(
        self,
        anchor: Component,
        current_price: float,
        swing_high: Optional[float],
        swing_low: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """Calculate bullish entry in OTE zone or from anchor bottom"""
        # Entry zone = anchor's low area (buy at support)
        entry_zone_low = anchor.price_low
        entry_zone_high = anchor.price_mid

        # Refine with OTE if swing points available
        if swing_high and swing_low and swing_high > swing_low:
            leg = swing_high - swing_low
            ote_low_price = swing_high - leg * self.ote_high
            ote_high_price = swing_high - leg * self.ote_low
            # Use OTE if it overlaps with anchor zone
            if ote_low_price <= anchor.price_high and ote_high_price >= anchor.price_low:
                entry_zone_low = max(entry_zone_low, ote_low_price)
                entry_zone_high = min(entry_zone_high, ote_high_price)

        entry_price = (entry_zone_low + entry_zone_high) / 2.0

        # Validate distance
        dist_pct = abs(current_price - entry_price) / current_price * 100.0
        if dist_pct > self.max_entry_distance_pct and current_price > entry_price:
            logger.debug(f"EntryEngine: bullish entry too far ({dist_pct:.2f}%)")
            return None

        entry_type = "MARKET" if current_price <= entry_zone_high else "LIMIT"
        ote_level = (entry_zone_low + entry_zone_high) / 2.0

        logger.debug(
            f"EntryEngine: BULLISH entry @ {entry_price:.4f} "
            f"(zone {entry_zone_low:.4f}-{entry_zone_high:.4f}, type={entry_type})"
        )
        return {
            "entry_price": entry_price,
            "entry_zone_low": entry_zone_low,
            "entry_zone_high": entry_zone_high,
            "entry_type": entry_type,
            "ote_level": ote_level,
        }

    def _bearish_entry(
        self,
        anchor: Component,
        current_price: float,
        swing_high: Optional[float],
        swing_low: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """Calculate bearish entry in OTE zone or from anchor top"""
        entry_zone_low = anchor.price_mid
        entry_zone_high = anchor.price_high

        if swing_high and swing_low and swing_high > swing_low:
            leg = swing_high - swing_low
            ote_low_price = swing_low + leg * self.ote_low
            ote_high_price = swing_low + leg * self.ote_high
            if ote_low_price <= anchor.price_high and ote_high_price >= anchor.price_low:
                entry_zone_low = max(entry_zone_low, ote_low_price)
                entry_zone_high = min(entry_zone_high, ote_high_price)

        entry_price = (entry_zone_low + entry_zone_high) / 2.0

        dist_pct = abs(current_price - entry_price) / current_price * 100.0
        if dist_pct > self.max_entry_distance_pct and current_price < entry_price:
            logger.debug(f"EntryEngine: bearish entry too far ({dist_pct:.2f}%)")
            return None

        entry_type = "MARKET" if current_price >= entry_zone_low else "LIMIT"
        ote_level = (entry_zone_low + entry_zone_high) / 2.0

        logger.debug(
            f"EntryEngine: BEARISH entry @ {entry_price:.4f} "
            f"(zone {entry_zone_low:.4f}-{entry_zone_high:.4f}, type={entry_type})"
        )
        return {
            "entry_price": entry_price,
            "entry_zone_low": entry_zone_low,
            "entry_zone_high": entry_zone_high,
            "entry_type": entry_type,
            "ote_level": ote_level,
        }
