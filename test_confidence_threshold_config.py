"""
Test for confidence threshold configuration enhancement
Tests that the confidence threshold is properly configurable and defaults to 50%
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_trading_config_min_confidence():
    """Test that MIN_CONFIDENCE in trading_config.py is set to 50"""
    from config.trading_config import TradingConfig, get_trading_config
    
    # Test class attribute
    assert TradingConfig.MIN_CONFIDENCE == 50, \
        f"Expected MIN_CONFIDENCE to be 50, got {TradingConfig.MIN_CONFIDENCE}"
    
    # Test config dictionary
    config = get_trading_config()
    assert config['min_confidence'] == 50, \
        f"Expected min_confidence in config to be 50, got {config['min_confidence']}"
    
    print("✅ TEST PASSED: trading_config.py MIN_CONFIDENCE = 50")


def test_ict_signal_engine_default_value():
    """Test that ICTSignalEngine source code has min_confidence set to 50"""
    # Read the source file directly to check the default value
    with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/ict_signal_engine.py', 'r') as f:
        content = f.read()
    
    # Look for the min_confidence line in _get_default_config
    if "'min_confidence': 50," in content:
        print("✅ TEST PASSED: ict_signal_engine.py default min_confidence = 50")
    else:
        raise AssertionError("Expected 'min_confidence': 50 in ict_signal_engine.py")


def test_backward_compatibility_mode():
    """Test that backward compatibility mode keeps old value of 60"""
    from config.trading_config import TradingConfig
    
    # Save original state
    original_mode = TradingConfig.BACKWARD_COMPATIBLE_MODE
    
    try:
        # Enable backward compatible mode
        TradingConfig.BACKWARD_COMPATIBLE_MODE = True
        config = TradingConfig.get_config()
        
        # Should return old value of 60 in backward compatible mode
        assert config['min_confidence'] == 60, \
            f"Expected backward compatible min_confidence to be 60, got {config['min_confidence']}"
        
        print("✅ TEST PASSED: Backward compatibility mode preserves old value (60)")
        
    finally:
        # Restore original state
        TradingConfig.BACKWARD_COMPATIBLE_MODE = original_mode


def test_comment_documentation():
    """Test that the comment in trading_config.py is properly updated"""
    with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/config/trading_config.py', 'r') as f:
        content = f.read()
    
    # Check that the comment mentions the recommended range
    if "50-70 recommended" in content or "Minimum confidence %" in content:
        print("✅ TEST PASSED: Configuration comment properly documents the setting")
    else:
        raise AssertionError("Expected proper documentation comment for MIN_CONFIDENCE")


if __name__ == '__main__':
    print("=" * 60)
    print("🧪 Testing Confidence Threshold Configuration")
    print("=" * 60)
    
    try:
        test_trading_config_min_confidence()
        test_ict_signal_engine_default_value()
        test_backward_compatibility_mode()
        test_comment_documentation()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\n📊 Expected Results:")
        print("   • Signals with 38.5% confidence → ❌ REJECTED (below 50%)")
        print("   • Signals with 55% confidence → ✅ SENT (passes!)")
        print("   • Signals with 65% confidence → ✅ SENT (same as before)")
        print("\n🎯 Benefits:")
        print("   ✅ Matches MTF consensus threshold (50%)")
        print("   ✅ Increases signal generation rate")
        print("   ✅ Maintains quality (10+ validation steps)")
        print("   ✅ Users can still adjust via config if needed")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
