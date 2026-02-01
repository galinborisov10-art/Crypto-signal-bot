"""
Wiring Analyzer - Runtime-aware dependency and code wiring analysis
Phase 2C: Read-only diagnostic tool for detecting wiring issues

This analyzer:
- Analyzes ALL code REACHABLE from bot.py (imported modules and their functions)
- REACHABLE ≠ EXECUTED: Analyzes code that CAN run, not only code that HAS run
- Detects missing imports, circular dependencies, signature mismatches
- Reports issues with file, line, severity
- NO behavior changes, NO auto-fix, NO modifications
"""

import ast
import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Optional, Tuple, Any
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Configuration constants
MAX_DEPENDENCY_DEPTH = 10  # Maximum recursion depth for dependency traversal

# Known external modules (stdlib and third-party)
EXTERNAL_MODULES = {
    'telegram', 'pandas', 'numpy', 'requests', 'ta', 'matplotlib', 
    'mplfinance', 'apscheduler', 'dotenv', 'logging', 'pathlib', 
    'datetime', 'asyncio', 'json', 'os', 'sys', 'time', 'hashlib', 
    're', 'io', 'html', 'pytz', 'gc', 'uuid', 'fcntl', 'functools',
    'collections', 'typing', 'dataclasses', 'abc', 'enum', 'threading',
    'multiprocessing', 'subprocess', 'shutil', 'tempfile', 'glob',
    'pickle', 'csv', 'xml', 'sqlite3', 'configparser', 'argparse',
    'http', 'urllib', 'socket', 'ssl', 'email', 'base64', 'binascii',
    'struct', 'array', 'math', 'random', 'statistics', 'decimal',
    'fractions', 'numbers', 'itertools', 'operator', 'contextlib',
    'warnings', 'traceback', 'inspect', 'importlib', 'ast', 'dis',
    'httpx', 'aiohttp', 'pydantic', 'sqlalchemy', 'alembic', 'redis',
    'celery', 'pytest', 'unittest', 'mock', 'coverage', 'flake8',
    'black', 'isort', 'mypy', 'pylint', 'bandit', 'safety',
    # Additional third-party libraries used in this project
    'bs4', 'feedparser', 'deep_translator', 'sklearn', 'tensorflow',
    'keras', 'torch', 'transformers', 'joblib', 'scipy', 'seaborn',
    'plotly', 'dash', 'flask', 'fastapi', 'uvicorn', 'gunicorn',
    'boto3', 'botocore', 's3transfer', 'click', 'rich', 'tqdm',
    'colorama', 'termcolor', 'prettytable', 'tabulate', 'psutil'
}

# Common built-in/library methods that should not be validated
COMMON_METHODS = {
    'get', 'set', 'pop', 'append', 'extend', 'remove', 'insert',
    'update', 'items', 'keys', 'values', 'split', 'join', 'strip',
    'replace', 'format', 'startswith', 'endswith', 'find', 'index',
    'count', 'sort', 'reverse', 'copy', 'clear', 'add', 'discard',
    'read', 'write', 'close', 'open', 'print', 'len', 'str', 'int',
    'float', 'bool', 'list', 'dict', 'set', 'tuple', 'range',
    'enumerate', 'zip', 'map', 'filter', 'sorted', 'reversed',
    'sum', 'min', 'max', 'abs', 'round', 'all', 'any', 'isinstance',
    'hasattr', 'getattr', 'setattr', 'delattr', 'type', 'id',
    'send', 'reply_text', 'edit_text', 'answer', 'edit_message_text'
}


class WiringIssue:
    """Represents a single wiring issue"""
    
    def __init__(
        self,
        severity: str,  # HIGH / MEDIUM / LOW
        file: str,
        line: Optional[int],
        function: Optional[str],
        issue_type: str,
        description: str,
        reason: str
    ):
        self.severity = severity
        self.file = file
        self.line = line
        self.function = function
        self.issue_type = issue_type
        self.description = description
        self.reason = reason
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "function": self.function,
            "issue_type": self.issue_type,
            "description": self.description,
            "reason": self.reason
        }


