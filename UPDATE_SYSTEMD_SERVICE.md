# 🔧 Update Systemd Service File on Server

## ⚠️ IMPORTANT: One-Time Manual Update Required

After merging this PR, you need to manually update the systemd service file on the server **ONCE** to apply the new configuration.

## 📋 Steps to Update

### 1. Connect to Server
```bash
ssh root@YOUR_SERVER_IP
```

### 2. Navigate to Bot Directory
```bash
cd /root/Crypto-signal-bot
```

### 3. Pull Latest Changes (if not done automatically)
```bash
git pull origin main
```

### 4. Copy Updated Service File
```bash
# Backup current service file
cp /etc/systemd/system/crypto-bot.service /etc/systemd/system/crypto-bot.service.backup

# Copy new service file from repo
cp /root/Crypto-signal-bot/crypto-signal-bot.service /etc/systemd/system/crypto-bot.service
```

### 5. Reload Systemd and Restart Bot
```bash
# Reload systemd to read new configuration
systemctl daemon-reload

# Stop bot completely
systemctl stop crypto-bot

# Kill any remaining processes
pkill -9 -f "python.*bot.py" || true
sleep 2

# Start bot with new configuration
systemctl start crypto-bot
```

### 6. Verify Bot is Running
```bash
# Check service status
systemctl status crypto-bot

# Check bot process
ps aux | grep bot.py | grep -v grep

# View recent logs
journalctl -u crypto-bot -n 20
```

### 7. Test in Telegram
```
/version
```

You should see:
- ✅ Recent "Bot Process Started" timestamp
- ✅ Low uptime (few minutes)
- ✅ Bot responds normally to all commands

## 🔍 What Changed in Service File

### New Environment Variables
```ini
Environment="PYTHONDONTWRITEBYTECODE=1"  # Prevents .pyc creation
Environment="PYTHONUNBUFFERED=1"         # Unbuffered output
```

### Pre-Start Cleanup
```ini
ExecStartPre=/bin/sh -c 'pkill -9 -f "python.*bot.py" || true'
ExecStartPre=/bin/sleep 1
```

### Improved Shutdown
```ini
KillMode=mixed            # Kill process group
KillSignal=SIGTERM        # Graceful shutdown
TimeoutStopSec=10         # Max stop time
```

## ✅ Verification

After update, deployments will:
1. ✅ Stop bot service first (not restart)
2. ✅ Kill all Python bot processes
3. ✅ Reload systemd configuration
4. ✅ Start bot with fresh code
5. ✅ Verify process PID and start time
6. ✅ Show process start time in `/version`

## 🚨 Troubleshooting

### If bot doesn't start after update:
```bash
# Check for syntax errors in service file
systemctl status crypto-bot

# View detailed logs
journalctl -u crypto-bot -n 50

# Test manually
cd /root/Crypto-signal-bot
source venv/bin/activate
python bot.py
```

### If old service file was not replaced:
```bash
# Verify service file location
ls -la /etc/systemd/system/crypto-bot.service

# Compare with repo version
diff /etc/systemd/system/crypto-bot.service /root/Crypto-signal-bot/crypto-signal-bot.service

# If different, copy again
cp /root/Crypto-signal-bot/crypto-signal-bot.service /etc/systemd/system/crypto-bot.service
systemctl daemon-reload
systemctl restart crypto-bot
```

## 📝 After This Update

Once this one-time manual update is complete:
- ✅ All future deployments will work automatically
- ✅ Bot version will always sync correctly
- ✅ No more stale Python cache issues
- ✅ Clean process restarts every time

## 🎯 Why This Manual Step is Needed

The GitHub Actions deployment script:
1. Updates files in `/root/Crypto-signal-bot/`
2. Restarts the `crypto-bot` service

BUT it doesn't copy the service file to `/etc/systemd/system/` because:
- That requires modifying systemd
- The service file path is outside the repo directory
- We need to do it manually once

After this one-time update, the deployment script will use `systemctl daemon-reload` to pick up any future changes automatically.

---

**Status**: 🟡 Waiting for manual server update  
**Priority**: High - Required for version sync fix to work  
**Estimated Time**: 2-3 minutes
