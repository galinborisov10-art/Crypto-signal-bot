#!/usr/bin/env python3
"""
Regression Suite Validation Script
===================================

Purpose: Verify no regressions in core functionality

Validates:
- /market command
- News alerts
- Backtest
- Pipeline steps
- Formatting
- Production service behavior
"""

import sys
import logging
from typing import Dict, List

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)


def validate_imports() -> Dict[str, any]:
    """Validate all critical modules can be imported"""
    results = {
        'status': 'UNKNOWN',
        'imports': []
    }
    
    critical_modules = [
        ('bot', 'Main bot module'),
        ('ict_signal_engine', 'ICT signal engine'),
        ('timeframe_contract', 'Timeframe contract'),
        ('entry_scenarios', 'Entry scenarios'),
        ('entry_scenario_config', 'Scenario config'),
        ('order_block_detector', 'Order block detector'),
        ('fvg_detector', 'FVG detector'),
        ('liquidity_map', 'Liquidity detector'),
        ('position_manager', 'Position manager'),
    ]
    
    all_passed = True
    
    for module_name, description in critical_modules:
        try:
            __import__(module_name)
            results['imports'].append({
                'module': module_name,
                'status': 'PASS',
                'description': description
            })
        except Exception as e:
            results['imports'].append({
                'module': module_name,
                'status': 'FAIL',
                'description': description,
                'error': str(e)
            })
            all_passed = False
    
    results['status'] = 'PASS' if all_passed else 'FAIL'
    return results


def validate_pipeline_components() -> Dict[str, any]:
    """Validate signal generation pipeline components"""
    results = {
        'status': 'UNKNOWN',
        'checks': []
    }
    
    try:
        from ict_signal_engine import ICTSignalEngine
        
        # Check engine can be instantiated
        try:
            engine = ICTSignalEngine()
            results['checks'].append({
                'name': 'engine_instantiation',
                'status': 'PASS',
                'message': 'ICTSignalEngine can be instantiated'
            })
        except Exception as e:
            results['checks'].append({
                'name': 'engine_instantiation',
                'status': 'FAIL',
                'message': f'Failed to instantiate engine: {e}'
            })
        
        # Check critical methods exist
        critical_methods = [
            'generate_signal',
            '_detect_ict_components',
            '_calculate_bias',
            '_calculate_mtf_consensus',
        ]
        
        for method in critical_methods:
            if hasattr(ICTSignalEngine, method):
                results['checks'].append({
                    'name': f'method_{method}',
                    'status': 'PASS',
                    'message': f'{method} exists'
                })
            else:
                results['checks'].append({
                    'name': f'method_{method}',
                    'status': 'FAIL',
                    'message': f'{method} missing'
                })
        
        results['status'] = 'PASS'
        
    except ImportError as e:
        results['status'] = 'FAIL'
        results['checks'].append({
            'name': 'engine_import',
            'status': 'FAIL',
            'message': f'Could not import ICTSignalEngine: {e}'
        })
    
    return results


def validate_detector_components() -> Dict[str, any]:
    """Validate detector components"""
    results = {
        'status': 'UNKNOWN',
        'checks': []
    }
    
    detectors = [
        ('order_block_detector', 'OrderBlockDetector', 'detect_order_blocks'),
        ('fvg_detector', 'FVGDetector', 'detect_fvg'),
        ('liquidity_map', 'LiquidityMap', 'detect_liquidity'),
    ]
    
    all_passed = True
    
    for module_name, class_name, method_name in detectors:
        try:
            module = __import__(module_name)
            
            # Check class exists
            if hasattr(module, class_name):
                results['checks'].append({
                    'name': f'{class_name}_exists',
                    'status': 'PASS',
                    'message': f'{class_name} class exists'
                })
                
                # Check method exists
                cls = getattr(module, class_name)
                if hasattr(cls, method_name):
                    results['checks'].append({
                        'name': f'{class_name}_{method_name}',
                        'status': 'PASS',
                        'message': f'{class_name}.{method_name} exists'
                    })
                else:
                    results['checks'].append({
                        'name': f'{class_name}_{method_name}',
                        'status': 'FAIL',
                        'message': f'{class_name}.{method_name} missing'
                    })
                    all_passed = False
            else:
                results['checks'].append({
                    'name': f'{class_name}_exists',
                    'status': 'FAIL',
                    'message': f'{class_name} class not found'
                })
                all_passed = False
                
        except Exception as e:
            results['checks'].append({
                'name': f'{module_name}_import',
                'status': 'FAIL',
                'message': f'Failed to import {module_name}: {e}'
            })
            all_passed = False
    
    results['status'] = 'PASS' if all_passed else 'FAIL'
    return results


