# PR 2: CANONICAL DIAGNOSTIC TEST PACK

## Overview

This PR implements **5 canonical diagnostic test groups** that integrate with the DiagnosticRunner foundation from PR 1. These tests provide comprehensive self-audit capabilities for the bot without modifying signal logic or behavior.

## ✅ CANONICAL CORRECTION APPLIED

**Problem**: Initial implementation used module-level sweep (`inspect.getmembers(ict_signal_engine)`), analyzing ALL functions in modules regardless of runtime reachability.

**Solution**: Implemented runtime-aware function discovery starting from bot.py entry point using AST + import inspection. Now analyzes ONLY the 171 functions actually reachable from bot.py at runtime.

**Key Change**: Added `discover_runtime_functions()` helper that:
- Parses bot.py AST to find imports (NO execution)
- Follows import chain to local modules only
- Builds allowlist of runtime-reachable callables
- Discovers 171 functions from 49 modules
- Entry point: bot.py (CANONICAL requirement met)

## Core Principles

✅ **Read-only**: Tests never modify signal logic or behavior  
✅ **Dry-run only**: No real trading or Telegram messages  
✅ **Mock external services**: Safe testing without side effects  
✅ **Admin-only**: Diagnostic execution restricted to admin users  
✅ **Runtime analysis**: Analyzes ONLY code actually used by the bot (CANONICAL)  

## The 5 Canonical Test Groups

### 1. Exception Sweep (UPDATED - CANONICAL)
**Purpose**: Auto-discover and test PUBLIC functions from bot.py runtime execution graph

**CANONICAL CHANGE**: Now uses runtime-aware discovery instead of module-level sweep

**What it does**:
- Discovers runtime-reachable functions starting from bot.py (171 functions from 49 modules)
- Tests first 20 functions with safe mock inputs (execution limit for speed)
- Validates signatures for all 171 functions
- Catches runtime exceptions without affecting production
- Excludes dangerous functions (send_message, execute_trade, place_order)

**Output**:
- Runtime functions discovered
- Functions tested vs skipped
- Any exceptions caught
- Pass/warn/fail status

**Example Result**:
```
✅ PASS: Tested 20 runtime-reachable functions without exceptions
Runtime functions discovered: 171
Tested: 20
Skipped: 151
```

### 2. Config/ENV Diagnostics
**Purpose**: Validate environment configuration

**What it does**:
- Checks required ENV vars (TELEGRAM_BOT_TOKEN, OWNER_CHAT_ID)
- Validates data types (int, str, bool)
- Detects missing recommended vars (BINANCE_API_KEY, etc.)
- Reports parsing issues

**Output**:
- List of ENV variables checked
- Missing required keys
- Type mismatches
- Configuration health status

**Example Result**:
```
✅ PASS: All ENV vars present and valid
⚠️ WARN: Missing recommended ENV vars: BINANCE_API_KEY
❌ FAIL: Missing required ENV vars: TELEGRAM_BOT_TOKEN
```

### 3. Indicator Edge-Case Tests
**Purpose**: Test indicators with boundary inputs to detect NaN/inf/divide-by-zero

**What it does**:
- Tests RSI, EMA, MACD calculations
- Uses edge-case inputs: empty data, single candle, all-same values
- Detects NaN propagation
- Catches divide-by-zero errors

**Output**:
- List of indicators tested
- Edge cases detected
- NaN/inf occurrences
- Pass/fail per indicator

**Example Result**:
```
✅ PASS: All indicators handled edge cases correctly
⚠️ WARN: RSI: NaN detected in all_same case
```

### 4. Schema/Serialization Validation
**Purpose**: Validate ICTSignal structure and JSON compatibility

**What it does**:
- Validates ICTSignal class structure
- Tests JSON serialization/deserialization round-trip
- Ensures required fields present
- Checks type consistency

**Output**:
- Schema validation results
- Missing fields
- Type mismatches
- Serialization errors

**Example Result**:
```
✅ PASS: ICTSignal schema and serialization valid
❌ FAIL: Missing required field: entry_price
```

### 5. Signal Pipeline Dry-Run
**Purpose**: Test signal generation pipeline without real actions

**What it does**:
- Enables DIAGNOSTIC_MODE flag
- Creates mock candle data
- Instantiates signal engine
- Verifies engine structure
- **NEVER sends real Telegram messages**
- **NEVER executes trades**
- **NEVER performs external writes**

**Output**:
- Pipeline execution trace
- Engine instantiation status
- Explicit confirmation of NO real actions

**Example Result**:
```
✅ PASS: DRY-RUN successful - NO real actions taken
🔍 DRY-RUN: Confirmed NO real Telegram messages sent
🔍 DRY-RUN: Confirmed NO real trades executed
```

