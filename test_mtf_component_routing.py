"""
Unit Tests for Phase 2: Multi-Timeframe Component Detection Routing
Tests that components are detected from correct timeframes:
- Structure Break → from structure_tf (4h)
- Displacement → from confirmation_tf (2h)
- Whale Blocks → from confirmation_tf (2h)
- Order Blocks, FVGs → from signal_tf (1h)
"""

import os
import sys
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ict_signal_engine import ICTSignalEngine
from timeframe_contract import TimeframeContract, SignalMode


def create_test_df(length=100, trend='neutral', displacement=False, structure_break=False):
    """
    Create a test DataFrame with candle data
    
    Args:
        length: Number of candles
        trend: 'bullish', 'bearish', or 'neutral'
        displacement: Whether to include displacement pattern
        structure_break: Whether to include structure break pattern
    """
    dates = pd.date_range(end=datetime.now(), periods=length, freq='1h')
    
    # Base price movement
    if trend == 'bullish':
        base_prices = np.linspace(40000, 45000, length)
    elif trend == 'bearish':
        base_prices = np.linspace(45000, 40000, length)
    else:
        base_prices = np.ones(length) * 42000
    
    # Add noise
    noise = np.random.randn(length) * 100
    close = base_prices + noise
    
    # Add displacement if requested (strong move in one direction)
    if displacement:
        displacement_start = length - 20
        if trend == 'bullish' or trend == 'neutral':
            close[displacement_start:] = close[displacement_start] + np.linspace(0, 2000, 20)
        else:
            close[displacement_start:] = close[displacement_start] - np.linspace(0, 2000, 20)
    
    # Add structure break if requested (break previous high/low)
    if structure_break:
        sb_start = length - 30
        if trend == 'bullish' or trend == 'neutral':
            # Break previous highs
            close[sb_start:] = np.max(close[:sb_start]) + np.linspace(100, 500, 30)
        else:
            # Break previous lows
            close[sb_start:] = np.min(close[:sb_start]) - np.linspace(100, 500, 30)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': close + np.random.randn(length) * 50,
        'high': close + abs(np.random.randn(length) * 100),
        'low': close - abs(np.random.randn(length) * 100),
        'close': close,
        'volume': np.random.randint(1000, 10000, length)
    })
    
    return df


class TestMultiTFDataExtraction:
    """Test 1: Verify generate_signal() extracts correct TF data"""
    
    def test_mtf_data_extraction_with_hierarchy(self):
        """Verify MTF data is properly extracted when hierarchy is provided"""
        engine = ICTSignalEngine()
        
        # Create MTF data
        df_1h = create_test_df(length=100)
        df_2h = create_test_df(length=50)
        df_4h = create_test_df(length=25)
        
        mtf_data = {
            '1h': df_1h,
            '2h': df_2h,
            '4h': df_4h
        }
        
        # Mock the internal methods to prevent full signal generation
        with patch.object(engine, '_detect_ict_components', return_value={
            'order_blocks': [],
            'fvgs': [],
            'whale_blocks': [],
            'liquidity_zones': [],
            'displacement': {'detected': False, 'strength': 0, 'source_tf': '2h'},
            'structure_break': {'broken': False, 'type': None, 'source_tf': '4h'}
        }):
            with patch.object(engine, '_get_htf_bias_with_fallback', return_value='NEUTRAL'):
                with patch.object(engine, '_analyze_mtf_confluence', return_value=None):
                    with patch.object(engine, '_get_liquidity_zones_with_fallback', return_value=[]):
                        # This should work without throwing errors
                        try:
                            signal = engine.generate_signal(
                                df=df_1h,
                                symbol='BTCUSDT',
                                timeframe='1h',
                                mtf_data=mtf_data
                            )
                            print("✅ PASSED: MTF data extraction works without errors")
                        except Exception as e:
                            raise AssertionError(f"MTF data extraction failed: {e}")
    
    def test_fallback_when_mtf_missing(self):
        """Verify fallback to signal_tf when MTF data is not provided"""
        engine = ICTSignalEngine()
        
        df_1h = create_test_df(length=100)
        
        # Mock the internal methods
        with patch.object(engine, '_detect_ict_components', return_value={
            'order_blocks': [],
            'fvgs': [],
            'whale_blocks': [],
            'liquidity_zones': [],
            'displacement': {'detected': False, 'strength': 0, 'source_tf': '1h'},
            'structure_break': {'broken': False, 'type': None, 'source_tf': '1h'}
        }):
            with patch.object(engine, '_get_htf_bias_with_fallback', return_value='NEUTRAL'):
                with patch.object(engine, '_analyze_mtf_confluence', return_value=None):
                    with patch.object(engine, '_get_liquidity_zones_with_fallback', return_value=[]):
                        # No MTF data provided - should fallback gracefully
                        try:
                            signal = engine.generate_signal(
                                df=df_1h,
                                symbol='BTCUSDT',
                                timeframe='1h',
                                mtf_data=None  # No MTF data
                            )
                            print("✅ PASSED: Fallback to signal_tf works without errors")
                        except Exception as e:
                            raise AssertionError(f"Fallback to signal_tf failed: {e}")


