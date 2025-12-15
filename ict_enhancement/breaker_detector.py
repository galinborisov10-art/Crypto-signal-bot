"""
🔥 Breaker Block Detector - ICT Enhancement Layer
Детектира Breaker Blocks (пробити Order Blocks, които стават противоположни зони)
"""

from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def detect_breaker_blocks(
    highs: List[float],
    lows: List[float],
    closes: List[float],
    order_blocks: List[Dict],
    lookback:  int = 50
) -> List[Dict]:
    """
    Детектира Breaker Blocks (пробити Bullish OB → Bearish resistance, Bearish OB → Bullish support)
    
    Args:
        highs:  High цени
        lows: Low цени
        closes: Close цени
        order_blocks: Списък с Order Blocks от главния анализ
        lookback:  Периоди назад за проверка
        
    Returns:
        List[Dict]: Списък с Breaker Blocks
    """
    try:
        breaker_blocks = []
        
        for ob in order_blocks:
            ob_type = ob. get('type')
            ob_high = ob.get('high')
            ob_low = ob.get('low')
            ob_index = ob.get('index', 0)
            
            # Проверяваме дали Order Block е пробит
            for i in range(ob_index + 1, min(ob_index + lookback, len(closes))):
                
                # Bullish OB пробит надолу → става Bearish Breaker
                if ob_type == 'bullish' and closes[i] < ob_low:
                    breaker_blocks.append({
                        'type': 'bearish_breaker',
                        'original_type': 'bullish_ob',
                        'high': ob_high,
                        'low': ob_low,
                        'break_index': i,
                        'break_price': closes[i],
                        'strength': 'high' if (ob_low - closes[i]) / ob_low > 0.01 else 'medium'
                    })
                    logger.info(f"🔴 Bearish Breaker detected @ {ob_low:.2f} (broken at {closes[i]:.2f})")
                    break
                
                # Bearish OB пробит нагоре → става Bullish Breaker
                elif ob_type == 'bearish' and closes[i] > ob_high: 
                    breaker_blocks. append({
                        'type':  'bullish_breaker',
                        'original_type':  'bearish_ob',
                        'high': ob_high,
                        'low': ob_low,
                        'break_index': i,
                        'break_price': closes[i],
                        'strength': 'high' if (closes[i] - ob_high) / ob_high > 0.01 else 'medium'
                    })
                    logger. info(f"🟢 Bullish Breaker detected @ {ob_high:.2f} (broken at {closes[i]:.2f})")
                    break
        
        return breaker_blocks
        
    except Exception as e: 
        logger.error(f"❌ Error detecting Breaker Blocks: {e}")
        return []
