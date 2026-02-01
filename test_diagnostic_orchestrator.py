#!/usr/bin/env python3
"""
Test suite for Diagnostic Orchestrator Infrastructure

This test file validates the orchestration infrastructure ONLY.
It does NOT test actual bot diagnostics - only the framework.

Tests cover:
- Timeout handling (per-test and global)
- Exception isolation
- DIAGNOSTIC_MODE reset guarantee
- Result collection and aggregation
- Status and severity validation
"""

import time
import unittest
from datetime import datetime

# Import the module to test
from diagnostic_orchestrator import (
    DiagnosticResult,
    DiagnosticRunner,
    run_diagnostics,
    DIAGNOSTIC_MODE
)


class TestDiagnosticResult(unittest.TestCase):
    """Test the DiagnosticResult dataclass"""
    
    def test_valid_result_creation(self):
        """Test creating a valid DiagnosticResult"""
        result = DiagnosticResult(
            test_name="test_example",
            status="PASS",
            severity="LOW",
            message="Test passed successfully",
            details={"key": "value"},
            execution_time=1.5
        )
        
        self.assertEqual(result.test_name, "test_example")
        self.assertEqual(result.status, "PASS")
        self.assertEqual(result.severity, "LOW")
        self.assertEqual(result.message, "Test passed successfully")
        self.assertEqual(result.details, {"key": "value"})
        self.assertEqual(result.execution_time, 1.5)
        self.assertIsInstance(result.timestamp, datetime)
    
    def test_invalid_status(self):
        """Test that invalid status raises ValueError"""
        with self.assertRaises(ValueError) as context:
            DiagnosticResult(
                test_name="test",
                status="INVALID",
                severity="LOW",
                message="Test"
            )
        self.assertIn("Invalid status", str(context.exception))
    
    def test_invalid_severity(self):
        """Test that invalid severity raises ValueError"""
        with self.assertRaises(ValueError) as context:
            DiagnosticResult(
                test_name="test",
                status="PASS",
                severity="INVALID",
                message="Test"
            )
        self.assertIn("Invalid severity", str(context.exception))
    
    def test_default_values(self):
        """Test that default values are set correctly"""
        result = DiagnosticResult(
            test_name="test",
            status="PASS",
            severity="LOW",
            message="Test"
        )
        
        self.assertEqual(result.details, {})
        self.assertEqual(result.execution_time, 0.0)
        self.assertIsInstance(result.timestamp, datetime)


