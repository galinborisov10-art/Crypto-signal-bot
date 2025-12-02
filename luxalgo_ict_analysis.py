"""
🔥 LuxAlgo Support/Resistance MTF + ICT Concepts Analysis System
Combined methodology for professional trading signals
"""

import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


# ===================================
# LUXALGO SUPPORT/RESISTANCE MTF
# ===================================

def detect_swing_points(highs: List[float], lows: List[float], lookback: int = 5) -> Dict:
    """
    Detect swing highs and swing lows for S/R calculation
    Returns dynamic support/resistance levels
    """
    try:
        swing_highs = []
        swing_lows = []
        
        for i in range(lookback, len(highs) - lookback):
            # Swing High: highest in lookback range
            is_swing_high = all(highs[i] >= highs[i-j] for j in range(1, lookback + 1)) and \
                           all(highs[i] >= highs[i+j] for j in range(1, lookback + 1))
            
            # Swing Low: lowest in lookback range
            is_swing_low = all(lows[i] <= lows[i-j] for j in range(1, lookback + 1)) and \
                          all(lows[i] <= lows[i+j] for j in range(1, lookback + 1))
            
            if is_swing_high:
                swing_highs.append({'index': i, 'price': highs[i]})
            if is_swing_low:
                swing_lows.append({'index': i, 'price': lows[i]})
        
        return {
            'swing_highs': swing_highs[-10:],  # Last 10 swing highs
            'swing_lows': swing_lows[-10:]     # Last 10 swing lows
        }
    
    except Exception as e:
        logger.error(f"Error detecting swing points: {e}")
        return {'swing_highs': [], 'swing_lows': []}


def calculate_luxalgo_sr_levels(highs: List[float], lows: List[float], closes: List[float], 
                                  volumes: List[float] = None) -> Dict:
    """
    LuxAlgo-style Support/Resistance with:
    - Dynamic levels (recent swing points)
    - Static levels (historical significant zones)
    - Liquidity zones (high volume areas)
    """
    try:
        current_price = closes[-1]
        swing_data = detect_swing_points(highs, lows, lookback=5)
        
        # Dynamic Resistance Levels
        resistances = sorted([sh['price'] for sh in swing_data['swing_highs'] 
                            if sh['price'] > current_price])[:3]
        
        # Dynamic Support Levels
        supports = sorted([sl['price'] for sl in swing_data['swing_lows'] 
                          if sl['price'] < current_price], reverse=True)[:3]
        
        # Static levels (historical highs/lows from last 200 candles)
        lookback = min(200, len(highs))
        historical_high = max(highs[-lookback:])
        historical_low = min(lows[-lookback:])
        
        # Liquidity zones (volume-weighted price areas)
        liquidity_zones = []
        if volumes and len(volumes) > 50:
            # Find high-volume price clusters
            recent_data = list(zip(closes[-50:], volumes[-50:]))
            volume_threshold = np.mean(volumes[-50:]) * 1.5
            
            for price, vol in recent_data:
                if vol > volume_threshold:
                    liquidity_zones.append(price)
        
        # Detect breakouts and retests
        breakout_status = detect_breakout_retest(closes, resistances, supports)
        
        return {
            'dynamic_resistance': resistances,
            'dynamic_support': supports,
            'static_resistance': historical_high,
            'static_support': historical_low,
            'liquidity_zones': liquidity_zones,
            'breakout_status': breakout_status,
            'current_price': current_price
        }
    
    except Exception as e:
        logger.error(f"Error in LuxAlgo S/R calculation: {e}")
        return None


def detect_breakout_retest(closes: List[float], resistances: List[float], 
                           supports: List[float]) -> str:
    """
    Detect if price broke through S/R and is retesting
    """
    try:
        if len(closes) < 5:
            return 'NONE'
        
        current = closes[-1]
        prev_close = closes[-2]
        
        # Breakout above resistance
        if resistances:
            nearest_resistance = min(resistances)
            if prev_close < nearest_resistance and current > nearest_resistance:
                return 'BREAKOUT_RESISTANCE'
            elif current < nearest_resistance < closes[-3]:
                return 'RETEST_RESISTANCE'
        
        # Breakout below support
        if supports:
            nearest_support = max(supports)
            if prev_close > nearest_support and current < nearest_support:
                return 'BREAKOUT_SUPPORT'
            elif current > nearest_support > closes[-3]:
                return 'RETEST_SUPPORT'
        
        return 'NONE'
    
    except Exception as e:
        logger.error(f"Error detecting breakout/retest: {e}")
        return 'NONE'


