"""
Function Inventory

Creates a comprehensive inventory of all functions in bot.py and main.py.
"""

import ast
import os
from typing import Dict, List, Any


def inventory_functions() -> Dict[str, Any]:
    """
    Create a complete function inventory for bot.py and main.py.
    
    Returns detailed categorization of all functions.
    """
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    bot_inventory = analyze_file_functions(os.path.join(base_path, 'bot.py'), 'bot.py')
    main_inventory = analyze_file_functions(os.path.join(base_path, 'main.py'), 'main.py')
    
    return {
        "bot.py": bot_inventory,
        "main.py": main_inventory,
        "summary": {
            "total_functions": bot_inventory['total_functions'] + main_inventory['total_functions'],
            "bot_py_functions": bot_inventory['total_functions'],
            "main_py_functions": main_inventory['total_functions'],
            "ratio": round(bot_inventory['total_functions'] / max(main_inventory['total_functions'], 1), 1)
        }
    }


def analyze_file_functions(filepath: str, filename: str) -> Dict[str, Any]:
    """Analyze all functions in a file"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
        tree = ast.parse(content)
    
    command_handlers = []
    callback_handlers = []
    message_handlers = []
    scheduler_jobs = []
    helper_functions = []
    async_functions = []
    
    # Categorization keywords
    command_keywords = ['command', 'start', 'help', 'signal', 'status', 'admin', 'settings']
    callback_keywords = ['callback', 'handle', 'button', 'query']
    scheduler_keywords = ['auto', 'scheduled', 'job', 'periodic', 'cron']
    
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_info = {
                "name": node.name,
                "line": node.lineno,
                "is_async": isinstance(node, ast.AsyncFunctionDef),
                "decorators": [get_decorator_name(dec) for dec in node.decorator_list],
                "args": [arg.arg for arg in node.args.args],
                "docstring": ast.get_docstring(node) or ""
            }
            
            # Categorize based on name and decorators
            func_name_lower = node.name.lower()
            decorators = func_info['decorators']
            
            # Check decorators first
            if any('admin' in dec.lower() for dec in decorators if dec):
                func_info['category'] = 'admin'
                command_handlers.append(func_info)
            elif 'callback' in func_name_lower or any('callback' in kw for kw in callback_keywords if kw in func_name_lower):
                func_info['category'] = 'callback'
                callback_handlers.append(func_info)
            elif 'command' in func_name_lower or any(kw in func_name_lower for kw in command_keywords):
                func_info['category'] = 'command'
                command_handlers.append(func_info)
            elif 'handler' in func_name_lower or 'handle' in func_name_lower:
                func_info['category'] = 'handler'
                message_handlers.append(func_info)
            elif any(kw in func_name_lower for kw in scheduler_keywords):
                func_info['category'] = 'scheduler'
                scheduler_jobs.append(func_info)
            else:
                func_info['category'] = 'helper'
                helper_functions.append(func_info)
            
            if func_info['is_async']:
                async_functions.append(func_info)
    
    # Special handling for main.py
    if filename == 'main.py':
        return {
            "total_functions": len(command_handlers) + len(callback_handlers) + len(message_handlers) + len(scheduler_jobs) + len(helper_functions),
            "categories": {
                "entry_point": [f for f in helper_functions if f['name'] == 'main'],
                "all_functions": command_handlers + callback_handlers + message_handlers + scheduler_jobs + helper_functions
            },
            "async_count": len(async_functions)
        }
    
    return {
        "total_functions": len(command_handlers) + len(callback_handlers) + len(message_handlers) + len(scheduler_jobs) + len(helper_functions),
        "categories": {
            "command_handlers": command_handlers[:10],  # Limit output
            "command_handler_count": len(command_handlers),
            "callback_handlers": callback_handlers[:10],
            "callback_handler_count": len(callback_handlers),
            "message_handlers": message_handlers[:10],
            "message_handler_count": len(message_handlers),
            "scheduler_jobs": scheduler_jobs[:10],
            "scheduler_job_count": len(scheduler_jobs),
            "helper_functions": helper_functions[:10],
            "helper_function_count": len(helper_functions)
        },
        "async_count": len(async_functions),
        "async_percentage": round(len(async_functions) / max(len(command_handlers) + len(callback_handlers) + len(message_handlers) + len(scheduler_jobs) + len(helper_functions), 1) * 100, 1)
    }


def get_decorator_name(decorator: ast.AST) -> str:
    """Extract decorator name from AST node"""
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Call):
        if isinstance(decorator.func, ast.Name):
            return decorator.func.id
        elif isinstance(decorator.func, ast.Attribute):
            return decorator.func.attr
    elif isinstance(decorator, ast.Attribute):
        return decorator.attr
    return "unknown"


if __name__ == "__main__":
    # Test the inventory
    results = inventory_functions()
    print("=== Function Inventory ===")
    print(f"Bot.py functions: {results['bot.py']['total_functions']}")
    print(f"Main.py functions: {results['main.py']['total_functions']}")
    print(f"\nBot.py categories:")
    for category, count in results['bot.py']['categories'].items():
        if category.endswith('_count'):
            print(f"  {category}: {count}")
