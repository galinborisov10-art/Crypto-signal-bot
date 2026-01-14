# 🏥 PR #10: Intelligent System Health Monitoring with Root Cause Analysis

## 📋 Overview

A **self-diagnostic system** that monitors ALL bot components 24/7 and sends **detailed Telegram alerts with ROOT CAUSE analysis** when issues are detected.

**Key Feature:** User can copy-paste error messages from Telegram directly to Copilot Chat for instant fix, without manual investigation.

---

## 🎯 Features Implemented

### 1. **Core Diagnostic Engine** (`system_diagnostics.py`)

Intelligent monitoring with deep root cause analysis for:

- **Trading Journal Health**
  - File existence and permissions
  - Last update timestamp
  - Metadata consistency
  - Error log analysis
  
- **ML Model Training**
  - Model file age
  - Training job execution
  - Data availability
  - Memory issues
  
- **Daily Reports**
  - Report execution status
  - Scheduler health
  
- **Position Monitor**
  - Error detection
  - Runtime issues
  
- **Scheduler**
  - Job execution
  - Misfires
  - Errors
  
- **Disk Space**
  - Usage monitoring
  - Critical alerts

### 2. **Smart Alert Formatting** (`diagnostic_messages.py`)

Telegram-friendly messages with:
- ✅ Status emojis (✅ Healthy, ⚠️ Warning, ❌ Critical)
- 🔍 Root cause analysis
- 📋 Evidence from logs
- 💡 Fix suggestions
- 🔧 Debug commands
- 📍 Code locations

### 3. **6 Automated Health Monitors**

Scheduled monitoring jobs:

| Monitor | Schedule | Purpose |
|---------|----------|---------|
| **Journal Health** | Every 6 hours | Detects journal update failures |
| **ML Training** | Daily at 10:00 | Checks model training status |
| **Daily Reports** | Daily at 09:00 | Verifies report execution |
| **Position Monitor** | Every hour | Detects monitoring errors |
| **Scheduler** | Every 12 hours | Checks job execution |
| **Disk Space** | Daily at 02:00 | Monitors storage |

### 4. **On-Demand Diagnostics**

**`/health` Command:**
- Runs all 6 diagnostic checks
- Returns comprehensive health summary
- Shows issue counts and status

---

## 📝 Usage

### Manual Health Check

```
/health
```

Returns:
```
🏥 SYSTEM HEALTH DIAGNOSTIC

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 TRADING JOURNAL: ✅ HEALTHY
   Status: Updating correctly

🤖 ML MODEL: ⚠️ WARNING
   Age: 12 days old
   Issue: Waiting for 50+ completed trades (38/50)
   
📊 DAILY REPORTS: ✅ HEALTHY
   Last report: Today 08:02
   Status: Executing on schedule

⚙️ POSITION MONITOR: ✅ HEALTHY
   Last check: 3 min ago
   Errors: 0 in last hour

⏰ SCHEDULER: ✅ HEALTHY
   Active jobs: 15
   Missed jobs: 0 in last 24h

💾 DISK SPACE: ✅ HEALTHY
   Used: 45% (2.3GB / 5GB)
   Available: 2.7GB

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Overall:  ✅ 5 OK, ⚠️ 1 WARNING, ❌ 0 CRITICAL

Last full scan: 14.01.2026 13:45
```

### Automatic Alerts

When issues are detected, alerts are automatically sent to owner:

**Example: Journal Error Alert**
```
🚨 JOURNAL HEALTH ALERT

📊 Status: ❌ CRITICAL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 PROBLEM:
Journal not updated for 8.5 hours

🔍 ROOT CAUSE:
AttributeError: 'ICTSignal' object has no attribute 'market_bias'

📋 EVIDENCE:
2026-01-14 10:45:43 - ERROR - ❌ Journal logging error in auto-signal: 
'ICTSignal' object has no attribute 'market_bias'

📍 CODE LOCATION:
bot.py lines ~9900-10200 (auto_signal_job function)

💡 FIX:
Code tries to access ict_signal.market_bias which does not exist. 
Should use ict_signal.bias instead.

🔧 DEBUG COMMANDS:
grep -n "market_bias" /root/Crypto-signal-bot/bot.py | head -n 10
grep -n "class ICTSignal" /root/Crypto-signal-bot/*.py

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 Use /health for full system check
📌 Copy this message to Copilot for instant fix
```

---

## 🔧 Technical Details

### Log Parsing

The system uses `grep_logs()` to analyze bot.log:

```python
# Search for errors in last 6 hours
errors = grep_logs('ERROR.*journal', hours=6)

# Check for auto-signal execution
signals = grep_logs('auto_signal_job', hours=24)
```

### Root Cause Analysis

Each diagnostic function performs multi-level checks:

1. **Check symptom** (e.g., journal not updated)
2. **Investigate cause** (e.g., auto-signal job not running?)
3. **Deep dive** (e.g., errors in logs? permissions?)
4. **Parse error** (e.g., AttributeError? PermissionError?)
5. **Return actionable fix** (e.g., "Check line X in file Y")

### File Structure

```
system_diagnostics.py      # Core diagnostic logic
diagnostic_messages.py      # Alert formatting
bot.py                      # Integration (health command + scheduler jobs)
bot.log                     # Log file for analysis (auto-created)
```

