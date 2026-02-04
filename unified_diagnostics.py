"""
Unified Diagnostics System
Combines all diagnostic modules into one interface

PR #117: Complete diagnostic system integration
Author: System Diagnostics Team
"""

import asyncio
from typing import Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


async def get_full_diagnostic_report() -> Dict[str, Any]:
    """
    Get complete diagnostic report combining all modules
    
    Returns:
        Unified diagnostic report
    """
    from comprehensive_diagnostics import run_smoke_test
    from function_health import get_function_health_report
    from replay_diagnostics import get_replay_diagnostics_report
    from performance_monitor import get_performance_report
    from system_diagnostics import run_full_health_check
    
    report = {
        'timestamp': datetime.now().isoformat(),
        'status': 'RUNNING'
    }
    
    try:
        # Run all diagnostics
        logger.info("Running unified diagnostics...")
        
        # 1. System health check
        system_health = await run_full_health_check()
        report['system_health'] = system_health
        
        # 2. Smoke test
        smoke_test = await run_smoke_test()
        report['smoke_test'] = smoke_test
        
        # 3. Function health
        function_health = await get_function_health_report()
        report['function_health'] = function_health
        
        # 4. Performance metrics
        performance = await get_performance_report()
        report['performance'] = performance
        
        # 5. Replay diagnostics (last 3 operations)
        replay = await get_replay_diagnostics_report(replay_count=3)
        report['replay'] = replay
        
        # Overall status
        errors = 0
        warnings = 0
        
        # Check smoke test
        if smoke_test.get('summary', {}).get('errors', 0) > 0:
            errors += smoke_test['summary']['errors']
        if smoke_test.get('summary', {}).get('warnings', 0) > 0:
            warnings += smoke_test['summary']['warnings']
        
        # Check function health
        if function_health.get('summary', {}).get('errors', 0) > 0:
            errors += function_health['summary']['errors']
        if function_health.get('summary', {}).get('warnings', 0) > 0:
            warnings += function_health['summary']['warnings']
        
        # Check performance bottlenecks
        if performance.get('summary', {}).get('bottlenecks_detected', 0) > 0:
            warnings += performance['summary']['bottlenecks_detected']
        
        # Determine overall status
        if errors > 0:
            report['status'] = 'ERROR'
        elif warnings > 0:
            report['status'] = 'WARNING'
        else:
            report['status'] = 'OK'
        
        report['summary'] = {
            'total_errors': errors,
            'total_warnings': warnings,
            'overall_health': report['status']
        }
        
        logger.info(f"Unified diagnostics complete: {report['status']}")
        
    except Exception as e:
        report['status'] = 'ERROR'
        report['error'] = str(e)
        logger.error(f"Unified diagnostics failed: {e}")
    
    return report


async def get_quick_status() -> Dict[str, Any]:
    """
    Get quick status summary (for /health command)
    
    Returns:
        Quick status summary
    """
    from comprehensive_diagnostics import run_smoke_test
    from performance_monitor import get_system_performance
    
    try:
        # Run smoke test
        smoke_test = await run_smoke_test()
        
        # Get system performance
        system_perf = await get_system_performance()
        
        # Build summary
        summary = {
            'timestamp': datetime.now().isoformat(),
            'smoke_test': {
                'passed': smoke_test.get('summary', {}).get('passed', 0),
                'total': smoke_test.get('summary', {}).get('total', 0),
                'errors': smoke_test.get('summary', {}).get('errors', 0),
                'warnings': smoke_test.get('summary', {}).get('warnings', 0),
            },
            'system': {
                'cpu_percent': system_perf.get('cpu', {}).get('process_percent', 0),
                'memory_mb': system_perf.get('memory', {}).get('process_mb', 0),
                'memory_percent': system_perf.get('memory', {}).get('system_percent', 0),
            },
            'status': 'OK' if smoke_test.get('summary', {}).get('errors', 0) == 0 else 'ERROR'
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Quick status failed: {e}")
        return {
            'timestamp': datetime.now().isoformat(),
            'status': 'ERROR',
            'error': str(e),
            'smoke_test': {'passed': 0, 'total': 0, 'errors': 1, 'warnings': 0},
            'system': {'cpu_percent': 0, 'memory_mb': 0, 'memory_percent': 0}
        }


if __name__ == "__main__":
    # Test the module
    async def main():
        print("\n🔗 TESTING UNIFIED DIAGNOSTICS")
        print("=" * 60)
        
        # Quick status
        print("\n📊 QUICK STATUS")
        print("━" * 60)
        status = await get_quick_status()
        print(f"Status: {status['status']}")
        if 'error' in status:
            print(f"Error: {status['error']}")
        if 'smoke_test' in status:
            print(f"Smoke Test: {status['smoke_test']['passed']}/{status['smoke_test']['total']} passed")
        if 'system' in status:
            print(f"CPU: {status['system']['cpu_percent']}%")
            print(f"Memory: {status['system']['memory_mb']} MB")
        
        print("\n" + "=" * 60)
        print("✅ Unified diagnostics working!")
        print("=" * 60)
    
    asyncio.run(main())
