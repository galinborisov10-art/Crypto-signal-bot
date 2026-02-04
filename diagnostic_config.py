"""Configuration for diagnostic system"""
from typing import List, Dict, Any

class DiagnosticConfig:
    """Configuration for what to check and what to ignore"""
    
    # Errors to completely ignore (won't show up in reports)
    IGNORED_ERRORS = [
        # Add error codes here that should be completely ignored
    ]
    
    # Warnings to suppress based on bot mode
    OPTIONAL_WARNINGS = {
        'BINANCE_API_KEY': {
            'severity': 'INFO',  # Downgrade from CRITICAL to INFO
            'message': 'Binance API not configured (optional for signal-only mode)',
            'show_when': 'BOT_MODE != TRADING'  # Only show if not in trading mode
        },
        'BINANCE_API_SECRET': {
            'severity': 'INFO',
            'message': 'Binance API secret not configured (optional for signal-only mode)',
            'show_when': 'BOT_MODE != TRADING'
        },
    }
    
    # Auto-fix settings
    AUTO_FIX_ENABLED = True
    AUTO_FIX_SAFE_ONLY = True  # Only auto-fix operations marked as safe
    
    # Auto-fixable operations
    AUTO_FIXABLE = {
        'JOURNAL_CORRUPTED': {
            'enabled': True,
            'safe': True,
            'requires_backup': True,
            'description': 'Restore trading journal from backup'
        },
        'LOG_TOO_BIG': {
            'enabled': True,
            'safe': True,
            'requires_backup': False,
            'description': 'Rotate log files'
        },
        'CACHE_STALE': {
            'enabled': True,
            'safe': True,
            'requires_backup': True,
            'description': 'Clear stale cache entries'
        },
        'MISSING_EMPTY_FILE': {
            'enabled': True,
            'safe': True,
            'requires_backup': False,
            'description': 'Create missing file'
        },
        'JSON_INVALID': {
            'enabled': True,
            'safe': True,
            'requires_backup': True,
            'description': 'Fix invalid JSON'
        },
    }
    
    # Tests configuration
    TESTS_CONFIG = {
        'comprehensive': {
            'enabled': True,
            'timeout': 300,  # 5 minutes max
            'tests': list(range(1, 21))  # All 20 tests
        },
        'smoke': {
            'enabled': True,
            'timeout': 30,  # 30 seconds max
            'tests': [1, 2, 3, 6, 15, 18]  # Critical tests only
        },
        'quick': {
            'enabled': True,
            'timeout': 10,  # 10 seconds max
            'tests': [1, 6, 18]  # Minimal health check
        }
    }
    
    @staticmethod
    def should_ignore_error(error_code: str) -> bool:
        """Check if error should be completely ignored"""
        return error_code in DiagnosticConfig.IGNORED_ERRORS
    
    @staticmethod
    def get_optional_warning_config(var_name: str) -> Dict[str, Any]:
        """Get config for optional warnings"""
        return DiagnosticConfig.OPTIONAL_WARNINGS.get(var_name, None)
    
    @staticmethod
    def can_auto_fix(error_code: str) -> bool:
        """Check if error can be auto-fixed"""
        if not DiagnosticConfig.AUTO_FIX_ENABLED:
            return False
        
        config = DiagnosticConfig.AUTO_FIXABLE.get(error_code)
        if not config:
            return False
        
        if DiagnosticConfig.AUTO_FIX_SAFE_ONLY and not config.get('safe', False):
            return False
        
        return config.get('enabled', False)
    
    @staticmethod
    def get_auto_fix_config(error_code: str) -> Dict[str, Any]:
        """Get auto-fix configuration for error"""
        return DiagnosticConfig.AUTO_FIXABLE.get(error_code, {})
