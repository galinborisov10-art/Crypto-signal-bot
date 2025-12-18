"""
Cache Manager - LRU Cache with TTL Expiration
Implements least-recently-used cache with time-to-live expiration for signal caching.

Author: galinborisov10-art
Date: 2025-12-18
"""

import logging
import time
from collections import OrderedDict
from typing import Optional, Any, Dict, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class CacheManager:
    """
    LRU Cache with TTL expiration.
    
    Features:
    - Least Recently Used (LRU) eviction policy
    - Time-to-Live (TTL) expiration
    - Statistics tracking (hits, misses, evictions, expirations)
    - Thread-safe operations
    - Convenience methods for signal caching
    """
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """
        Initialize the cache manager.
        
        Args:
            max_size: Maximum number of entries in cache (default: 100)
            ttl_seconds: Default time-to-live in seconds (default: 3600 = 1 hour)
        """
        self.max_size = max_size
        self.default_ttl = ttl_seconds
        
        # OrderedDict maintains insertion order for LRU
        self._cache: OrderedDict[str, Tuple[Any, float]] = OrderedDict()
        
        # Statistics
        self._hits = 0
        self._misses = 0
        self._evictions = 0
        self._expirations = 0
        
        logger.info(f"CacheManager initialized (max_size={max_size}, ttl={ttl_seconds}s)")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Checks expiration and moves to end if valid (LRU).
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        if key not in self._cache:
            self._misses += 1
            logger.debug(f"Cache miss: {key}")
            return None
        
        # Get value and expiration time
        value, expiration_time = self._cache[key]
        
        # Check if expired
        current_time = time.time()
        if current_time > expiration_time:
            # Remove expired entry
            del self._cache[key]
            self._expirations += 1
            self._misses += 1
            logger.debug(f"Cache expired: {key}")
            return None
        
        # Move to end (most recently used)
        self._cache.move_to_end(key)
        self._hits += 1
        logger.debug(f"Cache hit: {key}")
        
        return value
    
    def set(self, key: str, value: Any, ttl_seconds: Optional[int] = None) -> None:
        """
        Set value in cache.
        
        Adds entry and evicts oldest if max_size exceeded.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Custom TTL (uses default if None)
        """
        # Calculate expiration time
        ttl = ttl_seconds if ttl_seconds is not None else self.default_ttl
        expiration_time = time.time() + ttl
        
        # Check if key already exists
        if key in self._cache:
            # Update existing entry
            self._cache[key] = (value, expiration_time)
            self._cache.move_to_end(key)
            logger.debug(f"Cache updated: {key}")
        else:
            # Add new entry
            self._cache[key] = (value, expiration_time)
            logger.debug(f"Cache set: {key}")
            
            # Check if size exceeded
            if len(self._cache) > self.max_size:
                # Remove oldest entry (first item)
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
                logger.debug(f"Cache evicted (LRU): {oldest_key}")
    
    def cache_signal(
        self,
        symbol: str,
        timeframe: str,
        signal: Any,
        ttl: Optional[int] = None
    ) -> None:
        """
        Convenience method for caching signals.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            timeframe: Timeframe (e.g., "1H")
            signal: Signal object to cache
            ttl: Optional custom TTL
        """
        key = f"signal:{symbol}:{timeframe}"
        self.set(key, signal, ttl)
        logger.info(f"Cached signal: {symbol} {timeframe}")
    
    def get_cached_signal(self, symbol: str, timeframe: str) -> Optional[Any]:
        """
        Convenience method for retrieving cached signals.
        
        Args:
            symbol: Trading symbol (e.g., "BTCUSDT")
            timeframe: Timeframe (e.g., "1H")
            
        Returns:
            Cached signal or None
        """
        key = f"signal:{symbol}:{timeframe}"
        signal = self.get(key)
        if signal:
            logger.info(f"Retrieved cached signal: {symbol} {timeframe}")
        return signal
    
    def clear(self) -> None:
        """Clear all cache entries."""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} entries removed")
    
    def remove(self, key: str) -> bool:
        """
        Remove specific key from cache.
        
        Args:
            key: Cache key to remove
            
        Returns:
            True if key was removed, False if not found
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache removed: {key}")
            return True
        return False
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict with cache statistics
        """
        total_requests = self._hits + self._misses
        hit_rate = (self._hits / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': round(hit_rate, 2),
            'evictions': self._evictions,
            'expirations': self._expirations,
            'total_requests': total_requests
        }
    
    def get_detailed_stats(self) -> str:
        """
        Get formatted detailed statistics.
        
        Returns:
            Formatted statistics string
        """
        stats = self.get_stats()
        
        output = "📊 **Cache Statistics**\n\n"
        output += f"**Size:** {stats['size']}/{stats['max_size']} entries\n"
        output += f"**Requests:** {stats['total_requests']} total\n"
        output += f"**Hits:** {stats['hits']} ({stats['hit_rate']:.1f}%)\n"
        output += f"**Misses:** {stats['misses']}\n"
        output += f"**Evictions:** {stats['evictions']} (LRU)\n"
        output += f"**Expirations:** {stats['expirations']} (TTL)\n"
        
        return output
    
    def cleanup_expired(self) -> int:
        """
        Manually cleanup expired entries.
        
        Returns:
            Number of entries removed
        """
        current_time = time.time()
        expired_keys = []
        
        # Find expired keys
        for key, (value, expiration_time) in self._cache.items():
            if current_time > expiration_time:
                expired_keys.append(key)
        
        # Remove expired keys
        for key in expired_keys:
            del self._cache[key]
            self._expirations += 1
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
        
        return len(expired_keys)
    
    def get_keys(self) -> list:
        """
        Get all cache keys.
        
        Returns:
            List of cache keys
        """
        return list(self._cache.keys())
    
    def contains(self, key: str) -> bool:
        """
        Check if key exists in cache (without updating LRU).
        
        Args:
            key: Cache key
            
        Returns:
            True if key exists and not expired
        """
        if key not in self._cache:
            return False
        
        # Check expiration without updating LRU
        value, expiration_time = self._cache[key]
        current_time = time.time()
        
        if current_time > expiration_time:
            # Expired but still in cache
            return False
        
        return True


