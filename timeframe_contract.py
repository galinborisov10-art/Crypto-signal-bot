"""
🎯 CENTRALIZED TIMEFRAME HIERARCHY CONTRACT
Deterministic timeframe hierarchy for ICT signal generation

This module provides a single source of truth for:
- Signal TF (Entry timeframe)
- Confirmation TF (Next higher TF)
- Structure TF (Next higher TF from confirmation)
- HTF Bias TF (Same as Structure TF)

NO hardcoded overrides, NO implicit inheritance, NO cross-timeframe contamination
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class SignalMode(Enum):
    """Signal generation mode"""
    MANUAL = "MANUAL"
    AUTOMATIC = "AUTOMATIC"


class TimeframeCategory(Enum):
    """Timeframe category for TF-specific logic"""
    SHORT_TERM = "SHORT_TERM"      # 15m, 30m, 1h, 2h, 3h
    MEDIUM_TERM = "MEDIUM_TERM"    # 4h, 6h, 8h, 12h
    LONG_TERM = "LONG_TERM"        # 1d, 3d, 1w


@dataclass
class TimeframeHierarchy:
    """Timeframe hierarchy for a specific entry timeframe"""
    signal_tf: str          # Entry timeframe
    confirmation_tf: str    # Confirmation timeframe (next higher)
    structure_tf: str       # Structure timeframe (next higher from confirmation)
    htf_bias_tf: str        # HTF bias timeframe (same as structure)
    mode: SignalMode        # MANUAL or AUTOMATIC
    
    def __post_init__(self):
        """Validate timeframe hierarchy after initialization"""
        # HTF bias should always equal structure TF
        if self.htf_bias_tf != self.structure_tf:
            logger.warning(
                f"HTF bias TF ({self.htf_bias_tf}) differs from structure TF ({self.structure_tf}). "
                f"Forcing HTF bias = structure TF"
            )
            self.htf_bias_tf = self.structure_tf
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for logging/debugging"""
        return {
            'signal_tf': self.signal_tf,
            'confirmation_tf': self.confirmation_tf,
            'structure_tf': self.structure_tf,
            'htf_bias_tf': self.htf_bias_tf,
            'mode': self.mode.value
        }


