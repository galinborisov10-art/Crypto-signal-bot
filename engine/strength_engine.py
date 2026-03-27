"""
💪 STRENGTH ENGINE V2
Scores each ICT component and applies confluence weighting.

Corresponds to STEP 7 of the V2 signal pipeline.
Updates component.strength and component.confluence_score based on:
- Raw detector strength
- Overlap with other components (multi-confluence bonus)
- Proximity to current price
- Touch / retest history

Author: galinborisov10-art
Version: 2.0
"""

import logging
from typing import List, Dict, Any

from models.component import Component, ComponentType, ComponentPolarity

logger = logging.getLogger(__name__)

# Weights by component type
_TYPE_WEIGHTS: Dict[ComponentType, float] = {
    ComponentType.ORDER_BLOCK: 1.0,
    ComponentType.BREAKER_BLOCK: 1.1,
    ComponentType.FAIR_VALUE_GAP: 0.8,
    ComponentType.LIQUIDITY_ZONE: 0.9,
    ComponentType.SWING_HIGH: 0.6,
    ComponentType.SWING_LOW: 0.6,
    ComponentType.MARKET_STRUCTURE_SHIFT: 1.2,
    ComponentType.CHANGE_OF_CHARACTER: 1.2,
    ComponentType.OPTIMAL_TRADE_ENTRY: 1.3,
    ComponentType.PREMIUM_DISCOUNT: 0.7,
}


class StrengthEngine:
    """
    V2 Component Strength Scoring Engine

    Re-scores all components after detection to incorporate:
    1. Type-based weight multiplier
    2. Confluence bonus when multiple components overlap
    3. Proximity bonus (closer to current price = stronger signal)
    4. Retest bonus (tested zones are more proven)

    Args:
        confluence_bonus: Score bonus per overlapping component (default 8.0)
        proximity_weight: Weight for proximity to current price (default 0.3)
        retest_bonus: Bonus per retest/touch (default 5.0)
        max_score: Cap for final score (default 100.0)
    """

    def __init__(
        self,
        confluence_bonus: float = 8.0,
        proximity_weight: float = 0.3,
        retest_bonus: float = 5.0,
        max_score: float = 100.0,
    ):
        self.confluence_bonus = confluence_bonus
        self.proximity_weight = proximity_weight
        self.retest_bonus = retest_bonus
        self.max_score = max_score
        logger.info("StrengthEngine initialized")

    def score_components(
        self,
        components: List[Component],
        current_price: float,
    ) -> List[Component]:
        """
        Score and rank all components in-place.

        Args:
            components: All detected active Component objects
            current_price: Latest close price

        Returns:
            Same list, with .strength and .confluence_score updated, sorted descending
        """
        if not components or current_price <= 0:
            return components

        for comp in components:
            # Base score adjusted by type weight
            weight = _TYPE_WEIGHTS.get(comp.component_type, 1.0)
            base = comp.strength * weight

            # Confluence: how many other components overlap this zone
            overlaps = sum(
                1 for other in components
                if other is not comp and comp.overlaps_with(other)
            )
            confluence = overlaps * self.confluence_bonus
            comp.confluence_score = min(100.0, confluence)

            # Proximity bonus: 0-30 points based on how close to current price
            dist_pct = abs(comp.price_mid - current_price) / current_price * 100.0
            proximity_bonus = max(0.0, (3.0 - dist_pct) / 3.0 * 30.0) * self.proximity_weight

            # Retest bonus
            retest = min(comp.touch_count * self.retest_bonus, 20.0)

            # Final score
            comp.strength = min(
                self.max_score,
                base + confluence + proximity_bonus + retest,
            )

        # Sort strongest first
        components.sort(key=lambda c: c.strength, reverse=True)
        logger.debug(
            f"StrengthEngine: scored {len(components)} components, "
            f"top strength={components[0].strength:.1f}" if components else ""
        )
        return components

    def get_top_components(
        self,
        components: List[Component],
        n: int = 5,
        polarity: ComponentPolarity = None,
    ) -> List[Component]:
        """
        Get the top N strongest components, optionally filtered by polarity.

        Args:
            components: Scored component list
            n: Number of top components to return
            polarity: Optional polarity filter

        Returns:
            Top N components
        """
        filtered = [
            c for c in components
            if polarity is None or c.polarity == polarity
        ]
        return filtered[:n]

    def calculate_overall_confluence(
        self, components: List[Component]
    ) -> float:
        """
        Calculate an overall confluence score for the setup (0-100).
        Based on number and strength of aligned components.
        """
        if not components:
            return 0.0
        avg_strength = sum(c.strength for c in components) / len(components)
        count_bonus = min(len(components) * 5.0, 30.0)
        return min(100.0, avg_strength * 0.7 + count_bonus)
