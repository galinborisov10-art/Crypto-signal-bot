# Diagnostic Control Panel - Quick Reference

## 🚀 Quick Start

### Enable Diagnostic Mode
```bash
# Add to .env file
DIAGNOSTIC_MODE=true
```

### Access Diagnostics
1. Open Telegram bot
2. Click **🛠 Diagnostics**
3. Choose diagnostic action

## 📋 Quick Commands

### Run Quick Check (Telegram)
```
1. Click "🛠 Diagnostics"
2. Click "🔍 Quick Check"
3. View report
```

### Run Quick Check (CLI)
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

## 🔍 Quick Check Tests

| # | Test | Severity | Group |
|---|------|----------|-------|
| 1 | Logger Configuration | LOW | Core |
| 2 | Critical Imports | HIGH | Core |
| 3 | Signal Schema | MED | Core |
| 4 | NaN Detection | MED | Core |
| 5 | Duplicate Guard | MED | Core |
| 6 | MTF Timeframes Available | HIGH | MTF Data |
| 7 | HTF Components Storage | MED | MTF Data |
| 8 | Klines Data Freshness | MED | MTF Data |
| 9 | Price Data Sanity | HIGH | MTF Data |
| 10 | Signal Required Fields | HIGH | Signal Schema |
| 11 | Cache Write/Read Test | MED | Signal Schema |
| 12 | Signal Type Validation | LOW | Signal Schema |
| 13 | Memory Usage | MED | Runtime Health |
| 14 | Response Time Test | LOW | Runtime Health |
| 15 | Exception Rate | MED | Runtime Health |
| 16 | Job Queue Health | LOW | Runtime Health |
| 17 | Binance API Reachable | HIGH | External |
| 18 | Telegram API Responsive | MED | External |
| 19 | File System Access | MED | External |
| 20 | Log File Writeable | LOW | External |

**Total:** 20 checks (Phase 2A expanded from 5)

## 🛡️ DIAGNOSTIC_MODE Behavior

| Operation | Normal Mode | DIAGNOSTIC_MODE |
|-----------|-------------|-----------------|
| User signals | ✅ Sent | ❌ Blocked |
| Admin messages | ✅ Sent | ✅ Sent (prefixed) |
| Alerts | ✅ Sent | ❌ Blocked |
| Trading | ✅ Executed | ❌ Blocked |
| Diagnostics | ✅ Available | ✅ Available |

## 🔐 Access Control

- **Diagnostic Menu:** Admin only (OWNER_CHAT_ID)
- **Quick Check:** Admin only
- **DIAGNOSTIC_MODE:** Affects all users

## 📊 Report Interpretation

### Status Codes
- **PASS** ✅ - Check passed
- **WARN** ⚠️ - Warning, review recommended
- **FAIL** ❌ - Failure, action required

### Severity Levels
- **HIGH** 🔴 - Critical issue, immediate action
- **MED** 🟡 - Important, address soon
- **LOW** 🟢 - Informational, no urgency

## 🐛 Common Issues

### "Admin only" error
- **Cause:** Not admin user
- **Fix:** Use admin account

### Missing modules error
- **Cause:** Dependencies not installed
- **Fix:** `pip3 install -r requirements.txt`

### DIAGNOSTIC_MODE not working
- **Cause:** .env not loaded
- **Fix:** Restart bot

## 🔧 Maintenance

### Daily
- Review Quick Check results
- Monitor startup diagnostics

### Weekly
- Check for new warnings
- Review diagnostic logs

### Monthly
- Update dependencies
- Review security

## 📞 Quick Help

```
/help           - Bot help
🛠 Diagnostics  - Open diagnostic menu
🔍 Quick Check  - Run 20 diagnostic tests
🔙 Main Menu    - Return to main menu
```

---
**Version:** 2.0.0 (Phase 2A) | **Updated:** 2026-01-30 | **Tests:** 20
