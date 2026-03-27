"""
🔄 ICT SIGNAL ENGINE V2 - Adapter (V2 Pipeline with V1 API)

Adapter pattern: wraps the V2 pipeline (SignalPipelineV2) and exposes
the same API as the V1 ICTSignalEngine so that bot.py can switch to
the V2 pipeline without any modifications.

Usage:
    from ict_signal_engine_v2 import ICTSignalEngineV2

    engine = ICTSignalEngineV2()
    signal = engine.generate_signal(df, 'BTCUSDT', '1H', is_auto=False)
    # Returns ICTSignal (V1 format) – bot.py doesn't know the difference!

Author: galinborisov10-art
Version: 2.0 (adapter)
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd

# V2 imports
from models.signal_v2 import SignalDirection, SignalV2
from pipeline_v2.signal_pipeline import SignalPipelineV2

# V1 imports (for API compatibility)
from ict_signal_engine import (
    ICTSignal,
    MarketBias,
    SignalStrength,
    SignalType,
)

logger = logging.getLogger(__name__)

# Minimum number of candles an HTF DataFrame must contain before it is
# considered suitable for bias determination in the V2 pipeline.
_MIN_HTF_CANDLES = 50


class ICTSignalEngineV2:
    """
    V2 Pipeline Adapter – exposes the same API as V1 ICTSignalEngine.

    bot.py can use this class as a drop-in replacement for ICTSignalEngine.
    Internally it delegates all analysis to SignalPipelineV2 and converts
    the resulting SignalV2 object back to the V1 ICTSignal format.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize the V2 pipeline adapter.

        Args:
            config: Optional configuration dictionary (reserved for future use;
                    currently mirrors the V1 constructor signature).
        """
        self.config = config or {}
        self._pipeline = SignalPipelineV2()
        logger.info("ICTSignalEngineV2 adapter initialized (V2 pipeline)")

    # ------------------------------------------------------------------ #
    #  Public API  (same signature as ICTSignalEngine.generate_signal)    #
    # ------------------------------------------------------------------ #

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str = "1H",
        mtf_data: Optional[Dict[str, pd.DataFrame]] = None,
        is_auto: bool = False,
    ) -> Optional[ICTSignal]:
        """
        Generate a trading signal using the V2 pipeline.

        Signature is intentionally identical to V1 ICTSignalEngine.generate_signal()
        so that this class can be used as a transparent drop-in replacement.

        Args:
            df: OHLCV DataFrame for the primary timeframe.
            symbol: Trading pair (e.g. 'BTCUSDT').
            timeframe: Primary timeframe (e.g. '1H', '2H', '4H').
            mtf_data: Multi-timeframe data {timeframe: DataFrame}.
                      The highest-timeframe DataFrame (if present) is forwarded
                      to the V2 pipeline as htf_df for bias determination.
            is_auto: True for automated signals, False for manual requests.
                     (Retained for API compatibility; not used by V2 pipeline.)

        Returns:
            ICTSignal in V1 format, or None if no valid signal was found.
        """
        try:
            # Select an HTF DataFrame from mtf_data to pass as bias context.
            htf_df = self._select_htf_df(mtf_data, timeframe)

            v2_signal: Optional[SignalV2] = self._pipeline.run(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                htf_df=htf_df,
            )

            if v2_signal is None:
                logger.info(
                    f"[V2 ADAPTER] {symbol} {timeframe} – V2 pipeline returned None"
                )
                return None

            ict_signal = self._convert_v2_to_v1(v2_signal)
            logger.info(
                f"[V2 ADAPTER] ✅ {symbol} {timeframe} "
                f"{ict_signal.signal_type.value} signal converted (V2→V1) "
                f"conf={ict_signal.confidence:.1f}%"
            )
            return ict_signal

        except Exception as exc:
            logger.error(
                f"[V2 ADAPTER] Error generating signal for {symbol} {timeframe}: {exc}",
                exc_info=True,
            )
            return None

    # ------------------------------------------------------------------ #
    #  Conversion: V2 SignalV2  →  V1 ICTSignal                          #
    # ------------------------------------------------------------------ #

    def _convert_v2_to_v1(self, v2_signal: SignalV2) -> ICTSignal:
        """
        Convert a V2 SignalV2 object into the V1 ICTSignal format.

        Field mapping:
            v2_signal.entry_price        → entry_price
            v2_signal.stop_loss          → sl_price
            [tp1, tp2, tp3]              → tp_prices  (List[float])
            v2_signal.direction (enum)   → signal_type (enum BUY/SELL)
            v2_signal.confidence (float) → confidence (float)
            v2_signal.created_at         → timestamp (datetime)
            v2_signal.risk_reward_ratio  → risk_reward_ratio
            v2_signal.htf_bias           → htf_bias
        """
        signal_type = self._map_direction_to_signal_type(v2_signal.direction)
        signal_strength = self._map_confidence_to_strength(v2_signal.confidence)
        bias = self._map_direction_to_bias(v2_signal.direction)
        tp_prices = self._build_tp_list(v2_signal)
        order_blocks = self._extract_order_blocks(v2_signal)
        fvgs = self._extract_fvgs(v2_signal)
        liquidity_zones = self._extract_liquidity(v2_signal)

        timestamp = v2_signal.created_at if isinstance(v2_signal.created_at, datetime) else None
        if timestamp is None:
            logger.warning(
                "[V2 ADAPTER] v2_signal.created_at is not a datetime "
                f"(got {type(v2_signal.created_at).__name__!r}); falling back to utcnow()"
            )
            timestamp = datetime.utcnow()

        return ICTSignal(
            timestamp=timestamp,
            symbol=v2_signal.symbol,
            timeframe=v2_signal.timeframe,
            signal_type=signal_type,
            signal_strength=signal_strength,
            entry_price=v2_signal.entry_price,
            sl_price=v2_signal.stop_loss,
            tp_prices=tp_prices,
            confidence=float(v2_signal.confidence),
            risk_reward_ratio=v2_signal.risk_reward_ratio,
            # ICT components extracted from V2 signal metadata
            order_blocks=order_blocks,
            fair_value_gaps=fvgs,
            liquidity_zones=liquidity_zones,
            # V2 doesn't populate these; use safe defaults
            whale_blocks=[],
            liquidity_sweeps=[],
            internal_liquidity=[],
            breaker_blocks=[],
            mitigation_blocks=[],
            sibi_ssib_zones=[],
            fibonacci_data={},
            luxalgo_sr={},
            luxalgo_ict={},
            luxalgo_combined={},
            # Market analysis fields
            bias=bias,
            structure_broken=False,
            displacement_detected=False,
            mtf_confluence=0,
            htf_bias=v2_signal.htf_bias,
            mtf_structure="NEUTRAL",
            reasoning=f"V2 Pipeline: {v2_signal.direction.value} on {v2_signal.timeframe}",
            warnings=[],
        )

    # ------------------------------------------------------------------ #
    #  Helper methods                                                      #
    # ------------------------------------------------------------------ #

    def _select_htf_df(
        self,
        mtf_data: Optional[Dict[str, pd.DataFrame]],
        primary_timeframe: str,
    ) -> Optional[pd.DataFrame]:
        """
        Pick the best higher-timeframe DataFrame from mtf_data to use as
        HTF context for V2 bias determination.

        Returns the DataFrame whose timeframe key sorts highest (longest
        candles), excluding the primary timeframe itself.  Returns None if
        no suitable candidate is found.
        """
        if not mtf_data:
            return None

        # Rough ordering by typical timeframe length (higher index = higher TF).
        # Timeframe keys are normalised to lowercase for comparison so that
        # '1H' and '1h' both map to the same rank.
        tf_order = [
            "1m", "3m", "5m", "15m", "30m",
            "1h", "2h", "3h",
            "4h", "6h", "8h", "12h",
            "1d", "3d", "1w",
        ]

        def _rank(tf: str) -> int:
            try:
                return tf_order.index(tf.lower())
            except ValueError:
                return -1

        primary_rank = _rank(primary_timeframe)
        candidates = [
            (tf, df_)
            for tf, df_ in mtf_data.items()
            if _rank(tf) > primary_rank and df_ is not None and len(df_) >= _MIN_HTF_CANDLES
        ]

        if not candidates:
            return None

        # Return the DataFrame for the highest available timeframe
        best_tf, best_df = max(candidates, key=lambda x: _rank(x[0]))
        logger.debug(f"[V2 ADAPTER] Using HTF '{best_tf}' for bias determination")
        return best_df

    def _map_direction_to_signal_type(self, direction: SignalDirection) -> SignalType:
        """Map V2 SignalDirection (LONG/SHORT) → V1 SignalType (BUY/SELL)."""
        if direction == SignalDirection.LONG:
            return SignalType.BUY
        return SignalType.SELL

    def _map_direction_to_bias(self, direction: SignalDirection) -> MarketBias:
        """Map V2 SignalDirection → V1 MarketBias enum."""
        if direction == SignalDirection.LONG:
            return MarketBias.BULLISH
        return MarketBias.BEARISH

    def _map_confidence_to_strength(self, confidence: float) -> SignalStrength:
        """
        Map a numeric confidence score (0–100) to a V1 SignalStrength enum value.

        Thresholds:
            0–39  → WEAK
            40–54 → MODERATE
            55–69 → STRONG
            70–84 → VERY_STRONG
            85+   → EXTREME
        """
        if confidence >= 85:
            return SignalStrength.EXTREME
        if confidence >= 70:
            return SignalStrength.VERY_STRONG
        if confidence >= 55:
            return SignalStrength.STRONG
        if confidence >= 40:
            return SignalStrength.MODERATE
        return SignalStrength.WEAK

    def _build_tp_list(self, v2_signal: SignalV2) -> List[float]:
        """
        Build a V1-compatible [TP1, TP2, TP3] list from V2 separate fields.

        V2 stores three take-profit levels as individual attributes;
        V1 ICTSignal expects a single List[float].
        """
        return [
            v2_signal.take_profit_1,
            v2_signal.take_profit_2,
            v2_signal.take_profit_3,
        ]

    def _extract_order_blocks(self, v2_signal: SignalV2) -> List[Dict]:
        """
        Extract order-block component metadata from the V2 signal.

        V2 signals store contributing component names in the ``components``
        list (strings).  Where raw data is available in ``raw_data``, that
        is forwarded; otherwise an empty list is returned so that V1
        consumers that expect a list of dicts are still satisfied.
        """
        raw = v2_signal.raw_data or {}
        obs = raw.get("order_blocks", [])
        if isinstance(obs, list):
            return obs
        return []

    def _extract_fvgs(self, v2_signal: SignalV2) -> List[Dict]:
        """Extract fair-value-gap component metadata from the V2 signal."""
        raw = v2_signal.raw_data or {}
        fvgs = raw.get("fair_value_gaps", raw.get("fvgs", []))
        if isinstance(fvgs, list):
            return fvgs
        return []

    def _extract_liquidity(self, v2_signal: SignalV2) -> List[Dict]:
        """Extract liquidity-zone component metadata from the V2 signal."""
        raw = v2_signal.raw_data or {}
        liq = raw.get("liquidity_zones", [])
        if isinstance(liq, list):
            return liq
        return []
