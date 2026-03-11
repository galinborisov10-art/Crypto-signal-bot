# Changelog - 2026-03-11

## 🔧 Critical Fixes

### Rollback to Stable Engine
- **Commit:** 17daa62 (Feb 14, 2026)
- **Reason:** Engine became unstable after Feb 14
- **Action:** Rollback `ict_signal_engine.py` only
- **Result:** V2 code preserved, stable engine restored

### Duplicate Process Prevention
- **Problem:** Multiple bot instances running simultaneously
- **Solution:** 
  - Added fcntl file lock (`/tmp/crypto_bot.lock`)
  - Systemd `ExecStartPre` removes stale locks
  - Removed old `crypto-bot.service`
- **Result:** Single instance guaranteed

### Service Configuration
- **Active service:** `crypto-signal-bot.service`
- **Features:**
  - Single instance enforcement
  - Memory limit: 1G
  - Auto-restart on failure
  - Journal logging

## ✅ Verification
- 12 consecutive process checks: ✅ PASS
- Signal generation: ✅ ACTIVE
- Memory usage: 228.7M / 1G ✅ STABLE
