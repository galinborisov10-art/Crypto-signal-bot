"""
ICT Signal Pipeline V2 - Configuration Constants

All configuration for the ICT Signal Pipeline V2.
Modify this file to tune signal generation behavior.

Author: galinborisov10-art
"""

# ─────────────────────────────────────────────
# Candle count requirements per timeframe
# ─────────────────────────────────────────────
CANDLE_REQUIREMENTS = {
    'hard_minimum': 200,          # Hard reject below this
    'optimal': {
        '1d':  365,
        '4h':  500,
        '2h':  400,
        '1h':  400,
        '30m': 250,
        '15m': 250,
    },
    'soft_penalty_pct': 15,       # % confidence penalty when below optimal
}

# ─────────────────────────────────────────────
# Confidence thresholds
# ─────────────────────────────────────────────
CONFIDENCE_THRESHOLDS = {
    'AUTO':   60,
    'MANUAL': 70,
}

# ─────────────────────────────────────────────
# Scoring weights (100-point system)
# ─────────────────────────────────────────────
SCORING_WEIGHTS = {
    'ht_alignment':  20,   # HTF bias alignment
    'structure':     22,   # Structure confirmation (BOS/CHoCH)
    'orderflow':     20,   # Order block / FVG / breaker quality
    'liquidity':     12,   # Liquidity interaction
    'momentum':      10,   # Volume / momentum
    'pattern':        6,   # Candle pattern (pin bar, engulfing)
    'rr_viability':  10,   # Risk/reward viability
}

# ─────────────────────────────────────────────
# Risk / Reward
# ─────────────────────────────────────────────
RISK_REWARD = {
    'minimum': 2.5,     # Reject candidate below this
    'good':    3.0,
    'great':   4.0,
}

# ─────────────────────────────────────────────
# ATR buffers for SL placement
# ─────────────────────────────────────────────
ATR_BUFFERS = {
    'ob_long':    0.30,   # OB long: SL = OB.low - (0.30 * ATR)
    'ob_short':   0.30,   # OB short: SL = OB.high + (0.30 * ATR)
    'sweep_long': 0.25,   # Sweep long: SL = sweep_wick - (0.25 * ATR)
    'sweep_short':0.25,
    'fvg_long':   0.30,
    'fvg_short':  0.30,
}

# ─────────────────────────────────────────────
# Execution quality thresholds
# ─────────────────────────────────────────────
EXECUTION_QUALITY = {
    'max_spread_crypto':  0.0015,   # 0.15%
    'max_spread_forex':   0.0005,   # 0.05%
    'min_volume_24h':     100_000,  # $100k minimum
    'spread_penalty':     10,       # Points deducted when threshold exceeded
    'volume_penalty':     10,       # Points deducted when threshold exceeded
}

# ─────────────────────────────────────────────
# News pause (optional)
# ─────────────────────────────────────────────
NEWS_PAUSE = {
    'enabled':          False,
    'pause_before_min': 30,   # Pause 30 min before major event
    'pause_after_min':  30,   # Pause 30 min after major event
}

# ─────────────────────────────────────────────
# PIPO duplicate signal check
# ─────────────────────────────────────────────
PIPO = {
    'min_price_movement_pct': 0.5,  # Allow new signal if entry moved >= 0.5%
}

# ─────────────────────────────────────────────
# Market structure / swing detection
# ─────────────────────────────────────────────
STRUCTURE = {
    'swing_window':          3,     # Candles each side for swing high/low
    'swing_lookback':        5,     # Last N swings to evaluate bias
    'impulse_atr_multiplier':1.5,   # Body >= 1.5x avg body → impulse candle
    'atr_period':            14,
}

# ─────────────────────────────────────────────
# Liquidity detection
# ─────────────────────────────────────────────
LIQUIDITY = {
    'equal_level_tolerance': 0.003,   # 0.3% to classify as equal highs/lows
    'sweep_wick_tolerance':  0.005,   # 0.5% wick beyond pool
    'session_lookback':      50,      # Candles for session high/low
    'sweep_rejection_bars':  2,       # Max bars for rejection after sweep
}

# ─────────────────────────────────────────────
# Candidate generation
# ─────────────────────────────────────────────
CANDIDATES = {
    'sweep_max_candles_ago':     12,   # Max age of sweep for continuation
    'pullback_near_zone_pct':    0.03,  # 0-3% from price for pullback_cont
    'pullback_deep_zone_min':    0.03,  # 3% min from price for deep pullback
    'pullback_deep_zone_max':    0.08,  # 8% max from price for deep pullback
    'fvg_min_size_atr_mult':     0.5,   # FVG must be >= 0.5 * ATR
}

# ─────────────────────────────────────────────
# Confidence scoring proximity windows
# ─────────────────────────────────────────────
SCORING_PROXIMITY = {
    'sweep_max_candles_ago':        12,    # Max sweep age for liquidity score
    'sweep_pool_tolerance_mult':     5,    # Tolerance = entry * 0.005 * this
    'pool_proximity_tolerance_mult': 10,   # Tolerance = entry * 0.005 * this
}

# ─────────────────────────────────────────────
# Asset class detection (for spread limits)
# ─────────────────────────────────────────────
FOREX_SYMBOLS = ['EURUSD', 'GBPUSD', 'USDJPY', 'AUDUSD', 'USDCAD', 'NZDUSD', 'USDCHF',
                 'EURJPY', 'GBPJPY', 'EURGBP']
