#!/usr/bin/env python3
"""
Test suite for PR #119: Dual Timestamp Tracking
Tests the fix for cache persistence after restart

Key functionality tested:
1. Cache entries have both 'timestamp' and 'last_checked' fields
2. Duplicate checks update 'last_checked' and save cache
3. New signals update both 'timestamp' and 'last_checked'
4. Cleanup uses 'last_checked' instead of 'timestamp'
5. Backward compatibility: old entries without 'last_checked' still work
"""

import os
import json
import tempfile
import time
from datetime import datetime, timedelta
from signal_cache import is_signal_duplicate, load_sent_signals, save_sent_signals


def test_dual_timestamps_on_first_signal():
    """Test that first signal creates both timestamp and last_checked"""
    print("\n🧪 TEST 1: First signal creates dual timestamps")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Send first signal
        is_dup, msg = is_signal_duplicate(
            symbol="TESTCOIN",
            signal_type="BUY",
            timeframe="4h",
            entry_price=100.0,
            confidence=85,
            base_path=tmpdir
        )
        
        assert not is_dup, "First signal should NOT be duplicate"
        
        # Load cache and verify dual timestamps
        cache = load_sent_signals(tmpdir)
        key = "TESTCOIN_BUY_4h"
        
        assert key in cache, f"Signal key {key} should be in cache"
        assert 'timestamp' in cache[key], "Cache entry should have 'timestamp'"
        assert 'last_checked' in cache[key], "Cache entry should have 'last_checked'"
        
        # Both should be the same initially
        timestamp = cache[key]['timestamp']
        last_checked = cache[key]['last_checked']
        
        print(f"   ✓ timestamp: {timestamp}")
        print(f"   ✓ last_checked: {last_checked}")
        
        # Both should be very close (within a few microseconds)
        ts_time = datetime.fromisoformat(timestamp)
        lc_time = datetime.fromisoformat(last_checked)
        time_diff = abs((ts_time - lc_time).total_seconds())
        
        assert time_diff < 0.1, f"Initial timestamps should be close (diff: {time_diff}s)"
        
        print("✅ PASS: First signal creates both timestamps")


