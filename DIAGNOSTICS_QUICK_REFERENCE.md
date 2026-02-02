# Quick Reference: Startup Diagnostics Usage

## ✅ DO THIS

### At Startup (post_init)
```python
# ✅ CORRECT - Non-blocking, safe, message first
async def post_init(application):
    await send_startup_message(application)
    diagnostic_report = await run_startup_diagnostics_safe()
    await send_diagnostic_report(application, diagnostic_report)
```

### User Commands
```python
# ✅ CORRECT - User-triggered, not startup
async def handle_quick_check(update, context):
    from diagnostics import run_quick_check
    report = await run_quick_check()
    await update.message.reply_text(report)
```

### Background Jobs
```python
# ✅ CORRECT - Background job, not startup
async def diagnostic_cache_refresh():
    from diagnostics import run_quick_check
    await run_quick_check()
```

## ❌ DON'T DO THIS

### At Startup
```python
# ❌ WRONG - Direct call, no timeout, can block
async def post_init(application):
    from diagnostics import run_quick_check
    report = await run_quick_check()  # NO!
    await send_startup_message(application)
```

```python
# ❌ WRONG - Blocking try/except
async def post_init(application):
    try:
        from diagnostics import run_quick_check
        report = await run_quick_check()
        await send_startup_message(application)  # Blocked if fail!
    except Exception as e:
        logger.error(e)  # Message never sent!
```

```python
# ❌ WRONG - Diagnostics before message
async def post_init(application):
    diagnostic_report = await run_startup_diagnostics_safe()
    await send_startup_message(application)  # Should be FIRST!
```

## The Golden Rules

1. **Startup message ALWAYS comes FIRST**
2. **ONLY `run_startup_diagnostics_safe()` can call diagnostics at startup**
3. **User commands can call `run_quick_check()` directly**
4. **Diagnostics NEVER block startup**

## File: bot.py

### Line ~17651: Safe Wrapper
```python
async def run_startup_diagnostics_safe():
    # ⚠️ THIS IS THE ONLY FUNCTION ALLOWED TO CALL run_quick_check() AT STARTUP
    ...
```

### Line ~16290: User Command
```python
async def handle_quick_check(update, context):
    # ✅ ALLOWED: User-triggered command (not startup)
    from diagnostics import run_quick_check
    ...
```

### Line ~17936: Startup Flow
```python
async def post_init(application):
    # STEP 1: Send startup message FIRST
    await send_startup_message(application)
    
    # STEP 2: Run diagnostics (non-blocking)
    diagnostic_report = await run_startup_diagnostics_safe()
    
    # STEP 3: Send report (optional)
    await send_diagnostic_report(application, diagnostic_report)
```

## Tests

Run: `python3 test_non_blocking_diagnostics.py`

Expected: **14/14 tests PASS**

---

**Remember:** When in doubt, use `run_startup_diagnostics_safe()` at startup!
