"""
LuxAlgo Support & Resistance Signals MTF - Python Implementation
Converted from Pine Script v5
License: CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/)
© LuxAlgo
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field


@dataclass
class Bar:
    """Bar properties with their values"""
    o: float  # open
    h: float  # high
    l: float  # low
    c: float  # close
    v: float  # volume
    i: int    # index


@dataclass
class PivotPoint:
    """Store pivot high/low and index data"""
    x: int = 0      # last pivot bar index
    x1: int = 0     # previous pivot bar index
    h: float = 0.0  # last pivot high
    h1: float = 0.0 # previous pivot high
    l: float = 0.0  # last pivot low
    l1: float = 0.0 # previous pivot low
    hx: bool = False # pivot high cross status
    lx: bool = False # pivot low cross status


@dataclass
class SnRZone:
    """Support and Resistance zone data"""
    left: int
    right: int
    top: float
    bottom: float
    is_support: bool
    breakout: bool = False
    test: bool = False
    retest: bool = False
    liquidity_sweep: bool = False
    margin: float = 0.0
    lq_top: Optional[float] = None
    lq_bottom: Optional[float] = None
    lq_left: Optional[int] = None
    lq_right: Optional[int] = None


@dataclass
class LuxAlgoSignal:
    """Signal data from LuxAlgo S/R MTF"""
    type: str  # 'breakout', 'test', 'retest', 'rejection', 'liquidity_sweep'
    direction: str  # 'bullish', 'bearish'
    price: float
    bar_index: int
    zone: Optional[SnRZone] = None
    volume_profile: str = 'average'  # 'high', 'low', 'average', 'spike'


class LuxAlgoSRMTF:
    """
    LuxAlgo Support & Resistance Signals Multi-Timeframe Analyzer
    
    Detects:
    - Dynamic and static S/R levels
    - Breakouts and retests
    - Liquidity zones and manipulations
    - Volume-confirmed signals
    """
    
    def __init__(
        self,
        detection_length: int = 15,
        sr_margin: float = 2.0,
        manipulation_margin: float = 1.3,
        avoid_false_breakouts: bool = True,
        check_historical_sr: bool = True
    ):
        self.detection_length = detection_length
        self.sr_margin = sr_margin
        self.manipulation_margin = manipulation_margin
        self.avoid_false_breakouts = avoid_false_breakouts
        self.check_historical_sr = check_historical_sr
        
        # Storage
        self.resistance_zones: List[SnRZone] = []
        self.support_zones: List[SnRZone] = []
        self.pivot = PivotPoint()
        self.signals: List[LuxAlgoSignal] = []
        self.mss = 0  # Market structure state
        
    def calculate_atr(self, df: pd.DataFrame, period: int = 17) -> pd.Series:
        """Calculate Average True Range"""
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift(1))
        tr3 = abs(low - close.shift(1))
        
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=period).mean()
        
        return atr
    
    def get_volume_profile(self, volume: float, volume_sma: float) -> str:
        """Determine volume profile"""
        if pd.isna(volume) or pd.isna(volume_sma):
            return 'average'
        
        if volume >= 1.618 * volume_sma:
            return 'high'
        elif volume <= 0.618 * volume_sma:
            return 'low'
        elif volume > 4.669 * volume_sma:
            return 'spike'
        else:
            return 'average'
    
    def detect_pivot_high(self, df: pd.DataFrame, idx: int) -> Optional[float]:
        """Detect pivot high at index"""
        if idx < self.detection_length or idx >= len(df) - self.detection_length:
            return None
        
        center_high = df.loc[idx, 'high']
        
        # Check if highest in the window
        left_window = df.loc[idx - self.detection_length:idx - 1, 'high']
        right_window = df.loc[idx + 1:idx + self.detection_length, 'high']
        
        if center_high > left_window.max() and center_high > right_window.max():
            return center_high
        
        return None
    
    def detect_pivot_low(self, df: pd.DataFrame, idx: int) -> Optional[float]:
        """Detect pivot low at index"""
        if idx < self.detection_length or idx >= len(df) - self.detection_length:
            return None
        
        center_low = df.loc[idx, 'low']
        
        # Check if lowest in the window
        left_window = df.loc[idx - self.detection_length:idx - 1, 'low']
        right_window = df.loc[idx + 1:idx + self.detection_length, 'low']
        
        if center_low < left_window.min() and center_low < right_window.min():
            return center_low
        
        return None
    
    def create_resistance_zone(
        self,
        df: pd.DataFrame,
        pivot_idx: int,
        pivot_price: float,
        current_idx: int
    ) -> SnRZone:
        """Create resistance zone from pivot high"""
        price_range = df['high'].max() - df['low'].min()
        margin = price_range / df['high'].max()
        
        top = pivot_price
        bottom = pivot_price * (1 - margin * 0.17 * self.sr_margin)
        
        return SnRZone(
            left=pivot_idx,
            right=current_idx,
            top=top,
            bottom=bottom,
            is_support=False,
            margin=margin
        )
    
    def create_support_zone(
        self,
        df: pd.DataFrame,
        pivot_idx: int,
        pivot_price: float,
        current_idx: int
    ) -> SnRZone:
        """Create support zone from pivot low"""
        price_range = df['high'].max() - df['low'].min()
        margin = price_range / df['high'].max()
        
        top = pivot_price * (1 + margin * 0.17 * self.sr_margin)
        bottom = pivot_price
        
        return SnRZone(
            left=pivot_idx,
            right=current_idx,
            top=top,
            bottom=bottom,
            is_support=True,
            margin=margin
        )
    
    def check_breakout(
        self,
        df: pd.DataFrame,
        zone: SnRZone,
        idx: int
    ) -> Optional[LuxAlgoSignal]:
        """Check for breakout of S/R zone"""
        close = df.loc[idx, 'close']
        close_prev = df.loc[idx - 1, 'close']
        
        if zone.breakout:
            return None
        
        if zone.is_support:
            # Bearish breakout
            if self.avoid_false_breakouts:
                threshold = zone.bottom * (1 - zone.margin * 0.17)
                if close_prev < threshold and close < threshold:
                    return LuxAlgoSignal(
                        type='breakout',
                        direction='bearish',
                        price=close_prev,
                        bar_index=idx - 1,
                        zone=zone
                    )
            else:
                if close_prev < zone.bottom:
                    return LuxAlgoSignal(
                        type='breakout',
                        direction='bearish',
                        price=close_prev,
                        bar_index=idx - 1,
                        zone=zone
                    )
        else:
            # Bullish breakout
            if self.avoid_false_breakouts:
                threshold = zone.top * (1 + zone.margin * 0.17)
                if close_prev > threshold and close > threshold:
                    return LuxAlgoSignal(
                        type='breakout',
                        direction='bullish',
                        price=close_prev,
                        bar_index=idx - 1,
                        zone=zone
                    )
            else:
                if close_prev > zone.top:
                    return LuxAlgoSignal(
                        type='breakout',
                        direction='bullish',
                        price=close_prev,
                        bar_index=idx - 1,
                        zone=zone
                    )
        
        return None
    
    def check_test(
        self,
        df: pd.DataFrame,
        zone: SnRZone,
        idx: int
    ) -> Optional[LuxAlgoSignal]:
        """Check for test of S/R zone"""
        if zone.test or zone.breakout:
            return None
        
        high = df.loc[idx - 1, 'high']
        low = df.loc[idx - 1, 'low']
        close = df.loc[idx - 1, 'close']
        close_current = df.loc[idx, 'close']
        
        if zone.is_support:
            # Test from above
            if (low < zone.top and 
                close > zone.bottom and 
                close_current > zone.bottom and
                idx - 1 != zone.left):
                return LuxAlgoSignal(
                    type='test',
                    direction='bullish',
                    price=low,
                    bar_index=idx - 1,
                    zone=zone
                )
        else:
            # Test from below
            if (high > zone.bottom and 
                close < zone.top and 
                close_current < zone.top and
                idx - 1 != zone.left):
                return LuxAlgoSignal(
                    type='test',
                    direction='bearish',
                    price=high,
                    bar_index=idx - 1,
                    zone=zone
                )
        
        return None
    
    def check_retest(
        self,
        df: pd.DataFrame,
        zone: SnRZone,
        idx: int,
        opposite_broken: bool
    ) -> Optional[LuxAlgoSignal]:
        """Check for retest after breakout"""
        if not opposite_broken or zone.retest:
            return None
        
        open_prev = df.loc[idx - 1, 'open']
        high_prev = df.loc[idx - 1, 'high']
        low_prev = df.loc[idx - 1, 'low']
        close_prev = df.loc[idx - 1, 'close']
        
        if zone.is_support:
            # Retest from below after bullish breakout
            if (open_prev > zone.bottom and 
                low_prev < zone.top and 
                close_prev > zone.top and
                idx - 1 != zone.left):
                return LuxAlgoSignal(
                    type='retest',
                    direction='bullish',
                    price=low_prev,
                    bar_index=idx - 1,
                    zone=zone
                )
        else:
            # Retest from above after bearish breakout
            if (open_prev < zone.top and 
                high_prev > zone.bottom and 
                close_prev < zone.bottom and
                idx - 1 != zone.left):
                return LuxAlgoSignal(
                    type='retest',
                    direction='bearish',
                    price=high_prev,
                    bar_index=idx - 1,
                    zone=zone
                )
        
        return None
    
    def check_liquidity_sweep(
        self,
        df: pd.DataFrame,
        zone: SnRZone,
        idx: int
    ) -> bool:
        """Check for liquidity sweep / manipulation"""
        if zone.liquidity_sweep or idx != zone.right:
            return False
        
        high = df.loc[idx, 'high']
        low = df.loc[idx, 'low']
        close = df.loc[idx, 'close']
        
        if zone.is_support:
            # Sweep below support
            sweep_threshold = zone.bottom * (1 - zone.margin * 0.17 * self.manipulation_margin)
            if low < zone.bottom and close >= sweep_threshold:
                # Update liquidity zone
                if zone.lq_right and (zone.lq_right + self.detection_length > idx):
                    # Extend existing
                    zone.lq_right = idx + 1
                    zone.lq_bottom = max(min(low, zone.lq_bottom or low), sweep_threshold)
                else:
                    # Create new
                    zone.lq_left = idx - 1
                    zone.lq_right = idx + 1
                    zone.lq_top = zone.bottom
                    zone.lq_bottom = max(low, sweep_threshold)
                return True
        else:
            # Sweep above resistance
            sweep_threshold = zone.top * (1 + zone.margin * 0.17 * self.manipulation_margin)
            if high > zone.top and close <= sweep_threshold:
                # Update liquidity zone
                if zone.lq_right and (zone.lq_right + self.detection_length > idx):
                    # Extend existing
                    zone.lq_right = idx + 1
                    zone.lq_top = min(max(high, zone.lq_top or high), sweep_threshold)
                else:
                    # Create new
                    zone.lq_left = idx - 1
                    zone.lq_right = idx + 1
                    zone.lq_bottom = zone.top
                    zone.lq_top = min(high, sweep_threshold)
                return True
        
        return False
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Main analysis function
        
        Args:
            df: DataFrame with OHLCV data (columns: open, high, low, close, volume)
        
        Returns:
            Dictionary with analysis results
        """
        # Reset storage
        self.resistance_zones = []
        self.support_zones = []
        self.signals = []
        
        # Calculate indicators
        atr = self.calculate_atr(df)
        volume_sma = df['volume'].rolling(window=17).mean()
        
        # Process each bar
        for idx in range(self.detection_length, len(df)):
            # Detect pivot high
            pivot_high = self.detect_pivot_high(df, idx - self.detection_length)
            if pivot_high is not None:
                pivot_idx = idx - self.detection_length
                
                # Update pivot data
                self.pivot.h1 = self.pivot.h
                self.pivot.h = pivot_high
                self.pivot.x1 = self.pivot.x
                self.pivot.x = pivot_idx
                self.pivot.hx = False
                
                # Create or update resistance zone
                if len(self.resistance_zones) > 0:
                    last_zone = self.resistance_zones[0]
                    zone_range = last_zone.top - last_zone.bottom
                    
                    # Check if new pivot is in different zone
                    if (pivot_high < last_zone.bottom * (1 - last_zone.margin * 0.17 * self.sr_margin) or
                        pivot_high > last_zone.top * (1 + last_zone.margin * 0.17 * self.sr_margin)):
                        
                        # Create new zone
                        new_zone = self.create_resistance_zone(df, pivot_idx, pivot_high, idx)
                        self.resistance_zones.insert(0, new_zone)
                    else:
                        # Extend existing zone
                        last_zone.right = idx
                else:
                    # First zone
                    new_zone = self.create_resistance_zone(df, pivot_idx, pivot_high, idx)
                    self.resistance_zones.append(new_zone)
            
            # Detect pivot low
            pivot_low = self.detect_pivot_low(df, idx - self.detection_length)
            if pivot_low is not None:
                pivot_idx = idx - self.detection_length
                
                # Update pivot data
                self.pivot.l1 = self.pivot.l
                self.pivot.l = pivot_low
                self.pivot.x1 = self.pivot.x
                self.pivot.x = pivot_idx
                self.pivot.lx = False
                
                # Create or update support zone
                if len(self.support_zones) > 0:
                    last_zone = self.support_zones[0]
                    
                    # Check if new pivot is in different zone
                    if (pivot_low < last_zone.bottom * (1 - last_zone.margin * 0.17 * self.sr_margin) or
                        pivot_low > last_zone.top * (1 + last_zone.margin * 0.17 * self.sr_margin)):
                        
                        # Create new zone
                        new_zone = self.create_support_zone(df, pivot_idx, pivot_low, idx)
                        self.support_zones.insert(0, new_zone)
                    else:
                        # Extend existing zone
                        last_zone.right = idx
                else:
                    # First zone
                    new_zone = self.create_support_zone(df, pivot_idx, pivot_low, idx)
                    self.support_zones.append(new_zone)
            
            # Check market structure
            close = df.loc[idx, 'close']
            close_prev = df.loc[idx - 1, 'close']
            
            if close_prev > self.pivot.h and close > self.pivot.h and not self.pivot.hx:
                self.pivot.hx = True
                self.mss = 1  # Bullish structure
            
            if close_prev < self.pivot.l and close < self.pivot.l and not self.pivot.lx:
                self.pivot.lx = True
                self.mss = -1  # Bearish structure
            
            # Check resistance zones
            if len(self.resistance_zones) > 0:
                zone = self.resistance_zones[0]
                
                # Extend zone if price interacts
                if (df.loc[idx, 'high'] > zone.bottom * (1 - zone.margin * 0.17) and
                    not zone.breakout):
                    if df.loc[idx, 'high'] > zone.bottom:
                        zone.right = idx
                
                # Check for signals
                breakout_signal = self.check_breakout(df, zone, idx)
                if breakout_signal:
                    zone.breakout = True
                    zone.retest = False
                    zone.right = idx - 1
                    breakout_signal.volume_profile = self.get_volume_profile(
                        df.loc[idx - 1, 'volume'],
                        volume_sma.loc[idx - 1]
                    )
                    self.signals.append(breakout_signal)
                    
                    # Convert to support zone
                    new_support = SnRZone(
                        left=idx - 1,
                        right=idx + 1,
                        top=zone.top,
                        bottom=zone.bottom,
                        is_support=True,
                        margin=zone.margin
                    )
                    self.support_zones.insert(0, new_support)
                
                support_broken = len(self.support_zones) > 0 and self.support_zones[0].breakout
                
                retest_signal = self.check_retest(df, zone, idx, support_broken)
                if retest_signal:
                    zone.retest = True
                    zone.right = idx
                    retest_signal.volume_profile = self.get_volume_profile(
                        df.loc[idx - 1, 'volume'],
                        volume_sma.loc[idx - 1]
                    )
                    self.signals.append(retest_signal)
                
                test_signal = self.check_test(df, zone, idx)
                if test_signal:
                    zone.test = True
                    zone.right = idx
                    test_signal.volume_profile = self.get_volume_profile(
                        df.loc[idx - 1, 'volume'],
                        volume_sma.loc[idx - 1]
                    )
                    self.signals.append(test_signal)
                
                # Check liquidity sweep
                if self.check_liquidity_sweep(df, zone, idx):
                    zone.liquidity_sweep = True
                    sweep_signal = LuxAlgoSignal(
                        type='liquidity_sweep',
                        direction='bearish',
                        price=df.loc[idx, 'high'],
                        bar_index=idx,
                        zone=zone
                    )
                    self.signals.append(sweep_signal)
            
            # Check support zones
            if len(self.support_zones) > 0:
                zone = self.support_zones[0]
                
                # Extend zone if price interacts
                if (df.loc[idx, 'low'] < zone.top * (1 + zone.margin * 0.17) and
                    not zone.breakout):
                    if df.loc[idx, 'low'] < zone.top:
                        zone.right = idx
                
                # Check for signals
                breakout_signal = self.check_breakout(df, zone, idx)
                if breakout_signal:
                    zone.breakout = True
                    zone.retest = False
                    zone.right = idx - 1
                    breakout_signal.volume_profile = self.get_volume_profile(
                        df.loc[idx - 1, 'volume'],
                        volume_sma.loc[idx - 1]
                    )
                    self.signals.append(breakout_signal)
                    
                    # Convert to resistance zone
                    new_resistance = SnRZone(
                        left=idx - 1,
                        right=idx + 1,
                        top=zone.top,
                        bottom=zone.bottom,
                        is_support=False,
                        margin=zone.margin
                    )
                    self.resistance_zones.insert(0, new_resistance)
                
                resistance_broken = len(self.resistance_zones) > 0 and self.resistance_zones[0].breakout
                
                retest_signal = self.check_retest(df, zone, idx, resistance_broken)
                if retest_signal:
                    zone.retest = True
                    zone.right = idx
                    retest_signal.volume_profile = self.get_volume_profile(
                        df.loc[idx - 1, 'volume'],
                        volume_sma.loc[idx - 1]
                    )
                    self.signals.append(retest_signal)
                
                test_signal = self.check_test(df, zone, idx)
                if test_signal:
                    zone.test = True
                    zone.right = idx
                    test_signal.volume_profile = self.get_volume_profile(
                        df.loc[idx - 1, 'volume'],
                        volume_sma.loc[idx - 1]
                    )
                    self.signals.append(test_signal)
                
                # Check liquidity sweep
                if self.check_liquidity_sweep(df, zone, idx):
                    zone.liquidity_sweep = True
                    sweep_signal = LuxAlgoSignal(
                        type='liquidity_sweep',
                        direction='bullish',
                        price=df.loc[idx, 'low'],
                        bar_index=idx,
                        zone=zone
                    )
                    self.signals.append(sweep_signal)
        
        # Return results
        return {
            'support_zones': self.support_zones,
            'resistance_zones': self.resistance_zones,
            'signals': self.signals,
            'market_structure': 'bullish' if self.mss == 1 else 'bearish' if self.mss == -1 else 'neutral',
            'last_pivot_high': self.pivot.h,
            'last_pivot_low': self.pivot.l
        }
