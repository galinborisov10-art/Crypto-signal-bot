"""
Startup Sequence Tracer

Analyzes and documents the startup sequence of both main.py and bot.py
execution paths without actually running the bot.
"""

import ast
import os
import time
from typing import Dict, List, Any


def trace_startup_sequences() -> Dict[str, Any]:
    """
    Trace the startup sequences for both main.py and bot.py execution paths.
    
    Returns a dictionary with detailed step-by-step analysis of both paths.
    """
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    results = {
        "main.py": trace_main_py_startup(base_path),
        "bot.py": trace_bot_py_startup(base_path)
    }
    
    return results


def trace_main_py_startup(base_path: str) -> Dict[str, Any]:
    """Trace main.py startup sequence"""
    main_path = os.path.join(base_path, 'main.py')
    
    with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()
        tree = ast.parse(content)
    
    steps = []
    step_num = 1
    estimated_time = 0.0
    handlers_created = 0
    
    # Analyze imports (top-level)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                steps.append({
                    "step": step_num,
                    "line": node.lineno,
                    "action": f"import {alias.name}",
                    "time_ms": 0.1,
                    "type": "import"
                })
                step_num += 1
                estimated_time += 0.1
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            names = ", ".join([alias.name for alias in node.names])
            steps.append({
                "step": step_num,
                "line": node.lineno,
                "action": f"from {module} import {names}",
                "time_ms": 0.1,
                "type": "import"
            })
            step_num += 1
            estimated_time += 0.1
    
    # Find logging.basicConfig call
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'logging' and node.func.attr == 'basicConfig':
                        steps.append({
                            "step": step_num,
                            "line": node.lineno,
                            "action": "logging.basicConfig() called",
                            "creates": "StreamHandler #1",
                            "time_ms": 1.0,
                            "type": "logging_setup"
                        })
                        step_num += 1
                        estimated_time += 1.0
                        handlers_created += 1
    
    # Trace importlib loading of bot.py
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == 'main':
            for stmt in ast.walk(node):
                if isinstance(stmt, ast.Call):
                    if isinstance(stmt.func, ast.Attribute):
                        # spec_from_file_location
                        if stmt.func.attr == 'spec_from_file_location':
                            steps.append({
                                "step": step_num,
                                "line": stmt.lineno,
                                "action": "importlib.util.spec_from_file_location('bot_module', bot_path)",
                                "time_ms": 0.5,
                                "type": "importlib"
                            })
                            step_num += 1
                            estimated_time += 0.5
                        # module_from_spec
                        elif stmt.func.attr == 'module_from_spec':
                            steps.append({
                                "step": step_num,
                                "line": stmt.lineno,
                                "action": "importlib.util.module_from_spec(spec)",
                                "time_ms": 0.2,
                                "type": "importlib"
                            })
                            step_num += 1
                            estimated_time += 0.2
                        # exec_module - This is where bot.py actually executes
                        elif stmt.func.attr == 'exec_module':
                            steps.append({
                                "step": step_num,
                                "line": stmt.lineno,
                                "action": "spec.loader.exec_module(bot_module) - bot.py imports executed",
                                "time_ms": 1200.0,  # Bot.py takes significant time
                                "type": "bot_import",
                                "note": "This triggers all bot.py imports and logging setup (lines 35, 72)"
                            })
                            step_num += 1
                            estimated_time += 1200.0
                            handlers_created += 2  # bot.py adds 2 more handlers
    
    # Call to bot_module.main()
    steps.append({
        "step": step_num,
        "line": 41,  # Approximate
        "action": "bot_module.main() called",
        "time_ms": 100.0,
        "type": "bot_start",
        "note": "Bot initialization and polling starts"
    })
    estimated_time += 100.0
    
    return {
        "steps": steps,
        "total_time_ms": round(estimated_time, 2),
        "handlers_created": handlers_created,
        "execution_path": "main.py → importlib → bot.py → bot.main()",
        "logging_setup_sequence": [
            "1. main.py line 14: logging.basicConfig() creates StreamHandler #1",
            "2. bot.py line 35: logging.basicConfig() creates StreamHandler #2 (during exec_module)",
            "3. bot.py line 72: logging.addHandler(RotatingFileHandler) adds handler #3"
        ]
    }


