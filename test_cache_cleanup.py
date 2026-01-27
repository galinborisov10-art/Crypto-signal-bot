#!/usr/bin/env python3
"""
Test script to verify cache cleanup functionality
Tests PR #5 - Memory leak fix in diagnostic cache
"""

import time
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system_diagnostics import DIAGNOSTIC_CACHE, cleanup_expired_cache, CACHE_TTL

def test_cleanup_expired_cache():
    """Test that cleanup removes expired entries"""
    
    print("🧪 Testing cache cleanup functionality...")
    
    # Clear cache
    DIAGNOSTIC_CACHE.clear()
    print(f"✅ Cache cleared: {len(DIAGNOSTIC_CACHE)} entries")
    
    # Add some entries with different timestamps
    now = time.time()
    
    # Entry 1: Fresh (just added)
    DIAGNOSTIC_CACHE['fresh_entry'] = (now, "fresh data")
    
    # Entry 2: Old (10 minutes ago - should be expired)
    DIAGNOSTIC_CACHE['old_entry'] = (now - 600, "old data")  # 10 min ago
    
    # Entry 3: Expired (exactly CACHE_TTL + 1 second ago)
    DIAGNOSTIC_CACHE['expired_entry'] = (now - CACHE_TTL - 1, "expired data")
    
    # Entry 4: Almost expired (CACHE_TTL - 10 seconds ago - should NOT be expired)
    DIAGNOSTIC_CACHE['almost_expired'] = (now - CACHE_TTL + 10, "almost expired data")
    
    print(f"📊 Before cleanup: {len(DIAGNOSTIC_CACHE)} entries")
    print(f"   - fresh_entry: age=0s")
    print(f"   - old_entry: age=600s")
    print(f"   - expired_entry: age={CACHE_TTL + 1}s")
    print(f"   - almost_expired: age={CACHE_TTL - 10}s")
    
    # Run cleanup
    cleanup_expired_cache()
    
    print(f"📊 After cleanup: {len(DIAGNOSTIC_CACHE)} entries")
    
    # Verify results
    assert 'fresh_entry' in DIAGNOSTIC_CACHE, "❌ Fresh entry should NOT be removed"
    assert 'almost_expired' in DIAGNOSTIC_CACHE, "❌ Almost expired entry should NOT be removed"
    assert 'old_entry' not in DIAGNOSTIC_CACHE, "❌ Old entry SHOULD be removed"
    assert 'expired_entry' not in DIAGNOSTIC_CACHE, "❌ Expired entry SHOULD be removed"
    
    print("✅ Test passed: cleanup_expired_cache() works correctly!")
    print(f"   - Kept: fresh_entry, almost_expired")
    print(f"   - Removed: old_entry, expired_entry")
    
    return True

def test_no_expired_entries():
    """Test cleanup when no entries are expired"""
    
    print("\n🧪 Testing cleanup with no expired entries...")
    
    # Clear cache
    DIAGNOSTIC_CACHE.clear()
    
    # Add only fresh entries
    now = time.time()
    DIAGNOSTIC_CACHE['entry1'] = (now, "data1")
    DIAGNOSTIC_CACHE['entry2'] = (now - 10, "data2")  # 10 sec ago
    DIAGNOSTIC_CACHE['entry3'] = (now - 60, "data3")  # 1 min ago
    
    print(f"📊 Before cleanup: {len(DIAGNOSTIC_CACHE)} entries")
    
    # Run cleanup
    cleanup_expired_cache()
    
    print(f"📊 After cleanup: {len(DIAGNOSTIC_CACHE)} entries")
    
    # All entries should remain
    assert len(DIAGNOSTIC_CACHE) == 3, "❌ No entries should be removed"
    
    print("✅ Test passed: cleanup preserves fresh entries!")
    
    return True

def test_empty_cache():
    """Test cleanup on empty cache"""
    
    print("\n🧪 Testing cleanup on empty cache...")
    
    # Clear cache
    DIAGNOSTIC_CACHE.clear()
    
    print(f"📊 Before cleanup: {len(DIAGNOSTIC_CACHE)} entries")
    
    # Run cleanup (should not crash)
    cleanup_expired_cache()
    
    print(f"📊 After cleanup: {len(DIAGNOSTIC_CACHE)} entries")
    
    assert len(DIAGNOSTIC_CACHE) == 0, "❌ Empty cache should remain empty"
    
    print("✅ Test passed: cleanup handles empty cache!")
    
    return True

def main():
    """Run all tests"""
    
    print("=" * 60)
    print("🧪 PR #5 MEMORY LEAK FIX - Cache Cleanup Tests")
    print("=" * 60)
    print()
    
    try:
        test_cleanup_expired_cache()
        test_no_expired_entries()
        test_empty_cache()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print()
        print("📝 Summary:")
        print("   - cleanup_expired_cache() correctly removes expired entries")
        print("   - Fresh entries are preserved")
        print("   - Empty cache is handled safely")
        print()
        print("🎯 Memory leak fix is working as expected!")
        print()
        
        return 0
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
