# PR: Setup State Machine + POI Persistence + Signal Only on Entry Trigger

## 📋 Summary

This PR implements a state machine that separates **setup detection** from **signal emission**. Previously, signals were emitted immediately when a scenario was detected. Now, the system:

1. **Detects a valid setup** (scenario + entry zone)
2. **Stores it as pending** with TTL tracking
3. **Waits for entry trigger** conditions to be met
4. **Emits signal only when triggered**

This prevents premature signals and ensures entries happen at optimal price levels.

---

## 🔍 Phase 1: Files and Functions Changed

### Modified Files
1. **`entry_scenarios.py`** (+214 lines)
   - Added `select_entry_zone_for_scenario()` - extracts entry zone from scenario data
   - Added `is_entry_triggered()` - validates if entry conditions are met (197 lines)
   - Reuses existing validation functions: `_check_poi_retest()`, `_candle_reacted_from_zone()`, `_validate_reversal_behavior()`

2. **`ict_signal_engine.py`** (+188 / -190 lines, net: -2 lines)
   - Updated imports to include new functions and setup manager
   - Rewired Step 7 (Entry Scenario Selection) to use state machine
   - Two paths implemented:
     - PATH A: Active setup exists → check trigger → signal or wait
     - PATH B: No setup → detect scenario → create pending or signal if immediate

3. **`setup_state_manager.py`** (NEW FILE, 220 lines)
   - `SetupState` dataclass - stores scenario, entry_zone, TTL
   - `SetupStateManager` class - manages in-memory setup store
   - TTL configuration by timeframe (8 cycles for 2h default)
   - Singleton pattern via `get_setup_manager()`

### Test Files Created
4. **`tests/test_entry_zone_selection.py`** (270 lines) - 4 tests
5. **`tests/test_setup_state_machine.py`** (530 lines) - 8 tests
6. **`tests/test_integration_state_machine.py`** (355 lines) - 3 integration tests

**Total: 1,777 lines added, 190 lines removed**

---

## 🎯 Key Changes by Phase

### Phase 2: Entry Zone Selection (API Layer)
```python
def select_entry_zone_for_scenario(
    scenario_name: str,
    scenario_data: Dict,
    ict_components: Dict,
    current_price: float
) -> Optional[Dict]
```
- Returns pre-computed entry zone from scenario data
- Maintains 1:1 compatibility with existing behavior
- Enables future refactoring without breaking changes

### Phase 3: Entry Trigger Extraction
```python
def is_entry_triggered(
    scenario_name: str,
    scenario_data: Dict,
    entry_zone: Dict,
    current_price: float,
    ict_components: Dict,
    bias: str,
    timeframe: str,
    recent_candles: List = None
) -> Tuple[bool, str]
```

Scenario-specific logic (extracted, not invented):
- **ROLLBACK**: Price reaches break level (within entry zone tolerance)
- **PULLBACK**: POI retested with rejection (calls `_check_poi_retest()`)
- **CONTINUATION**: Reaction from OB/liquidity + impulse (calls `_candle_reacted_from_zone()`)
- **REVERSAL**: All components present + price near entry (calls `_validate_reversal_behavior()`)

### Phase 4: Setup State Machine
```python
class SetupState:
    symbol: str
    timeframe: str
    scenario_name: str
    scenario_data: Dict
    entry_zone: Dict
    ttl_remaining: int
    created_at: datetime
    last_checked_at: datetime
```

TTL measured in **evaluation cycles** (not candle timestamps):
```python
TTL_CYCLES_BY_TIMEFRAME = {
    '1m': 30,   # 30 minutes
    '5m': 24,   # 2 hours
    '1h': 12,   # 12 hours
    '2h': 8,    # 16 hours (default)
    '4h': 6,    # 24 hours
    '1d': 4,    # 4 days
    '1w': 2     # 2 weeks
}
```

### Phase 5: Engine Rewiring
**Before:**
```
Scenario detected → Immediate signal emission
```

**After:**
```
┌─────────────────────────────────────┐
│  Evaluation Cycle                   │
└─────────────────────────────────────┘
         │
         ├─→ Active setup exists? ─────YES─→ Check entry trigger
         │                                    ├─→ Triggered? ─YES─→ Emit signal
         │                                    └─→ No? ──→ Decrement TTL, return NO_TRADE
         │
         └─→ No setup ─────────────→ Run scenario detection
                                     ├─→ No scenario? ──→ Return NO_TRADE
                                     └─→ Scenario found ─→ Check trigger
                                                          ├─→ Immediate? ─→ Emit signal
                                                          └─→ No? ─→ Create pending setup, return NO_TRADE
```

---

## ✅ Acceptance Criteria Validation

| Criterion | Status | Evidence |
|-----------|--------|----------|
| 1. System enters PENDING_ENTRY state | ✅ | `test_setup_detected_stored_as_pending()` passes |
| 2. Signal only on entry trigger | ✅ | Engine checks `is_entry_triggered()` before emission |
| 3. "No eligible scenarios" not the only outcome | ✅ | Now returns "Setup pending entry trigger" |
| 4. No changes to SL/TP/RR/confidence | ✅ | No modifications to Steps 8-12 |
| 5. Unit tests added and passing | ✅ | 15 tests, all passing |
| 6. Backwards compatibility | ✅ | `scenario["entry_zone"]` still populated |
| 7. Single-signal rule | ✅ | `mark_triggered()` removes setup after emission |

