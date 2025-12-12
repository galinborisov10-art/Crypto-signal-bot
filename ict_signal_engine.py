"""
🎯 ICT SIGNAL ENGINE
Central ICT Signal Generation Engine

Combines ALL ICT concepts to generate professional trading signals:
- Integrates whale blocks, liquidity zones, order blocks, FVGs
- Multi-timeframe confluence analysis
- Market bias determination
- Entry/SL/TP calculation
- Confidence scoring
- Risk/reward optimization

Author: ICT Trading System
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

# Import ICT modules
try:
    from ict_whale_detector import WhaleDetector, WhaleOrderBlock
    from liquidity_map import LiquidityMapper, LiquidityZone, LiquiditySweep
    from ilp_detector import InternalLiquidityPoolDetector, LiquidityPool as ILPPool
    from luxalgo_ict_concepts import LuxAlgoICT
    from order_block_detector import OrderBlockDetector, OrderBlock, OrderBlockType
    from fvg_detector import FVGDetector, FairValueGap, FVGType
except ImportError as e:
    logging.warning(f"Some ICT modules not available: {e}")

logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class SignalStrength(Enum):
    """Signal strength levels"""
    VERY_STRONG = 5
    STRONG = 4
    MODERATE = 3
    WEAK = 2
    VERY_WEAK = 1


class MarketBias(Enum):
    """Market bias"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


@dataclass
class ICTComponents:
    """Container for all ICT components"""
    whale_blocks: List[WhaleOrderBlock] = field(default_factory=list)
    liquidity_zones: List[LiquidityZone] = field(default_factory=list)
    liquidity_sweeps: List[LiquiditySweep] = field(default_factory=list)
    ilp_pools: List[ILPPool] = field(default_factory=list)
    order_blocks: List[OrderBlock] = field(default_factory=list)
    fvgs: List[FairValueGap] = field(default_factory=list)
    luxalgo_data: Optional[Dict] = None


@dataclass
class MTFAnalysis:
    """Multi-timeframe analysis results"""
    htf_bias: MarketBias = MarketBias.NEUTRAL
    mtf_bias: MarketBias = MarketBias.NEUTRAL
    ltf_bias: MarketBias = MarketBias.NEUTRAL
    confluence_count: int = 0
    alignment_score: float = 0.0


@dataclass
class ICTSignal:
    """Complete ICT Trading Signal"""
    # Basic info
    signal_type: SignalType
    signal_strength: SignalStrength
    symbol: str
    timeframe: str
    timestamp: datetime
    
    # Entry and exits
    entry_price: float
    stop_loss: float
    take_profit_1: float
    take_profit_2: float
    take_profit_3: float
    
    # Metrics
    confidence: float  # 0-100
    risk_reward_ratio: float
    
    # ICT Components
    whale_blocks: List[WhaleOrderBlock] = field(default_factory=list)
    liquidity_zones: List[LiquidityZone] = field(default_factory=list)
    order_blocks: List[OrderBlock] = field(default_factory=list)
    fvgs: List[FairValueGap] = field(default_factory=list)
    
    # Analysis
    market_bias: MarketBias = MarketBias.NEUTRAL
    mtf_confluence: int = 0
    
    # Reasoning
    reasoning: str = ""
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'signal_type': self.signal_type.value,
            'signal_strength': self.signal_strength.value,
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'timestamp': self.timestamp.isoformat(),
            'entry_price': self.entry_price,
            'stop_loss': self.stop_loss,
            'take_profit_1': self.take_profit_1,
            'take_profit_2': self.take_profit_2,
            'take_profit_3': self.take_profit_3,
            'confidence': self.confidence,
            'risk_reward': self.risk_reward_ratio,
            'market_bias': self.market_bias.value,
            'mtf_confluence': self.mtf_confluence,
            'reasoning': self.reasoning,
            'warnings': self.warnings,
            'whale_blocks_count': len(self.whale_blocks),
            'liquidity_zones_count': len(self.liquidity_zones),
            'order_blocks_count': len(self.order_blocks),
            'fvgs_count': len(self.fvgs)
        }
    
    def __repr__(self) -> str:
        return (f"ICTSignal({self.signal_type.value} {self.symbol}, "
                f"strength={self.signal_strength.value}, "
                f"confidence={self.confidence:.1f}%, "
                f"R:R={self.risk_reward_ratio:.2f})")