# Global cache manager instance
_cache_manager_instance: Optional[CacheManager] = None


def get_cache_manager(max_size: int = 100, ttl_seconds: int = 3600) -> CacheManager:
    """
    Get or create global cache manager instance (singleton).
    
    Args:
        max_size: Maximum cache size (only used on first call)
        ttl_seconds: Default TTL (only used on first call)
        
    Returns:
        CacheManager instance
    """
    global _cache_manager_instance
    
    if _cache_manager_instance is None:
        _cache_manager_instance = CacheManager(max_size, ttl_seconds)
        logger.info("Created global cache manager instance")
    
    return _cache_manager_instance


def reset_cache_manager() -> None:
    """Reset global cache manager instance (for testing)."""
    global _cache_manager_instance
    _cache_manager_instance = None
    logger.info("Reset global cache manager instance")


# Example usage
if __name__ == "__main__":
    print("🗄️ Cache Manager - Test Mode")
    
    # Create cache manager
    cache = CacheManager(max_size=5, ttl_seconds=2)
    
    # Test basic operations
    print("\n1. Testing basic set/get:")
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    print(f"   Get key1: {cache.get('key1')}")
    print(f"   Get key2: {cache.get('key2')}")
    print(f"   Get key3 (missing): {cache.get('key3')}")
    
    # Test LRU eviction
    print("\n2. Testing LRU eviction:")
    for i in range(3, 8):
        cache.set(f"key{i}", f"value{i}")
    print(f"   Cache keys: {cache.get_keys()}")
    print(f"   Get key1 (evicted): {cache.get('key1')}")
    
    # Test TTL expiration
    print("\n3. Testing TTL expiration:")
    cache.set("temp_key", "temp_value", ttl_seconds=1)
    print(f"   Get temp_key (fresh): {cache.get('temp_key')}")
    print("   Waiting 2 seconds...")
    time.sleep(2)
    print(f"   Get temp_key (expired): {cache.get('temp_key')}")
    
    # Test signal caching
    print("\n4. Testing signal caching:")
    test_signal = {
        'symbol': 'BTCUSDT',
        'type': 'BUY',
        'confidence': 85
    }
    cache.cache_signal("BTCUSDT", "1H", test_signal)
    retrieved = cache.get_cached_signal("BTCUSDT", "1H")
    print(f"   Retrieved signal: {retrieved}")
    
    # Test statistics
    print("\n5. Cache Statistics:")
    print(cache.get_detailed_stats())
    
    # Test cleanup
    print("\n6. Testing manual cleanup:")
    cache.set("expire1", "val1", ttl_seconds=1)
    cache.set("expire2", "val2", ttl_seconds=1)
    time.sleep(2)
    removed = cache.cleanup_expired()
    print(f"   Removed {removed} expired entries")
    
    # Final stats
    print("\n7. Final Statistics:")
    stats = cache.get_stats()
    print(f"   Size: {stats['size']}/{stats['max_size']}")
    print(f"   Hit rate: {stats['hit_rate']:.1f}%")
    print(f"   Evictions: {stats['evictions']}")
    print(f"   Expirations: {stats['expirations']}")
    
    # Test singleton
    print("\n8. Testing singleton pattern:")
    cache1 = get_cache_manager()
    cache2 = get_cache_manager()
    print(f"   Same instance: {cache1 is cache2}")
    
    print("\n✅ Cache Manager test completed!")
