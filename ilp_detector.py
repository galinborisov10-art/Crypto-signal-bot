"""
Internal Liquidity Pool (ILP) Detector
======================================
Detects and analyzes internal liquidity pools in price action including:
- Equal highs and lows
- Swing points (highs and lows)
- IBSL (Internal Buy-Side Liquidity) and ISSL (Internal Sell-Side Liquidity)
- Liquidity sweeps and pool strength scoring

Author: galinborisov10-art
Date: 2025-12-12
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class LiquidityType(Enum):
    """Types of liquidity pools"""
    IBSL = "Internal Buy-Side Liquidity"  # Equal highs
    ISSL = "Internal Sell-Side Liquidity"  # Equal lows
    UNKNOWN = "Unknown"


class SwingType(Enum):
    """Types of swing points"""
    HIGH = "Swing High"
    LOW = "Swing Low"


@dataclass
class SwingPoint:
    """Represents a swing point in price action"""
    index: int
    price: float
    swing_type: SwingType
    timestamp: pd.Timestamp
    strength: int  # Number of bars on each side confirming the swing
    
    def __repr__(self):
        return f"SwingPoint({self.swing_type.value} @ {self.price:.2f}, strength={self.strength})"


@dataclass
class LiquidityPool:
    """Represents an internal liquidity pool"""
    pool_type: LiquidityType
    price_level: float
    indices: List[int]
    swing_points: List[SwingPoint]
    timestamp_first: pd.Timestamp
    timestamp_last: pd.Timestamp
    pool_count: int  # Number of equal highs/lows
    strength_score: float
    tolerance: float
    swept: bool = False
    sweep_index: Optional[int] = None
    sweep_timestamp: Optional[pd.Timestamp] = None
    
    def __repr__(self):
        status = "SWEPT" if self.swept else "ACTIVE"
        return (f"LiquidityPool({self.pool_type.value}, "
                f"price={self.price_level:.2f}, count={self.pool_count}, "
                f"strength={self.strength_score:.2f}, {status})")


class InternalLiquidityPoolDetector:
    """
    Detects internal liquidity pools in price action data.
    
    Internal liquidity pools form when price creates equal highs or equal lows,
    indicating areas where stop losses cluster and liquidity accumulates.
    """
    
    def __init__(
        self,
        swing_period: int = 5,
        equal_price_tolerance: float = 0.001,  # 0.1% tolerance for equal prices
        min_pool_count: int = 2,
        min_swing_strength: int = 2
    ):
        """
        Initialize the ILP Detector.
        
        Parameters:
        -----------
        swing_period : int
            Number of bars on each side to confirm a swing point
        equal_price_tolerance : float
            Percentage tolerance for considering prices as equal (default 0.1%)
        min_pool_count : int
            Minimum number of equal highs/lows to form a pool
        min_swing_strength : int
            Minimum strength required for a valid swing point
        """
        self.swing_period = swing_period
        self.equal_price_tolerance = equal_price_tolerance
        self.min_pool_count = min_pool_count
        self.min_swing_strength = min_swing_strength
        
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.liquidity_pools: List[LiquidityPool] = []
        
    def detect_swing_points(self, df: pd.DataFrame) -> Tuple[List[SwingPoint], List[SwingPoint]]:
        """
        Detect swing highs and swing lows in the price data.
        
        Parameters:
        -----------
        df : pd.DataFrame
            DataFrame with columns: 'high', 'low', 'close', and datetime index
            
        Returns:
        --------
        Tuple[List[SwingPoint], List[SwingPoint]]
            Lists of swing highs and swing lows
        """
        swing_highs = []
        swing_lows = []
        
        period = self.swing_period
        
        # Iterate through the data, leaving margins for comparison
        for i in range(period, len(df) - period):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_time = df.index[i]
            
            # Check for swing high
            is_swing_high = True
            for j in range(1, period + 1):
                if df['high'].iloc[i - j] >= current_high or df['high'].iloc[i + j] >= current_high:
                    is_swing_high = False
                    break
            
            if is_swing_high:
                swing_highs.append(SwingPoint(
                    index=i,
                    price=current_high,
                    swing_type=SwingType.HIGH,
                    timestamp=current_time,
                    strength=period
                ))
            
            # Check for swing low
            is_swing_low = True
            for j in range(1, period + 1):
                if df['low'].iloc[i - j] <= current_low or df['low'].iloc[i + j] <= current_low:
                    is_swing_low = False
                    break
            
            if is_swing_low:
                swing_lows.append(SwingPoint(
                    index=i,
                    price=current_low,
                    swing_type=SwingType.LOW,
                    timestamp=current_time,
                    strength=period
                ))
        
        self.swing_highs = swing_highs
        self.swing_lows = swing_lows
        
        logger.info(f"Detected {len(swing_highs)} swing highs and {len(swing_lows)} swing lows")
        
        return swing_highs, swing_lows
    
    def _are_prices_equal(self, price1: float, price2: float) -> bool:
        """
        Check if two prices are equal within tolerance.
        
        Parameters:
        -----------
        price1, price2 : float
            Prices to compare
            
        Returns:
        --------
        bool
            True if prices are equal within tolerance
        """
        avg_price = (price1 + price2) / 2
        tolerance_amount = avg_price * self.equal_price_tolerance
        return abs(price1 - price2) <= tolerance_amount
    
    def _group_equal_swings(self, swings: List[SwingPoint]) -> List[List[SwingPoint]]:
        """
        Group swing points with equal prices together.
        
        Parameters:
        -----------
        swings : List[SwingPoint]
            List of swing points to group
            
        Returns:
        --------
        List[List[SwingPoint]]
            Groups of swing points with equal prices
        """
        if not swings:
            return []
        
        groups = []
        current_group = [swings[0]]
        
        for i in range(1, len(swings)):
            # Check if current swing is equal to any swing in the current group
            is_equal = any(self._are_prices_equal(swings[i].price, s.price) 
                          for s in current_group)
            
            if is_equal:
                current_group.append(swings[i])
            else:
                if len(current_group) >= self.min_pool_count:
                    groups.append(current_group)
                current_group = [swings[i]]
        
        # Add the last group if it meets criteria
        if len(current_group) >= self.min_pool_count:
            groups.append(current_group)
        
        return groups
    
    def _calculate_pool_strength(self, pool_swings: List[SwingPoint], df: pd.DataFrame) -> float:
        """
        Calculate the strength score of a liquidity pool.
        
        Factors considered:
        - Number of touches (more touches = stronger)
        - Average swing strength
        - Time span of the pool
        - Volume at swing points (if available)
        
        Parameters:
        -----------
        pool_swings : List[SwingPoint]
            Swing points forming the pool
        df : pd.DataFrame
            Price data
            
        Returns:
        --------
        float
            Strength score (0-100)
        """
        if not pool_swings:
            return 0.0
        
        # Factor 1: Number of touches (30% weight)
        touch_score = min(len(pool_swings) / 5.0 * 30, 30)  # Max 30 points
        
        # Factor 2: Average swing strength (25% weight)
        avg_strength = np.mean([s.strength for s in pool_swings])
        strength_score = min(avg_strength / self.swing_period * 25, 25)  # Max 25 points
        
        # Factor 3: Time span (20% weight)
        time_span_bars = pool_swings[-1].index - pool_swings[0].index
        time_score = min(time_span_bars / 100 * 20, 20)  # Max 20 points
        
        # Factor 4: Volume intensity (25% weight) - if volume data available
        volume_score = 0
        if 'volume' in df.columns:
            try:
                volumes = [df['volume'].iloc[s.index] for s in pool_swings]
                avg_volume = df['volume'].mean()
                if avg_volume > 0:
                    volume_ratio = np.mean(volumes) / avg_volume
                    volume_score = min(volume_ratio * 25, 25)  # Max 25 points
            except Exception as e:
                logger.warning(f"Could not calculate volume score: {e}")
                volume_score = 12.5  # Default middle value if volume calculation fails
        else:
            volume_score = 12.5  # Default value if no volume data
        
        total_score = touch_score + strength_score + time_score + volume_score
        
        return round(total_score, 2)
    
    def detect_liquidity_pools(self, df: pd.DataFrame) -> List[LiquidityPool]:
        """
        Detect internal liquidity pools (IBSL and ISSL).
        
        Parameters:
        -----------
        df : pd.DataFrame
            DataFrame with OHLCV data and datetime index
            
        Returns:
        --------
        List[LiquidityPool]
            Detected liquidity pools
        """
        # First detect swing points if not already done
        if not self.swing_highs or not self.swing_lows:
            self.detect_swing_points(df)
        
        liquidity_pools = []
        
        # Detect IBSL (Internal Buy-Side Liquidity) - Equal Highs
        equal_high_groups = self._group_equal_swings(self.swing_highs)
        
        for group in equal_high_groups:
            avg_price = np.mean([s.price for s in group])
            strength = self._calculate_pool_strength(group, df)
            
            pool = LiquidityPool(
                pool_type=LiquidityType.IBSL,
                price_level=avg_price,
                indices=[s.index for s in group],
                swing_points=group,
                timestamp_first=group[0].timestamp,
                timestamp_last=group[-1].timestamp,
                pool_count=len(group),
                strength_score=strength,
                tolerance=self.equal_price_tolerance
            )
            liquidity_pools.append(pool)
        
        # Detect ISSL (Internal Sell-Side Liquidity) - Equal Lows
        equal_low_groups = self._group_equal_swings(self.swing_lows)
        
        for group in equal_low_groups:
            avg_price = np.mean([s.price for s in group])
            strength = self._calculate_pool_strength(group, df)
            
            pool = LiquidityPool(
                pool_type=LiquidityType.ISSL,
                price_level=avg_price,
                indices=[s.index for s in group],
                swing_points=group,
                timestamp_first=group[0].timestamp,
                timestamp_last=group[-1].timestamp,
                pool_count=len(group),
                strength_score=strength,
                tolerance=self.equal_price_tolerance
            )
            liquidity_pools.append(pool)
        
        # Sort pools by timestamp
        liquidity_pools.sort(key=lambda p: p.timestamp_first)
        
        self.liquidity_pools = liquidity_pools
        
        logger.info(f"Detected {len(liquidity_pools)} liquidity pools: "
                   f"{len(equal_high_groups)} IBSL, {len(equal_low_groups)} ISSL")
        
        return liquidity_pools
    
    def detect_liquidity_sweeps(self, df: pd.DataFrame) -> List[LiquidityPool]:
        """
        Detect liquidity sweeps - when price breaks through a liquidity pool.
        
        A sweep occurs when:
        - For IBSL: Price breaks above the equal highs
        - For ISSL: Price breaks below the equal lows
        
        Parameters:
        -----------
        df : pd.DataFrame
            DataFrame with OHLCV data and datetime index
            
        Returns:
        --------
        List[LiquidityPool]
            Updated liquidity pools with sweep information
        """
        if not self.liquidity_pools:
            self.detect_liquidity_pools(df)
        
        swept_pools = []
        
        for pool in self.liquidity_pools:
            if pool.swept:  # Already swept
                continue
            
            # Get the last index in the pool
            last_pool_index = pool.indices[-1]
            
            # Check subsequent bars for sweep
            for i in range(last_pool_index + 1, len(df)):
                if pool.pool_type == LiquidityType.IBSL:
                    # Check if price broke above the equal highs
                    if df['high'].iloc[i] > pool.price_level * (1 + self.equal_price_tolerance):
                        pool.swept = True
                        pool.sweep_index = i
                        pool.sweep_timestamp = df.index[i]
                        swept_pools.append(pool)
                        logger.info(f"IBSL sweep detected at {pool.sweep_timestamp}: "
                                  f"Price {df['high'].iloc[i]:.2f} broke above {pool.price_level:.2f}")
                        break
                
                elif pool.pool_type == LiquidityType.ISSL:
                    # Check if price broke below the equal lows
                    if df['low'].iloc[i] < pool.price_level * (1 - self.equal_price_tolerance):
                        pool.swept = True
                        pool.sweep_index = i
                        pool.sweep_timestamp = df.index[i]
                        swept_pools.append(pool)
                        logger.info(f"ISSL sweep detected at {pool.sweep_timestamp}: "
                                  f"Price {df['low'].iloc[i]:.2f} broke below {pool.price_level:.2f}")
                        break
        
        logger.info(f"Detected {len(swept_pools)} liquidity sweeps")
        
        return self.liquidity_pools
    
    def get_active_pools(self) -> List[LiquidityPool]:
        """
        Get all active (non-swept) liquidity pools.
        
        Returns:
        --------
        List[LiquidityPool]
            Active liquidity pools
        """
        return [pool for pool in self.liquidity_pools if not pool.swept]
    
    def get_swept_pools(self) -> List[LiquidityPool]:
        """
        Get all swept liquidity pools.
        
        Returns:
        --------
        List[LiquidityPool]
            Swept liquidity pools
        """
        return [pool for pool in self.liquidity_pools if pool.swept]
    
    def get_strongest_pools(self, n: int = 5, active_only: bool = True) -> List[LiquidityPool]:
        """
        Get the strongest liquidity pools by strength score.
        
        Parameters:
        -----------
        n : int
            Number of top pools to return
        active_only : bool
            Whether to only consider active (non-swept) pools
            
        Returns:
        --------
        List[LiquidityPool]
            Top N strongest pools
        """
        pools = self.get_active_pools() if active_only else self.liquidity_pools
        sorted_pools = sorted(pools, key=lambda p: p.strength_score, reverse=True)
        return sorted_pools[:n]
    
    def get_pool_summary(self) -> Dict:
        """
        Get a summary of all detected liquidity pools.
        
        Returns:
        --------
        Dict
            Summary statistics
        """
        active_pools = self.get_active_pools()
        swept_pools = self.get_swept_pools()
        
        active_ibsl = [p for p in active_pools if p.pool_type == LiquidityType.IBSL]
        active_issl = [p for p in active_pools if p.pool_type == LiquidityType.ISSL]
        
        swept_ibsl = [p for p in swept_pools if p.pool_type == LiquidityType.IBSL]
        swept_issl = [p for p in swept_pools if p.pool_type == LiquidityType.ISSL]
        
        return {
            'total_pools': len(self.liquidity_pools),
            'active_pools': len(active_pools),
            'swept_pools': len(swept_pools),
            'active_ibsl': len(active_ibsl),
            'active_issl': len(active_issl),
            'swept_ibsl': len(swept_ibsl),
            'swept_issl': len(swept_issl),
            'total_swing_highs': len(self.swing_highs),
            'total_swing_lows': len(self.swing_lows),
            'avg_pool_strength': np.mean([p.strength_score for p in self.liquidity_pools]) 
                                if self.liquidity_pools else 0,
            'strongest_active_pool': max(active_pools, key=lambda p: p.strength_score) 
                                    if active_pools else None
        }
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Complete analysis: detect swing points, liquidity pools, and sweeps.
        
        Parameters:
        -----------
        df : pd.DataFrame
            DataFrame with OHLCV data and datetime index
            
        Returns:
        --------
        Dict
            Complete analysis results
        """
        logger.info("Starting complete liquidity pool analysis...")
        
        # Detect swing points
        swing_highs, swing_lows = self.detect_swing_points(df)
        
        # Detect liquidity pools
        pools = self.detect_liquidity_pools(df)
        
        # Detect sweeps
        self.detect_liquidity_sweeps(df)
        
        # Get summary
        summary = self.get_pool_summary()
        
        logger.info("Analysis complete!")
        logger.info(f"Summary: {summary['total_pools']} pools detected "
                   f"({summary['active_pools']} active, {summary['swept_pools']} swept)")
        
        return {
            'swing_highs': swing_highs,
            'swing_lows': swing_lows,
            'liquidity_pools': pools,
            'active_pools': self.get_active_pools(),
            'swept_pools': self.get_swept_pools(),
            'summary': summary
        }


