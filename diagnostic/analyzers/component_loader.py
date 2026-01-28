"""
Component Loader Analyzer

Tracks all imports and component loading in main.py and bot.py
"""

import ast
import os
from typing import Dict, List, Any


def analyze_components() -> Dict[str, Any]:
    """
    Analyze component loading in both main.py and bot.py.
    
    Returns detailed information about imports and loading order.
    """
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    main_imports = analyze_file_imports(os.path.join(base_path, 'main.py'))
    bot_imports = analyze_file_imports(os.path.join(base_path, 'bot.py'))
    
    return {
        "main.py_imports": main_imports,
        "bot.py_imports": bot_imports,
        "total_modules_loaded_main": count_total_modules(main_imports, bot_imports),
        "total_modules_loaded_bot": count_total_modules_bot_only(bot_imports),
        "loading_order": {
            "main.py_path": [
                "1. main.py standard library imports (logging, sys, os, importlib.util)",
                "2. main.py logging.basicConfig() - creates StreamHandler #1",
                "3. bot.py loaded via importlib.util.exec_module()",
                "4. bot.py standard library imports (20+ modules)",
                "5. bot.py third-party imports (telegram, apscheduler, matplotlib, etc.)",
                "6. bot.py local imports (admin_module, diagnostics, ML engines, etc.)",
                "7. bot.py logging.basicConfig() - creates StreamHandler #2",
                "8. bot.py addHandler(RotatingFileHandler) - adds handler #3",
                "9. bot_module.main() called"
            ],
            "bot.py_path": [
                "1. bot.py standard library imports (20+ modules)",
                "2. bot.py third-party imports (telegram, apscheduler, matplotlib, etc.)",
                "3. bot.py local imports (admin_module, diagnostics, ML engines, etc.)",
                "4. bot.py logging.basicConfig() - creates StreamHandler #1",
                "5. bot.py addHandler(RotatingFileHandler) - adds handler #2",
                "6. main() called via if __name__ == '__main__'"
            ]
        },
        "differences": {
            "main_py_only": main_imports["standard_library"],
            "extra_handler_in_main_path": "main.py creates an extra StreamHandler before bot.py loads",
            "handler_count_main_path": 3,
            "handler_count_bot_path": 2
        }
    }


def analyze_file_imports(filepath: str) -> Dict[str, List[str]]:
    """Analyze all imports in a Python file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        tree = ast.parse(content)
    
    standard_library = []
    third_party = []
    local = []
    
    # Standard library modules (common ones)
    stdlib_modules = {
        'logging', 'sys', 'os', 'importlib', 'json', 'asyncio', 'hashlib', 
        'gc', 'uuid', 'fcntl', 'datetime', 'functools', 'pathlib', 'html',
        'io', 're', 'time', 'typing', 'collections', 'traceback', 'inspect',
        'ast', 'copy', 'threading', 'warnings', 'shutil'
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                module_name = alias.name.split('.')[0]
                if module_name in stdlib_modules or module_name.startswith('_'):
                    if module_name not in standard_library:
                        standard_library.append(module_name)
                else:
                    if alias.name not in third_party and alias.name not in local:
                        third_party.append(alias.name)
        
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                module_name = node.module.split('.')[0]
                
                if module_name in stdlib_modules or module_name.startswith('_'):
                    if module_name not in standard_library:
                        standard_library.append(module_name)
                elif module_name in ['telegram', 'apscheduler', 'matplotlib', 'mplfinance', 
                                     'pandas', 'numpy', 'dotenv', 'requests', 'scipy',
                                     'sklearn', 'tensorflow', 'keras', 'ta', 'pytz']:
                    if module_name not in third_party:
                        third_party.append(module_name)
                else:
                    # Likely a local import
                    full_import = f"{node.module} ({', '.join([alias.name for alias in node.names])})"
                    if full_import not in local:
                        local.append(full_import)
    
    # Special handling for main.py's bot.py import
    if 'main.py' in filepath:
        local.append("bot.py (via importlib)")
    
    return {
        "standard_library": sorted(standard_library),
        "third_party": sorted(third_party),
        "local": sorted(local)
    }


def count_total_modules(main_imports: Dict, bot_imports: Dict) -> int:
    """Count total unique modules loaded when running via main.py"""
    # main.py modules + bot.py modules (bot.py is loaded by main.py)
    all_modules = set()
    
    for category in ['standard_library', 'third_party', 'local']:
        all_modules.update(main_imports.get(category, []))
        all_modules.update(bot_imports.get(category, []))
    
    return len(all_modules)


def count_total_modules_bot_only(bot_imports: Dict) -> int:
    """Count total modules when running bot.py directly"""
    all_modules = set()
    
    for category in ['standard_library', 'third_party', 'local']:
        all_modules.update(bot_imports.get(category, []))
    
    return len(all_modules)


if __name__ == "__main__":
    # Test the analyzer
    results = analyze_components()
    print("=== Main.py Imports ===")
    print(f"Standard Library: {len(results['main.py_imports']['standard_library'])}")
    print(f"Third Party: {len(results['main.py_imports']['third_party'])}")
    print(f"Local: {len(results['main.py_imports']['local'])}")
    print(f"\n=== Bot.py Imports ===")
    print(f"Standard Library: {len(results['bot.py_imports']['standard_library'])}")
    print(f"Third Party: {len(results['bot.py_imports']['third_party'])}")
    print(f"Local: {len(results['bot.py_imports']['local'])}")
    print(f"\nTotal modules (main.py path): {results['total_modules_loaded_main']}")
    print(f"Total modules (bot.py path): {results['total_modules_loaded_bot']}")
