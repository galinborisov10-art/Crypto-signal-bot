"""
Unit tests for Execution Eligibility Evaluator (ESB v1.0 §2.3)
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from execution_eligibility_evaluator import evaluate_execution_eligibility


class TestExecutionEligibilityGates:
    """Test individual execution eligibility gates"""
    
    def test_ee01_execution_state_ready_pass(self):
        """EE-01: execution_state = READY should pass"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == True
    
    def test_ee01_execution_state_paused_fail(self):
        """EE-01: execution_state = PAUSED should fail"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'PAUSED',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == False
    
    def test_ee01_execution_state_disabled_fail(self):
        """EE-01: execution_state = DISABLED should fail"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'DISABLED',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == False
    
    def test_ee02_execution_layer_available_pass(self):
        """EE-02: execution_layer_available = True should pass"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == True
    
    def test_ee02_execution_layer_unavailable_fail(self):
        """EE-02: execution_layer_available = False should fail"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': False,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == False
    
    def test_ee03_symbol_not_locked_pass(self):
        """EE-03: symbol_execution_locked = False should pass"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == True
    
    def test_ee03_symbol_locked_fail(self):
        """EE-03: symbol_execution_locked = True should fail"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': True,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == False
    
    def test_ee04_position_capacity_available_pass(self):
        """EE-04: position_capacity_available = True should pass"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == True
    
    def test_ee04_position_capacity_unavailable_fail(self):
        """EE-04: position_capacity_available = False should fail"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': False,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == False
    
    def test_ee05_emergency_halt_inactive_pass(self):
        """EE-05: emergency_halt_active = False should pass"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == True
    
    def test_ee05_emergency_halt_active_fail(self):
        """EE-05: emergency_halt_active = True should fail"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': True
        }
        assert evaluate_execution_eligibility(context) == False


class TestExecutionEligibilityBehavior:
    """Test behavioral guarantees"""
    
    def test_all_gates_pass(self):
        """All gates passing should return True"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context) == True
    
    def test_any_single_gate_failure_blocks(self):
        """Any single gate failure should block"""
        base_context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        
        # Test each gate individually
        failures = [
            {'execution_state': 'PAUSED'},
            {'execution_layer_available': False},
            {'symbol_execution_locked': True},
            {'position_capacity_available': False},
            {'emergency_halt_active': True}
        ]
        
        for failure in failures:
            context = {**base_context, **failure}
            assert evaluate_execution_eligibility(context) == False
    
    def test_context_immutability(self):
        """Context should not be mutated"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        
        context_copy = context.copy()
        evaluate_execution_eligibility(context)
        
        assert context == context_copy
    
    def test_deterministic_behavior(self):
        """Same input should always produce same output"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        
        result1 = evaluate_execution_eligibility(context)
        result2 = evaluate_execution_eligibility(context)
        result3 = evaluate_execution_eligibility(context)
        
        assert result1 == result2 == result3 == True
    
    def test_missing_fields_fail(self):
        """Missing required fields should fail"""
        
        # Missing execution_state
        context_no_state = {
            'symbol': 'BTCUSDT',
            'execution_layer_available': True,
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context_no_state) == False
        
        # Missing execution_layer_available
        context_no_layer = {
            'symbol': 'BTCUSDT',
            'execution_state': 'READY',
            'symbol_execution_locked': False,
            'position_capacity_available': True,
            'emergency_halt_active': False
        }
        assert evaluate_execution_eligibility(context_no_layer) == False


class TestEvaluationOrder:
    """Test that gates are evaluated in fixed order"""
    
    def test_multiple_failures_short_circuit(self):
        """First failure should short-circuit (all gates fail)"""
        context = {
            'symbol': 'BTCUSDT',
            'execution_state': 'DISABLED',  # EE-01 FAIL
            'execution_layer_available': False,  # EE-02 FAIL
            'symbol_execution_locked': True,  # EE-03 FAIL
            'position_capacity_available': False,  # EE-04 FAIL
            'emergency_halt_active': True  # EE-05 FAIL
        }
        
        # Should fail immediately on first gate
        assert evaluate_execution_eligibility(context) == False
