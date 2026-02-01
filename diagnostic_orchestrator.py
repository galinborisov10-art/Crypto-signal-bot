#!/usr/bin/env python3
"""
Diagnostic Orchestrator - Foundation Infrastructure
====================================================

This module provides the core orchestration infrastructure for running
diagnostic tests safely and reliably.

**IMPORTANT**: This is orchestration infrastructure ONLY. It does NOT:
- Execute signals
- Send Telegram messages
- Make trades
- Write to database or files
- Modify bot logic

This module provides:
- DiagnosticResult dataclass for structured test results
- DiagnosticRunner class for orchestrating diagnostic checks
- Timeout handling (per-test and global)
- Exception isolation
- DIAGNOSTIC_MODE management with guaranteed reset

Author: Crypto Signal Bot Team
Created: 2026-02-01
"""

import asyncio
import logging
import signal
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, List, Tuple, Dict, Any, Optional

# Configure logging
logger = logging.getLogger(__name__)

# Global diagnostic mode flag
# This flag is used to prevent actual signal execution, Telegram sends, trades, etc.
# during diagnostic runs. All bot code should check this flag before performing
# actions that modify state or interact with external systems.
DIAGNOSTIC_MODE = False


@dataclass
class DiagnosticResult:
    """
    Structured result from a single diagnostic test.
    
    Attributes:
        test_name: Human-readable name of the diagnostic test
        status: Test result status - one of "PASS", "WARN", "FAIL"
        severity: Severity level - one of "LOW", "MED", "HIGH"
        message: Human-readable message describing the result
        details: Additional diagnostic details as a dictionary
        execution_time: Time taken to execute test in seconds
        timestamp: When the test was executed
    """
    test_name: str
    status: str  # "PASS" | "WARN" | "FAIL"
    severity: str  # "LOW" | "MED" | "HIGH"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        """Validate status and severity values"""
        valid_statuses = {"PASS", "WARN", "FAIL"}
        valid_severities = {"LOW", "MED", "HIGH"}
        
        if self.status not in valid_statuses:
            raise ValueError(f"Invalid status '{self.status}'. Must be one of {valid_statuses}")
        
        if self.severity not in valid_severities:
            raise ValueError(f"Invalid severity '{self.severity}'. Must be one of {valid_severities}")


class TimeoutError(Exception):
    """Custom timeout exception for diagnostic tests"""
    pass


