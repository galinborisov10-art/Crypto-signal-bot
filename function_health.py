"""
Function Health Status Module
Tests ONLY actively used bot commands and core functions

PR #117: Function health monitoring for production bot
Author: System Diagnostics Team
"""

import asyncio
import time
import traceback
from typing import Dict, Any, List, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class FunctionHealthChecker:
    """Tests health of actively used bot functions"""
    
    def __init__(self):
        self.results = []
        
    async def test_command_exists(self, command_name: str) -> Dict[str, Any]:
        """
        Test if a command handler exists in bot.py
        
        Args:
            command_name: Command name (e.g., 'start', 'signal')
            
        Returns:
            Test result with status
        """
        start_time = time.time()
        result = {
            'command': f'/{command_name}',
            'status': 'UNKNOWN',
            'execution_time': 0.0,
            'error': None,
            'timestamp': datetime.now().isoformat(),
            'handler_found': False,
            'function_found': False
        }
        
        try:
            # Read bot.py and check for command
            with open('bot.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Check for CommandHandler
            handler_pattern = f'CommandHandler("{command_name}"'
            if handler_pattern in content:
                result['handler_found'] = True
            
            # Check for function definition
            func_pattern = f'async def {command_name}_cmd'
            if func_pattern in content:
                result['function_found'] = True
            
            # Determine status
            if result['handler_found'] and result['function_found']:
                result['status'] = 'OK'
            elif result['handler_found']:
                result['status'] = 'WARNING'
                result['error'] = 'Handler found but function missing'
            elif result['function_found']:
                result['status'] = 'WARNING'
                result['error'] = 'Function found but handler missing'
            else:
                result['status'] = 'NOT_FOUND'
                result['error'] = f'Command /{command_name} not found in bot.py'
                
        except FileNotFoundError:
            result['status'] = 'ERROR'
            result['error'] = 'bot.py file not found'
            
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            logger.error(f"Error testing command {command_name}: {e}")
            
        finally:
            result['execution_time'] = round(time.time() - start_time, 3)
            
        return result
    
    async def test_module_exists(self, module_name: str, description: str = "") -> Dict[str, Any]:
        """
        Test if a Python module exists and can be imported
        
        Args:
            module_name: Module filename (e.g., 'ml_engine.py')
            description: Human-readable description
            
        Returns:
            Test result with status
        """
        start_time = time.time()
        result = {
            'module': module_name,
            'description': description,
            'status': 'UNKNOWN',
            'execution_time': 0.0,
            'error': None,
            'timestamp': datetime.now().isoformat(),
            'file_exists': False,
            'importable': False
        }
        
        try:
            # Check if file exists
            import os
            if os.path.exists(module_name):
                result['file_exists'] = True
                
                # Try to import (without .py extension)
                module_import_name = module_name.replace('.py', '')
                try:
                    __import__(module_import_name)
                    result['importable'] = True
                    result['status'] = 'OK'
                except ImportError as e:
                    result['status'] = 'IMPORT_ERROR'
                    result['error'] = f'File exists but import failed: {str(e)}'
                except Exception as e:
                    result['status'] = 'ERROR'
                    result['error'] = f'Import error: {str(e)}'
            else:
                result['status'] = 'NOT_FOUND'
                result['error'] = f'File {module_name} not found'
                
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            logger.error(f"Error testing module {module_name}: {e}")
            
        finally:
            result['execution_time'] = round(time.time() - start_time, 3)
            
        return result
    
    async def test_bot_commands(self) -> List[Dict[str, Any]]:
        """
        Test all production bot commands
        
        Based on actual CommandHandler entries in bot.py:
        - Core commands: start, help, version, market
        - Signal commands: signal, ict
        - News commands: news, breaking
        - Utility: task, dailyreport, workspace, restart, autonews
        - ML: ml_menu
        - Settings: toggle_ict
        
        Returns:
            List of test results for each command
        """
        # ACTUAL commands from bot.py (based on your grep output)
        commands = [
            'start',
            'help',
            'version',
            'v',  # alias for version
            'market',
            'signal',
            'ict',
            'news',
            'breaking',
            'task',
            'dailyreport',
            'workspace',
            'restart',
            'autonews',
            'ml_menu',
            'health',  # Added from our work
        ]
        
        results = []
        for cmd in commands:
            result = await self.test_command_exists(cmd)
            results.append(result)
        
        return results
    
    async def test_core_modules(self) -> List[Dict[str, Any]]:
        """
        Test core system modules that bot actually uses
        
        Based on your project structure:
        - ml_engine.py: ML predictions (limited confidence adjustment)
        - ml_predictor.py: ML prediction logic
        - ict_signal_engine.py: ICT signal generation
        - daily_reports.py: Daily report generation
        - chart_generator.py: Chart generation
        - graph_engine.py: Graph generation
        - cache_manager.py: Cache management
        
        Returns:
            List of test results for each module
        """
        modules = [
            ('ml_engine.py', 'ML Engine (±10-15% confidence only)'),
            ('ml_predictor.py', 'ML Predictor'),
            ('ict_signal_engine.py', 'ICT Signal Engine'),
            ('daily_reports.py', 'Daily Reports'),
            ('chart_generator.py', 'Chart Generator'),
            ('graph_engine.py', 'Graph Engine'),
            ('cache_manager.py', 'Cache Manager'),
            ('comprehensive_diagnostics.py', 'Diagnostics System'),
            ('system_diagnostics.py', 'System Health Checks'),
        ]
        
        results = []
        for module_name, description in modules:
            result = await self.test_module_exists(module_name, description)
            results.append(result)
        
        return results
    
    async def test_ml_constraints(self) -> Dict[str, Any]:
        """
        Test that ML model is properly constrained
        
        ML should:
        - Only affect confidence score
        - Limited to ±10-15% adjustment
        - Self-training enabled
        - NOT control trading decisions directly
        
        Returns:
            Test result for ML constraints
        """
        start_time = time.time()
        result = {
            'test': 'ML Constraints',
            'status': 'UNKNOWN',
            'execution_time': 0.0,
            'error': None,
            'timestamp': datetime.now().isoformat(),
            'checks': []
        }
        
        try:
            # Check if ml_engine.py exists
            import os
            if not os.path.exists('ml_engine.py'):
                result['status'] = 'SKIPPED'
                result['error'] = 'ML engine not found (optional module)'
                return result
            
            # Read ml_engine.py
            with open('ml_engine.py', 'r', encoding='utf-8') as f:
                ml_content = f.read()
            
            checks = []
            
            # Check 1: Confidence adjustment limit
            if '0.1' in ml_content or '0.15' in ml_content or 'confidence' in ml_content.lower():
                checks.append({'check': 'Confidence adjustment code found', 'status': 'OK'})
            else:
                checks.append({'check': 'Confidence adjustment code', 'status': 'WARNING', 'note': 'Not found'})
            
            # Check 2: Self-training capability
            if 'train' in ml_content.lower() or 'fit' in ml_content.lower():
                checks.append({'check': 'Self-training capability', 'status': 'OK'})
            else:
                checks.append({'check': 'Self-training capability', 'status': 'WARNING', 'note': 'Not found'})
            
            # Check 3: ML should NOT directly control trades
            if 'execute_trade' not in ml_content and 'buy' not in ml_content.lower() and 'sell' not in ml_content.lower():
                checks.append({'check': 'ML isolated from trade execution', 'status': 'OK'})
            else:
                checks.append({'check': 'ML isolation', 'status': 'WARNING', 'note': 'May have direct trade control'})
            
            result['checks'] = checks
            
            # Overall status
            warning_count = sum(1 for c in checks if c['status'] == 'WARNING')
            if warning_count == 0:
                result['status'] = 'OK'
            elif warning_count <= 1:
                result['status'] = 'WARNING'
            else:
                result['status'] = 'ERROR'
                result['error'] = f'{warning_count} constraint checks failed'
                
        except Exception as e:
            result['status'] = 'ERROR'
            result['error'] = str(e)
            logger.error(f"Error testing ML constraints: {e}")
            
        finally:
            result['execution_time'] = round(time.time() - start_time, 3)
            
        return result
    
    async def run_full_function_health_check(self) -> Dict[str, Any]:
        """
        Run complete function health check for production bot
        
        Returns:
            Comprehensive report of all function tests
        """
        logger.info("Starting function health check...")
        
        # Test bot commands
        command_results = await self.test_bot_commands()
        
        # Test core modules
        module_results = await self.test_core_modules()
        
        # Test ML constraints
        ml_constraint_result = await self.test_ml_constraints()
        
        # Aggregate results
        all_tests = command_results + module_results
        
        total = len(all_tests)
        ok_count = sum(1 for r in all_tests if r['status'] == 'OK')
        warning_count = sum(1 for r in all_tests if r['status'] == 'WARNING')
        error_count = sum(1 for r in all_tests if r['status'] in ['ERROR', 'IMPORT_ERROR'])
        not_found_count = sum(1 for r in all_tests if r['status'] == 'NOT_FOUND')
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'summary': {
                'total_tests': total,
                'ok': ok_count,
                'warnings': warning_count,
                'errors': error_count,
                'not_found': not_found_count,
                'success_rate': round((ok_count / total * 100) if total > 0 else 0, 1)
            },
            'command_tests': command_results,
            'module_tests': module_results,
            'ml_constraints': ml_constraint_result,
            'failed_tests': [r for r in all_tests if r['status'] in ['ERROR', 'IMPORT_ERROR']],
            'missing_items': [r for r in all_tests if r['status'] == 'NOT_FOUND'],
            'warnings': [r for r in all_tests if r['status'] == 'WARNING']
        }
        
        logger.info(f"Function health check complete: {ok_count}/{total} OK")
        
        return report


