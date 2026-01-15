# PR #115: Enhanced Swing Analysis - Quick User Guide

## How to Use

### 1. Access the Feature

In your Telegram chat with the bot:
1. Send `/market` command
2. Click **"🎯 Swing Trading Анализ"** button

### 2. What to Expect

**Progress Message (immediate)**
```
📊 SWING TRADING ANALYSIS

Генерирам детайлен swing анализ за 6 валути...
⏳ Това може да отнеме 30-60 секунди.

Моля изчакайте...
```

**Individual Analyses (6 messages)**
You'll receive detailed analysis for each of these coins:
- 🪙 BITCOIN (BTCUSDT)
- 💎 ETHEREUM (ETHUSDT)
- ⚡ BINANCE COIN (BNBUSDT)
- 🌐 SOLANA (SOLUSDT)
- 💰 RIPPLE (XRPUSDT)
- 🎯 CARDANO (ADAUSDT)

**Summary (7th message)**
Ranked opportunities from best to worst with action recommendations

### 3. Understanding Each Analysis

#### Section 1: Current Price
```
💰 Цена: $97,030.15 (+4.1% 24h, +6.2% 7d)
```
- Current price in USD
- 24-hour change percentage
- 7-day change percentage

#### Section 2: Market Structure
```
📊 СТРУКТУРА:
  • 4H: НЕУТРАЛНА
  • 1D: НЕУТРАЛНА
  • Подравняване: ⚠️ СМЕСЕНО
```
- **4H**: 4-hour timeframe structure (БИЧА/МЕЧA/НЕУТРАЛНА)
- **1D**: Daily timeframe structure
- **Подравняване**: Alignment between timeframes
  - ✅ БИЧА = Both bullish (best for longs)
  - ❌ МЕЧA = Both bearish (avoid longs)
  - ⚠️ СМЕСЕНО/КОНСОЛИДАЦИЯ = Unclear (wait)

#### Section 3: Key Levels
```
🔍 КЛЮЧОВИ НИВА:
  🔴 Съпротива: $99,941.05 (+3.0% от цена)
  🟢 Подкрепа: $94,119.25 (-3.0% под цена)
```
- **Съпротива (Resistance)**: Price level above current price that may stop upward movement
- **Подкрепа (Support)**: Price level below current price that may stop downward movement
- Use these for setting alerts and stop losses

#### Section 4: Volume & Momentum
```
📊 ОБЕМ & MOMENTUM:
  • Обем: 1.00x среден
  • Тренд: НОРМАЛЕН

😐 Fear & Greed: 48/100 (Неутрален)
```
- **Обем**: Volume compared to average (>1.2x = high interest)
- **Тренд**: Volume trend (INCREASING/DECREASING/NORMAL)
- **Fear & Greed**: Market sentiment (0-25 = Fear, 75-100 = Greed)

#### Section 5: Swing Setup
Shows the trading setup:
- **✅ БИЧИ ALIGNMENT**: Bullish setup, consider longs
- **❌ МЕЧИ ALIGNMENT**: Bearish setup, avoid longs
- **⚠️ КОНСОЛИДАЦИЯ**: Ranging, wait for breakout

Each includes:
- **Вход (Entry)**: Where to enter the trade
- **TP1/TP2 (Take Profit)**: Profit targets
- **SL (Stop Loss)**: Where to exit if wrong
- **R:R (Risk:Reward)**: Ratio of risk to reward (3:1 = good)

#### Section 6: Professional Analysis
Detailed narrative from swing trader perspective:
- **ПАЗАРЕН КОНТЕКСТ**: What's happening now
- **SWING TRADER ПЕРСПЕКТИВА**: How professional sees it
- **КЛЮЧОВИ РИСКОВЕ**: What could go wrong
- **УПРАВЛЕНИЕ НА ПОЗИЦИЯТА**: How to manage the trade
- **ВРЕМЕВА ЛИНИЯ**: When to expect movement

#### Section 7: Recommendation
```
✅ РЕЙТИНГ: 3.5/5 ⭐⭐⭐⭐☆

ПЛАН ЗА ДЕЙСТВИЕ:
1. [Step-by-step action plan]
2. ...

ИЗБЯГВАЙ АКО:
- [Conditions to avoid]
```
- **Rating**: 1-5 stars (5 = best setup, 1 = avoid)
- **Action Plan**: Numbered steps to follow
- **Avoid If**: Situations when setup is invalidated