class TestStructureBreakFromStructureTF:
    """Test 2: Verify structure break detected on structure_tf, not signal_tf"""
    
    def test_structure_break_uses_structure_tf(self):
        """Structure break should reflect structure_tf (4h), not signal_tf (1h)"""
        engine = ICTSignalEngine()
        
        # Setup: 1h has structure break (noisy), 4h has no structure break (clean)
        df_1h = create_test_df(length=100, trend='bullish', structure_break=True)
        df_2h = create_test_df(length=50, trend='bullish')
        df_4h = create_test_df(length=25, trend='neutral', structure_break=False)
        
        hierarchy = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
        
        # Call _detect_ict_components with MTF data
        components = engine._detect_ict_components(
            df_signal=df_1h,
            df_confirmation=df_2h,
            df_structure=df_4h,
            timeframe='1h',
            liquidity_zones=[],
            tf_hierarchy=hierarchy
        )
        
        # Structure break should be detected from 4h (structure_tf)
        assert 'structure_break' in components
        structure_info = components['structure_break']
        
        # Check source_tf is correct
        assert structure_info.get('source_tf') == '4h', \
            f"Expected structure_tf='4h', got '{structure_info.get('source_tf')}'"
        
        print(f"✅ PASSED: Structure break detected from {structure_info.get('source_tf')}")


class TestDisplacementFromConfirmationTF:
    """Test 3: Verify displacement detected on confirmation_tf, not signal_tf"""
    
    def test_displacement_uses_confirmation_tf(self):
        """Displacement should reflect confirmation_tf (2h), not signal_tf (1h)"""
        engine = ICTSignalEngine()
        
        # Setup: 1h has weak displacement, 2h has strong displacement
        df_1h = create_test_df(length=100, trend='neutral', displacement=False)
        df_2h = create_test_df(length=50, trend='bullish', displacement=True)
        df_4h = create_test_df(length=25, trend='neutral')
        
        hierarchy = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
        
        # Call _detect_ict_components with MTF data
        components = engine._detect_ict_components(
            df_signal=df_1h,
            df_confirmation=df_2h,
            df_structure=df_4h,
            timeframe='1h',
            liquidity_zones=[],
            tf_hierarchy=hierarchy
        )
        
        # Displacement should be detected from 2h (confirmation_tf)
        assert 'displacement' in components
        displacement_info = components['displacement']
        
        # Check source_tf is correct
        assert displacement_info.get('source_tf') == '2h', \
            f"Expected confirmation_tf='2h', got '{displacement_info.get('source_tf')}'"
        
        print(f"✅ PASSED: Displacement detected from {displacement_info.get('source_tf')}")


class TestWhaleBlocksFromConfirmationTF:
    """Test 4: Verify whale blocks detected on confirmation_tf"""
    
    def test_whale_blocks_use_confirmation_tf(self):
        """Whale blocks should be detected from confirmation_tf (2h)"""
        engine = ICTSignalEngine()
        
        # Create test data
        df_1h = create_test_df(length=100)
        df_2h = create_test_df(length=50)
        df_4h = create_test_df(length=25)
        
        hierarchy = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
        
        # Mock whale detector to track which df was used
        with patch.object(engine.whale_detector, 'detect_whale_blocks') as mock_whale:
            mock_whale.return_value = []
            
            # Call _detect_ict_components
            components = engine._detect_ict_components(
                df_signal=df_1h,
                df_confirmation=df_2h,
                df_structure=df_4h,
                timeframe='1h',
                liquidity_zones=[],
                tf_hierarchy=hierarchy
            )
            
            # Verify whale_detector was called with df_confirmation (2h data)
            assert mock_whale.called, "Whale detector should be called"
            
            # Check the dataframe passed (should be df_2h, not df_1h)
            call_args = mock_whale.call_args
            df_passed = call_args[0][0]  # First positional argument
            tf_passed = call_args[0][1]  # Second positional argument
            
            # Verify it's the 2h dataframe (has 50 rows, not 100)
            assert len(df_passed) == 50, \
                f"Expected 50 rows (2h data), got {len(df_passed)} rows"
            assert tf_passed == '2h', \
                f"Expected timeframe='2h', got '{tf_passed}'"
            
            print(f"✅ PASSED: Whale blocks detected from confirmation_tf (2h)")


