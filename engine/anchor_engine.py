"""
⚓ ANCHOR ENGINE V2
Selects the key anchor price level for the current setup.

The anchor is the most significant nearby ICT component that price is
expected to react from. Used in STEP 8 of the V2 pipeline.

Anchor candidates (in priority order):
1. Nearest active Order Block
2. Nearest FVG
3. Nearest Liquidity Zone
4. Swing High / Swing Low

Author: galinborisov10-art
Version: 2.0
"""

import logging
from typing import List, Optional, Dict, Any

from models.component import ComponentV2, ComponentType, ComponentPolarity

logger = logging.getLogger(__name__)

_PRIORITY = {
    ComponentType.ORDER_BLOCK: 1,
    ComponentType.BREAKER_BLOCK: 2,
    ComponentType.FAIR_VALUE_GAP: 3,
    ComponentType.LIQUIDITY_ZONE: 4,
    ComponentType.SWING_HIGH: 5,
    ComponentType.SWING_LOW: 5,
}


class AnchorEngine:
    """
    V2 Anchor Selection Engine

    Selects the single best anchor component that defines the trade setup's
    point of interest (POI) for entry.

    Args:
        max_distance_pct: Maximum distance from current price to consider (default 3.0%)
    """

    def __init__(self, max_distance_pct: float = 3.0):
        self.max_distance_pct = max_distance_pct
        logger.info(f"AnchorEngine initialized (max_distance={max_distance_pct}%)")

    def select_anchor(
        self,
        components: List[ComponentV2],
        current_price: float,
        bias: str,
    ) -> Optional[ComponentV2]:
        """
        Select the best anchor component for the current price and bias.

        Args:
            components: All detected active components
            current_price: Latest close price
            bias: HTF bias ('BULLISH' or 'BEARISH')

        Returns:
            The best ComponentV2 anchor, or None if no suitable anchor found
        """
        if not components or current_price <= 0:
            return None

        # Filter: active, aligned with bias, within distance
        candidates = self._filter_candidates(components, current_price, bias)
        if not candidates:
            logger.debug("AnchorEngine: no valid anchor candidates found")
            return None

        # Sort by priority then by distance
        candidates.sort(key=lambda c: (
            _PRIORITY.get(c.component_type, 99),
            self._distance_pct(c, current_price),
        ))

        anchor = candidates[0]
        logger.debug(
            f"AnchorEngine: selected anchor {anchor.component_type.value} "
            f"@ {anchor.price_mid:.4f} (strength={anchor.strength:.1f})"
        )
        return anchor

    def _filter_candidates(
        self,
        components: List[ComponentV2],
        current_price: float,
        bias: str,
    ) -> List[ComponentV2]:
        """Filter components to valid anchor candidates"""
        result = []
        for comp in components:
            if not comp.is_active:
                continue
            # Bias alignment
            if bias == "BULLISH" and comp.polarity != ComponentPolarity.BULLISH:
                continue
            if bias == "BEARISH" and comp.polarity != ComponentPolarity.BEARISH:
                continue
            # Distance check
            dist = self._distance_pct(comp, current_price)
            if dist > self.max_distance_pct:
                continue
            result.append(comp)
        return result

    def _distance_pct(self, comp: ComponentV2, current_price: float) -> float:
        """Calculate percentage distance from current price to component mid"""
        if current_price <= 0:
            return float("inf")
        return abs(comp.price_mid - current_price) / current_price * 100.0

    def get_anchor_info(
        self, anchor: Optional[ComponentV2]
    ) -> Dict[str, Any]:
        """Return a summary dict for the anchor"""
        if anchor is None:
            return {"anchor_found": False}
        return {
            "anchor_found": True,
            "anchor_type": anchor.component_type.value,
            "anchor_polarity": anchor.polarity.value,
            "anchor_price_high": anchor.price_high,
            "anchor_price_low": anchor.price_low,
            "anchor_price_mid": anchor.price_mid,
            "anchor_strength": anchor.strength,
        }
