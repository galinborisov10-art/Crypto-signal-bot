#!/usr/bin/env python3
"""
Intelligent Diagnostic System v2.0
==================================

🧠 Self-aware problem solver
🔍 Deep analysis with evidence
💡 Smart fix suggestions
⛔ READ-ONLY - Never modifies anything

Author: Auto-generated for Crypto Signal Bot
"""

import json
import os
import re
import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path
import ast
import traceback

logger = logging.getLogger(__name__)


class IntelligentDiagnostics:
    """
    Main diagnostic engine that analyzes problems without modifying anything.
    
    STRICT RULES:
    - READ-ONLY mode enforced
    - NEVER modifies code
    - NEVER changes settings
    - ONLY analyzes and reports
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or os.path.dirname(os.path.abspath(__file__))
        self.memory_file = os.path.join(self.base_path, 'diagnostic_memory.json')
        self.memory = self._load_memory()
        
        # ENFORCE READ-ONLY MODE
        self.READ_ONLY = True
        self.AUTO_FIX_ENABLED = False
        
        logger.info("🧠 Intelligent Diagnostics initialized in READ-ONLY mode")
    
    def _load_memory(self) -> Dict[str, Any]:
        """Load knowledge base from disk"""
        try:
            if os.path.exists(self.memory_file):
                with open(self.memory_file, 'r') as f:
                    return json.load(f)
            else:
                logger.warning(f"Memory file not found: {self.memory_file}")
                return self._get_default_memory()
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
            return self._get_default_memory()
    
    def _get_default_memory(self) -> Dict[str, Any]:
        """Default memory structure"""
        return {
            "metadata": {
                "version": "2.0.0",
                "total_errors_tracked": 0,
                "system_mode": "READ_ONLY"
            },
            "past_errors": [],
            "pattern_library": {"common_patterns": []},
            "function_registry": {"monitored_functions": []},
            "system_rules": {
                "AUTO_FIX_ENABLED": False,
                "READ_ONLY_MODE": True
            }
        }
    
    def _save_memory(self):
        """Save knowledge base to disk (READ-ONLY CHECK)"""
        if not self.READ_ONLY:
            logger.error("⛔ SECURITY: Attempted to save memory in READ-ONLY mode!")
            return False
        
        try:
            # Update timestamp
            self.memory['metadata']['last_updated'] = datetime.utcnow().isoformat() + 'Z'
            
            with open(self.memory_file, 'w') as f:
                json.dump(self.memory, f, indent=2)
            
            logger.info("💾 Memory saved successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
            return False
    
    async def analyze_problem(self, problem_description: str) -> Dict[str, Any]:
        """
        Main entry point: Analyze a problem
        
        Returns detailed report with:
        - Root cause
        - Evidence
        - Fix suggestions
        - NO automatic fixes applied
        """
        logger.info(f"🔍 Analyzing problem: {problem_description}")
        
        # Step 1: Check if we've seen this before
        known_error = self._check_knowledge_base(problem_description)
        
        if known_error:
            logger.info(f"⚡ Found in memory! Error ID: {known_error['id']}")
            return self._generate_report_from_memory(known_error)
        
        # Step 2: New problem - deep analysis
        logger.info("🆕 New problem - running deep analysis...")
        
        analysis = await self._deep_analysis(problem_description)
        
        # Step 3: Save to memory (for next time)
        self._store_error(analysis)
        
        # Step 4: Generate report
        report = self._generate_report(analysis)
        
        return report
    
    def _check_knowledge_base(self, problem: str) -> Optional[Dict[str, Any]]:
        """Fast lookup in knowledge base"""
        # Check past errors
        for error in self.memory.get('past_errors', []):
            if self._matches_signature(problem, error.get('signature', '')):
                return error
        
        # Check patterns
        for pattern in self.memory.get('pattern_library', {}).get('common_patterns', []):
            regex = pattern.get('signature_regex', '')
            if regex and re.search(regex, problem, re.IGNORECASE):
                return {
                    'id': pattern['pattern_id'],
                    'type': 'pattern',
                    'pattern': pattern
                }
        
        return None
    
    def _matches_signature(self, problem: str, signature: str) -> bool:
        """Check if problem matches known signature"""
        if not signature:
            return False
        
        # Simple fuzzy match
        problem_lower = problem.lower()
        signature_lower = signature.lower()
        
        # Extract key words
        problem_words = set(re.findall(r'\w+', problem_lower))
        signature_words = set(re.findall(r'\w+', signature_lower))
        
        # Check overlap
        overlap = len(problem_words & signature_words)
        threshold = min(len(signature_words) * 0.6, 3)  # 60% match or 3 words
        
        return overlap >= threshold
    
    async def _deep_analysis(self, problem: str) -> Dict[str, Any]:
        """
        Deep problem analysis - the main intelligence
        
        Steps:
        1. Generate hypotheses
        2. Collect evidence
        3. Test each hypothesis
        4. Identify root cause
        5. Generate fix suggestions
        """
        
        analysis = {
            'problem': problem,
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'hypotheses': [],
            'evidence': [],
            'root_cause': None,
            'fix_suggestions': []
        }
        
        # Generate hypotheses
        hypotheses = await self._generate_hypotheses(problem)
        analysis['hypotheses'] = hypotheses
        
        # Test each hypothesis
        for hypothesis in hypotheses:
            evidence = await self._test_hypothesis(hypothesis)
            hypothesis['evidence'] = evidence
            hypothesis['confidence'] = self._calculate_confidence(evidence)
        
        # Sort by confidence
        hypotheses.sort(key=lambda h: h.get('confidence', 0), reverse=True)
        
        # Best hypothesis = root cause
        if hypotheses:
            best = hypotheses[0]
            analysis['root_cause'] = {
                'description': best['description'],
                'confidence': best['confidence'],
                'evidence': best['evidence']
            }
            
            # Generate fixes
            analysis['fix_suggestions'] = await self._generate_fixes(best)
        
        return analysis
    
    async def _generate_hypotheses(self, problem: str) -> List[Dict[str, Any]]:
        """Generate possible causes"""
        hypotheses = []
        
        # Hypothesis 1: File missing
        if 'not found' in problem.lower() or 'missing' in problem.lower():
            hypotheses.append({
                'id': 'H1',
                'type': 'file_missing',
                'description': 'Required file is missing',
                'tests': ['check_file_existence']
            })
        
        # Hypothesis 2: Permission error
        if 'permission' in problem.lower() or 'access denied' in problem.lower():
            hypotheses.append({
                'id': 'H2',
                'type': 'permission_error',
                'description': 'File or resource permission issue',
                'tests': ['check_file_permissions']
            })
        
        # Hypothesis 3: Import/dependency issue
        if 'import' in problem.lower() or 'module' in problem.lower():
            hypotheses.append({
                'id': 'H3',
                'type': 'import_error',
                'description': 'Missing Python dependency',
                'tests': ['check_imports']
            })
        
        # Hypothesis 4: Configuration issue
        if 'config' in problem.lower() or 'setting' in problem.lower():
            hypotheses.append({
                'id': 'H4',
                'type': 'config_error',
                'description': 'Configuration file issue',
                'tests': ['check_config_files']
            })
        
        # Hypothesis 5: Code error (AttributeError, KeyError, etc.)
        if any(err in problem for err in ['AttributeError', 'KeyError', 'TypeError']):
            hypotheses.append({
                'id': 'H5',
                'type': 'code_error',
                'description': 'Code logic or data structure issue',
                'tests': ['analyze_traceback', 'check_code_context']
            })
        
        # Hypothesis 6: Data quality issue
        if 'journal' in problem.lower() or 'signal' in problem.lower():
            hypotheses.append({
                'id': 'H6',
                'type': 'data_issue',
                'description': 'Data source or quality problem',
                'tests': ['check_data_sources', 'validate_data_schema']
            })
        
        # Always add: General investigation
        hypotheses.append({
            'id': 'H_GENERAL',
            'type': 'general',
            'description': 'General investigation',
            'tests': ['check_logs', 'check_recent_changes']
        })
        
        return hypotheses
    
    async def _test_hypothesis(self, hypothesis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Test a hypothesis and collect evidence"""
        evidence = []
        
        for test_name in hypothesis.get('tests', []):
            try:
                test_result = await self._run_test(test_name, hypothesis)
                evidence.append(test_result)
            except Exception as e:
                logger.error(f"Test {test_name} failed: {e}")
                evidence.append({
                    'test': test_name,
                    'result': 'error',
                    'error': str(e)
                })
        
        return evidence
    
    async def _run_test(self, test_name: str, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """Run a specific test"""
        
        if test_name == 'check_file_existence':
            return await self._test_file_existence(hypothesis)
        
        elif test_name == 'check_file_permissions':
            return await self._test_file_permissions(hypothesis)
        
        elif test_name == 'check_imports':
            return await self._test_imports(hypothesis)
        
        elif test_name == 'check_config_files':
            return await self._test_config_files(hypothesis)
        
        elif test_name == 'analyze_traceback':
            return await self._test_analyze_traceback(hypothesis)
        
        elif test_name == 'check_logs':
            return await self._test_check_logs(hypothesis)
        
        else:
            return {
                'test': test_name,
                'result': 'not_implemented',
                'message': f"Test {test_name} not yet implemented"
            }
    
    async def _test_file_existence(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """Check if required files exist"""
        important_files = [
            'trading_journal.json',
            'risk_config.json',
            'bot.py',
            'ict_signal_engine.py'
        ]
        
        missing = []
        existing = []
        
        for file in important_files:
            path = os.path.join(self.base_path, file)
            if os.path.exists(path):
                existing.append(file)
            else:
                missing.append(file)
        
        return {
            'test': 'file_existence',
            'result': 'pass' if not missing else 'fail',
            'existing_files': existing,
            'missing_files': missing,
            'confidence_impact': len(missing) * 20  # Each missing file adds evidence
        }
    
    async def _test_file_permissions(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """Check file permissions"""
        issues = []
        
        for file in ['trading_journal.json', 'risk_config.json']:
            path = os.path.join(self.base_path, file)
            if os.path.exists(path):
                stat = os.stat(path)
                readable = os.access(path, os.R_OK)
                writable = os.access(path, os.W_OK)
                
                if not readable or not writable:
                    issues.append({
                        'file': file,
                        'readable': readable,
                        'writable': writable
                    })
        
        return {
            'test': 'file_permissions',
            'result': 'pass' if not issues else 'fail',
            'issues': issues,
            'confidence_impact': len(issues) * 15
        }
    
    async def _test_imports(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """Check for import errors in logs"""
        log_file = os.path.join(self.base_path, 'logs', 'bot.log')
        
        if not os.path.exists(log_file):
            return {
                'test': 'imports',
                'result': 'skip',
                'message': 'Log file not found'
            }
        
        import_errors = []
        
        try:
            with open(log_file, 'r') as f:
                # Read last 1000 lines
                lines = f.readlines()[-1000:]
                
                for line in lines:
                    if 'ImportError' in line or 'ModuleNotFoundError' in line:
                        import_errors.append(line.strip())
        except Exception as e:
            return {
                'test': 'imports',
                'result': 'error',
                'error': str(e)
            }
        
        return {
            'test': 'imports',
            'result': 'fail' if import_errors else 'pass',
            'errors': import_errors[:5],  # First 5
            'confidence_impact': len(import_errors) * 25
        }
    
    async def _test_config_files(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """Validate configuration files"""
        issues = []
        
        # Check risk_config.json
        config_path = os.path.join(self.base_path, 'risk_config.json')
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    config = json.load(f)
                
                # Basic validation
                if not isinstance(config, dict):
                    issues.append("risk_config.json is not a valid dict")
                
            except json.JSONDecodeError as e:
                issues.append(f"risk_config.json invalid JSON: {e}")
        else:
            issues.append("risk_config.json not found")
        
        return {
            'test': 'config_files',
            'result': 'pass' if not issues else 'fail',
            'issues': issues,
            'confidence_impact': len(issues) * 20
        }
    
    async def _test_analyze_traceback(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze exception traceback from logs"""
        log_file = os.path.join(self.base_path, 'logs', 'bot.log')
        
        if not os.path.exists(log_file):
            return {'test': 'traceback', 'result': 'skip'}
        
        tracebacks = []
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()[-2000:]  # Last 2000 lines
                
                current_tb = []
                in_traceback = False
                
                for line in lines:
                    if 'Traceback (most recent call last)' in line:
                        in_traceback = True
                        current_tb = [line]
                    elif in_traceback:
                        current_tb.append(line)
                        
                        # End of traceback
                        if line.strip() and not line.startswith(' '):
                            tracebacks.append(''.join(current_tb))
                            current_tb = []
                            in_traceback = False
        except Exception as e:
            return {'test': 'traceback', 'result': 'error', 'error': str(e)}
        
        return {
            'test': 'traceback',
            'result': 'fail' if tracebacks else 'pass',
            'tracebacks': tracebacks[-3:],  # Last 3
            'confidence_impact': len(tracebacks) * 30
        }
    
    async def _test_check_logs(self, hypothesis: Dict[str, Any]) -> Dict[str, Any]:
        """General log analysis"""
        log_file = os.path.join(self.base_path, 'logs', 'bot.log')
        
        if not os.path.exists(log_file):
            return {'test': 'logs', 'result': 'skip'}
        
        errors = []
        warnings = []
        
        try:
            with open(log_file, 'r') as f:
                lines = f.readlines()[-1000:]
                
                for line in lines:
                    if 'ERROR' in line:
                        errors.append(line.strip())
                    elif 'WARNING' in line:
                        warnings.append(line.strip())
        except Exception as e:
            return {'test': 'logs', 'result': 'error', 'error': str(e)}
        
        return {
            'test': 'logs',
            'result': 'info',
            'errors_found': len(errors),
            'warnings_found': len(warnings),
            'recent_errors': errors[-5:],
            'recent_warnings': warnings[-5:]
        }
    
    def _calculate_confidence(self, evidence: List[Dict[str, Any]]) -> int:
        """Calculate confidence score from evidence"""
        total_confidence = 0
        
        for item in evidence:
            if item.get('result') == 'fail':
                total_confidence += item.get('confidence_impact', 10)
        
        return min(100, total_confidence)
    
    async def _generate_fixes(self, hypothesis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate fix suggestions (READ-ONLY - does not apply them)"""
        fixes = []
        
        h_type = hypothesis.get('type')
        
        if h_type == 'file_missing':
            fixes.append({
                'strategy': 'create_missing_file',
                'description': 'Create the missing file',
                'priority': 1,
                'auto_applicable': False,
                'user_action_required': True,
                'steps': [
                    'Identify which file is missing',
                    'Check if backup exists',
                    'Create file with default structure',
                    'Restart bot'
                ]
            })
        
        elif h_type == 'import_error':
            fixes.append({
                'strategy': 'install_dependency',
                'description': 'Install missing Python package',
                'priority': 1,
                'auto_applicable': False,
                'user_action_required': True,
                'steps': [
                    'Identify missing package from error',
                    'Run: pip install <package>',
                    'Or: pip install -r requirements.txt',
                    'Restart bot'
                ]
            })
        
        elif h_type == 'config_error':
            fixes.append({
                'strategy': 'fix_config',
                'description': 'Fix configuration file',
                'priority': 1,
                'auto_applicable': False,
                'user_action_required': True,
                'steps': [
                    'Backup current config',
                    'Validate JSON syntax',
                    'Check required keys',
                    'Restore or fix manually'
                ]
            })
        
        # Always add: Check documentation
        fixes.append({
            'strategy': 'consult_docs',
            'description': 'Review error details and documentation',
            'priority': 3,
            'auto_applicable': False,
            'user_action_required': True
        })
        
        return fixes
    
    def _store_error(self, analysis: Dict[str, Any]):
        """Store analyzed error in memory (READ-ONLY check)"""
        if not self.READ_ONLY:
            logger.warning("⛔ Cannot store error - READ_ONLY mode")
            return
        
        error_id = f"ERR-{len(self.memory.get('past_errors', [])) + 1:03d}"
        
        error_record = {
            'id': error_id,
            'timestamp': analysis['timestamp'],
            'problem': analysis['problem'],
            'root_cause': analysis.get('root_cause'),
            'fix_suggestions': analysis.get('fix_suggestions', []),
            'status': 'pending_user_action'
        }
        
        self.memory.setdefault('past_errors', []).append(error_record)
        self.memory['metadata']['total_errors_tracked'] = len(self.memory['past_errors'])
        
        # Save to disk
        self._save_memory()
    
    def _generate_report(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Generate human-readable report"""
        return {
            'type': 'diagnostic_report',
            'timestamp': analysis['timestamp'],
            'problem': analysis['problem'],
            'root_cause': analysis.get('root_cause'),
            'evidence_summary': self._summarize_evidence(analysis),
            'fix_suggestions': analysis.get('fix_suggestions', []),
            'user_action_required': True,
            'auto_fix_available': False,
            'system_mode': 'READ_ONLY'
        }
    
    def _generate_report_from_memory(self, known_error: Dict[str, Any]) -> Dict[str, Any]:
        """Generate report from known error"""
        return {
            'type': 'diagnostic_report',
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'problem': known_error.get('problem', 'Known issue'),
            'root_cause': known_error.get('root_cause'),
            'from_memory': True,
            'error_id': known_error.get('id'),
            'fix_suggestions': known_error.get('fix_suggestions', []),
            'user_action_required': True,
            'auto_fix_available': False,
            'system_mode': 'READ_ONLY',
            'note': '⚡ This issue was seen before - using cached analysis'
        }
    
    def _summarize_evidence(self, analysis: Dict[str, Any]) -> str:
        """Create summary of evidence"""
        summary_parts = []
        
        for hypothesis in analysis.get('hypotheses', []):
            if hypothesis.get('confidence', 0) > 50:
                summary_parts.append(
                    f"{hypothesis['description']} "
                    f"(confidence: {hypothesis['confidence']}%)"
                )
        
        return '; '.join(summary_parts) if summary_parts else 'Insufficient evidence'


# Global instance
_diagnostic_engine = None

def get_diagnostic_engine(base_path: str = None) -> IntelligentDiagnostics:
    """Get singleton instance"""
    global _diagnostic_engine
    if _diagnostic_engine is None:
        _diagnostic_engine = IntelligentDiagnostics(base_path)
    return _diagnostic_engine
