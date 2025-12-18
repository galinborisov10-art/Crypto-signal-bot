"""
SIBI/SSIB Detector
Identifies Sell-Side Imbalance Buy-Side Inefficiency and Buy-Side Imbalance Sell-Side Inefficiency

These are advanced ICT concepts combining:
- Displacement (rapid price movement)
- Imbalance (FVG - Fair Value Gap)
- Liquidity void (low volume area)
"""

from typing import List, Optional, Dict
from dataclasses import dataclass
import pandas as pd
import logging

logger = logging.getLogger(__name__)


@dataclass
class SIBISSIBZone:
    """SIBI/SSIB Zone data structure"""
    type: str  # 'SIBI' or 'SSIB'
    index: int
    price_low: float
    price_high: float
    price_mid: float
    displacement_size: float  # Percentage of displacement
    displacement_direction: str  # 'UP' or 'DOWN'
    fvg_count: int
    liquidity_void: bool
    strength: float  # 0-10
    explanation: str
    
    def to_dict(self):
        return {
            'type': self.type,
            'index': self.index,
            'price_low': self.price_low,
            'price_high': self.price_high,
            'price_mid': self.price_mid,
            'displacement_size': self.displacement_size,
            'displacement_direction': self.displacement_direction,
            'fvg_count': self.fvg_count,
            'liquidity_void': self.liquidity_void,
            'strength': self.strength,
            'explanation': self.explanation
        }