### 4. Understanding the Summary

The 7th message ranks all coins:

#### Best Opportunities (🏆)
```
1. 🥇 SOL - 4.5/5 ⭐⭐⭐⭐⭐
   Силна бича структура, отличен R:R (4.2:1)
   Действие: BUY на pullback към $142.50
```
- Rating ≥ 3.5 stars
- Strong setups worth considering
- Top 3 get medals 🥇🥈🥉

#### Caution / Wait (⚠️)
- Rating 2.5-3.4 stars
- Unclear or range-bound
- Wait for better setup

#### Avoid (❌)
- Rating < 2.5 stars
- Bearish or weak setups
- Sit on sidelines

### 5. How to Use This Information

#### For Day Traders
- Focus on 4H structure
- Look for alignment with 1D
- Use tight stops (around SL levels)
- Take profits at TP1 quickly

#### For Swing Traders
- Focus on 1D structure
- Wait for clear alignment
- Hold for TP2 (3-14 days)
- Use trailing stops after TP1

#### For Position Traders
- Only trade when rating ≥ 4 stars
- Wait for pullbacks to support
- Hold through minor fluctuations
- Focus on weekly/monthly trends

### 6. Important Notes

⚠️ **This is NOT financial advice**
- Do your own research (DYOR)
- Never invest more than you can afford to lose
- Use proper risk management (1-2% per trade max)

⚠️ **Data Freshness**
- Analysis uses real-time data
- Market changes rapidly
- Re-run analysis every 4-6 hours
- Set price alerts instead of market orders

⚠️ **Rating System**
- 5 stars = Excellent setup, strong alignment
- 4 stars = Good setup, clear direction
- 3 stars = Decent setup, wait for confirmation
- 2 stars = Weak setup, high risk
- 1 star = Poor setup, avoid

### 7. Common Questions

**Q: Why does the analysis take 30-60 seconds?**
A: The bot fetches real-time data from Binance for all 6 coins, analyzes market structure, and generates professional narratives. This takes time but ensures accuracy.

**Q: Can I choose which coins to analyze?**
A: Currently analyzes all 6 pairs automatically. Future versions may allow selection.

**Q: How often should I check?**
A: For swing trading: every 4-6 hours. For day trading: every 1-2 hours.

**Q: What if a coin shows "ERROR"?**
A: API may be temporarily down for that pair. The bot continues with others.

**Q: Why are some terms in English?**
A: Technical trading terms (breakout, R:R, SL, TP) are standard in English globally. Labels and instructions are in Bulgarian.

**Q: Can I trust the recommendations?**
A: Use as ONE input in your decision. Combine with your own analysis, news, and risk tolerance.

### 8. Example Trade Flow

**Scenario: BTC shows 4.5/5 rating, BULLISH setup**

1. **Read the analysis** thoroughly
2. **Check action plan**: "Wait for pullback to $96,500"
3. **Set price alert** at $96,500 (don't chase current price)
4. **When alert triggers**:
   - Check if volume confirms (>1.2x average)
   - Check if 4H candle closes strong in the zone
   - Enter with 50% of planned position
5. **After entry**:
   - Set stop loss at $95,200 (from analysis)
   - Set alert at TP1: $99,800
6. **At TP1**:
   - Take 50% profit
   - Move SL to breakeven
   - Let rest run to TP2 with trailing SL
7. **Monitor**:
   - If SL hit: Exit, review, wait for new setup
   - If TP2 hit: Close position, celebrate 🎉

### 9. Tips for Success

✅ **DO**:
- Set price alerts, not market orders
- Wait for pullbacks in bullish setups
- Respect stop losses (never move them lower)
- Take partial profits at TP1
- Re-analyze before entering a trade
- Keep position sizes small (1-2% risk)

❌ **DON'T**:
- Chase breakouts without confirmation
- Enter in the middle of the range
- Ignore "AVOID IF" conditions
- Trade on weekends (low liquidity)
- Revenge trade after a loss
- Enter all 6 pairs at once (diversify timing)

### 10. Support

If you encounter issues:
- Check bot logs for errors
- Verify Binance API is accessible
- Try again in 5 minutes (may be rate limited)
- Contact bot administrator

---

**Last Updated**: PR #115 Implementation (Jan 2026)
**Version**: 1.0
