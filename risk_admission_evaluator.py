"""
Risk Admission Evaluator (ESB v1.0 §2.4)

Implements hard boolean risk gates to determine if a signal meets risk limits.
This is the FINAL gate before signal creation.
Only evaluated after §2.1, §2.2, and §2.3 pass.
"""

from typing import Dict
import logging

logger = logging.getLogger(__name__)

# Fixed risk limits (ESB v1.0 §2.4)
MAX_RISK_PER_SIGNAL = 1.5      # % of account at risk per signal
MAX_TOTAL_OPEN_RISK = 7.0      # % total open risk across all positions
MAX_SYMBOL_EXPOSURE = 3.0      # % exposure to single symbol
MAX_DIRECTION_EXPOSURE = 4.0   # % exposure to single direction (LONG/SHORT)
MAX_DAILY_LOSS = 4.0           # % maximum daily loss


def evaluate_risk_admission(context: Dict) -> bool:
    """
    Evaluate if signal meets risk admission limits (ESB v1.0 §2.4)
    
    Prerequisite: Signal must have already passed:
        - §2.1 Entry Gating
        - §2.2 Confidence Threshold
        - §2.3 Execution Eligibility
    
    Args:
        context: Dictionary containing risk metrics
            Required keys:
            - 'signal_risk': float (% of account at risk)
            - 'total_open_risk': float (% total open risk)
            - 'symbol_exposure': float (% exposure to this symbol)
            - 'direction_exposure': float (% exposure to this direction)
            - 'daily_loss': float (% daily loss)
    
    Returns:
        bool: True if risk admission allowed, False if HARD BLOCKED
    
    Risk Limits (FIXED):
        MAX_RISK_PER_SIGNAL     = 1.5%
        MAX_TOTAL_OPEN_RISK     = 7.0%
        MAX_SYMBOL_EXPOSURE     = 3.0%
        MAX_DIRECTION_EXPOSURE  = 4.0%
        MAX_DAILY_LOSS          = 4.0%
    
    Evaluation Order (FIXED, short-circuit on first fail):
        RA-01: signal_risk > MAX_RISK_PER_SIGNAL
        RA-02: total_open_risk > MAX_TOTAL_OPEN_RISK
        RA-03: symbol_exposure > MAX_SYMBOL_EXPOSURE
        RA-04: direction_exposure > MAX_DIRECTION_EXPOSURE
        RA-05: daily_loss > MAX_DAILY_LOSS
    
    Behavioral Guarantees:
        - Deterministic output
        - Does not mutate context
        - Missing fields → HARD BLOCK
        - Always returns boolean
        - Logs INFO on block with gate ID and values
        - Logs DEBUG on full pass
    
    Examples:
        >>> evaluate_risk_admission({
        ...     'signal_risk': 1.0,
        ...     'total_open_risk': 5.0,
        ...     'symbol_exposure': 2.0,
        ...     'direction_exposure': 3.0,
        ...     'daily_loss': 1.0
        ... })
        True
        
        >>> evaluate_risk_admission({
        ...     'signal_risk': 2.0,  # EXCEEDS 1.5%
        ...     'total_open_risk': 5.0,
        ...     'symbol_exposure': 2.0,
        ...     'direction_exposure': 3.0,
        ...     'daily_loss': 1.0
        ... })
        False
    """
    # Extract required fields
    signal_risk = context.get('signal_risk')
    total_open_risk = context.get('total_open_risk')
    symbol_exposure = context.get('symbol_exposure')
    direction_exposure = context.get('direction_exposure')
    daily_loss = context.get('daily_loss')
    
    # Validate all fields exist
    if any(x is None for x in [signal_risk, total_open_risk, symbol_exposure, direction_exposure, daily_loss]):
        logger.warning("RA BLOCKED: Missing required risk fields")
        return False
    
    # ===== RA-01: Signal Risk Per Position =====
    if signal_risk > MAX_RISK_PER_SIGNAL:
        logger.info(f"RA-01 BLOCKED: Signal risk {signal_risk:.2f}% > {MAX_RISK_PER_SIGNAL}%")
        return False
    
    # ===== RA-02: Total Open Risk =====
    if total_open_risk > MAX_TOTAL_OPEN_RISK:
        logger.info(f"RA-02 BLOCKED: Total open risk {total_open_risk:.2f}% > {MAX_TOTAL_OPEN_RISK}%")
        return False
    
    # ===== RA-03: Symbol Exposure =====
    if symbol_exposure > MAX_SYMBOL_EXPOSURE:
        logger.info(f"RA-03 BLOCKED: Symbol exposure {symbol_exposure:.2f}% > {MAX_SYMBOL_EXPOSURE}%")
        return False
    
    # ===== RA-04: Direction Exposure =====
    if direction_exposure > MAX_DIRECTION_EXPOSURE:
        logger.info(f"RA-04 BLOCKED: Direction exposure {direction_exposure:.2f}% > {MAX_DIRECTION_EXPOSURE}%")
        return False
    
    # ===== RA-05: Daily Loss Limit =====
    if daily_loss > MAX_DAILY_LOSS:
        logger.info(f"RA-05 BLOCKED: Daily loss {daily_loss:.2f}% > {MAX_DAILY_LOSS}%")
        return False
    
    # All gates passed
    logger.debug(f"✅ Risk Admission PASSED: signal_risk={signal_risk:.2f}%, total={total_open_risk:.2f}%, "
                 f"symbol={symbol_exposure:.2f}%, direction={direction_exposure:.2f}%, daily_loss={daily_loss:.2f}%")
    return True
