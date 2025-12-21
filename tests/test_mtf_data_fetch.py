"""
Test MTF (Multi-Timeframe) Data Fetching
Tests that all 13 timeframes are properly configured in fetch_mtf_data()
"""

import sys
import os

# Add parent directory to path to import bot.py from root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Remove bot package from path if it conflicts
if 'bot' in sys.modules:
    del sys.modules['bot']

def test_mtf_timeframes_configuration():
    """
    Test that fetch_mtf_data() is configured with all 13 required timeframes
    """
    # Read the bot.py file directly to check configuration
    bot_file_path = os.path.join(os.path.dirname(__file__), '..', 'bot.py')
    with open(bot_file_path, 'r') as f:
        bot_source = f.read()
    
    # Find the fetch_mtf_data function
    assert 'def fetch_mtf_data(' in bot_source, "fetch_mtf_data() function not found"
    
    # Check that all 13 timeframes are defined
    expected_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']
    
    # Extract the mtf_timeframes line
    mtf_line_found = False
    for line in bot_source.split('\n'):
        if 'mtf_timeframes = [' in line:
            mtf_line_found = True
            # Verify all timeframes are in this line
            for tf in expected_timeframes:
                assert f"'{tf}'" in line or f'"{tf}"' in line, f"Timeframe {tf} not found in mtf_timeframes list"
            break
    
    assert mtf_line_found, "mtf_timeframes list not found in fetch_mtf_data()"
    
    print("✅ All 13 timeframes are configured in fetch_mtf_data()")
    print(f"✅ Expected timeframes: {expected_timeframes}")
    
    # Verify the old configuration is not present
    assert "mtf_timeframes = ['1h', '4h', '1d']" not in bot_source, "Old 3-timeframe configuration still present!"
    print("✅ Old 3-timeframe configuration has been removed")
    
    return True


def test_mtf_timeframes_match_ict_engine():
    """
    Test that MTF timeframes match what ICT engine expects
    """
    # Read the ict_signal_engine.py file
    ict_file_path = os.path.join(os.path.dirname(__file__), '..', 'ict_signal_engine.py')
    with open(ict_file_path, 'r') as f:
        ict_source = f.read()
    
    # Check that the engine expects all 13 timeframes
    expected_timeframes = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']
    
    # The engine should define all_timeframes with these values
    assert "all_timeframes = " in ict_source, "all_timeframes not defined in _calculate_mtf_consensus"
    
    for tf in expected_timeframes:
        assert f"'{tf}'" in ict_source or f'"{tf}"' in ict_source, f"Timeframe {tf} not expected by ICT engine"
    
    print("✅ ICT engine expects all 13 timeframes")
    print(f"✅ Timeframes match between bot.py and ict_signal_engine.py")
    
    return True


def test_no_duplicate_mtf_fetch():
    """
    Test that there are no duplicate fetch_mtf_data() calls in generate_signal()
    """
    bot_file_path = os.path.join(os.path.dirname(__file__), '..', 'bot.py')
    with open(bot_file_path, 'r') as f:
        bot_source = f.read()
    
    # Look for the specific pattern that was problematic
    # We want to ensure mtf_data is used as a variable, not called twice
    lines = bot_source.split('\n')
    
    issue_found = False
    for i, line in enumerate(lines):
        # Check for the pattern: mtf_data = fetch_mtf_data(...) followed by mtf_data=fetch_mtf_data(...) in next few lines
        if 'mtf_data = fetch_mtf_data(' in line and 'result = ' not in line:
            # Check next 10 lines for duplicate call
            for j in range(i+1, min(i+11, len(lines))):
                if 'mtf_data=fetch_mtf_data(' in lines[j]:
                    issue_found = True
                    print(f"❌ Found duplicate fetch_mtf_data() call at line {j+1}")
                    print(f"   Previous assignment at line {i+1}")
                    break
    
    assert not issue_found, "Duplicate fetch_mtf_data() calls found!"
    print("✅ No duplicate fetch_mtf_data() calls found")
    
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing MTF Data Fetch Configuration")
    print("=" * 60)
    
    try:
        # Test 1: Check timeframes configuration
        print("\n📋 Test 1: Checking MTF timeframes configuration...")
        test_mtf_timeframes_configuration()
        
        # Test 2: Check consistency with ICT engine
        print("\n📋 Test 2: Checking consistency with ICT engine...")
        test_mtf_timeframes_match_ict_engine()
        
        # Test 3: Check for duplicate calls
        print("\n📋 Test 3: Checking for duplicate fetch_mtf_data() calls...")
        test_no_duplicate_mtf_fetch()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED")
        print("=" * 60)
        
    except AssertionError as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        sys.exit(1)
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ ERROR: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        sys.exit(1)

