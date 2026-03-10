"""
ICT Signal Pipeline V2 - Main Engine

Clean, modular, ICT-compliant signal generation pipeline.

Public interface is compatible with legacy ICTSignalEngine:

    engine = ICTSignalEngine()
    result = engine.generate_signal(df, 'BTCUSDT', '1h', mode='AUTO')
    # Returns ICTSignal-compatible object or NO_TRADE dict

8-step pipeline:
    Step 0: Data validation
    Step 1: HTF bias detection
    Step 2: Market structure detection
    Step 3: Orderflow detection (OB / Breaker / FVG)
    Step 4: Liquidity detection (pools + sweeps)
    Step 5: Candidate generation (6 ICT scenarios)
    Step 6: Confidence scoring (100-point system)
    Step 7: Entry / SL / TP calculation
    Step 8: Signal generation & validation

Author: galinborisov10-art
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from typing import Tuple

from ict_config import (
    CANDLE_REQUIREMENTS,
    CONFIDENCE_THRESHOLDS,
    PIPO,
)
from market_structure_detector import analyze_market_structure
from orderflow_detector import analyze_orderflow
from liquidity_detector import analyze_liquidity
from candidate_generator import generate_candidates
from confidence_scorer import score_candidate
from entry_calculator import calculate_entry_sl_tp, calculate_entry_zone
from execution_quality_checker import check_execution_quality

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Signal output dataclass
# ─────────────────────────────────────────────

@dataclass
class ICTSignalV2:
    """
    Output signal from the V2 pipeline.

    Compatible with the legacy ICTSignal interface while adding V2 fields.
    """
    symbol:        str
    timeframe:     str
    direction:     str                    # 'BUY' or 'SELL'
    entry:         float
    entry_zone:    Dict = field(default_factory=dict)
    sl:            float = 0.0
    tp:            float = 0.0
    confidence:    float = 0.0
    scenario:      str = ''
    signal_type:   str = ''               # 'BUY'/'SELL'/'STRONG_BUY'/'STRONG_SELL'
    market_bias:   str = 'NEUTRAL'
    rr_ratio:      float = 0.0
    score_breakdown: Dict = field(default_factory=dict)
    confirmations: List[str] = field(default_factory=list)
    warnings:      List[str] = field(default_factory=list)
    timestamp:     str = ''
    # Legacy compatibility fields
    entry_price:      float = 0.0
    sl_price:         float = 0.0
    tp_prices:        List[float] = field(default_factory=list)
    risk_reward_ratio: float = 0.0
    htf_bias:         str = 'NEUTRAL'
    bias:             str = 'NEUTRAL'
    entry_scenario:   str = ''
    entry_scenario_score: int = 0

    def __post_init__(self):
        # Keep legacy fields in sync
        self.entry_price       = self.entry
        self.sl_price          = self.sl
        self.tp_prices         = [self.tp] if self.tp else []
        self.risk_reward_ratio = self.rr_ratio
        self.htf_bias          = self.market_bias
        self.bias              = self.market_bias
        self.entry_scenario    = self.scenario
        self.entry_scenario_score = int(self.confidence)

    def to_dict(self) -> Dict:
        """Serialize to plain dictionary."""
        return {
            'symbol':           self.symbol,
            'timeframe':        self.timeframe,
            'direction':        self.direction,
            'signal_type':      self.signal_type,
            'entry':            self.entry,
            'entry_zone':       self.entry_zone,
            'sl':               self.sl,
            'tp':               self.tp,
            'confidence':       self.confidence,
            'scenario':         self.scenario,
            'market_bias':      self.market_bias,
            'rr_ratio':         self.rr_ratio,
            'score_breakdown':  self.score_breakdown,
            'confirmations':    self.confirmations,
            'warnings':         self.warnings,
            'timestamp':        self.timestamp,
            # Legacy
            'entry_price':      self.entry_price,
            'sl_price':         self.sl_price,
            'tp_prices':        self.tp_prices,
            'risk_reward_ratio': self.risk_reward_ratio,
            'htf_bias':         self.htf_bias,
            'bias':             self.bias,
            'entry_scenario':   self.entry_scenario,
            'entry_scenario_score': self.entry_scenario_score,
        }


# ─────────────────────────────────────────────
# NO_TRADE helpers
# ─────────────────────────────────────────────

def _no_trade(symbol: str, timeframe: str, reason: str, details: str,
              diagnostics: Optional[Dict] = None,
              suggestion: str = '') -> Dict:
    """Build a standardised NO_TRADE response dict."""
    return {
        'action':      'NO_TRADE',
        'symbol':      symbol,
        'timeframe':   timeframe,
        'timestamp':   datetime.now(timezone.utc).isoformat(),
        'reason':      reason,
        'details':     details,
        'diagnostics': diagnostics or {},
        'suggestion':  suggestion,
    }


# ─────────────────────────────────────────────
# Signal type helper
# ─────────────────────────────────────────────

def _signal_type(direction: str, confidence: float) -> str:
    """Map direction + confidence to a signal-type label."""
    if direction == 'BUY':
        return 'STRONG_BUY' if confidence >= 80 else 'BUY'
    return 'STRONG_SELL' if confidence >= 80 else 'SELL'


# ─────────────────────────────────────────────
# Candle count penalty
# ─────────────────────────────────────────────

def _candle_penalty(candle_count: int, timeframe: str) -> Tuple[int, Optional[str]]:
    """
    Calculate soft penalty for insufficient candle data.

    Returns:
        (penalty: int, warning: str or None)
    """
    optimal   = CANDLE_REQUIREMENTS['optimal'].get(timeframe.lower(), 250)
    hard_min  = CANDLE_REQUIREMENTS['hard_minimum']
    max_pen   = CANDLE_REQUIREMENTS['soft_penalty_pct']

    if candle_count < hard_min:
        return -1, None  # Signal: hard reject (handled separately)

    if candle_count >= optimal:
        return 0, None

    shortfall_pct = (optimal - candle_count) / optimal
    penalty       = int(max_pen * shortfall_pct)
    warning       = (
        f"Limited candle data ({candle_count} vs {optimal} optimal for {timeframe})"
    )
    return penalty, warning


# ─────────────────────────────────────────────
# ICT Signal Engine V2
# ─────────────────────────────────────────────

class ICTSignalEngine:
    """
    ICT Signal Engine V2 — clean 8-step pipeline.

    Public interface is compatible with legacy ICTSignalEngine.
    """

    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize engine with optional config overrides.

        Args:
            config: Optional dict to override default ICT config values.
                    Keys correspond to keys in ict_config.py top-level dicts.
        """
        self._config    = config or {}
        self._active_signals: Dict[str, Dict] = {}  # PIPO tracking

        logger.info("✅ ICT Signal Engine V2 initialized")

    # ─────────────────────────────────────────────
    # Public entry point
    # ─────────────────────────────────────────────

    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        mode: str = 'AUTO',
        volume_24h: float = 0.0,
        spread_pct: float = 0.0,
        mtf_data: Optional[Dict] = None,
    ) -> Union[ICTSignalV2, Dict]:
        """
        Main entry point — analyze market and generate ICT-compliant signal.

        Args:
            df:         OHLCV DataFrame (minimum 200 candles).
                        Expected columns: open, high, low, close, volume.
            symbol:     Trading pair (e.g., 'BTCUSDT', 'EURUSD').
            timeframe:  '15m', '30m', '1h', '2h', '4h', '1d'.
            mode:       'AUTO' (threshold 60%) or 'MANUAL' (threshold 70%).
            volume_24h: 24-hour volume in USD (optional).
            spread_pct: Current spread as fraction (optional).
            mtf_data:   Multi-timeframe data dict (optional, not used in V2 base).

        Returns:
            ICTSignalV2 object on success, or NO_TRADE dict on failure.
        """
        symbol    = symbol.upper()
        timeframe = timeframe.lower()
        mode      = mode.upper()

        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        logger.info(f"🎯 ICT Signal Engine V2 — {symbol} {timeframe} [{mode}]")
        logger.info(f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")

        try:
            return self._run_pipeline(df, symbol, timeframe, mode,
                                      volume_24h, spread_pct)
        except Exception as exc:
            logger.exception(f"💥 Unhandled exception in pipeline: {exc}")
            return _no_trade(
                symbol, timeframe,
                reason='Internal error',
                details=f'Pipeline error: {exc}',
                suggestion='Check logs for stack trace.',
            )

    # ─────────────────────────────────────────────
    # Pipeline
    # ─────────────────────────────────────────────

    def _run_pipeline(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str,
        mode: str,
        volume_24h: float,
        spread_pct: float,
    ) -> Union[ICTSignalV2, Dict]:

        # ── Step 0: Data validation ──────────────────────────────────
        logger.info("📊 Step 0: Data Validation")
        candle_count = len(df)
        hard_min     = CANDLE_REQUIREMENTS['hard_minimum']
        optimal      = CANDLE_REQUIREMENTS['optimal'].get(timeframe, 250)

        if candle_count < hard_min:
            return _no_trade(
                symbol, timeframe,
                reason='Insufficient historical data',
                details=(
                    f"Only {candle_count} candles available for {symbol} {timeframe}. "
                    f"Minimum {hard_min} required, optimal {optimal}."
                ),
                diagnostics={
                    'available_candles': candle_count,
                    'required_candles':  hard_min,
                    'optimal_candles':   optimal,
                    'data_coverage_days': round(candle_count * _tf_to_hours(timeframe) / 24, 2),
                },
                suggestion='Wait for more historical data or use lower timeframe.',
            )

        candle_pen, candle_warn = _candle_penalty(candle_count, timeframe)
        warnings: List[str] = []
        if candle_warn:
            warnings.append(candle_warn)
            logger.warning(f"⚠️ {candle_warn}")

        current_price = float(df['close'].iloc[-1])
        logger.info(f"   → Candles: {candle_count}  Price: {current_price:.4f}")

        # ── Step 1: HTF Bias ────────────────────────────────────────
        logger.info("📊 Step 1: HTF Bias Detection")
        structure = analyze_market_structure(df)
        htf_bias  = structure['htf_bias']

        # ── Step 2: Market Structure ────────────────────────────────
        logger.info("📊 Step 2: Market Structure Detection")
        bos   = structure.get('bos')
        choch = structure.get('choch')
        logger.info(f"   → BOS: {bos is not None}  CHoCH: {choch is not None}")

        # ── Step 3: Orderflow ───────────────────────────────────────
        logger.info("📊 Step 3: Orderflow Detection")
        orderflow = analyze_orderflow(df)
        atr       = orderflow['atr']

        # ── Step 4: Liquidity ───────────────────────────────────────
        logger.info("📊 Step 4: Liquidity Detection")
        liquidity = analyze_liquidity(
            df,
            swing_highs=structure.get('swing_highs', []),
            swing_lows =structure.get('swing_lows',  []),
        )

        # ── Step 5: Candidates ──────────────────────────────────────
        logger.info("📊 Step 5: Candidate Generation")
        candidates = generate_candidates(
            current_price=current_price,
            htf_bias=htf_bias,
            structure=structure,
            orderflow=orderflow,
            liquidity=liquidity,
        )

        if not candidates:
            return _no_trade(
                symbol, timeframe,
                reason='No valid ICT scenario detected',
                details=(
                    'No PULLBACK, CONTINUATION, or REVERSAL setup found. '
                    'Market structure does not align with any ICT entry model.'
                ),
                diagnostics={
                    'why_rejected': [
                        f'HTF bias: {htf_bias}',
                        f'BOS detected: {bos is not None}',
                        f'CHoCH detected: {choch is not None}',
                        f'Order blocks: {len(orderflow["order_blocks"])}',
                        f'FVGs: {len(orderflow["fvgs"])}',
                        f'Liquidity sweeps: {len(liquidity["sweeps"])}',
                    ],
                    'htf_bias': htf_bias,
                    'order_blocks': len(orderflow['order_blocks']),
                    'fvgs': len(orderflow['fvgs']),
                    'sweeps': len(liquidity['sweeps']),
                },
                suggestion='Wait for clearer HTF bias or structure break confirmation.',
            )

        # ── Step 6: Confidence Scoring ──────────────────────────────
        logger.info("📊 Step 6: Confidence Scoring")

        # Execution quality check (for penalty)
        exec_penalty, exec_warnings, should_pause = check_execution_quality(
            symbol, current_price, volume_24h, spread_pct
        )
        warnings.extend(exec_warnings)

        scored: List[tuple] = []
        for cand in candidates:
            score, breakdown = score_candidate(
                candidate=cand,
                htf_bias=htf_bias,
                structure=structure,
                orderflow=orderflow,
                liquidity=liquidity,
                df=df,
                candle_penalty=candle_pen,
                exec_penalty=exec_penalty,
            )
            scored.append((score, breakdown, cand))

        if not scored:
            return _no_trade(symbol, timeframe, reason='No scored candidates',
                             details='Scoring produced no results.',
                             diagnostics={'candidates_evaluated': len(candidates)})

        # Best candidate by score
        scored.sort(key=lambda x: x[0], reverse=True)
        best_score, best_breakdown, best_candidate = scored[0]

        threshold = CONFIDENCE_THRESHOLDS.get(mode, 60)

        if best_score < threshold:
            return _no_trade(
                symbol, timeframe,
                reason='Insufficient confidence',
                details=(
                    f"Signal confidence {best_score:.1f}% is below "
                    f"{threshold}% threshold for {mode} mode. "
                    f"Market conditions do not meet ICT setup requirements."
                ),
                diagnostics={
                    'confidence':         best_score,
                    'threshold':          threshold,
                    'mode':               mode,
                    'score_breakdown':    best_breakdown,
                    'missing_criteria':   self._missing_criteria(best_breakdown),
                    'htf_bias':           htf_bias,
                    'structure_breaks':   int(bos is not None),
                    'order_blocks':       len(orderflow['order_blocks']),
                    'liquidity_sweeps':   len(liquidity['sweeps']),
                    'candidates_evaluated': len(candidates),
                    'best_candidate_score': best_score,
                },
                suggestion='Wait for clearer HTF bias or structure break confirmation.',
            )

        # ── Step 7: Entry / SL / TP ─────────────────────────────────
        logger.info("📊 Step 7: Entry / SL / TP Calculation")
        levels = calculate_entry_sl_tp(best_candidate, atr, structure, liquidity)

        if levels is None:
            return _no_trade(
                symbol, timeframe,
                reason='Risk/Reward ratio insufficient',
                details=(
                    f"No structure target achieves minimum RR "
                    f"{2.5}:1 for {best_candidate['direction']} trade."
                ),
                diagnostics={
                    'scenario':  best_candidate['scenario'],
                    'direction': best_candidate['direction'],
                    'min_rr':    2.5,
                    'htf_bias':  htf_bias,
                },
                suggestion='Wait for deeper retracement or clearer structure target.',
            )

        entry = levels['entry']
        sl    = levels['sl']
        tp    = levels['tp']
        rr    = levels['rr']

        if rr < 2.5:
            return _no_trade(
                symbol, timeframe,
                reason='Risk/Reward ratio insufficient',
                details=(
                    f"Calculated RR {rr:.1f}:1 is below minimum 2.5:1 threshold. "
                    f"Entry {entry:.4f}, SL {sl:.4f}, TP {tp:.4f}."
                ),
                diagnostics={
                    'entry': entry, 'sl': sl, 'tp': tp,
                    'rr': rr, 'min_rr': 2.5,
                },
                suggestion='Wait for deeper retracement or clearer structure target.',
            )

        # ── Step 8: Signal Generation & Validation ──────────────────
        logger.info("📊 Step 8: Signal Validation")

        # Re-score with actual RR now that levels are known
        from confidence_scorer import score_rr
        rr_pts_actual = score_rr(entry, sl, tp)
        # Update breakdown
        old_rr_pts = best_breakdown.get('rr', 0)
        delta = rr_pts_actual - old_rr_pts
        best_breakdown['rr'] = rr_pts_actual
        final_confidence = max(0, min(100, best_score + delta))

        if final_confidence < threshold:
            return _no_trade(
                symbol, timeframe,
                reason='Insufficient confidence after RR adjustment',
                details=(
                    f"Final confidence {final_confidence:.1f}% below threshold {threshold}%."
                ),
                diagnostics={
                    'confidence': final_confidence,
                    'threshold':  threshold,
                    'score_breakdown': best_breakdown,
                },
            )

        # PIPO check
        pipo_result = self._check_pipo(symbol, timeframe, entry)
        if pipo_result:
            return pipo_result

        direction   = best_candidate['direction']
        sig_type    = _signal_type(direction, final_confidence)
        confirmations = best_candidate.get('confirmations', [])

        logger.info(
            f"✅ SIGNAL: {symbol} {timeframe} {sig_type} "
            f"@ {entry:.4f}  SL:{sl:.4f}  TP:{tp:.4f}  "
            f"RR:{rr:.2f}  CONF:{final_confidence:.0f}%"
        )

        signal = ICTSignalV2(
            symbol        = symbol,
            timeframe     = timeframe,
            direction     = direction,
            entry         = entry,
            entry_zone    = best_candidate.get('entry_zone', {}),
            sl            = sl,
            tp            = tp,
            confidence    = final_confidence,
            scenario      = best_candidate['scenario'],
            signal_type   = sig_type,
            market_bias   = htf_bias,
            rr_ratio      = rr,
            score_breakdown = best_breakdown,
            confirmations = confirmations,
            warnings      = warnings,
            timestamp     = datetime.now(timezone.utc).isoformat(),
        )

        # Register in PIPO tracker
        self._active_signals[f"{symbol}_{timeframe}"] = {
            'entry':     entry,
            'direction': direction,
            'timestamp': signal.timestamp,
        }

        return signal

    # ─────────────────────────────────────────────
    # PIPO duplicate check
    # ─────────────────────────────────────────────

    def _check_pipo(self, symbol: str, timeframe: str, new_entry: float) -> Optional[Dict]:
        """
        Check PIPO (Prevent Identical Price Operations) rule.

        Allow max 1 active signal per (symbol, timeframe) unless the new
        entry differs by >= 0.5% from the active entry.

        Returns:
            NO_TRADE dict if duplicate, None if allowed.
        """
        key = f"{symbol}_{timeframe}"
        active = self._active_signals.get(key)
        if not active:
            return None

        active_entry = active['entry']
        movement_pct = abs(new_entry - active_entry) / max(active_entry, 1e-9) * 100

        if movement_pct < PIPO['min_price_movement_pct']:
            return _no_trade(
                symbol, timeframe,
                reason='Duplicate signal (PIPO rule)',
                details=(
                    f"Active signal already exists for {symbol} {timeframe}. "
                    f"Current entry {new_entry:.4f} vs active {active_entry:.4f} "
                    f"(price movement {movement_pct:.2f}%, threshold {PIPO['min_price_movement_pct']}%)."
                ),
                diagnostics={
                    'active_entry':        active_entry,
                    'new_entry':           new_entry,
                    'price_movement_pct':  round(movement_pct, 2),
                    'pipo_threshold':      PIPO['min_price_movement_pct'],
                },
                suggestion=(
                    f"Wait for active signal to close or price to move >= "
                    f"{PIPO['min_price_movement_pct']}%."
                ),
            )

        return None

    # ─────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────

    @staticmethod
    def _missing_criteria(breakdown: Dict) -> List[str]:
        """
        Build a list of human-readable explanations for low sub-scores.
        """
        criteria = []
        maxes = {
            'ht_alignment': 20,
            'structure':    22,
            'orderflow':    20,
            'liquidity':    12,
            'momentum':     10,
            'pattern':       6,
            'rr':           10,
        }
        labels = {
            'ht_alignment': 'HTF alignment',
            'structure':    'Structure confirmation',
            'orderflow':    'Orderflow quality',
            'liquidity':    'Liquidity interaction',
            'momentum':     'Momentum/volume',
            'pattern':      'Candle pattern',
            'rr':           'RR viability',
        }
        for key, max_pts in maxes.items():
            actual = breakdown.get(key, 0)
            if actual < max_pts * 0.6:
                criteria.append(
                    f"{labels[key]} weak ({actual}/{max_pts} points)"
                )
        return criteria


# ─────────────────────────────────────────────
# Timeframe to hours helper (module-level)
# ─────────────────────────────────────────────

def _tf_to_hours(tf: str) -> float:
    """Convert timeframe string to approximate hours."""
    mapping = {
        '1m': 1/60, '5m': 5/60, '15m': 0.25, '30m': 0.5,
        '1h': 1, '2h': 2, '4h': 4, '8h': 8, '12h': 12, '1d': 24,
    }
    return mapping.get(tf.lower(), 1.0)