# ===================================
# ICT CONCEPTS
# ===================================

def detect_market_structure_shift(highs: List[float], lows: List[float], 
                                   closes: List[float]) -> Optional[Dict]:
    """
    ICT Market Structure Shift (MSS)
    Detects when market breaks previous structure (change of character)
    """
    try:
        if len(closes) < 20:
            return None
        
        # Find recent swing highs and lows
        swing_data = detect_swing_points(highs, lows, lookback=3)
        
        if not swing_data['swing_highs'] or not swing_data['swing_lows']:
            return None
        
        current_price = closes[-1]
        
        # Bullish MSS: price breaks above previous swing high
        if swing_data['swing_highs']:
            prev_swing_high = swing_data['swing_highs'][-1]['price']
            if current_price > prev_swing_high:
                return {
                    'type': 'BULLISH_MSS',
                    'level': prev_swing_high,
                    'confirmed': True
                }
        
        # Bearish MSS: price breaks below previous swing low
        if swing_data['swing_lows']:
            prev_swing_low = swing_data['swing_lows'][-1]['price']
            if current_price < prev_swing_low:
                return {
                    'type': 'BEARISH_MSS',
                    'level': prev_swing_low,
                    'confirmed': True
                }
        
        return None
    
    except Exception as e:
        logger.error(f"Error detecting MSS: {e}")
        return None


