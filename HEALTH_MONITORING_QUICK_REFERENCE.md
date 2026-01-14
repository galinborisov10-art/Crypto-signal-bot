# 🏥 Health Monitoring Quick Reference

## 📱 Telegram Commands

### `/health` - Full System Diagnostic
Check health status of all bot components instantly.

**Example Response:**
```
🏥 SYSTEM HEALTH DIAGNOSTIC
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 TRADING JOURNAL: ✅ HEALTHY
🤖 ML MODEL: ⚠️ WARNING  
📊 DAILY REPORTS: ✅ HEALTHY
⚙️ POSITION MONITOR: ✅ HEALTHY
⏰ SCHEDULER: ✅ HEALTHY
💾 DISK SPACE: ✅ HEALTHY

Overall: ✅ 5 OK, ⚠️ 1 WARNING, ❌ 0 CRITICAL
```

---

## 🔔 Automated Alerts

### When You'll Receive Alerts

You'll automatically receive Telegram alerts when:

1. **Trading Journal** issues detected (every 6h check)
2. **ML Model** not training (daily 10:00 check)
3. **Daily Reports** not sent (daily 09:00 check)
4. **Position Monitor** errors (hourly check)
5. **Scheduler** problems (every 12h check)
6. **Disk Space** critical (daily 02:00 check)

### Alert Example

```
🚨 JOURNAL HEALTH ALERT
📊 Status: ❌ CRITICAL

🔴 PROBLEM:
Journal not updated for 8.5 hours

🔍 ROOT CAUSE:
Auto-signal jobs are NOT running

💡 FIX:
Scheduler may have crashed. Check status.

🔧 DEBUG COMMANDS:
grep "auto_signal_job" bot.log | tail -n 20

📌 Copy this to Copilot for instant fix
```

---

## 🛠️ How to Use Alerts

### Option 1: Copy to Copilot (Recommended)

1. **Copy entire alert** from Telegram
2. **Open GitHub Copilot Chat**
3. **Paste alert** with: "Fix this issue"
4. Copilot will analyze and provide exact fix

### Option 2: Run Debug Commands

Each alert includes debug commands you can run:

```bash
# SSH into server
ssh user@server

# Navigate to bot directory
cd /root/Crypto-signal-bot

# Run suggested commands
grep "auto_signal_job" bot.log | tail -n 20
```

### Option 3: Send to Telegram `/task`

Forward the alert to your Telegram bot with:
```
/task Fix the journal health issue from the alert
```

---

## 📊 Health Status Meanings

| Status | Emoji | Meaning | Action Required |
|--------|-------|---------|-----------------|
| **HEALTHY** | ✅ | All good | None |
| **WARNING** | ⚠️ | Minor issue | Monitor |
| **CRITICAL** | ❌ | Urgent issue | Fix immediately |

---

## 🔍 Common Issues & Quick Fixes

### Issue: Journal Not Updating

**Symptoms:**
- Alert: "Journal not updated for X hours"
- Root Cause: Auto-signal jobs not running

**Quick Fix:**
```bash
# Restart bot
sudo systemctl restart crypto-bot

# Or manually
pkill -f bot.py
python3 bot.py
```

---

### Issue: ML Model Outdated

**Symptoms:**
- Alert: "ML model not trained for X days"
- Root Cause: Not enough completed trades

**Quick Fix:**
- **If < 50 trades:** Wait for more signals to complete
- **If > 50 trades:** Manually trigger training:
  ```
  /ml_train (in Telegram)
  ```

---

### Issue: Disk Space Low

**Symptoms:**
- Alert: "Disk space critically low: X% used"

**Quick Fix:**
```bash
# Find large files
du -sh /root/Crypto-signal-bot/* | sort -h

# Remove old logs
find /root/Crypto-signal-bot -name "*.log" -mtime +30 -delete

# Clean backups
rm /root/Crypto-signal-bot/backups/*.backup
```

---

### Issue: Daily Report Not Sent

**Symptoms:**
- Alert: "Daily report not sent in last 24 hours"

**Quick Fix:**
```bash
# Check scheduler logs
grep "Daily report" /root/Crypto-signal-bot/bot.log | tail -n 20

# Manually trigger report
# In Telegram: /dailyreport
```

---

### Issue: Scheduler Errors

**Symptoms:**
- Alert: "X scheduler errors in last 12 hours"

**Quick Fix:**
```bash
# Check scheduler status
grep "APScheduler" /root/Crypto-signal-bot/bot.log | tail -n 30

# Restart if needed
sudo systemctl restart crypto-bot
```

---

## 📅 Monitoring Schedule

| Monitor | Time (BG) | Time (UTC) | Frequency |
|---------|-----------|------------|-----------|
| Journal Health | Every 6h at :15 | Every 6h at :15 | 4x/day |
| ML Training | 12:00 | 10:00 | Daily |
| Daily Reports | 11:00 | 09:00 | Daily |
| Position Monitor | Every hour at :30 | Every hour at :30 | 24x/day |
| Scheduler Health | Every 12h at :45 | Every 12h at :45 | 2x/day |
| Disk Space | 04:00 | 02:00 | Daily |

---

## 🧪 Testing the System

### Trigger a Test Alert

1. **Stop auto-signals** (temporarily)
2. **Wait 6 hours**
3. Journal health monitor will detect issue
4. Alert will be sent to Telegram

### Manual Health Check

Run `/health` anytime to see current status.

---

## 📝 Logging

All health checks are logged to `bot.log`:

```bash
# View health check logs
grep "health check" /root/Crypto-signal-bot/bot.log

# View alerts sent
grep "health alert" /root/Crypto-signal-bot/bot.log

# Follow in real-time
tail -f /root/Crypto-signal-bot/bot.log | grep health
```

---

## 🚨 Emergency Procedures

### If Bot Crashes

1. **Check logs:**
   ```bash
   tail -n 100 /root/Crypto-signal-bot/bot.log
   ```

2. **Restart bot:**
   ```bash
   sudo systemctl restart crypto-bot
   ```

3. **Verify health:**
   Send `/health` in Telegram

### If Alerts Stop Coming

1. **Check bot is running:**
   ```bash
   ps aux | grep bot.py
   ```

2. **Check scheduler:**
   ```bash
   grep "APScheduler" /root/Crypto-signal-bot/bot.log | tail -n 20
   ```

3. **Manually run health check:**
   Send `/health` in Telegram

---

## 💡 Pro Tips

1. **Forward alerts to Copilot** - Fastest way to get fixes
2. **Run `/health` before deploying** - Catch issues early
3. **Check alerts after updates** - Ensure everything works
4. **Keep disk space > 20%** - Prevent emergency alerts
5. **Monitor ML training** - Ensure model stays current

---

## 📞 Support

If alerts are unclear or fixes don't work:

1. **Copy entire alert message**
2. **Send to Copilot Chat** with context
3. **Or create GitHub issue** with alert details

---

## 🎯 Success Metrics

You'll know the system is working when:

- ✅ You receive `/health` responses instantly
- ✅ Alerts arrive automatically when issues occur
- ✅ Each alert includes exact fix instructions
- ✅ You can fix issues without SSH access (via Copilot)
- ✅ No manual checking needed - system monitors itself

---

**Remember:** The goal is **zero manual investigation**. Every alert should give you everything needed to fix the issue! 🚀
