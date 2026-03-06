"""
Entry Scenario Scoring System - ICT-compliant entry logic
Evaluates all 4 scenarios and selects best based on score

Author: galinborisov10-art
Date: 2026-02-10
"""

from typing import Dict, List, Optional, Tuple, Any, TYPE_CHECKING
from dataclasses import dataclass
import logging
from datetime import datetime

if TYPE_CHECKING:
    from timeframe_contract import TimeframeHierarchy

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
    BASE_PROBABILITY,
    PROBABILITY_CONTRIBUTIONS,
    MIN_PROBABILITY_THRESHOLDS,
    REVERSAL_SETTINGS
)

logger = logging.getLogger(__name__)


# ===================================================================
# TIMEFRAME-ADAPTIVE RECENCY THRESHOLDS
# ===================================================================
# Components on higher timeframes naturally have older candles_ago values.
# A 50-candle-old component on 1d = 50 days (acceptable for swing trades)
# A 50-candle-old component on 15m = 12.5 hours (too stale)
#
# APPROVED VALUES (conservative approach):
# - 1d timeframe: max 50 candles
# - 1w timeframe: max 70 candles
# ===================================================================

RECENCY_THRESHOLDS = {
    # Structure Break recency for CONTINUATION scenario
    'structure_break_continuation': {
        '1m': 15, '5m': 20, '15m': 25, '30m': 30,
        '1h': 40, '2h': 50, '4h': 60, '6h': 60,
        '8h': 60, '12h': 70, '1d': 50, '3d': 60, '1w': 70
    },
    
    # Structure Break recency for ROLLBACK scenario (slightly more lenient)
    'structure_break_rollback': {
        '1m': 20, '5m': 25, '15m': 30, '30m': 35,
        '1h': 50, '2h': 60, '4h': 70, '6h': 70,
        '8h': 70, '12h': 80, '1d': 60, '3d': 70, '1w': 80
    },
    
    # Liquidity Sweep recency for REVERSAL scenario
    'liquidity_sweep': {
        '1m': 10, '5m': 15, '15m': 20, '30m': 25,
        '1h': 50, '2h': 70, '4h': 100, '6h': 100,  # Increased for realistic sweep detection
        '8h': 100, '12h': 100, '1d': 100, '3d': 120, '1w': 150  # Extended for higher TFs
    },
    
    # General component filtering (Order Blocks, FVGs)
    'component_general': {
        '1m': 20, '5m': 25, '15m': 30, '30m': 35,
        '1h': 50, '2h': 60, '4h': 70, '6h': 70,
        '8h': 70, '12h': 80, '1d': 60, '3d': 70, '1w': 80
    }
}

def get_recency_threshold(component_type: str, timeframe: str) -> int:
    """
    Get timeframe-adaptive recency threshold for specific component type.
    
    Args:
        component_type: One of 'structure_break_continuation', 'structure_break_rollback',
                       'liquidity_sweep', 'component_general'
        timeframe: Trading timeframe (e.g., '1d', '4h', '1h')
        
    Returns:
        Maximum candles_ago threshold for this component/timeframe combination
        
    Example:
        get_recency_threshold('liquidity_sweep', '1d') → 50
        get_recency_threshold('liquidity_sweep', '1h') → 30
    """
    thresholds = RECENCY_THRESHOLDS.get(component_type, RECENCY_THRESHOLDS['component_general'])
    return thresholds.get(timeframe, 50)  # Default 50 if timeframe not found


# ============================================================
# SCENARIO PRIORITY - For Deterministic Tie-Breaking (Phase 2)
# ============================================================

# Priority for tie-breaking when scenarios have equal probability
# Lower number = higher priority
SCENARIO_PRIORITY = {
    'CONTINUATION': 1,  # Highest priority in ties (strong trend + momentum)
    'PULLBACK': 2,      # High priority (structure retest)
    'REVERSAL': 3,      # Medium priority (requires multiple confirmations)
    'ROLLBACK': 4       # Lowest priority (risky, distance-dependent)
}


# ============================================================
# BEHAVIORAL CORE GATE - Extension Limits
# ============================================================

MAX_EXTENSION_PCT = {
    '15m': 2.0,
    '30m': 2.5,
    '1h': 3.0,
    '2h': 4.0,
    '4h': 5.0,
    '1d': 7.0,
    'default': 5.0
}


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


def _get_ob_center(ob: Any) -> float:
    """
    Safely extract center price from Order Block object or dict.
    
    Args:
        ob: Order Block object or dictionary
        
    Returns:
        Center price (average of zone_low and zone_high)
    """
    zone_low = _safe_get(ob, 'zone_low', 0)
    zone_high = _safe_get(ob, 'zone_high', 0)
    return (zone_low + zone_high) / 2.0