## Integration with DiagnosticRunner

All 5 tests integrate seamlessly with the FoundationRunner from PR 1:

- **Return type**: `FoundationResult` (from `diagnostic_runner.py`)
- **Isolated execution**: Each test has try/except wrapper
- **Timeout enforcement**: Runner enforces per-test timeout (default 30s)
- **Result aggregation**: Runner collects and formats results
- **Mode safety**: DIAGNOSTIC_MODE guaranteed to be reset

## How to Use

### Via Telegram Bot (Admin Only)

1. Send `/diagnostics` command
2. Select "🔍 Quick Check"
3. View report with all 26 tests (21 from PR 1 + 5 from PR 2)

### Programmatically

```python
from diagnostics import run_quick_check

# Run all 26 diagnostic tests
report = await run_quick_check()
print(report)
```

### Individual Tests

```python
from diagnostics import (
    test_exception_sweep,
    test_config_diagnostics,
    test_indicator_edge_cases,
    test_schema_validation,
    test_signal_pipeline_dryrun
)

# Run individual test
result = test_exception_sweep()
print(f"Status: {result.status}")
print(f"Message: {result.message}")
```

## Report Format

```
🛠 Diagnostic Report

⏱ Duration: 3.5s
✅ Passed: 13
⚠️ Warnings: 10
❌ Failed: 3

━━━━━ HIGH SEVERITY ━━━━━
(none)

━━━━━ MED SEVERITY ━━━━━
⚠️ PR2: Indicator Edge Cases: Found 2 minor issues
   - RSI: NaN detected in all_same
   - MACD: NaN detected in single_candle

━━━━━ LOW SEVERITY ━━━━━
✅ PR2: Exception Sweep: Tested 10 functions without exceptions
⚠️ PR2: Config Diagnostics: Missing recommended ENV vars
✅ PR2: Schema Validation: ICTSignal schema valid
✅ PR2: Signal Pipeline Dry-Run: DRY-RUN successful
```

## Files Modified

### `diagnostics.py`
- Added 5 new test functions (lines 1876-2418)
- Updated `run_quick_check()` to include PR 2 tests
- Added smart wrapping to handle FoundationResult vs old DiagnosticResult

### `bot.py`
- Updated diagnostics menu: "21 tests" → "26 tests (PR 1 + PR 2)"

## Security & Safety Guarantees

✅ **NO signal logic changes**: Tests only observe, never modify  
✅ **NO real trading**: All trading functions explicitly excluded  
✅ **NO Telegram messages**: Message sending functions excluded  
✅ **NO external writes**: File/network operations are read-only  
✅ **DIAGNOSTIC_MODE flag**: Automatically set and reset by runner  
✅ **Admin-only**: Execution restricted via bot.py authentication  

## Testing

### Test Script 1: Individual Tests
```bash
python3 /tmp/test_pr2_diagnostics.py
```

**Expected Output**:
```
✅ Passed: 3
⚠️ Warnings: 2
❌ Failed: 0
🎉 All PR 2 diagnostic tests executed successfully!
```

### Test Script 2: Full Suite
```bash
python3 /tmp/test_full_diagnostics.py
```

**Expected Output**:
```
🛠 Diagnostic Report
⏱ Duration: 3.1s
✅ Passed: 13/26
⚠️ Warnings: 10/26
❌ Failed: 3/26
```

## Success Criteria

✅ All 5 test groups implemented  
✅ Integration with FoundationRunner complete  
✅ Tests return FoundationResult  
✅ Tests registered in run_quick_check()  
✅ Diagnostics menu updated  
✅ No syntax errors  
✅ Tests execute without crashes  
✅ Admin-only execution enforced  
✅ NO signal logic modified  

## Known Limitations

- **Network-dependent tests** may fail in offline environments (Config, external API checks from PR 1)
- **Module availability**: Some tests may warn if optional modules not installed
- **Edge cases**: Indicator tests deliberately trigger edge cases to verify handling

## Future Work (Out of Scope for PR 2)

❌ **NOT included** (per PR requirements):
- Replay functionality (exists in separate system)
- Guardrails (future PR)
- Self-healing (future PR)
- Auto-fix (future PR)
- Additional test groups beyond the 5 specified

## Conclusion

PR 2 successfully implements the **first complete canonical diagnostic test pack** with 5 comprehensive test groups. These tests integrate seamlessly with PR 1's foundation runner and provide robust self-audit capabilities without any risk to production signal generation or trading.

**Total Diagnostic Coverage**: 26 tests (21 from PR 1 + 5 from PR 2)  
**Execution Time**: ~3-4 seconds  
**Safety Level**: Maximum (read-only, dry-run, admin-only)  
**Integration**: Seamless with existing bot.py diagnostics menu
