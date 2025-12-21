# Manual Testing Guide for Signal Callback Fix

## Overview
This guide helps verify that the `signal_callback` handler now uses ICT Engine correctly.

## Prerequisites
- Bot deployed and running
- Telegram access to bot
- Admin/owner account

## Test Cases

### Test 1: Button Click Flow - BTC 4h

**Objective:** Verify button clicks use ICT Engine

**Steps:**
1. Open bot in Telegram
2. Send `/signal` (no arguments)
3. Click `₿ BTC` button
4. Click `4h` button

**Expected Result:**
- ✅ Shows "🔍 Running ICT analysis for BTCUSDT (4h)..."
- ✅ Receives ICT signal or NO_TRADE message
- ✅ If NO_TRADE: Shows ❌ emoji (not ⚪)
- ✅ If NO_TRADE: Shows MTF breakdown sorted (1m → 1w)
- ✅ If NO_TRADE: Shows "← текущ" marker on current timeframe
- ✅ If NO_TRADE: Shows MTF Consensus percentage
- ✅ If valid signal: Shows 13-point ICT format
- ✅ If valid signal: May include chart with ICT annotations

**How to verify:**
- Check emoji: Should be ❌ (not ⚪) for NO_TRADE
- Check MTF section: Should list all timeframes
- Check format: Should match 13-point structure
- Check chart: Should show Order Blocks, FVG, Liquidity if present

---

### Test 2: Consistency with /signal Command

**Objective:** Verify button click produces same result as command

**Steps:**
1. **Via buttons:**
   - Send `/signal`
   - Click `₿ BTC`
   - Click `4h`
   - Take screenshot of output
   
2. **Via command:**
   - Send `/signal BTC 4h`
   - Take screenshot of output

3. **Compare outputs:**
   - Should have same format
   - Should have same ICT analysis
   - Should have same confidence score
   - Should have same TP/SL levels

**Expected Result:**
- ✅ Both produce identical or very similar output
- ✅ Both use ICT Engine
- ✅ Both show same signal type (BUY/SELL/NO_TRADE)

---

### Test 3: NO_TRADE Message Format

**Objective:** Verify NO_TRADE shows new format

**Test when market conditions are unclear:**

**Steps:**
1. Send `/signal`
2. Click coin button (any)
3. Click timeframe (any)
4. Wait for NO_TRADE response

**Expected NO_TRADE Format:**
```
❌ NO TRADE - Market conditions insufficient

📊 [SYMBOL] | [TF] | [TIME]
━━━━━━━━━━━━━━━━━━━━

📈 MTF Breakdown:
  1m: [SIGNAL] [EMOJI] [BAR] [%]
  5m: [SIGNAL] [EMOJI] [BAR] [%]
 15m: [SIGNAL] [EMOJI] [BAR] [%]
  1h: [SIGNAL] [EMOJI] [BAR] [%]
  2h: [SIGNAL] [EMOJI] [BAR] [%]
  4h: [SIGNAL] [EMOJI] [BAR] [%] ← текущ
  1d: [SIGNAL] [EMOJI] [BAR] [%]
  1w: [SIGNAL] [EMOJI] [BAR] [%]

💎 MTF Consensus: [%] agreement ([STRENGTH])
📊 Recommendation: [TEXT]

🔍 Reason:
• [REASON 1]
• [REASON 2]
...
```

**Check:**
- ✅ Uses ❌ emoji (not ⚪)
- ✅ Shows MTF Breakdown section
- ✅ Lists timeframes in order (1m, 5m, 15m, 1h, 2h, 4h, 1d, 1w)
- ✅ Shows "← текущ" marker on current timeframe
- ✅ Shows MTF Consensus percentage
- ✅ Shows recommendation text
- ✅ Shows reasons for NO_TRADE

---

### Test 4: Valid Signal Format

**Objective:** Verify valid signals show 13-point ICT format

**Test when market has clear setup:**

**Steps:**
1. Send `/signal`
2. Click coin button (try multiple)
3. Click timeframe (try multiple)
4. Wait for signal response

**Expected Valid Signal Format (13 Points):**
```
[EMOJI] [SIGNAL TYPE] - [SYMBOL]

1. 📊 [TF] | Confidence: [%] [EMOJI]
2. 💰 Price: $[PRICE]
3. 📈 Bias: [BULLISH/BEARISH]

4. 🎯 ICT Concepts:
   • Order Block: [PRICE RANGE]
   • FVG: [PRICE RANGE]
   • Liquidity: [PRICE]

5. 📍 ENTRY ZONE:
   Best: $[PRICE]
   Range: $[LOW] - $[HIGH]

6-8. 🎯 TAKE PROFIT:
   TP1: $[PRICE] (+[%]) - Primary
   TP2: $[PRICE] (+[%])
   TP3: $[PRICE] (+[%])

9. 🛡️ STOP LOSS: $[PRICE] (-[%])

10. ⚖️ Risk/Reward: 1:[RATIO]

11. 📊 MTF Analysis:
    [TIMEFRAMES WITH SIGNALS]
    💎 Consensus: [STRENGTH] ([%])

12. 🎯 Key Levels:
    [SUPPORT/RESISTANCE]

13. ⚠️ Not financial advice. DYOR!
```

