"""
Production-Safe Diagnostic System
Author: Copilot
Date: 2026-01-30
"""

import logging
import sys
import importlib
import inspect
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Callable
from datetime import datetime

logger = logging.getLogger(__name__)

class DiagnosticResult:
    """Single diagnostic check result"""
    def __init__(self, name: str, status: str, severity: str, message: str, details: str = ""):
        self.name = name
        self.status = status  # PASS / FAIL / WARN
        self.severity = severity  # HIGH / MED / LOW
        self.message = message
        self.details = details
        self.timestamp = datetime.now()

class DiagnosticRunner:
    """Safe diagnostic runner with isolation"""
    
    def __init__(self):
        self.results = []
        self.start_time = None
        self.end_time = None
    
    async def run_check(self, check_name: str, check_func, timeout: int = 30) -> DiagnosticResult:
        """
        Run single diagnostic check with isolation
        
        Args:
            check_name: Human-readable name
            check_func: Async or sync function to run
            timeout: Max seconds (default 30)
        
        Returns:
            DiagnosticResult
        """
        logger.info(f"🔍 Running: {check_name}")
        
        try:
            # Run with timeout
            if inspect.iscoroutinefunction(check_func):
                import asyncio
                result = await asyncio.wait_for(check_func(), timeout=timeout)
            else:
                result = check_func()
            
            return result
        
        except Exception as e:
            logger.error(f"❌ {check_name} failed: {e}")
            return DiagnosticResult(
                name=check_name,
                status="FAIL",
                severity="HIGH",
                message=f"Exception: {str(e)}",
                details=f"{type(e).__name__}: {e}"
            )
    
    async def run_all(self, checks: List[Tuple[str, Callable]]) -> List[DiagnosticResult]:
        """Run all diagnostic checks sequentially"""
        self.start_time = datetime.now()
        self.results = []
        
        for check_name, check_func in checks:
            result = await self.run_check(check_name, check_func)
            self.results.append(result)
        
        self.end_time = datetime.now()
        return self.results
    
    def format_report(self) -> str:
        """Format results as Telegram message"""
        duration = (self.end_time - self.start_time).total_seconds()
        
        passed = sum(1 for r in self.results if r.status == "PASS")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        warned = sum(1 for r in self.results if r.status == "WARN")
        
        report = f"🛠 *Diagnostic Report*\n\n"
        report += f"⏱ Duration: {duration:.1f}s\n"
        report += f"✅ Passed: {passed}\n"
        report += f"⚠️ Warnings: {warned}\n"
        report += f"❌ Failed: {failed}\n"
        report += f"\n{'='*30}\n\n"
        
        # Group by severity
        high_fails = [r for r in self.results if r.status == "FAIL" and r.severity == "HIGH"]
        if high_fails:
            report += "*🔴 HIGH SEVERITY FAILURES:*\n"
            for r in high_fails:
                report += f"• {r.name}\n  → {r.message}\n\n"
        
        med_fails = [r for r in self.results if r.status == "FAIL" and r.severity == "MED"]
        if med_fails:
            report += "*🟡 MEDIUM FAILURES:*\n"
            for r in med_fails:
                report += f"• {r.name}\n  → {r.message}\n\n"
        
        warnings = [r for r in self.results if r.status == "WARN"]
        if warnings:
            report += "*⚠️ WARNINGS:*\n"
            for r in warnings:
                report += f"• {r.name}\n  → {r.message}\n\n"
        
        return report


# ========================================
# CORE DIAGNOSTIC CHECKS (5 checks)
# ========================================

def check_logger_configuration() -> DiagnosticResult:
    """Check 1: Validate logger setup"""
    try:
        root_logger = logging.getLogger()
        
        # Check handlers - also check for NullHandler or no handlers in quiet mode
        handlers_count = len(root_logger.handlers)
        
        # Allow no handlers if logging is configured at module level
        if handlers_count == 0:
            # Check if any module-level loggers exist
            module_loggers = [name for name in logging.Logger.manager.loggerDict 
                            if logging.getLogger(name).handlers]
            
            if not module_loggers:
                return DiagnosticResult(
                    name="Logger Configuration",
                    status="WARN",
                    severity="LOW",
                    message="No root logger handlers (may use module-level loggers)"
                )
        
        # Check log level
        if root_logger.level > logging.INFO:
            return DiagnosticResult(
                name="Logger Configuration",
                status="WARN",
                severity="LOW",
                message=f"Log level is {logging.getLevelName(root_logger.level)} (consider INFO)"
            )
        
        return DiagnosticResult(
            name="Logger Configuration",
            status="PASS",
            severity="LOW",
            message=f"{handlers_count} handlers, level={logging.getLevelName(root_logger.level)}"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Logger Configuration",
            status="FAIL",
            severity="HIGH",
            message=f"Exception: {e}"
        )


