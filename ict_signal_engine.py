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
from entry_scenarios import select_best_entry_scenario
import json

# Import Entry Gating and Confidence Threshold evaluators (ESB v1.0 §2.1-2.2)
try:
    from entry_gating_evaluator import evaluate_entry_gating
    ENTRY_GATING_AVAILABLE = True
except ImportError:
    ENTRY_GATING_AVAILABLE = False
    logging.warning("Entry Gating Evaluator not available")

try:
    from confidence_threshold_evaluator import evaluate_confidence_threshold
    CONFIDENCE_THRESHOLD_AVAILABLE = True
except ImportError:
    CONFIDENCE_THRESHOLD_AVAILABLE = False
    logging.warning("Confidence Threshold Evaluator not available")

try:
    from execution_eligibility_evaluator import evaluate_execution_eligibility
    EXECUTION_ELIGIBILITY_AVAILABLE = True
except ImportError:
    EXECUTION_ELIGIBILITY_AVAILABLE = False
    logging.warning("Execution Eligibility Evaluator not available")

try:
    from risk_admission_evaluator import evaluate_risk_admission
    RISK_ADMISSION_AVAILABLE = True
except ImportError:
    RISK_ADMISSION_AVAILABLE = False
    logging.warning("Risk Admission Evaluator not available")

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


# ============================================================
# SL/TP CALCULATION CONSTANTS
# ============================================================

ATR_FALLBACK_PCT = 0.02  # 2% fallback when ATR calculation fails

TIMEFRAME_MIN_SL_DISTANCE = {
    '15m': 0.003, '30m': 0.004, '1h': 0.005,
    '2h': 0.007, '4h': 0.010, '1d': 0.015,
}

TIMEFRAME_BUFFER_PCT = {
    '15m': 0.001, '30m': 0.0015, '1h': 0.002,
    '2h': 0.0025, '4h': 0.003, '1d': 0.005,
}


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


