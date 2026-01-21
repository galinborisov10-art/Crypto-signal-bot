"""
Confidence Threshold Evaluator (ESB v1.0 §2.2)

Implements deterministic confidence threshold evaluation for signal eligibility.
Only evaluated after ENTRY_ALLOWED == True.

Author: galinborisov10-art
Date: 2026-01-21
"""

from typing import Dict

# Fixed thresholds per direction (ESB v1.0 §2.2)
CONFIDENCE_THRESHOLDS = {
    'BUY': 60.0,
    'SELL': 60.0,
    'STRONG_BUY': 70.0,
    'STRONG_SELL': 70.0
}


def evaluate_confidence_threshold(signal_context: Dict) -> bool:
    """
    Evaluate if signal's raw_confidence meets fixed threshold (ESB v1.0 §2.2)
    
    Args:
        signal_context: Dictionary containing signal metadata
            Required keys:
            - 'direction': str (BUY, SELL, STRONG_BUY, STRONG_SELL)
            - 'raw_confidence': float (0-100)
    
    Returns:
        bool: True if confidence >= threshold, False otherwise
    
    Behavioral Guarantees:
        - Deterministic output
        - Does not mutate signal_context
        - Independent from execution context
        - Hard pass/fail (no soft logic)
        - Always returns boolean
    
    Thresholds:
        BUY: 60.0
        SELL: 60.0
        STRONG_BUY: 70.0
        STRONG_SELL: 70.0
    
    Examples:
        >>> evaluate_confidence_threshold({'direction': 'BUY', 'raw_confidence': 65.0})
        True
        
        >>> evaluate_confidence_threshold({'direction': 'BUY', 'raw_confidence': 55.0})
        False
        
        >>> evaluate_confidence_threshold({'direction': 'STRONG_BUY', 'raw_confidence': 75.0})
        True
    """
    # Extract required fields
    direction = signal_context.get('direction')
    raw_confidence = signal_context.get('raw_confidence')
    
    # Validate required fields exist
    if direction is None or raw_confidence is None:
        return False  # HARD BLOCK: missing required fields
    
    # Lookup threshold
    threshold = CONFIDENCE_THRESHOLDS.get(direction)
    
    # Invalid direction → HARD BLOCK
    if threshold is None:
        return False
    
    # Compare confidence to threshold
    return raw_confidence >= threshold
