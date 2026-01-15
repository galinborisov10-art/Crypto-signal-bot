# PR #114: Testing Guide

## 🧪 How to Test the Implementation

This guide shows you how to manually test all the fixes implemented in PR #114.

---

## Prerequisites

1. The bot should be running
2. You have access to the Telegram bot
3. You have the required permissions (owner or approved user)

---

## Test 1: Quick Health Check

**Command:** `/quick_health`

**Expected Result:**
- Response in <5 seconds
- Shows:
  - ✅ File checks (Trading Journal, Signal Cache, ML Model)
  - ✅ Disk usage percentage
  - ✅ Log file size (if exists)
  - ✅ Bot uptime (if psutil available)
- Message in mixed Bulgarian/English
- Suggests `/health` for full diagnostic

**Example Output:**
```
🏥 БЪРЗА ПРОВЕРКА
━━━━━━━━━━━━━━━━━━━━━━━━
✅ Trading Journal (245.2KB)
✅ Signal Cache (0.2KB)
✅ ML Model (1.2MB)
✅ Disk: 78.5% used (15.4GB free)
ℹ️ Log: 45.2MB
ℹ️ Bot uptime: 12h 34m

━━━━━━━━━━━━━━━━━━━━━━━━
✅ Основни системи работят

За пълна диагностика: /health
Завършено в 14:23:45
```

---

## Test 2: Full Health Diagnostic

**Command:** `/health`

**Expected Result:**
- Shows progress: "🏥 СИСТЕМНА ДИАГНОСТИКА... Сканирам 12 компонента..."
- Completes within 90 seconds OR falls back to quick check
- Shows comprehensive report with:
  - All 12 components analyzed
  - Problems listed FIRST with full details
  - Healthy components listed in summary
  - Mixed Bulgarian/English format
  - Duration and timestamp

**Components Checked:**
1. Trading Signals
2. Backtests
3. ML Model
4. Daily Reports
5. Message Sending
6. Trading Journal
7. Scheduler
8. Position Monitor
9. Breaking News
10. Disk/System
11. Access Control
12. Real-Time Monitor (NEW)

**Example Output:**
```
🏥 СИСТЕМНА ДИАГНОСТИКА
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Завършено: 2026-01-15 14:23:45
Продължителност: 12.3s

✅ ВСИЧКИ СИСТЕМИ РАБОТЯТ (12/12)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✅ ЗДРАВИ КОМПОНЕНТИ (12/12):

✅ Trading Signals
✅ Backtests
✅ ML Model
...

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 ОБОБЩЕНИЕ:
  • Критични: 0
  • Предупреждения: 0
  • Здрави: 12

За бърза проверка: /quick_health
```

**If Problems Found:**
```
🏥 СИСТЕМНА ДИАГНОСТИКА
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Завършено: 2026-01-15 14:23:45
Продължителност: 15.8s

⚠️ ОТКРИТИ 2 ПРОБЛЕМА (10/12 OK)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

❌ ПРОБЛЕМ #1: REAL-TIME MONITOR
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Статус: CRITICAL

Проблем: Real-time monitor fails to start - AsyncIO scope error
Причина: asyncio not accessible in nested function scope
Решение: Use: loop = asyncio.get_running_loop()
          loop.create_task(...)

<code>cannot access free variable 'asyncio' where it is not...</code>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[... more problems ...]

✅ ЗДРАВИ КОМПОНЕНТИ (10/12):
✅ Trading Signals
✅ ML Model
...
```

---

## Test 3: Health Diagnostic Timeout

**How to Test:**
This is automatic - if the diagnostic takes longer than 90 seconds, it should automatically fall back to quick health check.

**Expected Result:**
- Progress message updated: "⚠️ Пълната диагностика отне повече от 90 секунди"
- Shows quick health check results instead
- Never hangs indefinitely

---

## Test 4: Long Message Chunking

**How to Test:**
If the health report is very long (>4000 characters), it should be split into multiple messages.

**Expected Result:**
- Multiple messages sent (if needed)
- 0.5 second delay between messages
- All information preserved

---

## Test 5: Real-Time Monitor Fix

**How to Test:**
Check the bot logs after restart:

