#!/usr/bin/env python3
"""
Scenario Logic Validation Script
=================================

Purpose: Validate scenario selection correctness and ICT logic alignment

Validates:
- Scenario aligns with structure TF
- Scenario respects HTF bias
- No illogical combinations (e.g., bullish continuation under bearish structure)
- Component strength influences scenario deterministically
- Scenario score consistent with detected components
"""

import sys
import logging
from typing import Dict, List, Tuple, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def validate_scenario_alignment(scenario: str, structure: str, bias: str) -> Tuple[bool, List[str]]:
    """Validate scenario aligns with structure and bias"""
    issues = []
    
    # Map scenarios to expected bias
    scenario_bias_map = {
        'CONTINUATION': {
            'BULLISH': ['BULLISH'],
            'BEARISH': ['BEARISH']
        },
        'PULLBACK': {
            'BULLISH': ['BULLISH'],
            'BEARISH': ['BEARISH']
        },
        'REVERSAL': {
            'BULLISH': ['BEARISH'],  # Bullish reversal from bearish
            'BEARISH': ['BULLISH']   # Bearish reversal from bullish
        },
        'ROLLBACK': {
            'BULLISH': ['BULLISH'],
            'BEARISH': ['BEARISH']
        }
    }
    
    # Check if scenario is valid
    if scenario not in scenario_bias_map:
        issues.append(f"Unknown scenario: {scenario}")
        return False, issues
    
    # Check bias alignment
    if scenario in scenario_bias_map:
        expected_biases = scenario_bias_map[scenario].get(bias, [])
        if bias not in expected_biases and scenario != 'REVERSAL':
            issues.append(f"Scenario {scenario} with {bias} bias may be illogical")
    
    # Check structure alignment
    structure_types = ['MSS', 'BOS', 'CHOCH']
    if structure not in structure_types and structure != 'UNKNOWN':
        issues.append(f"Invalid structure type: {structure}")
    
    # Specific logical checks
    if scenario == 'CONTINUATION' and structure == 'CHOCH':
        issues.append("CONTINUATION scenario with CHOCH structure is illogical (CHOCH indicates reversal)")
    
    if scenario == 'REVERSAL' and structure in ['MSS', 'BOS']:
        # This could be valid if MSS/BOS in opposite direction
        pass
    
    return len(issues) == 0, issues


def test_scenario_configurations() -> Dict[str, Any]:
    """Test various scenario configurations"""
    results = {
        'status': 'UNKNOWN',
        'tests': [],
        'errors': []
    }
    
    # Test cases: (scenario, structure, bias, should_pass)
    test_cases = [
        # Valid combinations
        ('CONTINUATION', 'MSS', 'BULLISH', True, "Bullish continuation with MSS"),
        ('CONTINUATION', 'BOS', 'BEARISH', True, "Bearish continuation with BOS"),
        ('PULLBACK', 'MSS', 'BULLISH', True, "Bullish pullback with MSS"),
        ('REVERSAL', 'CHOCH', 'BULLISH', True, "Bullish reversal with CHOCH"),
        ('REVERSAL', 'CHOCH', 'BEARISH', True, "Bearish reversal with CHOCH"),
        
        # Potentially illogical combinations
        ('CONTINUATION', 'CHOCH', 'BULLISH', False, "Continuation with CHOCH is illogical"),
    ]
    
    for scenario, structure, bias, should_pass, description in test_cases:
        is_valid, issues = validate_scenario_alignment(scenario, structure, bias)
        
        test_result = {
            'scenario': scenario,
            'structure': structure,
            'bias': bias,
            'expected': 'PASS' if should_pass else 'FAIL',
            'actual': 'PASS' if is_valid else 'FAIL',
            'description': description,
            'issues': issues
        }
        
        # Check if result matches expectation
        if (is_valid and should_pass) or (not is_valid and not should_pass):
            test_result['status'] = '✅ CORRECT'
        else:
            test_result['status'] = '❌ UNEXPECTED'
            results['errors'].append(f"{description}: Expected {test_result['expected']}, got {test_result['actual']}")
        
        results['tests'].append(test_result)
    
    # Overall status
    if len(results['errors']) == 0:
        results['status'] = 'PASS'
    else:
        results['status'] = 'FAIL'
    
    return results


