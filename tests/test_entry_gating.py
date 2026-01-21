"""
Entry Gating Tests - ESB v1.0 §2.1

Test suite for entry gating evaluator module.
All tests validate hard boolean blocking rules.

Author: galinborisov10-art
Date: 2026-01-21
"""

import pytest
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from entry_gating_evaluator import evaluate_entry_gating


class TestEntryGating:
    """Test Entry Gating Evaluation"""
    
    def test_entry_gating_independent_of_confidence(self):
        """Entry gating MUST NOT consider confidence value"""
        
        # High confidence signal that fails EG-01
        context_high_conf = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 95.0,  # High confidence
            'system_state': 'DEGRADED'  # Fails EG-01
        }
        assert evaluate_entry_gating(context_high_conf) == False
        
        # Low confidence signal that passes all gates
        context_low_conf = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 10.0,  # Low confidence
            'system_state': 'OPERATIONAL',
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        assert evaluate_entry_gating(context_low_conf) == True
    
    def test_any_single_eg_failure_blocks_entry(self):
        """Any single EG failure MUST force ENTRY_ALLOWED = False"""
        
        base_context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0,
            'system_state': 'OPERATIONAL',
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        
        # Test EG-01 failure
        context_eg01 = {**base_context, 'system_state': 'MAINTENANCE'}
        assert evaluate_entry_gating(context_eg01) == False
        
        # Test EG-02 failure
        context_eg02 = {**base_context, 'breaker_block_active': True}
        assert evaluate_entry_gating(context_eg02) == False
        
        # Test EG-03 failure
        context_eg03 = {**base_context, 'active_signal_exists': True}
        assert evaluate_entry_gating(context_eg03) == False
        
        # Test EG-04 failure
        context_eg04 = {**base_context, 'cooldown_active': True}
        assert evaluate_entry_gating(context_eg04) == False
        
        # Test EG-05 failure
        context_eg05 = {**base_context, 'market_state': 'CLOSED'}
        assert evaluate_entry_gating(context_eg05) == False
        
        # Test EG-07 failure
        context_eg07 = {**base_context, 'signature_already_seen': True}
        assert evaluate_entry_gating(context_eg07) == False
    
    def test_entry_allowed_cannot_flip_after_failure(self):
        """Once blocked, ENTRY_ALLOWED cannot flip to True"""
        
        context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0,
            'system_state': 'EMERGENCY',  # Fails EG-01
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        
        # First evaluation: BLOCKED
        result1 = evaluate_entry_gating(context)
        assert result1 == False
        
        # Second evaluation with same context: STILL BLOCKED
        result2 = evaluate_entry_gating(context)
        assert result2 == False
    
    def test_entry_gating_does_not_access_execution_context(self):
        """Entry gating MUST NOT access execution-related fields"""
        
        context_with_exec = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0,
            'system_state': 'OPERATIONAL',
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False,
            # Execution context (should be ignored)
            'position_size': 1000,
            'leverage': 5,
            'account_balance': 10000
        }
        
        # Should pass (execution fields ignored)
        assert evaluate_entry_gating(context_with_exec) == True
    
    def test_entry_gating_does_not_mutate_signal(self):
        """Entry gating MUST NOT modify the input signal"""
        
        context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0,
            'system_state': 'OPERATIONAL',
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        
        context_copy = context.copy()
        
        # Evaluate
        evaluate_entry_gating(context)
        
        # Context must remain unchanged
        assert context == context_copy
    
    def test_breaker_block_dominates_all_gates(self):
        """Breaker block MUST always block, regardless of other gates"""
        
        # All gates pass EXCEPT breaker block
        context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 95.0,  # High confidence
            'system_state': 'OPERATIONAL',
            'breaker_block_active': True,  # ACTIVE BREAKER BLOCK
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        
        assert evaluate_entry_gating(context) == False
    
    def test_structural_integrity_missing_required_fields(self):
        """Missing required fields MUST block entry"""
        
        # Missing 'symbol'
        context_no_symbol = {
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0
        }
        assert evaluate_entry_gating(context_no_symbol) == False
        
        # Missing 'direction'
        context_no_direction = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'raw_confidence': 75.0
        }
        assert evaluate_entry_gating(context_no_direction) == False
        
        # Invalid direction
        context_invalid_direction = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'INVALID',
            'raw_confidence': 75.0
        }
        assert evaluate_entry_gating(context_invalid_direction) == False
    
    def test_full_pass_all_gates(self):
        """All gates passing MUST result in ENTRY_ALLOWED = True"""
        
        context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0,
            'system_state': 'OPERATIONAL',
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        
        assert evaluate_entry_gating(context) == True


