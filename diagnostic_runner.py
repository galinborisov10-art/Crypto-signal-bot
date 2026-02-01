"""
Diagnostic Runner Foundation
PR 1: Foundation Only - NO auto-fix, NO guardrails, NO replay
"""

import asyncio
import inspect
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Optional, Dict, Any

logger = logging.getLogger(__name__)

# Global diagnostic mode flag
DIAGNOSTIC_MODE = False

@dataclass
class DiagnosticResult:
    """Structured result from a single diagnostic check"""
    test_name: str
    status: str  # "PASS" / "WARN" / "FAIL"
    severity: str  # "LOW" / "MED" / "HIGH"
    execution_time_ms: float
    message: str
    details: str = ""
    exception_info: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)


class DiagnosticRunner:
    """
    Foundation runner for diagnostic checks
    
    Responsibilities:
    - Sequential execution
    - Per-test isolation
    - Timeout enforcement
    - Result aggregation
    - Guaranteed mode cleanup
    """
    
    DEFAULT_TIMEOUT = 30  # seconds per test
    MAX_TOTAL_RUNTIME = 600  # 10 minutes total
    
    def __init__(self, timeout_per_test: int = DEFAULT_TIMEOUT, max_total_runtime: int = MAX_TOTAL_RUNTIME):
        self.timeout_per_test = timeout_per_test
        self.max_total_runtime = max_total_runtime
        self.results: List[DiagnosticResult] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    async def run_single_check(
        self, 
        test_name: str, 
        check_func: Callable,
        timeout: Optional[int] = None
    ) -> DiagnosticResult:
        """
        Run a single diagnostic check with isolation and timeout
        
        Args:
            test_name: Human-readable test name
            check_func: Sync or async callable that returns DiagnosticResult
            timeout: Override default timeout (seconds)
        
        Returns:
            DiagnosticResult (always, even on exception)
        """
        timeout = timeout or self.timeout_per_test
        start = time.time()
        
        try:
            logger.info(f"🔍 Running: {test_name}")
            
            # Execute check (handle both sync and async)
            if inspect.iscoroutinefunction(check_func):
                result = await asyncio.wait_for(check_func(), timeout=timeout)
            else:
                result = await asyncio.wait_for(
                    asyncio.to_thread(check_func),
                    timeout=timeout
                )
            
            elapsed_ms = (time.time() - start) * 1000
            
            # Ensure result has execution time
            if hasattr(result, 'execution_time_ms'):
                result.execution_time_ms = elapsed_ms
            
            return result
            
        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start) * 1000
            logger.error(f"❌ {test_name} timed out after {timeout}s")
            return DiagnosticResult(
                test_name=test_name,
                status="FAIL",
                severity="HIGH",
                execution_time_ms=elapsed_ms,
                message=f"Timeout after {timeout}s",
                exception_info="TimeoutError"
            )
            
        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            logger.error(f"❌ {test_name} raised exception: {e}")
            return DiagnosticResult(
                test_name=test_name,
                status="FAIL",
                severity="HIGH",
                execution_time_ms=elapsed_ms,
                message=f"Exception: {str(e)}",
                exception_info=f"{type(e).__name__}: {e}"
            )
    
    async def run_all_checks(self, checks: List[tuple]) -> List[DiagnosticResult]:
        """
        Run all diagnostic checks sequentially with total runtime cap
        
        Args:
            checks: List of (test_name, check_func) tuples
        
        Returns:
            List of DiagnosticResult
        """
        global DIAGNOSTIC_MODE
        
        self.results = []
        self.start_time = time.time()
        
        try:
            # Enable diagnostic mode
            DIAGNOSTIC_MODE = True
            logger.info("🔒 DIAGNOSTIC_MODE enabled")
            
            for test_name, check_func in checks:
                # Check total runtime cap
                elapsed = time.time() - self.start_time
                if elapsed > self.max_total_runtime:
                    logger.warning(f"⚠️ Total runtime cap ({self.max_total_runtime}s) exceeded, stopping")
                    break
                
                # Run check
                result = await self.run_single_check(test_name, check_func)
                self.results.append(result)
            
            self.end_time = time.time()
            return self.results
            
        finally:
            # GUARANTEE mode cleanup
            DIAGNOSTIC_MODE = False
            logger.info("🔓 DIAGNOSTIC_MODE disabled")
    
    def aggregate_results(self) -> Dict[str, Any]:
        """
        Aggregate results by status and severity
        
        Returns:
            Dictionary with counts and statistics
        """
        total = len(self.results)
        
        # Count by status
        passed = sum(1 for r in self.results if r.status == "PASS")
        warned = sum(1 for r in self.results if r.status == "WARN")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        
        # Count by severity
        high = sum(1 for r in self.results if r.severity == "HIGH")
        med = sum(1 for r in self.results if r.severity == "MED")
        low = sum(1 for r in self.results if r.severity == "LOW")
        
        # Execution time
        total_time = (self.end_time - self.start_time) if self.end_time and self.start_time else 0
        
        return {
            "total_tests": total,
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "severity_high": high,
            "severity_med": med,
            "severity_low": low,
            "total_time_seconds": total_time,
        }
