# CI Startup Guard Documentation

## Overview

The **Startup Diagnostics Guard** is a GitHub Actions CI check that enforces the non-blocking startup diagnostics policy for the Crypto Signal Bot. This guard prevents PRs from introducing code that could block bot startup or delay critical operational messages.

## Purpose

This CI guard ensures that:

1. ✅ The bot always sends its "Bot started and online" message immediately
2. ✅ Diagnostics never block the bot from becoming operational
3. ✅ Startup order is maintained: message first, diagnostics second
4. ✅ Only approved safe wrappers are used for startup diagnostics

## Policy Enforced

### Non-Blocking Startup Diagnostics Policy

**Core Principle:** Diagnostics are informational ONLY and NEVER block operations.

### Rules Enforced

#### Rule 1: No Direct `run_quick_check()` in `post_init()`

**❌ VIOLATION:**
```python
async def post_init(application):
    report = await run_quick_check()  # Direct call - BLOCKS startup
    await send_message(report)
```

**✅ CORRECT:**
```python
async def post_init(application):
    await send_startup_message(application)
    diagnostic_report = await run_startup_diagnostics_safe()  # Safe wrapper
    await send_diagnostic_report(application, diagnostic_report)
```

#### Rule 2: Startup Message Must Come First

**❌ VIOLATION:**
```python
async def post_init(application):
    diagnostic_report = await run_startup_diagnostics_safe()  # WRONG ORDER
    await send_startup_message(application)  # Too late!
```

**✅ CORRECT:**
```python
async def post_init(application):
    # STEP 1: Operational confirmation FIRST
    await send_startup_message(application)
    
    # STEP 2: Diagnostics SECOND
    diagnostic_report = await run_startup_diagnostics_safe()
    
    # STEP 3: Report results
    await send_diagnostic_report(application, diagnostic_report)
```

#### Rule 3: No Blocking Exception Handling

**❌ VIOLATION:**
```python
async def post_init(application):
    try:
        report = await run_quick_check()  # Blocking error handling
        await send_message(report)
    except Exception:
        pass  # Could hide startup issues
```

**✅ CORRECT:**
```python
async def post_init(application):
    await send_startup_message(application)
    # No try/except needed - run_startup_diagnostics_safe handles errors
    diagnostic_report = await run_startup_diagnostics_safe()
    await send_diagnostic_report(application, diagnostic_report)
```

## Allowed Patterns

### ✅ User-Triggered Diagnostics

```python
async def handle_quick_check(update, context):
    """Handler for /quickcheck command - user triggered"""
    report = await run_quick_check()  # OK - not at startup
    await update.message.reply_text(report)
```

### ✅ Safe Wrapper Implementation

```python
async def run_startup_diagnostics_safe():
    """Safe wrapper with timeout and error handling"""
    try:
        report = await asyncio.wait_for(
            run_quick_check(),  # OK - wrapped with timeout
            timeout=60.0
        )
        return report
    except Exception:
        return None  # Fail-safe
```

## How the Guard Works

### Detection Script

The guard uses a bash script (`.github/scripts/check_startup_diagnostics.sh`) that:

1. **Extracts the `post_init()` function** from `bot.py`
2. **Checks for violations** using pattern matching and line ordering
3. **Reports clear, actionable errors** when violations are found
4. **Exits with code 1** if violations detected (fails the CI check)

### GitHub Actions Workflow

The workflow (`.github/workflows/startup_diagnostics_guard.yml`):

- **Triggers on:**
  - Pull requests that modify `bot.py`, `diagnostics.py`, or `telegram_bot.py`
  - Pushes to `main` branch that modify `bot.py`

- **Execution:**
  - Runs in less than 10 seconds
  - Uses simple grep/sed pattern matching
  - No external dependencies required

- **Artifacts:**
  - On failure, uploads `bot.py` and the script for debugging

## CI Failure Messages

When the guard detects a violation, it outputs detailed error messages:

