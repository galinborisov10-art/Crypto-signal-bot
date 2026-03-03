# Architectural Consideration: Distance Weighting - RESOLVED

## Problem Statement

Should POI selection use:
1. **Weighted scoring** (distance 60% + strength 40%)?
2. **Strength-only** (ignore distance entirely)?
3. **Strength-first with distance tiebreaker** (compromise)?

---

## Decision: Strength-First with Distance Tiebreaker ✅

### Implementation
```python
best_poi = max(candidates, key=lambda x: (x['quality'], -x['distance_pct']))
```

This means:
1. **Primary:** Select POI with highest strength
2. **Tiebreaker:** If multiple POIs have same strength, select closest
3. **Distance penalties:** Preserved in probability calculation (compromise)

---

## Rationale

### Why NOT Weighted Scoring?

**Weighted approach:**
```python
weighted_score = distance_score * 0.6 + strength * 0.4
best_poi = max(candidates, key=lambda x: x['weighted_score'])
```

**Problems:**
- ❌ Violates single-gate architecture (re-weights distance after entry zone validation)
- ❌ Adds complexity (additional calculation)
- ❌ Distance validated twice (once in entry zone, again in weighting)
- ❌ May select weaker POI just because it's closer

**Example conflict:**
- POI A: strength=70, distance=6% → weighted_score = (7-6)/7*100*0.6 + 70*0.4 = 36.6
- POI B: strength=50, distance=2% → weighted_score = (7-2)/7*100*0.6 + 50*0.4 = 62.9
- **Weighted would select B** (weaker but closer)
- **Problem:** Violates ICT principle that stronger levels are more reliable

### Why NOT Strength-Only?

**Strength-only approach:**
```python
best_poi = max(candidates, key=lambda x: x['quality'])
```

**Problems:**
- ❌ Ignores distance entirely
- ❌ May select 7% POI when 2% POI has same strength
- ❌ Not practical (execution timing matters)

**Example issue:**
- POI A: strength=70, distance=7%
- POI B: strength=70, distance=2%
- **Would arbitrarily select one** (no tiebreaker)
- **Problem:** Entry timing is important for execution

### Why Strength-First + Distance Tiebreaker? ✅

**Chosen approach:**
```python
best_poi = max(candidates, key=lambda x: (x['quality'], -x['distance_pct']))
```

**Benefits:**
- ✅ **Clean architecture:** No distance re-weighting (true single-gate)
- ✅ **ICT aligned:** Quality is primary consideration
- ✅ **Practical:** Distance matters when strength is equal
- ✅ **Simple:** No additional calculations
- ✅ **Balanced:** Distance penalties in probability provide nuance

**Example behavior:**
- POI A: strength=70, distance=6%
- POI B: strength=50, distance=2%
- **Selects A** (stronger, even though farther) ✅ ICT principle
- But if:
- POI A: strength=70, distance=6%
- POI C: strength=70, distance=2%
- **Selects C** (same strength, closer) ✅ Practical

---

## Trade-off Analysis

| Approach | Architecture | ICT Aligned | Practical | Complexity |
|----------|-------------|-------------|-----------|------------|
| Weighted | ❌ Violates single-gate | ❌ Distance > strength | ✅ Good timing | ❌ High |
| Strength-only | ✅ Pure single-gate | ✅ Quality first | ❌ Ignores timing | ✅ Low |
| **Strength + tiebreaker** | **✅ True single-gate** | **✅ Quality first** | **✅ Considers timing** | **✅ Low** |

---

## Compromise Elements Preserved

While using strength-first selection, we **preserved distance penalties in probability calculations** as a compromise:

```python
# In _calculate_probability_rollback and _calculate_probability_pullback
distance_penalty_factor = min(distance_pct / 7.0, 1.0)
probability -= distance_penalty_factor * PROBABILITY_CONTRIBUTIONS['distance_penalty']
```

**Why keep penalties:**
- Provides nuanced consideration of distance
- Doesn't violate single-gate (happens after selection)
- Balances architecture purity with practicality
- Closer entries get higher probability (more likely to execute)

---

## Single-Gate Architecture Maintained

### ✅ Distance validated ONCE:
```
Entry Zone Calculation (line 3829):
    max_distance_pct = 0.070
    if distance > 7%: REJECT (TOO_FAR)
```

### ✅ POI selection uses passed candidates:
```
Scenario Scoring (line 1045):
    # All candidates already validated ≤ 7%
    best_poi = max(candidates, key=lambda x: (x['quality'], -x['distance_pct']))
    # No re-validation, no re-weighting
```

### ✅ Distance penalties (post-selection):
```
Probability Calculation (line 354):
    # Influences final probability, not selection
    distance_penalty_factor = min(distance_pct / 7.0, 1.0)
```

**Result:** Distance validated once (entry zone), used for selection tiebreaker, penalized in probability. No re-weighting. Clean single-gate.

---

## Example Scenarios

### Scenario 1: Different Strengths
**Candidates:**
- OB A: strength=70, distance=6%
- OB B: strength=50, distance=2%

**Selection:** OB A (strength 70 > 50)  
**Rationale:** Stronger level more reliable (ICT principle)  
**Probability:** A penalized more for distance, but still selected

### Scenario 2: Equal Strengths
**Candidates:**
- OB A: strength=70, distance=6%
- OB B: strength=70, distance=2%

**Selection:** OB B (distance 2% < 6% as tiebreaker)  
**Rationale:** Equal quality, prefer closer for better execution  
**Probability:** B gets higher probability (lower distance penalty)

### Scenario 3: All Candidates Fresh
**Candidates:**
- OB A: strength=70, distance=2%
- OB B: strength=65, distance=1.5%

**Selection:** OB A (strength 70 > 65)  
**Rationale:** Quality matters even when both very close  
**Probability:** Both high probability (minimal distance penalty)

---

## Conclusion

**Strength-first with distance tiebreaker** is the optimal solution:

✅ **Maintains single-gate architecture** (no re-weighting)  
✅ **Aligns with ICT principles** (quality > proximity)  
✅ **Practical** (considers distance when relevant)  
✅ **Simple** (no complex calculations)  
✅ **Balanced** (distance penalties provide nuance)  

This approach provides the **cleanest architecture** while remaining **practical and ICT-compliant**.

---

## Implementation Status

✅ Implemented in commit `d896210`  
✅ Code review feedback addressed in commit `2f60534`  
✅ All tests pass (7/7)  
✅ CodeQL scan clean (0 alerts)  
✅ Ready for merge  

**Branch:** `copilot/refactor-distance-weighting`  
**Status:** COMPLETE ✅
