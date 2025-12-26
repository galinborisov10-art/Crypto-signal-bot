"""Config Loader Module - Loads feature flags from JSON"""
import json
import logging
import os
from typing import Dict, Any

logger = logging.getLogger(__name__)
CONFIG_PATH = os.path. join(os.path.dirname(__file__), 'feature_flags.json')

def load_feature_flags() -> Dict[str, Any]:
    """Load feature flags from config/feature_flags.json"""
    try:
        with open(CONFIG_PATH, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading feature flags: {e}")
        return {}

def get_feature_flag(path: str, default: Any = False) -> Any:
    """Get specific feature flag by dot-separated path"""
    try: 
        flags = load_feature_flags()
        keys = path.split('.')
        value = flags
        for key in keys:
            value = value.get(key, default)
            if value == default:
                break
        return value
    except Exception as e: 
        logger.error(f"Error getting feature flag:  {e}")
        return default

def is_feature_enabled(feature_path: str) -> bool:
    """Check if feature is enabled"""
    return get_feature_flag(feature_path, default=False) == True
