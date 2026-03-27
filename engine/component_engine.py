"""
🔍 COMPONENT ENGINE V2
Runs all V2 detectors and aggregates ICT components.

Corresponds to STEP 3 of the V2 signal pipeline.
Orchestrates OrderBlockDetectorV2, FVGDetectorV2, LiquidityDetectorV2,
and BreakerDetectorV2 into a single component map.

Author: galinborisov10-art
Version: 2.0
"""

import logging
import pandas as pd
from typing import List, Dict, Any, Optional

from models.component import Component, ComponentType
from detectors.order_block_detector import OrderBlockDetectorV2
from detectors.fvg_detector import FVGDetectorV2
from detectors.liquidity_detector import LiquidityDetectorV2
from detectors.breaker_detector import BreakerDetectorV2

logger = logging.getLogger(__name__)


class ComponentEngine:
    """
    V2 Component Detection Engine

    Runs all ICT detectors on the provided OHLCV data and returns a unified
    list of Component objects, grouped by type.

    Args:
        ob_config: Config overrides for OrderBlockDetectorV2
        fvg_config: Config overrides for FVGDetectorV2
        liq_config: Config overrides for LiquidityDetectorV2
        breaker_config: Config overrides for BreakerDetectorV2
    """

    def __init__(
        self,
        ob_config: Optional[Dict[str, Any]] = None,
        fvg_config: Optional[Dict[str, Any]] = None,
        liq_config: Optional[Dict[str, Any]] = None,
        breaker_config: Optional[Dict[str, Any]] = None,
    ):
        ob_config = ob_config or {}
        fvg_config = fvg_config or {}
        liq_config = liq_config or {}
        breaker_config = breaker_config or {}

        self.ob_detector = OrderBlockDetectorV2(**ob_config)
        self.fvg_detector = FVGDetectorV2(**fvg_config)
        self.liq_detector = LiquidityDetectorV2(**liq_config)
        self.breaker_detector = BreakerDetectorV2(**breaker_config)
        logger.info("ComponentEngine initialized with all V2 detectors")

    def detect_all(
        self, df: pd.DataFrame, timeframe: str = "1H"
    ) -> Dict[str, List[Component]]:
        """
        Run all detectors on the OHLCV data.

        Args:
            df: OHLCV DataFrame
            timeframe: Chart timeframe label

        Returns:
            dict with keys:
                'order_blocks': List[Component]
                'fvgs': List[Component]
                'liquidity_zones': List[Component]
                'breaker_blocks': List[Component]
                'all': List[Component] (combined)
        """
        if df is None or len(df) < 20:
            logger.warning("ComponentEngine: insufficient data")
            return self._empty_result()

        logger.info(f"ComponentEngine: detecting components on {timeframe} ({len(df)} candles)")

        order_blocks = self.ob_detector.detect(df, timeframe)
        fvgs = self.fvg_detector.detect(df, timeframe)
        liquidity_zones = self.liq_detector.detect(df, timeframe)
        breaker_blocks = self.breaker_detector.detect(df, order_blocks, timeframe)

        all_components = order_blocks + fvgs + liquidity_zones + breaker_blocks

        summary = {
            "order_blocks": order_blocks,
            "fvgs": fvgs,
            "liquidity_zones": liquidity_zones,
            "breaker_blocks": breaker_blocks,
            "all": all_components,
        }

        logger.info(
            f"ComponentEngine: "
            f"{len(order_blocks)} OBs, {len(fvgs)} FVGs, "
            f"{len(liquidity_zones)} LiqZones, {len(breaker_blocks)} Breakers"
        )
        return summary

    def get_stats(self, components: Dict[str, List[Component]]) -> Dict[str, int]:
        """Return count statistics for each component type"""
        return {
            "order_blocks": len(components.get("order_blocks", [])),
            "fvgs": len(components.get("fvgs", [])),
            "liquidity_zones": len(components.get("liquidity_zones", [])),
            "breaker_blocks": len(components.get("breaker_blocks", [])),
            "total": len(components.get("all", [])),
        }

    @staticmethod
    def _empty_result() -> Dict[str, List[Component]]:
        return {
            "order_blocks": [],
            "fvgs": [],
            "liquidity_zones": [],
            "breaker_blocks": [],
            "all": [],
        }
