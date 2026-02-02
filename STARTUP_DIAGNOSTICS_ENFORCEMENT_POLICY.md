# 🛡️ Startup Diagnostics - Enforcement Policy

## Overview

This document defines the **STRICT ENFORCEMENT POLICY** for startup diagnostics to prevent blocking behavior in production.

## Problem History

**Issue:** The main branch contained old blocking diagnostic code that could prevent the bot from sending its startup confirmation message, violating operational guarantees.

**Root Cause:**
- Direct calls to `run_quick_check()` in `post_init()` without timeout protection
- Blocking try/except that could crash startup flow
- Startup message sent AFTER diagnostics (could be blocked)

## Enforcement Policy

### ❌ FORBIDDEN

The following patterns are **STRICTLY FORBIDDEN** at bot startup:

1. **Direct `run_quick_check()` calls in `post_init()`**
   ```python
   # ❌ FORBIDDEN - Can block startup
   async def post_init(application):
       from diagnostics import run_quick_check
       report = await run_quick_check()  # NO TIMEOUT!
   ```

2. **Blocking try/except with diagnostics**
   ```python
   # ❌ FORBIDDEN - Can prevent startup message
   try:
       from diagnostics import run_quick_check
       report = await run_quick_check()
       await send_startup_message()  # BLOCKED if diagnostics fail!
   except Exception as e:
       # Startup message never sent!
   ```

3. **Any code that can prevent startup message**
   ```python
   # ❌ FORBIDDEN - Diagnostics before message
   async def post_init(application):
       await run_diagnostics()  # Could fail/timeout
       await send_startup_message()  # Might never execute!
   ```

### ✅ ALLOWED

The following patterns are **EXPLICITLY ALLOWED**:

1. **Only `run_startup_diagnostics_safe()` at startup**
   ```python
   # ✅ ALLOWED - Safe wrapper with timeout
   async def post_init(application):
       await send_startup_message()  # FIRST, ALWAYS
       diagnostic_report = await run_startup_diagnostics_safe()  # SAFE
       await send_diagnostic_report(application, diagnostic_report)
   ```

2. **User-triggered diagnostic commands**
   ```python
   # ✅ ALLOWED - User command, not startup
   async def handle_quick_check(update, context):
       from diagnostics import run_quick_check
       report = await run_quick_check()  # OK - user triggered
   ```

3. **Background jobs and schedulers**
   ```python
   # ✅ ALLOWED - Background job, not startup
   async def diagnostic_cache_refresh_job():
       from diagnostics import run_quick_check
       report = await run_quick_check()  # OK - background
   ```

## Required Startup Flow

**ONLY THIS FLOW IS PERMITTED:**

```
1. send_startup_message()          ← ALWAYS FIRST
2. run_startup_diagnostics_safe()  ← SAFE, NON-BLOCKING, 60s timeout
3. send_diagnostic_report()        ← OPTIONAL, only if diagnostics succeeded
```

### Implementation Example

```python
async def post_init(application):
    """Post-initialization: startup message, diagnostics, diagnostic report"""
    
    # STEP 1: Send startup message FIRST (BEFORE diagnostics!)
    await send_startup_message(application)
    
    # STEP 2: Run diagnostics (non-blocking, fail-safe)
    diagnostic_report = await run_startup_diagnostics_safe()
    
    # STEP 3: Send diagnostic report (if available)
    await send_diagnostic_report(application, diagnostic_report)
```

## Safety Guarantees

The `run_startup_diagnostics_safe()` function provides these guarantees:

1. **Never raises exceptions** - All errors caught and logged
2. **Never blocks startup** - 60-second timeout enforced
3. **Always returns** - Returns `None` on any failure
4. **Comprehensive logging** - All errors logged with stack traces
5. **Fail-safe** - Bot continues operating even if diagnostics crash

## Code Locations

### Safe Wrapper (ONLY place allowed to call `run_quick_check()` at startup)
- **File:** `bot.py`
- **Function:** `run_startup_diagnostics_safe()` (line ~17651)
- **Purpose:** Safe wrapper with timeout and exception handling

### User Commands (Allowed to call `run_quick_check()` directly)
- **File:** `bot.py`
- **Function:** `handle_quick_check()` (line ~16290)
- **Purpose:** User-triggered diagnostic command
- **Trigger:** Manual user command, not startup

### Startup Flow (ONLY permitted flow)
- **File:** `bot.py`
- **Function:** `post_init()` (line ~17936)
- **Purpose:** Post-initialization callback
- **Flow:** `send_startup_message` → `run_startup_diagnostics_safe` → `send_diagnostic_report`

## Verification Checklist

Before any PR merge to main, verify:

- [ ] No direct `run_quick_check()` calls in `post_init()`
- [ ] No blocking try/except with diagnostics at startup
- [ ] Startup message is sent FIRST, before any diagnostics
- [ ] Only `run_startup_diagnostics_safe()` calls diagnostics at startup
- [ ] All user commands are properly documented as "user-triggered"
- [ ] All tests pass (14/14 in `test_non_blocking_diagnostics.py`)

## Monitoring

In production, these log messages confirm correct behavior:

```
✅ Startup message sent                     ← Message sent FIRST
🔍 Running startup diagnostics (non-blocking)  ← Safe wrapper started
✅ Diagnostics complete                     ← Diagnostics finished
✅ Diagnostic report sent                   ← Report sent (optional)
```

If diagnostics fail, you'll see:

```
✅ Startup message sent                     ← Message STILL sent
⚠️ Startup diagnostics timed out (non-critical)  ← Diagnostic failed
ℹ️ No diagnostic report to send            ← Report skipped
```

**The key is: startup message is ALWAYS sent, regardless of diagnostic status.**

## Consequences of Violations

Violating this policy can cause:

1. **Bot appears offline** - Startup message never sent
2. **Operational uncertainty** - No confirmation of bot status
3. **Timeout failures** - Diagnostics block indefinitely
4. **Crash loops** - Bot restarts but never confirms online
5. **Production incidents** - Users cannot determine bot health

## Contact

For questions or clarification on this policy, refer to:

- **PR:** copilot/ensure-non-blocking-diagnostics
- **Documentation:** NON_BLOCKING_DIAGNOSTICS_IMPLEMENTATION.md
- **Tests:** test_non_blocking_diagnostics.py

---

**Last Updated:** 2026-02-02  
**Status:** ✅ ENFORCED  
**Version:** 1.0