def detect_liquidity_grab(highs: List[float], lows: List[float], 
                          closes: List[float], volumes: List[float]) -> Optional[Dict]:
    """
    ICT Liquidity Grab (Stop Hunt)
    Detects when price sweeps highs/lows to grab liquidity then reverses
    """
    try:
        if len(closes) < 10:
            return None
        
        current = closes[-1]
        
        # Recent swing high (last 20 candles)
        lookback = min(20, len(highs) - 1)
        recent_high = max(highs[-lookback:-1])
        recent_low = min(lows[-lookback:-1])
        
        # Bullish Liquidity Grab: sweep low + strong reversal up
        if lows[-1] < recent_low and closes[-1] > closes[-2]:
            volume_surge = volumes[-1] > np.mean(volumes[-10:]) * 1.3 if volumes else False
            return {
                'type': 'BULLISH_LIQUIDITY_GRAB',
                'swept_level': recent_low,
                'reversal_confirmed': volume_surge
            }
        
        # Bearish Liquidity Grab: sweep high + strong reversal down
        if highs[-1] > recent_high and closes[-1] < closes[-2]:
            volume_surge = volumes[-1] > np.mean(volumes[-10:]) * 1.3 if volumes else False
            return {
                'type': 'BEARISH_LIQUIDITY_GRAB',
                'swept_level': recent_high,
                'reversal_confirmed': volume_surge
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Error detecting liquidity grab: {e}")
        return None


def detect_fair_value_gaps(opens: List[float], highs: List[float], 
                           lows: List[float], closes: List[float]) -> List[Dict]:
    """
    ICT Fair Value Gaps (FVG) - imbalance/inefficiency
    Detects 3-candle patterns where middle candle gap isn't filled
    """
    try:
        fvgs = []
        
        for i in range(2, len(closes)):
            # Bullish FVG: candle 1 high < candle 3 low
            if lows[i] > highs[i-2]:
                fvgs.append({
                    'type': 'BULLISH_FVG',
                    'top': lows[i],
                    'bottom': highs[i-2],
                    'index': i,
                    'filled': False
                })
            
            # Bearish FVG: candle 1 low > candle 3 high
            if highs[i] < lows[i-2]:
                fvgs.append({
                    'type': 'BEARISH_FVG',
                    'top': lows[i-2],
                    'bottom': highs[i],
                    'index': i,
                    'filled': False
                })
        
        # Keep only recent unfilled FVGs
        current_price = closes[-1]
        active_fvgs = []
        for fvg in fvgs[-10:]:  # Last 10 FVGs
            if fvg['type'] == 'BULLISH_FVG' and current_price >= fvg['bottom']:
                fvg['filled'] = current_price > fvg['top']
                active_fvgs.append(fvg)
            elif fvg['type'] == 'BEARISH_FVG' and current_price <= fvg['top']:
                fvg['filled'] = current_price < fvg['bottom']
                active_fvgs.append(fvg)
        
        return active_fvgs
    
    except Exception as e:
        logger.error(f"Error detecting FVGs: {e}")
        return []


def detect_displacement(closes: List[float], atr: float) -> Optional[Dict]:
    """
    ICT Displacement - strong directional move (breakout)
    Candle move > 1.5x ATR indicates displacement
    """
    try:
        if len(closes) < 3 or not atr:
            return None
        
        last_move = abs(closes[-1] - closes[-2])
        prev_move = abs(closes[-2] - closes[-3])
        
        if last_move > atr * 1.5:
            direction = 'BULLISH' if closes[-1] > closes[-2] else 'BEARISH'
            strength = last_move / atr
            
            return {
                'type': f'{direction}_DISPLACEMENT',
                'strength': strength,
                'confirmed': last_move > prev_move * 2
            }
        
        return None
    
    except Exception as e:
        logger.error(f"Error detecting displacement: {e}")
        return None


def calculate_optimal_trade_entry(sr_data: Dict, fvgs: List[Dict], 
                                   current_price: float) -> Optional[Dict]:
    """
    ICT Optimal Trade Entry (OTE) - 0.62-0.79 Fibonacci retracement
    Combined with FVG and S/R confluence
    """
    try:
        if not sr_data or not sr_data.get('dynamic_support'):
            return None
        
        # Calculate Fibonacci levels for pullback entry
        resistance = sr_data.get('dynamic_resistance', [current_price * 1.02])[0]
        support = sr_data.get('dynamic_support', [current_price * 0.98])[0]
        
        range_size = resistance - support
        
        # OTE zone: 0.62 - 0.79 retracement
        ote_high = support + (range_size * 0.79)
        ote_low = support + (range_size * 0.62)
        
        # Check if price is in OTE zone
        in_ote_zone = ote_low <= current_price <= ote_high
        
        # Confluence with FVG
        fvg_confluence = False
        for fvg in fvgs:
            if not fvg['filled'] and fvg['bottom'] <= current_price <= fvg['top']:
                fvg_confluence = True
                break
        
        return {
            'ote_zone': {'high': ote_high, 'low': ote_low},
            'in_ote_zone': in_ote_zone,
            'fvg_confluence': fvg_confluence,
            'optimal_entry': in_ote_zone and fvg_confluence
        }
    
    except Exception as e:
        logger.error(f"Error calculating OTE: {e}")
        return None


# ===================================
# FIBONACCI AUTO-CALCULATOR
# ===================================

def calculate_fibonacci_extension(swing_low: float, swing_high: float, 
                                   retracement_level: float, direction: str = 'BULLISH') -> Dict:
    """
    Auto-calculate Fibonacci extension levels
    Returns penultimate level for TP target
    """
    try:
        range_size = swing_high - swing_low
        
        if direction == 'BULLISH':
            # Extension levels from retracement
            fib_levels = {
                '0.0': retracement_level,
                '0.382': retracement_level + (range_size * 0.382),
                '0.618': retracement_level + (range_size * 0.618),
                '1.0': retracement_level + range_size,
                '1.272': retracement_level + (range_size * 1.272),
                '1.414': retracement_level + (range_size * 1.414),
                '1.618': retracement_level + (range_size * 1.618),  # Penultimate
                '2.0': retracement_level + (range_size * 2.0)       # Last
            }
        else:  # BEARISH
            fib_levels = {
                '0.0': retracement_level,
                '0.382': retracement_level - (range_size * 0.382),
                '0.618': retracement_level - (range_size * 0.618),
                '1.0': retracement_level - range_size,
                '1.272': retracement_level - (range_size * 1.272),
                '1.414': retracement_level - (range_size * 1.414),
                '1.618': retracement_level - (range_size * 1.618),  # Penultimate
                '2.0': retracement_level - (range_size * 2.0)       # Last
            }
        
        # Penultimate level (1.618) is the main TP target
        penultimate_tp = fib_levels['1.618']
        
        return {
            'all_levels': fib_levels,
            'penultimate_tp': penultimate_tp,
            'final_tp': fib_levels['2.0']
        }
    
    except Exception as e:
        logger.error(f"Error calculating Fibonacci: {e}")
        return None


# ===================================
# COMBINED ANALYSIS
# ===================================

def combined_luxalgo_ict_analysis(opens: List[float], highs: List[float], 
                                   lows: List[float], closes: List[float],
                                   volumes: List[float] = None) -> Dict:
    """
    Master function combining LuxAlgo MTF + ICT Concepts
    Returns comprehensive analysis for entry/SL/TP decisions
    """
    try:
        # LuxAlgo S/R Analysis
        sr_data = calculate_luxalgo_sr_levels(highs, lows, closes, volumes)
        
        # ICT Concepts
        mss = detect_market_structure_shift(highs, lows, closes)
        liquidity_grab = detect_liquidity_grab(highs, lows, closes, volumes)
        fvgs = detect_fair_value_gaps(opens, highs, lows, closes)
        
        # ATR for displacement
        true_ranges = []
        for i in range(1, min(14, len(closes))):
            tr = max(highs[i] - lows[i], 
                    abs(highs[i] - closes[i-1]), 
                    abs(lows[i] - closes[i-1]))
            true_ranges.append(tr)
        atr = np.mean(true_ranges) if true_ranges else 0
        
        displacement = detect_displacement(closes, atr)
        ote = calculate_optimal_trade_entry(sr_data, fvgs, closes[-1])
        
        # Fibonacci calculation
        if sr_data and sr_data.get('dynamic_support') and sr_data.get('dynamic_resistance'):
            swing_low = sr_data['dynamic_support'][0] if sr_data['dynamic_support'] else closes[-1] * 0.98
            swing_high = sr_data['dynamic_resistance'][0] if sr_data['dynamic_resistance'] else closes[-1] * 1.02
            
            # Determine direction from MSS or displacement
            direction = 'BULLISH'
            if mss and 'BEARISH' in mss.get('type', ''):
                direction = 'BEARISH'
            elif displacement and 'BEARISH' in displacement.get('type', ''):
                direction = 'BEARISH'
            
            fib_extension = calculate_fibonacci_extension(swing_low, swing_high, closes[-1], direction)
        else:
            fib_extension = None
        
        return {
            'luxalgo_sr': sr_data,
            'ict_mss': mss,
            'ict_liquidity_grab': liquidity_grab,
            'ict_fvgs': fvgs,
            'ict_displacement': displacement,
            'ict_ote': ote,
            'fibonacci': fib_extension,
            'atr': atr
        }
    
    except Exception as e:
        logger.error(f"Error in combined analysis: {e}")
        return {}


# ===================================
# MULTI-TIMEFRAME CONTINUOUS ANALYSIS
# ===================================

async def analyze_all_timeframes(symbol: str, fetch_klines_func) -> Dict:
    """
    Analyze ALL timeframes continuously
    Monitor entire chart structure across all TFs
    Returns combined MTF analysis
    """
    try:
        timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '3h', '4h', '1d', '1w']
        all_tf_analysis = {}
        
        for tf in timeframes:
            try:
                # Fetch klines for this timeframe
                klines = await fetch_klines_func(symbol, tf, limit=200)
                
                if not klines or len(klines) < 50:
                    continue
                
                # Extract OHLCV
                opens = [float(k[1]) for k in klines]
                highs = [float(k[2]) for k in klines]
                lows = [float(k[3]) for k in klines]
                closes = [float(k[4]) for k in klines]
                volumes = [float(k[5]) for k in klines]
                
                # Run combined analysis
                analysis = combined_luxalgo_ict_analysis(opens, highs, lows, closes, volumes)
                
                # Extract key signals
                signal = determine_tf_signal(analysis)
                
                all_tf_analysis[tf] = {
                    'analysis': analysis,
                    'signal': signal,
                    'price': closes[-1]
                }
                
            except Exception as e:
                logger.error(f"Error analyzing {tf}: {e}")
                continue
        
        # Calculate multi-timeframe consensus
        consensus = calculate_mtf_consensus(all_tf_analysis)
        
        return {
            'timeframes': all_tf_analysis,
            'consensus': consensus
        }
    
    except Exception as e:
        logger.error(f"Error in MTF analysis: {e}")
        return {}


