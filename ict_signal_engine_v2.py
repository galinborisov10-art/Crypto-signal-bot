"""
🔄 ICT Signal Engine V2 - Adapter
Wraps the V2 signal pipeline (SignalPipelineV2) behind the V1 API signature.

This adapter allows existing callers of ICTSignalEngine.generate_signal() to
switch to the V2 pipeline without changing their call sites.

V2 pipeline location:  pipeline_v2/signal_pipeline.py  → SignalPipelineV2
V2 signal model:       models/signal_v2.py              → SignalV2

Author: galinborisov10-art
Version: 2.0
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

# V2 imports
from models.signal_v2 import SignalDirection
from models.signal_v2 import SignalStrength as SignalStrengthV2
from models.signal_v2 import SignalV2
from pipeline_v2.signal_pipeline import SignalPipelineV2

# V1 imports (for compatibility)
from ict_signal_engine import (
    ICTSignal,
    MarketBias,
    SignalStrength,
    SignalType,
)

logger = logging.getLogger(__name__)


class ICTSignalEngineV2:
    """
    Adapter that wraps SignalPipelineV2 behind the V1 ICTSignalEngine API.

    Callers use the same generate_signal() signature as ICTSignalEngine,
    but the underlying computation is performed by SignalPipelineV2.

    **Behavioral differences vs. V1 ICTSignalEngine:**
    - V2 pipeline does not produce V1-specific ICT component lists
      (whale_blocks, order_blocks, fair_value_gaps, etc.).  All those
      fields on the returned ICTSignal will be empty lists / dicts.
    - HTF bias is determined by SignalPipelineV2 using a fixed timeframe
      (see _DEFAULT_HTF_TF).  If that timeframe is present in mtf_data it
      will be used; otherwise the primary df is used for bias.

    Args:
        config: Optional configuration dict (reserved for future use)
    """

    # Must match SignalPipelineV2's default htf_timeframe constructor argument.
    # If that default changes in signal_pipeline.py, update this constant too.
    _DEFAULT_HTF_TF: str = "4H"

    # Confidence threshold above which BUY/SELL is promoted to STRONG_BUY/SELL.
    # Mirrors the same threshold used in ICTSignalEngine._determine_signal_type().
    _STRONG_SIGNAL_CONFIDENCE: float = 85.0

    def __init__(self, config: Optional[Dict] = None):
        """Initialize V2 pipeline adapter."""
        self._config = config or {}
        self._pipeline_class = SignalPipelineV2
        logger.info("ICTSignalEngineV2 initialized (V2 pipeline adapter)")

    # ──────────────────────────────────────────────────────────────────────────
    # Public API (mirrors ICTSignalEngine)
    # ──────────────────────────────────────────────────────────────────────────

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str = "1H",
        mtf_data: Optional[Dict[str, pd.DataFrame]] = None,
        is_auto: bool = False,
    ) -> Optional[ICTSignal]:
        """
        Generate a signal using the V2 pipeline (V1 API signature).

        Args:
            df: Primary timeframe OHLCV DataFrame
            symbol: Trading pair (e.g. 'BTCUSDT')
            timeframe: Primary timeframe label (e.g. '1H')
            mtf_data: Optional dict of additional timeframe DataFrames
            is_auto: Whether signal is auto-triggered.  Kept for V1 API
                     compatibility; the V2 pipeline does not distinguish
                     auto vs. manual triggers at this time.

        Returns:
            ICTSignal in V1 format, or None if no signal was found
        """
        try:
            htf_df = self._get_htf_df(mtf_data)

            pipeline = self._pipeline_class(
                htf_timeframe=self._DEFAULT_HTF_TF
            )

            v2_signal: Optional[SignalV2] = pipeline.run(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                htf_df=htf_df,
            )

            if v2_signal is None:
                logger.info(
                    f"V2 pipeline returned None for {symbol} {timeframe}"
                )
                return None

            return self._convert_v2_to_v1(v2_signal)

        except Exception as exc:
            logger.error(
                f"V2 adapter error for {symbol}: {exc}", exc_info=True
            )
            return None

    # ──────────────────────────────────────────────────────────────────────────
    # Private helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get_htf_df(
        self, mtf_data: Optional[Dict[str, pd.DataFrame]]
    ) -> Optional[pd.DataFrame]:
        """
        Extract the HTF DataFrame from mtf_data if available.

        V2 pipeline uses a fixed HTF timeframe ('4H' by default).  If
        mtf_data contains that timeframe's data, pass it to the pipeline so
        it can compute HTF bias from real HTF candles; otherwise the pipeline
        will fall back to using the primary df for bias calculation.
        """
        if not mtf_data:
            return None
        return mtf_data.get(self._DEFAULT_HTF_TF)

    def _convert_v2_to_v1(self, v2_signal: SignalV2) -> ICTSignal:
        """Convert a V2 SignalV2 object to a V1 ICTSignal."""
        direction = v2_signal.direction  # SignalDirection enum (LONG / SHORT)

        signal_type = self._map_direction_to_signal_type(
            direction, v2_signal.confidence
        )
        bias = self._map_direction_to_bias(direction)
        signal_strength = self._map_strength_v2_to_v1(v2_signal.strength)

        return ICTSignal(
            timestamp=v2_signal.created_at,
            symbol=v2_signal.symbol,
            timeframe=v2_signal.timeframe,
            signal_type=signal_type,
            signal_strength=signal_strength,
            entry_price=v2_signal.entry_price,
            sl_price=v2_signal.stop_loss,
            tp_prices=[
                v2_signal.take_profit_1,
                v2_signal.take_profit_2,
                v2_signal.take_profit_3,
            ],
            confidence=v2_signal.confidence,
            risk_reward_ratio=v2_signal.risk_reward_ratio,
            bias=bias,
            htf_bias=v2_signal.htf_bias,
            # V2 pipeline does not produce V1-specific ICT component lists;
            # use safe empty defaults so all ICTSignal fields remain valid.
            whale_blocks=[],
            liquidity_zones=[],
            liquidity_sweeps=[],
            order_blocks=[],
            fair_value_gaps=[],
            internal_liquidity=[],
            breaker_blocks=[],
            mitigation_blocks=[],
            sibi_ssib_zones=[],
            fibonacci_data={},
            luxalgo_sr={},
            luxalgo_ict={},
            luxalgo_combined={},
        )

    def _map_direction_to_signal_type(
        self, direction: SignalDirection, confidence: float
    ) -> SignalType:
        """
        Map V2 SignalDirection → V1 SignalType.

        High-confidence signals are promoted to STRONG_BUY / STRONG_SELL,
        mirroring the behaviour of ICTSignalEngine._determine_signal_type().
        """
        if direction == SignalDirection.LONG:
            return (
                SignalType.STRONG_BUY
                if confidence >= self._STRONG_SIGNAL_CONFIDENCE
                else SignalType.BUY
            )
        return (
            SignalType.STRONG_SELL
            if confidence >= self._STRONG_SIGNAL_CONFIDENCE
            else SignalType.SELL
        )

    def _map_direction_to_bias(self, direction: SignalDirection) -> MarketBias:
        """Map V2 SignalDirection → V1 MarketBias."""
        if direction == SignalDirection.LONG:
            return MarketBias.BULLISH
        return MarketBias.BEARISH

    def _map_strength_v2_to_v1(self, strength: SignalStrengthV2) -> SignalStrength:
        """
        Map V2 SignalStrength → V1 SignalStrength.

        Both enums share the same member names
        (WEAK / MODERATE / STRONG / VERY_STRONG / EXTREME), so we map by
        name to avoid hard-coding value conversions.
        """
        try:
            return SignalStrength[strength.name]
        except (KeyError, AttributeError):
            logger.warning(
                f"Unknown V2 strength '{strength}'; defaulting to MODERATE"
            )
            return SignalStrength.MODERATE