def test_duplicate_updates_last_checked():
    """Test that duplicate check updates last_checked and saves cache"""
    print("\n🧪 TEST 2: Duplicate updates last_checked (CRITICAL)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Send first signal
        is_dup1, _ = is_signal_duplicate(
            symbol="XRPUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=2.0357,
            confidence=85,
            base_path=tmpdir
        )
        
        assert not is_dup1, "First signal should be allowed"
        
        # Get initial timestamps
        cache1 = load_sent_signals(tmpdir)
        key = "XRPUSDT_BUY_4h"
        initial_timestamp = cache1[key]['timestamp']
        initial_last_checked = cache1[key]['last_checked']
        
        print(f"   Initial timestamp: {initial_timestamp}")
        print(f"   Initial last_checked: {initial_last_checked}")
        
        # Wait to ensure time difference
        time.sleep(2)
        
        # Send duplicate signal
        is_dup2, _ = is_signal_duplicate(
            symbol="XRPUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=2.0357,  # Same entry
            confidence=85,
            base_path=tmpdir
        )
        
        assert is_dup2, "Duplicate signal should be blocked"
        
        # Get updated timestamps
        cache2 = load_sent_signals(tmpdir)
        updated_timestamp = cache2[key]['timestamp']
        updated_last_checked = cache2[key]['last_checked']
        
        print(f"   Updated timestamp: {updated_timestamp}")
        print(f"   Updated last_checked: {updated_last_checked}")
        
        # Verify timestamp NOT changed
        assert initial_timestamp == updated_timestamp, \
            "timestamp should NOT change on duplicate"
        
        # Verify last_checked WAS updated
        assert initial_last_checked != updated_last_checked, \
            "last_checked SHOULD be updated on duplicate"
        
        print("✅ PASS: Duplicate updates last_checked and saves cache")


def test_new_signal_updates_both_timestamps():
    """Test that new signal (entry diff >= 1.5%) updates both timestamps"""
    print("\n🧪 TEST 3: New signal updates both timestamps")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Send first signal
        is_signal_duplicate(
            symbol="BTCUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=50000.0,
            confidence=85,
            base_path=tmpdir
        )
        
        cache1 = load_sent_signals(tmpdir)
        key = "BTCUSDT_BUY_4h"
        first_timestamp = cache1[key]['timestamp']
        
        time.sleep(2)
        
        # Send new signal with different entry (>1.5% difference)
        is_signal_duplicate(
            symbol="BTCUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=51000.0,  # ~2% difference
            confidence=85,
            base_path=tmpdir
        )
        
        cache2 = load_sent_signals(tmpdir)
        new_timestamp = cache2[key]['timestamp']
        new_last_checked = cache2[key]['last_checked']
        
        # Both should be updated and close
        assert first_timestamp != new_timestamp, "timestamp should be updated for new signal"
        
        # Check they're very close (within 0.1 seconds)
        ts_time = datetime.fromisoformat(new_timestamp)
        lc_time = datetime.fromisoformat(new_last_checked)
        time_diff = abs((ts_time - lc_time).total_seconds())
        
        assert time_diff < 0.1, f"Both timestamps should be close for new signal (diff: {time_diff}s)"
        
        print("✅ PASS: New signal updates both timestamps")


def test_cleanup_uses_last_checked():
    """Test that cleanup uses last_checked instead of timestamp"""
    print("\n🧪 TEST 4: Cleanup uses last_checked for retention")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = {}
        
        # Create entry with old timestamp but recent last_checked
        # This simulates a signal that was sent 8 days ago but checked yesterday
        key = "ETHUSDT_BUY_4h"
        cache[key] = {
            'timestamp': (datetime.now() - timedelta(days=8)).isoformat(),  # 8 days old
            'last_checked': (datetime.now() - timedelta(days=1)).isoformat(),  # 1 day old
            'entry_price': 3500.0,
            'confidence': 88
        }
        
        save_sent_signals(cache, tmpdir)
        
        # Load cache (triggers cleanup)
        loaded = load_sent_signals(tmpdir)
        
        # Entry should NOT be cleaned (last_checked is recent)
        assert key in loaded, "Entry should NOT be cleaned (recent last_checked)"
        
        print("✅ PASS: Cleanup uses last_checked instead of timestamp")


def test_cleanup_removes_inactive_entries():
    """Test that cleanup removes entries inactive for >168h"""
    print("\n🧪 TEST 5: Cleanup removes truly inactive entries")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = {}
        
        # Create entry with both timestamps old (>168h)
        key1 = "OLD_INACTIVE_BUY_4h"
        cache[key1] = {
            'timestamp': (datetime.now() - timedelta(hours=169)).isoformat(),
            'last_checked': (datetime.now() - timedelta(hours=169)).isoformat(),
            'entry_price': 1000.0,
            'confidence': 80
        }
        
        # Create entry with recent last_checked
        key2 = "ACTIVE_BUY_4h"
        cache[key2] = {
            'timestamp': (datetime.now() - timedelta(hours=169)).isoformat(),
            'last_checked': datetime.now().isoformat(),
            'entry_price': 2000.0,
            'confidence': 85
        }
        
        save_sent_signals(cache, tmpdir)
        
        # Load cache (triggers cleanup)
        loaded = load_sent_signals(tmpdir)
        
        assert key1 not in loaded, "Inactive entry should be cleaned"
        assert key2 in loaded, "Active entry should be kept"
        
        print("✅ PASS: Cleanup removes inactive entries correctly")


def test_backward_compatibility():
    """Test that old cache entries without last_checked still work"""
    print("\n🧪 TEST 6: Backward compatibility with old cache format")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache = {}
        
        # Create old-format entry (no last_checked)
        key = "LEGACY_BUY_4h"
        cache[key] = {
            'timestamp': (datetime.now() - timedelta(hours=24)).isoformat(),
            'entry_price': 5000.0,
            'confidence': 80
            # Note: No 'last_checked' field
        }
        
        save_sent_signals(cache, tmpdir)
        
        # Load cache (should not crash)
        loaded = load_sent_signals(tmpdir)
        
        # Entry should still exist (24h old, within 168h cleanup)
        assert key in loaded, "Legacy entry should still exist"
        
        # Now trigger a duplicate check
        is_dup, _ = is_signal_duplicate(
            symbol="LEGACY",
            signal_type="BUY",
            timeframe="4h",
            entry_price=5000.0,
            confidence=80,
            base_path=tmpdir
        )
        
        # Should be detected as duplicate
        assert is_dup, "Legacy entry should still work for duplicate detection"
        
        # Reload and verify last_checked was added
        updated = load_sent_signals(tmpdir)
        assert 'last_checked' in updated[key], "last_checked should be added after duplicate check"
        
        print("✅ PASS: Backward compatibility works correctly")


def test_restart_persistence_scenario():
    """Test the main bug fix: cache persists after restart even after 168h"""
    print("\n🧪 TEST 7: Bot restart scenario (Main Bug Fix)")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Day 0: Send signal
        is_signal_duplicate(
            symbol="PERSIST",
            signal_type="BUY",
            timeframe="4h",
            entry_price=100.0,
            confidence=85,
            base_path=tmpdir
        )
        
        # Simulate regular duplicate checks over 7+ days
        # by manually updating last_checked
        cache = load_sent_signals(tmpdir)
        key = "PERSIST_BUY_4h"
        
        # Make timestamp 8 days old (would be cleaned in old system)
        cache[key]['timestamp'] = (datetime.now() - timedelta(days=8)).isoformat()
        # But last_checked is recent (from yesterday's duplicate check)
        cache[key]['last_checked'] = (datetime.now() - timedelta(days=1)).isoformat()
        
        save_sent_signals(cache, tmpdir)
        
        # Simulate bot restart (reload cache)
        print("   Simulating bot restart...")
        reloaded = load_sent_signals(tmpdir)
        
        # Entry should PERSIST (not cleaned up)
        assert key in reloaded, "Entry should persist after restart despite old timestamp"
        
        # Duplicate check should still work
        is_dup, _ = is_signal_duplicate(
            symbol="PERSIST",
            signal_type="BUY",
            timeframe="4h",
            entry_price=100.0,
            confidence=85,
            base_path=tmpdir
        )
        
        assert is_dup, "Duplicate should still be blocked after restart"
        
        print("✅ PASS: Cache persists correctly after restart (Bug Fixed!)")


def run_all_tests():
    """Run all dual timestamp tracking tests"""
    print("=" * 70)
    print("🔬 DUAL TIMESTAMP TRACKING TESTS (PR #119)")
    print("=" * 70)
    
    tests = [
        test_dual_timestamps_on_first_signal,
        test_duplicate_updates_last_checked,
        test_new_signal_updates_both_timestamps,
        test_cleanup_uses_last_checked,
        test_cleanup_removes_inactive_entries,
        test_backward_compatibility,
        test_restart_persistence_scenario,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ FAIL: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
        except Exception as e:
            print(f"❌ ERROR: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)
    print(f"📊 TEST RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    if failed == 0:
        print("\n✅ ALL DUAL TIMESTAMP TESTS PASSED!")
        print("\n🎉 Cache persistence bug is FIXED!")
        print("\nKey improvements:")
        print("  • Cache entries now have dual timestamps")
        print("  • Duplicates refresh last_checked to prevent cleanup")
        print("  • Cache persists across restarts even after 168h")
        print("  • Backward compatible with old cache format")
        return 0
    else:
        print(f"\n❌ {failed} TESTS FAILED")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(run_all_tests())