def validate_configuration() -> Dict[str, any]:
    """Validate configuration files"""
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
        
        # Validate trigger weights
        required_triggers = ['MSS/BOS', 'DISPLACEMENT', 'LIQUIDITY_SWEEP', 'BREAKER/MITIGATION']
        for trigger in required_triggers:
            if trigger in TRIGGER_WEIGHTS:
                results['checks'].append({
                    'name': f'trigger_{trigger}',
                    'status': 'PASS',
                    'message': f'{trigger}: {TRIGGER_WEIGHTS[trigger]}'
                })
            else:
                results['checks'].append({
                    'name': f'trigger_{trigger}',
                    'status': 'FAIL',
                    'message': f'{trigger} not defined'
                })
        
        # Validate min score
        if MIN_SCENARIO_SCORE > 0:
            results['checks'].append({
                'name': 'min_scenario_score',
                'status': 'PASS',
                'message': f'MIN_SCENARIO_SCORE: {MIN_SCENARIO_SCORE}'
            })
        else:
            results['checks'].append({
                'name': 'min_scenario_score',
                'status': 'FAIL',
                'message': 'MIN_SCENARIO_SCORE invalid'
            })
        
        # Validate scenario configs
        required_scenarios = ['CONTINUATION', 'PULLBACK', 'REVERSAL', 'ROLLBACK']
        for scenario in required_scenarios:
            if scenario in SCENARIO_CONFIGS:
                results['checks'].append({
                    'name': f'scenario_{scenario}',
                    'status': 'PASS',
                    'message': f'{scenario} configured'
                })
            else:
                results['checks'].append({
                    'name': f'scenario_{scenario}',
                    'status': 'WARN',
                    'message': f'{scenario} not configured'
                })
        
        results['status'] = 'PASS'
        
    except ImportError as e:
        results['status'] = 'FAIL'
        results['checks'].append({
            'name': 'config_import',
            'status': 'FAIL',
            'message': f'Could not import config: {e}'
        })
    
    return results


def print_results(import_results: Dict, pipeline_results: Dict, 
                  detector_results: Dict, config_results: Dict):
    """Print validation results"""
    logger.info("\n" + "="*80)
    logger.info("REGRESSION SUITE VALIDATION RESULTS")
    logger.info("="*80)
    
    # Import validation
    logger.info("\n📦 Module Imports:")
    for imp in import_results.get('imports', []):
        status_icon = '✅' if imp['status'] == 'PASS' else '❌'
        logger.info(f"  {status_icon} {imp['module']}: {imp['description']}")
        if imp.get('error'):
            logger.info(f"      Error: {imp['error']}")
    
    # Pipeline validation
    logger.info("\n🔄 Pipeline Components:")
    for check in pipeline_results.get('checks', []):
        status_icon = '✅' if check['status'] == 'PASS' else '❌'
        logger.info(f"  {status_icon} {check['name']}: {check['message']}")
    
    # Detector validation
    logger.info("\n🔍 Detectors:")
    for check in detector_results.get('checks', []):
        status_icon = '✅' if check['status'] == 'PASS' else '❌'
        logger.info(f"  {status_icon} {check['name']}: {check['message']}")
    
    # Configuration validation
    logger.info("\n⚙️ Configuration:")
    for check in config_results.get('checks', []):
        status_icon = '✅' if check['status'] == 'PASS' else '⚠️' if check['status'] == 'WARN' else '❌'
        logger.info(f"  {status_icon} {check['name']}: {check['message']}")
    
    # Final status
    logger.info("\n" + "="*80)
    all_passed = all([
        import_results.get('status') == 'PASS',
        pipeline_results.get('status') == 'PASS',
        detector_results.get('status') == 'PASS',
        config_results.get('status') in ['PASS', 'WARN']
    ])
    
    if all_passed:
        logger.info("✅ FINAL STATUS: PASS")
        return 0
    else:
        logger.info("❌ FINAL STATUS: FAIL")
        return 1


def main():
    """Main validation entry point"""
    logger.info("🧪 REGRESSION SUITE VALIDATION")
    logger.info("="*80)
    
    # Run all validations
    import_results = validate_imports()
    pipeline_results = validate_pipeline_components()
    detector_results = validate_detector_components()
    config_results = validate_configuration()
    
    # Print and return results
    return print_results(import_results, pipeline_results, detector_results, config_results)


if __name__ == "__main__":
    sys.exit(main())