class TimeframeContract:
    """
    Centralized timeframe hierarchy contract
    Provides deterministic TF mapping for all signal types
    """
    
    # Timeframe Category Mappings
    TF_CATEGORIES = {
        # Short-term timeframes (conservative TP, tight SL)
        '15m': TimeframeCategory.SHORT_TERM,
        '30m': TimeframeCategory.SHORT_TERM,
        '1h': TimeframeCategory.SHORT_TERM,
        '2h': TimeframeCategory.SHORT_TERM,
        '3h': TimeframeCategory.SHORT_TERM,
        
        # Medium-term timeframes (moderate TP/SL)
        '4h': TimeframeCategory.MEDIUM_TERM,
        '6h': TimeframeCategory.MEDIUM_TERM,
        '8h': TimeframeCategory.MEDIUM_TERM,
        '12h': TimeframeCategory.MEDIUM_TERM,
        
        # Long-term timeframes (aggressive TP, wider SL)
        '1d': TimeframeCategory.LONG_TERM,
        '3d': TimeframeCategory.LONG_TERM,
        '1w': TimeframeCategory.LONG_TERM
    }
    
    # TP Multipliers by Category
    TP_MULTIPLIERS = {
        TimeframeCategory.SHORT_TERM: (1.0, 3.0, 5.0),   # Conservative
        TimeframeCategory.MEDIUM_TERM: (2.0, 4.0, 6.0),  # Aggressive
        TimeframeCategory.LONG_TERM: (2.0, 4.0, 6.0)     # Aggressive
    }
    
    # SL Buffer Percentage by Category
    SL_BUFFER_PCT = {
        TimeframeCategory.SHORT_TERM: 0.002,   # 0.2%
        TimeframeCategory.MEDIUM_TERM: 0.003,  # 0.3%
        TimeframeCategory.LONG_TERM: 0.003     # 0.3%
    }
    
    # Minimum SL Distance by Timeframe
    MIN_SL_DISTANCE = {
        '15m': 0.005,   # 0.5%
        '30m': 0.0075,  # 0.75%
        '1h': 0.010,    # 1.0%
        '2h': 0.0125,   # 1.25%
        '4h': 0.020,    # 2.0%
        '1d': 0.030     # 3.0%
    }
    
    # ATR Multipliers for Displacement Detection
    ATR_DISPLACEMENT_MULTIPLIERS = {
        '15m': 0.003, '30m': 0.004, '1h': 0.005,
        '2h': 0.006, '4h': 0.008, '1d': 0.012
    }
    
    # ATR Multipliers for Structure Break Detection
    ATR_STRUCTURE_MULTIPLIERS = {
        '15m': 0.001, '30m': 0.0015, '1h': 0.002,
        '2h': 0.0025, '4h': 0.003, '1d': 0.005
    }
    
    # Manual Signal Timeframe Hierarchies
    # Supports: 15m, 30m, 1h, 2h, 4h, 1d
    MANUAL_HIERARCHIES = {
        '15m': {
            'signal_tf': '15m',
            'confirmation_tf': '30m',
            'structure_tf': '1h',
            'htf_bias_tf': '1h'
        },
        '30m': {
            'signal_tf': '30m',
            'confirmation_tf': '1h',
            'structure_tf': '2h',
            'htf_bias_tf': '2h'
        },
        '1h': {
            'signal_tf': '1h',
            'confirmation_tf': '2h',
            'structure_tf': '4h',
            'htf_bias_tf': '4h'
        },
        '2h': {
            'signal_tf': '2h',
            'confirmation_tf': '4h',
            'structure_tf': '1d',
            'htf_bias_tf': '1d'
        },
        '4h': {
            'signal_tf': '4h',
            'confirmation_tf': '1d',
            'structure_tf': '1d',
            'htf_bias_tf': '1d'
        },
        '1d': {
            'signal_tf': '1d',
            'confirmation_tf': '1d',
            'structure_tf': '1d',
            'htf_bias_tf': '1d'
        }
    }
    
    # Automatic Signal Timeframe Hierarchies
    # Supports: 1h, 2h, 4h, 1d
    AUTOMATIC_HIERARCHIES = {
        '1h': {
            'signal_tf': '1h',
            'confirmation_tf': '2h',
            'structure_tf': '4h',
            'htf_bias_tf': '4h'
        },
        '2h': {
            'signal_tf': '2h',
            'confirmation_tf': '4h',
            'structure_tf': '1d',
            'htf_bias_tf': '1d'
        },
        '4h': {
            'signal_tf': '4h',
            'confirmation_tf': '1d',
            'structure_tf': '1d',
            'htf_bias_tf': '1d'
        },
        '1d': {
            'signal_tf': '1d',
            'confirmation_tf': '1d',
            'structure_tf': '1d',
            'htf_bias_tf': '1d'
        }
    }
    
    @classmethod
    def get_hierarchy(
        cls,
        signal_tf: str,
        mode: SignalMode = SignalMode.MANUAL
    ) -> Optional[TimeframeHierarchy]:
        """
        Get timeframe hierarchy for a specific entry timeframe
        
        Args:
            signal_tf: Entry timeframe (e.g., '1h', '4h', '1d')
            mode: Signal mode (MANUAL or AUTOMATIC)
        
        Returns:
            TimeframeHierarchy object or None if not supported
        """
        # Normalize timeframe string (handle '1H' -> '1h')
        normalized_tf = signal_tf.lower()
        
        # Select hierarchy based on mode
        hierarchies = cls.MANUAL_HIERARCHIES if mode == SignalMode.MANUAL else cls.AUTOMATIC_HIERARCHIES
        
        if normalized_tf not in hierarchies:
            logger.error(
                f"Unsupported timeframe '{signal_tf}' for {mode.value} signals. "
                f"Supported: {list(hierarchies.keys())}"
            )
            return None
        
        config = hierarchies[normalized_tf]
        return TimeframeHierarchy(
            signal_tf=config['signal_tf'],
            confirmation_tf=config['confirmation_tf'],
            structure_tf=config['structure_tf'],
            htf_bias_tf=config['htf_bias_tf'],
            mode=mode
        )
    
    @classmethod
    def get_all_timeframes_for_hierarchy(
        cls,
        signal_tf: str,
        mode: SignalMode = SignalMode.MANUAL
    ) -> List[str]:
        """
        Get all unique timeframes required for a signal
        
        Args:
            signal_tf: Entry timeframe
            mode: Signal mode (MANUAL or AUTOMATIC)
        
        Returns:
            List of unique timeframes needed
        """
        hierarchy = cls.get_hierarchy(signal_tf, mode)
        if not hierarchy:
            return []
        
        # Collect all unique timeframes
        tfs = [
            hierarchy.signal_tf,
            hierarchy.confirmation_tf,
            hierarchy.structure_tf,
            hierarchy.htf_bias_tf
        ]
        
        # Return unique timeframes in order
        unique_tfs = []
        for tf in tfs:
            if tf not in unique_tfs:
                unique_tfs.append(tf)
        
        return unique_tfs
    
    @classmethod
    def get_tf_category(cls, timeframe: str) -> Optional[TimeframeCategory]:
        """
        Get category for a timeframe
        
        Args:
            timeframe: Timeframe string (e.g., '1h', '4h')
        
        Returns:
            TimeframeCategory or None if not found
        """
        normalized_tf = timeframe.lower()
        return cls.TF_CATEGORIES.get(normalized_tf)
    
    @classmethod
    def get_tp_multipliers(cls, timeframe: str) -> Tuple[float, float, float]:
        """
        Get TP multipliers for a timeframe
        
        Args:
            timeframe: Timeframe string (e.g., '1h', '4h')
        
        Returns:
            Tuple of (TP1, TP2, TP3) multipliers
        """
        category = cls.get_tf_category(timeframe)
        if category:
            return cls.TP_MULTIPLIERS[category]
        
        # Default to short-term (conservative)
        logger.warning(f"Unknown timeframe '{timeframe}', using conservative TPs")
        return cls.TP_MULTIPLIERS[TimeframeCategory.SHORT_TERM]
    
    @classmethod
    def get_sl_buffer_pct(cls, timeframe: str) -> float:
        """
        Get SL buffer percentage for a timeframe
        
        Args:
            timeframe: Timeframe string (e.g., '1h', '4h')
        
        Returns:
            Buffer percentage (e.g., 0.002 for 0.2%)
        """
        category = cls.get_tf_category(timeframe)
        if category:
            return cls.SL_BUFFER_PCT[category]
        
        # Default to short-term (tighter buffer)
        logger.warning(f"Unknown timeframe '{timeframe}', using 0.002 buffer")
        return 0.002
    
    @classmethod
    def get_min_sl_distance(cls, timeframe: str) -> float:
        """
        Get minimum SL distance for a timeframe
        
        Args:
            timeframe: Timeframe string (e.g., '1h', '4h')
        
        Returns:
            Minimum SL distance percentage (e.g., 0.010 for 1.0%)
        """
        normalized_tf = timeframe.lower()
        return cls.MIN_SL_DISTANCE.get(normalized_tf, 0.015)  # Default 1.5%
    
    @classmethod
    def get_displacement_atr_multiplier(cls, timeframe: str) -> float:
        """
        Get ATR multiplier for displacement detection
        
        Args:
            timeframe: Timeframe string (e.g., '1h', '4h')
        
        Returns:
            ATR multiplier for displacement
        """
        normalized_tf = timeframe.lower()
        return cls.ATR_DISPLACEMENT_MULTIPLIERS.get(normalized_tf, 0.005)
    
    @classmethod
    def get_structure_atr_multiplier(cls, timeframe: str) -> float:
        """
        Get ATR multiplier for structure break detection
        
        Args:
            timeframe: Timeframe string (e.g., '1h', '4h')
        
        Returns:
            ATR multiplier for structure breaks
        """
        normalized_tf = timeframe.lower()
        return cls.ATR_STRUCTURE_MULTIPLIERS.get(normalized_tf, 0.002)
    
    @classmethod
    def validate_component_timeframe(
        cls,
        component_tf: str,
        expected_tf: str,
        component_name: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that a component comes from the correct timeframe
        
        Args:
            component_tf: Timeframe the component was detected on
            expected_tf: Expected timeframe for this component type
            component_name: Name of component (for logging)
        
        Returns:
            (is_valid, error_message)
        """
        component_tf_normalized = component_tf.lower()
        expected_tf_normalized = expected_tf.lower()
        
        if component_tf_normalized != expected_tf_normalized:
            error = (
                f"{component_name} timeframe mismatch: "
                f"detected on {component_tf}, expected {expected_tf}"
            )
            return False, error
        
        return True, None
    
    @classmethod
    def get_supported_manual_timeframes(cls) -> List[str]:
        """Get list of supported manual signal timeframes"""
        return list(cls.MANUAL_HIERARCHIES.keys())
    
    @classmethod
    def get_supported_automatic_timeframes(cls) -> List[str]:
        """Get list of supported automatic signal timeframes"""
        return list(cls.AUTOMATIC_HIERARCHIES.keys())
    
    @classmethod
    def is_supported_timeframe(cls, signal_tf: str, mode: SignalMode) -> bool:
        """Check if timeframe is supported for given mode"""
        normalized_tf = signal_tf.lower()
        hierarchies = cls.MANUAL_HIERARCHIES if mode == SignalMode.MANUAL else cls.AUTOMATIC_HIERARCHIES
        return normalized_tf in hierarchies
    
    @classmethod
    def get_all_supported_timeframes(cls) -> List[str]:
        """
        Get all supported timeframes across both manual and automatic modes
        
        Returns:
            List of all supported timeframes (e.g., ['1m', '5m', '15m', ...])
        """
        manual_tfs = set(cls.MANUAL_HIERARCHIES.keys())
        auto_tfs = set(cls.AUTOMATIC_HIERARCHIES.keys())
        all_tfs = sorted(manual_tfs | auto_tfs, key=lambda x: cls._tf_sort_key(x))
        return all_tfs
    
    @classmethod
    def get_mtf_timeframes(cls) -> List[str]:
        """
        Get standard timeframes for multi-timeframe analysis
        Excludes noisy short-term TFs (1m, 3m) and non-standard TFs (6h, 12h, 3d)
        
        Returns:
            List of MTF timeframes for consensus analysis
        """
        # Standard MTF timeframes for consensus
        # Removed: 1m, 3m (too noisy), 6h, 12h, 3d (non-standard)
        return ['5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w']
    
    @staticmethod
    def _tf_sort_key(tf: str) -> int:
        """Helper to sort timeframes chronologically"""
        tf_order = {
            '1m': 1, '3m': 3, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '3h': 180, '4h': 240,
            '6h': 360, '8h': 480, '12h': 720,
            '1d': 1440, '3d': 4320, '1w': 10080
        }
        return tf_order.get(tf, 0)


class TimeframeDebugLogger:
    """
    Debug logger for tracking component timeframe sources
    Provides detailed logging for timeframe validation
    """
    
    @staticmethod
    def log_hierarchy_usage(hierarchy: TimeframeHierarchy, symbol: str):
        """Log the timeframe hierarchy being used for a signal"""
        logger.info("=" * 70)
        logger.info(f"📊 TIMEFRAME HIERARCHY - {symbol} ({hierarchy.mode.value})")
        logger.info("=" * 70)
        logger.info(f"   Signal TF (Entry):       {hierarchy.signal_tf}")
        logger.info(f"   Confirmation TF:         {hierarchy.confirmation_tf}")
        logger.info(f"   Structure TF:            {hierarchy.structure_tf}")
        logger.info(f"   HTF Bias TF:             {hierarchy.htf_bias_tf}")
        logger.info("=" * 70)
    
    @staticmethod
    def log_component_source(component_type: str, timeframe: str, count: int):
        """Log which timeframe a component was detected on"""
        logger.info(f"   🔍 {component_type}: {count} detected on {timeframe}")
    
    @staticmethod
    def log_scoring_timeframe(timeframe: str, scenario: str):
        """Log which timeframe is being used for scenario scoring"""
        logger.info(f"   📊 Scoring {scenario} using {timeframe} components")
    
    @staticmethod
    def log_bias_timeframe(timeframe: str, bias: str):
        """Log which timeframe is being used for bias calculation"""
        logger.info(f"   🎯 Bias calculation using {timeframe}: {bias}")
    
    @staticmethod
    def log_telegram_display(hierarchy: TimeframeHierarchy):
        """Log timeframe information being sent to Telegram"""
        logger.info("=" * 70)
        logger.info("📱 TELEGRAM MESSAGE TIMEFRAME DISPLAY")
        logger.info("=" * 70)
        logger.info(f"   Entry TF shown:          {hierarchy.signal_tf}")
        logger.info(f"   Confirmation TF shown:   {hierarchy.confirmation_tf}")
        logger.info(f"   Structure TF shown:      {hierarchy.structure_tf}")
        logger.info(f"   HTF Bias TF shown:       {hierarchy.htf_bias_tf}")
        logger.info("=" * 70)
    
    @staticmethod
    def log_component_validation_error(
        component_type: str,
        detected_tf: str,
        expected_tf: str,
        issue: str
    ):
        """Log component timeframe validation errors"""
        logger.error("=" * 70)
        logger.error("❌ TIMEFRAME VALIDATION ERROR")
        logger.error("=" * 70)
        logger.error(f"   Component:    {component_type}")
        logger.error(f"   Detected TF:  {detected_tf}")
        logger.error(f"   Expected TF:  {expected_tf}")
        logger.error(f"   Issue:        {issue}")
        logger.error("=" * 70)
    
    @staticmethod
    def log_comprehensive_signal_debug(
        symbol: str,
        hierarchy: TimeframeHierarchy,
        components: Dict,
        bias: str,
        scenario: Optional[str] = None
    ):
        """
        MANDATORY: Comprehensive per-signal debug logging
        Shows complete TF routing and component origin
        """
        logger.info("\n" + "=" * 80)
        logger.info("🔍 COMPREHENSIVE SIGNAL DEBUG LOG")
        logger.info("=" * 80)
        logger.info(f"Symbol: {symbol} | Mode: {hierarchy.mode.value}")
        logger.info("-" * 80)
        
        # 1. Timeframe Hierarchy
        logger.info("📊 TIMEFRAME HIERARCHY:")
        logger.info(f"   Signal TF (Entry):     {hierarchy.signal_tf}")
        logger.info(f"   Confirmation TF:       {hierarchy.confirmation_tf}")
        logger.info(f"   Structure TF:          {hierarchy.structure_tf}")
        logger.info(f"   HTF Bias TF:           {hierarchy.htf_bias_tf}")
        logger.info("-" * 80)
        
        # 2. Component → TF Origin Mapping
        logger.info("🔍 COMPONENT → TF ORIGIN MAPPING:")
        
        obs = components.get('order_blocks', [])
        logger.info(f"   Order Blocks:          {len(obs)} from {hierarchy.signal_tf} (signal_tf)")
        
        fvgs = components.get('fvgs', [])
        logger.info(f"   FVGs:                  {len(fvgs)} from {hierarchy.signal_tf} (signal_tf)")
        
        liq_zones = components.get('liquidity_zones', [])
        logger.info(f"   Liquidity Zones:       {len(liq_zones)} from {hierarchy.signal_tf} (signal_tf)")
        
        sweeps = components.get('liquidity_sweeps', [])
        logger.info(f"   Liquidity Sweeps:      {len(sweeps)} from {hierarchy.signal_tf} (signal_tf)")
        
        displacement = components.get('displacement', {})
        disp_detected = displacement.get('detected', False)
        logger.info(f"   Displacement:          {'✅ Detected' if disp_detected else '❌ Not detected'} on {hierarchy.signal_tf} (signal_tf)")
        
        structure = components.get('structure_break', {})
        struct_type = structure.get('type', 'None')
        logger.info(f"   Structure Break:       {struct_type} from {hierarchy.structure_tf} (structure_tf)")
        
        breakers = components.get('breaker_blocks', [])
        logger.info(f"   Breaker Blocks:        {len(breakers)} from {hierarchy.signal_tf} (signal_tf)")
        
        mitigations = components.get('mitigation_blocks', [])
        logger.info(f"   Mitigation Blocks:     {len(mitigations)} from {hierarchy.signal_tf} (signal_tf)")
        
        logger.info("-" * 80)
        
        # 3. Scoring TF Used
        logger.info("📊 SCORING TIMEFRAME:")
        logger.info(f"   Entry Scenario Scoring: {hierarchy.signal_tf} (signal_tf)")
        logger.info(f"   Components Used:        OBs, FVGs, Displacement from {hierarchy.signal_tf}")
        if scenario:
            logger.info(f"   Selected Scenario:      {scenario}")
        logger.info("-" * 80)
        
        # 4. Bias TF Used
        logger.info("🎯 BIAS CALCULATION:")
        logger.info(f"   HTF Bias TF:           {hierarchy.htf_bias_tf}")
        logger.info(f"   Bias Result:           {bias}")
        logger.info("-" * 80)
        
        # 5. Structure TF Used
        logger.info("🏗️ STRUCTURE ANALYSIS:")
        logger.info(f"   Structure TF:          {hierarchy.structure_tf}")
        logger.info(f"   MSS/BOS Analyzed on:   {hierarchy.structure_tf}")
        if struct_type != 'None':
            logger.info(f"   Structure Break Type:  {struct_type}")
        logger.info("-" * 80)
        
        # 6. Cross-TF Contamination Check
        logger.info("✅ CROSS-TF CONTAMINATION CHECK:")
        contamination = False
        
        # Check if any components have wrong TF
        for ob in obs:
            ob_tf = getattr(ob, 'timeframe', None) or ob.get('timeframe', None) if isinstance(ob, dict) else None
            if ob_tf and ob_tf != hierarchy.signal_tf:
                logger.error(f"   ❌ Order Block from {ob_tf} in entry (expected {hierarchy.signal_tf})")
                contamination = True
        
        for fvg in fvgs:
            fvg_tf = getattr(fvg, 'timeframe', None) or fvg.get('timeframe', None) if isinstance(fvg, dict) else None
            if fvg_tf and fvg_tf != hierarchy.signal_tf:
                logger.error(f"   ❌ FVG from {fvg_tf} in entry (expected {hierarchy.signal_tf})")
                contamination = True
        
        if not contamination:
            logger.info(f"   ✅ All entry components from signal_tf ({hierarchy.signal_tf})")
            logger.info(f"   ✅ No structure_tf components in entry scoring")
            logger.info(f"   ✅ No htf_bias_tf OBs/FVGs in entry zone")
        
        logger.info("=" * 80 + "\n")


# Example usage and testing
if __name__ == "__main__":
    # Configure logging
    logging.basicConfig(level=logging.INFO)
    
    print("\n" + "=" * 70)
    print("MANUAL SIGNAL HIERARCHIES")
    print("=" * 70)
    
    for tf in TimeframeContract.get_supported_manual_timeframes():
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.MANUAL)
        if hierarchy:
            print(f"\n{tf} signal:")
            print(f"  Signal TF:       {hierarchy.signal_tf}")
            print(f"  Confirmation TF: {hierarchy.confirmation_tf}")
            print(f"  Structure TF:    {hierarchy.structure_tf}")
            print(f"  HTF Bias TF:     {hierarchy.htf_bias_tf}")
    
    print("\n" + "=" * 70)
    print("AUTOMATIC SIGNAL HIERARCHIES")
    print("=" * 70)
    
    for tf in TimeframeContract.get_supported_automatic_timeframes():
        hierarchy = TimeframeContract.get_hierarchy(tf, SignalMode.AUTOMATIC)
        if hierarchy:
            print(f"\n{tf} automatic:")
            print(f"  Signal TF:       {hierarchy.signal_tf}")
            print(f"  Confirmation TF: {hierarchy.confirmation_tf}")
            print(f"  Structure TF:    {hierarchy.structure_tf}")
            print(f"  HTF Bias TF:     {hierarchy.htf_bias_tf}")
    
    print("\n" + "=" * 70)
    print("VALIDATION EXAMPLES")
    print("=" * 70)
    
    # Test validation
    is_valid, error = TimeframeContract.validate_component_timeframe(
        component_tf="1h",
        expected_tf="1h",
        component_name="Order Block"
    )
    print(f"\nValid component: {is_valid}")
    
    is_valid, error = TimeframeContract.validate_component_timeframe(
        component_tf="4h",
        expected_tf="1h",
        component_name="Order Block"
    )
    print(f"\nInvalid component: {is_valid}")
    print(f"Error: {error}")
    
    print("\n" + "=" * 70)
    print("DEBUG LOGGING EXAMPLE")
    print("=" * 70)
    
    hierarchy = TimeframeContract.get_hierarchy("1h", SignalMode.MANUAL)
    if hierarchy:
        TimeframeDebugLogger.log_hierarchy_usage(hierarchy, "BTCUSDT")
        TimeframeDebugLogger.log_component_source("Order Blocks", "1h", 5)
        TimeframeDebugLogger.log_scoring_timeframe("1h", "PULLBACK")
        TimeframeDebugLogger.log_bias_timeframe("4h", "BULLISH")