class TestDiagnosticRunner(unittest.TestCase):
    """Test the DiagnosticRunner class"""
    
    def test_successful_test(self):
        """Test running a successful diagnostic test"""
        def passing_test():
            return DiagnosticResult(
                test_name="passing_test",
                status="PASS",
                severity="LOW",
                message="Test passed"
            )
        
        runner = DiagnosticRunner()
        results = runner.run_all([("passing_test", passing_test)])
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "PASS")
        self.assertEqual(results[0].test_name, "passing_test")
        self.assertGreater(results[0].execution_time, 0)
    
    def test_timeout_handling(self):
        """Test that timeouts are handled correctly"""
        def slow_test():
            time.sleep(5)  # Sleep longer than timeout
            return DiagnosticResult(
                test_name="slow_test",
                status="PASS",
                severity="LOW",
                message="Should not reach here"
            )
        
        runner = DiagnosticRunner(per_test_timeout=1)  # 1 second timeout
        results = runner.run_all([("slow_test", slow_test)])
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "FAIL")
        self.assertEqual(results[0].severity, "HIGH")
        self.assertIn("timeout", results[0].message.lower())
    
    def test_exception_isolation(self):
        """Test that exceptions in one test don't crash the runner"""
        def failing_test():
            raise ValueError("Intentional test failure")
        
        def passing_test():
            return DiagnosticResult(
                test_name="passing_test",
                status="PASS",
                severity="LOW",
                message="Test passed"
            )
        
        runner = DiagnosticRunner()
        results = runner.run_all([
            ("failing_test", failing_test),
            ("passing_test", passing_test)
        ])
        
        self.assertEqual(len(results), 2)
        
        # First test should fail with exception
        self.assertEqual(results[0].status, "FAIL")
        self.assertEqual(results[0].severity, "HIGH")
        self.assertIn("ValueError", results[0].message)
        
        # Second test should still run and pass
        self.assertEqual(results[1].status, "PASS")
    
    def test_diagnostic_mode_reset(self):
        """Test that DIAGNOSTIC_MODE is always reset after run"""
        import diagnostic_orchestrator
        
        # Ensure DIAGNOSTIC_MODE starts as False
        diagnostic_orchestrator.DIAGNOSTIC_MODE = False
        
        def simple_test():
            # Check that DIAGNOSTIC_MODE is True during execution
            self.assertTrue(diagnostic_orchestrator.DIAGNOSTIC_MODE)
            return DiagnosticResult(
                test_name="mode_test",
                status="PASS",
                severity="LOW",
                message="Test"
            )
        
        runner = DiagnosticRunner()
        runner.run_all([("mode_test", simple_test)])
        
        # DIAGNOSTIC_MODE should be False after run
        self.assertFalse(diagnostic_orchestrator.DIAGNOSTIC_MODE)
    
    def test_diagnostic_mode_reset_on_exception(self):
        """Test that DIAGNOSTIC_MODE is reset even when tests raise exceptions"""
        import diagnostic_orchestrator
        
        diagnostic_orchestrator.DIAGNOSTIC_MODE = False
        
        def crashing_test():
            raise RuntimeError("Crash!")
        
        runner = DiagnosticRunner()
        runner.run_all([("crash_test", crashing_test)])
        
        # DIAGNOSTIC_MODE should still be False after crash
        self.assertFalse(diagnostic_orchestrator.DIAGNOSTIC_MODE)
    
    def test_global_timeout(self):
        """Test that global timeout stops execution"""
        def slow_test():
            time.sleep(1.5)  # Each test takes 1.5 seconds
            return DiagnosticResult(
                test_name="slow_test",
                status="PASS",
                severity="LOW",
                message="Test"
            )
        
        # Run 10 tests with 3-second global timeout
        # Should only complete ~2 tests (1.5s each = 3s for 2 tests)
        runner = DiagnosticRunner(per_test_timeout=10, global_timeout=3)
        results = runner.run_all([
            ("test_1", slow_test),
            ("test_2", slow_test),
            ("test_3", slow_test),
            ("test_4", slow_test),
            ("test_5", slow_test),
            ("test_6", slow_test),
            ("test_7", slow_test),
            ("test_8", slow_test),
            ("test_9", slow_test),
            ("test_10", slow_test),
        ])
        
        # Should have stopped early due to global timeout
        # With 1.5s per test, we expect 2 tests in 3 seconds
        self.assertLess(len(results), 10, "Global timeout should stop execution early")
        self.assertLessEqual(len(results), 3, "Should complete at most 3 tests in 3 seconds")
        self.assertGreater(len(results), 0, "At least one test should run")
    
    def test_result_collection(self):
        """Test that results are collected correctly"""
        def make_test(name, status, severity):
            def test():
                return DiagnosticResult(
                    test_name=name,
                    status=status,
                    severity=severity,
                    message=f"{name} message"
                )
            return test
        
        runner = DiagnosticRunner()
        results = runner.run_all([
            ("pass_low", make_test("pass_low", "PASS", "LOW")),
            ("warn_med", make_test("warn_med", "WARN", "MED")),
            ("fail_high", make_test("fail_high", "FAIL", "HIGH")),
        ])
        
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].status, "PASS")
        self.assertEqual(results[1].status, "WARN")
        self.assertEqual(results[2].status, "FAIL")
    
    def test_get_summary(self):
        """Test the get_summary method"""
        def make_test(name, status, severity):
            def test():
                return DiagnosticResult(
                    test_name=name,
                    status=status,
                    severity=severity,
                    message="Test"
                )
            return test
        
        runner = DiagnosticRunner()
        runner.run_all([
            ("pass_1", make_test("pass_1", "PASS", "LOW")),
            ("pass_2", make_test("pass_2", "PASS", "MED")),
            ("warn_1", make_test("warn_1", "WARN", "MED")),
            ("fail_1", make_test("fail_1", "FAIL", "HIGH")),
        ])
        
        summary = runner.get_summary()
        
        self.assertEqual(summary["total_tests"], 4)
        self.assertEqual(summary["passed"], 2)
        self.assertEqual(summary["warned"], 1)
        self.assertEqual(summary["failed"], 1)
        self.assertEqual(summary["severity_high"], 1)
        self.assertEqual(summary["severity_med"], 2)
        self.assertEqual(summary["severity_low"], 1)
        self.assertGreater(summary["total_execution_time"], 0)
        
        # Check tests_by_status
        self.assertEqual(len(summary["tests_by_status"]["PASS"]), 2)
        self.assertEqual(len(summary["tests_by_status"]["WARN"]), 1)
        self.assertEqual(len(summary["tests_by_status"]["FAIL"]), 1)
    
    def test_empty_checks(self):
        """Test running with no checks"""
        runner = DiagnosticRunner()
        results = runner.run_all([])
        
        self.assertEqual(len(results), 0)
        summary = runner.get_summary()
        self.assertEqual(summary["total_tests"], 0)


