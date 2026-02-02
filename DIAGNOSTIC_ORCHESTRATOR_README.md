# Diagnostic Orchestrator - Foundation Infrastructure

## ⚠️ PRODUCTION SAFETY NOTICE

**This module is DIAGNOSTIC INFRASTRUCTURE ONLY.**

- ✅ **Intended use:** Manual or admin-triggered diagnostic test execution
- ✅ **Intended use:** Diagnostic test development and validation
- ❌ **NOT for use:** Production runtime code paths (bot.py, signal handlers, trading)
- ❌ **NOT for use:** Scheduled tasks, Telegram handlers, or startup logic

**The `DIAGNOSTIC_MODE` flag in this module is separate from and must not be confused with the production `DIAGNOSTIC_MODE` environment variable used in `bot.py`.**

This module is intentionally NOT wired into bot startup or runtime logic. It provides orchestration infrastructure that should only be explicitly invoked when running diagnostics.

---

## Overview

The Diagnostic Orchestrator is a **foundation infrastructure module** for running diagnostic tests safely and reliably. This is orchestration infrastructure ONLY - it does not include any actual diagnostic tests.

## What It Does

✅ **Provides:**
- `DiagnosticResult` dataclass for structured test results
- `DiagnosticRunner` class for orchestrating diagnostic checks
- Per-test timeout handling (default: 30 seconds)
- Global runtime cap enforcement (default: 10 minutes)
- Exception isolation (one test failure doesn't crash the runner)
- `DIAGNOSTIC_MODE` management with guaranteed reset
- Result collection and aggregation

❌ **Does NOT:**
- Execute signals
- Send Telegram messages
- Make trades
- Write to database or files
- Modify bot logic
- Include any diagnostic tests (foundation only)

## Architecture

### DiagnosticResult Dataclass

Structured result from a single diagnostic test:

```python
@dataclass
class DiagnosticResult:
    test_name: str          # Human-readable test name
    status: str            # "PASS" | "WARN" | "FAIL"
    severity: str          # "LOW" | "MED" | "HIGH"
    message: str           # Human-readable message
    details: Dict[str, Any] # Additional diagnostic details
    execution_time: float  # Time taken in seconds
    timestamp: datetime    # When the test was executed
```

**Status Values:**
- `"PASS"` - Test passed successfully
- `"WARN"` - Test completed with warnings
- `"FAIL"` - Test failed

**Severity Levels:**
- `"LOW"` - Minor issue or informational
- `"MED"` - Moderate issue that should be addressed
- `"HIGH"` - Critical issue requiring immediate attention

### DiagnosticRunner Class

Orchestrates the execution of diagnostic tests:

```python
class DiagnosticRunner:
    DEFAULT_PER_TEST_TIMEOUT = 30   # seconds
    DEFAULT_GLOBAL_TIMEOUT = 600    # 10 minutes
    
    def __init__(
        self,
        per_test_timeout: int = DEFAULT_PER_TEST_TIMEOUT,
        global_timeout: int = DEFAULT_GLOBAL_TIMEOUT
    )
    
    def run_all(
        self,
        checks: List[Tuple[str, Callable]]
    ) -> List[DiagnosticResult]
    
    def get_summary(self) -> Dict[str, Any]
```

## Usage

### Basic Example

```python
from diagnostic_orchestrator import DiagnosticRunner, DiagnosticResult

def my_diagnostic_test():
    """Example diagnostic test"""
    # Perform your diagnostic checks here
    return DiagnosticResult(
        test_name="my_test",
        status="PASS",
        severity="LOW",
        message="Test completed successfully",
        details={"items_checked": 5}
    )

# Create runner
runner = DiagnosticRunner()

# Run checks
results = runner.run_all([
    ("My Test", my_diagnostic_test),
])

# Get summary
summary = runner.get_summary()
print(f"Passed: {summary['passed']}, Failed: {summary['failed']}")
```

### Custom Timeouts

```python
# Increase per-test timeout for slow operations
runner = DiagnosticRunner(
    per_test_timeout=60,   # 1 minute per test
    global_timeout=1800    # 30 minutes total
)
```

### Convenience Function

```python
from diagnostic_orchestrator import run_diagnostics

# Quick one-liner
results = run_diagnostics([
    ("test_1", test_function_1),
    ("test_2", test_function_2),
])
```

## Safety Features

### 1. Per-Test Timeout
Each test is limited to a maximum execution time (default 30 seconds). If a test exceeds this, it returns a FAIL result with timeout details.

### 2. Global Runtime Cap
The entire diagnostic run is capped at a maximum time (default 10 minutes). If this limit is reached, the runner stops executing remaining tests.

### 3. Exception Isolation
Each test runs in isolation. If a test raises an exception, it's caught and converted to a FAIL result. Other tests continue to run.

### 4. DIAGNOSTIC_MODE Management

⚠️ **IMPORTANT PRODUCTION SAFETY NOTICE**

The `DIAGNOSTIC_MODE` flag in this module is for **diagnostic infrastructure only**:

- ✅ **USE:** In diagnostic test functions called via `DiagnosticRunner`
- ✅ **USE:** In admin-triggered diagnostic commands
- ✅ **USE:** In manual diagnostic execution contexts

- ❌ **DO NOT USE:** In production runtime code paths (bot.py, signal handlers, trading logic)
- ❌ **DO NOT USE:** In scheduled tasks or Telegram command handlers
- ❌ **DO NOT USE:** In startup or initialization code

**For production runtime diagnostic mode, use `bot.py`'s `DIAGNOSTIC_MODE` which is controlled via environment variable.**

This module is intentionally NOT wired into bot startup or runtime logic. It provides orchestration infrastructure that is explicitly invoked only when running diagnostics.

The runner automatically:
- Enables `DIAGNOSTIC_MODE = True` at the start of a diagnostic run
- Disables `DIAGNOSTIC_MODE = False` at the end
- **Guarantees** reset even if something crashes (via try/finally)

Diagnostic test code can check this flag:
```python
from diagnostic_orchestrator import DIAGNOSTIC_MODE

def diagnostic_test_function():
    # This is OK - we're in a diagnostic test context
    if DIAGNOSTIC_MODE:
        logger.info("Running in diagnostic mode")
    # Test logic here
```

**Production code should NEVER import or check this flag:**
```python
# ❌ WRONG - Do not do this in bot.py or production handlers
from diagnostic_orchestrator import DIAGNOSTIC_MODE  # NO!

# ✅ CORRECT - Use bot.py's environment-based flag
DIAGNOSTIC_MODE = os.getenv('DIAGNOSTIC_MODE', 'false').lower() == 'true'
```

## Result Aggregation

The `get_summary()` method provides aggregate statistics:

```python
{
    "total_tests": 10,
    "passed": 7,
    "warned": 2,
    "failed": 1,
    "severity_high": 1,
    "severity_med": 3,
    "severity_low": 6,
    "total_execution_time": 45.2,
    "tests_by_status": {
        "PASS": ["test1", "test2", ...],
        "WARN": ["test3", ...],
        "FAIL": ["test4"]
    }
}
```

## Testing

The module includes comprehensive tests in `test_diagnostic_orchestrator.py`:

```bash
# Run all tests
python3 test_diagnostic_orchestrator.py

# Expected output:
# Tests run: 17
# Successes: 17
# Failures: 0
```

**Test Coverage:**
- ✅ DiagnosticResult validation
- ✅ Timeout handling (per-test and global)
- ✅ Exception isolation
- ✅ DIAGNOSTIC_MODE reset guarantee
- ✅ Result collection and aggregation
- ✅ Edge cases

## Example Output

See `example_diagnostic_usage.py` for a complete working example.

```bash
python3 example_diagnostic_usage.py
```

## Implementation Notes

### Thread-Based Timeout
Uses `threading.Thread` with `join(timeout)` for timeout enforcement. This works reliably for both sync and async functions.

### Sequential Execution
Tests run one at a time in the order specified. This is intentional for:
- Predictable behavior
- Easier debugging
- Resource management
- Clearer logging

### No Parallelization
This is a deliberate design choice. Diagnostic tests may interact with shared resources, and sequential execution ensures:
- No race conditions
- Deterministic results
- Simpler error handling

## Files

- `diagnostic_orchestrator.py` - Main implementation
- `test_diagnostic_orchestrator.py` - Comprehensive test suite
- `example_diagnostic_usage.py` - Usage example
- `DIAGNOSTIC_ORCHESTRATOR_README.md` - This file

## Next Steps

This is **foundation infrastructure only**. Future work may include:

1. **Diagnostic Tests** - Actual bot diagnostic implementations
2. **Integration** - Wire into existing diagnostic system
3. **Reporting** - Format results for Telegram/logging
4. **Persistence** - Save diagnostic history

But those are **separate PRs** - this PR provides only the orchestration foundation.

## Requirements Met

✅ DiagnosticResult dataclass created  
✅ DiagnosticRunner class with run_all method  
✅ Per-test timeout mechanism (30s default)  
✅ Global runtime cap (10 minutes)  
✅ Per-test exception isolation  
✅ DIAGNOSTIC_MODE enable/disable with guaranteed reset  
✅ Structured result collection  
✅ Zero changes to existing bot logic  
✅ Zero test implementations (foundation only)  
✅ Code is well-documented with docstrings  
✅ Comprehensive test suite included  

## License

Part of the Crypto Signal Bot project.
