"""
Unit tests for Confidence Threshold Evaluator (ESB v1.0 §2.2)

Author: galinborisov10-art
Date: 2026-01-21
"""

try:
    import pytest
except ImportError:
    pytest = None

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from confidence_threshold_evaluator import evaluate_confidence_threshold, CONFIDENCE_THRESHOLDS


class TestConfidenceThresholds:
    """Test confidence threshold evaluation"""
    
    def test_buy_threshold_pass(self):
        """BUY signal with confidence >= 60.0 should pass"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 65.0
        }
        assert evaluate_confidence_threshold(signal_context) == True
    
    def test_buy_threshold_fail(self):
        """BUY signal with confidence < 60.0 should fail"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 55.0
        }
        assert evaluate_confidence_threshold(signal_context) == False
    
    def test_buy_threshold_exact(self):
        """BUY signal with confidence = 60.0 should pass"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 60.0
        }
        assert evaluate_confidence_threshold(signal_context) == True
    
    def test_sell_threshold_pass(self):
        """SELL signal with confidence >= 60.0 should pass"""
        signal_context = {
            'direction': 'SELL',
            'raw_confidence': 62.0
        }
        assert evaluate_confidence_threshold(signal_context) == True
    
    def test_sell_threshold_fail(self):
        """SELL signal with confidence < 60.0 should fail"""
        signal_context = {
            'direction': 'SELL',
            'raw_confidence': 58.0
        }
        assert evaluate_confidence_threshold(signal_context) == False
    
    def test_strong_buy_threshold_pass(self):
        """STRONG_BUY signal with confidence >= 70.0 should pass"""
        signal_context = {
            'direction': 'STRONG_BUY',
            'raw_confidence': 75.0
        }
        assert evaluate_confidence_threshold(signal_context) == True
    
    def test_strong_buy_threshold_fail(self):
        """STRONG_BUY signal with confidence < 70.0 should fail"""
        signal_context = {
            'direction': 'STRONG_BUY',
            'raw_confidence': 65.0
        }
        assert evaluate_confidence_threshold(signal_context) == False
    
    def test_strong_sell_threshold_pass(self):
        """STRONG_SELL signal with confidence >= 70.0 should pass"""
        signal_context = {
            'direction': 'STRONG_SELL',
            'raw_confidence': 72.0
        }
        assert evaluate_confidence_threshold(signal_context) == True
    
    def test_strong_sell_threshold_fail(self):
        """STRONG_SELL signal with confidence < 70.0 should fail"""
        signal_context = {
            'direction': 'STRONG_SELL',
            'raw_confidence': 68.0
        }
        assert evaluate_confidence_threshold(signal_context) == False


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_confidence_zero(self):
        """Confidence = 0 should always fail"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 0.0
        }
        assert evaluate_confidence_threshold(signal_context) == False
    
    def test_confidence_one_below_threshold(self):
        """Confidence = threshold - 0.01 should fail"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 59.99
        }
        assert evaluate_confidence_threshold(signal_context) == False
    
    def test_confidence_one_above_threshold(self):
        """Confidence = threshold + 0.01 should pass"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 60.01
        }
        assert evaluate_confidence_threshold(signal_context) == True
    
    def test_confidence_hundred(self):
        """Confidence = 100 should always pass"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 100.0
        }
        assert evaluate_confidence_threshold(signal_context) == True
    
    def test_missing_direction(self):
        """Missing direction should fail"""
        signal_context = {
            'raw_confidence': 75.0
        }
        assert evaluate_confidence_threshold(signal_context) == False
    
    def test_missing_confidence(self):
        """Missing raw_confidence should fail"""
        signal_context = {
            'direction': 'BUY'
        }
        assert evaluate_confidence_threshold(signal_context) == False
    
    def test_invalid_direction(self):
        """Invalid direction should fail"""
        signal_context = {
            'direction': 'INVALID',
            'raw_confidence': 75.0
        }
        assert evaluate_confidence_threshold(signal_context) == False
    
    def test_none_confidence(self):
        """None confidence should fail"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': None
        }
        assert evaluate_confidence_threshold(signal_context) == False


class TestBehavioralGuarantees:
    """Test behavioral guarantees"""
    
    def test_signal_immutability(self):
        """Signal context should not be mutated"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 65.0,
            'symbol': 'BTCUSDT'
        }
        
        context_copy = signal_context.copy()
        
        # Evaluate
        evaluate_confidence_threshold(signal_context)
        
        # Signal context must remain unchanged
        assert signal_context == context_copy
    
    def test_deterministic_behavior(self):
        """Same input should always produce same output"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 65.0
        }
        
        # Evaluate multiple times
        result1 = evaluate_confidence_threshold(signal_context)
        result2 = evaluate_confidence_threshold(signal_context)
        result3 = evaluate_confidence_threshold(signal_context)
        
        # All results must be identical
        assert result1 == result2 == result3 == True
    
    def test_independence_from_execution_context(self):
        """Execution context fields should be ignored"""
        signal_context = {
            'direction': 'BUY',
            'raw_confidence': 65.0,
            # Execution context (should be ignored)
            'position_size': 1000,
            'leverage': 5,
            'account_balance': 10000,
            'entry_price': 50000.0
        }
        
        # Should pass (execution fields ignored)
        assert evaluate_confidence_threshold(signal_context) == True
    
    def test_always_returns_boolean(self):
        """Function should always return boolean"""
        
        # Valid context
        context_valid = {'direction': 'BUY', 'raw_confidence': 65.0}
        result_valid = evaluate_confidence_threshold(context_valid)
        assert isinstance(result_valid, bool)
        
        # Invalid context
        context_invalid = {'direction': 'INVALID', 'raw_confidence': 65.0}
        result_invalid = evaluate_confidence_threshold(context_invalid)
        assert isinstance(result_invalid, bool)


class TestAllThresholds:
    """Comprehensive test of all thresholds"""
    
    def test_all_directions_at_threshold(self):
        """Test all directions at exact threshold value"""
        for direction, threshold in CONFIDENCE_THRESHOLDS.items():
            signal_context = {
                'direction': direction,
                'raw_confidence': threshold
            }
            assert evaluate_confidence_threshold(signal_context) == True, \
                f"{direction} at threshold {threshold} should pass"
    
    def test_all_directions_below_threshold(self):
        """Test all directions below threshold value"""
        for direction, threshold in CONFIDENCE_THRESHOLDS.items():
            signal_context = {
                'direction': direction,
                'raw_confidence': threshold - 1.0
            }
            assert evaluate_confidence_threshold(signal_context) == False, \
                f"{direction} below threshold {threshold} should fail"
    
    def test_all_directions_above_threshold(self):
        """Test all directions above threshold value"""
        for direction, threshold in CONFIDENCE_THRESHOLDS.items():
            signal_context = {
                'direction': direction,
                'raw_confidence': threshold + 10.0
            }
            assert evaluate_confidence_threshold(signal_context) == True, \
                f"{direction} above threshold {threshold} should pass"


if __name__ == '__main__':
    # Allow running tests without pytest
    print("Running Confidence Threshold Tests...")
    
    test_classes = [
        TestConfidenceThresholds,
        TestEdgeCases,
        TestBehavioralGuarantees,
        TestAllThresholds
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n{test_class.__name__}:")
        test_instance = test_class()
        
        for method_name in dir(test_instance):
            if method_name.startswith('test_'):
                total_tests += 1
                try:
                    method = getattr(test_instance, method_name)
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
