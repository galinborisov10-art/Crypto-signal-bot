"""
Entry Scenario Scoring System - Configuration
All tunable parameters in one place

Author: galinborisov10-art
Date: 2026-02-10
"""

# ============================================================
# TRIGGER WEIGHTS (равни по важност, но с нюанси)
# ============================================================
TRIGGER_WEIGHTS = {
    'MSS/BOS': 40,           # Structure break (най-силен)
    'DISPLACEMENT': 35,       # Momentum confirmation
    'LIQUIDITY_SWEEP': 25,    # Liquidity grab
    'BREAKER/MITIGATION': 20  # Structure refinement
}

# Trigger strength thresholds (weighted scoring)
TRIGGER_STRENGTH_THRESHOLDS = {
    'HIGH': 75,    # >= 75 total score
    'MEDIUM': 50   # >= 50 total score
}

# ============================================================
# TRIGGER DETECTION SETTINGS
# ============================================================
TRIGGER_SETTINGS = {
    # Displacement
    'displacement_min_strength': 0.6,      # Production threshold
    'displacement_strong_threshold': 0.8,  # Strong displacement bonus
    
    # Liquidity sweep recency (in candles)
    'liquidity_sweep_recency_candles': {
        '15m': 12,
        '1h': 6,
        '4h': 3,
        '1d': 2,
        'default': 6
    }
}

# ============================================================
# SCENARIO SCORING WEIGHTS
# ============================================================

# ROLLBACK scoring
ROLLBACK_WEIGHTS = {
    'base_score': 50,
    'structure_strength_multiplier': 0.4,  # structure.strength * 0.4
    'displacement_bonus': 20,
    'liquidity_sweep_bonus': 15,
    'trigger_count_bonus': 10,             # Per additional trigger
    'distance_penalty_per_pct': -3         # -3 per 1% distance
}

# PULLBACK scoring
PULLBACK_WEIGHTS = {
    'base_score': 40,
    'poi_quality_multiplier': 0.5,         # POI quality * 0.5
    'trigger_count_bonus': 15,             # Per trigger
    'structure_trigger_bonus': 10,         # If has MSS/BOS
    'distance_penalty_per_pct': -5         # Stricter penalty
}

# CONTINUATION scoring
CONTINUATION_WEIGHTS = {
    'base_score': 60,
    'trigger_count_bonus': 20,             # Per trigger (max 2 extra)
    'displacement_strong_bonus': 15,       # If displacement > 0.8
    'structure_trigger_bonus': 10,         # If has MSS/BOS
    'no_poi_in_range_bonus': 10           # Clear path ahead
}

# REVERSAL scoring
REVERSAL_WEIGHTS = {
    'base_score': 55,
    'sweep_bonus': 25,                     # Liquidity sweep present
    'choch_bonus': 20,                     # CHOCH confirmation
    'mss_bonus': 15,                       # MSS confirmation
    'displacement_contra_bonus': 15,       # Displacement in reversal direction
    'trigger_count_bonus': 10              # Per additional trigger
}

# ============================================================
# DISTANCE LIMITS
# ============================================================

# ROLLBACK
ROLLBACK_DISTANCE = {
    'min_pct': 0.01,    # 1.0%
    'max_pct': 0.05,    # 5.0%
    'buffer_pct': 0.002 # 0.2%
}

# PULLBACK
PULLBACK_DISTANCE = {
    'min_pct': 0.002,   # 0.2%
    'max_pct': 0.05,    # 5.0%
    'buffer_pct': 0.002 # 0.2%
}

# CONTINUATION
CONTINUATION_DISTANCE = {
    'retracement_pct': 0.007,    # 0.7%
    'poi_check_range_pct': 0.03, # 3.0%
    'buffer_pct': 0.005          # 0.5%
}

# REVERSAL
REVERSAL_DISTANCE = {
    'min_pct': 0.002,   # 0.2% (to POI)
    'max_pct': 0.05,    # 5.0% (to break level)
    'buffer_pct': 0.002 # 0.2%
}

# ============================================================
# POI QUALITY SCORES
# ============================================================
POI_QUALITY = {
    'OB': 90,        # Order Block
    'FVG': 80,       # Fair Value Gap
    'BSL': 70,       # Buy Side Liquidity
    'SSL': 70,       # Sell Side Liquidity
    'min_acceptable': 65  # Reject POI below this
}

# ============================================================
# POSITION SIZE ADVISORY
# ============================================================
POSITION_SIZE = {
    'ROLLBACK': 100,
    'PULLBACK': 100,
    'CONTINUATION': {
        'default': 65,
        'min': 60,
        'max': 75,
        '3_triggers': 75,  # If 3+ triggers
        '2_triggers': 65   # If 2 triggers
    },
    'REVERSAL': 100
}

# ============================================================
# MINIMUM SCENARIO SCORE
# ============================================================
MIN_SCENARIO_SCORE = 60  # Scenarios below this are rejected

# ============================================================
# MINIMUM TRIGGERS PER SCENARIO
# ============================================================
MIN_TRIGGERS = {
    'ROLLBACK': 2,       # Strict: 2+ triggers
    'PULLBACK': 1,       # Flexible: 1 trigger OK if POI quality >= 85
    'CONTINUATION': 2,   # Strict: 2+ triggers
    'REVERSAL': 2        # Strict: 2+ triggers (sweep + structure)
}

# High quality POI threshold (for PULLBACK with 1 trigger)
PULLBACK_HIGH_QUALITY_THRESHOLD = 85

# ============================================================
# REVERSAL DETECTION SETTINGS
# ============================================================
REVERSAL_SETTINGS = {
    'require_sweep': True,           # Must have liquidity sweep
    'require_structure_flip': True,  # Must have MSS/CHOCH in opposite direction
    'displacement_bonus': True       # Bonus if displacement in reversal direction
}
