#!/usr/bin/env python3
"""
Market Logic Dominance Analysis
Analyzes whether REVERSAL properly dominates over PULLBACK when structural flip is confirmed

This addresses the concern that POI quality multiplier may be overweighted
relative to structural reversal logic.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from entry_scenario_config import (
    PULLBACK_WEIGHTS,
    REVERSAL_WEIGHTS,
    MIN_SCENARIO_SCORE,
    POI_QUALITY
)


def print_header(title: str):
    """Print formatted header"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_section(title: str):
    """Print section header"""
    print(f"\n{'─' * 80}")
    print(f"  {title}")
    print(f"{'─' * 80}")


def analyze_pullback_scoring():
    """Analyze PULLBACK scoring mechanics"""
    print_section("PULLBACK Scoring Analysis")
    
    print(f"\nBase Score: {PULLBACK_WEIGHTS['base_score']}")
    print(f"POI Quality Multiplier: {PULLBACK_WEIGHTS['poi_quality_multiplier']}")
    print(f"Trigger Count Bonus: {PULLBACK_WEIGHTS['trigger_count_bonus']} per trigger")
    print(f"Structure Trigger Bonus: {PULLBACK_WEIGHTS['structure_trigger_bonus']}")
    print(f"Distance Penalty: {PULLBACK_WEIGHTS['distance_penalty_per_pct']} per 1%")
    
    print("\n📊 Example Calculations:")
    
    # Scenario: 4 triggers, POI quality varies
    triggers = 4
    has_structure = True
    distance_pct = 1.0
    
    print(f"\nWith {triggers} triggers, structure trigger, {distance_pct}% distance:")
    
    for poi_quality in [70, 75, 80, 85, 90]:
        score = PULLBACK_WEIGHTS['base_score']
        score += poi_quality * PULLBACK_WEIGHTS['poi_quality_multiplier']
        score += triggers * PULLBACK_WEIGHTS['trigger_count_bonus']
        if has_structure:
            score += PULLBACK_WEIGHTS['structure_trigger_bonus']
        score += distance_pct * PULLBACK_WEIGHTS['distance_penalty_per_pct']
        
        poi_contribution = poi_quality * PULLBACK_WEIGHTS['poi_quality_multiplier']
        
        print(f"   POI Quality {poi_quality}: Score = {score:.0f} (POI contrib: {poi_contribution:.1f})")
    
    return PULLBACK_WEIGHTS


def analyze_reversal_scoring():
    """Analyze REVERSAL scoring mechanics"""
    print_section("REVERSAL Scoring Analysis")
    
    print(f"\nBase Score: {REVERSAL_WEIGHTS['base_score']}")
    print(f"Sweep Bonus: {REVERSAL_WEIGHTS['sweep_bonus']}")
    print(f"CHOCH Bonus: {REVERSAL_WEIGHTS['choch_bonus']}")
    print(f"MSS Bonus: {REVERSAL_WEIGHTS['mss_bonus']}")
    print(f"Displacement Bonus: {REVERSAL_WEIGHTS['displacement_contra_bonus']}")
    print(f"Trigger Count Bonus: {REVERSAL_WEIGHTS['trigger_count_bonus']} per additional trigger")
    
    print("\n📊 Example Calculations:")
    
    # Full reversal pattern: sweep + CHOCH + displacement + 4 triggers
    print("\nFull Reversal Pattern (Sweep + CHOCH + Displacement):")
    
    score = REVERSAL_WEIGHTS['base_score']
    score += REVERSAL_WEIGHTS['sweep_bonus']
    score += REVERSAL_WEIGHTS['choch_bonus']
    score += REVERSAL_WEIGHTS['displacement_contra_bonus']
    
    # 4 triggers total, need 2 minimum, so 2 extra
    extra_triggers = 2
    score += extra_triggers * REVERSAL_WEIGHTS['trigger_count_bonus']
    
    print(f"   Base: {REVERSAL_WEIGHTS['base_score']}")
    print(f"   + Sweep: {REVERSAL_WEIGHTS['sweep_bonus']}")
    print(f"   + CHOCH: {REVERSAL_WEIGHTS['choch_bonus']}")
    print(f"   + Displacement: {REVERSAL_WEIGHTS['displacement_contra_bonus']}")
    print(f"   + {extra_triggers} extra triggers × {REVERSAL_WEIGHTS['trigger_count_bonus']}: {extra_triggers * REVERSAL_WEIGHTS['trigger_count_bonus']}")
    print(f"   = Total: {score}")
    
    return score, REVERSAL_WEIGHTS