class WiringReport:
    """Structured wiring analysis report"""
    
    def __init__(self):
        self.issues: List[WiringIssue] = []
        self.modules_analyzed = 0
        self.functions_analyzed = 0
        self.dependency_graph: Dict[str, List[str]] = {}
        self.timestamp = datetime.now(timezone.utc)
    
    def add_issue(self, issue: WiringIssue):
        """Add an issue to the report"""
        self.issues.append(issue)
    
    def format_telegram(self) -> str:
        """Format for Telegram display (compact)"""
        high_count = sum(1 for issue in self.issues if issue.severity == 'HIGH')
        med_count = sum(1 for issue in self.issues if issue.severity == 'MEDIUM')
        low_count = sum(1 for issue in self.issues if issue.severity == 'LOW')
        
        total_issues = len(self.issues)
        
        report = "🔌 *Wiring Analysis Report*\n\n"
        report += f"📊 Summary:\n"
        report += f"Issues found: {total_issues}\n"
        report += f"├─ 🔴 HIGH: {high_count}\n"
        report += f"├─ 🟡 MEDIUM: {med_count}\n"
        report += f"└─ 🟢 LOW: {low_count}\n\n"
        
        # Show HIGH severity issues
        if high_count > 0:
            report += "🔴 HIGH SEVERITY:\n"
            for issue in self.issues:
                if issue.severity == 'HIGH':
                    location = f"{issue.file}"
                    if issue.line:
                        location += f":{issue.line}"
                    report += f"• {location}\n"
                    report += f"  {issue.description}\n"
            report += "\n"
        
        # Show MEDIUM severity issues (limited to 3)
        if med_count > 0:
            report += "🟡 MEDIUM:\n"
            count = 0
            for issue in self.issues:
                if issue.severity == 'MEDIUM' and count < 3:
                    location = f"{issue.file}"
                    if issue.line:
                        location += f":{issue.line}"
                    report += f"• {location}\n"
                    report += f"  {issue.description}\n"
                    count += 1
            if med_count > 3:
                report += f"  ... and {med_count - 3} more\n"
            report += "\n"
        
        report += f"Analysis root: bot.py\n"
        report += f"Modules analyzed: {self.modules_analyzed}\n"
        
        return report
    
    def to_dict(self) -> Dict:
        """Structured data for logging/storage"""
        return {
            "timestamp": self.timestamp.isoformat(),
            "root_module": "bot.py",
            "modules_analyzed": self.modules_analyzed,
            "functions_analyzed": self.functions_analyzed,
            "issues": [issue.to_dict() for issue in self.issues],
            "dependency_graph": self.dependency_graph
        }