class TestEntryGatingEdgeCases:
    """Test Edge Cases and Boundary Conditions"""
    
    def test_eg01_all_invalid_system_states(self):
        """Test all invalid system states block entry"""
        base_context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0,
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        
        # Test DEGRADED
        context_degraded = {**base_context, 'system_state': 'DEGRADED'}
        assert evaluate_entry_gating(context_degraded) == False
        
        # Test MAINTENANCE
        context_maintenance = {**base_context, 'system_state': 'MAINTENANCE'}
        assert evaluate_entry_gating(context_maintenance) == False
        
        # Test EMERGENCY
        context_emergency = {**base_context, 'system_state': 'EMERGENCY'}
        assert evaluate_entry_gating(context_emergency) == False
    
    def test_eg05_all_invalid_market_states(self):
        """Test all invalid market states block entry"""
        base_context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0,
            'system_state': 'OPERATIONAL',
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'signature_already_seen': False
        }
        
        # Test CLOSED
        context_closed = {**base_context, 'market_state': 'CLOSED'}
        assert evaluate_entry_gating(context_closed) == False
        
        # Test HALTED
        context_halted = {**base_context, 'market_state': 'HALTED'}
        assert evaluate_entry_gating(context_halted) == False
        
        # Test INVALID
        context_invalid = {**base_context, 'market_state': 'INVALID'}
        assert evaluate_entry_gating(context_invalid) == False
    
    def test_eg06_all_valid_directions(self):
        """Test all valid directions pass structural integrity"""
        base_context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'raw_confidence': 75.0,
            'system_state': 'OPERATIONAL',
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        
        # Test BUY
        context_buy = {**base_context, 'direction': 'BUY'}
        assert evaluate_entry_gating(context_buy) == True
        
        # Test SELL
        context_sell = {**base_context, 'direction': 'SELL'}
        assert evaluate_entry_gating(context_sell) == True
        
        # Test STRONG_BUY
        context_strong_buy = {**base_context, 'direction': 'STRONG_BUY'}
        assert evaluate_entry_gating(context_strong_buy) == True
        
        # Test STRONG_SELL
        context_strong_sell = {**base_context, 'direction': 'STRONG_SELL'}
        assert evaluate_entry_gating(context_strong_sell) == True
    
    def test_eg06_empty_string_fields_block_entry(self):
        """Test that empty string fields block entry"""
        base_context = {
            'raw_confidence': 75.0,
            'system_state': 'OPERATIONAL',
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        
        # Empty symbol
        context_empty_symbol = {
            **base_context,
            'symbol': '',
            'timeframe': '1h',
            'direction': 'BUY'
        }
        assert evaluate_entry_gating(context_empty_symbol) == False
        
        # Empty timeframe
        context_empty_timeframe = {
            **base_context,
            'symbol': 'BTCUSDT',
            'timeframe': '',
            'direction': 'BUY'
        }
        assert evaluate_entry_gating(context_empty_timeframe) == False
        
        # Empty direction
        context_empty_direction = {
            **base_context,
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': ''
        }
        assert evaluate_entry_gating(context_empty_direction) == False
    
    def test_eg06_none_raw_confidence_blocks_entry(self):
        """Test that None raw_confidence blocks entry"""
        context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': None,  # None value
            'system_state': 'OPERATIONAL',
            'breaker_block_active': False,
            'active_signal_exists': False,
            'cooldown_active': False,
            'market_state': 'OPEN',
            'signature_already_seen': False
        }
        assert evaluate_entry_gating(context) == False
    
    def test_default_values_allow_entry(self):
        """Test that default values (when not provided) allow entry"""
        # Only required fields provided
        context_minimal = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0
        }
        # Should pass because:
        # - system_state defaults to 'OPERATIONAL'
        # - breaker_block_active defaults to False
        # - active_signal_exists defaults to False
        # - cooldown_active defaults to False
        # - market_state defaults to 'OPEN'
        # - signature_already_seen defaults to False
        assert evaluate_entry_gating(context_minimal) == True
    
    def test_multiple_failures_still_return_false(self):
        """Test that multiple gate failures still return False"""
        context = {
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'direction': 'BUY',
            'raw_confidence': 75.0,
            'system_state': 'EMERGENCY',  # EG-01 FAIL
            'breaker_block_active': True,  # EG-02 FAIL
            'active_signal_exists': True,  # EG-03 FAIL
            'cooldown_active': True,  # EG-04 FAIL
            'market_state': 'CLOSED',  # EG-05 FAIL
            'signature_already_seen': True  # EG-07 FAIL
        }
        assert evaluate_entry_gating(context) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
