"""
Import Chain Mapper

Maps the full import dependency tree and identifies modules that configure logging.
"""

import ast
import os
from typing import Dict, List, Any, Set
import glob


def map_import_chains() -> Dict[str, Any]:
    """
    Map the complete import chain and identify logging configurations.
    
    Scans all Python files in the repository for logging setup calls.
    """
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # Get all Python files in the repository
    py_files = []
    for pattern in ['*.py', '*/*.py']:
        py_files.extend(glob.glob(os.path.join(base_path, pattern)))
    
    # Filter out test files, backups, and diagnostic files
    py_files = [f for f in py_files if not any(x in f for x in [
        '/test_', '.backup', '/tests/', '/diagnostic/', '/.', '/pull_requests/',
        '/backups/', '/legacy_', '/demo_', '/docs/'
    ])]
    
    logging_configs = {}
    modules_with_basicConfig = []
    modules_with_addHandler = []
    
    for filepath in py_files:
        relative_path = os.path.relpath(filepath, base_path)
        configs = analyze_logging_setup(filepath)
        
        if configs:
            logging_configs[relative_path] = configs
            
            for config in configs:
                if config['type'] == 'basicConfig':
                    modules_with_basicConfig.append(relative_path)
                elif config['type'] == 'addHandler':
                    modules_with_addHandler.append(relative_path)
    
    # Analyze dependencies
    import_tree = build_import_tree(base_path, py_files)
    
    return {
        "logging_configs": logging_configs,
        "total_logging_configs": sum(len(v) for v in logging_configs.values()),
        "modules_with_basicConfig": sorted(set(modules_with_basicConfig)),
        "modules_with_addHandler": sorted(set(modules_with_addHandler)),
        "total_modules_with_logging_setup": len(logging_configs),
        "import_tree": import_tree,
        "circular_dependencies": detect_circular_deps(import_tree),
        "critical_findings": {
            "main_py_calls_basicConfig": "main.py" in modules_with_basicConfig,
            "bot_py_calls_basicConfig": "bot.py" in modules_with_basicConfig,
            "bot_py_adds_handler": "bot.py" in modules_with_addHandler,
            "conflict": "main.py" in modules_with_basicConfig and "bot.py" in modules_with_basicConfig,
            "conflict_explanation": "Both main.py and bot.py call logging.basicConfig(), causing duplicate handlers"
        }
    }


def analyze_logging_setup(filepath: str) -> List[Dict[str, Any]]:
    """Analyze a file for logging configuration calls"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
    except Exception as e:
        return []
    
    configs = []
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            # Check for logging.basicConfig()
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'logging' and node.func.attr == 'basicConfig':
                        configs.append({
                            "line": node.lineno,
                            "type": "basicConfig",
                            "creates": "StreamHandler"
                        })
                    elif node.func.attr == 'addHandler':
                        # Determine handler type if possible
                        handler_type = "Unknown"
                        if node.args:
                            arg = node.args[0]
                            if isinstance(arg, ast.Call) and isinstance(arg.func, ast.Name):
                                handler_type = arg.func.id
                        
                        configs.append({
                            "line": node.lineno,
                            "type": "addHandler",
                            "handler": handler_type
                        })
    
    return configs


def build_import_tree(base_path: str, py_files: List[str]) -> Dict[str, List[str]]:
    """Build a tree of imports for the repository"""
    import_tree = {}
    
    for filepath in py_files:
        relative_path = os.path.relpath(filepath, base_path)
        imports = get_local_imports(filepath, base_path)
        import_tree[relative_path] = imports
    
    return import_tree


def get_local_imports(filepath: str, base_path: str) -> List[str]:
    """Get all local (non-stdlib, non-third-party) imports from a file"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            tree = ast.parse(content)
    except Exception:
        return []
    
    local_imports = []
    
    # Common third-party modules to exclude
    third_party = {
        'telegram', 'apscheduler', 'matplotlib', 'mplfinance', 'pandas',
        'numpy', 'dotenv', 'requests', 'scipy', 'sklearn', 'tensorflow',
        'keras', 'ta', 'pytz'
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                # Check if it's likely a local import
                if module_name not in third_party and not module_name.startswith('_'):
                    # Check if it's not a standard library module
                    if not is_stdlib_module(module_name):
                        local_imports.append(node.module)
    
    return local_imports


def is_stdlib_module(module_name: str) -> bool:
    """Check if a module is part of the standard library"""
    stdlib_modules = {
        'logging', 'sys', 'os', 'importlib', 'json', 'asyncio', 'hashlib',
        'gc', 'uuid', 'fcntl', 'datetime', 'functools', 'pathlib', 'html',
        'io', 're', 'time', 'typing', 'collections', 'traceback', 'inspect',
        'ast', 'copy', 'threading', 'warnings', 'shutil', 'subprocess',
        'tempfile', 'glob', 'pickle', 'base64', 'zlib', 'gzip', 'zipfile',
        'tarfile', 'csv', 'configparser', 'argparse', 'unittest', 'random',
        'math', 'statistics', 'decimal', 'fractions', 'itertools', 'operator',
        'array', 'queue', 'heapq', 'bisect', 'weakref', 'enum', 'dataclasses'
    }
    return module_name in stdlib_modules


def detect_circular_deps(import_tree: Dict[str, List[str]]) -> List[List[str]]:
    """Detect circular dependencies in the import tree"""
    circular = []
    
    def has_cycle(node: str, visited: Set[str], path: List[str]) -> bool:
        if node in visited:
            if node in path:
                cycle_start = path.index(node)
                circular.append(path[cycle_start:] + [node])
                return True
            return False
        
        visited.add(node)
        path.append(node)
        
        for child in import_tree.get(node, []):
            # Convert import to file path
            child_file = child.replace('.', '/') + '.py'
            if child_file in import_tree:
                if has_cycle(child_file, visited, path[:]):
                    return True
        
        return False
    
    visited = set()
    for node in import_tree:
        if node not in visited:
            has_cycle(node, visited, [])
    
    return circular


if __name__ == "__main__":
    # Test the mapper
    results = map_import_chains()
    print(f"=== Import Chain Analysis ===")
    print(f"Total modules with logging setup: {results['total_modules_with_logging_setup']}")
    print(f"Modules calling basicConfig: {len(results['modules_with_basicConfig'])}")
    print(f"  {results['modules_with_basicConfig'][:5]}")
    print(f"Modules calling addHandler: {len(results['modules_with_addHandler'])}")
    print(f"\nCritical Findings:")
    for key, value in results['critical_findings'].items():
        print(f"  {key}: {value}")
