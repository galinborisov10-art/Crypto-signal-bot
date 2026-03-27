"""
📊 CONFIDENCE ENGINE V2
Calculates final signal confidence score (0-100%).

Corresponds to STEP 13 of the V2 signal pipeline.

Factors considered:
- HTF bias strength
- Component confluence score
- Anchor component strength
- Risk:Reward quality
- Entry zone precision
- Market session alignment (optional)

Author: galinborisov10-art
Version: 2.0
"""

import logging
from typing import Optional, Dict, Any, List

from models.component_v2 import ComponentV2
from models.signal_v2 import SignalStrength

logger = logging.getLogger(__name__)

# Confidence thresholds for signal strength labels
_STRENGTH_THRESHOLDS = [
    (85, SignalStrength.EXTREME),
    (70, SignalStrength.VERY_STRONG),
    (55, SignalStrength.STRONG),
    (40, SignalStrength.MODERATE),
    (0, SignalStrength.WEAK),
]


class ConfidenceEngine:
    """
    V2 Signal Confidence Engine

    Aggregates multiple scoring factors into a single 0-100 confidence score
    and maps it to a SignalStrength label.

    Args:
        min_confidence: Minimum score to emit a signal (default 40.0)
        htf_weight: Weight for HTF bias factor (default 0.25)
        confluence_weight: Weight for component confluence (default 0.30)
        anchor_weight: Weight for anchor strength (default 0.20)
        rr_weight: Weight for RR quality (default 0.15)
        entry_weight: Weight for entry precision (default 0.10)
    """

    def __init__(
        self,
        min_confidence: float = 40.0,
        htf_weight: float = 0.25,
        confluence_weight: float = 0.30,
        anchor_weight: float = 0.20,
        rr_weight: float = 0.15,
        entry_weight: float = 0.10,
    ):
        self.min_confidence = min_confidence
        self.weights = {
            "htf": htf_weight,
            "confluence": confluence_weight,
            "anchor": anchor_weight,
            "rr": rr_weight,
            "entry": entry_weight,
        }
        total = sum(self.weights.values())
        assert abs(total - 1.0) < 0.01, f"Weights must sum to 1.0, got {total}"
        logger.info(f"ConfidenceEngine initialized (min_confidence={min_confidence})")

    def calculate(
        self,
        htf_bias_data: Dict[str, Any],
        components: List[ComponentV2],
        anchor: Optional[ComponentV2],
        risk_data: Optional[Dict[str, Any]],
        entry_data: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculate the final confidence score for the signal.

        Args:
            htf_bias_data: Output from HTFBiasEngine.determine_bias()
            components: All scored ComponentV2 objects from StrengthEngine
            anchor: Selected anchor ComponentV2
            risk_data: Output from RiskEngine.calculate()
            entry_data: Output from EntryEngine.calculate_entry()

        Returns:
            dict with keys:
                confidence (float): 0-100
                strength (SignalStrength): strength label
                factors (dict): individual factor scores
                passes_threshold (bool): whether signal should be emitted
        """
        htf_score = self._score_htf(htf_bias_data)
        confluence_score = self._score_confluence(components)
        anchor_score = self._score_anchor(anchor)
        rr_score = self._score_rr(risk_data)
        entry_score = self._score_entry(entry_data)

        factors = {
            "htf": htf_score,
            "confluence": confluence_score,
            "anchor": anchor_score,
            "rr": rr_score,
            "entry": entry_score,
        }

        confidence = sum(
            factors[k] * self.weights[k] for k in self.weights
        )
        confidence = min(100.0, max(0.0, confidence))
        strength = self._to_strength(confidence)

        passes = confidence >= self.min_confidence

        logger.debug(
            f"ConfidenceEngine: score={confidence:.1f}, strength={strength.value}, "
            f"passes={passes}, factors={factors}"
        )
        return {
            "confidence": confidence,
            "strength": strength,
            "factors": factors,
            "passes_threshold": passes,
        }

    def _score_htf(self, htf_data: Dict[str, Any]) -> float:
        """Score from HTF bias data (0-100)"""
        if not htf_data:
            return 0.0
        if htf_data.get("bias", "RANGING") == "RANGING":
            return 0.0
        return float(htf_data.get("confidence", 50.0))

    def _score_confluence(self, components: List[ComponentV2]) -> float:
        """Score based on component confluence (0-100)"""
        if not components:
            return 0.0
        avg = sum(c.confluence_score for c in components) / len(components)
        count_bonus = min(len(components) * 5.0, 30.0)
        return min(100.0, avg + count_bonus)

    def _score_anchor(self, anchor: Optional[ComponentV2]) -> float:
        """Score from anchor component strength (0-100)"""
        if anchor is None:
            return 0.0
        return float(anchor.strength)

    def _score_rr(self, risk_data: Optional[Dict[str, Any]]) -> float:
        """Score from risk:reward ratio (0-100)"""
        if not risk_data:
            return 0.0
        rr = float(risk_data.get("risk_reward_ratio", 0.0))
        # Perfect score at RR >= 5.0, zero at RR < 1.0
        return min(100.0, max(0.0, (rr - 1.0) / 4.0 * 100.0))

    def _score_entry(self, entry_data: Optional[Dict[str, Any]]) -> float:
        """Score from entry zone precision (0-100)"""
        if not entry_data:
            return 0.0
        entry_type = entry_data.get("entry_type", "LIMIT")
        # MARKET entries score less than precise LIMIT entries
        return 70.0 if entry_type == "LIMIT" else 50.0

    @staticmethod
    def _to_strength(confidence: float) -> SignalStrength:
        """Map confidence score to SignalStrength label"""
        for threshold, strength in _STRENGTH_THRESHOLDS:
            if confidence >= threshold:
                return strength
        return SignalStrength.WEAK
