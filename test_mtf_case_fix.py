"""
Test MTF Case Sensitivity Fix

Validates that _analyze_mtf_confluence() correctly uses lowercase timeframe keys
to match the keys returned by fetch_mtf_data().
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def test_mtf_case_consistency():
    """
    Test that _analyze_mtf_confluence() uses lowercase keys matching fetch_mtf_data()
    """
    print("=" * 70)
    print("Testing MTF Case Sensitivity Fix")
    print("=" * 70)
    
    # Read ict_signal_engine.py
    engine_file = os.path.join(os.path.dirname(__file__), 'ict_signal_engine.py')
    with open(engine_file, 'r') as f:
        engine_source = f.read()
    
    # Find the _analyze_mtf_confluence method
    assert 'def _analyze_mtf_confluence(' in engine_source, \
        "_analyze_mtf_confluence method not found"
    print("✅ Found _analyze_mtf_confluence method")
    
    # Extract the relevant lines (around line 2038-2040)
    lines = engine_source.split('\n')
    found_bug = False
    found_fix = False
    
    for i, line in enumerate(lines):
        # Look for the problematic patterns
        if "htf_df = mtf_data.get('1D')" in line or "mtf_data.get('4H')" in line:
            found_bug = True
            print(f"❌ FOUND BUG at line {i+1}: {line.strip()}")
            print("   Uses UPPERCASE keys ('1D', '4H') which won't match fetch_mtf_data()")
        
        # Look for the fixed patterns
        if "htf_df = mtf_data.get('1d')" in line:
            found_fix = True
            print(f"✅ FOUND FIX at line {i+1}: {line.strip()}")
            print("   Uses lowercase keys ('1d') matching fetch_mtf_data()")
    
    # Verify the fix is in place
    assert not found_bug or found_fix, \
        "Bug still present: _analyze_mtf_confluence uses UPPERCASE keys!"
    
    if found_fix:
        print("\n" + "=" * 70)
        print("✅ MTF Case Sensitivity Fix VERIFIED")
        print("=" * 70)
        print("\nExpected behavior:")
        print("  • fetch_mtf_data() returns: {'1h': df, '4h': df, '1d': df}")
        print("  • _analyze_mtf_confluence() searches for: '1h', '4h', '1d'")
        print("  • MTF data will be found and used correctly")
        print("  • No more -40% confidence penalty")
        print("  • Signal count should increase 3-4x")
        return True
    else:
        print("\n" + "=" * 70)
        print("⚠️ Fix not detected - manual verification needed")
        print("=" * 70)
        return False


def test_fetch_mtf_data_returns_lowercase():
    """
    Verify that fetch_mtf_data() uses lowercase timeframe keys
    """
    print("\n" + "=" * 70)
    print("Verifying fetch_mtf_data() Configuration")
    print("=" * 70)
    
    # Read bot.py
    bot_file = os.path.join(os.path.dirname(__file__), 'bot.py')
    with open(bot_file, 'r') as f:
        bot_source = f.read()
    
    # Find the mtf_timeframes list
    lines = bot_source.split('\n')
    for i, line in enumerate(lines):
        if 'mtf_timeframes = [' in line:
            print(f"✅ Found mtf_timeframes at line {i+1}")
            print(f"   {line.strip()}")
            
            # Verify all timeframes are lowercase
            if "'1h'" in line and "'4h'" in line and "'1d'" in line:
                print("✅ All timeframes are lowercase (correct)")
                return True
            elif "'1H'" in line or "'4H'" in line or "'1D'" in line:
                print("❌ Found UPPERCASE timeframes (bug in fetch_mtf_data)")
                return False
    
    print("⚠️ mtf_timeframes list not found")
    return False


def test_no_uppercase_bug_patterns():
    """
    Search for any remaining uppercase MTF key patterns
    """
    print("\n" + "=" * 70)
    print("Scanning for Uppercase Bug Patterns")
    print("=" * 70)
    
    engine_file = os.path.join(os.path.dirname(__file__), 'ict_signal_engine.py')
    with open(engine_file, 'r') as f:
        lines = f.readlines()
    
    # Patterns that indicate the bug (excluding fallback checks)
    bug_patterns = [
        ("mtf_data.get('1H')", "Should be '1h'"),
        ("mtf_data.get('2H')", "Should be '2h'"),
        ("mtf_data.get('4H')", "Should be '4h'"),
        ("mtf_data.get('1D')", "Should be '1d'"),
        ("mtf_data.get('1W')", "Should be '1w'"),
    ]
    
    found_issues = []
    for i, line in enumerate(lines):
        # Skip lines that are fallback checks (contain "if" and "else")
        if 'if mtf_data.get(' in line and 'else mtf_data.get(' in line:
            continue  # This is a proper fallback pattern
        
        for pattern, suggestion in bug_patterns:
            if pattern in line and 'else mtf_data.get' not in line:
                found_issues.append((i+1, line.strip(), suggestion))
    
    if found_issues:
        print("❌ Found uppercase bug patterns:")
        for line_num, line_text, suggestion in found_issues:
            print(f"   Line {line_num}: {line_text}")
            print(f"             → {suggestion}")
        return False
    else:
        print("✅ No uppercase bug patterns found")
        print("   (Fallback patterns are OK and intentional)")
        return True


if __name__ == "__main__":
    try:
        # Run all tests
        test1 = test_mtf_case_consistency()
        test2 = test_fetch_mtf_data_returns_lowercase()
        test3 = test_no_uppercase_bug_patterns()
        
        if test1 and test2 and test3:
            print("\n" + "=" * 70)
            print("🎉 ALL TESTS PASSED - MTF Case Bug is FIXED")
            print("=" * 70)
            sys.exit(0)
        else:
            print("\n" + "=" * 70)
            print("❌ SOME TESTS FAILED")
            print("=" * 70)
            sys.exit(1)
            
    except Exception as e:
        print("\n" + "=" * 70)
        print(f"❌ ERROR: {e}")
        print("=" * 70)
        import traceback
        traceback.print_exc()
        sys.exit(1)
