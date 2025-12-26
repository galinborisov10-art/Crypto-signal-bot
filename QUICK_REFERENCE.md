# Phase 2 Part 1: Quick Reference Card

## 🚀 Quick Start

### Enable Feature (Testing)
```json
// Edit config/feature_flags.json
{
  "fundamental_analysis": {
    "enabled": true,
    "sentiment_analysis": true,
    "btc_correlation": true,
    "signal_integration": true
  }
}
```

### Disable Feature (Default/Rollback)
```json
{
  "fundamental_analysis": {
    "signal_integration": false
  }
}
```

---

## 🧪 Testing

### Run All Tests
```bash
pytest tests/test_signal_integration.py -v
```

### Run Validation
```bash
python validate_phase2_part1.py
```

### Check Syntax
```bash
python -m py_compile bot.py
```

---

## 📊 Expected Behavior

### Flags Disabled (Default)
```
/signal BTC
→ Technical-only analysis (unchanged)
→ No fundamental data shown
→ Safe for production
```

### Flags Enabled
```
/signal BTC
→ Technical analysis
→ + Sentiment analysis
→ + BTC correlation
→ + Combined score
→ + Recommendation
```

---

## 🔢 Score Calculation

```
Combined = Technical 
         + (Sentiment - 50) × 0.3    (±15 max)
         + BTC_Impact                (-15 to +10)
         
Clamped to [0, 100]
```

### Examples
| Tech | Sent | BTC  | Result |
|------|------|------|--------|
| 78   | -    | -    | 78     |
| 78   | +6   | +10  | 94     |
| 78   | -6   | -15  | 57     |

---

## 📁 Key Files

- `utils/fundamental_helper.py` - Main integration logic
- `utils/news_cache.py` - News caching system
- `config/feature_flags.json` - Feature toggles
- `bot.py` (lines 6666-6747) - /signal integration
- `tests/test_signal_integration.py` - Test suite

---

## 🔍 Troubleshooting

### Feature not working?
1. Check flags: `cat config/feature_flags.json`
2. Check logs: Look for "🔬 Running fundamental analysis"
3. Verify imports: `python -c "from utils.fundamental_helper import FundamentalHelper"`

### Tests failing?
```bash
# Install dependencies
pip install pytest pandas numpy

# Run tests
pytest tests/test_signal_integration.py -v
```

### Cache issues?
```python
from utils.news_cache import NewsCache
cache = NewsCache()
cache.clear_cache()  # Clear all cache
```

---

## 📞 Support

- Full docs: `PHASE2_PART1_README.md`
- Implementation: `IMPLEMENTATION_SUMMARY.txt`
- Tests: `tests/test_signal_integration.py`
- Validation: `validate_phase2_part1.py`

---

## ✅ Checklist

- [ ] Tests passing? `pytest tests/test_signal_integration.py -v`
- [ ] Flags configured? Check `config/feature_flags.json`
- [ ] Bot running? Check logs for errors
- [ ] Cache directory exists? `ls -la cache/`
- [ ] Documentation read? See `PHASE2_PART1_README.md`

---

**Version:** Phase 2 Part 1  
**Status:** Production Ready  
**Risk:** Zero (flags disabled by default)
