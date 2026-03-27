"""
🚀 SIGNAL ENGINE V2
Main signal generation engine for the V2 pipeline (STEPS 5-12).

Orchestrates the individual V2 engines to produce a complete SignalV2 object.
This is the core of the V2 signal generation flow, called by SignalPipelineV2.

Pipeline steps handled here:
    STEP 5:  Component scoring (StrengthEngine)
    STEP 6:  Determine trade direction from components + HTF bias
    STEP 7:  Final component strength ranking
    STEP 8:  Anchor selection (AnchorEngine)
    STEP 9:  Entry calculation (EntryEngine)
    STEP 10: SL calculation (RiskEngine)
    STEP 11: TP calculation with RR enforcement (RiskEngine)
    STEP 12: Confidence scoring (ConfidenceEngine)

Author: galinborisov10-art
Version: 2.0
"""

import uuid
import logging
import pandas as pd
from typing import Optional, Dict, Any, List

from models.signal import SignalV2, SignalDirection, SignalStatus
from models.component import ComponentV2, ComponentPolarity
from engine.strength_engine import StrengthEngine
from engine.anchor_engine import AnchorEngine
from engine.entry_engine import EntryEngine
from engine.risk_engine import RiskEngine
from engine.confidence_engine import ConfidenceEngine

logger = logging.getLogger(__name__)


class SignalEngine:
    """
    V2 Signal Engine

    Given OHLCV data, detected components, and HTF bias, produces a SignalV2
    object (or None if no valid setup exists).

    Args:
        strength_engine: StrengthEngine instance (created if not provided)
        anchor_engine: AnchorEngine instance (created if not provided)
        entry_engine: EntryEngine instance (created if not provided)
        risk_engine: RiskEngine instance (created if not provided)
        confidence_engine: ConfidenceEngine instance (created if not provided)
    """

    def __init__(
        self,
        strength_engine: Optional[StrengthEngine] = None,
        anchor_engine: Optional[AnchorEngine] = None,
        entry_engine: Optional[EntryEngine] = None,
        risk_engine: Optional[RiskEngine] = None,
        confidence_engine: Optional[ConfidenceEngine] = None,
    ):
        self.strength_engine = strength_engine or StrengthEngine()
        self.anchor_engine = anchor_engine or AnchorEngine()
        self.entry_engine = entry_engine or EntryEngine()
        self.risk_engine = risk_engine or RiskEngine()
        self.confidence_engine = confidence_engine or ConfidenceEngine()
        logger.info("SignalEngine V2 initialized")

    def generate(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        components: List[ComponentV2],
        htf_bias_data: Dict[str, Any],
    ) -> Optional[SignalV2]:
        """
        Generate a trading signal from components and HTF bias.

        Args:
            df: OHLCV DataFrame (current timeframe)
            symbol: Trading pair symbol
            timeframe: Current timeframe label
            components: All detected ComponentV2 objects (unsorted)
            htf_bias_data: Output from HTFBiasEngine

        Returns:
            SignalV2 object if a valid setup is found, else None
        """
        if df is None or len(df) < 20:
            logger.warning(f"SignalEngine: insufficient data for {symbol}")
            return None

        bias = htf_bias_data.get("bias", "RANGING")
        if bias == "RANGING":
            logger.info(f"SignalEngine: {symbol} HTF bias is RANGING - no signal")
            return None

        current_price = float(df["close"].iloc[-1])

        # STEP 5-7: Score and rank components
        scored = self.strength_engine.score_components(
            [c for c in components if c.is_active], current_price
        )
        if not scored:
            logger.info(f"SignalEngine: {symbol} no active components")
            return None

        # STEP 6: Determine direction
        direction = SignalDirection.LONG if bias == "BULLISH" else SignalDirection.SHORT
        polarity = ComponentPolarity.BULLISH if bias == "BULLISH" else ComponentPolarity.BEARISH

        # STEP 8: Anchor selection
        anchor = self.anchor_engine.select_anchor(scored, current_price, bias)
        if anchor is None:
            logger.info(f"SignalEngine: {symbol} no valid anchor found")
            return None

        # Get recent swing points
        swing_high, swing_low = self._get_swing_points(df)

        # STEP 9: Entry calculation
        entry_data = self.entry_engine.calculate_entry(
            anchor, current_price, bias, swing_high, swing_low
        )
        if entry_data is None:
            logger.info(f"SignalEngine: {symbol} no valid entry found")
            return None

        entry_price = entry_data["entry_price"]

        # STEPS 10-11: Risk calculation
        risk_data = self.risk_engine.calculate(
            entry_price, anchor, bias, swing_low, swing_high
        )
        if risk_data is None or not self.risk_engine.validate_rr(risk_data):
            logger.info(f"SignalEngine: {symbol} risk/RR validation failed")
            return None

        # STEP 12: Confidence
        conf_data = self.confidence_engine.calculate(
            htf_bias_data, scored, anchor, risk_data, entry_data
        )
        if not conf_data.get("passes_threshold", False):
            logger.info(
                f"SignalEngine: {symbol} confidence {conf_data['confidence']:.1f}% "
                f"below threshold"
            )
            return None

        # Build SignalV2
        signal = SignalV2(
            signal_id=str(uuid.uuid4()),
            symbol=symbol,
            timeframe=timeframe,
            direction=direction,
            entry_price=entry_price,
            entry_zone_low=entry_data["entry_zone_low"],
            entry_zone_high=entry_data["entry_zone_high"],
            stop_loss=risk_data["stop_loss"],
            take_profit_1=risk_data["take_profit_1"],
            take_profit_2=risk_data["take_profit_2"],
            take_profit_3=risk_data["take_profit_3"],
            confidence=conf_data["confidence"],
            strength=conf_data["strength"],
            status=SignalStatus.PENDING,
            components=[c.component_type.value for c in scored[:5]],
            htf_bias=bias,
            anchor_level=anchor.price_mid,
            risk_reward_ratio=risk_data["risk_reward_ratio"],
            raw_data={
                "entry_data": entry_data,
                "risk_data": risk_data,
                "confidence_factors": conf_data.get("factors", {}),
                "htf_bias_data": htf_bias_data,
                "anchor_info": self.anchor_engine.get_anchor_info(anchor),
            },
        )

        logger.info(
            f"SignalEngine: ✅ {symbol} {timeframe} {direction.value} signal generated "
            f"(conf={signal.confidence:.1f}%, RR={signal.risk_reward_ratio:.2f})"
        )
        return signal

    @staticmethod
    def _get_swing_points(df: pd.DataFrame, lookback: int = 20):
        """Get recent swing high and swing low from last N candles"""
        recent = df.tail(lookback)
        swing_high = float(recent["high"].max())
        swing_low = float(recent["low"].min())
        return swing_high, swing_low
