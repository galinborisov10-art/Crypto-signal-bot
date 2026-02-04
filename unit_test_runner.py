"""
Unit Test Runner for Diagnostic System
Automatically discovers and runs unit tests for bot functions
"""

import unittest
import sys
import os
from io import StringIO
from typing import Dict, List, Tuple

class UnitTestRunner:
    """Discover and run unit tests"""
    
    def __init__(self, test_dir: str = "tests"):
        self.test_dir = test_dir
        self.base_path = os.path.dirname(os.path.abspath(__file__))
        
    def discover_tests(self) -> unittest.TestSuite:
        """Discover all test files"""
        
        test_path = os.path.join(self.base_path, self.test_dir)
        
        # Create tests directory if it doesn't exist
        if not os.path.exists(test_path):
            os.makedirs(test_path)
            
            # Create __init__.py
            init_file = os.path.join(test_path, '__init__.py')
            if not os.path.exists(init_file):
                open(init_file, 'w').close()
        
        # Discover tests
        loader = unittest.TestLoader()
        
        try:
            suite = loader.discover(test_path, pattern='test_*.py')
            return suite
        except:
            # No tests found, return empty suite
            return unittest.TestSuite()
    
    def run_tests(self) -> Dict:
        """Run all discovered tests and return results"""
        
        suite = self.discover_tests()
        
        # Capture output
        output = StringIO()
        runner = unittest.TextTestRunner(stream=output, verbosity=2)
        
        result = runner.run(suite)
        
        return {
            'total': result.testsRun,
            'passed': result.testsRun - len(result.failures) - len(result.errors),
            'failed': len(result.failures),
            'errors': len(result.errors),
            'skipped': len(result.skipped),
            'success_rate': ((result.testsRun - len(result.failures) - len(result.errors)) / result.testsRun * 100) if result.testsRun > 0 else 0,
            'failures': [self._format_failure(f) for f in result.failures],
            'errors': [self._format_error(e) for e in result.errors],
            'output': output.getvalue()
        }
    
    def _format_failure(self, failure: Tuple) -> Dict:
        """Format test failure"""
        test, traceback = failure
        
        return {
            'test': str(test),
            'traceback': traceback,
            'module': test.__class__.__module__,
            'name': test._testMethodName
        }
    
    def _format_error(self, error: Tuple) -> Dict:
        """Format test error"""
        test, traceback = error
        
        return {
            'test': str(test),
            'traceback': traceback,
            'module': test.__class__.__module__,
            'name': test._testMethodName
        }
    
    def format_results(self, results: Dict) -> str:
        """Format test results as string"""
        
        if results['total'] == 0:
            return "ℹ️ No unit tests found\n\n📝 Create tests in 'tests/' directory\n  Example: tests/test_signals.py"
        
        output = "🧪 Unit Test Results\n"
        output += "━" * 45 + "\n\n"
        
        output += f"📊 Summary:\n"
        output += f"  Total: {results['total']}\n"
        output += f"  ✅ Passed: {results['passed']}\n"
        output += f"  ❌ Failed: {results['failed']}\n"
        output += f"  🔥 Errors: {results['errors']}\n"
        output += f"  ⏭️ Skipped: {results['skipped']}\n"
        output += f"  Success Rate: {results['success_rate']:.1f}%\n\n"
        
        # Show failures
        if results['failures']:
            output += f"❌ Failed Tests ({len(results['failures'])}):\n"
            for failure in results['failures']:
                output += f"  • {failure['name']} ({failure['module']})\n"
            output += "\n"
        
        # Show errors
        if results.get('errors') and isinstance(results['errors'], list):
            output += f"🔥 Test Errors ({len(results['errors'])}):\n"
            for error in results['errors']:
                output += f"  • {error['name']} ({error['module']})\n"
            output += "\n"
        
        return output
    
    def create_sample_test(self):
        """Create a sample test file"""
        
        test_path = os.path.join(self.base_path, self.test_dir)
        os.makedirs(test_path, exist_ok=True)
        
        sample_test = os.path.join(test_path, 'test_sample.py')
        
        if not os.path.exists(sample_test):
            with open(sample_test, 'w') as f:
                f.write('''"""
Sample Unit Tests
Replace this with actual tests for your bot functions
"""

import unittest

class TestSample(unittest.TestCase):
    """Sample test suite"""
    
    def test_example_pass(self):
        """Example passing test"""
        self.assertEqual(1 + 1, 2)
    
    def test_example_string(self):
        """Test string operations"""
        self.assertEqual("hello".upper(), "HELLO")
    
    # Uncomment to see a failing test
    # def test_example_fail(self):
    #     """Example failing test"""
    #     self.assertEqual(1 + 1, 3)

if __name__ == '__main__':
    unittest.main()
''')
            return True
        return False

