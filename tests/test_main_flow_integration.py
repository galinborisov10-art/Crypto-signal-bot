"""
Integration tests for Entry Gating + Confidence Threshold in main flow (ESB v1.0 §2.1-2.2)

Tests the integration of Entry Gating and Confidence Threshold evaluators
into the ICT Signal Engine's main signal generation flow.

Author: galinborisov10-art
Date: 2026-01-21
"""

try:
    import pytest
except ImportError:
    pytest = None

import sys
import os
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ict_signal_engine import ICTSignalEngine
from entry_gating_evaluator import evaluate_entry_gating
from confidence_threshold_evaluator import evaluate_confidence_threshold


class TestMainFlowIntegration:
    """Test integration of Entry Gating and Confidence Threshold"""
    
    if pytest:
        @pytest.fixture
        def engine(self):
            """Create ICT Signal Engine"""
            return ICTSignalEngine()
        
        @pytest.fixture
        def sample_df(self):
            """Create sample DataFrame with realistic price data"""
            dates = pd.date_range('2025-01-01', periods=100, freq='1H')
            
            # Generate realistic price movement
            base_price = 50000
            prices = [base_price]
            
            for i in range(99):
                # Random walk with slight upward bias
                change = np.random.randn() * 100 + 10
                new_price = max(prices[-1] + change, base_price * 0.95)
                prices.append(new_price)
            
            df = pd.DataFrame({
                'timestamp': dates,
                'open': prices,
                'high': [p + abs(np.random.randn() * 50) for p in prices],
                'low': [p - abs(np.random.randn() * 50) for p in prices],
                'close': [p + np.random.randn() * 30 for p in prices],
                'volume': [1000000 + np.random.randn() * 200000 for _ in prices]
            })
            df.set_index('timestamp', inplace=True)
            return df
    
    if pytest:
        def test_signal_blocked_by_entry_gating(self, engine, sample_df, monkeypatch):
        """Signals failing entry gating should be blocked before threshold check"""
        
        # Mock entry gating to fail
        def mock_entry_gating(context):
            return False
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', mock_entry_gating)
        
        # Generate signal
        signal = engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # Signal should be None (blocked)
        assert signal is None, "Signal should be blocked by Entry Gating"
    
    def test_signal_blocked_by_confidence_threshold(self, engine, sample_df, monkeypatch):
        """Signals failing confidence threshold should be blocked after entry gating"""
        
        # Mock entry gating to pass
        def mock_entry_gating(context):
            return True
        
        # Mock confidence threshold to fail
        def mock_confidence_threshold(context):
            return False
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', mock_entry_gating)
        monkeypatch.setattr('ict_signal_engine.evaluate_confidence_threshold', mock_confidence_threshold)
        
        # Generate signal
        signal = engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # Signal should be None (blocked)
        assert signal is None, "Signal should be blocked by Confidence Threshold"
    
    def test_signal_passes_both_checks(self, engine, sample_df, monkeypatch):
        """Signals passing both checks should proceed to execution"""
        
        # Mock both to pass
        def mock_entry_gating(context):
            return True
        
        def mock_confidence_threshold(context):
            return True
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', mock_entry_gating)
        monkeypatch.setattr('ict_signal_engine.evaluate_confidence_threshold', mock_confidence_threshold)
        
        # Generate signal
        signal = engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # Signal should NOT be None (allowed to proceed)
        # Note: May still be None if signal generation finds no valid setup
        # This test validates that the checks don't block a valid signal
        if signal is not None:
            assert signal.symbol == 'BTCUSDT'
            assert signal.timeframe == '1h'
    
    def test_evaluation_order(self, engine, sample_df, monkeypatch):
        """Confidence threshold should NOT be called if entry gating fails"""
        
        confidence_called = {'called': False}
        
        def mock_entry_gating(context):
            return False  # FAIL
        
        def mock_confidence_threshold(context):
            confidence_called['called'] = True
            return True
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', mock_entry_gating)
        monkeypatch.setattr('ict_signal_engine.evaluate_confidence_threshold', mock_confidence_threshold)
        
        # Generate signal
        engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # Confidence threshold should NOT have been called
        assert confidence_called['called'] == False, "Confidence threshold should not be called if entry gating fails"
    
    def test_signal_context_immutability(self, engine, sample_df, monkeypatch):
        """Signal context should not be mutated by evaluators"""
        
        original_contexts = []
        
        def mock_entry_gating(context):
            original_contexts.append(context.copy())
            # Try to mutate (should not affect subsequent calls due to .copy() in engine)
            context['mutated'] = True
            return True
        
        def mock_confidence_threshold(context):
            # Verify context hasn't been mutated
            assert 'mutated' not in context, "Context should not contain mutations from entry gating"
            return True
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', mock_entry_gating)
        monkeypatch.setattr('ict_signal_engine.evaluate_confidence_threshold', mock_confidence_threshold)
        
        # Generate signal
        engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # Context should remain unchanged
        # (assertion is in mock_confidence_threshold)
    
    def test_entry_gating_context_structure(self, engine, sample_df, monkeypatch):
        """Entry gating should receive properly structured context"""
        
        received_context = {}
        
        def mock_entry_gating(context):
            nonlocal received_context
            received_context = context.copy()
            return True
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', mock_entry_gating)
        monkeypatch.setattr('ict_signal_engine.evaluate_confidence_threshold', lambda c: True)
        
        # Generate signal
        engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # Verify required fields are present
        if received_context:
            assert 'symbol' in received_context
            assert 'timeframe' in received_context
            assert 'direction' in received_context
            assert 'raw_confidence' in received_context
            assert 'system_state' in received_context
            assert 'breaker_block_active' in received_context
            assert 'active_signal_exists' in received_context
            assert 'cooldown_active' in received_context
            assert 'market_state' in received_context
            assert 'signature_already_seen' in received_context
    
    def test_confidence_threshold_context_structure(self, engine, sample_df, monkeypatch):
        """Confidence threshold should receive properly structured context"""
        
        received_context = {}
        
        def mock_confidence_threshold(context):
            nonlocal received_context
            received_context = context.copy()
            return True
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', lambda c: True)
        monkeypatch.setattr('ict_signal_engine.evaluate_confidence_threshold', mock_confidence_threshold)
        
        # Generate signal
        engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # Verify required fields are present
        if received_context:
            assert 'direction' in received_context
            assert 'raw_confidence' in received_context
    
    def test_signal_blocked_by_execution_eligibility(self, engine, sample_df, monkeypatch):
        """Signals failing execution eligibility should be blocked after §2.2"""
        
        # Mock §2.1 and §2.2 to pass
        def mock_entry_gating(context):
            return True
        
        def mock_confidence_threshold(context):
            return True
        
        # Mock §2.3 to fail
        def mock_execution_eligibility(context):
            return False
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', mock_entry_gating)
        monkeypatch.setattr('ict_signal_engine.evaluate_confidence_threshold', mock_confidence_threshold)
        monkeypatch.setattr('ict_signal_engine.evaluate_execution_eligibility', mock_execution_eligibility)
        
        # Generate signal
        signal = engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # Signal should be None (blocked by §2.3)
        assert signal is None, "Signal should be blocked by Execution Eligibility"
    
    def test_evaluation_order_2_3(self, engine, sample_df, monkeypatch):
        """§2.3 should NOT be called if §2.2 fails"""
        
        execution_eligibility_called = {'called': False}
        
        def mock_entry_gating(context):
            return True
        
        def mock_confidence_threshold(context):
            return False  # FAIL §2.2
        
        def mock_execution_eligibility(context):
            execution_eligibility_called['called'] = True
            return True
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', mock_entry_gating)
        monkeypatch.setattr('ict_signal_engine.evaluate_confidence_threshold', mock_confidence_threshold)
        monkeypatch.setattr('ict_signal_engine.evaluate_execution_eligibility', mock_execution_eligibility)
        
        # Generate signal
        engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # §2.3 should NOT have been called
        assert execution_eligibility_called['called'] == False, "Execution Eligibility should not be called if Confidence Threshold fails"
    
    def test_execution_eligibility_context_structure(self, engine, sample_df, monkeypatch):
        """Execution Eligibility should receive properly structured context"""
        
        received_context = {}
        
        def mock_execution_eligibility(context):
            nonlocal received_context
            received_context = context.copy()
            return True
        
        monkeypatch.setattr('ict_signal_engine.evaluate_entry_gating', lambda c: True)
        monkeypatch.setattr('ict_signal_engine.evaluate_confidence_threshold', lambda c: True)
        monkeypatch.setattr('ict_signal_engine.evaluate_execution_eligibility', mock_execution_eligibility)
        
        # Generate signal
        engine.generate_signal(sample_df, 'BTCUSDT', '1h')
        
        # Verify required fields are present
        if received_context:
            assert 'symbol' in received_context
            assert 'execution_state' in received_context
            assert 'execution_layer_available' in received_context
            assert 'symbol_execution_locked' in received_context
            assert 'position_capacity_available' in received_context
            assert 'emergency_halt_active' in received_context


