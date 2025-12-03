"""
🔥 LuxAlgo Support/Resistance MTF + ICT Concepts Analysis System
Combined methodology for professional trading signals

Full Pine Script Implementation - Exact TradingView Replication
© LuxAlgo - License: CC BY-NC-SA 4.0
"""

import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Optional
import logging

# Import LuxAlgo modules
from luxalgo_sr_mtf import LuxAlgoSRMTF, LuxAlgoSignal, SnRZone
from luxalgo_ict_concepts import LuxAlgoICT, OrderBlock, FairValueGap, MarketStructure, LiquidityLevel

logger = logging.getLogger(__name__)


class CombinedLuxAlgoAnalysis:
    """
    Combined LuxAlgo Analysis System
    
    Integrates:
    1. Support & Resistance Signals MTF
    2. ICT Concepts (Smart Money)
    
    Entry Conditions:
    - Market Structure Shift (ICT) +
    - S/R Retest (LuxAlgo MTF) +
    - Signal Confirmation (LuxAlgo MTF)
    """
    
    def __init__(
        self,
        sr_detection_length: int = 15,
        sr_margin: float = 2.0,
        ict_swing_length: int = 10,
        enable_sr: bool = True,
        enable_ict: bool = True
    ):
        # Initialize both analyzers
        self.sr_analyzer = LuxAlgoSRMTF(
            detection_length=sr_detection_length,
            sr_margin=sr_margin,
            avoid_false_breakouts=True,
            check_historical_sr=True
        ) if enable_sr else None
        
        self.ict_analyzer = LuxAlgoICT(
            swing_length=ict_swing_length,
            show_ob=True,
            show_fvg=True,
            show_liquidity=True,
            show_structure=True
        ) if enable_ict else None
        
        self.enable_sr = enable_sr
        self.enable_ict = enable_ict
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Perform combined LuxAlgo analysis
        
        Args:
            df: DataFrame with columns: open, high, low, close, volume
        
        Returns:
            Complete analysis with both S/R and ICT elements
        """
        results = {
            'sr_data': None,
            'ict_data': None,
            'combined_signal': None,
            'entry_valid': False,
            'sl_price': None,
            'tp_price': None,
            'bias': 'neutral'
        }
        
        try:
            # Run S/R MTF analysis
            if self.enable_sr and self.sr_analyzer:
                sr_results = self.sr_analyzer.analyze(df)
                results['sr_data'] = sr_results
                logger.info(f"S/R Analysis: {len(sr_results.get('support_zones', []))} support, "
                           f"{len(sr_results.get('resistance_zones', []))} resistance zones")
            
            # Run ICT analysis
            if self.enable_ict and self.ict_analyzer:
                ict_results = self.ict_analyzer.analyze(df)
                results['ict_data'] = ict_results
                logger.info(f"ICT Analysis: {len(ict_results.get('order_blocks', []))} OBs, "
                           f"{len(ict_results.get('fvgs', []))} FVGs, "
                           f"trend: {ict_results.get('trend')}")
            
            # Generate combined trading signal
            if self.enable_sr and self.enable_ict and results['sr_data'] and results['ict_data']:
                combined = self._generate_combined_signal(
                    df,
                    results['sr_data'],
                    results['ict_data']
                )
                results.update(combined)
            
            return results
            
        except Exception as e:
            logger.error(f"Error in combined LuxAlgo analysis: {e}")
            return results
    
    def _generate_combined_signal(
        self,
        df: pd.DataFrame,
        sr_data: Dict,
        ict_data: Dict
    ) -> Dict:
        """
        Generate combined trading signal based on both methodologies
        
        Entry Rules:
        1. MSS/BOS detected (ICT) +
        2. Price interacts with S/R zone (LuxAlgo MTF) +
        3. Signal confirmation from LuxAlgo (breakout/retest/test)
        """
        current_price = df.iloc[-1]['close']
        
        # Get latest structure from ICT
        last_structure = ict_data.get('last_structure')
        ict_trend = ict_data.get('trend', 'neutral')
        
        # Get latest signals from S/R MTF
        sr_signals = sr_data.get('signals', [])
        latest_sr_signal = sr_signals[-1] if sr_signals else None
        
        # Get zones
        support_zones = sr_data.get('support_zones', [])
        resistance_zones = sr_data.get('resistance_zones', [])
        
        # Check for valid entry
        entry_valid = False
        bias = 'neutral'
        signal_strength = 0
        
        # Bullish Setup
        if (last_structure and 
            last_structure.direction == 'bullish' and
            latest_sr_signal and
            latest_sr_signal.direction == 'bullish'):
            
            # Check if signal type is valid (retest or test of support)
            if latest_sr_signal.type in ['retest', 'test']:
                entry_valid = True
                bias = 'bullish'
                signal_strength = 70
                
                # Increase strength if structure is MSS
                if last_structure.type == 'MSS':
                    signal_strength += 15
                
                # Check for additional confirmation
                if ict_data.get('price_zone') == 'discount':
                    signal_strength += 15
        
        # Bearish Setup
        elif (last_structure and 
              last_structure.direction == 'bearish' and
              latest_sr_signal and
              latest_sr_signal.direction == 'bearish'):
            
            if latest_sr_signal.type in ['retest', 'test']:
                entry_valid = True
                bias = 'bearish'
                signal_strength = 70
                
                if last_structure.type == 'MSS':
                    signal_strength += 15
                
                if ict_data.get('price_zone') == 'premium':
                    signal_strength += 15
        
        # Calculate SL and TP
        sl_price = self._calculate_stop_loss(
            current_price,
            bias,
            support_zones,
            resistance_zones,
            ict_data.get('liquidity_levels', [])
        )
        
        tp_price = self._calculate_take_profit(
            current_price,
            bias,
            df,
            ict_data,
            sr_data
        )
        
        return {
            'entry_valid': entry_valid,
            'bias': bias,
            'signal_strength': signal_strength,
            'sl_price': sl_price,
            'tp_price': tp_price,
            'last_structure': last_structure,
            'latest_sr_signal': latest_sr_signal,
            'ict_trend': ict_trend
        }
    
    def _calculate_stop_loss(
        self,
        current_price: float,
        bias: str,
        support_zones: List[SnRZone],
        resistance_zones: List[SnRZone],
        liquidity_levels: List[LiquidityLevel]
    ) -> Optional[float]:
        """
        Calculate stop loss based on:
        - Nearest S/R zone
        - Liquidity sweep level
        Choose the more conservative option
        """
        if bias == 'neutral':
            return None
        
        candidates = []
        
        if bias == 'bullish':
            # SL below support or below liquidity sweep
            for zone in support_zones:
                if zone.bottom < current_price:
                    candidates.append(zone.bottom)
            
            for liq in liquidity_levels:
                if not liq.is_buy_side and liq.price < current_price:
                    candidates.append(liq.price)
            
            # Most conservative = highest price below current
            return max(candidates) * 0.995 if candidates else current_price * 0.98
        
        else:  # bearish
            # SL above resistance or above liquidity sweep
            for zone in resistance_zones:
                if zone.top > current_price:
                    candidates.append(zone.top)
            
            for liq in liquidity_levels:
                if liq.is_buy_side and liq.price > current_price:
                    candidates.append(liq.price)
            
            # Most conservative = lowest price above current
            return min(candidates) * 1.005 if candidates else current_price * 1.02
    
    def _calculate_take_profit(
        self,
        current_price: float,
        bias: str,
        df: pd.DataFrame,
        ict_data: Dict,
        sr_data: Dict
    ) -> Optional[float]:
        """
        Calculate take profit using:
        1. ICT targets (liquidity pools, FVG close)
        2. Fibonacci extension (penultimate level)
        Choose the closest safe target
        """
        if bias == 'neutral':
            return None
        
        targets = []
        
        # ICT Targets
        if bias == 'bullish':
            # Target: Next resistance zone or liquidity level
            for zone in sr_data.get('resistance_zones', []):
                if zone.bottom > current_price:
                    targets.append(zone.bottom)
            
            for liq in ict_data.get('liquidity_levels', []):
                if liq.is_buy_side and liq.price > current_price and not liq.swept:
                    targets.append(liq.price)
            
            # Unfilled FVG as target
            for fvg in ict_data.get('fvgs', []):
                if not fvg.is_bullish and fvg.bottom > current_price and not fvg.mitigated:
                    targets.append(fvg.bottom)
        
        else:  # bearish
            for zone in sr_data.get('support_zones', []):
                if zone.top < current_price:
                    targets.append(zone.top)
            
            for liq in ict_data.get('liquidity_levels', []):
                if not liq.is_buy_side and liq.price < current_price and not liq.swept:
                    targets.append(liq.price)
            
            for fvg in ict_data.get('fvgs', []):
                if fvg.is_bullish and fvg.top < current_price and not fvg.mitigated:
                    targets.append(fvg.top)
        
        # Fibonacci Targets
        fib_target = self._calculate_fibonacci_target(df, bias, current_price)
        if fib_target:
            targets.append(fib_target)
        
        # Return closest target
        if not targets:
            return current_price * 1.02 if bias == 'bullish' else current_price * 0.98
        
        if bias == 'bullish':
            return min(targets)  # Closest above
        else:
            return max(targets)  # Closest below
    
    def _calculate_fibonacci_target(
        self,
        df: pd.DataFrame,
        bias: str,
        current_price: float
    ) -> Optional[float]:
        """
        Calculate Fibonacci extension - use penultimate level (1.618 or 2.618)
        """
        try:
            # Get recent swing high and low
            recent_high = df['high'].iloc[-50:].max()
            recent_low = df['low'].iloc[-50:].min()
            range_size = recent_high - recent_low
            
            if bias == 'bullish':
                # Fibonacci extension above recent high
                fib_1618 = recent_high + (range_size * 0.618)
                fib_2618 = recent_high + (range_size * 1.618)
                # Return penultimate level (1.618)
                return fib_2618
            else:
                # Fibonacci extension below recent low
                fib_1618 = recent_low - (range_size * 0.618)
                fib_2618 = recent_low - (range_size * 1.618)
                return fib_2618
                
        except Exception as e:
            logger.error(f"Fibonacci calculation error: {e}")
            return None


# Legacy function wrappers for backward compatibility
def calculate_luxalgo_sr_levels(highs: List[float], lows: List[float], closes: List[float], 
                                  volumes: List[float] = None) -> Dict:
    """Legacy wrapper - converts to DataFrame and uses new system"""
    try:
        df = pd.DataFrame({
            'high': highs,
            'low': lows,
            'close': closes,
            'open': closes,  # Approximate
            'volume': volumes if volumes else [0] * len(closes)
        })
        
        analyzer = CombinedLuxAlgoAnalysis()
        results = analyzer.analyze(df)
        
        # Convert to legacy format
        sr_data = results.get('sr_data', {})
        support_zones = sr_data.get('support_zones', [])
        resistance_zones = sr_data.get('resistance_zones', [])
        
        return {
            'dynamic_resistance': [z.top for z in resistance_zones[:3]],
            'dynamic_support': [z.bottom for z in support_zones[:3]],
            'static_resistance': max(highs) if highs else None,
            'static_support': min(lows) if lows else None,
            'current_price': closes[-1] if closes else None,
            'breakout_status': 'detected' if sr_data.get('signals') else 'none'
        }
    except Exception as e:
        logger.error(f"Legacy S/R calculation error: {e}")
        return None


# Legacy function - deprecated but kept for compatibility
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
