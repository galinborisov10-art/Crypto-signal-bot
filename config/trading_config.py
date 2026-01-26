"""
Enhanced Trading Configuration for PR #8
Structure-Aware TP Placement + News Integration

Can disable all new features for backward compatibility
"""

import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class TradingConfig:
    """
    Enhanced trading configuration with PR #8 features
    All features can be disabled for backward compatibility
    """
    
    # ════════════════════════════════════════════════════════════════
    # FEATURE TOGGLES (PR #8)
    # ════════════════════════════════════════════════════════════════
    
    # Layer 1: News Sentiment Filter
    USE_NEWS_FILTER = True  # Set False to disable news filtering
    
    # Layer 2: Structure-Aware TP Placement
    USE_STRUCTURE_TP = True  # Set False to use mathematical TPs
    
    # Layer 3: Bulgarian Messages
    USE_BULGARIAN_MESSAGES = True  # Set False for English
    
    # ════════════════════════════════════════════════════════════════
    # QUALITY FILTERS (PR #8 Enhanced)
    # ════════════════════════════════════════════════════════════════
    
    # Signal quality thresholds (set to 50 for optimal signal generation)
    MIN_CONFIDENCE = 50  # Minimum confidence % to send signals (50-70 recommended)
    MIN_MTF_CONFLUENCE = 0.6  # Increased from 0.5 (set to 0.5 for old)
    MIN_WHALE_BLOCKS = 2  # Set to 0 for old behavior
    MIN_TOTAL_COMPONENTS = 5  # Set to 0 for old behavior
    
    # ════════════════════════════════════════════════════════════════
    # TP SETTINGS (PR #8 Enhanced)
    # ════════════════════════════════════════════════════════════════
    
    # Risk/Reward ratios (more flexible for structure-aware TPs)
    MIN_RR_TP1 = 2.5  # Decreased from 3.0 (more flexible)
    MIN_RR_TP2 = 3.5  # Decreased from 5.0
    MIN_RR_TP3 = 5.0  # Decreased from 8.0
    
    # Mathematical TP multipliers (fallback when structure TP disabled)
    MATH_TP1_MULTIPLIER = 3.0
    MATH_TP2_MULTIPLIER = 5.0
    MATH_TP3_MULTIPLIER = 8.0
    
    # ════════════════════════════════════════════════════════════════
    # OBSTACLE EVALUATION (PR #8 New)
    # ════════════════════════════════════════════════════════════════
    
    # Obstacle strength threshold (only consider obstacles >= this strength)
    MIN_OBSTACLE_STRENGTH = 60  # 0-100 scale
    
    # Buffer before placing TP before obstacle (0.3% = 0.003)
    OBSTACLE_BUFFER_PCT = 0.003
    
    # Obstacle strength thresholds for decisions
    VERY_STRONG_OBSTACLE = 75  # >= 75: Very likely rejection (85% confidence)
    STRONG_OBSTACLE = 60  # 60-74: Likely rejection (70% confidence)
    MODERATE_OBSTACLE = 45  # 45-59: Uncertain (50% confidence)
    # < 45: Likely break (70% confidence)
    
    # ════════════════════════════════════════════════════════════════
    # NEWS SENTIMENT THRESHOLDS (PR #8 New)
    # ════════════════════════════════════════════════════════════════
    
    # Block signal if sentiment conflicts (sentiment score: -100 to +100)
    NEWS_BLOCK_THRESHOLD_NEGATIVE = -30  # Block BUY if sentiment < -30
    NEWS_BLOCK_THRESHOLD_POSITIVE = 30   # Block SELL if sentiment > +30
    
    # Warn if mild conflict
    NEWS_WARN_THRESHOLD = 10  # Warn if |sentiment| > 10
    
    # News importance weights
    NEWS_WEIGHT_CRITICAL = 3.0
    NEWS_WEIGHT_IMPORTANT = 2.0
    NEWS_WEIGHT_NORMAL = 1.0
    
    # News time window (hours)
    NEWS_LOOKBACK_HOURS = 24
    
    # ════════════════════════════════════════════════════════════════
    # BACKWARD COMPATIBILITY MODE
    # ════════════════════════════════════════════════════════════════
    
    # Master switch: Enable to revert ALL changes and act like old system
    BACKWARD_COMPATIBLE_MODE = False
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """
        Get configuration dictionary
        
        If BACKWARD_COMPATIBLE_MODE is True, returns old system settings
        Otherwise returns enhanced PR #8 settings
        
        Returns:
            Dictionary with all configuration parameters
        """
        if cls.BACKWARD_COMPATIBLE_MODE:
            logger.warning("⚠️ BACKWARD COMPATIBLE MODE ENABLED - Using old system settings")
            return {
                # Disable all new features
                'use_news_filter': False,
                'use_structure_tp': False,
                'use_bulgarian_messages': False,
                
                # Old quality filters
                'min_confidence': 60,
                'min_mtf_confluence': 0.5,
                'min_whale_blocks': 0,
                'min_total_components': 0,
                
                # Old TP settings
                'min_rr_tp1': 3.0,
                'min_rr_tp2': 5.0,
                'min_rr_tp3': 8.0,
                'math_tp1_multiplier': 3.0,
                'math_tp2_multiplier': 5.0,
                'math_tp3_multiplier': 8.0,
                
                # Disabled features (safe defaults)
                'min_obstacle_strength': 100,  # Effectively disabled
                'obstacle_buffer_pct': 0.003,
                'news_block_threshold_negative': -100,  # Never blocks
                'news_block_threshold_positive': 100,   # Never blocks
                'news_warn_threshold': 100,  # Never warns
                'news_weight_critical': 1.0,
                'news_weight_important': 1.0,
                'news_weight_normal': 1.0,
                'news_lookback_hours': 24,
                'very_strong_obstacle': 100,
                'strong_obstacle': 100,
                'moderate_obstacle': 100,
            }
        else:
            # Enhanced PR #8 settings
            return {
                # Enable new features
                'use_news_filter': cls.USE_NEWS_FILTER,
                'use_structure_tp': cls.USE_STRUCTURE_TP,
                'use_bulgarian_messages': cls.USE_BULGARIAN_MESSAGES,
                
                # Enhanced quality filters
                'min_confidence': cls.MIN_CONFIDENCE,
                'min_mtf_confluence': cls.MIN_MTF_CONFLUENCE,
                'min_whale_blocks': cls.MIN_WHALE_BLOCKS,
                'min_total_components': cls.MIN_TOTAL_COMPONENTS,
                
                # Enhanced TP settings
                'min_rr_tp1': cls.MIN_RR_TP1,
                'min_rr_tp2': cls.MIN_RR_TP2,
                'min_rr_tp3': cls.MIN_RR_TP3,
                'math_tp1_multiplier': cls.MATH_TP1_MULTIPLIER,
                'math_tp2_multiplier': cls.MATH_TP2_MULTIPLIER,
                'math_tp3_multiplier': cls.MATH_TP3_MULTIPLIER,
                
                # Obstacle evaluation
                'min_obstacle_strength': cls.MIN_OBSTACLE_STRENGTH,
                'obstacle_buffer_pct': cls.OBSTACLE_BUFFER_PCT,
                'very_strong_obstacle': cls.VERY_STRONG_OBSTACLE,
                'strong_obstacle': cls.STRONG_OBSTACLE,
                'moderate_obstacle': cls.MODERATE_OBSTACLE,
                
                # News sentiment
                'news_block_threshold_negative': cls.NEWS_BLOCK_THRESHOLD_NEGATIVE,
                'news_block_threshold_positive': cls.NEWS_BLOCK_THRESHOLD_POSITIVE,
                'news_warn_threshold': cls.NEWS_WARN_THRESHOLD,
                'news_weight_critical': cls.NEWS_WEIGHT_CRITICAL,
                'news_weight_important': cls.NEWS_WEIGHT_IMPORTANT,
                'news_weight_normal': cls.NEWS_WEIGHT_NORMAL,
                'news_lookback_hours': cls.NEWS_LOOKBACK_HOURS,
            }
    
    @classmethod
    def load_from_file(cls, config_file: str = None) -> Dict[str, Any]:
        """
        Load configuration from file (future enhancement)
        
        Args:
            config_file: Path to config file (JSON/YAML)
            
        Returns:
            Configuration dictionary
        """
        # For now, just return default config
        # Future: Load from JSON/YAML file
        return cls.get_config()


# Export default configuration
def get_trading_config() -> Dict[str, Any]:
    """
    Get trading configuration dictionary
    
    Returns:
        Configuration dictionary with all PR #8 settings
    """
    return TradingConfig.get_config()


# For backward compatibility
def get_legacy_config() -> Dict[str, Any]:
    """
    Get legacy (old system) configuration
    
    Returns:
        Configuration dictionary with old system settings
    """
    original_mode = TradingConfig.BACKWARD_COMPATIBLE_MODE
    TradingConfig.BACKWARD_COMPATIBLE_MODE = True
    config = TradingConfig.get_config()
    TradingConfig.BACKWARD_COMPATIBLE_MODE = original_mode
    return config