def determine_tf_signal(analysis: Dict) -> str:
    """
    Determine signal direction from analysis data
    """
    try:
        if not analysis:
            return 'NEUTRAL'
        
        bullish_count = 0
        bearish_count = 0
        
        # Check MSS
        mss = analysis.get('ict_mss')
        if mss and mss.get('confirmed'):
            if 'BULLISH' in mss['type']:
                bullish_count += 2
            elif 'BEARISH' in mss['type']:
                bearish_count += 2
        
        # Check S/R breakout
        sr = analysis.get('luxalgo_sr', {})
        breakout = sr.get('breakout_status', 'NONE')
        if 'RESISTANCE' in breakout and 'BREAKOUT' in breakout:
            bullish_count += 1
        elif 'SUPPORT' in breakout and 'BREAKOUT' in breakout:
            bearish_count += 1
        elif 'SUPPORT' in breakout and 'RETEST' in breakout:
            bullish_count += 1
        elif 'RESISTANCE' in breakout and 'RETEST' in breakout:
            bearish_count += 1
        
        # Check FVGs
        fvgs = analysis.get('ict_fvgs', [])
        unfilled = [f for f in fvgs if not f.get('filled')]
        if unfilled:
            latest_fvg = unfilled[-1]
            if latest_fvg['type'] == 'BULLISH_FVG':
                bullish_count += 1
            elif latest_fvg['type'] == 'BEARISH_FVG':
                bearish_count += 1
        
        # Determine signal
        if bullish_count > bearish_count + 1:
            return 'BUY'
        elif bearish_count > bullish_count + 1:
            return 'SELL'
        else:
            return 'NEUTRAL'
    
    except Exception as e:
        logger.error(f"Error determining TF signal: {e}")
        return 'NEUTRAL'


