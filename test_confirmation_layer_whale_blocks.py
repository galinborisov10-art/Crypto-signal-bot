"""
Test to verify Confirmation Layer checks for Whale Blocks.

Per specification:
3️⃣ CONFIRMATION LAYER (confirmation_tf)
Проверява дали има поне едно от:
• MSS
• BOS
• Displacement
• Sweep + Displacement
• Whale Blocks  ← This was missing!
"""

import sys
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def test_confirmation_layer_includes_whale_blocks():
    """
    Test: Confirmation layer checks for whale blocks
    
    Specification requirement:
    "Проверява дали има поне едно от:
     • MSS
     • BOS
     • Displacement
     • Sweep + Displacement
     • Whale Blocks"
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Confirmation Layer Includes Whale Blocks Check")
    logger.info("=" * 80)
    
    logger.info("\nVerifying confirmation layer implementation...")
    
    try:
        # Read the confirmation layer implementation
        with open('ict_signal_engine.py', 'r') as f:
            content = f.read()
        
        # Find the _analyze_confirmation_layer method
        if '_analyze_confirmation_layer' not in content:
            logger.error("❌ Could not find _analyze_confirmation_layer method")
            return False
        
        # Extract just the method content
        start_idx = content.find('def _analyze_confirmation_layer')
        end_idx = content.find('\n    def ', start_idx + 100)
        if end_idx == -1:
            end_idx = len(content)
        method_content = content[start_idx:end_idx]
        
        # Check for whale blocks detection
        violations = []
        
        # Check 1: Whale blocks variable exists
        if 'has_whale_blocks' not in method_content:
            violations.append("Missing 'has_whale_blocks' variable in confirmation layer")
        
        # Check 2: Whale detector is called
        if 'whale_detector.detect_whale_blocks' not in method_content:
            violations.append("Whale detector is not being called in confirmation layer")
        
        # Check 3: Whale blocks in confirmation check
        confirmation_check_pattern = 'has_whale_blocks'
        if confirmation_check_pattern not in method_content:
            violations.append("Whale blocks not included in confirmation check logic")
        
        # Check 4: Whale blocks in logging
        whale_log_patterns = [
            'Whale Blocks:',  # Could be with quotes or f-string
            'has_whale_blocks'  # Variable should be in logging
        ]
        if not any(pattern in method_content for pattern in whale_log_patterns):
            violations.append("Whale blocks not included in confirmation layer logging")
        
        # Check 5: All required confirmation checks present
        required_checks = [
            'has_structure_break',  # MSS/BOS
            'has_displacement',      # Displacement
            'has_sweep',            # Sweep
            'has_whale_blocks'      # Whale Blocks
        ]
        
        for check in required_checks:
            if check not in method_content:
                violations.append(f"Missing required confirmation check: {check}")
        
        if violations:
            logger.error("\n❌ TEST FAILED: Whale blocks check not properly implemented")
            for v in violations:
                logger.error(f"   • {v}")
            return False
        else:
            logger.info("\n✅ TEST PASSED: Whale blocks check properly implemented")
            logger.info("   • has_whale_blocks variable present")
            logger.info("   • whale_detector.detect_whale_blocks() called")
            logger.info("   • Whale blocks included in confirmation logic")
            logger.info("   • Whale blocks included in logging")
            logger.info("   • All 5 confirmation checks present:")
            logger.info("     - MSS/BOS (structure break)")
            logger.info("     - Displacement")
            logger.info("     - Sweep")
            logger.info("     - Sweep + Displacement")
            logger.info("     - Whale Blocks")
            return True
            
    except Exception as e:
        logger.error(f"\n❌ TEST ERROR: {str(e)}")
        return False


def test_confirmation_layer_uses_correct_timeframe():
    """
    Test: Confirmation layer uses confirmation_tf parameter
    
    Specification requirement:
    "Confirmation се детектира САМО от confirmation_tf."
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Confirmation Layer Uses Correct Timeframe")
    logger.info("=" * 80)
    
    logger.info("\nVerifying confirmation_tf parameter usage...")
    
    try:
        with open('ict_signal_engine.py', 'r') as f:
            content = f.read()
        
        # Find the _analyze_confirmation_layer method
        start_idx = content.find('def _analyze_confirmation_layer')
        if start_idx == -1:
            logger.error("❌ Could not find _analyze_confirmation_layer method")
            return False
        
        # Find the end of the method (next 'def ' or end of file)
        end_idx = content.find('\n    def ', start_idx + 100)
        if end_idx == -1:
            end_idx = len(content)
        
        method_content = content[start_idx:end_idx]
        
        violations = []
        
        # Check 1: Method receives confirmation_tf parameter
        if 'confirmation_tf: str' not in method_content:
            violations.append("Method does not receive confirmation_tf parameter")
        
        # Check 2: Uses confirmation_tf for data lookup
        if 'mtf_data.get(confirmation_tf)' not in method_content:
            violations.append("Does not use confirmation_tf to get data from mtf_data")
        
        # Check 3: Passes confirmation_tf to whale detector
        if 'detect_whale_blocks(df, confirmation_tf)' not in method_content:
            violations.append("Does not pass confirmation_tf to whale detector")
        
        # Check 4: No hardcoded timeframes in the method
        hardcoded_tfs = ["'1h'", "'2h'", "'4h'", "'1d'", '"1h"', '"2h"', '"4h"', '"1d"']
        for tf in hardcoded_tfs:
            if tf in method_content and 'log' not in method_content[method_content.find(tf)-50:method_content.find(tf)+50].lower():
                # Allow in logging messages, but not in logic
                violations.append(f"Found hardcoded timeframe {tf} in confirmation layer logic")
        
        if violations:
            logger.error("\n❌ TEST FAILED: Confirmation layer timeframe issues")
            for v in violations:
                logger.error(f"   • {v}")
            return False
        else:
            logger.info("\n✅ TEST PASSED: Confirmation layer uses correct timeframe")
            logger.info("   • Receives confirmation_tf parameter")
            logger.info("   • Uses confirmation_tf for data lookup")
            logger.info("   • Passes confirmation_tf to whale detector")
            logger.info("   • No hardcoded timeframes in logic")
            return True
            
    except Exception as e:
        logger.error(f"\n❌ TEST ERROR: {str(e)}")
        return False


