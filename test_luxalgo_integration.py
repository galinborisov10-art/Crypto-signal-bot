"""
Unit tests for LuxAlgo integration fixes

Tests verify that:
1. analyze() never returns None
2. analyze() handles insufficient data gracefully
3. analyze() handles exceptions safely
4. ict_signal_engine handles None from LuxAlgo (defensive)

Author: Copilot
Date: 2026-01-08
"""

import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import dependencies if available
try:
    import pandas as pd
    import numpy as np
    from unittest.mock import Mock, MagicMock, patch
    DEPENDENCIES_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Dependencies not available: {e}")
    print("Skipping tests - install dependencies with: pip install pandas numpy")
    DEPENDENCIES_AVAILABLE = False
    sys.exit(0)

try:
    from luxalgo_ict_analysis import CombinedLuxAlgoAnalysis
    LUXALGO_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ LuxAlgo module not available: {e}")
    LUXALGO_AVAILABLE = False


class TestLuxAlgoNeverReturnsNone:
    """CRITICAL: Test that analyze() never returns None"""
    
    def test_analyze_never_returns_none_minimal_data(self):
        """Test with minimal data - should return dict, not None"""
        analyzer = CombinedLuxAlgoAnalysis()
        
        # Minimal DataFrame (1 row)
        df = pd.DataFrame({
            'open': [100],
            'high': [101],
            'low': [99],
            'close': [100.5],
            'volume': [1000]
        })
        
        result = analyzer.analyze(df)
        
        # CRITICAL assertions
        assert result is not None, "analyze() returned None!"
        assert isinstance(result, dict), "analyze() must return dict"
        assert 'sr_data' in result, "Missing sr_data in result"
        assert 'ict_data' in result, "Missing ict_data in result"
        assert 'combined_signal' in result, "Missing combined_signal in result"
        assert 'entry_valid' in result, "Missing entry_valid in result"
        assert 'status' in result, "Missing status in result"
        
        print(f"✅ Test passed: analyze() returned dict with status: {result['status']}")
    
    def test_analyze_never_returns_none_normal_data(self):
        """Test with normal data - should return dict, not None"""
        analyzer = CombinedLuxAlgoAnalysis()
        
        # Normal DataFrame (50 rows)
        np.random.seed(42)
        prices = 100 + np.random.randn(50).cumsum()
        
        df = pd.DataFrame({
            'open': prices,
            'high': prices + np.abs(np.random.randn(50)),
            'low': prices - np.abs(np.random.randn(50)),
            'close': prices + np.random.randn(50) * 0.5,
            'volume': 1000 + np.random.randn(50) * 100
        })
        
        result = analyzer.analyze(df)
        
        # CRITICAL assertions
        assert result is not None, "analyze() returned None!"
        assert isinstance(result, dict), "analyze() must return dict"
        assert 'status' in result, "Missing status in result"
        
        print(f"✅ Test passed: Normal data - status: {result['status']}")


class TestLuxAlgoHandlesInsufficientData:
    """Test fallback when data is insufficient"""
    
    def test_analyze_empty_dataframe(self):
        """Test with empty DataFrame"""
        analyzer = CombinedLuxAlgoAnalysis()
        
        df = pd.DataFrame()
        
        result = analyzer.analyze(df)
        
        # Should return safe defaults
        assert result is not None
        assert result['entry_valid'] == False
        assert result['status'] in ['insufficient_data', 'no_structure', 'exception']
        assert isinstance(result['sr_data'], dict)
        assert isinstance(result['ict_data'], dict)
        
        print(f"✅ Empty DataFrame handled: status={result['status']}")
    
    def test_analyze_too_few_rows(self):
        """Test with too few rows (< 20)"""
        analyzer = CombinedLuxAlgoAnalysis()
        
        # Only 10 rows
        df = pd.DataFrame({
            'open': [100] * 10,
            'high': [101] * 10,
            'low': [99] * 10,
            'close': [100.5] * 10,
            'volume': [1000] * 10
        })
        
        result = analyzer.analyze(df)
        
        assert result is not None
        assert result['entry_valid'] == False
        assert 'insufficient_data' in result['status'] or result['status'] == 'no_structure'
        
        print(f"✅ Too few rows handled: status={result['status']}")
    
    def test_analyze_missing_columns(self):
        """Test with missing required columns"""
        analyzer = CombinedLuxAlgoAnalysis()
        
        # Missing 'close' column
        df = pd.DataFrame({
            'open': [100] * 30,
            'high': [101] * 30,
            'low': [99] * 30,
            'volume': [1000] * 30
        })
        
        result = analyzer.analyze(df)
        
        assert result is not None
        assert result['entry_valid'] == False
        assert 'insufficient_data' in result['status'] or 'exception' in result['status']
        
        print(f"✅ Missing columns handled: status={result['status']}")


