# Phase 1: Production-Safe Diagnostic Control Panel

## Overview

The Diagnostic Control Panel provides production-safe testing and monitoring capabilities for the Crypto Signal Bot. When enabled, it prevents real signals from being sent to users while allowing safe testing and diagnostic operations.

## Features

### 1. DIAGNOSTIC_MODE Flag

**Purpose:** Provides a global switch to enable/disable diagnostic mode for production-safe testing.

**Location:** Environment variable in `.env` file

**Usage:**
```bash
# In .env file
DIAGNOSTIC_MODE=true   # Enable diagnostic mode
DIAGNOSTIC_MODE=false  # Disable diagnostic mode (production)
```

**When DIAGNOSTIC_MODE is enabled:**
- ❌ **NO** real user signals are sent via Telegram
- ❌ **NO** user alerts are sent
- ❌ **NO** Binance trading operations occur (if implemented)
- ✅ Admin messages are prefixed with `[DIAGNOSTIC MODE]`
- ✅ All blocked operations are logged
- ✅ Diagnostic reports go to admin only

**Implementation:**
```python
# bot.py (line ~304)
DIAGNOSTIC_MODE = os.getenv('DIAGNOSTIC_MODE', 'false').lower() == 'true'

if DIAGNOSTIC_MODE:
    logger.warning("⚠️ DIAGNOSTIC MODE ENABLED - No real signals/alerts will be sent!")
    logger.warning("   → All Telegram sends will be mocked")
    logger.warning("   → All Binance trades will be mocked")
    logger.warning("   → Reports go to admin only")
```

### 2. Safe Send Telegram Function

**Purpose:** Wrapper around Telegram send operations that respects DIAGNOSTIC_MODE.

**Function:** `safe_send_telegram(context, chat_id, text, **kwargs)`

**Behavior:**
- In normal mode: Sends messages normally
- In DIAGNOSTIC_MODE:
  - Blocks messages to non-admin users (returns None)
  - Prefixes admin messages with `[DIAGNOSTIC MODE]`
  - Logs all blocked messages

**Example:**
```python
# Instead of:
await context.bot.send_message(chat_id=user_id, text="Signal generated!")

# Use:
await safe_send_telegram(context, user_id, "Signal generated!")
```

### 3. Telegram Diagnostic Menu

**Access:** Admin only (OWNER_CHAT_ID)

**Main Menu Button:** 🛠 Diagnostics

**Submenu Options:**
- 🔍 **Quick Check** - Runs 5 core diagnostic tests (implemented)
- 🔬 **Full Self-Audit** - Comprehensive system audit (placeholder)
- 📊 **System Status** - Current system status (placeholder)
- 🔄 **Replay Last Signal** - Re-run last signal for testing (placeholder)
- 🔙 **Back to Main Menu** - Return to main menu

### 4. Quick Check - 5 Core Diagnostic Tests

The Quick Check runs 5 essential diagnostic tests and provides a formatted report.

#### Test 1: Logger Configuration
- **Severity:** LOW
- **Checks:** 
  - Handler count
  - Log level configuration
- **Pass Criteria:** At least one handler configured

#### Test 2: Critical Imports
- **Severity:** HIGH
- **Checks:** Required modules:
  - `pandas`
  - `numpy`
  - `requests`
  - `telegram`
  - `ta` (technical analysis)
- **Pass Criteria:** All modules importable

#### Test 3: Signal Schema Validation
- **Severity:** MED
- **Checks:**
  - ICTSignalEngine exists
  - Required methods: `generate_signal`, `_detect_ict_components`, `_calculate_sl_price`
- **Pass Criteria:** Engine structure is valid

#### Test 4: NaN Detection
- **Severity:** MED
- **Checks:**
  - Creates sample data
  - Calculates SMA and EMA indicators
  - Verifies no NaN values in results
- **Pass Criteria:** Indicators calculate without NaN

#### Test 5: Duplicate Signal Guard
- **Severity:** MED
- **Checks:**
  - CacheManager exists
  - Has duplicate detection methods
- **Pass Criteria:** Cache system is available

#### Report Format

```
🛠 *Diagnostic Report*

⏱ Duration: 0.2s
✅ Passed: 4
⚠️ Warnings: 1
❌ Failed: 0

==============================

*⚠️ WARNINGS:*
• Logger Configuration
  → No root logger handlers (may use module-level loggers)
```

### 5. Startup Diagnostics (Optional)

**Purpose:** Automatically run Quick Check when bot starts and send report to admin.

**Configuration:** Enabled by default via `post_init` callback

**Features:**
- Runs Quick Check on bot startup
- Sends report to admin (OWNER_CHAT_ID)
- Gracefully handles errors
- Logs all diagnostic activity

**Example Output:**
```
🤖 *Bot Started*

🛠 *Diagnostic Report*
⏱ Duration: 0.2s
✅ Passed: 4
⚠️ Warnings: 1
❌ Failed: 0
...
```

