# PR 2A Quick Reference Guide

## Running Diagnostics

### Via Python Script
```bash
python3 test_pr2a_diagnostics.py
```

### Via Python Code
```python
import asyncio
from diagnostics import run_quick_check

async def main():
    report = await run_quick_check()
    print(report)

asyncio.run(main())
```

### Via Telegram Bot
Send the following command to the bot:
```
/diagnostics quick_check
```
or
```
/admin diagnostics
```

## What Gets Checked (24 Tests)

### 1. Logger Tests (4)
- ✅ Logger configuration validation
- ✅ Handler formatter validation
- ✅ Log file accessibility check
- ✅ Log level consistency check

### 2. Exception Sweep (3)
- ✅ Auto-discover public bot functions
- ✅ Mock execution safety (blacklisted functions)
- ✅ Exception type analysis

### 3. Indicator Tests (4)
- ✅ NaN propagation detection
- ✅ Divide-by-zero safety
- ✅ Boundary input testing
- ✅ Indicator schema validation

### 4. Signal Pipeline Dry-Run (3)
- ✅ Signal creation dry-run (no real sends)
- ✅ Signal schema validation
- ✅ Mock send validation

### 5. Config/Env Tests (3)
- ✅ Required config keys check
- ✅ Value type validation
- ✅ Default fallback safety

### 6. Schema/Type Validation (2)
- ✅ Core data objects validation
- ✅ Serialization safety test

### 7. Duplicate/Idempotency (2)
- ✅ Duplicate guard existence check
- ✅ Deduplication key validation

### 8. Retry/Loop Risk (1)
- ✅ Unbounded retry detection

### 9. Binance Read-Only (2)
- ✅ Mock Binance data fetch
- ✅ Response schema validation

## Expected Output

```
🛠 *Diagnostic Report*

⏱ Duration: 1.5s
✅ Passed: 19
⚠️ Warnings: 3
❌ Failed: 2

==============================

*🔴 HIGH SEVERITY FAILURES:*
• [Check name]
  → [Failure reason]

*⚠️ WARNINGS:*
• [Check name]
  → [Warning reason]
```

## Severity Levels

- **HIGH**: Critical issues that could prevent bot operation
- **MED**: Important issues that may affect functionality
- **LOW**: Minor issues or informational warnings

## Status Codes

- **PASS**: Check completed successfully
- **WARN**: Issue detected but not critical
- **FAIL**: Critical issue detected

## Safety Guarantees

### READ-ONLY Operations
All 24 checks are **guaranteed read-only**:
- ❌ No file writes
- ❌ No database modifications
- ❌ No API mutations
- ❌ No Telegram sends
- ❌ No state changes

### Mocked Services
External services are fully mocked:
- ✅ Binance API: Mock response parsing only
- ✅ Telegram API: Message formatting only (no sends)
- ✅ Database: Read operations only

## Performance

- **Typical Execution Time:** 1-2 seconds
- **Timeout Per Check:** 30 seconds (configurable)
- **Total Runtime Cap:** 10 minutes
- **Memory Impact:** Minimal (<50MB)

## Troubleshooting

### Common Issues

**Issue:** "Cannot import diagnostics"
**Solution:** Ensure you're in the correct directory and dependencies are installed:
```bash
pip install -r requirements.txt
```

**Issue:** "Missing critical config"
**Solution:** Create a `.env` file with required variables:
```bash
TELEGRAM_BOT_TOKEN=your_token_here
ADMIN_CHAT_ID=your_chat_id_here
```

**Issue:** "High severity failures"
**Solution:** Review the specific failure message and fix the underlying issue. Diagnostics are informational only - they don't auto-fix.

## Integration with Bot

The diagnostics are integrated into the bot's admin system:

1. **Telegram Command:** `/admin diagnostics`
2. **Admin Dashboard:** Diagnostics tab
3. **Scheduled Runs:** Can be configured via cron/scheduler

## Advanced Usage

### Running Specific Checks

```python
from diagnostic_tests import check_logger_configuration

result = check_logger_configuration()
print(f"Status: {result.status}")
print(f"Message: {result.message}")
```

### Custom Check Lists

```python
from diagnostics import DiagnosticRunner
from diagnostic_tests import check_nan_propagation, check_divide_by_zero_safety

runner = DiagnosticRunner()
checks = [
    ("NaN Check", check_nan_propagation),
    ("Divide by Zero", check_divide_by_zero_safety)
]

results = await runner.run_all(checks)
report = runner.format_report()
print(report)
```

## Files Reference

- **diagnostic_tests.py**: All 24 check implementations
- **diagnostics.py**: Runner and integration code
- **diagnostic_runner.py**: FoundationRunner (from PR 1)
- **test_pr2a_diagnostics.py**: Test script
- **PR_2A_IMPLEMENTATION_SUMMARY.md**: Full documentation

## Support

For issues or questions:
1. Check `PR_2A_IMPLEMENTATION_SUMMARY.md` for detailed docs
2. Review test output from `test_pr2a_diagnostics.py`
3. Check bot logs for diagnostic execution errors

---

**Last Updated:** 2026-02-01  
**Version:** PR 2A  
**Status:** Production Ready ✅
