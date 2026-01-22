"""
Unit tests for Risk Admission Evaluator (ESB v1.0 §2.4)
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from risk_admission_evaluator import (
    evaluate_risk_admission,
    MAX_RISK_PER_SIGNAL,
    MAX_TOTAL_OPEN_RISK,
    MAX_SYMBOL_EXPOSURE,
    MAX_DIRECTION_EXPOSURE,
    MAX_DAILY_LOSS
)


class TestRiskAdmissionGates:
    """Test individual risk admission gates"""
    
    def test_ra01_signal_risk_pass(self):
        """RA-01: signal_risk <= 1.5% should pass"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 1.0
        }
        assert evaluate_risk_admission(context) == True
    
    def test_ra01_signal_risk_fail(self):
        """RA-01: signal_risk > 1.5% should fail"""
        context = {
            'signal_risk': 2.0,  # EXCEEDS 1.5%
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 1.0
        }
        assert evaluate_risk_admission(context) == False
    
    def test_ra01_signal_risk_exact_limit(self):
        """RA-01: signal_risk = 1.5% should pass"""
        context = {
            'signal_risk': 1.5,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 1.0
        }
        assert evaluate_risk_admission(context) == True
    
    def test_ra02_total_open_risk_pass(self):
        """RA-02: total_open_risk <= 7.0% should pass"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 6.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 1.0
        }
        assert evaluate_risk_admission(context) == True
    
    def test_ra02_total_open_risk_fail(self):
        """RA-02: total_open_risk > 7.0% should fail"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 8.0,  # EXCEEDS 7.0%
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 1.0
        }
        assert evaluate_risk_admission(context) == False
    
    def test_ra03_symbol_exposure_pass(self):
        """RA-03: symbol_exposure <= 3.0% should pass"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.5,
            'direction_exposure': 3.0,
            'daily_loss': 1.0
        }
        assert evaluate_risk_admission(context) == True
    
    def test_ra03_symbol_exposure_fail(self):
        """RA-03: symbol_exposure > 3.0% should fail"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 3.5,  # EXCEEDS 3.0%
            'direction_exposure': 3.0,
            'daily_loss': 1.0
        }
        assert evaluate_risk_admission(context) == False
    
    def test_ra04_direction_exposure_pass(self):
        """RA-04: direction_exposure <= 4.0% should pass"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.5,
            'daily_loss': 1.0
        }
        assert evaluate_risk_admission(context) == True
    
    def test_ra04_direction_exposure_fail(self):
        """RA-04: direction_exposure > 4.0% should fail"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 4.5,  # EXCEEDS 4.0%
            'daily_loss': 1.0
        }
        assert evaluate_risk_admission(context) == False
    
    def test_ra05_daily_loss_pass(self):
        """RA-05: daily_loss <= 4.0% should pass"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 3.5
        }
        assert evaluate_risk_admission(context) == True
    
    def test_ra05_daily_loss_fail(self):
        """RA-05: daily_loss > 4.0% should fail"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 4.5  # EXCEEDS 4.0%
        }
        assert evaluate_risk_admission(context) == False


class TestRiskAdmissionBehavior:
    """Test behavioral guarantees"""
    
    def test_all_gates_pass(self):
        """All gates passing should return True"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 2.0
        }
        assert evaluate_risk_admission(context) == True
    
    def test_any_single_gate_failure_blocks(self):
        """Any single gate failure should block"""
        base_context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 2.0
        }
        
        # Test each gate individually
        failures = [
            {'signal_risk': 2.0},        # RA-01 fail
            {'total_open_risk': 8.0},    # RA-02 fail
            {'symbol_exposure': 3.5},    # RA-03 fail
            {'direction_exposure': 4.5}, # RA-04 fail
            {'daily_loss': 4.5}          # RA-05 fail
        ]
        
        for failure in failures:
            context = {**base_context, **failure}
            assert evaluate_risk_admission(context) == False
    
    def test_context_immutability(self):
        """Context should not be mutated"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 2.0
        }
        
        context_copy = context.copy()
        evaluate_risk_admission(context)
        
        assert context == context_copy
    
    def test_deterministic_behavior(self):
        """Same input should always produce same output"""
        context = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 2.0
        }
        
        result1 = evaluate_risk_admission(context)
        result2 = evaluate_risk_admission(context)
        result3 = evaluate_risk_admission(context)
        
        assert result1 == result2 == result3 == True
    
    def test_missing_fields_fail(self):
        """Missing required fields should fail"""
        
        # Missing signal_risk
        context_no_signal_risk = {
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 2.0
        }
        assert evaluate_risk_admission(context_no_signal_risk) == False
        
        # Missing daily_loss
        context_no_daily_loss = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0
        }
        assert evaluate_risk_admission(context_no_daily_loss) == False
    
    def test_always_returns_boolean(self):
        """Function should always return boolean"""
        
        # Valid context
        context_valid = {
            'signal_risk': 1.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 2.0
        }
        result_valid = evaluate_risk_admission(context_valid)
        assert isinstance(result_valid, bool)
        
        # Invalid context (exceeds limits)
        context_invalid = {
            'signal_risk': 10.0,
            'total_open_risk': 5.0,
            'symbol_exposure': 2.0,
            'direction_exposure': 3.0,
            'daily_loss': 2.0
        }
        result_invalid = evaluate_risk_admission(context_invalid)
        assert isinstance(result_invalid, bool)


class TestEvaluationOrder:
    """Test that gates are evaluated in fixed order"""
    
    def test_multiple_failures_short_circuit(self):
        """First failure should short-circuit"""
        context = {
            'signal_risk': 10.0,       # RA-01 FAIL
            'total_open_risk': 20.0,   # RA-02 FAIL
            'symbol_exposure': 10.0,   # RA-03 FAIL
            'direction_exposure': 10.0, # RA-04 FAIL
            'daily_loss': 10.0         # RA-05 FAIL
        }
        
        # Should fail immediately on first gate
        assert evaluate_risk_admission(context) == False
    
    def test_all_limits_at_exact_threshold(self):
        """All metrics at exact threshold should pass"""
        context = {
            'signal_risk': MAX_RISK_PER_SIGNAL,
            'total_open_risk': MAX_TOTAL_OPEN_RISK,
            'symbol_exposure': MAX_SYMBOL_EXPOSURE,
            'direction_exposure': MAX_DIRECTION_EXPOSURE,
            'daily_loss': MAX_DAILY_LOSS
        }
        assert evaluate_risk_admission(context) == True