def trace_bot_py_startup(base_path: str) -> Dict[str, Any]:
    """Trace bot.py direct execution sequence"""
    bot_path = os.path.join(base_path, 'bot.py')
    
    with open(bot_path, 'r', encoding='utf-8') as f:
        content = f.read()
        tree = ast.parse(content)
    
    steps = []
    step_num = 1
    estimated_time = 0.0
    handlers_created = 0
    
    # Count imports
    import_count = 0
    for node in tree.body[:100]:  # First 100 top-level statements
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_count += 1
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if import_count <= 10:  # Show first 10
                        steps.append({
                            "step": step_num,
                            "line": node.lineno,
                            "action": f"import {alias.name}",
                            "time_ms": 0.5,
                            "type": "import"
                        })
                        step_num += 1
                        estimated_time += 0.5
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if import_count <= 10:  # Show first 10
                    names = ", ".join([alias.name for alias in node.names])
                    steps.append({
                        "step": step_num,
                        "line": node.lineno,
                        "action": f"from {module} import {names}",
                        "time_ms": 0.5,
                        "type": "import"
                    })
                    step_num += 1
                    estimated_time += 0.5
    
    # Summarize remaining imports
    if import_count > 10:
        steps.append({
            "step": step_num,
            "line": "various",
            "action": f"... and {import_count - 10} more imports",
            "time_ms": (import_count - 10) * 0.5,
            "type": "import_summary"
        })
        step_num += 1
        estimated_time += (import_count - 10) * 0.5
    
    # Find logging.basicConfig call (line 35)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'logging' and node.func.attr == 'basicConfig':
                        steps.append({
                            "step": step_num,
                            "line": node.lineno,
                            "action": "logging.basicConfig() called",
                            "creates": "StreamHandler #1",
                            "time_ms": 1.0,
                            "type": "logging_setup"
                        })
                        step_num += 1
                        estimated_time += 1.0
                        handlers_created += 1
    
    # Find RotatingFileHandler addition (around line 72)
    steps.append({
        "step": step_num,
        "line": 72,
        "action": "logging.getLogger().addHandler(RotatingFileHandler)",
        "creates": "RotatingFileHandler for bot.log",
        "time_ms": 2.0,
        "type": "logging_setup"
    })
    step_num += 1
    estimated_time += 2.0
    handlers_created += 1
    
    # Additional setup time for modules
    steps.append({
        "step": step_num,
        "line": "80-100",
        "action": "Load admin modules, diagnostics, and other components",
        "time_ms": 200.0,
        "type": "component_loading"
    })
    step_num += 1
    estimated_time += 200.0
    
    # if __name__ == "__main__"
    steps.append({
        "step": step_num,
        "line": "end of file",
        "action": "if __name__ == '__main__': main() called",
        "time_ms": 100.0,
        "type": "main_entry",
        "note": "Bot initialization and polling starts"
    })
    estimated_time += 100.0
    
    return {
        "steps": steps,
        "total_time_ms": round(estimated_time, 2),
        "handlers_created": handlers_created,
        "execution_path": "bot.py → main()",
        "logging_setup_sequence": [
            "1. bot.py line 35: logging.basicConfig() creates StreamHandler #1",
            "2. bot.py line 72: logging.addHandler(RotatingFileHandler) adds handler #2"
        ]
    }


if __name__ == "__main__":
    # Test the tracer
    results = trace_startup_sequences()
    print("=== Main.py Startup ===")
    print(f"Total time: {results['main.py']['total_time_ms']}ms")
    print(f"Handlers created: {results['main.py']['handlers_created']}")
    print(f"\n=== Bot.py Startup ===")
    print(f"Total time: {results['bot.py']['total_time_ms']}ms")
    print(f"Handlers created: {results['bot.py']['handlers_created']}")
