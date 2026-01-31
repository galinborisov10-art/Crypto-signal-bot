# Quick Start Guide: Replay Diagnostics

## 🚀 What is Replay Diagnostics?

Replay Diagnostics automatically captures signal snapshots and allows you to replay them later to detect regressions in your signal generation logic. This is your **deploy safety net** - it ensures your signal logic remains consistent across code changes.

## 📱 How to Use (Telegram)

### Step 1: Access Diagnostics Menu
From the bot's main menu:
```
🏠 Main Menu → 🛠 Diagnostics
```

### Step 2: Available Commands

#### 🎬 Replay Signals
**What it does:** Re-runs all cached signals and compares them with originals
**When to use:** After code changes, before deployment, or regular health checks

**Example output:**
```
🎬 Signal Replay Report

📊 Testing 5 cached signals...

1. ✅ BTCUSDT 15m - Match
2. ✅ ETHUSDT 1h - Match
3. ❌ BTCUSDT 5m - Regression
   └─ Changed: entry_delta
4. ✅ SOLUSDT 30m - Match
5. ✅ XRPUSDT 1h - Match

✅ Passed: 4
❌ Failed: 1
⚠️ Errors: 0

⚠️ Warning: 1 regression(s) detected!
```

#### 📈 Replay Report
**What it does:** Shows cache status and recent signals
**When to use:** To check what signals are available for replay

**Example output:**
```
📈 Replay Cache Status

Cached signals: 5/10
Storage: replay_cache.json

Recent Signals:
• BTCUSDT 15m - 2026-01-31T10:30
• ETHUSDT 1h - 2026-01-31T11:15
• BTCUSDT 5m - 2026-01-31T11:45
• SOLUSDT 30m - 2026-01-31T12:00
• XRPUSDT 1h - 2026-01-31T12:30
```

#### 🗑️ Clear Replay Cache
**What it does:** Clears all cached signals
**When to use:** To reset storage or free up space

**Example output:**
```
✅ Replay cache cleared
```

## 🔄 Automatic Signal Capture

Signals are **automatically captured** during generation:
- No manual action needed
- Happens in the background
- Doesn't slow down signal generation
- Stores last 10 signals (older ones are auto-removed)

## 🎯 Typical Workflow

### Before Code Deployment
```
1. 🎬 Replay Signals
   └─ Check: All signals should show "✅ Match"
   
2. If all match:
   ✅ Safe to deploy
   
3. If regression detected:
   ⚠️ Review code changes
   🔍 Investigate what changed
   🛠️ Fix the issue
   🔄 Repeat step 1
```

### Regular Health Checks
```
1. Weekly: Run "🎬 Replay Signals"
2. Check for unexpected regressions
3. Monitor signal consistency
```

### After Major Updates
```
1. Before update: Run "🎬 Replay Signals" (baseline)
2. Apply update
3. After update: Run "🎬 Replay Signals" (comparison)
4. Verify: Should match baseline
```

## 📊 Understanding Results

### ✅ Match
- Signal logic is stable
- Results are consistent
- Safe to continue

### ❌ Regression
- Signal logic changed
- Results differ from original
- Review code changes

**Common regression types:**
- `signal_type` - Signal changed from LONG to SHORT (or vice versa)
- `direction` - Direction changed
- `entry_delta` - Entry price changed > 0.01%
- `sl_delta` - Stop loss changed > 0.01%
- `tp_delta` - Take profit levels changed > 0.01%

### ⚠️ Replay Error
- Signal couldn't be replayed
- Possible data issue
- Review logs for details

## 🔐 Security

- **Admin-only:** Only bot owner can access replay features
- **Read-only:** Replay never modifies your signals or trading
- **Isolated:** Completely separate from live trading
- **Safe:** Failures never affect signal generation

## 💡 Tips

### Best Practices
1. ✅ Run replay checks before major deployments
2. ✅ Keep at least 5-10 signals cached for good coverage
3. ✅ Clear cache after fixing regressions to get fresh baseline
4. ✅ Run weekly health checks

### What to Do When Regression Detected
1. **Don't panic** - Trading is not affected
2. **Review code changes** - What changed recently?
3. **Check logs** - Look for the specific signal that regressed
4. **Investigate diffs** - What field changed and why?
5. **Fix or verify** - Either fix the bug or verify the change was intentional
6. **Re-test** - Run replay again after fix

### Storage Management
- **Automatic rotation:** When 11th signal arrives, oldest is removed
- **Storage size:** ~50KB per signal, ~500KB total max
- **Location:** `replay_cache.json` (not in git)
- **Cleanup:** Click "🗑️ Clear Replay Cache" anytime

## 🚫 Troubleshooting

### "No signals in cache yet"
**Solution:** Generate some signals first (use `/signal BTC` command)

### "Replay produced no signal"
**Cause:** Market conditions changed drastically since original signal
**Solution:** This is normal - not all replays produce signals

### "❌ Admin only"
**Cause:** Non-admin user trying to access replay features
**Solution:** Only bot owner (OWNER_CHAT_ID) can use replay diagnostics

## 📚 Learn More

For detailed technical documentation, see:
- `PHASE_2B_REPLAY_DIAGNOSTICS.md` - Full implementation guide
- `PHASE_2B_SUMMARY.md` - Technical summary
- `test_replay_diagnostics.py` - Test suite with examples

## ✨ Quick Reference

| Button | Action | When to Use |
|--------|--------|-------------|
| 🎬 Replay Signals | Run regression tests | Before deployment, regular checks |
| 📈 Replay Report | View cache status | Check what's cached |
| 🗑️ Clear Cache | Reset storage | After fixing regressions |

---

**Need help?** Contact bot owner or review documentation files.

**Status:** ✅ Ready to use!
