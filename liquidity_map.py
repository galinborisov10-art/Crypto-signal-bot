"""
💧 LIQUIDITY MAP - Advanced Liquidity Visualization System
Maps and tracks all liquidity pools across multiple timeframes

Features:
- 🎯 Buy-Side Liquidity (BSL) detection
- 🎯 Sell-Side Liquidity (SSL) detection
- 💥 Liquidity sweep detection
- 📊 Heatmap generation
- 🔄 Real-time liquidity tracking
- 📈 Historical liquidity patterns
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)


@dataclass
class LiquidityZone:
    """Represents a liquidity accumulation zone"""
    price_level: float
    zone_type: str  # 'BSL' or 'SSL'
    strength: float
    touches: int
    first_touch: datetime
    last_touch: datetime
    volume_at_level: float
    swept: bool = False
    sweep_time: Optional[datetime] = None
    sweep_price: Optional[float] = None
    timeframe: str = '1H'
    confidence: float = 0.0


@dataclass
class LiquiditySweep:
    """Represents a liquidity sweep event"""
    timestamp: datetime
    price: float
    sweep_type: str  # 'BSL_SWEEP' or 'SSL_SWEEP'
    liquidity_zone: LiquidityZone
    strength: float
    fake_breakout: bool
    reversal_candles: int = 0
    volume_spike: float = 0.0


class LiquidityMapper:
    """Advanced Liquidity Mapping System"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or self._get_default_config()
        self.liquidity_zones = []
        self.sweep_events = []
        
    def _get_default_config(self) -> Dict[str, Any]:
        return {
            'touch_threshold': 3,
            'price_tolerance': 0.001,
            'volume_threshold': 1.5,
            'sweep_reversal_candles': 5,
            'min_sweep_strength': 0.6
        }
    
    def detect_liquidity_zones(self, df: pd.DataFrame, timeframe: str = '1H') -> List[LiquidityZone]:
        """Detect all liquidity zones"""
        logger.info(f"Detecting liquidity zones on {timeframe}")
        zones = []
        
        # Detect BSL and SSL zones
        bsl_zones = self._detect_bsl_zones(df, timeframe)
        ssl_zones = self._detect_ssl_zones(df, timeframe)
        zones.extend(bsl_zones)
        zones.extend(ssl_zones)
        
        # Calculate confidence
        zones = self._calculate_zone_confidence(zones, df)
        zones = [z for z in zones if z.confidence >= 0.5]
        
        self.liquidity_zones.extend(zones)
        logger.info(f"Detected {len(zones)} liquidity zones")
        return zones
    
    def _detect_bsl_zones(self, df: pd.DataFrame, timeframe: str) -> List[LiquidityZone]:
        """Detect Buy-Side Liquidity zones"""
        zones = []
        tolerance = df['close'].mean() * self.config['price_tolerance']
        swing_highs = self._find_swing_highs(df)
        clustered = self._cluster_price_levels(swing_highs, tolerance)
        
        for cluster in clustered:
            if len(cluster['indices']) >= self.config['touch_threshold']:
                times = [df.index[i] for i in cluster['indices']]
                volumes = [df['volume'].iloc[i] for i in cluster['indices']]
                
                zone = LiquidityZone(
                    price_level=cluster['price'],
                    zone_type='BSL',
                    strength=len(cluster['indices']) / self.config['touch_threshold'],
                    touches=len(cluster['indices']),
                    first_touch=min(times),
                    last_touch=max(times),
                    volume_at_level=sum(volumes),
                    timeframe=timeframe
                )
                zones.append(zone)
        
        return zones
    
    def _detect_ssl_zones(self, df: pd.DataFrame, timeframe: str) -> List[LiquidityZone]:
        """Detect Sell-Side Liquidity zones"""
        zones = []
        tolerance = df['close'].mean() * self.config['price_tolerance']
        swing_lows = self._find_swing_lows(df)
        clustered = self._cluster_price_levels(swing_lows, tolerance)
        
        for cluster in clustered:
            if len(cluster['indices']) >= self.config['touch_threshold']:
                times = [df.index[i] for i in cluster['indices']]
                volumes = [df['volume'].iloc[i] for i in cluster['indices']]
                
                zone = LiquidityZone(
                    price_level=cluster['price'],
                    zone_type='SSL',
                    strength=len(cluster['indices']) / self.config['touch_threshold'],
                    touches=len(cluster['indices']),
                    first_touch=min(times),
                    last_touch=max(times),
                    volume_at_level=sum(volumes),
                    timeframe=timeframe
                )
                zones.append(zone)
        
        return zones
    
    def _find_swing_highs(self, df: pd.DataFrame, window: int = 5) -> List[Tuple[int, float]]:
        """Find swing high points"""
        swing_highs = []
        for i in range(window, len(df) - window):
            if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                swing_highs.append((i, df['high'].iloc[i]))
        return swing_highs
    
    def _find_swing_lows(self, df: pd.DataFrame, window: int = 5) -> List[Tuple[int, float]]:
        """Find swing low points"""
        swing_lows = []
        for i in range(window, len(df) - window):
            if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                swing_lows.append((i, df['low'].iloc[i]))
        return swing_lows
    
    def _cluster_price_levels(self, swing_points: List[Tuple[int, float]], tolerance: float) -> List[Dict]:
        """Cluster similar price levels"""
        if not swing_points:
            return []
        
        clusters = []
        used = set()
        
        for i, (idx1, price1) in enumerate(swing_points):
            if i in used:
                continue
            
            cluster = {'price': price1, 'indices': [idx1], 'prices': [price1]}
            used.add(i)
            
            for j, (idx2, price2) in enumerate(swing_points[i+1:], i+1):
                if j not in used and abs(price1 - price2) <= tolerance:
                    cluster['indices'].append(idx2)
                    cluster['prices'].append(price2)
                    used.add(j)
            
            cluster['price'] = np.mean(cluster['prices'])
            clusters.append(cluster)
        
        return clusters
    
    def _calculate_zone_confidence(self, zones: List[LiquidityZone], df: pd.DataFrame) -> List[LiquidityZone]:
        """Calculate confidence score for each zone"""
        if not zones:
            return zones
        
        volume_mean = df['volume'].mean()
        
        for zone in zones:
            score = 0.0
            score += min(zone.touches / 10, 0.4)
            score += min(zone.volume_at_level / (volume_mean * zone.touches * 2), 0.3)
            score += zone.strength * 0.2
            
            days_ago = (df.index[-1] - zone.last_touch).days
            score += max(0, 0.1 - (days_ago / 30) * 0.1)
            
            zone.confidence = min(score, 1.0)
        
        return zones
    
    def detect_liquidity_sweeps(self, df: pd.DataFrame, zones: Optional[List[LiquidityZone]] = None) -> List[LiquiditySweep]:
        """Detect liquidity sweep events"""
        if zones is None:
            zones = self.liquidity_zones
        
        sweeps = []
        volume_ma = df['volume'].rolling(20).mean()
        
        for i in range(20, len(df)):
            current_high = df['high'].iloc[i]
            current_low = df['low'].iloc[i]
            current_close = df['close'].iloc[i]
            current_volume = df['volume'].iloc[i]
            
            for zone in zones:
                if zone.zone_type == 'BSL' and not zone.swept:
                    if current_high > zone.price_level and current_close < zone.price_level:
                        fake_breakout = self._check_fake_breakout(df, i, zone.price_level, 'BSL')
                        
                        if fake_breakout:
                            sweep = LiquiditySweep(
                                timestamp=df.index[i],
                                price=current_high,
                                sweep_type='BSL_SWEEP',
                                liquidity_zone=zone,
                                strength=self._calculate_sweep_strength(df, i, zone),
                                fake_breakout=True,
                                reversal_candles=self._count_reversal_candles(df, i, 'down'),
                                volume_spike=current_volume / volume_ma.iloc[i] if volume_ma.iloc[i] > 0 else 1.0
                            )
                            sweeps.append(sweep)
                            zone.swept = True
                
                elif zone.zone_type == 'SSL' and not zone.swept:
                    if current_low < zone.price_level and current_close > zone.price_level:
                        fake_breakout = self._check_fake_breakout(df, i, zone.price_level, 'SSL')
                        
                        if fake_breakout:
                            sweep = LiquiditySweep(
                                timestamp=df.index[i],
                                price=current_low,
                                sweep_type='SSL_SWEEP',
                                liquidity_zone=zone,
                                strength=self._calculate_sweep_strength(df, i, zone),
                                fake_breakout=True,
                                reversal_candles=self._count_reversal_candles(df, i, 'up'),
                                volume_spike=current_volume / volume_ma.iloc[i] if volume_ma.iloc[i] > 0 else 1.0
                            )
                            sweeps.append(sweep)
                            zone.swept = True
        
        self.sweep_events.extend(sweeps)
        return sweeps
    
    def _check_fake_breakout(self, df: pd.DataFrame, index: int, level: float, sweep_type: str) -> bool:
        """Check if breakout is fake"""
        if index + self.config['sweep_reversal_candles'] >= len(df):
            return False
        
        next_candles = df.iloc[index+1:index+1+self.config['sweep_reversal_candles']]
        
        if sweep_type == 'BSL':
            bearish_count = sum(next_candles['close'] < next_candles['open'])
            return bearish_count >= self.config['sweep_reversal_candles'] * 0.6
        elif sweep_type == 'SSL':
            bullish_count = sum(next_candles['close'] > next_candles['open'])
            return bullish_count >= self.config['sweep_reversal_candles'] * 0.6
        
        return False
    
    def _calculate_sweep_strength(self, df: pd.DataFrame, index: int, zone: LiquidityZone) -> float:
        """Calculate sweep strength"""
        strength = zone.confidence * 0.4
        volume_ma = df['volume'].iloc[max(0, index-20):index].mean()
        
        if volume_ma > 0:
            volume_ratio = df['volume'].iloc[index] / volume_ma
            strength += min(volume_ratio / 3, 0.3)
        
        return min(strength, 1.0)
    
    def _count_reversal_candles(self, df: pd.DataFrame, index: int, direction: str) -> int:
        """Count reversal candles"""
        count = 0
        max_candles = min(10, len(df) - index - 1)
        
        for i in range(index + 1, index + 1 + max_candles):
            if direction == 'up' and df['close'].iloc[i] > df['open'].iloc[i]:
                count += 1
            elif direction == 'down' and df['close'].iloc[i] < df['open'].iloc[i]:
                count += 1
            else:
                break
        
        return count


if __name__ == "__main__":
    print("Liquidity Mapper ready!")