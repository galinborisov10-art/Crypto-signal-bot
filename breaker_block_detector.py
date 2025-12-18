"""
Breaker Block Detector
Identifies order blocks that have been breached and now act with opposite polarity.
"""

from dataclasses import dataclass
from typing import List, Optional
from enum import Enum
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class BreakerBlockType(Enum):
    """Breaker block types"""
    BULLISH_BREAKER = "BULLISH_BREAKER"  # Was bearish OB, now bullish support
    BEARISH_BREAKER = "BEARISH_BREAKER"  # Was bullish OB, now bearish resistance


@dataclass
class BreakerBlock:
    """Breaker Block data structure"""
    type: BreakerBlockType
    original_type: str  # Original OB type before breach
    price_low: float
    price_high: float
    price_mid: float
    breach_price: float
    breach_index: int
    index: int  # Original OB index
    strength: float  # 0-10 scale
    volume_spike: float
    status: str  # ACTIVE, TESTED, INVALIDATED
    retest_count: int = 0
    
    def to_dict(self):
        return {
            'type': self.type.value,
            'original_type': self.original_type,
            'price_low': self.price_low,
            'price_high': self.price_high,
            'price_mid': self.price_mid,
            'breach_price': self.breach_price,
            'breach_index': self.breach_index,
            'strength': self.strength,
            'status': self.status,
            'retest_count': self.retest_count
        }


class BreakerBlockDetector:
    """
    Detects Breaker Blocks - Order Blocks that have been breached
    
    Logic:
    1. Takes existing Order Blocks
    2. Checks if price has breached them (close beyond zone)
    3. Marks breached OBs as Breaker Blocks with flipped polarity
    4. Calculates new strength based on breach characteristics
    """
    
    def __init__(self, config: Optional[dict] = None):
        self.config = config or self._get_default_config()
        logger.info("BreakerBlockDetector initialized")
    
    def _get_default_config(self) -> dict:
        return {
            'breach_threshold': 0.001,  # 0.1% beyond zone to confirm breach
            'min_strength': 3.0,  # Minimum strength to consider
            'strength_retention': 0.75,  # Breaker retains 75% of original OB strength
        }
    
    def detect_breaker_blocks(
        self, 
        df: pd.DataFrame,
        order_blocks: List
    ) -> List[BreakerBlock]:
        """
        Detect breaker blocks from order blocks
        
        Args:
            df: OHLCV dataframe
            order_blocks: List of OrderBlock objects
            
        Returns:
            List of BreakerBlock objects
        """
        if not order_blocks:
            return []
        
        breaker_blocks = []
        current_price = df['close'].iloc[-1]
        
        for ob in order_blocks:
            # Skip if OB strength too low
            if hasattr(ob, 'strength') and ob.strength < self.config['min_strength']:
                continue
            
            # Check if OB is breached
            breach_info = self._check_breach(df, ob, current_price)
            
            if breach_info:
                breaker = self._create_breaker_block(ob, breach_info, df)
                if breaker:
                    breaker_blocks.append(breaker)
                    logger.debug(f"Detected {breaker.type.value} at {breaker.price_mid:.2f}")
        
        return breaker_blocks
    
    def _check_breach(self, df: pd.DataFrame, ob, current_price: float) -> Optional[dict]:
        """
        Check if order block has been breached
        
        Returns breach info dict or None
        """
        ob_type = str(ob.type.value) if hasattr(ob.type, 'value') else str(ob.type)
        threshold = self.config['breach_threshold']
        
        # Get OB boundaries
        ob_top = ob.top if hasattr(ob, 'top') else ob.price_high
        ob_bottom = ob.bottom if hasattr(ob, 'bottom') else ob.price_low
        ob_index = ob.index if hasattr(ob, 'index') else ob.candle_index if hasattr(ob, 'candle_index') else 0
        
        # Check for breach after OB formation
        for i in range(ob_index + 1, len(df)):
            close = df['close'].iloc[i]
            
            if 'BULLISH' in ob_type:
                # Bullish OB breached downward
                breach_level = ob_bottom * (1 - threshold)
                if close < breach_level:
                    return {
                        'breach_price': close,
                        'breach_index': i,
                        'direction': 'DOWN',
                        'new_type': BreakerBlockType.BEARISH_BREAKER
                    }
            
            elif 'BEARISH' in ob_type:
                # Bearish OB breached upward  
                breach_level = ob_top * (1 + threshold)
                if close > breach_level:
                    return {
                        'breach_price': close,
                        'breach_index': i,
                        'direction': 'UP',
                        'new_type': BreakerBlockType.BULLISH_BREAKER
                    }
        
        return None
    
    def _create_breaker_block(self, ob, breach_info: dict, df: pd.DataFrame) -> Optional[BreakerBlock]:
        """Create BreakerBlock from breached OrderBlock"""
        try:
            ob_top = ob.top if hasattr(ob, 'top') else ob.price_high
            ob_bottom = ob.bottom if hasattr(ob, 'bottom') else ob.price_low
            ob_strength = ob.strength if hasattr(ob, 'strength') else 5.0
            ob_type = str(ob.type.value) if hasattr(ob.type, 'value') else str(ob.type)
            ob_index = ob.index if hasattr(ob, 'index') else ob.candle_index if hasattr(ob, 'candle_index') else 0
            
            # Calculate volume spike at breach
            breach_idx = breach_info['breach_index']
            if 'volume' in df.columns:
                breach_volume = df['volume'].iloc[breach_idx]
                avg_volume = df['volume'].iloc[max(0, breach_idx-20):breach_idx].mean()
                volume_spike = breach_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                volume_spike = 1.0
            
            # Breaker strength = original OB strength × retention factor
            breaker_strength = ob_strength * self.config['strength_retention']
            
            # Add bonus for strong volume spike
            if volume_spike > 2.0:
                breaker_strength *= 1.2
            
            breaker = BreakerBlock(
                type=breach_info['new_type'],
                original_type=ob_type,
                price_low=ob_bottom,
                price_high=ob_top,
                price_mid=(ob_top + ob_bottom) / 2,
                breach_price=breach_info['breach_price'],
                breach_index=breach_info['breach_index'],
                index=ob_index,
                strength=min(10.0, breaker_strength),
                volume_spike=volume_spike,
                status='ACTIVE',
                retest_count=0
            )
            
            return breaker
            
        except Exception as e:
            logger.error(f"Error creating breaker block: {e}")
            return None
