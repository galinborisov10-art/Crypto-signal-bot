"""
🐋 ICT WHALE ORDER BLOCK DETECTOR
High-Quality Institutional Order Detection System
Identifies HQPO (High-Quality Unprocessed Orders)

Methodology:
1. Displacement detection (large moves without pullback)
2. Fair Value Gap (FVG) identification immediately after
3. Wick-less candles (institutional absorption)
4. Volume spike confirmation
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class WhaleOrderBlock:
    """Whale Order Block structure"""
    price_level: float
    zone_high: float
    zone_low: float
    zone_type: str  # 'buy' or 'sell'
    confidence: int  # 0-100
    displacement_pct: float
    has_fvg: bool
    wickless_candles: int
    volume_spike: float
    timeframe: str
    identified_at: datetime
    still_valid: bool = True
    explanation: str = ""
    
    def to_dict(self) -> Dict:
        return {
            'price_level': self.price_level,
            'zone_high': self.zone_high,
            'zone_low': self.zone_low,
            'zone_type': self.zone_type,
            'confidence': self.confidence,
            'displacement_pct': self.displacement_pct,
            'has_fvg': self.has_fvg,
            'wickless_candles': self.wickless_candles,
            'volume_spike': self.volume_spike,
            'timeframe': self.timeframe,
            'identified_at': self.identified_at.isoformat(),
            'still_valid': self.still_valid,
            'explanation': self.explanation
        }


class WhaleDetector:
    """
    Whale Order Block Detection System
    
    Identifies institutional order blocks using:
    - Displacement (sudden price moves)
    - Fair Value Gaps (FVG)
    - Wickless candles (clean institutional absorption)
    - Volume confirmation
    """
    
    def __init__(
        self,
        displacement_threshold: float = 1.5,  # % move to qualify as displacement
        fvg_min_size: float = 0.3,  # Minimum FVG size in %
        volume_spike_threshold: float = 1.5,  # Volume vs average
        lookback_period: int = 20
    ):
        self.displacement_threshold = displacement_threshold
        self.fvg_min_size = fvg_min_size
        self.volume_spike_threshold = volume_spike_threshold
        self.lookback_period = lookback_period
    
    def detect_displacement(self, df: pd.DataFrame, idx: int) -> Tuple[bool, float]:
        """
        Detect displacement - rapid price movement without retracement
        
        Returns: (is_displacement, displacement_percentage)
        """
        if idx < 3:
            return False, 0.0
        
        try:
            current_close = df.iloc[idx]['close']
            prev_close = df.iloc[idx - 1]['close']
            
            # Calculate price change
            price_change_pct = abs((current_close - prev_close) / prev_close * 100)
            
            # Check if it's a displacement
            if price_change_pct >= self.displacement_threshold:
                # Verify no significant pullback in previous candles
                prev_3_range = df.iloc[idx-3:idx]['close'].max() - df.iloc[idx-3:idx]['close'].min()
                prev_3_range_pct = (prev_3_range / prev_close) * 100
                
                # If previous range was small (consolidation) before big move = displacement
                if prev_3_range_pct < self.displacement_threshold:
                    return True, price_change_pct
            
            return False, price_change_pct
            
        except Exception as e:
            logger.error(f"Displacement detection error: {e}")
            return False, 0.0
    
    def detect_fvg(self, df: pd.DataFrame, idx: int) -> Tuple[bool, Optional[Dict]]:
        """
        Detect Fair Value Gap after displacement
        
        FVG = Gap between:
        - Bullish: candle[i-2].low > candle[i].high
        - Bearish: candle[i-2].high < candle[i].low
        """
        if idx < 2:
            return False, None
        
        try:
            current = df.iloc[idx]
            prev_1 = df.iloc[idx - 1]
            prev_2 = df.iloc[idx - 2]
            
            # Bullish FVG
            if prev_2['low'] > current['high']:
                gap_size = prev_2['low'] - current['high']
                gap_pct = (gap_size / current['close']) * 100
                
                if gap_pct >= self.fvg_min_size:
                    return True, {
                        'type': 'bullish',
                        'gap_high': prev_2['low'],
                        'gap_low': current['high'],
                        'gap_size_pct': gap_pct
                    }
            
            # Bearish FVG
            if prev_2['high'] < current['low']:
                gap_size = current['low'] - prev_2['high']
                gap_pct = (gap_size / current['close']) * 100
                
                if gap_pct >= self.fvg_min_size:
                    return True, {
                        'type': 'bearish',
                        'gap_high': current['low'],
                        'gap_low': prev_2['high'],
                        'gap_size_pct': gap_pct
                    }
            
            return False, None
            
        except Exception as e:
            logger.error(f"FVG detection error: {e}")
            return False, None
    
    def detect_wickless_candles(self, df: pd.DataFrame, idx: int, direction: str) -> int:
        """
        Count wickless or near-wickless candles
        
        Wickless = institutional absorption without retail participation
        """
        try:
            count = 0
            lookback = min(5, idx)
            
            for i in range(idx - lookback, idx + 1):
                candle = df.iloc[i]
                body_size = abs(candle['close'] - candle['open'])
                full_range = candle['high'] - candle['low']
                
                if full_range == 0:
                    continue
                
                body_ratio = body_size / full_range
                
                # Wickless if body is > 90% of full range
                if body_ratio > 0.90:
                    # Check direction matches
                    if direction == 'bullish' and candle['close'] > candle['open']:
                        count += 1
                    elif direction == 'bearish' and candle['close'] < candle['open']:
                        count += 1
            
            return count
            
        except Exception as e:
            logger.error(f"Wickless detection error: {e}")
            return 0
    
    def detect_volume_spike(self, df: pd.DataFrame, idx: int) -> float:
        """
        Detect volume spike compared to average
        
        Returns: volume_ratio (current / average)
        """
        try:
            if 'volume' not in df.columns or idx < self.lookback_period:
                return 1.0
            
            current_volume = df.iloc[idx]['volume']
            avg_volume = df.iloc[idx - self.lookback_period:idx]['volume'].mean()
            
            if avg_volume == 0:
                return 1.0
            
            volume_ratio = current_volume / avg_volume
            return volume_ratio
            
        except Exception as e:
            logger.error(f"Volume spike detection error: {e}")
            return 1.0
    
    def calculate_confidence(
        self,
        displacement_pct: float,
        has_fvg: bool,
        wickless_count: int,
        volume_spike: float
    ) -> Tuple[int, str]:
        """
        Calculate confidence score for whale order block
        
        Returns: (confidence 0-100, explanation)
        """
        confidence = 0
        explanation_parts = []
        
        # Displacement component (0-40 points)
        if displacement_pct >= self.displacement_threshold:
            displacement_score = min(40, int((displacement_pct / self.displacement_threshold) * 20))
            confidence += displacement_score
            explanation_parts.append(f"Displacement: {displacement_pct:.2f}% (+{displacement_score})")
        
        # FVG component (0-25 points)
        if has_fvg:
            confidence += 25
            explanation_parts.append("FVG detected (+25)")
        
        # Wickless candles component (0-20 points)
        wickless_score = min(20, wickless_count * 5)
        confidence += wickless_score
        if wickless_count > 0:
            explanation_parts.append(f"Wickless candles: {wickless_count} (+{wickless_score})")
        
        # Volume spike component (0-15 points)
        if volume_spike >= self.volume_spike_threshold:
            volume_score = min(15, int((volume_spike / self.volume_spike_threshold) * 10))
            confidence += volume_score
            explanation_parts.append(f"Volume spike: {volume_spike:.2f}x (+{volume_score})")
        
        explanation = " | ".join(explanation_parts)
        return min(100, confidence), explanation
    
    def detect_whale_blocks(
        self,
        df: pd.DataFrame,
        timeframe: str = "4h"
    ) -> List[WhaleOrderBlock]:
        """
        Main method: Detect all whale order blocks in DataFrame
        
        Returns: List of WhaleOrderBlock objects
        """
        whale_blocks = []
        
        try:
            for idx in range(self.lookback_period, len(df)):
                # Step 1: Check for displacement
                is_displacement, displacement_pct = self.detect_displacement(df, idx)
                
                if not is_displacement:
                    continue
                
                # Step 2: Check for FVG
                has_fvg, fvg_data = self.detect_fvg(df, idx)
                
                # Step 3: Detect wickless candles
                direction = 'bullish' if df.iloc[idx]['close'] > df.iloc[idx]['open'] else 'bearish'
                wickless_count = self.detect_wickless_candles(df, idx, direction)
                
                # Step 4: Check volume spike
                volume_spike = self.detect_volume_spike(df, idx)
                
                # Step 5: Calculate confidence
                confidence, explanation = self.calculate_confidence(
                    displacement_pct,
                    has_fvg,
                    wickless_count,
                    volume_spike
                )
                
                # Only keep high-confidence blocks (>= 50)
                if confidence >= 50:
                    candle = df.iloc[idx]
                    zone_type = 'buy' if direction == 'bullish' else 'sell'
                    
                    # Define zone boundaries
                    if zone_type == 'buy':
                        zone_high = candle['high']
                        zone_low = candle['low']
                        price_level = zone_low
                    else:
                        zone_high = candle['high']
                        zone_low = candle['low']
                        price_level = zone_high
                    
                    whale_block = WhaleOrderBlock(
                        price_level=price_level,
                        zone_high=zone_high,
                        zone_low=zone_low,
                        zone_type=zone_type,
                        confidence=confidence,
                        displacement_pct=displacement_pct,
                        has_fvg=has_fvg,
                        wickless_candles=wickless_count,
                        volume_spike=volume_spike,
                        timeframe=timeframe,
                        identified_at=datetime.now(),
                        still_valid=True,
                        explanation=explanation
                    )
                    
                    whale_blocks.append(whale_block)
                    logger.info(f"🐋 Whale Block detected: {zone_type.upper()} @ {price_level:.2f} (confidence: {confidence}%)")
            
            return whale_blocks
            
        except Exception as e:
            logger.error(f"Whale detection error: {e}")
            return []
    
    def validate_whale_block(
        self,
        whale_block: WhaleOrderBlock,
        current_price: float
    ) -> bool:
        """
        Check if whale block is still valid (not breached)
        
        Rules:
        - Buy block: Invalid if price closes below zone_low
        - Sell block: Invalid if price closes above zone_high
        """
        try:
            if whale_block.zone_type == 'buy':
                # Buy block invalidated if price breaks below
                if current_price < whale_block.zone_low:
                    whale_block.still_valid = False
                    return False
            
            elif whale_block.zone_type == 'sell':
                # Sell block invalidated if price breaks above
                if current_price > whale_block.zone_high:
                    whale_block.still_valid = False
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return False


# Example usage
if __name__ == "__main__":
    # Test with sample data
    sample_data = {
        'open': [100, 101, 102, 105, 106],
        'high': [101, 102, 107, 107, 108],
        'low': [99, 100, 102, 104, 105],
        'close': [100.5, 101.5, 106, 106.5, 107],
        'volume': [1000, 1100, 5000, 1200, 1000]
    }
    
    df = pd.DataFrame(sample_data)
    
    detector = WhaleDetector()
    whale_blocks = detector.detect_whale_blocks(df, timeframe="1h")
    
    print(f"\n🐋 Detected {len(whale_blocks)} whale order blocks")
    for block in whale_blocks:
        print(f"\n{block.zone_type.upper()} Block @ {block.price_level:.2f}")
        print(f"Confidence: {block.confidence}%")
        print(f"Explanation: {block.explanation}")
