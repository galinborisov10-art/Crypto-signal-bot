"""Enhanced error localization for diagnostics"""
import os
import re
from typing import Dict, Any, Optional, List

class ErrorLocalizer:
    """Provides detailed location information for errors"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
    
    def locate_env_var(self, var_name: str) -> Dict[str, Any]:
        """Find exact location of env var in .env file"""
        env_file = os.path.join(self.base_path, '.env')
        
        result = {
            "file": env_file,
            "exists": os.path.exists(env_file),
            "line_number": None,
            "current_value": None,
            "is_commented": False,
            "context": []
        }
        
        if not result["exists"]:
            return result
        
        try:
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            for i, line in enumerate(lines, 1):
                # Check for exact match or commented
                if var_name in line:
                    result["line_number"] = i
                    result["current_value"] = line.strip()
                    result["is_commented"] = line.strip().startswith('#')
                    
                    # Get context (3 lines before, 3 after)
                    start = max(0, i-4)
                    end = min(len(lines), i+3)
                    result["context"] = [
                        {"line": j+1, "content": lines[j].rstrip(), "is_target": j+1 == i}
                        for j in range(start, end)
                    ]
                    break
        except Exception as e:
            result["error"] = str(e)
        
        return result
    
    def locate_json_error(self, file_path: str) -> Dict[str, Any]:
        """Find exact location of JSON syntax error"""
        result = {
            "file": file_path,
            "exists": os.path.exists(file_path),
            "error_line": None,
            "error_column": None,
            "error_message": None,
            "context": None
        }
        
        if not result["exists"]:
            return result
        
        try:
            import json
            with open(file_path, 'r') as f:
                content = f.read()
                json.loads(content)  # Try to parse
                result["valid"] = True
        except json.JSONDecodeError as e:
            result["valid"] = False
            result["error_line"] = e.lineno
            result["error_column"] = e.colno
            result["error_message"] = e.msg
            
            # Get context around error
            try:
                lines = content.split('\n')
                start = max(0, e.lineno - 3)
                end = min(len(lines), e.lineno + 2)
                result["context"] = [
                    {
                        "line": i+1,
                        "content": lines[i],
                        "is_error": i+1 == e.lineno,
                        "marker": " " * (e.colno - 1) + "^" if i+1 == e.lineno else ""
                    }
                    for i in range(start, end)
                ]
            except:
                pass
        except Exception as e:
            result["error_message"] = str(e)
        
        return result
    
    def format_error_location(self, error_type: str, location_data: Dict[str, Any]) -> str:
        """Format location data into readable string"""
        
        if error_type == "env_var":
            if not location_data["exists"]:
                return f"📍 File not found: {location_data['file']}\n   Create it first!"
            
            if location_data["line_number"]:
                status = "commented out ❌" if location_data["is_commented"] else "found ✅"
                msg = f"📍 {location_data['file']}:{location_data['line_number']}\n"
                msg += f"   Status: {status}\n"
                msg += f"   Current: {location_data['current_value']}\n"
                
                if location_data.get("context"):
                    msg += "\n📋 Context:\n"
                    for ctx in location_data["context"]:
                        prefix = ">>>" if ctx["is_target"] else "   "
                        msg += f"{prefix} {ctx['line']:3d} | {ctx['content']}\n"
                
                return msg
            else:
                return f"📍 Not found in {location_data['file']}\n   ✅ Expected: Add this line to .env file"
        
        elif error_type == "json":
            if not location_data["exists"]:
                return f"📍 File not found: {location_data['file']}"
            
            if location_data.get("valid"):
                return f"✅ JSON valid: {location_data['file']}"
            
            msg = f"📍 {location_data['file']}:{location_data['error_line']}:{location_data['error_column']}\n"
            msg += f"   Error: {location_data['error_message']}\n"
            
            if location_data.get("context"):
                msg += "\n📋 Context:\n"
                for ctx in location_data["context"]:
                    prefix = ">>>" if ctx["is_error"] else "   "
                    msg += f"{prefix} {ctx['line']:3d} | {ctx['content']}\n"
                    if ctx.get("marker"):
                        msg += f"       {ctx['marker']}\n"
            
            return msg
        
        return str(location_data)