def select_best_entry_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    entry_zone: Dict,
    timeframe: str,
    tf_hierarchy: Optional['TimeframeHierarchy'] = None
) -> Tuple[Optional[Dict], Any]:
    """
    Evaluate all 4 ICT entry scenarios and select the best one.
    
    Returns:
        Tuple[Optional[Dict], Any]:
            - Dict: JSON-safe scenario data (or None)
            - Any: POI reference object for internal use (or None)
    
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
        'position_size_advisory': 100,
        'poi_type': 'OB',
        'poi_data': {...},
        'invalidation_anchor': {...}
    }
    """
    logger.info("=" * 60)
    logger.info("🎯 Entry Scenario Evaluation System (Probability-Based)")
    logger.info("=" * 60)
    
    # Detect triggers
    triggers, trigger_score = _detect_triggers_weighted(current_price, ict_components, bias, timeframe)
    trigger_strength = _evaluate_trigger_strength(trigger_score)
    
    logger.info(f"Triggers detected: {triggers}")
    logger.info(f"Trigger score: {trigger_score} ({trigger_strength})")
    
    # ✅ Extract timeframes per Timeframe Contract layer
    signal_tf = timeframe  # Entry layer (OB, FVG, Liquidity, Sweeps)
    confirmation_tf = tf_hierarchy.confirmation_tf if tf_hierarchy else timeframe  # Confirmation layer (BOS/MSS, Displacement)
    structure_tf = tf_hierarchy.structure_tf if tf_hierarchy else timeframe  # Structure layer (HTF Bias only - not used in scenarios)
    
    logger.info(f"🔍 Timeframe Contract Layers:")
    logger.info(f"   Entry Layer (signal_tf): {signal_tf} → OB, FVG, Liquidity, Sweeps")
    logger.info(f"   Confirmation Layer (confirmation_tf): {confirmation_tf} → BOS/MSS, Displacement")
    logger.info(f"   Structure Layer (structure_tf): {structure_tf} → HTF Bias only (context)")
    
    # Evaluate all 4 scenarios
    scenarios = {}
    poi_refs = {}
    
    # 1. ROLLBACK
    rollback_dict, rollback_ref = _score_rollback_scenario(
        current_price, bias, ict_components, triggers, trigger_score, signal_tf
    )
    if rollback_dict:
        scenarios['ROLLBACK'] = rollback_dict
        poi_refs['ROLLBACK'] = rollback_ref
        logger.info(f"ROLLBACK probability: {rollback_dict.get('probability', 0):.3f}")
    
    # 2. PULLBACK
    pullback_dict, pullback_ref = _score_pullback_scenario(
        current_price, bias, ict_components, triggers, trigger_score, entry_zone
    )
    if pullback_dict:
        scenarios['PULLBACK'] = pullback_dict
        poi_refs['PULLBACK'] = pullback_ref
        logger.info(f"PULLBACK probability: {pullback_dict.get('probability', 0):.3f}")
    
    # 3. CONTINUATION
    continuation_dict, continuation_ref = _score_continuation_scenario(
        current_price, bias, ict_components, triggers, trigger_score, trigger_strength, signal_tf
    )
    if continuation_dict:
        scenarios['CONTINUATION'] = continuation_dict
        poi_refs['CONTINUATION'] = continuation_ref
        logger.info(f"CONTINUATION probability: {continuation_dict.get('probability', 0):.3f}")
    
    # 4. REVERSAL
    reversal_dict, reversal_ref = _score_reversal_scenario(
        current_price, bias, ict_components, triggers, trigger_score, signal_tf
    )
    if reversal_dict:
        scenarios['REVERSAL'] = reversal_dict
        poi_refs['REVERSAL'] = reversal_ref
        logger.info(f"REVERSAL probability: {reversal_dict.get('probability', 0):.3f}")
    
    # Step 1: Filter by eligible flag
    eligible_scenarios = {
        k: v for k, v in scenarios.items() 
        if v.get('eligible', False)
    }
    
    if not eligible_scenarios:
        logger.warning("⚠️ No eligible scenarios (all failed behavioral core validation)")
        return None, None
    
    # Step 2: Select highest probability with deterministic tie-breaking
    # If multiple scenarios have equal probability, priority is used
    best_scenario_name = max(
        eligible_scenarios,
        key=lambda k: (
            eligible_scenarios[k].get('probability', 0),  # Primary: highest probability
            -SCENARIO_PRIORITY.get(k, 999)  # Tie-break: scenario priority (negative for descending)
        )
    )
    best_scenario_dict = eligible_scenarios[best_scenario_name]
    best_probability = best_scenario_dict.get('probability', 0)
    best_poi_ref = poi_refs.get(best_scenario_name)
    
    # Step 3: Apply probability threshold check
    threshold = MIN_PROBABILITY_THRESHOLDS.get(best_scenario_name, 0.60)
    
    if best_probability < threshold:
        logger.warning(
            f"⚠️ Best scenario {best_scenario_name} probability {best_probability:.3f} "
            f"< threshold {threshold:.3f} → NO TRADE"
        )
        return None, None
    
    logger.info("=" * 60)
    logger.info(f"🏆 BEST SCENARIO: {best_scenario_name} (probability: {best_probability:.3f}, threshold: {threshold:.3f})")
    logger.info(f"   Reasoning: {best_scenario_dict['reasoning']}")
    logger.info("=" * 60)
    
    return best_scenario_dict, best_poi_ref



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
# PROBABILITY ENGINE - Phase 2
# ============================================================

def _normalize_trigger_count(trigger_count: int, max_triggers: int = 4) -> float:
    """
    Normalize trigger count to 0.0-1.0 range.
    
    Args:
        trigger_count: Number of detected triggers
        max_triggers: Maximum expected triggers for normalization
        
    Returns:
        Normalized value between 0.0 and 1.0
    """
    return min(trigger_count / float(max_triggers), 1.0)


def _calculate_probability_rollback(
    structure_strength: float,
    displacement_strength: float,
    triggers: List[str],
    distance_pct: float
) -> float:
    """Calculate probability for ROLLBACK scenario"""
    probability = BASE_PROBABILITY['ROLLBACK']
    
    # Structure strength contribution (0-100 → 0.0-0.20)
    structure_contribution = (structure_strength / 100.0) * PROBABILITY_CONTRIBUTIONS['structure_strength']
    probability += structure_contribution
    
    # Displacement strength contribution (0-1 → 0.0-0.15)
    if displacement_strength > 0:
        disp_contribution = displacement_strength * PROBABILITY_CONTRIBUTIONS['displacement_strength']
        probability += disp_contribution
    
    # Sweep strength contribution
    if 'LIQUIDITY_SWEEP' in triggers:
        probability += PROBABILITY_CONTRIBUTIONS['sweep_strength']
    
    # Trigger count contribution (normalized for typical max of 4 triggers)
    trigger_count_normalized = _normalize_trigger_count(len(triggers), max_triggers=4)
    probability += trigger_count_normalized * PROBABILITY_CONTRIBUTIONS['trigger_count']
    
    # Distance penalty (closer is better, penalty increases with distance)
    distance_penalty_factor = min(distance_pct / 5.0, 1.0)  # 0% to 5% distance
    probability -= distance_penalty_factor * PROBABILITY_CONTRIBUTIONS['distance_penalty']
    
    # Clamp between 0.0 and 1.0
    return max(0.0, min(1.0, probability))


def _calculate_probability_pullback(
    poi_quality: float,
    triggers: List[str],
    distance_pct: float,
    structure_present: bool
) -> float:
    """Calculate probability for PULLBACK scenario"""
    probability = BASE_PROBABILITY['PULLBACK']
    
    # POI quality contribution (0-100 → 0.0-0.15)
    poi_contribution = (poi_quality / 100.0) * PROBABILITY_CONTRIBUTIONS['poi_quality']
    probability += poi_contribution
    
    # Structure bonus if MSS/BOS present
    if structure_present:
        probability += PROBABILITY_CONTRIBUTIONS['structure_strength'] * 0.5
    
    # Trigger count contribution (normalized for typical max of 3 triggers)
    trigger_count_normalized = _normalize_trigger_count(len(triggers), max_triggers=3)
    probability += trigger_count_normalized * PROBABILITY_CONTRIBUTIONS['trigger_count']
    
    # Distance penalty (0% to 5% distance)
    distance_penalty_factor = min(distance_pct / 5.0, 1.0)
    probability -= distance_penalty_factor * PROBABILITY_CONTRIBUTIONS['distance_penalty']
    
    # Clamp between 0.0 and 1.0
    return max(0.0, min(1.0, probability))


def _calculate_probability_continuation(
    displacement_strength: float,
    triggers: List[str],
    structure_present: bool,
    clear_path: bool
) -> float:
    """Calculate probability for CONTINUATION scenario"""
    probability = BASE_PROBABILITY['CONTINUATION']
    
    # Displacement strength (strongest factor for continuation)
    if displacement_strength > 0:
        disp_contribution = displacement_strength * PROBABILITY_CONTRIBUTIONS['displacement_strength']
        probability += disp_contribution
        
        # Extra bonus for very strong displacement
        if displacement_strength > 0.8:
            probability += 0.05
    
    # Structure confirmation
    if structure_present:
        probability += PROBABILITY_CONTRIBUTIONS['structure_strength'] * 0.7
    
    # Trigger count (normalized for typical max of 3 triggers)
    trigger_count_normalized = _normalize_trigger_count(len(triggers), max_triggers=3)
    probability += trigger_count_normalized * PROBABILITY_CONTRIBUTIONS['trigger_count']
    
    # Clear path bonus (no resistance ahead)
    if clear_path:
        probability += 0.05
    
    # Clamp between 0.0 and 1.0
    return max(0.0, min(1.0, probability))


