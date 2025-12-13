"""
ICT Enhancement Layer - Main orchestrator
"""

import logging
import pandas as pd
from typing import Dict, Optional
from .hqpo_detector import HQPODetector

logger = logging.getLogger(__name__)

class ICTEnhancer:
    """Main ICT Enhancement class"""
    
    def __init__(self, config: Optional[Dict] = None):
        self.config = config or {}
        self.enabled = self.config.get('use_ict_enhancer', False)
        self.min_confidence = self.config.get('ict_enhancer_min_confidence', 70)
        self.hqpo_detector = HQPODetector(self.config)
        logger.info(f"ICT Enhancer: {'ENABLED' if self.enabled else 'DISABLED'}")
    
    def enhance_signal(self, original_signal: Dict, df: pd.DataFrame, symbol: str, timeframe: str) -> Dict:
        """Enhance signal with ICT analysis"""
        if not self.enabled or original_signal is None:
            return original_signal
        
        if original_signal.get('confidence', 0) < self.min_confidence:
            return original_signal
        
        try:
            hqpo_zones = self.hqpo_detector.detect(df)
            
            enhanced = original_signal.copy()
            enhanced['ict_enhanced'] = True
            enhanced['hqpo_zones_count'] = len(hqpo_zones)
            enhanced['hqpo_zones'] = hqpo_zones
            
            if len(hqpo_zones) > 0:
                boost = min(len(hqpo_zones) * 3, 10)
                enhanced['confidence'] = min(original_signal['confidence'] + boost, 95)
            
            logger.info(f"✅ Enhanced {symbol} {timeframe}")
            return enhanced
        
        except Exception as e:
            logger.error(f"ICT enhancement failed: {e}")
            return original_signal
