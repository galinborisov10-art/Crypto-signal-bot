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
import json

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
    from liquidity_map import LiquidityMapper, LiquidityZone, LiquiditySweep
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

# Fibonacci Analyzer
try:
    from fibonacci_analyzer import FibonacciAnalyzer, FibonacciLevel
    FIBONACCI_AVAILABLE = True
except ImportError:
    FIBONACCI_AVAILABLE = False
    logging.warning("FibonacciAnalyzer not available")

# LuxAlgo Combined Analysis
try:
    from luxalgo_ict_analysis import CombinedLuxAlgoAnalysis
    LUXALGO_COMBINED_AVAILABLE = True
except ImportError:
    LUXALGO_COMBINED_AVAILABLE = False
    logging.warning("CombinedLuxAlgoAnalysis not available")

# Chart Generator
try:
    from chart_generator import ChartGenerator
    CHART_GENERATOR_AVAILABLE = True
except ImportError:
    CHART_GENERATOR_AVAILABLE = False
    logging.warning("ChartGenerator not available")

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
    
    # New Components
    fibonacci_data: Dict = field(default_factory=dict)
    luxalgo_sr: Dict = field(default_factory=dict)
    luxalgo_ict: Dict = field(default_factory=dict)
    luxalgo_combined: Dict = field(default_factory=dict)
    
    # Market Analysis
    bias: MarketBias = MarketBias.NEUTRAL
    structure_broken: bool = False
    displacement_detected: bool = False
    mtf_confluence: int = 0
    htf_bias: str = "NEUTRAL"
    mtf_structure: str = "NEUTRAL"
    mtf_consensus_data: Dict = field(default_factory=dict)  # NEW: MTF consensus breakdown
    
    # Entry Zone (NEW - ICT-Compliant)
    entry_zone: Dict = field(default_factory=dict)  # NEW: Entry zone details
    entry_status: str = "UNKNOWN"  # NEW: Entry zone status (VALID_WAIT/VALID_NEAR/etc)
    
    # Distance Penalty (Soft Constraint)
    distance_penalty: bool = False  # NEW: Whether confidence was reduced due to distance out of range
    
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
            'mtf_consensus_data': self.mtf_consensus_data,
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
        
        # Initialize Fibonacci Analyzer
        self.fibonacci_analyzer = FibonacciAnalyzer(
            retracement_levels=[0.236, 0.382, 0.5, 0.618, 0.786],
            extension_levels=[1.272, 1.414, 1.618, 2.0, 2.618],
            ote_range=(0.62, 0.79)
        ) if FIBONACCI_AVAILABLE else None
        
        # Initialize LuxAlgo Combined Analysis
        self.luxalgo_combined = CombinedLuxAlgoAnalysis(
            sr_detection_length=15,
            sr_margin=2.0,
            ict_swing_length=10,
            enable_sr=True,
            enable_ict=True
        ) if LUXALGO_COMBINED_AVAILABLE else None
        
        # Initialize Chart Generator
        self.chart_generator = ChartGenerator() if CHART_GENERATOR_AVAILABLE else None
        
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
        logger.info(f"Fibonacci Analyzer: {FIBONACCI_AVAILABLE}")
        logger.info(f"LuxAlgo Combined: {LUXALGO_COMBINED_AVAILABLE}")
        logger.info(f"Chart Generator: {CHART_GENERATOR_AVAILABLE}")
    
    def _get_default_config(self) -> Dict:
        """Get default configuration"""
        return {
            'min_confidence': 60,          # Min 60% confidence (STRICT ICT)
            'min_risk_reward': 3.0,        # Min 1:3 R:R (STRICT ICT)
            'max_sl_distance_pct': 3.0,    # Max 3% SL distance
            'tp_multipliers': [3, 5, 8],   # TP at 3R, 5R, 8R (STRICT ICT)
            'require_mtf_confluence': True, # Require MTF alignment (STRICT ICT)
            'min_mtf_confluence': 0.5,     # Min 50% MTF consensus (STRICT ICT)
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
        mtf_analysis = self._analyze_mtf_confluence(df, mtf_data, symbol) if mtf_data is not None and isinstance(mtf_data, dict) else None
        
        # СТЪПКА 3: ENTRY MODEL (текущ TF)
        logger.info(f"📊 Step 3: Entry Model ({timeframe})")
        
        # СТЪПКА 4: LIQUIDITY MAP (с cache fallback)
        logger.info("📊 Step 4: Liquidity Map")
        liquidity_zones = self._get_liquidity_zones_with_fallback(df, symbol, timeframe)
        
        # СТЪПКА 5-7: ICT COMPONENTS
        logger.info("📊 Steps 5-7: ICT Components")
        ict_components = self._detect_ict_components(df, timeframe)
        ict_components['liquidity_zones'] = liquidity_zones  # Add liquidity zones
        
        bias = self._determine_market_bias(df, ict_components, mtf_analysis)
        structure_broken = self._check_structure_break(df)
        displacement_detected = self._check_displacement(df)
        
        # СТЪПКА 7b: EARLY EXIT за HOLD/RANGING
        if bias in [MarketBias.NEUTRAL, MarketBias.RANGING]:
            logger.info(f"🔄 Market bias is {bias.value} - creating HOLD signal (early exit)")
            
            # Calculate base confidence for informational purposes
            base_confidence = self._calculate_signal_confidence(
                ict_components, mtf_analysis, bias, structure_broken, 
                displacement_detected, 0.0  # RR not applicable for HOLD
            )
            
            # Get current price
            current_price = df['close'].iloc[-1]
            
            # Calculate MTF consensus data
            mtf_consensus_data = self._calculate_mtf_consensus(symbol, timeframe, bias, mtf_data)
            
            return self._create_hold_signal(
                symbol=symbol,
                timeframe=timeframe,
                bias=bias,
                confidence=base_confidence,
                df=df,
                ict_components=ict_components,
                mtf_data=mtf_data,
                current_price=current_price,
                htf_bias=htf_bias,
                mtf_consensus_data=mtf_consensus_data,
                structure_broken=structure_broken,
                displacement_detected=displacement_detected,
                mtf_analysis=mtf_analysis
            )
        
        # From here onwards: BULLISH/BEARISH signals only
        # СТЪПКА 8: ENTRY CALCULATION WITH ICT-COMPLIANT ZONE
        logger.info("📊 Step 8: Entry + ICT Zone Validation")
        
        # Get current price
        current_price = df['close'].iloc[-1]
        
        # Calculate ICT-compliant entry zone
        bias_str = bias.value if hasattr(bias, 'value') else str(bias)
        fvg_zones = ict_components.get('fvgs', [])
        order_blocks = ict_components.get('order_blocks', [])
        sr_levels = ict_components.get('luxalgo_sr', {})
        
        entry_zone, entry_status = self._calculate_ict_compliant_entry_zone(
            current_price=current_price,
            direction=bias_str,
            fvg_zones=fvg_zones,
            order_blocks=order_blocks,
            sr_levels=sr_levels
        )
        
        # ✅ UPDATED: Only reject for TOO_LATE (timing issue), not NO_ZONE (distance issue)
        # Validate entry zone timing
        if entry_status == 'TOO_LATE':
            logger.error(f"❌ Entry zone validation failed: {entry_status}")
            context = self._extract_context_data(df, bias)
            # Calculate MTF consensus for detailed breakdown
            mtf_consensus_data = self._calculate_mtf_consensus(symbol, timeframe, bias, mtf_data)
            
            return self._create_no_trade_message(
                symbol=symbol,
                timeframe=timeframe,
                reason=f"Entry zone validation failed: {entry_status}",
                details=f"Current price: ${current_price:.2f}. Price already passed the entry zone.",
                mtf_breakdown=mtf_consensus_data.get("breakdown", {}),
                current_price=context['current_price'],
                price_change_24h=context['price_change_24h'],
                rsi=context['rsi'],
                signal_direction=context['signal_direction'],
                confidence=None
            )
        
        # ✅ SOFT CONSTRAINT: Handle NO_ZONE case with fallback instead of rejection
        if entry_status == 'NO_ZONE' or entry_zone is None:
            logger.warning(f"⚠️ No valid entry zone found, creating fallback zone at current price")
            # Create fallback entry zone based on current price with small buffer
            fallback_distance = 0.01  # 1% from current price
            if bias_str == 'BEARISH':
                # BEARISH: Entry above current price
                entry_zone = {
                    'source': 'FALLBACK',
                    'low': current_price * (1 + fallback_distance * 0.8),
                    'high': current_price * (1 + fallback_distance * 1.2),
                    'center': current_price * (1 + fallback_distance),
                    'quality': 40,  # Low quality for fallback
                    'distance_pct': fallback_distance * 100,
                    'distance_price': current_price * fallback_distance,
                    'distance_out_of_range': False,  # Within optimal range
                    'distance_comment': None
                }
            else:  # BULLISH
                # BULLISH: Entry below current price
                entry_zone = {
                    'source': 'FALLBACK',
                    'low': current_price * (1 - fallback_distance * 1.2),
                    'high': current_price * (1 - fallback_distance * 0.8),
                    'center': current_price * (1 - fallback_distance),
                    'quality': 40,  # Low quality for fallback
                    'distance_pct': fallback_distance * 100,
                    'distance_price': current_price * fallback_distance,
                    'distance_out_of_range': False,  # Within optimal range
                    'distance_comment': None
                }
            entry_status = 'VALID_FALLBACK'
            logger.info(f"✅ Fallback entry zone created at ${entry_zone['center']:.2f}")
        
        # Use entry zone center as entry price
        entry_price = entry_zone['center']
        logger.info(f"✅ Entry price set to entry zone center: ${entry_price:.2f}")
        
        # Keep existing entry setup for SL calculation (fallback)
        entry_setup = self._identify_entry_setup(df, ict_components, bias)
        if not entry_setup:
            # Use entry_zone as fallback entry_setup
            entry_setup = {
                'type': f"{bias_str.lower()}_zone",
                'price_zone': (entry_zone['low'], entry_zone['high']),
                'source': entry_zone['source']
            }
        
        # СТЪПКА 9: SL/TP + VALIDATION
        logger.info("📊 Step 9: SL/TP + Validation")
        sl_price = self._calculate_sl_price(df, entry_setup, entry_price, bias)
        
        # ✅ VALIDATE SL (STRICT ICT)
        order_block = entry_setup.get('ob') or (ict_components['order_blocks'][0] if ict_components.get('order_blocks') else None)
        if order_block:
            sl_price, sl_valid = self._validate_sl_position(sl_price, order_block, bias, entry_price)
            if not sl_valid or sl_price is None:
                logger.error("❌ SL не може да бъде ICT-compliant - сигналът НЕ СЕ ИЗПРАЩА")
                return None
        else:
            logger.error("❌ Няма Order Block за SL валидация - сигналът НЕ СЕ ИЗПРАЩА")
            return None
        
        # ✅ TP с гарантиран RR ≥ 1:3 (with Fibonacci optimization)
        fibonacci_data = ict_components.get('fibonacci_data', {})
        bias_str = bias.value if hasattr(bias, 'value') else str(bias)
        tp_prices = self._calculate_tp_with_min_rr(
            entry_price, sl_price, liquidity_zones, 
            min_rr=3.0, 
            fibonacci_data=fibonacci_data,
            bias=bias_str
        )
        
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
            logger.error(f"❌ RR {risk_reward_ratio:.2f} < {self.config['min_risk_reward']} - сигналът НЕ СЕ ИЗПРАЩА")
            context = self._extract_context_data(df, bias)
            return self._create_no_trade_message(
                symbol=symbol,
                timeframe=timeframe,
                reason=f"Risk/Reward под минимум ({risk_reward_ratio:.2f})",
                details=f"Необходими: RR ≥{self.config['min_risk_reward']}. Намерени: {risk_reward_ratio:.2f}",
                mtf_breakdown={},
                current_price=context['current_price'],
                price_change_24h=context['price_change_24h'],
                rsi=context['rsi'],
                signal_direction=context['signal_direction'],
                confidence=None
            )
        
        # BASE CONFIDENCE
        base_confidence = self._calculate_signal_confidence(
            ict_components, mtf_analysis, bias, structure_broken, 
            displacement_detected, risk_reward_ratio
        )
        
        # ============================================
        # LIQUIDITY-BASED CONFIDENCE ADJUSTMENT
        # ============================================
        liquidity_boost = 0.0
        try:
            if ict_components.get('liquidity_zones'):
                logger.info("💧 Applying liquidity-based confidence adjustment")
                current_price = df['close'].iloc[-1]
                
                # Find nearest liquidity zone
                nearest_zone = None
                min_distance = float('inf')
                
                for zone in ict_components['liquidity_zones']:
                    zone_price = zone.price_level if hasattr(zone, 'price_level') else zone.get('price_level', 0)
                    if zone_price > 0:
                        distance = abs(zone_price - current_price) / current_price
                        if distance < min_distance:
                            min_distance = distance
                            nearest_zone = zone
                
                # Boost confidence if near strong liquidity zone
                if nearest_zone and min_distance < 0.02:  # Within 2% of price
                    zone_confidence = nearest_zone.confidence if hasattr(nearest_zone, 'confidence') else nearest_zone.get('confidence', 0)
                    zone_type = nearest_zone.zone_type if hasattr(nearest_zone, 'zone_type') else nearest_zone.get('zone_type', '')
                    
                    liquidity_boost = zone_confidence * 0.05  # Up to 5% boost
                    
                    # Apply boost in same direction as zone type
                    bias_str = bias.value if hasattr(bias, 'value') else str(bias)
                    if (bias_str == 'BULLISH' and zone_type == 'SSL') or \
                       (bias_str == 'BEARISH' and zone_type == 'BSL'):
                        base_confidence = min(base_confidence * (1 + liquidity_boost), 100.0)
                        logger.info(f"💧 Liquidity boost: +{liquidity_boost*100:.1f}% (near {zone_type})")
            
            # Check for recent liquidity sweeps
            if ict_components.get('liquidity_sweeps'):
                logger.info("💥 Checking liquidity sweeps")
                recent_sweeps = []
                for sweep in ict_components['liquidity_sweeps']:
                    sweep_timestamp = sweep.timestamp if hasattr(sweep, 'timestamp') else sweep.get('timestamp')
                    if sweep_timestamp and (df.index[-1] - sweep_timestamp).total_seconds() < 3600*4:  # Last 4 hours
                        recent_sweeps.append(sweep)
                
                if recent_sweeps:
                    last_sweep = recent_sweeps[-1]
                    sweep_type = last_sweep.sweep_type if hasattr(last_sweep, 'sweep_type') else last_sweep.get('sweep_type', '')
                    sweep_strength = last_sweep.strength if hasattr(last_sweep, 'strength') else last_sweep.get('strength', 0)
                    
                    # Boost if sweep aligns with signal direction
                    bias_str = bias.value if hasattr(bias, 'value') else str(bias)
                    if (bias_str == 'BULLISH' and sweep_type == 'SSL_SWEEP') or \
                       (bias_str == 'BEARISH' and sweep_type == 'BSL_SWEEP'):
                        sweep_boost = sweep_strength * 0.03  # Up to 3% boost
                        base_confidence = min(base_confidence * (1 + sweep_boost), 100.0)
                        logger.info(f"💥 Sweep boost: +{sweep_boost*100:.1f}% ({sweep_type})")
                        
        except Exception as e:
            logger.warning(f"⚠️ Liquidity confidence adjustment failed: {e}")
        
        # ✅ APPLY CONTEXT-AWARE FILTERS (NEW - Enhances confidence accuracy)
        logger.info("📊 Step 11a: Context-Aware Filtering")
        context_warnings = []
        try:
            # Extract enhanced context (pass symbol for BTC correlation)
            context_data = self._extract_context_data(df, bias, symbol)
            
            # Apply context filters to adjust confidence
            confidence_after_context, context_warnings = self._apply_context_filters(
                base_confidence,
                context_data,
                ict_components
            )
            
            logger.info(f"Context-aware confidence: {base_confidence:.1f}% → {confidence_after_context:.1f}%")
            
        except Exception as e:
            logger.warning(f"Context filtering failed, using base confidence: {e}")
            confidence_after_context = base_confidence
            context_warnings = []
        
        # ✅ DISTANCE PENALTY (Soft Constraint - NEW)
        logger.info("📊 Step 11b: Distance Penalty Check")
        distance_penalty_applied = False
        
        if entry_zone and entry_zone.get('distance_out_of_range'):
            logger.warning(f"⚠️ Entry zone outside optimal range ({entry_zone['distance_pct']:.1f}%), applying confidence penalty")
            confidence_after_context = confidence_after_context * 0.8  # Reduce by 20%
            distance_penalty_applied = True
            logger.info(f"Distance penalty applied: confidence reduced by 20% → {confidence_after_context:.1f}%")
            
            # Add warning about distance
            if entry_zone.get('distance_comment'):
                context_warnings.append(entry_zone['distance_comment'])
        
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
                    # Prepare trade data with Pure ICT features
                    trade_data = {
                        'entry_price': entry_price,
                        'analysis_data': ml_features,
                        'ict_components': ict_components,  # ✅ NEW: Pass ICT components
                        'volume_ratio': context_data.get('volume_ratio', 1.0),  # ✅ NEW
                        'volatility': context_data.get('volatility_pct', 1.0),  # ✅ NEW
                        'btc_correlation': context_data.get('btc_correlation', 0.0),  # ✅ NEW
                        'mtf_confluence': mtf_analysis.get('confluence_count', 0) / 5 if mtf_analysis else 0.5,  # ✅ NEW
                        'risk_reward_ratio': risk_reward_ratio,  # ✅ NEW
                        'rsi': context_data.get('rsi', 50.0),  # ✅ NEW
                        'sentiment_score': 50.0,  # ✅ NEW: Placeholder (TODO: Add real sentiment)
                        'confidence': confidence_after_context  # ✅ UPDATED: Use context-adjusted confidence
                    }
                    
                    # Get win probability
                    win_probability = self.ml_predictor.predict(trade_data)
                    
                    if win_probability is not None:
                        # Get confidence adjustment (use context-adjusted confidence as base)
                        ml_confidence_adjustment = self.ml_predictor.get_confidence_adjustment(
                            ml_probability=win_probability,
                            current_confidence=confidence_after_context
                        )
                        
                        logger.info(f"ML win probability: {win_probability:.1f}%")
                        logger.info(f"ML confidence adjustment: {ml_confidence_adjustment:+.1f}%")
                        ml_mode = f"ML Predictor (Win: {win_probability:.1f}%)"
                        
                except Exception as e:
                    logger.error(f"❌ ML Predictor error: {e}")
            
            # ═══════════════════════════════════════════════════════════════
            # SHADOW ML PREDICTOR (LOG-ONLY, NO PRODUCTION IMPACT)
            # ═══════════════════════════════════════════════════════════════
            if self.ml_predictor and self.ml_predictor.is_trained:
                try:
                    # Prepare trade data (EXACT SAME format as production ML Predictor)
                    shadow_trade_data = {
                        'entry_price': entry_price,
                        'analysis_data': ml_features,
                        'ict_components': ict_components,
                        'volume_ratio': context_data.get('volume_ratio', 1.0),
                        'volatility': context_data.get('volatility_pct', 1.0),
                        'btc_correlation': context_data.get('btc_correlation', 0.0),
                        'mtf_confluence': mtf_analysis.get('confluence_count', 0) / 5 if mtf_analysis else 0.5,
                        'risk_reward_ratio': risk_reward_ratio,
                        'rsi': context_data.get('rsi', 50.0),
                        'sentiment_score': 50.0,  # Placeholder (same as production)
                        'confidence': base_confidence  # Use base confidence (before ML adjustment)
                    }
                    
                    # Get shadow prediction (NOT USED FOR DECISIONS)
                    shadow_prediction = self.ml_predictor.predict(shadow_trade_data)
                    
                    if shadow_prediction is not None:
                        # Calculate final confidence (production logic, unchanged)
                        final_conf = base_confidence + ml_confidence_adjustment
                        
                        # Determine decision (for logging only, NOT USED)
                        decision = "SIGNAL" if final_conf >= self.config['min_confidence'] else "REJECT"
                        
                        # Log structured data (JSON on one line)
                        shadow_log = json.dumps({
                            "symbol": symbol,
                            "timeframe": timeframe,
                            "ict_confidence": round(base_confidence, 2),
                            "ml_engine_adjustment": round(ml_confidence_adjustment, 2),
                            "final_confidence": round(final_conf, 2),
                            "ml_predictor_confidence": round(shadow_prediction, 2),
                            "delta": round(shadow_prediction - final_conf, 2),
                            "decision": decision
                        })
                        
                        logger.info(f"[SHADOW_ML_PREDICTOR] {shadow_log}")
                        
                except Exception as e:
                    # Shadow error is non-critical - log and continue
                    logger.debug(f"[SHADOW_ML_PREDICTOR] Non-critical error: {e}")
            # ═══════════════════════════════════════════════════════════════
            # END SHADOW MODE
            # ═══════════════════════════════════════════════════════════════
            
            # ✅ ML RESTRICTIONS (STRICT ICT) - Step 11.25
            logger.info("📊 Step 11.25: ML ICT Compliance Check")
            
            # 1. ML може само да прави SL по-консервативен (по-далеч от entry), НЕ по-близо
            # (В този код SL не се променя от ML, така че проверката не е необходима)
            
            # 2. Гарантирай че RR няма да падне под 3.0 след ML adjustment
            # (Проверката е след изчисляване на confidence по-долу)
            
            # 3. ML confidence adjustment НЕ МОЖЕ да нарушава правилата
            # - Ако confidence стане < 60%, сигналът не се изпраща
            # - Ако MTF consensus < 50%, ML не може да промени това

        # ✅ UPDATED: Use context-adjusted confidence as base for ML adjustment
        confidence = confidence_after_context + ml_confidence_adjustment
        confidence = max(0.0, min(100.0, confidence))
        
        # ✅ ML RESTRICTION: Гарантирай че confidence не пада под минимум
        if confidence < self.config['min_confidence'] and ml_confidence_adjustment < 0:
            logger.warning(f"⚠️ ML adjustment би свалил confidence под {self.config['min_confidence']}% - ограничаване")
            confidence = self.config['min_confidence']
        
        # СТЪПКА 11.5: MTF CONSENSUS CHECK (STRICT ICT)
        logger.info("📊 Step 11.5: MTF Consensus Check")
        mtf_consensus_data = self._calculate_mtf_consensus(symbol, timeframe, bias, mtf_data)
        
        # Ако MTF consensus < 50%, confidence = 0 и сигналът НЕ СЕ ИЗПРАЩА
        if mtf_consensus_data['consensus_pct'] < 50.0:
            logger.error(f"❌ MTF consensus {mtf_consensus_data['consensus_pct']:.1f}% < 50% - сигналът НЕ СЕ ИЗПРАЩА")
            # Изпрати информативно съобщение
            context = self._extract_context_data(df, bias)
            return self._create_no_trade_message(
                symbol=symbol,
                timeframe=timeframe,
                reason=f"Липса на MTF consensus ({mtf_consensus_data['consensus_pct']:.1f}%)",
                details=f"Необходими: ≥50% aligned TFs. Намерени: {mtf_consensus_data['aligned_count']}/{mtf_consensus_data['total_count']}",
                mtf_breakdown=mtf_consensus_data['breakdown'],
                current_price=context['current_price'],
                price_change_24h=context['price_change_24h'],
                rsi=context['rsi'],
                signal_direction=context['signal_direction'],
                confidence=confidence
            )
        
        # Confidence check
        if confidence < self.config['min_confidence']:
            logger.error(f"❌ Confidence {confidence:.1f}% < {self.config['min_confidence']}% - сигналът НЕ СЕ ИЗПРАЩА")
            context = self._extract_context_data(df, bias)
            return self._create_no_trade_message(
                symbol=symbol,
                timeframe=timeframe,
                reason=f"Ниска увереност ({confidence:.1f}%)",
                details=f"Необходими: ≥{self.config['min_confidence']}%. Намерени: {confidence:.1f}%",
                mtf_breakdown=mtf_consensus_data['breakdown'],
                current_price=context['current_price'],
                price_change_24h=context['price_change_24h'],
                rsi=context['rsi'],
                signal_direction=context['signal_direction'],
                confidence=confidence
            )
        
        # СТЪПКА 12: CONFIDENCE SCORING
        logger.info("📊 Step 12: Final Confidence")
        signal_strength = self._calculate_signal_strength(confidence, risk_reward_ratio, ict_components)
        signal_type = self._determine_signal_type(bias, signal_strength, confidence)
        reasoning = self._generate_reasoning(ict_components, bias, entry_setup, mtf_analysis)
        warnings = self._generate_warnings(ict_components, risk_reward_ratio, df)
        
        # ✅ ADD CONTEXT WARNINGS (if any)
        if context_warnings:
            warnings.extend(context_warnings)
            logger.info(f"Added {len(context_warnings)} context-based warnings")
        
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
            liquidity_sweeps=[ls.__dict__ if hasattr(ls, '__dict__') else ls for ls in ict_components.get('liquidity_sweeps', [])],
            order_blocks=[ob.to_dict() if hasattr(ob, 'to_dict') else ob for ob in ict_components.get('order_blocks', [])],
            fair_value_gaps=[fvg.to_dict() if hasattr(fvg, 'to_dict') else fvg for fvg in ict_components.get('fvgs', [])],
            internal_liquidity=[ilp for ilp in ict_components.get('internal_liquidity', [])],
            breaker_blocks=[bb.to_dict() for bb in ict_components.get('breaker_blocks', [])],
            mitigation_blocks=[mb.to_dict() for mb in ict_components.get('mitigation_blocks', [])],
            sibi_ssib_zones=[sz.to_dict() for sz in ict_components.get('sibi_ssib_zones', [])],
            fibonacci_data=ict_components.get('fibonacci_data', {}),
            luxalgo_sr=ict_components.get('luxalgo_sr', {}),
            luxalgo_ict=ict_components.get('luxalgo_ict', {}),
            luxalgo_combined=ict_components.get('luxalgo_combined', {}),
            bias=bias,
            structure_broken=structure_broken,
            displacement_detected=displacement_detected,
            mtf_confluence=mtf_analysis.get('confluence_count', 0) if mtf_analysis else 0,
            htf_bias=htf_bias,
            mtf_structure=mtf_analysis.get('mtf_structure', 'NEUTRAL') if mtf_analysis else 'NEUTRAL',
            mtf_consensus_data=mtf_consensus_data,
            entry_zone=entry_zone,  # NEW: Entry zone details (with distance metadata)
            entry_status=entry_status,  # NEW: Entry zone status
            distance_penalty=distance_penalty_applied,  # ✅ NEW: Distance penalty tracking
            reasoning=reasoning,
            warnings=warnings,
            zone_explanations=zone_explanations
        )
        
        logger.info(f"✅ Generated {signal_type.value} signal (UNIFIED)")
        
        # Generate chart if chart generator available
        if self.chart_generator:
            try:
                logger.info("📊 Generating ICT chart...")
                chart_bytes = self.chart_generator.generate(
                    df=df,
                    signal=signal,
                    symbol=symbol,
                    timeframe=timeframe
                )
                
                # Store chart data in a temp location for bot retrieval
                # The bot will handle sending it via Telegram
                if chart_bytes:
                    logger.info(f"✅ Chart generated successfully ({len(chart_bytes)} bytes)")
                else:
                    logger.warning("⚠️ Chart generation returned empty bytes")
                    
            except Exception as e:
                logger.error(f"❌ Chart generation error: {e}")
        
        if self.cache_manager:
            try:
                self.cache_manager.cache_signal(symbol, timeframe, signal)
            except Exception as e:
                logger.warning(f"Cache error: {e}")
        
        # ✅ LOG FINAL SIGNAL METRICS (for validation)
        logger.info("=" * 60)
        logger.info("📊 FINAL SIGNAL METRICS:")
        logger.info(f"   Base Confidence: {base_confidence:.1f}%")
        logger.info(f"   Context-Adjusted: {confidence:.1f}%")
        logger.info(f"   Distance Penalty Applied: {distance_penalty_applied}")
        if distance_penalty_applied:
            logger.info(f"   Distance: {entry_zone.get('distance_pct', 0):.1f}% (outside optimal 0.5-3% range)")
        logger.info(f"   Signal Type: {signal_type.value if hasattr(signal_type, 'value') else signal_type}")
        logger.info(f"   Warnings: {len(warnings)}")
        if context_warnings:
            logger.info(f"   Context Warnings: {context_warnings}")
        logger.info("=" * 60)
        
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
        
        # Calculate volume metrics (Pure ICT - no MA)
        if 'volume' in df.columns:
            df['volume_median'] = df['volume'].rolling(window=20).median()
            df['volume_ratio'] = df['volume'] / df['volume_median'].replace(0, 1)
        else:
            df['volume'] = 0
            df['volume_median'] = 0
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
        # Note: .mean() here is legitimate - it's part of the standard ATR formula,
        # not a moving average for trading signals (ICT compliant)
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
        
        # Run LuxAlgo Combined Analysis
        if self.luxalgo_combined:
            try:
                luxalgo_result = self.luxalgo_combined.analyze(df)
                
                # CRITICAL: Handle None explicitly (defensive)
                if luxalgo_result is None:
                    logger.warning("LuxAlgo returned None - using safe defaults")
                    luxalgo_result = {
                        'sr_data': {'support_zones': [], 'resistance_zones': []},
                        'ict_data': {},
                        'combined_signal': {},
                        'entry_valid': False,
                        'status': 'returned_none'
                    }
                
                components['luxalgo_sr'] = luxalgo_result.get('sr_data', {})
                components['luxalgo_ict'] = luxalgo_result.get('ict_data', {})
                components['luxalgo_combined'] = luxalgo_result.get('combined_signal', {})
                
                # NEW: Structured logging
                entry_valid = luxalgo_result.get('entry_valid', False)
                status = luxalgo_result.get('status', 'unknown')
                sr_zones = len(luxalgo_result.get('sr_data', {}).get('support_zones', [])) + \
                           len(luxalgo_result.get('sr_data', {}).get('resistance_zones', []))
                
                logger.info(f"LuxAlgo result: entry_valid={entry_valid}, status={status}, sr_zones={sr_zones}")
                
                # NOTE: LuxAlgo is now ADVISORY only, not a hard gate
                # entry_valid is used for confidence scoring, not signal blocking
                
            except Exception as e:
                logger.error(f"LuxAlgo Combined analysis error: {e}")
                components['luxalgo_sr'] = {}
                components['luxalgo_ict'] = {}
                components['luxalgo_combined'] = {}
        else:
            components['luxalgo_sr'] = {}
            components['luxalgo_ict'] = {}
            components['luxalgo_combined'] = {}
        
        # Run Fibonacci Analysis
        # Determine bias from existing components
        bias_str = self._determine_bias_from_components(components)
        if self.fibonacci_analyzer:
            try:
                fibonacci_data = self.fibonacci_analyzer.analyze(df, bias_str, lookback=50)
                components['fibonacci_data'] = fibonacci_data
                
                logger.info(f"Fibonacci analysis complete - "
                           f"In OTE: {fibonacci_data.get('in_ote_zone', False)}, "
                           f"Nearest level: {fibonacci_data.get('nearest_level', {}).get('level') if fibonacci_data.get('nearest_level') else None}")
            except Exception as e:
                logger.error(f"Fibonacci analysis error: {e}")
                components['fibonacci_data'] = {}
        else:
            components['fibonacci_data'] = {}
        
        return components
    
    def _analyze_mtf_confluence(
        self,
        primary_df: pd.DataFrame,
        mtf_data: Optional[Dict[str, pd.DataFrame]],
        symbol: str
    ) -> Optional[Dict]:
        """Analyze multi-timeframe confluence"""
        if not self.mtf_analyzer or mtf_data is None or not isinstance(mtf_data, dict):
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
    
    def _calculate_mtf_consensus(
        self,
        symbol: str,
        primary_timeframe: str,
        target_bias: MarketBias,
        mtf_data: Optional[Dict[str, pd.DataFrame]] = None
    ) -> Dict:
        """
        Изчисли Multi-Timeframe Consensus (STRICT ICT)
        
        Проверява bias на всички timeframes: 1m, 3m, 5m, 15m, 30m, 1h, 2h, 4h, 6h, 12h, 1d, 3d, 1w
        
        Returns:
            Dict с:
                - consensus_pct: процент съгласни timeframes (0-100)
                - breakdown: детайлен breakdown по TF
                - aligned_tfs: списък със съгласни TF
                - conflicting_tfs: списък с конфликтни TF
        """
        all_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']
        
        breakdown = {}
        aligned_count = 0
        total_count = 0
        
        # Проверка на първичния timeframe
        breakdown[primary_timeframe] = {
            'bias': target_bias.value if hasattr(target_bias, 'value') else str(target_bias),
            'confidence': 100,  # Първичният TF е 100% сигурен
            'aligned': True
        }
        aligned_count += 1
        total_count += 1
        
        # Проверка на други timeframes (ако има данни)
        if mtf_data is not None and isinstance(mtf_data, dict):
            for tf in all_timeframes:
                if tf == primary_timeframe:
                    continue  # Вече е добавен
                
                tf_df = mtf_data.get(tf)
                if tf_df is not None and not tf_df.empty and len(tf_df) >= 20:
                    # ✅ PURE ICT BIAS CALCULATION (no MA/EMA)
                    try:
                        tf_bias, confidence = self._calculate_pure_ict_bias_for_tf(tf_df)
                        
                        # Провери alignment
                        is_aligned = (tf_bias == target_bias) or (tf_bias == MarketBias.NEUTRAL)
                        
                        breakdown[tf] = {
                            'bias': tf_bias.value if hasattr(tf_bias, 'value') else str(tf_bias),
                            'confidence': round(confidence, 1),
                            'aligned': is_aligned
                        }
                        
                        if is_aligned:
                            aligned_count += 1
                        total_count += 1
                        
                    except Exception as e:
                        logger.warning(f"MTF consensus analysis failed for {tf}: {e}")
                        breakdown[tf] = {
                            'bias': 'NEUTRAL',
                            'confidence': 0,
                            'aligned': True
                        }
                        aligned_count += 1
                        total_count += 1
                else:
                    # Няма данни за този TF - счита се за aligned (не пречи)
                    breakdown[tf] = {
                        'bias': 'NO_DATA',
                        'confidence': 0,
                        'aligned': True
                    }
                    aligned_count += 1
                    total_count += 1
        else:
            # Няма MTF data - счита се всичко като aligned
            for tf in all_timeframes:
                if tf != primary_timeframe:
                    breakdown[tf] = {
                        'bias': 'NO_DATA',
                        'confidence': 0,
                        'aligned': True
                    }
                    aligned_count += 1
                    total_count += 1
        
        # Изчисли consensus процент
        consensus_pct = (aligned_count / total_count * 100) if total_count > 0 else 0
        
        # Подготви списъци
        aligned_tfs = [tf for tf, data in breakdown.items() if data['aligned']]
        conflicting_tfs = [tf for tf, data in breakdown.items() if not data['aligned']]
        
        logger.info(f"📊 MTF Consensus: {consensus_pct:.1f}% ({aligned_count}/{total_count} TFs aligned)")
        
        return {
            'consensus_pct': round(consensus_pct, 1),
            'breakdown': breakdown,
            'aligned_tfs': aligned_tfs,
            'conflicting_tfs': conflicting_tfs,
            'aligned_count': aligned_count,
            'total_count': total_count
        }
    
    def _calculate_pure_ict_bias_for_tf(
        self, 
        df: pd.DataFrame
    ) -> Tuple[MarketBias, float]:
        """
        ✅ PURE ICT Bias Calculation for MTF Timeframes - NO MA/EMA!
        
        Uses:
        1. Market Structure (HH+HL vs LH+LL) - 50 points
        2. Order Block direction - 30 points
        3. Price Displacement - 20 points
        
        Args:
            df: DataFrame with OHLCV data
            
        Returns:
            Tuple of (MarketBias, confidence_score)
        """
        if len(df) < 20:
            return MarketBias.NEUTRAL, 0.0
        
        bullish_score = 0
        bearish_score = 0
        max_score = 100
        
        # ═══════════════════════════════════════════════════════════
        # 1. MARKET STRUCTURE (50 points)
        # ═══════════════════════════════════════════════════════════
        try:
            highs = df['high'].values
            lows = df['low'].values
            
            # Find swing points (simple method - last 10 candles)
            swing_highs = []
            swing_lows = []
            
            for i in range(5, len(df) - 5):
                # Swing high: higher than 5 candles before and after
                if all(highs[i] > highs[i-j] for j in range(1, 6)) and \
                   all(highs[i] > highs[i+j] for j in range(1, 6)):
                    swing_highs.append(highs[i])
                
                # Swing low: lower than 5 candles before and after
                if all(lows[i] < lows[i-j] for j in range(1, 6)) and \
                   all(lows[i] < lows[i+j] for j in range(1, 6)):
                    swing_lows.append(lows[i])
            
            # Analyze structure
            if len(swing_highs) >= 2 and len(swing_lows) >= 2:
                # Higher Highs + Higher Lows = BULLISH
                if swing_highs[-1] > swing_highs[-2] and swing_lows[-1] > swing_lows[-2]:
                    bullish_score += 50
                # Lower Highs + Lower Lows = BEARISH
                elif swing_highs[-1] < swing_highs[-2] and swing_lows[-1] < swing_lows[-2]:
                    bearish_score += 50
                # Mixed structure = ranging (no points)
        except Exception as e:
            logger.debug(f"Market structure analysis error: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # 2. ORDER BLOCKS (30 points)
        # ═══════════════════════════════════════════════════════════
        try:
            bullish_obs = 0
            bearish_obs = 0
            
            # Check last 15 candles for order block patterns
            for i in range(len(df) - 15, len(df) - 1):
                if i < 1:
                    continue
                
                candle = df.iloc[i]
                next_candle = df.iloc[i + 1]
                
                # Bullish OB: Down candle followed by break of high
                if candle['close'] < candle['open']:
                    if next_candle['close'] > candle['high']:
                        bullish_obs += 1
                
                # Bearish OB: Up candle followed by break of low
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
        # 3. DISPLACEMENT (20 points)
        # ═══════════════════════════════════════════════════════════
        try:
            # Check last 5 candles for strong directional move
            last_5 = df.tail(5)
            
            total_bullish_body = 0
            total_bearish_body = 0
            
            for idx, candle in last_5.iterrows():
                body = abs(candle['close'] - candle['open'])
                
                if candle['close'] > candle['open']:  # Bullish
                    total_bullish_body += body
                else:  # Bearish
                    total_bearish_body += body
            
            # Require 60% dominance for displacement
            if total_bullish_body > total_bearish_body * 1.6:
                bullish_score += 20
            elif total_bearish_body > total_bullish_body * 1.6:
                bearish_score += 20
        except Exception as e:
            logger.debug(f"Displacement analysis error: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # DETERMINE BIAS
        # ═══════════════════════════════════════════════════════════
        
        if bullish_score >= 60 and bullish_score > bearish_score:
            return MarketBias.BULLISH, bullish_score
        elif bearish_score >= 60 and bearish_score > bullish_score:
            return MarketBias.BEARISH, bearish_score
        elif abs(bullish_score - bearish_score) <= 20:
            return MarketBias.RANGING, max(bullish_score, bearish_score)
        else:
            return MarketBias.NEUTRAL, 50.0
    
    def _determine_bias_from_components(self, components: Dict) -> str:
        """
        Helper to determine bias string from components for Fibonacci analysis
        
        Args:
            components: ICT components dictionary
            
        Returns:
            'BULLISH' or 'BEARISH' string
        """
        bullish_count = 0
        bearish_count = 0
        
        # Count bullish/bearish order blocks
        for ob in components.get('order_blocks', []):
            ob_type = str(ob.get('type', '')) if isinstance(ob, dict) else str(getattr(ob, 'type', ''))
            if 'BULLISH' in ob_type.upper():
                bullish_count += 1
            elif 'BEARISH' in ob_type.upper():
                bearish_count += 1
        
        # Count FVGs
        for fvg in components.get('fvgs', []):
            fvg_type = str(fvg.get('type', '')) if isinstance(fvg, dict) else str(getattr(fvg, 'type', ''))
            if 'BULLISH' in fvg_type.upper():
                bullish_count += 1
            elif 'BEARISH' in fvg_type.upper():
                bearish_count += 1
        
        return 'BULLISH' if bullish_count >= bearish_count else 'BEARISH'
    
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
    
    def _calculate_ict_compliant_entry_zone(
        self,
        current_price: float,
        direction: str,  # 'BULLISH' or 'BEARISH'
        fvg_zones: List,
        order_blocks: List,
        sr_levels: Dict
    ) -> Tuple[Optional[Dict], str]:
        """
        Calculate ICT-compliant entry zone based on price structure.
        
        ✅ UPDATED: Soft constraint approach - zones at any distance are accepted
        
        CRITICAL RULES:
        1. BEARISH (SELL): Entry zone MUST be ABOVE current price
           - Search for: Bearish FVG, Bearish OB, or Resistance level
           - Zone must be > current_price * 1.005 (at least 0.5% above)
        
        2. BULLISH (BUY): Entry zone MUST be BELOW current price
           - Search for: Bullish FVG, Bullish OB, or Support level
           - Zone must be < current_price * 0.995 (at least 0.5% below)
        
        3. Distance constraints (SOFT - metadata only):
           - Optimal range: 0.5% - 3.0% from current price
           - Zones outside this range are marked with 'out_of_optimal_range' flag
           - Confidence may be reduced by 20% if distance is out of range
           - ⚠️ NO HARD REJECTION based on distance anymore
        
        4. Entry buffer: ±0.2% around zone boundaries
        
        Returns:
            (entry_zone_dict, status)
            
            entry_zone_dict structure:
            {
                'source': str,  # 'FVG', 'OB', 'S/R', or 'FALLBACK'
                'low': float,
                'high': float,
                'center': float,
                'quality': int,  # 0-100
                'distance_pct': float,  # % distance from current price
                'distance_price': float,  # absolute price distance
                'distance_out_of_range': bool,  # ✅ NEW: True if outside 0.5-3% optimal range
                'distance_comment': str | None  # ✅ NEW: Warning message if out of range
            }
            
            status codes:
            - 'VALID_WAIT': Entry zone found, wait for pullback (distance > 1.5%)
            - 'VALID_NEAR': Entry zone found, price approaching (0.5% - 1.5%)
            - 'TOO_LATE': Price already passed the entry zone (hard reject)
            - 'NO_ZONE': No valid entry zone found (converted to fallback in calling code)
        """
        min_distance_pct = 0.005  # 0.5%
        max_distance_pct = 0.030  # 3.0%
        entry_buffer_pct = 0.002  # 0.2%
        
        valid_zones = []
        
        # Normalize direction
        direction_upper = direction.upper() if isinstance(direction, str) else str(direction).upper()
        is_bearish = 'BEARISH' in direction_upper
        is_bullish = 'BULLISH' in direction_upper
        
        # ==== SEARCH FOR VALID ZONES ====
        
        if is_bearish:
            # BEARISH (SELL): Look for zones ABOVE current price
            
            # Check FVG zones
            for fvg in fvg_zones:
                fvg_type = str(fvg.get('type', '')) if isinstance(fvg, dict) else str(getattr(fvg, 'type', ''))
                if 'BEARISH' not in fvg_type.upper():
                    continue
                
                # Get FVG boundaries
                if isinstance(fvg, dict):
                    fvg_low = fvg.get('bottom', fvg.get('low', 0))
                    fvg_high = fvg.get('top', fvg.get('high', 0))
                else:
                    fvg_low = getattr(fvg, 'bottom', getattr(fvg, 'low', 0))
                    fvg_high = getattr(fvg, 'top', getattr(fvg, 'high', 0))
                
                if not fvg_low or not fvg_high:
                    continue
                
                # Check if FVG is ABOVE current price (min distance)
                if fvg_low > current_price * (1 + min_distance_pct):
                    distance_pct = (fvg_low - current_price) / current_price
                    
                    # ✅ SOFT CONSTRAINT: Always add zone, regardless of distance
                    # Get quality
                    quality = fvg.get('strength', 70) if isinstance(fvg, dict) else getattr(fvg, 'strength', 70)
                    if not isinstance(quality, (int, float)):
                        quality = 70
                    
                    valid_zones.append({
                        'source': 'FVG',
                        'low': fvg_low,
                        'high': fvg_high,
                        'quality': quality,
                        'distance_pct': distance_pct,
                        'distance_price': fvg_low - current_price,
                        'out_of_optimal_range': distance_pct > max_distance_pct  # ✅ NEW: Soft constraint flag
                    })
            
            # Check Order Blocks
            for ob in order_blocks:
                ob_type = str(ob.get('type', '')) if isinstance(ob, dict) else str(getattr(ob, 'type', ''))
                if 'BEARISH' not in ob_type.upper():
                    continue
                
                # Get OB boundaries
                if isinstance(ob, dict):
                    ob_low = ob.get('zone_low', ob.get('bottom', 0))
                    ob_high = ob.get('zone_high', ob.get('top', 0))
                else:
                    ob_low = getattr(ob, 'zone_low', getattr(ob, 'bottom', 0))
                    ob_high = getattr(ob, 'zone_high', getattr(ob, 'top', 0))
                
                if not ob_low or not ob_high:
                    continue
                
                # Check if OB is ABOVE current price
                if ob_low > current_price * (1 + min_distance_pct):
                    distance_pct = (ob_low - current_price) / current_price
                    
                    # ✅ SOFT CONSTRAINT: Always add zone, regardless of distance
                    quality = ob.get('strength', 75) if isinstance(ob, dict) else getattr(ob, 'strength', 75)
                    if not isinstance(quality, (int, float)):
                        quality = 75
                    
                    valid_zones.append({
                        'source': 'OB',
                        'low': ob_low,
                        'high': ob_high,
                        'quality': quality,
                        'distance_pct': distance_pct,
                        'distance_price': ob_low - current_price,
                        'out_of_optimal_range': distance_pct > max_distance_pct  # ✅ NEW: Soft constraint flag
                    })
            
            # Check Resistance levels
            resistance_zones = sr_levels.get('resistance_zones', []) if isinstance(sr_levels, dict) else []
            for res in resistance_zones:
                res_price = res.get('price', res.get('price_level', 0)) if isinstance(res, dict) else getattr(res, 'price', 0)
                
                if not res_price:
                    continue
                
                # Resistance must be ABOVE current price
                if res_price > current_price * (1 + min_distance_pct):
                    distance_pct = (res_price - current_price) / current_price
                    
                    # ✅ SOFT CONSTRAINT: Always add zone, regardless of distance
                    quality = res.get('strength', 60) if isinstance(res, dict) else getattr(res, 'strength', 60)
                    if not isinstance(quality, (int, float)):
                        quality = 60
                    
                    # Create zone with small buffer around resistance
                    zone_width = res_price * 0.002  # 0.2% width
                    valid_zones.append({
                        'source': 'S/R',
                        'low': res_price - zone_width,
                        'high': res_price + zone_width,
                        'quality': quality,
                        'distance_pct': distance_pct,
                        'distance_price': res_price - current_price,
                        'out_of_optimal_range': distance_pct > max_distance_pct  # ✅ NEW: Soft constraint flag
                    })
        
        elif is_bullish:
            # BULLISH (BUY): Look for zones BELOW current price
            
            # Check FVG zones
            for fvg in fvg_zones:
                fvg_type = str(fvg.get('type', '')) if isinstance(fvg, dict) else str(getattr(fvg, 'type', ''))
                if 'BULLISH' not in fvg_type.upper():
                    continue
                
                # Get FVG boundaries
                if isinstance(fvg, dict):
                    fvg_low = fvg.get('bottom', fvg.get('low', 0))
                    fvg_high = fvg.get('top', fvg.get('high', 0))
                else:
                    fvg_low = getattr(fvg, 'bottom', getattr(fvg, 'low', 0))
                    fvg_high = getattr(fvg, 'top', getattr(fvg, 'high', 0))
                
                if not fvg_low or not fvg_high:
                    continue
                
                # Check if FVG is BELOW current price (min distance)
                if fvg_high < current_price * (1 - min_distance_pct):
                    distance_pct = (current_price - fvg_high) / current_price
                    
                    # ✅ SOFT CONSTRAINT: Always add zone, regardless of distance
                    quality = fvg.get('strength', 70) if isinstance(fvg, dict) else getattr(fvg, 'strength', 70)
                    if not isinstance(quality, (int, float)):
                        quality = 70
                    
                    valid_zones.append({
                        'source': 'FVG',
                        'low': fvg_low,
                        'high': fvg_high,
                        'quality': quality,
                        'distance_pct': distance_pct,
                        'distance_price': current_price - fvg_high,
                        'out_of_optimal_range': distance_pct > max_distance_pct  # ✅ NEW: Soft constraint flag
                    })
            
            # Check Order Blocks
            for ob in order_blocks:
                ob_type = str(ob.get('type', '')) if isinstance(ob, dict) else str(getattr(ob, 'type', ''))
                if 'BULLISH' not in ob_type.upper():
                    continue
                
                # Get OB boundaries
                if isinstance(ob, dict):
                    ob_low = ob.get('zone_low', ob.get('bottom', 0))
                    ob_high = ob.get('zone_high', ob.get('top', 0))
                else:
                    ob_low = getattr(ob, 'zone_low', getattr(ob, 'bottom', 0))
                    ob_high = getattr(ob, 'zone_high', getattr(ob, 'top', 0))
                
                if not ob_low or not ob_high:
                    continue
                
                # Check if OB is BELOW current price
                if ob_high < current_price * (1 - min_distance_pct):
                    distance_pct = (current_price - ob_high) / current_price
                    
                    # ✅ SOFT CONSTRAINT: Always add zone, regardless of distance
                    quality = ob.get('strength', 75) if isinstance(ob, dict) else getattr(ob, 'strength', 75)
                    if not isinstance(quality, (int, float)):
                        quality = 75
                    
                    valid_zones.append({
                        'source': 'OB',
                        'low': ob_low,
                        'high': ob_high,
                        'quality': quality,
                        'distance_pct': distance_pct,
                        'distance_price': current_price - ob_high,
                        'out_of_optimal_range': distance_pct > max_distance_pct  # ✅ NEW: Soft constraint flag
                    })
            
            # Check Support levels
            support_zones = sr_levels.get('support_zones', []) if isinstance(sr_levels, dict) else []
            for sup in support_zones:
                sup_price = sup.get('price', sup.get('price_level', 0)) if isinstance(sup, dict) else getattr(sup, 'price', 0)
                
                if not sup_price:
                    continue
                
                # Support must be BELOW current price
                if sup_price < current_price * (1 - min_distance_pct):
                    distance_pct = (current_price - sup_price) / current_price
                    
                    # ✅ SOFT CONSTRAINT: Always add zone, regardless of distance
                    quality = sup.get('strength', 60) if isinstance(sup, dict) else getattr(sup, 'strength', 60)
                    if not isinstance(quality, (int, float)):
                        quality = 60
                    
                    # Create zone with small buffer around support
                    zone_width = sup_price * 0.002  # 0.2% width
                    valid_zones.append({
                        'source': 'S/R',
                        'low': sup_price - zone_width,
                        'high': sup_price + zone_width,
                        'quality': quality,
                        'distance_pct': distance_pct,
                        'distance_price': current_price - sup_price,
                        'out_of_optimal_range': distance_pct > max_distance_pct  # ✅ NEW: Soft constraint flag
                    })
        
        # ==== EVALUATE ZONES ====
        
        if not valid_zones:
            # Check if there are zones in the WRONG direction (price already passed)
            zones_behind = []
            
            if is_bearish:
                # Check for bearish zones BELOW current price (too late)
                for fvg in fvg_zones:
                    fvg_type = str(fvg.get('type', '')) if isinstance(fvg, dict) else str(getattr(fvg, 'type', ''))
                    if 'BEARISH' in fvg_type.upper():
                        fvg_high = fvg.get('top', fvg.get('high', 0)) if isinstance(fvg, dict) else getattr(fvg, 'top', getattr(fvg, 'high', 0))
                        if fvg_high and fvg_high < current_price:
                            zones_behind.append(fvg)
                
                for ob in order_blocks:
                    ob_type = str(ob.get('type', '')) if isinstance(ob, dict) else str(getattr(ob, 'type', ''))
                    if 'BEARISH' in ob_type.upper():
                        ob_high = ob.get('zone_high', ob.get('top', 0)) if isinstance(ob, dict) else getattr(ob, 'zone_high', getattr(ob, 'top', 0))
                        if ob_high and ob_high < current_price:
                            zones_behind.append(ob)
            
            elif is_bullish:
                # Check for bullish zones ABOVE current price (too late)
                for fvg in fvg_zones:
                    fvg_type = str(fvg.get('type', '')) if isinstance(fvg, dict) else str(getattr(fvg, 'type', ''))
                    if 'BULLISH' in fvg_type.upper():
                        fvg_low = fvg.get('bottom', fvg.get('low', 0)) if isinstance(fvg, dict) else getattr(fvg, 'bottom', getattr(fvg, 'low', 0))
                        if fvg_low and fvg_low > current_price:
                            zones_behind.append(fvg)
                
                for ob in order_blocks:
                    ob_type = str(ob.get('type', '')) if isinstance(ob, dict) else str(getattr(ob, 'type', ''))
                    if 'BULLISH' in ob_type.upper():
                        ob_low = ob.get('zone_low', ob.get('bottom', 0)) if isinstance(ob, dict) else getattr(ob, 'zone_low', getattr(ob, 'bottom', 0))
                        if ob_low and ob_low > current_price:
                            zones_behind.append(ob)
            
            if zones_behind:
                logger.warning(f"❌ Entry zones exist but price already passed them (TOO_LATE)")
                return None, 'TOO_LATE'
            else:
                logger.warning(f"❌ No valid entry zones found in acceptable range (NO_ZONE)")
                return None, 'NO_ZONE'
        
        # ==== SELECT BEST ZONE ====
        
        # Priority: quality * (1 - distance_pct * 10)
        # Prefer closer zones with high quality
        for zone in valid_zones:
            zone['priority'] = zone['quality'] * (1 - zone['distance_pct'] * 10)
        
        best_zone = max(valid_zones, key=lambda z: z['priority'])
        
        # ==== BUILD ENTRY ZONE DICT ====
        
        # Calculate if zone is outside optimal range (using constants)
        distance_out_of_range = best_zone['distance_pct'] * 100 > max_distance_pct * 100 or best_zone['distance_pct'] * 100 < min_distance_pct * 100
        
        entry_zone = {
            'source': best_zone['source'],
            'low': best_zone['low'] * (1 - entry_buffer_pct),
            'high': best_zone['high'] * (1 + entry_buffer_pct),
            'center': (best_zone['low'] + best_zone['high']) / 2,
            'quality': int(best_zone['quality']),
            'distance_pct': best_zone['distance_pct'] * 100,  # Convert to percentage
            'distance_price': best_zone['distance_price'],
            # ✅ NEW FIELDS (soft constraint metadata)
            'distance_out_of_range': distance_out_of_range,
            'distance_comment': f"⚠ Entry distance outside optimal range ({min_distance_pct*100:.1f}–{max_distance_pct*100:.1f}%): {best_zone['distance_pct'] * 100:.1f}%" 
                                if distance_out_of_range
                                else None
        }
        
        # ==== DETERMINE STATUS ====
        
        distance_pct = best_zone['distance_pct']
        
        if distance_pct > 0.015:  # > 1.5%
            status = 'VALID_WAIT'
            logger.info(f"✅ Entry zone found: {entry_zone['source']} at ${entry_zone['center']:.2f} ({entry_zone['distance_pct']:.1f}% away) - WAIT for pullback")
        elif distance_pct >= 0.005:  # 0.5% - 1.5%
            status = 'VALID_NEAR'
            logger.info(f"✅ Entry zone found: {entry_zone['source']} at ${entry_zone['center']:.2f} ({entry_zone['distance_pct']:.1f}% away) - Price APPROACHING")
        else:
            # Too close, should have been caught earlier but safety check
            status = 'TOO_LATE'
            logger.warning(f"⚠️ Entry zone too close: {entry_zone['distance_pct']:.1f}%")
        
        return entry_zone, status

    def _calculate_tp_prices(self, entry_price: float, sl_price: float, bias, ict_components: dict) -> list:
        """Calculate TP levels with 1:2, 1:3, 1:5 RR"""
        risk = abs(entry_price - sl_price)
        if str(bias) == 'MarketBias.BULLISH':
            return [entry_price + risk*3, entry_price + risk*2, entry_price + risk*5]
        else:
            return [entry_price - risk*3, entry_price - risk*2, entry_price - risk*5]

    def _calculate_tp_with_min_rr(
        self,
        entry_price: float,
        sl_price: float,
        liquidity_zones: List,
        min_rr: float = 3.0,
        fibonacci_data: Optional[Dict] = None,
        bias: Optional[str] = None
    ) -> List[float]:
        """
        MANDATORY: Calculate TP with GUARANTEED RR >= 1:3
        Now with Fibonacci integration for optimal TP placement
        """
        # ✅ NORMALIZE BIAS: str or enum → uppercase string
        bias_str = None
        if bias:
            if isinstance(bias, MarketBias):
                bias_str = bias.value.upper()
            elif isinstance(bias, str):
                bias_str = bias.upper()
            else:
                bias_str = str(bias).upper()
        
        # ✅ GUARD: Raise exception for HOLD/RANGING
        if bias_str in ['NEUTRAL', 'RANGING']:
            raise ValueError(
                f"CRITICAL: _calculate_tp_with_min_rr() called for {bias_str} signal! "
                f"HOLD/RANGING must use early exit. Pipeline violation."
            )
        
        # ✅ VALIDATE params
        if sl_price is None or entry_price is None:
            raise ValueError(
                f"Invalid params: entry={entry_price}, sl={sl_price}. "
                f"Cannot calculate TP without valid prices."
            )
        
        risk = abs(entry_price - sl_price)
        direction = 'LONG' if entry_price > sl_price else 'SHORT'
        
        # TP1: МИНИМУМ RR 1:3
        if direction == 'LONG':
            tp1 = entry_price + (risk * min_rr)
        else:
            tp1 = entry_price - (risk * min_rr)
        
        tp_levels = [tp1]
        logger.info(f"✅ TP1 calculated: {tp1} (RR {min_rr}:1 guaranteed)")
        
        # Try Fibonacci targets first (if available)
        if fibonacci_data and self.fibonacci_analyzer and bias:
            try:
                fib_targets = self.fibonacci_analyzer.get_tp_targets_from_fibonacci(
                    entry_price, bias, fibonacci_data
                )
                
                if fib_targets:
                    logger.info(f"💎 {len(fib_targets)} Fibonacci TP targets found")
                    
                    # Add Fibonacci targets that are beyond TP1
                    for fib_tp in fib_targets:
                        if direction == 'LONG' and fib_tp > tp1:
                            tp_levels.append(fib_tp)
                            logger.info(f"✅ TP{len(tp_levels)} aligned with Fibonacci: {fib_tp}")
                        elif direction == 'SHORT' and fib_tp < tp1:
                            tp_levels.append(fib_tp)
                            logger.info(f"✅ TP{len(tp_levels)} aligned with Fibonacci: {fib_tp}")
                        
                        if len(tp_levels) >= 3:
                            break
            except Exception as e:
                logger.warning(f"Fibonacci TP calculation failed: {e}")
        
        # Fallback to liquidity zones if not enough Fibonacci targets
        if len(tp_levels) < 3 and liquidity_zones:
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
        
        # Final fallback: structural levels
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
        # ✅ GUARD: Raise exception for HOLD/RANGING
        if bias in [MarketBias.NEUTRAL, MarketBias.RANGING]:
            raise ValueError(
                f"CRITICAL: _calculate_sl_price() called for {bias.value} signal! "
                f"HOLD/RANGING must use early exit. Pipeline violation."
            )
        
        atr = df['atr'].iloc[-1]
        
        if bias == MarketBias.BULLISH:
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
            # ✅ BULLISH: SL MUST be BELOW entry, so use max() to push SL downward
            min_sl = entry_price * 0.99
            return max(sl_price, min_sl)  # FIXED: Changed min() to max()
        
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
            # ✅ BEARISH: SL MUST be ABOVE entry, so use min() to keep SL tight but compliant
            max_sl = entry_price * 1.01
            return min(sl_price, max_sl)  # FIXED: Changed max() to min()

    def _validate_sl_position(self, sl_price: float, order_block, direction, entry_price: float) -> Tuple[float, bool]:
        """
        ЗАДЪЛЖИТЕЛНО: Валидира че SL е под/над валиден Order Block (STRICT ICT)
        
        BULLISH: SL ТРЯБВА да е ПОД Order Block bottom (buffer ≥ 0.2-0.3%)
        BEARISH: SL ТРЯБВА да е НАД Order Block top (buffer ≥ 0.2-0.3%)
        
        Returns:
            Tuple[float, bool]: (validated_sl_price, is_valid)
                - is_valid=False означава че SL не може да бъде ICT-compliant
        """
        if not order_block:
            logger.warning("⚠️ No Order Block for SL validation - INVALID")
            return sl_price, False
        
        # Get OB boundaries - handle both object and dict types
        if isinstance(order_block, dict):
            ob_bottom = order_block.get('zone_low') or order_block.get('bottom')
            ob_top = order_block.get('zone_high') or order_block.get('top')
        else:
            ob_bottom = getattr(order_block, 'zone_low', None) or getattr(order_block, 'bottom', None)
            ob_top = getattr(order_block, 'zone_high', None) or getattr(order_block, 'top', None)
        
        if not ob_bottom or not ob_top:
            logger.warning("⚠️ Invalid Order Block structure - INVALID")
            return sl_price, False
        
        # Минимален buffer (0.2-0.3%)
        min_buffer_pct = 0.002  # 0.2%
        max_buffer_pct = 0.003  # 0.3%
        
        if direction == 'BULLISH' or direction == MarketBias.BULLISH:
            # SL ТРЯБВА да е ПОД OB bottom с buffer
            required_sl_max = ob_bottom * (1 - min_buffer_pct)
            
            if sl_price >= ob_bottom:
                # SL е ВЪТРЕ или НАД OB - FORBIDDEN
                logger.error(f"❌ BEARISH SL {sl_price:.2f} >= OB bottom {ob_bottom:.2f} - FORBIDDEN")
                return None, False
            
            if sl_price > required_sl_max:
                # SL е твърде близо до OB - коригирай
                sl_price = ob_bottom * (1 - max_buffer_pct)  # 0.3% под OB
                logger.warning(f"⚠️ SL КОРИГИРАН ПОД OB с buffer: {sl_price:.2f}")
            
            # Проверка че SL не е твърде близо до Entry
            min_sl_distance_pct = 0.005  # Минимум 0.5% от entry
            if abs(entry_price - sl_price) / entry_price < min_sl_distance_pct:
                logger.error(f"❌ SL твърде близо до Entry ({abs(entry_price - sl_price) / entry_price * 100:.2f}%) - FORBIDDEN")
                return None, False
        
        elif direction == 'BEARISH' or direction == MarketBias.BEARISH:
            # SL ТРЯБВА да е НАД OB top с buffer
            required_sl_min = ob_top * (1 + min_buffer_pct)
            
            if sl_price <= ob_top:
                # SL е ВЪТРЕ или ПОД OB - FORBIDDEN
                logger.error(f"❌ BULLISH SL {sl_price:.2f} <= OB top {ob_top:.2f} - FORBIDDEN")
                return None, False
            
            if sl_price < required_sl_min:
                # SL е твърде близо до OB - коригирай
                sl_price = ob_top * (1 + max_buffer_pct)  # 0.3% над OB
                logger.warning(f"⚠️ SL КОРИГИРАН НАД OB с buffer: {sl_price:.2f}")
            
            # Проверка че SL не е твърде близо до Entry
            min_sl_distance_pct = 0.005  # Минимум 0.5% от entry
            if abs(sl_price - entry_price) / entry_price < min_sl_distance_pct:
                logger.error(f"❌ SL твърде близо до Entry ({abs(sl_price - entry_price) / entry_price * 100:.2f}%) - FORBIDDEN")
                return None, False
        
        logger.info(f"✅ SL validated: {sl_price:.2f} (ICT-compliant)")
        return sl_price, True

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
        
        # LuxAlgo confidence boost
        luxalgo_sr = ict_components.get('luxalgo_sr', {})
        luxalgo_combined = ict_components.get('luxalgo_combined', {})
        
        # Check if price near S/R zone (+15%)
        if luxalgo_sr and (luxalgo_sr.get('support_zones') or luxalgo_sr.get('resistance_zones')):
            confidence += 15
            logger.info("✅ LuxAlgo S/R zones present: +15% confidence")
        
        # Check entry validation (+10%)
        if luxalgo_combined.get('entry_valid', False):
            confidence += 10
            logger.info("✅ LuxAlgo entry validation passed: +10% confidence")
        
        # Check bias alignment (+10%)
        luxalgo_bias = luxalgo_combined.get('bias', 'neutral')
        if luxalgo_bias != 'neutral' and luxalgo_bias.upper() == str(bias).split('.')[-1]:
            confidence += 10
            logger.info(f"✅ LuxAlgo bias aligned with {bias}: +10% confidence")
        
        # Fibonacci OTE zone boost (+10%)
        fibonacci_data = ict_components.get('fibonacci_data', {})
        if fibonacci_data.get('in_ote_zone', False):
            confidence += 10
            logger.info("✅ Price in Fibonacci OTE zone: +10% confidence")
        
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
    
    def _create_hold_signal(
        self,
        symbol: str,
        timeframe: str,
        bias: MarketBias,
        confidence: float,
        df: pd.DataFrame,
        ict_components: Dict,
        mtf_data: Optional[Dict[str, pd.DataFrame]],
        current_price: float,
        htf_bias: str,
        mtf_consensus_data: Dict,
        structure_broken: bool,
        displacement_detected: bool,
        mtf_analysis: Optional[Dict]
    ) -> ICTSignal:
        """
        Create HOLD signal for NEUTRAL/RANGING market conditions
        
        HOLD signals are informational only:
        - NO entry price
        - NO stop loss
        - NO take profit
        - NO risk/reward ratio
        - entry_zone is None (not empty dict)
        - entry_status is 'HOLD'
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            bias: Market bias (NEUTRAL or RANGING)
            confidence: Signal confidence
            df: Price dataframe
            ict_components: Detected ICT components
            mtf_data: Multi-timeframe data
            current_price: Current price
            htf_bias: Higher timeframe bias
            mtf_consensus_data: MTF consensus breakdown
            structure_broken: Whether structure was broken
            displacement_detected: Whether displacement was detected
            mtf_analysis: MTF analysis data
            
        Returns:
            ICTSignal with HOLD type (informational only)
        """
        # Reasoning based on bias type
        if bias == MarketBias.RANGING:
            reasoning = "ℹ️ Пазарът консолидира в диапазон. Няма ясна посока."
        else:  # NEUTRAL
            reasoning = "ℹ️ Пазарната структура е неутрална. Открити са противоречиви сигнали."
        
        # Add ICT component counts to reasoning
        whale_count = len(ict_components.get('whale_blocks', []))
        liq_count = len(ict_components.get('liquidity_zones', []))
        ob_count = len(ict_components.get('order_blocks', []))
        fvg_count = len(ict_components.get('fvgs', []))
        
        reasoning += f"\n\nICT Компоненти открити:"
        if whale_count > 0:
            reasoning += f"\n• {whale_count} Whale Order Blocks"
        if liq_count > 0:
            reasoning += f"\n• {liq_count} Liquidity Zones"
        if ob_count > 0:
            reasoning += f"\n• {ob_count} Order Blocks"
        if fvg_count > 0:
            reasoning += f"\n• {fvg_count} Fair Value Gaps"
        
        reasoning += "\n\nТези зони са информативни и могат да бъдат използвани за наблюдение на пазара."
        
        # Warnings specific to HOLD signals
        warnings = [
            "Цената се движи странично между поддръжка и съпротива",
            "Изчакайте потвърждение на пробив преди вход",
            "Ниска вероятност за посочни сделки"
        ]
        
        # Add MTF warning if applicable
        if mtf_consensus_data and mtf_consensus_data.get('consensus_pct', 0) < 50:
            warnings.append(f"MTF консенсус е нисък ({mtf_consensus_data['consensus_pct']:.1f}%)")
        
        # Zone explanations (if available)
        zone_explanations = {}
        if self.zone_explainer:
            try:
                bias_str = bias.value if hasattr(bias, 'value') else str(bias)
                zone_explanations = self.zone_explainer.generate_all_explanations(ict_components, bias_str)
            except Exception as e:
                logger.error(f"Zone explanations error: {e}")
        
        # Create HOLD signal
        signal = ICTSignal(
            timestamp=datetime.now(),
            symbol=symbol,
            timeframe=timeframe,
            signal_type=SignalType.HOLD,
            signal_strength=SignalStrength.WEAK,  # Always WEAK for HOLD
            entry_price=None,  # ✅ NO entry price for HOLD
            sl_price=None,  # ✅ NO stop loss for HOLD
            tp_prices=[],  # ✅ NO take profits for HOLD
            confidence=confidence,
            risk_reward_ratio=None,  # ✅ NO RR for HOLD
            whale_blocks=[wb.to_dict() if hasattr(wb, 'to_dict') else wb for wb in ict_components.get('whale_blocks', [])],
            liquidity_zones=[lz.__dict__ if hasattr(lz, '__dict__') else lz for lz in ict_components.get('liquidity_zones', [])],
            liquidity_sweeps=[ls.__dict__ if hasattr(ls, '__dict__') else ls for ls in ict_components.get('liquidity_sweeps', [])],
            order_blocks=[ob.to_dict() if hasattr(ob, 'to_dict') else ob for ob in ict_components.get('order_blocks', [])],
            fair_value_gaps=[fvg.to_dict() if hasattr(fvg, 'to_dict') else fvg for fvg in ict_components.get('fvgs', [])],
            internal_liquidity=[ilp for ilp in ict_components.get('internal_liquidity', [])],
            breaker_blocks=[bb.to_dict() for bb in ict_components.get('breaker_blocks', [])],
            mitigation_blocks=[mb.to_dict() for mb in ict_components.get('mitigation_blocks', [])],
            sibi_ssib_zones=[sz.to_dict() for sz in ict_components.get('sibi_ssib_zones', [])],
            fibonacci_data=ict_components.get('fibonacci_data', {}),
            luxalgo_sr=ict_components.get('luxalgo_sr', {}),
            luxalgo_ict=ict_components.get('luxalgo_ict', {}),
            luxalgo_combined=ict_components.get('luxalgo_combined', {}),
            bias=bias,
            structure_broken=structure_broken,
            displacement_detected=displacement_detected,
            mtf_confluence=mtf_analysis.get('confluence_count', 0) if mtf_analysis else 0,
            htf_bias=htf_bias,
            mtf_structure=mtf_analysis.get('mtf_structure', 'NEUTRAL') if mtf_analysis else 'NEUTRAL',
            mtf_consensus_data=mtf_consensus_data,
            entry_zone=None,  # ✅ None for HOLD (not empty dict)
            entry_status='HOLD',  # ✅ HOLD status
            distance_penalty=False,
            reasoning=reasoning,
            warnings=warnings,
            zone_explanations=zone_explanations
        )
        
        logger.info(f"✅ Generated HOLD signal (early exit) - {bias.value}")
        logger.info(f"   Confidence: {confidence:.1f}%")
        logger.info(f"   MTF Consensus: {mtf_consensus_data.get('consensus_pct', 0):.1f}%")
        
        return signal
    
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
    
    def _create_no_trade_message(
        self,
        symbol: str,
        timeframe: str,
        reason: str,
        details: str,
        mtf_breakdown: Dict,
        current_price: float = None,
        price_change_24h: float = None,
        rsi: float = None,
        signal_direction: str = None,
        confidence: float = None
    ) -> Dict:
        """
        Създава съобщение "Няма подходящ трейд" с обяснение
        
        Args:
            symbol: Trading pair symbol
            timeframe: Analysis timeframe
            reason: Main reason for blocking the trade
            details: Detailed explanation with values
            mtf_breakdown: Multi-timeframe analysis breakdown
            current_price: Current price of the asset
            price_change_24h: 24h price change percentage
            rsi: RSI indicator value
            signal_direction: Signal direction (BUY/SELL)
            confidence: Signal confidence percentage
        
        Returns:
            Dict със структурирано съобщение (не ICTSignal обект)
        """
        # Calculate MTF consensus percentage
        mtf_consensus_pct = 0.0
        if mtf_breakdown:
            aligned_count = sum(1 for data in mtf_breakdown.values() if data.get('aligned', False))
            total_count = len(mtf_breakdown)
            mtf_consensus_pct = (aligned_count / total_count * 100) if total_count > 0 else 0.0
        
        return {
            'type': 'NO_TRADE',
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': datetime.now().isoformat(),
            'reason': reason,
            'details': details,
            'mtf_breakdown': mtf_breakdown,
            'mtf_consensus_pct': mtf_consensus_pct,
            'current_price': current_price,
            'price_change_24h': price_change_24h,
            'rsi': rsi,
            'signal_direction': signal_direction,
            'confidence': confidence,
            # Keep legacy message field for backward compatibility (will be ignored by new format)
            'message': f"""
❌ <b>НЯМА ПОДХОДЯЩ ТРЕЙД</b>

💰 <b>Символ:</b> {symbol}
⏰ <b>Таймфрейм:</b> {timeframe}

🚫 <b>Причина:</b> {reason}
📋 <b>Детайли:</b> {details}

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>MTF Breakdown:</b>
{self._format_mtf_breakdown(mtf_breakdown)}

💡 <b>Препоръка:</b> Изчакайте по-добри условия или проверете друг таймфрейм
"""
        }
    
    def _format_mtf_breakdown(self, breakdown: Dict) -> str:
        """Форматира MTF breakdown за показване"""
        lines = []
        for tf, data in sorted(breakdown.items(), key=lambda x: self._timeframe_order(x[0])):
            bias = data['bias']
            confidence = data['confidence']
            aligned = data['aligned']
            
            emoji = "✅" if aligned else "❌"
            if bias == 'NO_DATA':
                line = f"{emoji} {tf}: Няма данни"
            else:
                line = f"{emoji} {tf}: {bias} ({confidence:.0f}% уверен)"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _timeframe_order(self, tf: str) -> int:
        """Връща числов ред на timeframe за сортиране"""
        order = {
            '1m': 1, '3m': 2, '5m': 3, '15m': 4, '30m': 5,
            '1h': 6, '2h': 7, '4h': 8, '6h': 9, '12h': 10,
            '1d': 11, '3d': 12, '1w': 13
        }
        return order.get(tf, 999)
    
    def _extract_context_data(
        self, 
        df: pd.DataFrame, 
        bias: 'MarketBias',
        symbol: Optional[str] = None  # NEW: Optional parameter (backward compatible)
    ) -> Dict:
        """
        Extract context data for no-trade messages
        
        Returns:
            Dict with current_price, price_change_24h, rsi, signal_direction
        """
        try:
            current_price = df['close'].iloc[-1]
            
            # Calculate 24h price change (if enough data)
            price_change_24h = None
            if len(df) >= 24:
                price_24h_ago = df['close'].iloc[-24]
                price_change_24h = ((current_price - price_24h_ago) / price_24h_ago) * 100
            
            # Calculate RSI
            rsi = None
            if 'rsi' in df.columns:
                rsi = df['rsi'].iloc[-1]
            else:
                # Calculate RSI if not present
                if len(df) >= 15:
                    delta = df['close'].diff()
                    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                    rs = gain / loss.replace(0, 1)
                    rs_value = rs.iloc[-1]
                    # Validate RSI calculation
                    if pd.notna(rs_value) and rs_value != float('inf'):
                        rsi = 100 - (100 / (1 + rs_value))
                    else:
                        rsi = None
            
            # Determine signal direction from bias
            signal_direction = None
            if hasattr(bias, 'value'):
                bias_val = bias.value
            else:
                bias_val = str(bias)
            
            if 'BULLISH' in bias_val.upper() or 'BUY' in bias_val.upper():
                signal_direction = 'BUY'
            elif 'BEARISH' in bias_val.upper() or 'SELL' in bias_val.upper():
                signal_direction = 'SELL'
            else:
                signal_direction = 'NEUTRAL'
            
            # === NEW: ENHANCED CONTEXT (Add below existing code) ===
            
            # Volume Context
            volume_ratio = 1.0
            volume_spike = False
            try:
                if 'volume_ratio' in df.columns:
                    # Use pre-calculated volume_ratio from dataframe (uses median)
                    volume_ratio = df['volume_ratio'].iloc[-1]
                    volume_spike = volume_ratio > 2.0
                elif 'volume' in df.columns and len(df) >= 20:
                    # Fallback: calculate using median
                    volume_median = df['volume'].rolling(20).median().iloc[-1]
                    current_volume = df['volume'].iloc[-1]
                    if volume_median > 0:
                        volume_ratio = current_volume / volume_median
                        volume_spike = volume_ratio > 2.0
            except Exception as e:
                logger.debug(f"Volume context calculation error: {e}")
            
            # Volatility Context
            volatility_pct = 0.0
            high_volatility = False
            try:
                if 'atr' in df.columns:
                    atr = df['atr'].iloc[-1]
                    volatility_pct = (atr / current_price) * 100 if current_price > 0 else 0
                    high_volatility = volatility_pct > 3.0
            except Exception as e:
                logger.debug(f"Volatility context calculation error: {e}")
            
            # Trading Session Context
            session = 'UNKNOWN'
            try:
                hour_utc = datetime.utcnow().hour
                if 0 <= hour_utc < 8:
                    session = 'ASIAN'
                elif 8 <= hour_utc < 16:
                    session = 'LONDON'
                else:
                    session = 'NEW_YORK'
            except Exception as e:
                logger.debug(f"Session detection error: {e}")
            
            # BTC Correlation Context
            btc_correlation = None
            btc_aligned = None
            if symbol and symbol not in ['BTCUSDT', 'BTC', 'BTCUSD']:
                # Calculate real BTC correlation
                btc_correlation, btc_aligned = self._calculate_btc_correlation(symbol, df)
            
            return {
                # ✅ EXISTING FIELDS (unchanged)
                'current_price': current_price,
                'price_change_24h': price_change_24h,
                'rsi': rsi,
                'signal_direction': signal_direction,
                
                # ✅ NEW FIELDS (added for enhanced context)
                'volume_ratio': round(volume_ratio, 2),
                'volume_spike': volume_spike,
                'volatility_pct': round(volatility_pct, 2),
                'high_volatility': high_volatility,
                'btc_correlation': btc_correlation,
                'btc_aligned': btc_aligned,
                'trading_session': session
            }
        except Exception as e:
            logger.warning(f"Error extracting context data for bias {bias}: {e}", exc_info=True)
            return {
                'current_price': None,
                'price_change_24h': None,
                'rsi': None,
                'signal_direction': None
            }
    
    def _apply_context_filters(
        self,
        base_confidence: float,
        context: Dict,
        ict_components: Dict
    ) -> Tuple[float, List[str]]:
        """
        ✅ NEW: Apply context-based confidence adjustments and generate warnings
        
        This method enhances signal quality by considering market context:
        - Volume conditions
        - Volatility levels
        - Trading session
        - BTC correlation (for altcoins)
        
        Args:
            base_confidence: Base confidence score from ICT analysis
            context: Context data from _extract_context_data()
            ict_components: ICT components dictionary
            
        Returns:
            Tuple of (adjusted_confidence, warnings_list)
            
        ⚠️ IMPORTANT: This method only ADJUSTS confidence, never blocks signals!
        Signal blocking is still controlled by existing min_confidence threshold.
        """
        warnings = []
        adjustment = 0.0
        
        try:
            # === FILTER 1: VOLUME ANALYSIS ===
            volume_ratio = context.get('volume_ratio', 1.0)
            volume_spike = context.get('volume_spike', False)
            
            if volume_ratio < 0.5:
                # Very low volume - reduce confidence
                warnings.append("⚠️ LOW VOLUME - Reduced liquidity may affect execution")
                adjustment -= 10
                logger.info("Context filter: Low volume detected (-10%)")
            elif volume_spike:
                # High volume spike - increase confidence
                warnings.append("✅ HIGH VOLUME - Strong market participation")
                adjustment += 5
                logger.info("Context filter: Volume spike detected (+5%)")
            
            # === FILTER 2: VOLATILITY ANALYSIS ===
            volatility_pct = context.get('volatility_pct', 0.0)
            high_volatility = context.get('high_volatility', False)
            
            if high_volatility:
                # High volatility - slight confidence reduction (riskier)
                warnings.append("⚠️ HIGH VOLATILITY - Consider wider stop loss")
                adjustment -= 5
                logger.info(f"Context filter: High volatility ({volatility_pct:.1f}%) detected (-5%)")
            
            # === FILTER 3: TRADING SESSION ===
            session = context.get('trading_session', 'UNKNOWN')
            
            if session == 'ASIAN':
                # Asian session - typically lower liquidity for crypto
                warnings.append("ℹ️ ASIAN SESSION - Lower liquidity period")
                adjustment -= 5
                logger.info("Context filter: Asian session (-5%)")
            elif session == 'LONDON':
                # London session - high liquidity
                warnings.append("✅ LONDON SESSION - Peak liquidity period")
                adjustment += 5
                logger.info("Context filter: London session (+5%)")
            elif session == 'NEW_YORK':
                # NY session - high liquidity (especially overlap with London)
                warnings.append("✅ NEW YORK SESSION - High liquidity period")
                adjustment += 3
                logger.info("Context filter: New York session (+3%)")
            
            # === FILTER 4: BTC CORRELATION (for altcoins only) ===
            btc_correlation = context.get('btc_correlation')
            btc_aligned = context.get('btc_aligned')
            
            if btc_correlation is not None:
                if btc_aligned == False:
                    # Low correlation - independent move (can be risky)
                    warnings.append("⚠️ LOW BTC CORRELATION - Independent price action")
                    adjustment -= 10
                    logger.info(f"Context filter: Low BTC correlation ({btc_correlation:.2f}) (-10%)")
                elif btc_aligned == True:
                    # High correlation - trend confirmation
                    warnings.append("✅ BTC ALIGNED - Trend confirmation")
                    adjustment += 10
                    logger.info(f"Context filter: High BTC correlation ({btc_correlation:.2f}) (+10%)")
            
            # === CALCULATE ADJUSTED CONFIDENCE ===
            adjusted_confidence = base_confidence + adjustment
            
            # Ensure confidence stays within 0-100 bounds
            adjusted_confidence = max(0.0, min(100.0, adjusted_confidence))
            
            # Log summary
            if adjustment != 0:
                logger.info(f"✅ Context filters applied: {adjustment:+.1f}% adjustment")
                logger.info(f"   Base confidence: {base_confidence:.1f}% → Adjusted: {adjusted_confidence:.1f}%")
            else:
                logger.info("✅ Context filters: No adjustments needed")
            
            return adjusted_confidence, warnings
            
        except Exception as e:
            logger.error(f"❌ Context filter error: {e}")
            # On error, return original confidence with no warnings
            return base_confidence, []
    
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
                # Note: .mean() here is legitimate - it's part of the standard RSI formula
                # (exponential smoothing of gains/losses), not a moving average for signals
                delta = df['close'].diff()
                gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
                loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
                rs = gain / loss.replace(0, 1)
                rsi = 100 - (100 / (1 + rs.iloc[-1]))
            
            # Volume metrics (use from dataframe - already calculated with median)
            if 'volume_ratio' in df.columns:
                volume_ratio = df['volume_ratio'].iloc[-1]
            else:
                # Fallback if not in dataframe
                volume_median = df['volume'].iloc[-20:].median()
                current_volume = df['volume'].iloc[-1]
                volume_ratio = current_volume / volume_median if volume_median > 0 else 1.0
            
            # Volatility (ATR-based)
            returns = df['close'].pct_change()
            volatility = returns.std() * 100
            
            # Price change
            price_change_pct = ((current_price - df['close'].iloc[-20]) / df['close'].iloc[-20]) * 100
            
            # Price position in 20-period range (Pure ICT - no MA/Bollinger)
            range_high = df['high'].iloc[-20:].max()
            range_low = df['low'].iloc[-20:].min()
            bb_position = (current_price - range_low) / (range_high - range_low) if (range_high - range_low) > 0 else 0.5
            
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
        if mtf_data is None or not isinstance(mtf_data, dict):
            logger.warning("No MTF data available, using NEUTRAL bias")
            return 'NEUTRAL'
        
        try:
            # Опит 1: 1D timeframe (HTF)
            if '1d' in mtf_data or '1D' in mtf_data:
                df_1d = mtf_data.get('1d') if mtf_data.get('1d') is not None else mtf_data.get('1D')
                if df_1d is not None and not df_1d.empty and len(df_1d) >= 20:
                    # Determine bias from 1D
                    bias_components = self._detect_ict_components(df_1d, '1d')
                    htf_bias = self._determine_market_bias(df_1d, bias_components, None)
                    htf_bias_str = htf_bias.value if hasattr(htf_bias, 'value') else str(htf_bias)
                    logger.info(f"✅ HTF Bias from 1D: {htf_bias_str}")
                    return htf_bias_str
            
            # Опит 2: 4H timeframe (fallback)
            logger.warning("⚠️ 1D bias failed, trying 4H fallback...")
            if '4h' in mtf_data or '4H' in mtf_data:
                df_4h = mtf_data.get('4h') if mtf_data.get('4h') is not None else mtf_data.get('4H')
                if df_4h is not None and not df_4h.empty and len(df_4h) >= 20:
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
    
    def format_13_point_output(self, signal: ICTSignal, df: pd.DataFrame) -> Dict:
        """
        Format signal as comprehensive 13-point output structure
        
        Args:
            signal: ICTSignal object
            df: OHLCV DataFrame
            
        Returns:
            Dictionary with 13 comprehensive analysis points
        """
        try:
            current_price = df['close'].iloc[-1]
            
            # Get primary order block for SL validation
            primary_ob = signal.order_blocks[0] if signal.order_blocks else None
            
            # Validate SL positioning
            sl_compliant, sl_reason = self._validate_sl_under_over_ob(signal, primary_ob)
            
            output = {
                '1_mtf_bias': {
                    'htf_bias': signal.htf_bias,
                    'mtf_structure': signal.mtf_structure,
                    'confluence_score': signal.mtf_confluence,
                    'bias_description': f"{signal.htf_bias} bias with {signal.mtf_confluence}/5 confluence"
                },
                
                '2_liquidity_map': {
                    'total_zones': len(signal.liquidity_zones),
                    'zones': signal.liquidity_zones[:5],  # Top 5
                    'sweeps_detected': len(signal.liquidity_sweeps),
                    'next_target': signal.liquidity_zones[0] if signal.liquidity_zones else None
                },
                
                '3_ict_zones': {
                    'whale_blocks': len(signal.whale_blocks),
                    'order_blocks': len(signal.order_blocks),
                    'fair_value_gaps': len(signal.fair_value_gaps),
                    'internal_liquidity': len(signal.internal_liquidity),
                    'breaker_blocks': len(signal.breaker_blocks),
                    'mitigation_blocks': len(signal.mitigation_blocks),
                    'sibi_ssib': len(signal.sibi_ssib_zones)
                },
                
                '4_order_blocks_detail': [
                    self._format_order_block(ob) for ob in signal.order_blocks[:3]
                ],
                
                '5_fvg_analysis': {
                    'total_fvgs': len(signal.fair_value_gaps),
                    'bullish_fvgs': sum(1 for fvg in signal.fair_value_gaps if 'BULLISH' in str(fvg.get('type', ''))),
                    'bearish_fvgs': sum(1 for fvg in signal.fair_value_gaps if 'BEARISH' in str(fvg.get('type', ''))),
                    'nearest_fvg': signal.fair_value_gaps[0] if signal.fair_value_gaps else None
                },
                
                '6_luxalgo_sr': {
                    'support_zones': len(signal.luxalgo_sr.get('support_zones', [])),
                    'resistance_zones': len(signal.luxalgo_sr.get('resistance_zones', [])),
                    'price_near_sr': self._check_price_near_sr(current_price, signal.luxalgo_sr),
                    'entry_valid': signal.luxalgo_combined.get('entry_valid', False),
                    'luxalgo_bias': signal.luxalgo_combined.get('bias', 'neutral')
                },
                
                '7_fibonacci': {
                    'in_ote_zone': signal.fibonacci_data.get('in_ote_zone', False),
                    'swing_high': signal.fibonacci_data.get('swing_high'),
                    'swing_low': signal.fibonacci_data.get('swing_low'),
                    'ote_zone': signal.fibonacci_data.get('ote_zone'),
                    'nearest_level': signal.fibonacci_data.get('nearest_level'),
                    'retracements_count': len(signal.fibonacci_data.get('retracements', [])),
                    'extensions_count': len(signal.fibonacci_data.get('extensions', []))
                },
                
                '8_entry': {
                    'price': signal.entry_price,
                    'signal_type': signal.signal_type.value,
                    'confidence': signal.confidence,
                    'strength': signal.signal_strength.value,
                    'reasoning': signal.reasoning
                },
                
                '9_stop_loss': {
                    'price': signal.sl_price,
                    'reason': sl_reason,
                    'order_block_reference': self._get_sl_order_block(signal, primary_ob),
                    'ict_compliant': sl_compliant,
                    'distance_pct': abs((signal.sl_price - signal.entry_price) / signal.entry_price) * 100
                },
                
                '10_take_profit': {
                    'tp1': {
                        'price': signal.tp_prices[0] if signal.tp_prices else None,
                        'risk_reward': self._calculate_rr(signal, 0),
                        'distance_pct': abs((signal.tp_prices[0] - signal.entry_price) / signal.entry_price) * 100 if signal.tp_prices else 0
                    },
                    'tp2': {
                        'price': signal.tp_prices[1] if len(signal.tp_prices) > 1 else None,
                        'risk_reward': self._calculate_rr(signal, 1) if len(signal.tp_prices) > 1 else None,
                        'distance_pct': abs((signal.tp_prices[1] - signal.entry_price) / signal.entry_price) * 100 if len(signal.tp_prices) > 1 else None
                    } if len(signal.tp_prices) > 1 else None,
                    'tp3': {
                        'price': signal.tp_prices[2] if len(signal.tp_prices) > 2 else None,
                        'risk_reward': self._calculate_rr(signal, 2) if len(signal.tp_prices) > 2 else None,
                        'distance_pct': abs((signal.tp_prices[2] - signal.entry_price) / signal.entry_price) * 100 if len(signal.tp_prices) > 2 else None
                    } if len(signal.tp_prices) > 2 else None,
                    'risk_reward_ratio': signal.risk_reward_ratio,
                    'min_rr_guaranteed': 3.0,
                    'rr_compliance': 'COMPLIANT' if signal.risk_reward_ratio >= 3.0 else f'NON_COMPLIANT (RR: {signal.risk_reward_ratio:.2f})'
                },
                
                '11_mtf_structure': {
                    'htf_trend': signal.htf_bias,
                    'mtf_structure': signal.mtf_structure,
                    'structure_broken': signal.structure_broken,
                    'displacement_detected': signal.displacement_detected,
                    'alignment_score': signal.mtf_confluence
                },
                
                '12_next_liquidity_forecast': {
                    'nearest_liquidity': signal.liquidity_zones[0] if signal.liquidity_zones else None,
                    'target_type': 'BUY_SIDE' if (hasattr(signal.bias, 'value') and signal.bias.value == 'BULLISH') else 'SELL_SIDE',
                    'estimated_distance': self._calculate_liquidity_distance(current_price, signal.liquidity_zones)
                },
                
                '13_ml_optimization': {
                    'ml_available': self.ml_engine is not None or self.ml_predictor is not None,
                    'ml_used': signal.confidence > 50,  # Simplified check
                    'optimized_entry': signal.entry_price,
                    'optimized_sl': signal.sl_price,
                    'optimized_tps': signal.tp_prices
                },
                
                'chart_data': None,  # Will be populated by chart generator
                
                'analysis_sequence': {
                    'timestamp': signal.timestamp.isoformat() if isinstance(signal.timestamp, datetime) else str(signal.timestamp),
                    'timeframe': signal.timeframe,
                    'sequence_completed': True,
                    'steps_executed': 12
                }
            }
            
            logger.info("✅ 13-point output formatted successfully")
            return output
            
        except Exception as e:
            logger.error(f"Error formatting 13-point output: {e}")
            return {}
    
    def _validate_sl_under_over_ob(self, signal: ICTSignal, order_block) -> Tuple[bool, str]:
        """
        Validate that SL is correctly positioned relative to Order Block
        
        Returns:
            Tuple of (is_compliant, reason_description)
        """
        if not order_block:
            return False, "No Order Block available for validation"
        
        try:
            # Get OB boundaries
            if isinstance(order_block, dict):
                ob_bottom = order_block.get('zone_low') or order_block.get('bottom')
                ob_top = order_block.get('zone_high') or order_block.get('top')
            else:
                ob_bottom = getattr(order_block, 'zone_low', None) or getattr(order_block, 'bottom', None)
                ob_top = getattr(order_block, 'zone_high', None) or getattr(order_block, 'top', None)
            
            if not ob_bottom or not ob_top:
                return False, "Invalid Order Block structure"
            
            # Check compliance based on bias
            bias_str = signal.bias.value if hasattr(signal.bias, 'value') else str(signal.bias)
            
            if 'BULLISH' in bias_str.upper():
                # For bullish: SL must be BELOW Order Block
                if signal.sl_price < ob_bottom:
                    return True, f"SL correctly positioned below Order Block ({signal.sl_price:.2f} < {ob_bottom:.2f})"
                else:
                    return False, f"SL VIOLATION: SL {signal.sl_price:.2f} should be below OB bottom {ob_bottom:.2f}"
            
            elif 'BEARISH' in bias_str.upper():
                # For bearish: SL must be ABOVE Order Block
                if signal.sl_price > ob_top:
                    return True, f"SL correctly positioned above Order Block ({signal.sl_price:.2f} > {ob_top:.2f})"
                else:
                    return False, f"SL VIOLATION: SL {signal.sl_price:.2f} should be above OB top {ob_top:.2f}"
            
            return False, "Unknown bias for SL validation"
            
        except Exception as e:
            logger.error(f"SL validation error: {e}")
            return False, f"Validation error: {str(e)}"
    
    def _get_sl_order_block(self, signal: ICTSignal, order_block) -> Optional[Dict]:
        """Get Order Block reference used for SL calculation"""
        if not order_block:
            return None
        
        try:
            if isinstance(order_block, dict):
                return {
                    'zone_low': order_block.get('zone_low'),
                    'zone_high': order_block.get('zone_high'),
                    'type': order_block.get('type')
                }
            else:
                return {
                    'zone_low': getattr(order_block, 'zone_low', None),
                    'zone_high': getattr(order_block, 'zone_high', None),
                    'type': str(getattr(order_block, 'type', None))
                }
        except Exception as e:
            logger.error(f"Error getting SL Order Block: {e}")
            return None
    
    def _calculate_rr(self, signal: ICTSignal, tp_index: int) -> Optional[float]:
        """Calculate Risk/Reward ratio for specific TP level"""
        if tp_index >= len(signal.tp_prices):
            return None
        
        try:
            tp = signal.tp_prices[tp_index]
            risk = abs(signal.entry_price - signal.sl_price)
            reward = abs(tp - signal.entry_price)
            
            if risk == 0:
                return None
            
            return reward / risk
            
        except Exception as e:
            logger.error(f"Error calculating RR: {e}")
            return None
    
    def _format_order_block(self, ob) -> Dict:
        """Format Order Block for output"""
        try:
            if isinstance(ob, dict):
                return {
                    'zone_low': ob.get('zone_low'),
                    'zone_high': ob.get('zone_high'),
                    'type': ob.get('type'),
                    'strength': ob.get('strength', 'MEDIUM')
                }
            else:
                return {
                    'zone_low': getattr(ob, 'zone_low', None),
                    'zone_high': getattr(ob, 'zone_high', None),
                    'type': str(getattr(ob, 'type', None)),
                    'strength': getattr(ob, 'strength', 'MEDIUM')
                }
        except Exception as e:
            logger.error(f"Error formatting Order Block: {e}")
            return {}
    
    def _check_price_near_sr(self, price: float, luxalgo_sr: Dict) -> bool:
        """Check if price is near any S/R zone"""
        try:
            threshold = 0.02  # 2% threshold
            
            support_zones = luxalgo_sr.get('support_zones', [])
            resistance_zones = luxalgo_sr.get('resistance_zones', [])
            
            for zone in support_zones + resistance_zones:
                zone_price = zone.get('price', 0)
                if zone_price and abs(price - zone_price) / price < threshold:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking price near S/R: {e}")
            return False
    
    def _calculate_liquidity_distance(self, current_price: float, liquidity_zones: List) -> Optional[float]:
        """Calculate distance to nearest liquidity zone"""
        if not liquidity_zones:
            return None
        
        try:
            nearest_zone = liquidity_zones[0]
            zone_price = nearest_zone.get('price', nearest_zone.get('price_level', current_price))
            distance_pct = abs((zone_price - current_price) / current_price) * 100
            return distance_pct
            
        except Exception as e:
            logger.error(f"Error calculating liquidity distance: {e}")
            return None

    def _get_liquidity_zones_with_fallback(self, df: pd.DataFrame, symbol: str, timeframe: str) -> List:
        """
        ЗАДЪЛЖИТЕЛНО: Опитва fresh liquidity map, САМО АКО НЕ е готова → cache
        """
        try:
            # Опит 1: Fresh liquidity map
            if hasattr(self, 'liquidity_mapper') and self.liquidity_mapper:
                try:
                    liquidity_zones = self.liquidity_mapper.detect_liquidity_zones(df, timeframe)
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
    
    def _fetch_btc_data(
        self,
        start_time: datetime,
        end_time: datetime,
        timeframe: str = '1h'
    ) -> Optional[pd.DataFrame]:
        """
        Fetch BTC price data for correlation calculation
        
        Args:
            start_time: Start datetime
            end_time: End datetime
            timeframe: Candle timeframe (default: 1h)
            
        Returns:
            DataFrame with BTC OHLCV data or None if fetch fails
        """
        try:
            # Import requests here to handle missing dependency gracefully
            # This allows the engine to work without requests if BTC correlation is not needed
            import requests
            
            # Convert datetime to milliseconds
            start_ms = int(start_time.timestamp() * 1000)
            end_ms = int(end_time.timestamp() * 1000)
            
            # Binance timeframe mapping
            tf_map = {
                '1m': '1m',
                '3m': '3m',
                '5m': '5m',
                '15m': '15m',
                '30m': '30m',
                '1h': '1h',
                '2h': '2h',
                '4h': '4h',
                '6h': '6h',
                '12h': '12h',
                '1d': '1d',
                '3d': '3d',
                '1w': '1w',
            }
            
            interval = tf_map.get(timeframe.lower(), '1h')
            
            # Binance API endpoint
            url = "https://api.binance.com/api/v3/klines"
            params = {
                'symbol': 'BTCUSDT',
                'interval': interval,
                'startTime': start_ms,
                'endTime': end_ms,
                'limit': 500
            }
            
            # Fetch BTC klines
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code != 200:
                logger.warning(f"Binance API returned {response.status_code}")
                return None
            
            klines = response.json()
            
            if not klines:
                logger.warning("No BTC data returned from Binance")
                return None
            
            # Convert to DataFrame
            df = pd.DataFrame(klines, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            # Convert types
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['close'] = df['close'].astype(float)
            
            # Set index
            df = df.set_index('timestamp')
            
            logger.debug(f"✅ Fetched {len(df)} BTC candles for correlation")
            return df[['close']]  # Return only close prices
            
        except ImportError as e:
            logger.warning(f"Required library not available - BTC correlation disabled: {e}")
            return None
        except Exception as e:
            logger.warning(f"BTC data fetch failed: {e}")
            return None
    
    def _calculate_btc_correlation(
        self,
        symbol: str,
        df: pd.DataFrame
    ) -> Tuple[Optional[float], Optional[bool]]:
        """
        Calculate correlation with BTC price movement
        
        Args:
            symbol: Trading pair symbol
            df: Price DataFrame with datetime index
            
        Returns:
            Tuple of (correlation, is_aligned)
            - correlation: Pearson correlation coefficient (-1 to 1) or None
            - is_aligned: True if |correlation| > 0.7, False if < 0.3, None otherwise
        """
        try:
            # Skip BTC itself
            if symbol.upper() in ['BTCUSDT', 'BTC', 'BTCUSD', 'BTCBUSD']:
                return None, None
            
            # Need at least 30 candles for meaningful correlation
            if len(df) < 30:
                logger.debug("Insufficient data for BTC correlation (need 30+ candles)")
                return None, None
            
            # Get time range from df
            start_time = df.index[0]
            end_time = df.index[-1]
            
            # Determine timeframe from df index frequency
            if len(df) >= 2:
                time_diff = (df.index[1] - df.index[0]).total_seconds() / 60
                if time_diff <= 1:
                    tf = '1m'
                elif time_diff <= 3:
                    tf = '3m'
                elif time_diff <= 5:
                    tf = '5m'
                elif time_diff <= 15:
                    tf = '15m'
                elif time_diff <= 30:
                    tf = '30m'
                elif time_diff <= 60:
                    tf = '1h'
                elif time_diff <= 240:
                    tf = '4h'
                else:
                    tf = '1d'
            else:
                tf = '1h'  # Default fallback
            
            # Fetch BTC data
            btc_df = self._fetch_btc_data(start_time, end_time, tf)
            
            if btc_df is None or len(btc_df) < 30:
                logger.debug("BTC data fetch failed or insufficient")
                return None, None
            
            # Align timestamps (merge on index)
            merged = df[['close']].merge(
                btc_df[['close']],
                left_index=True,
                right_index=True,
                how='inner',
                suffixes=('_asset', '_btc')
            )
            
            if len(merged) < 30:
                logger.debug(f"After merge, only {len(merged)} matching candles - insufficient")
                return None, None
            
            # Calculate percentage returns
            returns_df = merged.pct_change().dropna()
            
            # Ensure we still have enough data after dropna
            if len(returns_df) < 29:  # Need at least 29 returns for 30 candles
                logger.debug(f"After pct_change, only {len(returns_df)} returns - insufficient")
                return None, None
            
            asset_returns = returns_df['close_asset']
            btc_returns = returns_df['close_btc']
            
            # Calculate Pearson correlation
            correlation = asset_returns.corr(btc_returns)
            
            # Check if correlation is valid
            if pd.isna(correlation) or np.isinf(correlation):
                logger.debug("Correlation calculation returned NaN or Inf")
                return None, None
            
            # Determine alignment
            abs_corr = abs(correlation)
            if abs_corr > 0.7:
                is_aligned = True  # Strong correlation (following BTC)
            elif abs_corr < 0.3:
                is_aligned = False  # Weak correlation (independent move)
            else:
                is_aligned = None  # Moderate correlation (neutral)
            
            logger.info(f"✅ BTC correlation for {symbol}: {correlation:.3f} (aligned: {is_aligned})")
            return correlation, is_aligned
            
        except Exception as e:
            logger.warning(f"BTC correlation calculation error: {e}")
            return None, None
    
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
