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

| Test | Severity | Checks |
|------|----------|--------|
| Logger Configuration | LOW | Handler count, log level |
| Critical Imports | HIGH | pandas, numpy, requests, telegram, ta |
| Signal Schema | MED | ICTSignalEngine structure |
| NaN Detection | MED | Indicator calculations |
| Duplicate Guard | MED | Cache manager presence |

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
🔍 Quick Check  - Run 5 core tests
🔙 Main Menu    - Return to main menu
```

---
**Version:** 1.0.0 | **Updated:** 2026-01-30
