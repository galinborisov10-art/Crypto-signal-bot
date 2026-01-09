"""
Unit tests for LuxAlgo integration fix
Ensures analyze() never returns None and has proper fallback behavior
"""

import pytest
import os
import sys
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestLuxAlgoAnalyzeContract:
    """Test that analyze() always returns valid dict structure"""
    
    def test_analyze_returns_dict_not_none_with_none_input(self):
        """Ensure analyze() NEVER returns None when given None input"""
        # Mock the dependencies to avoid import errors
        with patch('luxalgo_ict_analysis.LuxAlgoSRMTF'), \
             patch('luxalgo_ict_analysis.LuxAlgoICT'), \
             patch('luxalgo_ict_analysis.detect_breaker_blocks'):
            
            from luxalgo_ict_analysis import CombinedLuxAlgoAnalysis
            
            analyzer = CombinedLuxAlgoAnalysis()
            
            # Test with None input
            result = analyzer.analyze(None)
            assert result is not None, "analyze() should NEVER return None"
            assert isinstance(result, dict), "analyze() should always return a dict"
            assert 'status' in result, "Result should contain 'status' key"
            assert 'entry_valid' in result, "Result should contain 'entry_valid' key"
            assert result['entry_valid'] is False, "entry_valid should be False for invalid input"
            assert result['status'] == 'invalid_input_none', "Status should indicate None input"
    
    def test_analyze_insufficient_data(self):
        """Test analyze() with insufficient data"""
        with patch('luxalgo_ict_analysis.LuxAlgoSRMTF'), \
             patch('luxalgo_ict_analysis.LuxAlgoICT'), \
             patch('luxalgo_ict_analysis.detect_breaker_blocks'):
            
            from luxalgo_ict_analysis import CombinedLuxAlgoAnalysis
            
            analyzer = CombinedLuxAlgoAnalysis(min_periods=50)
            
            # Create DataFrame with only 5 rows (less than min_periods)
            df = pd.DataFrame({
                'close': np.random.rand(5),
                'high': np.random.rand(5),
                'low': np.random.rand(5),
                'open': np.random.rand(5),
                'volume': np.random.rand(5)
            })
            
            result = analyzer.analyze(df)
            assert result is not None, "analyze() should never return None"
            assert isinstance(result, dict), "analyze() should return dict"
            assert result['status'] == 'insufficient_data', "Status should indicate insufficient data"
            assert result['entry_valid'] is False, "entry_valid should be False for insufficient data"
            assert 'sr_data' in result, "Result should have sr_data key"
            assert 'ict_data' in result, "Result should have ict_data key"
            assert 'combined_signal' in result, "Result should have combined_signal key"
    
    def test_analyze_valid_data_structure(self):
        """Test analyze() with valid data returns all required keys"""
        with patch('luxalgo_ict_analysis.LuxAlgoSRMTF') as mock_sr, \
             patch('luxalgo_ict_analysis.LuxAlgoICT') as mock_ict, \
             patch('luxalgo_ict_analysis.detect_breaker_blocks', return_value=[]):
            
            # Mock the analyzers to return valid data
            mock_sr_instance = Mock()
            mock_sr_instance.analyze.return_value = {
                'support_zones': [],
                'resistance_zones': []
            }
            mock_sr.return_value = mock_sr_instance
            
            mock_ict_instance = Mock()
            mock_ict_instance.analyze.return_value = {
                'order_blocks': [],
                'fvgs': [],
                'trend': 'neutral'
            }
            mock_ict.return_value = mock_ict_instance
            
            from luxalgo_ict_analysis import CombinedLuxAlgoAnalysis
            
            analyzer = CombinedLuxAlgoAnalysis(min_periods=10)
            
            # Create valid DataFrame
            df = pd.DataFrame({
                'close': np.random.rand(100),
                'high': np.random.rand(100),
                'low': np.random.rand(100),
                'open': np.random.rand(100),
                'volume': np.random.rand(100)
            })
            
            result = analyzer.analyze(df)
            
            # Verify structure
            assert result is not None, "analyze() should never return None"
            assert isinstance(result, dict), "Result should be a dict"
            
            # Required keys
            assert 'sr_data' in result, "Result should have sr_data"
            assert 'ict_data' in result, "Result should have ict_data"
            assert 'combined_signal' in result, "Result should have combined_signal"
            assert 'entry_valid' in result, "Result should have entry_valid"
            assert 'status' in result, "Result should have status"
            
            # Types
            assert isinstance(result['sr_data'], dict), "sr_data should be dict"
            assert isinstance(result['ict_data'], dict), "ict_data should be dict"
            assert isinstance(result['combined_signal'], dict), "combined_signal should be dict"
            assert isinstance(result['entry_valid'], bool), "entry_valid should be bool"
            assert isinstance(result['status'], str), "status should be str"
    
    def test_analyze_never_raises_exception(self):
        """Ensure analyze() catches all exceptions and returns safe dict"""
        with patch('luxalgo_ict_analysis.LuxAlgoSRMTF') as mock_sr, \
             patch('luxalgo_ict_analysis.LuxAlgoICT') as mock_ict, \
             patch('luxalgo_ict_analysis.detect_breaker_blocks'):
            
            # Mock the analyzers to raise exceptions
            mock_sr_instance = Mock()
            mock_sr_instance.analyze.side_effect = Exception("SR analyzer failed")
            mock_sr.return_value = mock_sr_instance
            
            mock_ict_instance = Mock()
            mock_ict_instance.analyze.side_effect = Exception("ICT analyzer failed")
            mock_ict.return_value = mock_ict_instance
            
            from luxalgo_ict_analysis import CombinedLuxAlgoAnalysis
            
            analyzer = CombinedLuxAlgoAnalysis(min_periods=10)
            
            # Create problematic data
            df = pd.DataFrame({
                'close': [np.nan] * 100,
                'high': [np.inf] * 100,
                'low': [-np.inf] * 100,
                'open': [0] * 100,
                'volume': [0] * 100
            })
            
            # Should NOT raise, should return safe default
            result = analyzer.analyze(df)
            assert result is not None, "analyze() should never return None even on exception"
            assert isinstance(result, dict), "analyze() should return dict even on exception"
            assert result['entry_valid'] is False, "entry_valid should be False on exception"
            assert 'exception' in result['status'] or result['status'] == 'success', \
                "Status should indicate exception or success"