class TestConvenienceFunction(unittest.TestCase):
    """Test the convenience function"""
    
    def test_run_diagnostics(self):
        """Test the run_diagnostics convenience function"""
        def simple_test():
            return DiagnosticResult(
                test_name="simple",
                status="PASS",
                severity="LOW",
                message="Test"
            )
        
        results = run_diagnostics([("simple_test", simple_test)])
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "PASS")
    
    def test_run_diagnostics_with_kwargs(self):
        """Test run_diagnostics with custom timeout"""
        def slow_test():
            time.sleep(2)
            return DiagnosticResult(
                test_name="slow",
                status="PASS",
                severity="LOW",
                message="Test"
            )
        
        # Should timeout with 1 second per-test timeout
        results = run_diagnostics(
            [("slow_test", slow_test)],
            per_test_timeout=1
        )
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, "FAIL")
        self.assertIn("timeout", results[0].message.lower())


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def test_test_returning_none(self):
        """Test handling of test that returns None instead of DiagnosticResult"""
        def bad_test():
            return None
        
        runner = DiagnosticRunner()
        results = runner.run_all([("bad_test", bad_test)])
        
        # Should handle gracefully
        self.assertEqual(len(results), 1)
        # The implementation treats None return as timeout
        self.assertEqual(results[0].status, "FAIL")
    
    def test_test_returning_wrong_type(self):
        """Test handling of test that returns wrong type"""
        def bad_test():
            return "not a DiagnosticResult"
        
        runner = DiagnosticRunner()
        # This should be handled by exception isolation
        results = runner.run_all([("bad_test", bad_test)])
        
        self.assertEqual(len(results), 1)


def run_tests():
    """Run all tests and print results"""
    print("=" * 80)
    print("🧪 Running Diagnostic Orchestrator Infrastructure Tests")
    print("=" * 80)
    print()
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestDiagnosticResult))
    suite.addTests(loader.loadTestsFromTestCase(TestDiagnosticRunner))
    suite.addTests(loader.loadTestsFromTestCase(TestConvenienceFunction))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print()
    print("=" * 80)
    print("📊 Test Summary")
    print("=" * 80)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 80)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    import sys
    success = run_tests()
    sys.exit(0 if success else 1)
