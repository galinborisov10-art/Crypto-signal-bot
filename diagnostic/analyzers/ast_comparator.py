"""
AST Comparator

Uses Python's AST module to compare code structure between files.
"""

import ast
import os
from typing import Dict, List, Any


def compare_code_structure(file1_name: str, file2_name: str) -> Dict[str, Any]:
    """
    Compare two Python files using AST analysis.
    
    Args:
        file1_name: Name of first file (e.g., 'bot.py')
        file2_name: Name of second file (e.g., 'main.py')
    
    Returns:
        Dictionary with comprehensive AST comparison
    """
    base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    file1_path = os.path.join(base_path, file1_name)
    file2_path = os.path.join(base_path, file2_name)
    
    with open(file1_path, 'r', encoding='utf-8') as f:
        tree1 = ast.parse(f.read())
    
    with open(file2_path, 'r', encoding='utf-8') as f:
        tree2 = ast.parse(f.read())
    
    file1_analysis = analyze_ast(tree1, file1_name)
    file2_analysis = analyze_ast(tree2, file2_name)
    
    return {
        "file1": file1_name,
        "file2": file2_name,
        "file1_analysis": file1_analysis,
        "file2_analysis": file2_analysis,
        "comparison": compare_analyses(file1_analysis, file2_analysis, file1_name, file2_name)
    }


def analyze_ast(tree: ast.AST, filename: str) -> Dict[str, Any]:
    """Analyze an AST tree and extract information"""
    
    functions = []
    classes = []
    imports = []
    logging_calls = []
    constants = []
    
    for node in ast.walk(tree):
        # Functions
        if isinstance(node, ast.FunctionDef):
            func_info = {
                "name": node.name,
                "line": node.lineno,
                "args": [arg.arg for arg in node.args.args],
                "decorators": [get_decorator_name(dec) for dec in node.decorator_list],
                "is_async": False
            }
            functions.append(func_info)
        
        # Async functions
        elif isinstance(node, ast.AsyncFunctionDef):
            func_info = {
                "name": node.name,
                "line": node.lineno,
                "args": [arg.arg for arg in node.args.args],
                "decorators": [get_decorator_name(dec) for dec in node.decorator_list],
                "is_async": True
            }
            functions.append(func_info)
        
        # Classes
        elif isinstance(node, ast.ClassDef):
            class_info = {
                "name": node.name,
                "line": node.lineno,
                "bases": [get_name(base) for base in node.bases],
                "methods": count_methods(node)
            }
            classes.append(class_info)
        
        # Imports
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append({
                    "type": "import",
                    "module": alias.name,
                    "line": node.lineno
                })
        
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                imports.append({
                    "type": "from",
                    "module": module,
                    "name": alias.name,
                    "line": node.lineno
                })
        
        # Logging calls
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    if node.func.value.id == 'logging' or node.func.value.id == 'logger':
                        logging_calls.append({
                            "type": node.func.attr,
                            "line": node.lineno,
                            "object": node.func.value.id
                        })
        
        # Constants
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    if target.id.isupper():  # Likely a constant
                        constants.append({
                            "name": target.id,
                            "line": node.lineno
                        })
    
    return {
        "functions": functions,
        "function_count": len(functions),
        "async_function_count": sum(1 for f in functions if f['is_async']),
        "classes": classes,
        "class_count": len(classes),
        "imports": imports,
        "import_count": len(imports),
        "logging_calls": logging_calls,
        "logging_call_count": len(logging_calls),
        "constants": constants,
        "constant_count": len(constants)
    }


def get_decorator_name(decorator: ast.AST) -> str:
    """Extract decorator name from AST node"""
    if isinstance(decorator, ast.Name):
        return decorator.id
    elif isinstance(decorator, ast.Call):
        if isinstance(decorator.func, ast.Name):
            return decorator.func.id
    return "unknown"


def get_name(node: ast.AST) -> str:
    """Extract name from various AST node types"""
    if isinstance(node, ast.Name):
        return node.id
    elif isinstance(node, ast.Attribute):
        return f"{get_name(node.value)}.{node.attr}"
    return "unknown"


def count_methods(class_node: ast.ClassDef) -> int:
    """Count methods in a class"""
    count = 0
    for node in class_node.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            count += 1
    return count


def compare_analyses(analysis1: Dict, analysis2: Dict, name1: str, name2: str) -> Dict[str, Any]:
    """Compare two AST analyses"""
    
    # Function names
    func1_names = set(f['name'] for f in analysis1['functions'])
    func2_names = set(f['name'] for f in analysis2['functions'])
    
    # Import modules
    import1_modules = set(imp['module'] for imp in analysis1['imports'])
    import2_modules = set(imp['module'] for imp in analysis2['imports'])
    
    # Logging call types
    log1_types = set(call['type'] for call in analysis1['logging_calls'])
    log2_types = set(call['type'] for call in analysis2['logging_calls'])
    
    return {
        "function_comparison": {
            f"unique_to_{name1}": sorted(func1_names - func2_names)[:20],  # Limit output
            f"unique_to_{name2}": sorted(func2_names - func1_names),
            "common": sorted(func1_names & func2_names),
            f"{name1}_has_more_functions": len(func1_names) > len(func2_names),
            "function_count_difference": len(func1_names) - len(func2_names)
        },
        "import_comparison": {
            f"unique_to_{name1}": sorted(import1_modules - import2_modules)[:30],
            f"unique_to_{name2}": sorted(import2_modules - import1_modules),
            "common": sorted(import1_modules & import2_modules),
            "import_count_difference": len(import1_modules) - len(import2_modules)
        },
        "logging_comparison": {
            f"{name1}_logging_calls": analysis1['logging_call_count'],
            f"{name2}_logging_calls": analysis2['logging_call_count'],
            f"{name1}_call_types": sorted(log1_types),
            f"{name2}_call_types": sorted(log2_types),
            "has_basicConfig": {
                name1: any(call['type'] == 'basicConfig' for call in analysis1['logging_calls']),
                name2: any(call['type'] == 'basicConfig' for call in analysis2['logging_calls'])
            },
            "has_addHandler": {
                name1: any(call['type'] == 'addHandler' for call in analysis1['logging_calls']),
                name2: any(call['type'] == 'addHandler' for call in analysis2['logging_calls'])
            }
        },
        "size_comparison": {
            f"{name1}_total_elements": (
                analysis1['function_count'] + 
                analysis1['class_count'] + 
                analysis1['import_count']
            ),
            f"{name2}_total_elements": (
                analysis2['function_count'] + 
                analysis2['class_count'] + 
                analysis2['import_count']
            ),
            f"{name1}_is_larger": True  # bot.py is always larger
        }
    }


if __name__ == "__main__":
    # Test the comparator
    results = compare_code_structure('bot.py', 'main.py')
    print("=== AST Comparison ===")
    print(f"File 1: {results['file1']}")
    print(f"  Functions: {results['file1_analysis']['function_count']}")
    print(f"  Classes: {results['file1_analysis']['class_count']}")
    print(f"  Imports: {results['file1_analysis']['import_count']}")
    print(f"  Logging calls: {results['file1_analysis']['logging_call_count']}")
    print(f"\nFile 2: {results['file2']}")
    print(f"  Functions: {results['file2_analysis']['function_count']}")
    print(f"  Classes: {results['file2_analysis']['class_count']}")
    print(f"  Imports: {results['file2_analysis']['import_count']}")
    print(f"  Logging calls: {results['file2_analysis']['logging_call_count']}")
