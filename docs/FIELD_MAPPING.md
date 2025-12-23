# 📋 Field Mapping Reference

## Overview

This document describes the standardized field mappings used across the Trading Journal, ML Engine, and Daily Reports systems.

## Trade Status Fields

### Status Field

The `status` field indicates the **lifecycle state** of a trade:

| Value | Meaning | Used In |
|-------|---------|---------|
| `PENDING` | Trade recorded but not yet executed | Trading Journal |
| `ACTIVE` | Trade is currently open/running | Trading Journal |
| `COMPLETED` | Trade has closed (win/loss/breakeven) | Trading Journal, Daily Reports |

### Outcome Field

The `outcome` field indicates the **result** of a completed trade:

| Value | Meaning | Profit/Loss |
|-------|---------|-------------|
| `SUCCESS` | Winning trade | profit > 0 |
| `FAILED` | Losing trade | profit < 0 |
| `BREAKEVEN` | No profit or loss | profit = 0 |

---

## Format Evolution

### Old Format (Legacy - Still Supported)

Used before standardization (pre-Dec 2025):

```json
{
  "status": "WIN",     // ❌ Non-standard: status = outcome
  "outcome": "WIN"     // ❌ Redundant
}
```

```json
{
  "status": "LOSS",    // ❌ Non-standard: status = outcome
  "outcome": "LOSS"    // ❌ Redundant
}
```

**Issues:**
- `status` field mixed lifecycle state with outcome
- No way to distinguish "active trade" from "completed trade"
- Daily reports expected different format

---

### New Format (Standardized - Current)

Used after standardization (Dec 2025+):

```json
{
  "status": "COMPLETED",   // ✅ Lifecycle state
  "outcome": "SUCCESS"     // ✅ Trade result
}
```

```json
{
  "status": "COMPLETED",   // ✅ Lifecycle state
  "outcome": "FAILED"      // ✅ Trade result
}
```

```json
{
  "status": "COMPLETED",   // ✅ Lifecycle state
  "outcome": "BREAKEVEN"   // ✅ No profit/loss
}
```

**Benefits:**
- Clear separation of lifecycle vs result
- Compatible with daily reports expectations
- Enables proper win rate calculations
- Supports breakeven trades

---

## Backward Compatibility

All systems handle **both formats** to ensure smooth transition:

### bot.py - `update_trade_outcome()`

**Writes new format:**
```python
if outcome == 'WIN':
    trade['status'] = 'COMPLETED'
    trade['outcome'] = 'SUCCESS'
elif outcome == 'LOSS':
    trade['status'] = 'COMPLETED'
    trade['outcome'] = 'FAILED'
else:
    trade['status'] = 'COMPLETED'
    trade['outcome'] = 'BREAKEVEN'
```

### bot.py - `analyze_trade_patterns()`

**Reads both formats:**
```python
# Handle both old (WIN/LOSS) and new (SUCCESS/FAILED) formats
if outcome in ['WIN', 'SUCCESS']:
    # Process as winning trade
```

Applied in 4 locations:
- Line 2808 - Successful conditions
- Line 2834 - Timeframe stats
- Line 2847 - Symbol stats
- Line 2860 - Confidence accuracy

### daily_reports.py - `_convert_journal_to_signal_format()`

**Reads both formats:**
```python
# Standardize status
current_status = trade.get('status', 'PENDING')
completed_statuses = ['SUCCESS', 'FAILED', 'WIN', 'LOSS', 'COMPLETED', 'BREAKEVEN']
status = 'COMPLETED' if current_status in completed_statuses else 'ACTIVE'

# Normalize outcome - handle both old and new formats
if outcome in ['SUCCESS', 'WIN'] or profit > 0:
    result = 'WIN'
elif outcome in ['FAILED', 'LOSS'] or profit < 0:
    result = 'LOSS'
else:
    result = 'BREAKEVEN'
```

---

## Migration Strategy

### Phase 1: Dual Support (Current)
- ✅ New trades written in new format
- ✅ Old trades still readable
- ✅ All systems handle both formats
- ✅ No data migration needed

### Phase 2: Future (Optional)
- Consider batch migration of old trades
- Update documentation to deprecate old format
- Add warnings for old format usage

---

## Field Validation Rules