def example_usage():
    """
    Example usage of the Internal Liquidity Pool Detector.
    """
    # Create sample data
    dates = pd.date_range('2025-01-01', periods=200, freq='1H')
    np.random.seed(42)
    
    # Generate price data with some equal highs and lows
    close_prices = 100 + np.cumsum(np.random.randn(200) * 0.5)
    high_prices = close_prices + np.random.rand(200) * 2
    low_prices = close_prices - np.random.rand(200) * 2
    volumes = np.random.randint(1000, 10000, 200)
    
    # Add some deliberate equal highs and lows
    high_prices[50] = high_prices[55] = high_prices[60] = 105.5  # Equal highs
    low_prices[100] = low_prices[105] = low_prices[110] = 98.2  # Equal lows
    
    df = pd.DataFrame({
        'open': close_prices - 0.5,
        'high': high_prices,
        'low': low_prices,
        'close': close_prices,
        'volume': volumes
    }, index=dates)
    
    # Initialize detector
    detector = InternalLiquidityPoolDetector(
        swing_period=5,
        equal_price_tolerance=0.002,  # 0.2% tolerance
        min_pool_count=2,
        min_swing_strength=2
    )
    
    # Run complete analysis
    results = detector.analyze(df)
    
    # Print results
    print("\n" + "="*70)
    print("INTERNAL LIQUIDITY POOL ANALYSIS RESULTS")
    print("="*70)
    
    print(f"\nSwing Points Detected:")
    print(f"  - Swing Highs: {len(results['swing_highs'])}")
    print(f"  - Swing Lows: {len(results['swing_lows'])}")
    
    print(f"\nLiquidity Pools:")
    print(f"  - Total Pools: {results['summary']['total_pools']}")
    print(f"  - Active Pools: {results['summary']['active_pools']}")
    print(f"  - Swept Pools: {results['summary']['swept_pools']}")
    print(f"  - Active IBSL: {results['summary']['active_ibsl']}")
    print(f"  - Active ISSL: {results['summary']['active_issl']}")
    print(f"  - Average Pool Strength: {results['summary']['avg_pool_strength']:.2f}")
    
    print("\nTop 5 Strongest Active Pools:")
    for i, pool in enumerate(detector.get_strongest_pools(5), 1):
        print(f"  {i}. {pool}")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    example_usage()
