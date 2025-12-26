"""
News Cache Module
Simple file-based news caching to reduce API calls
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class NewsCache:
    """
    Simple file-based cache for news articles
    Reduces redundant API calls and improves performance
    """
    
    def __init__(self, cache_dir: str = 'cache', ttl_minutes: int = 60):
        """
        Initialize news cache
        
        Args:
            cache_dir: Directory for cache files (default: 'cache')
            ttl_minutes: Time-to-live in minutes (default: 60)
        """
        self.cache_dir = cache_dir
        self.ttl_minutes = ttl_minutes
        self.cache_file = os.path.join(cache_dir, 'news_cache.json')
        
        # Create cache directory if it doesn't exist
        os.makedirs(cache_dir, exist_ok=True)
        
        logger.info(f"NewsCache initialized: dir={cache_dir}, ttl={ttl_minutes}min")
    
    def get_cached_news(self, symbol: str) -> Optional[List[Dict]]:
        """
        Retrieve cached news articles for a symbol
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            
        Returns:
            List of news articles if cache valid, None if expired/missing
        """
        try:
            if not os.path.exists(self.cache_file):
                logger.debug(f"Cache file not found: {self.cache_file}")
                return None
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Check if symbol exists in cache
            if symbol not in cache_data:
                logger.debug(f"Symbol {symbol} not in cache")
                return None
            
            symbol_cache = cache_data[symbol]
            
            # Check if cache is expired
            cached_time = datetime.fromisoformat(symbol_cache['timestamp'])
            expiry_time = cached_time + timedelta(minutes=self.ttl_minutes)
            
            if datetime.now() > expiry_time:
                logger.info(f"Cache expired for {symbol} (cached at {cached_time})")
                return None
            
            logger.info(f"Cache HIT for {symbol}: {len(symbol_cache['articles'])} articles")
            return symbol_cache['articles']
            
        except Exception as e:
            logger.warning(f"Error reading cache: {e}")
            return None
    
    def set_cached_news(self, symbol: str, articles: List[Dict]) -> bool:
        """
        Store news articles in cache
        
        Args:
            symbol: Trading symbol
            articles: List of news article dicts
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load existing cache or create new
            cache_data = {}
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
            
            # Store articles with timestamp
            cache_data[symbol] = {
                'articles': articles,
                'timestamp': datetime.now().isoformat(),
                'count': len(articles)
            }
            
            # Write to file
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
            
            logger.info(f"Cached {len(articles)} articles for {symbol}")
            return True
            
        except Exception as e:
            logger.error(f"Error writing cache: {e}")
            return False
    
    def clear_cache(self, symbol: Optional[str] = None) -> bool:
        """
        Clear cache for specific symbol or all symbols
        
        Args:
            symbol: Symbol to clear (None = clear all)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.cache_file):
                logger.debug("No cache file to clear")
                return True
            
            if symbol is None:
                # Clear entire cache
                os.remove(self.cache_file)
                logger.info("Cleared entire news cache")
                return True
            
            # Clear specific symbol
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            if symbol in cache_data:
                del cache_data[symbol]
                
                with open(self.cache_file, 'w') as f:
                    json.dump(cache_data, f, indent=2)
                
                logger.info(f"Cleared cache for {symbol}")
            else:
                logger.debug(f"Symbol {symbol} not in cache")
            
            return True
            
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict:
        """
        Get cache statistics
        
        Returns:
            Dict with cache stats (symbols count, total articles, etc.)
        """
        try:
            if not os.path.exists(self.cache_file):
                return {'symbols': 0, 'total_articles': 0}
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            total_articles = sum(data['count'] for data in cache_data.values())
            
            return {
                'symbols': len(cache_data),
                'total_articles': total_articles,
                'cache_file': self.cache_file
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {'symbols': 0, 'total_articles': 0, 'error': str(e)}
