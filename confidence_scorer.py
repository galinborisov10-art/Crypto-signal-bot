"""
ICT Signal Pipeline V2 - Confidence Scorer

Transparent 100-point scoring system for ICT signal candidates.

Scoring breakdown:
  - HT Alignment     (0-20 pts)
  - Structure        (0-22 pts)
  - Orderflow        (0-20 pts)
  - Liquidity        (0-12 pts)
  - Momentum/Volume  (0-10 pts)
  - Pattern          (0-6 pts)
  - RR Viability     (0-10 pts)
  Penalties applied after sum.

Author: galinborisov10-art
"""

import logging
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple

from ict_config import SCORING_WEIGHTS, RISK_REWARD

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Sub-scorers
# ─────────────────────────────────────────────

def score_ht_alignment(htf_bias: str, candidate_direction: str) -> int:
    """
    Score Higher Timeframe alignment (0-20 points).

    Rules:
    - +20: HTF bias perfectly matches direction (1D/4H alignment).
    - +10: Partial match (HTF neutral, no strong confirmation).
    -   0: HTF contradicts entry direction.

    Args:
        htf_bias:            'BULLISH', 'BEARISH', or 'NEUTRAL'.
        candidate_direction: 'BUY' or 'SELL'.

    Returns:
        Integer score 0-20.
    """
    if candidate_direction == 'BUY':
        if htf_bias == 'BULLISH':
            return 20
        elif htf_bias == 'NEUTRAL':
            return 10
        else:  # BEARISH
            return 0
    else:  # SELL
        if htf_bias == 'BEARISH':
            return 20
        elif htf_bias == 'NEUTRAL':
            return 10
        else:  # BULLISH
            return 0


def score_structure(bos: Optional[Dict], choch: Optional[Dict],
                    candidate_scenario: str, candidate_direction: str) -> int:
    """
    Score structure confirmation (0-22 points).

    Rules:
    - +22: Clean BOS/CHoCH supporting the scenario direction.
    - +12: Partial structure (BOS detected but not strongly aligned).
    -   0: No structure or contradicting structure.

    Args:
        bos:                 BOS dict or None.
        choch:               CHoCH dict or None.
        candidate_scenario:  Scenario name string.
        candidate_direction: 'BUY' or 'SELL'.

    Returns:
        Integer score 0-22.
    """
    expected_dir = 'BULLISH' if candidate_direction == 'BUY' else 'BEARISH'

    # Reversal scenario → CHoCH is the primary confirmation
    if candidate_scenario == 'reversal':
        if choch and choch.get('direction') == expected_dir:
            return 22
        if bos and bos.get('direction') == expected_dir:
            return 12
        return 0

    # Non-reversal scenarios → BOS is primary
    if bos and bos.get('direction') == expected_dir:
        if choch:
            return 22  # Both BOS + CHoCH = full score
        return 20

    # BOS exists but wrong direction (lower partial credit)
    if bos and bos.get('direction') != expected_dir:
        return 6

    # No BOS but has CHoCH in right direction
    if choch and choch.get('direction') == expected_dir:
        return 12

    return 0


def score_orderflow(poi_type: str, poi_strength: int, candidate: Dict) -> int:
    """
    Score orderflow quality (0-20 points).

    Rules:
    - +20: Valid untested OB / Breaker / FVG at entry zone.
    - +10: Partially tested POI.
    -   0: No POI or fully mitigated.

    Args:
        poi_type:     POI type string from candidate.
        poi_strength: 0-100 strength from orderflow analysis.
        candidate:    Full candidate dict (used to check 'tested' flag).

    Returns:
        Integer score 0-20.
    """
    if poi_type in ('BULLISH_OB', 'BEARISH_OB', 'BREAKER'):
        base = 20
    elif poi_type in ('BULLISH_FVG', 'BEARISH_FVG'):
        base = 18
    else:
        base = 10  # Generic sweep / CHoCH level

    # Scale by poi_strength
    scaled = int(base * (poi_strength / 100.0))
    return min(scaled, 20)