class DiagnosticRunner:
    """
    Orchestrator for running diagnostic tests safely and reliably.
    
    This class manages:
    - Sequential execution of diagnostic checks
    - Per-test timeout enforcement
    - Global runtime cap enforcement
    - Exception isolation (one test failure doesn't crash the runner)
    - DIAGNOSTIC_MODE state management with guaranteed reset
    - Structured result collection and aggregation
    
    Usage:
        runner = DiagnosticRunner()
        checks = [
            ("test_name_1", test_function_1),
            ("test_name_2", test_function_2),
        ]
        results = runner.run_all(checks)
    """
    
    # Default timeouts
    DEFAULT_PER_TEST_TIMEOUT = 30  # seconds
    DEFAULT_GLOBAL_TIMEOUT = 600  # 10 minutes
    
    def __init__(
        self,
        per_test_timeout: int = DEFAULT_PER_TEST_TIMEOUT,
        global_timeout: int = DEFAULT_GLOBAL_TIMEOUT
    ):
        """
        Initialize the DiagnosticRunner.
        
        Args:
            per_test_timeout: Maximum time (in seconds) allowed for each test (default: 30)
            global_timeout: Maximum total time (in seconds) for all tests (default: 600)
        """
        self.per_test_timeout = per_test_timeout
        self.global_timeout = global_timeout
        self.results: List[DiagnosticResult] = []
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
    
    def _run_with_timeout(self, func: Callable, timeout: int) -> DiagnosticResult:
        """
        Run a function with a timeout using threading.
        
        This is a synchronous implementation that works with both sync and async functions.
        Uses threading.Timer for timeout enforcement.
        
        Args:
            func: The function to run (should return DiagnosticResult)
            timeout: Maximum time in seconds
            
        Returns:
            DiagnosticResult from the function or timeout/error result
        """
        result_container = []
        exception_container = []
        
        def target():
            try:
                result = func()
                result_container.append(result)
            except Exception as e:
                exception_container.append(e)
        
        thread = threading.Thread(target=target, daemon=True)
        thread.start()
        thread.join(timeout=timeout)
        
        if thread.is_alive():
            # Thread is still running - timeout occurred
            logger.error(f"Test timed out after {timeout} seconds")
            return None  # Signal timeout
        
        if exception_container:
            raise exception_container[0]
        
        if result_container:
            return result_container[0]
        
        return None
    
    def _run_single_check(
        self,
        test_name: str,
        test_func: Callable[[], DiagnosticResult],
        timeout: Optional[int] = None
    ) -> DiagnosticResult:
        """
        Run a single diagnostic check with timeout and exception isolation.
        
        This method ensures that:
        - The test runs within the specified timeout
        - Any exceptions are caught and converted to FAIL results
        - Execution time is tracked
        
        Args:
            test_name: Name of the test (for logging and results)
            test_func: Callable that returns a DiagnosticResult
            timeout: Override default timeout (optional)
            
        Returns:
            DiagnosticResult (always returns a result, even on failure)
        """
        effective_timeout = timeout if timeout is not None else self.per_test_timeout
        start_time = time.time()
        
        logger.info(f"🔍 Running diagnostic: {test_name} (timeout: {effective_timeout}s)")
        
        try:
            # Run the test with timeout
            result = self._run_with_timeout(test_func, effective_timeout)
            
            if result is None:
                # Timeout occurred
                execution_time = time.time() - start_time
                logger.error(f"❌ {test_name} - TIMEOUT after {effective_timeout}s")
                return DiagnosticResult(
                    test_name=test_name,
                    status="FAIL",
                    severity="HIGH",
                    message=f"Test timeout after {effective_timeout} seconds",
                    details={"timeout_seconds": effective_timeout},
                    execution_time=execution_time
                )
            
            # Success - calculate execution time and update result
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            logger.info(f"✅ {test_name} - {result.status} ({execution_time:.2f}s)")
            return result
            
        except Exception as e:
            # Exception occurred - create FAIL result
            execution_time = time.time() - start_time
            logger.error(f"❌ {test_name} - EXCEPTION: {type(e).__name__}: {e}")
            return DiagnosticResult(
                test_name=test_name,
                status="FAIL",
                severity="HIGH",
                message=f"Test raised exception: {type(e).__name__}: {str(e)}",
                details={"exception_type": type(e).__name__, "exception_message": str(e)},
                execution_time=execution_time
            )
    
    def run_all(self, checks: List[Tuple[str, Callable]]) -> List[DiagnosticResult]:
        """
        Run all diagnostic checks sequentially with global timeout.
        
        This is the main entry point for running diagnostics. It:
        - Enables DIAGNOSTIC_MODE at the start
        - Runs each check sequentially with timeout and exception isolation
        - Enforces a global runtime cap
        - GUARANTEES DIAGNOSTIC_MODE is reset even if something crashes
        
        Args:
            checks: List of (test_name, test_function) tuples
            
        Returns:
            List of DiagnosticResult objects, one per test
            
        Example:
            runner = DiagnosticRunner()
            results = runner.run_all([
                ("test_1", my_test_function_1),
                ("test_2", my_test_function_2),
            ])
        """
        global DIAGNOSTIC_MODE
        
        # Clear previous results
        self.results = []
        self.start_time = time.time()
        
        logger.info("=" * 80)
        logger.info("🚀 Starting Diagnostic Runner")
        logger.info(f"   Tests to run: {len(checks)}")
        logger.info(f"   Per-test timeout: {self.per_test_timeout}s")
        logger.info(f"   Global timeout: {self.global_timeout}s")
        logger.info("=" * 80)
        
        try:
            # ENABLE DIAGNOSTIC_MODE
            DIAGNOSTIC_MODE = True
            logger.info("🔒 DIAGNOSTIC_MODE ENABLED")
            
            # Run each check sequentially
            for idx, (test_name, test_func) in enumerate(checks, 1):
                # Check global timeout BEFORE running test
                elapsed = time.time() - self.start_time
                if elapsed >= self.global_timeout:
                    logger.warning(
                        f"⚠️  Global timeout ({self.global_timeout}s) reached. "
                        f"Stopping after {idx - 1}/{len(checks)} tests."
                    )
                    break
                
                # Calculate remaining time for this test
                remaining_global = self.global_timeout - elapsed
                test_timeout = min(self.per_test_timeout, remaining_global)
                
                # Skip test if no time remaining (need at least 1 second)
                if test_timeout < 1:
                    logger.warning(
                        f"⚠️  Insufficient time remaining for {test_name} ({test_timeout:.2f}s). "
                        f"Stopping after {idx - 1}/{len(checks)} tests."
                    )
                    break
                
                # Run the check
                logger.info(f"\n[{idx}/{len(checks)}] {test_name}")
                result = self._run_single_check(test_name, test_func, timeout=int(test_timeout))
                self.results.append(result)
            
            self.end_time = time.time()
            total_time = self.end_time - self.start_time
            
            logger.info("\n" + "=" * 80)
            logger.info("✅ Diagnostic Runner Complete")
            logger.info(f"   Total time: {total_time:.2f}s")
            logger.info(f"   Tests run: {len(self.results)}/{len(checks)}")
            logger.info("=" * 80)
            
            return self.results
            
        except Exception as e:
            # Something went catastrophically wrong
            logger.error(f"💥 Diagnostic runner crashed: {type(e).__name__}: {e}")
            self.end_time = time.time()
            return self.results
            
        finally:
            # GUARANTEE DIAGNOSTIC_MODE IS RESET
            # This runs even if there's an exception or early return
            DIAGNOSTIC_MODE = False
            logger.info("🔓 DIAGNOSTIC_MODE DISABLED (guaranteed reset)")
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the diagnostic run results.
        
        Returns:
            Dictionary containing:
            - total_tests: Total number of tests run
            - passed: Number of PASS results
            - warned: Number of WARN results
            - failed: Number of FAIL results
            - severity_high: Number of HIGH severity results
            - severity_med: Number of MED severity results
            - severity_low: Number of LOW severity results
            - total_execution_time: Total time in seconds
            - tests_by_status: Dictionary mapping status to list of test names
        """
        if not self.results:
            return {
                "total_tests": 0,
                "passed": 0,
                "warned": 0,
                "failed": 0,
                "severity_high": 0,
                "severity_med": 0,
                "severity_low": 0,
                "total_execution_time": 0.0,
                "tests_by_status": {"PASS": [], "WARN": [], "FAIL": []},
            }
        
        # Count by status
        passed = sum(1 for r in self.results if r.status == "PASS")
        warned = sum(1 for r in self.results if r.status == "WARN")
        failed = sum(1 for r in self.results if r.status == "FAIL")
        
        # Count by severity
        severity_high = sum(1 for r in self.results if r.severity == "HIGH")
        severity_med = sum(1 for r in self.results if r.severity == "MED")
        severity_low = sum(1 for r in self.results if r.severity == "LOW")
        
        # Total execution time
        total_time = sum(r.execution_time for r in self.results)
        
        # Group tests by status
        tests_by_status = {
            "PASS": [r.test_name for r in self.results if r.status == "PASS"],
            "WARN": [r.test_name for r in self.results if r.status == "WARN"],
            "FAIL": [r.test_name for r in self.results if r.status == "FAIL"],
        }
        
        return {
            "total_tests": len(self.results),
            "passed": passed,
            "warned": warned,
            "failed": failed,
            "severity_high": severity_high,
            "severity_med": severity_med,
            "severity_low": severity_low,
            "total_execution_time": total_time,
            "tests_by_status": tests_by_status,
        }


# Convenience function for running diagnostics
def run_diagnostics(checks: List[Tuple[str, Callable]], **kwargs) -> List[DiagnosticResult]:
    """
    Convenience function to run diagnostics without creating a runner instance.
    
    Args:
        checks: List of (test_name, test_function) tuples
        **kwargs: Optional arguments passed to DiagnosticRunner constructor
        
    Returns:
        List of DiagnosticResult objects
        
    Example:
        results = run_diagnostics([
            ("my_test", my_test_func),
        ])
    """
    runner = DiagnosticRunner(**kwargs)
    return runner.run_all(checks)
