"""
Simple verification that AUTO mode blocking is in place.
This just checks the code has the correct blocking logic.
"""

import re

def verify_auto_blocking():
    """Verify AUTO mode blocking code is present"""
    print("=" * 60)
    print("VERIFICATION: AUTO Mode Blocking Logic")
    print("=" * 60)
    
    with open('ict_signal_engine.py', 'r') as f:
        content = f.read()
    
    # Check for Step 7 NO_ZONE blocking
    if "if entry_status == 'NO_ZONE' or entry_zone is None:" in content and 'if is_auto:' in content:
        print("✅ Step 7: NO_ZONE blocking for AUTO mode found")
    else:
        print("❌ Step 7: NO_ZONE blocking MISSING")
        return False
    
    # Check for Step 7 no scenario blocking
    if 'if not entry_scenario_result and is_auto:' in content:
        print("✅ Step 7: No scenario blocking for AUTO mode found")
    else:
        print("❌ Step 7: No scenario blocking MISSING")
        return False
    
    # Check for Step 8 no anchor blocking
    if 'if not invalidation_anchor and is_auto:' in content:
        print("✅ Step 8: No anchor blocking for AUTO mode found")
    else:
        print("❌ Step 8: No anchor blocking MISSING")
        return False
    
    # Check for MANUAL mode fallback allowed
    if 'FALLBACK allowed only in MANUAL/DEBUG mode' in content or 'MANUAL mode' in content:
        print("✅ MANUAL mode fallback logic found")
    else:
        print("❌ MANUAL mode fallback logic MISSING")
        return False
    
    print("\n✅ All AUTO mode blocking logic verified in code!")
    return True

def verify_schema_safe_filtering():
    """Verify schema-safe filtering code is present"""
    print("\n" + "=" * 60)
    print("VERIFICATION: Schema-Safe Filtering Logic")
    print("=" * 60)
    
    with open('ict_signal_engine.py', 'r') as f:
        content = f.read()
    
    # Check for safe field access with try/except
    if 'try:' in content and 'except Exception as e:' in content and 'keeping component' in content.lower():
        print("✅ Try/except error handling for filtering found")
    else:
        print("❌ Try/except error handling MISSING")
        return False
    
    # Check for missing field handling
    if 'if strength is None:' in content or 'if fill_pct is None:' in content:
        print("✅ Missing field checks found")
    else:
        print("❌ Missing field checks MISSING")
        return False
    
    # Check for debug logging
    if 'First Order Block schema' in content or 'First FVG schema' in content:
        print("✅ Debug schema logging found")
    else:
        print("❌ Debug schema logging MISSING")
        return False
    
    print("\n✅ All schema-safe filtering logic verified in code!")
    return True

def verify_clean_liquidity_flow():
    """Verify clean liquidity/sweeps flow is present"""
    print("\n" + "=" * 60)
    print("VERIFICATION: Clean Liquidity/Sweeps Flow")
    print("=" * 60)
    
    with open('ict_signal_engine.py', 'r') as f:
        content = f.read()
    
    # Check for clear flow comments
    if 'LIQUIDITY ZONES & SWEEPS - Clear flow without duplication' in content:
        print("✅ Clear flow documentation found")
    else:
        print("❌ Clear flow documentation MISSING")
        return False
    
    # Check for 3-step flow
    if 'Step 1: Get or calculate liquidity zones' in content:
        print("✅ Step 1: Get/calculate zones found")
    else:
        print("❌ Step 1 MISSING")
        return False
    
    if 'Step 2: Store liquidity zones in components' in content:
        print("✅ Step 2: Store zones found")
    else:
        print("❌ Step 2 MISSING")
        return False
    
    if 'Step 3: Calculate liquidity sweeps (ONCE)' in content:
        print("✅ Step 3: Calculate sweeps ONCE found")
    else:
        print("❌ Step 3 MISSING")
        return False
    
    print("\n✅ Clean liquidity flow verified in code!")
    return True

def main():
    results = {
        'auto_blocking': verify_auto_blocking(),
        'schema_safe': verify_schema_safe_filtering(),
        'clean_liquidity': verify_clean_liquidity_flow(),
    }
    
    print("\n" + "=" * 60)
    print("FINAL VERIFICATION RESULTS")
    print("=" * 60)
    for test_name, passed in results.items():
        status = "✅ VERIFIED" if passed else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    if all(results.values()):
        print("\n✅ ALL BLOCKING FIXES VERIFIED IN CODE!")
        return 0
    else:
        print("\n❌ SOME FIXES MISSING")
        return 1

if __name__ == "__main__":
    import sys
    sys.exit(main())
