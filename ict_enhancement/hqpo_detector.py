"""
HQPO (High Quality Premium/Discount Orders) Detector
"""

import logging
import pandas as pd
from typing import List, Dict

logger = logging.getLogger(__name__)

class HQPODetector:
    """Detects HQPO zones (Whale blocks without wicks)"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.min_body_wick_ratio = 0.1
        self.min_volume_ratio = 1.5
        self.lookback_candles = 50
    
    def detect(self, df: pd.DataFrame) -> List[Dict]:
        """Detect HQPO zones in dataframe"""
        hqpo_zones = []
        
        if len(df) < 20:
            return hqpo_zones
        
        avg_volume = df['volume'].rolling(window=20).mean()
        start_idx = max(10, len(df) - self.lookback_candles)
        
        for i in range(start_idx, len(df) - 1):
            candle = df.iloc[i]
            next_candle = df.iloc[i + 1]
            
            bullish = self._check_bullish_hqpo(candle, next_candle, avg_volume.iloc[i])
            if bullish:
                hqpo_zones.append({
                    'type': 'BULLISH_HQPO',
                    'index': i,
                    'price_low': float(candle['low']),
                    'price_high': float(candle['high']),
                    'strength': bullish['strength'],
                    'volume_ratio': bullish['volume_ratio']
                })
            
            bearish = self._check_bearish_hqpo(candle, next_candle, avg_volume.iloc[i])
            if bearish:
                hqpo_zones.append({
                    'type': 'BEARISH_HQPO',
                    'index': i,
                    'price_low': float(candle['low']),
                    'price_high': float(candle['high']),
                    'strength': bearish['strength'],
                    'volume_ratio': bearish['volume_ratio']
                })
        
        logger.info(f"HQPO: Found {len(hqpo_zones)} zones")
        return hqpo_zones
    
    def _check_bullish_hqpo(self, candle, next_candle, avg_volume):
        """Check Bullish HQPO"""
        if candle['close'] >= candle['open']:
            return None
        
        body = candle['open'] - candle['close']
        wick = candle['close'] - candle['low']
        
        if body == 0:
            return None
        
        ratio = wick / body
        if ratio > self.min_body_wick_ratio:
            return None
        
        has_gap = next_candle['low'] > candle['high']
        vol_ratio = candle['volume'] / avg_volume if avg_volume > 0 else 0
        
        strength = 0.5
        if ratio < 0.05:
            strength += 0.2
        if has_gap:
            strength += 0.2
        if vol_ratio > self.min_volume_ratio:
            strength += 0.1
        
        if ratio < self.min_body_wick_ratio or has_gap or vol_ratio > self.min_volume_ratio:
            return {'strength': min(strength, 1.0), 'volume_ratio': float(vol_ratio)}
        return None
    
    def _check_bearish_hqpo(self, candle, next_candle, avg_volume):
        """Check Bearish HQPO"""
        if candle['close'] <= candle['open']:
            return None
        
        body = candle['close'] - candle['open']
        wick = candle['high'] - candle['close']
        
        if body == 0:
            return None
        
        ratio = wick / body
        if ratio > self.min_body_wick_ratio:
            return None
        
        has_gap = next_candle['high'] < candle['low']
        vol_ratio = candle['volume'] / avg_volume if avg_volume > 0 else 0
        
        strength = 0.5
        if ratio < 0.05:
            strength += 0.2
        if has_gap:
            strength += 0.2
        if vol_ratio > self.min_volume_ratio:
            strength += 0.1
        
        if ratio < self.min_body_wick_ratio or has_gap or vol_ratio > self.min_volume_ratio:
            return {'strength': min(strength, 1.0), 'volume_ratio': float(vol_ratio)}
        return None
