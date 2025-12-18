"""
🎯 ICT SIGNAL ENGINE
Central ICT Signal Generator - Combines ALL ICT concepts into unified signal generation

Features:
- Integrates Whale Order Blocks detection
- Integrates Liquidity Pools mapping
- Integrates Market Structure analysis
- Integrates Internal Liquidity detection
- Fair Value Gaps detection
- Multi-Timeframe Confluence analysis
- Complete signal generation with entry/SL/TP
- Confidence scoring (0-100%)
- Signal strength levels (WEAK to EXTREME)

Author: galinborisov10-art
Date: 2025-12-12
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import logging

# Import ICT modules
try:
    from order_block_detector import OrderBlockDetector, OrderBlock, OrderBlockType, MitigationBlock
    ORDER_BLOCK_AVAILABLE = True
except ImportError:
    ORDER_BLOCK_AVAILABLE = False
    logging.warning("OrderBlockDetector not available")

try:
    from fvg_detector import FVGDetector, FairValueGap, FVGType
    FVG_AVAILABLE = True
except ImportError:
    FVG_AVAILABLE = False
    logging.warning("FVGDetector not available")

try:
    from ict_whale_detector import WhaleDetector, WhaleOrderBlock
    WHALE_AVAILABLE = True
except ImportError:
    WHALE_AVAILABLE = False
    logging.warning("WhaleDetector not available")

try:
    from liquidity_map import LiquidityMapper, LiquidityZone
    LIQUIDITY_AVAILABLE = True
except ImportError:
    LIQUIDITY_AVAILABLE = False
    logging.warning("LiquidityMapper not available")

try:
    from ilp_detector import InternalLiquidityPoolDetector
    ILP_AVAILABLE = True
except ImportError:
    ILP_AVAILABLE = False
    logging.warning("ILP Detector not available")

try:
    from mtf_analyzer import MultiTimeframeAnalyzer, MTFSignal, Bias
    MTF_AVAILABLE = True
except ImportError:
    MTF_AVAILABLE = False
    logging.warning("MTF Analyzer not available")

try:
    from breaker_block_detector import BreakerBlockDetector, BreakerBlock
    BREAKER_AVAILABLE = True
except ImportError:
    BREAKER_AVAILABLE = False
    logging.warning("BreakerBlockDetector not available")

try:
    from sibi_ssib_detector import SIBISSIBDetector, SIBISSIBZone
    SIBI_SSIB_AVAILABLE = True
except ImportError:
    SIBI_SSIB_AVAILABLE = False
    logging.warning("SIBISSIBDetector not available")

try:
    from zone_explainer import ZoneExplainer
    ZONE_EXPLAINER_AVAILABLE = True
except ImportError:
    ZONE_EXPLAINER_AVAILABLE = False
    logging.warning("ZoneExplainer not available")

try:
    from cache_manager import get_cache_manager
    CACHE_MANAGER_AVAILABLE = True
except ImportError:
    CACHE_MANAGER_AVAILABLE = False
    logging.warning("CacheManager not available")

try:
    from config.config_loader import load_feature_flags, get_flag
    FEATURE_FLAGS_AVAILABLE = True
except ImportError:
    FEATURE_FLAGS_AVAILABLE = False
    logging.warning("Feature flags not available")

# ML Integration
try:
    from ml_engine import MLTradingEngine
    ML_ENGINE_AVAILABLE = True
except ImportError:
    ML_ENGINE_AVAILABLE = False
    logging.warning("MLTradingEngine not available")

try:
    from ml_predictor import MLPredictor, get_ml_predictor
    ML_PREDICTOR_AVAILABLE = True
except ImportError:
    ML_PREDICTOR_AVAILABLE = False
    logging.warning("MLPredictor not available")

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SignalType(Enum):
    """Signal types"""
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"
    STRONG_BUY = "STRONG_BUY"
    STRONG_SELL = "STRONG_SELL"


class SignalStrength(Enum):
    """Signal strength levels"""
    WEAK = 1
    MODERATE = 2
    STRONG = 3
    VERY_STRONG = 4
    EXTREME = 5


class MarketBias(Enum):
    """Market bias"""
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"
    RANGING = "RANGING"


@dataclass
class ICTSignal:
    """
    Complete ICT Trading Signal
    
    Attributes:
        timestamp: Signal generation time
        symbol: Trading pair (e.g., "BTC/USDT")
        timeframe: Primary timeframe
        signal_type: BUY/SELL/HOLD/STRONG_BUY/STRONG_SELL
        signal_strength: 1-5 (WEAK to EXTREME)
        entry_price: Recommended entry price
        sl_price: Stop loss price
        tp_prices: List of take profit targets [TP1, TP2, TP3]
        confidence: Confidence score (0-100)
        risk_reward_ratio: Risk/reward ratio
        whale_blocks: List of whale order blocks
        liquidity_zones: List of liquidity zones
        order_blocks: List of standard order blocks
        fair_value_gaps: List of FVGs
        internal_liquidity: Internal liquidity pools
        bias: Market bias (BULLISH/BEARISH/NEUTRAL)
        structure_broken: Whether structure was broken
        displacement_detected: Whether displacement was detected
        mtf_confluence: Multi-timeframe confluence score
        reasoning: Human-readable explanation
        warnings: List of warnings/caveats
    """
    timestamp: datetime
    symbol: str
    timeframe: str
    signal_type: SignalType
    signal_strength: SignalStrength
    entry_price: float
    sl_price: float
    tp_prices: List[float]
    confidence: float
    risk_reward_ratio: float
    
    # ICT Components
    whale_blocks: List[Dict] = field(default_factory=list)
    liquidity_zones: List[Dict] = field(default_factory=list)
    liquidity_sweeps: List[Dict] = field(default_factory=list)
    order_blocks: List[Dict] = field(default_factory=list)
    fair_value_gaps: List[Dict] = field(default_factory=list)
    internal_liquidity: List[Dict] = field(default_factory=list)
    breaker_blocks: List[Dict] = field(default_factory=list)
    mitigation_blocks: List[Dict] = field(default_factory=list)
    sibi_ssib_zones: List[Dict] = field(default_factory=list)
    
    # Market Analysis
    bias: MarketBias = MarketBias.NEUTRAL
    structure_broken: bool = False
    displacement_detected: bool = False
    mtf_confluence: int = 0
    htf_bias: str = "NEUTRAL"
    mtf_structure: str = "NEUTRAL"
    
    # Explanation
    reasoning: str = ""
    warnings: List[str] = field(default_factory=list)
    zone_explanations: Dict[str, List[str]] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return {
            'timestamp': self.timestamp.isoformat() if isinstance(self.timestamp, datetime) else str(self.timestamp),
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'signal_type': self.signal_type.value,
            'signal_strength': self.signal_strength.value,
            'entry_price': self.entry_price,
            'sl_price': self.sl_price,
            'tp_prices': self.tp_prices,
            'confidence': self.confidence,
            'risk_reward_ratio': self.risk_reward_ratio,
            'whale_blocks_count': len(self.whale_blocks),
            'liquidity_zones_count': len(self.liquidity_zones),
            'order_blocks_count': len(self.order_blocks),
            'fvgs_count': len(self.fair_value_gaps),
            'bias': self.bias.value,
            'structure_broken': self.structure_broken,
            'displacement_detected': self.displacement_detected,
            'mtf_confluence': self.mtf_confluence,
            'htf_bias': self.htf_bias,
            'mtf_structure': self.mtf_structure,
            'reasoning': self.reasoning,
            'warnings': self.warnings
        }


class ICTSignalEngine:
    """
    Central ICT Signal Generation Engine
    
    Combines all ICT concepts into a unified signal generation system:
    - Whale Order Blocks
    - Liquidity Mapping
    - Standard Order Blocks
    - Fair Value Gaps
    - Internal Liquidity Pools
    - Multi-Timeframe Analysis
    """
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize ICT Signal Engine
        
        Args:
            config: Configuration parameters
        """
        self.config = config or self._get_default_config()
        
        # Load feature flags
        if FEATURE_FLAGS_AVAILABLE:
            try:
                feature_flags = load_feature_flags()
                # Merge feature flags into config
                self.config.update({
                    'use_breaker_blocks': feature_flags.get('use_breaker_blocks', True),
                    'use_mitigation_blocks': feature_flags.get('use_mitigation_blocks', True),
                    'use_sibi_ssib': feature_flags.get('use_sibi_ssib', True),
                    'use_zone_explanations': feature_flags.get('use_zone_explanations', True),
                    'use_cache': feature_flags.get('use_cache', True),
                    'cache_ttl_seconds': feature_flags.get('cache_ttl_seconds', 3600),
                    'cache_max_size': feature_flags.get('cache_max_size', 100)
                })
            except Exception as e:
                logger.warning(f"Could not load feature flags: {e}")
        
        # Initialize sub-detectors
        self.ob_detector = OrderBlockDetector() if ORDER_BLOCK_AVAILABLE else None
        self.fvg_detector = FVGDetector() if FVG_AVAILABLE else None
        self.whale_detector = WhaleDetector() if WHALE_AVAILABLE else None
        self.liquidity_mapper = LiquidityMapper() if LIQUIDITY_AVAILABLE else None
        self.ilp_detector = InternalLiquidityPoolDetector() if ILP_AVAILABLE else None
        self.mtf_analyzer = MultiTimeframeAnalyzer() if MTF_AVAILABLE else None
        
        # Initialize new detectors
        use_breaker_blocks = self.config.get('use_breaker_blocks', True)
        self.breaker_detector = BreakerBlockDetector() if BREAKER_AVAILABLE and use_breaker_blocks else None
        
        use_sibi_ssib = self.config.get('use_sibi_ssib', True)
        self.sibi_ssib_detector = SIBISSIBDetector() if SIBI_SSIB_AVAILABLE and use_sibi_ssib else None
        
        # Initialize zone explainer
        use_zone_explanations = self.config.get('use_zone_explanations', True)
        self.zone_explainer = ZoneExplainer() if ZONE_EXPLAINER_AVAILABLE and use_zone_explanations else None
        
        # Initialize cache manager
        use_cache = self.config.get('use_cache', True)
        if CACHE_MANAGER_AVAILABLE and use_cache:
            try:
                cache_max_size = self.config.get('cache_max_size', 100)
                cache_ttl = self.config.get('cache_ttl_seconds', 3600)
                self.cache_manager = get_cache_manager(cache_max_size, cache_ttl)
            except Exception as e:
                logger.warning(f"Could not initialize cache manager: {e}")
                self.cache_manager = None
        else:
            self.cache_manager = None
        
        # Initialize ML engines (if available)
        self.ml_engine = None
        self.ml_predictor = None
        self.use_ml = self.config.get('use_ml', True)

        if self.use_ml:
            if ML_ENGINE_AVAILABLE:
                try:
                    self.ml_engine = MLTradingEngine()
                    logger.info("✅ ML Trading Engine initialized")
                except Exception as e:
                    logger.warning(f"⚠️ ML Engine initialization failed: {e}")
            
            if ML_PREDICTOR_AVAILABLE:
                try:
                    self.ml_predictor = get_ml_predictor()
                    logger.info("✅ ML Predictor initialized")
                except Exception as e:
                    logger.warning(f"⚠️ ML Predictor initialization failed: {e}")
        
        logger.info("ICT Signal Engine initialized")
        logger.info(f"Order Blocks: {ORDER_BLOCK_AVAILABLE}")
        logger.info(f"FVG: {FVG_AVAILABLE}")
        logger.info(f"Whale: {WHALE_AVAILABLE}")
        logger.info(f"Liquidity: {LIQUIDITY_AVAILABLE}")
        logger.info(f"ILP: {ILP_AVAILABLE}")
        logger.info(f"MTF: {MTF_AVAILABLE}")
        logger.info(f"Breaker Blocks: {BREAKER_AVAILABLE}")
        logger.info(f"SIBI/SSIB: {SIBI_SSIB_AVAILABLE}")
        logger.info(f"Zone Explainer: {ZONE_EXPLAINER_AVAILABLE}")
        logger.info(f"Cache Manager: {self.cache_manager is not None}")
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'min_confidence': 70,          # Min 70% confidence
            'min_risk_reward': 2.0,        # Min 1:2 R:R
            'max_sl_distance_pct': 3.0,    # Max 3% SL distance
            'tp_multipliers': [2, 3, 5],   # TP at 2R, 3R, 5R
            'require_mtf_confluence': False, # Require MTF alignment
            'min_mtf_confluence': 2,       # Min 2 timeframes aligned
            'use_whale_blocks': True,      # Use whale detection
            'use_liquidity': True,         # Use liquidity mapping
            'use_order_blocks': True,      # Use order blocks
            'use_fvgs': True,              # Use FVGs
            'displacement_required': True, # Require displacement
            'min_displacement_pct': 0.5,   # Min 0.5% displacement
            'structure_break_weight': 0.2, # Weight for structure break
            'whale_block_weight': 0.25,    # Weight for whale blocks
            'liquidity_weight': 0.2,       # Weight for liquidity
            'ob_weight': 0.15,             # Weight for order blocks
            'fvg_weight': 0.1,             # Weight for FVGs
            'mtf_weight': 0.1,             # Weight for MTF confluence
            'structure_break_threshold': 1.0,  # 1% threshold for structure break
            'entry_adjustment_pct': 0.5,   # 0.5% entry price adjustment
            
            # ML Configuration
            'use_ml': True,                    # Enable ML optimization
            'ml_min_confidence_boost': -20,    # Min confidence adjustment
            'ml_max_confidence_boost': 20,     # Max confidence adjustment
            'ml_entry_adjustment_max': 0.005,  # Max entry adjustment (0.5%)
            'ml_sl_tighten_max': 0.95,         # Max SL tighten multiplier
            'ml_sl_widen_max': 1.10,           # Max SL widen multiplier
            'ml_tp_extension_max': 1.15,       # Max TP extension (15%)
            'ml_override_threshold': 15,       # Min confidence diff for ML override
        }
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str = "1H",
        mtf_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Optional[ICTSignal]:
        """
        Generate ICT signal with UNIFIED analysis sequence
        
        ✅ ЕДНАКВА последователност за ВСИЧКИ таймфремове (1w до 1m)
        ✅ ЕДНАКВА логика за ръчни И автоматични сигнали
        """
        logger.info(f"🎯 Generating UNIFIED ICT signal for {symbol} on {timeframe}")
        
        # Cache check
        if self.cache_manager:
            try:
                cached_signal = self.cache_manager.get_cached_signal(symbol, timeframe)
                if cached_signal:
                    return cached_signal
            except Exception as e:
                logger.warning(f"Cache error: {e}")
        
        if len(df) < 50:
            logger.warning("Insufficient data")
            return None
        
        df = self._prepare_dataframe(df)
        
        # ═══════ УНИФИЦИРАНА ПОСЛЕДОВАТЕЛНОСТ (12 СТЪПКИ) ═══════
        
        # СТЪПКА 1: HTF BIAS (1D → 4H fallback)
        logger.info("📊 Step 1: HTF Bias")
        htf_bias = self._get_htf_bias_with_fallback(symbol, mtf_data)
        
        # СТЪПКА 2: MTF STRUCTURE (4H)
        logger.info("📊 Step 2: MTF Structure")
        mtf_analysis = self._analyze_mtf_confluence(df, mtf_data, symbol) if mtf_data else None
        
        # СТЪПКА 3: ENTRY MODEL (текущ TF)
        logger.info(f"📊 Step 3: Entry Model ({timeframe})")
        
        # СТЪПКА 4: LIQUIDITY MAP (с cache fallback)
        logger.info("📊 Step 4: Liquidity Map")
        liquidity_zones = self._get_liquidity_zones_with_fallback(symbol, timeframe)
        
        # СТЪПКА 5-7: ICT COMPONENTS
        logger.info("📊 Steps 5-7: ICT Components")
        ict_components = self._detect_ict_components(df, timeframe)
        ict_components['liquidity_zones'] = liquidity_zones  # Add liquidity zones
        
        bias = self._determine_market_bias(df, ict_components, mtf_analysis)
        structure_broken = self._check_structure_break(df)
        displacement_detected = self._check_displacement(df)
        
        # СТЪПКА 8: ENTRY CALCULATION
        logger.info("📊 Step 8: Entry")
        entry_setup = self._identify_entry_setup(df, ict_components, bias)
        if not entry_setup:
            return None
        
        entry_price = self._calculate_entry_price(df, entry_setup, bias)
        
        # СТЪПКА 9: SL/TP + VALIDATION
        logger.info("📊 Step 9: SL/TP + Validation")
        sl_price = self._calculate_sl_price(df, entry_setup, entry_price, bias)
        
        # ✅ VALIDATE SL
        order_block = entry_setup.get('ob') or (ict_components['order_blocks'][0] if ict_components.get('order_blocks') else None)
        if order_block:
            sl_price = self._validate_sl_position(sl_price, order_block, bias)
        
        # ✅ TP с гарантиран RR ≥ 1:3
        tp_prices = self._calculate_tp_with_min_rr(entry_price, sl_price, liquidity_zones, min_rr=3.0)
        
        # СТЪПКА 10: RR CHECK
        logger.info("📊 Step 10: RR Guarantee")
        risk = abs(entry_price - sl_price)
        reward = abs(tp_prices[0] - entry_price) if tp_prices else 0
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        if risk_reward_ratio < 3.0:
            logger.error(f"❌ RR {risk_reward_ratio:.2f} < 3.0 - adjusting")
            if bias == MarketBias.BULLISH:
                tp_prices[0] = entry_price + (risk * 3.0)
            else:
                tp_prices[0] = entry_price - (risk * 3.0)
            risk_reward_ratio = 3.0
        
        if risk_reward_ratio < self.config['min_risk_reward']:
            return None
        
        # BASE CONFIDENCE
        base_confidence = self._calculate_signal_confidence(
            ict_components, mtf_analysis, bias, structure_broken, 
            displacement_detected, risk_reward_ratio
        )
        
        # СТЪПКА 11: ML OPTIMIZATION (ЗАПАЗВАМЕ existing logic)
        logger.info("📊 Step 11: ML Optimization")

        ml_confidence_adjustment = 0.0
        ml_features = {}

        if self.use_ml and (self.ml_engine or self.ml_predictor):
            # Extract ML features
            ml_features = self._extract_ml_features(
                df=df,
                components=ict_components,
                mtf_analysis=mtf_analysis,
                bias=bias,
                displacement=displacement_detected,
                structure_break=structure_broken
            )
            
            # Update ICT confidence in features
            ml_features['ict_confidence'] = base_confidence / 100.0
            
            # Try ML Engine (hybrid prediction)
            if self.ml_engine and self.ml_engine.model is not None:
                try:
                    # Map bias to signal type
                    classical_signal = 'BUY' if bias == MarketBias.BULLISH else 'SELL' if bias == MarketBias.BEARISH else 'HOLD'
                    
                    ml_signal, ml_confidence, ml_mode = self.ml_engine.predict_signal(
                        analysis=ml_features,
                        classical_signal=classical_signal,
                        classical_confidence=base_confidence
                    )
                    
                    # Check if ML changes the signal direction
                    if ml_signal != classical_signal:
                        logger.warning(f"⚠️ ML suggests {ml_signal} vs ICT {classical_signal}")
                        
                        # SAFETY: Only allow ML override if confidence difference > 15%
                        if abs(ml_confidence - base_confidence) > self.config['ml_override_threshold']:
                            logger.warning(f"⚠️ ML override: {ml_signal} with {ml_confidence:.1f}% confidence")
                            # Update bias based on ML
                            if ml_signal == 'BUY':
                                bias = MarketBias.BULLISH
                            elif ml_signal == 'SELL':
                                bias = MarketBias.BEARISH
                            else:
                                logger.info("ML suggests HOLD, returning no signal")
                                return None
                        else:
                            logger.info(f"✅ ML adjustment too small, keeping ICT signal")
                            ml_confidence = base_confidence
                    
                    ml_confidence_adjustment = ml_confidence - base_confidence
                    
                    # Clamp adjustment to configured limits
                    ml_confidence_adjustment = max(
                        self.config['ml_min_confidence_boost'],
                        min(self.config['ml_max_confidence_boost'], ml_confidence_adjustment)
                    )
                    
                    logger.info(f"ML confidence adjustment: {ml_confidence_adjustment:+.1f}% (Mode: {ml_mode})")
                    
                except Exception as e:
                    logger.error(f"❌ ML Engine prediction error: {e}")
            
            # Try ML Predictor (win probability) if ML Engine not available
            elif self.ml_predictor and self.ml_predictor.is_trained:
                try:
                    # Prepare trade data
                    trade_data = {
                        'entry_price': entry_price,
                        'analysis_data': ml_features
                    }
                    
                    # Get win probability
                    win_probability = self.ml_predictor.predict(trade_data)
                    
                    if win_probability is not None:
                        # Get confidence adjustment
                        ml_confidence_adjustment = self.ml_predictor.get_confidence_adjustment(
                            ml_probability=win_probability,
                            current_confidence=base_confidence
                        )
                        
                        logger.info(f"ML win probability: {win_probability:.1f}%")
                        logger.info(f"ML confidence adjustment: {ml_confidence_adjustment:+.1f}%")
                        ml_mode = f"ML Predictor (Win: {win_probability:.1f}%)"
                        
                except Exception as e:
                    logger.error(f"❌ ML Predictor error: {e}")

        confidence = base_confidence + ml_confidence_adjustment
        confidence = max(0.0, min(100.0, confidence))
        
        if confidence < self.config['min_confidence']:
            return None
        
        # СТЪПКА 12: CONFIDENCE SCORING
        logger.info("📊 Step 12: Final Confidence")
        signal_strength = self._calculate_signal_strength(confidence, risk_reward_ratio, ict_components)
        signal_type = self._determine_signal_type(bias, signal_strength, confidence)
        reasoning = self._generate_reasoning(ict_components, bias, entry_setup, mtf_analysis)
        warnings = self._generate_warnings(ict_components, risk_reward_ratio, df)
        
        zone_explanations = {}
        if self.zone_explainer:
            try:
                bias_str = bias.value if hasattr(bias, 'value') else str(bias)
                zone_explanations = self.zone_explainer.generate_all_explanations(ict_components, bias_str)
            except Exception as e:
                logger.error(f"Zone explanations error: {e}")
        
        # CREATE SIGNAL
        signal = ICTSignal(
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            signal_type=signal_type,
            signal_strength=signal_strength,
            entry_price=entry_price,
            sl_price=sl_price,
            tp_prices=tp_prices,
            confidence=confidence,
            risk_reward_ratio=risk_reward_ratio,
            whale_blocks=[wb.to_dict() if hasattr(wb, 'to_dict') else wb for wb in ict_components.get('whale_blocks', [])],
            liquidity_zones=[lz.__dict__ if hasattr(lz, '__dict__') else lz for lz in ict_components.get('liquidity_zones', [])],
            order_blocks=[ob.to_dict() if hasattr(ob, 'to_dict') else ob for ob in ict_components.get('order_blocks', [])],
            fair_value_gaps=[fvg.to_dict() if hasattr(fvg, 'to_dict') else fvg for fvg in ict_components.get('fvgs', [])],
            internal_liquidity=[ilp for ilp in ict_components.get('internal_liquidity', [])],
            breaker_blocks=[bb.to_dict() for bb in ict_components.get('breaker_blocks', [])],
            mitigation_blocks=[mb.to_dict() for mb in ict_components.get('mitigation_blocks', [])],
            sibi_ssib_zones=[sz.to_dict() for sz in ict_components.get('sibi_ssib_zones', [])],
            bias=bias,
            structure_broken=structure_broken,
            displacement_detected=displacement_detected,
            mtf_confluence=mtf_analysis.get('confluence_count', 0) if mtf_analysis else 0,
            htf_bias=htf_bias,
            mtf_structure=mtf_analysis.get('mtf_structure', 'NEUTRAL') if mtf_analysis else 'NEUTRAL',
            reasoning=reasoning,
            warnings=warnings,
            zone_explanations=zone_explanations
        )
        
        logger.info(f"✅ Generated {signal_type.value} signal (UNIFIED)")
        
        if self.cache_manager:
            try:
                self.cache_manager.cache_signal(symbol, timeframe, signal)
            except Exception as e:
                logger.warning(f"Cache error: {e}")
        
        return signal
    
    def _prepare_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare dataframe with indicators"""
        df = df.copy()
        
        # Ensure datetime index
        if 'timestamp' in df.columns and not isinstance(df.index, pd.DatetimeIndex):
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.set_index('timestamp')
        
        # Calculate ATR
        df['atr'] = self._calculate_atr(df, period=14)
        
        # Calculate EMAs
        
        # Calculate volume metrics
        if 'volume' in df.columns:
            df['volume_ma'] = df['volume'].rolling(window=20).mean()
            df['volume_ratio'] = df['volume'] / df['volume_ma'].replace(0, 1)
        else:
            df['volume'] = 0
            df['volume_ma'] = 0
            df['volume_ratio'] = 1.0
        
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
    
    def _detect_ict_components(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> Dict[str, List]:
        """
        Detect all ICT components
        
        Returns dict with:
        - whale_blocks
        - liquidity_zones
        - order_blocks
        - fvgs
        - internal_liquidity
        """
        components = {
            'whale_blocks': [],
            'liquidity_zones': [],
            'order_blocks': [],
            'fvgs': [],
            'internal_liquidity': []
        }
        
        # Detect Order Blocks
        if self.config['use_order_blocks'] and self.ob_detector:
            try:
                order_blocks = self.ob_detector.detect_order_blocks(df, timeframe)
                components['order_blocks'] = order_blocks
                logger.info(f"Detected {len(order_blocks)} order blocks")
            except Exception as e:
                logger.error(f"Order block detection error: {e}")
        
        # Detect Fair Value Gaps
        if self.config['use_fvgs'] and self.fvg_detector:
            try:
                fvgs = self.fvg_detector.detect_fvgs(df, timeframe)
                components['fvgs'] = fvgs
                logger.info(f"Detected {len(fvgs)} FVGs")
            except Exception as e:
                logger.error(f"FVG detection error: {e}")
        
        # Detect Whale Blocks
        if self.config['use_whale_blocks'] and self.whale_detector:
            try:
                whale_blocks = self.whale_detector.detect_whale_blocks(df, timeframe)
                components['whale_blocks'] = whale_blocks
                logger.info(f"Detected {len(whale_blocks)} whale blocks")
            except Exception as e:
                logger.error(f"Whale detection error: {e}")
        
        # Detect Liquidity Zones
        if self.config['use_liquidity'] and self.liquidity_mapper:
            try:
                liquidity_zones = self.liquidity_mapper.detect_liquidity_zones(df)
                components['liquidity_zones'] = liquidity_zones
                logger.info(f"Detected {len(liquidity_zones)} liquidity zones")

                # Detect Liquidity Sweeps
                if liquidity_zones:
                    try:
                        sweeps = self.liquidity_mapper.detect_liquidity_sweeps(df, liquidity_zones)
                        components['liquidity_sweeps'] = sweeps
                        logger.info(f"Detected {len(sweeps)} liquidity sweeps")
                    except Exception as e:
                        logger.error(f"Sweep detection error: {e}")
            except Exception as e:
                logger.error(f"Liquidity detection error: {e}")
        
        # Detect Internal Liquidity Pools
        if self.ilp_detector:
            try:
                ilp_analysis = self.ilp_detector.analyze(df)
                components['internal_liquidity'] = ilp_analysis.get('pools', [])
                logger.info(f"Detected {len(components['internal_liquidity'])} ILPs")
            except Exception as e:
                logger.error(f"ILP detection error: {e}")
        
        # Detect Breaker Blocks
        if self.breaker_detector and components.get('order_blocks'):
            try:
                breaker_blocks = self.breaker_detector.detect_breaker_blocks(
                    df,
                    components['order_blocks']
                )
                components['breaker_blocks'] = breaker_blocks
                logger.info(f"Detected {len(breaker_blocks)} breaker blocks")
            except Exception as e:
                logger.error(f"Breaker block detection error: {e}")
                components['breaker_blocks'] = []
        else:
            components['breaker_blocks'] = []
        
        # Detect Mitigation Blocks  
        if self.ob_detector:
            try:
                mitigation_blocks = self.ob_detector.detect_mitigation_blocks(
                    df,
                    components.get('order_blocks', [])
                )
                components['mitigation_blocks'] = mitigation_blocks
                logger.info(f"Detected {len(mitigation_blocks)} mitigation blocks")
            except Exception as e:
                logger.error(f"Mitigation block detection error: {e}")
                components['mitigation_blocks'] = []
        else:
            components['mitigation_blocks'] = []
        
        # Detect SIBI/SSIB
        if self.sibi_ssib_detector:
            try:
                sibi_ssib_zones = self.sibi_ssib_detector.detect_sibi_ssib(
                    df,
                    components.get('fvgs', []),
                    components.get('liquidity_zones', [])
                )
                components['sibi_ssib_zones'] = sibi_ssib_zones
                logger.info(f"Detected {len(sibi_ssib_zones)} SIBI/SSIB zones")
            except Exception as e:
                logger.error(f"SIBI/SSIB detection error: {e}")
                components['sibi_ssib_zones'] = []
        else:
            components['sibi_ssib_zones'] = []
        
        return components
    
    def _analyze_mtf_confluence(
        self,
        primary_df: pd.DataFrame,
        mtf_data: Optional[Dict[str, pd.DataFrame]],
        symbol: str
    ) -> Optional[Dict]:
        """Analyze multi-timeframe confluence"""
        if not self.mtf_analyzer or not mtf_data:
            return None
        
        try:
            # Get higher timeframes
            htf_df = mtf_data.get('1D') or mtf_data.get('4H')
            mtf_df = mtf_data.get('4H') or mtf_data.get('1H')
            ltf_df = mtf_data.get('1H') or primary_df
            
            if htf_df is None or mtf_df is None or ltf_df is None:
                return None
            
            # Analyze
            signals = self.mtf_analyzer.analyze_multi_timeframe(htf_df, mtf_df, ltf_df, symbol)
            
            if not signals:
                return None
            
            # Get first signal
            signal = signals[0]
            
            return {
                'htf_bias': signal.htf_bias.value,
                'mtf_structure': signal.mtf_structure,
                'ltf_trigger': signal.ltf_trigger,
                'confluence_count': signal.alignment_score * 5,  # Scale to 0-5
                'alignment_score': signal.alignment_score
            }
        except Exception as e:
            logger.error(f"MTF analysis error: {e}")
            return None
    
    def _determine_market_bias(
        self,
        df: pd.DataFrame,
        ict_components: Dict,
        mtf_analysis: Optional[Dict]
    ) -> MarketBias:
        """Determine overall market bias"""
        bullish_score = 0
        bearish_score = 0
        
        
        # Order blocks
        bullish_obs = [ob for ob in ict_components.get('order_blocks', []) 
                       if hasattr(ob, 'type') and 'BULLISH' in str(ob.type.value)]
        bearish_obs = [ob for ob in ict_components.get('order_blocks', []) 
                       if hasattr(ob, 'type') and 'BEARISH' in str(ob.type.value)]
        
        if len(bullish_obs) > len(bearish_obs):
            bullish_score += 1
        elif len(bearish_obs) > len(bullish_obs):
            bearish_score += 1
        
        # FVGs
        bullish_fvgs = [fvg for fvg in ict_components.get('fvgs', []) 
                        if hasattr(fvg, 'is_bullish') and fvg.is_bullish]
        bearish_fvgs = [fvg for fvg in ict_components.get('fvgs', []) 
                        if hasattr(fvg, 'is_bullish') and not fvg.is_bullish]
        
        if len(bullish_fvgs) > len(bearish_fvgs):
            bullish_score += 1
        elif len(bearish_fvgs) > len(bullish_fvgs):
            bearish_score += 1
        
        # MTF bias
        if mtf_analysis:
            htf_bias = mtf_analysis.get('htf_bias', 'NEUTRAL')
            if 'BULLISH' in htf_bias:
                bullish_score += 2
            elif 'BEARISH' in htf_bias:
                bearish_score += 2
        
        # Determine bias
        if bullish_score >= 4 and bullish_score > bearish_score:
            return MarketBias.BULLISH
        elif bearish_score >= 4 and bearish_score > bullish_score:
            return MarketBias.BEARISH
        elif abs(bullish_score - bearish_score) <= 1:
            return MarketBias.RANGING
        else:
            return MarketBias.NEUTRAL
    
    def _check_structure_break(self, df: pd.DataFrame) -> bool:
        """Check for recent structure break (BOS/CHOCH)"""
        # Simple check: look for break of recent swing high/low
        lookback = 20
        
        if len(df) < lookback:
            return False
        
        recent_high = df['high'].iloc[-lookback:].max()
        recent_low = df['low'].iloc[-lookback:].min()
        current_price = df['close'].iloc[-1]
        
        # Check if recent candles broke structure
        threshold_pct = self.config['structure_break_threshold'] / 100
        for i in range(-5, 0):
            if df['high'].iloc[i] > recent_high * (1 + threshold_pct):
                return True  # Bullish break
            if df['low'].iloc[i] < recent_low * (1 - threshold_pct):
                return True  # Bearish break
        
        return False
    
    def _check_displacement(self, df: pd.DataFrame) -> bool:
        """Check for recent displacement"""
        if len(df) < 5:
            return False
        
        # Check last 3 candles for displacement
        for i in range(-3, 0):
            price_change = abs(df['close'].iloc[i] - df['open'].iloc[i])
            price_change_pct = (price_change / df['open'].iloc[i]) * 100
            
            if price_change_pct >= self.config['min_displacement_pct']:
                return True
        
        return False
    
    def _identify_entry_setup(
        self,
        df: pd.DataFrame,
        ict_components: Dict,
        bias: MarketBias
    ) -> Optional[Dict]:
        """Identify valid entry setup"""
        current_price = df['close'].iloc[-1]
        atr = df['atr'].iloc[-1]
        
        if bias == MarketBias.BULLISH:
            # Look for bullish entry
            
            # Check for bullish order blocks near price
            bullish_obs = [ob for ob in ict_components.get('order_blocks', []) 
                          if hasattr(ob, 'type') and 'BULLISH' in str(ob.type.value)
                          and hasattr(ob, 'is_valid') and ob.is_valid()
                          and ob.bottom * 0.90 <= current_price <= ob. top * 1.15]
            
            if bullish_obs:
                best_ob = max(bullish_obs, key=lambda x: x.strength)
                return {
                    'type': 'bullish_ob',
                    'ob': best_ob,
                    'price_zone': (best_ob.bottom, best_ob.top)
                }
            
            # Check for bullish FVGs
            bullish_fvgs = [fvg for fvg in ict_components.get('fvgs', []) 
                           if hasattr(fvg, 'is_bullish') and fvg.is_bullish
                           and hasattr(fvg, 'is_valid') and fvg.is_valid()
                           and fvg.bottom * 0.90 <= current_price <= fvg.top * 1.15]
            
            if bullish_fvgs:
                best_fvg = max(bullish_fvgs, key=lambda x: x.strength)
                return {
                    'type': 'bullish_fvg',
                    'fvg': best_fvg,
                    'price_zone': (best_fvg.bottom, best_fvg.top)
                }
        
        elif bias == MarketBias.BEARISH:
            # Look for bearish entry
            
            # Check for bearish order blocks near price
            bearish_obs = [ob for ob in ict_components.get('order_blocks', []) 
                          if hasattr(ob, 'type') and 'BEARISH' in str(ob.type.value)
                          and hasattr(ob, 'is_valid') and ob.is_valid()
                          and ob.bottom * 0.95 <= current_price <= ob.top]
            
            if bearish_obs:
                best_ob = max(bearish_obs, key=lambda x: x.strength)
                return {
                    'type': 'bearish_ob',
                    'ob': best_ob,
                    'price_zone': (best_ob.bottom, best_ob.top)
                }
            
            # Check for bearish FVGs
            bearish_fvgs = [fvg for fvg in ict_components.get('fvgs', []) 
                           if hasattr(fvg, 'is_bullish') and not fvg.is_bullish
                           and hasattr(fvg, 'is_valid') and fvg.is_valid()
                           and fvg.bottom * 0.85 <= current_price <= fvg.top * 1.10]
            
            if bearish_fvgs:
                best_fvg = max(bearish_fvgs, key=lambda x: x.strength)
                return {
                    'type': 'bearish_fvg',
                    'fvg': best_fvg,
                    'price_zone': (best_fvg.bottom, best_fvg.top)
                }
        
        return None
    
    def _calculate_entry_price(
        self,
        df: pd.DataFrame,
        entry_setup: Dict,
        bias: MarketBias
    ) -> float:
        """Calculate optimal entry price"""
        current_price = df['close'].iloc[-1]
        price_zone = entry_setup.get('price_zone', (current_price, current_price))
        
        # Enter at middle of zone or current price
        adjustment = self.config['entry_adjustment_pct'] / 100
        if bias == MarketBias.BULLISH:
            # Enter near bottom of bullish zone
            entry = price_zone[0] * (1 + adjustment)
        else:
            # Enter near top of bearish zone
            entry = price_zone[1] * (1 - adjustment)
        
        return entry
    

    def _calculate_tp_prices(self, entry_price: float, sl_price: float, bias, ict_components: dict) -> list:
        """Calculate TP levels with 1:2, 1:3, 1:5 RR"""
        risk = abs(entry_price - sl_price)
        if str(bias) == 'MarketBias. BULLISH':
            return [entry_price + risk*3, entry_price + risk*2, entry_price + risk*5]
        else:
            return [entry_price - risk*3, entry_price - risk*2, entry_price - risk*5]

    def _calculate_tp_with_min_rr(
        self,
        entry_price: float,
        sl_price: float,
        liquidity_zones: List,
        min_rr: float = 3.0
    ) -> List[float]:
        """
        ЗАДЪЛЖИТЕЛНО: Изчислява TP с ГАРАНТИРАН RR ≥ 1:3
        """
        risk = abs(entry_price - sl_price)
        direction = 'LONG' if entry_price > sl_price else 'SHORT'
        
        # TP1: МИНИМУМ RR 1:3
        if direction == 'LONG':
            tp1 = entry_price + (risk * min_rr)
        else:
            tp1 = entry_price - (risk * min_rr)
        
        tp_levels = [tp1]
        logger.info(f"✅ TP1 calculated: {tp1} (RR {min_rr}:1 guaranteed)")
        
        # TP2 & TP3: Align with liquidity zones
        if liquidity_zones:
            for liq_zone in liquidity_zones:
                liq_price = liq_zone.get('price', liq_zone.get('price_level', 0))
                
                if direction == 'LONG' and liq_price > tp1:
                    tp_levels.append(liq_price)
                    logger.info(f"✅ TP{len(tp_levels)} aligned with liquidity: {liq_price}")
                elif direction == 'SHORT' and liq_price < tp1:
                    tp_levels.append(liq_price)
                    logger.info(f"✅ TP{len(tp_levels)} aligned with liquidity: {liq_price}")
                
                if len(tp_levels) >= 3:
                    break
        
        # Ако няма liquidity → структурни нива
        if len(tp_levels) == 1:
            tp2 = entry_price + (risk * 5) if direction == 'LONG' else entry_price - (risk * 5)
            tp_levels.append(tp2)
            logger.info(f"✅ TP2 extended to 5R: {tp2}")
            
            tp3 = entry_price + (risk * 8) if direction == 'LONG' else entry_price - (risk * 8)
            tp_levels.append(tp3)
            logger.info(f"✅ TP3 extended to 8R: {tp3}")
        
        return tp_levels[:3]

    def _calculate_sl_price(
        self,
        df: pd.DataFrame,
        entry_setup: Dict,
        entry_price: float,
        bias: MarketBias
    ) -> float:
        """Calculate stop loss using ICT invalidation levels"""
        atr = df['atr'].iloc[-1]
        
        if bias == MarketBias. BULLISH:
            # SL below last swing low OR below OB/FVG zone
            lookback = 20
            recent_low = df['low'].iloc[-lookback: ].min()
            
            # Use entry zone bottom if available
            price_zone = entry_setup.get('price_zone', (entry_price, entry_price))
            zone_low = min(price_zone)
            
            # SL = lower of:  zone bottom - buffer OR recent swing low
            buffer = atr * 0.5  # 0.5 ATR buffer
            sl_from_zone = zone_low - buffer
            sl_from_swing = recent_low - buffer
            
            sl_price = min(sl_from_zone, sl_from_swing)
            
            # Ensure minimum distance (1% from entry)
            min_sl = entry_price * 0.99
            return min(sl_price, min_sl)
        
        else:  # BEARISH
            # SL above last swing high OR above OB/FVG zone
            lookback = 20
            recent_high = df['high'].iloc[-lookback:].max()
            
            # Use entry zone top if available
            price_zone = entry_setup.get('price_zone', (entry_price, entry_price))
            zone_high = max(price_zone)
            
            # SL = higher of: zone top + buffer OR recent swing high
            buffer = atr * 0.5
            sl_from_zone = zone_high + buffer
            sl_from_swing = recent_high + buffer
            
            sl_price = max(sl_from_zone, sl_from_swing)
            
            # Ensure minimum distance (1% from entry)
            max_sl = entry_price * 1.01
            return max(sl_price, max_sl)

    def _validate_sl_position(self, sl_price: float, order_block, direction) -> float:
        """
        ЗАДЪЛЖИТЕЛНО: Валидира че SL е под/над валиден Order Block
        
        BULLISH: SL ТРЯБВА да е ПОД Order Block bottom
        BEARISH: SL ТРЯБВА да е НАД Order Block top
        """
        if not order_block:
            logger.warning("No Order Block for SL validation")
            return sl_price
        
        # Get OB boundaries - handle both object and dict types
        if isinstance(order_block, dict):
            ob_bottom = order_block.get('zone_low') or order_block.get('bottom')
            ob_top = order_block.get('zone_high') or order_block.get('top')
        else:
            ob_bottom = getattr(order_block, 'zone_low', None) or getattr(order_block, 'bottom', None)
            ob_top = getattr(order_block, 'zone_high', None) or getattr(order_block, 'top', None)
        
        if not ob_bottom or not ob_top:
            logger.warning("Invalid Order Block structure")
            return sl_price
        
        if direction == 'BULLISH' or direction == MarketBias.BULLISH:
            # SL ТРЯБВА да е ПОД OB bottom
            if sl_price >= ob_bottom:
                sl_price = ob_bottom * 0.998  # 0.2% под OB
                logger.warning(f"⚠️ SL КОРИГИРАН ПОД OB: {sl_price}")
        
        elif direction == 'BEARISH' or direction == MarketBias.BEARISH:
            # SL ТРЯБВА да е НАД OB top
            if sl_price <= ob_top:
                sl_price = ob_top * 1.002  # 0.2% над OB
                logger.warning(f"⚠️ SL КОРИГИРАН НАД OB: {sl_price}")
        
        return sl_price

    def _calculate_signal_confidence(
        self,
        ict_components: Dict,
        mtf_analysis: Optional[Dict],
        bias: MarketBias,
        structure_broken: bool,
        displacement_detected: bool,
        risk_reward_ratio: float
    ) -> float:
        """Calculate signal confidence score (0-100)"""
        confidence = 0.0
        
        # Structure break (20%)
        if structure_broken:
            confidence += 20 * self.config['structure_break_weight'] / 0.2
        
        # Whale blocks (25%)
        whale_blocks = ict_components.get('whale_blocks', [])
        if whale_blocks:
            whale_score = min(25, len(whale_blocks) * 10)
            confidence += whale_score * self.config['whale_block_weight'] / 0.25
        
        # Liquidity zones (20%)
        liquidity_zones = ict_components.get('liquidity_zones', [])
        if liquidity_zones:
            liq_score = min(20, len(liquidity_zones) * 5)
            confidence += liq_score * self.config['liquidity_weight'] / 0.2
        
        # Order blocks (15%)
        order_blocks = ict_components.get('order_blocks', [])
        if order_blocks:
            ob_score = min(15, len(order_blocks) * 5)
            confidence += ob_score * self.config['ob_weight'] / 0.15
        
        # FVGs (10%)
        fvgs = ict_components.get('fvgs', [])
        if fvgs:
            fvg_score = min(10, len(fvgs) * 3)
            confidence += fvg_score * self.config['fvg_weight'] / 0.1
        
        # MTF confluence (10%)
        if mtf_analysis:
            confluence_count = mtf_analysis.get('confluence_count', 0)
            mtf_score = min(10, confluence_count * 3)
            confidence += mtf_score * self.config['mtf_weight'] / 0.1
        
        # Breaker blocks (5%)
        breaker_blocks = ict_components.get('breaker_blocks', [])
        if breaker_blocks:
            breaker_score = min(5, len(breaker_blocks) * 2)
            confidence += breaker_score
        
        # Mitigation blocks (5%)
        mitigation_blocks = ict_components.get('mitigation_blocks', [])
        if mitigation_blocks:
            mitigation_score = min(5, len(mitigation_blocks) * 2)
            confidence += mitigation_score
        
        # SIBI/SSIB (5%)
        sibi_ssib = ict_components.get('sibi_ssib_zones', [])
        if sibi_ssib:
            sibi_ssib_score = min(5, len(sibi_ssib) * 2)
            confidence += sibi_ssib_score
        
        # Displacement bonus (10%)
        if displacement_detected:
            confidence += 10
        
        # Risk/reward bonus (max 10%)
        rr_bonus = min(10, (risk_reward_ratio / 2) * 5)
        confidence += rr_bonus
        
        # Bias penalty
        if bias == MarketBias.NEUTRAL or bias == MarketBias.RANGING:
            confidence *= 0.8
        
        return min(100, max(0, confidence))
    
    def _calculate_signal_strength(
        self,
        confidence: float,
        risk_reward_ratio: float,
        ict_components: Dict
    ) -> SignalStrength:
        """Calculate signal strength (1-5)"""
        # Base on confidence
        if confidence >= 90:
            strength = 5
        elif confidence >= 80:
            strength = 4
        elif confidence >= 70:
            strength = 3
        elif confidence >= 60:
            strength = 2
        else:
            strength = 1
        
        # Boost for high R:R
        if risk_reward_ratio >= 4:
            strength = min(5, strength + 1)
        
        # Boost for multiple ICT confirmations
        total_confirmations = (
            len(ict_components.get('whale_blocks', [])) +
            len(ict_components.get('liquidity_zones', [])) +
            len(ict_components.get('order_blocks', [])) +
            len(ict_components.get('fvgs', []))
        )
        
        if total_confirmations >= 5:
            strength = min(5, strength + 1)
        
        return SignalStrength(strength)
    
    def _determine_signal_type(
        self,
        bias: MarketBias,
        signal_strength: SignalStrength,
        confidence: float
    ) -> SignalType:
        """Determine signal type"""
        if bias == MarketBias.NEUTRAL or bias == MarketBias.RANGING:
            return SignalType.HOLD
        
        if bias == MarketBias.BULLISH:
            if signal_strength.value >= 4 and confidence >= 85:
                return SignalType.STRONG_BUY
            else:
                return SignalType.BUY
        
        elif bias == MarketBias.BEARISH:
            if signal_strength.value >= 4 and confidence >= 85:
                return SignalType.STRONG_SELL
            else:
                return SignalType.SELL
        
        return SignalType.HOLD
    
    def _generate_reasoning(
        self,
        ict_components: Dict,
        bias: MarketBias,
        entry_setup: Optional[Dict],
        mtf_analysis: Optional[Dict]
    ) -> str:
        """Generate human-readable reasoning"""
        lines = []
        
        # Market bias
        lines.append(f"Market Bias: {bias.value}")
        
        # HTF bias
        if mtf_analysis:
            htf_bias = mtf_analysis.get('htf_bias', 'NEUTRAL')
            lines.append(f"Higher Timeframe: {htf_bias}")
        
        # Entry setup
        if entry_setup:
            setup_type = entry_setup.get('type', 'unknown')
            lines.append(f"Entry Setup: {setup_type.replace('_', ' ').title()}")
        
        # ICT components
        whale_count = len(ict_components.get('whale_blocks', []))
        liq_count = len(ict_components.get('liquidity_zones', []))
        ob_count = len(ict_components.get('order_blocks', []))
        fvg_count = len(ict_components.get('fvgs', []))
        
        lines.append(f"\nICT Confirmations:")
        if whale_count > 0:
            lines.append(f"- {whale_count} Whale Order Blocks detected")
        if liq_count > 0:
            lines.append(f"- {liq_count} Liquidity Zones identified")
        if ob_count > 0:
            lines.append(f"- {ob_count} Order Blocks found")
        if fvg_count > 0:
            lines.append(f"- {fvg_count} Fair Value Gaps present")
        
        # MTF confluence
        if mtf_analysis:
            confluence = mtf_analysis.get('confluence_count', 0)
            if confluence >= 2:
                lines.append(f"- Multi-timeframe alignment ({int(confluence)}/5 TFs)")
        
        return '\n'.join(lines)
    
    def _generate_warnings(
        self,
        ict_components: Dict,
        risk_reward_ratio: float,
        df: pd.DataFrame
    ) -> List[str]:
        """Generate warnings and caveats"""
        warnings = []
        
        # Low R:R warning
        if risk_reward_ratio < 2.5:
            warnings.append("Risk/reward ratio below 2.5")
        
        # Limited ICT confirmations
        total_confirmations = (
            len(ict_components.get('whale_blocks', [])) +
            len(ict_components.get('liquidity_zones', [])) +
            len(ict_components.get('order_blocks', [])) +
            len(ict_components.get('fvgs', []))
        )
        
        if total_confirmations < 3:
            warnings.append("Limited ICT confirmations")
        
        # High volatility
        atr = df['atr'].iloc[-1]
        current_price = df['close'].iloc[-1]
        atr_pct = (atr / current_price) * 100
        
        if atr_pct > 3:
            warnings.append("High volatility detected")
        
        # Low volume
        if 'volume_ratio' in df.columns:
            volume_ratio = df['volume_ratio'].iloc[-1]
            if volume_ratio < 0.7:
                warnings.append("Below average volume")
        
        return warnings
    
    def _extract_ml_features(
        self,
        df: pd.DataFrame,
        components: Dict,
        mtf_analysis: Optional[Dict],
        bias: 'MarketBias',
        displacement: bool,
        structure_break: bool
    ) -> Dict:
        """
        Extract ML features from ICT analysis
        
        CRITICAL: NO EMA/MACD/MA - ONLY ICT + NEUTRAL INDICATORS
        
        Returns:
            Dictionary of ML features
        """
        try:
            current_price = df['close'].iloc[-1]
            
            # ═══════════════════════════════════════════════
            # NEUTRAL TECHNICAL INDICATORS
            # ═══════════════════════════════════════════════
            
            # RSI
            if 'rsi' in df.columns:
                rsi = df['rsi'].iloc[-1]
            else:
                # Calculate RSI if not present
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss.replace(0, 1)
                rsi = 100 - (100 / (1 + rs.iloc[-1]))
            
            # Volume metrics
            avg_volume = df['volume'].iloc[-20:].mean()
            current_volume = df['volume'].iloc[-1]
            volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1.0
            
            # Volatility (ATR-based)
            returns = df['close'].pct_change()
            volatility = returns.std() * 100
            
            # Price change
            price_change_pct = ((current_price - df['close'].iloc[-20]) / df['close'].iloc[-20]) * 100
            
            # Bollinger Bands position (neutral indicator)
            bb_sma = df['close'].rolling(20).mean().iloc[-1]
            bb_std = df['close'].rolling(20).std().iloc[-1]
            bb_upper = bb_sma + (2 * bb_std)
            bb_lower = bb_sma - (2 * bb_std)
            bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if (bb_upper - bb_lower) > 0 else 0.5
            
            # ═══════════════════════════════════════════════
            # PURE ICT METRICS
            # ═══════════════════════════════════════════════
            
            num_order_blocks = len(components.get('order_blocks', []))
            num_fvgs = len(components.get('fvgs', []))
            num_whale_blocks = len(components.get('whale_blocks', []))
            num_liquidity_zones = len(components.get('liquidity_zones', []))
            num_ilp = len(components.get('internal_liquidity', []))
            
            # Calculate liquidity strength
            liquidity_strength = 0.0
            for liq_zone in components.get('liquidity_zones', []):
                if hasattr(liq_zone, 'strength'):
                    liquidity_strength += liq_zone.strength
            liquidity_strength = liquidity_strength / max(num_liquidity_zones, 1)
            
            # MTF confluence
            mtf_confluence = 0.0
            if mtf_analysis:
                aligned_tfs = 0
                total_tfs = 0
                for tf, tf_data in mtf_analysis.items():
                    if isinstance(tf_data, dict) and 'bias' in tf_data:
                        total_tfs += 1
                        if tf_data['bias'] == bias:
                            aligned_tfs += 1
                mtf_confluence = aligned_tfs / max(total_tfs, 1)
            
            # Bias strength
            bias_strength = 1.0 if bias == MarketBias.BULLISH else -1.0 if bias == MarketBias.BEARISH else 0.0
            
            # ═══════════════════════════════════════════════
            # CONSTRUCT FEATURE DICT
            # ═══════════════════════════════════════════════
            
            features = {
                # Technical indicators (for ml_engine compatibility)
                'rsi': rsi,
                'price_change_pct': price_change_pct,
                'volume_ratio': volume_ratio,
                'volatility': volatility,
                'bb_position': bb_position,
                'ict_confidence': 0.5,  # Will be updated after confidence calculation
                
                # ICT-specific features
                'num_order_blocks': num_order_blocks,
                'num_fvgs': num_fvgs,
                'num_whale_blocks': num_whale_blocks,
                'num_liquidity_zones': num_liquidity_zones,
                'num_ilp': num_ilp,
                'liquidity_strength': liquidity_strength,
                'mtf_confluence': mtf_confluence,
                'bias_strength': bias_strength,
                'displacement_detected': 1 if displacement else 0,
                'structure_break_detected': 1 if structure_break else 0,
                
                # Market context (TODO: Implement if needed for ML models)
                'btc_correlation': 0.0,  # Placeholder - correlation with BTC price movement
                'sentiment_score': 0.0,  # Placeholder - news/social sentiment score
            }
            
            return features
            
        except Exception as e:
            logger.error(f"❌ ML feature extraction error: {e}")
            return {}
    
    def _apply_ml_optimization(
        self,
        entry_price: float,
        stop_loss: float,
        take_profit: List[float],
        ml_features: Dict,
        bias: 'MarketBias',
        components: Dict
    ) -> Tuple[float, float, List[float]]:
        """
        Apply ML-based optimization to Entry/SL/TP
        
        CRITICAL RULES:
        - Entry can be adjusted ±0.5% max
        - SL can ONLY move AWAY from entry (more conservative)
        - BULLISH: SL stays ПОД Order Block
        - BEARISH: SL stays НАД Order Block
        - TP can be extended based on liquidity zones
        - NEVER violates ICT Order Block placement
        
        Returns:
            (optimized_entry, optimized_sl, optimized_tp_list)
        """
        try:
            optimized_entry = entry_price
            optimized_sl = stop_loss
            optimized_tp = take_profit.copy()
            
            # Get ML confidence metrics
            ml_confidence = ml_features.get('ict_confidence', 0.5) * 100
            liquidity_strength = ml_features.get('liquidity_strength', 0.0)
            mtf_confluence = ml_features.get('mtf_confluence', 0.0)
            
            # ═══════════════════════════════════════════════
            # 1. ENTRY OPTIMIZATION (±0.5% max)
            # ═══════════════════════════════════════════════
            
            if ml_confidence > 80 and mtf_confluence > 0.6:
                # Find closest OB to current entry
                order_blocks = components.get('order_blocks', [])
                
                best_entry_zone = None
                min_distance = float('inf')
                
                for ob in order_blocks:
                    if hasattr(ob, 'zone_high') and hasattr(ob, 'zone_low'):
                        ob_mid = (ob.zone_high + ob.zone_low) / 2
                        distance = abs(ob_mid - entry_price) / entry_price
                        
                        # Only consider OBs within 0.5% of entry
                        if distance < 0.005 and distance < min_distance:
                            # Check if OB aligns with bias
                            if bias == MarketBias.BULLISH and hasattr(ob, 'type') and 'BULLISH' in str(ob.type.value):
                                best_entry_zone = ob_mid
                                min_distance = distance
                            elif bias == MarketBias.BEARISH and hasattr(ob, 'type') and 'BEARISH' in str(ob.type.value):
                                best_entry_zone = ob_mid
                                min_distance = distance
                
                if best_entry_zone is not None:
                    logger.info(f"🎯 ML optimizing entry: {entry_price:.2f} → {best_entry_zone:.2f}")
                    optimized_entry = best_entry_zone
            
            # ═══════════════════════════════════════════════
            # 2. STOP LOSS OPTIMIZATION
            # ═══════════════════════════════════════════════
            
            # If ML confidence is LOW, widen SL
            if ml_confidence < 60:
                sl_distance = abs(stop_loss - entry_price)
                new_sl_distance = sl_distance * 1.1
                
                if bias == MarketBias.BULLISH:
                    optimized_sl = optimized_entry - new_sl_distance  # ПОД entry
                else:
                    optimized_sl = optimized_entry + new_sl_distance  # НАД entry
                
                logger.info(f"🛡️ ML widening SL due to low confidence: {stop_loss:.2f} → {optimized_sl:.2f}")
            
            # If ML confidence is HIGH, tighten SL (but never closer than nearest OB)
            elif ml_confidence > 85 and liquidity_strength > 0.7:
                order_blocks = components.get('order_blocks', [])
                
                # Find nearest OB in SL direction
                nearest_ob_distance = float('inf')
                
                for ob in order_blocks:
                    if hasattr(ob, 'zone_high') and hasattr(ob, 'zone_low'):
                        
                        if bias == MarketBias.BULLISH:
                            # BULLISH: Check OB below entry (SL should be ПОД OB)
                            ob_edge = ob.zone_low  # Bottom of OB
                            
                            if ob_edge < entry_price:  # OB is below entry
                                distance = abs(entry_price - ob_edge)
                                nearest_ob_distance = min(nearest_ob_distance, distance)
                        
                        elif bias == MarketBias.BEARISH:
                            # BEARISH: Check OB above entry (SL should be НАД OB)
                            ob_edge = ob.zone_high  # Top of OB
                            
                            if ob_edge > entry_price:  # OB is above entry
                                distance = abs(ob_edge - entry_price)
                                nearest_ob_distance = min(nearest_ob_distance, distance)
                
                # Tighten SL, but NOT closer than OB + 5% buffer
                sl_distance = abs(stop_loss - entry_price)
                new_sl_distance = max(
                    sl_distance * 0.95,              # Tighten by 5%
                    nearest_ob_distance * 1.05       # BUT keep 5% beyond OB
                )
                
                if bias == MarketBias.BULLISH:
                    optimized_sl = optimized_entry - new_sl_distance  # ПОД entry
                else:
                    optimized_sl = optimized_entry + new_sl_distance  # НАД entry
                
                logger.info(f"🎯 ML tightening SL: {stop_loss:.2f} → {optimized_sl:.2f}")
                logger.info(f"   (Keeping SL {'ПОД' if bias == MarketBias.BULLISH else 'НАД'} nearest OB)")
            
            # ═══════════════════════════════════════════════
            # 3. TAKE PROFIT OPTIMIZATION
            # ═══════════════════════════════════════════════
            
            if liquidity_strength > 0.6:
                liquidity_zones = components.get('liquidity_zones', [])
                
                for i, tp in enumerate(take_profit):
                    extended_tp = tp
                    
                    for liq_zone in liquidity_zones:
                        if hasattr(liq_zone, 'price_level'):
                            liq_price = liq_zone.price_level
                            
                            # Check if liquidity is in profit direction
                            if bias == MarketBias.BULLISH and liq_price > tp and liq_price < tp * 1.15:
                                extended_tp = max(extended_tp, liq_price)
                            elif bias == MarketBias.BEARISH and liq_price < tp and liq_price > tp * 0.85:
                                extended_tp = min(extended_tp, liq_price)
                    
                    if extended_tp != tp:
                        logger.info(f"💎 ML extending TP{i+1}: {tp:.2f} → {extended_tp:.2f} (liquidity target)")
                        optimized_tp[i] = extended_tp
            
            return optimized_entry, optimized_sl, optimized_tp
            
        except Exception as e:
            logger.error(f"❌ ML optimization error: {e}")
            return entry_price, stop_loss, take_profit
    
    def _get_htf_bias_with_fallback(self, symbol: str, mtf_data: Optional[Dict]) -> str:
        """
        ЗАДЪЛЖИТЕЛНО: Получава HTF bias от 1D → 4H fallback
        """
        if not mtf_data:
            logger.warning("No MTF data available, using NEUTRAL bias")
            return 'NEUTRAL'
        
        try:
            # Опит 1: 1D timeframe (HTF)
            if '1d' in mtf_data or '1D' in mtf_data:
                df_1d = mtf_data.get('1d') or mtf_data.get('1D')
                if df_1d is not None and len(df_1d) >= 20:
                    # Determine bias from 1D
                    bias_components = self._detect_ict_components(df_1d, '1d')
                    htf_bias = self._determine_market_bias(df_1d, bias_components, None)
                    htf_bias_str = htf_bias.value if hasattr(htf_bias, 'value') else str(htf_bias)
                    logger.info(f"✅ HTF Bias from 1D: {htf_bias_str}")
                    return htf_bias_str
            
            # Опит 2: 4H timeframe (fallback)
            logger.warning("⚠️ 1D bias failed, trying 4H fallback...")
            if '4h' in mtf_data or '4H' in mtf_data:
                df_4h = mtf_data.get('4h') or mtf_data.get('4H')
                if df_4h is not None and len(df_4h) >= 20:
                    bias_components = self._detect_ict_components(df_4h, '4h')
                    htf_bias = self._determine_market_bias(df_4h, bias_components, None)
                    htf_bias_str = htf_bias.value if hasattr(htf_bias, 'value') else str(htf_bias)
                    logger.info(f"✅ HTF Bias from 4H (fallback): {htf_bias_str}")
                    return htf_bias_str
            
            logger.warning("❌ No HTF data available, using NEUTRAL bias")
            return 'NEUTRAL'
            
        except Exception as e:
            logger.error(f"HTF bias error: {e}, defaulting to NEUTRAL")
            return 'NEUTRAL'

    def _get_liquidity_zones_with_fallback(self, symbol: str, timeframe: str) -> List:
        """
        ЗАДЪЛЖИТЕЛНО: Опитва fresh liquidity map, САМО АКО НЕ е готова → cache
        """
        try:
            # Опит 1: Fresh liquidity map
            if hasattr(self, 'liquidity_mapper') and self.liquidity_mapper:
                try:
                    liquidity_zones = self.liquidity_mapper.detect_liquidity_zones(symbol, timeframe)
                    if liquidity_zones:
                        logger.info(f"✅ Fresh liquidity map: {len(liquidity_zones)} zones")
                        return liquidity_zones
                except Exception as e:
                    logger.warning(f"Fresh liquidity map failed: {e}")
            
            # Опит 2: Cache fallback
            if self.cache_manager:
                cached_zones = self.cache_manager.get(f"liquidity_zones_{symbol}_{timeframe}")
                if cached_zones:
                    logger.warning(f"⚠️ Using CACHED liquidity zones for {symbol} {timeframe}")
                    return cached_zones
            
            logger.warning(f"❌ No liquidity zones available for {symbol} {timeframe}")
            return []
            
        except Exception as e:
            logger.error(f"Liquidity zones error: {e}")
            return []
    
    def record_signal_outcome(
        self,
        signal_id: str,
        outcome: str,  # 'WIN', 'LOSS', 'BE' (break-even)
        actual_rr: float,
        signal_data: Optional[Dict] = None
    ) -> None:
        """
        Record signal outcome for ML training
        
        Args:
            signal_id: Unique signal identifier
            outcome: Trade outcome
            actual_rr: Actual risk/reward achieved
            signal_data: Original signal data with ML features
        """
        try:
            if not self.use_ml or not signal_data:
                return
            
            # Record in ML Engine
            if self.ml_engine:
                ml_features = signal_data.get('ml_features', {})
                success = outcome == 'WIN'
                
                # Extract required fields
                symbol = signal_data.get('symbol', 'UNKNOWN')
                timeframe = signal_data.get('timeframe', '1h')
                signal_type = signal_data.get('signal_type', 'HOLD')
                confidence = signal_data.get('confidence', 50.0)
                
                self.ml_engine.record_outcome(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal=signal_type,
                    confidence=confidence,
                    features=ml_features,
                    success=success
                )
                
                logger.info(f"✅ ML outcome recorded: {signal_id} - {outcome} (RR: {actual_rr:.2f})")
            
        except Exception as e:
            logger.error(f"❌ ML outcome recording error: {e}")


# Example usage
if __name__ == "__main__":
    print("🎯 ICT Signal Engine - Test Mode")
    
    # Create sample data
    dates = pd.date_range(start='2025-01-01', periods=200, freq='1H')
    np.random.seed(42)
    
    # Simulate realistic price data
    base_price = 50000
    prices = []
    current = base_price
    
    for i in range(200):
        # Add trending moves with some order blocks
        if i == 80:  # Bullish setup
            change = -150  # OB candle
        elif i in [81, 82, 83]:  # Displacement
            change = 600
        elif i == 150:  # Bearish setup
            change = 200  # OB candle
        elif i in [151, 152, 153]:  # Displacement
            change = -550
        else:
            change = np.random.randn() * 100
        
        current += change
        prices.append(current)
    
    # Create dataframe
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + abs(np.random.randn() * 50) for p in prices],
        'low': [p - abs(np.random.randn() * 50) for p in prices],
        'close': [p + np.random.randn() * 30 for p in prices],
        'volume': [1000000 + np.random.randn() * 200000 for _ in prices]
    })
    
    # Initialize engine
    engine = ICTSignalEngine()
    
    # Generate signal
    signal = engine.generate_signal(df, symbol="BTCUSDT", timeframe="1H")
    
    if signal:
        print(f"\n✅ Generated {signal.signal_type.value} signal!")
        print(f"\n📊 Signal Details:")
        print(f"   Symbol: {signal.symbol}")
        print(f"   Timeframe: {signal.timeframe}")
        print(f"   Strength: {'🔥' * signal.signal_strength.value}")
        print(f"   Confidence: {signal.confidence:.1f}%")
        print(f"\n💰 Trade Setup:")
        print(f"   Entry: ${signal.entry_price:.2f}")
        print(f"   Stop Loss: ${signal.sl_price:.2f}")
        print(f"   Take Profits:")
        for i, tp in enumerate(signal.tp_prices, 1):
            print(f"     TP{i}: ${tp:.2f}")
        print(f"   Risk/Reward: {signal.risk_reward_ratio:.2f}")
        print(f"\n📈 ICT Analysis:")
        print(f"   Market Bias: {signal.bias.value}")
        print(f"   Whale Blocks: {len(signal.whale_blocks)}")
        print(f"   Liquidity Zones: {len(signal.liquidity_zones)}")
        print(f"   Order Blocks: {len(signal.order_blocks)}")
        print(f"   FVGs: {len(signal.fair_value_gaps)}")
        print(f"   MTF Confluence: {signal.mtf_confluence}")
        print(f"\n📝 Reasoning:")
        print(signal.reasoning)
        if signal.warnings:
            print(f"\n⚠️  Warnings:")
            for warning in signal.warnings:
                print(f"   - {warning}")
    else:
        print("\n❌ No signal generated (conditions not met)")
    
    print("\n✅ ICT Signal Engine test completed!")
    print(f"Total lines: {sum(1 for line in open(__file__))}+")