class TestFallbackBehavior:
    """Test 5: Verify graceful fallback to signal_tf when MTF data unavailable"""
    
    def test_fallback_when_confirmation_missing(self):
        """Should fallback to signal_tf when confirmation TF is missing"""
        engine = ICTSignalEngine()
        
        df_1h = create_test_df(length=100)
        hierarchy = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
        
        # Call with missing confirmation data
        components = engine._detect_ict_components(
            df_signal=df_1h,
            df_confirmation=None,  # Missing!
            df_structure=df_1h,
            timeframe='1h',
            liquidity_zones=[],
            tf_hierarchy=hierarchy
        )
        
        # Should not crash and should have components
        assert components is not None
        assert 'displacement' in components
        assert 'whale_blocks' in components
        
        # Source should fallback to 1h
        assert components['displacement'].get('source_tf') == '1h', \
            "Should fallback to signal_tf when confirmation_tf missing"
        
        print("✅ PASSED: Fallback to signal_tf when confirmation data missing")
    
    def test_fallback_when_structure_missing(self):
        """Should fallback to signal_tf when structure TF is missing"""
        engine = ICTSignalEngine()
        
        df_1h = create_test_df(length=100)
        hierarchy = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
        
        # Call with missing structure data
        components = engine._detect_ict_components(
            df_signal=df_1h,
            df_confirmation=df_1h,
            df_structure=None,  # Missing!
            timeframe='1h',
            liquidity_zones=[],
            tf_hierarchy=hierarchy
        )
        
        # Should not crash and should have components
        assert components is not None
        assert 'structure_break' in components
        
        # Source should fallback to 1h
        assert components['structure_break'].get('source_tf') == '1h', \
            "Should fallback to signal_tf when structure_tf missing"
        
        print("✅ PASSED: Fallback to signal_tf when structure data missing")


class TestNoDuplicateDetection:
    """Test 6: Verify components not detected twice"""
    
    def test_no_duplicate_structure_detection(self):
        """Structure break should be detected ONCE (not in main flow)"""
        engine = ICTSignalEngine()
        
        df_1h = create_test_df(length=100)
        
        # Track how many times _check_structure_break is called
        call_count = {'count': 0}
        original_check = engine._check_structure_break
        
        def tracked_check(df):
            call_count['count'] += 1
            return original_check(df)
        
        engine._check_structure_break = tracked_check
        
        # Generate components
        hierarchy = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
        components = engine._detect_ict_components(
            df_signal=df_1h,
            df_confirmation=df_1h,
            df_structure=df_1h,
            timeframe='1h',
            liquidity_zones=[],
            tf_hierarchy=hierarchy
        )
        
        # Should be called exactly ONCE (in _detect_ict_components, not again in main flow)
        assert call_count['count'] == 1, \
            f"Structure break should be detected ONCE, but was called {call_count['count']} times"
        
        print(f"✅ PASSED: Structure break detected exactly once (not duplicated)")
    
    def test_no_duplicate_displacement_detection(self):
        """Displacement should be detected ONCE (not in main flow)"""
        engine = ICTSignalEngine()
        
        df_1h = create_test_df(length=100)
        
        # Track how many times _check_displacement is called
        call_count = {'count': 0}
        original_check = engine._check_displacement
        
        def tracked_check(df):
            call_count['count'] += 1
            return original_check(df)
        
        engine._check_displacement = tracked_check
        
        # Generate components
        hierarchy = TimeframeContract.get_hierarchy('1h', SignalMode.MANUAL)
        components = engine._detect_ict_components(
            df_signal=df_1h,
            df_confirmation=df_1h,
            df_structure=df_1h,
            timeframe='1h',
            liquidity_zones=[],
            tf_hierarchy=hierarchy
        )
        
        # Should be called exactly ONCE
        assert call_count['count'] == 1, \
            f"Displacement should be detected ONCE, but was called {call_count['count']} times"
        
        print(f"✅ PASSED: Displacement detected exactly once (not duplicated)")


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 80)
    print("PHASE 2: MULTI-TIMEFRAME COMPONENT ROUTING TESTS")
    print("=" * 80)
    
    test_classes = [
        TestMultiTFDataExtraction,
        TestStructureBreakFromStructureTF,
        TestDisplacementFromConfirmationTF,
        TestWhaleBlocksFromConfirmationTF,
        TestFallbackBehavior,
        TestNoDuplicateDetection
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = []
    
    for test_class in test_classes:
        print(f"\n{'=' * 80}")
        print(f"Running: {test_class.__name__}")
        print(f"{'=' * 80}")
        
        test_methods = [m for m in dir(test_class) if m.startswith('test_')]
        
        for method_name in test_methods:
            total_tests += 1
            test_instance = test_class()
            test_method = getattr(test_instance, method_name)
            
            try:
                test_method()
                passed_tests += 1
            except Exception as e:
                failed_tests.append((test_class.__name__, method_name, str(e)))
                print(f"❌ FAILED: {method_name}")
                print(f"   Error: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("TEST SUMMARY")
    print("=" * 80)
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {len(failed_tests)}")
    
    if failed_tests:
        print("\nFailed Tests:")
        for class_name, method_name, error in failed_tests:
            print(f"  • {class_name}.{method_name}")
            print(f"    {error}")
    else:
        print("\n✅ ALL TESTS PASSED!")
    
    return len(failed_tests) == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
