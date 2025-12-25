"""
Multi-Timeframe Analyzer for ICT Trading Strategy
Implements comprehensive 1D/4H/1H analysis with HTF bias, MTF structure, and LTF entries
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Bias(Enum):
    """Market bias enumeration"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    RANGING = "RANGING"


class StructureType(Enum):
    """Market structure types"""
    BOS = "BOS"  # Break of Structure
    CHOCH = "CHOCH"  # Change of Character
    HH = "HH"  # Higher High
    HL = "HL"  # Higher Low
    LH = "LH"  # Lower High
    LL = "LL"  # Lower Low


class OrderBlockType(Enum):
    """Order block classifications"""
    BULLISH_OB = "BULLISH_OB"
    BEARISH_OB = "BEARISH_OB"
    BREAKER = "BREAKER"
    MITIGATION = "MITIGATION"


class FVGType(Enum):
    """Fair Value Gap types"""
    BULLISH_FVG = "BULLISH_FVG"
    BEARISH_FVG = "BEARISH_FVG"
    BALANCED = "BALANCED"


@dataclass
class SwingPoint:
    """Represents a swing high or low"""
    index: int
    price: float
    timestamp: datetime
    is_high: bool
    strength: int = 1
    mitigated: bool = False


@dataclass
class OrderBlock:
    """Order Block structure"""
    start_idx: int
    end_idx: int
    high: float
    low: float
    type: OrderBlockType
    timestamp: datetime
    strength: float = 1.0
    tested: bool = False
    mitigated: bool = False
    volume: float = 0.0


@dataclass
class FairValueGap:
    """Fair Value Gap structure"""
    start_idx: int
    end_idx: int
    top: float
    bottom: float
    type: FVGType
    timestamp: datetime
    filled: bool = False
    fill_percentage: float = 0.0


@dataclass
class LiquidityPool:
    """Liquidity zone structure"""
    price: float
    timestamp: datetime
    type: str  # 'BSL' (Buy Side) or 'SSL' (Sell Side)
    strength: float = 1.0
    swept: bool = False
    touches: int = 1


@dataclass
class StructureBreak:
    """Structure break event"""
    index: int
    price: float
    timestamp: datetime
    type: StructureType
    timeframe: str
    previous_level: float
    strength: float = 1.0


@dataclass
class MTFSignal:
    """Multi-timeframe trading signal"""
    timestamp: datetime
    symbol: str
    direction: str  # 'LONG' or 'SHORT'
    entry_price: float
    stop_loss: float
    take_profit: List[float]
    htf_bias: Bias
    mtf_structure: str
    ltf_trigger: str
    confidence: float
    risk_reward: float
    alignment_score: float
    order_blocks: List[OrderBlock] = field(default_factory=list)
    fvgs: List[FairValueGap] = field(default_factory=list)
    liquidity_targets: List[LiquidityPool] = field(default_factory=list)
    notes: str = ""