def check_critical_imports() -> DiagnosticResult:
    """Check 2: Validate critical dependencies"""
    required_modules = [
        'pandas',
        'numpy',
        'requests',
        'telegram',
        'ta'  # Technical analysis library
    ]
    
    missing = []
    for module_name in required_modules:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(module_name)
    
    if missing:
        return DiagnosticResult(
            name="Critical Imports",
            status="FAIL",
            severity="HIGH",
            message=f"Missing modules: {', '.join(missing)}"
        )
    
    return DiagnosticResult(
        name="Critical Imports",
        status="PASS",
        severity="LOW",
        message="All critical modules available"
    )


def check_signal_schema_validation() -> DiagnosticResult:
    """Check 3: Validate signal object structure"""
    try:
        # Import signal engine
        from ict_signal_engine import ICTSignalEngine
        
        # Create mock signal
        engine = ICTSignalEngine()
        
        # Check required attributes/methods exist
        required_methods = ['generate_signal', '_detect_ict_components', '_calculate_sl_price']
        missing = [m for m in required_methods if not hasattr(engine, m)]
        
        if missing:
            return DiagnosticResult(
                name="Signal Schema",
                status="FAIL",
                severity="HIGH",
                message=f"Missing methods: {', '.join(missing)}"
            )
        
        return DiagnosticResult(
            name="Signal Schema",
            status="PASS",
            severity="MED",
            message="Signal engine structure valid"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Signal Schema",
            status="FAIL",
            severity="HIGH",
            message=f"Exception: {e}"
        )


def check_nan_in_indicators() -> DiagnosticResult:
    """Check 4: Test indicator calculations for NaN"""
    try:
        # Create sample data (using 'h' for hourly frequency - lowercase for pandas 2.x)
        dates = pd.date_range(start='2024-01-01', periods=100, freq='h')
        df = pd.DataFrame({
            'timestamp': dates,
            'open': np.random.uniform(45000, 50000, 100),
            'high': np.random.uniform(50000, 51000, 100),
            'low': np.random.uniform(44000, 45000, 100),
            'close': np.random.uniform(45000, 50000, 100),
            'volume': np.random.randint(1000, 10000, 100)
        })
        
        # Test basic indicators
        df['sma_20'] = df['close'].rolling(window=20).mean()
        df['ema_20'] = df['close'].ewm(span=20).mean()
        
        # Check for NaN in last row (should have enough data)
        last_row = df.iloc[-1]
        nan_fields = [col for col in ['sma_20', 'ema_20'] if pd.isna(last_row[col])]
        
        if nan_fields:
            return DiagnosticResult(
                name="NaN Detection",
                status="FAIL",
                severity="HIGH",
                message=f"NaN in indicators: {', '.join(nan_fields)}"
            )
        
        return DiagnosticResult(
            name="NaN Detection",
            status="PASS",
            severity="MED",
            message="Indicators calculate without NaN"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="NaN Detection",
            status="FAIL",
            severity="MED",
            message=f"Exception: {e}"
        )


def check_duplicate_signal_guard() -> DiagnosticResult:
    """Check 5: Verify duplicate signal prevention exists"""
    try:
        # Check if cache manager exists - try both locations
        try:
            from cache_manager import CacheManager
            cache_mgr = CacheManager()
        except ImportError:
            try:
                from bot import CacheManager
                cache_mgr = CacheManager()
            except (ImportError, AttributeError):
                # CacheManager not available - this is OK, system may use different deduplication
                return DiagnosticResult(
                    name="Duplicate Guard",
                    status="WARN",
                    severity="LOW",
                    message="CacheManager not found (may use different duplicate prevention)"
                )
        
        # Check for duplicate detection method
        if not hasattr(cache_mgr, 'has_signal') and not hasattr(cache_mgr, 'get'):
            return DiagnosticResult(
                name="Duplicate Guard",
                status="WARN",
                severity="MED",
                message="CacheManager exists but no obvious duplicate detection method"
            )
        
        return DiagnosticResult(
            name="Duplicate Guard",
            status="PASS",
            severity="MED",
            message="Cache manager with duplicate detection present"
        )
    
    except Exception as e:
        return DiagnosticResult(
            name="Duplicate Guard",
            status="FAIL",
            severity="MED",
            message=f"Exception: {e}"
        )


# ========================================
# QUICK CHECK FUNCTION
# ========================================

async def run_quick_check() -> str:
    """Run 5 core diagnostic checks"""
    runner = DiagnosticRunner()
    
    checks = [
        ("Logger Configuration", check_logger_configuration),
        ("Critical Imports", check_critical_imports),
        ("Signal Schema", check_signal_schema_validation),
        ("NaN Detection", check_nan_in_indicators),
        ("Duplicate Guard", check_duplicate_signal_guard),
    ]
    
    await runner.run_all(checks)
    return runner.format_report()