class WiringAnalyzer:
    """Analyzes code wiring from bot.py execution path"""
    
    def __init__(self):
        self.root_module = "bot"
        self.dependency_graph: Dict[str, List[str]] = {}
        self.function_calls: Dict[str, List[Tuple[str, int, List[str]]]] = {}  # module -> [(func_name, line, args)]
        self.function_defs: Dict[str, Dict[str, Any]] = {}  # module.func -> {params, line, ...}
        self.issues: List[WiringIssue] = []
        self.visited_modules: Set[str] = set()
        self.base_path = self._detect_base_path()
        self.module_asts: Dict[str, ast.Module] = {}  # Cache ASTs for analysis
    
    def _detect_base_path(self) -> Path:
        """Detect base path for the project"""
        # Try environment variable first
        env_path = os.getenv('BOT_BASE_PATH')
        if env_path:
            path = Path(env_path)
            if path.exists() and (path / 'bot.py').exists():
                return path
        
        # Try common paths
        for path_str in [
            '/root/Crypto-signal-bot',
            '/workspaces/Crypto-signal-bot',
            '/home/runner/work/Crypto-signal-bot/Crypto-signal-bot'
        ]:
            try:
                path = Path(path_str)
                if path.exists() and (path / 'bot.py').exists():
                    return path
            except (PermissionError, OSError):
                # Skip paths we don't have permission to access
                continue
        
        # Fallback to current directory
        return Path.cwd()
    
    def analyze(self) -> WiringReport:
        """
        Analyze wiring starting from bot.py
        
        Steps:
        1. Load bot.py module
        2. Trace all imports recursively (ALL reachable modules)
        3. Build dependency graph
        4. Analyze function definitions in all reachable modules
        5. Analyze function calls and validate signatures
        6. Detect wiring issues
        7. Return structured report
        
        Note: REACHABLE ≠ EXECUTED
        We analyze all code that CAN be called, not only code that HAS been called.
        """
        report = WiringReport()
        
        try:
            logger.info("🔌 Starting wiring analysis from bot.py")
            
            # Step 1-3: Build dependency graph (imports all reachable modules)
            self._build_dependency_graph(self.root_module)
            
            # Step 4: Analyze function definitions in all reachable modules
            self._analyze_function_definitions()
            
            # Step 5: Analyze function calls and validate signatures
            self._analyze_function_calls()
            
            # Store dependency graph in report
            report.dependency_graph = self.dependency_graph
            report.modules_analyzed = len(self.visited_modules)
            report.functions_analyzed = len(self.function_defs)
            
            # Step 6: Detect issues
            self._detect_circular_dependencies()
            self._detect_missing_imports()
            self._detect_signature_mismatches()
            
            # Step 7: Package report
            report.issues = self.issues
            
            logger.info(f"✅ Wiring analysis complete: {len(self.issues)} issues found")
            
        except Exception as e:
            logger.error(f"❌ Wiring analysis failed: {e}", exc_info=True)
            report.add_issue(WiringIssue(
                severity="HIGH",
                file="wiring_analyzer.py",
                line=None,
                function="analyze",
                issue_type="analysis_failure",
                description="Wiring analysis failed",
                reason=str(e)
            ))
        
        return report
    
    def _build_dependency_graph(self, module_name: str, depth: int = 0):
        """
        Build dependency graph by tracing imports from root module
        
        Args:
            module_name: Name of module to analyze
            depth: Current recursion depth (limit to 10)
        """
        # Prevent infinite recursion
        if depth > MAX_DEPENDENCY_DEPTH or module_name in self.visited_modules:
            return
        
        self.visited_modules.add(module_name)
        
        try:
            # Find module file path
            module_file = None
            
            # First, check if it's in the base directory
            potential_paths = [
                self.base_path / f"{module_name}.py",
                self.base_path / module_name / "__init__.py",
            ]
            
            for path in potential_paths:
                if path.exists():
                    module_file = path
                    break
            
            # If not found locally, check if already imported
            if not module_file and module_name in sys.modules:
                module = sys.modules[module_name]
                module_file_str = getattr(module, '__file__', None)
                if module_file_str:
                    module_file = Path(module_file_str)
                    # Only analyze local modules
                    if not str(module_file).startswith(str(self.base_path)):
                        return
            
            if not module_file or not module_file.exists():
                return
            
            # Parse AST to find imports
            try:
                with open(module_file, 'r', encoding='utf-8') as f:
                    tree = ast.parse(f.read(), filename=str(module_file))
                    # Cache the AST for later analysis
                    self.module_asts[module_name] = tree
            except Exception as e:
                logger.debug(f"Could not parse {module_name}: {e}")
                return
            
            # Extract imports
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        imports.append(node.module)
            
            # Store dependencies
            self.dependency_graph[module_name] = imports
            
            # Recursively analyze imported modules
            for imported_module in imports:
                # Only follow local imports (not standard library or third-party)
                if self._is_local_module(imported_module):
                    self._build_dependency_graph(imported_module, depth + 1)
        
        except Exception as e:
            logger.debug(f"Error analyzing module {module_name}: {e}")
    
    def _is_local_module(self, module_name: str) -> bool:
        """Check if module is a local project module (not stdlib or third-party)"""
        # Check if it starts with any external module
        for ext_mod in EXTERNAL_MODULES:
            if module_name.startswith(ext_mod):
                return False
        
        return True
    
    def _analyze_function_definitions(self):
        """
        Analyze all function definitions in reachable modules
        
        Extracts function signatures (parameters, defaults) for all functions
        in modules that are reachable from bot.py.
        """
        for module_name, tree in self.module_asts.items():
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    func_key = f"{module_name}.{node.name}"
                    
                    # Extract parameter info
                    params = []
                    defaults_count = len(node.args.defaults)
                    args_count = len(node.args.args)
                    required_count = args_count - defaults_count
                    
                    for i, arg in enumerate(node.args.args):
                        param_info = {
                            'name': arg.arg,
                            'required': i < required_count,
                            'position': i
                        }
                        params.append(param_info)
                    
                    self.function_defs[func_key] = {
                        'module': module_name,
                        'name': node.name,
                        'line': node.lineno,
                        'params': params,
                        'required_params': required_count,
                        'total_params': args_count,
                        'has_varargs': node.args.vararg is not None,
                        'has_kwargs': node.args.kwarg is not None,
                        'is_async': isinstance(node, ast.AsyncFunctionDef)
                    }
    
    def _analyze_function_calls(self):
        """
        Analyze function calls in reachable modules
        
        Extracts all function calls to track usage patterns and prepare
        for signature validation.
        """
        for module_name, tree in self.module_asts.items():
            calls = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    # Try to extract function name
                    func_name = None
                    if isinstance(node.func, ast.Name):
                        func_name = node.func.id
                    elif isinstance(node.func, ast.Attribute):
                        func_name = node.func.attr
                    
                    if func_name:
                        # Count arguments
                        arg_count = len(node.args)
                        kwarg_count = len(node.keywords)
                        
                        calls.append((
                            func_name,
                            getattr(node, 'lineno', 0),
                            {
                                'args': arg_count,
                                'kwargs': kwarg_count,
                                'total': arg_count + kwarg_count
                            }
                        ))
            
            if calls:
                self.function_calls[module_name] = calls
    
    def _detect_signature_mismatches(self):
        """
        Detect function calls with wrong argument counts
        
        Compares function calls against their definitions to find
        signature mismatches that would cause runtime errors.
        
        Note: Only validates calls to locally-defined functions to avoid
        false positives from built-in methods and library functions.
        """
        for module_name, calls in self.function_calls.items():
            for func_name, line, call_info in calls:
                # Skip common built-in/library methods that generate false positives
                if func_name in COMMON_METHODS:
                    continue
                
                # Look for function definition in current module
                func_key = f"{module_name}.{func_name}"
                func_def = self.function_defs.get(func_key)
                
                # If not found locally, only check imported functions from our modules
                if not func_def:
                    # Try to find in imported modules only
                    found_in_import = False
                    for imported_module in self.dependency_graph.get(module_name, []):
                        if self._is_local_module(imported_module):
                            imported_key = f"{imported_module}.{func_name}"
                            func_def = self.function_defs.get(imported_key)
                            if func_def:
                                found_in_import = True
                                break
                    
                    # If not found in our local modules, skip (likely external/built-in)
                    if not found_in_import:
                        continue
                
                if func_def:
                    # Check if call matches signature
                    required = func_def['required_params']
                    total = func_def['total_params']
                    has_varargs = func_def['has_varargs']
                    has_kwargs = func_def['has_kwargs']
                    
                    args_provided = call_info['args']
                    kwargs_provided = call_info['kwargs']
                    
                    # Skip validation if function accepts *args or **kwargs
                    if has_varargs or has_kwargs:
                        continue
                    
                    # For methods, first parameter is usually 'self' or 'cls'
                    # We don't count it in the call, so adjust required count
                    if func_def['params'] and func_def['params'][0]['name'] in ['self', 'cls']:
                        required = max(0, required - 1)
                        total = max(0, total - 1)
                    
                    # Total arguments provided (positional + keyword)
                    total_provided = args_provided + kwargs_provided
                    
                    # Check if too few arguments
                    if total_provided < required:
                        self.issues.append(WiringIssue(
                            severity="HIGH",
                            file=f"{module_name}.py",
                            line=line,
                            function=func_name,
                            issue_type="signature_mismatch",
                            description=f"Function '{func_name}' called with too few arguments",
                            reason=f"Expected at least {required} args, got {total_provided}"
                        ))
                    
                    # Check if too many arguments (and no *args)
                    elif total_provided > total and not has_varargs:
                        self.issues.append(WiringIssue(
                            severity="HIGH",
                            file=f"{module_name}.py",
                            line=line,
                            function=func_name,
                            issue_type="signature_mismatch",
                            description=f"Function '{func_name}' called with too many arguments",
                            reason=f"Expected at most {total} args, got {total_provided}"
                        ))
    
    def _detect_circular_dependencies(self):
        """Detect circular dependencies using DFS"""
        
        def has_cycle_dfs(node: str, visited: Set[str], rec_stack: Set[str], path: List[str]) -> Optional[List[str]]:
            """DFS to detect cycles in dependency graph"""
            visited.add(node)
            rec_stack.add(node)
            path.append(node)
            
            for neighbor in self.dependency_graph.get(node, []):
                if neighbor not in visited:
                    cycle = has_cycle_dfs(neighbor, visited, rec_stack, path.copy())
                    if cycle:
                        return cycle
                elif neighbor in rec_stack:
                    # Found cycle
                    cycle_start = path.index(neighbor)
                    return path[cycle_start:] + [neighbor]
            
            rec_stack.remove(node)
            return None
        
        visited: Set[str] = set()
        
        for module in self.dependency_graph.keys():
            if module not in visited:
                cycle = has_cycle_dfs(module, visited, set(), [])
                if cycle:
                    self.issues.append(WiringIssue(
                        severity="MEDIUM",
                        file=f"{cycle[0]}.py",
                        line=None,
                        function=None,
                        issue_type="circular_dependency",
                        description="Circular dependency detected",
                        reason=f"Cycle: {' → '.join(cycle)}"
                    ))
    
    def _detect_missing_imports(self):
        """Detect imports that may fail at runtime"""
        for module_name, imports in self.dependency_graph.items():
            for imported_module in imports:
                # Skip external modules
                if not self._is_local_module(imported_module):
                    continue
                
                # Check if module is reachable
                try:
                    importlib.import_module(imported_module)
                except ImportError:
                    # Only report if it's a local module that should exist
                    module_file = self.base_path / f"{imported_module.replace('.', '/')}.py"
                    if not module_file.exists():
                        # Check if it's a package
                        package_dir = self.base_path / imported_module.replace('.', '/')
                        if not (package_dir.exists() and (package_dir / '__init__.py').exists()):
                            self.issues.append(WiringIssue(
                                severity="HIGH",
                                file=f"{module_name}.py",
                                line=None,
                                function=None,
                                issue_type="missing_import",
                                description=f"Import '{imported_module}' may fail",
                                reason=f"Module not found: {imported_module}"
                            ))

