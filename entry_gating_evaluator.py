"""
Entry Gating Evaluator - ESB v1.0 §2.1

This module implements Entry Gating rules for ICT signal evaluation.
Entry gating is a hard boolean blocker system that determines if a signal
is allowed to proceed to confidence evaluation and execution.

All gates are deterministic boolean checks.
One FAIL = HARD BLOCK (ENTRY_ALLOWED = False)

Author: galinborisov10-art
Date: 2026-01-21
"""

from typing import Dict


def evaluate_entry_gating(raw_signal_context: Dict) -> bool:
    """
    Evaluate entry gating rules (ESB v1.0 §2.1)
    
    This function evaluates all entry gates in a fixed, deterministic order.
    ALL gates must pass for entry to be allowed.
    
    Entry gates (EG) are hard boolean blockers:
    - EG-01: System State Validity
    - EG-02: Breaker Block Active
    - EG-03: Signal Collision Lock
    - EG-04: Cooldown Gate
    - EG-05: Market Admissibility
    - EG-06: Structural Signal Integrity
    - EG-07: Duplicate Signature Block
    
    Args:
        raw_signal_context: Dictionary containing signal metadata
        
    Returns:
        ENTRY_ALLOWED (bool): True if all gates pass, False if any gate fails
        
    Note:
        - Entry gating is INDEPENDENT of confidence value
        - Entry gating does NOT access execution context
        - Entry gating does NOT modify the input signal
        - No overrides, no fallback - one FAIL = HARD BLOCK
    """
    
    # ========================================================================
    # EG-06: Structural Signal Integrity (MUST BE FIRST)
    # ========================================================================
    # Required fields validation
    required_fields = ['symbol', 'timeframe', 'direction', 'raw_confidence']
    
    for field in required_fields:
        # Check if field exists and is not None
        if field not in raw_signal_context or raw_signal_context[field] is None:
            return False  # HARD BLOCK
        
        # Check if string fields are not empty
        if field in ['symbol', 'timeframe', 'direction']:
            if raw_signal_context[field] == '':
                return False  # HARD BLOCK
    
    # Validate direction value
    valid_directions = ['BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL']
    if raw_signal_context.get('direction') not in valid_directions:
        return False  # HARD BLOCK
    
    # ========================================================================
    # EG-01: System State Validity
    # ========================================================================
    # Check if system is in operational state
    system_state = raw_signal_context.get('system_state', 'OPERATIONAL')
    blocked_states = ['DEGRADED', 'MAINTENANCE', 'EMERGENCY']
    
    if system_state in blocked_states:
        return False  # HARD BLOCK
    
    # ========================================================================
    # EG-02: Breaker Block Active
    # ========================================================================
    # Check if breaker block is active
    breaker_block_active = raw_signal_context.get('breaker_block_active', False)
    
    if breaker_block_active:
        return False  # HARD BLOCK
    
    # ========================================================================
    # EG-03: Signal Collision Lock
    # ========================================================================
    # Check if active signal already exists for same symbol+timeframe
    active_signal_exists = raw_signal_context.get('active_signal_exists', False)
    
    if active_signal_exists:
        return False  # HARD BLOCK
    
    # ========================================================================
    # EG-04: Cooldown Gate
    # ========================================================================
    # Check if cooldown is active for symbol+timeframe
    cooldown_active = raw_signal_context.get('cooldown_active', False)
    
    if cooldown_active:
        return False  # HARD BLOCK
    
    # ========================================================================
    # EG-05: Market Admissibility
    # ========================================================================
    # Check if market is open and tradeable
    market_state = raw_signal_context.get('market_state', 'OPEN')
    invalid_market_states = ['CLOSED', 'HALTED', 'INVALID']
    
    if market_state in invalid_market_states:
        return False  # HARD BLOCK
    
    # ========================================================================
    # EG-07: Duplicate Signature Block
    # ========================================================================
    # Check if signal signature has already been seen
    signature_already_seen = raw_signal_context.get('signature_already_seen', False)
    
    if signature_already_seen:
        return False  # HARD BLOCK
    
    # ========================================================================
    # ALL GATES PASSED
    # ========================================================================
    return True