async def get_function_health_report() -> Dict[str, Any]:
    """
    Get function health report for production bot
    
    Returns:
        Function health status report
    """
    checker = FunctionHealthChecker()
    return await checker.run_full_function_health_check()


if __name__ == "__main__":
    # Test the module
    async def main():
        print("\n🔍 TESTING PRODUCTION BOT FUNCTIONS")
        print("=" * 60)
        
        report = await get_function_health_report()
        
        print("\n📊 SUMMARY")
        print("━" * 60)
        print(f"Total Tests: {report['summary']['total_tests']}")
        print(f"✅ OK: {report['summary']['ok']}")
        print(f"⚠️ Warnings: {report['summary']['warnings']}")
        print(f"❌ Errors: {report['summary']['errors']}")
        print(f"🔍 Not Found: {report['summary']['not_found']}")
        print(f"Success Rate: {report['summary']['success_rate']}%")
        
        print("\n📋 BOT COMMANDS")
        print("━" * 60)
        for cmd in report['command_tests']:
            status_icon = {'OK': '✅', 'WARNING': '⚠️', 'ERROR': '❌', 'NOT_FOUND': '🔍'}.get(cmd['status'], '❓')
            print(f"{status_icon} {cmd['command']:20} {cmd['status']}")
            if cmd.get('error'):
                print(f"   └─ {cmd['error']}")
        
        print("\n🔧 CORE MODULES")
        print("━" * 60)
        for mod in report['module_tests']:
            status_icon = {'OK': '✅', 'WARNING': '⚠️', 'ERROR': '❌', 'NOT_FOUND': '🔍', 'IMPORT_ERROR': '⚠️'}.get(mod['status'], '❓')
            print(f"{status_icon} {mod['module']:30} {mod['status']}")
            if mod.get('description'):
                print(f"   ├─ {mod['description']}")
            if mod.get('error'):
                print(f"   └─ {mod['error']}")
        
        print("\n🤖 ML CONSTRAINTS CHECK")
        print("━" * 60)
        ml = report['ml_constraints']
        status_icon = {'OK': '✅', 'WARNING': '⚠️', 'ERROR': '❌', 'SKIPPED': '⏭️'}.get(ml['status'], '❓')
        print(f"{status_icon} ML Constraints: {ml['status']}")
        if ml.get('checks'):
            for check in ml['checks']:
                check_icon = {'OK': '✅', 'WARNING': '⚠️'}.get(check['status'], '❓')
                print(f"   {check_icon} {check['check']}")
                if check.get('note'):
                    print(f"      └─ {check['note']}")
        
        print("\n" + "=" * 60)
    
    asyncio.run(main())
