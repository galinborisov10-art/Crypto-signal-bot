"""
Integration Tests for Phase 2 Part 1: Signal Enhancement with Fundamental Analysis
Tests FundamentalHelper, NewsCache, and formatting functions
"""

import pytest
import os
import sys
import json
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.news_cache import NewsCache
from utils.fundamental_helper import FundamentalHelper, format_fundamental_section
from fundamental.sentiment_analyzer import SentimentAnalyzer
from fundamental.btc_correlator import BTCCorrelator


class TestFundamentalHelper:
    """Test FundamentalHelper class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.helper = FundamentalHelper()
    
    def test_is_enabled_when_flags_false(self):
        """Test feature detection when flags are disabled (default)"""
        # Default flags should be false
        enabled = self.helper.is_enabled()
        assert enabled == False, "Should be disabled by default"
    
    def test_is_enabled_when_flags_true(self, tmp_path, monkeypatch):
        """Test feature detection when all required flags are true"""
        # Create temp config with enabled flags
        config_file = tmp_path / "feature_flags.json"
        config_data = {
            "fundamental_analysis": {
                "enabled": True,
                "sentiment_analysis": True,
                "btc_correlation": True,
                "signal_integration": True
            }
        }
        
        with open(config_file, 'w') as f:
            json.dump(config_data, f)
        
        # Monkey patch the config path
        import config.config_loader as loader
        original_path = loader.CONFIG_PATH
        loader.CONFIG_PATH = str(config_file)
        
        try:
            helper = FundamentalHelper()
            enabled = helper.is_enabled()
            assert enabled == True, "Should be enabled when all flags are true"
        finally:
            loader.CONFIG_PATH = original_path
    
    def test_combined_score_technical_only(self):
        """Test combined score with technical analysis only (no fundamental data)"""
        technical_confidence = 78.0
        fundamental_data = {}
        
        result = self.helper.calculate_combined_score(
            technical_confidence=technical_confidence,
            fundamental_data=fundamental_data
        )
        
        assert result['combined_score'] == 78.0, "Should equal technical confidence"
        assert result['sentiment_contribution'] == 0.0
        assert result['btc_correlation_contribution'] == 0.0
    
    def test_combined_score_with_positive_sentiment(self):
        """Test combined score with positive sentiment boost"""
        technical_confidence = 78.0
        fundamental_data = {
            'sentiment': {
                'score': 70,  # (70-50) * 0.3 = +6
                'label': 'POSITIVE',
                'top_news': [],
                'confidence': 0.85
            }
        }
        
        result = self.helper.calculate_combined_score(
            technical_confidence=technical_confidence,
            fundamental_data=fundamental_data
        )
        
        # Expected: 78 + 6 = 84
        assert result['combined_score'] == 84.0, f"Expected 84, got {result['combined_score']}"
        assert result['sentiment_contribution'] == 6.0
    
    def test_combined_score_with_negative_sentiment(self):
        """Test combined score with negative sentiment penalty"""
        technical_confidence = 78.0
        fundamental_data = {
            'sentiment': {
                'score': 30,  # (30-50) * 0.3 = -6
                'label': 'NEGATIVE',
                'top_news': [],
                'confidence': 0.75
            }
        }
        
        result = self.helper.calculate_combined_score(
            technical_confidence=technical_confidence,
            fundamental_data=fundamental_data
        )
        
        # Expected: 78 - 6 = 72
        assert result['combined_score'] == 72.0, f"Expected 72, got {result['combined_score']}"
        assert result['sentiment_contribution'] == -6.0
    
    def test_combined_score_with_btc_divergence(self):
        """Test combined score with BTC divergence penalty"""
        technical_confidence = 78.0
        fundamental_data = {
            'btc_correlation': {
                'correlation': 0.92,
                'btc_trend': 'BEARISH',
                'symbol_trend': 'BULLISH',
                'aligned': False,
                'impact': -15,  # Strong divergence penalty
                'btc_change': -2.1,
                'symbol_change': +2.3
            }
        }
        
        result = self.helper.calculate_combined_score(
            technical_confidence=technical_confidence,
            fundamental_data=fundamental_data
        )
        
        # Expected: 78 - 15 = 63
        assert result['combined_score'] == 63.0, f"Expected 63, got {result['combined_score']}"
        assert result['btc_correlation_contribution'] == -15.0
    
    def test_combined_score_with_both_positive(self):
        """Test combined score with both sentiment and BTC alignment positive"""
        technical_confidence = 78.0
        fundamental_data = {
            'sentiment': {
                'score': 70,  # +6
                'label': 'POSITIVE',
                'top_news': [],
                'confidence': 0.85
            },
            'btc_correlation': {
                'correlation': 0.92,
                'btc_trend': 'BULLISH',
                'symbol_trend': 'BULLISH',
                'aligned': True,
                'impact': +10,  # Strong alignment boost
                'btc_change': +2.1,
                'symbol_change': +2.3
            }
        }
        
        result = self.helper.calculate_combined_score(
            technical_confidence=technical_confidence,
            fundamental_data=fundamental_data
        )
        
        # Expected: 78 + 6 + 10 = 94
        assert result['combined_score'] == 94.0, f"Expected 94, got {result['combined_score']}"
        assert result['sentiment_contribution'] == 6.0
        assert result['btc_correlation_contribution'] == 10.0
    
    def test_recommendation_strong_bullish(self):
        """Test recommendation generation for strong bullish signal"""
        fundamental_data = {
            'sentiment': {
                'score': 70,
                'label': 'POSITIVE',
                'top_news': [],
                'confidence': 0.85
            },
            'btc_correlation': {
                'correlation': 0.92,
                'btc_trend': 'BULLISH',
                'symbol_trend': 'BULLISH',
                'aligned': True,
                'impact': +10,
                'btc_change': +2.1,
                'symbol_change': +2.3
            }
        }
        
        recommendation = self.helper.generate_recommendation(
            signal_direction='BULLISH',
            technical_confidence=78.0,
            fundamental_data=fundamental_data,
            combined_score=94.0
        )
        
        assert 'Strong conditions for LONG' in recommendation
        assert 'Both technical and fundamental' in recommendation
    
    def test_recommendation_btc_divergence_warning(self):
        """Test recommendation includes warning for BTC divergence"""
        fundamental_data = {
            'btc_correlation': {
                'correlation': 0.92,
                'btc_trend': 'BEARISH',
                'symbol_trend': 'BULLISH',
                'aligned': False,
                'impact': -15,
                'btc_change': -2.1,
                'symbol_change': +2.3
            }
        }
        
        recommendation = self.helper.generate_recommendation(
            signal_direction='BULLISH',
            technical_confidence=78.0,
            fundamental_data=fundamental_data,
            combined_score=63.0
        )
        
        assert 'WARNING' in recommendation
        assert 'BTC divergence' in recommendation.lower() or 'divergence' in recommendation.lower()
    
    def test_combined_score_clamped_to_100(self):
        """Test that combined score is clamped to 100 max"""
        technical_confidence = 95.0
        fundamental_data = {
            'sentiment': {
                'score': 100,  # +15
                'label': 'POSITIVE'
            },
            'btc_correlation': {
                'correlation': 0.95,
                'aligned': True,
                'impact': +10
            }
        }
        
        result = self.helper.calculate_combined_score(
            technical_confidence=technical_confidence,
            fundamental_data=fundamental_data
        )
        
        # Would be 95 + 15 + 10 = 120, but should clamp to 100
        assert result['combined_score'] == 100.0
        assert result['combined_score'] <= 100.0


class TestNewsCache:
    """Test NewsCache class"""
    
    def setup_method(self):
        """Setup test fixtures with temp cache directory"""
        self.test_cache_dir = 'cache/test_cache'
        os.makedirs(self.test_cache_dir, exist_ok=True)
        self.cache = NewsCache(cache_dir=self.test_cache_dir, ttl_minutes=1)
    
    def teardown_method(self):
        """Cleanup test cache"""
        import shutil
        if os.path.exists(self.test_cache_dir):
            shutil.rmtree(self.test_cache_dir)
    
    def test_cache_miss_on_empty(self):
        """Test cache returns None when empty"""
        result = self.cache.get_cached_news('BTCUSDT')
        assert result is None, "Should return None for cache miss"
    
    def test_cache_set_and_get(self):
        """Test caching works - set and retrieve"""
        articles = [
            {'title': 'Bitcoin reaches new high', 'source': 'Bloomberg', 'time': datetime.now().isoformat()},
            {'title': 'ETF approved', 'source': 'Reuters', 'time': datetime.now().isoformat()}
        ]
        
        # Set cache
        success = self.cache.set_cached_news('BTCUSDT', articles)
        assert success == True, "Should successfully cache articles"
        
        # Get cache
        cached = self.cache.get_cached_news('BTCUSDT')
        assert cached is not None, "Should retrieve cached articles"
        assert len(cached) == 2, "Should have 2 articles"
        assert cached[0]['title'] == 'Bitcoin reaches new high'
    
    def test_cache_expiration(self):
        """Test TTL expiration works"""
        articles = [
            {'title': 'Old news', 'source': 'CoinDesk', 'time': datetime.now().isoformat()}
        ]
        
        # Use cache with very short TTL (we'll manually modify timestamp)
        self.cache.set_cached_news('ETHUSDT', articles)
        
        # Manually modify cache timestamp to be old
        cache_file = self.cache.cache_file
        with open(cache_file, 'r') as f:
            cache_data = json.load(f)
        
        # Set timestamp to 2 minutes ago (TTL is 1 minute)
        old_time = datetime.now() - timedelta(minutes=2)
        cache_data['ETHUSDT']['timestamp'] = old_time.isoformat()
        
        with open(cache_file, 'w') as f:
            json.dump(cache_data, f)
        
        # Should return None due to expiration
        result = self.cache.get_cached_news('ETHUSDT')
        assert result is None, "Should return None for expired cache"
    
    def test_clear_cache_single_symbol(self):
        """Test clearing cache for specific symbol"""
        # Add multiple symbols
        self.cache.set_cached_news('BTCUSDT', [{'title': 'BTC news'}])
        self.cache.set_cached_news('ETHUSDT', [{'title': 'ETH news'}])
        
        # Clear only BTC
        self.cache.clear_cache('BTCUSDT')
        
        # BTC should be gone, ETH should remain
        btc_cache = self.cache.get_cached_news('BTCUSDT')
        eth_cache = self.cache.get_cached_news('ETHUSDT')
        
        assert btc_cache is None, "BTC cache should be cleared"
        assert eth_cache is not None, "ETH cache should remain"
    
    def test_clear_all_cache(self):
        """Test clearing entire cache"""
        # Add multiple symbols
        self.cache.set_cached_news('BTCUSDT', [{'title': 'BTC news'}])
        self.cache.set_cached_news('ETHUSDT', [{'title': 'ETH news'}])
        
        # Clear all
        self.cache.clear_cache(None)
        
        # Both should be gone
        btc_cache = self.cache.get_cached_news('BTCUSDT')
        eth_cache = self.cache.get_cached_news('ETHUSDT')
        
        assert btc_cache is None, "BTC cache should be cleared"
        assert eth_cache is None, "ETH cache should be cleared"
    
    def test_cache_stats(self):
        """Test cache statistics"""
        # Add some articles
        self.cache.set_cached_news('BTCUSDT', [{'title': 'News 1'}, {'title': 'News 2'}])
        self.cache.set_cached_news('ETHUSDT', [{'title': 'News 3'}])
        
        stats = self.cache.get_cache_stats()
        
        assert stats['symbols'] == 2, "Should have 2 symbols"
        assert stats['total_articles'] == 3, "Should have 3 total articles"


class TestFormatting:
    """Test formatting functions"""
    
    def test_format_fundamental_section_with_all_data(self):
        """Test formatting with complete fundamental data"""
        fundamental_data = {
            'sentiment': {
                'score': 70,
                'label': 'POSITIVE',
                'top_news': [
                    {'title': 'SEC approves Bitcoin ETF', 'impact': 20, 'time': datetime.now().isoformat()}
                ],
                'confidence': 0.85
            },
            'btc_correlation': {
                'correlation': 0.92,
                'btc_trend': 'BULLISH',
                'symbol_trend': 'BULLISH',
                'aligned': True,
                'impact': +10,
                'btc_change': +2.1,
                'symbol_change': +2.3
            }
        }
        
        combined_analysis = {
            'combined_score': 94.0,
            'technical_contribution': 78.0,
            'sentiment_contribution': 6.0,
            'btc_correlation_contribution': 10.0
        }
        
        recommendation = "Strong conditions for LONG positions."
        
        result = format_fundamental_section(
            fundamental_data,
            combined_analysis,
            recommendation
        )
        
        assert len(result) > 0, "Should return formatted text"
        assert 'FUNDAMENTAL ANALYSIS' in result
        assert 'POSITIVE' in result
        assert 'BTC Correlation' in result
        assert 'COMBINED ANALYSIS' in result
        assert '94' in result  # Combined score
        assert 'RECOMMENDATION' in result
        assert recommendation in result
    
    def test_format_returns_empty_when_no_data(self):
        """Test formatting returns empty string when no fundamental data"""
        result = format_fundamental_section(
            fundamental_data=None,
            combined_analysis={},
            recommendation=""
        )
        
        assert result == "", "Should return empty string for no data"
        
        # Also test with empty dict
        result2 = format_fundamental_section(
            fundamental_data={},
            combined_analysis={},
            recommendation=""
        )
        
        assert result2 == "", "Should return empty string for empty data"


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