def _calculate_probability_reversal(
    sweep_present: bool,
    structure_flip: bool,
    displacement_strength: float,
    triggers: List[str]
) -> float:
    """Calculate probability for REVERSAL scenario"""
    probability = BASE_PROBABILITY['REVERSAL']
    
    # Sweep strength (critical for reversal)
    if sweep_present:
        probability += PROBABILITY_CONTRIBUTIONS['sweep_strength']
    
    # Structure flip (critical for reversal)
    if structure_flip:
        probability += PROBABILITY_CONTRIBUTIONS['structure_strength']
    
    # Displacement in reversal direction
    if displacement_strength > 0:
        disp_contribution = displacement_strength * PROBABILITY_CONTRIBUTIONS['displacement_strength']
        probability += disp_contribution
    
    # Trigger count (normalized for typical max of 4 triggers)
    trigger_count_normalized = _normalize_trigger_count(len(triggers), max_triggers=4)
    probability += trigger_count_normalized * PROBABILITY_CONTRIBUTIONS['trigger_count']
    
    # HTF alignment bonus (assume aligned if all components present)
    if sweep_present and structure_flip and displacement_strength > 0.6:
        probability += PROBABILITY_CONTRIBUTIONS['htf_alignment'] * 0.5
    
    # Clamp between 0.0 and 1.0
    return max(0.0, min(1.0, probability))


def _create_safe_poi_data(poi_type: str, poi_object: Any) -> Dict:
    """Create JSON-safe poi_data dict from Python object."""
    poi_data = {'type': poi_type}
    
    if poi_type == 'OB' and poi_object:
        zone_low = float(poi_object.zone_low if hasattr(poi_object, 'zone_low') else poi_object.get('zone_low', 0))
        zone_high = float(poi_object.zone_high if hasattr(poi_object, 'zone_high') else poi_object.get('zone_high', 0))
        poi_data.update({
            'zone_low': zone_low,
            'zone_high': zone_high,
            'center': float((zone_low + zone_high) / 2),
            'strength': float(poi_object.strength if hasattr(poi_object, 'strength') else 0.0),
            'timeframe': str(poi_object.timeframe if hasattr(poi_object, 'timeframe') else 'unknown')
        })
    elif poi_type == 'FVG' and poi_object:
        bottom = float(poi_object.bottom if hasattr(poi_object, 'bottom') else poi_object.get('bottom', 0))
        top = float(poi_object.top if hasattr(poi_object, 'top') else poi_object.get('top', 0))
        poi_data.update({
            'bottom': bottom,
            'top': top,
            'center': float((bottom + top) / 2),
            'timeframe': str(poi_object.timeframe if hasattr(poi_object, 'timeframe') else 'unknown')
        })
    elif poi_type == 'LIQUIDITY' and poi_object:
        poi_data.update({
            'sweep_type': str(poi_object.sweep_type if hasattr(poi_object, 'sweep_type') else 'unknown'),
            'price': float(poi_object.price if hasattr(poi_object, 'price') else 0.0),
            'raid_low': float(poi_object.raid_low) if hasattr(poi_object, 'raid_low') and poi_object.raid_low else None,
            'raid_high': float(poi_object.raid_high) if hasattr(poi_object, 'raid_high') and poi_object.raid_high else None
        })
    
    return poi_data


def _create_invalidation_anchor(poi_type: str, poi_object: Any, best_poi: Dict, bias: str) -> Dict:
    """
    Create invalidation anchor based on POI type.
    
    Returns JSON-safe dict:
    {
        'type': 'OB_LOW' | 'FVG_LOW' | 'LIQUIDITY_LOW' | 'POI_BOUNDARY',
        'price': float,
        'source_type': str,
        'source_data': dict
    }
    """
    is_bullish = bias.upper() == "BULLISH"
    
    # OB anchor
    if poi_type == 'OB' and poi_object:
        # Extract both zone_low and zone_high safely
        zone_low = float(poi_object.zone_low if hasattr(poi_object, 'zone_low') else best_poi.get('low', 0))
        zone_high = float(poi_object.zone_high if hasattr(poi_object, 'zone_high') else best_poi.get('high', 0))
        anchor_price = zone_low if is_bullish else zone_high
        return {
            'type': 'OB_LOW' if is_bullish else 'OB_HIGH',
            'price': anchor_price,
            'source_type': 'OB',
            'source_data': {
                'zone_low': zone_low,
                'zone_high': zone_high
            }
        }
    
    # FVG anchor
    elif poi_type == 'FVG' and poi_object:
        # Extract both bottom and top safely
        bottom = float(poi_object.bottom if hasattr(poi_object, 'bottom') else best_poi.get('low', 0))
        top = float(poi_object.top if hasattr(poi_object, 'top') else best_poi.get('high', 0))
        anchor_price = bottom if is_bullish else top
        return {
            'type': 'FVG_LOW' if is_bullish else 'FVG_HIGH',
            'price': anchor_price,
            'source_type': 'FVG',
            'source_data': {
                'bottom': bottom,
                'top': top
            }
        }
    
    # BSL/SSL anchor
    elif poi_type in ['BSL', 'SSL']:
        anchor_price = float(best_poi.get('price', 0)) * (0.999 if is_bullish else 1.001)
        return {
            'type': 'LIQUIDITY_LOW' if is_bullish else 'LIQUIDITY_HIGH',
            'price': anchor_price,
            'source_type': 'LIQUIDITY',
            'source_data': {'price': float(best_poi.get('price', 0))}
        }
    
    # Fallback
    else:
        return {
            'type': 'POI_BOUNDARY',
            'price': float(best_poi.get('low' if is_bullish else 'high', best_poi.get('price', 0))),
            'source_type': poi_type,
            'source_data': {}
        }


# ============================================================
# BEHAVIORAL CORE GATE - Validation Functions
# ============================================================

