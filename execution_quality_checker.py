"""
ICT Signal Pipeline V2 - Execution Quality Checker

Checks execution quality factors:
  - Spread (crypto: max 0.15%, forex: max 0.05%)
  - 24h volume (min $100k)
  - News calendar pause (optional)

Returns a penalty score and list of warnings.  Never blocks signal generation
(signal-only bot), but applies confidence penalty when thresholds exceeded.

Author: galinborisov10-art
"""

import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ict_config import EXECUTION_QUALITY, NEWS_PAUSE, FOREX_SYMBOLS

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Spread check
# ─────────────────────────────────────────────

def check_spread(spread_pct: float, symbol: str) -> Tuple[int, Optional[str]]:
    """
    Check if spread is within acceptable limits.

    Args:
        spread_pct: Current spread as a fraction (e.g., 0.0012 = 0.12%).
        symbol:     Trading symbol to determine asset class.

    Returns:
        Tuple of (penalty: int, warning: Optional[str]).
        penalty is 0 (acceptable) or EXECUTION_QUALITY['spread_penalty'] (exceeded).
    """
    is_forex = any(symbol.upper().startswith(fx) or symbol.upper() == fx
                   for fx in FOREX_SYMBOLS)
    max_spread = (EXECUTION_QUALITY['max_spread_forex']
                  if is_forex
                  else EXECUTION_QUALITY['max_spread_crypto'])

    if spread_pct > max_spread:
        penalty = EXECUTION_QUALITY['spread_penalty']
        warning = (
            f"Spread {spread_pct * 100:.2f}% exceeds max "
            f"{max_spread * 100:.2f}% for {symbol}"
        )
        return penalty, warning

    return 0, f"Spread {spread_pct * 100:.2f}% (acceptable)"


# ─────────────────────────────────────────────
# Volume check
# ─────────────────────────────────────────────

def check_volume(volume_24h: float,
                 min_threshold: float = EXECUTION_QUALITY['min_volume_24h']
                 ) -> Tuple[int, Optional[str]]:
    """
    Check if 24h volume meets the minimum liquidity threshold.

    Args:
        volume_24h:     24-hour trading volume in USD.
        min_threshold:  Minimum acceptable volume (default $100k).

    Returns:
        Tuple of (penalty: int, warning: Optional[str]).
    """
    if volume_24h < min_threshold:
        penalty = EXECUTION_QUALITY['volume_penalty']
        warning = (
            f"24h volume ${volume_24h:,.0f} below minimum "
            f"${min_threshold:,.0f}"
        )
        return penalty, warning

    return 0, f"Volume ${volume_24h:,.0f} (acceptable)"


# ─────────────────────────────────────────────
# News calendar
# ─────────────────────────────────────────────

def check_news_calendar(symbol: str) -> Optional[Dict]:
    """
    Check if there is a major news event near the current time.

    Only active when NEWS_PAUSE['enabled'] is True.
    Currently a stub — integrate with an economic calendar API if needed.

    Args:
        symbol: Trading symbol.

    Returns:
        Dict {should_pause: bool, reason: str, minutes_to_event: int}
        or None if news pause is disabled or no event found.
    """
    if not NEWS_PAUSE.get('enabled', False):
        return None

    # Stub: no live calendar integration in V2 base implementation
    logger.debug(f"   News calendar check for {symbol} — no events (stub)")
    return None


# ─────────────────────────────────────────────
# Combined checker
# ─────────────────────────────────────────────

def check_execution_quality(
    symbol: str,
    price: float,
    volume_24h: float = 0.0,
    spread_pct: float = 0.0,
) -> Tuple[int, List[str], bool]:
    """
    Run all execution quality checks for a signal candidate.

    Args:
        symbol:     Trading symbol.
        price:      Current price (for context).
        volume_24h: 24h volume in USD (0 = not checked).
        spread_pct: Current spread as fraction (0 = not checked).

    Returns:
        Tuple of:
          - total_penalty: int (0-20, to be subtracted from confidence)
          - warnings:      List[str] of human-readable warnings
          - should_pause:  bool (True only if news pause is active)
    """
    total_penalty = 0
    warnings: List[str] = []
    should_pause = False

    # --- Spread ---
    if spread_pct > 0:
        sp_penalty, sp_warn = check_spread(spread_pct, symbol)
        total_penalty += sp_penalty
        if sp_warn:
            warnings.append(sp_warn)

    # --- Volume ---
    if volume_24h > 0:
        vol_penalty, vol_warn = check_volume(volume_24h)
        total_penalty += vol_penalty
        if vol_warn:
            warnings.append(vol_warn)

    # --- News ---
    news = check_news_calendar(symbol)
    if news and news.get('should_pause'):
        should_pause = True
        warnings.append(news.get('reason', 'News pause active'))

    total_penalty = min(total_penalty, 20)

    logger.info(
        f"   → Execution quality: penalty={total_penalty} "
        f"warnings={len(warnings)} pause={should_pause}"
    )
    return total_penalty, warnings, should_pause
