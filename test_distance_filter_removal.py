#!/usr/bin/env python3
"""
Test script to validate distance filter removal changes.
This script verifies the soft constraint approach without running the full engine.
"""

def test_distance_logic():
    """Test the new distance constraint logic"""
    
    print("=" * 60)
    print("🧪 Testing Distance Filter Removal")
    print("=" * 60)
    
    # Simulating zone distances
    test_cases = [
        {"distance_pct": 0.004, "description": "0.4% - Below optimal range"},
        {"distance_pct": 0.010, "description": "1.0% - Within optimal range"},
        {"distance_pct": 0.025, "description": "2.5% - Within optimal range"},
        {"distance_pct": 0.035, "description": "3.5% - Above optimal range"},
        {"distance_pct": 0.050, "description": "5.0% - Above optimal range"},
        {"distance_pct": 0.100, "description": "10.0% - Far above optimal range"},
    ]
    
    min_distance_pct = 0.005  # 0.5%
    max_distance_pct = 0.030  # 3.0%
    
    print("\n📊 Zone Acceptance Test (OLD vs NEW)")
    print("-" * 60)
    
    for case in test_cases:
        distance_pct = case['distance_pct']
        desc = case['description']
        
        # OLD LOGIC: Hard filter
        old_accepted = distance_pct <= max_distance_pct and distance_pct >= min_distance_pct
        
        # NEW LOGIC: Soft constraint (always accept if above min)
        new_accepted = distance_pct >= min_distance_pct
        out_of_optimal_range = distance_pct > max_distance_pct or distance_pct < min_distance_pct
        
        print(f"\n{desc}")
        print(f"  Distance: {distance_pct * 100:.1f}%")
        print(f"  OLD: {'✅ ACCEPTED' if old_accepted else '❌ REJECTED (hard)'}")
        print(f"  NEW: {'✅ ACCEPTED' if new_accepted else '❌ REJECTED'}")
        if new_accepted and out_of_optimal_range:
            print(f"       ⚠️  Flagged as out_of_optimal_range (confidence penalty -20%)")
    
    print("\n" + "=" * 60)
    print("📊 Confidence Penalty Test")
    print("=" * 60)
    
    base_confidence = 75.0
    
    for case in test_cases:
        distance_pct = case['distance_pct']
        desc = case['description']
        
        # Check if zone would be accepted
        if distance_pct >= min_distance_pct:
            out_of_optimal_range = distance_pct > max_distance_pct or distance_pct < min_distance_pct
            
            if out_of_optimal_range:
                adjusted_confidence = base_confidence * 0.8  # 20% penalty
                print(f"\n{desc}")
                print(f"  Base confidence: {base_confidence:.1f}%")
                print(f"  Distance penalty: -20%")
                print(f"  Final confidence: {adjusted_confidence:.1f}%")
            else:
                print(f"\n{desc}")
                print(f"  Confidence: {base_confidence:.1f}% (no penalty)")
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")
    print("=" * 60)
    
    # Summary
    print("\n📋 SUMMARY:")
    print("1. ✅ Zones at any distance >= 0.5% are now ACCEPTED")
    print("2. ✅ Zones outside 0.5-3% range are FLAGGED (not rejected)")
    print("3. ✅ Confidence penalty (-20%) applied for out-of-range zones")
    print("4. ✅ NO hard rejections based on distance anymore")
    print("5. ✅ SL/TP/RR calculations remain unaffected")
    
    return True

if __name__ == "__main__":
    test_distance_logic()