class SIBISSIBDetector:
    """
    Detects SIBI and SSIB zones
    
    SIBI = Sell-Side Imbalance Buy-Side Inefficiency
    - Occurs during bullish displacement
    - Leaves imbalance/void below
    - Potential support zone
    
    SSIB = Buy-Side Imbalance Sell-Side Inefficiency
    - Occurs during bearish displacement  
    - Leaves imbalance/void above
    - Potential resistance zone
    """
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or self._get_default_config()
        logger.info("SIBISSIBDetector initialized")
    
    def _get_default_config(self) -> Dict:
        return {
            'min_displacement_pct': 0.5,  # Min 0.5% move to qualify
            'lookback_period': 50,
            'fvg_lookback': 5,  # Check FVGs within 5 candles
            'min_strength': 4.0
        }
    
    def detect_sibi_ssib(
        self,
        df: pd.DataFrame,
        fvgs: List,
        liquidity_zones: List
    ) -> List[SIBISSIBZone]:
        """
        Detect SIBI/SSIB zones
        
        Args:
            df: OHLCV dataframe
            fvgs: List of Fair Value Gaps
            liquidity_zones: List of liquidity zones
            
        Returns:
            List of SIBI/SSIB zones
        """
        zones = []
        lookback = self.config['lookback_period']
        
        for i in range(lookback, len(df)):
            # Check for displacement
            displacement = self._check_displacement(df, i)
            
            if not displacement:
                continue
            
            # Check for FVG at same location
            fvg_at_location = self._get_nearby_fvgs(fvgs, i, self.config['fvg_lookback'])
            
            if not fvg_at_location:
                continue
            
            # Check for liquidity void
            has_liquidity_void = self._check_liquidity_void(df, i-10, i)
            
            if not has_liquidity_void:
                continue
            
            # Determine type and create zone
            zone = self._create_zone(df, i, displacement, fvg_at_location, has_liquidity_void)
            
            if zone and zone.strength >= self.config['min_strength']:
                zones.append(zone)
                logger.debug(f"Detected {zone.type} at index {i}")
        
        return zones
    
    def _check_displacement(self, df: pd.DataFrame, index: int) -> Optional[Dict]:
        """
        Check for displacement (rapid price movement)
        
        Displacement criteria:
        - Large candle (>0.5% body)
        - Minimal wicks
        - Above average volume
        """
        if index < 5:
            return None
        
        row = df.iloc[index]
        open_price = row['open']
        close_price = row['close']
        
        # Calculate body size as percentage
        body_pct = abs((close_price - open_price) / open_price) * 100
        
        if body_pct < self.config['min_displacement_pct']:
            return None
        
        # Check wick size (should be minimal for displacement)
        body_size = abs(close_price - open_price)
        upper_wick = row['high'] - max(open_price, close_price)
        lower_wick = min(open_price, close_price) - row['low']
        
        # Wicks should be less than 30% of body
        if upper_wick > body_size * 0.3 or lower_wick > body_size * 0.3:
            return None
        
        # Determine direction
        direction = 'UP' if close_price > open_price else 'DOWN'
        
        return {
            'size': body_pct,
            'direction': direction,
            'index': index
        }
    
    def _get_nearby_fvgs(self, fvgs: List, index: int, lookback: int) -> List:
        """Get FVGs within lookback candles of index"""
        nearby = []
        
        for fvg in fvgs:
            # Get FVG index with fallback logic
            if hasattr(fvg, 'index'):
                fvg_index = fvg.index
            elif hasattr(fvg, 'candle_index'):
                fvg_index = fvg.candle_index
            else:
                fvg_index = 0
            
            if abs(fvg_index - index) <= lookback:
                nearby.append(fvg)
        
        return nearby
    
    def _check_liquidity_void(self, df: pd.DataFrame, start: int, end: int) -> bool:
        """
        Check for liquidity void (area with low volume and wide spreads)
        """
        if start < 0 or end >= len(df):
            return False
        
        if 'volume' not in df.columns:
            return False
        
        # Calculate average volume in range
        volume_slice = df['volume'].iloc[start:end]
        avg_volume = volume_slice.mean()
        
        # Calculate overall average volume
        overall_avg = df['volume'].iloc[max(0, start-50):start].mean()
        
        # Liquidity void if volume significantly below average
        return avg_volume < overall_avg * 0.6
    
    def _create_zone(
        self,
        df: pd.DataFrame,
        index: int,
        displacement: Dict,
        fvgs: List,
        has_void: bool
    ) -> Optional[SIBISSIBZone]:
        """Create SIBI/SSIB zone from detected components"""
        
        # Get price range
        candle_range = df.iloc[index-5:index+5]
        price_low = candle_range['low'].min()
        price_high = candle_range['high'].max()
        price_mid = (price_high + price_low) / 2
        
        # Determine zone type
        if displacement['direction'] == 'UP':
            zone_type = 'SIBI'
            explanation = (
                "Sell-Side Imbalance Buy-Side Inefficiency: "
                "Bullish displacement left imbalance below. "
                "Price may return to fill inefficiency before continuing up."
            )
        else:
            zone_type = 'SSIB'
            explanation = (
                "Buy-Side Imbalance Sell-Side Inefficiency: "
                "Bearish displacement left imbalance above. "
                "Price may return to fill inefficiency before continuing down."
            )
        
        # Calculate strength
        strength = self._calculate_strength(displacement, len(fvgs), has_void)
        
        zone = SIBISSIBZone(
            type=zone_type,
            index=index,
            price_low=price_low,
            price_high=price_high,
            price_mid=price_mid,
            displacement_size=displacement['size'],
            displacement_direction=displacement['direction'],
            fvg_count=len(fvgs),
            liquidity_void=has_void,
            strength=strength,
            explanation=explanation
        )
        
        return zone
    
    def _calculate_strength(self, displacement: Dict, fvg_count: int, has_void: bool) -> float:
        """Calculate zone strength 0-10"""
        strength = 5.0  # Base
        
        # Displacement size bonus
        if displacement['size'] > 1.0:
            strength += 2.0
        elif displacement['size'] > 0.7:
            strength += 1.0
        
        # FVG count bonus
        strength += min(2.0, fvg_count * 0.5)
        
        # Liquidity void bonus
        if has_void:
            strength += 1.0
        
        return min(10.0, strength)