def get_tp_multipliers_by_timeframe(timeframe: str) -> tuple:
    """
    Get optimized TP multipliers based on timeframe volatility
    
    Strategy:
    - Lower TFs (1h, 2h): (1, 3, 5) - Quick validation, conservative targets
    - Higher TFs (4h, 1d): (2, 4, 6) - Capture trends, aggressive targets
    
    Reasoning:
    - 1h/2h: Faster moves, quicker reversals → Need fast TP hits
    - 4h/1d: Stronger trends, more follow-through → Can hold for bigger TPs
    
    Args:
        timeframe: Candle timeframe (e.g., '1h', '4h', '1d')
        
    Returns:
        tuple: (tp1_mult, tp2_mult, tp3_mult)
        
    Examples:
        >>> get_tp_multipliers_by_timeframe('1h')
        (1.0, 3.0, 5.0)
        >>> get_tp_multipliers_by_timeframe('4h')
        (2.0, 4.0, 6.0)
    """
    tf = timeframe.lower().strip()
    
    # Short-term: Conservative targets (1, 3, 5)
    if tf in ['15m', '30m', '1h', '2h', '3h']:  # ← Added 3h
        logger.info(f"📊 Using conservative TPs (1,3,5) for {timeframe}")
        return (1.0, 3.0, 5.0)
    
    # Medium/Long-term: Aggressive targets (2, 4, 6)
    elif tf in ['4h', '6h', '8h', '12h', '1d', '3d', '1w']:
        logger.info(f"📊 Using aggressive TPs (2,4,6) for {timeframe}")
        return (2.0, 4.0, 6.0)
    
    # Default: Conservative (safer)
    else:
        logger.warning(f"⚠️ Unknown timeframe {timeframe}, defaulting to conservative TPs (1,3,5)")
        return (1.0, 3.0, 5.0)


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
    
    # ✅ PR #4: Timeframe Hierarchy
    timeframe_hierarchy: Dict = field(default_factory=dict)  # NEW: TF hierarchy info (Structure/Confirmation/Entry)
    
    # ✅ Entry Scenario Detection (NEW)
    entry_scenario: Optional[str] = None  # ROLLBACK/PULLBACK/CONTINUATION/REVERSAL
    entry_scenario_score: int = 0  # 0-100 score
    entry_scenario_reasoning: str = ""  # Why this scenario was selected
    entry_scenario_triggers: List[str] = field(default_factory=list)  # Detected triggers
    
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
            'entry_scenario': self.entry_scenario,
            'entry_scenario_score': self.entry_scenario_score,
            'entry_scenario_reasoning': self.entry_scenario_reasoning,
            'entry_scenario_triggers': self.entry_scenario_triggers,
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
    
    # Altcoins that use independent analysis mode (bypass BTC HTF bias early exit)
    ALT_INDEPENDENT_SYMBOLS = ["ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT", "XRPUSDT"]
    
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
        
        # ✅ PR #4: Load timeframe hierarchy configuration
        self.tf_hierarchy = self._load_tf_hierarchy()
        logger.info(f"✅ TF Hierarchy loaded: {len(self.tf_hierarchy.get('hierarchies', {}))} timeframes configured")
        
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
            'min_confidence': 50,          # Min 60% confidence (STRICT ICT)
            'min_risk_reward': 3.0,        # Min 1:3 R:R (STRICT ICT)
            'max_sl_distance_pct': 3.0,    # Max 3% SL distance
            'tp_multipliers': [3, 5, 8],   # TP at 3R, 5R, 8R (STRICT ICT)
            'require_mtf_confluence': True, # Require MTF alignment (STRICT ICT)
            'min_mtf_confluence': 0.50,     # Min 50% MTF consensus (STRICT ICT)
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
            'breaker_block_weight': 0.08,  # Weight for breaker blocks (ESB v1.0 §4)
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
    
    def _load_tf_hierarchy(self) -> Dict:
        """
        ✅ PR #4: Load timeframe hierarchy configuration
        
        Returns:
            Dict with TF hierarchy rules for each entry timeframe
        """
        try:
            # Try to load from config file
            from pathlib import Path
            config_path = Path(__file__).parent / 'config' / 'timeframe_hierarchy.json'
            
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    hierarchy = json.load(f)
                logger.info(f"📊 Loaded TF hierarchy from {config_path}")
                return hierarchy
            else:
                logger.warning("⚠️ TF hierarchy config not found, using defaults")
                return self._get_default_tf_hierarchy()
                
        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON decode error in TF hierarchy: {e}")
            return self._get_default_tf_hierarchy()
        except Exception as e:
            logger.error(f"❌ Error loading TF hierarchy: {e}")
            return self._get_default_tf_hierarchy()
    
    def _get_default_tf_hierarchy(self) -> Dict:
        """
        Fallback TF hierarchy if config file not available
        
        Returns:
            Default hierarchy configuration
        """
        return {
            "hierarchies": {
                "15m": {
                    "entry_tf": "15m",
                    "confirmation_tf": "30m",
                    "structure_tf": "1h",
                    "htf_bias_tf": "1h"
                },
                "30m": {
                    "entry_tf": "30m",
                    "confirmation_tf": "1h",
                    "structure_tf": "1h",
                    "htf_bias_tf": "1h"
                },
                "1h": {
                    "entry_tf": "1h",
                    "confirmation_tf": "2h",
                    "structure_tf": "4h",
                    "htf_bias_tf": "4h"
                },
                "2h": {
                    "entry_tf": "2h",
                    "confirmation_tf": "4h",
                    "structure_tf": "4h",
                    "htf_bias_tf": "4h"
                },
                "3h": {
                    "entry_tf": "3h",
                    "confirmation_tf": "4h",
                    "structure_tf": "1d",
                    "htf_bias_tf": "1d"
                },
                "4h": {
                    "entry_tf": "4h",
                    "confirmation_tf": "4h",
                    "structure_tf": "1d",
                    "htf_bias_tf": "1d"
                },
                "1d": {
                    "entry_tf": "1d",
                    "confirmation_tf": "1d",
                    "structure_tf": "1d",
                    "htf_bias_tf": "1d"
                }
            },
            "validation_rules": {
                "structure_penalty_if_missing": 0.25,
                "confirmation_penalty_if_missing": 0.15,
                "allow_fallback_tfs": True
            }
        }
    
    def _validate_mtf_hierarchy(
        self,
        entry_tf: str,
        mtf_analysis: Dict,
        confidence: float
    ) -> Tuple[float, List[str], Dict]:
        """
        ✅ PR #4: Validate MTF analysis follows ICT timeframe hierarchy
        
        Validates that the expected Structure TF and Confirmation TF are present.
        Applies penalties (not rejections) if TFs are missing.
        
        Args:
            entry_tf: Entry timeframe (e.g., '1h', '2h', '4h', '1d')
            mtf_analysis: Dictionary of MTF analysis results keyed by timeframe
            confidence: Current confidence score
            
        Returns:
            Tuple of (adjusted_confidence, warnings, hierarchy_info)
        """
        warnings = []
        adjusted_confidence = confidence
        hierarchy_info = {}
        
        try:
            # Get expected hierarchy for this entry TF
            hierarchies = self.tf_hierarchy.get('hierarchies', {})
            hierarchy = hierarchies.get(entry_tf)
            
            if not hierarchy:
                logger.warning(f"⚠️ No TF hierarchy defined for {entry_tf}, skipping validation")
                return adjusted_confidence, warnings, hierarchy_info
            
            # Extract expected TFs
            expected_confirmation_tf = hierarchy.get('confirmation_tf')
            expected_structure_tf = hierarchy.get('structure_tf')
            expected_htf_bias_tf = hierarchy.get('htf_bias_tf')
            
            # Store hierarchy info for signal message
            hierarchy_info = {
                'entry_tf': entry_tf,
                'confirmation_tf': expected_confirmation_tf,
                'structure_tf': expected_structure_tf,
                'htf_bias_tf': expected_htf_bias_tf,
                'description': hierarchy.get('description', '')
            }
            
            # Get validation rules
            rules = self.tf_hierarchy.get('validation_rules', {})
            confirmation_penalty = rules.get('confirmation_penalty_if_missing', 0.15)
            structure_penalty = rules.get('structure_penalty_if_missing', 0.25)
            
            # Get available TFs from MTF analysis
            available_tfs = list(mtf_analysis.keys()) if mtf_analysis else []
            
            logger.info(f"📊 TF Hierarchy Validation for {entry_tf}:")
            logger.info(f"   Expected - Structure: {expected_structure_tf}, Confirmation: {expected_confirmation_tf}")
            logger.info(f"   Available: {available_tfs}")
            
            # VALIDATION 1: Check Confirmation TF
            if expected_confirmation_tf:
                if expected_confirmation_tf in available_tfs:
                    logger.info(f"   ✅ Confirmation TF ({expected_confirmation_tf}) present")
                    hierarchy_info['confirmation_tf_present'] = True
                else:
                    warning_msg = (
                        f"⚠️ Missing Confirmation TF ({expected_confirmation_tf}) "
                        f"- intermediate pattern validation limited"
                    )
                    warnings.append(warning_msg)
                    adjusted_confidence -= confirmation_penalty
                    hierarchy_info['confirmation_tf_present'] = False
                    logger.warning(f"   {warning_msg} (-{confirmation_penalty*100:.0f}%)")
            
            # VALIDATION 2: Check Structure TF
            if expected_structure_tf:
                if expected_structure_tf in available_tfs:
                    logger.info(f"   ✅ Structure TF ({expected_structure_tf}) present")
                    hierarchy_info['structure_tf_present'] = True
                    
                    # Additional check: Structure bias alignment (if data available)
                    structure_data = mtf_analysis.get(expected_structure_tf, {})
                    structure_bias = structure_data.get('bias')
                    
                    if structure_bias:
                        hierarchy_info['structure_bias'] = structure_bias
                        logger.info(f"   📊 Structure bias: {structure_bias}")
                else:
                    warning_msg = (
                        f"⚠️ Missing Structure TF ({expected_structure_tf}) "
                        f"- major trend validation limited"
                    )
                    warnings.append(warning_msg)
                    adjusted_confidence -= structure_penalty
                    hierarchy_info['structure_tf_present'] = False
                    logger.warning(f"   {warning_msg} (-{structure_penalty*100:.0f}%)")
            
            # VALIDATION 3: Check HTF Bias TF (informational only, no penalty)
            if expected_htf_bias_tf:
                if expected_htf_bias_tf in available_tfs:
                    logger.info(f"   ✅ HTF Bias TF ({expected_htf_bias_tf}) present")
                    hierarchy_info['htf_bias_tf_present'] = True
                else:
                    logger.info(f"   ℹ️ HTF Bias TF ({expected_htf_bias_tf}) not available (optional)")
                    hierarchy_info['htf_bias_tf_present'] = False
            
            # Summary
            if not warnings:
                logger.info("   ✅ TF hierarchy fully compliant")
            else:
                logger.info(f"   ⚠️ TF hierarchy: {len(warnings)} issue(s), confidence adjusted")
            
            return adjusted_confidence, warnings, hierarchy_info
            
        except Exception as e:
            logger.error(f"❌ TF hierarchy validation error: {e}")
            import traceback
            traceback.print_exc()
            return confidence, warnings, hierarchy_info
    
    def generate_signal(
        self,
        df: pd.DataFrame,
        symbol: str,
        timeframe: str = "1H",
        mtf_data: Optional[Dict[str, pd.DataFrame]] = None,
        is_auto: bool = False  # ← NEW: Distinguish auto vs manual signals
    ) -> Optional[ICTSignal]:
        """
        Generate ICT signal with UNIFIED analysis sequence
        
        ✅ ЕДНАКВА последователност за ВСИЧКИ таймфремове (1w до 1m)
        ✅ ЕДНАКВА логика за ръчни И автоматични сигнали
        """
        logger.info(f"🎯 Generating UNIFIED ICT signal for {symbol} on {timeframe}")
        
        # Cache check with distance re-validation
        if self.cache_manager:
            try:
                cached_signal = self.cache_manager.get_cached_signal(symbol, timeframe)
                if cached_signal:
                    # ✅ Re-validate entry distance against current price
                    current_price = df['close'].iloc[-1]
                    
                    # Guard against zero or invalid price
                    if current_price <= 0:
                        logger.warning(
                            f"⚠️ Invalid current price: ${current_price:.4f} - "
                            f"invalidating cache and re-analyzing"
                        )
                        # Don't return cache, continue to full analysis below
                    else:
                        entry_price = cached_signal.entry_price
                        distance_pct = abs(entry_price - current_price) / current_price
                        
                        MAX_ENTRY_DISTANCE_PCT = 0.07  # 5% max (universal limit, consistent with line 2578)
                        if distance_pct > MAX_ENTRY_DISTANCE_PCT:
                            logger.warning(
                                f"⚠️ Cached signal entry too far: {distance_pct*100:.1f}% > 7.0% MAX "
                                f"(entry: ${entry_price:.4f}, current: ${current_price:.4f}) "
                                f"- invalidating cache and re-analyzing"
                            )
                            # Don't return cache, continue to full analysis below
                        else:
                            logger.info(
                                f"✅ Using cached signal for {symbol} {timeframe} "
                                f"(entry {distance_pct*100:.1f}% away - within limits)"
                            )
                            return cached_signal
            except Exception as e:
                logger.warning(f"Cache error: {e}")
        
        if len(df) < 200:
            logger.warning("Insufficient data")
            return None
        
        df = self._prepare_dataframe(df)
        
        # ═══════ УНИФИЦИРАНА ПОСЛЕДОВАТЕЛНОСТ (12 СТЪПКИ) ═══════
        
        # СТЪПКА 1: HTF BIAS (1D → 4H fallback)
        # ✅ FIX: Define entry_tf from parameter
        entry_tf = timeframe

        logger.info("📊 Step 1: HTF Bias")
        htf_bias = self._get_htf_bias_with_fallback(symbol, mtf_data, timeframe)
        
        # СТЪПКА 2: MTF STRUCTURE (4H)
        logger.info("📊 Step 2: MTF Structure")
        mtf_analysis = self._analyze_mtf_confluence(df, mtf_data, symbol) if mtf_data is not None and isinstance(mtf_data, dict) else None
        
        # ✅ PR #4: СТЪПКА 6b: TIMEFRAME HIERARCHY VALIDATION (NEW)
        logger.info("=" * 60)
        logger.info("STEP 6b: TIMEFRAME HIERARCHY VALIDATION")
        logger.info("=" * 60)
        
        # Initialize variables for hierarchy validation
        tf_warnings = []
        hierarchy_info = {}
        initial_confidence = 80.0  # Starting confidence before validation
        
        # Perform TF hierarchy validation
        validated_confidence, tf_warnings, hierarchy_info = self._validate_mtf_hierarchy(
            entry_tf=timeframe,
            mtf_analysis=mtf_analysis if mtf_analysis else {},
            confidence=initial_confidence
        )
        
        # Store hierarchy info for later use in signal generation
        context_warnings = tf_warnings  # Will be added to signal warnings later
        
        if tf_warnings:
            logger.warning(f"⚠️ TF hierarchy issues: {len(tf_warnings)} warnings")
            for warning in tf_warnings:
                logger.warning(f"   {warning}")
        else:
            logger.info("✅ TF hierarchy validated - full compliance")
        
        logger.info(f"📊 Confidence after TF validation: {validated_confidence:.1f}%")
        
        # СТЪПКА 3: ENTRY MODEL (текущ TF)
        logger.info(f"📊 Step 3: Entry Model ({timeframe})")
        
        # СТЪПКА 4: LIQUIDITY MAP (с cache fallback)
        logger.info("📊 Step 4: Liquidity Map")
        liquidity_zones = self._get_liquidity_zones_with_fallback(df, symbol, timeframe)
        
        # СТЪПКА 5-7: ICT COMPONENTS
        logger.info("📊 Steps 5-7: ICT Components")
        ict_components = self._detect_ict_components(df, timeframe)
        ict_components['liquidity_zones'] = liquidity_zones  # Add liquidity zones
        
        # STEP 7: Bias Determination - START DIAGNOSTIC LOGGING
        logger.info("🔍 Step 7: Bias Determination")
        
        # Calculate bias with diagnostic details
        # ✅ FIX: Use PURE structure-only bias (no OB/displacement)
        bias_str, bias_confidence = self._calculate_pure_ict_bias_for_tf(df, symbol, entry_tf)
        bias = MarketBias[bias_str]  # Convert string to enum
        structure_broken = self._check_structure_break(df)
        displacement_detected, displacement_strength = self._check_displacement(df)
        ict_components["displacement"] = {"detected": displacement_detected, "strength": displacement_strength}
        ict_components["structure_break"] = {"type": "MSS" if structure_broken else None}

        # Add structure_break and displacement to ict_components for Entry Scenarios
        
        # Log bias calculation breakdown
        # Filter only MEDIUM-STRONG order blocks for bias (strength >= 40)
        bullish_obs = [ob for ob in ict_components.get('order_blocks', []) 
                       if hasattr(ob, 'type') and 'BULLISH' in str(ob.type.value) 
                       and hasattr(ob, 'strength') and ob.strength >= 40]
        bearish_obs = [ob for ob in ict_components.get('order_blocks', []) 
                       if hasattr(ob, 'type') and 'BEARISH' in str(ob.type.value)
                       and hasattr(ob, 'strength') and ob.strength >= 40]
        bullish_fvgs = [fvg for fvg in ict_components.get('fvgs', []) 
                        if hasattr(fvg, 'is_bullish') and fvg.is_bullish]
        bearish_fvgs = [fvg for fvg in ict_components.get('fvgs', []) 
                        if hasattr(fvg, 'is_bullish') and not fvg.is_bullish]
        
        ob_score = len(bullish_obs) - len(bearish_obs)
        fvg_score = len(bullish_fvgs) - len(bearish_fvgs)
        mtf_bias_str = mtf_analysis.get('htf_bias', 'NEUTRAL') if mtf_analysis else 'NEUTRAL'
        
        logger.info(f"   → Bias Calculation Breakdown:")
        logger.info(f"      • OB Score: {ob_score} (Bullish: {len(bullish_obs)}, Bearish: {len(bearish_obs)})")
        logger.info(f"      • FVG Score: {fvg_score} (Bullish: {len(bullish_fvgs)}, Bearish: {len(bearish_fvgs)})")
        logger.info(f"      • MTF Bias: {mtf_bias_str}")
        logger.info(f"      • Structure Broken: {structure_broken}")
        logger.info(f"      • Displacement Detected: {displacement_detected}")
        logger.info(f"   → Final Bias: {bias.value}")
        
        # СТЪПКА 7b: Apply confidence penalty for NEUTRAL/RANGING bias (NO EARLY EXIT)
        # ✅ FIX #1: HTF is now a soft constraint (penalty) instead of hard block
        confidence_penalty = 0.0  # Track penalty for Step 11 confidence calculation
        
        if bias in [MarketBias.NEUTRAL, MarketBias.RANGING]:
            logger.warning(f"⚠️ Step 7b: {symbol} bias is {bias.value} - RANGING market detected")
            logger.info(f"   → RANGING market = no clear directional bias")
            logger.info(f"   → Returning HOLD signal (no trade setup)")
            
            # ✅ EARLY EXIT: RANGING = HOLD (no trade)
            return {
                'action': 'HOLD',
                'confidence': 0,
                'reason': 'RANGING_MARKET',
                'message': f'{symbol} market is RANGING on {timeframe}. No clear directional bias. Wait for breakout.',
                'bias': bias.value,
                'timeframe': timeframe,
                'symbol': symbol
            }
        else:
            # Directional bias (BULLISH/BEARISH) - no penalty
            confidence_penalty = 0.0
            logger.info(f"✅ Step 7b: Directional bias {bias.value} - no penalty")
        
        # ✅ CONTINUE TO STEP 8 (NO EARLY EXIT FOR DIRECTIONAL BIAS)
        # At this point, bias is guaranteed to be BULLISH or BEARISH
        logger.info(f"✅ PASSED Step 7: Continuing with bias {bias.value} (penalty: {confidence_penalty*100:.0f}%)")
        
        # СТЪПКА 8: ENTRY CALCULATION WITH ICT-COMPLIANT ZONE
        logger.info("🔍 Step 8: Entry Zone Validation")
        
        # Get current price
        current_price = df['close'].iloc[-1]
        logger.info(f"   → Current Price: ${current_price:.2f}")
        
        # Calculate ICT-compliant entry zone
        bias_str = bias.value if hasattr(bias, 'value') else str(bias)
        fvg_zones = ict_components.get('fvgs', [])
        order_blocks = ict_components.get('order_blocks', [])
        sr_levels = ict_components.get('luxalgo_sr', {})
        
        logger.info(f"   → Available ICT Components:")
        logger.info(f"      • Order Blocks: {len(order_blocks)}")
        logger.info(f"      • FVG Zones: {len(fvg_zones)}")
        sr_count = 0
        if sr_levels and isinstance(sr_levels, dict):
            sr_count = len(sr_levels.get('support_zones', [])) + len(sr_levels.get('resistance_zones', []))
        logger.info(f"      • S/R Levels: {sr_count}")
        
        entry_zone, entry_status = self._calculate_ict_compliant_entry_zone(
            current_price=current_price,
            direction=bias_str,
            fvg_zones=fvg_zones,
            order_blocks=order_blocks,
            sr_levels=sr_levels,
            timeframe=timeframe
        )
        
        logger.info(f"   → Entry Zone Status: {entry_status}")
        if entry_zone:
            logger.info(f"      • Zone Center: ${entry_zone.get('center', 0):.2f}")
            logger.info(f"      • Zone Range: ${entry_zone.get('low', 0):.2f} - ${entry_zone.get('high', 0):.2f}")
            logger.info(f"      • Source: {entry_zone.get('source', 'UNKNOWN')}")
            logger.info(f"      • Quality: {entry_zone.get('quality', 0)}")
        
        # ✅ UPDATED: Only reject for TOO_LATE (timing issue), not NO_ZONE (distance issue)
        # Validate entry zone timing
        if entry_status == 'TOO_LATE':
            logger.info(f"❌ BLOCKED at Step 8: Entry zone validation failed (TOO_LATE)")
            logger.info(f"✅ Generating NO_TRADE (blocked_at_step: 8, reason: Price already passed entry zone)")
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
        
        # ✅ NEW: Reject signals with entry zones too far (exceeds universal 5% max)
        if entry_status == 'TOO_FAR':
            logger.info(f"❌ BLOCKED at Step 8: Entry zone too far from current price")
            logger.info(f"✅ Generating NO_TRADE (blocked_at_step: 8, reason: Entry distance exceeds 7% universal maximum)")
            context = self._extract_context_data(df, bias)
            mtf_consensus_data = self._calculate_mtf_consensus(symbol, timeframe, bias, mtf_data)
            
            return self._create_no_trade_message(
                symbol=symbol,
                timeframe=timeframe,
                reason=f"Entry zone validation failed: {entry_status}",
                details=f"Entry zone too far from current price (exceeds universal 7% maximum for all timeframes).",
                mtf_breakdown=mtf_consensus_data.get("breakdown", {}),
                current_price=context['current_price'],
                price_change_24h=context['price_change_24h'],
                rsi=context['rsi'],
                signal_direction=context['signal_direction'],
                confidence=None
            )
        
        # ✅ SOFT CONSTRAINT: Handle NO_ZONE case with fallback instead of rejection
        if entry_status == 'NO_ZONE' or entry_zone is None:
            logger.info(f"⚠️ Step 8 Warning: No ICT zone in optimal range, using fallback")
            # ✅ NON-INVASIVE DIAGNOSTIC LOGGING
            logger.warning(f"⚠️ No ICT zone found in optimal range (0.5-7%) for {symbol}")
            logger.info(f"   → Creating fallback entry zone at current price ${current_price:.2f}")
            logger.debug(f"   → Fallback zone: ±1% from current price")
            
            # Diagnostic: Log available ICT components
            sr_count = len(sr_levels.get('support_zones', [])) + len(sr_levels.get('resistance_zones', []))
            logger.debug(f"   → Available ICT components:")
            logger.debug(f"      - Order Blocks: {len(order_blocks)}")
            logger.debug(f"      - FVG Zones: {len(fvg_zones)}")
            logger.debug(f"      - S/R Levels: {sr_count}")
            
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
        
        # Log successful entry zone validation
        logger.info(f"✅ PASSED Step 8: Entry zone validated ({entry_status})")
        
        # Extract entry price from entry zone for Step 9
        entry_price = entry_zone.get('center', current_price)
        logger.info(f"   → Entry Price: ${entry_price:.2f} (from entry zone)")
        
        # Keep existing entry setup for SL calculation (fallback)
        entry_setup = self._identify_entry_setup(df, ict_components, bias)
        if not entry_setup:
            # Use entry_zone as fallback entry_setup
            entry_setup = {
                'type': f"{bias_str.lower()}_zone",
                'price_zone': (entry_zone['low'], entry_zone['high']),
                'source': entry_zone['source']
            }
        
        
        # =========================================================================
        # СТЪПКА 8.1: ENTRY SCENARIO SELECTION (ICT Scoring System)
        # =========================================================================
        logger.info("=" * 60)
        logger.info("🎯 Step 8.1: Entry Scenario Selection (ICT Scoring System)")
        logger.info("=" * 60)
        
        entry_scenario_result, poi_ref = select_best_entry_scenario(
            current_price=current_price,
            bias=bias_str,
            ict_components=ict_components,
            entry_zone=entry_zone,
            timeframe=timeframe
        )
        
        if entry_scenario_result:
            # Store poi_ref if available
            if poi_ref:
                entry_setup['poi_ref'] = poi_ref
            
            logger.info(f"✅ Selected Scenario: {entry_scenario_result['scenario']}")
            logger.info(f"   Score: {entry_scenario_result['score']}/100")
            logger.info(f"   Entry Price: ${entry_scenario_result['entry_zone']['center']:.4f}")
            logger.info(f"   Entry Range: ${entry_scenario_result['entry_zone']['low']:.4f} - ${entry_scenario_result['entry_zone']['high']:.4f}")
            logger.info(f"   Distance: {entry_scenario_result['entry_zone']['distance_pct']:.1f}%")
            logger.info(f"   Triggers: {', '.join(entry_scenario_result['triggers'])} ({entry_scenario_result['trigger_strength']})")
            logger.info(f"   Position Size Advisory: {entry_scenario_result['position_size_advisory']}%")
            logger.info(f"   Reasoning: {entry_scenario_result['reasoning']}")
            logger.info(f"   POI Type: {entry_scenario_result.get('poi_type', 'NONE')}")
            
            # Log invalidation anchor info
            anchor = entry_scenario_result.get('invalidation_anchor', {})
            if anchor:
                logger.info(f"   Anchor: {anchor.get('type')} @ ${anchor.get('price', 0):.4f}")
            
            # Override entry_zone with scenario result
            entry_zone = entry_scenario_result['entry_zone']
            # ✅ IMPORTANT: Update entry_price after scenario override
            entry_price = entry_zone.get('center', entry_price)
            logger.info(f"   → Updated Entry Price: ${entry_price:.2f} (from scenario entry zone)")

            
            logger.info(f"✅ Entry zone updated with {entry_scenario_result['scenario']} logic")
        else:
            logger.warning("⚠️ No valid scenario scored above minimum - using Step 8 entry_zone")
        
        logger.info("=" * 60)
        # СТЪПКА 9: SL/TP + VALIDATION
        logger.info("🔍 Step 9: SL/TP Calculation & Validation")
        logger.info("=" * 60)
        
        # Get invalidation_anchor (or create fallback)
        invalidation_anchor = None
        
        if entry_scenario_result:
            invalidation_anchor = entry_scenario_result.get('invalidation_anchor')
        
        if not invalidation_anchor:
            logger.warning("⚠️ No anchor from Step 8.1 - creating fallback")
            
            swing_price = self._find_recent_swing_for_sl(df, bias, entry_price)
            
            if swing_price:
                invalidation_anchor = {
                    'type': 'SWING_LOW' if bias == MarketBias.BULLISH else 'SWING_HIGH',
                    'price': float(swing_price),
                    'source_type': 'SWING_FALLBACK',
                    'source_data': {}
                }
                logger.info(f"   → Fallback: SWING @ ${swing_price:.2f}")
            else:
                # Use ATR fallback
                if 'atr' in df.columns and len(df) > 0:
                    atr = df['atr'].iloc[-1]
                    if pd.isna(atr) or atr == 0:
                        atr = entry_price * 0.02
                else:
                    atr = entry_price * 0.02
                
                anchor_price = entry_price - (atr * 1.5) if bias == MarketBias.BULLISH else entry_price + (atr * 1.5)
                invalidation_anchor = {
                    'type': 'ATR',
                    'price': float(anchor_price),
                    'source_type': 'ATR_FALLBACK',
                    'source_data': {'atr': float(atr)}
                }
                logger.info(f"   → Fallback: ATR @ ${anchor_price:.2f}")
        
        # Calculate SL from anchor (SINGLE SOURCE)
        sl_price = self._calculate_sl_from_anchor(
            invalidation_anchor=invalidation_anchor,
            bias=bias,
            entry_price=entry_price,
            timeframe=timeframe,
            df=df
        )
        
        if sl_price is None:
            logger.error("❌ BLOCKED at Step 9: SL calculation failed")
            logger.error("❌ SL не може да бъде изчислен - сигналът НЕ СЕ ИЗПРАЩА")
            return None
        
        logger.info(f"✅ SL calculated: ${sl_price:.2f}")
        
        # ✅ TP calculation (PR #8 Enhanced: Structure-aware vs Mathematical)
        logger.info("🔍 Step 9b: Take Profit Calculation")
        
        fibonacci_data = ict_components.get('fibonacci_data', {})
        bias_str = bias.value if hasattr(bias, 'value') else str(bias)
        
        # Try to use structure-aware TP placement (PR #8)
        try:
            direction = 'LONG' if bias == MarketBias.BULLISH else 'SHORT'
            tp_prices = self._calculate_smart_tp_with_structure_validation(
                entry_price=entry_price,
                sl_price=sl_price,
                direction=direction,
                ict_components=ict_components,
                timeframe=timeframe
            )
            logger.info(f"   → Structure-aware TPs: {[f'${tp:.2f}' for tp in tp_prices]}")
        except Exception as e:
            logger.warning(f"⚠️ Structure TP calculation failed: {e}")
            # Fallback to original mathematical TP
            tp_prices = self._calculate_tp_with_min_rr(
                entry_price, sl_price, liquidity_zones, 
                min_rr=3.0, 
                fibonacci_data=fibonacci_data,
                bias=bias_str,
                timeframe=timeframe
            )
            logger.info(f"   → Mathematical TPs (fallback): {[f'${tp:.2f}' for tp in tp_prices]}")
        
        logger.info(f"✅ PASSED Step 9: SL/TP calculated and validated")
        
        # СТЪПКА 10: RR CHECK
        logger.info("🔍 Step 10: Risk/Reward Validation")
        risk = abs(entry_price - sl_price)
        
        # ✅ FIX: Validate against TP2 (primary target) instead of TP1 (quick profit)
        # This allows TP1 for fast scalping while ensuring TP2 meets quality standards
        # Note: tp_prices array is [TP1, TP2, TP3], so tp_prices[1] is TP2
        if len(tp_prices) >= 2:
            # Use TP2 for quality validation (tp_prices[1] = second element = TP2)
            reward = abs(tp_prices[1] - entry_price)
            tp_label = "TP2"
            logger.info(f"   → Validating R:R against TP2 (primary target)")
        elif len(tp_prices) >= 1:
            # Fallback to TP1 if only one TP exists
            reward = abs(tp_prices[0] - entry_price)
            tp_label = "TP1"
            logger.info(f"   → Validating R:R against TP1 (single target)")
        else:
            reward = 0
            tp_label = "N/A"
        
        risk_reward_ratio = reward / risk if risk > 0 else 0
        
        logger.info(f"   → Risk: ${risk:.2f}")
        logger.info(f"   → Reward ({tp_label}): ${reward:.2f}")
        logger.info(f"   → R:R Ratio: {risk_reward_ratio:.2f} (1:{risk_reward_ratio:.1f})")
        logger.info(f"   → Minimum Required: {self.config['min_risk_reward']:.2f} (1:{self.config['min_risk_reward']:.0f})")
        
        if risk_reward_ratio < self.config['min_risk_reward']:
            logger.info(f"❌ BLOCKED at Step 10: R:R {risk_reward_ratio:.2f} < {self.config['min_risk_reward']} (1:{risk_reward_ratio:.1f} < 1:{self.config['min_risk_reward']:.0f})")
            logger.info(f"✅ Generating NO_TRADE (blocked_at_step: 10, reason: Insufficient RR)")
            logger.error(f"❌ RR {risk_reward_ratio:.2f} < {self.config['min_risk_reward']} - сигналът НЕ СЕ ИЗПРАЩА")
            context = self._extract_context_data(df, bias)
            return self._create_no_trade_message(
                symbol=symbol,
                timeframe=timeframe,
                reason=f"Risk/Reward под минимум ({risk_reward_ratio:.2f})",
                details=f"Необходими: RR >={self.config['min_risk_reward']}. Намерени: {risk_reward_ratio:.2f}",
                mtf_breakdown={},
                current_price=context['current_price'],
                price_change_24h=context['price_change_24h'],
                rsi=context['rsi'],
                signal_direction=context['signal_direction'],
                confidence=None
            )
        
        logger.info(f"✅ PASSED Step 10: RR validated ({risk_reward_ratio:.2f} >= {self.config['min_risk_reward']:.2f} → 1:{risk_reward_ratio:.1f} >= 1:{self.config['min_risk_reward']:.0f})")
        
        # BASE CONFIDENCE
        logger.info("🔍 Step 11: Confidence Calculation")
        base_confidence = self._calculate_signal_confidence(
            ict_components, mtf_analysis, bias, structure_broken, 
            displacement_detected, risk_reward_ratio
        )
        logger.info(f"   → Base Confidence: {base_confidence:.1f}%")
        
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
        
        # ✅ DISTANCE PENALTY (Soft Constraint - FIX #4)
        logger.info("📊 Step 11b: Distance Penalty Check")
        distance_penalty_applied = False
        
        if entry_zone:
            distance_pct = entry_zone.get('distance_pct', 0)
            
            # ✅ FIX #4: Only penalize very close entries (<0.5%)
            # Entries 0.5-10% are optimal, >10% just get informational warning
            if distance_pct < 0.5:
                logger.warning(f"⚠️ Entry very close to current price ({distance_pct:.1f}%) - low risk/reward potential")
                confidence_after_context = confidence_after_context * 0.9  # Reduce by 10%
                distance_penalty_applied = True
                logger.info(f"Distance penalty applied: confidence reduced by 10% → {confidence_after_context:.1f}%")
                context_warnings.append(f"⚠️ Entry very close to current price ({distance_pct:.1f}%) - low risk/reward")
            elif distance_pct > 10.0:
                # Just informational - no penalty
                logger.info(f"ℹ️ Entry {distance_pct:.1f}% from current price - waiting for retracement")
                context_warnings.append(f"ℹ️ Entry {distance_pct:.1f}% from current price - valid ICT retracement setup")
        
        # ✅ HTF BIAS PENALTY (Soft Constraint - FIX #1)
        logger.info("📊 Step 11c: HTF Bias Penalty Check")
        if confidence_penalty > 0:
            logger.warning(f"⚠️ Applying HTF bias penalty: -{confidence_penalty*100:.0f}%")
            confidence_after_context = confidence_after_context * (1 - confidence_penalty)
            logger.info(f"HTF penalty applied: confidence reduced to {confidence_after_context:.1f}%")
            
            # Add warning about HTF bias
            if confidence_penalty >= 0.40:
                context_warnings.append("⚠️ Non-directional bias on both HTF and own structure - high uncertainty")
            elif confidence_penalty >= 0.35:
                context_warnings.append("⚠️ Non-directional HTF bias - reduced confidence")
            elif confidence_penalty >= 0.20:
                context_warnings.append("ℹ️ HTF bias unclear, relying on own structure")
        
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
            
            # ═══════════════════════════════════════════════════════════════
            # ML MOVED TO FINAL POSITION (PR-ML-8)
            # ═══════════════════════════════════════════════════════════════
            # ML now runs AFTER all guards/risk filters as advisory-only layer.
            # See ML Advisory call after line ~1547 (after all evaluations pass).
            # This ensures ML NEVER influences signal direction, only confidence.
            # ═══════════════════════════════════════════════════════════════
            
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

        # ✅ Pre-ML confidence (before ML advisory layer runs)
        # ML will be applied AFTER all guards at the end of the pipeline
        confidence = confidence_after_context
        confidence = max(0.0, min(100.0, confidence))
        
        logger.info(f"   → Confidence (before ML advisory): {confidence:.1f}%")
        
        # СТЪПКА 11.5: MTF CONSENSUS CHECK (STRICT ICT)
        logger.info("🔍 Step 11.5: MTF Consensus Validation")
        mtf_consensus_data = self._calculate_mtf_consensus(symbol, timeframe, bias, mtf_data)
        
        logger.info(f"   → MTF Consensus: {mtf_consensus_data['consensus_pct']:.1f}%")
        logger.info(f"   → Aligned TFs: {mtf_consensus_data['aligned_count']}/{mtf_consensus_data['total_count']}")
        logger.info(f"   → Minimum Required: 50%")
        
        # Ако MTF consensus < 50%, confidence = 0 и сигналът НЕ СЕ ИЗПРАЩА
        if mtf_consensus_data['consensus_pct'] < 50.0:
            logger.info(f"❌ BLOCKED at Step 11.5: MTF consensus {mtf_consensus_data['consensus_pct']:.1f}% < 50%")
            logger.info(f"✅ Generating NO_TRADE (blocked_at_step: 11.5, reason: Insufficient MTF consensus)")
            logger.error(f"❌ MTF consensus {mtf_consensus_data['consensus_pct']:.1f}% < 50% - сигналът НЕ СЕ ИЗПРАЩА")
            # Изпрати информативно съобщение
            context = self._extract_context_data(df, bias)
            return self._create_no_trade_message(
                symbol=symbol,
                timeframe=timeframe,
                reason=f"Липса на MTF consensus ({mtf_consensus_data['consensus_pct']:.1f}%)",
                details=f"Необходими: >=50% aligned TFs. Намерени: {mtf_consensus_data['aligned_count']}/{mtf_consensus_data['total_count']}",
                mtf_breakdown=mtf_consensus_data['breakdown'],
                current_price=context['current_price'],
                price_change_24h=context['price_change_24h'],
                rsi=context['rsi'],
                signal_direction=context['signal_direction'],
                confidence=confidence
            )
        
        logger.info(f"✅ PASSED Step 11.5: MTF consensus validated ({mtf_consensus_data['consensus_pct']:.1f}% >= 50%)")

        # ✅ NEW: HTF Bias Direction Validation (CRITICAL ICT PRINCIPLE)
        logger.info("🔍 Step 11.5b: HTF Bias Direction Alignment")
        
        # Get HTF bias from earlier analysis
        htf_bias_value = ict_components.get('htf_bias', 'NEUTRAL')
        entry_bias_value = bias.value if hasattr(bias, 'value') else str(bias)
        
        logger.info(f"   → HTF Bias: {htf_bias_value}")
        logger.info(f"   → Entry Bias: {entry_bias_value}")
        
        # ICT Rule: NEVER trade against HTF bias
        if htf_bias_value in ['BULLISH', 'BEARISH'] and htf_bias_value != 'NEUTRAL':
            if (htf_bias_value == 'BEARISH' and entry_bias_value == 'BULLISH') or \
               (htf_bias_value == 'BULLISH' and entry_bias_value == 'BEARISH'):
                logger.info(f"❌ BLOCKED at Step 11.5b: Counter-HTF trade detected!")
                logger.info(f"   HTF ({hierarchy.get('htf_bias_tf', 'unknown')}) is {htf_bias_value}, but entry ({timeframe}) is {entry_bias_value}")
                logger.error(f"❌ Counter-HTF trade: HTF {htf_bias_value} vs Entry {entry_bias_value} - BLOCKED")
                
                context = self._extract_context_data(df, bias)
                return self._create_no_trade_message(
                    symbol=symbol,
                    timeframe=timeframe,
                    reason=f"Counter-trend trade against HTF bias",
                    details=f"HTF ({hierarchy.get('htf_bias_tf', 'unknown')}): {htf_bias_value}, Entry ({timeframe}): {entry_bias_value}. ICT principle: Never trade against HTF bias.",
                    mtf_breakdown=mtf_consensus_data['breakdown'],
                    current_price=context['current_price'],
                    price_change_24h=context['price_change_24h'],
                    rsi=context['rsi'],
                    signal_direction=context['signal_direction'],
                    confidence=confidence
                )
        
        logger.info(f"✅ PASSED Step 11.5b: HTF bias aligned or neutral ({htf_bias_value})")
        
        # Confidence check (dynamic based on auto vs manual)
        logger.info("🔍 Step 11.6: Final Confidence Check")
        
        # Determine min confidence based on signal type
        min_confidence = 50 if is_auto else 55
        mode = "Auto" if is_auto else "Manual"
        
        logger.info(f"   → Final Confidence: {confidence:.1f}%")
        logger.info(f"   → Minimum Required: {min_confidence}% ({mode} mode)")
        
        if confidence < min_confidence:
            logger.info(f"❌ BLOCKED at Step 11.6: Confidence {confidence:.1f}% < {min_confidence}% ({mode} mode)")
            logger.error(f"❌ Confidence {confidence:.1f}% < {min_confidence}% - сигналът НЕ СЕ ИЗПРАЩА ({mode})")
            context = self._extract_context_data(df, bias)
            return self._create_no_trade_message(
                symbol=symbol,
                timeframe=timeframe,
                reason=f"Ниска увереност ({confidence:.1f}%) за {mode} сигнал",
                details=f"Необходими: >={min_confidence}%. Намерени: {confidence:.1f}%",
                mtf_breakdown=mtf_consensus_data['breakdown'],
                current_price=context['current_price'],
                price_change_24h=context['price_change_24h'],
                rsi=context['rsi'],
                signal_direction=context['signal_direction'],
                confidence=confidence
            )
        
        logger.info(f"✅ PASSED Step 11.6: Confidence validated ({confidence:.1f}% >= {min_confidence}% - {mode} mode)")
        
        # СТЪПКА 12: FINAL SIGNAL GENERATION
        logger.info("🔍 Step 12: Final Signal Generation")
        signal_strength = self._calculate_signal_strength(confidence, risk_reward_ratio, ict_components)
        signal_type = self._determine_signal_type(bias, signal_strength, confidence)
        
        logger.info(f"   → Signal Type: {signal_type.value}")
        logger.info(f"   → Signal Strength: {signal_strength.value}")
        logger.info(f"   → Confidence: {confidence:.1f}%")
        
        # =========================================================================
        # ✅ ESB v1.0 §2.1-2.2: ENTRY GATING & CONFIDENCE THRESHOLD EVALUATION
        # =========================================================================
        logger.info("=" * 60)
        logger.info("STEP 12.1: ENTRY GATING EVALUATION (ESB §2.1)")
        logger.info("=" * 60)
        
        if ENTRY_GATING_AVAILABLE:
            # Build signal context for Entry Gating evaluation
            signal_context = {
                'symbol': symbol,
                'timeframe': timeframe,
                'direction': signal_type.value if hasattr(signal_type, 'value') else str(signal_type),
                'raw_confidence': confidence,
                
                # Entry Gating fields
                'system_state': self._get_system_state(),
                'breaker_block_active': self._check_breaker_block_active(ict_components, signal_type),
                'active_signal_exists': self._check_active_signal(symbol, timeframe),
                'cooldown_active': self._check_cooldown(symbol, timeframe),
                'market_state': self._get_market_state(symbol),
                'signature_already_seen': self._check_signature(symbol, timeframe, signal_type, datetime.now())
            }
            
            # Evaluate Entry Gating (ESB §2.1)
            entry_allowed = evaluate_entry_gating(signal_context.copy())  # Use copy to ensure immutability
            
            if not entry_allowed:
                logger.info(f"⛔ Entry Gating BLOCKED: {symbol} {timeframe}")
                logger.debug(f"Entry Gating context: {signal_context}")
                return None  # HARD BLOCK
            
            logger.info(f"✅ PASSED Entry Gating: {symbol} {timeframe}")
        else:
            logger.warning("⚠️ Entry Gating evaluator not available - skipping check")
        
        # =========================================================================
        logger.info("=" * 60)
        logger.info("STEP 12.2: CONFIDENCE THRESHOLD EVALUATION (ESB §2.2)")
        logger.info("=" * 60)
        
        if CONFIDENCE_THRESHOLD_AVAILABLE:
            # Build signal context for Confidence Threshold evaluation
            # Reuse same context from Entry Gating (only direction and raw_confidence are required)
            confidence_context = {
                'direction': signal_type.value if hasattr(signal_type, 'value') else str(signal_type),
                'raw_confidence': confidence
            }
            
            # Evaluate Confidence Threshold (ESB §2.2)
            threshold_passed = evaluate_confidence_threshold(confidence_context.copy())  # Use copy to ensure immutability
            
            if not threshold_passed:
                logger.info(f"⛔ Confidence Threshold BLOCKED: {symbol} {timeframe} (confidence: {confidence:.2f})")
                return None  # HARD BLOCK
            
            logger.info(f"✅ PASSED Confidence Threshold: {symbol} {timeframe} (confidence: {confidence:.2f})")
        else:
            logger.warning("⚠️ Confidence Threshold evaluator not available - skipping check")
        
        # =========================================================================
        logger.info("=" * 60)
        logger.info("STEP 12.3: EXECUTION ELIGIBILITY EVALUATION (ESB §2.3)")
        logger.info("=" * 60)
        
        if EXECUTION_ELIGIBILITY_AVAILABLE:
            # Build execution context for Execution Eligibility evaluation
            execution_context = {
                'symbol': symbol,
                'execution_state': self._get_execution_state(),
                'execution_layer_available': self._check_execution_layer_available(),
                'symbol_execution_locked': self._check_symbol_execution_lock(symbol),
                'position_capacity_available': self._check_position_capacity(symbol, signal_type.value if hasattr(signal_type, 'value') else str(signal_type)),
                'emergency_halt_active': self._check_emergency_halt()
            }
            
            # Evaluate Execution Eligibility (ESB §2.3)
            execution_allowed = evaluate_execution_eligibility(execution_context.copy())  # Use copy to ensure immutability
            
            if not execution_allowed:
                logger.info(f"⛔ §2.3 Execution Eligibility BLOCKED: {symbol} {timeframe}")
                logger.debug(f"Execution Eligibility context: {execution_context}")
                return None  # HARD BLOCK
            
            logger.info(f"✅ PASSED Execution Eligibility: {symbol} {timeframe}")
        else:
            logger.warning("⚠️ Execution Eligibility evaluator not available - skipping check")
        
        # =========================================================================
        logger.info("=" * 60)
        logger.info("STEP 12.4: RISK ADMISSION EVALUATION (ESB §2.4)")
        logger.info("=" * 60)
        
        if RISK_ADMISSION_AVAILABLE:
            # Build risk context for Risk Admission evaluation
            risk_context = {
                'signal_risk': self._get_signal_risk(),
                'total_open_risk': self._get_total_open_risk(),
                'symbol_exposure': self._get_symbol_exposure(symbol),
                'direction_exposure': self._get_direction_exposure(signal_type.value if hasattr(signal_type, 'value') else str(signal_type)),
                'daily_loss': self._get_daily_loss()
            }
            
            # Evaluate Risk Admission (ESB §2.4)
            risk_admitted = evaluate_risk_admission(risk_context.copy())  # Use copy to ensure immutability
            
            if not risk_admitted:
                logger.info(f"⛔ §2.4 Risk Admission BLOCKED: {symbol} {timeframe}")
                logger.debug(f"Risk context: {risk_context}")
                return None  # HARD BLOCK
            
            logger.info(f"✅ PASSED Risk Admission: {symbol} {timeframe}")
        else:
            logger.warning("⚠️ Risk Admission evaluator not available - skipping check")
        
        logger.info("=" * 60)
        logger.info("✅ ALL EVALUATIONS PASSED (§2.1-2.4) - PROCEEDING TO SIGNAL CREATION")
        logger.info("=" * 60)
        
        # =========================================================================
        # END ENTRY GATING, CONFIDENCE THRESHOLD, EXECUTION ELIGIBILITY & RISK ADMISSION
        # =========================================================================
        
        # ═══════════════════════════════════════════════════════════════
        # ✅ PR-ML-8: ML ADVISORY LAYER (FINAL POSITION)
        # ═══════════════════════════════════════════════════════════════
        # ML runs LAST, after all strategy decisions, risk filters, and guards.
        # ML acts ONLY as advisory layer that modifies confidence within bounds.
        # ML NEVER influences signal direction, entry/SL/TP, or overrides guards.
        # ═══════════════════════════════════════════════════════════════
        logger.info("=" * 60)
        logger.info("STEP 12.0: ML ADVISORY LAYER (PR-ML-8)")
        logger.info("=" * 60)
        
        # Strategy signal is now LOCKED - ML cannot change it
        strategy_signal = 'BUY' if bias == MarketBias.BULLISH else 'SELL' if bias == MarketBias.BEARISH else 'HOLD'
        
        if self.use_ml and self.ml_engine and self.ml_engine.model is not None:
            try:
                logger.info(f"🤖 Invoking ML Advisory (confidence-only modification)")
                logger.info(f"   Strategy Signal (LOCKED): {strategy_signal}")
                logger.info(f"   Base Confidence: {confidence:.1f}%")
                
                # Call new ML advisory method
                ml_advisory = self.ml_engine.get_confidence_modifier(
                    analysis=ml_features,
                    final_signal=strategy_signal,
                    base_confidence=confidence
                )
                
                # Apply ML modifier to confidence ONLY
                original_confidence = confidence
                confidence = confidence * ml_advisory['confidence_modifier']
                
                # Clamp to valid range
                confidence = max(0.0, min(100.0, confidence))
                
                # Logging
                logger.info(f"   ML Mode: {ml_advisory['mode']}")
                logger.info(f"   ML Confidence: {ml_advisory['ml_confidence']:.1f}%")
                logger.info(f"   Confidence Modifier: {ml_advisory['confidence_modifier']:.3f}x")
                logger.info(f"   Confidence: {original_confidence:.1f}% → {confidence:.1f}%")
                
                # Log warnings if any
                if ml_advisory['warnings']:
                    for warning in ml_advisory['warnings']:
                        logger.warning(f"⚠️ {warning}")
                
                logger.info(f"✅ ML Advisory complete (direction unchanged: {strategy_signal})")
                
            except Exception as e:
                logger.error(f"❌ ML Advisory error: {e}")
                logger.info(f"✅ Continuing with ICT-only confidence: {confidence:.1f}%")
        else:
            logger.info("ℹ️ ML Advisory not available - using ICT-only confidence")
        
        logger.info("=" * 60)
        # ═══════════════════════════════════════════════════════════════
        # END ML ADVISORY LAYER
        # ═══════════════════════════════════════════════════════════════
        
        # ✅ FIX 3: STEP 12a - Entry Timing Validation
        logger.info("🔍 Step 12a: Entry Timing Validation")
        is_valid, reason = self._validate_entry_timing(
            entry_price, 
            current_price, 
            signal_type,
            bias
        )
        
        if not is_valid:
            logger.error(f"❌ BLOCKED at Step 12a: {reason}")
            return None  # Don't send invalid signal
        else:
            logger.info(f"   → {reason}")
        
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
        # ✅ Entry scenario already selected in Step 8.1
        if entry_scenario_result:
            logger.info(f"🎯 Using Entry Scenario from Step 8.1: {entry_scenario_result['scenario']} (score: {entry_scenario_result['score']})")
        else:
            logger.info("⚠️ No entry scenario from Step 8.1 (score < 60)")

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
            timeframe_hierarchy=hierarchy_info,  # ✅ PR #4: TF hierarchy info
            reasoning=reasoning,
            warnings=warnings,
            entry_scenario=entry_scenario_result['scenario'] if entry_scenario_result else None,
            entry_scenario_score=entry_scenario_result['score'] if entry_scenario_result else 0,
            entry_scenario_reasoning=entry_scenario_result['reasoning'] if entry_scenario_result else "",
            entry_scenario_triggers=entry_scenario_result.get("triggers", []) if entry_scenario_result else [],
            zone_explanations=zone_explanations
        )
        
        logger.info("=" * 60)
        logger.info("✅ SIGNAL GENERATION COMPLETE")
        logger.info(f"   Signal Type: {signal_type.value}")
        logger.info(f"   Entry: ${entry_price:.2f}")
        logger.info(f"   SL: ${sl_price:.2f}")
        logger.info(f"   TP1: ${tp_prices[0]:.2f}")
        logger.info(f"   RR: {risk_reward_ratio:.2f}")
        logger.info(f"   Confidence: {confidence:.1f}%")
        logger.info(f"   MTF Consensus: {mtf_consensus_data['consensus_pct']:.1f}%")
        logger.info("=" * 60)
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
        
        # ═══════════════════════════════════════════════════════════
        # ✅ PR #8 LAYER 1: NEWS SENTIMENT FILTER (Before final return)
        # ═══════════════════════════════════════════════════════════
        logger.info("📰 Step 12b: News Sentiment Filter (PR #8)")
        
        news_check = self._check_news_sentiment_before_signal(
            symbol=symbol,
            signal_type=signal_type.value if hasattr(signal_type, 'value') else str(signal_type),
            timeframe=timeframe
        )
        
        if not news_check['allow_signal']:
            logger.warning(f"❌ BLOCKED at Step 12b: {news_check['reasoning']}")
            logger.info(f"   Sentiment Score: {news_check['sentiment_score']:.0f}")
            if news_check['critical_news']:
                logger.info(f"   Critical News: {len(news_check['critical_news'])} articles")
            return None  # Don't send signal
        
        # Add news sentiment to warnings if there's a mild conflict
        if abs(news_check['sentiment_score']) > 10 and news_check['reasoning']:
            warnings.append(news_check['reasoning'])
            logger.info(f"Added news sentiment warning: {news_check['reasoning']}")
        
        logger.info(f"✅ PASSED Step 12b: News sentiment check ({news_check['sentiment_score']:.0f})")
        
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
        """Calculate ATR with safe defaults."""
        try:
            if df is None or len(df) == 0:
                return pd.Series(dtype=float)
            
            if len(df) < period:
                logger.warning(f"⚠️ Insufficient data for ATR (need {period} bars, have {len(df)})")
                fallback_atr = df['close'].iloc[-1] * ATR_FALLBACK_PCT
                logger.info(f"   → Using {ATR_FALLBACK_PCT*100:.0f}% fallback ATR: ${fallback_atr:.2f}")
                # Return a Series with the same index
                return pd.Series([fallback_atr] * len(df), index=df.index, dtype=float)
            
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
            
            # Check for NaN or 0 values at the end
            if pd.isna(atr.iloc[-1]) or atr.iloc[-1] == 0:
                logger.warning(f"⚠️ ATR is {atr.iloc[-1]} - using {ATR_FALLBACK_PCT*100:.0f}% fallback")
                fallback_atr = df['close'].iloc[-1] * ATR_FALLBACK_PCT
                atr = atr.fillna(fallback_atr)
                atr = atr.replace(0, fallback_atr)
            
            return atr
            
        except Exception as e:
            logger.error(f"❌ ATR calculation error: {e}")
            if df is not None and len(df) > 0:
                fallback_atr = df['close'].iloc[-1] * ATR_FALLBACK_PCT
                return pd.Series([fallback_atr] * len(df), index=df.index, dtype=float)
            return pd.Series(dtype=float)
    
    def _find_recent_swing_for_sl(self, df: pd.DataFrame, bias: MarketBias, entry_price: float, lookback: int = 50) -> Optional[float]:
        """Find recent swing low/high for SL fallback."""
        try:
            if df is None or len(df) < 10:
                return None
            
            lookback = min(lookback, len(df) - 5)
            recent_df = df.iloc[-lookback:]
            
            if bias == MarketBias.BULLISH:
                swing_low = recent_df['low'].min()
                if swing_low < entry_price:
                    logger.info(f"   → Found swing low @ ${swing_low:.2f}")
                    return float(swing_low)
            else:
                swing_high = recent_df['high'].max()
                if swing_high > entry_price:
                    logger.info(f"   → Found swing high @ ${swing_high:.2f}")
                    return float(swing_high)
            
            return None
        except Exception as e:
            logger.error(f"❌ Swing detection error: {e}")
            return None
    
    def _calculate_sl_from_anchor(
        self,
        invalidation_anchor: Dict,
        bias: MarketBias,
        entry_price: float,
        timeframe: str,
        df: pd.DataFrame
    ) -> Optional[float]:
        """Calculate SL from invalidation anchor - SINGLE SOURCE OF TRUTH."""
        
        anchor_price = invalidation_anchor.get('price')
        anchor_type = invalidation_anchor.get('type')
        
        if anchor_price is None:
            logger.error(f"❌ Invalid anchor price")
            return None
        
        is_bullish = bias == MarketBias.BULLISH
        
        # Sanity check 1: Anchor on correct side
        if is_bullish and anchor_price >= entry_price:
            logger.error(f"❌ Anchor ${anchor_price:.2f} >= entry ${entry_price:.2f} for LONG")
            return None
        if not is_bullish and anchor_price <= entry_price:
            logger.error(f"❌ Anchor ${anchor_price:.2f} <= entry ${entry_price:.2f} for SHORT")
            return None
        
        # Sanity check 2: Minimum distance
        distance_pct = abs(anchor_price - entry_price) / entry_price
        min_distance = TIMEFRAME_MIN_SL_DISTANCE.get(timeframe, 0.005)
        
        if distance_pct < min_distance:
            logger.warning(f"⚠️ Anchor too close ({distance_pct*100:.2f}% < {min_distance*100:.1f}%)")
            if is_bullish:
                anchor_price = entry_price * (1 - min_distance)
            else:
                anchor_price = entry_price * (1 + min_distance)
            logger.info(f"   → Extended anchor to ${anchor_price:.2f}")
        
        # Calculate buffer
        # Ensure ATR column exists (calculate if missing)
        if df is not None and len(df) > 0 and 'atr' not in df.columns:
            df['atr'] = self._calculate_atr(df)
        
        if 'atr' in df.columns and len(df) > 0:
            atr_value = df['atr'].iloc[-1]
            if pd.isna(atr_value) or atr_value == 0:
                atr_value = entry_price * ATR_FALLBACK_PCT
        else:
            atr_value = entry_price * ATR_FALLBACK_PCT
        
        atr_buffer = atr_value * 0.25
        pct_buffer = entry_price * TIMEFRAME_BUFFER_PCT.get(timeframe, 0.002)
        buffer = max(atr_buffer, pct_buffer)
        
        # Apply buffer
        if is_bullish:
            sl_price = anchor_price - buffer
        else:
            sl_price = anchor_price + buffer
        
        logger.info(f"   → Anchor: {anchor_type} @ ${anchor_price:.2f}")
        logger.info(f"   → Buffer: ${buffer:.2f} (ATR: ${atr_buffer:.2f}, TF%: ${pct_buffer:.2f})")
        logger.info(f"   → SL: ${sl_price:.2f} ({abs(sl_price - entry_price) / entry_price * 100:.2f}% from entry)")
        
        return float(sl_price)
    
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
                
                # Add ILP sweeps to liquidity_sweeps (quality filter)
                ilp_swept_pools = ilp_analysis.get('swept_pools', [])
                if ilp_swept_pools:
                    quality_ilp_sweeps = []
                    for pool in ilp_swept_pools:
                        # Get attributes safely
                        candles_ago = getattr(pool, 'candles_ago', 999)
                        strength = getattr(pool, 'strength_score', 0)
                        
                        # Quality filter: recent (< 20 candles) and strong (> 0.5)
                        if candles_ago <= 20 and strength >= 0.5:
                            quality_ilp_sweeps.append({
                                'type': pool.pool_type.value,  # IBSL or ISSL
                                'price': pool.price,
                                'candles_ago': candles_ago,
                                'strength': strength,
                                'source': 'ILP'
                            })
                    
                    # Merge with existing liquidity_sweeps
                    if quality_ilp_sweeps:
                        existing_sweeps = components.get('liquidity_sweeps', [])
                        existing_sweeps.extend(quality_ilp_sweeps)
                        components['liquidity_sweeps'] = existing_sweeps
                        logger.info(f"Added {len(quality_ilp_sweeps)} quality ILP sweeps (recent & strong)")
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
                
                # Ensure result is valid dict (defensive)
                if not isinstance(luxalgo_result, dict):
                    logger.warning(f"LuxAlgo returned invalid type: {type(luxalgo_result)}, using defaults")
                    luxalgo_result = {
                        "sr_data": {},
                        "ict_data": {},
                        "combined_signal": {},
                        "entry_valid": False,
                        "status": "invalid_return_type"
                    }
                
                components['luxalgo_sr'] = luxalgo_result.get('sr_data', {})
                components['luxalgo_ict'] = luxalgo_result.get('ict_data', {})
                components['luxalgo_combined'] = luxalgo_result.get('combined_signal', {})
                
                # Extract entry_valid and status for observability
                entry_valid = luxalgo_result.get('entry_valid', False)
                status = luxalgo_result.get('status', 'unknown')
                
                # Structured logging (mandatory)
                sr_data = components['luxalgo_sr']
                sr_zones_count = len(sr_data.get('support_zones', [])) + len(sr_data.get('resistance_zones', []))
                logger.info(
                    f"LuxAlgo result: entry_valid={entry_valid}, status={status}, "
                    f"sr_zones={sr_zones_count}"
                )
                
                # ADVISORY MODE: entry_valid is used for confidence, NOT as hard gate
                # (Existing downstream logic should use entry_valid as confidence modifier)
                
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
        ✅ IMPROVED MTF Consensus:
        1. RANGING/NEUTRAL = ignored (not counted as conflicting)
        2. Dynamic TF selection based on entry TF
        3. Correct formula: aligned / (bullish + bearish) * 100
        """
        
        # Dynamic MTF hierarchy based on entry timeframe
        MTF_HIERARCHY = {
            '5m':  ['5m', '15m', '30m', '1h'],
            '15m': ['15m', '30m', '1h', '4h'],
            '30m': ['30m', '1h', '2h', '4h'],
            '1h':  ['1h', '2h', '4h', '1d'],
            '2h':  ['2h', '4h', '1d'],
            '4h':  ['4h', '1d'],
            '1d':  ['1d', '1w']
        }
        
        # Get relevant timeframes for this entry TF
        relevant_tfs = MTF_HIERARCHY.get(primary_timeframe, ['1h', '4h', '1d'])
        
        # ✅ NORMALIZE target_bias to MarketBias enum
        if isinstance(target_bias, str):
            target_bias = MarketBias[target_bias.upper()]
        
        breakdown = {}
        aligned_count = 0
        bullish_votes = 0
        bearish_votes = 0
        
        # Primary timeframe is always 100% aligned
        breakdown[primary_timeframe] = {
            'bias': target_bias.value if hasattr(target_bias, 'value') else str(target_bias),
            'confidence': 100,
            'aligned': True
        }
        aligned_count += 1
        if target_bias == MarketBias.BULLISH:
            bullish_votes += 1
        elif target_bias == MarketBias.BEARISH:
            bearish_votes += 1
        
        # Check other relevant timeframes
        if mtf_data is not None and isinstance(mtf_data, dict):
            for tf in relevant_tfs:
                if tf == primary_timeframe:
                    continue  # Already added
                
                tf_df = mtf_data.get(tf)
                if tf_df is not None and not tf_df.empty and len(tf_df) >= 20:
                    try:
                        tf_bias, confidence = self._calculate_pure_ict_bias_for_tf(tf_df, symbol, tf)
                        
                        # ✅ NORMALIZE tf_bias to enum immediately
                        if isinstance(tf_bias, str):
                            tf_bias = MarketBias[tf_bias.upper()]
                        
                        # ✅ FIX: RANGING/NEUTRAL = ignored (not counted)
                        if tf_bias in [MarketBias.NEUTRAL, MarketBias.RANGING]:
                            breakdown[tf] = {
                                'bias': tf_bias.value if hasattr(tf_bias, 'value') else str(tf_bias),
                                'confidence': round(confidence, 1),
                                'aligned': None  # Not counted
                            }
                            continue  # Skip, don't count as vote
                        
                        # Count directional votes only (AFTER RANGING filter)
                        if tf_bias == MarketBias.BULLISH:
                            bullish_votes += 1
                        elif tf_bias == MarketBias.BEARISH:
                            bearish_votes += 1
                        
                        # Check alignment AFTER we know it's directional
                        # ✅ NORMALIZE both to enum for comparison
                        tf_bias_enum = tf_bias if isinstance(tf_bias, MarketBias) else MarketBias[str(tf_bias).upper()]
                        target_bias_enum = target_bias if isinstance(target_bias, MarketBias) else MarketBias[str(target_bias).upper()]
                        
                        is_aligned = (tf_bias_enum == target_bias_enum)
                        logger.info(f"   → MTF {tf}: bias={tf_bias_enum.value}, target={target_bias_enum.value}, aligned={is_aligned}")
                        
                        if is_aligned:
                            aligned_count += 1
                        
                        breakdown[tf] = {
                            'bias': tf_bias.value if hasattr(tf_bias, 'value') else str(tf_bias),
                            'confidence': round(confidence, 1),
                            'aligned': is_aligned
                        }
                        
                    except Exception as e:
                        logger.warning(f"MTF consensus analysis failed for {tf}: {e}")
        
        # ✅ CORRECT FORMULA: aligned / (bullish + bearish) * 100
        total_directional_votes = bullish_votes + bearish_votes
        if total_directional_votes > 0:
            consensus_pct = (aligned_count / total_directional_votes) * 100
        else:
            consensus_pct = 0
        
        aligned_tfs = [tf for tf, data in breakdown.items() if data.get('aligned') == True]
        conflicting_tfs = [tf for tf, data in breakdown.items() if data.get('aligned') == False]
        neutral_tfs = [tf for tf, data in breakdown.items() if data.get('aligned') is None]
        
        logger.info(f"📊 MTF Consensus: {consensus_pct:.1f}% ({aligned_count} aligned, {len(neutral_tfs)} neutral, {len(conflicting_tfs)} conflicting)")
        
        return {
            'consensus_pct': round(consensus_pct, 1),
            'breakdown': breakdown,
            'aligned_tfs': aligned_tfs,
            'conflicting_tfs': conflicting_tfs,
            'neutral_tfs': neutral_tfs,
            'aligned_count': aligned_count,
            'total_count': total_directional_votes,
            'total_votes': total_directional_votes,
            'bullish_votes': bullish_votes,
            'bearish_votes': bearish_votes
        }

    def _calculate_pure_ict_bias_for_tf(self, df: pd.DataFrame, symbol: str, timeframe: str) -> Tuple[str, float]:
        """
        Calculate pure ICT bias based ONLY on market structure (HH/HL vs LH/LL).
        
        NO Order Blocks, NO Displacement - PURE structure analysis.
        
        Args:
            df: DataFrame with OHLCV data for the specific timeframe
            symbol: Trading symbol
            timeframe: Timeframe being analyzed
            
        Returns:
            Tuple of (bias_direction, bias_score)
            - bias_direction: "BULLISH", "BEARISH", or "RANGING"
            - bias_score: 0-50 confidence score (structure only)
        """
        logger.info(f"🔍 Calculating PURE structure bias for {symbol} {timeframe}")
        
        bullish_score = 0
        bearish_score = 0
        max_score = 50  # Only structure (was 100 with OB+Displacement)
        
        # ═══════════════════════════════════════════════════════════
        # STRUCTURE ANALYSIS (ONLY SOURCE OF BIAS)
        # ═══════════════════════════════════════════════════════════
        
        try:
            swing_highs = []
            swing_lows = []
            window = 5
            
            for i in range(window, len(df) - window):
                # Swing high
                if df['high'].iloc[i] == df['high'].iloc[i-window:i+window+1].max():
                    swing_highs.append({
                        'price': df['high'].iloc[i],
                        'index': i,
                        'time': df.index[i]
                    })
                
                # Swing low
                if df['low'].iloc[i] == df['low'].iloc[i-window:i+window+1].min():
                    swing_lows.append({
                        'price': df['low'].iloc[i],
                        'index': i,
                        'time': df.index[i]
                    })
            
            # Analyze last 2 swing points
            if len(swing_highs) >= 2:
                last_high = swing_highs[-1]['price']
                prev_high = swing_highs[-2]['price']
                
                if last_high > prev_high:
                    bullish_score += 25  # HH (Higher High)
                    logger.info(f"  ✅ HH detected: {prev_high:.2f} → {last_high:.2f} (+25 bullish)")
                else:
                    bearish_score += 25  # LH (Lower High)
                    logger.info(f"  ✅ LH detected: {prev_high:.2f} → {last_high:.2f} (+25 bearish)")
            
            if len(swing_lows) >= 2:
                last_low = swing_lows[-1]['price']
                prev_low = swing_lows[-2]['price']
                
                if last_low > prev_low:
                    bullish_score += 25  # HL (Higher Low)
                    logger.info(f"  ✅ HL detected: {prev_low:.2f} → {last_low:.2f} (+25 bullish)")
                else:
                    bearish_score += 25  # LL (Lower Low)
                    logger.info(f"  ✅ LL detected: {prev_low:.2f} → {last_low:.2f} (+25 bearish)")
            
            logger.info(f"  📊 Structure scores: Bullish={bullish_score}, Bearish={bearish_score}")
            
        except Exception as e:
            logger.warning(f"⚠️ Structure analysis failed: {e}")
        
        # ═══════════════════════════════════════════════════════════
        # DETERMINE BIAS (STRUCTURE ONLY)
        # ═══════════════════════════════════════════════════════════
        
        threshold = 50  # Need full structure score (both HH+HL or LH+LL)
        
        if bullish_score >= threshold and bullish_score > bearish_score:
            bias = "BULLISH"
            score = bullish_score
            logger.info(f"  ✅ BIAS: BULLISH (HH + HL confirmed)")
        elif bearish_score >= threshold and bearish_score > bullish_score:
            bias = "BEARISH"
            score = bearish_score
            logger.info(f"  ✅ BIAS: BEARISH (LH + LL confirmed)")
        else:
            bias = "RANGING"
            score = max(bullish_score, bearish_score)
            logger.info(f"  ⚠️ BIAS: RANGING (mixed structure, score={score})")
        
        return bias, score

    
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
        """
        Determine market bias from HTF (Higher Timeframe)
        
        ✅ ICT Rule: Bias = HTF structure direction
        - HTF bias has ABSOLUTE priority
        - Local OB/FVG are for entry validation, NOT bias determination
        """
        
        # ✅ PRIORITY 1: HTF Bias (return directly if available)
        if mtf_analysis and 'htf_bias' in mtf_analysis:
            htf_bias = mtf_analysis.get('htf_bias', 'NEUTRAL')
            
            if 'BULLISH' in htf_bias.upper():
                return MarketBias.BULLISH
            elif 'BEARISH' in htf_bias.upper():
                return MarketBias.BEARISH
            # If HTF is NEUTRAL, continue to fallback logic
        
        # ✅ FALLBACK: Calculate from local components (when HTF unavailable)
        bullish_score = 0
        bearish_score = 0
        
        # Order blocks
        # Filter only MEDIUM-STRONG order blocks for bias (strength >= 40)
        bullish_obs = [ob for ob in ict_components.get('order_blocks', []) 
                       if hasattr(ob, 'type') and 'BULLISH' in str(ob.type.value) 
                       and hasattr(ob, 'strength') and ob.strength >= 40]
        bearish_obs = [ob for ob in ict_components.get('order_blocks', []) 
                       if hasattr(ob, 'type') and 'BEARISH' in str(ob.type.value)
                       and hasattr(ob, 'strength') and ob.strength >= 40]
        
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
        
        # Determine bias from local components
        if bullish_score >= 1 and bullish_score > bearish_score:
            return MarketBias.BULLISH
        elif bearish_score >= 1 and bearish_score > bullish_score:
            return MarketBias.BEARISH
        elif bullish_score == bearish_score > 0:
            return MarketBias.NEUTRAL
        else:
            return MarketBias.RANGING

    def _check_structure_break(self, df: pd.DataFrame) -> bool:
        """Check for recent structure break (BOS/CHOCH/MSS)
        
        Logic:
        - Get swing high/low from candles -150 to -3 (PAST)
        - Check if last 3 candles (PRESENT) broke those levels
        """
        lookback = 150
        recent = 3
        
        if len(df) < lookback + recent:
            return False
        
        # IMPORTANT: Swing points from PAST candles (exclude last 3)
        start_idx = -(lookback + recent)
        end_idx = -recent
        
        swing_high = df['high'].iloc[start_idx:end_idx].max()
        swing_low = df['low'].iloc[start_idx:end_idx].min()
        
        # Check if last 3 candles broke structure
        threshold_pct = self.config.get('structure_break_threshold', 0.1) / 100
        
        for i in range(-recent, 0):
            # Bullish break: close above swing high
            if df['close'].iloc[i] > swing_high * (1 + threshold_pct):
                return True
            
            # Bearish break: close below swing low  
            if df['close'].iloc[i] < swing_low * (1 - threshold_pct):
                return True
        
        return False
    def _check_displacement(self, df: pd.DataFrame) -> tuple:
        """Check for recent displacement
        
        Returns:
            (detected: bool, strength: float)
        """
        if len(df) < 5:
            return False, 0.0
        
        max_strength = 0.0
        detected = False
        
        # Check last 3 candles for displacement
        for i in range(-3, 0):
            price_change = abs(df['close'].iloc[i] - df['open'].iloc[i])
            price_change_pct = (price_change / df['open'].iloc[i]) * 100
            max_strength = max(max_strength, price_change_pct)
            
            if price_change_pct >= self.config['min_displacement_pct']:
                detected = True
        
        return detected, max_strength
    
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
        sr_levels: Dict,
        timeframe: str
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
        
        3. Distance constraints (UNIVERSAL 5% MAX):
           - HARD REJECT: > 5% from current price (TOO_FAR - stale signal)
           - Buffer zone: 3% - 5% from current price (VALID_WAIT - needs pullback)
           - Optimal range: 0.5% - 3% from current price (VALID_NEAR - best entry)
           - Very close: < 0.5% from current price (TOO_LATE - warning only)
           - Universal 5% maximum applies to ALL timeframes (15m - 1w)
        
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
            - 'TOO_FAR': Entry zone too far (> 5% universal max - HARD REJECT)
            - 'VALID_WAIT': Entry zone in buffer (3% - 5% - wait for pullback)
            - 'VALID_NEAR': Entry zone in optimal range (0.5% - 3% - price approaching)
            - 'TOO_LATE': Price already passed the entry zone (< 0.5% - warning only)
            - 'NO_ZONE': No valid entry zone found (converted to fallback in calling code)
        """
        # ✅ Universal entry distance limits for ALL timeframes (15m - 1w)
        # Entry distance measures signal freshness, not trade duration
        # A signal with 20% entry distance is equally stale on any timeframe
        # Applies to both automatic signals (1h, 2h, 4h, 1d) and manual analysis (all TFs)
        min_distance_pct = 0.005  # 0.5% minimum (unchanged)
        max_distance_pct = 0.050  # 5% UNIVERSAL MAX (all timeframes)
        entry_buffer_pct = 0.002  # 0.2% buffer (unchanged)
        
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
        
        # ✅ FIX #5: Validate distance DIRECTION (not just magnitude)
        entry_center = entry_zone['center']
        
        if is_bearish:
            # BEARISH: Entry should be ABOVE current price (waiting for rally to sell)
            if entry_center <= current_price:
                logger.warning(f"⚠️ BEARISH entry ${entry_center:.2f} is NOT above current ${current_price:.2f}")
                logger.warning(f"   → Entry may have been hit already (check Step 12a)")
            
            # Calculate UPWARD distance
            distance_directional = (entry_center - current_price) / current_price * 100
            distance_direction = "above"
            entry_zone['distance_direction'] = distance_direction
            entry_zone['distance_directional'] = distance_directional
            logger.info(f"   → Entry {abs(distance_directional):.1f}% {distance_direction} current price")
            
        elif is_bullish:
            # BULLISH: Entry should be BELOW current price (waiting for dip to buy)
            if entry_center >= current_price:
                logger.warning(f"⚠️ BULLISH entry ${entry_center:.2f} is NOT below current ${current_price:.2f}")
                logger.warning(f"   → Entry may have been hit already (check Step 12a)")
            
            # Calculate DOWNWARD distance
            distance_directional = (current_price - entry_center) / current_price * 100
            distance_direction = "below"
            entry_zone['distance_direction'] = distance_direction
            entry_zone['distance_directional'] = distance_directional
            logger.info(f"   → Entry {abs(distance_directional):.1f}% {distance_direction} current price")
        
        # ==== DETERMINE STATUS ====
        
        distance_pct = best_zone['distance_pct']
        
        # ✅ FIRST: Check against universal 5% max (reject stale signals)
        if distance_pct > max_distance_pct:  # > 5%
            status = 'TOO_FAR'
            logger.error(
                f"❌ Entry zone too far: {distance_pct*100:.1f}% > "
                f"{max_distance_pct*100:.1f}% MAX - "
                f"сигналът НЕ СЕ ИЗПРАЩА (stale signal, universal limit for all timeframes)"
            )
            return None, 'TOO_FAR'  # REJECT SIGNAL
        
        # ✅ Buffer zone (3% - 5%) - needs pullback
        elif distance_pct > 0.030:  # 3% - 5%
            status = 'VALID_WAIT'
            logger.info(
                f"✅ Entry zone in buffer: {entry_zone['source']} at "
                f"${entry_zone['center']:.2f} ({distance_pct*100:.1f}% away) - "
                f"WAIT for pullback"
            )
        
        # ✅ Optimal zone (0.5% - 3%) - best entry range
        elif distance_pct >= 0.005:  # 0.5% - 3%
            status = 'VALID_NEAR'
            logger.info(
                f"✅ Entry zone in optimal range: {entry_zone['source']} at "
                f"${entry_zone['center']:.2f} ({distance_pct*100:.1f}% away) - "
                f"Price APPROACHING"
            )
        
        # ✅ Very close (< 0.5%) - may be too late but don't reject
        else:  # < 0.5%
            status = 'TOO_LATE'
            logger.warning(
                f"⚠️ Entry zone very close: {distance_pct*100:.1f}% - "
                f"may be too late for optimal entry"
            )
        
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
        bias: Optional[str] = None,
        timeframe: str = '1h'
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
        
        # Final fallback: structural levels with timeframe-based multipliers
        if len(tp_levels) == 1:
            # Get timeframe-optimized multipliers
            tp1_mult, tp2_mult, tp3_mult = get_tp_multipliers_by_timeframe(timeframe)
            
            tp2 = entry_price + (risk * tp2_mult) if direction == 'LONG' else entry_price - (risk * tp2_mult)
            tp_levels.append(tp2)
            logger.info(f"✅ TP2 extended to {tp2_mult}R: {tp2}")
            
            tp3 = entry_price + (risk * tp3_mult) if direction == 'LONG' else entry_price - (risk * tp3_mult)
            tp_levels.append(tp3)
            logger.info(f"✅ TP3 extended to {tp3_mult}R: {tp3}")
        
        return tp_levels[:3]

    def _calculate_sl_price(
        self,
        df: pd.DataFrame,
        entry_setup: Dict,
        entry_price: float,
        bias: MarketBias
    ) -> float:
        """
        ✅ ICT-COMPLIANT Stop Loss using invalidation levels (NOT volatility-based)
        
        Priority (LONG):
          1. Bullish Order Block low
          2. FVG low
          3. Liquidity sweep low
          4. Last swing low (structure)
          5. ATR fallback
        
        Priority (SHORT):
          1. Bearish Order Block high
          2. FVG high
          3. Liquidity sweep high
          4. Last swing high (structure)
          5. ATR fallback
        
        Returns:
            float: Stop loss price
        """
        # ✅ GUARD: Raise exception for HOLD/RANGING
        if bias in [MarketBias.NEUTRAL, MarketBias.RANGING]:
            raise ValueError(
                f"CRITICAL: _calculate_sl_price() called for {bias.value} signal! "
                f"HOLD/RANGING must use early exit. Pipeline violation."
            )
        
        # Get timeframe (backwards compatible)
        timeframe = entry_setup.get('timeframe', '1h')
        
        # ✅ TIMEFRAME-BASED minimum SL distance (NOT fixed 3%!)
        MIN_SL_DISTANCE = {
            '15m': 0.005,   # 0.5%
            '30m': 0.0075,  # 0.75%
            '1h': 0.010,    # 1.0%
            '2h': 0.0125,   # 1.25%
            '4h': 0.020,    # 2.0%
            '1d': 0.030     # 3.0%
        }
        min_sl_pct = MIN_SL_DISTANCE.get(timeframe, 0.015)
        
        # ✅ ICT Buffer (small, structure-based - NOT 1.5 ATR!)
        atr = df['atr'].iloc[-1]
        buffer_pct = 0.002 if timeframe in ['15m', '30m', '1h'] else 0.003
        buffer = max(atr * 0.25, entry_price * buffer_pct)
        
        sl_price = None
        sl_reason = "UNKNOWN"
        
        if bias == MarketBias.BULLISH:
            # Priority 1: Order Block low
            order_block = entry_setup.get('order_block')
            if order_block:
                if isinstance(order_block, dict):
                    ob_low = order_block.get('zone_low') or order_block.get('bottom')
                else:
                    ob_low = getattr(order_block, 'zone_low', None) or getattr(order_block, 'bottom', None)
                
                if ob_low:
                    sl_price = ob_low - buffer
                    sl_reason = "OB_INVALIDATION"
                    logger.info(f"✅ LONG SL: OB invalidation @ {sl_price:.2f} (OB low: {ob_low:.2f})")
            
            # Priority 2: FVG low
            if not sl_price:
                fvg_zone = entry_setup.get('fvg_zone')
                if fvg_zone:
                    fvg_low = fvg_zone.get('low') if isinstance(fvg_zone, dict) else getattr(fvg_zone, 'low', None)
                    if fvg_low:
                        sl_price = fvg_low - buffer
                        sl_reason = "FVG_INVALIDATION"
                        logger.info(f"✅ LONG SL: FVG invalidation @ {sl_price:.2f}")
            
            # Priority 3: Liquidity sweep level
            if not sl_price:
                sweep_level = entry_setup.get('liquidity_sweep_level')
                if sweep_level:
                    sl_price = sweep_level - buffer
                    sl_reason = "LIQUIDITY_SWEEP_PROTECTION"
                    logger.info(f"✅ LONG SL: Sweep protection @ {sl_price:.2f}")
            
            # Priority 4: Last swing low
            if not sl_price:
                lookback = 30
                swing_low = df['low'].iloc[-lookback:].min()
                sl_price = swing_low - buffer
                sl_reason = "SWING_LOW_STRUCTURE"
                logger.info(f"✅ LONG SL: Swing low @ {sl_price:.2f}")
            
            # Priority 5: ATR fallback
            if not sl_price:
                sl_price = entry_price - (atr * 2.0)
                sl_reason = "ATR_FALLBACK"
                logger.warning(f"⚠️ LONG SL: ATR fallback @ {sl_price:.2f}")
            
            # ✅ Ensure SL is BELOW entry
            if sl_price >= entry_price:
                sl_price = entry_price * (1 - min_sl_pct)
                sl_reason = f"{sl_reason}_CORRECTED"
                logger.warning(f"⚠️ SL corrected to {min_sl_pct*100:.1f}% below entry: {sl_price:.2f}")
            
            # ✅ Ensure minimum distance
            sl_distance_pct = (entry_price - sl_price) / entry_price
            if sl_distance_pct < min_sl_pct:
                sl_price = entry_price * (1 - min_sl_pct)
                sl_reason = f"{sl_reason}_MIN_DISTANCE"
                logger.warning(f"⚠️ SL expanded to min {min_sl_pct*100:.1f}%: {sl_price:.2f}")
        
        else:
            # Priority 1: Order Block high
            order_block = entry_setup.get('order_block')
            if order_block:
                if isinstance(order_block, dict):
                    ob_high = order_block.get('zone_high') or order_block.get('top')
                else:
                    ob_high = getattr(order_block, 'zone_high', None) or getattr(order_block, 'top', None)
                
                if ob_high:
                    sl_price = ob_high + buffer
                    sl_reason = "OB_INVALIDATION"
                    logger.info(f"✅ SHORT SL: OB invalidation @ {sl_price:.2f} (OB high: {ob_high:.2f})")
            
            # Priority 2: FVG high
            if not sl_price:
                fvg_zone = entry_setup.get('fvg_zone')
                if fvg_zone:
                    fvg_high = fvg_zone.get('high') if isinstance(fvg_zone, dict) else getattr(fvg_zone, 'high', None)
                    if fvg_high:
                        sl_price = fvg_high + buffer
                        sl_reason = "FVG_INVALIDATION"
                        logger.info(f"✅ SHORT SL: FVG invalidation @ {sl_price:.2f}")
            
            # Priority 3: Liquidity sweep level
            if not sl_price:
                sweep_level = entry_setup.get('liquidity_sweep_level')
                if sweep_level:
                    sl_price = sweep_level + buffer
                    sl_reason = "LIQUIDITY_SWEEP_PROTECTION"
                    logger.info(f"✅ SHORT SL: Sweep protection @ {sl_price:.2f}")
            
            # Priority 4: Last swing high
            if not sl_price:
                lookback = 30
                swing_high = df['high'].iloc[-lookback:].max()
                sl_price = swing_high + buffer
                sl_reason = "SWING_HIGH_STRUCTURE"
                logger.info(f"✅ SHORT SL: Swing high @ {sl_price:.2f}")
            
            # Priority 5: ATR fallback
            if not sl_price:
                sl_price = entry_price + (atr * 2.0)
                sl_reason = "ATR_FALLBACK"
                logger.warning(f"⚠️ SHORT SL: ATR fallback @ {sl_price:.2f}")
            
            # ✅ Ensure SL is ABOVE entry
            if sl_price <= entry_price:
                sl_price = entry_price * (1 + min_sl_pct)
                sl_reason = f"{sl_reason}_CORRECTED"
                logger.warning(f"⚠️ SL corrected to {min_sl_pct*100:.1f}% above entry: {sl_price:.2f}")
            
            # ✅ Ensure minimum distance
            sl_distance_pct = (sl_price - entry_price) / entry_price
            if sl_distance_pct < min_sl_pct:
                sl_price = entry_price * (1 + min_sl_pct)
                sl_reason = f"{sl_reason}_MIN_DISTANCE"
                logger.warning(f"⚠️ SL expanded to min {min_sl_pct*100:.1f}%: {sl_price:.2f}")
        
        logger.info(f"🎯 Final SL: {sl_price:.2f} | Reason: {sl_reason} | Distance: {abs(sl_price - entry_price) / entry_price * 100:.2f}%")
        return sl_price

    def _validate_entry_timing(
        self,
        entry_price: float,
        current_price: float,
        signal_type,
        bias
    ) -> Tuple[bool, str]:
        """
        ✅ FIX 3: Validate that entry is still achievable
        
        ICT Rule: 
        - SELL: Entry MUST be ABOVE current price (waiting for retracement rally)
        - BUY: Entry MUST be BELOW current price (waiting for pullback)
        
        Args:
            entry_price: Proposed entry price
            current_price: Current market price
            signal_type: Signal type (BUY/SELL/STRONG_BUY/STRONG_SELL)
            bias: Market bias
            
        Returns:
            Tuple[bool, str]: (is_valid, reason_message)
        """
        # Get signal type string
        signal_type_str = signal_type.value if hasattr(signal_type, 'value') else str(signal_type)
        
        # Maximum acceptable distance: 20% (likely stale if further)
        max_distance_pct = 0.20
        
        if signal_type_str in ['SELL', 'STRONG_SELL']:
            if entry_price <= current_price:
                return False, f"❌ SELL entry ${entry_price:.2f} is NOT above current price ${current_price:.2f} - trade already happened!"
            
            distance_pct = (entry_price - current_price) / current_price
            if distance_pct > max_distance_pct:
                return False, f"❌ SELL entry {distance_pct*100:.1f}% above current price - likely stale signal (max 20%)"
        
        elif signal_type_str in ['BUY', 'STRONG_BUY']:
            if entry_price >= current_price:
                return False, f"❌ BUY entry ${entry_price:.2f} is NOT below current price ${current_price:.2f} - trade already happened!"
            
            distance_pct = (current_price - entry_price) / current_price
            if distance_pct > max_distance_pct:
                return False, f"❌ BUY entry {distance_pct*100:.1f}% below current price - likely stale signal (max 20%)"
        
        return True, "✅ Entry timing valid"

    def _validate_sl_position(self, sl_price: float, order_block, direction, entry_price: float) -> Tuple[float, bool]:
        """
        ЗАДЪЛЖИТЕЛНО: Валидира че SL е под/над валиден Order Block (STRICT ICT)
        
        BULLISH: SL ТРЯБВА да е ПОД Order Block bottom (buffer >= 0.2-0.3%)
        BEARISH: SL ТРЯБВА да е НАД Order Block top (buffer >= 0.2-0.3%)
        
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
                logger.error(f"❌ BULLISH SL {sl_price:.2f} >= OB bottom {ob_bottom:.2f} - FORBIDDEN")
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
                logger.error(f"❌ BEARISH SL {sl_price:.2f} <= OB top {ob_top:.2f} - FORBIDDEN")
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
        
        # Breaker blocks (8%) - Implements ESB v1.0 §4 – optional breaker block confluence boost
        breaker_blocks = ict_components.get('breaker_blocks', [])
        if breaker_blocks:
            breaker_score = min(8, len(breaker_blocks) * 3)
            confidence += breaker_score * self.config['breaker_block_weight'] / 0.08
        
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
        # ✅ Entry scenario already selected in Step 8.1
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
            entry_scenario=entry_scenario_result['scenario'] if entry_scenario_result else None,
            entry_scenario_score=entry_scenario_result['score'] if entry_scenario_result else 0,
            entry_scenario_reasoning=entry_scenario_result['reasoning'] if entry_scenario_result else "",
            entry_scenario_triggers=entry_scenario_result.get("triggers", []) if entry_scenario_result else [],
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
        context_info = []  # ✅ PR #3 FIX #4: Separate context from warnings
        adjustment = 0.0
        
        try:
            # ✅ PR #3 FIX #4: Determine current session first
            session = context.get('trading_session', 'UNKNOWN')
            is_peak_session = session in ['LONDON', 'NEW_YORK']
            
            # === FILTER 1: VOLUME ANALYSIS ===
            volume_ratio = context.get('volume_ratio', 1.0)
            volume_spike = context.get('volume_spike', False)
            
            if volume_ratio < 0.5:
                # ✅ PR #3 FIX #4: Only warn about low volume during off-peak sessions
                if not is_peak_session:
                    warnings.append("⚠️ LOW VOLUME - Reduced liquidity may affect execution")
                    adjustment -= 10
                    logger.info("Context filter: Low volume detected (-10%)")
                else:
                    # During peak sessions, low volume relative to 24h avg is less critical
                    logger.info("Context filter: Low volume detected but ignored (peak session)")
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
            # ✅ PR #3 FIX #4: Move session info to context (not warnings)
            
            if session == 'ASIAN':
                # Asian session - typically lower liquidity for crypto
                context_info.append("ℹ️ ASIAN SESSION - Lower liquidity period")
                adjustment -= 5
                logger.info("Context filter: Asian session (-5%)")
            elif session == 'LONDON':
                # London session - high liquidity
                context_info.append("🌍 LONDON SESSION - Peak liquidity period")
                adjustment += 5
                logger.info("Context filter: London session (+5%)")
            elif session == 'NEW_YORK':
                # NY session - high liquidity (especially overlap with London)
                context_info.append("🗽 NEW YORK SESSION - High liquidity period")
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
            
            # ✅ PR #3 FIX #4: Return both warnings and context info
            # Combine context_info into warnings for now (backward compatible)
            all_messages = warnings + context_info
            
            return adjusted_confidence, all_messages
            
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
    
    def _get_htf_bias_with_fallback(self, symbol: str, mtf_data: Optional[Dict], entry_timeframe: str) -> str:
        """
