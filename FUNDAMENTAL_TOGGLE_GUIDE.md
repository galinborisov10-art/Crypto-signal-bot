# Fundamental Analysis Toggle Guide

## 📖 Overview

This guide explains how to use the user-controllable fundamental analysis toggle feature in the Crypto Signal Bot. This feature allows each user to independently enable or disable fundamental analysis integration in `/signal` commands with customizable weight distribution.

---

## 🎯 What is Fundamental Analysis?

Fundamental analysis adds market context to technical signals by incorporating:

- **Fear & Greed Index** - Market sentiment indicator
- **Market Cap & Volume** - Overall market health metrics
- **BTC Dominance** - Bitcoin's market share percentage
- **News Sentiment** - Analysis of recent crypto news

When enabled, fundamental analysis is combined with technical analysis (ICT + ML) to provide a more comprehensive trading signal.

---

## 🚀 Quick Start

### Check Current Status

```
/fund
```

Shows your current fundamental analysis settings.

### Enable Fundamental Analysis

```
/fund on
```

Activates fundamental analysis for your signals.

### Disable Fundamental Analysis

```
/fund off
```

Deactivates fundamental analysis (technical only).

---

## ⚙️ Settings Menu

Access the full settings menu with:

```
/settings
```

You'll see:
- Current fundamental analysis status (✅ ENABLED or ❌ DISABLED)
- Weight distribution (if enabled)
- Interactive toggle button

### Toggle Button

Click **🔄 Toggle Fundamental** to switch between enabled/disabled states instantly.

---

## 📊 How It Works

### Technical Analysis Only (Default)

When fundamental analysis is **DISABLED**:

```
🟢 STRONG BUY - BTCUSDT

📊 4h | Confidence: 75.3% 🔥
📊 Analysis Mode: Technical ✅ | Fundamental ❌

[ICT + ML analysis only]
```

The confidence score is based purely on:
- ICT (Inner Circle Trader) analysis: 70%
- ML (Machine Learning) predictions: 30%

### Combined Analysis

When fundamental analysis is **ENABLED**:

```
🟢 STRONG BUY - BTCUSDT

📊 4h | Confidence: 77.1% 🔥
📊 Analysis Mode: Technical ✅ + Fundamental ✅ (70/30)

   Technical: 75.3% (ICT + ML)
   Fundamental: 82.0%
   Combined: 77.1%

[ICT + ML analysis sections]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🧠 FUNDAMENTAL ANALYSIS:

📊 Fear & Greed Index: 23 (Extreme Fear) 🔴
💹 BTC Dominance: 57.5%
💰 Market Cap: $3.04T (-0.8% 24h)
📊 Volume 24h: $76.2B

💡 Market Context:
⚠️ Умерен продавачески натиск.
Fear & Greed в зона "Extreme Fear" - потенциална възможност за покупка.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

The confidence score combines:
- Technical analysis: 70% weight (default)
- Fundamental analysis: 30% weight (default)

---

## 🎚️ Weight Configuration

### Default Weights

By default, the system uses:
- **Technical**: 70%
- **Fundamental**: 30%

This means technical analysis has more influence on the final confidence score.

### How Weights Work

Example calculation:
```
Technical Score: 75.3%
Fundamental Score: 82.0%
Technical Weight: 70%
Fundamental Weight: 30%

Combined = (75.3 × 0.70) + (82.0 × 0.30)
Combined = 52.71 + 24.60
Combined = 77.31% ≈ 77.1%
```

### Custom Weights (Future Feature)

Currently, weights are fixed at 70/30. Future updates may allow customization:

```
/fund weight 50  (50% fundamental, 50% technical)
/fund weight 20  (20% fundamental, 80% technical)
```

---

## 📋 Command Reference

### /fund

Main command for fundamental analysis control.

**Usage:**
```
/fund          → Show current status
/fund on       → Enable fundamental analysis
/fund off      → Disable fundamental analysis
/fund status   → Show detailed status (same as /fund)
```

**Examples:**

```bash
# Check status
/fund

Output:
🧠 FUNDAMENTAL ANALYSIS SETTINGS

Status: ❌ DISABLED

Commands:
/fund on  - Enable fundamental analysis
/fund off - Disable fundamental analysis
/fund status - Show this status
/settings - Full settings menu
```

```bash
# Enable
/fund on

Output:
✅ Fundamental Analysis ENABLED

Signals will now include:
• Fear & Greed Index
• Market Cap & Volume
• BTC Dominance
• News Sentiment

Weight Distribution:
• Technical: 70%
• Fundamental: 30%

Use /signal to see enhanced analysis!
```

```bash
# Disable
/fund off

Output:
❌ Fundamental Analysis DISABLED

Signals will use:
• Technical analysis only (ICT + ML)

Use /fund on to re-enable fundamental analysis.
```

### /settings

Access full settings menu with interactive buttons.

**Features:**
- View all your settings
- Toggle fundamental analysis with button
- See weight distribution when enabled
- Access timeframe settings

---

## 🔧 Technical Documentation

### Architecture

The fundamental analysis toggle is implemented with these components:

#### 1. User Settings Storage

```python
settings = {
    'use_fundamental': False,      # User preference (default: disabled)
    'fundamental_weight': 0.3,     # Weight for fundamental (default: 30%)
    # ... other settings
}
```

#### 2. Feature Flag Check

Before running fundamental analysis, the system checks:

```python
user_wants_fundamental = settings.get('use_fundamental', False)
feature_flag_enabled = feature_flags['fundamental_analysis']['enabled']

if user_wants_fundamental and feature_flag_enabled:
    # Run fundamental analysis
