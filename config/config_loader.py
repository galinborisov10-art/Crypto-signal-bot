"""
Feature Flags Configuration Loader
"""

import json
import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

CONFIG_PATH = 'config/feature_flags.json'

def load_feature_flags() -> Dict[str, Any]:
    """Load feature flags from JSON file"""
    if not os.path.exists(CONFIG_PATH):
        logger.warning(f"Feature flags file not found, using defaults")
        return get_default_flags()
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        logger.info(f"Feature flags loaded")
        return config
    except Exception as e:
        logger.error(f"Error loading feature flags: {e}")
        return get_default_flags()

def get_default_flags() -> Dict[str, Any]:
    """Get default feature flags"""
    return {
        'use_ict_enhancer': False,
        'ict_enhancer_min_confidence': 70,
        'use_archive': False,
        'auto_alerts_enabled': True,
        'auto_alerts_interval_minutes': 15,
        'auto_alerts_top_n': 3,
        'news_tracking_enabled': True,
        'debug_mode': False,
        'use_ict_only': False,
        'use_traditional': True,
        'use_hybrid': True,
        'use_breaker_blocks': True,
        'use_mitigation_blocks': True,
        'use_sibi_ssib': True,
        'use_zone_explanations': True,
        'use_cache': True,
        'hybrid_mode': 'smart',
        'ict_weight': 0.6,
        'traditional_weight': 0.4,
        'cache_ttl_seconds': 3600,
        'cache_max_size': 100
    }

def update_feature_flag(key: str, value: Any) -> bool:
    """Update a single feature flag"""
    try:
        config = load_feature_flags()
        config[key] = value
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info(f"Feature flag updated: {key} = {value}")
        return True
    except Exception as e:
        logger.error(f"Error updating feature flag: {e}")
        return False

def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled"""
    config = load_feature_flags()
    return config.get(feature_name, False)

def get_flag(name: str, default: Any = None) -> Any:
    """
    Get single feature flag value.
    
    Args:
        name: Flag name
        default: Default value if flag not found
        
    Returns:
        Flag value or default
    """
    config = load_feature_flags()
    return config.get(name, default)

def set_flag(name: str, value: Any) -> bool:
    """
    Set single feature flag.
    
    Args:
        name: Flag name
        value: New value
        
    Returns:
        True if successful, False otherwise
    """
    return update_feature_flag(name, value)

def toggle_flag(name: str) -> bool:
    """
    Toggle boolean feature flag.
    
    Args:
        name: Flag name
        
    Returns:
        New flag value (True/False)
    """
    try:
        config = load_feature_flags()
        current_value = config.get(name, False)
        
        # Only toggle if current value is boolean
        if not isinstance(current_value, bool):
            logger.warning(f"Cannot toggle non-boolean flag: {name}")
            return current_value
        
        new_value = not current_value
        update_feature_flag(name, new_value)
        logger.info(f"Toggled flag {name}: {current_value} -> {new_value}")
        return new_value
    except Exception as e:
        logger.error(f"Error toggling flag: {e}")
        return False

def save_feature_flags(flags: Dict[str, Any]) -> bool:
    """
    Save complete feature flags configuration.
    
    Args:
        flags: Complete flags dictionary
        
    Returns:
        True if successful, False otherwise
    """
    try:
        os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
        with open(CONFIG_PATH, 'w') as f:
            json.dump(flags, f, indent=2)
        logger.info("Feature flags saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving feature flags: {e}")
        return False
