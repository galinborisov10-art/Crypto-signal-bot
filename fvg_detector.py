"""
⚡ FAIR VALUE GAP (FVG) DETECTOR
Detects price imbalances and gaps (Fair Value Gaps / Imbalances)

Features:
- Bullish/Bearish FVG detection
- Gap size measurement
- Mitigation tracking (50%, 100%)
- FVG strength scoring
- Multi-timeframe FVG analysis
- High-quality FVG filtering
- Auto-invalidation on mitigation

Author: galinborisov10-art
Date: 2025-12-12
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FVGType(Enum):
    """Fair Value Gap types"""
    BULLISH = "BULLISH_FVG"
    BEARISH = "BEARISH_FVG"


@dataclass
class FairValueGap:
    """
    Represents a Fair Value Gap (Imbalance)
    
    A FVG occurs when there's a gap between three candles:
    - Bullish FVG: candle[0].high < candle[2].low (gap up)
    - Bearish FVG: candle[0].low > candle[2].high (gap down)
    
    Attributes:
        top: Upper boundary of the gap
        bottom: Lower boundary of the gap
        gap_size: Size of the gap in price
        gap_size_pct: Gap size as percentage
        is_bullish: True if bullish FVG, False if bearish
        timestamp: When the FVG was created
        candle_index: Index of the middle candle
        strength: Strength score (0-100)
        mitigated: Mitigation status (False, '50%', '100%')
        fill_percentage: How much of the gap has been filled (0-100)
        timeframe: Timeframe of detection
        volume_imbalance: Volume spike during formation
        tested_count: Number of times price touched the gap
    """
    top: float
    bottom: float
    gap_size: float
    gap_size_pct: float
    is_bullish: bool
    timestamp: datetime
    candle_index: int
    strength: float
    mitigated: str = "False"  # False, 50%, 100%
    fill_percentage: float = 0.0
    timeframe: str = "1H"
    volume_imbalance: float = 1.0
    tested_count: int = 0
    invalidated: bool = False
    
    @property
    def type(self) -> FVGType:
        """Get FVG type"""
        return FVGType.BULLISH if self.is_bullish else FVGType.BEARISH
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'top': self.top,
            'bottom': self.bottom,
            'gap_size': self.gap_size,
            'gap_size_pct': self.gap_size_pct,
            'is_bullish': self.is_bullish,
            'type': self.type.value,
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            'candle_index': self.candle_index,
            'strength': self.strength,
            'mitigated': self.mitigated,
            'fill_percentage': self.fill_percentage,
            'timeframe': self.timeframe,
            'volume_imbalance': self.volume_imbalance,
            'tested_count': self.tested_count,
            'invalidated': self.invalidated
        }
    
    def is_valid(self) -> bool:
        """Check if FVG is still valid for trading"""
        if self.invalidated:
            return False
        if self.mitigated == "100%":
            return False
        if self.fill_percentage >= 100:
            return False
        return True
    
    def get_50_level(self) -> float:
        """Get 50% fill level"""
        return (self.top + self.bottom) / 2


class FVGDetector:
    """
    Fair Value Gap Detector
    
    Detects imbalances in price action where gaps exist between candles,
    indicating areas where price may return to fill the gap.
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize FVG Detector
        
        Args:
            config: Configuration parameters
        """
        self.config = config or self._get_default_config()
        self.detected_fvgs: List[FairValueGap] = []
        
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'min_gap_size_pct': 0.1,      # Min 0.1% gap size
            'min_gap_size_abs': 10,        # Min absolute gap size
            'min_strength': 60,             # Min strength score
            'max_age_bars': 100,            # Max age before invalidation
            'volume_threshold': 1.2,        # Min volume ratio
            'mitigation_50_pct': 50,        # 50% mitigation threshold
            'mitigation_100_pct': 95,       # 100% mitigation threshold
            'quality_filter': True,         # Enable quality filtering
            'displacement_required': True,  # Require displacement
            'min_displacement_pct': 0.3,   # Min 0.3% displacement
        }
    
    def detect_fvgs(
        self,
        df: pd.DataFrame,
        timeframe: str = "1H"
    ) -> List[FairValueGap]:
        """
        Main FVG detection function
        
        Args:
            df: OHLCV dataframe with columns: open, high, low, close, volume
            timeframe: Timeframe string (e.g., "1H", "4H")
            
        Returns:
            List of detected Fair Value Gaps
        """
        if len(df) < 5:
            logger.warning("Insufficient data for FVG detection")
            return []
        
        # Prepare data
        df = self._prepare_dataframe(df)
        
        # Clear old FVGs
        self.detected_fvgs = []
        
        # Detect bullish FVGs
        bullish_fvgs = self._detect_bullish_fvgs(df, timeframe)
        self.detected_fvgs.extend(bullish_fvgs)
        
        # Detect bearish FVGs
        bearish_fvgs = self._detect_bearish_fvgs(df, timeframe)
        self.detected_fvgs.extend(bearish_fvgs)
        
        # Update mitigation status
        self._update_mitigation_status(df, self.detected_fvgs)
        
        # Filter by quality if enabled
        if self.config['quality_filter']:
            valid_fvgs = self.filter_high_quality_fvgs(self.detected_fvgs)
        else:
            valid_fvgs = self.detected_fvgs
        
        logger.info(f"Detected {len(valid_fvgs)} valid FVGs on {timeframe}")
        
        return valid_fvgs
    
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
        
        # Calculate price metrics
        df['price_change'] = df['close'].pct_change() * 100
        df['atr'] = self._calculate_atr(df, period=14)
        
        return df
    
    def _calculate_atr(self, df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def _detect_bullish_fvgs(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> List[FairValueGap]:
        """
        Detect bullish Fair Value Gaps
        
        Bullish FVG: candle[i-2].high < candle[i].low
        This creates a gap where price jumped up, leaving an imbalance
        
        Args:
            df: Prepared dataframe
            timeframe: Timeframe string
            
        Returns:
            List of bullish FVGs
        """
        bullish_fvgs = []
        
        for i in range(2, len(df)):
            # Check for bullish FVG pattern
            if self._is_bullish_fvg(df, i):
                # Calculate gap metrics
                gap_top = df['low'].iloc[i]
                gap_bottom = df['high'].iloc[i-2]
                gap_size = gap_top - gap_bottom
                gap_size_pct = (gap_size / gap_bottom) * 100
                
                # Check minimum gap size (OR logic: either percentage OR absolute satisfies)
                if gap_size_pct < self.config['min_gap_size_pct'] and gap_size < self.config['min_gap_size_abs']:
                    continue
                
                # Calculate volume imbalance
                volume_imbalance = df['volume_ratio'].iloc[i-1] if 'volume_ratio' in df else 1.0
                
                # Check volume threshold
                if volume_imbalance < self.config['volume_threshold']:
                    continue
                
                # Check for displacement if required
                if self.config['displacement_required']:
                    displacement = self._calculate_displacement(df, i-1, direction='up')
                    if displacement < self.config['min_displacement_pct']:
                        continue
                else:
                    displacement = 0
                
                # Calculate strength
                strength = self._calculate_fvg_strength(
                    gap_size_pct=gap_size_pct,
                    volume_imbalance=volume_imbalance,
                    displacement=displacement
                )
                
                if strength < self.config['min_strength']:
                    continue
                
                # Create FVG
                fvg = FairValueGap(
                    top=gap_top,
                    bottom=gap_bottom,
                    gap_size=gap_size,
                    gap_size_pct=gap_size_pct,
                    is_bullish=True,
                    timestamp=df.index[i],
                    candle_index=i,
                    strength=strength,
                    timeframe=timeframe,
                    volume_imbalance=volume_imbalance
                )
                
                bullish_fvgs.append(fvg)
        
        return bullish_fvgs
    
    def _detect_bearish_fvgs(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> List[FairValueGap]:
        """
        Detect bearish Fair Value Gaps
        
        Bearish FVG: candle[i-2].low > candle[i].high
        This creates a gap where price dropped down, leaving an imbalance
        
        Args:
            df: Prepared dataframe
            timeframe: Timeframe string
            
        Returns:
            List of bearish FVGs
        """
        bearish_fvgs = []
        
        for i in range(2, len(df)):
            # Check for bearish FVG pattern
            if self._is_bearish_fvg(df, i):
                # Calculate gap metrics
                gap_top = df['low'].iloc[i-2]
                gap_bottom = df['high'].iloc[i]
                gap_size = gap_top - gap_bottom
                gap_size_pct = (gap_size / gap_top) * 100
                
                # Check minimum gap size (OR logic: either percentage OR absolute satisfies)
                if gap_size_pct < self.config['min_gap_size_pct'] and gap_size < self.config['min_gap_size_abs']:
                    continue
                
                # Calculate volume imbalance
                volume_imbalance = df['volume_ratio'].iloc[i-1] if 'volume_ratio' in df else 1.0
                
                # Check volume threshold
                if volume_imbalance < self.config['volume_threshold']:
                    continue
                
                # Check for displacement if required
                if self.config['displacement_required']:
                    displacement = self._calculate_displacement(df, i-1, direction='down')
                    if displacement < self.config['min_displacement_pct']:
                        continue
                else:
                    displacement = 0
                
                # Calculate strength
                strength = self._calculate_fvg_strength(
                    gap_size_pct=gap_size_pct,
                    volume_imbalance=volume_imbalance,
                    displacement=displacement
                )
                
                if strength < self.config['min_strength']:
                    continue
                
                # Create FVG
                fvg = FairValueGap(
                    top=gap_top,
                    bottom=gap_bottom,
                    gap_size=gap_size,
                    gap_size_pct=gap_size_pct,
                    is_bullish=False,
                    timestamp=df.index[i],
                    candle_index=i,
                    strength=strength,
                    timeframe=timeframe,
                    volume_imbalance=volume_imbalance
                )
                
                bearish_fvgs.append(fvg)
        
        return bearish_fvgs
    
    def _is_bullish_fvg(self, df: pd.DataFrame, i: int) -> bool:
        """
        Check if pattern forms a bullish FVG
        
        Pattern: candle[i-2].high < candle[i].low
        """
        if i < 2:
            return False
        
        return df['high'].iloc[i-2] < df['low'].iloc[i]
    
    def _is_bearish_fvg(self, df: pd.DataFrame, i: int) -> bool:
        """
        Check if pattern forms a bearish FVG
        
        Pattern: candle[i-2].low > candle[i].high
        """
        if i < 2:
            return False
        
        return df['low'].iloc[i-2] > df['high'].iloc[i]
    
    def _calculate_displacement(
        self,
        df: pd.DataFrame,
        index: int,
        direction: str = 'up'
    ) -> float:
        """Calculate displacement percentage"""
        if index < 1:
            return 0
        
        start_price = df['close'].iloc[index-1]
        end_price = df['close'].iloc[index]
        
        if direction == 'up':
            displacement = ((end_price - start_price) / start_price) * 100
        else:
            displacement = ((start_price - end_price) / start_price) * 100
        
        return max(0, displacement)
    
    def _calculate_fvg_strength(
        self,
        gap_size_pct: float,
        volume_imbalance: float,
        displacement: float
    ) -> float:
        """
        Calculate FVG strength score (0-100)
        
        Args:
            gap_size_pct: Gap size percentage
            volume_imbalance: Volume ratio
            displacement: Displacement percentage
            
        Returns:
            Strength score (0-100)
        """
        # Gap size score (max 40 points)
        gap_score = min(40, gap_size_pct * 20)
        
        # Volume score (max 30 points)
        vol_score = min(30, (volume_imbalance - 1) * 25)
        
        # Displacement score (max 30 points)
        disp_score = min(30, displacement * 5)
        
        total_score = gap_score + vol_score + disp_score
        
        return max(0, min(100, total_score))
    
    def _update_mitigation_status(
        self,
        df: pd.DataFrame,
        fvgs: List[FairValueGap]
    ):
        """
        Update mitigation status for all FVGs
        
        Args:
            df: Dataframe
            fvgs: List of FVGs to check
        """
        for fvg in fvgs:
            # Find candles after the FVG
            fvg_idx = fvg.candle_index
            start_idx = fvg_idx + 1
            
            if start_idx >= len(df):
                continue
            
            # Check mitigation
            mitigated, fill_pct = self.check_mitigation(fvg, df, start_idx)
            
            fvg.mitigated = mitigated
            fvg.fill_percentage = fill_pct
            
            # Invalidate if 100% filled
            if fill_pct >= self.config['mitigation_100_pct']:
                fvg.invalidated = True
    
    def check_mitigation(
        self,
        fvg: FairValueGap,
        df: pd.DataFrame,
        start_idx: int
    ) -> Tuple[str, float]:
        """
        Check mitigation status of a FVG
        
        Args:
            fvg: Fair Value Gap to check
            df: Dataframe
            start_idx: Starting index to check from
            
        Returns:
            Tuple of (mitigation_status, fill_percentage)
        """
        fifty_level = fvg.get_50_level()
        gap_range = fvg.top - fvg.bottom
        
        max_fill = 0.0
        
        for i in range(start_idx, len(df)):
            high = df['high'].iloc[i]
            low = df['low'].iloc[i]
            
            if fvg.is_bullish:
                # Bullish FVG: check if price came back down
                if low <= fvg.top:
                    fvg.tested_count += 1
                    
                    # Calculate fill percentage
                    fill_amount = fvg.top - low
                    fill_pct = (fill_amount / gap_range) * 100
                    max_fill = max(max_fill, fill_pct)
            else:
                # Bearish FVG: check if price came back up
                if high >= fvg.bottom:
                    fvg.tested_count += 1
                    
                    # Calculate fill percentage
                    fill_amount = high - fvg.bottom
                    fill_pct = (fill_amount / gap_range) * 100
                    max_fill = max(max_fill, fill_pct)
        
        # Determine mitigation status
        if max_fill >= self.config['mitigation_100_pct']:
            return "100%", max_fill
        elif max_fill >= self.config['mitigation_50_pct']:
            return "50%", max_fill
        else:
            return "False", max_fill
    
    def filter_high_quality_fvgs(
        self,
        fvgs: List[FairValueGap]
    ) -> List[FairValueGap]:
        """
        Filter for high-quality FVGs
        
        Args:
            fvgs: List of FVGs to filter
            
        Returns:
            Filtered list of high-quality FVGs
        """
        quality_fvgs = []
        
        for fvg in fvgs:
            # Check if valid
            if not fvg.is_valid():
                continue
            
            # Check strength
            if fvg.strength < self.config['min_strength']:
                continue
            
            # Check volume imbalance
            if fvg.volume_imbalance < self.config['volume_threshold']:
                continue
            
            # Check gap size
            if fvg.gap_size_pct < self.config['min_gap_size_pct']:
                continue
            
            quality_fvgs.append(fvg)
        
        # Sort by strength (highest first)
        quality_fvgs.sort(key=lambda x: x.strength, reverse=True)
        
        return quality_fvgs
    
    def get_active_fvgs(
        self,
        current_price: float,
        price_range_pct: float = 5.0
    ) -> List[FairValueGap]:
        """
        Get FVGs near current price
        
        Args:
            current_price: Current market price
            price_range_pct: Percentage range to consider (default 5%)
            
        Returns:
            List of nearby active FVGs
        """
        range_threshold = current_price * (price_range_pct / 100)
        
        active_fvgs = []
        for fvg in self.detected_fvgs:
            # Check if FVG is valid
            if not fvg.is_valid():
                continue
            
            # Check if FVG is near current price
            if abs(fvg.bottom - current_price) <= range_threshold or \
               abs(fvg.top - current_price) <= range_threshold or \
               (fvg.bottom <= current_price <= fvg.top):
                active_fvgs.append(fvg)
        
        # Sort by strength (highest first)
        active_fvgs.sort(key=lambda x: x.strength, reverse=True)
        
        return active_fvgs
    
    def get_nearest_fvg(
        self,
        current_price: float,
        direction: str = 'both'
    ) -> Optional[FairValueGap]:
        """
        Get nearest FVG to current price
        
        Args:
            current_price: Current market price
            direction: 'above', 'below', or 'both'
            
        Returns:
            Nearest FVG or None
        """
        valid_fvgs = [fvg for fvg in self.detected_fvgs if fvg.is_valid()]
        
        if not valid_fvgs:
            return None
        
        if direction == 'above':
            # Find nearest FVG above current price
            above_fvgs = [fvg for fvg in valid_fvgs if fvg.bottom > current_price]
            if not above_fvgs:
                return None
            return min(above_fvgs, key=lambda x: abs(x.bottom - current_price))
        
        elif direction == 'below':
            # Find nearest FVG below current price
            below_fvgs = [fvg for fvg in valid_fvgs if fvg.top < current_price]
            if not below_fvgs:
                return None
            return min(below_fvgs, key=lambda x: abs(x.top - current_price))
        
        else:
            # Find nearest FVG in any direction
            return min(valid_fvgs, key=lambda x: min(
                abs(x.bottom - current_price),
                abs(x.top - current_price)
            ))


# Example usage
if __name__ == "__main__":
    print("⚡ Fair Value Gap Detector - Test Mode")
    
    # Create sample data
    dates = pd.date_range(start='2025-01-01', periods=100, freq='1H')
    np.random.seed(42)
    
    # Simulate price data with some FVGs
    base_price = 50000
    prices = []
    current = base_price
    
    for i in range(100):
        # Add some FVG patterns
        if i == 30:  # Bullish FVG setup
            change = 50
        elif i == 31:  # Gap
            change = 800  # Big jump up
        elif i == 32:
            change = 200
        elif i == 60:  # Bearish FVG setup
            change = -30
        elif i == 61:  # Gap
            change = -700  # Big drop down
        elif i == 62:
            change = -150
        else:
            change = np.random.randn() * 80
        
        current += change
        prices.append(current)
    
    # Create dataframe
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 40) for p in prices],
        'low': [p - abs(np.random.randn() * 40) for p in prices],
        'close': [p + np.random.randn() * 25 for p in prices],
        'volume': [1000000 + np.random.randn() * 200000 for _ in prices]
    })
    
    # Initialize detector
    detector = FVGDetector()
    
    # Detect FVGs
    fvgs = detector.detect_fvgs(df, timeframe="1H")
    
    print(f"\n✅ Detected {len(fvgs)} Fair Value Gaps")
    
    for i, fvg in enumerate(fvgs, 1):
        print(f"\n{i}. {fvg.type.value}")
        print(f"   Price Range: ${fvg.bottom:.2f} - ${fvg.top:.2f}")
        print(f"   Gap Size: ${fvg.gap_size:.2f} ({fvg.gap_size_pct:.3f}%)")
        print(f"   Strength: {fvg.strength:.1f}/100")
        print(f"   Volume Imbalance: {fvg.volume_imbalance:.2f}x")
        print(f"   Mitigated: {fvg.mitigated} ({fvg.fill_percentage:.1f}%)")
        print(f"   50% Level: ${fvg.get_50_level():.2f}")
        print(f"   Tests: {fvg.tested_count}")
    
    # Test active FVGs
    current_price = df['close'].iloc[-1]
    active_fvgs = detector.get_active_fvgs(current_price, price_range_pct=10.0)
    print(f"\n📍 Active FVGs near ${current_price:.2f}: {len(active_fvgs)}")
    
    # Test nearest FVG
    nearest_above = detector.get_nearest_fvg(current_price, direction='above')
    nearest_below = detector.get_nearest_fvg(current_price, direction='below')
    
    if nearest_above:
        print(f"🔼 Nearest FVG above: ${nearest_above.bottom:.2f} - ${nearest_above.top:.2f}")
    if nearest_below:
        print(f"🔽 Nearest FVG below: ${nearest_below.bottom:.2f} - ${nearest_below.top:.2f}")
    
    print("\n✅ FVG Detector test completed!")
    print(f"Total lines: {sum(1 for line in open(__file__))}+")
