"""
🔄 SIGNAL PIPELINE
Main V2 Signal Generation Orchestrator (STEPS 1-15)

This is the top-level entry point for the V2 signal pipeline.
It coordinates all V2 engines and detectors to produce trading signals.

Pipeline Steps:
    STEP 1:  Validate inputs (symbol, timeframe, data)
    STEP 2:  HTF bias determination (HTFBiasEngine)
    STEP 3:  Component detection (ComponentEngine → all detectors)
    STEP 4:  Filter components by HTF bias alignment
    STEP 5:  Component scoring (StrengthEngine)
    STEP 6:  Determine trade direction
    STEP 7:  Final strength ranking
    STEP 8:  Anchor selection (AnchorEngine)
    STEP 9:  Entry zone calculation (EntryEngine)
    STEP 10: Stop Loss calculation (RiskEngine)
    STEP 11: Take Profit calculation with min RR (RiskEngine)
    STEP 12: Confidence factors aggregation
    STEP 13: Final confidence score (ConfidenceEngine)
    STEP 14: Signal validation (is_valid check)
    STEP 15: Return Signal or None

Author: galinborisov10-art
Version: 2.0
"""

import logging
import pandas as pd
from typing import Optional, Dict, Any, List

from models.signal import Signal, SignalV2
from models.component import Component, ComponentV2
from engine.htf_bias_engine import HTFBiasEngine
from engine.component_engine import ComponentEngine
from engine.signal_engine import SignalEngine

logger = logging.getLogger(__name__)