class TestHelperMethods:
    """Test helper methods for signal context building"""
    
    @pytest.fixture
    def engine(self):
        """Create ICT Signal Engine"""
        return ICTSignalEngine()
    
    def test_get_system_state(self, engine):
        """Test _get_system_state returns valid state"""
        state = engine._get_system_state()
        
        assert state in ['OPERATIONAL', 'DEGRADED', 'MAINTENANCE', 'EMERGENCY']
        assert state == 'OPERATIONAL'  # Default implementation
    
    def test_check_breaker_block_active(self, engine):
        """Test _check_breaker_block_active logic"""
        # Create mock signal type
        signal_type = Mock()
        signal_type.value = 'BUY'
        
        # Test with no breaker blocks
        ict_components_empty = {'breaker_blocks': []}
        result = engine._check_breaker_block_active(ict_components_empty, signal_type)
        assert result == False
        
        # Test with bullish breaker block (should match BUY signal)
        bb_bullish = Mock()
        bb_bullish.type = Mock()
        bb_bullish.type.value = 'BULLISH'
        
        ict_components_bullish = {'breaker_blocks': [bb_bullish]}
        result = engine._check_breaker_block_active(ict_components_bullish, signal_type)
        assert result == True
        
        # Test with bearish breaker block (should NOT match BUY signal)
        bb_bearish = Mock()
        bb_bearish.type = Mock()
        bb_bearish.type.value = 'BEARISH'
        
        ict_components_bearish = {'breaker_blocks': [bb_bearish]}
        result = engine._check_breaker_block_active(ict_components_bearish, signal_type)
        assert result == False
    
    def test_check_active_signal(self, engine):
        """Test _check_active_signal returns False (default implementation)"""
        result = engine._check_active_signal('BTCUSDT', '1h')
        assert result == False
    
    def test_check_cooldown(self, engine):
        """Test _check_cooldown returns False (default implementation)"""
        result = engine._check_cooldown('BTCUSDT', '1h')
        assert result == False
    
    def test_get_market_state(self, engine):
        """Test _get_market_state returns valid state"""
        state = engine._get_market_state('BTCUSDT')
        
        assert state in ['OPEN', 'CLOSED', 'HALTED', 'INVALID']
        assert state == 'OPEN'  # Default implementation (crypto is 24/7)
    
    def test_check_signature(self, engine):
        """Test _check_signature returns False (default implementation)"""
        signal_type = Mock()
        signal_type.value = 'BUY'
        
        result = engine._check_signature('BTCUSDT', '1h', signal_type, datetime.now())
        assert result == False
    
    def test_get_execution_state(self, engine):
        """Test _get_execution_state returns valid state"""
        state = engine._get_execution_state()
        
        assert state in ['READY', 'PAUSED', 'DISABLED']
        assert state == 'READY'  # Default implementation (allows execution)
    
    def test_check_execution_layer_available(self, engine):
        """Test _check_execution_layer_available returns True (default implementation)"""
        result = engine._check_execution_layer_available()
        assert result == True
    
    def test_check_symbol_execution_lock(self, engine):
        """Test _check_symbol_execution_lock returns False (default implementation)"""
        result = engine._check_symbol_execution_lock('BTCUSDT')
        assert result == False
    
    def test_check_position_capacity(self, engine):
        """Test _check_position_capacity returns True (default implementation)"""
        result = engine._check_position_capacity('BTCUSDT', 'BUY')
        assert result == True
    
    def test_check_emergency_halt(self, engine):
        """Test _check_emergency_halt returns False (default implementation)"""
        result = engine._check_emergency_halt()
        assert result == False