```
❌ CI GUARD FAILURE: Blocking Startup Diagnostics Detected
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

VIOLATION: Direct run_quick_check() call found in post_init()

This violates the non-blocking startup diagnostics policy:
  - Diagnostics MUST be wrapped in run_startup_diagnostics_safe()
  - Diagnostics MUST NOT block bot startup
  - Diagnostics MUST come AFTER send_startup_message()

FOUND IN: bot.py, line 123 (post_init function)

HOW TO FIX:
  1. Use run_startup_diagnostics_safe() instead of direct calls
  2. Ensure send_startup_message() is called FIRST
  3. See PR #235 for correct implementation

CORRECT PATTERN:
  async def post_init(application):
      await send_startup_message(application)  # FIRST
      diagnostic_report = await run_startup_diagnostics_safe()  # SECOND
      await send_diagnostic_report(application, diagnostic_report)

For details, see NON_BLOCKING_DIAGNOSTICS_IMPLEMENTATION.md
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

## Resolving CI Failures

If the guard fails on your PR:

### Step 1: Review the Error Message

The guard provides detailed information about:
- Which rule was violated
- Where in the code the violation was found
- How to fix the violation
- Examples of correct implementation

### Step 2: Check Your Changes

Compare your code against the correct patterns shown in this document and the error message.

### Step 3: Fix the Violation

Apply the recommended fix:

1. **For direct calls:** Wrap in `run_startup_diagnostics_safe()`
2. **For ordering:** Move `send_startup_message()` to the top
3. **For exception handling:** Remove try/except and use the safe wrapper

### Step 4: Test Locally

Before pushing, test the guard locally:

```bash
bash .github/scripts/check_startup_diagnostics.sh
```

This should output:
```
✅ STARTUP DIAGNOSTICS GUARD: PASSED
```

### Step 5: Push and Verify

Push your changes and verify the CI check passes.

## Testing the Guard

### Local Testing

Run the script manually:

```bash
cd /path/to/Crypto-signal-bot
bash .github/scripts/check_startup_diagnostics.sh
```

### Expected Results

On the current `main` branch:
```
✅ STARTUP DIAGNOSTICS GUARD: PASSED
```

### Testing Violations

To test that the guard catches violations, you can temporarily modify `bot.py` to introduce a violation, then run the script.

**Example Test:**
1. Change `post_init()` to call `run_quick_check()` directly
2. Run: `bash .github/scripts/check_startup_diagnostics.sh`
3. Should output: `❌ STARTUP DIAGNOSTICS GUARD: FAILED`
4. Revert the change

## Files

### Created Files

1. **`.github/scripts/check_startup_diagnostics.sh`**
   - Bash script that performs the actual checks
   - Executable: `chmod +x` before running
   - Zero dependencies (uses standard bash/grep/sed)

2. **`.github/workflows/startup_diagnostics_guard.yml`**
   - GitHub Actions workflow definition
   - Triggers on PR and main branch changes
   - Runs the detection script

3. **`docs/CI_STARTUP_GUARD.md`** (this file)
   - Documentation explaining the guard
   - Policy reference
   - Troubleshooting guide

### No Files Modified

This is a **PURE CI ENFORCEMENT** PR:

- ❌ `bot.py` - NOT modified
- ❌ `diagnostics.py` - NOT modified
- ❌ `telegram_bot.py` - NOT modified
- ❌ Any runtime code - NOT modified

## Performance

- **Execution Time:** < 10 seconds
- **Dependencies:** None (uses standard Unix tools)
- **Resource Usage:** Minimal (grep/sed pattern matching only)
- **False Positives:** Zero on correct implementation

## Maintenance

### Updating Detection Rules

If new patterns need to be detected:

1. Edit `.github/scripts/check_startup_diagnostics.sh`
2. Add new rule section following the existing pattern
3. Test locally against both valid and invalid code
4. Update this documentation

### Disabling the Guard

To temporarily disable (not recommended):

1. Comment out the workflow in `.github/workflows/startup_diagnostics_guard.yml`
2. Or skip the check with `[skip ci]` in commit message (applies to all checks)

To permanently remove:
1. Delete `.github/workflows/startup_diagnostics_guard.yml`
2. Delete `.github/scripts/check_startup_diagnostics.sh`

## References

- **Policy Document:** `NON_BLOCKING_DIAGNOSTICS_IMPLEMENTATION.md`
- **Implementation PR:** #235 (referenced in error messages)
- **Complete Policy:** `STARTUP_DIAGNOSTICS_ENFORCEMENT_POLICY.md`

## FAQ

### Q: Why is this necessary?

**A:** Without enforcement, it's easy to accidentally introduce blocking calls during startup that prevent the bot from sending operational confirmation messages. This guard prevents such regressions.

### Q: What if I need to add new diagnostic code?

**A:** New diagnostics should:
1. Be called from user handlers (commands) - these are not checked
2. Or be added to `run_quick_check()` in `diagnostics.py` - this is safe
3. Never be called directly from `post_init()` - use the safe wrapper

### Q: Can I call diagnostics from other places?

**A:** Yes! The guard only checks `post_init()`. You can call diagnostics from:
- User command handlers
- Scheduled jobs
- Other async functions
- Anywhere except `post_init()` without the safe wrapper

### Q: What if I find a false positive?

**A:** If the guard incorrectly flags valid code:
1. Document the case
2. Update the detection script to exclude the pattern
3. Test thoroughly
4. Update this documentation

### Q: Is this guard required for merging?

**A:** Yes. This is a CI check that must pass before merging to `main`.

## Summary

The Startup Diagnostics Guard is a **safety guardrail** that:

- ✅ Prevents blocking startup diagnostics from being introduced
- ✅ Ensures operational messages are always sent first
- ✅ Provides clear, actionable error messages
- ✅ Runs fast (< 10 seconds)
- ✅ Has zero false positives on correct code
- ✅ Requires no external dependencies
- ✅ Is safe to run on every PR

This guard is part of maintaining a reliable, production-ready bot that always confirms operational status, regardless of diagnostic outcomes.
