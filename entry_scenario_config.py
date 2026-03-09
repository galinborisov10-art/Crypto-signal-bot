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
    'poi_quality_multiplier': 0.4,         # POI quality * 0.4 (REDUCED: was 0.5)
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
    'choch_bonus': 25,                     # CHOCH confirmation (INCREASED: was 20)
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
    'OB': 45,        # Order Block (lowered from 90 - matches MEDIUM strength)
    'FVG': 60,       # Fair Value Gap (lowered from 80 - matches detection min)
    'BSL': 50,        # Buy Side Liquidity (uses confidence * 100)
    'SSL': 50,        # Sell Side Liquidity (uses confidence * 100)
    'min_acceptable': 40  # Reject POI below this (lowered from 65)
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
# PROBABILITY ENGINE (Phase 2 - Replaces Score System)
# ============================================================

# Base probabilities for each scenario type
BASE_PROBABILITY = {
    'CONTINUATION': 0.55,
    'PULLBACK': 0.50,
    'REVERSAL': 0.52,
    'ROLLBACK': 0.48
}

# Contribution weights for probability calculation
PROBABILITY_CONTRIBUTIONS = {
    'structure_strength': 0.20,
    'displacement_strength': 0.15,
    'poi_quality': 0.15,
    'sweep_strength': 0.15,
    'trigger_count': 0.08,
    'htf_alignment': 0.10,
    'distance_penalty': 0.15
}

# Minimum probability thresholds for each scenario
MIN_PROBABILITY_THRESHOLDS = {
    'CONTINUATION': 0.65,
    'PULLBACK': 0.60,
    'REVERSAL': 0.55,
    'ROLLBACK': 0.55
}

# Default fallback threshold when scenario type is not in MIN_PROBABILITY_THRESHOLDS
DEFAULT_MIN_PROBABILITY_THRESHOLD = 0.60

# ============================================================
# STRUCTURE ALIGNMENT MODIFIERS - Phase 2 Enhancement
# ============================================================
# These modifiers adjust probability based on HTF vs Entry TF structure alignment.
# They do NOT hard-block signals - threshold remains the final decision gate.

STRUCTURE_ALIGNMENT = {
    'htf_aligned': 1.10,      # HTF and Entry both bullish/bearish (+10% bonus)
    'ranging_penalty': 0.90,  # Entry TF mixed/ranging (-10% penalty, pullback/consolidation)
    'opposite': 0.75          # HTF and Entry opposite directions (-25% penalty, conflict)
}

# ============================================================
# REVERSAL DETECTION SETTINGS
# ============================================================
REVERSAL_SETTINGS = {
    'require_sweep': True,              # Entry layer: Must have liquidity sweep
    'require_structure_flip': False,    # REMOVED: Structure flip is confirmation layer
    'use_confirmation_modifier': True,  # Use ±8% probability modifier
    'confirmation_modifier_pct': 0.08,  # ±8% based on confirmation presence
    'displacement_bonus': True          # Bonus if displacement in reversal direction
}

# ============================================================
# SCENARIO CONFIGURATIONS (for API compatibility)
# ============================================================
SCENARIO_CONFIGS = {
    'CONTINUATION': {
        'name': 'Continuation',
        'description': 'Trend continuation scenario',
        'min_probability': MIN_PROBABILITY_THRESHOLDS['CONTINUATION'],
        'weights': CONTINUATION_WEIGHTS
    },
    'PULLBACK': {
        'name': 'Pullback',
        'description': 'Pullback to structure scenario',
        'min_probability': MIN_PROBABILITY_THRESHOLDS['PULLBACK'],
        'weights': PULLBACK_WEIGHTS,
        'distance': PULLBACK_DISTANCE
    },
    'REVERSAL': {
        'name': 'Reversal',
        'description': 'Trend reversal scenario',
        'min_probability': MIN_PROBABILITY_THRESHOLDS['REVERSAL'],
        'weights': REVERSAL_WEIGHTS,
        'settings': REVERSAL_SETTINGS
    },
    'ROLLBACK': {
        'name': 'Rollback',
        'description': 'Rollback to structure scenario',
        'min_probability': MIN_PROBABILITY_THRESHOLDS['ROLLBACK'],
        'weights': ROLLBACK_WEIGHTS,
        'distance': ROLLBACK_DISTANCE
    }
}

# ============================================================
# LEGACY CONSTANTS - Backward Compatibility ONLY
# ============================================================
# ⚠️ WARNING: These are NOT used in entry_scenarios.py (Phase 2 removed them)
# They exist ONLY for scenario_validation.py and other legacy validation scripts
# DO NOT USE these in active production code!
#
# Phase 2 Implementation Note:
# - The main entry_scenarios.py uses PROBABILITY-BASED selection (Phase 2)
# - These score-based constants are DEPRECATED
# - They remain here ONLY to prevent import errors in validation scripts
# - For production logic, see: MIN_PROBABILITY_THRESHOLDS (above)

MIN_SCENARIO_SCORE = 70  # Legacy - validation script only (NOT used in Phase 2)

MIN_TRIGGERS = {          # Legacy - validation script only (NOT used in Phase 2)
    'ROLLBACK': 2,
    'PULLBACK': 1,
    'CONTINUATION': 2,
    'REVERSAL': 2
}

PULLBACK_HIGH_QUALITY_THRESHOLD = 85  # Legacy - validation script only (NOT used in Phase 2)

# ============================================================
# PULLBACK Requirements (Fix #1)
# ============================================================
# ICT Principle: PULLBACK = Displacement → Retracement to POI → Continuation
# Without prior displacement a retracement may just be range movement.
PULLBACK_REQUIREMENTS = {
    'min_displacement_strength': 0.35,  # Minimum prior displacement strength
    'displacement_source': 'structure_tf',  # Must come from structure TF
}

# ============================================================
# CONTINUATION Consolidation Check (Fix #2)
# ============================================================
# ICT Principle: CONTINUATION = Trend → Consolidation/Pause → Breakout from POI
# Without prior consolidation, it's just displacement continuation.
CONSOLIDATION_CHECK = {
    'max_range_ratio': 0.40,   # Recent range < 40% of displacement strength = consolidation
    'consolidation_penalty': 0.70,  # -30% probability when no consolidation detected
    'lookback_candles': {
        '5m': 8,
        '15m': 6,
        '1h': 5,
        '4h': 4,
        '1d': 3,
    }
}

# ============================================================
# Multi-Pattern Confluence (Fix #6)
# ============================================================
# ICT Principle: Best setups occur when multiple patterns align at the same POI.
PATTERN_CONFLUENCE = {
    'bonus': 0.15,                         # +15% probability for multi-pattern confluence
    'min_probability_for_confluence': 0.50, # Pattern must be ≥50% to count for confluence
}

# ============================================================
# Pattern Types with Subtypes (Fix #5)
# ============================================================
PATTERN_TYPES = {
    'PULLBACK': {
        'subtypes': ['STRUCTURE_RETEST', 'OB_RETRACEMENT', 'FVG_FILL'],
        'description': 'Retracement to POI in trend direction'
    },
    'CONTINUATION': {
        'subtypes': ['DISPLACEMENT_BREAKOUT'],
        'description': 'Resumption after consolidation'
    },
    'REVERSAL': {
        'subtypes': ['LIQUIDITY_SWEEP_REVERSAL', 'CHOCH_REVERSAL'],
        'description': 'Change of direction after liquidity grab'
    }
}