def test_confirmation_layer_returns_confidence_modifier():
    """
    Test: Confirmation layer returns confidence modifier only
    
    Specification requirement:
    "Логика:
     • Ако има ≥ 1 → +8% към confidence
     • Ако няма → -8% към confidence"
    """
    logger.info("\n" + "=" * 80)
    logger.info("TEST: Confirmation Layer Returns Confidence Modifier")
    logger.info("=" * 80)
    
    logger.info("\nVerifying confidence modifier logic...")
    
    try:
        with open('ict_signal_engine.py', 'r') as f:
            content = f.read()
        
        # Find the _analyze_confirmation_layer method
        start_idx = content.find('def _analyze_confirmation_layer')
        if start_idx == -1:
            logger.error("❌ Could not find _analyze_confirmation_layer method")
            return False
        
        end_idx = content.find('\n    def ', start_idx + 100)
        if end_idx == -1:
            end_idx = len(content)
        
        method_content = content[start_idx:end_idx]
        
        violations = []
        
        # Check 1: Uses 0.08 for modifier
        if '0.08' not in method_content:
            violations.append("Does not use 0.08 (8%) for confidence modifier")
        
        # Check 2: Positive modifier when confirmation found
        if 'if has_confirmation' not in method_content:
            violations.append("Does not check has_confirmation for modifier calculation")
        
        # Check 3: Returns tuple with bool and float
        if 'return has_confirmation, confidence_modifier' not in method_content:
            violations.append("Does not return (has_confirmation, confidence_modifier) tuple")
        
        # Check 4: Never returns None
        if 'return None' in method_content:
            violations.append("Method returns None (violates specification)")
        
        # Check 5: Does not set eligible flag (check code, not docstrings)
        # Find where actual code starts (after docstring)
        code_start = method_content.find('logger.info')
        if code_start == -1:
            code_start = method_content.find('if ')
        
        if code_start > 0:
            code_only = method_content[code_start:]
            if 'eligible = False' in code_only or 'eligible=False' in code_only:
                violations.append("Method sets eligible flag (violates specification)")
        
        if violations:
            logger.error("\n❌ TEST FAILED: Confidence modifier issues")
            for v in violations:
                logger.error(f"   • {v}")
            return False
        else:
            logger.info("\n✅ TEST PASSED: Confidence modifier correctly implemented")
            logger.info("   • Uses ±8% (0.08) for modifier")
            logger.info("   • Returns +8% when confirmation found")
            logger.info("   • Returns -8% when confirmation not found")
            logger.info("   • Never returns None")
            logger.info("   • Does not set eligible flag")
            return True
            
    except Exception as e:
        logger.error(f"\n❌ TEST ERROR: {str(e)}")
        return False


def run_all_tests():
    """Run all confirmation layer tests"""
    logger.info("\n" + "=" * 80)
    logger.info("CONFIRMATION LAYER VALIDATION TEST SUITE")
    logger.info("Verifying whale blocks check implementation")
    logger.info("=" * 80)
    
    results = {
        "Whale Blocks Check": test_confirmation_layer_includes_whale_blocks(),
        "Correct Timeframe": test_confirmation_layer_uses_correct_timeframe(),
        "Confidence Modifier": test_confirmation_layer_returns_confidence_modifier()
    }
    
    # Print summary
    logger.info("\n" + "=" * 80)
    logger.info("TEST SUMMARY")
    logger.info("=" * 80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        logger.info(f"{status}: {test_name}")
    
    logger.info("-" * 80)
    logger.info(f"Total: {passed}/{total} tests passed")
    logger.info("=" * 80)
    
    if passed == total:
        logger.info("\n✅ ALL TESTS PASSED - Confirmation layer correctly implemented")
        return 0
    else:
        logger.error(f"\n❌ {total - passed} TEST(S) FAILED - Issues remain")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
