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
- 🔍 **Quick Check** - Runs 20 diagnostic tests (Phase 2A expanded)
- 🔬 **Full Self-Audit** - Comprehensive system audit (placeholder)
- 📊 **System Status** - Current system status (placeholder)
- 🔄 **Replay Last Signal** - Re-run last signal for testing (placeholder)
- 🔙 **Back to Main Menu** - Return to main menu

### 4. Quick Check - 20 Diagnostic Tests (Phase 2A Expanded)

The Quick Check runs 20 essential diagnostic tests across 4 groups and provides a formatted report.

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

#### Phase 2A New Checks:

**GROUP 1: MTF Data Validation**

#### Test 6: MTF Timeframes Available
- **Severity:** HIGH
- **Checks:**
  - 1h, 2h, 4h, 1d data fetchable from Binance
  - Response status code 200
  - Data not empty
- **Pass Criteria:** All 4 timeframes accessible

#### Test 7: HTF Components Storage
- **Severity:** MED
- **Checks:**
  - htf_components dict can be created
  - Can write test HTF data
  - Can read back HTF data
  - Data persists correctly
- **Pass Criteria:** Storage read/write working

#### Test 8: Klines Data Freshness
- **Severity:** MED
- **Checks:**
  - Latest 1h kline for BTCUSDT
  - Timestamp within last 2 hours
  - Close time is recent
- **Pass Criteria:** Data is fresh (<2h old)

#### Test 9: Price Data Sanity
- **Severity:** HIGH
- **Checks:**
  - No zero/negative prices
  - High >= Low
  - High >= Open, Close
  - Low <= Open, Close
- **Pass Criteria:** All candles valid

**GROUP 2: Signal Schema Extended**

#### Test 10: Signal Required Fields
- **Severity:** HIGH
- **Checks:**
  - ICTSignalEngine methods exist
  - generate_signal, _detect_ict_components
  - _calculate_sl_price, _calculate_tp_prices
- **Pass Criteria:** All methods present

#### Test 11: Cache Write/Read Test
- **Severity:** MED
- **Checks:**
  - Write test signal to temp cache
  - Read back same signal
  - Data integrity preserved
- **Pass Criteria:** Cache I/O working

#### Test 12: Signal Type Validation
- **Severity:** LOW
- **Checks:**
  - SignalType enum (LONG, SHORT)
  - MarketBias enum (BULLISH, BEARISH, NEUTRAL)
- **Pass Criteria:** Enums found

**GROUP 3: Runtime Health**

#### Test 13: Memory Usage
- **Severity:** MED
- **Checks:**
  - Current process RSS < 1GB
  - Warn at 500MB
  - Uses psutil or resource module
- **Pass Criteria:** Memory < 500MB

#### Test 14: Response Time Test
- **Severity:** LOW
- **Checks:**
  - Simple calculation < 100ms
  - DataFrame operation < 500ms
  - Indicator calculation < 2s
- **Pass Criteria:** All ops within thresholds

#### Test 15: Exception Rate
- **Severity:** MED
- **Checks:**
  - Parse last 1000 log lines
  - Count ERROR/EXCEPTION entries
  - Warn if > 5%, fail if > 10%
- **Pass Criteria:** Error rate < 5%

#### Test 16: Job Queue Health
- **Severity:** LOW
- **Checks:**
  - No repeated "timeout" in logs
  - No "stuck" indicators
  - No infinite loop warnings
- **Pass Criteria:** No stuck job indicators

**GROUP 4: External Integration**

#### Test 17: Binance API Reachable
- **Severity:** HIGH
- **Checks:**
  - GET api.binance.com/api/v3/ping
  - Status 200
  - Response time < 5s
- **Pass Criteria:** API responsive

#### Test 18: Telegram API Responsive
- **Severity:** MED
- **Checks:**
  - telegram module importable
  - telegram.Bot class exists
  - No connection errors in logs
- **Pass Criteria:** Module available

#### Test 19: File System Access
- **Severity:** MED
- **Checks:**
  - Can read bot.py
  - Can write to temp directory
  - Cache directory accessible
- **Pass Criteria:** Read/write working

#### Test 20: Log File Writeable
- **Severity:** LOW
- **Checks:**
  - bot.log exists
  - bot.log is writeable
  - No permission errors
- **Pass Criteria:** Log file writeable

#### Report Format

```
🛠 *Diagnostic Report*

⏱ Duration: 2.3s
✅ Passed: 18
⚠️ Warnings: 2
❌ Failed: 0

==============================

*⚠️ WARNINGS:*
• HTF Components Storage
  → htf_components dict not found (may not be initialized)

• Exception Rate
  → 3.2% error rate in last 1000 log lines (threshold: 5%)

*✅ ALL HIGH SEVERITY CHECKS PASSED*
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

### Version 2.0.0 (2026-01-30) - Phase 2A
- ✅ Expanded Quick Check from 5 to 20 tests
- ✅ Added GROUP 1: MTF Data Validation (4 checks)
- ✅ Added GROUP 2: Signal Schema Extended (3 checks)
- ✅ Added GROUP 3: Runtime Health (4 checks)
- ✅ Added GROUP 4: External Integration (4 checks)
- ✅ Updated format_report() for 20 checks
- ✅ Optimized report to stay under 4000 chars
- ✅ All checks have proper error handling
- ✅ All checks respect 30s timeout

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
**Version:** 2.0.0 (Phase 2A)  
**Author:** Copilot  
**Status:** Production Ready ✅
