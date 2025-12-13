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
        'debug_mode': False
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