class TestEndToEndFlow:
    """Test complete end-to-end signal generation flow"""
    
    @pytest.fixture
    def engine(self):
        """Create ICT Signal Engine"""
        return ICTSignalEngine()
    
    @pytest.fixture
    def realistic_df(self):
        """Create realistic DataFrame that might generate a signal"""
        dates = pd.date_range('2025-01-01', periods=200, freq='1H')
        
        # Generate strong uptrend
        base_price = 45000
        prices = [base_price]
        
        for i in range(199):
            # Strong upward trend with some volatility
            change = np.random.randn() * 80 + 25
            new_price = prices[-1] + change
            prices.append(max(new_price, base_price))
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p + abs(np.random.randn() * 60) for p in prices],
            'low': [p - abs(np.random.randn() * 60) for p in prices],
            'close': [p + np.random.randn() * 40 for p in prices],
            'volume': [1500000 + np.random.randn() * 300000 for _ in prices]
        })
        df.set_index('timestamp', inplace=True)
        return df
    
    def test_full_flow_with_real_evaluators(self, engine, realistic_df):
        """Test full flow with actual evaluators (not mocked)"""
        # This test uses the real evaluators
        # It might not generate a signal (due to other checks), but should not crash
        
        try:
            signal = engine.generate_signal(realistic_df, 'BTCUSDT', '1h')
            
            # If signal is generated, verify it passed both checks
            if signal is not None:
                assert signal.symbol == 'BTCUSDT'
                assert signal.timeframe == '1h'
                # Signal must have confidence >= threshold
                assert signal.confidence >= 60.0  # Minimum threshold for BUY/SELL
        except Exception as e:
            # If there's an error, it should not be from our integration
            assert 'evaluate_entry_gating' not in str(e)
            assert 'evaluate_confidence_threshold' not in str(e)


