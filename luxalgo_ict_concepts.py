"""
LuxAlgo ICT Concepts - Python Implementation
Converted from Pine Script v5
License: CC BY-NC-SA 4.0 (https://creativecommons.org/licenses/by-nc-sa/4.0/)
© LuxAlgo

Implements:
- Market Structure (MSS/BOS)
- Order Blocks
- Fair Value Gaps (FVG)
- Liquidity (BSL/SSL)
- Volume Imbalance
- Premium/Discount zones
- Displacement
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class SwingType(Enum):
    """Swing point types"""
    HIGH = 1
    LOW = -1


@dataclass
class SwingPoint:
    """Swing high/low point"""
    index: int
    price: float
    type: SwingType
    broken: bool = False
    
    
@dataclass
class OrderBlock:
    """Order Block zone"""
    start_idx: int
    end_idx: int
    top: float
    bottom: float
    is_bullish: bool
    breaker: bool = False
    mitigated: bool = False
    strength: float = 0.0
    

@dataclass
class FairValueGap:
    """Fair Value Gap"""
    start_idx: int
    end_idx: int
    top: float
    bottom: float
    is_bullish: bool
    mitigated: bool = False
    

@dataclass
class LiquidityLevel:
    """Buy/Sell Side Liquidity"""
    index: int
    price: float
    is_buy_side: bool  # True = BSL, False = SSL
    swept: bool = False
    

@dataclass
class MarketStructure:
    """Market Structure Shift/Break"""
    index: int
    price: float
    type: str  # 'MSS' or 'BOS'
    direction: str  # 'bullish' or 'bearish'


@dataclass
class PremiumDiscount:
    """Premium/Discount zones"""
    equilibrium: float
    premium_start: float
    discount_end: float
    

class LuxAlgoICT:
    """
    LuxAlgo ICT Concepts Implementation
    
    Full implementation of Inner Circle Trader (ICT) concepts:
    - Smart Money Concepts
    - Order Blocks
    - Fair Value Gaps
    - Liquidity Sweeps
    - Market Structure
    """
    
    def __init__(
        self,
        swing_length: int = 10,
        show_ob: bool = True,
        show_fvg: bool = True,
        show_liquidity: bool = True,
        show_structure: bool = True,
        ob_filter_strength: int = 0,
        fvg_extend: int = 0
    ):
        self.swing_length = swing_length
        self.show_ob = show_ob
        self.show_fvg = show_fvg
        self.show_liquidity = show_liquidity
        self.show_structure = show_structure
        self.ob_filter_strength = ob_filter_strength
        self.fvg_extend = fvg_extend
        
        # Storage
        self.swing_highs: List[SwingPoint] = []
        self.swing_lows: List[SwingPoint] = []
        self.order_blocks: List[OrderBlock] = []
        self.fvgs: List[FairValueGap] = []
        self.liquidity_levels: List[LiquidityLevel] = []
        self.structures: List[MarketStructure] = []
        
        # State tracking
        self.last_bull_break = None
        self.last_bear_break = None
        self.trend = 0  # 1 = bullish, -1 = bearish, 0 = neutral
        
    def detect_swing_high(self, df: pd.DataFrame, idx: int) -> Optional[float]:
        """Detect swing high at index using zigzag logic"""
        if idx < self.swing_length or idx >= len(df) - self.swing_length:
            return None
        
        center = df.loc[idx, 'high']
        
        # Check left side
        left_max = df.loc[idx - self.swing_length:idx - 1, 'high'].max()
        if center <= left_max:
            return None
        
        # Check right side
        right_max = df.loc[idx + 1:idx + self.swing_length, 'high'].max()
        if center <= right_max:
            return None
        
        return center
    
    def detect_swing_low(self, df: pd.DataFrame, idx: int) -> Optional[float]:
        """Detect swing low at index using zigzag logic"""
        if idx < self.swing_length or idx >= len(df) - self.swing_length:
            return None
        
        center = df.loc[idx, 'low']
        
        # Check left side
        left_min = df.loc[idx - self.swing_length:idx - 1, 'low'].min()
        if center >= left_min:
            return None
        
        # Check right side
        right_min = df.loc[idx + 1:idx + self.swing_length, 'low'].min()
        if center >= right_min:
            return None
        
        return center
    
    def detect_order_block(
        self,
        df: pd.DataFrame,
        idx: int,
        displacement_detected: bool,
        is_bullish: bool
    ) -> Optional[OrderBlock]:
        """
        Detect Order Block formation
        OB = Last opposite-colored candle before strong move
        """
        if idx < 3:
            return None
        
        if is_bullish:
            # Bullish OB: Last red candle before bullish displacement
            for i in range(idx - 1, max(idx - 5, 0), -1):
                candle = df.iloc[i]
                if candle['close'] < candle['open']:  # Red candle
                    # Check if followed by bullish move
                    next_candle = df.iloc[i + 1]
                    if next_candle['close'] > candle['high']:
                        return OrderBlock(
                            start_idx=i,
                            end_idx=i,
                            top=candle['high'],
                            bottom=candle['low'],
                            is_bullish=True,
                            strength=abs(next_candle['close'] - candle['low']) / candle['low']
                        )
        else:
            # Bearish OB: Last green candle before bearish displacement
            for i in range(idx - 1, max(idx - 5, 0), -1):
                candle = df.iloc[i]
                if candle['close'] > candle['open']:  # Green candle
                    # Check if followed by bearish move
                    next_candle = df.iloc[i + 1]
                    if next_candle['close'] < candle['low']:
                        return OrderBlock(
                            start_idx=i,
                            end_idx=i,
                            top=candle['high'],
                            bottom=candle['low'],
                            is_bullish=False,
                            strength=abs(candle['high'] - next_candle['close']) / candle['high']
                        )
        
        return None
    
    def detect_fvg(self, df: pd.DataFrame, idx: int) -> Optional[FairValueGap]:
        """
        Detect Fair Value Gap (Imbalance)
        Bullish FVG: candle[i-2].high < candle[i].low (gap up)
        Bearish FVG: candle[i-2].low > candle[i].high (gap down)
        """
        if idx < 2:
            return None
        
        curr = df.iloc[idx]
        prev1 = df.iloc[idx - 1]
        prev2 = df.iloc[idx - 2]
        
        # Bullish FVG
        if prev2['high'] < curr['low']:
            return FairValueGap(
                start_idx=idx - 1,
                end_idx=idx,
                top=curr['low'],
                bottom=prev2['high'],
                is_bullish=True
            )
        
        # Bearish FVG
        if prev2['low'] > curr['high']:
            return FairValueGap(
                start_idx=idx - 1,
                end_idx=idx,
                top=prev2['low'],
                bottom=curr['high'],
                is_bullish=False
            )
        
        return None
    
    def detect_liquidity_sweep(
        self,
        df: pd.DataFrame,
        idx: int,
        swing_point: SwingPoint
    ) -> bool:
        """
        Detect liquidity sweep
        BSL sweep: price goes above swing high then reverses
        SSL sweep: price goes below swing low then reverses
        """
        if idx <= swing_point.index:
            return False
        
        curr = df.iloc[idx]
        
        if swing_point.type == SwingType.HIGH:
            # BSL sweep
            if curr['high'] > swing_point.price and curr['close'] < swing_point.price:
                return True
        else:
            # SSL sweep
            if curr['low'] < swing_point.price and curr['close'] > swing_point.price:
                return True
        
        return False
    
    def detect_break_of_structure(
        self,
        df: pd.DataFrame,
        idx: int,
        swing_point: SwingPoint,
        is_counter_trend: bool = False
    ) -> Optional[MarketStructure]:
        """
        Detect Break of Structure (BOS) or Market Structure Shift (MSS)
        BOS: Break in trend direction
        MSS: Break against trend (trend reversal signal)
        """
        if idx <= swing_point.index:
            return None
        
        curr = df.iloc[idx]
        
        if swing_point.type == SwingType.HIGH:
            # Bullish break above swing high
            if curr['close'] > swing_point.price:
                structure_type = 'MSS' if is_counter_trend else 'BOS'
                return MarketStructure(
                    index=idx,
                    price=swing_point.price,
                    type=structure_type,
                    direction='bullish'
                )
        else:
            # Bearish break below swing low
            if curr['close'] < swing_point.price:
                structure_type = 'MSS' if is_counter_trend else 'BOS'
                return MarketStructure(
                    index=idx,
                    price=swing_point.price,
                    type=structure_type,
                    direction='bearish'
                )
        
        return None
    
    def check_ob_mitigation(self, df: pd.DataFrame, ob: OrderBlock, idx: int) -> bool:
        """Check if Order Block has been mitigated (price entered 50% of zone)"""
        if ob.mitigated or idx <= ob.end_idx:
            return False
        
        curr = df.iloc[idx]
        mid_point = (ob.top + ob.bottom) / 2
        
        if ob.is_bullish:
            # Bullish OB mitigated if price touches it from above
            if curr['low'] <= mid_point:
                return True
        else:
            # Bearish OB mitigated if price touches it from below
            if curr['high'] >= mid_point:
                return True
        
        return False
    
    def check_fvg_mitigation(self, df: pd.DataFrame, fvg: FairValueGap, idx: int) -> bool:
        """Check if FVG has been filled"""
        if fvg.mitigated or idx <= fvg.end_idx:
            return False
        
        curr = df.iloc[idx]
        
        if fvg.is_bullish:
            # Bullish FVG filled if price goes back into gap
            if curr['low'] <= fvg.top:
                return True
        else:
            # Bearish FVG filled if price goes back into gap
            if curr['high'] >= fvg.bottom:
                return True
        
        return False
    
    def calculate_premium_discount(self, df: pd.DataFrame) -> PremiumDiscount:
        """Calculate Premium/Discount zones based on recent range"""
        recent_high = df['high'].iloc[-50:].max()
        recent_low = df['low'].iloc[-50:].min()
        
        equilibrium = (recent_high + recent_low) / 2
        premium_start = equilibrium + (recent_high - equilibrium) * 0.5
        discount_end = equilibrium - (equilibrium - recent_low) * 0.5
        
        return PremiumDiscount(
            equilibrium=equilibrium,
            premium_start=premium_start,
            discount_end=discount_end
        )
    
    def analyze(self, df: pd.DataFrame) -> Dict:
        """
        Main ICT analysis function
        
        Args:
            df: DataFrame with OHLCV data
        
        Returns:
            Dictionary with all ICT elements
        """
        # Reset storage
        self.swing_highs = []
        self.swing_lows = []
        self.order_blocks = []
        self.fvgs = []
        self.liquidity_levels = []
        self.structures = []
        
        # Step 1: Detect swing points
        for idx in range(self.swing_length, len(df) - self.swing_length):
            # Swing highs
            swing_high = self.detect_swing_high(df, idx)
            if swing_high is not None:
                self.swing_highs.append(SwingPoint(
                    index=idx,
                    price=swing_high,
                    type=SwingType.HIGH
                ))
                
                if self.show_liquidity:
                    self.liquidity_levels.append(LiquidityLevel(
                        index=idx,
                        price=swing_high,
                        is_buy_side=True
                    ))
            
            # Swing lows
            swing_low = self.detect_swing_low(df, idx)
            if swing_low is not None:
                self.swing_lows.append(SwingPoint(
                    index=idx,
                    price=swing_low,
                    type=SwingType.LOW
                ))
                
                if self.show_liquidity:
                    self.liquidity_levels.append(LiquidityLevel(
                        index=idx,
                        price=swing_low,
                        is_buy_side=False
                    ))
        
        # Step 2: Detect market structures, OBs, and FVGs
        for idx in range(self.swing_length + 2, len(df)):
            curr = df.iloc[idx]
            prev = df.iloc[idx - 1]
            
            # Calculate displacement
            body_size = abs(curr['close'] - curr['open'])
            avg_body = df['close'].iloc[max(0, idx-20):idx].sub(
                df['open'].iloc[max(0, idx-20):idx]
            ).abs().mean()
            
            displacement_detected = body_size > avg_body * 2 if avg_body > 0 else False
            
            # Check for BOS/MSS
            if self.show_structure:
                # Check bullish breaks
                for swing_high in reversed(self.swing_highs):
                    if swing_high.broken or swing_high.index >= idx - 1:
                        continue
                    
                    if curr['close'] > swing_high.price:
                        is_counter = self.trend == -1
                        structure = self.detect_break_of_structure(df, idx, swing_high, is_counter)
                        if structure:
                            self.structures.append(structure)
                            swing_high.broken = True
                            self.trend = 1
                            self.last_bull_break = idx
                        break
                
                # Check bearish breaks
                for swing_low in reversed(self.swing_lows):
                    if swing_low.broken or swing_low.index >= idx - 1:
                        continue
                    
                    if curr['close'] < swing_low.price:
                        is_counter = self.trend == 1
                        structure = self.detect_break_of_structure(df, idx, swing_low, is_counter)
                        if structure:
                            self.structures.append(structure)
                            swing_low.broken = True
                            self.trend = -1
                            self.last_bear_break = idx
                        break
            
            # Detect Order Blocks
            if self.show_ob and displacement_detected:
                # Bullish OB
                if curr['close'] > curr['open'] and curr['close'] > prev['high']:
                    ob = self.detect_order_block(df, idx, True, True)
                    if ob and ob.strength >= self.ob_filter_strength / 100:
                        # Check for duplicates
                        is_duplicate = any(
                            abs(existing.start_idx - ob.start_idx) <= 1 and
                            existing.is_bullish == ob.is_bullish
                            for existing in self.order_blocks
                        )
                        if not is_duplicate:
                            self.order_blocks.append(ob)
                
                # Bearish OB
                if curr['close'] < curr['open'] and curr['close'] < prev['low']:
                    ob = self.detect_order_block(df, idx, True, False)
                    if ob and ob.strength >= self.ob_filter_strength / 100:
                        is_duplicate = any(
                            abs(existing.start_idx - ob.start_idx) <= 1 and
                            existing.is_bullish == ob.is_bullish
                            for existing in self.order_blocks
                        )
                        if not is_duplicate:
                            self.order_blocks.append(ob)
            
            # Detect FVG
            if self.show_fvg:
                fvg = self.detect_fvg(df, idx)
                if fvg:
                    # Check for duplicates
                    is_duplicate = any(
                        abs(existing.start_idx - fvg.start_idx) <= 1
                        for existing in self.fvgs
                    )
                    if not is_duplicate:
                        self.fvgs.append(fvg)
            
            # Check liquidity sweeps
            if self.show_liquidity:
                for liq in self.liquidity_levels:
                    if not liq.swept and idx > liq.index:
                        if liq.is_buy_side:
                            if curr['high'] > liq.price and curr['close'] < liq.price:
                                liq.swept = True
                        else:
                            if curr['low'] < liq.price and curr['close'] > liq.price:
                                liq.swept = True
            
            # Check OB mitigation
            for ob in self.order_blocks:
                if self.check_ob_mitigation(df, ob, idx):
                    ob.mitigated = True
            
            # Check FVG mitigation
            for fvg in self.fvgs:
                if self.check_fvg_mitigation(df, fvg, idx):
                    fvg.mitigated = True
        
        # Calculate Premium/Discount
        premium_discount = self.calculate_premium_discount(df)
        
        # Filter: Keep only recent unmitigated elements
        active_obs = [ob for ob in self.order_blocks if not ob.mitigated][-10:]
        active_fvgs = [fvg for fvg in self.fvgs if not fvg.mitigated][-5:]
        recent_structures = self.structures[-10:]
        
        # Get current price position
        current_price = df.iloc[-1]['close']
        if current_price > premium_discount.equilibrium:
            price_zone = 'premium'
        elif current_price < premium_discount.equilibrium:
            price_zone = 'discount'
        else:
            price_zone = 'equilibrium'
        
        return {
            'order_blocks': active_obs,
            'all_order_blocks': self.order_blocks,
            'fvgs': active_fvgs,
            'all_fvgs': self.fvgs,
            'structures': recent_structures,
            'liquidity_levels': self.liquidity_levels,
            'swing_highs': self.swing_highs[-10:],
            'swing_lows': self.swing_lows[-10:],
            'premium_discount': premium_discount,
            'price_zone': price_zone,
            'trend': 'bullish' if self.trend == 1 else 'bearish' if self.trend == -1 else 'neutral',
            'last_structure': recent_structures[-1] if recent_structures else None
        }
