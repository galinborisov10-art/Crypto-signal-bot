# Setup State Machine - Visual Flow Diagram

## State Transition Diagram

```
                                EVALUATION CYCLE START
                                         |
                                         v
                        ┌────────────────────────────────┐
                        │  Check for Active Setup        │
                        │  key = (symbol, timeframe)     │
                        └────────────────────────────────┘
                                         |
                    ┌────────────────────┴────────────────────┐
                    |                                         |
                    v                                         v
         ┌──────────────────────┐                 ┌──────────────────────┐
         │  PATH A:             │                 │  PATH B:             │
         │  Active Setup Exists │                 │  No Active Setup     │
         └──────────────────────┘                 └──────────────────────┘
                    |                                         |
                    v                                         v
         ┌──────────────────────┐                 ┌──────────────────────┐
         │  is_entry_triggered? │                 │  Run Scenario        │
         │  (validate trigger)  │                 │  Detection           │
         └──────────────────────┘                 └──────────────────────┘
                    |                                         |
          ┌─────────┴─────────┐                    ┌─────────┴─────────┐
          |                   |                    |                   |
          v                   v                    v                   v
    ┌─────────┐         ┌─────────┐         ┌─────────┐         ┌─────────┐
    │ TRUE    │         │ FALSE   │         │ Valid   │         │ No      │
    │         │         │         │         │ Scenario│         │ Scenario│
    └─────────┘         └─────────┘         └─────────┘         └─────────┘
          |                   |                    |                   |
          v                   v                    v                   v
    ┌──────────┐        ┌──────────┐        ┌──────────┐        ┌──────────┐
    │🎯 ENTRY  │        │⏳ PENDING│        │ Check    │        │ NO_TRADE │
    │ TRIGGERED│        │ ENTRY    │        │ Trigger? │        │ "No      │
    │          │        │          │        │          │        │ scenario"│
    └──────────┘        └──────────┘        └──────────┘        └──────────┘
          |                   |                    |
          v                   v             ┌──────┴──────┐
    ┌──────────┐        ┌──────────┐       |             |
    │ Mark as  │        │Decrement │       v             v
    │Triggered │        │   TTL    │  ┌────────┐    ┌────────┐
    │          │        │          │  │ TRUE   │    │ FALSE  │
    └──────────┘        └──────────┘  │        │    │        │
          |                   |        └────────┘    └────────┘
          v                   |             |             |
    ┌──────────┐              |             v             v
    │ Remove   │              |        ┌────────┐    ┌────────┐
    │ from     │              |        │Signal  │    │ Create │
    │ Store    │              |        │Now     │    │Pending │
    └──────────┘              |        └────────┘    │ Setup  │
          |                   |             |        └────────┘
          v                   |             v             |
    ┌──────────┐              v        ┌────────┐        v
    │Continue  │        ┌──────────┐   │ Mark + │   ┌────────┐
    │to Step 8 │        │ NO_TRADE │   │ Remove │   │NO_TRADE│
    │(SL/TP/RR)│        │ "Setup   │   │        │   │"Setup  │
    └──────────┘        │ pending" │   └────────┘   │created"│
          |             └──────────┘        |        └────────┘
          v                                 v             |
     SIGNAL                            Continue          END
     EMITTED                          to Step 8
```

## State Lifecycle

### State 1: NO SETUP
```
Initial state: No active setup for (symbol, timeframe)
→ Run scenario detection
   ├─→ No scenario found → Return NO_TRADE
   └─→ Scenario found → Check trigger
       ├─→ Trigger true → Emit signal (immediate)
       └─→ Trigger false → Create pending setup → PENDING state
```

### State 2: PENDING (TTL > 0)
```
Setup exists, waiting for entry trigger
→ Check is_entry_triggered()
   ├─→ True → Emit signal → Mark triggered → Remove setup → NO SETUP
   └─→ False → Decrement TTL → Return NO_TRADE
       ├─→ TTL > 0 → Stay in PENDING
       └─→ TTL = 0 → Remove setup → NO SETUP (expired)
```

### State 3: TRIGGERED (Transient)
```
Setup triggered, signal emitted
→ mark_triggered() called
→ Setup removed from store
→ Returns to NO SETUP state
→ Ensures single-signal rule (no duplicates)
```

---

## Scenario-Specific Trigger Conditions

### ROLLBACK
**Trigger:** Price reaches break level (within entry zone)
```python
entry_low <= current_price <= entry_high
```

### PULLBACK
**Trigger:** POI retested with rejection
```python
_check_poi_retest(poi, recent_candles, bias)
→ Returns (retested=True, rejection_strength >= 0.002)
```

### CONTINUATION
**Trigger:** Reaction from OB/liquidity + impulse
```python
_candle_reacted_from_zone(candle, ob, bias) → True
AND
reaction_body >= avg_body * 1.2
```

### REVERSAL
**Trigger:** All components present + price near entry
```python
_validate_reversal_behavior(sweeps, structure_break, displacement) → True
AND
distance_pct < 1.0%
```

---

## TTL Configuration Matrix

| Timeframe | TTL Cycles | Duration Coverage |
|-----------|------------|-------------------|
| 1m        | 30         | ~30 minutes       |
| 5m        | 24         | ~2 hours          |
| 15m       | 16         | ~4 hours          |
| 1h        | 12         | ~12 hours         |
| **2h**    | **8**      | **~16 hours** ⭐  |
| 4h        | 6          | ~24 hours         |
| 1d        | 4          | ~4 days           |
| 1w        | 2          | ~2 weeks          |

⭐ Default: 8 cycles for 2h timeframe

---

## API Reference

### Entry Zone Selection
```python
entry_zone = select_entry_zone_for_scenario(
    scenario_name='ROLLBACK',
    scenario_data={...},
    ict_components={...},
    current_price=50000.0
)
# Returns: {'center', 'low', 'high', 'source', 'quality', 'distance_pct'}
```

### Entry Trigger Validation
```python
is_triggered, reason = is_entry_triggered(
    scenario_name='ROLLBACK',
    scenario_data={...},
    entry_zone={...},
    current_price=49500.0,
    ict_components={...},
    bias='BULLISH',
    timeframe='2h',
    recent_candles=[...]
)
# Returns: (bool, str)
```

### State Management
```python
manager = get_setup_manager()

# Create pending setup
setup = manager.create_setup(symbol, timeframe, scenario_name, scenario_data, entry_zone)

# Check for active setup
active = manager.get_setup(symbol, timeframe)

# Decrement TTL
still_active = manager.decrement_ttl(symbol, timeframe)

# Mark as triggered (removes setup)
manager.mark_triggered(symbol, timeframe)
```

---

## Monitoring Commands

### Setup Creation Activity
```bash
grep "🧠 SETUP_DETECTED" bot.log | tail -20
```

### Pending Setups Status
```bash
grep "⏳ SETUP_PENDING_ENTRY" bot.log | tail -20
```

### Trigger Events
```bash
grep "🎯 ENTRY_TRIGGERED" bot.log | tail -20
```

### Expiry Events
```bash
grep "⌛ SETUP_EXPIRED" bot.log | tail -20
```

### Trigger Success Rate
```bash
echo "Scale: 2
$(grep -c '🎯 ENTRY_TRIGGERED' bot.log) / $(grep -c '🧠 SETUP_DETECTED' bot.log) * 100" | bc
```

---

**Status: COMPLETE ✅**
**Ready for Production Deployment 🚀**
