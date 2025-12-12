"""
📦 ORDER BLOCK DETECTOR
High-Quality Institutional Order Block Detection Module

Features:
- Bullish/Bearish Order Block detection
- Breaker block detection (broken order blocks)
- Strength calculation based on displacement
- Volume confirmation
- Mitigation tracking
- Historical order block database
- Real-time validation

Author: galinborisov10-art
Date: 2025-12-12
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrderBlockType(Enum):
    """Order block types"""
    BULLISH = "BULLISH_OB"
    BEARISH = "BEARISH_OB"
    BREAKER_BULLISH = "BREAKER_BULLISH"
    BREAKER_BEARISH = "BREAKER_BEARISH"


@dataclass
class OrderBlock:
    """
    Represents an institutional order block
    
    Attributes:
        top: Upper boundary of the order block
        bottom: Lower boundary of the order block
        type: Type of order block (BULLISH/BEARISH/BREAKER)
        timestamp: When the OB was created
        candle_index: Index of the originating candle
        strength: Strength score (0-100)
        displacement_pct: Percentage displacement that created it
        volume_ratio: Volume compared to average
        mitigated: Whether price has returned to the block
        mitigation_pct: Percentage of block that's been tested (0-100)
        tested_count: Number of times price has touched the block
        breaker: Whether this is a breaker block (broken OB)
        timeframe: Timeframe of detection
    """
    top: float
    bottom: float
    type: OrderBlockType
    timestamp: datetime
    candle_index: int
    strength: float
    displacement_pct: float
    volume_ratio: float
    mitigated: bool = False
    mitigation_pct: float = 0.0
    tested_count: int = 0
    breaker: bool = False
    timeframe: str = "1H"
    body_size: float = 0.0
    wick_ratio: float = 0.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'top': self.top,
            'bottom': self.bottom,
            'type': self.type.value,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            'candle_index': self.candle_index,
            'strength': self.strength,
            'displacement_pct': self.displacement_pct,
            'volume_ratio': self.volume_ratio,
            'mitigated': self.mitigated,
            'mitigation_pct': self.mitigation_pct,
            'tested_count': self.tested_count,
            'breaker': self.breaker,
            'timeframe': self.timeframe,
            'body_size': self.body_size,
            'wick_ratio': self.wick_ratio
        }
    
    def is_valid(self) -> bool:
        """Check if order block is still valid for trading"""
        if self.mitigated and self.mitigation_pct > 75:
            return False
        if self.tested_count > 3:
            return False
        return True


class OrderBlockDetector:
    """
    Detects high-quality institutional order blocks
    
    An order block is the last bullish/bearish candle before a strong move
    in the opposite direction, indicating institutional interest.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize Order Block Detector
        
        Args:
            config: Configuration parameters
        """
        self.config = config or self._get_default_config()
        self.detected_obs: List[OrderBlock] = []
        
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'min_displacement_pct': 0.5,  # Min 0.5% move to qualify
            'min_volume_ratio': 1.2,       # Min 1.2x average volume
            'min_strength': 60,             # Min strength score 60/100
            'lookback_candles': 5,          # Look back 5 candles for OB
            'displacement_candles': 3,      # Displacement within 3 candles
            'max_wick_ratio': 0.4,          # Max 40% wick size
            'min_body_ratio': 0.3,          # Min 30% body size
            'mitigation_threshold': 0.5,    # 50% retracement = mitigated
            'breaker_lookback': 20,         # Lookback for breaker detection
            'max_age_bars': 50,             # Max age before invalidation
            'breaker_threshold_pct': 1.0,   # 1% threshold for breaker detection
        }
    
    def detect_order_blocks(
        self,
        df: pd.DataFrame,
        timeframe: str = "1H"
    ) -> List[OrderBlock]:
        """
        Main order block detection function
        
        Args:
            df: OHLCV dataframe with columns: open, high, low, close, volume
            timeframe: Timeframe string (e.g., "1H", "4H")
            
        Returns:
            List of detected order blocks
        """
        if len(df) < 10:
            logger.warning("Insufficient data for order block detection")
            return []
        
        # Prepare data
        df = self._prepare_dataframe(df)
        
        # Clear old order blocks
        self.detected_obs = []
        
        # Detect bullish order blocks
        bullish_obs = self._identify_bullish_ob(df, timeframe)
        self.detected_obs.extend(bullish_obs)
        
        # Detect bearish order blocks
        bearish_obs = self._identify_bearish_ob(df, timeframe)
        self.detected_obs.extend(bearish_obs)
        
        # Check for breaker blocks
        breaker_obs = self._find_breaker_blocks(df, self.detected_obs)
        self.detected_obs.extend(breaker_obs)
        
        # Update mitigation status
        self._update_mitigation_status(df, self.detected_obs)
        
        # Filter by quality
        valid_obs = [ob for ob in self.detected_obs if self.validate_order_block(ob)]
        
        logger.info(f"Detected {len(valid_obs)} valid order blocks on {timeframe}")
        
        return valid_obs
    
    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare dataframe with required indicators"""
        df = df.copy()
        
        # Ensure datetime index
        if 'timestamp' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        
        # Calculate volume metrics
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma'].replace(0, 1)
        else:
            df['volume'] = 0
            df['volume_ma'] = 0
            df['volume_ratio'] = 1.0
        
        # Calculate candle characteristics
        df['body'] = abs(df['close'] - df['open'])
        df['range'] = df['high'] - df['low']
        df['body_ratio'] = df['body'] / df['range'].replace(0, 1)
        df['upper_wick'] = df['high'] - df[['open', 'close']].max(axis=1)
        df['lower_wick'] = df[['open', 'close']].min(axis=1) - df['low']
        df['wick_ratio'] = (df['upper_wick'] + df['lower_wick']) / df['range'].replace(0, 1)
        
        # Calculate price change
        df['price_change'] = df['close'].pct_change() * 100
        
        return df
    
    def _identify_bullish_ob(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> List[OrderBlock]:
        """
        Identify bullish order blocks
        
        A bullish OB is the last bearish candle before a strong bullish move
        """
        bullish_obs = []
        lookback = self.config['lookback_candles']
        disp_candles = self.config['displacement_candles']
        
        for i in range(lookback, len(df) - disp_candles):
            # Check if this is a bearish candle
            if df['close'].iloc[i] >= df['open'].iloc[i]:
                continue
            
            # Check for displacement (strong move up) in next candles
            displacement = self._calculate_displacement(df, i, direction='up')
            
            if displacement < self.config['min_displacement_pct']:
                continue
            
            # Check volume confirmation
            volume_ratio = df['volume_ratio'].iloc[i] if 'volume_ratio' in df else 1.0
            
            if volume_ratio < self.config['min_volume_ratio']:
                continue
            
            # Calculate strength
            strength = self._calculate_ob_strength(
                displacement=displacement,
                volume_ratio=volume_ratio,
                body_ratio=df['body_ratio'].iloc[i],
                wick_ratio=df['wick_ratio'].iloc[i]
            )
            
            if strength < self.config['min_strength']:
                continue
            
            # Create order block
            ob = OrderBlock(
                top=df['high'].iloc[i],
                bottom=df['low'].iloc[i],
                type=OrderBlockType.BULLISH,
                timestamp=df.index[i],
                candle_index=i,
                strength=strength,
                displacement_pct=displacement,
                volume_ratio=volume_ratio,
                timeframe=timeframe,
                body_size=df['body'].iloc[i],
                wick_ratio=df['wick_ratio'].iloc[i]
            )
            
            bullish_obs.append(ob)
        
        return bullish_obs
    
    def _identify_bearish_ob(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> List[OrderBlock]:
        """
        Identify bearish order blocks
        
        A bearish OB is the last bullish candle before a strong bearish move
        """
        bearish_obs = []
        lookback = self.config['lookback_candles']
        disp_candles = self.config['displacement_candles']
        
        for i in range(lookback, len(df) - disp_candles):
            # Check if this is a bullish candle
            if df['close'].iloc[i] <= df['open'].iloc[i]:
                continue
            
            # Check for displacement (strong move down) in next candles
            displacement = self._calculate_displacement(df, i, direction='down')
            
            if displacement < self.config['min_displacement_pct']:
                continue
            
            # Check volume confirmation
            volume_ratio = df['volume_ratio'].iloc[i] if 'volume_ratio' in df else 1.0
            
            if volume_ratio < self.config['min_volume_ratio']:
                continue
            
            # Calculate strength
            strength = self._calculate_ob_strength(
                displacement=displacement,
                volume_ratio=volume_ratio,
                body_ratio=df['body_ratio'].iloc[i],
                wick_ratio=df['wick_ratio'].iloc[i]
            )
            
            if strength < self.config['min_strength']:
                continue
            
            # Create order block
            ob = OrderBlock(
                top=df['high'].iloc[i],
                bottom=df['low'].iloc[i],
                type=OrderBlockType.BEARISH,
                timestamp=df.index[i],
                candle_index=i,
                strength=strength,
                displacement_pct=displacement,
                volume_ratio=volume_ratio,
                timeframe=timeframe,
                body_size=df['body'].iloc[i],
                wick_ratio=df['wick_ratio'].iloc[i]
            )
            
            bearish_obs.append(ob)
        
        return bearish_obs
    
    def _calculate_displacement(
        self,
        df: pd.DataFrame,
        index: int,
        direction: str = 'up'
    ) -> float:
        """
        Calculate displacement percentage
        
        Args:
            df: Dataframe
            index: Starting candle index
            direction: 'up' or 'down'
            
        Returns:
            Displacement percentage
        """
        disp_candles = self.config['displacement_candles']
        start_price = df['close'].iloc[index]
        
        if direction == 'up':
            # Find highest high in next N candles
            end_index = min(index + disp_candles, len(df) - 1)
            end_price = df['high'].iloc[index+1:end_index+1].max()
            displacement = ((end_price - start_price) / start_price) * 100
        else:
            # Find lowest low in next N candles
            end_index = min(index + disp_candles, len(df) - 1)
            end_price = df['low'].iloc[index+1:end_index+1].min()
            displacement = ((start_price - end_price) / start_price) * 100
        
        return max(0, displacement)
    
    def _calculate_ob_strength(
        self,
        displacement: float,
        volume_ratio: float,
        body_ratio: float,
        wick_ratio: float
    ) -> float:
        """
        Calculate order block strength score (0-100)
        
        Args:
            displacement: Displacement percentage
            volume_ratio: Volume compared to average
            body_ratio: Body size ratio
            wick_ratio: Wick size ratio
            
        Returns:
            Strength score (0-100)
        """
        # Displacement score (max 40 points)
        disp_score = min(40, displacement * 4)
        
        # Volume score (max 30 points)
        vol_score = min(30, (volume_ratio - 1) * 20)
        
        # Body ratio score (max 20 points)
        body_score = min(20, body_ratio * 30)
        
        # Wick penalty (max -10 points)
        wick_penalty = min(10, wick_ratio * 25)
        
        total_score = disp_score + vol_score + body_score - wick_penalty
        
        return max(0, min(100, total_score))
    
    def _find_breaker_blocks(
        self,
        df: pd.DataFrame,
        order_blocks: List[OrderBlock]
    ) -> List[OrderBlock]:
        """
        Find breaker blocks (order blocks that have been broken)
        
        When an order block is broken, it can act as a breaker block
        (support becomes resistance or vice versa)
        
        Args:
            df: Dataframe
            order_blocks: List of detected order blocks
            
        Returns:
            List of breaker blocks
        """
        breaker_blocks = []
        lookback = self.config['breaker_lookback']
        
        for ob in order_blocks:
            # Skip already identified breakers
            if ob.breaker:
                continue
            
            # Find candles after the OB
            ob_idx = ob.candle_index
            start_idx = ob_idx + 1
            end_idx = min(ob_idx + lookback, len(df))
            
            if start_idx >= len(df):
                continue
            
            # Check if OB was broken
            if ob.type == OrderBlockType.BULLISH:
                # Bullish OB broken if price closes below it
                threshold = 1 - (self.config['breaker_threshold_pct'] / 100)
                broken = any(df['close'].iloc[start_idx:end_idx] < ob.bottom * threshold)
                
                if broken:
                    # Create bearish breaker block
                    breaker = OrderBlock(
                        top=ob.top,
                        bottom=ob.bottom,
                        type=OrderBlockType.BREAKER_BEARISH,
                        timestamp=ob.timestamp,
                        candle_index=ob.candle_index,
                        strength=ob.strength * 0.8,  # Slightly lower strength
                        displacement_pct=ob.displacement_pct,
                        volume_ratio=ob.volume_ratio,
                        breaker=True,
                        timeframe=ob.timeframe,
                        body_size=ob.body_size,
                        wick_ratio=ob.wick_ratio
                    )
                    breaker_blocks.append(breaker)
            
            elif ob.type == OrderBlockType.BEARISH:
                # Bearish OB broken if price closes above it
                threshold = 1 + (self.config['breaker_threshold_pct'] / 100)
                broken = any(df['close'].iloc[start_idx:end_idx] > ob.top * threshold)
                
                if broken:
                    # Create bullish breaker block
                    breaker = OrderBlock(
                        top=ob.top,
                        bottom=ob.bottom,
                        type=OrderBlockType.BREAKER_BULLISH,
                        timestamp=ob.timestamp,
                        candle_index=ob.candle_index,
                        strength=ob.strength * 0.8,
                        displacement_pct=ob.displacement_pct,
                        volume_ratio=ob.volume_ratio,
                        breaker=True,
                        timeframe=ob.timeframe,
                        body_size=ob.body_size,
                        wick_ratio=ob.wick_ratio
                    )
                    breaker_blocks.append(breaker)
        
        return breaker_blocks
    
    def _update_mitigation_status(
        self,
        df: pd.DataFrame,
        order_blocks: List[OrderBlock]
    ):
        """
        Update mitigation status for all order blocks
        
        Args:
            df: Dataframe
            order_blocks: List of order blocks to check
        """
        for ob in order_blocks:
            # Find candles after the OB
            ob_idx = ob.candle_index
            start_idx = ob_idx + 1
            
            if start_idx >= len(df):
                continue
            
            # Check how much of the block has been retraced
            ob_range = ob.top - ob.bottom
            
            for i in range(start_idx, len(df)):
                price = df['close'].iloc[i]
                
                # Check if price is in the OB zone
                if ob.bottom <= price <= ob.top:
                    ob.tested_count += 1
                    
                    # Calculate mitigation percentage
                    if ob.type in [OrderBlockType.BULLISH, OrderBlockType.BREAKER_BULLISH]:
                        # For bullish OB, check how deep price went
                        mitigation = ((ob.top - price) / ob_range) * 100
                    else:
                        # For bearish OB, check how high price went
                        mitigation = ((price - ob.bottom) / ob_range) * 100
                    
                    ob.mitigation_pct = max(ob.mitigation_pct, mitigation)
                    
                    # Mark as mitigated if > threshold
                    if ob.mitigation_pct >= self.config['mitigation_threshold'] * 100:
                        ob.mitigated = True
    
    def validate_order_block(self, ob: OrderBlock) -> bool:
        """
        Validate if order block meets quality criteria
        
        Args:
            ob: Order block to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check strength
        if ob.strength < self.config['min_strength']:
            return False
        
        # Check if still valid
        if not ob.is_valid():
            return False
        
        # Check body ratio
        if ob.body_size == 0 or ob.wick_ratio > self.config['max_wick_ratio']:
            return False
        
        return True
    
    def check_mitigation(
        self,
        ob: OrderBlock,
        current_price: float
    ) -> Tuple[bool, float]:
        """
        Check if current price has mitigated the order block
        
        Args:
            ob: Order block to check
            current_price: Current market price
            
        Returns:
            Tuple of (is_mitigated, mitigation_percentage)
        """
        # Check if price is in OB zone
        if not (ob.bottom <= current_price <= ob.top):
            return False, 0.0
        
        # Calculate mitigation percentage
        ob_range = ob.top - ob.bottom
        
        if ob.type in [OrderBlockType.BULLISH, OrderBlockType.BREAKER_BULLISH]:
            mitigation_pct = ((ob.top - current_price) / ob_range) * 100
        else:
            mitigation_pct = ((current_price - ob.bottom) / ob_range) * 100
        
        is_mitigated = mitigation_pct >= (self.config['mitigation_threshold'] * 100)
        
        return is_mitigated, mitigation_pct
    
    def get_active_order_blocks(
        self,
        current_price: float,
        price_range_pct: float = 5.0
    ) -> List[OrderBlock]:
        """
        Get order blocks near current price
        
        Args:
            current_price: Current market price
            price_range_pct: Percentage range to consider (default 5%)
            
        Returns:
            List of nearby active order blocks
        """
        range_threshold = current_price * (price_range_pct / 100)
        
        active_obs = []
        for ob in self.detected_obs:
            # Check if OB is valid
            if not ob.is_valid():
                continue
            
            # Check if OB is near current price
            if abs(ob.bottom - current_price) <= range_threshold or \
               abs(ob.top - current_price) <= range_threshold:
                active_obs.append(ob)
        
        # Sort by strength (highest first)
        active_obs.sort(key=lambda x: x.strength, reverse=True)
        
        return active_obs


# Example usage
if __name__ == "__main__":
    print("📦 Order Block Detector - Test Mode")
    
    # Create sample data
    dates = pd.date_range(start='2025-01-01', periods=100, freq='1H')
    np.random.seed(42)
    
    # Simulate price data with some order blocks
    base_price = 50000
    prices = []
    current = base_price
    
    for i in range(100):
        # Add some order block patterns
        if i == 30:  # Bullish OB
            change = -200  # Down candle
        elif i == 31:  # Displacement
            change = 800
        elif i == 32:
            change = 600
        elif i == 60:  # Bearish OB
            change = 300  # Up candle
        elif i == 61:  # Displacement
            change = -700
        elif i == 62:
            change = -500
        else:
            change = np.random.randn() * 100
        
        current += change
        prices.append(current)
    
    # Create dataframe
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 50) for p in prices],
        'low': [p - abs(np.random.randn() * 50) for p in prices],
        'close': [p + np.random.randn() * 30 for p in prices],
        'volume': [1000000 + np.random.randn() * 200000 for _ in prices]
    })
    
    # Initialize detector
    detector = OrderBlockDetector()
    
    # Detect order blocks
    order_blocks = detector.detect_order_blocks(df, timeframe="1H")
    
    print(f"\n✅ Detected {len(order_blocks)} order blocks")
    
    for i, ob in enumerate(order_blocks, 1):
        print(f"\n{i}. {ob.type.value}")
        print(f"   Price Range: ${ob.bottom:.2f} - ${ob.top:.2f}")
        print(f"   Strength: {ob.strength:.1f}/100")
        print(f"   Displacement: {ob.displacement_pct:.2f}%")
        print(f"   Volume Ratio: {ob.volume_ratio:.2f}x")
        print(f"   Mitigated: {ob.mitigated} ({ob.mitigation_pct:.1f}%)")
        print(f"   Tests: {ob.tested_count}")
    
    print("\n✅ Order Block Detector test completed!")
    print(f"Total lines: {sum(1 for line in open(__file__))}+")