def calculate_mtf_consensus(all_tf_analysis: Dict) -> Dict:
    """
    Calculate consensus across all timeframes
    Weighted by timeframe importance
    """
    try:
        # Timeframe weights (higher TF = more weight)
        tf_weights = {
            '1m': 1, '5m': 2, '15m': 3, '30m': 4, '1h': 5,
            '2h': 6, '3h': 7, '4h': 8, '1d': 10, '1w': 12
        }
        
        buy_score = 0
        sell_score = 0
        neutral_score = 0
        total_weight = 0
        
        for tf, data in all_tf_analysis.items():
            signal = data.get('signal', 'NEUTRAL')
            weight = tf_weights.get(tf, 1)
            
            if signal == 'BUY':
                buy_score += weight
            elif signal == 'SELL':
                sell_score += weight
            else:
                neutral_score += weight
            
            total_weight += weight
        
        # Calculate percentages
        if total_weight > 0:
            buy_pct = (buy_score / total_weight) * 100
            sell_pct = (sell_score / total_weight) * 100
            neutral_pct = (neutral_score / total_weight) * 100
        else:
            buy_pct = sell_pct = neutral_pct = 0
        
        # Determine consensus signal
        if buy_pct > 50:
            consensus_signal = 'BUY'
            consensus_strength = buy_pct
        elif sell_pct > 50:
            consensus_signal = 'SELL'
            consensus_strength = sell_pct
        else:
            consensus_signal = 'NEUTRAL'
            consensus_strength = neutral_pct
        
        return {
            'signal': consensus_signal,
            'strength': consensus_strength,
            'buy_percentage': buy_pct,
            'sell_percentage': sell_pct,
            'neutral_percentage': neutral_pct,
            'timeframes_analyzed': len(all_tf_analysis)
        }
    
    except Exception as e:
        logger.error(f"Error calculating MTF consensus: {e}")
        return {'signal': 'NEUTRAL', 'strength': 0}
