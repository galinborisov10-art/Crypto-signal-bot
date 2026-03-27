"""
🛡️ RISK ENGINE V2
Calculates Stop Loss and Take Profit levels with minimum RR enforcement.

Corresponds to STEPS 10-11 of the V2 signal pipeline.

SL logic:
- Bullish: SL placed below anchor zone low (with buffer)
- Bearish: SL placed above anchor zone high (with buffer)

TP logic:
- TP1 at 1:1 RR
- TP2 at 1:2 RR
- TP3 at 1:3 RR (minimum enforced)

Author: galinborisov10-art
Version: 2.0
"""

import logging
from typing import Optional, Dict, Any, List

from models.component_v2 import ComponentV2

logger = logging.getLogger(__name__)


class RiskEngine:
    """
    V2 Risk Calculation Engine

    Calculates SL and TP levels ensuring the minimum RR requirement is met.

    Args:
        sl_buffer_pct: Extra buffer below/above anchor for SL (default 0.1%)
        min_rr: Minimum required Risk:Reward ratio for TP3 (default 3.0)
        sl_max_pct: Maximum allowed SL as % of entry price (default 5.0%)
    """

    def __init__(
        self,
        sl_buffer_pct: float = 0.1,
        min_rr: float = 3.0,
        sl_max_pct: float = 5.0,
    ):
        self.sl_buffer_pct = sl_buffer_pct
        self.min_rr = min_rr
        self.sl_max_pct = sl_max_pct
        logger.info(
            f"RiskEngine initialized (sl_buffer={sl_buffer_pct}%, "
            f"min_rr={min_rr}, sl_max={sl_max_pct}%)"
        )

    def calculate(
        self,
        entry_price: float,
        anchor: ComponentV2,
        bias: str,
        swing_low: Optional[float] = None,
        swing_high: Optional[float] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate SL and TP levels.

        Args:
            entry_price: Calculated entry price
            anchor: Selected anchor component
            bias: 'BULLISH' or 'BEARISH'
            swing_low: Recent swing low (used for SL reference on bullish)
            swing_high: Recent swing high (used for SL reference on bearish)

        Returns:
            dict with keys:
                stop_loss (float)
                take_profit_1 (float): 1:1 RR
                take_profit_2 (float): 1:2 RR
                take_profit_3 (float): 1:3 RR
                risk_reward_ratio (float): Actual TP3 RR
                sl_pips (float): SL distance
            or None if SL is invalid
        """
        if entry_price <= 0 or anchor is None:
            return None

        if bias == "BULLISH":
            return self._bullish_risk(entry_price, anchor, swing_low)
        elif bias == "BEARISH":
            return self._bearish_risk(entry_price, anchor, swing_high)
        return None

    def _bullish_risk(
        self,
        entry: float,
        anchor: ComponentV2,
        swing_low: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """Calculate SL/TP for bullish setup"""
        buffer = entry * (self.sl_buffer_pct / 100.0)

        # SL: below anchor low (or swing low, whichever is lower)
        sl_candidates = [anchor.price_low - buffer]
        if swing_low and swing_low < anchor.price_low:
            sl_candidates.append(swing_low - buffer)
        sl = min(sl_candidates)

        if sl >= entry:
            logger.warning("RiskEngine: bullish SL >= entry, invalid")
            return None

        sl_pips = entry - sl
        max_sl = entry * (self.sl_max_pct / 100.0)
        if sl_pips > max_sl:
            logger.warning(
                f"RiskEngine: SL too wide ({sl_pips:.4f} > {max_sl:.4f})"
            )
            return None

        tp1 = entry + sl_pips * 1.0
        tp2 = entry + sl_pips * 2.0
        tp3 = entry + sl_pips * self.min_rr
        rr = sl_pips and (tp3 - entry) / sl_pips or 0.0

        logger.debug(
            f"RiskEngine: BULLISH SL={sl:.4f}, TP1={tp1:.4f}, "
            f"TP2={tp2:.4f}, TP3={tp3:.4f}, RR={rr:.2f}"
        )
        return {
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "take_profit_3": tp3,
            "risk_reward_ratio": rr,
            "sl_pips": sl_pips,
        }

    def _bearish_risk(
        self,
        entry: float,
        anchor: ComponentV2,
        swing_high: Optional[float],
    ) -> Optional[Dict[str, Any]]:
        """Calculate SL/TP for bearish setup"""
        buffer = entry * (self.sl_buffer_pct / 100.0)

        sl_candidates = [anchor.price_high + buffer]
        if swing_high and swing_high > anchor.price_high:
            sl_candidates.append(swing_high + buffer)
        sl = max(sl_candidates)

        if sl <= entry:
            logger.warning("RiskEngine: bearish SL <= entry, invalid")
            return None

        sl_pips = sl - entry
        max_sl = entry * (self.sl_max_pct / 100.0)
        if sl_pips > max_sl:
            logger.warning(
                f"RiskEngine: SL too wide ({sl_pips:.4f} > {max_sl:.4f})"
            )
            return None

        tp1 = entry - sl_pips * 1.0
        tp2 = entry - sl_pips * 2.0
        tp3 = entry - sl_pips * self.min_rr
        rr = sl_pips and (entry - tp3) / sl_pips or 0.0

        logger.debug(
            f"RiskEngine: BEARISH SL={sl:.4f}, TP1={tp1:.4f}, "
            f"TP2={tp2:.4f}, TP3={tp3:.4f}, RR={rr:.2f}"
        )
        return {
            "stop_loss": sl,
            "take_profit_1": tp1,
            "take_profit_2": tp2,
            "take_profit_3": tp3,
            "risk_reward_ratio": rr,
            "sl_pips": sl_pips,
        }

    def validate_rr(self, risk_data: Optional[Dict[str, Any]]) -> bool:
        """Check that the calculated RR meets the minimum requirement"""
        if risk_data is None:
            return False
        return risk_data.get("risk_reward_ratio", 0.0) >= self.min_rr
