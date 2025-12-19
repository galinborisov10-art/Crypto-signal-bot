# 🔒 Security Guide - Crypto Signal Bot v2.0.0

**Last Updated:** 2025-12-19  
**Version:** 2.0.0 - Security Hardening Release

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Security Features](#security-features)
3. [Rate Limiting](#rate-limiting)
4. [Authentication System](#authentication-system)
5. [Admin Commands](#admin-commands)
6. [Token Encryption](#token-encryption)
7. [Security Monitoring](#security-monitoring)
8. [Best Practices](#best-practices)
9. [Incident Response](#incident-response)
10. [Troubleshooting](#troubleshooting)

---

## Overview

After the recent security incident (token compromise on 2025-12-17), we've implemented comprehensive security measures to protect the bot and prevent future attacks. This guide explains all security features and how to use them.

### What's New in v2.0.0

- 🛡️ **Rate Limiting:** 20 requests/minute, 100 requests/hour per user
- 🔐 **Authentication:** Blacklist/Whitelist system with admin controls
- 🔒 **Encrypted Token Storage:** Secure bot token encryption with cryptography
- 📊 **Security Monitoring:** Real-time threat detection and logging
- ⚠️ **Auto-ban:** Automatic ban after 3 rate limit violations

---

## Security Features

### 1. Rate Limiting

Prevents spam and DDoS attacks by limiting user requests.

**Limits:**
- **Per Minute:** 20 requests
- **Per Hour:** 100 requests
- **Auto-ban:** After 3 violations (60 minutes ban)

**How it works:**
- Each user request is tracked by user ID
- Old requests are automatically cleaned up
- Violations are logged in security monitor
- Banned users receive clear error messages

**Example:**
```
User sends 21 requests in 1 minute → Rate limit exceeded
User violates 3 times → Automatic 60-minute ban
```

### 2. Authentication System

Controls who can use the bot with admin, blacklist, and whitelist.

**Access Modes:**

**Public Mode (Default):**
- Everyone can use the bot
- Blacklisted users are blocked
- No whitelist required

**Whitelist Mode:**
- Only whitelisted users + admins can use
- Enable with `WHITELIST_MODE=true` in .env
- Add user IDs in `WHITELISTED_USER_IDS`

**Admin Access:**
- Admins always have full access
- Set via `ADMIN_USER_IDS` in .env
- Multiple admins supported (comma-separated)

### 3. Token Encryption

Protects the bot token from theft.

**Features:**
- Encrypts token using Fernet (AES-256)
- Stores encrypted token in `.bot_token_encrypted`
- Validates token with SHA-256 hash
- Automatic key generation (`.encryption_key`)
- Token rotation with backup support

**Security:**
- Encryption key: Read-only (chmod 400)
- Encrypted token: Read-only (chmod 400)
- Backups stored in `.token_backups/`

### 4. Security Monitoring

Tracks all security events and assesses threat levels.

**Event Types:**
- `RATE_LIMIT_EXCEEDED` - User exceeded rate limit
- `AUTO_BAN` - User auto-banned after violations
- `UNAUTHORIZED_ACCESS` - Blocked access attempt
- `USER_BLACKLISTED` - User added to blacklist
- `USER_UNBANNED` - User manually unbanned

**Threat Levels:**
- 🟢 **LOW:** < 20 events/hour (normal)
- 🟡 **MEDIUM:** 20-50 events/hour (elevated)
- 🟠 **HIGH:** 50-100 events/hour (critical attention)
- 🔴 **CRITICAL:** > 100 events/hour (under attack)

---

## Rate Limiting

### How Rate Limiting Works

The rate limiter tracks requests per user using sliding windows:

1. **Per-Minute Window:** Last 60 seconds
2. **Per-Hour Window:** Last 3600 seconds

When a user makes a request:
1. Check if user is banned → Deny if banned
2. Clean up old timestamps
3. Check minute limit (20) → Deny if exceeded
4. Check hour limit (100) → Deny if exceeded
5. Record request timestamp
6. Mark suspicious if limit exceeded

### Auto-ban System

**Trigger:** 3 rate limit violations  
**Duration:** 60 minutes (configurable)  
**Process:**
1. User exceeds rate limit → Violation #1
2. User exceeds again → Violation #2
3. User exceeds third time → **AUTO-BANNED** for 60 minutes

**Ban Expiration:**
- Bans expire automatically
- Users can be manually unbanned by admins
- Ban timer shown in error messages

### User Experience

**Normal User:**
```
/signal BTC
✅ Signal delivered
```

**Rate Limited User:**
```
/signal BTC
⚠️ Rate limit exceeded. Please try again later.
```

**Banned User:**
```
/signal BTC
🚫 You are temporarily banned for 45 minutes.
Reason: Rate limit violations
```

---

## Authentication System

### Admin Setup

**1. Set Admin User IDs:**

Edit `.env` file:
```bash
ADMIN_USER_IDS=123456789,987654321
```

Multiple admins supported (comma-separated).

**2. Get Your Telegram User ID:**

- Send `/start` to [@userinfobot](https://t.me/userinfobot)
- Your ID will be displayed
- Add to `ADMIN_USER_IDS`

**3. Restart Bot:**
```bash
python bot.py
```

### Blacklist System

Block malicious or abusive users.

**Add to Blacklist:**
```
/blacklist USER_ID [REASON]
```

**Example:**
```
/blacklist 123456789 Spam and abuse
✅ User 123456789 blacklisted.
Reason: Spam and abuse
```

**Remove from Blacklist:**
```
/unblacklist USER_ID
```

**Effects:**
- Blacklisted users cannot use any bot commands
- All requests are blocked immediately
- Admins cannot be blacklisted

### Whitelist Mode

Restrict bot to approved users only.

**Enable Whitelist Mode:**

Edit `.env`:
```bash
WHITELIST_MODE=true
WHITELISTED_USER_IDS=111111111,222222222,333333333
```

**Add User to Whitelist (Future Feature):**
```
/whitelist USER_ID
```

**How it Works:**
- Only whitelisted users + admins can use bot
- Non-whitelisted users get "Access denied" message
- Useful for private/premium bots

---

## Admin Commands

### Security Commands

#### `/blacklist USER_ID [REASON]`
Add user to blacklist.

**Usage:**
```
/blacklist 123456789 Spam
```

**Response:**
```
✅ User 123456789 blacklisted

Reason: Spam

This user can no longer use the bot.
```

---

#### `/unblacklist USER_ID`
Remove user from blacklist.

**Usage:**
```
/unblacklist 123456789
```

**Response:**
```
✅ User 123456789 removed from blacklist

This user can now use the bot again.
```

---

#### `/security_stats`
Show security statistics and threat level.

**Response:**
```
━━━━━━━━━━━━━━━━━━━━
🔒 SECURITY REPORT
━━━━━━━━━━━━━━━━━━━━

Threat Level: 🟢 LOW

Events (Last Hour): 3
Events (Last 24h): 45

Event Breakdown:
• RATE_LIMIT_EXCEEDED: 2
• USER_BLACKLISTED: 1

Authentication Stats:
• Admins: 2
• Blacklisted: 1
• Whitelisted: 0
• Whitelist Mode: OFF

━━━━━━━━━━━━━━━━━━━━
```

---

#### `/unban USER_ID`
Manually unban rate-limited user.

**Usage:**
```
/unban 123456789
```

**Response:**
```
✅ User 123456789 unbanned

Rate limit ban has been lifted.
```

---

#### `/version`
Show bot version with security features.

**Response:**
```
━━━━━━━━━━━━━━━━━━━━
🤖 ICT Signal Bot
━━━━━━━━━━━━━━━━━━━━

📦 Version: 2.0.0
📅 Release: 2025-12-19
🏷️ Codename: ICT Complete + Security

✨ Features:
• Complete ICT Signal Engine
• Fibonacci Analyzer
• LuxAlgo Combined Integration
• 13-Point Unified Output
• Security Hardening
• Rate Limiting
• Auto-deployment

🔒 Security:
• Encrypted token storage
• Rate limiting (20/min, 100/hour)
• Auto-ban on abuse (3 violations)
• Authentication system
• Blacklist/Whitelist support
• Security monitoring
• Threat level assessment

━━━━━━━━━━━━━━━━━━━━
```

---

## Token Encryption

### How It Works

The bot token is encrypted using industry-standard encryption:

1. **Encryption Key Generation:**
   - Fernet key generated (AES-256)
   - Stored in `.encryption_key` (read-only)
   - Key never committed to git

2. **Token Storage:**
   - Token encrypted with Fernet cipher
   - Stored in `.bot_token_encrypted`
   - Hash stored in `.bot_token_hash` for validation

3. **Token Retrieval:**
   - Primary: From `TELEGRAM_BOT_TOKEN` env variable
   - Fallback: Decrypt from `.bot_token_encrypted`
   - Validation: Check against stored hash

### Token Rotation

If your token is compromised:

1. **Get New Token:**
   - Contact @BotFather on Telegram
   - Generate new token

2. **Update Environment:**
   ```bash
   export TELEGRAM_BOT_TOKEN="new_token_here"
   ```

3. **Or Use Rotation (Future Feature):**
   ```python
   from security.token_manager import token_manager
   token_manager.rotate_token("new_token_here")
   ```

### Security Files

**Generated Files:**
- `.encryption_key` - Fernet encryption key (chmod 400)
- `.bot_token_encrypted` - Encrypted token (chmod 400)
- `.bot_token_hash` - SHA-256 hash for validation (chmod 400)
- `.token_backups/` - Old token backups

**⚠️ NEVER commit these files to git!** Already in `.gitignore`.

---

## Security Monitoring

### Event Logging

All security events are logged with:
- Timestamp
- Event type
- User ID
- Details

**Example Log:**
```
🔒 Security Event: RATE_LIMIT_EXCEEDED | User 123456789 | signal_cmd
⚠️ User 123456789 exceeded minute limit: 21/20
🔒 User 123456789 AUTO-BANNED after 3 violations
```

### Threat Assessment

Automatically assesses threat level based on event frequency:

**Algorithm:**
```python
events_last_hour = count_recent_events(3600)

if events_last_hour > 100:
    threat_level = "CRITICAL"
elif events_last_hour > 50:
    threat_level = "HIGH"
elif events_last_hour > 20:
    threat_level = "MEDIUM"
else:
    threat_level = "LOW"
```

**When Threat Level Changes:**
- Logged to console
- Future: Admin notifications via Telegram

---

## Best Practices

### 1. Environment Security

**DO:**
- ✅ Use `.env` file for secrets
- ✅ Set `ADMIN_USER_IDS` properly
- ✅ Restrict file permissions (chmod 400)
- ✅ Keep `.env` in `.gitignore`

**DON'T:**
- ❌ Hardcode tokens in code
- ❌ Commit `.env` to git
- ❌ Share encryption keys
- ❌ Use same token across environments

### 2. Admin Access

**DO:**
- ✅ Use multiple admin IDs for redundancy
- ✅ Regularly review admin list
- ✅ Monitor security logs

**DON'T:**
- ❌ Give admin access to untrusted users
- ❌ Use bot owner ID as only admin
- ❌ Ignore security reports

### 3. Rate Limiting

**DO:**
- ✅ Monitor rate limit violations
- ✅ Investigate repeated offenders
- ✅ Adjust limits if needed (config)

**DON'T:**
- ❌ Disable rate limiting
- ❌ Set limits too high
- ❌ Ignore auto-ban notifications

### 4. Monitoring

**DO:**
- ✅ Check `/security_stats` daily
- ✅ Investigate HIGH/CRITICAL threat levels
- ✅ Review blacklist regularly

**DON'T:**
- ❌ Ignore security alerts
- ❌ Neglect log analysis
- ❌ Forget to clear old events

---

## Incident Response

### If Token is Compromised

1. **Immediately Revoke Token:**
   - Contact @BotFather
   - Revoke current token
   - Generate new token

2. **Update Environment:**
   ```bash
   export TELEGRAM_BOT_TOKEN="new_token"
   ```

3. **Restart Bot:**
   ```bash
   python bot.py
   ```

4. **Verify:**
   - Check logs for unauthorized activity
   - Review security stats
   - Monitor for unusual behavior

### If Under Attack

1. **Check Threat Level:**
   ```
   /security_stats
   ```

2. **If CRITICAL:**
   - Review recent events
   - Identify attacking users
   - Blacklist malicious IDs

3. **Blacklist Attackers:**
   ```
   /blacklist USER_ID Attack
   ```

4. **Monitor:**
   - Watch threat level decrease
   - Check for new attacks
   - Adjust rate limits if needed

### If Legitimate User Banned

1. **Verify User:**
   - Check if user is legitimate
   - Review their activity logs

2. **Unban:**
   ```
   /unban USER_ID
   ```

3. **Communicate:**
   - Explain rate limits to user
   - Advise to slow down requests

---

## Troubleshooting

### "Security modules not available"

**Problem:** Security modules failed to load.

**Solution:**
1. Check if `cryptography` is installed:
   ```bash
   pip install cryptography
   ```

2. Verify files exist:
   ```bash
   ls -la security/
   ```

3. Check imports:
   ```python
   from security.rate_limiter import rate_limiter
   ```

### "Failed to get bot token"

**Problem:** Token manager can't find token.

**Solution:**
1. Set environment variable:
   ```bash
   export TELEGRAM_BOT_TOKEN="your_token"
   ```

2. Or create `.env` file:
   ```
   TELEGRAM_BOT_TOKEN=your_token_here
   ```

3. Restart bot

### Rate Limiting Too Strict

**Problem:** Legitimate users getting rate limited.

**Solution:**
1. Edit `.env`:
   ```bash
   MAX_REQUESTS_PER_MINUTE=30
   MAX_REQUESTS_PER_HOUR=150
   ```

2. Restart bot

### Admin Commands Not Working

**Problem:** `/blacklist` returns "requires admin privileges"

**Solution:**
1. Check `ADMIN_USER_IDS` in `.env`:
   ```bash
   ADMIN_USER_IDS=123456789
   ```

2. Get your user ID from @userinfobot

3. Add your ID to .env

4. Restart bot

---

## Configuration Reference

### Environment Variables

```bash
# Admin Users (comma-separated)
ADMIN_USER_IDS=123456789,987654321

# Rate Limiting (optional)
MAX_REQUESTS_PER_MINUTE=20
MAX_REQUESTS_PER_HOUR=100
BAN_DURATION_MINUTES=60

# Whitelist Mode (optional)
WHITELIST_MODE=false
WHITELISTED_USER_IDS=111111111,222222222
```

### Default Values

- **Max Requests Per Minute:** 20
- **Max Requests Per Hour:** 100
- **Ban Duration:** 60 minutes
- **Whitelist Mode:** Disabled

---

## Support

**Issues:** [GitHub Issues](https://github.com/galinborisov10-art/Crypto-signal-bot/issues)  
**Documentation:** [GitHub Wiki](https://github.com/galinborisov10-art/Crypto-signal-bot/wiki)  
**Author:** galinborisov10-art

---

**Version:** 2.0.0 - Security Hardening  
**Last Updated:** 2025-12-19  
**Security is not a feature, it's a requirement!** 🔒
