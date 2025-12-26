# Quick Reference: /market Enhancement (Phase 2 Part 2)

## 🚀 Quick Start

### Enable Feature (30 seconds)

```bash
# 1. Edit config file
nano config/feature_flags.json

# 2. Set these values to true:
{
  "fundamental_analysis": {
    "enabled": true,
    "market_integration": true
  }
}

# 3. Restart bot
./bot-service.sh restart

# 4. Test command
# Send /market in Telegram
```

### Disable Feature (30 seconds)

```bash
# 1. Edit config file
nano config/feature_flags.json

# 2. Set to false:
{
  "fundamental_analysis": {
    "market_integration": false
  }
}

# 3. Restart bot
./bot-service.sh restart
```

## 📝 Commands

### Test /market Enhancement
```
/market
```

**Expected Output (when enabled):**
- Basic market data (existing)
- ➕ Market Sentiment
- ➕ Fear & Greed Index
- ➕ BTC Dominance
- ➕ Market Cap
- ➕ Top News
- ➕ Market Context

## ⚙️ Configuration

### Minimal Config (Enable Feature)
```json
{
  "fundamental_analysis": {
    "enabled": true,
    "market_integration": true
  }
}
```

### Full Config (All Options)
```json
{
  "fundamental_analysis": {
    "enabled": true,                // Master switch
    "sentiment_analysis": true,     // Optional: news sentiment
    "btc_correlation": false,       // Optional: BTC correlation
    "signal_integration": false,    // Optional: signal enhancement
    "market_integration": true      // Required: /market enhancement
  }
}
```

## 🧪 Testing

### Run Unit Tests
```bash
cd /home/runner/work/Crypto-signal-bot/Crypto-signal-bot
python3 -m pytest tests/test_market_integration.py -v
```

**Expected:** `14 passed in ~1s`

### Test Feature Disabled
```bash
# 1. Disable in config
# 2. Restart bot
# 3. Run /market
# Expected: Only basic market data (no fundamental section)
```

### Test Feature Enabled
```bash
# 1. Enable in config
# 2. Restart bot
# 3. Run /market
# Expected: Basic data + fundamental analysis section
```

### Test API Failure Handling
```bash
# Check logs after /market command
tail -f bot.log | grep "market fundamental"

# Expected (on success):
# ✅ Market fundamental analysis sent

# Expected (on failure):
# ⚠️ Market fundamental analysis unavailable
```

## 🔍 Troubleshooting

### No fundamental data shown
```bash
# 1. Check feature flags
cat config/feature_flags.json | grep market_integration
# Should show: "market_integration": true

# 2. Check logs
tail -50 bot.log | grep -i "market"

# 3. Verify cache directory
ls -la cache/market/
```

### API errors in logs
```bash
# Check network connectivity
curl https://api.alternative.me/fng/
curl https://api.coingecko.com/api/v3/global

# Clear cache and retry
rm -rf cache/market/news_cache.json
./bot-service.sh restart
```

### Feature not activating
```bash
# 1. Verify JSON syntax
python3 -m json.tool config/feature_flags.json

# 2. Verify both flags enabled
grep -A 5 "fundamental_analysis" config/feature_flags.json

# 3. Check bot logs for startup errors
grep -i "error\|warning" bot.log | tail -20
```

## 📊 What Gets Shown

### Fear & Greed Index
- **Value:** 0-100 scale
- **Labels:** Extreme Fear, Fear, Neutral, Greed, Extreme Greed
- **Source:** Alternative.me
- **Update:** Every 60 minutes (cached)

### BTC Dominance
- **Value:** Percentage (e.g., 48.5%)
- **Context:**
  - >50%: BTC leading market
  - 45-50%: Healthy altcoin participation
  - <45%: Altseason conditions

### Market Cap
- **Value:** Total crypto market cap in trillions
- **Source:** CoinGecko
- **Includes:** All cryptocurrencies

### Market Context
AI-generated insights based on:
- Price action (strong/moderate buying/selling)
- News sentiment
- Fear & Greed level
- BTC dominance trends

## 🔒 Safety Checklist

Before enabling in production:

