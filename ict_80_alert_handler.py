"""
ICT 80% TP Alert Handler
Pure ICT re-analysis when position reaches 80% to TP
Uses SAME logic as ict_signal_engine. generate_signal()
"""

import logging
from datetime import datetime
from typing import Dict, Optional
import pandas as pd

logger = logging.getLogger(__name__)

class ICT80AlertHandler:
    """Handles 80% TP alerts with ICT re-analysis"""
    
    def __init__(self, ict_engine):
        """
        Args:
            ict_engine:  Instance of ICTSignalEngine
        """
        self.ict_engine = ict_engine
        
    async def analyze_position(
        self,
        symbol: str,
        timeframe: str,
        signal_type: str,
        entry_price: float,
        tp_price: float,
        current_price: float,
        original_confidence: float,
        klines: list
    ) -> Dict:
        """
        Re-analyze position using ICT methodology
        
        Returns:
            {
                'recommendation': 'HOLD' | 'PARTIAL_CLOSE' | 'CLOSE_NOW',
                'confidence': float,  # New confidence %
                'reasoning': str,
                'score_hold': int,
                'score_close': int,
                'warnings': list
            }
        """
        
        try:
            # 1. Convert klines to DataFrame
            df = self._klines_to_dataframe(klines)
            
            if len(df) < 50:
                logger.warning("Insufficient data for ICT re-analysis")
                return self._fallback_response("Insufficient data")
            
            # 2. Generate FRESH ICT signal
            fresh_signal = self. ict_engine.generate_signal(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                mtf_data=None  # TODO: Add MTF data if available
            )
            
            if not fresh_signal:
                logger.warning("No fresh ICT signal generated")
                return self._fallback_response("No signal")
            
            # 3. Compare fresh vs original signal
            return self._compare_signals(
                original_type=signal_type,
                original_confidence=original_confidence,
                fresh_signal=fresh_signal,
                current_price=current_price,
                entry_price=entry_price,
                tp_price=tp_price
            )
            
        except Exception as e:
            logger.error(f"Error in ICT 80% re-analysis: {e}")
            return self._fallback_response(f"Error: {e}")
    
    def _klines_to_dataframe(self, klines: list) -> pd.DataFrame:
        """Convert Binance klines to DataFrame"""
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 
            'taker_buy_base', 'taker_buy_quote', 'ignore'
        ])
        
        # Convert types
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        df = df.set_index('timestamp')
        
        return df[['open', 'high', 'low', 'close', 'volume']]
    
    def _compare_signals(
        self,
        original_type: str,
        original_confidence: float,
        fresh_signal,
        current_price:  float,
        entry_price:  float,
        tp_price:  float
    ) -> Dict:
        """
        Compare original signal with fresh ICT analysis
        
        Decision Logic:
        1. If fresh signal SAME direction + high confidence → HOLD
        2. If fresh signal OPPOSITE direction → CLOSE NOW
        3. If fresh signal weaker/no signal → PARTIAL CLOSE
        4. Check structure breaks, liquidity, order blocks
        """
        
        hold_score = 0
        close_score = 0
        warnings = []
        reasoning_parts = []
        
        # === 1. SIGNAL DIRECTION ===
        fresh_type = fresh_signal. signal_type. value  # 'BUY' or 'SELL'
        
        if fresh_type == original_type:
            hold_score += 3
            reasoning_parts.append(f"✅ ICT bias все още {original_type}")
        elif fresh_type == ('SELL' if original_type == 'BUY' else 'BUY'):
            close_score += 5
            warnings.append(f"⚠️ ICT bias обърна към {fresh_type}!")
            reasoning_parts.append(f"❌ ICT bias обърна към {fresh_type}")
        
        # === 2. CONFIDENCE CHANGE ===
        confidence_diff = fresh_signal.confidence - original_confidence
        
        if confidence_diff > 10: 
            hold_score += 2
            reasoning_parts.append(f"✅ Увереност нараства ({fresh_signal.confidence:.1f}%)")
        elif confidence_diff < -15:
            close_score += 2
            warnings.append(f"⚠️ Увереност пада ({fresh_signal.confidence:. 1f}%)")
            reasoning_parts.append(f"⚠️ Увереност пада до {fresh_signal.confidence:.1f}%")
        else:
            reasoning_parts.append(f"📊 Увереност стабилна ({fresh_signal. confidence:.1f}%)")
        
        # === 3. STRUCTURE BREAK ===
        if fresh_signal.structure_broken:
            if fresh_signal.bias. value == original_type:
                hold_score += 2
                reasoning_parts.append(f"✅ Structure break потвърждава {original_type}")
            else:
                close_score += 3
                warnings.append("⚠️ Structure break обръща!")
                reasoning_parts.append("❌ Structure break в обратна посока")
        
        # === 4. DISPLACEMENT ===
        if fresh_signal.displacement_detected:
            if fresh_signal. bias.value == original_type:
                hold_score += 2
                reasoning_parts.append("✅ Displacement силен")
            else:
                close_score += 2
                warnings.append("⚠️ Displacement обръща")
        
        # === 5. MTF CONFLUENCE ===
        if fresh_signal.mtf_confluence >= 2:
            hold_score += 2
            reasoning_parts.append(f"✅ MTF confluence силен ({fresh_signal.mtf_confluence})")
        elif fresh_signal.mtf_confluence == 0:
            close_score += 1
            reasoning_parts.append("⚠️ Няма MTF confluence")
        
        # === 6. ORDER BLOCKS ===
        bullish_obs = len([ob for ob in fresh_signal.order_blocks if 'BULLISH' in str(ob. get('type', ''))])
        bearish_obs = len([ob for ob in fresh_signal.order_blocks if 'BEARISH' in str(ob.get('type', ''))])
        
        if original_type == 'BUY':
            if bullish_obs > bearish_obs:
                hold_score += 1
                reasoning_parts.append(f"✅ Bullish OBs доминират ({bullish_obs})")
            elif bearish_obs > bullish_obs:
                close_score += 1
                reasoning_parts.append(f"⚠️ Bearish OBs нарастват ({bearish_obs})")
        else:  # SELL
            if bearish_obs > bullish_obs:
                hold_score += 1
                reasoning_parts.append(f"✅ Bearish OBs доминират ({bearish_obs})")
            elif bullish_obs > bearish_obs:
                close_score += 1
                reasoning_parts.append(f"⚠️ Bullish OBs нарастват ({bullish_obs})")
        
        # === 7. LIQUIDITY ZONES ===
        if len(fresh_signal.liquidity_zones) > 0:
            # Check if price near major liquidity
            for lz in fresh_signal.liquidity_zones[: 3]:  # Top 3
                lz_price = lz.get('price', 0)
                distance_pct = abs(current_price - lz_price) / current_price * 100
                
                if distance_pct < 2:  # Within 2%
                    if original_type == 'BUY' and lz_price > current_price:
                        hold_score += 1
                        reasoning_parts.append(f"✅ Ликвидност над цената при ${lz_price:.4f}")
                    elif original_type == 'SELL' and lz_price < current_price:
                        hold_score += 1
                        reasoning_parts.append(f"✅ Ликвидност под цената при ${lz_price:.4f}")
                    else:
                        close_score += 1
                        warnings.append(f"⚠️ Ликвидност може да обърне при ${lz_price:.4f}")
        
        # === DECISION ===
        if hold_score >= close_score + 3:
            recommendation = 'HOLD'
        elif close_score >= hold_score + 2:
            recommendation = 'CLOSE_NOW'
        else: 
            recommendation = 'PARTIAL_CLOSE'
        
        return {
            'recommendation': recommendation,
            'confidence': fresh_signal.confidence,
            'reasoning': '\n'.join(reasoning_parts),
            'score_hold': hold_score,
            'score_close': close_score,
            'warnings': warnings,
            'fresh_signal': fresh_signal
        }
    
    def _fallback_response(self, reason: str) -> Dict:
        """Fallback when ICT analysis fails"""
        return {
            'recommendation': 'PARTIAL_CLOSE',  # Safe default
            'confidence': 0,
            'reasoning': f"Не мога да реанализирам:  {reason}\nПрепоръчвам частично затваряне за сигурност.",
            'score_hold': 0,
            'score_close': 0,
            'warnings': [f"⚠️ {reason}"],
            'fresh_signal': None
        }

