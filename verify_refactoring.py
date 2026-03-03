#!/usr/bin/env python3
"""
Verification script for ICT Signal Engine Single-Gate Architecture refactoring.
Checks that all required changes were implemented correctly.
"""

import re
import sys

def check_file(filename, checks):
    """Check a file for specific patterns"""
    print(f"\n{'='*60}")
    print(f"Checking: {filename}")
    print('='*60)
    
    try:
        with open(filename, 'r') as f:
            content = f.read()
        
        all_passed = True
        for check_name, pattern, should_exist in checks:
            if should_exist:
                if re.search(pattern, content, re.MULTILINE):
                    print(f"✅ {check_name}")
                else:
                    print(f"❌ {check_name} - NOT FOUND")
                    all_passed = False
            else:
                if re.search(pattern, content, re.MULTILINE):
                    print(f"❌ {check_name} - STILL EXISTS (should be removed)")
                    all_passed = False
                else:
                    print(f"✅ {check_name} - Correctly removed")
        
        return all_passed
    except FileNotFoundError:
        print(f"❌ File not found: {filename}")
        return False

def main():
    print("\n" + "="*60)
    print("ICT SIGNAL ENGINE REFACTORING VERIFICATION")
    print("="*60)
    
    results = []
    
    # CHANGE 1: _filter_quality_components updates
    results.append(check_file('ict_signal_engine.py', [
        ("Function accepts timeframe parameter", 
         r"def _filter_quality_components\(self, raw_components: Dict, timeframe: str\)", True),
        ("Timeframe-based thresholds (15m-2h)", 
         r"if timeframe in \['15m', '30m', '1h', '2h'\]:", True),
        ("Timeframe-based thresholds (4h-1w)", 
         r"elif timeframe in \['4h', '1d', '1w'\]:", True),
        ("OB strength threshold = 30", 
         r"min_ob_strength = 30", True),
        ("OB age threshold = 30", 
         r"max_component_age = 30", True),
        ("OB strength threshold = 35", 
         r"min_ob_strength = 35", True),
        ("OB age threshold = 40", 
         r"max_component_age = 40", True),
        ("Apply age filter to OB", 
         r"candles_ago <= max_component_age", True),
        ("Apply age filter to Liquidity Sweeps", 
         r"candles_ago <= max_component_age.*# Use timeframe-based threshold", True),
    ]))
    
    # CHANGE 2: Entry zone distance 5% → 7%
    results.append(check_file('ict_signal_engine.py', [
        ("max_distance_pct = 0.070", 
         r"max_distance_pct = 0\.070", True),
        ("Documentation updated to 7%", 
         r"UNIVERSAL 7% MAX", True),
        ("Old 5% reference removed", 
         r"max_distance_pct = 0\.050", False),
    ]))
    
    results.append(check_file('entry_scenario_config.py', [
        ("PULLBACK_DISTANCE max_pct = 0.07", 
         r"'max_pct': 0\.07.*# 7\.0%.*\(increased from 5%\)", True),
        ("ROLLBACK_DISTANCE max_pct = 0.07", 
         r"'max_pct': 0\.07.*# 7\.0%.*\(increased from 5%\)", True),
        ("REVERSAL_DISTANCE max_pct = 0.07", 
         r"'max_pct': 0\.07.*# 7\.0%.*\(increased from 5%\)", True),
    ]))
    
    # CHANGE 3: Remove duplicate gates from scenarios
    results.append(check_file('entry_scenarios.py', [
        ("Pullback: No distance gate", 
         r"if distance_pct > 5\.0:", False),
        ("Pullback: Single-gate documentation", 
         r"✅ SINGLE-GATE: Only validates CORE structure behavior", True),
        ("Continuation: No age gate", 
         r"if candles_ago is not None and candles_ago > 20:", False),
        ("Reversal: No age gate (sweep)", 
         r"if sweep_candles_ago > 10:", False),
        ("Rollback: No age gate", 
         r"if candles_ago is not None and candles_ago > 25:", False),
    ]))
    
    # CHANGE 4: Weighted POI selection
    results.append(check_file('entry_scenarios.py', [
        ("Weighted score calculation", 
         r"weighted_score = distance_score \* 0\.6 \+ strength \* 0\.4", True),
        ("Distance score formula", 
         r"distance_score = max\(0, \(7\.0 - distance_pct\) / 7\.0 \* 100\)", True),
        ("No hard quality filter", 
         r"poi_candidates = \[p for p in poi_candidates if p\['quality'\] >= POI_QUALITY\['min_acceptable'\]\]", False),
        ("Select by weighted score", 
         r"best_poi = max\(poi_candidates, key=lambda x: x\['weighted_score'\]\)", True),
        ("Distance penalty uses 7.0", 
         r"distance_penalty_factor = min\(distance_pct / 7\.0, 1\.0\)", True),
    ]))
    
    # Summary
    print("\n" + "="*60)
    print("VERIFICATION SUMMARY")
    print("="*60)
    
    if all(results):
        print("✅ ALL CHECKS PASSED")
        print("\nThe refactoring has been successfully implemented:")
        print("  1. ✅ Timeframe-based component filtering")
        print("  2. ✅ Entry distance increased to 7%")
        print("  3. ✅ Duplicate gates removed from scenarios")
        print("  4. ✅ Weighted POI selection implemented")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("\nPlease review the failed checks above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