## File Structure

```
Crypto-signal-bot/
├── bot.py                  # Main bot file with DIAGNOSTIC_MODE integration
├── diagnostics.py          # New diagnostic system module
├── .env.example           # Updated with DIAGNOSTIC_MODE documentation
└── DIAGNOSTIC_GUIDE.md    # This file
```

## Usage Guide

### For Developers

1. **Enable Diagnostic Mode for Testing:**
   ```bash
   echo "DIAGNOSTIC_MODE=true" >> .env
   python3 bot.py
   ```

2. **Run Quick Check via Telegram:**
   - Open bot in Telegram
   - Click "🛠 Diagnostics" button
   - Click "🔍 Quick Check"
   - View diagnostic report

3. **Run Quick Check via CLI:**
   ```bash
   python3 -c "
   import asyncio
   from diagnostics import run_quick_check
   
   async def test():
       report = await run_quick_check()
       print(report)
   
   asyncio.run(test())
   "
   ```

### For Admins

1. **Check Bot Health:**
   - Use "🛠 Diagnostics" → "🔍 Quick Check" daily
   - Review any WARNINGS or FAILURES
   - Address HIGH severity issues immediately

2. **Review Startup Diagnostics:**
   - Check admin messages when bot restarts
   - Look for diagnostic report
   - Investigate any failures

3. **Production Testing:**
   - Enable DIAGNOSTIC_MODE before testing new features
   - Verify no real signals are sent
   - Disable DIAGNOSTIC_MODE when done

## Security Considerations

### ✅ Safe Operations (Always Allowed)
- Reading files
- Searching code
- Analyzing data
- Viewing logs
- Running diagnostics

### ⚠️ Blocked in DIAGNOSTIC_MODE
- Sending signals to users
- Sending alerts
- Executing trades
- Writing to production databases (if implemented)
- External API calls that modify state

### 🔒 Admin-Only Features
- Diagnostic menu access
- Quick Check execution
- System status viewing
- Diagnostic reports

## Troubleshooting

### Issue: "Admin only" message when accessing diagnostics
**Solution:** Only OWNER_CHAT_ID can access diagnostics. Verify your user ID matches OWNER_CHAT_ID in .env file.

### Issue: Diagnostic check fails with "Missing modules"
**Solution:** Install required dependencies:
```bash
pip3 install -r requirements.txt
```

### Issue: DIAGNOSTIC_MODE doesn't block messages
**Solution:** 
1. Verify DIAGNOSTIC_MODE=true in .env
2. Restart bot to reload environment variables
3. Check logs for "DIAGNOSTIC MODE ENABLED" message

### Issue: Quick Check times out
**Solution:** Each check has 30-second timeout. If timeout occurs:
1. Check system resources
2. Verify all dependencies are installed
3. Review logs for specific check that timed out

## Future Enhancements (Phase 2+)

- 🔬 **Full Self-Audit** - Comprehensive system analysis
- 📊 **System Status** - Real-time metrics and health
- 🔄 **Replay Last Signal** - Signal replay for debugging
- 📈 **Historical Diagnostics** - Track health over time
- 🔔 **Alert on Failures** - Notify admin of critical issues
- 📝 **Diagnostic Logs** - Persistent diagnostic history

## API Reference

### DiagnosticResult Class
```python
class DiagnosticResult:
    name: str        # Test name
    status: str      # PASS / FAIL / WARN
    severity: str    # HIGH / MED / LOW
    message: str     # Result message
    details: str     # Additional details
    timestamp: datetime
```

### DiagnosticRunner Class
```python
class DiagnosticRunner:
    async def run_check(check_name, check_func, timeout=30)
    async def run_all(checks: List[Tuple[str, callable]])
    def format_report() -> str
```

### Core Functions
```python
async def run_quick_check() -> str
async def safe_send_telegram(context, chat_id, text, **kwargs) -> Optional[Any]
async def diagnostics_menu_handler(update, context)
async def handle_quick_check(update, context)
```

### DiagnosticRunner Methods
```python
async def run_check(check_name: str, check_func, timeout: int = 30) -> DiagnosticResult
async def run_all(checks: List[Tuple[str, Callable]]) -> List[DiagnosticResult]
def format_report() -> str
```

## Change Log

### Version 1.0.0 (2026-01-30)
- ✅ Initial implementation
- ✅ DIAGNOSTIC_MODE flag
- ✅ safe_send_telegram wrapper
- ✅ Quick Check with 5 tests
- ✅ Telegram diagnostic menu
- ✅ Startup diagnostics
- ✅ Admin-only access control

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review logs for error messages
3. Contact bot owner (OWNER_CHAT_ID)

---

**Last Updated:** 2026-01-30  
**Version:** 1.0.0  
**Author:** Copilot  
**Status:** Production Ready ✅