---

## 🧪 Testing

### Run Test Suite

```bash
python3 test_health_monitoring.py
```

This tests:
- ✅ Journal loading
- ✅ Journal diagnostics
- ✅ ML diagnostics
- ✅ Disk space checks
- ✅ Log parsing
- ✅ Full health check
- ✅ Message formatting

### Expected Output

```
================================================================================
🏥 TESTING PR #10: INTELLIGENT HEALTH MONITORING
================================================================================

📝 TEST 1: Load Journal
--------------------------------------------------------------------------------
✅ Journal loaded successfully
   Total trades: 3
   Trades in list: 3

📝 TEST 2: Journal Diagnostics
--------------------------------------------------------------------------------
✅ No journal issues detected

🤖 TEST 3: ML Model Diagnostics
--------------------------------------------------------------------------------
⚠️ Found 1 ML issues:
  ...

💬 TEST 7: Message Formatting
--------------------------------------------------------------------------------
Generated health summary message:
🏥 SYSTEM HEALTH DIAGNOSTIC
...

================================================================================
✅ ALL TESTS COMPLETED
================================================================================
```

---

## 📊 Alert Scenarios

### Scenario 1: Journal Not Updating

**Detection:**
- Journal `last_trade` timestamp > 6 hours old

**Analysis:**
1. Check if auto-signal jobs running → No logs found
2. **Root Cause:** Scheduler crashed
3. **Fix:** Restart bot

**Alert:**
```
🔴 PROBLEM: Journal not updated for 8.5h
🔍 ROOT CAUSE: Auto-signal jobs are NOT running
💡 FIX: Scheduler may have crashed. Check scheduler status.
```

### Scenario 2: ML Model Outdated

**Detection:**
- ML model file last modified > 10 days ago

**Analysis:**
1. Check if weekly training job ran → Found logs
2. Check for training errors → Found "Minimum 50 trades" error
3. **Root Cause:** Insufficient completed trades (38/50)
4. **Fix:** Wait for more trades to complete

**Alert:**
```
🔴 PROBLEM: ML model not trained for 12 days
🔍 ROOT CAUSE: Not enough completed trades (38/50 minimum)
💡 FIX: Need 12 more completed trades. Wait for signals to hit TP/SL.
```

### Scenario 3: Disk Space Critical

**Detection:**
- Disk usage > 90%

**Alert:**
```
🔴 PROBLEM: Disk space critically low: 92.5% used
📋 CURRENT USAGE:
  • Used: 4.62GB / 5GB
  • Free: 0.38GB
  • Usage: 92.5%
💡 FIX: Clean up old logs, backups, or temporary files IMMEDIATELY
```

---

## 🔍 Debugging

### Check Diagnostic Logs

```bash
# View health monitor execution
grep "health check" bot.log | tail -n 20

# View alerts sent
grep "health alert" bot.log | tail -n 10

# Check scheduler status
grep "APScheduler" bot.log | tail -n 20
```

### Manual Diagnostic Run

```python
from system_diagnostics import run_full_health_check
import asyncio

# Run diagnostics
health = asyncio.run(run_full_health_check('/path/to/bot'))

# Print results
print(health['summary'])
for component, data in health['components'].items():
    print(f"{component}: {data['status']}")
    if data['issues']:
        for issue in data['issues']:
            print(f"  - {issue['problem']}")
```

---

## 🎯 Success Criteria

- [x] All 6 monitors running on schedule
- [x] Alerts show ROOT CAUSE, not just symptom
- [x] Alerts include exact error from logs
- [x] Alerts include code location (file + line)
- [x] Alerts include fix suggestions
- [x] Alerts include debug commands
- [x] /health command works on-demand
- [x] All messages formatted for copy-paste to Copilot
- [x] User can fix issues without SSH access

---

## 🚀 Future Enhancements

Potential additions:
- 📧 Email alerts for critical issues
- 📈 Health history tracking
- 🤖 Auto-fix for common issues
- 📊 Health dashboard endpoint
- 🔔 Configurable alert thresholds
- 📱 Push notifications

---

## 📄 Files Changed

- **New:** `system_diagnostics.py` (605 lines) - Core diagnostic engine
- **New:** `diagnostic_messages.py` (365 lines) - Alert formatting
- **New:** `test_health_monitoring.py` (175 lines) - Test suite
- **Modified:** `bot.py` - Added /health command + 6 scheduler jobs
- **Modified:** `.gitignore` - Added bot.log

---

## ✅ Verification

To verify the implementation:

1. **Run tests:** `python3 test_health_monitoring.py`
2. **Check command:** Send `/health` in Telegram
3. **Trigger alert:** Delete journal file and wait 6 hours
4. **Verify logs:** `tail -f bot.log | grep health`

---

## 🎉 Summary

This PR delivers a comprehensive **intelligent health monitoring system** with:

✅ **24/7 monitoring** of all critical components  
✅ **Root cause analysis** instead of just symptoms  
✅ **Actionable fixes** with exact commands  
✅ **Copy-paste friendly** alerts for Copilot  
✅ **Zero manual investigation** required  

Users can now receive detailed error reports via Telegram and get instant fixes by forwarding to Copilot Chat! 🚀