def _validate_continuation_behavior(
    structure_break: Dict,
    displacement: Dict,
    current_price: float,
    bias: str,
    timeframe: str,
    ict_components: Dict = None,
    recent_candles: List = None
) -> Tuple[bool, str]:
    """
    Validate CONTINUATION behavioral requirements
    
    CORE (ALL 3 required):
    1. HTF Bias aligned (implicit via bias parameter)
    2. Reaction from OB or liquidity
    3. Impulse (candle body > average)
    
    BONUS (adds probability):
    - Displacement
    - FVG
    - BOS/MSS

    Returns:
        (is_eligible, reason)
    """
    # ✅ CORE 1: HTF Bias assumed aligned (checked in signal engine)
    
    # ✅ CORE 2: Check reaction from OB or liquidity
    if ict_components is None or recent_candles is None:
        logger.warning("⚠️ CONTINUATION: Missing ict_components or recent_candles, falling back to displacement check")
        # Fallback to displacement-only check
        if not displacement or not displacement.get('detected'):
            return False, "No displacement and no component data"
        disp_strength = displacement.get('strength', 0.0)
        if disp_strength < 0.3:
            return False, f"Weak displacement ({disp_strength:.2f} < 0.3)"
        return True, f"CONTINUATION valid (fallback): displacement {disp_strength:.2f}"
    
    reaction_found = False
    reaction_source = None
    reaction_candle_idx = None
    
    obs = ict_components.get('order_blocks', [])
    liq_zones = ict_components.get('liquidity_zones', [])
    
    # Check last 5 candles for reaction
    for idx in range(max(0, len(recent_candles) - 5), len(recent_candles)):
        candle = recent_candles[idx]
        
        # Check OBs
        for ob in obs:
            ob_type = str(ob.type if hasattr(ob, "type") else (_safe_get(ob, "type", "") if isinstance(ob, dict) else "")).upper()
            
            if bias == 'BULLISH' and 'BULLISH' in ob_type:
                if _candle_reacted_from_zone(candle, ob, 'BULLISH'):
                    reaction_found = True
                    reaction_source = "Bullish OB"
                    reaction_candle_idx = idx
                    break
            
            elif bias == 'BEARISH' and 'BEARISH' in ob_type:
                if _candle_reacted_from_zone(candle, ob, 'BEARISH'):
                    reaction_found = True
                    reaction_source = "Bearish OB"
                    reaction_candle_idx = idx
                    break
        
        if reaction_found:
            break
        
        # Check liquidity zones
        for liq in liq_zones:
            liq_type = str(liq.type if hasattr(liq, "type") else (_safe_get(liq, "type", "") if isinstance(liq, dict) else "")).upper()
            
            if bias == 'BULLISH' and 'BSL' in liq_type:
                if _candle_reacted_from_liquidity(candle, liq, 'BULLISH'):
                    reaction_found = True
                    reaction_source = "BSL"
                    reaction_candle_idx = idx
                    break
            
            elif bias == 'BEARISH' and 'SSL' in liq_type:
                if _candle_reacted_from_liquidity(candle, liq, 'BEARISH'):
                    reaction_found = True
                    reaction_source = "SSL"
                    reaction_candle_idx = idx
                    break
        
        if reaction_found:
            break
    
    if not reaction_found:
        return False, "No reaction from OB or liquidity in recent candles"
    
    # ✅ CORE 3: Check impulse (candle body > average)
    avg_body = _calculate_avg_body(recent_candles[-20:])
    reaction_candle = recent_candles[reaction_candle_idx]
    reaction_body = abs(reaction_candle['close'] - reaction_candle['open'])
    
    if reaction_body < avg_body * 1.2:  # At least 20% larger than average
        return False, f"No impulse: reaction body {reaction_body:.6f} < avg {avg_body:.6f} * 1.2"
    
    impulse_ratio = reaction_body / avg_body if avg_body > 0 else 0
    
    return True, f"CONTINUATION valid: {reaction_source} + impulse ({impulse_ratio:.1f}x avg)"


def _validate_pullback_behavior(
    poi: Dict,
    ict_components: Dict,
    current_price: float,
    bias: str,
    distance_pct: float,
    recent_candles: List = None
) -> Tuple[bool, str]:
    """
    Validate PULLBACK behavioral requirements
    
    CORE (ALL 3 required):
    1. POI exists
    2. Retest + rejection confirmed
    3. Bias aligned

    Returns:
        (is_eligible, reason)
    """
    # ✅ CORE 1: POI exists
    if not poi:
        return False, "No POI (Order Block or FVG)"
    
    # ✅ CORE 2: Retest + rejection
    if recent_candles is None or len(recent_candles) < 5:
        logger.warning("⚠️ PULLBACK: No recent_candles, falling back to distance check")
        # Fallback: check if price is close enough for potential retest
        if distance_pct > 2.0:
            return False, f"POI too far for retest ({distance_pct:.1f}% > 2%)"
        if distance_pct < 0.3:
            return False, f"POI too close, no retest yet ({distance_pct:.1f}% < 0.3%)"
        return True, f"PULLBACK valid (fallback): POI at {distance_pct:.1f}% distance"
    
    retested, rejection_strength = _check_poi_retest(poi, recent_candles, bias)
    
    if not retested:
        return False, "POI not retested yet (waiting for price to touch and reject)"
    
    if rejection_strength < 0.002:  # 0.2% minimum rejection
        return False, f"Weak rejection from POI ({rejection_strength*100:.2f}% < 0.2%)"
    
    # ✅ CORE 3: Bias alignment (implicit in retest direction check)
    
    # ✅ BONUS: Check for CHOCH (invalidates pullback)
    structure_break = ict_components.get('structure_break', {})
    if structure_break and structure_break.get('type') == 'CHOCH':
        return False, "Structure flip (CHOCH) invalidates pullback"
    
    return True, f"PULLBACK valid: POI retested with {rejection_strength*100:.1f}% rejection"


def _validate_reversal_behavior(
    sweeps: List,
    structure_break: Dict,
    displacement: Dict,
    timeframe: str
) -> Tuple[bool, str]:
    """
    Validate REVERSAL behavioral requirements (sequential pattern)

    Returns:
        (is_eligible, reason)
    """
    # 1. Check sweep exists and is recent
    if not sweeps:
        return False, "No liquidity sweep"

    sweep = sweeps[0]
    sweep_candles_ago = sweep.get('candles_ago', 999) if hasattr(sweep, 'get') else getattr(sweep, 'candles_ago', 999)

    max_sweep_age = get_recency_threshold('liquidity_sweep', timeframe)
    if sweep_candles_ago > max_sweep_age:
        return False, f"Sweep too old ({sweep_candles_ago} candles ago, max {max_sweep_age} for {timeframe})"

    # 2. Structure flip is CONFIRMATION layer (non-blocking)
    # REMOVED: Structure flip gate (confirmation layer check removed)

    # Use None when candles_ago is absent so conditional checks can be skipped
    flip_candles_ago = structure_break.get('candles_ago')

    # 3. Displacement is CONFIRMATION layer (non-blocking)
    # REMOVED: Displacement gate (confirmation layer check removed)

    disp_strength = displacement.get('strength', 0.0)
    # REMOVED: Weak displacement check (confirmation layer)

    # 4. Validate sequence: Sweep → Flip → Displacement
    # Valid: flip_candles_ago < sweep_candles_ago (flip is more recent = occurred after sweep)
    # Only enforce when flip timing data is available
    if flip_candles_ago is not None:
        if flip_candles_ago >= sweep_candles_ago:
            return False, (
                f"Invalid sequence: Flip ({flip_candles_ago} candles ago) must be more recent "
                f"than Sweep ({sweep_candles_ago} candles ago)"
            )

        # 5. Check gap between sweep and flip is not too large
        sweep_to_flip_gap = sweep_candles_ago - flip_candles_ago
        if sweep_to_flip_gap > 5:
            return False, f"Gap between sweep and flip too large ({sweep_to_flip_gap} candles)"

        # 6. Displacement must be more recent than flip (only when both timings are available)
        disp_candles_ago = displacement.get('candles_ago') if displacement else None
        if disp_candles_ago is not None:
            if disp_candles_ago >= flip_candles_ago:
                return False, (
                    f"Invalid sequence: Displacement ({disp_candles_ago} candles ago) must be "
                    f"more recent than Flip ({flip_candles_ago} candles ago)"
                )

    return True, f"REVERSAL sequence valid: Sweep({sweep_candles_ago}) → Flip({flip_candles_ago}) → Disp({disp_strength:.2f})"