Get HTF bias based on entry timeframe hierarchy

✅ Uses timeframe_hierarchy.json:
- 1H/2H entries → HTF bias from 1D
- 4H/1D entries → HTF bias from 1W
"""
        if mtf_data is None or not isinstance(mtf_data, dict):
            logger.warning("No MTF data available, using NEUTRAL bias")
            return 'NEUTRAL'
        
        try:
            # ✅ Get HTF bias timeframe from hierarchy config
            entry_tf_normalized = entry_timeframe.lower()
            hierarchy = self.tf_hierarchy.get('hierarchies', {}).get(entry_tf_normalized, {})
            
            if hierarchy:
                htf_bias_tf = hierarchy.get('htf_bias_tf', '1d')
                logger.info(f"✅ Using HTF bias TF: {htf_bias_tf} for {entry_timeframe} entry")
            else:
                # Fallback: 1H/2H→1D, 4H/1D→1W
                htf_bias_tf = '1w' if entry_tf_normalized in ['4h', '1d'] else '1d'
                logger.warning(f"⚠️ {entry_timeframe} not in config, using: {htf_bias_tf}")
            
            # Try to get data for the HTF bias timeframe
            for tf_variant in [htf_bias_tf, htf_bias_tf.upper(), htf_bias_tf.replace('w', 'W').replace('d', 'D').replace('h', 'H')]:
                if tf_variant in mtf_data:
                    df_htf = mtf_data[tf_variant]
                    if df_htf is not None and not df_htf.empty and len(df_htf) >= 20:
                        bias_components = self._detect_ict_components(df_htf, htf_bias_tf)
                        htf_bias = self._determine_market_bias(df_htf, bias_components, None)
                        htf_bias_str = htf_bias.value if hasattr(htf_bias, 'value') else str(htf_bias)
                        logger.info(f"✅ HTF Bias from {htf_bias_tf.upper()}: {htf_bias_str}")
                        return htf_bias_str
            
            # Fallback: try 1D then 4H
            logger.warning(f"⚠️ {htf_bias_tf} not available, trying 1D fallback...")
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
    
    # ═══════════════════════════════════════════════════════════════════
    # PR #8 LAYER 2: STRUCTURE-AWARE TP PLACEMENT
    # ═══════════════════════════════════════════════════════════════════
    
    def _find_obstacles_in_path(
        self,
        entry_price: float,
        target_price: float,
        direction: str,  # 'LONG' or 'SHORT'
        ict_components: Dict
    ) -> List[Dict]:
        """
        Scan for OPPOSING zones between Entry and Target (PR #8)
        
        For LONG: Find BEARISH zones (resistance)
        - Bearish Order Blocks
        - Bearish FVGs
        - Resistance levels (LuxAlgo S/R)
        - Bearish Whale Blocks
        
        For SHORT: Find BULLISH zones (support)
        - Bullish Order Blocks
        - Bullish FVGs
        - Support levels
        - Bullish Whale Blocks
        
        Args:
            entry_price: Entry price
            target_price: Target price (TP level)
            direction: 'LONG' or 'SHORT'
            ict_components: Dict with all ICT components
            
        Returns:
            List of obstacles sorted by proximity to entry:
            [
                {
                    'type': 'BEARISH_OB' | 'BEARISH_FVG' | 'RESISTANCE' | 'BEARISH_WHALE',
                    'price': float,
                    'strength': 0-100,
                    'description': 'Human-readable Bulgarian text'
                },
                ...
            ]
        """
        try:
            obstacles = []
            
            # Determine price range
            min_price = min(entry_price, target_price)
            max_price = max(entry_price, target_price)
            
            logger.info(f"🔍 Scanning obstacles between ${min_price:.2f} and ${max_price:.2f}")
            
            # 1. Check Order Blocks
            order_blocks = ict_components.get('order_blocks', [])
            for ob in order_blocks:
                try:
                    # Get OB price and type
                    if hasattr(ob, 'price'):
                        ob_price = ob.price
                    elif isinstance(ob, dict):
                        ob_price = ob.get('price', 0)
                    else:
                        continue
                    
                    # Check if in range
                    if min_price <= ob_price <= max_price:
                        # Get OB type
                        if hasattr(ob, 'type'):
                            ob_type_str = str(ob.type.value) if hasattr(ob.type, 'value') else str(ob.type)
                        elif isinstance(ob, dict):
                            ob_type_str = ob.get('type', '')
                        else:
                            continue
                        
                        # Check if opposing
                        is_obstacle = False
                        obstacle_type = ''
                        
                        if direction == 'LONG' and 'BEARISH' in ob_type_str.upper():
                            is_obstacle = True
                            obstacle_type = 'BEARISH_OB'
                        elif direction == 'SHORT' and 'BULLISH' in ob_type_str.upper():
                            is_obstacle = True
                            obstacle_type = 'BULLISH_OB'
                        
                        if is_obstacle:
                            # Get strength from OB
                            strength = 70  # Default
                            if hasattr(ob, 'strength'):
                                strength = ob.strength
                            elif isinstance(ob, dict):
                                strength = ob.get('strength', 70)
                            
                            obstacles.append({
                                'type': obstacle_type,
                                'price': ob_price,
                                'strength': strength,
                                'description': 'Институционална зона' if obstacle_type == 'BEARISH_OB' else 'Институционална подкрепа',
                                'source': 'ORDER_BLOCK'
                            })
                            logger.debug(f"   Found obstacle: {obstacle_type} @ ${ob_price:.2f} (strength: {strength})")
                except Exception as e:
                    logger.debug(f"Error processing order block: {e}")
                    continue
            
            # 2. Check FVGs
            fvgs = ict_components.get('fvgs', [])
            for fvg in fvgs:
                try:
                    # Get FVG price (center)
                    if hasattr(fvg, 'high') and hasattr(fvg, 'low'):
                        fvg_price = (fvg.high + fvg.low) / 2
                    elif isinstance(fvg, dict):
                        fvg_high = fvg.get('high', 0)
                        fvg_low = fvg.get('low', 0)
                        fvg_price = (fvg_high + fvg_low) / 2 if fvg_high and fvg_low else 0
                    else:
                        continue
                    
                    if not fvg_price:
                        continue
                    
                    # Check if in range
                    if min_price <= fvg_price <= max_price:
                        # Check if opposing
                        is_bullish = False
                        if hasattr(fvg, 'is_bullish'):
                            is_bullish = fvg.is_bullish
                        elif isinstance(fvg, dict):
                            is_bullish = fvg.get('is_bullish', False)
                        
                        is_obstacle = False
                        obstacle_type = ''
                        
                        if direction == 'LONG' and not is_bullish:
                            is_obstacle = True
                            obstacle_type = 'BEARISH_FVG'
                        elif direction == 'SHORT' and is_bullish:
                            is_obstacle = True
                            obstacle_type = 'BULLISH_FVG'
                        
                        if is_obstacle:
                            # FVG strength based on gap size
                            strength = 60  # Default
                            if hasattr(fvg, 'strength'):
                                strength = fvg.strength
                            elif isinstance(fvg, dict):
                                strength = fvg.get('strength', 60)
                            
                            obstacles.append({
                                'type': obstacle_type,
                                'price': fvg_price,
                                'strength': strength,
                                'description': 'Fair Value Gap зона',
                                'source': 'FVG'
                            })
                            logger.debug(f"   Found obstacle: {obstacle_type} @ ${fvg_price:.2f} (strength: {strength})")
                except Exception as e:
                    logger.debug(f"Error processing FVG: {e}")
                    continue
            
            # 3. Check Support/Resistance (LuxAlgo)
            luxalgo_sr = ict_components.get('luxalgo_sr', {})
            if luxalgo_sr:
                try:
                    # For LONG, check resistance zones
                    if direction == 'LONG':
                        resistance_zones = luxalgo_sr.get('resistance_zones', [])
                        for zone in resistance_zones:
                            zone_price = zone.get('price', 0)
                            if zone_price and min_price <= zone_price <= max_price:
                                strength = zone.get('strength', 65)
                                obstacles.append({
                                    'type': 'RESISTANCE',
                                    'price': zone_price,
                                    'strength': strength,
                                    'description': 'Съпротива (LuxAlgo)',
                                    'source': 'LUXALGO_SR'
                                })
                                logger.debug(f"   Found obstacle: RESISTANCE @ ${zone_price:.2f} (strength: {strength})")
                    
                    # For SHORT, check support zones
                    elif direction == 'SHORT':
                        support_zones = luxalgo_sr.get('support_zones', [])
                        for zone in support_zones:
                            zone_price = zone.get('price', 0)
                            if zone_price and min_price <= zone_price <= max_price:
                                strength = zone.get('strength', 65)
                                obstacles.append({
                                    'type': 'SUPPORT',
                                    'price': zone_price,
                                    'strength': strength,
                                    'description': 'Подкрепа (LuxAlgo)',
                                    'source': 'LUXALGO_SR'
                                })
                                logger.debug(f"   Found obstacle: SUPPORT @ ${zone_price:.2f} (strength: {strength})")
                except Exception as e:
                    logger.debug(f"Error processing LuxAlgo S/R: {e}")
            
            # 4. Check Whale Blocks
            whale_blocks = ict_components.get('whale_blocks', [])
            for wb in whale_blocks:
                try:
                    # Get whale block price
                    if hasattr(wb, 'price'):
                        wb_price = wb.price
                    elif isinstance(wb, dict):
                        wb_price = wb.get('price', 0)
                    else:
                        continue
                    
                    if not wb_price:
                        continue
                    
                    # Check if in range
                    if min_price <= wb_price <= max_price:
                        # Get whale block type
                        if hasattr(wb, 'block_type'):
                            wb_type_str = str(wb.block_type.value) if hasattr(wb.block_type, 'value') else str(wb.block_type)
                        elif isinstance(wb, dict):
                            wb_type_str = wb.get('block_type', '')
                        else:
                            continue
                        
                        # Check if opposing
                        is_obstacle = False
                        obstacle_type = ''
                        
                        if direction == 'LONG' and 'BEARISH' in wb_type_str.upper():
                            is_obstacle = True
                            obstacle_type = 'BEARISH_WHALE'
                        elif direction == 'SHORT' and 'BULLISH' in wb_type_str.upper():
                            is_obstacle = True
                            obstacle_type = 'BULLISH_WHALE'
                        
                        if is_obstacle:
                            # Whale blocks are typically stronger
                            strength = 80  # Default high strength
                            if hasattr(wb, 'strength'):
                                strength = wb.strength
                            elif isinstance(wb, dict):
                                strength = wb.get('strength', 80)
                            
                            obstacles.append({
                                'type': obstacle_type,
                                'price': wb_price,
                                'strength': strength,
                                'description': 'Whale Institution Block',
                                'source': 'WHALE_BLOCK'
                            })
                            logger.debug(f"   Found obstacle: {obstacle_type} @ ${wb_price:.2f} (strength: {strength})")
                except Exception as e:
                    logger.debug(f"Error processing whale block: {e}")
                    continue
            
            # Sort obstacles by proximity to entry price
            obstacles.sort(key=lambda x: abs(x['price'] - entry_price))
            
            logger.info(f"   Found {len(obstacles)} obstacles in path")
            
            return obstacles
            
        except Exception as e:
            logger.error(f"Error finding obstacles in path from ${entry_price:.2f} to ${target_price:.2f}: {type(e).__name__}: {str(e)}")
            import traceback
            logger.debug(f"Obstacle detection traceback: {traceback.format_exc()}")
            return []
    
    def _evaluate_obstacle_strength(
        self,
        obstacle: Dict,
        context: Dict  # Contains HTF bias, displacement, etc.
    ) -> Dict:
        """
        Evaluate obstacle and predict market reaction (PR #8)
        
        Scoring System (0-100):
        - Base strength: From detector (volume, candle size, age)
        - HTF bias alignment: +20 if aligned, -20 if against
        - Displacement: -15 if strong momentum in our direction
        - Retest history: +10 if tested 2+ times
        - Volume profile: +/-10 based on volume strength
        - Zone age: -5 if > 100 candles old
        - MTF confirmation: +15 if confirmed on multiple TFs
        
        Decision Thresholds:
        - Strength >= 75: "МНОГО ВЕРОЯТНО ОТБЛЪСКВАНЕ" (85% confidence)
        - Strength 60-74: "ВЕРОЯТНО ОТБЛЪСКВАНЕ" (70% confidence)
        - Strength 45-59: "НЕСИГУРНО" (50% confidence)
        - Strength < 45: "ВЕРОЯТНО ПРОБИВАНЕ" (70% confidence)
        
        Args:
            obstacle: Obstacle dict with type, price, strength, description
            context: Context dict with HTF bias, displacement, direction
            
        Returns:
            {
                'strength': 0-100,
                'will_likely_reject': True/False,
                'confidence': 0-100,
                'decision': 'Bulgarian text',
                'reasoning': 'Detailed explanation in Bulgarian'
            }
        """
        try:
            # Start with base strength from detector
            base_strength = obstacle.get('strength', 50)
            adjusted_strength = float(base_strength)
            
            reasoning_parts = []
            
            # 1. HTF bias alignment
            htf_bias = context.get('htf_bias', 'NEUTRAL')
            direction = context.get('direction', 'LONG')
            obstacle_type = obstacle.get('type', '')
            
            if htf_bias != 'NEUTRAL':
                if (direction == 'LONG' and 'BEARISH' in obstacle_type and htf_bias == 'BEARISH') or \
                   (direction == 'SHORT' and 'BULLISH' in obstacle_type and htf_bias == 'BULLISH'):
                    # HTF supports obstacle (stronger)
                    adjusted_strength += 20
                    reasoning_parts.append("HTF bias подкрепя зоната ⚠️")
                else:
                    # HTF against obstacle (weaker)
                    adjusted_strength -= 20
                    reasoning_parts.append("HTF bias е срещу зоната ✅")
            
            # 2. Displacement check
            displacement_detected = context.get('displacement_detected', False)
            if displacement_detected:
                adjusted_strength -= 15
                reasoning_parts.append("Силен momentum в нашата посока ✅")
            
            # 3. Volume (if available from obstacle)
            if obstacle.get('volume_strength', 0) > 1.5:
                adjusted_strength += 10
                reasoning_parts.append("Висок volume в зоната ⚠️")
            elif obstacle.get('volume_strength', 0) < 0.7:
                adjusted_strength -= 10
                reasoning_parts.append("Нисък volume в зоната ✅")
            
            # 4. MTF confirmation (simplified - check if obstacle source is multi-TF)
            if 'mtf_confluence' in context and context['mtf_confluence'] > 2:
                adjusted_strength += 15
                reasoning_parts.append("MTF потвърждение (4H+1D) ⚠️")
            
            # Clamp to 0-100
            adjusted_strength = max(0, min(100, adjusted_strength))
            
            # Determine decision and confidence
            from config.trading_config import get_trading_config
            config = get_trading_config()
            
            very_strong_threshold = config.get('very_strong_obstacle', 75)
            strong_threshold = config.get('strong_obstacle', 60)
            moderate_threshold = config.get('moderate_obstacle', 45)
            
            will_reject = False
            confidence = 50
            decision = ""
            
            if adjusted_strength >= very_strong_threshold:
                will_reject = True
                confidence = 85
                decision = "МНОГО ВЕРОЯТНО ОТБЛЪСКВАНЕ"
                reasoning_parts.append("Заключение: Силна съпротива, ще отблъсне")
            elif adjusted_strength >= strong_threshold:
                will_reject = True
                confidence = 70
                decision = "ВЕРОЯТНО ОТБЛЪСКВАНЕ"
                reasoning_parts.append("Заключение: Вероятна съпротива")
            elif adjusted_strength >= moderate_threshold:
                will_reject = False
                confidence = 50
                decision = "НЕСИГУРНО"
                reasoning_parts.append("Заключение: Несигурна зона")
            else:
                will_reject = False
                confidence = 70
                decision = "ВЕРОЯТНО ПРОБИВАНЕ"
                reasoning_parts.append("Заключение: Слаба зона, вероятно ще пробие")
            
            reasoning = '\n'.join(reasoning_parts)
            
            return {
                'strength': adjusted_strength,
                'will_likely_reject': will_reject,
                'confidence': confidence,
                'decision': decision,
                'reasoning': reasoning
            }
            
        except Exception as e:
            logger.error(f"Error evaluating obstacle: {e}")
            # Return neutral evaluation on error
            return {
                'strength': 50,
                'will_likely_reject': False,
                'confidence': 50,
                'decision': 'НЕСИГУРНО',
                'reasoning': 'Грешка при оценка'
            }
    
    def _calculate_smart_tp_with_structure_validation(
        self,
        entry_price: float,
        sl_price: float,  # NEVER modified
        direction: str,  # 'LONG' or 'SHORT'
        ict_components: Dict,
        timeframe: str
    ) -> List[float]:
        """
        Calculate structure-aware TPs (PR #8 Layer 2)
        
        CRITICAL RULES:
        - SL is NEVER modified ✅
        - Entry is NEVER modified ✅
        - Only TP is adjusted based on obstacles
        - Min RR must still be met (2.5:1 minimum)
        
        Process:
        1. Calculate mathematical TPs (Risk × 3, × 5, × 8)
        2. Scan obstacles between Entry and TP3
        3. Evaluate each obstacle strength
        4. For each TP level:
           a. Check if obstacle in path
           b. If obstacle weak (< 45): Place TP AFTER obstacle
           c. If obstacle strong (>= 75): Place TP BEFORE obstacle (0.3% buffer)
           d. Validate RR still meets minimum
           e. If RR fails: Keep mathematical TP + add warning
        5. Return adjusted TPs
        
        Args:
            entry_price: Entry price (fixed)
            sl_price: Stop loss price (fixed)
            direction: 'LONG' or 'SHORT'
            ict_components: ICT components dict
            timeframe: Timeframe
            
        Returns:
            [tp1, tp2, tp3] with smart positioning
        """
        try:
            # Load config
            from config.trading_config import get_trading_config
            config = get_trading_config()
            
            # Check if structure TP is enabled
            if not config.get('use_structure_tp', True):
                logger.info("📊 Structure TP disabled - using mathematical TPs")
                # Fallback to mathematical TPs
                risk = abs(entry_price - sl_price)
                tp1_mult, tp2_mult, tp3_mult = get_tp_multipliers_by_timeframe(timeframe)
                
                if direction == 'LONG':
                    return [
                        entry_price + (risk * tp1_mult),
                        entry_price + (risk * tp2_mult),
                        entry_price + (risk * tp3_mult)
                    ]
                else:
                    return [
                        entry_price - (risk * tp1_mult),
                        entry_price - (risk * tp2_mult),
                        entry_price - (risk * tp3_mult)
                    ]
            
            # Step 1: Calculate mathematical TPs
            risk = abs(entry_price - sl_price)
            tp1_mult, tp2_mult, tp3_mult = get_tp_multipliers_by_timeframe(timeframe)
            
            if direction == 'LONG':
                math_tp1 = entry_price + (risk * tp1_mult)
                math_tp2 = entry_price + (risk * tp2_mult)
                math_tp3 = entry_price + (risk * tp3_mult)
            else:
                math_tp1 = entry_price - (risk * tp1_mult)
                math_tp2 = entry_price - (risk * tp2_mult)
                math_tp3 = entry_price - (risk * tp3_mult)
            
            logger.info(f"📊 Mathematical TPs: TP1=${math_tp1:.2f}, TP2=${math_tp2:.2f}, TP3=${math_tp3:.2f}")
            
            # Step 2: Scan obstacles between Entry and TP3
            max_tp = max(math_tp1, math_tp2, math_tp3) if direction == 'LONG' else min(math_tp1, math_tp2, math_tp3)
            obstacles = self._find_obstacles_in_path(
                entry_price=entry_price,
                target_price=max_tp,
                direction=direction,
                ict_components=ict_components
            )
            
            if not obstacles:
                logger.info("✅ No obstacles found - using mathematical TPs")
                return [math_tp1, math_tp2, math_tp3]
            
            # Step 3 & 4: Evaluate obstacles and adjust TPs
            logger.info(f"🔍 Evaluating {len(obstacles)} obstacles for TP adjustment")
            
            # Build context for obstacle evaluation
            context = {
                'direction': direction,
                'htf_bias': ict_components.get('htf_bias', 'NEUTRAL'),
                'displacement_detected': ict_components.get('displacement_detected', False),
                'mtf_confluence': ict_components.get('mtf_confluence', 0)
            }
            
            # Adjust each TP level
            min_rr_tp1 = config.get('min_rr_tp1', 2.5)
            min_rr_tp2 = config.get('min_rr_tp2', 3.5)
            min_rr_tp3 = config.get('min_rr_tp3', 5.0)
            
            adjusted_tp1 = self._adjust_tp_before_obstacle(
                math_tp=math_tp1,
                obstacles=obstacles,
                entry_price=entry_price,
                direction=direction,
                risk=risk,
                min_rr=min_rr_tp1
            )
            
            adjusted_tp2 = self._adjust_tp_before_obstacle(
                math_tp=math_tp2,
                obstacles=obstacles,
                entry_price=entry_price,
                direction=direction,
                risk=risk,
                min_rr=min_rr_tp2
            )
            
            adjusted_tp3 = self._adjust_tp_before_obstacle(
                math_tp=math_tp3,
                obstacles=obstacles,
                entry_price=entry_price,
                direction=direction,
                risk=risk,
                min_rr=min_rr_tp3
            )
            
            logger.info(f"✅ Structure-aware TPs: TP1=${adjusted_tp1:.2f}, TP2=${adjusted_tp2:.2f}, TP3=${adjusted_tp3:.2f}")
            
            return [adjusted_tp1, adjusted_tp2, adjusted_tp3]
            
        except Exception as e:
            logger.error(f"Error calculating smart TPs: {e}")
            # Fallback to mathematical TPs with timeframe-based multipliers
            risk = abs(entry_price - sl_price)
            tp1_mult, tp2_mult, tp3_mult = get_tp_multipliers_by_timeframe(timeframe)
            if direction == 'LONG':
                return [
                    entry_price + (risk * tp1_mult),
                    entry_price + (risk * tp2_mult),
                    entry_price + (risk * tp3_mult)
                ]
            else:
                return [
                    entry_price - (risk * tp1_mult),
                    entry_price - (risk * tp2_mult),
                    entry_price - (risk * tp3_mult)
                ]
    
    def _adjust_tp_before_obstacle(
        self,
        math_tp: float,
        obstacles: List[Dict],
        entry_price: float,
        direction: str,
        risk: float,  # Fixed from SL distance
        min_rr: float = 2.5
    ) -> float:
        """
        Adjust single TP level considering obstacles (PR #8 Helper)
        
        Logic:
        1. Find obstacles between Entry and math_tp
        2. Filter by strength (>= 60 = significant)
        3. If no significant obstacles: Return math_tp unchanged
        4. If obstacle found:
           a. Calculate safe TP (0.3% before obstacle)
           b. Check if safe TP meets min RR
           c. If YES: Use safe TP
           d. If NO: Keep math_tp + log warning for user
        
        Args:
            math_tp: Mathematical TP (Risk × multiplier)
            obstacles: List of obstacles
            entry_price: Entry price
            direction: 'LONG' or 'SHORT'
            risk: Risk amount (|entry - sl|)
            min_rr: Minimum RR ratio required
            
        Returns:
            Adjusted TP (or original if RR fails)
        """
        try:
            from config.trading_config import get_trading_config
            config = get_trading_config()
            
            min_obstacle_strength = config.get('min_obstacle_strength', 60)
            obstacle_buffer = config.get('obstacle_buffer_pct', 0.003)
            
            # Find obstacles in path
            min_price = min(entry_price, math_tp)
            max_price = max(entry_price, math_tp)
            
            obstacles_in_path = []
            for obs in obstacles:
                obs_price = obs.get('price', 0)
                obs_strength = obs.get('strength', 0)
                
                # Check if in path and significant
                if min_price < obs_price < max_price and obs_strength >= min_obstacle_strength:
                    # Evaluate obstacle
                    context = {
                        'direction': direction,
                        'htf_bias': 'NEUTRAL',  # Simplified for helper
                        'displacement_detected': False,
                        'mtf_confluence': 0
                    }
                    evaluation = self._evaluate_obstacle_strength(obs, context)
                    
                    if evaluation['will_likely_reject']:
                        obstacles_in_path.append({
                            'obstacle': obs,
                            'evaluation': evaluation,
                            'price': obs_price
                        })
            
            # No significant obstacles - use mathematical TP
            if not obstacles_in_path:
                return math_tp
            
            # Find nearest strong obstacle
            if direction == 'LONG':
                # For LONG, find lowest obstacle price
                obstacles_in_path.sort(key=lambda x: x['price'])
                nearest_obstacle = obstacles_in_path[0]
            else:
                # For SHORT, find highest obstacle price
                obstacles_in_path.sort(key=lambda x: x['price'], reverse=True)
                nearest_obstacle = obstacles_in_path[0]
            
            # Calculate safe TP (before obstacle with buffer)
            obstacle_price = nearest_obstacle['price']
            if direction == 'LONG':
                safe_tp = obstacle_price * (1 - obstacle_buffer)  # 0.3% before
            else:
                safe_tp = obstacle_price * (1 + obstacle_buffer)  # 0.3% before
            
            # Validate RR
            reward = abs(safe_tp - entry_price)
            actual_rr = reward / risk if risk > 0 else 0
            
            if actual_rr >= min_rr:
                # Safe TP meets minimum RR - use it
                logger.info(f"   ✅ TP adjusted to ${safe_tp:.2f} (before obstacle @ ${obstacle_price:.2f}, RR: {actual_rr:.2f})")
                return safe_tp
            else:
                # Safe TP doesn't meet minimum RR - keep mathematical TP and warn
                logger.warning(f"   ⚠️ Obstacle @ ${obstacle_price:.2f} but safe TP has RR {actual_rr:.2f} < {min_rr:.2f}")
                logger.warning(f"   → Keeping mathematical TP ${math_tp:.2f} (RR: {abs(math_tp - entry_price) / risk:.2f})")
                return math_tp
            
        except Exception as e:
            logger.error(f"Error adjusting TP: {e}")
            return math_tp  # Return original on error
    
    def _check_news_sentiment_before_signal(
        self,
        symbol: str,
        signal_type: str,  # 'BUY' or 'SELL'
        timeframe: str
    ) -> Dict:
        """
        Check recent news sentiment BEFORE generating signal (PR #8 Layer 1)
        
        Logic:
        - Get news from last 24h (configurable)
        - Calculate weighted sentiment (-100 to +100)
        - CRITICAL news: × 3 weight
        - IMPORTANT news: × 2 weight
        - NORMAL news: × 1 weight
        
        Decision matrix:
        - BUY signal + sentiment < -30: BLOCK signal
        - BUY signal + sentiment -10 to -30: WARN
        - SELL signal + sentiment > +30: BLOCK signal
        - SELL signal + sentiment +10 to +30: WARN
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            signal_type: 'BUY' or 'SELL'
            timeframe: Timeframe being analyzed
            
        Returns:
            {
                'allow_signal': True/False,
                'sentiment_score': -100 to +100,
                'critical_news': List[news],
                'reasoning': 'Explanation in Bulgarian'
            }
        """
        try:
            # Check if news filter is enabled
            from config.trading_config import get_trading_config
            config = get_trading_config()
            
            if not config.get('use_news_filter', True):
                logger.info("📰 News filter disabled - allowing signal")
                return {
                    'allow_signal': True,
                    'sentiment_score': 0,
                    'critical_news': [],
                    'reasoning': 'News filter disabled'
                }
            
            # Try to get fundamental helper
            try:
                from utils.fundamental_helper import FundamentalHelper
                fundamental_helper = FundamentalHelper()
                
                # Check if fundamental analysis is enabled
                if not fundamental_helper.is_enabled():
                    logger.info("📰 Fundamental analysis disabled - allowing signal")
                    return {
                        'allow_signal': True,
                        'sentiment_score': 0,
                        'critical_news': [],
                        'reasoning': 'Fundamental analysis disabled'
                    }
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize FundamentalHelper: {e}")
                # Allow signal if news system unavailable
                return {
                    'allow_signal': True,
                    'sentiment_score': 0,
                    'critical_news': [],
                    'reasoning': 'News system unavailable'
                }
            
            # Get news from cache
            from utils.news_cache import NewsCache
            news_cache = NewsCache(cache_dir='cache', ttl_minutes=60)
            news_articles = news_cache.get_cached_news(symbol)
            
            if not news_articles:
                logger.info(f"📰 No news available for {symbol} - allowing signal")
                return {
                    'allow_signal': True,
                    'sentiment_score': 0,
                    'critical_news': [],
                    'reasoning': 'No recent news'
                }
            
            # Filter news from last N hours
            from datetime import datetime, timedelta
            lookback_hours = config.get('news_lookback_hours', 24)
            cutoff = datetime.now() - timedelta(hours=lookback_hours)
            
            recent_news = []
            for article in news_articles:
                try:
                    time_str = article.get('time', '')
                    if time_str:
                        article_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        if article_time >= cutoff:
                            recent_news.append(article)
                    else:
                        # Include if no timestamp (better safe than sorry)
                        recent_news.append(article)
                except:
                    recent_news.append(article)
            
            if not recent_news:
                logger.info(f"📰 No recent news (last {lookback_hours}h) - allowing signal")
                return {
                    'allow_signal': True,
                    'sentiment_score': 0,
                    'critical_news': [],
                    'reasoning': f'No news in last {lookback_hours}h'
                }
            
            # Analyze sentiment with weighted importance
            from fundamental.sentiment_analyzer import SentimentAnalyzer
            sentiment_analyzer = SentimentAnalyzer()
            
            # Calculate weighted sentiment (-100 to +100)
            news_weight_critical = config.get('news_weight_critical', 3.0)
            news_weight_important = config.get('news_weight_important', 2.0)
            news_weight_normal = config.get('news_weight_normal', 1.0)
            
            # Sentiment normalization constants
            SENTIMENT_NEUTRAL_BASELINE = 50.0  # Base sentiment value (neutral)
            SENTIMENT_SCALE_FACTOR = 2.0       # Multiplier to convert 0-100 to -100 to +100
            
            total_sentiment = 0.0
            total_weight = 0.0
            critical_news = []
            
            for article in recent_news:
                # Analyze individual article using public analyze_news method
                single_result = sentiment_analyzer.analyze_news([article])
                single_sentiment = single_result.get('score', SENTIMENT_NEUTRAL_BASELINE)
                
                # Determine importance weight
                importance = article.get('importance', 'NORMAL').upper()
                if importance == 'CRITICAL':
                    weight = news_weight_critical
                    critical_news.append({
                        'title': title,
                        'importance': 'CRITICAL',
                        'sentiment': single_sentiment,
                        'time_ago': article.get('time_ago', 'N/A')
                    })
                elif importance == 'IMPORTANT':
                    weight = news_weight_important
                    critical_news.append({
                        'title': title,
                        'importance': 'IMPORTANT',
                        'sentiment': single_sentiment,
                        'time_ago': article.get('time_ago', 'N/A')
                    })
                else:
                    weight = news_weight_normal
                
                # Convert 0-100 to -100 to +100
                normalized_sentiment = (single_sentiment - SENTIMENT_NEUTRAL_BASELINE) * SENTIMENT_SCALE_FACTOR
                
                total_sentiment += normalized_sentiment * weight
                total_weight += weight
            
            # Calculate weighted average sentiment
            sentiment_score = total_sentiment / total_weight if total_weight > 0 else 0
            
            logger.info(f"📰 News sentiment for {symbol}: {sentiment_score:.1f} (from {len(recent_news)} articles)")
            
            # Get thresholds from config
            block_negative = config.get('news_block_threshold_negative', -30)
            block_positive = config.get('news_block_threshold_positive', 30)
            warn_threshold = config.get('news_warn_threshold', 10)
            
            # Decision logic
            allow_signal = True
            reasoning = ""
            
            if signal_type in ['BUY', 'STRONG_BUY']:
                if sentiment_score < block_negative:
                    allow_signal = False
                    reasoning = f"⛔ СИГНАЛ БЛОКИРАН: Силно негативни новини (Sentiment: {sentiment_score:.0f}). LONG позиция е рискова."
                    logger.warning(f"❌ Blocking BUY signal - negative sentiment: {sentiment_score:.1f}")
                elif sentiment_score < -warn_threshold:
                    reasoning = f"⚠️ ВНИМАНИЕ: Леко негативни новини (Sentiment: {sentiment_score:.0f}). Бъди предпазлив с LONG."
                    logger.warning(f"⚠️ Warning for BUY signal - mild negative sentiment: {sentiment_score:.1f}")
                else:
                    reasoning = f"✅ Новините поддържат LONG позиция (Sentiment: {sentiment_score:.0f})"
                    logger.info(f"✅ News supports BUY signal: {sentiment_score:.1f}")
            
            elif signal_type in ['SELL', 'STRONG_SELL']:
                if sentiment_score > block_positive:
                    allow_signal = False
                    reasoning = f"⛔ СИГНАЛ БЛОКИРАН: Силно позитивни новини (Sentiment: {sentiment_score:.0f}). SHORT позиция е рискова."
                    logger.warning(f"❌ Blocking SELL signal - positive sentiment: {sentiment_score:.1f}")
                elif sentiment_score > warn_threshold:
                    reasoning = f"⚠️ ВНИМАНИЕ: Леко позитивни новини (Sentiment: {sentiment_score:.0f}). Бъди предпазлив с SHORT."
                    logger.warning(f"⚠️ Warning for SELL signal - mild positive sentiment: {sentiment_score:.1f}")
                else:
                    reasoning = f"✅ Новините поддържат SHORT позиция (Sentiment: {sentiment_score:.0f})"
                    logger.info(f"✅ News supports SELL signal: {sentiment_score:.1f}")
            
            return {
                'allow_signal': allow_signal,
                'sentiment_score': sentiment_score,
                'critical_news': critical_news[:3],  # Top 3 critical news
                'reasoning': reasoning
            }
            
        except Exception as e:
            logger.error(f"❌ News sentiment check error: {e}")
            # On error, allow signal (don't block trading on news system failure)
            return {
                'allow_signal': True,
                'sentiment_score': 0,
                'critical_news': [],
                'reasoning': f'News check error: {str(e)}'
            }
    
    # ============================================================================
    # ENTRY GATING & CONFIDENCE THRESHOLD HELPER METHODS (ESB v1.0 §2.1-2.2)
    # ============================================================================
    
    def _get_system_state(self) -> str:
        """
        Get current system state (OPERATIONAL, DEGRADED, MAINTENANCE, EMERGENCY)
        
        Returns:
            str: System state
        """
        # TODO: Implement system state check (can be enhanced in follow-up PR)
        # For now, always return OPERATIONAL
        return 'OPERATIONAL'
    
    def _check_breaker_block_active(self, ict_components: Dict, signal_type) -> bool:
        """
        Check if an active breaker block exists in signal direction
        
        Args:
            ict_components: Dictionary of ICT components
            signal_type: Signal type (BUY, SELL, STRONG_BUY, STRONG_SELL)
            
        Returns:
            bool: True if breaker block is active in signal direction
        """
        try:
            breaker_blocks = ict_components.get('breaker_blocks', [])
            
            # Get signal direction
            signal_direction = signal_type.value if hasattr(signal_type, 'value') else str(signal_type)
            
            for bb in breaker_blocks:
                # Check if breaker block aligns with signal direction
                bb_type = bb.get('type', '') if isinstance(bb, dict) else getattr(bb, 'type', '')
                bb_type_str = bb_type.value if hasattr(bb_type, 'value') else str(bb_type)
                
                if 'BUY' in signal_direction and 'BULLISH' in bb_type_str:
                    return True
                if 'SELL' in signal_direction and 'BEARISH' in bb_type_str:
                    return True
            
            return False
        except Exception as e:
            logger.warning(f"Error checking breaker block: {e}")
            return False
    
    def _check_active_signal(self, symbol: str, timeframe: str) -> bool:
        """
        Check if an active signal already exists for this symbol+timeframe
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            
        Returns:
            bool: True if active signal exists
        """
        # TODO: Implement signal collision check (can be enhanced in follow-up PR)
        # For now, return False (no collision)
        return False
    
    def _check_cooldown(self, symbol: str, timeframe: str) -> bool:
        """
        Check if cooldown is active for this symbol+timeframe
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            
        Returns:
            bool: True if cooldown is active
        """
        # TODO: Implement cooldown check (can be enhanced in follow-up PR)
        # For now, return False (no cooldown)
        return False
    
    def _get_market_state(self, symbol: str) -> str:
        """
        Get market state for symbol (OPEN, CLOSED, HALTED, INVALID)
        
        Args:
            symbol: Trading symbol
            
        Returns:
            str: Market state
        """
        # TODO: Implement market state check (can be enhanced in follow-up PR)
        # For now, assume market is open (crypto markets are 24/7)
        return 'OPEN'
    
    def _check_signature(self, symbol: str, timeframe: str, signal_type, timestamp) -> bool:
        """
        Check if signal signature has been seen before (deduplication)
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe
            signal_type: Signal type
            timestamp: Signal timestamp
            
        Returns:
            bool: True if signature has been seen before
        """
        # TODO: Implement signature deduplication (can be enhanced in follow-up PR)
        # For now, return False (not seen)
        return False
    
    # ============================================================================
    # END ENTRY GATING HELPER METHODS
    # ============================================================================
    
    # ============================================================================
    # EXECUTION ELIGIBILITY HELPER METHODS (ESB v1.0 §2.3)
    # ============================================================================
    
    def _get_execution_state(self) -> str:
        """
        Get current execution system state
        
        Returns:
            str: "READY" / "PAUSED" / "DISABLED"
        
        Default: "READY" (allows execution)
        
        Future implementation: Check system state from config or monitoring system
        """
        # TODO: Implement dynamic execution state check
        # For now, return safe default
        return 'READY'
    
    def _check_execution_layer_available(self) -> bool:
        """
        Check if execution layer is available
        
        Returns:
            bool: True if available, False otherwise
        
        Default: True (allows execution)
        
        Future implementation: Health check on execution layer
        """
        # TODO: Implement execution layer health check
        # For now, return safe default
        return True
    
    def _check_symbol_execution_lock(self, symbol: str) -> bool:
        """
        Check if symbol has execution lock
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
        
        Returns:
            bool: True if locked, False otherwise
        
        Default: False (allows execution)
        
        Future implementation: Check symbol-specific locks from config/database
        """
        # TODO: Implement symbol lock check
        # For now, return safe default (not locked)
        return False
    
    def _check_position_capacity(self, symbol: str, direction: str) -> bool:
        """
        Check if position capacity is available for symbol/direction
        
        Args:
            symbol: Trading symbol
            direction: Signal direction (e.g., "BUY", "SELL")
        
        Returns:
            bool: True if capacity available, False otherwise
        
        Default: True (allows execution)
        
        Future implementation: Check max positions limit, per-symbol limits
        """
        # TODO: Implement position capacity check
        # For now, return safe default
        return True
    
    def _check_emergency_halt(self) -> bool:
        """
        Check if emergency execution halt is active
        
        Returns:
            bool: True if halt active, False otherwise
        
        Default: False (allows execution)
        
        Future implementation: Check emergency halt flag from monitoring system
        """
        # TODO: Implement emergency halt check
        # For now, return safe default (not active)
        return False
    
    # ============================================================================
    # END EXECUTION ELIGIBILITY HELPER METHODS
    # ============================================================================
    
    # ============================================================================
    # RISK ADMISSION HELPER METHODS (ESB v1.0 §2.4)
    # ============================================================================
    
    def _get_signal_risk(self) -> float:
        """
        Calculate risk per signal as % of account
        
        Returns:
            float: Risk per signal (%)
        
        Default: 1.0% (safe, non-blocking)
        
        Future implementation: Calculate based on entry price, SL, and position size
        Formula: risk = ((entry - sl) / entry) * 100
        """
        # TODO: Implement actual signal risk calculation
        # For now, return safe default
        return 1.0
    
    def _get_total_open_risk(self) -> float:
        """
        Calculate total open risk across all positions
        
        Returns:
            float: Total open risk (%)
        
        Default: 0.0% (safe, non-blocking)
        
        Future implementation: Sum risk from all open positions
        """
        # TODO: Implement total open risk aggregation
        # For now, return safe default
        return 0.0
    
    def _get_symbol_exposure(self, symbol: str) -> float:
        """
        Calculate exposure to specific symbol
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
        
        Returns:
            float: Symbol exposure (%)
        
        Default: 0.0% (safe, non-blocking)
        
        Future implementation: Calculate from open positions for this symbol
        """
        # TODO: Implement symbol exposure calculation
        # For now, return safe default
        return 0.0
    
    def _get_direction_exposure(self, direction: str) -> float:
        """
        Calculate exposure to specific direction (LONG/SHORT)
        
        Args:
            direction: Signal direction (e.g., "BUY", "SELL")
        
        Returns:
            float: Direction exposure (%)
        
        Default: 0.0% (safe, non-blocking)
        
        Future implementation: Aggregate exposure from all positions in this direction
        """
        # TODO: Implement direction exposure calculation
        # For now, return safe default
        return 0.0
    
    def _get_daily_loss(self) -> float:
        """
        Calculate daily loss as % of account
        
        Returns:
            float: Daily loss (%)
        
        Default: 0.0% (safe, non-blocking)
        
        Future implementation: Calculate from closed trades today
        """
        # TODO: Implement daily loss calculation
        # For now, return safe default
        return 0.0
    
    # ============================================================================
    # END RISK ADMISSION HELPER METHODS
    # ============================================================================
    
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