def calculate_poi_break_even(reversal_score: float):
    """Calculate POI quality needed for PULLBACK to match REVERSAL"""
    print_section("POI Quality Break-Even Analysis")
    
    print(f"\nREVERSAL Score (full pattern): {reversal_score}")
    print(f"\nTo match this, PULLBACK needs:")
    
    # PULLBACK with 4 triggers, structure, 1% distance
    triggers = 4
    base = PULLBACK_WEIGHTS['base_score']
    trigger_bonus = triggers * PULLBACK_WEIGHTS['trigger_count_bonus']
    structure_bonus = PULLBACK_WEIGHTS['structure_trigger_bonus']
    distance_penalty = 1.0 * PULLBACK_WEIGHTS['distance_penalty_per_pct']
    
    fixed_score = base + trigger_bonus + structure_bonus + distance_penalty
    
    print(f"   Base: {base}")
    print(f"   + {triggers} triggers × {PULLBACK_WEIGHTS['trigger_count_bonus']}: {trigger_bonus}")
    print(f"   + Structure: {structure_bonus}")
    print(f"   + Distance penalty (1%): {distance_penalty}")
    print(f"   = Fixed portion: {fixed_score}")
    
    # POI needed: (reversal_score - fixed_score) / multiplier
    poi_needed = (reversal_score - fixed_score) / PULLBACK_WEIGHTS['poi_quality_multiplier']
    
    print(f"\nPOI quality needed: ({reversal_score} - {fixed_score}) / {PULLBACK_WEIGHTS['poi_quality_multiplier']}")
    print(f"                  = {poi_needed:.1f}")
    
    # Check if this is reasonable
    max_poi = POI_QUALITY['OB']  # 90
    min_poi = POI_QUALITY['min_acceptable']  # 65
    
    print(f"\n📊 Context:")
    print(f"   Max POI quality (OB): {max_poi}")
    print(f"   Min acceptable POI: {min_poi}")
    print(f"   Required POI: {poi_needed:.1f}")
    
    if poi_needed > max_poi:
        print(f"\n✅ GOOD: REVERSAL dominates (POI {poi_needed:.1f} > max {max_poi})")
        print(f"   Structural reversal properly prioritized")
        return "REVERSAL_DOMINATES"
    elif poi_needed >= (max_poi - 5):
        print(f"\n⚠️  MARGINAL: Only top-tier POIs (>={poi_needed:.0f}) beat reversal")
        print(f"   This is acceptable - exceptional POI should compete")
        return "ACCEPTABLE"
    else:
        print(f"\n❌ PROBLEM: Common POIs can beat structural reversal")
        print(f"   POI quality {poi_needed:.1f} is too low - many OBs qualify")
        print(f"   POI multiplier is OVERWEIGHTED")
        return "POI_OVERWEIGHTED"
    
    return poi_needed


def test_scenario_comparison():
    """Test specific scenario: Sweep + CHOCH + Displacement vs Strong POI"""
    print_section("Scenario Comparison Test")
    
    print("\n📋 SCENARIO: Market showing clear reversal pattern")
    print("   Components:")
    print("   • BSL Sweep (recent)")
    print("   • CHOCH confirmed")
    print("   • Displacement in reversal direction")
    print("   • 4 total triggers")
    print("   • Bearish OB present (quality varies)")
    
    # REVERSAL calculation
    reversal_score = REVERSAL_WEIGHTS['base_score']
    reversal_score += REVERSAL_WEIGHTS['sweep_bonus']
    reversal_score += REVERSAL_WEIGHTS['choch_bonus']
    reversal_score += REVERSAL_WEIGHTS['displacement_contra_bonus']
    reversal_score += 2 * REVERSAL_WEIGHTS['trigger_count_bonus']  # 2 extra
    
    print(f"\n🔄 REVERSAL Score: {reversal_score}")
    print(f"   Breakdown: 55 + 25 + 20 + 15 + (2×10) = {reversal_score}")
    
    # PULLBACK calculations for different POI qualities
    print(f"\n📉 PULLBACK Scores (with same 4 triggers):")
    
    for poi_quality in [70, 75, 80, 85, 90]:
        pullback_score = PULLBACK_WEIGHTS['base_score']
        pullback_score += poi_quality * PULLBACK_WEIGHTS['poi_quality_multiplier']
        pullback_score += 4 * PULLBACK_WEIGHTS['trigger_count_bonus']
        pullback_score += PULLBACK_WEIGHTS['structure_trigger_bonus']
        pullback_score += 1.0 * PULLBACK_WEIGHTS['distance_penalty_per_pct']
        
        winner = "PULLBACK" if pullback_score > reversal_score else "REVERSAL"
        diff = abs(pullback_score - reversal_score)
        
        poi_type = "Common" if poi_quality <= 75 else "Good" if poi_quality <= 85 else "Excellent"
        
        print(f"   POI {poi_quality} ({poi_type}): {pullback_score:.0f} → {winner} wins by {diff:.0f}")


