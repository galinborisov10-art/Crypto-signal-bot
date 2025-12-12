"""
🎯 ICT SMART MONEY ZONE (SMZ) MAPPER
Maps institutional accumulation/distribution zones

Identifies:
1. Institutional Order Blocks (IOB)
2. Breaker Blocks
3. Mitigation Blocks
4. Accumulation/Distribution zones
5. FVG clusters + Imbalance zones
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class SmartMoneyZone:
    """Smart Money Zone structure"""
    zone_id: str
    zone_type: str  # 'IOB', 'Breaker', 'Mitigation', 'Accumulation', 'Distribution'
    price_high: float
    price_low: float
    price_center: float
    direction: str  # 'bullish' or 'bearish'
    strength: int  # 0-100
    formed_at: datetime
    still_valid: bool = True
    probability: float = 0.0  # Probability institutions will act here
    explanation: str = ""
    related_fvgs: List[Dict] = None
    
    def __post_init__(self):
        if self.related_fvgs is None:
            self.related_fvgs = []
    
    def to_dict(self) -> Dict:
        return {
            'zone_id': self.zone_id,
            'zone_type': self.zone_type,
            'price_high': self.price_high,
            'price_low': self.price_low,
            'price_center': self.price_center,
            'direction': self.direction,
            'strength': self.strength,
            'formed_at': self.formed_at.isoformat(),
            'still_valid': self.still_valid,
            'probability': self.probability,
            'explanation': self.explanation,
            'related_fvgs': self.related_fvgs
        }


class SMZMapper:
    """
    Smart Money Zone Mapping System
    
    Maps zones where institutions accumulate or distribute:
    - Order Blocks: Last down candle before rally (bullish OB)
    - Breaker Blocks: Order blocks that failed and flipped
    - Mitigation Blocks: Zones that need to be "mitigated" (filled)
    """
    
    def __init__(
        self,
        ob_lookback: int = 20,
        min_ob_body_pct: float = 30,  # Minimum body size as % of range
        fvg_cluster_distance: float = 0.5,  # % distance to cluster FVGs
        accumulation_bars: int = 10
    ):
        self.ob_lookback = ob_lookback
        self.min_ob_body_pct = min_ob_body_pct
        self.fvg_cluster_distance = fvg_cluster_distance
        self.accumulation_bars = accumulation_bars
    
    def detect_order_blocks(self, df: pd.DataFrame) -> List[SmartMoneyZone]:
        """
        Detect Institutional Order Blocks
        
        Bullish OB: Last bearish candle before bullish structure shift
        Bearish OB: Last bullish candle before bearish structure shift
        """
        order_blocks = []
        
        try:
            for i in range(self.ob_lookback, len(df) - 2):
                current = df.iloc[i]
                next_1 = df.iloc[i + 1]
                next_2 = df.iloc[i + 2]
                
                # Calculate body size
                body_size = abs(current['close'] - current['open'])
                full_range = current['high'] - current['low']
                
                if full_range == 0:
                    continue
                
                body_pct = (body_size / full_range) * 100
                
                # Only consider strong candles
                if body_pct < self.min_ob_body_pct:
                    continue
                
                # Bullish Order Block detection
                # Last red candle before strong green move
                if (current['close'] < current['open'] and  # Red candle
                    next_1['close'] > next_1['open'] and    # Green candle
                    next_2['close'] > next_2['open'] and    # Green candle
                    next_2['close'] > current['high']):      # Breaks above OB
                    
                    strength, explanation = self._calculate_ob_strength(
                        df, i, 'bullish', body_pct
                    )
                    
                    ob = SmartMoneyZone(
                        zone_id=f"OB_BULL_{i}",
                        zone_type='IOB',
                        price_high=current['high'],
                        price_low=current['low'],
                        price_center=(current['high'] + current['low']) / 2,
                        direction='bullish',
                        strength=strength,
                        formed_at=df.index[i] if isinstance(df.index, pd.DatetimeIndex) else datetime.now(),
                        still_valid=True,
                        explanation=explanation
                    )
                    
                    order_blocks.append(ob)
                    logger.info(f"🎯 Bullish OB @ {ob.price_center:.2f} (strength: {strength}%)")
                
                # Bearish Order Block detection
                # Last green candle before strong red move
                elif (current['close'] > current['open'] and  # Green candle
                      next_1['close'] < next_1['open'] and    # Red candle
                      next_2['close'] < next_2['open'] and    # Red candle
                      next_2['close'] < current['low']):       # Breaks below OB
                    
                    strength, explanation = self._calculate_ob_strength(
                        df, i, 'bearish', body_pct
                    )
                    
                    ob = SmartMoneyZone(
                        zone_id=f"OB_BEAR_{i}",
                        zone_type='IOB',
                        price_high=current['high'],
                        price_low=current['low'],
                        price_center=(current['high'] + current['low']) / 2,
                        direction='bearish',
                        strength=strength,
                        formed_at=df.index[i] if isinstance(df.index, pd.DatetimeIndex) else datetime.now(),
                        still_valid=True,
                        explanation=explanation
                    )
                    
                    order_blocks.append(ob)
                    logger.info(f"🎯 Bearish OB @ {ob.price_center:.2f} (strength: {strength}%)")
            
            return order_blocks
            
        except Exception as e:
            logger.error(f"Order block detection error: {e}")
            return []
    
    def _calculate_ob_strength(
        self,
        df: pd.DataFrame,
        idx: int,
        direction: str,
        body_pct: float
    ) -> Tuple[int, str]:
        """Calculate Order Block strength"""
        strength = 0
        explanation_parts = []
        
        # Factor 1: Body size (0-30 points)
        body_score = int((body_pct / 100) * 30)
        strength += body_score
        explanation_parts.append(f"Body: {body_pct:.1f}% (+{body_score})")
        
        # Factor 2: Volume (0-25 points)
        if 'volume' in df.columns and idx > 0:
            current_vol = df.iloc[idx]['volume']
            avg_vol = df.iloc[max(0, idx-20):idx]['volume'].mean()
            
            if avg_vol > 0:
                vol_ratio = current_vol / avg_vol
                vol_score = min(25, int(vol_ratio * 10))
                strength += vol_score
                explanation_parts.append(f"Volume: {vol_ratio:.1f}x (+{vol_score})")
        
        # Factor 3: Structure break momentum (0-25 points)
        try:
            next_2 = df.iloc[idx + 2]
            ob_candle = df.iloc[idx]
            
            if direction == 'bullish':
                break_pct = ((next_2['close'] - ob_candle['high']) / ob_candle['high']) * 100
            else:
                break_pct = ((ob_candle['low'] - next_2['close']) / ob_candle['low']) * 100
            
            momentum_score = min(25, int(break_pct * 5))
            strength += momentum_score
            explanation_parts.append(f"Break: {break_pct:.1f}% (+{momentum_score})")
        except:
            pass
        
        # Factor 4: Untested zone bonus (0-20 points)
        # Check if price hasn't returned to OB yet
        try:
            future_prices = df.iloc[idx+3:min(idx+23, len(df))]
            
            if direction == 'bullish':
                has_returned = any(future_prices['low'] <= ob_candle['high'])
            else:
                has_returned = any(future_prices['high'] >= ob_candle['low'])
            
            if not has_returned:
                strength += 20
                explanation_parts.append("Untested (+20)")
        except:
            pass
        
        explanation = " | ".join(explanation_parts)
        return min(100, strength), explanation
    
    def detect_breaker_blocks(
        self,
        df: pd.DataFrame,
        order_blocks: List[SmartMoneyZone]
    ) -> List[SmartMoneyZone]:
        """
        Detect Breaker Blocks - Order Blocks that failed and flipped
        
        Bullish OB becomes Bearish Breaker if price breaks below
        Bearish OB becomes Bullish Breaker if price breaks above
        """
        breakers = []
        
        try:
            for ob in order_blocks:
                # Find OB index in dataframe
                ob_time = ob.formed_at
                
                # Check if OB was broken
                future_data = df[df.index > ob_time] if isinstance(df.index, pd.DatetimeIndex) else df
                
                for idx in range(len(future_data)):
                    candle = future_data.iloc[idx]
                    
                    # Bullish OB broken (becomes Bearish Breaker)
                    if ob.direction == 'bullish' and candle['close'] < ob.price_low:
                        breaker = SmartMoneyZone(
                            zone_id=f"BREAKER_{ob.zone_id}",
                            zone_type='Breaker',
                            price_high=ob.price_high,
                            price_low=ob.price_low,
                            price_center=ob.price_center,
                            direction='bearish',  # Flipped
                            strength=ob.strength,
                            formed_at=datetime.now(),
                            still_valid=True,
                            probability=75.0,
                            explanation=f"Bullish OB flipped to Bearish Breaker"
                        )
                        breakers.append(breaker)
                        logger.info(f"🔄 Breaker Block formed @ {breaker.price_center:.2f}")
                        break
                    
                    # Bearish OB broken (becomes Bullish Breaker)
                    elif ob.direction == 'bearish' and candle['close'] > ob.price_high:
                        breaker = SmartMoneyZone(
                            zone_id=f"BREAKER_{ob.zone_id}",
                            zone_type='Breaker',
                            price_high=ob.price_high,
                            price_low=ob.price_low,
                            price_center=ob.price_center,
                            direction='bullish',  # Flipped
                            strength=ob.strength,
                            formed_at=datetime.now(),
                            still_valid=True,
                            probability=75.0,
                            explanation=f"Bearish OB flipped to Bullish Breaker"
                        )
                        breakers.append(breaker)
                        logger.info(f"🔄 Breaker Block formed @ {breaker.price_center:.2f}")
                        break
            
            return breakers
            
        except Exception as e:
            logger.error(f"Breaker detection error: {e}")
            return []
    
    def detect_accumulation_distribution(self, df: pd.DataFrame) -> List[SmartMoneyZone]:
        """
        Detect Accumulation/Distribution zones
        
        Accumulation: Tight range + low volume → expansion up
        Distribution: Tight range + low volume → expansion down
        """
        zones = []
        
        try:
            for i in range(self.accumulation_bars, len(df) - 5):
                # Get range of bars
                range_data = df.iloc[i:i+self.accumulation_bars]
                
                # Calculate range tightness
                high_max = range_data['high'].max()
                low_min = range_data['low'].min()
                range_size = high_max - low_min
                avg_price = (high_max + low_min) / 2
                range_pct = (range_size / avg_price) * 100
                
                # Tight range = potential accumulation/distribution
                if range_pct < 2.0:  # Less than 2% range
                    # Check volume
                    if 'volume' in df.columns:
                        range_vol = range_data['volume'].mean()
                        prev_vol = df.iloc[max(0, i-20):i]['volume'].mean()
                        
                        if prev_vol > 0 and range_vol < prev_vol * 0.7:  # Low volume
                            # Check for expansion after
                            expansion_data = df.iloc[i+self.accumulation_bars:i+self.accumulation_bars+5]
                            
                            if len(expansion_data) > 0:
                                expansion_move = expansion_data['close'].iloc[-1] - avg_price
                                expansion_pct = (expansion_move / avg_price) * 100
                                
                                # Accumulation if expansion up
                                if expansion_pct > 1.5:
                                    zone = SmartMoneyZone(
                                        zone_id=f"ACCUM_{i}",
                                        zone_type='Accumulation',
                                        price_high=high_max,
                                        price_low=low_min,
                                        price_center=avg_price,
                                        direction='bullish',
                                        strength=70,
                                        formed_at=df.index[i] if isinstance(df.index, pd.DatetimeIndex) else datetime.now(),
                                        still_valid=False,  # Already expanded
                                        probability=0.0,
                                        explanation=f"Accumulation zone: {range_pct:.2f}% range, {expansion_pct:.2f}% expansion"
                                    )
                                    zones.append(zone)
                                    logger.info(f"📈 Accumulation zone @ {zone.price_center:.2f}")
                                
                                # Distribution if expansion down
                                elif expansion_pct < -1.5:
                                    zone = SmartMoneyZone(
                                        zone_id=f"DISTRIB_{i}",
                                        zone_type='Distribution',
                                        price_high=high_max,
                                        price_low=low_min,
                                        price_center=avg_price,
                                        direction='bearish',
                                        strength=70,
                                        formed_at=df.index[i] if isinstance(df.index, pd.DatetimeIndex) else datetime.now(),
                                        still_valid=False,  # Already expanded
                                        probability=0.0,
                                        explanation=f"Distribution zone: {range_pct:.2f}% range, {expansion_pct:.2f}% expansion"
                                    )
                                    zones.append(zone)
                                    logger.info(f"📉 Distribution zone @ {zone.price_center:.2f}")
            
            return zones
            
        except Exception as e:
            logger.error(f"Accumulation/Distribution detection error: {e}")
            return []
    
    def cluster_fvgs(self, fvgs: List[Dict]) -> List[Dict]:
        """
        Cluster Fair Value Gaps that are close together
        
        Creates "imbalance zones" where multiple FVGs exist
        """
        if not fvgs:
            return []
        
        clusters = []
        used_indices = set()
        
        for i, fvg1 in enumerate(fvgs):
            if i in used_indices:
                continue
            
            cluster = [fvg1]
            used_indices.add(i)
            
            for j, fvg2 in enumerate(fvgs[i+1:], start=i+1):
                if j in used_indices:
                    continue
                
                # Check distance
                distance_pct = abs(fvg1['gap_center'] - fvg2['gap_center']) / fvg1['gap_center'] * 100
                
                if distance_pct <= self.fvg_cluster_distance:
                    cluster.append(fvg2)
                    used_indices.add(j)
            
            # Only keep significant clusters
            if len(cluster) >= 2:
                cluster_high = max([fvg['gap_high'] for fvg in cluster])
                cluster_low = min([fvg['gap_low'] for fvg in cluster])
                cluster_center = (cluster_high + cluster_low) / 2
                
                clusters.append({
                    'cluster_high': cluster_high,
                    'cluster_low': cluster_low,
                    'cluster_center': cluster_center,
                    'num_fvgs': len(cluster),
                    'fvgs': cluster
                })
        
        return clusters
    
    def map_all_zones(
        self,
        df: pd.DataFrame,
        fvgs: List[Dict] = None
    ) -> Dict[str, List[SmartMoneyZone]]:
        """
        Main method: Map all Smart Money Zones
        
        Returns: Dict with all zone types
        """
        all_zones = {
            'order_blocks': [],
            'breakers': [],
            'accumulation': [],
            'distribution': [],
            'fvg_clusters': []
        }
        
        try:
            # Detect Order Blocks
            order_blocks = self.detect_order_blocks(df)
            all_zones['order_blocks'] = order_blocks
            
            # Detect Breaker Blocks
            breakers = self.detect_breaker_blocks(df, order_blocks)
            all_zones['breakers'] = breakers
            
            # Detect Accumulation/Distribution
            accum_distrib = self.detect_accumulation_distribution(df)
            
            for zone in accum_distrib:
                if zone.zone_type == 'Accumulation':
                    all_zones['accumulation'].append(zone)
                else:
                    all_zones['distribution'].append(zone)
            
            # Cluster FVGs if provided
            if fvgs:
                fvg_clusters = self.cluster_fvgs(fvgs)
                all_zones['fvg_clusters'] = fvg_clusters
            
            logger.info(f"🎯 Mapped: {len(order_blocks)} OBs, {len(breakers)} Breakers, "
                       f"{len(all_zones['accumulation'])} Accum, {len(all_zones['distribution'])} Distrib")
            
            return all_zones
            
        except Exception as e:
            logger.error(f"Zone mapping error: {e}")
            return all_zones


# Example usage
if __name__ == "__main__":
    sample_data = {
        'open': [100, 102, 101, 99, 98, 103, 105, 104, 106, 108],
        'high': [103, 104, 102, 100, 99, 106, 107, 105, 108, 110],
        'low': [99, 101, 99, 97, 96, 102, 104, 103, 105, 107],
        'close': [102, 101, 99, 98, 97, 105, 106, 104, 107, 109],
        'volume': [1000, 1100, 900, 800, 700, 2000, 1500, 1200, 1300, 1400]
    }
    
    df = pd.DataFrame(sample_data)
    
    mapper = SMZMapper()
    zones = mapper.map_all_zones(df)
    
    print(f"\n🎯 Detected Smart Money Zones:")
    print(f"Order Blocks: {len(zones['order_blocks'])}")
    print(f"Breakers: {len(zones['breakers'])}")
    print(f"Accumulation: {len(zones['accumulation'])}")
    print(f"Distribution: {len(zones['distribution'])}")
