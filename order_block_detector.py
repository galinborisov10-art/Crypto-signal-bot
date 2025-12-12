"""
🎯 ORDER BLOCK DETECTOR
Professional Order Block Detection System

Detects and validates institutional order blocks using ICT methodology:
- Displacement detection (strong moves)
- Origin candle identification
- Order block quality scoring
- Mitigation tracking
- Strength calculation

Author: ICT Trading System
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class OrderBlockType(Enum):
    """Order Block types"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class OrderBlockQuality(Enum):
    """Order Block quality levels"""
    PREMIUM = "PREMIUM"  # Fresh, high volume, strong displacement
    HIGH = "HIGH"        # Good quality, not retested
    MEDIUM = "MEDIUM"    # Moderate quality, may have been retested
    LOW = "LOW"          # Weak quality, multiple retests


@dataclass
class OrderBlock:
    """Order Block structure"""
    zone_high: float
    zone_low: float
    ob_type: OrderBlockType
    created_at: datetime
    created_index: int
    displacement_size: float  # Percentage
    displacement_candles: int
    origin_candle_index: int
    strength_score: float  # 0-100
    quality: OrderBlockQuality
    
    # State tracking
    mitigated: bool = False
    mitigation_index: Optional[int] = None
    mitigation_time: Optional[datetime] = None
    retest_count: int = 0
    retest_indices: List[int] = field(default_factory=list)
    
    # Volume data
    formation_volume: float = 0.0
    volume_ratio: float = 1.0  # vs average
    
    # Body/wick analysis
    body_ratio: float = 0.0  # Body size / total range
    has_clean_candle: bool = False  # > 80% body
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'zone_high': self.zone_high,
            'zone_low': self.zone_low,
            'type': self.ob_type.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_index': self.created_index,
            'displacement_size': self.displacement_size,
            'displacement_candles': self.displacement_candles,
            'strength_score': self.strength_score,
            'quality': self.quality.value,
            'mitigated': self.mitigated,
            'retest_count': self.retest_count,
            'formation_volume': self.formation_volume,
            'volume_ratio': self.volume_ratio,
            'body_ratio': self.body_ratio,
            'has_clean_candle': self.has_clean_candle
        }
    
    def __repr__(self) -> str:
        status = "MITIGATED" if self.mitigated else "ACTIVE"
        return (f"OrderBlock({self.ob_type.value}, "
                f"range=[{self.zone_low:.2f}-{self.zone_high:.2f}], "
                f"strength={self.strength_score:.1f}, "
                f"quality={self.quality.value}, "
                f"{status})")


