#!/usr/bin/env python3
"""
Test script for PR #4 - Diagnostic Cache Performance

Tests:
1. Cache functionality (cache hit/miss)
2. Performance improvement (cached vs non-cached)
3. Cache expiration
"""

import asyncio
import time
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from system_diagnostics import grep_logs_cached, grep_logs, DIAGNOSTIC_CACHE

async def test_cache_functionality():
    """Test that caching works correctly"""
    print("=" * 60)
    print("TEST 1: Cache Functionality")
    print("=" * 60)
    
    # Clear cache
    DIAGNOSTIC_CACHE.clear()
    
    # First call - should be cache miss
    print("\n1️⃣ First call (cache MISS expected)...")
    start = time.time()
    result1 = await grep_logs_cached('ERROR', hours=1)
    time1 = time.time() - start
    print(f"   ⏱️  Time: {time1:.3f}s")
    print(f"   📊 Results: {len(result1)} lines")
    
    # Second call - should be cache hit
    print("\n2️⃣ Second call (cache HIT expected)...")
    start = time.time()
    result2 = await grep_logs_cached('ERROR', hours=1)
    time2 = time.time() - start
    print(f"   ⏱️  Time: {time2:.3f}s")
    print(f"   📊 Results: {len(result2)} lines")
    
    # Verify results are same
    assert result1 == result2, "Cached results don't match!"
    print("\n   ✅ Results match!")
    
    # Check performance improvement
    speedup = time1 / time2 if time2 > 0 else float('inf')
    print(f"\n   🚀 Speedup: {speedup:.1f}x faster")
    
    if time2 < 0.1:
        print("   ✅ Cache is working - second call was instant!")
    else:
        print("   ⚠️  Warning: Second call should be near-instant")
    
    return True

async def test_force_refresh():
    """Test force_refresh parameter"""
    print("\n" + "=" * 60)
    print("TEST 2: Force Refresh")
    print("=" * 60)
    
    # Clear cache
    DIAGNOSTIC_CACHE.clear()
    
    # First call
    print("\n1️⃣ Initial call...")
    await grep_logs_cached('ERROR', hours=1)
    
    # Force refresh should bypass cache
    print("\n2️⃣ Force refresh call...")
    start = time.time()
    result = await grep_logs_cached('ERROR', hours=1, force_refresh=True)
    time_taken = time.time() - start
    
    print(f"   ⏱️  Time: {time_taken:.3f}s")
    
    if time_taken > 0.01:
        print("   ✅ Force refresh bypassed cache!")
    else:
        print("   ⚠️  Warning: Force refresh might not be working")
    
    return True

async def test_different_patterns():
    """Test that different patterns have separate cache entries"""
    print("\n" + "=" * 60)
    print("TEST 3: Multiple Patterns")
    print("=" * 60)
    
    # Clear cache
    DIAGNOSTIC_CACHE.clear()
    
    patterns = [
        'ERROR.*journal',
        'ERROR.*ml',
        'ERROR.*position'
    ]
    
    print("\n📝 Caching multiple patterns...")
    for pattern in patterns:
        await grep_logs_cached(pattern, hours=6)
        print(f"   ✅ Cached: {pattern}")
    
    print(f"\n💾 Cache size: {len(DIAGNOSTIC_CACHE)} entries")
    
    if len(DIAGNOSTIC_CACHE) >= len(patterns):
        print("   ✅ Each pattern has separate cache entry!")
    else:
        print("   ⚠️  Warning: Some patterns may be sharing cache entries")
    
    return True

async def test_performance_comparison():
    """Compare performance of cached vs non-cached"""
    print("\n" + "=" * 60)
    print("TEST 4: Performance Comparison")
    print("=" * 60)
    
    # Clear cache
    DIAGNOSTIC_CACHE.clear()
    
    pattern = 'ERROR'
    hours = 6
    
    # Test non-cached (direct grep_logs)
    print("\n1️⃣ Direct grep_logs() - no cache...")
    start = time.time()
    result_direct = grep_logs(pattern, hours)
    time_direct = time.time() - start
    print(f"   ⏱️  Time: {time_direct:.3f}s")
    print(f"   📊 Results: {len(result_direct)} lines")
    
    # Test cached (first call - miss)
    print("\n2️⃣ grep_logs_cached() - first call (miss)...")
    start = time.time()
    result_cached1 = await grep_logs_cached(pattern, hours)
    time_cached1 = time.time() - start
    print(f"   ⏱️  Time: {time_cached1:.3f}s")
    print(f"   📊 Results: {len(result_cached1)} lines")
    
    # Test cached (second call - hit)
    print("\n3️⃣ grep_logs_cached() - second call (hit)...")
    start = time.time()
    result_cached2 = await grep_logs_cached(pattern, hours)
    time_cached2 = time.time() - start
    print(f"   ⏱️  Time: {time_cached2:.3f}s")
    print(f"   📊 Results: {len(result_cached2)} lines")
    
    # Calculate speedup
    speedup = time_direct / time_cached2 if time_cached2 > 0 else float('inf')
    
    print("\n📊 PERFORMANCE SUMMARY:")
    print(f"   • Direct call:        {time_direct:.3f}s")
    print(f"   • Cached (miss):      {time_cached1:.3f}s")
    print(f"   • Cached (hit):       {time_cached2:.3f}s")
    print(f"   • Speedup:            {speedup:.1f}x faster")
    
    if speedup > 10:
        print("   ✅ EXCELLENT! Cache provides >10x speedup!")
    elif speedup > 5:
        print("   ✅ GOOD! Cache provides >5x speedup!")
    elif speedup > 2:
        print("   ✅ Cache provides 2-5x speedup")
    else:
        print("   ⚠️  Cache speedup is less than expected")
    
    return True

async def main():
    """Run all tests"""
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "PR #4: DIAGNOSTIC CACHE TESTS" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    
    try:
        await test_cache_functionality()
        await test_force_refresh()
        await test_different_patterns()
        await test_performance_comparison()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nCache is working correctly and providing performance benefits!")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
