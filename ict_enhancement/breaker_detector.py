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
    order_blocks: List,
    lookback: int = 50
) -> List[Dict]:
    """
    Детектира Breaker Blocks (пробити Bullish OB → Bearish resistance, Bearish OB → Bullish support)
    
    ✅ FIX #2: Enhanced to handle both dict and object types for OrderBlocks
    
    Args:
        highs: High цени
        lows: Low цени
        closes: Close цени
        order_blocks: Списък с Order Blocks (dict or object instances)
        lookback: Периоди назад за проверка
        
    Returns:
        List[Dict]: Списък с Breaker Blocks
    """
    try:
        breaker_blocks = []
        
        for ob in order_blocks:
            try:
                # ✅ FIX #2: Type-agnostic data extraction
                if isinstance(ob, dict):
                    # Dictionary type
                    ob_type = ob.get('type', '')
                    ob_high = ob.get('zone_high') or ob.get('top') or ob.get('high')
                    ob_low = ob.get('zone_low') or ob.get('bottom') or ob.get('low')
                    ob_index = ob.get('index') or ob.get('candle_index', 0)
                else:
                    # Object type (class instance)
                    ob_type = str(getattr(ob, 'type', ''))
                    # Handle enum types
                    if hasattr(ob_type, 'value'):
                        ob_type = ob_type.value
                    ob_high = (getattr(ob, 'zone_high', None) or 
                              getattr(ob, 'top', None) or 
                              getattr(ob, 'high', None))
                    ob_low = (getattr(ob, 'zone_low', None) or 
                             getattr(ob, 'bottom', None) or 
                             getattr(ob, 'low', None))
                    ob_index = (getattr(ob, 'index', None) or 
                               getattr(ob, 'candle_index', 0))
                
                # Validate required fields exist
                if not ob_high or not ob_low or not ob_type:
                    logger.warning(f"⚠️ Skipping invalid OB (missing bounds or type)")
                    continue
                
                # Ensure ob_index is valid
                if ob_index >= len(closes):
                    logger.warning(f"⚠️ Skipping OB with invalid index {ob_index} >= {len(closes)}")
                    continue
                
                # Normalize ob_type to lowercase for comparison
                ob_type_lower = str(ob_type).lower()
                
                # Проверяваме дали Order Block е пробит
                for i in range(ob_index + 1, min(ob_index + lookback, len(closes))):
                    
                    # Bullish OB пробит надолу → става Bearish Breaker
                    if 'bullish' in ob_type_lower and closes[i] < ob_low:
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
                    elif 'bearish' in ob_type_lower and closes[i] > ob_high:
                        breaker_blocks.append({
                            'type': 'bullish_breaker',
                            'original_type': 'bearish_ob',
                            'high': ob_high,
                            'low': ob_low,
                            'break_index': i,
                            'break_price': closes[i],
                            'strength': 'high' if (closes[i] - ob_high) / ob_high > 0.01 else 'medium'
                        })
                        logger.info(f"🟢 Bullish Breaker detected @ {ob_high:.2f} (broken at {closes[i]:.2f})")
                        break
                        
            except Exception as e:
                logger.warning(f"⚠️ Error processing OB for breaker detection: {e}")
                continue
        
        return breaker_blocks
        
    except Exception as e:
        logger.error(f"❌ Error detecting Breaker Blocks: {e}")
        return []
