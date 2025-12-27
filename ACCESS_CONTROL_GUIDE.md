# Access Control System Guide

## 📋 Overview

The Crypto Signal Bot now includes a comprehensive **Access Control System** that restricts command access to a whitelist of authorized users. This prevents unauthorized users from accessing bot functionality while maintaining a friendly user experience.

---

## 🔒 Key Features

### ✅ User Whitelist Enforcement
- Only users in the `ALLOWED_USERS` whitelist can execute commands
- Owner (first user in whitelist) has full access
- Easy user approval/removal system

### 🚫 Unauthorized Access Blocking
- Unauthorized users receive clear denial messages
- All unauthorized attempts are logged
- Owner receives real-time notifications

### 📊 Access Logging
- All access attempts (authorized and unauthorized) are logged
- Detailed information: user ID, username, command, timestamp
- Separate log levels for authorized (INFO) and unauthorized (WARNING)

### 🔔 Owner Notifications
- Real-time alerts when unauthorized users attempt access
- Includes user details, command attempted, and timestamp
- Shows approval command for quick authorization

---

## 🛠️ Configuration

### ALLOWED_USERS Whitelist

The whitelist is configured in `bot.py`:

```python
# Default configuration (Owner only)
OWNER_CHAT_ID = 7003238836
ALLOWED_USERS = {OWNER_CHAT_ID}
```

### Adding Users to Whitelist

#### Method 1: Using Bot Commands (Recommended)
Owner can approve users directly from Telegram:

```bash
/approve 123456789  # Approve user with ID 123456789
/users              # List all authorized users
/block 123456789    # Remove user from whitelist
```

#### Method 2: Environment Variable
Set the `ALLOWED_USERS` environment variable (comma-separated):

```bash
export ALLOWED_USERS="7003238836,245016734,123456789"
```

#### Method 3: Manual File Edit
Edit `allowed_users.json`:

```json
[
  7003238836,
  245016734,
  123456789
]
```

**⚠️ Important:** User IDs are integers, not strings!

---

## 🔐 How It Works

### The @require_access Decorator

All protected commands use the `@require_access()` decorator:

```python
@require_access()
@rate_limited(calls=5, period=60)
async def signal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate trading signal - PROTECTED"""
    # Command logic here...
```

**Decorator Order:** `@require_access()` must be placed **ABOVE** `@rate_limited()` to check access first.

### Authorization Flow

1. **User sends command** → Bot receives command
2. **Access check** → `@require_access()` verifies user ID
3. **If authorized** → Command executes normally
4. **If unauthorized** → 
   - User receives "ACCESS DENIED" message
   - Owner receives notification
   - Command is blocked
   - Attempt is logged

---

## 📝 Protected Commands

### Critical Commands (Fully Protected)
- `/signal` - Trading signals
- `/market` - Market analysis
- `/ict` - ICT analysis
- `/settings` - User settings
- `/fund` - Fundamental analysis
- `/alerts` - Alert settings
- `/stats` - Statistics
- `/journal` - Trading journal
- `/backtest` - Backtesting
- `/risk` - Risk management

### Admin Commands (Fully Protected)
- `/restart` - Bot restart
- `/update` - Bot update
- `/test` - System test
- `/approve` - Approve user
- `/block` - Block user
- `/users` - List users

### Report Commands (Fully Protected)
- `/daily_report` - Daily report
- `/weekly_report` - Weekly report
- `/monthly_report` - Monthly report
- `/reports` - All reports

### Public Commands (Informative for Unauthorized)
- `/start` - Shows welcome message or access info
- `/help` - Shows help or access requirements

---

## 🔔 Owner Alerts

When an unauthorized user attempts to use a command, the owner receives:

```
⚠️ UNAUTHORIZED ACCESS ATTEMPT

👤 User: @hacker123
🆔 User ID: 987654321
💬 Chat ID: 987654321
⚡ Command: signal_cmd

🕐 Time: 2025-12-27 14:30:00

This user is not in the whitelist.
```

Owner can then decide to:
- Approve: `/approve 987654321`
- Ignore: No action needed
- Block (if spamming): Already blocked automatically

---

## 📊 Logging System

### Log Levels

**Authorized Access (INFO):**
```
✅ Authorized access: @user123 (ID: 123456789) -> signal_cmd
```

**Unauthorized Attempt (WARNING):**
```
⛔ UNAUTHORIZED ACCESS ATTEMPT: User: @hacker (ID: 999) | Command: signal_cmd | Chat: 999
```

**Owner Notification (INFO):**
```
📨 Sent unauthorized access alert to owner (ID: 7003238836)
```

### Log File Location
- Console output: Real-time logging
- File: `bot.log` (if configured)
- Separate access log: `bot_access.log` (optional enhancement)

---

## 🚀 Usage Examples

### Example 1: Authorized User
```
User: /signal BTC
Bot: [Generates signal normally]
Log: ✅ Authorized access: @john (ID: 123456789) -> signal_cmd
```

