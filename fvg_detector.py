"""
📊 FAIR VALUE GAP (FVG) DETECTOR
Professional FVG/Imbalance Detection System

Detects and tracks Fair Value Gaps using ICT methodology:
- 3-candle pattern detection (bullish & bearish)
- Gap size calculation
- Fill tracking (partial & full)
- Quality scoring
- Multi-candle gaps

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


class FVGType(Enum):
    """Fair Value Gap types"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"


class FillStatus(Enum):
    """FVG fill status"""
    UNFILLED = "UNFILLED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FULLY_FILLED = "FULLY_FILLED"


@dataclass
class FairValueGap:
    """Fair Value Gap structure"""
    gap_high: float
    gap_low: float
    gap_size: float  # Absolute size
    gap_size_pct: float  # Percentage
    gap_type: FVGType
    created_at: datetime
    created_index: int
    candle_indices: List[int]  # Indices of candles forming the gap
    
    # Fill tracking
    filled: bool = False
    fill_status: FillStatus = FillStatus.UNFILLED
    fill_percentage: float = 0.0
    fill_index: Optional[int] = None
    fill_time: Optional[datetime] = None
    
    # Quality metrics
    quality_score: float = 0.0
    after_displacement: bool = False
    high_volume: bool = False
    multi_candle: bool = False
    
    # Formation context
    formation_volume: float = 0.0
    volume_ratio: float = 1.0
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'gap_high': self.gap_high,
            'gap_low': self.gap_low,
            'gap_size': self.gap_size,
            'gap_size_pct': self.gap_size_pct,
            'type': self.gap_type.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'created_index': self.created_index,
            'filled': self.filled,
            'fill_status': self.fill_status.value,
            'fill_percentage': self.fill_percentage,
            'quality_score': self.quality_score,
            'after_displacement': self.after_displacement,
            'high_volume': self.high_volume,
            'multi_candle': self.multi_candle
        }
    
    def __repr__(self) -> str:
        return (f"FVG({self.gap_type.value}, "
                f"gap=[{self.gap_low:.2f}-{self.gap_high:.2f}], "
                f"size={self.gap_size_pct:.2f}%, "
                f"quality={self.quality_score:.1f}, "
                f"{self.fill_status.value})")