def score_liquidity(sweeps: List[Dict], pools: List[Dict],
                    entry_zone: Dict, candidate_direction: str) -> int:
    """
    Score liquidity interaction (0-12 points).

    Rules:
    - +12: Fresh sweep + cluster + rejection + follow-through.
    - +6:  Liquidity pool nearby (no sweep).
    -  0:  No liquidity interaction.

    Args:
        sweeps:              Detected liquidity sweeps.
        pools:               Detected liquidity pools.
        entry_zone:          Candidate entry zone.
        candidate_direction: 'BUY' or 'SELL'.

    Returns:
        Integer score 0-12.
    """
    preferred = entry_zone.get('preferred', 0)
    tolerance = preferred * 0.005  # 0.5% window

    # Fresh sweep in support of direction
    sweep_type = 'SSL_SWEEP' if candidate_direction == 'BUY' else 'BSL_SWEEP'
    fresh_sweep = next(
        (s for s in sweeps
         if s['type'] == sweep_type and s['candles_ago'] <= 12
         and abs(s['pool_price'] - preferred) <= tolerance * 5),
        None
    )
    if fresh_sweep:
        return min(12, 6 + int(fresh_sweep['strength'] / 16))

    # Liquidity pool nearby
    pool_type = 'SELL_SIDE_LIQUIDITY' if candidate_direction == 'BUY' else 'BUY_SIDE_LIQUIDITY'
    near_pool = next(
        (p for p in pools
         if p['type'] == pool_type
         and abs(p['price'] - preferred) <= tolerance * 10),
        None
    )
    if near_pool:
        return 6

    return 0


def score_momentum(df: pd.DataFrame) -> int:
    """
    Score momentum / volume (0-10 points).

    Rules:
    - +10: Volume spike >= 1.5x average volume in last 5 candles.
    - +5:  Moderate strength (strong close on last candle).
    -  0:  Weak momentum.

    Args:
        df: OHLCV DataFrame.

    Returns:
        Integer score 0-10.
    """
    try:
        if 'volume' in df.columns and len(df) >= 20:
            avg_vol = float(df['volume'].rolling(20).mean().iloc[-1])
            recent_vol = float(df['volume'].iloc[-5:].mean())
            if avg_vol > 0 and recent_vol >= avg_vol * 1.5:
                return 10
            if avg_vol > 0 and recent_vol >= avg_vol * 1.1:
                return 5

        # Fallback: check candle body strength
        close = float(df['close'].iloc[-1])
        open_ = float(df['open'].iloc[-1])
        high  = float(df['high'].iloc[-1])
        low   = float(df['low'].iloc[-1])
        candle_range = max(high - low, 1e-9)
        body_pct = abs(close - open_) / candle_range
        if body_pct >= 0.6:
            return 5
        return 0

    except Exception as exc:
        logger.warning(f"⚠️ score_momentum error: {exc}")
        return 0


def score_pattern(df: pd.DataFrame, entry_zone: Dict) -> int:
    """
    Score candle pattern at the entry zone (0-6 points).

    Rules:
    - +6: Clean pin bar or engulfing candle.
    - +3: Weaker pattern (close near zone edge, long wick).
    -  0: No recognizable pattern.

    Args:
        df:         OHLCV DataFrame.
        entry_zone: Candidate entry zone dict.

    Returns:
        Integer score 0-6.
    """
    try:
        last   = df.iloc[-1]
        second = df.iloc[-2] if len(df) >= 2 else None

        open_  = float(last['open'])
        close  = float(last['close'])
        high   = float(last['high'])
        low    = float(last['low'])
        rng    = max(high - low, 1e-9)
        body   = abs(close - open_)

        # Pin bar: small body, large wick >= 2x body
        upper_wick = high - max(close, open_)
        lower_wick = min(close, open_) - low
        if body > 0 and (upper_wick >= 2 * body or lower_wick >= 2 * body):
            return 6

        # Engulfing: current body engulfs previous candle body
        if second is not None:
            prev_body_high = max(float(second['open']), float(second['close']))
            prev_body_low  = min(float(second['open']), float(second['close']))
            if close > open_ and close > prev_body_high and open_ < prev_body_low:
                return 6  # Bullish engulfing
            if close < open_ and close < prev_body_low and open_ > prev_body_high:
                return 6  # Bearish engulfing

        # Weak pattern: close in top/bottom 30% of range
        if close > low + 0.7 * rng or close < low + 0.3 * rng:
            return 3

        return 0

    except Exception as exc:
        logger.warning(f"⚠️ score_pattern error: {exc}")
        return 0


