"""
Execution Eligibility Evaluator (ESB v1.0 §2.3)

Implements hard boolean gates to determine if a signal is eligible for execution.
Only evaluated after Entry Gating (§2.1) and Confidence Threshold (§2.2) pass.
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)


def evaluate_execution_eligibility(context: Dict) -> bool:
    """
    Evaluate if signal is eligible for execution (ESB v1.0 §2.3)
    
    Prerequisite: Signal must have already passed:
        - Entry Gating (§2.1)
        - Confidence Threshold (§2.2)
    
    Args:
        context: Dictionary containing execution eligibility fields
            Required keys:
            - 'symbol': str
            - 'execution_state': str (READY / PAUSED / DISABLED)
            - 'execution_layer_available': bool
            - 'symbol_execution_locked': bool
            - 'position_capacity_available': bool
            - 'emergency_halt_active': bool
    
    Returns:
        bool: True if eligible for execution, False if HARD BLOCKED
    
    Evaluation Order (FIXED):
        EE-01: Execution System State
        EE-02: Execution Layer Availability
        EE-03: Symbol Execution Lock
        EE-04: Position Capacity Gate
        EE-05: Emergency Execution Halt
    
    Guarantees:
        - Deterministic output
        - Does not mutate context
        - One failure = immediate False
        - No soft logic or overrides
    
    Examples:
        >>> evaluate_execution_eligibility({
        ...     'symbol': 'BTCUSDT',
        ...     'execution_state': 'READY',
        ...     'execution_layer_available': True,
        ...     'symbol_execution_locked': False,
        ...     'position_capacity_available': True,
        ...     'emergency_halt_active': False
        ... })
        True
        
        >>> evaluate_execution_eligibility({
        ...     'symbol': 'BTCUSDT',
        ...     'execution_state': 'PAUSED',  # FAIL
        ...     'execution_layer_available': True,
        ...     'symbol_execution_locked': False,
        ...     'position_capacity_available': True,
        ...     'emergency_halt_active': False
        ... })
        False
    """
    symbol = context.get('symbol', 'UNKNOWN')
    
    # ===== EE-01: Execution System State =====
    execution_state = context.get('execution_state')
    if execution_state != 'READY':
        logger.info(f"EE-01 BLOCKED: Execution state not READY: {execution_state} ({symbol})")
        return False
    
    # ===== EE-02: Execution Layer Availability =====
    execution_layer_available = context.get('execution_layer_available')
    if not execution_layer_available:
        logger.info(f"EE-02 BLOCKED: Execution layer unavailable ({symbol})")
        return False
    
    # ===== EE-03: Symbol Execution Lock =====
    symbol_execution_locked = context.get('symbol_execution_locked')
    if symbol_execution_locked:
        logger.info(f"EE-03 BLOCKED: Symbol execution locked ({symbol})")
        return False
    
    # ===== EE-04: Position Capacity Gate =====
    position_capacity_available = context.get('position_capacity_available')
    if not position_capacity_available:
        logger.info(f"EE-04 BLOCKED: Position capacity unavailable ({symbol})")
        return False
    
    # ===== EE-05: Emergency Execution Halt =====
    emergency_halt_active = context.get('emergency_halt_active')
    if emergency_halt_active:
        logger.info(f"EE-05 BLOCKED: Emergency halt active ({symbol})")
        return False
    
    # All gates passed
    logger.debug(f"✅ Execution Eligibility PASSED: {symbol}")
    return True