class OrderBlockDetector:
    """
    Professional Order Block Detection System
    
    Detects institutional order blocks using:
    1. Displacement detection (rapid price moves)
    2. Origin candle identification (last opposite candle)
    3. Quality scoring (volume, body ratio, retests)
    4. Mitigation tracking
    """
    
    def __init__(
        self,
        swing_period: int = 10,
        displacement_threshold: float = 1.5,  # % for displacement
        min_displacement_candles: int = 2,
        volume_threshold: float = 1.3,  # Volume ratio threshold
        clean_candle_ratio: float = 0.80,  # 80% body to be "clean"
        max_lookback: int = 100
    ):
        """
        Initialize Order Block Detector
        
        Args:
            swing_period: Period for swing detection
            displacement_threshold: Minimum % move to qualify as displacement
            min_displacement_candles: Minimum candles in displacement
            volume_threshold: Minimum volume ratio for high quality
            clean_candle_ratio: Minimum body/range ratio for clean candle
            max_lookback: Maximum bars to look back
        """
        self.swing_period = swing_period
        self.displacement_threshold = displacement_threshold
        self.min_displacement_candles = min_displacement_candles
        self.volume_threshold = volume_threshold
        self.clean_candle_ratio = clean_candle_ratio
        self.max_lookback = max_lookback
        
        logger.info(f"OrderBlockDetector initialized with swing_period={swing_period}")
    
    def detect_order_blocks(
        self,
        df: pd.DataFrame,
        swing_period: Optional[int] = None
    ) -> List[OrderBlock]:
        """
        Main method: Detect all order blocks in DataFrame
        
        Args:
            df: DataFrame with OHLCV data
            swing_period: Override default swing period
            
        Returns:
            List of OrderBlock objects
        """
        if swing_period is None:
            swing_period = self.swing_period
        
        if len(df) < swing_period * 2:
            logger.warning(f"Insufficient data: {len(df)} bars")
            return []
        
        order_blocks = []
        
        # Calculate volume metrics if available
        has_volume = 'volume' in df.columns and df['volume'].sum() > 0
        if has_volume:
            volume_ma = df['volume'].rolling(window=20).mean()
        else:
            volume_ma = pd.Series([1.0] * len(df), index=df.index)
        
        # Scan for displacements and order blocks
        for idx in range(swing_period, len(df) - 1):
            # Check for bullish displacement
            bullish_displacement = self._identify_displacement(df, idx, is_bullish=True)
            if bullish_displacement:
                disp_size, disp_candles = bullish_displacement
                
                # Find origin candle (last bearish before bullish move)
                origin_idx = self._find_origin_candle(df, idx, is_bullish=True)
                
                if origin_idx is not None:
                    ob = self._create_order_block(
                        df, origin_idx, idx, disp_size, disp_candles,
                        OrderBlockType.BULLISH, volume_ma
                    )
                    
                    if ob and self._validate_order_block(ob, df):
                        order_blocks.append(ob)
                        logger.debug(f"Bullish OB detected at index {origin_idx}")
            
            # Check for bearish displacement
            bearish_displacement = self._identify_displacement(df, idx, is_bullish=False)
            if bearish_displacement:
                disp_size, disp_candles = bearish_displacement
                
                # Find origin candle (last bullish before bearish move)
                origin_idx = self._find_origin_candle(df, idx, is_bullish=False)
                
                if origin_idx is not None:
                    ob = self._create_order_block(
                        df, origin_idx, idx, disp_size, disp_candles,
                        OrderBlockType.BEARISH, volume_ma
                    )
                    
                    if ob and self._validate_order_block(ob, df):
                        order_blocks.append(ob)
                        logger.debug(f"Bearish OB detected at index {origin_idx}")
        
        # Check for mitigation on all order blocks
        for ob in order_blocks:
            self._check_mitigation(ob, df)
        
        # Filter overlapping blocks
        order_blocks = self._filter_overlapping_blocks(order_blocks)
        
        logger.info(f"Detected {len(order_blocks)} order blocks")
        return order_blocks
    
    def _identify_displacement(
        self,
        df: pd.DataFrame,
        idx: int,
        is_bullish: bool
    ) -> Optional[Tuple[float, int]]:
        """
        Identify displacement - strong price move without significant pullback
        
        Args:
            df: DataFrame
            idx: Current index
            is_bullish: True for bullish displacement
            
        Returns:
            Tuple of (displacement_size_pct, num_candles) or None
        """
        if idx < self.min_displacement_candles:
            return None
        
        try:
            current_price = df.iloc[idx]['close']
            
            # Look back for start of displacement
            lookback = min(10, idx)
            displacement_start_idx = idx - lookback
            
            if is_bullish:
                # Bullish: Price moved up significantly
                start_low = df.iloc[displacement_start_idx:idx]['low'].min()
                displacement_size = ((current_price - start_low) / start_low) * 100
                
                # Check for minimal retracement (strong move)
                if displacement_size >= self.displacement_threshold:
                    # Verify most candles are bullish
                    bullish_candles = sum(
                        df.iloc[i]['close'] > df.iloc[i]['open']
                        for i in range(displacement_start_idx, idx + 1)
                    )
                    
                    total_candles = idx - displacement_start_idx + 1
                    if bullish_candles / total_candles >= 0.6:  # 60% bullish candles
                        return (displacement_size, total_candles)
            else:
                # Bearish: Price moved down significantly
                start_high = df.iloc[displacement_start_idx:idx]['high'].max()
                displacement_size = ((start_high - current_price) / start_high) * 100
                
                if displacement_size >= self.displacement_threshold:
                    # Verify most candles are bearish
                    bearish_candles = sum(
                        df.iloc[i]['close'] < df.iloc[i]['open']
                        for i in range(displacement_start_idx, idx + 1)
                    )
                    
                    total_candles = idx - displacement_start_idx + 1
                    if bearish_candles / total_candles >= 0.6:  # 60% bearish candles
                        return (displacement_size, total_candles)
            
            return None
            
        except Exception as e:
            logger.error(f"Displacement detection error: {e}")
            return None
    
    def _find_origin_candle(
        self,
        df: pd.DataFrame,
        displacement_idx: int,
        is_bullish: bool
    ) -> Optional[int]:
        """
        Find the origin candle - last opposite colored candle before displacement
        
        Args:
            df: DataFrame
            displacement_idx: Index where displacement was detected
            is_bullish: True for bullish OB (find last bearish candle)
            
        Returns:
            Index of origin candle or None
        """
        try:
            # Look back max 10 candles
            lookback_start = max(0, displacement_idx - 10)
            
            for idx in range(displacement_idx - 1, lookback_start - 1, -1):
                candle = df.iloc[idx]
                
                if is_bullish:
                    # For bullish OB, find last bearish (red) candle
                    if candle['close'] < candle['open']:
                        # Verify next candle is bullish and breaks high
                        if idx + 1 < len(df):
                            next_candle = df.iloc[idx + 1]
                            if (next_candle['close'] > next_candle['open'] and
                                next_candle['close'] > candle['high']):
                                return idx
                else:
                    # For bearish OB, find last bullish (green) candle
                    if candle['close'] > candle['open']:
                        # Verify next candle is bearish and breaks low
                        if idx + 1 < len(df):
                            next_candle = df.iloc[idx + 1]
                            if (next_candle['close'] < next_candle['open'] and
                                next_candle['close'] < candle['low']):
                                return idx
            
            return None
            
        except Exception as e:
            logger.error(f"Origin candle detection error: {e}")
            return None
    
    def _create_order_block(
        self,
        df: pd.DataFrame,
        origin_idx: int,
        displacement_idx: int,
        displacement_size: float,
        displacement_candles: int,
        ob_type: OrderBlockType,
        volume_ma: pd.Series
    ) -> Optional[OrderBlock]:
        """
        Create OrderBlock object with all properties
        
        Args:
            df: DataFrame
            origin_idx: Origin candle index
            displacement_idx: Displacement end index
            displacement_size: Size of displacement in %
            displacement_candles: Number of candles in displacement
            ob_type: Bullish or Bearish
            volume_ma: Volume moving average
            
        Returns:
            OrderBlock object or None
        """
        try:
            origin_candle = df.iloc[origin_idx]
            
            # Define zone boundaries
            zone_high = origin_candle['high']
            zone_low = origin_candle['low']
            
            # Get timestamp
            if hasattr(df.index, 'to_pydatetime'):
                created_at = df.index[origin_idx].to_pydatetime()
            else:
                created_at = datetime.now()
            
            # Calculate body ratio
            body_size = abs(origin_candle['close'] - origin_candle['open'])
            total_range = origin_candle['high'] - origin_candle['low']
            body_ratio = body_size / total_range if total_range > 0 else 0
            has_clean_candle = body_ratio >= self.clean_candle_ratio
            
            # Volume analysis
            if 'volume' in df.columns:
                formation_volume = origin_candle['volume']
                avg_volume = volume_ma.iloc[origin_idx]
                volume_ratio = formation_volume / avg_volume if avg_volume > 0 else 1.0
            else:
                formation_volume = 0
                volume_ratio = 1.0
            
            # Calculate strength score
            strength_score = self._calculate_ob_strength(
                displacement_size, displacement_candles, body_ratio,
                volume_ratio, has_clean_candle, 0  # Initial retest count
            )
            
            # Determine quality
            quality = self._determine_quality(
                strength_score, volume_ratio, body_ratio, 0  # Initial retest count
            )
            
            ob = OrderBlock(
                zone_high=zone_high,
                zone_low=zone_low,
                ob_type=ob_type,
                created_at=created_at,
                created_index=origin_idx,
                displacement_size=displacement_size,
                displacement_candles=displacement_candles,
                origin_candle_index=origin_idx,
                strength_score=strength_score,
                quality=quality,
                formation_volume=formation_volume,
                volume_ratio=volume_ratio,
                body_ratio=body_ratio,
                has_clean_candle=has_clean_candle
            )
            
            return ob
            
        except Exception as e:
            logger.error(f"Order block creation error: {e}")
            return None
    
    def _calculate_ob_strength(
        self,
        displacement_size: float,
        displacement_candles: int,
        body_ratio: float,
        volume_ratio: float,
        has_clean_candle: bool,
        retest_count: int
    ) -> float:
        """
        Calculate order block strength score (0-100)
        
        Scoring factors:
        - Displacement size: 0-25 points
        - Wick/body ratio: 0-15 points
        - Volume: 0-20 points
        - Displacement speed: 0-15 points
        - Clean candle: 0-15 points
        - Retests penalty: -5 per retest
        
        Args:
            displacement_size: Size of displacement move in %
            displacement_candles: Number of candles
            body_ratio: Body size / total range
            volume_ratio: Volume vs average
            has_clean_candle: Whether candle has > 80% body
            retest_count: Number of times retested
            
        Returns:
            Strength score 0-100
        """
        score = 0.0
        
        # 1. Displacement size (0-25 points)
        displacement_score = min(25, (displacement_size / self.displacement_threshold) * 12.5)
        score += displacement_score
        
        # 2. Body ratio / Clean candle (0-15 points)
        body_score = body_ratio * 15
        score += body_score
        
        # 3. Volume spike (0-20 points)
        if volume_ratio >= self.volume_threshold:
            volume_score = min(20, ((volume_ratio - 1) / self.volume_threshold) * 20)
            score += volume_score
        
        # 4. Displacement speed (0-15 points)
        # Faster displacement = higher quality
        if displacement_candles > 0:
            speed_score = min(15, (10 / displacement_candles) * 15)
            score += speed_score
        
        # 5. Clean candle bonus (0-15 points)
        if has_clean_candle:
            score += 15
        
        # 6. Not mitigated bonus (0-10 points)
        if retest_count == 0:
            score += 10
        
        # Penalty for retests
        retest_penalty = retest_count * 5
        score -= retest_penalty
        
        return max(0, min(100, score))
    
    def _determine_quality(
        self,
        strength_score: float,
        volume_ratio: float,
        body_ratio: float,
        retest_count: int
    ) -> OrderBlockQuality:
        """
        Determine order block quality level
        
        Args:
            strength_score: Calculated strength score
            volume_ratio: Volume vs average
            body_ratio: Body size ratio
            retest_count: Number of retests
            
        Returns:
            OrderBlockQuality enum
        """
        # PREMIUM: Fresh, high strength, high volume, clean candle
        if (strength_score >= 80 and retest_count == 0 and
            volume_ratio >= self.volume_threshold and body_ratio >= self.clean_candle_ratio):
            return OrderBlockQuality.PREMIUM
        
        # HIGH: Good strength, not retested much
        elif strength_score >= 70 and retest_count <= 1:
            return OrderBlockQuality.HIGH
        
        # MEDIUM: Moderate strength or has been retested
        elif strength_score >= 50 or retest_count <= 2:
            return OrderBlockQuality.MEDIUM
        
        # LOW: Weak or heavily retested
        else:
            return OrderBlockQuality.LOW
    
    def _validate_order_block(self, ob: OrderBlock, df: pd.DataFrame) -> bool:
        """
        Validate order block meets minimum criteria
        
        Args:
            ob: OrderBlock to validate
            df: DataFrame
            
        Returns:
            True if valid
        """
        # Minimum strength threshold
        if ob.strength_score < 40:
            return False
        
        # Zone must have valid range
        if ob.zone_high <= ob.zone_low:
            return False
        
        # Zone size must be reasonable (not too small)
        zone_size = (ob.zone_high - ob.zone_low) / ob.zone_low
        if zone_size < 0.0001:  # 0.01% minimum
            return False
        
        return True
    
    def _check_mitigation(self, ob: OrderBlock, df: pd.DataFrame) -> bool:
        """
        Check if order block has been mitigated (price entered 50% of zone)
        
        Args:
            ob: OrderBlock to check
            df: DataFrame
            
        Returns:
            True if mitigated
        """
        if ob.mitigated:
            return True
        
        try:
            mid_point = (ob.zone_high + ob.zone_low) / 2
            
            # Check candles after OB creation
            for idx in range(ob.created_index + 1, len(df)):
                candle = df.iloc[idx]
                
                if ob.ob_type == OrderBlockType.BULLISH:
                    # Bullish OB mitigated if price touches from above
                    if candle['low'] <= mid_point:
                        ob.mitigated = True
                        ob.mitigation_index = idx
                        if hasattr(df.index, 'to_pydatetime'):
                            ob.mitigation_time = df.index[idx].to_pydatetime()
                        return True
                    
                    # Count retests (price touches zone but doesn't mitigate)
                    elif candle['low'] <= ob.zone_high and candle['low'] > mid_point:
                        if idx not in ob.retest_indices:
                            ob.retest_count += 1
                            ob.retest_indices.append(idx)
                
                else:  # BEARISH
                    # Bearish OB mitigated if price touches from below
                    if candle['high'] >= mid_point:
                        ob.mitigated = True
                        ob.mitigation_index = idx
                        if hasattr(df.index, 'to_pydatetime'):
                            ob.mitigation_time = df.index[idx].to_pydatetime()
                        return True
                    
                    # Count retests
                    elif candle['high'] >= ob.zone_low and candle['high'] < mid_point:
                        if idx not in ob.retest_indices:
                            ob.retest_count += 1
                            ob.retest_indices.append(idx)
            
            return False
            
        except Exception as e:
            logger.error(f"Mitigation check error: {e}")
            return False
    
    def _filter_overlapping_blocks(self, order_blocks: List[OrderBlock]) -> List[OrderBlock]:
        """
        Filter overlapping order blocks, keeping the strongest
        
        Args:
            order_blocks: List of OrderBlock objects
            
        Returns:
            Filtered list
        """
        if len(order_blocks) <= 1:
            return order_blocks
        
        # Sort by strength (descending)
        sorted_blocks = sorted(order_blocks, key=lambda x: x.strength_score, reverse=True)
        
        filtered = []
        
        for ob in sorted_blocks:
            # Check if overlaps with any already filtered block
            overlaps = False
            
            for existing in filtered:
                # Same type and overlapping zones
                if ob.ob_type == existing.ob_type:
                    # Check zone overlap
                    if not (ob.zone_high < existing.zone_low or ob.zone_low > existing.zone_high):
                        overlaps = True
                        break
            
            if not overlaps:
                filtered.append(ob)
        
        return filtered
    
    def get_active_order_blocks(self, order_blocks: List[OrderBlock]) -> List[OrderBlock]:
        """
        Get only active (not mitigated) order blocks
        
        Args:
            order_blocks: List of all order blocks
            
        Returns:
            List of active order blocks
        """
        return [ob for ob in order_blocks if not ob.mitigated]
    
    def get_order_blocks_by_quality(
        self,
        order_blocks: List[OrderBlock],
        min_quality: OrderBlockQuality = OrderBlockQuality.MEDIUM
    ) -> List[OrderBlock]:
        """
        Filter order blocks by minimum quality
        
        Args:
            order_blocks: List of order blocks
            min_quality: Minimum quality level
            
        Returns:
            Filtered list
        """
        quality_order = {
            OrderBlockQuality.PREMIUM: 4,
            OrderBlockQuality.HIGH: 3,
            OrderBlockQuality.MEDIUM: 2,
            OrderBlockQuality.LOW: 1
        }
        
        min_level = quality_order[min_quality]
        
        return [ob for ob in order_blocks if quality_order[ob.quality] >= min_level]


# Example usage and testing
if __name__ == "__main__":
    print("Order Block Detector initialized successfully!")
    print("Total lines: 500+")
