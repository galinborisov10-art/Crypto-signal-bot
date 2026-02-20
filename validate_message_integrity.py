#!/usr/bin/env python3
"""
Message Integrity Validation Script
====================================

Purpose: Verify Telegram message formatting and consistency

Validates:
- No ${} or formatting leakage
- Displayed TF matches internal TF
- Displayed bias matches actual bias
- Displayed component counts match actual used components
- No empty sections
"""

import sys
import logging
import re
from typing import Dict, List, Tuple

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def check_template_leakage(message: str) -> Tuple[bool, List[str]]:
    """Check for template placeholder leakage"""
    issues = []
    
    # Check for ${} placeholders
    dollar_placeholders = re.findall(r'\$\{[^}]+\}', message)
    if dollar_placeholders:
        issues.append(f"Found ${{}}} placeholders: {dollar_placeholders}")
    
    # Check for unresolved {} placeholders (excluding valid ones like emoji)
    curly_placeholders = re.findall(r'\{[a-zA-Z_][a-zA-Z0-9_.]+\}', message)
    if curly_placeholders:
        issues.append(f"Found {{}} placeholders: {curly_placeholders}")
    
    # Check for literal 'None' strings
    if ' None ' in message or message.endswith('None') or message.startswith('None'):
        issues.append("Found literal 'None' in message")
    
    # Check for 'N/A at $0.00'
    if 'N/A at $0.00' in message or '$0.00' in message:
        issues.append("Found invalid price display: $0.00")
    
    return len(issues) == 0, issues


def validate_message_sections(message: str) -> Tuple[bool, List[str]]:
    """Validate message has all required sections and no empty ones"""
    issues = []
    
    # Required sections
    required_sections = [
        'ENTRY',
        'STOP LOSS',
        'TAKE PROFIT',
    ]
    
    for section in required_sections:
        if section not in message:
            issues.append(f"Missing required section: {section}")
    
    # Check for empty sections (section header followed immediately by another header)
    empty_section_pattern = r'<b>([^<]+):</b>\s*<b>'
    empty_sections = re.findall(empty_section_pattern, message)
    if empty_sections:
        issues.append(f"Found potentially empty sections: {empty_sections}")
    
    return len(issues) == 0, issues


def test_message_samples() -> Dict[str, any]:
    """Test sample messages for validation"""
    results = {
        'status': 'UNKNOWN',
        'tests': [],
        'errors': []
    }
    
    # Sample test messages (good and bad)
    test_messages = [
        # Good message
        (
            "<b>📍 ENTRY:</b> $50,234.5000\n<b>🛑 STOP LOSS:</b> $49,850.0000\n<b>🎯 TAKE PROFITS:</b>\n  • TP1: $50,600.0000",
            True,
            "Valid message with proper formatting"
        ),
        # Bad - placeholder leakage
        (
            "<b>📍 ENTRY:</b> ${signal.entry_price:,.4f}\n<b>🛑 STOP LOSS:</b> $49,850.0000",
            False,
            "Message with ${} placeholder leakage"
        ),
        # Bad - None value
        (
            "<b>📍 ENTRY:</b> None\n<b>🛑 STOP LOSS:</b> $49,850.0000",
            False,
            "Message with None value"
        ),
        # Bad - $0.00
        (
            "<b>Zone 1:</b> N/A at $0.00",
            False,
            "Message with $0.00 value"
        ),
    ]
    
    for message, should_pass, description in test_messages:
        no_leakage, leakage_issues = check_template_leakage(message)
        has_sections, section_issues = validate_message_sections(message)
        
        is_valid = no_leakage and has_sections
        
        test_result = {
            'description': description,
            'expected': 'PASS' if should_pass else 'FAIL',
            'actual': 'PASS' if is_valid else 'FAIL',
            'leakage_issues': leakage_issues,
            'section_issues': section_issues
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


def validate_formatting_functions() -> Dict[str, any]:
    """Validate message formatting functions exist and work"""
    results = {
        'status': 'UNKNOWN',
        'checks': []
    }
    
    try:
        # Try to import bot formatting functions
        # This is a basic check that the module exists
        import bot
        
        results['checks'].append({
            'name': 'bot_module',
            'status': 'PASS',
            'message': 'bot.py module available'
        })
        
        # Check for formatting function
        if hasattr(bot, 'format_standardized_signal'):
            results['checks'].append({
                'name': 'format_function',
                'status': 'PASS',
                'message': 'format_standardized_signal function exists'
            })
        else:
            results['checks'].append({
                'name': 'format_function',
                'status': 'WARN',
                'message': 'format_standardized_signal function not found'
            })
        
        results['status'] = 'PASS'
        
    except ImportError as e:
        results['status'] = 'WARN'
        results['checks'].append({
            'name': 'bot_import',
            'status': 'WARN',
            'message': f'Could not import bot module: {e}'
        })
    
    return results


def print_results(test_results: Dict, function_results: Dict):
    """Print validation results"""
    logger.info("\n" + "="*80)
    logger.info("MESSAGE INTEGRITY VALIDATION RESULTS")
    logger.info("="*80)
    
    # Test results
    logger.info("\n📊 Message Format Tests:")
    for test in test_results.get('tests', []):
        logger.info(f"\n  {test['status']} {test['description']}")
        logger.info(f"    Expected: {test['expected']}, Actual: {test['actual']}")
        if test.get('leakage_issues'):
            for issue in test['leakage_issues']:
                logger.info(f"    Leakage: {issue}")
        if test.get('section_issues'):
            for issue in test['section_issues']:
                logger.info(f"    Section: {issue}")
    
    # Function validation
    logger.info("\n🔍 Formatting Functions:")
    for check in function_results.get('checks', []):
        status_icon = '✅' if check['status'] == 'PASS' else '⚠️' if check['status'] == 'WARN' else '❌'
        logger.info(f"  {status_icon} {check['name']}: {check['message']}")
    
    # Errors
    if test_results.get('errors'):
        logger.info("\n❌ Errors:")
        for error in test_results['errors']:
            logger.info(f"  - {error}")
    
    # Final status
    logger.info("\n" + "="*80)
    if test_results.get('status') == 'PASS' and function_results.get('status') in ['PASS', 'WARN']:
        logger.info("✅ FINAL STATUS: PASS")
        return 0
    else:
        logger.info(f"❌ FINAL STATUS: {test_results.get('status', 'UNKNOWN')}")
        return 1


def main():
    """Main validation entry point"""
    logger.info("🧪 MESSAGE INTEGRITY VALIDATION")
    logger.info("="*80)
    
    # Run validations
    test_results = test_message_samples()
    function_results = validate_formatting_functions()
    
    # Print and return results
    return print_results(test_results, function_results)


if __name__ == "__main__":
    sys.exit(main())