### Example 2: Unauthorized User
```
User: /signal BTC
Bot: ⛔ ACCESS DENIED
     You are not authorized to use this bot.
     If you believe this is an error, please contact the bot owner.

Owner receives:
     ⚠️ UNAUTHORIZED ACCESS ATTEMPT
     👤 User: @jane (ID: 987654321)
     ⚡ Command: signal_cmd
     ...

Log: ⛔ UNAUTHORIZED ACCESS ATTEMPT: User: @jane (ID: 987654321) | Command: signal_cmd
```

### Example 3: Public Command (Unauthorized)
```
User: /start
Bot: 👋 Welcome to Crypto Signal Bot!
     
     🔒 This is a private trading bot.
     Access is restricted to authorized users only.
     
     📧 Your user ID is 987654321
     The owner can approve you with: /approve 987654321

Log: ⚠️ Unauthorized /start from @jane (ID: 987654321)
```

---

## 🛡️ Security Best Practices

### 1. Never Commit Real User IDs to Public Repos
```bash
# Use environment variables in production
export ALLOWED_USERS="7003238836,245016734"
```

### 2. Use .env File (Gitignored)
```bash
# .env
ALLOWED_USERS=7003238836,245016734,123456789
```

### 3. Regular User Audit
```bash
# Review authorized users monthly
/users

# Remove users who no longer need access
/block 123456789
```

### 4. Monitor Unauthorized Attempts
- Check logs regularly for patterns
- Investigate repeated unauthorized attempts
- Block persistent attackers if needed

### 5. Keep Owner Alerts Enabled
- Always monitor owner notifications
- Quick response to suspicious activity
- Easy user approval workflow

---

## 🔧 Troubleshooting

### Problem: User Can't Access Bot

**Solution:**
1. Check if user is in `ALLOWED_USERS`:
   ```bash
   /users
   ```

2. Add user if not present:
   ```bash
   /approve USER_ID
   ```

3. Verify user ID is correct (must be integer)

4. Check `allowed_users.json` file integrity

---

### Problem: Owner Not Receiving Alerts

**Solution:**
1. Verify `OWNER_CHAT_ID` is set correctly
2. Check bot can send messages to owner
3. Review logs for notification errors:
   ```
   ❌ Failed to notify owner about unauthorized access: [error]
   ```

4. Test with `/test` command

---

### Problem: Authorized User Getting Denied

**Solution:**
1. Verify user ID matches exactly (no typos)
2. Reload `allowed_users.json`:
   ```bash
   /restart
   ```

3. Check user ID format (must be integer, not string)

4. Review logs for authorization check:
   ```
   ✅ Authorized access: @user (ID: XXX)
   ```

---

### Problem: All Users Getting Access Denied

**Solution:**
1. Check `ALLOWED_USERS` is not empty
2. Verify file loading:
   ```
   ✅ Заредени 3 разрешени потребители
   ```

3. Restart bot:
   ```bash
   /restart
   ```

4. Check environment variables

---

## 📈 Advanced Configuration

### Custom Allowed Users for Specific Commands

You can create command-specific whitelists:

```python
# Only these users can use ML commands
ML_USERS = {7003238836, 245016734}

@require_access(allowed_users=ML_USERS)
@rate_limited(calls=3, period=60)
async def ml_train_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ML training - restricted to ML users only"""
    # ...
```

### Multiple Owner Support

```python
OWNERS = {7003238836, 245016734}  # Multiple owners
ALLOWED_USERS = OWNERS.union({123456789, 987654321})  # Add regular users
```

### Time-Based Access

```python
from datetime import datetime, time

def require_access_time_based(start_hour=9, end_hour=17):
    """Only allow access during business hours"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update, context, *args, **kwargs):
            current_hour = datetime.now().hour
            if not (start_hour <= current_hour < end_hour):
                await update.message.reply_text("Bot only available 9 AM - 5 PM")
                return
            return await require_access()(func)(update, context, *args, **kwargs)
        return wrapper
    return decorator
```

---

## 📞 Support

**Questions or Issues?**

1. Check this guide first
2. Review logs for error messages
3. Test with `/test` command
4. Contact bot owner for access issues
5. Report bugs on GitHub: https://github.com/galinborisov10-art/Crypto-signal-bot

---

## 📜 Changelog

### Version 2.1.0 (2025-12-27)
- ✅ Added `@require_access()` decorator
- ✅ Applied to all command handlers
- ✅ Owner notification system
- ✅ Comprehensive logging
- ✅ Public commands show info for unauthorized users
- ✅ User approval/blocking commands
- ✅ File-based whitelist persistence

---

## 🎯 Summary

The Access Control System provides:
- **Security:** Only authorized users can access commands
- **Transparency:** All attempts logged and monitored
- **Flexibility:** Easy user management via commands or files
- **User-Friendly:** Clear messages for unauthorized users
- **Owner Control:** Real-time alerts and approval workflow

**Default Behavior:**
- ✅ Owner has full access
- ✅ Unauthorized users blocked
- ✅ Owner notified of attempts
- ✅ All activity logged

**Getting Started:**
1. Ensure your user ID is in `ALLOWED_USERS`
2. Use `/approve USER_ID` to add trusted users
3. Monitor owner notifications for unauthorized attempts
4. Review `/users` regularly to audit access

---

**🔒 Your bot is now secure and protected!**
