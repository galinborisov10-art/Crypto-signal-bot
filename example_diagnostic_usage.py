#!/usr/bin/env python3
"""
Example usage of the Diagnostic Orchestrator

This demonstrates how to use the DiagnosticRunner and DiagnosticResult
to create and run diagnostic tests.
"""

import time
from diagnostic_orchestrator import DiagnosticRunner, DiagnosticResult


def example_passing_test():
    """Example of a passing diagnostic test"""
    return DiagnosticResult(
        test_name="example_passing_test",
        status="PASS",
        severity="LOW",
        message="Everything looks good!",
        details={"checked_items": 3, "issues_found": 0}
    )


def example_warning_test():
    """Example of a test with warnings"""
    return DiagnosticResult(
        test_name="example_warning_test",
        status="WARN",
        severity="MED",
        message="Found minor issues that should be addressed",
        details={"warnings": ["Config file is old", "Cache is large"]}
    )


def example_failing_test():
    """Example of a failing diagnostic test"""
    return DiagnosticResult(
        test_name="example_failing_test",
        status="FAIL",
        severity="HIGH",
        message="Critical issue detected!",
        details={"error": "Database connection failed"}
    )


def example_slow_test():
    """Example of a test that takes some time"""
    time.sleep(2)  # Simulate work
    return DiagnosticResult(
        test_name="example_slow_test",
        status="PASS",
        severity="LOW",
        message="Slow operation completed successfully"
    )


def main():
    print("=" * 80)
    print("Diagnostic Orchestrator Example")
    print("=" * 80)
    print()
    
    # Create the runner
    runner = DiagnosticRunner(
        per_test_timeout=30,  # 30 seconds per test
        global_timeout=600    # 10 minutes total
    )
    
    # Define the checks to run
    checks = [
        ("Passing Test", example_passing_test),
        ("Warning Test", example_warning_test),
        ("Failing Test", example_failing_test),
        ("Slow Test", example_slow_test),
    ]
    
    # Run all checks
    print("Running diagnostic checks...\n")
    results = runner.run_all(checks)
    
    # Display results
    print("\n" + "=" * 80)
    print("Results Summary")
    print("=" * 80)
    
    for result in results:
        status_icon = {
            "PASS": "✅",
            "WARN": "⚠️",
            "FAIL": "❌"
        }.get(result.status, "❓")
        
        print(f"\n{status_icon} {result.test_name}")
        print(f"   Status: {result.status} (Severity: {result.severity})")
        print(f"   Message: {result.message}")
        print(f"   Time: {result.execution_time:.2f}s")
        if result.details:
            print(f"   Details: {result.details}")
    
    # Get summary statistics
    summary = runner.get_summary()
    
    print("\n" + "=" * 80)
    print("Overall Statistics")
    print("=" * 80)
    print(f"Total tests: {summary['total_tests']}")
    print(f"Passed: {summary['passed']}")
    print(f"Warnings: {summary['warned']}")
    print(f"Failed: {summary['failed']}")
    print(f"Total execution time: {summary['total_execution_time']:.2f}s")
    print()
    print(f"High severity: {summary['severity_high']}")
    print(f"Medium severity: {summary['severity_med']}")
    print(f"Low severity: {summary['severity_low']}")
    print("=" * 80)


if __name__ == "__main__":
    main()