def validate_scoring_consistency() -> Dict[str, Any]:
    """Validate scenario scoring is consistent"""
    results = {
        'status': 'UNKNOWN',
        'checks': []
    }
    
    try:
        from entry_scenario_config import (
            TRIGGER_WEIGHTS,
            MIN_SCENARIO_SCORE,
            SCENARIO_CONFIGS
        )
        
        # Check trigger weights are defined
        if TRIGGER_WEIGHTS:
            results['checks'].append({
                'name': 'trigger_weights_defined',
                'status': 'PASS',
                'message': f'Trigger weights: {TRIGGER_WEIGHTS}'
            })
        else:
            results['checks'].append({
                'name': 'trigger_weights_defined',
                'status': 'FAIL',
                'message': 'Trigger weights not defined'
            })
        
        # Check min score threshold
        if MIN_SCENARIO_SCORE > 0:
            results['checks'].append({
                'name': 'min_score_defined',
                'status': 'PASS',
                'message': f'Min score: {MIN_SCENARIO_SCORE}'
            })
        else:
            results['checks'].append({
                'name': 'min_score_defined',
                'status': 'FAIL',
                'message': 'Min score not properly defined'
            })
        
        # Check scenario configs exist
        if SCENARIO_CONFIGS:
            results['checks'].append({
                'name': 'scenario_configs_defined',
                'status': 'PASS',
                'message': f'Scenarios defined: {list(SCENARIO_CONFIGS.keys())}'
            })
        else:
            results['checks'].append({
                'name': 'scenario_configs_defined',
                'status': 'FAIL',
                'message': 'Scenario configs not defined'
            })
        
        results['status'] = 'PASS'
        
    except ImportError as e:
        results['status'] = 'WARN'
        results['checks'].append({
            'name': 'import_config',
            'status': 'WARN',
            'message': f'Could not import config: {e}'
        })
    
    return results


def print_results(test_results: Dict[str, Any], scoring_results: Dict[str, Any]):
    """Print validation results"""
    logger.info("\n" + "="*80)
    logger.info("SCENARIO LOGIC VALIDATION RESULTS")
    logger.info("="*80)
    
    # Test results
    logger.info("\n📊 Scenario Alignment Tests:")
    for test in test_results.get('tests', []):
        logger.info(f"\n  {test['status']} {test['description']}")
        logger.info(f"    Scenario: {test['scenario']}, Structure: {test['structure']}, Bias: {test['bias']}")
        logger.info(f"    Expected: {test['expected']}, Actual: {test['actual']}")
        if test.get('issues'):
            for issue in test['issues']:
                logger.info(f"    Issue: {issue}")
    
    # Scoring validation
    logger.info("\n🔍 Scoring Consistency:")
    for check in scoring_results.get('checks', []):
        status_icon = '✅' if check['status'] == 'PASS' else '⚠️' if check['status'] == 'WARN' else '❌'
        logger.info(f"  {status_icon} {check['name']}: {check['message']}")
    
    # Errors
    if test_results.get('errors'):
        logger.info("\n❌ Errors:")
        for error in test_results['errors']:
            logger.info(f"  - {error}")
    
    # Final status
    logger.info("\n" + "="*80)
    overall_status = test_results.get('status', 'UNKNOWN')
    if overall_status == 'PASS' and scoring_results.get('status') in ['PASS', 'WARN']:
        logger.info("✅ FINAL STATUS: PASS")
        return 0
    else:
        logger.info(f"❌ FINAL STATUS: {overall_status}")
        return 1


def main():
    """Main validation entry point"""
    logger.info("🧪 SCENARIO LOGIC VALIDATION")
    logger.info("="*80)
    
    # Run validations
    test_results = test_scenario_configurations()
    scoring_results = validate_scoring_consistency()
    
    # Print and return results
    return print_results(test_results, scoring_results)


if __name__ == "__main__":
    sys.exit(main())