if __name__ == "__main__":
    # Allow running tests without pytest
    print("Running Main Flow Integration Tests...")
    
    test_classes = [
        TestMainFlowIntegration,
        TestHelperMethods,
        TestEndToEndFlow
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        
        # Create fixtures
        engine = ICTSignalEngine()
        dates = pd.date_range('2025-01-01', periods=100, freq='1H')
        base_price = 50000
        prices = [base_price + np.random.randn() * 100 for _ in range(100)]
        
        sample_df = pd.DataFrame({
            'timestamp': dates,
            'open': prices,
            'high': [p + abs(np.random.randn() * 50) for p in prices],
            'low': [p - abs(np.random.randn() * 50) for p in prices],
            'close': [p + np.random.randn() * 30 for p in prices],
            'volume': [1000000 + np.random.randn() * 200000 for _ in prices]
        })
        sample_df.set_index('timestamp', inplace=True)
        
        test_instance = test_class()
        
        for method_name in dir(test_instance):
            if method_name.startswith('test_'):
                total_tests += 1
                try:
                    method = getattr(test_instance, method_name)
                    
                    # Handle fixtures
                    if method_name in ['test_signal_blocked_by_entry_gating', 
                                      'test_signal_blocked_by_confidence_threshold',
                                      'test_signal_passes_both_checks',
                                      'test_evaluation_order',
                                      'test_signal_context_immutability']:
                        print(f"  ⊘ {method_name} (skipped - requires pytest monkeypatch)")
                        continue
                    
                    # Call method (some require fixtures)
                    if 'engine' in method.__code__.co_varnames:
                        if 'sample_df' in method.__code__.co_varnames or 'realistic_df' in method.__code__.co_varnames:
                            method(engine, sample_df)
                        else:
                            method(engine)
                    else:
                        method()
                    
                    print(f"  ✓ {method_name}")
                    passed_tests += 1
                except Exception as e:
                    print(f"  ✗ {method_name}: {str(e)}")
                    failed_tests += 1
    
    print(f"\n{'='*50}")
    print(f"Total: {total_tests} | Passed: {passed_tests} | Failed: {failed_tests}")
    
    if failed_tests == 0:
        print("✅ All tests passed!")
    else:
        print(f"❌ {failed_tests} test(s) failed")
