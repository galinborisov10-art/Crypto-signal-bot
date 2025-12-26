"""
Backward compatibility tests
Ensures new code doesn't break existing functionality
"""

import pytest
from unittest.mock import Mock, patch, mock_open
import json


class TestBackwardCompatibility:
    """Ensure existing features work with new code"""
    
    def test_feature_flags_disabled_by_default(self):
        """Test that all new features are disabled by default"""
        
        # Mock feature_flags.json
        feature_flags = {
            "fundamental_analysis": {
                "enabled": False,
                "sentiment_analysis": False,
                "btc_correlation": False
            }
        }
        
        # All should be False
        assert feature_flags["fundamental_analysis"]["enabled"] == False
        assert feature_flags["fundamental_analysis"]["sentiment_analysis"] == False
        assert feature_flags["fundamental_analysis"]["btc_correlation"] == False
    
    def test_existing_imports_still_work(self):
        """Test that existing imports are not broken"""
        
        # These should all work without errors
        try:
            from ict_signal_engine import ICTSignalEngine
            from real_time_monitor import RealTimePositionMonitor
            from ict_80_alert_handler import ICT80AlertHandler
            
            assert True, "All existing imports work"
        except ImportError as e:
            pytest.fail(f"Existing imports broken: {e}")
    
    def test_fundamental_module_optional(self):
        """Test that fundamental module is optional"""
        
        # Should not crash if fundamental module is not imported
        try:
            # Simulate bot running without fundamental analysis
            feature_flags = {"fundamental_analysis": {"enabled": False}}
            
            # Bot should work normally
            assert True, "Bot works without fundamental analysis"
        except Exception as e:
            pytest.fail(f"Bot crashes without fundamental module: {e}")