class TestLuxAlgoExceptionSafety:
    """Test that analyze() handles exceptions gracefully"""
    
    def test_analyze_invalid_data(self):
        """Test with invalid data that might cause exception"""
        analyzer = CombinedLuxAlgoAnalysis()
        
        # Invalid data (all NaN)
        df = pd.DataFrame({
            'open': [np.nan] * 30,
            'high': [np.nan] * 30,
            'low': [np.nan] * 30,
            'close': [np.nan] * 30,
            'volume': [np.nan] * 30
        })
        
        result = analyzer.analyze(df)
        
        # Must not raise, must return safe defaults
        assert result is not None
        assert result['entry_valid'] == False
        assert 'exception' in result['status'].lower() or result['status'] in ['insufficient_data', 'no_structure']
        
        print(f"✅ Invalid data (NaN) handled: status={result['status']}")
    
    def test_analyze_with_mocked_exception(self):
        """Test exception handling with mocked component failure"""
        analyzer = CombinedLuxAlgoAnalysis()
        
        # Create normal data
        df = pd.DataFrame({
            'open': [100] * 30,
            'high': [101] * 30,
            'low': [99] * 30,
            'close': [100.5] * 30,
            'volume': [1000] * 30
        })
        
        # Mock sr_analyzer to raise exception
        if analyzer.sr_analyzer:
            with patch.object(analyzer.sr_analyzer, 'analyze', side_effect=Exception("Mocked error")):
                result = analyzer.analyze(df)
                
                # Should catch exception and return safe defaults
                assert result is not None
                assert result['entry_valid'] == False
                assert 'exception' in result['status'].lower()
                
                print(f"✅ Mocked exception handled: status={result['status']}")
        else:
            print("⚠️ Skipping mocked exception test - sr_analyzer not available")


class TestICTSignalEngineHandlesNone:
    """Test that ict_signal_engine handles None from LuxAlgo defensively"""
    
    def test_ict_engine_handles_luxalgo_none(self):
        """Test that ict_signal_engine can handle None from LuxAlgo (defensive layer)"""
        # This is an integration test - verify the defensive None check exists
        
        # Import ict_signal_engine
        try:
            from ict_signal_engine import ICTSignalEngine
            
            # Create engine
            engine = ICTSignalEngine()
            
            # Verify luxalgo_combined exists
            if engine.luxalgo_combined:
                # Mock analyze to return None (simulating old buggy behavior)
                with patch.object(engine.luxalgo_combined, 'analyze', return_value=None):
                    # Create sample DataFrame
                    df = pd.DataFrame({
                        'timestamp': pd.date_range('2025-01-01', periods=100, freq='1H'),
                        'open': 100 + np.random.randn(100),
                        'high': 101 + np.random.randn(100),
                        'low': 99 + np.random.randn(100),
                        'close': 100 + np.random.randn(100),
                        'volume': 1000 + np.random.randn(100) * 100
                    })
                    df = df.set_index('timestamp')
                    
                    # Call _detect_ict_components (which calls LuxAlgo internally)
                    components = engine._detect_ict_components(df, '1h')
                    
                    # Should have safe defaults for LuxAlgo components
                    assert 'luxalgo_sr' in components
                    assert 'luxalgo_ict' in components
                    assert 'luxalgo_combined' in components
                    
                    # Should be empty dicts (safe defaults)
                    assert isinstance(components['luxalgo_sr'], dict)
                    assert isinstance(components['luxalgo_ict'], dict)
                    assert isinstance(components['luxalgo_combined'], dict)
                    
                    print("✅ ICT engine handles LuxAlgo None gracefully")
            else:
                print("⚠️ Skipping ICT engine test - luxalgo_combined not available")
                
        except ImportError as e:
            print(f"⚠️ Skipping ICT engine test - import failed: {e}")


# Run tests
if __name__ == "__main__":
    if not DEPENDENCIES_AVAILABLE or not LUXALGO_AVAILABLE:
        print("⚠️ Cannot run tests - missing dependencies")
        sys.exit(1)
    
    print("=" * 60)
    print("🧪 LuxAlgo Integration Tests")
    print("=" * 60)
    
    try:
        # Test 1: Never returns None
        print("\n📋 Test Suite 1: analyze() Never Returns None")
        print("-" * 60)
        test1 = TestLuxAlgoNeverReturnsNone()
        test1.test_analyze_never_returns_none_minimal_data()
        test1.test_analyze_never_returns_none_normal_data()
        
        # Test 2: Handles insufficient data
        print("\n📋 Test Suite 2: Handle Insufficient Data")
        print("-" * 60)
        test2 = TestLuxAlgoHandlesInsufficientData()
        test2.test_analyze_empty_dataframe()
        test2.test_analyze_too_few_rows()
        test2.test_analyze_missing_columns()
        
        # Test 3: Exception safety
        print("\n📋 Test Suite 3: Exception Safety")
        print("-" * 60)
        test3 = TestLuxAlgoExceptionSafety()
        test3.test_analyze_invalid_data()
        test3.test_analyze_with_mocked_exception()
        
        # Test 4: ICT engine defensive layer
        print("\n📋 Test Suite 4: ICT Engine Defensive Layer")
        print("-" * 60)
        test4 = TestICTSignalEngineHandlesNone()
        test4.test_ict_engine_handles_luxalgo_none()
        
        print("\n" + "=" * 60)
        print("✅ All LuxAlgo Integration Tests Completed!")
        print("=" * 60)
    except Exception as e:
        print(f"\n❌ Test execution failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