```bash
tail -f bot.log | grep -i "real-time"
```

**Expected Result:**
```
✅ Real-time Position Monitor STARTED (30s interval)
✅ 80% TP alerts and WIN/LOSS notifications enabled
```

**NOT:**
```
❌ Failed to start real-time monitor: cannot access free variable 'asyncio'
```

---

## Test 6: Rate Limiting

**Test 6a: /health rate limit**
- Send `/health` command 6 times in 1 minute

**Expected Result:**
- First 5 commands work
- 6th command shows rate limit message

**Test 6b: /quick_health rate limit**
- Send `/quick_health` command 11 times in 1 minute

**Expected Result:**
- First 10 commands work
- 11th command shows rate limit message

---

## Test 7: Access Control

**How to Test:**
Try commands from unauthorized user (if you have test account)

**Expected Result:**
- Both `/health` and `/quick_health` should require access
- Shows access denied message if not authorized

---

## Test 8: Error Detection

**How to Test:**
1. Check if real-time monitor error was detected (if it existed before)
2. Run `/health`
3. Look for "Real-Time Monitor" component

**Expected Result:**
If the asyncio error existed before the fix:
- Should be detected in health report
- Should show exact error message
- Should show file/line location
- Should show fix suggestion

After applying the fix:
- Real-Time Monitor should show as HEALTHY
- No asyncio errors in logs

---

## Automated Tests

You can also run the automated test suite:

```bash
cd /home/runner/work/Crypto-signal-bot/Crypto-signal-bot

# Run PR #114 specific tests
python3 test_pr114_health_fix.py

# Run existing health monitoring tests
python3 test_health_monitoring.py
```

**Expected Result:**
```
============================================================
TEST SUMMARY
============================================================
✅ PASS - Imports
✅ PASS - Quick Health Check
✅ PASS - Real-Time Monitor Diagnostic
✅ PASS - Full Health Check
✅ PASS - AsyncIO Scope Fix

============================================================
TOTAL: 5/5 tests passed
============================================================
```

---

## Verification Checklist

After testing, verify:

- [ ] `/quick_health` responds in <5 seconds
- [ ] `/health` completes within 90 seconds
- [ ] Health report shows 12 components
- [ ] Problems (if any) show root cause and fix
- [ ] Messages use mixed Bulgarian/English
- [ ] Real-time monitor starts without asyncio error
- [ ] Rate limiting works (5 calls/min for /health, 10 for /quick_health)
- [ ] Long messages are chunked properly
- [ ] No indefinite hangs
- [ ] Bot logs show "Real-time Position Monitor STARTED"

---

## Troubleshooting

### Issue: `/health` times out after 90s

**Solution:** This is expected behavior - it should fall back to quick check. If you want to see the full report, investigate why the diagnostic is taking so long:

```bash
grep "Health check" bot.log | tail -20
```

### Issue: `/quick_health` not found

**Solution:** Make sure the command handler is registered:

```bash
grep "quick_health" bot.py | grep "add_handler"
```

Should show:
```python
app.add_handler(CommandHandler("quick_health", quick_health_cmd))
```

### Issue: Real-time monitor still fails

**Solution:** Check the exact error in logs:

```bash
grep "Failed to start real-time monitor" bot.log | tail -1
```

Verify the fix was applied:

```bash
grep -A 2 "get_running_loop" bot.py
```

Should show:
```python
loop = asyncio.get_running_loop()
monitor_task = loop.create_task(real_time_monitor_global.start_monitoring())
```

---

## Success Criteria

✅ All tests pass  
✅ No indefinite hangs  
✅ Real-time monitor starts successfully  
✅ 12 components analyzed  
✅ Quick health check works  
✅ Mixed BG/EN format  
✅ Root cause analysis shown  

---

## Support

If any test fails or behaves unexpectedly:

1. Check bot.log for errors
2. Run automated tests: `python3 test_pr114_health_fix.py`
3. Verify all files compile: `python3 -m py_compile bot.py system_diagnostics.py diagnostic_messages.py`
4. Review PR114_IMPLEMENTATION_SUMMARY.md for detailed implementation info

---

**Ready to test! 🚀**
