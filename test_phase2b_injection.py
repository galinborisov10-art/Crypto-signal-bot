#!/usr/bin/env python3
"""
Test Phase 2B: Dependency Injection Implementation

Verifies that:
1. ReplayEngine requires signal_engine parameter (no default)
2. ReplayEngine does NOT import from bot module
3. All Phase 2B fixes are preserved
"""

import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

def test_replay_engine_requires_signal_engine():
    """Test that ReplayEngine requires signal_engine parameter"""
    print("=" * 70)
    print("TEST 1: ReplayEngine requires signal_engine (no default parameter)")
    print("=" * 70)
    
    try:
        from diagnostics import ReplayCache, ReplayEngine
        
        cache = ReplayCache()
        
        # This should FAIL because signal_engine is required
        try:
            engine = ReplayEngine(cache)
            print("❌ FAILED: ReplayEngine() should require signal_engine parameter")
            return False
        except TypeError as e:
            if "signal_engine" in str(e):
                print(f"✅ PASSED: ReplayEngine correctly requires signal_engine parameter")
                print(f"   Error message: {e}")
                return True
            else:
                print(f"❌ FAILED: Unexpected TypeError: {e}")
                return False
                
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_no_bot_import_in_replay_engine():
    """Test that ReplayEngine does NOT import from bot module"""
    print("\n" + "=" * 70)
    print("TEST 2: ReplayEngine does NOT import from bot module")
    print("=" * 70)
    
    try:
        # Read the ReplayEngine source code
        with open('diagnostics.py', 'r') as f:
            source = f.read()
        
        # Find the ReplayEngine class
        class_start = source.find("class ReplayEngine:")
        if class_start == -1:
            print("❌ FAILED: Could not find ReplayEngine class")
            return False
        
        # Find the next class (to limit search scope)
        next_class = source.find("\nclass ", class_start + 1)
        if next_class == -1:
            replay_engine_code = source[class_start:]
        else:
            replay_engine_code = source[class_start:next_class]
        
        # Check for bot imports in ReplayEngine class
        if "from bot import" in replay_engine_code:
            print("❌ FAILED: Found 'from bot import' in ReplayEngine class")
            return False
        
        if "import bot" in replay_engine_code and "# import" not in replay_engine_code:
            print("❌ FAILED: Found 'import bot' in ReplayEngine class")
            return False
        
        print("✅ PASSED: ReplayEngine does NOT import from bot module")
        return True
        
    except Exception as e:
        print(f"❌ FAILED: Error reading source: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_phase2b_fixes_preserved():
    """Test that Phase 2B fixes are preserved"""
    print("\n" + "=" * 70)
    print("TEST 3: Phase 2B fixes are preserved")
    print("=" * 70)
    
    try:
        with open('diagnostics.py', 'r') as f:
            source = f.read()
        
        checks = {
            'PRICE_TOLERANCE_PERCENT = 0.005': 'Price tolerance of 0.5%',
            'CONFIDENCE_TOLERANCE = 5': 'Confidence tolerance of ±5',
            'def check_confidence_match': 'check_confidence_match function',
            "'confidence_delta': check_confidence_match": 'confidence_delta in checks dict'
        }
        
        all_passed = True
        for check, description in checks.items():
            if check in source:
                print(f"✅ Found: {description}")
            else:
                print(f"❌ Missing: {description}")
                all_passed = False
        
        if all_passed:
            print("\n✅ PASSED: All Phase 2B fixes are preserved")
            return True
        else:
            print("\n❌ FAILED: Some Phase 2B fixes are missing")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error checking fixes: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_dependency_injection_works():
    """Test that dependency injection works correctly"""
    print("\n" + "=" * 70)
    print("TEST 4: Dependency injection works correctly")
    print("=" * 70)
    
    try:
        from diagnostics import ReplayCache, ReplayEngine
        from ict_signal_engine import ICTSignalEngine
        
        # Create instances
        cache = ReplayCache()
        signal_engine = ICTSignalEngine()
        
        # Create ReplayEngine with injected engine
        replay_engine = ReplayEngine(cache=cache, signal_engine=signal_engine)
        
        # Verify the engine was set correctly
        if replay_engine.signal_engine is signal_engine:
            print("✅ PASSED: ReplayEngine correctly uses injected signal_engine")
            print(f"   Engine type: {type(replay_engine.signal_engine).__name__}")
            return True
        else:
            print("❌ FAILED: ReplayEngine did not use injected signal_engine")
            return False
            
    except Exception as e:
        print(f"❌ FAILED: Error testing injection: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("PHASE 2B: DEPENDENCY INJECTION - TEST SUITE")
    print("=" * 70 + "\n")
    
    results = []
    
    # Run tests
    results.append(("ReplayEngine requires signal_engine", test_replay_engine_requires_signal_engine()))
    results.append(("No bot imports in ReplayEngine", test_no_bot_import_in_replay_engine()))
    results.append(("Phase 2B fixes preserved", test_phase2b_fixes_preserved()))
    results.append(("Dependency injection works", test_dependency_injection_works()))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Phase 2B dependency injection is correctly implemented.\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Please review the implementation.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
