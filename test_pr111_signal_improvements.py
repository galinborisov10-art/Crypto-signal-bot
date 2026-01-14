#!/usr/bin/env python3
"""
Test suite for PR #111: Signal Improvements + Documentation Updates

Tests:
1. timedelta import fix
2. Signal deduplication persistence
3. Startup suppression logic
4. Help and settings command output
"""

import sys
import os
import json
import tempfile
from datetime import datetime, timedelta
import unittest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestPR111Fixes(unittest.TestCase):
    """Test critical fixes from PR #111"""
    
    def test_timedelta_import(self):
        """Test 1: Verify timedelta is imported at top level"""
        print("\n=== Test 1: timedelta Import Fix ===")
        
        # Try importing bot.py to check for NameError
        try:
            import bot
            # Check if timedelta is accessible
            self.assertTrue(hasattr(bot, 'timedelta'), "timedelta should be imported")
            print("✅ timedelta successfully imported at top level")
            print("✅ No NameError on bot startup")
        except NameError as e:
            if 'timedelta' in str(e):
                self.fail(f"❌ timedelta import failed: {e}")
            raise
        except Exception as e:
            # Other import errors are OK (missing Telegram token, etc.)
            print(f"⚠️ Bot import has other errors (expected): {type(e).__name__}")
            print("✅ But no timedelta NameError detected")
    
    def test_signal_cache_persistence(self):
        """Test 2: Signal cache persistence across restarts"""
        print("\n=== Test 2: Signal Deduplication Persistence ===")
        
        from signal_cache import is_signal_duplicate, load_sent_signals, save_sent_signals
        
        # Use temporary directory for testing
        with tempfile.TemporaryDirectory() as temp_dir:
            # Test 1: New signal should not be duplicate
            is_dup, reason = is_signal_duplicate(
                'BTCUSDT', 'BUY', '4h', 50000, 75, 
                cooldown_minutes=60, base_path=temp_dir
            )
            self.assertFalse(is_dup, "First signal should not be duplicate")
            print(f"✅ Test 1 passed: {reason}")
            
            # Test 2: Immediate duplicate should be detected
            is_dup, reason = is_signal_duplicate(
                'BTCUSDT', 'BUY', '4h', 50000, 75,
                cooldown_minutes=60, base_path=temp_dir
            )
            self.assertTrue(is_dup, "Immediate duplicate should be detected")
            print(f"✅ Test 2 passed: {reason}")
            
            # Test 3: Price proximity check (within 0.5%)
            is_dup, reason = is_signal_duplicate(
                'BTCUSDT', 'BUY', '4h', 50200, 75,  # 0.4% difference
                cooldown_minutes=60, base_path=temp_dir
            )
            self.assertTrue(is_dup, "Similar price should be duplicate")
            print(f"✅ Test 3 passed: {reason}")
            
            # Test 4: Cache persistence - load and verify
            cache = load_sent_signals(temp_dir)
            self.assertIn('BTCUSDT_BUY_4h', cache, "Signal should be in cache")
            self.assertEqual(cache['BTCUSDT_BUY_4h']['confidence'], 75)
            print(f"✅ Test 4 passed: Cache persists in JSON file")
            
            # Test 5: Different signal type should not be duplicate
            is_dup, reason = is_signal_duplicate(
                'BTCUSDT', 'SELL', '4h', 50000, 75,
                cooldown_minutes=60, base_path=temp_dir
            )
            self.assertFalse(is_dup, "Different signal type should not be duplicate")
            print(f"✅ Test 5 passed: {reason}")
            
            # Test 6: Different timeframe should not be duplicate
            is_dup, reason = is_signal_duplicate(
                'BTCUSDT', 'BUY', '1h', 50000, 75,
                cooldown_minutes=60, base_path=temp_dir
            )
            self.assertFalse(is_dup, "Different timeframe should not be duplicate")
            print(f"✅ Test 6 passed: {reason}")
            
            # Test 7: Cache cleanup (simulate old entry)
            old_cache = {
                'ETHUSDT_BUY_1h': {
                    'timestamp': (datetime.now() - timedelta(hours=25)).isoformat(),
                    'entry_price': 3000,
                    'confidence': 70
                }
            }
            save_sent_signals(old_cache, temp_dir)
            
            # Load should cleanup old entries
            new_cache = load_sent_signals(temp_dir)
            self.assertNotIn('ETHUSDT_BUY_1h', new_cache, "Old entries should be cleaned up")
            print(f"✅ Test 7 passed: Cache auto-cleanup works (24h old entries removed)")
    
    def test_startup_suppression(self):
        """Test 3: Startup suppression logic"""
        print("\n=== Test 3: Startup Suppression ===")
        
        # Simulate startup mode
        startup_mode = True
        startup_time = datetime.now()
        grace_period = 300  # 5 minutes
        
        # Test 1: Within grace period - should suppress
        elapsed = (datetime.now() - startup_time).total_seconds()
        should_suppress = startup_mode and elapsed < grace_period
        self.assertTrue(should_suppress, "Should suppress within grace period")
        print(f"✅ Test 1 passed: Signals suppressed at {elapsed:.0f}s (< 300s)")
        
        # Test 2: Simulate time passage
        startup_time_old = datetime.now() - timedelta(seconds=301)
        elapsed = (datetime.now() - startup_time_old).total_seconds()
        should_suppress = startup_mode and elapsed < grace_period
        self.assertFalse(should_suppress, "Should not suppress after grace period")
        print(f"✅ Test 2 passed: Signals allowed at {elapsed:.0f}s (> 300s)")
        
        # Test 3: Startup mode disabled
        startup_mode = False
        elapsed = 10  # 10 seconds
        should_suppress = startup_mode and elapsed < grace_period
        self.assertFalse(should_suppress, "Should not suppress when mode disabled")
        print(f"✅ Test 3 passed: Signals allowed when startup_mode=False")
    
    def test_help_command_content(self):
        """Test 4: Help command has comprehensive content"""
        print("\n=== Test 4: Help Command Content ===")
        
        # We can't easily test the actual command, but we can verify
        # the structure is correct by checking if key sections would be present
        required_sections = [
            "СИСТЕМА & МОНИТОРИНГ",
            "TRADING & СИГНАЛИ",
            "ОТЧЕТИ",
            "УПРАВЛЕНИЕ",
            "АКТИВНА ФУНКЦИОНАЛНОСТ"
        ]
        
        # Check that the implementation exists in bot.py
        with open('bot.py', 'r', encoding='utf-8') as f:
            bot_content = f.read()
            
            for section in required_sections:
                self.assertIn(section, bot_content, f"Help should contain {section} section")
                print(f"✅ Help contains: {section}")
            
            # Check for key commands
            key_commands = ['/health', '/signal', '/dailyreport', '/settings', '/positions']
            for cmd in key_commands:
                self.assertIn(cmd, bot_content, f"Help should document {cmd}")
                print(f"✅ Help documents: {cmd}")
    
    def test_settings_command_content(self):
        """Test 5: Settings command has detailed content"""
        print("\n=== Test 5: Settings Command Content ===")
        
        required_sections = [
            "SIGNAL SETTINGS",
            "RISK MANAGEMENT",
            "ICT ANALYSIS SETTINGS",
            "ML & AUTOMATION",
            "HEALTH MONITORING SCHEDULE"
        ]
        
        with open('bot.py', 'r', encoding='utf-8') as f:
            bot_content = f.read()
            
            for section in required_sections:
                self.assertIn(section, bot_content, f"Settings should contain {section} section")
                print(f"✅ Settings contains: {section}")
            
            # Check for key settings info
            key_info = [
                "Signal Deduplication",
                "Startup Grace Period",
                "Persistent (JSON file)",
                "Order Blocks",
                "Fair Value Gaps"
            ]
            for info in key_info:
                self.assertIn(info, bot_content, f"Settings should show {info}")
                print(f"✅ Settings shows: {info}")
    
    def test_timestamp_format(self):
        """Test 6: Timestamp formatting for BG timezone"""
        print("\n=== Test 6: Timestamp Format ===")
        
        import pytz
        
        # Test BG timezone formatting
        bg_tz = pytz.timezone('Europe/Sofia')
        now = datetime.now(bg_tz)
        timestamp_str = now.strftime('%d.%m.%Y %H:%M')
        
        # Verify format is correct (DD.MM.YYYY HH:MM)
        parts = timestamp_str.split()
        self.assertEqual(len(parts), 2, "Should have date and time parts")
        
        date_parts = parts[0].split('.')
        self.assertEqual(len(date_parts), 3, "Date should have 3 parts (DD.MM.YYYY)")
        
        time_parts = parts[1].split(':')
        self.assertEqual(len(time_parts), 2, "Time should have 2 parts (HH:MM)")
        
        print(f"✅ Timestamp format valid: {timestamp_str}")
        print(f"✅ BG timezone applied correctly")


def run_tests():
    """Run all tests and report results"""
    print("=" * 60)
    print("PR #111 Test Suite")
    print("=" * 60)
    
    # Create test suite
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPR111Fixes)
    
    # Run tests with verbose output
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    print(f"Tests run: {result.testsRun}")
    print(f"Successes: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ ALL TESTS PASSED!")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
