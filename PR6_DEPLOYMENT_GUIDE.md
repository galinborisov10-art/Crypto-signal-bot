# PR #6: Auto Signal Scheduler - Deployment Guide

## 📋 Pre-Deployment Checklist

✅ **Code Review**
- [x] All tests passing
- [x] No syntax errors
- [x] Code review completed
- [x] Follows existing patterns

✅ **Implementation Complete**
- [x] `auto_signal_job()` function created (200+ lines)
- [x] 4 scheduler jobs configured (1H, 2H, 4H, 1D)
- [x] Help text updated
- [x] Validation tests added

✅ **Files Modified**
- `bot.py` (+256 lines, -1 line)
- `test_pr6_auto_signals.py` (+132 lines, new file)

---

## 🚀 Deployment Steps

### 1. Deploy Code
```bash
# Pull latest changes
git pull origin copilot/add-2h-timeframe-scheduler

# Or merge PR #6 to main and deploy
git checkout main
git merge copilot/add-2h-timeframe-scheduler
git push origin main
```

### 2. Restart Bot
```bash
# Stop current instance
pkill -f bot.py

# Start new instance
python3 bot.py
# OR if using systemd:
sudo systemctl restart crypto-signal-bot
```

### 3. Verify Scheduler Registration

**Check logs for:**
```
✅ Auto signal 1H scheduled (every hour at :05)
✅ Auto signal 2H scheduled (every 2 hours at :07)  ← NEW!
✅ Auto signal 4H scheduled (every 4 hours at :10)
✅ Auto signal 1D scheduled (daily at 09:15 UTC)
✅ APScheduler стартиран: ... + 🤖 AUTO SIGNALS (1H, 2H, 4H, 1D)
```

### 4. Wait for First Signals

**Expected first signals:**
- **Next hour :05** → 1H signal (e.g., if now is 14:30, wait until 15:05)
- **Next even hour :07** → 2H signal (e.g., 16:07, 18:07, 20:07)
- **Next 4-hour mark :10** → 4H signal (e.g., 16:10, 20:10, 00:10)
- **Tomorrow 09:15 UTC** → 1D signal

### 5. Verify Signal Format

**Expected message format:**
```
🤖 АВТОМАТИЧЕН СИГНАЛ - [TIMEFRAME]

[Standard ICT signal with all components]
```

**Signal should include:**
- Source badge: "🤖 АВТОМАТИЧЕН"
- Timeframe label (1H, 2H, 4H, or 1D)
- All ICT components (OBs, FVGs, S/R, etc.)
- Chart visualization (if available)

---

## 🧪 Testing Checklist

### After Deployment:

- [ ] Bot starts without errors
- [ ] Scheduler logs show 4 auto signal jobs registered
- [ ] Logs mention "AUTO SIGNALS (1H, 2H, 4H, 1D)"
- [ ] First 1H signal received at next :05 mark
- [ ] First 2H signal received at next even hour :07 mark
- [ ] Signal has "🤖 АВТОМАТИЧЕН" label
- [ ] Signal includes chart
- [ ] Signal recorded to stats database
- [ ] High confidence signals logged to ML journal

### Help Command Test:

```
/help
```

**Should show:**
```
10. Автоматични сигнали:
/alerts - Вкл/Изкл
/alerts 30 - Промени интервала на 30 мин

📊 Auto timeframes: 1H (hourly), 2H (every 2h), 4H (every 4h), 1D (daily)
```

---

## 📊 Expected Schedule

### Hourly Pattern:
```
Time  | 1H | 2H | 4H | 1D | Notes
------|----|----|----|----|------------------
00:05 | ✓  |    |    |    | Every hour
00:07 |    | ✓  |    |    | Every 2 hours
00:10 |    |    | ✓  |    | Every 4 hours
01:05 | ✓  |    |    |    |
02:05 | ✓  |    |    |    |
02:07 |    | ✓  |    |    |
03:05 | ✓  |    |    |    |
04:05 | ✓  |    |    |    |
04:07 |    | ✓  |    |    |
04:10 |    |    | ✓  |    |
05:05 | ✓  |    |    |    |
...
09:15 |    |    |    | ✓  | Once daily
```

**Perfect stagger - no overlaps!**

---

## 🔧 Monitoring

### Key Metrics to Watch:

1. **Scheduler Health**
   - All 4 jobs registered on startup
   - Jobs execute at correct times
   - No errors in job execution

2. **Signal Quality**
   - Signals use ICT engine
   - Proper deduplication (60-min cooldown)
   - Top 3 signals by confidence sent
   - Charts generated successfully

3. **Resource Usage**
   - Memory cleanup after each job
   - No memory leaks
   - API rate limits respected

### Log Patterns to Monitor:

**Success:**
```
🤖 Running auto signal job for 1H
📤 Sending 3 auto signal(s) for 1H
✅ Auto signal sent for BTCUSDT (1H)
✅ Chart sent for auto signal BTCUSDT
📊 AUTO-SIGNAL recorded to stats (ID: ...)
✅ Auto signal job complete for 1H. Sent 3 signals.
```

**No Signals:**
```
🤖 Running auto signal job for 2H
⚠️ No signals for 2H (or all already sent)
```

**Errors (to investigate):**
```
❌ Auto signal analysis error for BTCUSDT 2h: ...
❌ Failed to send auto signal message for ETHUSDT: ...
❌ Auto signal job error for 4h: ...
```

---

## 🎯 Success Criteria

### After 24 Hours:

- [ ] Bot running without crashes
- [ ] 24 x 1H signals sent (hourly)
- [ ] 12 x 2H signals sent (every 2 hours) ← **NEW!**
- [ ] 6 x 4H signals sent (every 4 hours)
- [ ] 1 x 1D signal sent (daily at 09:15)
- [ ] All signals have proper format
- [ ] No scheduler conflicts or overlaps
- [ ] No memory issues
- [ ] Stats and ML journal updated

---

## 🚨 Rollback Plan

If issues occur:

```bash
# Revert to previous version
git revert HEAD~3  # Revert last 3 commits (test fix, test add, main implementation)
git push origin copilot/add-2h-timeframe-scheduler

# OR checkout previous working commit
git checkout f8ff88c  # Before PR #6 changes
git push -f origin copilot/add-2h-timeframe-scheduler

# Restart bot
sudo systemctl restart crypto-signal-bot
```

**Rollback removes:**
- Auto signal scheduler jobs
- `auto_signal_job()` function
- Auto timeframes from help text

**User impact:**
- Returns to manual `/signal` commands only
- No auto signals at scheduled times

---

## 📞 Support

**If you encounter issues:**

1. Check bot logs: `tail -f bot.log`
2. Check scheduler status in logs
3. Verify environment variables (especially OWNER_CHAT_ID)
4. Test manually: `/signal BTCUSDT 2h`
5. Run validation test: `python3 test_pr6_auto_signals.py`

---

## 🎉 Post-Deployment

### After successful deployment:

1. **Monitor first signals** (wait for :05, :07, :10, 09:15 marks)
2. **Verify signal quality** (ICT components, confidence scores)
3. **Check performance** (memory usage, API calls)
4. **Update documentation** if needed
5. **Mark PR #6 as complete** ✅

---

**Deployment prepared by:** GitHub Copilot  
**Date:** 2026-01-13  
**PR:** #6 - Add 2H Timeframe to Auto Scheduler  
**Status:** ✅ READY FOR PRODUCTION
