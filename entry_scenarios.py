"""
Entry Scenario Scoring System - ICT-compliant entry logic
Evaluates all 4 scenarios and selects best based on score

Author: galinborisov10-art
Date: 2026-02-10
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import logging
from datetime import datetime

from entry_scenario_config import (
    TRIGGER_WEIGHTS,
    TRIGGER_STRENGTH_THRESHOLDS,
    TRIGGER_SETTINGS,
    ROLLBACK_WEIGHTS,
    PULLBACK_WEIGHTS,
    CONTINUATION_WEIGHTS,
    REVERSAL_WEIGHTS,
    ROLLBACK_DISTANCE,
    PULLBACK_DISTANCE,
    CONTINUATION_DISTANCE,
    REVERSAL_DISTANCE,
    POI_QUALITY,
    POSITION_SIZE,
    MIN_SCENARIO_SCORE,
    MIN_TRIGGERS,
    PULLBACK_HIGH_QUALITY_THRESHOLD,
    REVERSAL_SETTINGS
)

logger = logging.getLogger(__name__)


# ============================================================
# PUBLIC API (единствена функция която се извиква отвън)
# ============================================================


def _safe_get(obj, attr, default=None):
    """Safely get attribute from object or dict"""
    if hasattr(obj, attr):
        return getattr(obj, attr)
    elif isinstance(obj, dict):
        return obj.get(attr, default)
    else:
        return default

def select_best_entry_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    entry_zone: Dict,
    timeframe: str
) -> Optional[Dict]:
    """
    Evaluate all 4 ICT entry scenarios and select the best one.
    
    Returns dict with scenario details OR None if no scenario scores above minimum.
    
    Return structure:
    {
        'scenario': 'ROLLBACK',
        'entry_zone': {
            'center': 49500.0,
            'low': 49400.9,
            'high': 49599.0,
            'source': 'ROLLBACK_BOS',
            'quality': 85,
            'distance_pct': 1.0,
            'distance_price': 500.0
        },
        'score': 85,
        'triggers': ['MSS/BOS', 'DISPLACEMENT'],
        'trigger_strength': 'HIGH',
        'reasoning': 'Rollback to BOS break level @ $49500 (1.0% away, 2 triggers)',
        'position_size_advisory': 100
    }
    """
    logger.info("=" * 60)
    logger.info("🎯 Entry Scenario Scoring System")
    logger.info("=" * 60)
    
    # Detect triggers
    triggers, trigger_score = _detect_triggers_weighted(current_price, ict_components, bias, timeframe)
    trigger_strength = _evaluate_trigger_strength(trigger_score)
    
    logger.info(f"Triggers detected: {triggers}")
    logger.info(f"Trigger score: {trigger_score} ({trigger_strength})")
    
    # Score all 4 scenarios
    scenarios = {}
    
    # 1. ROLLBACK
    rollback = _score_rollback_scenario(
        current_price, bias, ict_components, triggers, trigger_score
    )
    if rollback:
        scenarios['ROLLBACK'] = rollback
        logger.info(f"ROLLBACK score: {rollback['score']}")
    
    # 2. PULLBACK
    pullback = _score_pullback_scenario(
        current_price, bias, ict_components, triggers, trigger_score, entry_zone
    )
    if pullback:
        scenarios['PULLBACK'] = pullback
        logger.info(f"PULLBACK score: {pullback['score']}")
    
    # 3. CONTINUATION
    continuation = _score_continuation_scenario(
        current_price, bias, ict_components, triggers, trigger_score, trigger_strength
    )
    if continuation:
        scenarios['CONTINUATION'] = continuation
        logger.info(f"CONTINUATION score: {continuation['score']}")
    
    # 4. REVERSAL
    reversal = _score_reversal_scenario(
        current_price, bias, ict_components, triggers, trigger_score
    )
    if reversal:
        scenarios['REVERSAL'] = reversal
        logger.info(f"REVERSAL score: {reversal['score']}")
    
    # Filter by minimum score
    valid_scenarios = {k: v for k, v in scenarios.items() if v['score'] >= MIN_SCENARIO_SCORE}
    
    if not valid_scenarios:
        logger.warning(f"⚠️ No scenario scored above {MIN_SCENARIO_SCORE} minimum")
        return None
    
    # Select best scenario (highest score)
    best_scenario_name, best_scenario = max(valid_scenarios.items(), key=lambda x: x[1]['score'])
    
    logger.info("=" * 60)
    logger.info(f"🏆 BEST SCENARIO: {best_scenario_name} (score: {best_scenario['score']})")
    logger.info(f"   Reasoning: {best_scenario['reasoning']}")
    logger.info("=" * 60)
    
    return best_scenario


# ============================================================
# TRIGGER DETECTION (Weighted)
# ============================================================

def _detect_triggers_weighted(
    current_price: float,
    ict_components: Dict,
    bias: str,
    timeframe: str
) -> Tuple[List[str], int]:
    """
    Detect triggers and calculate weighted score.
    
    Returns: (trigger_list, total_score)
    """
    triggers = []
    total_score = 0
    
    # 1. MSS/BOS/CHOCH (Structure break)
    sb = ict_components.get('structure_break')
    if sb and sb.get('type') in ['MSS', 'BOS', 'CHOCH']:
        triggers.append('MSS/BOS')
        total_score += TRIGGER_WEIGHTS['MSS/BOS']
    
    # 2. Liquidity sweep (with recency check)
    sweeps = ict_components.get('liquidity_sweeps', [])
    if sweeps:
        sweep = sweeps[0]
        # Handle both dict and object
        if hasattr(sweep, 'candles_ago'):
            candles_ago = sweep.candles_ago
        elif isinstance(sweep, dict):
            candles_ago = sweep.candles_ago if hasattr(sweep, "candles_ago") else (sweep.get("candles_ago", 999) if isinstance(sweep, dict) else 999)
        else:
            candles_ago = 999
        recency_candles = TRIGGER_SETTINGS['liquidity_sweep_recency_candles'].get(
            timeframe,
            TRIGGER_SETTINGS['liquidity_sweep_recency_candles']['default']
        )
        
        for sweep in sweeps:
            candles_ago = sweep.candles_ago if hasattr(sweep, "candles_ago") else (sweep.get("candles_ago", 999) if isinstance(sweep, dict) else 999)
            if candles_ago <= recency_candles:
                triggers.append('LIQUIDITY_SWEEP')
                total_score += TRIGGER_WEIGHTS['LIQUIDITY_SWEEP']
                logger.debug(f"   Recent sweep detected ({candles_ago} candles ago)")
                break
    
    # 3. Displacement
    disp = ict_components.get('displacement')
    if disp and disp.get('detected', False):
        strength = disp.get('strength', 0)
        
        if strength >= TRIGGER_SETTINGS['displacement_min_strength']:
            triggers.append('DISPLACEMENT')
            
            # Weighted scoring based on displacement strength
            if strength >= TRIGGER_SETTINGS['displacement_strong_threshold']:
                total_score += TRIGGER_WEIGHTS['DISPLACEMENT']
                logger.debug(f"   Strong displacement: {strength:.2f}")
            else:
                # Partial score for medium displacement
                total_score += int(TRIGGER_WEIGHTS['DISPLACEMENT'] * 0.7)
                logger.debug(f"   Medium displacement: {strength:.2f}")
    
    # 4. Breaker/Mitigation
    if ict_components.get('breaker_blocks') or ict_components.get('mitigation_blocks'):
        triggers.append('BREAKER/MITIGATION')
        total_score += TRIGGER_WEIGHTS['BREAKER/MITIGATION']
    
    return triggers, total_score


def _evaluate_trigger_strength(trigger_score: int) -> str:
    """Evaluate trigger strength based on weighted score"""
    if trigger_score >= TRIGGER_STRENGTH_THRESHOLDS['HIGH']:
        return "HIGH"
    elif trigger_score >= TRIGGER_STRENGTH_THRESHOLDS['MEDIUM']:
        return "MEDIUM"
    else:
        return "LOW"


# ============================================================
# ROLLBACK SCENARIO SCORING
# ============================================================

def _score_rollback_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int
) -> Optional[Dict]:
    """
    Score ROLLBACK scenario: retest to structure break level
    
    Returns scenario dict with score OR None if invalid
    """
    sb = ict_components.get('structure_break')
    if not sb or sb.get('type') not in ['MSS', 'BOS', 'CHOCH']:
        return None
    
    break_level = sb.get('break_level')
    if not break_level:
        return None
    
    # Distance check
    distance_pct = abs(break_level - current_price) / current_price * 100
    
    if distance_pct < ROLLBACK_DISTANCE['min_pct'] * 100:
        logger.debug(f"   ROLLBACK: too close ({distance_pct:.1f}% < {ROLLBACK_DISTANCE['min_pct']*100:.0f}%)")
        return None
    
    if distance_pct > ROLLBACK_DISTANCE['max_pct'] * 100:
        logger.debug(f"   ROLLBACK: too far ({distance_pct:.1f}% > {ROLLBACK_DISTANCE['max_pct']*100:.0f}%)")
        return None
    
    # Already retested check
    if sb.get('retested', False):
        logger.debug(f"   ROLLBACK: break_level already retested")
        return None
    
    # Bias alignment check
    is_bullish = bias.upper() == "BULLISH"
    is_bearish = bias.upper() == "BEARISH"
    
    if is_bullish and break_level >= current_price:
        logger.debug(f"   ROLLBACK: BULLISH but break_level above current")
        return None
    
    if is_bearish and break_level <= current_price:
        logger.debug(f"   ROLLBACK: BEARISH but break_level below current")
        return None
    
    # Trigger requirement check
    if len(triggers) < MIN_TRIGGERS['ROLLBACK']:
        logger.debug(f"   ROLLBACK: insufficient triggers ({len(triggers)} < {MIN_TRIGGERS['ROLLBACK']})")
        return None
    
    # ============================================================
    # SCORE CALCULATION
    # ============================================================
    score = ROLLBACK_WEIGHTS['base_score']
    
    # Structure strength bonus
    structure_strength = sb.get('strength', 50)
    score += structure_strength * ROLLBACK_WEIGHTS['structure_strength_multiplier']
    
    # Trigger bonuses
    if 'DISPLACEMENT' in triggers:
        score += ROLLBACK_WEIGHTS['displacement_bonus']
    
    if 'LIQUIDITY_SWEEP' in triggers:
        score += ROLLBACK_WEIGHTS['liquidity_sweep_bonus']
    
    # Additional trigger bonus
    extra_triggers = len(triggers) - MIN_TRIGGERS['ROLLBACK']
    if extra_triggers > 0:
        score += extra_triggers * ROLLBACK_WEIGHTS['trigger_count_bonus']
    
    # Distance penalty
    score += distance_pct * ROLLBACK_WEIGHTS['distance_penalty_per_pct']
    
    # Cap score at 100
    score = min(100, max(0, score))
    
    # Build entry zone
    buffer = ROLLBACK_DISTANCE['buffer_pct']
    entry_zone = {
        'center': break_level,
        'low': break_level * (1 - buffer),
        'high': break_level * (1 + buffer),
        'source': f"ROLLBACK_{sb.get('type')}",
        'quality': int(structure_strength),
        'distance_pct': distance_pct,
        'distance_price': abs(break_level - current_price)
    }
    
    return {
        'scenario': 'ROLLBACK',
        'entry_zone': entry_zone,
        'score': int(score),
        'triggers': triggers,
        'trigger_strength': _evaluate_trigger_strength(trigger_score),
        'reasoning': f"Rollback to {sb.get('type')} break level @ ${break_level:.2f} ({distance_pct:.1f}% away, {len(triggers)} triggers)",
        'position_size_advisory': POSITION_SIZE['ROLLBACK']
    }


# ============================================================
# PULLBACK SCENARIO SCORING
# ============================================================

def _score_pullback_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
    entry_zone: Dict
) -> Optional[Dict]:
    """
    Score PULLBACK scenario: retracement to POI (OB/FVG/BSL/SSL)
    """
    poi_candidates = []
    is_bullish = bias.upper() == "BULLISH"
    is_bearish = bias.upper() == "BEARISH"
    
    # 1. Check Order Blocks
    obs = ict_components.get('order_blocks', [])
    for ob in obs:
        ob_type = str(ob.type if hasattr(ob, "type") else (_safe_get(ob, "type", "") if isinstance(ob, dict) else "")).upper()
        ob_center = ((ob.zone_low if hasattr(ob, 'zone_low') else (ob.zone_low if hasattr(ob, 'zone_low') else (_safe_get(ob, 'zone_low', 0) if isinstance(ob, dict) else 0) if isinstance(ob, dict) else 0)) + (ob.zone_high if hasattr(ob, 'zone_high') else (ob.zone_high if hasattr(ob, 'zone_high') else (_safe_get(ob, 'zone_high', 0) if isinstance(ob, dict) else 0) if isinstance(ob, dict) else 0))) / 2
        
        if is_bullish and 'BULLISH' in ob_type and ob_center < current_price:
            distance_pct = abs(ob_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                poi_candidates.append({
                    'type': 'OB',
                    'price': ob_center,
                    'low': ob.zone_low if hasattr(ob, 'zone_low') else (ob.get('zone_low') if isinstance(ob, dict) else None),
                    'high': ob.zone_high if hasattr(ob, 'zone_high') else (ob.get('zone_high') if isinstance(ob, dict) else None),
                    'distance_pct': distance_pct,
                    'quality': POI_QUALITY['OB']
                })
        
        if is_bearish and 'BEARISH' in ob_type and ob_center > current_price:
            distance_pct = abs(ob_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                poi_candidates.append({
                    'type': 'OB',
                    'price': ob_center,
                    'low': ob.zone_low if hasattr(ob, 'zone_low') else (ob.get('zone_low') if isinstance(ob, dict) else None),
                    'high': ob.zone_high if hasattr(ob, 'zone_high') else (ob.get('zone_high') if isinstance(ob, dict) else None),
                    'distance_pct': distance_pct,
                    'quality': POI_QUALITY['OB']
                })
    
    # 2. Check FVGs
    fvgs = ict_components.get('fvgs', [])
    for fvg in fvgs:
        fvg_type = getattr(fvg, 'type', None) or _safe_get(fvg, 'type', '')
        fvg_center = (fvg.bottom if hasattr(fvg, 'bottom') else (_safe_get(fvg, 'bottom', 0) if isinstance(fvg, dict) else 0) + fvg.top if hasattr(fvg, 'top') else (_safe_get(fvg, 'top', 0) if isinstance(fvg, dict) else 0)) / 2
        
        if is_bullish and 'BULLISH' in str(fvg_type).upper() and fvg_center < current_price:
            distance_pct = abs(fvg_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                poi_candidates.append({
                    'type': 'FVG',
                    'price': fvg_center,
                    'low': fvg.bottom if hasattr(fvg, 'bottom') else (_safe_get(fvg, 'bottom') if isinstance(fvg, dict) else None),
                    'high': fvg.top if hasattr(fvg, 'top') else (_safe_get(fvg, 'top') if isinstance(fvg, dict) else None),
                    'distance_pct': distance_pct,
                    'quality': POI_QUALITY['FVG']
                })
        
        if is_bearish and 'BEARISH' in str(fvg_type).upper() and fvg_center > current_price:
            distance_pct = abs(fvg_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                poi_candidates.append({
                    'type': 'FVG',
                    'price': fvg_center,
                    'low': fvg.bottom if hasattr(fvg, 'bottom') else (_safe_get(fvg, 'bottom') if isinstance(fvg, dict) else None),
                    'high': fvg.top if hasattr(fvg, 'top') else (_safe_get(fvg, 'top') if isinstance(fvg, dict) else None),
                    'distance_pct': distance_pct,
                    'quality': POI_QUALITY['FVG']
                })
    
    # 3. Check Liquidity zones (BSL/SSL)
    liq_zones = ict_components.get('liquidity_zones', [])
    for liq in liq_zones:
        liq_type = (liq.type if hasattr(liq, 'type') else (_safe_get(liq, 'type', '') if isinstance(liq, dict) else '')).upper()
        liq_price = liq.price if hasattr(liq, 'price') else (liq.price if hasattr(liq, 'price') else (_safe_get(liq, 'price', 0) if isinstance(liq, dict) else 0) if isinstance(liq, dict) else 0)
        
        if is_bullish and 'BSL' in liq_type and liq_price < current_price:
            distance_pct = abs(liq_price - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                poi_candidates.append({
                    'type': 'BSL',
                    'price': liq_price,
                    'low': liq_price * 0.999,
                    'high': liq_price * 1.001,
                    'distance_pct': distance_pct,
                    'quality': POI_QUALITY['BSL']
                })
        
        if is_bearish and 'SSL' in liq_type and liq_price > current_price:
            distance_pct = abs(liq_price - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                poi_candidates.append({
                    'type': 'SSL',
                    'price': liq_price,
                    'low': liq_price * 0.999,
                    'high': liq_price * 1.001,
                    'distance_pct': distance_pct,
                    'quality': POI_QUALITY['SSL']
                })
    
    if not poi_candidates:
        return None
    
    # Filter by minimum quality
    poi_candidates = [p for p in poi_candidates if p['quality'] >= POI_QUALITY['min_acceptable']]
    
    if not poi_candidates:
        logger.debug("   PULLBACK: no POI with acceptable quality")
        return None
    
    # Select best POI (highest quality, then closest)
    best_poi = max(poi_candidates, key=lambda x: (x['quality'], -x['distance_pct']))
    
    # Trigger requirement check (flexible for high-quality POI)
    if len(triggers) < MIN_TRIGGERS['PULLBACK']:
        if best_poi['quality'] < PULLBACK_HIGH_QUALITY_THRESHOLD:
            logger.debug(f"   PULLBACK: insufficient triggers and POI quality < {PULLBACK_HIGH_QUALITY_THRESHOLD}")
            return None
        else:
            logger.info(f"   ⚠️ PULLBACK accepted with 1 trigger (POI quality {best_poi['quality']})")
    
    # ============================================================
    # SCORE CALCULATION
    # ============================================================
    score = PULLBACK_WEIGHTS['base_score']
    
    # POI quality bonus
    score += best_poi['quality'] * PULLBACK_WEIGHTS['poi_quality_multiplier']
    
    # Trigger count bonus
    score += len(triggers) * PULLBACK_WEIGHTS['trigger_count_bonus']
    
    # Structure trigger bonus
    if 'MSS/BOS' in triggers:
        score += PULLBACK_WEIGHTS['structure_trigger_bonus']
    
    # Distance penalty
    score += best_poi['distance_pct'] * PULLBACK_WEIGHTS['distance_penalty_per_pct']
    
    # Cap score
    score = min(100, max(0, score))
    
    # Build entry zone
    buffer = PULLBACK_DISTANCE['buffer_pct']
    entry_zone = {
        'center': best_poi['price'],
        'low': best_poi['low'] * (1 - buffer),
        'high': best_poi['high'] * (1 + buffer),
        'source': f"PULLBACK_{best_poi['type']}",
        'quality': best_poi['quality'],
        'distance_pct': best_poi['distance_pct'],
        'distance_price': abs(best_poi['price'] - current_price)
    }
    
    return {
        'scenario': 'PULLBACK',
        'entry_zone': entry_zone,
        'score': int(score),
        'triggers': triggers,
        'trigger_strength': _evaluate_trigger_strength(trigger_score),
        'reasoning': f"Pullback to {best_poi['type']} @ ${best_poi['price']:.2f} ({best_poi['distance_pct']:.1f}% away, quality {best_poi['quality']})",
        'position_size_advisory': POSITION_SIZE['PULLBACK']
    }


# ============================================================
# CONTINUATION SCENARIO SCORING
# ============================================================

def _score_continuation_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
    trigger_strength: str
) -> Optional[Dict]:
    """
    Score CONTINUATION scenario: minimal retracement, high momentum
    """
    # Strict trigger requirement
    if len(triggers) < MIN_TRIGGERS['CONTINUATION']:
        logger.debug(f"   CONTINUATION: insufficient triggers ({len(triggers)} < {MIN_TRIGGERS['CONTINUATION']})")
        return None
    
    # Must have displacement OR structure trigger
    has_momentum = 'DISPLACEMENT' in triggers or 'MSS/BOS' in triggers
    if not has_momentum:
        logger.debug("   CONTINUATION: no displacement or structure trigger")
        return None
    
    # Check for POI in path (reject if found)
    is_bullish = bias.upper() == "BULLISH"
    check_range = CONTINUATION_DISTANCE['poi_check_range_pct']
    
    obs = ict_components.get('order_blocks', [])
    for ob in obs:
        ob_center = (ob.zone_low if hasattr(ob, 'zone_low') else (_safe_get(ob, 'zone_low', 0) if isinstance(ob, dict) else 0) + ob.zone_high if hasattr(ob, 'zone_high') else (_safe_get(ob, 'zone_high', 0) if isinstance(ob, dict) else 0)) / 2
        
        if is_bullish and current_price * (1 - check_range) <= ob_center <= current_price:
            logger.debug(f"   CONTINUATION: found OB in path @ ${ob_center:.2f}")
            return None
        
        if not is_bullish and current_price <= ob_center <= current_price * (1 + check_range):
            logger.debug(f"   CONTINUATION: found OB in path @ ${ob_center:.2f}")
            return None
    
    # ============================================================
    # SCORE CALCULATION
    # ============================================================
    score = CONTINUATION_WEIGHTS['base_score']
    
    # Trigger count bonus (max 2 extra triggers)
    extra_triggers = min(len(triggers) - MIN_TRIGGERS['CONTINUATION'], 2)
    score += extra_triggers * CONTINUATION_WEIGHTS['trigger_count_bonus']
    
    # Strong displacement bonus
    disp = ict_components.get('displacement', {})
    if disp.get('strength', 0) >= TRIGGER_SETTINGS['displacement_strong_threshold']:
        score += CONTINUATION_WEIGHTS['displacement_strong_bonus']
    
    # Structure trigger bonus
    if 'MSS/BOS' in triggers:
        score += CONTINUATION_WEIGHTS['structure_trigger_bonus']
    
    # No POI in range bonus
    score += CONTINUATION_WEIGHTS['no_poi_in_range_bonus']
    
    # Cap score
    score = min(100, max(0, score))
    
    # Calculate entry price
    retracement = CONTINUATION_DISTANCE['retracement_pct']
    entry_price = current_price * (1 - retracement) if is_bullish else current_price * (1 + retracement)
    
    buffer = CONTINUATION_DISTANCE['buffer_pct']
    entry_zone = {
        'center': entry_price,
        'low': entry_price * (1 - buffer),
        'high': entry_price * (1 + buffer),
        'source': 'CONTINUATION',
        'quality': 75,  # Medium quality (no specific POI)
        'distance_pct': retracement * 100,
        'distance_price': abs(entry_price - current_price)
    }
    
    # Dynamic position size based on trigger count
    if len(triggers) >= 3:
        position_size = POSITION_SIZE['CONTINUATION']['3_triggers']
    else:
        position_size = POSITION_SIZE['CONTINUATION']['2_triggers']
    
    return {
        'scenario': 'CONTINUATION',
        'entry_zone': entry_zone,
        'score': int(score),
        'triggers': triggers,
        'trigger_strength': trigger_strength,
        'reasoning': f"Continuation with {len(triggers)} triggers (minimal retracement {retracement*100:.1f}%)",
        'position_size_advisory': position_size
    }


# ============================================================
# REVERSAL SCENARIO SCORING
# ============================================================

def _score_reversal_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int
) -> Optional[Dict]:
    """
    Score REVERSAL scenario: market structure flip with liquidity sweep
    """
    # Strict trigger requirement
    if len(triggers) < MIN_TRIGGERS['REVERSAL']:
        logger.debug(f"   REVERSAL: insufficient triggers ({len(triggers)} < {MIN_TRIGGERS['REVERSAL']})")
        return None
    
    # Check for liquidity sweep (required)
    if REVERSAL_SETTINGS['require_sweep']:
        if 'LIQUIDITY_SWEEP' not in triggers:
            logger.debug("   REVERSAL: no liquidity sweep detected")
            return None
    
    # Check for structure flip (MSS/CHOCH in opposite direction)
    sb = ict_components.get('structure_break')
    if REVERSAL_SETTINGS['require_structure_flip']:
        if not sb or sb.get('type') not in ['MSS', 'CHOCH']:
            logger.debug("   REVERSAL: no structure flip (MSS/CHOCH) detected")
            return None
        
        # Check if structure flip is in opposite direction to current bias
        sb_direction = sb.get('direction', '').upper()
        bias_upper = bias.upper()
        
        # REVERSAL detection: validate structure flip direction
        if sb_direction:
            bias_upper = bias.upper()
            if bias_upper == 'BULLISH' and sb_direction == 'BULLISH':
                logger.debug("   REVERSAL: same direction as bias")
                return None
            if bias_upper == 'BEARISH' and sb_direction == 'BEARISH':
                logger.debug("   REVERSAL: same direction as bias")
                return None
    
    # Entry can be either rollback to break_level OR pullback to first POI
    break_level = sb.get('break_level') if sb else None
    entry_price = None
    entry_type = None
    distance_pct = 0
    
    # Option 1: Rollback to reversal break level
    if break_level:
        distance_to_break = abs(break_level - current_price) / current_price * 100
        
        if REVERSAL_DISTANCE['min_pct'] * 100 <= distance_to_break <= REVERSAL_DISTANCE['max_pct'] * 100:
            entry_price = break_level
            entry_type = 'BREAK_LEVEL'
            distance_pct = distance_to_break
    
    # Option 2: Pullback to first POI (if no valid break_level)
    if not entry_price:
        obs = ict_components.get('order_blocks', [])
        is_bullish_bias = bias.upper() == 'BULLISH'
        logger.debug(f"   REVERSAL POI search: {len(obs)} OBs, bias={bias.upper()}")
        
        for ob in obs:
            ob_type = str(ob.type if hasattr(ob, "type") else (_safe_get(ob, "type", "") if isinstance(ob, dict) else "")).upper()
            ob_center = (ob.zone_low if hasattr(ob, 'zone_low') else (_safe_get(ob, 'zone_low', 0) if isinstance(ob, dict) else 0) + ob.zone_high if hasattr(ob, 'zone_high') else (_safe_get(ob, 'zone_high', 0) if isinstance(ob, dict) else 0)) / 2
            distance_to_ob = abs(ob_center - current_price) / current_price * 100
            
            # Step 2: Correct REVERSAL POI direction logic
            # BULLISH→BEARISH: find BEARISH OB below price (price pulls back down)
            # BEARISH→BULLISH: find BULLISH OB above price (price pulls back up)
            
            if is_bullish_bias and 'BEARISH' in ob_type and ob_center < current_price:
                logger.debug(f"      Found BEARISH OB @ ${ob_center:.2f}, distance={distance_to_ob:.2f}%")
                
                if REVERSAL_DISTANCE['min_pct'] * 100 <= distance_to_ob <= REVERSAL_DISTANCE['max_pct'] * 100:
                    entry_price = ob_center
                    entry_type = 'POI'
                    distance_pct = distance_to_ob
                    logger.debug(f"      ✅ REVERSAL POI accepted")
                    break
                else:
                    logger.debug(f"      ❌ Distance out of range: {distance_to_ob:.2f}% not in [{REVERSAL_DISTANCE['min_pct']*100:.1f}%, {REVERSAL_DISTANCE['max_pct']*100:.1f}%]")
            
            elif not is_bullish_bias and 'BULLISH' in ob_type and ob_center > current_price:
                logger.debug(f"      Found BULLISH OB @ ${ob_center:.2f}, distance={distance_to_ob:.2f}%")
                
                if REVERSAL_DISTANCE['min_pct'] * 100 <= distance_to_ob <= REVERSAL_DISTANCE['max_pct'] * 100:
                    entry_price = ob_center
                    entry_type = 'POI'
                    distance_pct = distance_to_ob
                    logger.debug(f"      ✅ REVERSAL POI accepted")
                    break
                else:
                    logger.debug(f"      ❌ Distance out of range: {distance_to_ob:.2f}% not in [{REVERSAL_DISTANCE['min_pct']*100:.1f}%, {REVERSAL_DISTANCE['max_pct']*100:.1f}%]")
    if not entry_price:
        obs = ict_components.get('order_blocks', [])
        is_bullish_bias = bias.upper() == 'BULLISH'
        logger.debug(f"   REVERSAL POI search: {len(obs)} OBs, bias={bias.upper()}")
        
        for ob in obs:
            ob_type = str(ob.type if hasattr(ob, "type") else (_safe_get(ob, "type", "") if isinstance(ob, dict) else "")).upper()
            ob_center = (ob.zone_low if hasattr(ob, 'zone_low') else (_safe_get(ob, 'zone_low', 0) if isinstance(ob, dict) else 0) + ob.zone_high if hasattr(ob, 'zone_high') else (_safe_get(ob, 'zone_high', 0) if isinstance(ob, dict) else 0)) / 2
            distance_to_ob = abs(ob_center - current_price) / current_price * 100
            
            # Step 2: Correct REVERSAL POI direction logic
            # BULLISH→BEARISH: find BEARISH OB below price (price pulls back down)
            # BEARISH→BULLISH: find BULLISH OB above price (price pulls back up)
            
            if is_bullish_bias and 'BEARISH' in ob_type and ob_center < current_price:
                logger.debug(f"      Found BEARISH OB @ ${ob_center:.2f}, distance={distance_to_ob:.2f}%")
                
                if REVERSAL_DISTANCE['min_pct'] * 100 <= distance_to_ob <= REVERSAL_DISTANCE['max_pct'] * 100:
                    entry_price = ob_center
                    entry_type = 'POI'
                    distance_pct = distance_to_ob
                    logger.debug(f"      ✅ REVERSAL POI accepted")
                    break
                else:
                    logger.debug(f"      ❌ Distance out of range: {distance_to_ob:.2f}% not in [{REVERSAL_DISTANCE['min_pct']*100:.1f}%, {REVERSAL_DISTANCE['max_pct']*100:.1f}%]")
            
            elif not is_bullish_bias and 'BULLISH' in ob_type and ob_center > current_price:
                logger.debug(f"      Found BULLISH OB @ ${ob_center:.2f}, distance={distance_to_ob:.2f}%")
                
                if REVERSAL_DISTANCE['min_pct'] * 100 <= distance_to_ob <= REVERSAL_DISTANCE['max_pct'] * 100:
                    entry_price = ob_center
                    entry_type = 'POI'
                    distance_pct = distance_to_ob
                    logger.debug(f"      ✅ REVERSAL POI accepted")
                    break
                else:
                    logger.debug(f"      ❌ Distance out of range: {distance_to_ob:.2f}% not in [{REVERSAL_DISTANCE['min_pct']*100:.1f}%, {REVERSAL_DISTANCE['max_pct']*100:.1f}%]")
    if not entry_price:
        obs = ict_components.get('order_blocks', [])
        is_bullish_bias = bias.upper() == 'BULLISH'
        logger.debug(f"   REVERSAL POI search: {len(obs)} OBs, bias={bias.upper()}")
        
        for ob in obs:
            ob_type = str(ob.type if hasattr(ob, "type") else (_safe_get(ob, "type", "") if isinstance(ob, dict) else "")).upper()
            ob_center = (ob.zone_low if hasattr(ob, 'zone_low') else (_safe_get(ob, 'zone_low', 0) if isinstance(ob, dict) else 0) + ob.zone_high if hasattr(ob, 'zone_high') else (_safe_get(ob, 'zone_high', 0) if isinstance(ob, dict) else 0)) / 2
            distance_to_ob = abs(ob_center - current_price) / current_price * 100
            
            # Step 2: Correct REVERSAL POI direction logic
            # BULLISH→BEARISH: find BEARISH OB below price (price pulls back down)
            # BEARISH→BULLISH: find BULLISH OB above price (price pulls back up)
            
            if is_bullish_bias and 'BEARISH' in ob_type and ob_center < current_price:
                logger.debug(f"      Found BEARISH OB @ ${ob_center:.2f}, distance={distance_to_ob:.2f}%")
                
                if REVERSAL_DISTANCE['min_pct'] * 100 <= distance_to_ob <= REVERSAL_DISTANCE['max_pct'] * 100:
                    entry_price = ob_center
                    entry_type = 'POI'
                    distance_pct = distance_to_ob
                    logger.debug(f"      ✅ REVERSAL POI accepted")
                    break
                else:
                    logger.debug(f"      ❌ Distance out of range: {distance_to_ob:.2f}% not in [{REVERSAL_DISTANCE['min_pct']*100:.1f}%, {REVERSAL_DISTANCE['max_pct']*100:.1f}%]")
            
            elif not is_bullish_bias and 'BULLISH' in ob_type and ob_center > current_price:
                logger.debug(f"      Found BULLISH OB @ ${ob_center:.2f}, distance={distance_to_ob:.2f}%")
                
                if REVERSAL_DISTANCE['min_pct'] * 100 <= distance_to_ob <= REVERSAL_DISTANCE['max_pct'] * 100:
                    entry_price = ob_center
                    entry_type = 'POI'
                    distance_pct = distance_to_ob
                    logger.debug(f"      ✅ REVERSAL POI accepted")
                    break
                else:
                    logger.debug(f"      ❌ Distance out of range: {distance_to_ob:.2f}% not in [{REVERSAL_DISTANCE['min_pct']*100:.1f}%, {REVERSAL_DISTANCE['max_pct']*100:.1f}%]")
        logger.debug("   REVERSAL: no valid entry point found")
        return None
    
    # ============================================================
    # SCORE CALCULATION
    # ============================================================
    score = REVERSAL_WEIGHTS['base_score']
    
    # Sweep bonus
    score += REVERSAL_WEIGHTS['sweep_bonus']
    
    # Structure flip bonus
    if sb and sb.get('type') == 'CHOCH':
        score += REVERSAL_WEIGHTS['choch_bonus']
    elif sb and sb.get('type') == 'MSS':
        score += REVERSAL_WEIGHTS['mss_bonus']
    
    # Displacement in reversal direction bonus
    disp = ict_components.get('displacement', {})
    if REVERSAL_SETTINGS['displacement_bonus']:
        if disp.get('detected') and disp.get('strength', 0) >= TRIGGER_SETTINGS['displacement_min_strength']:
            score += REVERSAL_WEIGHTS['displacement_contra_bonus']
    
    # Additional trigger bonus
    extra_triggers = len(triggers) - MIN_TRIGGERS['REVERSAL']
    if extra_triggers > 0:
        score += extra_triggers * REVERSAL_WEIGHTS['trigger_count_bonus']
    
    # Cap score
    score = min(100, max(0, score))
    
    # Build entry zone
    buffer = REVERSAL_DISTANCE['buffer_pct']
    entry_zone = {
        'center': entry_price,
        'low': entry_price * (1 - buffer),
        'high': entry_price * (1 + buffer),
        'source': f"REVERSAL_{entry_type}",
        'quality': 80,  # High quality (reversal setup)
        'distance_pct': distance_pct,
        'distance_price': abs(entry_price - current_price)
    }
    
    return {
        'scenario': 'REVERSAL',
        'entry_zone': entry_zone,
        'score': int(score),
        'triggers': triggers,
        'trigger_strength': _evaluate_trigger_strength(trigger_score),
        'reasoning': f"Reversal setup with sweep + {sb.get('type')} @ ${entry_price:.2f} ({distance_pct:.1f}% away)",
        'position_size_advisory': POSITION_SIZE['REVERSAL']
    }