**Check:**
- ✅ Shows all 13 points
- ✅ Has ICT Concepts section (OB, FVG, Liquidity)
- ✅ Has Entry Zone with best entry
- ✅ Has 3 TP levels
- ✅ Has Stop Loss
- ✅ Has Risk/Reward ratio
- ✅ Has MTF Analysis
- ✅ Has disclaimer

---

### Test 5: Chart Generation

**Objective:** Verify charts include ICT annotations

**Steps:**
1. Send `/signal`
2. Click coin button
3. Click timeframe
4. Wait for response

**Expected Result:**
- ✅ Chart image sent (if signal is valid)
- ✅ Chart shows candlesticks
- ✅ Chart shows Order Blocks (if present)
- ✅ Chart shows FVG zones (if present)
- ✅ Chart shows Liquidity levels (if present)
- ✅ Chart shows Entry/TP/SL markers (if valid signal)

**How to verify:**
- Open chart image
- Look for colored boxes (Order Blocks)
- Look for shaded areas (FVG)
- Look for horizontal lines (Liquidity, Entry, TP, SL)

---

### Test 6: All Supported Coins

**Objective:** Verify all coin buttons work

**Test each coin:**
- [ ] ₿ BTC (BTCUSDT)
- [ ] Ξ ETH (ETHUSDT)
- [ ] ⚡ SOL (SOLUSDT)
- [ ] 💎 XRP (XRPUSDT)
- [ ] 🔷 BNB (BNBUSDT)
- [ ] ♠️ ADA (ADAUSDT)

**For each coin:**
1. Click coin button
2. Click any timeframe
3. Verify ICT analysis appears
4. Verify NO_TRADE or valid signal format

---

### Test 7: All Timeframes

**Objective:** Verify all timeframe buttons work

**Test each timeframe:**
- [ ] 15m
- [ ] 1h
- [ ] 4h
- [ ] 1d

**For each timeframe:**
1. Click any coin
2. Click timeframe
3. Verify ICT analysis for that timeframe
4. Verify "← текущ" marker appears on correct timeframe in MTF breakdown

---

### Test 8: Real-Time Monitor Integration

**Objective:** Verify signals are tracked

**Steps:**
1. Get a valid signal (BUY or SELL)
2. Check bot logs or database for:
   - Signal added to monitor
   - Signal ID generated
   - Entry price recorded
   - TP/SL levels recorded

**Expected Result:**
- ✅ Signal added to real-time monitor
- ✅ Will receive alerts at 80% to TP
- ✅ Will receive alerts on WIN/LOSS

---

### Test 9: Error Handling

**Objective:** Verify graceful error handling

**Test scenarios:**
1. **Network error:** Disconnect internet briefly
   - Should show error message
   - Should not crash

2. **Invalid data:** (Hard to test manually)
   - Should show error message
   - Should not crash

**Expected Result:**
- ✅ Shows "❌ Failed to fetch market data" or similar
- ✅ Bot continues working after error

---

### Test 10: Performance

**Objective:** Verify response time

**Steps:**
1. Click coin button
2. Click timeframe button
3. Measure time until response

**Expected Result:**
- ✅ Analysis starts within 1-2 seconds
- ✅ Complete response within 5-10 seconds
- ✅ Chart generated (if applicable) within 15 seconds

---

## Regression Tests

### Verify Old Functionality Still Works

**Test these commands still work:**
- [ ] `/start` - Shows welcome message
- [ ] `/help` - Shows help
- [ ] `/market` - Shows market overview
- [ ] `/settings` - Shows settings
- [ ] `/news` - Shows news
- [ ] Other commands...

---

## Bug Report Template

If you find issues, report using this template:

```
**Test Case:** [Test number and name]
**Steps:** [What you did]
**Expected:** [What should happen]
**Actual:** [What actually happened]
**Screenshot:** [Attach screenshot]
**Logs:** [Attach relevant bot logs]
```

---

## Success Criteria

All tests should pass with these results:

- ✅ Button clicks produce ICT analysis
- ✅ NO_TRADE uses ❌ emoji and shows MTF breakdown
- ✅ Valid signals use 13-point ICT format
- ✅ Charts show ICT annotations
- ✅ Consistent with `/signal` command
- ✅ All coins work
- ✅ All timeframes work
- ✅ Signals tracked in monitor
- ✅ Error handling works
- ✅ Performance acceptable

---

## Automated Verification

Run this before manual testing:

```bash
cd /path/to/Crypto-signal-bot
python3 verify_signal_callback_fix.py
```

Should output:
```
✅ ALL VERIFICATIONS PASSED!
signal_callback is now using ICT Engine (not legacy code)
```

---

## Notes for Testers

1. **Take screenshots** of NO_TRADE and valid signals
2. **Compare with `/signal` command** output
3. **Test during different market conditions**
4. **Monitor bot logs** for errors
5. **Test multiple coins and timeframes**
6. **Verify charts are generated**

---

## Rollback Plan

If issues found:

1. Stop the bot
2. Checkout previous version:
   ```bash
   git checkout <previous_commit>
   ```
3. Restart bot
4. Report issues in GitHub

---

## Contact

Report issues to: [Bot Owner/Admin]
GitHub PR: [PR Number/Link]
