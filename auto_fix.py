"""Auto-fix module for safe diagnostic fixes"""
import os
import json
import shutil
from datetime import datetime
from typing import Dict, Any, Optional

class AutoFixer:
    """Handles automatic fixes for safe operations"""
    
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.backup_dir = os.path.join(base_path, 'backups', 'auto_fix')
        os.makedirs(self.backup_dir, exist_ok=True)
    
    def can_auto_fix(self, error_code: str) -> bool:
        """Check if error can be safely auto-fixed"""
        safe_fixes = [
            'JOURNAL_CORRUPTED',
            'LOG_TOO_BIG',
            'CACHE_STALE',
            'MISSING_EMPTY_FILE',
            'JSON_INVALID',
        ]
        return error_code in safe_fixes
    
    def backup_file(self, file_path: str) -> Optional[str]:
        """Create backup before fixing"""
        if not os.path.exists(file_path):
            return None
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = os.path.basename(file_path)
        backup_path = os.path.join(self.backup_dir, f"{filename}.{timestamp}.backup")
        
        try:
            shutil.copy2(file_path, backup_path)
            return backup_path
        except Exception as e:
            print(f"Backup failed: {e}")
            return None
    
    def fix_corrupted_journal(self) -> Dict[str, Any]:
        """Fix corrupted trading_journal.json"""
        journal_path = os.path.join(self.base_path, 'trading_journal.json')
        
        # Backup first
        backup_path = self.backup_file(journal_path)
        
        try:
            # Try to find latest valid backup
            backups = sorted([
                f for f in os.listdir(os.path.join(self.base_path, 'backups'))
                if 'trading_journal' in f
            ], reverse=True)
            
            if backups:
                # Restore from backup
                latest_backup = os.path.join(self.base_path, 'backups', backups[0])
                shutil.copy2(latest_backup, journal_path)
                return {
                    "success": True,
                    "action": "Restored from backup",
                    "backup_used": backups[0],
                    "backup_created": backup_path
                }
            else:
                # Create new empty journal
                with open(journal_path, 'w') as f:
                    json.dump([], f)
                return {
                    "success": True,
                    "action": "Created new empty journal",
                    "backup_created": backup_path
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "backup_created": backup_path
            }
    
    def fix_log_too_big(self) -> Dict[str, Any]:
        """Rotate large log file"""
        log_path = os.path.join(self.base_path, 'bot.log')
        
        if not os.path.exists(log_path):
            return {"success": False, "error": "Log file not found"}
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            archive_path = os.path.join(
                self.base_path, 
                'logs_archive', 
                f'bot.{timestamp}.log'
            )
            os.makedirs(os.path.dirname(archive_path), exist_ok=True)
            
            # Move old log
            shutil.move(log_path, archive_path)
            
            # Create new empty log
            open(log_path, 'w').close()
            
            return {
                "success": True,
                "action": "Log rotated",
                "archived_to": archive_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def fix_stale_cache(self) -> Dict[str, Any]:
        """Clear stale cache entries"""
        cache_path = os.path.join(self.base_path, 'signal_cache.json')
        
        # Backup first
        backup_path = self.backup_file(cache_path)
        
        try:
            if not os.path.exists(cache_path):
                return {"success": False, "error": "Cache file not found"}
            
            with open(cache_path, 'r') as f:
                cache = json.load(f)
            
            # Remove entries older than 24 hours
            from datetime import datetime, timedelta
            cutoff = datetime.now() - timedelta(hours=24)
            
            cleaned_cache = {}
            removed_count = 0
            
            for signal_id, data in cache.items():
                if isinstance(data, dict):
                    timestamp_str = data.get('timestamp')
                    if timestamp_str:
                        try:
                            timestamp = datetime.fromisoformat(timestamp_str)
                            if timestamp > cutoff:
                                cleaned_cache[signal_id] = data
                            else:
                                removed_count += 1
                        except:
                            # Keep if timestamp invalid
                            cleaned_cache[signal_id] = data
            
            # Write cleaned cache
            with open(cache_path, 'w') as f:
                json.dump(cleaned_cache, f, indent=2)
            
            return {
                "success": True,
                "action": "Cache cleaned",
                "removed_entries": removed_count,
                "backup_created": backup_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "backup_created": backup_path
            }
    
    def fix_missing_file(self, file_path: str, default_content: Any = None) -> Dict[str, Any]:
        """Create missing file with default content"""
        try:
            if default_content is None:
                # Empty JSON array for JSON files
                if file_path.endswith('.json'):
                    default_content = []
                else:
                    default_content = ""
            
            # Create directory if needed
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w') as f:
                if isinstance(default_content, (dict, list)):
                    json.dump(default_content, f, indent=2)
                else:
                    f.write(str(default_content))
            
            return {
                "success": True,
                "action": "File created",
                "file": file_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def fix_json_invalid(self, file_path: str) -> Dict[str, Any]:
        """Fix invalid JSON file"""
        backup_path = self.backup_file(file_path)
        
        try:
            # Try to restore from backup first
            backup_dir = os.path.join(self.base_path, 'backups')
            filename = os.path.basename(file_path)
            
            backups = sorted([
                f for f in os.listdir(backup_dir)
                if filename in f and f.endswith('.backup')
            ], reverse=True)
            
            if backups:
                # Restore from latest backup
                latest_backup = os.path.join(backup_dir, backups[0])
                shutil.copy2(latest_backup, file_path)
                return {
                    "success": True,
                    "action": "Restored from backup",
                    "backup_used": backups[0],
                    "backup_created": backup_path
                }
            else:
                # Create new empty structure
                with open(file_path, 'w') as f:
                    json.dump([], f)
                return {
                    "success": True,
                    "action": "Created new empty file",
                    "backup_created": backup_path
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "backup_created": backup_path
            }
    
    def rollback_fix(self, backup_path: str, target_path: str) -> Dict[str, Any]:
        """Rollback a fix using backup"""
        try:
            if not os.path.exists(backup_path):
                return {"success": False, "error": "Backup not found"}
            
            shutil.copy2(backup_path, target_path)
            return {
                "success": True,
                "action": "Rollback completed",
                "restored_from": backup_path
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