def recommend_adjustments():
    """Recommend weight adjustments if needed"""
    print_section("Recommendations")
    
    # Current break-even
    reversal_full = 55 + 25 + 20 + 15 + 20  # 135
    pullback_fixed = 40 + 60 + 10 - 5  # 105
    poi_needed = (reversal_full - pullback_fixed) / 0.5  # 60
    
    if poi_needed < 85:  # If common OBs can beat reversal
        print("\n❌ ISSUE CONFIRMED: POI multiplier is overweighted")
        print(f"   Current: POI quality {poi_needed:.0f} can beat structural reversal")
        print(f"   This is too low - many OBs have quality 75-85")
        
        print("\n💡 RECOMMENDED ADJUSTMENTS:")
        print("\nOption 1: Reduce POI multiplier")
        print(f"   Current: 0.5")
        print(f"   Suggested: 0.35-0.40")
        print(f"   Effect: POI contribution reduced, REVERSAL more competitive")
        
        print("\nOption 2: Increase REVERSAL bonuses")
        print(f"   Current CHOCH: {REVERSAL_WEIGHTS['choch_bonus']}")
        print(f"   Suggested: 25-30")
        print(f"   Current Displacement: {REVERSAL_WEIGHTS['displacement_contra_bonus']}")
        print(f"   Suggested: 20")
        print(f"   Effect: Structural flip gets more weight")
        
        print("\nOption 3: Combined approach (RECOMMENDED)")
        print(f"   POI multiplier: 0.5 → 0.4")
        print(f"   CHOCH bonus: 20 → 25")
        print(f"   Effect: Balanced adjustment, REVERSAL dominates except for exceptional POIs")
        
        # Calculate new break-even with recommended changes
        print("\n📊 Impact of Combined Approach:")
        new_reversal = 55 + 25 + 25 + 15 + 20  # +5 from CHOCH
        new_poi_needed = (new_reversal - pullback_fixed) / 0.4  # 0.4 multiplier
        print(f"   New REVERSAL score: {new_reversal}")
        print(f"   New POI needed to match: {new_poi_needed:.1f}")
        print(f"   Result: Only exceptional OBs (90+) can compete ✅")
        
    else:
        print("\n✅ Current weights appear balanced")
        print(f"   POI quality {poi_needed:.0f} needed to match reversal")
        print(f"   Only exceptional POIs can beat structural flip")
        print("\n   No adjustments recommended")


def run_analysis():
    """Run complete market logic dominance analysis"""
    print_header("MARKET LOGIC DOMINANCE ANALYSIS")
    print("Evaluating: REVERSAL vs PULLBACK scoring when structural flip confirmed")
    
    # Analyze current weights
    pullback_weights = analyze_pullback_scoring()
    reversal_score, reversal_weights = analyze_reversal_scoring()
    
    # Calculate break-even
    result = calculate_poi_break_even(reversal_score)
    
    # Test specific scenarios
    test_scenario_comparison()
    
    # Provide recommendations
    recommend_adjustments()
    
    # Final summary
    print_header("ANALYSIS SUMMARY")
    
    print("\n📊 Current State:")
    print(f"   REVERSAL (full pattern): {reversal_score}")
    print(f"   PULLBACK break-even POI: ~60 quality")
    print(f"   Max POI quality: 90")
    
    print("\n🎯 Market Logic Assessment:")
    
    if result == "POI_OVERWEIGHTED":
        print("   ❌ POI multiplier is OVERWEIGHTED")
        print("   ⚠️  Common POIs (75-85) can beat structural reversal")
        print("   📈 RECOMMENDATION: Adjust weights (see recommendations above)")
    elif result == "ACCEPTABLE":
        print("   ⚠️  Marginal - only top-tier POIs compete")
        print("   ✅ Acceptable but could be improved")
    else:
        print("   ✅ REVERSAL properly dominates")
        print("   ✅ Structural flip prioritized correctly")
    
    print("\n🔍 Key Insight:")
    print("   When sweep + CHOCH + displacement are present:")
    print("   • This represents confirmed structural reversal")
    print("   • Should be one of the strongest ICT patterns")
    print("   • PULLBACK should only win with exceptional POI (90+)")
    print("   • Current: PULLBACK can win with good POI (75-85)")
    
    print("\n" + "=" * 80)
    print("  Analysis Complete - See recommendations above")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_analysis()