---

## 🧪 Test Results

### Entry Zone Selection Tests (4/4 passing)
```
✅ TEST 1: CONTINUATION Entry Zone with OB
✅ TEST 2: ROLLBACK Entry Zone with Break Level
✅ TEST 3: REVERSAL Entry Zone with Sweep
✅ TEST 4: PULLBACK Entry Zone with POI
```

### State Machine Tests (8/8 passing)
```
✅ TEST 1: Setup Detected → Stored as Pending
✅ TEST 2: Setup Pending → TTL Decreased
✅ TEST 3: Entry Triggered → Signal Emitted Once
✅ TEST 4: TTL Expires → Setup Removed
✅ TEST 5: Entry Trigger - ROLLBACK (Price in Zone)
✅ TEST 6: Entry Trigger - CONTINUATION (With Reaction)
✅ TEST 7: Multiple Setups (Different Symbols)
✅ TEST 8: TTL Configuration by Timeframe
```

### Integration Tests (3/3 passing)
```
✅ Full State Machine Flow (6 cycles: pending → trigger → signal)
✅ TTL Expiry Flow (6 cycles: pending → expired, no signal)
✅ Immediate Trigger Flow (trigger true on detection → immediate signal)
```

---

## 📊 Behavior Changes

### Before This PR
- Scenario detected → Signal emitted immediately
- "No eligible scenarios" → NO_TRADE
- All validation happens at detection time

### After This PR
- Scenario detected → Setup stored → Wait for trigger → Signal on trigger
- "No eligible scenarios" → NO_TRADE
- "Setup pending entry trigger" → NO_TRADE (NEW)
- Validation split: setup validation at detection, trigger validation on each cycle

---

## 🔒 Backwards Compatibility

### Preserved Behavior
- All scenario scoring math unchanged (probabilities, weights, thresholds)
- All detection algorithms unchanged (HTF bias, liquidity, OB/FVG, sweeps)
- All SL/TP/RR/confidence calculations unchanged
- `scenario["entry_zone"]` field still populated and available

### New Behavior (Additive Only)
- Setup can exist in PENDING state (new capability)
- Signals delayed until trigger conditions met (refinement)
- TTL-based expiry for stale setups (safety feature)

---

## 🚀 Usage Examples

### Example 1: ROLLBACK Setup Lifecycle
```
Cycle 1: BOS detected at $49,500, current price $50,000
         → Setup created (TTL=8)
         → NO_TRADE: "Setup pending entry trigger (ROLLBACK pending: 1.0% away)"

Cycle 2: Price at $49,900 (TTL=7)
         → NO_TRADE: "Setup pending entry trigger (ROLLBACK pending: 0.8% away)"

Cycle 3: Price reaches $49,500 (TTL=6)
         → ✅ SIGNAL EMITTED: "ROLLBACK triggered: Price reached break level @ $49,500"
         → Setup removed (single-signal rule)
```

### Example 2: PULLBACK Setup Expiry
```
Cycle 1: OB detected at $49,100, current price $50,000
         → Setup created (TTL=8)
         → NO_TRADE: "Setup pending entry trigger (PULLBACK pending: 1.8% from POI)"

Cycles 2-8: Price never retests POI, TTL decrements each cycle
         → NO_TRADE on each cycle

Cycle 9: TTL reaches 0
         → Setup expired
         → Next cycle will re-evaluate (may detect new setup or return "No eligible scenarios")
```

---

## 🔧 Technical Details

### State Machine Key
```python
key = (symbol, timeframe)  # e.g., ('BTCUSDT', '2h')
```

### TTL Decrement Logic
- Decrements by 1 on each evaluation cycle where trigger is false
- When TTL reaches 0, setup is removed
- Expired setups are re-evaluated on next cycle (may create new setup)

### Single-Signal Rule Implementation
```python
# After signal emission
setup_manager.mark_triggered(symbol, timeframe)
# → Removes setup from store
# → Subsequent cycles have no active setup
# → No duplicate signals possible
```

---

## 📝 Code Review Checklist

- [ ] No new entry trigger logic invented (✅ reuses existing checks)
- [ ] No scenario scoring changes (✅ no probability/weight modifications)
- [ ] No SL/TP/RR/confidence changes (✅ Steps 8-12 untouched)
- [ ] No detection algorithm changes (✅ HTF/liquidity/OB/sweeps unchanged)
- [ ] Tests comprehensive (✅ 15 tests covering all scenarios)
- [ ] Logging added (✅ 4 transition logs)
- [ ] Single-signal rule enforced (✅ via `mark_triggered()`)
- [ ] Backwards compatible (✅ `entry_zone` field preserved)

---

## 🎓 Next Steps (Post-Merge)

1. Monitor production logs for state transitions:
   - `🧠 SETUP_DETECTED` - setup creation rate
   - `⏳ SETUP_PENDING_ENTRY` - average pending duration
   - `🎯 ENTRY_TRIGGERED` - trigger success rate
   - `⌛ SETUP_EXPIRED` - expiry rate (should be low)

2. Tune TTL values based on real data if needed

3. Consider adding setup invalidation logic (future enhancement):
   - Context changes (HTF bias flip)
   - Structural invalidation (new contrary structure)
   - Manual override/cancellation

---

**Implementation Status: COMPLETE ✅**
**Tests Status: 15/15 PASSING ✅**
**Ready for Code Review ✅**