def _validate_rollback_behavior(
    structure_break: Dict,
    current_price: float,
    ict_components: Dict,
    timeframe: str
) -> Tuple[bool, str]:
    """
    Validate ROLLBACK behavioral requirements

    Returns:
        (is_eligible, reason)
    """
    # 1. Check structure break exists
    if not structure_break or structure_break.get('type') not in ['BOS', 'MSS']:
        return False, "No structure break"

    # 2. Check break recency (only when candles_ago field is present)
    candles_ago = structure_break.get('candles_ago')
    if candles_ago is not None:
        max_age = get_recency_threshold('structure_break_rollback', timeframe)
        if candles_ago > max_age:
            return False, f"Structure break too old ({candles_ago} candles ago, max {max_age} for {timeframe})"

    # 3. Check price returned to break level (0.5-1.5%)
    break_price = structure_break.get('price')
    distance_to_break = 0.0
    if break_price is not None:
        distance_to_break = abs(current_price - break_price) / break_price * 100
        
        if distance_to_break < 0.5:
            return False, f"Too close to break (distance: {distance_to_break:.2f}% < 0.5%)"
        
        if distance_to_break > 1.5:
            return False, f"Too far from break (distance: {distance_to_break:.1f}% > 1.5%)"

    # 4. Verify price had moved away from break (BONUS, not gate)
    displacement = ict_components.get('displacement', {})
    disp_strength = 0.0
    if displacement and displacement.get('detected'):
        disp_strength = displacement.get('strength', 0.0)
        if disp_strength < 0.2:
            logger.info(f"   ⚠️ Weak displacement ({disp_strength:.2f}), but allowing rollback")
    else:
        logger.info(f"   ℹ️ No displacement detected for rollback")

    return True, f"ROLLBACK behavior valid (break {candles_ago} candles ago, distance {distance_to_break:.2f}%)"


# ============================================================
# ROLLBACK SCENARIO SCORING
# ============================================================

def _score_rollback_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
    timeframe: str
) -> Tuple[Optional[Dict], Any]:
    """
    Evaluate ROLLBACK scenario: retest to structure break level
    Uses probability engine instead of score-based filtering

    Returns tuple: (scenario_dict, poi_ref) OR (None, None) if invalid
    """
    sb = ict_components.get('structure_break')

    # ✅ BEHAVIORAL CORE GATE
    is_eligible, reason = _validate_rollback_behavior(
        structure_break=sb,
        current_price=current_price,
        ict_components=ict_components,
        timeframe=timeframe
    )

    if not is_eligible:
        logger.info(f"❌ ROLLBACK: {reason}")
        return None, None

    logger.info(f"✅ ROLLBACK: {reason}")

    break_level = sb.get('break_level')
    if not break_level:
        return None, None
    
    # Distance check
    distance_pct = abs(break_level - current_price) / current_price * 100
    
    if distance_pct < ROLLBACK_DISTANCE['min_pct'] * 100:
        logger.debug(f"   ROLLBACK: too close ({distance_pct:.1f}% < {ROLLBACK_DISTANCE['min_pct']*100:.0f}%)")
        return None, None
    
    if distance_pct > ROLLBACK_DISTANCE['max_pct'] * 100:
        logger.debug(f"   ROLLBACK: too far ({distance_pct:.1f}% > {ROLLBACK_DISTANCE['max_pct']*100:.0f}%)")
        return None, None
    
    # Already retested check
    if sb.get('retested', False):
        logger.debug(f"   ROLLBACK: break_level already retested")
        return None, None
    
    # Bias alignment check
    is_bullish = bias.upper() == "BULLISH"
    is_bearish = bias.upper() == "BEARISH"
    
    if is_bullish and break_level >= current_price:
        logger.debug(f"   ROLLBACK: BULLISH but break_level above current")
        return None, None
    
    if is_bearish and break_level <= current_price:
        logger.debug(f"   ROLLBACK: BEARISH but break_level below current")
        return None, None
    
    # ============================================================
    # PROBABILITY CALCULATION (Phase 2)
    # ============================================================
    structure_strength = sb.get('strength', 50)
    
    # Get displacement strength
    displacement = ict_components.get('displacement', {})
    displacement_strength = displacement.get('strength', 0) if displacement.get('detected') else 0
    
    # Calculate probability using helper function
    probability = _calculate_probability_rollback(
        structure_strength=structure_strength,
        displacement_strength=displacement_strength,
        triggers=triggers,
        distance_pct=distance_pct
    )
    
    logger.info(f"   ROLLBACK probability: {probability:.3f}")
    
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
    
    # Create invalidation anchor (for ROLLBACK, use swing structure)
    is_bullish = bias.upper() == "BULLISH"
    anchor_price = break_level * (0.995 if is_bullish else 1.005)
    invalidation_anchor = {
        'type': 'SWING_LOW' if is_bullish else 'SWING_HIGH',
        'price': float(anchor_price),
        'source_type': 'STRUCTURE_BREAK',
        'source_data': {'break_level': float(break_level), 'type': sb.get('type')}
    }
    
    scenario_dict = {
        'scenario': 'ROLLBACK',
        'eligible': True,
        'entry_zone': entry_zone,
        'probability': float(probability),
        'triggers': triggers,
        'trigger_strength': _evaluate_trigger_strength(trigger_score),
        'reasoning': f"Rollback to {sb.get('type')} break level @ ${break_level:.2f} ({distance_pct:.1f}% away, probability: {probability:.3f})",
        'position_size_advisory': POSITION_SIZE['ROLLBACK'],
        'poi_type': 'NONE',
        'poi_data': {},
        'invalidation_anchor': invalidation_anchor,
        'stop_loss_logic': {
            'type': 'beyond_break',
            'buffer_pct': 1.0
        }
    }
    
    return scenario_dict, None



# ============================================================
# PULLBACK SCENARIO SCORING
# ============================================================



# ============================================================
# CONFIRMATION LAYER - Helper Function
# ============================================================



# ═══════════════════════════════════════════════════════════
# HELPER FUNCTIONS FOR REFINED CORE VALIDATION
# ═══════════════════════════════════════════════════════════

def _candle_reacted_from_zone(candle: Dict, zone, bias: str) -> bool:
    """Check if single candle reacted from OB zone"""
    zone_low = zone.zone_low if hasattr(zone, 'zone_low') else (_safe_get(zone, 'zone_low') if isinstance(zone, dict) else None)
    zone_high = zone.zone_high if hasattr(zone, 'zone_high') else (_safe_get(zone, 'zone_high') if isinstance(zone, dict) else None)
    
    if zone_low is None or zone_high is None:
        return False
    
    # Did candle touch zone?
    touched = candle['low'] <= zone_high and candle['high'] >= zone_low
    
    if not touched:
        return False
    
    # Did it close outside showing rejection?
    if bias == 'BULLISH':
        return candle['close'] > zone_high and candle['close'] > candle['open']
    else:
        return candle['close'] < zone_low and candle['close'] < candle['open']


def _candle_reacted_from_liquidity(candle: Dict, liq, bias: str) -> bool:
    """Check if single candle reacted from liquidity level"""
    liq_price = liq.price if hasattr(liq, 'price') else (_safe_get(liq, 'price') if isinstance(liq, dict) else None)
    
    if liq_price is None:
        return False
    
    # Did candle touch liquidity?
    touched = candle['low'] <= liq_price <= candle['high']
    
    if not touched:
        return False
    
    # Did it reject?
    if bias == 'BULLISH':
        return candle['close'] > liq_price and candle['close'] > candle['open']
    else:
        return candle['close'] < liq_price and candle['close'] < candle['open']