### Status Field Validation
```python
VALID_STATUSES = ['PENDING', 'ACTIVE', 'COMPLETED']

def validate_status(status):
    return status in VALID_STATUSES
```

### Outcome Field Validation
```python
VALID_OUTCOMES = ['SUCCESS', 'FAILED', 'BREAKEVEN', None]

def validate_outcome(outcome):
    # Outcome only valid for COMPLETED trades
    return outcome in VALID_OUTCOMES
```

### Combined Validation
```python
def validate_trade_fields(trade):
    status = trade.get('status')
    outcome = trade.get('outcome')
    
    # Status required
    if not validate_status(status):
        return False
    
    # Outcome required only if COMPLETED
    if status == 'COMPLETED':
        if not validate_outcome(outcome):
            return False
    
    return True
```

---

## Example Trade Records

### New Trade (Just Opened)
```json
{
  "id": "20251223_BTCUSDT_001",
  "symbol": "BTCUSDT",
  "status": "ACTIVE",      // ✅ Trade is running
  "outcome": null,         // ✅ Not yet determined
  "entry_price": 98500.00,
  "tp_price": 99500.00,
  "sl_price": 97500.00
}
```

### Winning Trade (Closed)
```json
{
  "id": "20251223_BTCUSDT_001",
  "symbol": "BTCUSDT",
  "status": "COMPLETED",   // ✅ Trade closed
  "outcome": "SUCCESS",    // ✅ Hit TP
  "entry_price": 98500.00,
  "exit_price": 99500.00,
  "tp_price": 99500.00,
  "sl_price": 97500.00,
  "profit_loss_pct": 1.01
}
```

### Losing Trade (Closed)
```json
{
  "id": "20251223_BTCUSDT_002",
  "symbol": "BTCUSDT",
  "status": "COMPLETED",   // ✅ Trade closed
  "outcome": "FAILED",     // ✅ Hit SL
  "entry_price": 98500.00,
  "exit_price": 97500.00,
  "tp_price": 99500.00,
  "sl_price": 97500.00,
  "profit_loss_pct": -1.01
}
```

### Legacy Trade (Old Format - Still Works)
```json
{
  "id": "20251220_BTCUSDT_001",
  "symbol": "BTCUSDT",
  "status": "WIN",         // ❌ Old format
  "outcome": "WIN",        // ❌ Old format
  "entry_price": 97000.00,
  "exit_price": 98000.00,
  "profit_loss_pct": 1.03
}
```
**Note:** Old format still processed correctly by all systems.

---

## Code References

### Writing Trades (New Format)
- **File:** `bot.py`
- **Function:** `update_trade_outcome()`
- **Lines:** 2763-2773

### Reading Trades (Both Formats)
- **File:** `bot.py`
- **Function:** `analyze_trade_patterns()`
- **Lines:** 2808, 2834, 2847, 2860

- **File:** `daily_reports.py`
- **Function:** `_convert_journal_to_signal_format()`
- **Lines:** 54-78

---

## Testing

### Test Both Formats Work
```python
# Test new format
new_trade = {
    'status': 'COMPLETED',
    'outcome': 'SUCCESS',
    'profit_loss_pct': 1.5
}
assert is_winning_trade(new_trade) == True

# Test old format
old_trade = {
    'status': 'WIN',
    'outcome': 'WIN',
    'profit_loss_pct': 1.5
}
assert is_winning_trade(old_trade) == True
```

### Test Status Detection
```python
# Completed statuses (both formats)
assert is_completed('COMPLETED') == True
assert is_completed('WIN') == True
assert is_completed('LOSS') == True
assert is_completed('SUCCESS') == True
assert is_completed('FAILED') == True

# Active statuses
assert is_completed('ACTIVE') == False
assert is_completed('PENDING') == False
```

---

## Related Documentation

- [DATA_FLOW_FIXES.md](./DATA_FLOW_FIXES.md) - Overview of all fixes
- [JOURNAL_AUTO_INIT.md](./JOURNAL_AUTO_INIT.md) - Journal initialization
- [AUDIT_REPORT.md](../AUDIT_REPORT.md) - Full system audit

---

**Last Updated:** 2025-12-23  
**Current Format:** New (Standardized)  
**Legacy Support:** ✅ Enabled  
**Migration Required:** ❌ No (automatic dual support)