```

This ensures:
- User control over their own signals
- Global feature flag can disable for maintenance
- Double-check prevents unexpected behavior

#### 3. Score Combination

```python
# Get weights
fund_weight = settings.get('fundamental_weight', 0.3)
tech_weight = 1 - fund_weight

# Calculate scores
technical_confidence = ict_signal.confidence  # ICT + ML
fundamental_score = calculate_fundamental_score(data)

# Combine
combined_confidence = (technical_confidence * tech_weight) + 
                      (fundamental_score * fund_weight)
```

#### 4. Signal Formatting

The signal message includes:
- Analysis mode indicator (always visible)
- Score breakdown (when fundamental enabled)
- Fundamental section (when fundamental enabled)

### Data Flow

```
User executes /signal
    ↓
Check user settings (use_fundamental)
    ↓
Check feature flag (enabled)
    ↓
If BOTH true:
    ├─ Fetch fundamental data
    ├─ Calculate fundamental score
    ├─ Combine with technical (weighted)
    └─ Display enhanced signal
Else:
    └─ Display technical-only signal
```

### Backward Compatibility

Existing users automatically receive:
- `use_fundamental: False` (opt-in, not opt-out)
- `fundamental_weight: 0.3` (standard ratio)

This ensures no unexpected changes to existing user behavior.

---

## 💡 Use Cases

### For Conservative Traders

Keep fundamental analysis **disabled** to rely purely on proven technical indicators:

```
/fund off
```

Benefits:
- Faster signal generation
- Focus on price action
- Simpler decision making

### For Context-Aware Traders

Enable fundamental analysis to get the full market picture:

```
/fund on
```

Benefits:
- Market sentiment awareness
- Better timing during fear/greed extremes
- Correlation with BTC movements

### For Testing

Toggle on/off to compare results:

```
/fund off
/signal BTC

[Note the technical score]

/fund on
/signal BTC

[Compare with combined score]
```

---

## 🔍 Troubleshooting

### Fundamental Section Not Showing

**Issue:** Enabled fundamental but not seeing the section

**Solutions:**

1. **Check Feature Flag**
   - Admin must enable in `config/feature_flags.json`
   - Look for `fundamental_analysis.enabled: true`

2. **Check Data Availability**
   - Fundamental analysis requires cached data
   - May not work if cache is empty
   - Wait a few minutes and try again

3. **Verify Setting**
   ```
   /fund
   ```
   Should show "Status: ✅ ENABLED"

### Combined Score Not Changing

**Issue:** Enabling fundamental doesn't change confidence

**Reasons:**

1. **Similar Scores**
   - If technical and fundamental scores are close, combined will be similar
   - Example: Tech 75% + Fund 76% → Combined 75.3%

2. **Cache Miss**
   - No fundamental data available
   - Falls back to technical only
   - Check bot logs for warnings

### Settings Not Persisting

**Issue:** Settings reset after restart

**Solution:**
- Settings are stored in bot memory (bot_data)
- Currently not persisted to disk
- This is expected behavior
- Future update may add persistence

---

## 📈 Best Practices

### 1. Start with Default

For new users:
```
/fund off  (or keep default)
/signal BTC
```

Learn the technical signals first.

### 2. Compare Results

After understanding technical:
```
/fund on
/signal BTC
```

Compare how fundamental context affects the signal.

### 3. Market Conditions

**High Volatility:**
- Consider enabling fundamental
- Market sentiment matters more

**Stable Markets:**
- Technical may be sufficient
- Fundamental adds less value

### 4. Timeframe Consideration

**Short Timeframes (1m, 5m, 15m):**
- Fundamental less relevant
- Suggest: `/fund off`

**Long Timeframes (4h, 1d, 1w):**
- Fundamental more important
- Suggest: `/fund on`

---

## 🔐 Privacy & Security

### Data Storage

- Settings stored per user (by chat_id)
- No personal data collected
- Settings are in-memory (not saved to disk)

### Feature Flags

- Global feature flag provides admin control
- Can disable fundamental analysis system-wide
- User settings preserved when re-enabled

---

## 🆕 Future Enhancements

Planned improvements:

1. **Custom Weights**
   ```
   /fund weight 40  (40% fund, 60% tech)
   ```

2. **Auto-Toggle by Timeframe**
   ```
   /fund auto  (enable on 4h+, disable on <1h)
   ```

3. **Preset Profiles**
   ```
   /fund profile conservative  (10% fund, 90% tech)
   /fund profile balanced      (30% fund, 70% tech)
   /fund profile aggressive    (50% fund, 50% tech)
   ```

4. **Persistent Settings**
   - Save settings to database
   - Survive bot restarts

---

## 📞 Support

### Commands Summary

| Command | Description |
|---------|-------------|
| `/fund` | Show fundamental status |
| `/fund on` | Enable fundamental analysis |
| `/fund off` | Disable fundamental analysis |
| `/fund status` | Detailed status info |
| `/settings` | Full settings menu with buttons |
| `/signal` | Generate signal (respects your settings) |

### Get Help

If you encounter issues:

1. Check this guide
2. Run `/fund` to verify settings
3. Try toggling off and on
4. Check with bot admin

---

## ✅ Summary

The fundamental analysis toggle gives you control over how your signals are generated:

- **Default:** Technical only (ICT + ML)
- **Enabled:** Technical + Fundamental (weighted combination)
- **Easy Control:** `/fund on` or `/fund off`
- **Visual Indicator:** Always shows mode in signals
- **Flexible:** Change anytime, affects future signals only

Start with the default, experiment with both modes, and choose what works best for your trading style!

---

**Last Updated:** December 27, 2024
**Version:** 1.0.0
**Feature:** User-Controllable Fundamental Analysis Toggle