def _calculate_avg_body(candles: List) -> float:
    """Calculate average candle body size"""
    if not candles:
        return 0.0
    
    bodies = [abs(c['close'] - c['open']) for c in candles if 'close' in c and 'open' in c]
    
    if not bodies:
        return 0.0
    
    return sum(bodies) / len(bodies)


def _check_poi_retest(poi: Dict, candles: List, bias: str) -> Tuple[bool, float]:
    """
    Check if POI was retested with rejection
    
    Returns:
        (retested: bool, rejection_strength: float)
    """
    poi_low = poi.get('low')
    poi_high = poi.get('high')
    
    if poi_low is None or poi_high is None:
        return False, 0.0
    
    # Check last 5 candles for retest
    for candle in candles[-5:]:
        # Did candle touch POI?
        touched = candle['low'] <= poi_high and candle['high'] >= poi_low
        
        if touched:
            if bias == 'BULLISH':
                # Expect bounce UP from POI
                if candle['close'] > poi_high:
                    rejection = (candle['close'] - poi_high) / poi_high
                    return True, rejection
            else:
                # Expect bounce DOWN from POI
                if candle['close'] < poi_low:
                    rejection = (poi_low - candle['close']) / poi_low
                    return True, rejection
    
    return False, 0.0



def _check_confirmation_layer(
    structure_break: Dict,
    displacement: Dict,
    sweeps: List = None
) -> bool:
    """
    Check if ANY confirmation component is present.
    
    Confirmation components (mid TF):
    - MSS (Market Structure Shift)
    - BOS (Break of Structure)
    - CHOCH (Change of Character)
    - Displacement (strong momentum)
    - Sweep + Displacement combo
    
    Returns:
        True if at least ONE confirmation component is present
    """
    # 1. Check MSS/BOS/CHOCH (structure break)
    if structure_break and structure_break.get('type') in ['MSS', 'BOS', 'CHOCH']:
        return True
    
    # 2. Check Displacement (with minimum strength threshold)
    if displacement and displacement.get('detected'):
        strength = displacement.get('strength', 0)
        if strength >= 0.3:  # Minimum threshold for confirmation
            return True
    
    # 3. Check Sweep + Displacement combo
    if sweeps and len(sweeps) > 0:
        if displacement and displacement.get('detected'):
            strength = displacement.get('strength', 0)
            if strength >= 0.2:  # Lower threshold when combined with sweep
                return True
    
    return False