def score_rr(entry: float, sl: float, tp: float) -> int:
    """
    Score Risk/Reward viability (0-10 points).

    Rules:
    - +10: RR >= 4.0
    - +8:  RR >= 3.0
    - +6:  RR >= 2.5 (minimum acceptable)
    -  0:  RR < 2.5 → candidate should be rejected

    Args:
        entry: Entry price.
        sl:    Stop-loss price.
        tp:    Take-profit price.

    Returns:
        Integer score 0-10.
    """
    risk   = abs(entry - sl)
    reward = abs(tp - entry)
    if risk <= 0:
        return 0
    rr = reward / risk
    if rr >= RISK_REWARD['great']:
        return 10
    if rr >= RISK_REWARD['good']:
        return 8
    if rr >= RISK_REWARD['minimum']:
        return 6
    return 0  # Below minimum → candidate invalid


# ─────────────────────────────────────────────
# Main scorer
# ─────────────────────────────────────────────

def score_candidate(
    candidate: Dict,
    htf_bias: str,
    structure: Dict,
    orderflow: Dict,
    liquidity: Dict,
    df: pd.DataFrame,
    candle_penalty: int = 0,
    exec_penalty: int = 0,
) -> Tuple[int, Dict]:
    """
    Score a single candidate using the full 100-point system.

    Args:
        candidate:      Candidate dict from candidate_generator.
        htf_bias:       'BULLISH', 'BEARISH', or 'NEUTRAL'.
        structure:      Output from analyze_market_structure().
        orderflow:      Output from analyze_orderflow().
        liquidity:      Output from analyze_liquidity().
        df:             OHLCV DataFrame (for pattern/momentum).
        candle_penalty: Soft penalty for insufficient data (0-15).
        exec_penalty:   Penalty for poor execution quality (0-10).

    Returns:
        Tuple of (total_score: int, breakdown: dict).
    """
    direction = candidate['direction']
    scenario  = candidate['scenario']
    entry_zone = candidate.get('entry_zone', {})
    poi_type  = candidate.get('poi_type', '')
    poi_strength = candidate.get('poi_strength', 50)

    bos   = structure.get('bos')
    choch = structure.get('choch')
    sweeps = liquidity.get('sweeps', [])
    pools  = liquidity.get('pools', [])

    # --- Individual scores ---
    ht_pts    = score_ht_alignment(htf_bias, direction)
    struct_pts = score_structure(bos, choch, scenario, direction)
    of_pts    = score_orderflow(poi_type, poi_strength, candidate)
    liq_pts   = score_liquidity(sweeps, pools, entry_zone, direction)
    mom_pts   = score_momentum(df)
    pat_pts   = score_pattern(df, entry_zone)

    # RR needs entry/sl/tp from candidate (if pre-calculated)
    entry = candidate.get('entry', entry_zone.get('preferred', 0))
    sl    = candidate.get('sl', 0)
    tp    = candidate.get('tp', 0)
    rr_pts = score_rr(entry, sl, tp) if sl and tp else 6  # Assume acceptable if not yet calculated

    # HTF contradiction penalty
    htf_contradiction = (
        (direction == 'BUY'  and htf_bias == 'BEARISH') or
        (direction == 'SELL' and htf_bias == 'BULLISH')
    )
    htf_penalty = 15 if htf_contradiction else 0

    raw_total = ht_pts + struct_pts + of_pts + liq_pts + mom_pts + pat_pts + rr_pts
    penalties = candle_penalty + exec_penalty + htf_penalty
    total     = max(0, min(100, raw_total - penalties))

    breakdown = {
        'ht_alignment':  ht_pts,
        'structure':     struct_pts,
        'orderflow':     of_pts,
        'liquidity':     liq_pts,
        'momentum':      mom_pts,
        'pattern':       pat_pts,
        'rr':            rr_pts,
        'penalties': {
            'candle_count': candle_penalty,
            'execution':    exec_penalty,
            'htf_contradiction': htf_penalty,
        },
    }

    logger.info(
        f"   Score [{scenario} {direction}]: "
        f"HT={ht_pts} STR={struct_pts} OF={of_pts} LIQ={liq_pts} "
        f"MOM={mom_pts} PAT={pat_pts} RR={rr_pts} PEN=-{penalties} "
        f"→ TOTAL={total}"
    )

    return total, breakdown