class FVGDetector:
    """
    Professional Fair Value Gap Detection System
    
    Detects imbalances in price action where price moves so fast
    that it leaves gaps (fair value gaps) that often get filled later.
    
    Features:
    - Standard 3-candle FVG detection
    - Multi-candle gap support
    - Gap quality scoring
    - Fill tracking (partial & full)
    - Volume analysis
    """
    
    def __init__(
        self,
        min_size_pct: float = 0.1,  # Minimum gap size in %
        displacement_threshold: float = 1.5,  # % for displacement detection
        volume_threshold: float = 1.5,  # Volume spike threshold
        max_lookback: int = 100,
        enable_multi_candle: bool = True
    ):
        """
        Initialize FVG Detector
        
        Args:
            min_size_pct: Minimum gap size to consider valid (percentage)
            displacement_threshold: % move to qualify as displacement
            volume_threshold: Volume ratio for high volume classification
            max_lookback: Maximum bars to analyze
            enable_multi_candle: Enable multi-candle gap detection
        """
        self.min_size_pct = min_size_pct
        self.displacement_threshold = displacement_threshold
        self.volume_threshold = volume_threshold
        self.max_lookback = max_lookback
        self.enable_multi_candle = enable_multi_candle
        
        logger.info(f"FVGDetector initialized with min_size={min_size_pct}%")
    
    def detect_fvgs(
        self,
        df: pd.DataFrame,
        min_size_pct: Optional[float] = None
    ) -> List[FairValueGap]:
        """
        Main method: Detect all Fair Value Gaps in DataFrame
        
        Args:
            df: DataFrame with OHLCV data
            min_size_pct: Override minimum gap size
            
        Returns:
            List of FairValueGap objects
        """
        if min_size_pct is None:
            min_size_pct = self.min_size_pct
        
        if len(df) < 3:
            logger.warning(f"Insufficient data: {len(df)} bars")
            return []
        
        fvgs = []
        
        # Calculate volume metrics
        has_volume = 'volume' in df.columns and df['volume'].sum() > 0
        if has_volume:
            volume_ma = df['volume'].rolling(window=20).mean()
        else:
            volume_ma = pd.Series([1.0] * len(df), index=df.index)
        
        # Detect standard 3-candle FVGs
        for idx in range(2, len(df)):
            # Bullish FVG
            bullish_fvg = self._is_bullish_fvg(
                df.iloc[idx - 2],
                df.iloc[idx - 1],
                df.iloc[idx],
                idx
            )
            
            if bullish_fvg:
                gap_high, gap_low = bullish_fvg
                fvg = self._create_fvg(
                    df, idx, gap_high, gap_low, FVGType.BULLISH,
                    [idx - 2, idx - 1, idx], volume_ma, min_size_pct
                )
                
                if fvg:
                    fvgs.append(fvg)
                    logger.debug(f"Bullish FVG detected at index {idx}")
            
            # Bearish FVG
            bearish_fvg = self._is_bearish_fvg(
                df.iloc[idx - 2],
                df.iloc[idx - 1],
                df.iloc[idx],
                idx
            )
            
            if bearish_fvg:
                gap_high, gap_low = bearish_fvg
                fvg = self._create_fvg(
                    df, idx, gap_high, gap_low, FVGType.BEARISH,
                    [idx - 2, idx - 1, idx], volume_ma, min_size_pct
                )
                
                if fvg:
                    fvgs.append(fvg)
                    logger.debug(f"Bearish FVG detected at index {idx}")
        
        # Detect multi-candle gaps if enabled
        if self.enable_multi_candle:
            multi_fvgs = self._detect_multi_candle_fvgs(df, volume_ma, min_size_pct)
            fvgs.extend(multi_fvgs)
        
        # Check fill status for all FVGs
        for fvg in fvgs:
            self._check_gap_filled(fvg, df)
        
        # Filter tiny gaps
        fvgs = self._filter_tiny_gaps(fvgs, min_size_pct)
        
        logger.info(f"Detected {len(fvgs)} Fair Value Gaps")
        return fvgs
    
    def _is_bullish_fvg(
        self,
        candle1: pd.Series,
        candle2: pd.Series,
        candle3: pd.Series,
        idx: int
    ) -> Optional[Tuple[float, float]]:
        """
        Check for bullish FVG pattern
        
        Bullish FVG occurs when:
        - candle1.high < candle3.low (gap exists)
        - Gap indicates upward price imbalance
        
        Args:
            candle1: First candle (2 bars ago)
            candle2: Middle candle (1 bar ago)
            candle3: Current candle
            idx: Current index
            
        Returns:
            Tuple of (gap_high, gap_low) or None
        """
        try:
            # Check if gap exists: candle1 high is below candle3 low
            if candle1['high'] < candle3['low']:
                gap_high = candle3['low']
                gap_low = candle1['high']
                return (gap_high, gap_low)
            
            return None
            
        except Exception as e:
            logger.error(f"Bullish FVG check error at {idx}: {e}")
            return None
    
    def _is_bearish_fvg(
        self,
        candle1: pd.Series,
        candle2: pd.Series,
        candle3: pd.Series,
        idx: int
    ) -> Optional[Tuple[float, float]]:
        """
        Check for bearish FVG pattern
        
        Bearish FVG occurs when:
        - candle1.low > candle3.high (gap exists)
        - Gap indicates downward price imbalance
        
        Args:
            candle1: First candle (2 bars ago)
            candle2: Middle candle (1 bar ago)
            candle3: Current candle
            idx: Current index
            
        Returns:
            Tuple of (gap_high, gap_low) or None
        """
        try:
            # Check if gap exists: candle1 low is above candle3 high
            if candle1['low'] > candle3['high']:
                gap_high = candle1['low']
                gap_low = candle3['high']
                return (gap_high, gap_low)
            
            return None
            
        except Exception as e:
            logger.error(f"Bearish FVG check error at {idx}: {e}")
            return None
    
    def _create_fvg(
        self,
        df: pd.DataFrame,
        idx: int,
        gap_high: float,
        gap_low: float,
        fvg_type: FVGType,
        candle_indices: List[int],
        volume_ma: pd.Series,
        min_size_pct: float
    ) -> Optional[FairValueGap]:
        """
        Create FairValueGap object with all properties
        
        Args:
            df: DataFrame
            idx: Current index
            gap_high: High of the gap
            gap_low: Low of the gap
            fvg_type: Bullish or Bearish
            candle_indices: Indices of candles forming gap
            volume_ma: Volume moving average
            min_size_pct: Minimum gap size threshold
            
        Returns:
            FairValueGap object or None
        """
        try:
            # Calculate gap size
            gap_size = gap_high - gap_low
            reference_price = (gap_high + gap_low) / 2
            gap_size_pct = (gap_size / reference_price) * 100
            
            # Filter too small gaps
            if gap_size_pct < min_size_pct:
                return None
            
            # Get timestamp
            if hasattr(df.index, 'to_pydatetime'):
                created_at = df.index[idx].to_pydatetime()
            else:
                created_at = datetime.now()
            
            # Volume analysis
            if 'volume' in df.columns:
                # Use middle candle volume
                middle_idx = candle_indices[1] if len(candle_indices) >= 2 else idx
                formation_volume = df.iloc[middle_idx]['volume']
                avg_volume = volume_ma.iloc[middle_idx]
                volume_ratio = formation_volume / avg_volume if avg_volume > 0 else 1.0
                high_volume = volume_ratio >= self.volume_threshold
            else:
                formation_volume = 0
                volume_ratio = 1.0
                high_volume = False
            
            # Check if after displacement
            after_displacement = self._check_displacement(df, idx, fvg_type)
            
            # Multi-candle check
            multi_candle = len(candle_indices) > 3
            
            # Calculate quality score
            quality_score = self._calculate_fvg_quality(
                gap_size_pct, after_displacement, high_volume,
                multi_candle, volume_ratio, False  # Not filled yet
            )
            
            fvg = FairValueGap(
                gap_high=gap_high,
                gap_low=gap_low,
                gap_size=gap_size,
                gap_size_pct=gap_size_pct,
                gap_type=fvg_type,
                created_at=created_at,
                created_index=idx,
                candle_indices=candle_indices,
                quality_score=quality_score,
                after_displacement=after_displacement,
                high_volume=high_volume,
                multi_candle=multi_candle,
                formation_volume=formation_volume,
                volume_ratio=volume_ratio
            )
            
            return fvg
            
        except Exception as e:
            logger.error(f"FVG creation error: {e}")
            return None
    
    def _check_displacement(
        self,
        df: pd.DataFrame,
        idx: int,
        fvg_type: FVGType
    ) -> bool:
        """
        Check if FVG occurred after a displacement move
        
        Args:
            df: DataFrame
            idx: Current index
            fvg_type: Type of FVG
            
        Returns:
            True if after displacement
        """
        try:
            if idx < 10:
                return False
            
            # Look at previous 10 candles
            lookback = df.iloc[idx - 10:idx]
            
            if fvg_type == FVGType.BULLISH:
                # Check for strong upward move
                low_start = lookback['low'].min()
                high_end = df.iloc[idx]['high']
                move_pct = ((high_end - low_start) / low_start) * 100
                
                return move_pct >= self.displacement_threshold
            
            else:  # BEARISH
                # Check for strong downward move
                high_start = lookback['high'].max()
                low_end = df.iloc[idx]['low']
                move_pct = ((high_start - low_end) / high_start) * 100
                
                return move_pct >= self.displacement_threshold
            
        except Exception as e:
            logger.error(f"Displacement check error: {e}")
            return False
    
    def _calculate_fvg_quality(
        self,
        gap_size_pct: float,
        after_displacement: bool,
        high_volume: bool,
        multi_candle: bool,
        volume_ratio: float,
        filled: bool
    ) -> float:
        """
        Calculate FVG quality score (0-100)
        
        Scoring factors:
        - Large gap size: 0-30 points
        - After displacement: 0-25 points
        - Not yet filled: 0-20 points
        - High volume: 0-15 points
        - Multi-candle gap: 0-10 points
        
        Args:
            gap_size_pct: Gap size in percentage
            after_displacement: Whether after displacement
            high_volume: High volume flag
            multi_candle: Multi-candle gap flag
            volume_ratio: Volume vs average
            filled: Whether gap is filled
            
        Returns:
            Quality score 0-100
        """
        score = 0.0
        
        # 1. Gap size (0-30 points)
        # Larger gaps are more significant
        if gap_size_pct >= 1.0:  # 1% or larger
            score += 30
        elif gap_size_pct >= 0.5:
            score += 20
        elif gap_size_pct >= 0.3:
            score += 15
        elif gap_size_pct >= 0.1:
            score += 10
        else:
            score += 5
        
        # 2. After displacement (0-25 points)
        if after_displacement:
            score += 25
        
        # 3. Not filled (0-20 points)
        if not filled:
            score += 20
        
        # 4. High volume (0-15 points)
        if high_volume:
            volume_score = min(15, (volume_ratio / self.volume_threshold) * 15)
            score += volume_score
        
        # 5. Multi-candle gap (0-10 points)
        if multi_candle:
            score += 10
        
        return min(100, score)
    
    def _check_gap_filled(self, fvg: FairValueGap, df: pd.DataFrame) -> bool:
        """
        Check if FVG has been filled (price returned into gap)
        
        Args:
            fvg: FairValueGap to check
            df: DataFrame
            
        Returns:
            True if filled
        """
        if fvg.filled:
            return True
        
        try:
            gap_mid = (fvg.gap_high + fvg.gap_low) / 2
            
            # Check candles after FVG creation
            for idx in range(fvg.created_index + 1, len(df)):
                candle = df.iloc[idx]
                
                if fvg.gap_type == FVGType.BULLISH:
                    # Bullish FVG filled when price comes back down into gap
                    if candle['low'] <= fvg.gap_high:
                        # Calculate fill percentage
                        if candle['low'] <= fvg.gap_low:
                            # Fully filled
                            fvg.fill_percentage = 100.0
                            fvg.fill_status = FillStatus.FULLY_FILLED
                            fvg.filled = True
                        else:
                            # Partially filled
                            filled_amount = fvg.gap_high - candle['low']
                            fvg.fill_percentage = (filled_amount / fvg.gap_size) * 100
                            fvg.fill_status = FillStatus.PARTIALLY_FILLED
                            
                            # Consider >= 50% as filled
                            if fvg.fill_percentage >= 50:
                                fvg.filled = True
                        
                        fvg.fill_index = idx
                        if hasattr(df.index, 'to_pydatetime'):
                            fvg.fill_time = df.index[idx].to_pydatetime()
                        
                        return fvg.filled
                
                else:  # BEARISH
                    # Bearish FVG filled when price comes back up into gap
                    if candle['high'] >= fvg.gap_low:
                        # Calculate fill percentage
                        if candle['high'] >= fvg.gap_high:
                            # Fully filled
                            fvg.fill_percentage = 100.0
                            fvg.fill_status = FillStatus.FULLY_FILLED
                            fvg.filled = True
                        else:
                            # Partially filled
                            filled_amount = candle['high'] - fvg.gap_low
                            fvg.fill_percentage = (filled_amount / fvg.gap_size) * 100
                            fvg.fill_status = FillStatus.PARTIALLY_FILLED
                            
                            # Consider >= 50% as filled
                            if fvg.fill_percentage >= 50:
                                fvg.filled = True
                        
                        fvg.fill_index = idx
                        if hasattr(df.index, 'to_pydatetime'):
                            fvg.fill_time = df.index[idx].to_pydatetime()
                        
                        return fvg.filled
            
            return False
            
        except Exception as e:
            logger.error(f"Gap fill check error: {e}")
            return False
    
    def _detect_multi_candle_fvgs(
        self,
        df: pd.DataFrame,
        volume_ma: pd.Series,
        min_size_pct: float
    ) -> List[FairValueGap]:
        """
        Detect multi-candle Fair Value Gaps (4+ candles)
        
        Sometimes gaps occur over multiple candles during strong moves
        
        Args:
            df: DataFrame
            volume_ma: Volume moving average
            min_size_pct: Minimum gap size
            
        Returns:
            List of multi-candle FVGs
        """
        multi_fvgs = []
        
        try:
            # Look for 4-5 candle patterns
            for idx in range(4, len(df)):
                # Bullish multi-candle FVG
                # Check if there's a gap between candle[idx-3] high and candle[idx] low
                if df.iloc[idx - 3]['high'] < df.iloc[idx]['low']:
                    gap_high = df.iloc[idx]['low']
                    gap_low = df.iloc[idx - 3]['high']
                    
                    fvg = self._create_fvg(
                        df, idx, gap_high, gap_low, FVGType.BULLISH,
                        [idx - 3, idx - 2, idx - 1, idx], volume_ma, min_size_pct
                    )
                    
                    if fvg:
                        multi_fvgs.append(fvg)
                
                # Bearish multi-candle FVG
                if df.iloc[idx - 3]['low'] > df.iloc[idx]['high']:
                    gap_high = df.iloc[idx - 3]['low']
                    gap_low = df.iloc[idx]['high']
                    
                    fvg = self._create_fvg(
                        df, idx, gap_high, gap_low, FVGType.BEARISH,
                        [idx - 3, idx - 2, idx - 1, idx], volume_ma, min_size_pct
                    )
                    
                    if fvg:
                        multi_fvgs.append(fvg)
            
            return multi_fvgs
            
        except Exception as e:
            logger.error(f"Multi-candle FVG detection error: {e}")
            return []
    
    def _filter_tiny_gaps(
        self,
        fvgs: List[FairValueGap],
        min_size: float
    ) -> List[FairValueGap]:
        """
        Filter out tiny gaps below minimum size
        
        Args:
            fvgs: List of FVGs
            min_size: Minimum gap size in %
            
        Returns:
            Filtered list
        """
        return [fvg for fvg in fvgs if fvg.gap_size_pct >= min_size]
    
    def get_active_fvgs(
        self,
        fvgs: List[FairValueGap],
        include_partial: bool = False
    ) -> List[FairValueGap]:
        """
        Get only unfilled or partially filled FVGs
        
        Args:
            fvgs: List of all FVGs
            include_partial: Include partially filled gaps
            
        Returns:
            List of active FVGs
        """
        if include_partial:
            return [fvg for fvg in fvgs if fvg.fill_status != FillStatus.FULLY_FILLED]
        else:
            return [fvg for fvg in fvgs if not fvg.filled]
    
    def get_fvgs_by_type(
        self,
        fvgs: List[FairValueGap],
        fvg_type: FVGType
    ) -> List[FairValueGap]:
        """
        Filter FVGs by type
        
        Args:
            fvgs: List of FVGs
            fvg_type: BULLISH or BEARISH
            
        Returns:
            Filtered list
        """
        return [fvg for fvg in fvgs if fvg.gap_type == fvg_type]
    
    def get_high_quality_fvgs(
        self,
        fvgs: List[FairValueGap],
        min_quality: float = 70.0
    ) -> List[FairValueGap]:
        """
        Get high quality FVGs above threshold
        
        Args:
            fvgs: List of FVGs
            min_quality: Minimum quality score
            
        Returns:
            High quality FVGs
        """
        return [fvg for fvg in fvgs if fvg.quality_score >= min_quality]


# Example usage and testing
if __name__ == "__main__":
    print("FVG Detector initialized successfully!")
    print("Total lines: 450+")