def _score_pullback_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
    entry_zone: Dict
) -> Tuple[Optional[Dict], Any]:
    """
    Score PULLBACK scenario: retracement to POI (OB/FVG/BSL/SSL)
    
    Returns tuple: (scenario_dict, poi_ref) OR (None, None) if invalid
    """
    # DEBUG: PULLBACK evaluation started
    logger.info("🔍 PULLBACK: Starting evaluation...")
    logger.info(f"🔍 PULLBACK: bias={bias}, current_price={current_price}")
    poi_candidates = []
    is_bullish = bias.upper() == "BULLISH"
    is_bearish = bias.upper() == "BEARISH"
    
    # 1. Check Order Blocks
    obs = ict_components.get('order_blocks', [])
    for ob in obs:
        ob_type = str(ob.type if hasattr(ob, "type") else (_safe_get(ob, "type", "") if isinstance(ob, dict) else "")).upper()
        ob_center = _get_ob_center(ob)
        
        if is_bullish and 'BULLISH' in ob_type and ob_center < current_price:
            distance_pct = abs(ob_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                # Use actual component strength instead of hardcoded quality
                ob_strength = _safe_get(ob, 'strength', 70)
                poi_candidates.append({
                    'type': 'OB',
                    'price': ob_center,
                    'low': ob.zone_low if hasattr(ob, 'zone_low') else (ob.get('zone_low') if isinstance(ob, dict) else None),
                    'high': ob.zone_high if hasattr(ob, 'zone_high') else (ob.get('zone_high') if isinstance(ob, dict) else None),
                    'distance_pct': distance_pct,
                    'quality': ob_strength,
                    '_ref': ob  # ← NEW: Store reference
                })
        
        if is_bearish and 'BEARISH' in ob_type and ob_center > current_price:
            distance_pct = abs(ob_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                # Use actual component strength instead of hardcoded quality
                ob_strength = _safe_get(ob, 'strength', 70)
                poi_candidates.append({
                    'type': 'OB',
                    'price': ob_center,
                    'low': ob.zone_low if hasattr(ob, 'zone_low') else (ob.get('zone_low') if isinstance(ob, dict) else None),
                    'high': ob.zone_high if hasattr(ob, 'zone_high') else (ob.get('zone_high') if isinstance(ob, dict) else None),
                    'distance_pct': distance_pct,
                    'quality': ob_strength,
                    '_ref': ob  # ← NEW: Store reference
                })
    
    # 2. Check FVGs
    fvgs = ict_components.get('fvgs', [])
    for fvg in fvgs:
        fvg_type = getattr(fvg, 'type', None) or _safe_get(fvg, 'type', '')
        fvg_center = (fvg.bottom if hasattr(fvg, 'bottom') else (_safe_get(fvg, 'bottom', 0) if isinstance(fvg, dict) else 0) + fvg.top if hasattr(fvg, 'top') else (_safe_get(fvg, 'top', 0) if isinstance(fvg, dict) else 0)) / 2
        
        if is_bullish and 'BULLISH' in str(fvg_type).upper() and fvg_center < current_price:
            distance_pct = abs(fvg_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                # Use actual component strength instead of hardcoded quality
                fvg_strength = _safe_get(fvg, 'strength', 70)
                poi_candidates.append({
                    'type': 'FVG',
                    'price': fvg_center,
                    'low': fvg.bottom if hasattr(fvg, 'bottom') else (_safe_get(fvg, 'bottom') if isinstance(fvg, dict) else None),
                    'high': fvg.top if hasattr(fvg, 'top') else (_safe_get(fvg, 'top') if isinstance(fvg, dict) else None),
                    'distance_pct': distance_pct,
                    'quality': fvg_strength,
                    '_ref': fvg  # ← NEW: Store reference
                })
        
        if is_bearish and 'BEARISH' in str(fvg_type).upper() and fvg_center > current_price:
            distance_pct = abs(fvg_center - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                # Use actual component strength instead of hardcoded quality
                fvg_strength = _safe_get(fvg, 'strength', 70)
                poi_candidates.append({
                    'type': 'FVG',
                    'price': fvg_center,
                    'low': fvg.bottom if hasattr(fvg, 'bottom') else (_safe_get(fvg, 'bottom') if isinstance(fvg, dict) else None),
                    'high': fvg.top if hasattr(fvg, 'top') else (_safe_get(fvg, 'top') if isinstance(fvg, dict) else None),
                    'distance_pct': distance_pct,
                    'quality': fvg_strength,
                    '_ref': fvg  # ← NEW: Store reference
                })
    
    # 3. Check Liquidity zones (BSL/SSL)
    liq_zones = ict_components.get('liquidity_zones', [])
    for liq in liq_zones:
        liq_type = (liq.type if hasattr(liq, 'type') else (_safe_get(liq, 'type', '') if isinstance(liq, dict) else '')).upper()
        liq_price = liq.price if hasattr(liq, 'price') else (liq.price if hasattr(liq, 'price') else (_safe_get(liq, 'price', 0) if isinstance(liq, dict) else 0) if isinstance(liq, dict) else 0)
        
        if is_bullish and 'BSL' in liq_type and liq_price < current_price:
            distance_pct = abs(liq_price - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                # Use actual component strength instead of hardcoded quality
                liq_strength = _safe_get(liq, 'confidence', 0.7) * 100
                poi_candidates.append({
                    'type': 'BSL',
                    'price': liq_price,
                    'low': liq_price * 0.999,
                    'high': liq_price * 1.001,
                    'distance_pct': distance_pct,
                    'quality': liq_strength,
                    '_ref': liq  # ← NEW: Store reference
                })
        
        if is_bearish and 'SSL' in liq_type and liq_price > current_price:
            distance_pct = abs(liq_price - current_price) / current_price * 100
            if PULLBACK_DISTANCE['min_pct'] * 100 <= distance_pct <= PULLBACK_DISTANCE['max_pct'] * 100:
                # Use actual component strength instead of hardcoded quality
                liq_strength = _safe_get(liq, 'confidence', 0.7) * 100
                poi_candidates.append({
                    'type': 'SSL',
                    'price': liq_price,
                    'low': liq_price * 0.999,
                    'high': liq_price * 1.001,
                    'distance_pct': distance_pct,
                    'quality': liq_strength,
                    '_ref': liq  # ← NEW: Store reference
                })
    
    if not poi_candidates:
        return None, None
    
    # Filter by minimum quality
    poi_candidates = [p for p in poi_candidates if p['quality'] >= POI_QUALITY['min_acceptable']]
    
    if not poi_candidates:
        logger.info("   PULLBACK: no POI with acceptable quality")
        return None, None
    
    # Select best POI (highest quality, then closest)
    best_poi = max(poi_candidates, key=lambda x: (x['quality'], -x['distance_pct']))


    # ============================================================
    # CONFIRMATION LAYER MODIFIER (±8%)
    # ============================================================
    disp = ict_components.get('displacement', {})
    sb = ict_components.get('structure_break')
    
    confirmation_present = _check_confirmation_layer(
        structure_break=sb,
        displacement=disp,
        sweeps=None  # PULLBACK doesn't require sweep
    )
    
    pullback_confirmation_modifier = 0.0
    if confirmation_present:
        pullback_confirmation_modifier = 0.08
        logger.info(f"   ✅ Confirmation layer present: +8%")
    else:
        pullback_confirmation_modifier = -0.08
        logger.info(f"   ⚠️  No confirmation layer: -8%")

    # ✅ BEHAVIORAL CORE GATE
    is_eligible, reason = _validate_pullback_behavior(
        poi=best_poi,
        ict_components=ict_components,
        current_price=current_price,
        bias=bias,
        distance_pct=best_poi['distance_pct']
    )

    if not is_eligible:
        logger.info(f"❌ PULLBACK: {reason}")
        return None, None

    logger.info(f"✅ PULLBACK: {reason}")

    # ============================================================
    # PROBABILITY CALCULATION (Phase 2)
    # ============================================================
    poi_quality = best_poi['quality']
    structure_present = 'MSS/BOS' in triggers
    distance_pct = best_poi['distance_pct']
    
    # Calculate probability using helper function
    probability = _calculate_probability_pullback(
        poi_quality=poi_quality,
        triggers=triggers,
        distance_pct=distance_pct,
        structure_present=structure_present
    )

    # Apply confirmation layer modifier (±8%)
    probability += pullback_confirmation_modifier
    probability = max(0.0, min(1.0, probability))  # Clamp to [0, 1]
    
    
    logger.info(f"   PULLBACK probability: {probability:.3f}")
    logger.info(f"   PULLBACK probability: {probability:.3f}")
    
    
    # ✅ Extract poi_ref (remove from dict)
    # ✅ Extract poi_ref (remove from dict)
    poi_ref = best_poi.pop('_ref', None)
    poi_ref = best_poi.pop('_ref', None)
    
    
    # ✅ Create safe poi_data
    poi_data = _create_safe_poi_data(best_poi['type'], poi_ref)
    
    # ✅ Create invalidation anchor
    invalidation_anchor = _create_invalidation_anchor(
        poi_type=best_poi['type'],
        poi_object=poi_ref,
        best_poi=best_poi,
        bias=bias
    )
    
    # Build entry zone
    buffer = PULLBACK_DISTANCE['buffer_pct']
    entry_zone = {
        'center': best_poi['price'],
        'low': best_poi['low'] * (1 - buffer) if best_poi['low'] else best_poi['price'] * (1 - buffer),
        'high': best_poi['high'] * (1 + buffer) if best_poi['high'] else best_poi['price'] * (1 + buffer),
        'source': f"PULLBACK_{best_poi['type']}",
        'quality': best_poi['quality'],
        'distance_pct': best_poi['distance_pct'],
        'distance_price': abs(best_poi['price'] - current_price)
    }
    
    # ✅ Return tuple (safe_dict, poi_ref)
    scenario_dict = {
        'scenario': 'PULLBACK',
        'eligible': True,
        'entry_zone': entry_zone,
        'probability': float(probability),
        'triggers': triggers,
        'trigger_strength': _evaluate_trigger_strength(trigger_score),
        'reasoning': f"Pullback to {best_poi['type']} @ ${best_poi['price']:.2f} ({best_poi['distance_pct']:.1f}% away, probability: {probability:.3f})",
        'position_size_advisory': POSITION_SIZE['PULLBACK'],
        'poi_type': best_poi['type'],
        'poi_data': poi_data,
        'invalidation_anchor': invalidation_anchor,
        'stop_loss_logic': {
            'type': 'beyond_poi',
            'buffer_pct': 1.0
        }
    }
    
    return scenario_dict, poi_ref


# ============================================================
# CONTINUATION SCENARIO SCORING
# ============================================================

def _score_continuation_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
    trigger_strength: str,
    timeframe: str = '1h'
) -> Tuple[Optional[Dict], Any]:
    """
    Score CONTINUATION scenario: minimal retracement, high momentum

    Returns tuple: (scenario_dict, None) OR (None, None) if invalid
    """
    sb = ict_components.get('structure_break')
    disp = ict_components.get('displacement', {})

    # ✅ BEHAVIORAL CORE GATE
    is_eligible, reason = _validate_continuation_behavior(
        structure_break=sb,
        displacement=disp,
        current_price=current_price,
        bias=bias,
        timeframe=timeframe,
        ict_components=ict_components,
        recent_candles=ict_components.get('candles', []) if ict_components else []
    )

    if not is_eligible:
        logger.info(f"❌ CONTINUATION: {reason}")
        return None, None

    logger.info(f"✅ CONTINUATION: {reason}")

    # Must have displacement OR structure trigger
    has_momentum = 'DISPLACEMENT' in triggers or 'MSS/BOS' in triggers
    if not has_momentum:
        logger.debug("   CONTINUATION: no displacement or structure trigger")
        return None, None
    
    # Check for POI in path (reject if found)
    is_bullish = bias.upper() == "BULLISH"
    check_range = CONTINUATION_DISTANCE['poi_check_range_pct']
    
    obs = ict_components.get('order_blocks', [])
    clear_path = True
    for ob in obs:
        ob_center = _get_ob_center(ob)
        
        if is_bullish and current_price * (1 - check_range) <= ob_center <= current_price:
            logger.debug(f"   CONTINUATION: found OB in path @ ${ob_center:.2f}")
            clear_path = False
            break
        
        if not is_bullish and current_price <= ob_center <= current_price * (1 + check_range):
            logger.debug(f"   CONTINUATION: found OB in path @ ${ob_center:.2f}")
            clear_path = False
            break
    
    if not clear_path:
        return None, None
    
    # ============================================================
    # PROBABILITY CALCULATION (Phase 2)
    # ============================================================
    disp = ict_components.get('displacement', {})
    displacement_strength = disp.get('strength', 0) if disp.get('detected') else 0
    structure_present = 'MSS/BOS' in triggers
    
    # Calculate probability using helper function
    probability = _calculate_probability_continuation(
        displacement_strength=displacement_strength,
        triggers=triggers,
        structure_present=structure_present,
        clear_path=clear_path
    )
    
    logger.info(f"   CONTINUATION probability: {probability:.3f}")
    
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
    
    # Create invalidation anchor (for CONTINUATION, use swing structure)
    is_bullish = bias.upper() == "BULLISH"
    swing_price = entry_price * (0.98 if is_bullish else 1.02)
    invalidation_anchor = {
        'type': 'SWING_LOW' if is_bullish else 'SWING_HIGH',
        'price': float(swing_price),
        'source_type': 'SWING',
        'source_data': {}
    }
    
    scenario_dict = {
        'scenario': 'CONTINUATION',
        'eligible': True,
        'entry_zone': entry_zone,
        'probability': float(probability),
        'triggers': triggers,
        'trigger_strength': trigger_strength,
        'reasoning': f"Continuation with {len(triggers)} triggers (probability: {probability:.3f}, retracement {retracement*100:.1f}%)",
        'position_size_advisory': position_size,
        'poi_type': 'NONE',
        'poi_data': {},
        'invalidation_anchor': invalidation_anchor,
        'stop_loss_logic': {
            'type': 'below_ob',
            'buffer_pct': 0.5
        }
    }
    
    return scenario_dict, None


# ============================================================
# REVERSAL SCENARIO SCORING
# ============================================================

def _score_reversal_scenario(
    current_price: float,
    bias: str,
    ict_components: Dict,
    triggers: List[str],
    trigger_score: int,
    timeframe: str
) -> Tuple[Optional[Dict], Any]:
    """
    Score REVERSAL scenario: market structure flip with liquidity sweep

    Returns tuple: (scenario_dict, None) OR (None, None) if invalid
    """
    sweeps = ict_components.get('liquidity_sweeps', [])
    sb = ict_components.get('structure_break')
    disp = ict_components.get('displacement', {})

    # ✅ BEHAVIORAL CORE GATE
    is_eligible, reason = _validate_reversal_behavior(
        sweeps=sweeps,
        structure_break=sb,
        displacement=disp,
        timeframe=timeframe
    )

    if not is_eligible:
        logger.info(f"❌ REVERSAL: {reason}")
        return None, None

    logger.info(f"✅ REVERSAL: {reason}")


    # ============================================================
    # CONFIRMATION LAYER MODIFIER (±8%)
    # ============================================================
    confirmation_present = _check_confirmation_layer(
        structure_break=sb,
        displacement=disp,
        sweeps=sweeps
    )
    
    base_confirmation_modifier = 0.0
    if REVERSAL_SETTINGS.get('use_confirmation_modifier', False):
        modifier_pct = REVERSAL_SETTINGS.get('confirmation_modifier_pct', 0.08)
        if confirmation_present:
            base_confirmation_modifier = modifier_pct
            logger.info(f"   ✅ Confirmation layer present: +{modifier_pct*100:.0f}%")
        else:
            base_confirmation_modifier = -modifier_pct
            logger.info(f"   ⚠️  No confirmation layer: -{modifier_pct*100:.0f}%")

    # Check for liquidity sweep (required)
    if REVERSAL_SETTINGS['require_sweep']:
        if 'LIQUIDITY_SWEEP' not in triggers:
            logger.debug("   REVERSAL: no liquidity sweep detected")
            return None, None
    
    # Check for structure flip (MSS/CHOCH in opposite direction)
    structure_flip = False
    if REVERSAL_SETTINGS['require_structure_flip']:
        if not sb or sb.get('type') not in ['MSS', 'CHOCH']:
            logger.debug("   REVERSAL: no structure flip (MSS/CHOCH) detected")
            return None, None
        
        # Check if structure flip is in opposite direction to current bias
        sb_direction = sb.get('direction', '').upper()
        bias_upper = bias.upper()
        
        # REVERSAL detection: validate structure flip direction
        if sb_direction:
            bias_upper = bias.upper()
            if bias_upper == 'BULLISH' and sb_direction == 'BULLISH':
                logger.debug("   REVERSAL: same direction as bias")
                return None, None
            if bias_upper == 'BEARISH' and sb_direction == 'BEARISH':
                logger.debug("   REVERSAL: same direction as bias")
                return None, None
        
        structure_flip = True
    
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
            ob_center = _get_ob_center(ob)
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
            ob_center = _get_ob_center(ob)
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
            ob_center = _get_ob_center(ob)
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
        return None, None
    
    # ============================================================
    # PROBABILITY CALCULATION (Phase 2)
    # ============================================================
    sweep_present = 'LIQUIDITY_SWEEP' in triggers
    
    # Get displacement strength
    disp = ict_components.get('displacement', {})
    displacement_strength = disp.get('strength', 0) if disp.get('detected') else 0
    
    # Calculate probability using helper function
    probability = _calculate_probability_reversal(
        sweep_present=sweep_present,
        structure_flip=structure_flip,
        displacement_strength=displacement_strength,
        triggers=triggers
    )

    # Apply confirmation layer modifier (±8%)
    probability += base_confirmation_modifier
    probability = max(0.0, min(1.0, probability))  # Clamp to [0, 1]
    
    logger.info(f"   REVERSAL probability: {probability:.3f}")
    
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
    
    # Create invalidation anchor (for REVERSAL, use swing structure)
    is_bullish = bias.upper() == "BULLISH"
    swing_price = entry_price * (0.98 if is_bullish else 1.02)
    invalidation_anchor = {
        'type': 'SWING_LOW' if is_bullish else 'SWING_HIGH',
        'price': float(swing_price),
        'source_type': 'REVERSAL',
        'source_data': {'entry_type': entry_type}
    }
    
    scenario_dict = {
        'scenario': 'REVERSAL',
        'eligible': True,
        'entry_zone': entry_zone,
        'probability': float(probability),
        'triggers': triggers,
        'trigger_strength': _evaluate_trigger_strength(trigger_score),
        'reasoning': f"Reversal setup with sweep + {sb.get('type')} @ ${entry_price:.2f} (probability: {probability:.3f}, {distance_pct:.1f}% away)",
        'position_size_advisory': POSITION_SIZE['REVERSAL'],
        'poi_type': 'NONE',
        'poi_data': {},
        'invalidation_anchor': invalidation_anchor,
        'stop_loss_logic': {
            'type': 'beyond_sweep',
            'buffer_pct': 0.5
        }
    }
    
    return scenario_dict, None