class ICTSignalEngine:
    """
    Central ICT Signal Generation Engine
    
    Integrates all ICT concepts to generate high-probability trading signals.
    
    Features:
    - Multi-timeframe analysis
    - ICT component detection
    - Market bias determination
    - Entry/SL/TP calculation
    - Confidence scoring
    - Signal validation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize ICT Signal Engine
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or self._get_default_config()
        
        # Initialize detectors
        self.whale_detector = WhaleDetector(
            displacement_threshold=self.config.get('whale_displacement', 1.5),
            fvg_min_size=self.config.get('whale_fvg_size', 0.3),
            volume_spike_threshold=self.config.get('whale_volume', 1.5)
        )
        
        self.liquidity_mapper = LiquidityMapper()
        
        self.ilp_detector = InternalLiquidityPoolDetector(
            swing_period=self.config.get('ilp_swing_period', 5)
        )
        
        self.ob_detector = OrderBlockDetector(
            swing_period=self.config.get('ob_swing_period', 10),
            displacement_threshold=self.config.get('ob_displacement', 1.5)
        )
        
        self.fvg_detector = FVGDetector(
            min_size_pct=self.config.get('fvg_min_size', 0.1),
            displacement_threshold=self.config.get('fvg_displacement', 1.5)
        )
        
        self.luxalgo = LuxAlgoICT(
            swing_length=self.config.get('luxalgo_swing', 10)
        )
        
        logger.info("ICTSignalEngine initialized successfully")
    
    def _get_default_config(self) -> Dict[str, Any]:
        """Get default configuration"""
        return {
            'min_confidence': 60,
            'min_risk_reward': 2.0,
            'tp_multipliers': [2.0, 3.0, 4.0],
            'require_mtf_confluence': False,
            'whale_displacement': 1.5,
            'whale_fvg_size': 0.3,
            'whale_volume': 1.5,
            'ilp_swing_period': 5,
            'ob_swing_period': 10,
            'ob_displacement': 1.5,
            'fvg_min_size': 0.1,
            'fvg_displacement': 1.5,
            'luxalgo_swing': 10
        }
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str = '1h',
        mtf_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[ICTSignal]:
        """
        Main method: Generate ICT trading signal
        
        Args:
            df: Primary timeframe DataFrame
            symbol: Trading pair symbol
            timeframe: Timeframe label
            mtf_data: Multi-timeframe data dict
            
        Returns:
            ICTSignal object or None
        """
        try:
            logger.info(f"Generating ICT signal for {symbol} on {timeframe}")
            
            # Validate data
            if df is None or len(df) < 50:
                logger.warning("Insufficient data for signal generation")
                return None
            
            # Step 1: Detect all ICT components
            components = self._detect_ict_components(df, timeframe)
            
            # Step 2: Multi-timeframe analysis
            mtf_analysis = self._analyze_mtf_confluence(df, mtf_data) if mtf_data else None
            
            # Step 3: Determine market bias
            bias = self._determine_market_bias(components, mtf_analysis)
            
            # Step 4: Identify entry setup
            entry_setup = self._identify_entry_setup(components, bias)
            
            if not entry_setup:
                logger.info("No valid entry setup found")
                return None
            
            # Step 5: Calculate entry price
            entry_price = self._calculate_entry_price(df, entry_setup)
            
            # Step 6: Calculate stop loss
            stop_loss = self._calculate_stop_loss(df, entry_setup, bias)
            
            # Step 7: Calculate take profits
            tp1, tp2, tp3 = self._calculate_take_profits(entry_price, stop_loss, bias)
            
            # Step 8: Calculate risk/reward
            risk = abs(entry_price - stop_loss)
            reward = abs(tp1 - entry_price)
            risk_reward = reward / risk if risk > 0 else 0
            
            # Validate risk/reward
            if risk_reward < self.config['min_risk_reward']:
                logger.info(f"R:R too low: {risk_reward:.2f}")
                return None
            
            # Step 9: Calculate confidence
            confidence = self._calculate_signal_confidence(
                components, mtf_analysis, entry_setup
            )
            
            # Validate confidence
            if confidence < self.config['min_confidence']:
                logger.info(f"Confidence too low: {confidence:.1f}%")
                return None
            
            # Step 10: Calculate signal strength
            strength = self._calculate_signal_strength(confidence, risk_reward, components)
            
            # Step 11: Generate reasoning
            reasoning = self._generate_reasoning(bias, components, entry_setup)
            
            # Step 12: Generate warnings
            warnings = self._generate_warnings(df, components, mtf_analysis)
            
            # Step 13: Determine signal type
            signal_type = SignalType.BUY if bias == MarketBias.BULLISH else SignalType.SELL
            
            # Create signal
            signal = ICTSignal(
                signal_type=signal_type,
                signal_strength=strength,
                symbol=symbol,
                timeframe=timeframe,
                timestamp=datetime.now(),
                entry_price=entry_price,
                stop_loss=stop_loss,
                take_profit_1=tp1,
                take_profit_2=tp2,
                take_profit_3=tp3,
                confidence=confidence,
                risk_reward_ratio=risk_reward,
                whale_blocks=components.whale_blocks,
                liquidity_zones=components.liquidity_zones,
                order_blocks=components.order_blocks,
                fvgs=components.fvgs,
                market_bias=bias,
                mtf_confluence=mtf_analysis.confluence_count if mtf_analysis else 0,
                reasoning=reasoning,
                warnings=warnings
            )
            
            logger.info(f"Generated signal: {signal}")
            return signal
            
        except Exception as e:
            logger.error(f"Signal generation error: {e}", exc_info=True)
            return None
    
    def _detect_ict_components(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> ICTComponents:
        """
        Detect all ICT components in the data
        
        Args:
            df: DataFrame
            timeframe: Timeframe label
            
        Returns:
            ICTComponents object
        """
        components = ICTComponents()
        
        try:
            # Whale blocks
            components.whale_blocks = self.whale_detector.detect_whale_blocks(df, timeframe)
            logger.debug(f"Detected {len(components.whale_blocks)} whale blocks")
            
            # Liquidity zones
            components.liquidity_zones = self.liquidity_mapper.detect_liquidity_zones(df, timeframe)
            logger.debug(f"Detected {len(components.liquidity_zones)} liquidity zones")
            
            # Liquidity sweeps
            components.liquidity_sweeps = self.liquidity_mapper.detect_liquidity_sweeps(
                df, components.liquidity_zones
            )
            logger.debug(f"Detected {len(components.liquidity_sweeps)} liquidity sweeps")
            
            # Internal liquidity pools
            self.ilp_detector.detect_swing_points(df)
            components.ilp_pools = self.ilp_detector.detect_liquidity_pools(df)
            logger.debug(f"Detected {len(components.ilp_pools)} ILP pools")
            
            # Order blocks
            components.order_blocks = self.ob_detector.detect_order_blocks(df)
            logger.debug(f"Detected {len(components.order_blocks)} order blocks")
            
            # Fair Value Gaps
            components.fvgs = self.fvg_detector.detect_fvgs(df)
            logger.debug(f"Detected {len(components.fvgs)} FVGs")
            
            # LuxAlgo ICT analysis
            components.luxalgo_data = self.luxalgo.analyze(df)
            logger.debug("LuxAlgo analysis completed")
            
        except Exception as e:
            logger.error(f"Component detection error: {e}")
        
        return components
    
    def _analyze_mtf_confluence(
        self,
        df: pd.DataFrame,
        mtf_data: Optional[Dict[str, pd.DataFrame]]
    ) -> Optional[MTFAnalysis]:
        """
        Analyze multi-timeframe confluence
        
        Args:
            df: Primary timeframe data
            mtf_data: Dictionary with higher timeframe data
            
        Returns:
            MTFAnalysis object
        """
        if not mtf_data:
            return None
        
        try:
            analysis = MTFAnalysis()
            
            # Analyze each timeframe
            timeframes = ['1D', '4H', '1H']
            biases = []
            
            for tf in timeframes:
                if tf in mtf_data:
                    tf_df = mtf_data[tf]
                    bias = self._detect_timeframe_bias(tf_df)
                    biases.append(bias)
                    
                    if tf == '1D':
                        analysis.htf_bias = bias
                    elif tf == '4H':
                        analysis.mtf_bias = bias
                    elif tf == '1H':
                        analysis.ltf_bias = bias
            
            # Calculate confluence
            bullish_count = sum(1 for b in biases if b == MarketBias.BULLISH)
            bearish_count = sum(1 for b in biases if b == MarketBias.BEARISH)
            
            analysis.confluence_count = max(bullish_count, bearish_count)
            analysis.alignment_score = analysis.confluence_count / len(biases) if biases else 0
            
            return analysis
            
        except Exception as e:
            logger.error(f"MTF analysis error: {e}")
            return None
    
    def _detect_timeframe_bias(self, df: pd.DataFrame) -> MarketBias:
        """
        Detect bias for a single timeframe
        
        Args:
            df: DataFrame
            
        Returns:
            MarketBias
        """
        try:
            if len(df) < 50:
                return MarketBias.NEUTRAL
            
            # Calculate EMAs
            ema_20 = df['close'].ewm(span=20, adjust=False).mean()
            ema_50 = df['close'].ewm(span=50, adjust=False).mean()
            
            current_price = df['close'].iloc[-1]
            
            # Price above both EMAs = bullish
            if current_price > ema_20.iloc[-1] and current_price > ema_50.iloc[-1]:
                if ema_20.iloc[-1] > ema_50.iloc[-1]:
                    return MarketBias.BULLISH
            
            # Price below both EMAs = bearish
            elif current_price < ema_20.iloc[-1] and current_price < ema_50.iloc[-1]:
                if ema_20.iloc[-1] < ema_50.iloc[-1]:
                    return MarketBias.BEARISH
            
            return MarketBias.NEUTRAL
            
        except Exception as e:
            logger.error(f"Bias detection error: {e}")
            return MarketBias.NEUTRAL
    
    def _determine_market_bias(
        self,
        components: ICTComponents,
        mtf_analysis: Optional[MTFAnalysis]
    ) -> MarketBias:
        """
        Determine overall market bias
        
        Args:
            components: ICT components
            mtf_analysis: MTF analysis results
            
        Returns:
            MarketBias
        """
        bullish_score = 0
        bearish_score = 0
        
        # MTF bias (strongest signal)
        if mtf_analysis:
            if mtf_analysis.htf_bias == MarketBias.BULLISH:
                bullish_score += 3
            elif mtf_analysis.htf_bias == MarketBias.BEARISH:
                bearish_score += 3
            
            if mtf_analysis.mtf_bias == MarketBias.BULLISH:
                bullish_score += 2
            elif mtf_analysis.mtf_bias == MarketBias.BEARISH:
                bearish_score += 2
        
        # Whale blocks
        bullish_whales = sum(1 for wb in components.whale_blocks if wb.zone_type == 'buy')
        bearish_whales = sum(1 for wb in components.whale_blocks if wb.zone_type == 'sell')
        if bullish_whales > bearish_whales:
            bullish_score += 1
        elif bearish_whales > bullish_whales:
            bearish_score += 1
        
        # Order blocks
        bullish_obs = sum(1 for ob in components.order_blocks 
                         if ob.ob_type == OrderBlockType.BULLISH and not ob.mitigated)
        bearish_obs = sum(1 for ob in components.order_blocks 
                         if ob.ob_type == OrderBlockType.BEARISH and not ob.mitigated)
        if bullish_obs > bearish_obs:
            bullish_score += 1
        elif bearish_obs > bullish_obs:
            bearish_score += 1
        
        # FVGs
        bullish_fvgs = sum(1 for fvg in components.fvgs 
                          if fvg.gap_type == FVGType.BULLISH and not fvg.filled)
        bearish_fvgs = sum(1 for fvg in components.fvgs 
                          if fvg.gap_type == FVGType.BEARISH and not fvg.filled)
        if bullish_fvgs > bearish_fvgs:
            bullish_score += 1
        elif bearish_fvgs > bullish_fvgs:
            bearish_score += 1
        
        # Determine bias
        if bullish_score > bearish_score and bullish_score >= 3:
            return MarketBias.BULLISH
        elif bearish_score > bullish_score and bearish_score >= 3:
            return MarketBias.BEARISH
        else:
            return MarketBias.NEUTRAL
    
    def _identify_entry_setup(
        self,
        components: ICTComponents,
        bias: MarketBias
    ) -> Optional[Dict[str, Any]]:
        """
        Identify valid entry setup
        
        Args:
            components: ICT components
            bias: Market bias
            
        Returns:
            Entry setup dictionary or None
        """
        if bias == MarketBias.NEUTRAL:
            return None
        
        setup = {
            'bias': bias,
            'order_block': None,
            'fvg': None,
            'liquidity_target': None,
            'confluence': 0
        }
        
        try:
            if bias == MarketBias.BULLISH:
                # Find bullish order block
                bullish_obs = [ob for ob in components.order_blocks 
                              if ob.ob_type == OrderBlockType.BULLISH and not ob.mitigated]
                if bullish_obs:
                    setup['order_block'] = max(bullish_obs, key=lambda x: x.strength_score)
                    setup['confluence'] += 1
                
                # Find bullish FVG
                bullish_fvgs = [fvg for fvg in components.fvgs 
                               if fvg.gap_type == FVGType.BULLISH and not fvg.filled]
                if bullish_fvgs:
                    setup['fvg'] = max(bullish_fvgs, key=lambda x: x.quality_score)
                    setup['confluence'] += 1
                
                # Find liquidity target above
                bsl_zones = [lz for lz in components.liquidity_zones if lz.zone_type == 'BSL']
                if bsl_zones:
                    setup['liquidity_target'] = max(bsl_zones, key=lambda x: x.strength)
                    setup['confluence'] += 1
            
            else:  # BEARISH
                # Find bearish order block
                bearish_obs = [ob for ob in components.order_blocks 
                              if ob.ob_type == OrderBlockType.BEARISH and not ob.mitigated]
                if bearish_obs:
                    setup['order_block'] = max(bearish_obs, key=lambda x: x.strength_score)
                    setup['confluence'] += 1
                
                # Find bearish FVG
                bearish_fvgs = [fvg for fvg in components.fvgs 
                               if fvg.gap_type == FVGType.BEARISH and not fvg.filled]
                if bearish_fvgs:
                    setup['fvg'] = max(bearish_fvgs, key=lambda x: x.quality_score)
                    setup['confluence'] += 1
                
                # Find liquidity target below
                ssl_zones = [lz for lz in components.liquidity_zones if lz.zone_type == 'SSL']
                if ssl_zones:
                    setup['liquidity_target'] = max(ssl_zones, key=lambda x: x.strength)
                    setup['confluence'] += 1
            
            # Need at least 1 confluence
            if setup['confluence'] >= 1:
                return setup
            
            return None
            
        except Exception as e:
            logger.error(f"Entry setup identification error: {e}")
            return None
    
    def _calculate_entry_price(
        self,
        df: pd.DataFrame,
        entry_setup: Dict[str, Any]
    ) -> float:
        """
        Calculate entry price based on setup
        
        Args:
            df: DataFrame
            entry_setup: Entry setup dictionary
            
        Returns:
            Entry price
        """
        current_price = df['close'].iloc[-1]
        
        # If order block present, use middle of OB zone
        if entry_setup['order_block']:
            ob = entry_setup['order_block']
            return (ob.zone_high + ob.zone_low) / 2
        
        # If FVG present, use middle of gap
        elif entry_setup['fvg']:
            fvg = entry_setup['fvg']
            return (fvg.gap_high + fvg.gap_low) / 2
        
        # Otherwise use current price
        else:
            return current_price
    
    def _calculate_stop_loss(
        self,
        df: pd.DataFrame,
        entry_setup: Dict[str, Any],
        bias: MarketBias
    ) -> float:
        """
        Calculate stop loss based on structure
        
        Args:
            df: DataFrame
            entry_setup: Entry setup
            bias: Market bias
            
        Returns:
            Stop loss price
        """
        # Calculate ATR for buffer
        high = df['high']
        low = df['low']
        close = df['close']
        
        tr1 = high - low
        tr2 = abs(high - close.shift())
        tr3 = abs(low - close.shift())
        tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
        atr = tr.rolling(window=14).mean().iloc[-1]
        
        # Use order block for SL placement
        if entry_setup['order_block']:
            ob = entry_setup['order_block']
            if bias == MarketBias.BULLISH:
                # SL below bullish OB
                return ob.zone_low - (atr * 0.5)
            else:
                # SL above bearish OB
                return ob.zone_high + (atr * 0.5)
        
        # Use recent swing
        else:
            if bias == MarketBias.BULLISH:
                recent_low = df['low'].iloc[-20:].min()
                return recent_low - (atr * 0.5)
            else:
                recent_high = df['high'].iloc[-20:].max()
                return recent_high + (atr * 0.5)
    
    def _calculate_take_profits(
        self,
        entry: float,
        sl: float,
        bias: MarketBias
    ) -> Tuple[float, float, float]:
        """
        Calculate multiple take profit levels
        
        Args:
            entry: Entry price
            sl: Stop loss price
            bias: Market bias
            
        Returns:
            Tuple of (TP1, TP2, TP3)
        """
        risk = abs(entry - sl)
        multipliers = self.config['tp_multipliers']
        
        if bias == MarketBias.BULLISH:
            tp1 = entry + (risk * multipliers[0])
            tp2 = entry + (risk * multipliers[1])
            tp3 = entry + (risk * multipliers[2])
        else:
            tp1 = entry - (risk * multipliers[0])
            tp2 = entry - (risk * multipliers[1])
            tp3 = entry - (risk * multipliers[2])
        
        return (tp1, tp2, tp3)
    
    def _calculate_signal_confidence(
        self,
        components: ICTComponents,
        mtf_analysis: Optional[MTFAnalysis],
        entry_setup: Dict[str, Any]
    ) -> float:
        """
        Calculate signal confidence score (0-100)
        
        Args:
            components: ICT components
            mtf_analysis: MTF analysis
            entry_setup: Entry setup
            
        Returns:
            Confidence score
        """
        score = 0.0
        
        # MTF confluence (0-30 points)
        if mtf_analysis:
            score += mtf_analysis.alignment_score * 30
        
        # Entry setup confluence (0-20 points)
        setup_confluence = entry_setup.get('confluence', 0)
        score += min(20, setup_confluence * 10)
        
        # Order block quality (0-15 points)
        if entry_setup.get('order_block'):
            ob = entry_setup['order_block']
            score += (ob.strength_score / 100) * 15
        
        # FVG quality (0-15 points)
        if entry_setup.get('fvg'):
            fvg = entry_setup['fvg']
            score += (fvg.quality_score / 100) * 15
        
        # Whale block presence (0-10 points)
        if components.whale_blocks:
            score += 10
        
        # Liquidity sweep (0-10 points)
        if components.liquidity_sweeps:
            score += 10
        
        return min(100, score)
    
    def _calculate_signal_strength(
        self,
        confidence: float,
        risk_reward: float,
        components: ICTComponents
    ) -> SignalStrength:
        """
        Calculate signal strength level
        
        Args:
            confidence: Confidence score
            risk_reward: Risk/reward ratio
            components: ICT components
            
        Returns:
            SignalStrength enum
        """
        # Calculate combined score
        score = 0
        
        # Confidence contribution
        if confidence >= 85:
            score += 3
        elif confidence >= 75:
            score += 2
        elif confidence >= 65:
            score += 1
        
        # R:R contribution
        if risk_reward >= 4:
            score += 2
        elif risk_reward >= 3:
            score += 1
        
        # Component count
        total_components = (
            len(components.whale_blocks) +
            len(components.order_blocks) +
            len(components.fvgs) +
            len(components.liquidity_sweeps)
        )
        
        if total_components >= 5:
            score += 2
        elif total_components >= 3:
            score += 1
        
        # Map to strength
        if score >= 6:
            return SignalStrength.VERY_STRONG
        elif score >= 5:
            return SignalStrength.STRONG
        elif score >= 3:
            return SignalStrength.MODERATE
        elif score >= 2:
            return SignalStrength.WEAK
        else:
            return SignalStrength.VERY_WEAK
    
    def _generate_reasoning(
        self,
        bias: MarketBias,
        components: ICTComponents,
        entry_setup: Dict[str, Any]
    ) -> str:
        """
        Generate human-readable reasoning
        
        Args:
            bias: Market bias
            components: ICT components
            entry_setup: Entry setup
            
        Returns:
            Reasoning string
        """
        parts = []
        
        # Bias
        parts.append(f"Market bias: {bias.value}")
        
        # Entry setup
        if entry_setup.get('order_block'):
            ob = entry_setup['order_block']
            parts.append(f"{ob.ob_type.value} order block detected (strength: {ob.strength_score:.1f})")
        
        if entry_setup.get('fvg'):
            fvg = entry_setup['fvg']
            parts.append(f"{fvg.gap_type.value} FVG identified (quality: {fvg.quality_score:.1f})")
        
        # Components
        if components.whale_blocks:
            parts.append(f"{len(components.whale_blocks)} whale block(s) detected")
        
        if components.liquidity_sweeps:
            parts.append(f"{len(components.liquidity_sweeps)} liquidity sweep(s) occurred")
        
        # Confluence
        confluence = entry_setup.get('confluence', 0)
        parts.append(f"Setup confluence: {confluence}/3")
        
        return " | ".join(parts)
    
    def _generate_warnings(
        self,
        df: pd.DataFrame,
        components: ICTComponents,
        mtf_analysis: Optional[MTFAnalysis]
    ) -> List[str]:
        """
        Generate risk warnings
        
        Args:
            df: DataFrame
            components: ICT components
            mtf_analysis: MTF analysis
            
        Returns:
            List of warning strings
        """
        warnings = []
        
        # MTF divergence
        if mtf_analysis and mtf_analysis.confluence_count <= 1:
            warnings.append("⚠️ Low MTF confluence - timeframes not aligned")
        
        # No whale blocks
        if not components.whale_blocks:
            warnings.append("⚠️ No whale blocks detected - institutional presence unclear")
        
        # Many mitigated OBs
        mitigated_obs = sum(1 for ob in components.order_blocks if ob.mitigated)
        if mitigated_obs > len(components.order_blocks) * 0.5:
            warnings.append("⚠️ Many order blocks already mitigated")
        
        # Most FVGs filled
        filled_fvgs = sum(1 for fvg in components.fvgs if fvg.filled)
        if filled_fvgs > len(components.fvgs) * 0.7 and len(components.fvgs) > 0:
            warnings.append("⚠️ Most FVGs already filled")
        
        # High volatility
        if len(df) >= 20:
            recent_range = (df['high'].iloc[-20:].max() - df['low'].iloc[-20:].min()) / df['close'].iloc[-1]
            if recent_range > 0.10:  # 10%+ range
                warnings.append("⚠️ High volatility detected - increased risk")
        
        return warnings


# Example usage
if __name__ == "__main__":
    print("ICT Signal Engine initialized successfully!")
    print("Total lines: 800+")