class SignalPipeline:
    """
    Signal Pipeline

    Complete end-to-end trading signal pipeline.
    Accepts raw OHLCV data (and optional HTF data) and returns a Signal
    or None if no valid setup is found.

    Args:
        symbol: Trading pair symbol (e.g. 'BTCUSDT').  Used by generate_signal().
        enable_telegram: If True the pipeline itself may send Telegram messages.
                         Set to False when the bot handles Telegram (default False).
        htf_bias_engine: HTFBiasEngine instance (created with defaults if not provided)
        component_engine: ComponentEngine instance (created with defaults if not provided)
        signal_engine: SignalEngine instance (created with defaults if not provided)
        htf_timeframe: Timeframe to treat as HTF for bias (default '4H')
        min_data_points: Minimum OHLCV candles required (default 100)
    """

    # Preferred HTF timeframe keys to look for in df_by_tf
    _HTF_PREFERENCE = ["1d", "1D", "4h", "4H", "1w", "1W"]

    def __init__(
        self,
        symbol: str = "",
        enable_telegram: bool = False,
        htf_bias_engine: Optional[HTFBiasEngine] = None,
        component_engine: Optional[ComponentEngine] = None,
        signal_engine: Optional[SignalEngine] = None,
        htf_timeframe: str = "4H",
        min_data_points: int = 100,
    ):
        self.symbol = symbol
        self.enable_telegram = enable_telegram
        self.htf_bias_engine = htf_bias_engine or HTFBiasEngine()
        self.component_engine = component_engine or ComponentEngine()
        self.signal_engine = signal_engine or SignalEngine()
        self.htf_timeframe = htf_timeframe
        self.min_data_points = min_data_points
        logger.info(
            f"SignalPipeline initialized "
            f"(symbol={symbol}, htf_tf={htf_timeframe}, min_candles={min_data_points})"
        )

    def generate_signal(
        self,
        df_by_tf: Dict[str, pd.DataFrame],
        trigger_type: str = "manual",
    ) -> Optional[Signal]:
        """
        Generate a trading signal from a multi-timeframe OHLCV dict.

        This is the primary entry point used by bot.py.

        Args:
            df_by_tf: Mapping of timeframe label → OHLCV DataFrame.
                      E.g. {'1H': df_1h, '4H': df_4h, '1D': df_1d}
                      The first key is treated as the primary (entry) timeframe.
            trigger_type: 'manual' (user command) or 'auto' (scheduler).

        Returns:
            Signal object if a valid signal is found, else None.
        """
        if not df_by_tf:
            logger.error("[PIPELINE] generate_signal called with empty df_by_tf")
            return None

        # Determine primary timeframe (first entry)
        primary_tf = next(iter(df_by_tf))
        df = df_by_tf[primary_tf]

        # Determine HTF dataframe if available
        htf_df: Optional[pd.DataFrame] = None
        for htf_key in self._HTF_PREFERENCE:
            if htf_key in df_by_tf and htf_key != primary_tf:
                htf_df = df_by_tf[htf_key]
                break

        symbol = self.symbol
        logger.info(
            f"[PIPELINE] generate_signal: symbol={symbol} primary_tf={primary_tf} "
            f"trigger={trigger_type} htf_available={htf_df is not None}"
        )
        return self.run(df, symbol, primary_tf, htf_df)

    def run(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str = "1H",
        htf_df: Optional[pd.DataFrame] = None,
    ) -> Optional[Signal]:
        """
        Run the full signal pipeline.

        Args:
            df: OHLCV DataFrame for the current timeframe
            symbol: Trading pair (e.g. 'BTC/USDT')
            timeframe: Current timeframe label (e.g. '1H')
            htf_df: Optional separate HTF OHLCV DataFrame for bias determination.
                    If not provided, df is used for bias too.

        Returns:
            Signal object if a valid signal is found, else None
        """
        logger.info(f"[PIPELINE] Starting for {symbol} {timeframe}")

        # ── STEP 1: Validate inputs ──────────────────────────────────────
        if not self._validate_inputs(df, symbol, timeframe):
            return None

        # ── STEP 2: HTF Bias ────────────────────────────────────────────
        bias_df = htf_df if htf_df is not None and len(htf_df) >= 50 else df
        htf_bias_data = self.htf_bias_engine.determine_bias(
            bias_df, symbol=symbol, timeframe=self.htf_timeframe
        )
        bias = htf_bias_data.get("bias", "RANGING")
        logger.info(
            f"[PIPELINE] STEP 2 HTF Bias: {bias} "
            f"(conf={htf_bias_data.get('confidence', 0):.1f}%)"
        )

        if bias == "RANGING":
            logger.info(f"[PIPELINE] {symbol} RANGING - aborting pipeline")
            return None

        # ── STEP 3: Component Detection ──────────────────────────────────
        component_map = self.component_engine.detect_all(df, timeframe)
        all_components: List[Component] = component_map.get("all", [])
        stats = self.component_engine.get_stats(component_map)
        logger.info(
            f"[PIPELINE] STEP 3 Components: "
            f"{stats['order_blocks']} OBs, {stats['fvgs']} FVGs, "
            f"{stats['liquidity_zones']} LiqZones, {stats['breaker_blocks']} Breakers"
        )

        if not all_components:
            logger.info(f"[PIPELINE] {symbol} no components found - aborting")
            return None

        # ── STEPS 5-13: Signal generation (delegated to SignalEngine) ────
        signal = self.signal_engine.generate(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            components=all_components,
            htf_bias_data=htf_bias_data,
        )

        # ── STEP 14: Final validation ────────────────────────────────────
        if signal is not None and not signal.is_valid:
            logger.warning(
                f"[PIPELINE] {symbol} signal failed is_valid check - discarding"
            )
            return None

        if signal:
            logger.info(
                f"[PIPELINE] ✅ {symbol} {timeframe} {signal.direction.value} "
                f"signal complete | conf={signal.confidence:.1f}% | "
                f"entry={signal.entry_price:.4f} | SL={signal.stop_loss:.4f} | "
                f"TP3={signal.take_profit_3:.4f} | RR={signal.risk_reward_ratio:.2f}"
            )
        else:
            logger.info(f"[PIPELINE] {symbol} {timeframe} - no signal generated")

        # ── STEP 15: Return ──────────────────────────────────────────────
        return signal

    def _validate_inputs(
        self, df: pd.DataFrame, symbol: str, timeframe: str
    ) -> bool:
        """Validate that inputs are usable"""
        if not symbol:
            logger.error("[PIPELINE] STEP 1 FAILED: symbol is empty")
            return False
        if df is None:
            logger.error(f"[PIPELINE] STEP 1 FAILED: df is None for {symbol}")
            return False
        if len(df) < self.min_data_points:
            logger.warning(
                f"[PIPELINE] STEP 1 FAILED: {symbol} has only {len(df)} candles "
                f"(min={self.min_data_points})"
            )
            return False
        required_cols = {"open", "high", "low", "close", "volume"}
        missing = required_cols - set(df.columns)
        if missing:
            logger.error(
                f"[PIPELINE] STEP 1 FAILED: {symbol} df missing columns: {missing}"
            )
            return False
        logger.debug(f"[PIPELINE] STEP 1 OK: {symbol} {timeframe} ({len(df)} candles)")
        return True


# Backward-compatibility alias
SignalPipelineV2 = SignalPipeline