class MultiTimeframeAnalyzer:
    """
    Comprehensive Multi-Timeframe ICT Analysis System
    Analyzes market structure across 1D, 4H, and 1H timeframes
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the MTF Analyzer
        
        Args:
            config: Configuration dictionary with analysis parameters
        """
        self.config = config or self._get_default_config()
        self.htf_data = {}  # 1D data
        self.mtf_data = {}  # 4H data
        self.ltf_data = {}  # 1H data
        
        # Structure storage
        self.htf_bias = Bias.NEUTRAL
        self.mtf_bias = Bias.NEUTRAL
        self.structure_breaks = []
        self.order_blocks = []
        self.fvgs = []
        self.liquidity_pools = []
        self.swing_points = {'1D': [], '4H': [], '1H': []}
        
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'swing_lookback': 10,
            'structure_lookback': 50,
            'ob_strength_threshold': 0.6,
            'fvg_min_size': 0.001,  # 0.1%
            'liquidity_threshold': 3,
            'alignment_threshold': 0.7,
            'min_confidence': 0.65,
            'risk_reward_min': 2.0,
            'atr_period': 14,
            'volume_ma_period': 20,
            'htf_timeframe': '1D',
            'mtf_timeframe': '4H',
            'ltf_timeframe': '1H'
        }
    
    def analyze_multi_timeframe(self, htf_df: pd.DataFrame, mtf_df: pd.DataFrame, 
                                ltf_df: pd.DataFrame, symbol: str) -> List[MTFSignal]:
        """
        Perform complete multi-timeframe analysis
        
        Args:
            htf_df: Higher timeframe (1D) data
            mtf_df: Medium timeframe (4H) data
            ltf_df: Lower timeframe (1H) data
            symbol: Trading pair symbol
            
        Returns:
            List of MTF trading signals
        """
        logger.info(f"Starting MTF analysis for {symbol}")
        
        # Store data
        self.htf_data = self._prepare_dataframe(htf_df)
        self.mtf_data = self._prepare_dataframe(mtf_df)
        self.ltf_data = self._prepare_dataframe(ltf_df)
        
        # Step 1: HTF Bias Detection (1D)
        self.htf_bias = self._detect_htf_bias(self.htf_data, '1D')
        logger.info(f"HTF Bias: {self.htf_bias.value}")
        
        # Step 2: MTF Structure Analysis (4H)
        self.mtf_bias = self._analyze_mtf_structure(self.mtf_data, '4H')
        logger.info(f"MTF Bias: {self.mtf_bias.value}")
        
        # Step 3: Identify key structures across timeframes
        self._identify_swing_points(self.htf_data, '1D')
        self._identify_swing_points(self.mtf_data, '4H')
        self._identify_swing_points(self.ltf_data, '1H')
        
        # Step 4: Detect BOS/CHOCH
        self._detect_structure_breaks(self.mtf_data, '4H')
        self._detect_structure_breaks(self.ltf_data, '1H')
        
        # Step 5: Identify order blocks
        self._identify_order_blocks(self.mtf_data, '4H')
        self._identify_order_blocks(self.ltf_data, '1H')
        
        # Step 6: Find Fair Value Gaps
        self._identify_fvgs(self.mtf_data, '4H')
        self._identify_fvgs(self.ltf_data, '1H')
        
        # Step 7: Map liquidity pools
        self._identify_liquidity_pools(self.htf_data, '1D')
        self._identify_liquidity_pools(self.mtf_data, '4H')
        
        # Step 8: Generate LTF entry signals
        signals = self._generate_ltf_signals(symbol)
        
        logger.info(f"Generated {len(signals)} signals for {symbol}")
        return signals
    
    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare and enrich dataframe with indicators"""
        df = df.copy()
        
        # Ensure datetime index
        if 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
        
        # Calculate ATR
        df['atr'] = self._calculate_atr(df, self.config['atr_period'])
        
        # Calculate volume metrics
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(
                window=self.config['volume_ma_period']
            ).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma']
        else:
            df['volume'] = 0
            df['volume_ma'] = 0
            df['volume_ratio'] = 1
        
        # Price range
        df['range'] = df['high'] - df['low']
        df['body'] = abs(df['close'] - df['open'])
        df['body_ratio'] = df['body'] / df['range']
        
        return df
    
    def _calculate_atr(self, df: pd.DataFrame, period: int) -> pd.Series:
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
    
    def _detect_htf_bias(self, df: pd.DataFrame, timeframe: str) -> Bias:
        """
        ✅ PURE ICT HTF Bias Detection - NO EMA/MA!
        
        Uses:
        - Market structure (HH/HL vs LH/LL) - 60% weight
        - Order Blocks - 30% weight
        - Displacement - 10% weight
        
        Args:
            df: DataFrame with OHLCV data
            timeframe: Timeframe string
            
        Returns:
            Bias enum (BULLISH/BEARISH/RANGING/NEUTRAL)
        """
        if len(df) < 50:
            return Bias.NEUTRAL
        
        bullish_score = 0
        bearish_score = 0
        max_score = 100
        
        # ═══════════════════════════════════════════════════════════
        # 1. MARKET STRUCTURE (60 points)
        # ═══════════════════════════════════════════════════════════
        swings = self._find_swing_points(df, self.config['swing_lookback'])
        structure_bias = self._analyze_structure_bias(swings)
        
        if structure_bias == Bias.BULLISH:
            bullish_score += 60
        elif structure_bias == Bias.BEARISH:
            bearish_score += 60
        
        # ═══════════════════════════════════════════════════════════
        # 2. ORDER BLOCKS (30 points)
        # ═══════════════════════════════════════════════════════════
        try:
            bullish_obs = 0
            bearish_obs = 0
            
            # Analyze last 20 candles for order block patterns
            for i in range(len(df) - 20, len(df) - 1):
                if i < 1:
                    continue
                
                candle = df.iloc[i]
                next_candle = df.iloc[i + 1]
                
                # Bullish OB: Down candle + break of high
                if candle['close'] < candle['open']:
                    if next_candle['close'] > candle['high']:
                        bullish_obs += 1
                
                # Bearish OB: Up candle + break of low
                if candle['close'] > candle['open']:
                    if next_candle['close'] < candle['low']:
                        bearish_obs += 1
            
            if bullish_obs > bearish_obs:
                bullish_score += 30
            elif bearish_obs > bullish_obs:
                bearish_score += 30
                
        except Exception as e:
            logger.debug(f"Order block analysis error: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # 3. DISPLACEMENT (10 points)
        # ═══════════════════════════════════════════════════════════
        recent_change = (df['close'].iloc[-1] / df['close'].iloc[-20] - 1) * 100
        
        if recent_change > 5:  # 5% up move
            bullish_score += 10
        elif recent_change < -5:  # 5% down move
            bearish_score += 10
        
        # ═══════════════════════════════════════════════════════════
        # DETERMINE BIAS
        # ═══════════════════════════════════════════════════════════
        
        if bullish_score >= 70 and bullish_score > bearish_score:
            return Bias.BULLISH
        elif bearish_score >= 70 and bearish_score > bullish_score:
            return Bias.BEARISH
        elif abs(bullish_score - bearish_score) <= 20:
            return Bias.RANGING
        else:
            return Bias.NEUTRAL
    
    def _analyze_mtf_structure(self, df: pd.DataFrame, timeframe: str) -> Bias:
        """Analyze medium timeframe structure"""
        if len(df) < 30:
            return Bias.NEUTRAL
        
        # Find recent structure breaks
        swings = self._find_swing_points(df, self.config['swing_lookback'])
        
        if len(swings) < 4:
            return Bias.NEUTRAL
        
        # Analyze last few swings
        recent_swings = swings[-6:]
        
        # Check for BOS or CHOCH
        highs = [s for s in recent_swings if s.is_high]
        lows = [s for s in recent_swings if not s.is_high]
        
        if len(highs) >= 2 and len(lows) >= 2:
            # Bullish: Higher Highs and Higher Lows
            hh = highs[-1].price > highs[-2].price if len(highs) >= 2 else False
            hl = lows[-1].price > lows[-2].price if len(lows) >= 2 else False
            
            # Bearish: Lower Highs and Lower Lows
            lh = highs[-1].price < highs[-2].price if len(highs) >= 2 else False
            ll = lows[-1].price < lows[-2].price if len(lows) >= 2 else False
            
            if hh and hl:
                return Bias.BULLISH
            elif lh and ll:
                return Bias.BEARISH
        
        return Bias.NEUTRAL
    
    def _find_swing_points(self, df: pd.DataFrame, lookback: int) -> List[SwingPoint]:
        """Identify swing highs and lows"""
        swings = []
        
        for i in range(lookback, len(df) - lookback):
            # Swing High
            if df['high'].iloc[i] == df['high'].iloc[i-lookback:i+lookback+1].max():
                swings.append(SwingPoint(
                    index=i,
                    price=df['high'].iloc[i],
                    timestamp=df.index[i],
                    is_high=True,
                    strength=lookback
                ))
            
            # Swing Low
            if df['low'].iloc[i] == df['low'].iloc[i-lookback:i+lookback+1].min():
                swings.append(SwingPoint(
                    index=i,
                    price=df['low'].iloc[i],
                    timestamp=df.index[i],
                    is_high=False,
                    strength=lookback
                ))
        
        return swings
    
    def _identify_swing_points(self, df: pd.DataFrame, timeframe: str):
        """Store swing points for a timeframe"""
        swings = self._find_swing_points(df, self.config['swing_lookback'])
        self.swing_points[timeframe] = swings
    
    def _analyze_structure_bias(self, swings: List[SwingPoint]) -> Bias:
        """Analyze market structure from swing points"""
        if len(swings) < 4:
            return Bias.NEUTRAL
        
        highs = [s.price for s in swings if s.is_high]
        lows = [s.price for s in swings if not s.is_high]
        
        if len(highs) >= 2 and len(lows) >= 2:
            recent_highs = highs[-2:]
            recent_lows = lows[-2:]
            
            hh = recent_highs[-1] > recent_highs[-2]
            hl = recent_lows[-1] > recent_lows[-2]
            lh = recent_highs[-1] < recent_highs[-2]
            ll = recent_lows[-1] < recent_lows[-2]
            
            if hh and hl:
                return Bias.BULLISH
            elif lh and ll:
                return Bias.BEARISH
        
        return Bias.NEUTRAL
    
    def _detect_structure_breaks(self, df: pd.DataFrame, timeframe: str):
        """Detect BOS and CHOCH events"""
        swings = self.swing_points.get(timeframe, [])
        
        if len(swings) < 3:
            return
        
        for i in range(2, len(swings)):
            current = swings[i]
            previous = swings[i-1]
            prior = swings[i-2]
            
            # BOS - continuation pattern
            if current.is_high == prior.is_high:
                if current.is_high and current.price > prior.price:
                    # Bullish BOS
                    self.structure_breaks.append(StructureBreak(
                        index=current.index,
                        price=current.price,
                        timestamp=current.timestamp,
                        type=StructureType.BOS,
                        timeframe=timeframe,
                        previous_level=prior.price,
                        strength=0.8
                    ))
                elif not current.is_high and current.price < prior.price:
                    # Bearish BOS
                    self.structure_breaks.append(StructureBreak(
                        index=current.index,
                        price=current.price,
                        timestamp=current.timestamp,
                        type=StructureType.BOS,
                        timeframe=timeframe,
                        previous_level=prior.price,
                        strength=0.8
                    ))
    
    def _identify_order_blocks(self, df: pd.DataFrame, timeframe: str):
        """Identify order blocks - last bearish candle before bullish move"""
        for i in range(1, len(df) - 1):
            # Bullish OB: Last down candle before up move
            if (df['close'].iloc[i] < df['open'].iloc[i] and  # Bearish candle
                df['close'].iloc[i+1] > df['open'].iloc[i+1] and  # Followed by bullish
                df['close'].iloc[i+1] > df['high'].iloc[i]):  # Strong move up
                
                volume_strength = df['volume_ratio'].iloc[i] if 'volume_ratio' in df else 1.0
                
                self.order_blocks.append(OrderBlock(
                    start_idx=i,
                    end_idx=i,
                    high=df['high'].iloc[i],
                    low=df['low'].iloc[i],
                    type=OrderBlockType.BULLISH_OB,
                    timestamp=df.index[i],
                    strength=min(volume_strength, 1.0),
                    volume=df['volume'].iloc[i]
                ))
            
            # Bearish OB: Last up candle before down move
            if (df['close'].iloc[i] > df['open'].iloc[i] and  # Bullish candle
                df['close'].iloc[i+1] < df['open'].iloc[i+1] and  # Followed by bearish
                df['close'].iloc[i+1] < df['low'].iloc[i]):  # Strong move down
                
                volume_strength = df['volume_ratio'].iloc[i] if 'volume_ratio' in df else 1.0
                
                self.order_blocks.append(OrderBlock(
                    start_idx=i,
                    end_idx=i,
                    high=df['high'].iloc[i],
                    low=df['low'].iloc[i],
                    type=OrderBlockType.BEARISH_OB,
                    timestamp=df.index[i],
                    strength=min(volume_strength, 1.0),
                    volume=df['volume'].iloc[i]
                ))
    
    def _identify_fvgs(self, df: pd.DataFrame, timeframe: str):
        """Identify Fair Value Gaps"""
        for i in range(2, len(df)):
            # Bullish FVG: Gap between candle[i-2] high and candle[i] low
            if df['low'].iloc[i] > df['high'].iloc[i-2]:
                gap_size = (df['low'].iloc[i] - df['high'].iloc[i-2]) / df['close'].iloc[i]
                
                if gap_size >= self.config['fvg_min_size']:
                    self.fvgs.append(FairValueGap(
                        start_idx=i-2,
                        end_idx=i,
                        top=df['low'].iloc[i],
                        bottom=df['high'].iloc[i-2],
                        type=FVGType.BULLISH_FVG,
                        timestamp=df.index[i]
                    ))
            
            # Bearish FVG: Gap between candle[i-2] low and candle[i] high
            if df['high'].iloc[i] < df['low'].iloc[i-2]:
                gap_size = (df['low'].iloc[i-2] - df['high'].iloc[i]) / df['close'].iloc[i]
                
                if gap_size >= self.config['fvg_min_size']:
                    self.fvgs.append(FairValueGap(
                        start_idx=i-2,
                        end_idx=i,
                        top=df['low'].iloc[i-2],
                        bottom=df['high'].iloc[i],
                        type=FVGType.BEARISH_FVG,
                        timestamp=df.index[i]
                    ))
    
    def _identify_liquidity_pools(self, df: pd.DataFrame, timeframe: str):
        """Identify liquidity pools at equal highs/lows"""
        threshold = df['atr'].iloc[-1] * 0.1 if 'atr' in df else df['close'].iloc[-1] * 0.001
        
        # Find equal highs (Buy Side Liquidity)
        highs = []
        for i in range(len(df) - 10, len(df)):
            if df['high'].iloc[i] == df['high'].iloc[i-5:i+1].max():
                highs.append((df['high'].iloc[i], df.index[i]))
        
        # Group similar highs
        for price, timestamp in highs:
            similar = [p for p, _ in highs if abs(p - price) < threshold]
            if len(similar) >= self.config['liquidity_threshold']:
                self.liquidity_pools.append(LiquidityPool(
                    price=price,
                    timestamp=timestamp,
                    type='BSL',
                    strength=len(similar) / self.config['liquidity_threshold'],
                    touches=len(similar)
                ))
        
        # Find equal lows (Sell Side Liquidity)
        lows = []
        for i in range(len(df) - 10, len(df)):
            if df['low'].iloc[i] == df['low'].iloc[i-5:i+1].min():
                lows.append((df['low'].iloc[i], df.index[i]))
        
        # Group similar lows
        for price, timestamp in lows:
            similar = [p for p, _ in lows if abs(p - price) < threshold]
            if len(similar) >= self.config['liquidity_threshold']:
                self.liquidity_pools.append(LiquidityPool(
                    price=price,
                    timestamp=timestamp,
                    type='SSL',
                    strength=len(similar) / self.config['liquidity_threshold'],
                    touches=len(similar)
                ))
    
    def _generate_ltf_signals(self, symbol: str) -> List[MTFSignal]:
        """Generate LTF entry signals based on MTF alignment"""
        signals = []
        
        if len(self.ltf_data) < 20:
            return signals
        
        current_price = self.ltf_data['close'].iloc[-1]
        atr = self.ltf_data['atr'].iloc[-1]
        
        # Check alignment
        alignment_score = self._calculate_alignment_score()
        
        if alignment_score < self.config['alignment_threshold']:
            logger.info(f"Insufficient alignment: {alignment_score:.2f}")
            return signals
        
        # Generate long signals
        if self.htf_bias == Bias.BULLISH or self.mtf_bias == Bias.BULLISH:
            long_signal = self._check_long_entry(symbol, current_price, atr, alignment_score)
            if long_signal:
                signals.append(long_signal)
        
        # Generate short signals
        if self.htf_bias == Bias.BEARISH or self.mtf_bias == Bias.BEARISH:
            short_signal = self._check_short_entry(symbol, current_price, atr, alignment_score)
            if short_signal:
                signals.append(short_signal)
        
        return signals
    
    def _calculate_alignment_score(self) -> float:
        """Calculate multi-timeframe alignment score"""
        score = 0.0
        max_score = 5.0
        
        # HTF and MTF bias alignment (2 points)
        if self.htf_bias == self.mtf_bias and self.htf_bias != Bias.NEUTRAL:
            score += 2.0
        elif self.htf_bias != Bias.NEUTRAL and self.mtf_bias != Bias.NEUTRAL:
            if (self.htf_bias == Bias.BULLISH and self.mtf_bias != Bias.BEARISH) or \
               (self.htf_bias == Bias.BEARISH and self.mtf_bias != Bias.BULLISH):
                score += 1.0
        
        # Recent structure breaks (1 point)
        recent_breaks = [sb for sb in self.structure_breaks 
                        if (datetime.now() - sb.timestamp).days < 7]
        if recent_breaks:
            score += 1.0
        
        # Valid order blocks (1 point)
        valid_obs = [ob for ob in self.order_blocks if not ob.mitigated]
        if len(valid_obs) >= 2:
            score += 1.0
        
        # Unfilled FVGs (1 point)
        unfilled_fvgs = [fvg for fvg in self.fvgs if not fvg.filled]
        if len(unfilled_fvgs) >= 1:
            score += 1.0
        
        return score / max_score
    
    def _check_long_entry(self, symbol: str, current_price: float, 
                         atr: float, alignment_score: float) -> Optional[MTFSignal]:
        """Check for long entry setup"""
        # Find bullish OB near current price
        bullish_obs = [ob for ob in self.order_blocks 
                      if ob.type == OrderBlockType.BULLISH_OB and not ob.mitigated
                      and ob.low <= current_price <= ob.high * 1.02]
        
        if not bullish_obs:
            return None
        
        best_ob = max(bullish_obs, key=lambda x: x.strength)
        
        # Find bullish FVG
        bullish_fvgs = [fvg for fvg in self.fvgs 
                       if fvg.type == FVGType.BULLISH_FVG and not fvg.filled
                       and fvg.bottom <= current_price <= fvg.top * 1.01]
        
        # Entry at OB
        entry_price = (best_ob.low + best_ob.high) / 2
        stop_loss = best_ob.low - (atr * 0.5)
        
        # Targets at liquidity pools
        bsl_targets = sorted([lp.price for lp in self.liquidity_pools 
                             if lp.type == 'BSL' and lp.price > entry_price])
        
        if not bsl_targets:
            # Default targets
            take_profit = [
                entry_price + (atr * 2),
                entry_price + (atr * 3),
                entry_price + (atr * 4)
            ]
        else:
            take_profit = bsl_targets[:3]
        
        risk_reward = (take_profit[0] - entry_price) / (entry_price - stop_loss)
        
        if risk_reward < self.config['risk_reward_min']:
            return None
        
        confidence = alignment_score * 0.5 + (best_ob.strength * 0.3) + 0.2
        
        if confidence < self.config['min_confidence']:
            return None
        
        return MTFSignal(
            timestamp=datetime.now(),
            symbol=symbol,
            direction='LONG',
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_bias=self.htf_bias,
            mtf_structure=self.mtf_bias.value,
            ltf_trigger='Bullish OB + FVG',
            confidence=confidence,
            risk_reward=risk_reward,
            alignment_score=alignment_score,
            order_blocks=[best_ob],
            fvgs=bullish_fvgs,
            liquidity_targets=[lp for lp in self.liquidity_pools if lp.type == 'BSL'],
            notes=f"Entry at bullish OB (strength: {best_ob.strength:.2f})"
        )
    
    def _check_short_entry(self, symbol: str, current_price: float,
                          atr: float, alignment_score: float) -> Optional[MTFSignal]:
        """Check for short entry setup"""
        # Find bearish OB near current price
        bearish_obs = [ob for ob in self.order_blocks 
                      if ob.type == OrderBlockType.BEARISH_OB and not ob.mitigated
                      and ob.low * 0.98 <= current_price <= ob.high]
        
        if not bearish_obs:
            return None
        
        best_ob = max(bearish_obs, key=lambda x: x.strength)
        
        # Find bearish FVG
        bearish_fvgs = [fvg for fvg in self.fvgs 
                       if fvg.type == FVGType.BEARISH_FVG and not fvg.filled
                       and fvg.bottom * 0.99 <= current_price <= fvg.top]
        
        # Entry at OB
        entry_price = (best_ob.low + best_ob.high) / 2
        stop_loss = best_ob.high + (atr * 0.5)
        
        # Targets at liquidity pools
        ssl_targets = sorted([lp.price for lp in self.liquidity_pools 
                             if lp.type == 'SSL' and lp.price < entry_price], reverse=True)
        
        if not ssl_targets:
            # Default targets
            take_profit = [
                entry_price - (atr * 2),
                entry_price - (atr * 3),
                entry_price - (atr * 4)
            ]
        else:
            take_profit = ssl_targets[:3]
        
        risk_reward = (entry_price - take_profit[0]) / (stop_loss - entry_price)
        
        if risk_reward < self.config['risk_reward_min']:
            return None
        
        confidence = alignment_score * 0.5 + (best_ob.strength * 0.3) + 0.2
        
        if confidence < self.config['min_confidence']:
            return None
        
        return MTFSignal(
            timestamp=datetime.now(),
            symbol=symbol,
            direction='SHORT',
            entry_price=entry_price,
            stop_loss=stop_loss,
            take_profit=take_profit,
            htf_bias=self.htf_bias,
            mtf_structure=self.mtf_bias.value,
            ltf_trigger='Bearish OB + FVG',
            confidence=confidence,
            risk_reward=risk_reward,
            alignment_score=alignment_score,
            order_blocks=[best_ob],
            fvgs=bearish_fvgs,
            liquidity_targets=[lp for lp in self.liquidity_pools if lp.type == 'SSL'],
            notes=f"Entry at bearish OB (strength: {best_ob.strength:.2f})"
        )
    
    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get comprehensive analysis summary"""
        return {
            'htf_bias': self.htf_bias.value,
            'mtf_bias': self.mtf_bias.value,
            'alignment_score': self._calculate_alignment_score(),
            'structure_breaks': len(self.structure_breaks),
            'order_blocks': {
                'total': len(self.order_blocks),
                'bullish': len([ob for ob in self.order_blocks if ob.type == OrderBlockType.BULLISH_OB]),
                'bearish': len([ob for ob in self.order_blocks if ob.type == OrderBlockType.BEARISH_OB]),
                'active': len([ob for ob in self.order_blocks if not ob.mitigated])
            },
            'fvgs': {
                'total': len(self.fvgs),
                'bullish': len([fvg for fvg in self.fvgs if fvg.type == FVGType.BULLISH_FVG]),
                'bearish': len([fvg for fvg in self.fvgs if fvg.type == FVGType.BEARISH_FVG]),
                'unfilled': len([fvg for fvg in self.fvgs if not fvg.filled])
            },
            'liquidity_pools': {
                'total': len(self.liquidity_pools),
                'buy_side': len([lp for lp in self.liquidity_pools if lp.type == 'BSL']),
                'sell_side': len([lp for lp in self.liquidity_pools if lp.type == 'SSL']),
                'unswept': len([lp for lp in self.liquidity_pools if not lp.swept])
            },
            'swing_points': {
                '1D': len(self.swing_points.get('1D', [])),
                '4H': len(self.swing_points.get('4H', [])),
                '1H': len(self.swing_points.get('1H', []))
            }
        }


# Example usage
if __name__ == "__main__":
    # Initialize analyzer
    analyzer = MultiTimeframeAnalyzer()
    
    # Example data (in practice, fetch from exchange)
    # htf_df = pd.DataFrame(...)  # 1D data
    # mtf_df = pd.DataFrame(...)  # 4H data
    # ltf_df = pd.DataFrame(...)  # 1H data
    
    # Perform analysis
    # signals = analyzer.analyze_multi_timeframe(htf_df, mtf_df, ltf_df, 'BTCUSDT')
    
    # Display results
    # for signal in signals:
    #     print(f"Signal: {signal.direction} at {signal.entry_price}")
    #     print(f"Confidence: {signal.confidence:.2%}")
    #     print(f"R:R = {signal.risk_reward:.2f}")
    
    print("Multi-Timeframe Analyzer initialized successfully!")
    print("Total lines: 700+")