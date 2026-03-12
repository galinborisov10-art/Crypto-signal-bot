# 🔙 Rollback Information

## Stable Version: Commit 1f163c3 (Feb 6, 2026)

### ✅ Какво ОСТАВА след rollback:

#### Core Signal Engine:
- `ict_signal_engine.py` (2813 lines) - основен engine
- MTF (Multi-Timeframe) analysis
- ICT Components:
  - Order Blocks (OB)
  - Fair Value Gaps (FVG)
  - Liquidity detection
  - Whale detection
- Entry/SL/TP calculation
- Bias calculation system

#### Bot Infrastructure:
- Telegram bot основи
- Chart generation (mpl_chart_service.py)
- Configuration система
- Logging и error handling

### ❌ Какво СЕ ПРЕМАХВА:

#### Entry Scenarios System (Feb 7 - Mar 11):
- `entry_scenarios.py` - ROLLBACK/PULLBACK/CONTINUATION/REVERSAL scenarios
- `scenario_pattern_detector.py` - pattern matching logic
- `entry_scenario_config.py` - scenario configuration
- `scenario_validation.py` - validation rules
- 10+ bug fix commits за scenario system

#### Reason for Removal:
- Нестабилен код с множество bugs
- Сложна логика без proper testing
- Конфликти с основния signal engine
- Непредвидими резултати

### 📊 Rollback Impact:

| Feature | Before Rollback | After Rollback | Status |
|---------|----------------|----------------|---------|
| Signal Engine | ✅ Working | ✅ Working | Stable |
| ICT Components | ✅ Working | ✅ Working | Stable |
| Chart Generation | ✅ Working | ✅ Working | Stable |
| Entry Scenarios | ❌ Buggy | ❌ Removed | Clean |
| Overall Stability | ⚠️ Unstable | ✅ Stable | Fixed |

### 🔄 Recovery Options:

If rollback causes issues (unlikely):
```bash
git reset --hard backup-before-reset-TIMESTAMP
git push --force origin main
```

### 📝 Future Development:

Ако искаш да добавиш scenario system отново:
1. Създай нов feature branch
2. Реимплементирай със SOLID testing
3. Test на demo environment първо
4. Merge само след стабилни резултати
