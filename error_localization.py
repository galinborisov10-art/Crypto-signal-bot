"""
Enhanced Error Localization Module
Provides detailed error formatting with location, context, and fix suggestions
"""

import os
import re
from pathlib import Path
from typing import Dict, Optional, List

class ErrorLocalizer:
    """Enhanced error localization with detailed formatting"""
    
    def __init__(self, base_path: str = "/root/Crypto-signal-bot"):
        self.base_path = Path(base_path)
        
    def format_error(self, 
                    error_type: str,
                    message: str,
                    file_path: Optional[str] = None,
                    line_number: Optional[int] = None,
                    current_value: Optional[str] = None,
                    expected_value: Optional[str] = None,
                    fix_command: Optional[str] = None,
                    severity: str = "ERROR") -> str:
        """
        Format error with detailed information
        
        Args:
            error_type: Type of error (e.g., "Configuration Error")
            message: Error message
            file_path: Path to file with error
            line_number: Line number (if applicable)
            current_value: Current (wrong) value
            expected_value: Expected (correct) value
            fix_command: Manual fix command
            severity: ERROR, WARNING, or INFO
        """
        
        icon = "❌" if severity == "ERROR" else "⚠️" if severity == "WARNING" else "ℹ️"
        
        output = f"{icon} {severity}: {error_type}\n"
        output += "━" * 45 + "\n"
        output += f"📋 Issue: {message}\n\n"
        
        # Location information
        if file_path:
            output += "📍 Location:\n"
            output += f"  File: {file_path}\n"
            if line_number:
                output += f"  Line: {line_number}\n"
            output += "\n"
        
        # Current state
        if current_value:
            output += "📋 Current state:\n"
            output += f"  {current_value}\n\n"
        
        # Expected state
        if expected_value:
            output += "✅ Expected:\n"
            output += f"  {expected_value}\n\n"
        
        # Fix command
        if fix_command:
            output += "🔧 Fix command:\n"
            output += f"  {fix_command}\n\n"
        
        return output
    
    def locate_config_error(self, missing_key: str, file_path: str = ".env") -> Dict:
        """Locate configuration error in file"""
        
        full_path = self.base_path / file_path
        line_number = None
        current_value = "Not found"
        
        if full_path.exists():
            with open(full_path, 'r') as f:
                for i, line in enumerate(f, 1):
                    if missing_key in line:
                        line_number = i
                        current_value = line.strip()
                        if line.strip().startswith('#'):
                            current_value += "  ← Commented out"
                        break
        
        return {
            'file': str(full_path),
            'line': line_number,
            'current': current_value,
            'expected': f"{missing_key}=YOUR_VALUE_HERE"
        }
    
    def locate_import_error(self, module_name: str) -> Dict:
        """Locate import/dependency error"""
        
        # Try to find where module is imported
        import_locations = []
        
        for py_file in self.base_path.glob("*.py"):
            try:
                with open(py_file, 'r') as f:
                    for i, line in enumerate(f, 1):
                        if f"import {module_name}" in line or f"from {module_name}" in line:
                            import_locations.append({
                                'file': str(py_file),
                                'line': i,
                                'code': line.strip()
                            })
            except:
                pass
        
        return {
            'module': module_name,
            'locations': import_locations,
            'pip_command': f"pip install {module_name}"
        }
    
    def locate_file_error(self, file_path: str) -> Dict:
        """Locate file-related error"""
        
        full_path = self.base_path / file_path
        
        return {
            'file': str(full_path),
            'exists': full_path.exists(),
            'parent_exists': full_path.parent.exists(),
            'permissions': oct(os.stat(full_path).st_mode)[-3:] if full_path.exists() else None
        }
    
    def get_code_snippet(self, file_path: str, line_number: int, context: int = 3) -> str:
        """Get code snippet around error line"""
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            start = max(0, line_number - context - 1)
            end = min(len(lines), line_number + context)
            
            snippet = ""
            for i in range(start, end):
                marker = "→ " if i == line_number - 1 else "  "
                snippet += f"{marker}{i+1:4d} | {lines[i]}"
            
            return snippet
        except:
            return "Could not read file"