- [ ] Feature flags disabled by default ✅
- [ ] Tests all passing ✅
- [ ] Logs show no errors ✅
- [ ] Cache directory created (`cache/market/`) ✅
- [ ] Network access to APIs verified ✅
- [ ] Backup config saved ✅

## 🚨 Emergency Rollback

### Quick Disable (5 seconds)
```bash
sed -i 's/"market_integration": true/"market_integration": false/' config/feature_flags.json
./bot-service.sh restart
```

### Full Rollback (30 seconds)
```bash
git log --oneline | grep "market"
# Note the commit hash before enhancement

git revert <commit-hash>
git push origin main
./bot-service.sh restart
```

## 📈 Performance

### Expected Response Times
- **First call (no cache):** ~3-4 seconds
- **Cached calls:** ~2-3 seconds
- **Feature disabled:** ~2-3 seconds (unchanged)

### Cache Information
- **Location:** `cache/market/news_cache.json`
- **TTL:** 60 minutes
- **Size:** <1 KB
- **Auto-cleanup:** On expiration

## 🌐 API Status Check

### Test Fear & Greed API
```bash
curl -s https://api.alternative.me/fng/ | python3 -m json.tool
```

**Expected:**
```json
{
  "data": [{
    "value": "65",
    "value_classification": "Greed"
  }]
}
```

### Test CoinGecko API
```bash
curl -s https://api.coingecko.com/api/v3/global | python3 -m json.tool
```

**Expected:**
```json
{
  "data": {
    "market_cap_percentage": {"btc": 48.5},
    "total_market_cap": {"usd": 1850000000000}
  }
}
```

## 📝 Logs Reference

### Success Messages
```
🔬 Running market fundamental analysis
Fear & Greed Index: 65 (Greed)
Market overview: BTC dominance=48.5%, Market cap=$1.85T
✅ Market fundamental analysis sent
```

### Warning Messages
```
⚠️ Market fundamental analysis unavailable: [reason]
Fear & Greed API timeout
CoinGecko API request failed
```

### Debug Messages
```
Market integration enabled: True
Fear & Greed Index retrieved from cache
Sentiment analysis added: POSITIVE
```

## 🔧 Advanced Usage

### Change Cache TTL
Edit `utils/market_data_fetcher.py`:
```python
# Default: 60 minutes
fetcher = MarketDataFetcher(cache_ttl=30)  # 30 minutes
```

### Custom Context Messages
Edit `utils/market_helper.py`:
```python
def generate_market_context(self, ...):
    # Customize messages here
    if price_change_24h > 5:
        lines.append("🚀 Extreme buying pressure!")
```

### Add More Metrics
Extend `get_market_overview()` in `market_data_fetcher.py`:
```python
result['altcoin_season_index'] = data.get('altcoin_index', 0)
```

## 📚 Files Reference

| File | Purpose | Lines | Tests |
|------|---------|-------|-------|
| `utils/market_data_fetcher.py` | Fetch APIs | 168 | 6 |
| `utils/market_helper.py` | Analysis & formatting | 293 | 6 |
| `bot.py` (modified) | Integration | +45 | - |
| `tests/test_market_integration.py` | Tests | 357 | 14 |
| `config/feature_flags.json` | Config | - | - |

## ✅ Validation Checklist

After deployment:

- [ ] Tests pass: `pytest tests/test_market_integration.py -v`
- [ ] Feature disabled by default: `grep market_integration config/feature_flags.json`
- [ ] /market works (disabled): Basic data only
- [ ] /market works (enabled): Basic + fundamental data
- [ ] Logs show no errors: `grep -i error bot.log | tail -10`
- [ ] Cache created: `ls cache/market/news_cache.json`
- [ ] APIs accessible: `curl https://api.alternative.me/fng/`

## 🎯 Success Criteria

✅ All 14 tests passing
✅ Zero breaking changes to existing /market
✅ Feature flags control activation
✅ Graceful error handling (no crashes)
✅ API calls cached (60 min TTL)
✅ Fear & Greed Index working
✅ BTC Dominance showing
✅ Market context intelligent
✅ Message formatting clean
✅ No API keys required

---

**Last Updated:** 2025-12-26
**Version:** 1.0.0
**Status:** Ready for deployment ✅