class TestLuxAlgoAdvisoryMode:
    """Test that LuxAlgo is advisory, not blocking"""
    
    def test_luxalgo_failure_does_not_block_analysis(self):
        """Simulate LuxAlgo returning failure, verify analysis can continue"""
        with patch('luxalgo_ict_analysis.LuxAlgoSRMTF'), \
             patch('luxalgo_ict_analysis.LuxAlgoICT'), \
             patch('luxalgo_ict_analysis.detect_breaker_blocks'):
            
            from luxalgo_ict_analysis import CombinedLuxAlgoAnalysis
            
            analyzer = CombinedLuxAlgoAnalysis()
            result = analyzer.analyze(None)
            
            # Even on failure, we get valid dict
            assert result['entry_valid'] is False, "entry_valid should be False on failure"
            
            # Downstream code can safely continue with:
            # - result.get('sr_data', {})
            # - result.get('entry_valid', False)
            # Without crashes
            
            assert result.get('sr_data', {}) == {}, "sr_data should be empty dict on failure"
            assert result.get('entry_valid', False) is False, "entry_valid should default to False"
    
    def test_luxalgo_result_structure_allows_safe_get_operations(self):
        """Test that the result structure allows safe .get() operations"""
        with patch('luxalgo_ict_analysis.LuxAlgoSRMTF'), \
             patch('luxalgo_ict_analysis.LuxAlgoICT'), \
             patch('luxalgo_ict_analysis.detect_breaker_blocks'):
            
            from luxalgo_ict_analysis import CombinedLuxAlgoAnalysis
            
            analyzer = CombinedLuxAlgoAnalysis()
            
            # Test with None (worst case)
            result = analyzer.analyze(None)
            
            # These should all work without AttributeError
            sr_data = result.get('sr_data', {})
            ict_data = result.get('ict_data', {})
            combined_signal = result.get('combined_signal', {})
            entry_valid = result.get('entry_valid', False)
            status = result.get('status', 'unknown')
            
            # Verify we can do nested .get() operations safely
            support_zones = sr_data.get('support_zones', [])
            resistance_zones = sr_data.get('resistance_zones', [])
            
            assert isinstance(sr_data, dict), "sr_data should be dict"
            assert isinstance(ict_data, dict), "ict_data should be dict"
            assert isinstance(combined_signal, dict), "combined_signal should be dict"
            assert isinstance(entry_valid, bool), "entry_valid should be bool"
            assert isinstance(status, str), "status should be str"
            assert isinstance(support_zones, list), "support_zones should be list"
            assert isinstance(resistance_zones, list), "resistance_zones should be list"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
