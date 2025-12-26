"""
Unit tests for Phase 2 Part 2: Market Integration
Tests MarketDataFetcher, MarketHelper, and formatting functions
"""

import pytest
import json
import os
import sys
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.market_data_fetcher import MarketDataFetcher
from utils.market_helper import MarketHelper, format_market_fundamental_section


class TestMarketDataFetcher:
    """Test MarketDataFetcher class"""
    
    def test_init(self):
        """Test initialization"""
        fetcher = MarketDataFetcher(cache_ttl=30)
        assert fetcher.cache_ttl == 30
        assert fetcher.cache is not None
    
    @patch('utils.market_data_fetcher.requests.get')
    def test_fetch_fear_greed_index_success(self, mock_get):
        """Test successful Fear & Greed Index fetch"""
        # Mock API response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': [{
                'value': '65',
                'value_classification': 'Greed',
                'timestamp': '1234567890'
            }]
        }
        mock_get.return_value = mock_response
        
        fetcher = MarketDataFetcher(cache_ttl=1)
        result = fetcher.get_fear_greed_index()
        
        assert result is not None
        assert result['value'] == 65
        assert result['label'] == 'Greed'
        assert 'timestamp' in result
    
    @patch('utils.market_data_fetcher.requests.get')
    def test_fear_greed_caching(self, mock_get):
        """Test that Fear & Greed Index is cached"""
        import tempfile
        import shutil
        
        # Create temporary cache directory
        temp_cache = tempfile.mkdtemp()
        
        try:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [{
                    'value': '70',
                    'value_classification': 'Greed',
                    'timestamp': '1234567890'
                }]
            }
            mock_get.return_value = mock_response
            
            # Use isolated cache
            from utils.news_cache import NewsCache
            fetcher = MarketDataFetcher(cache_ttl=60)
            fetcher.cache = NewsCache(cache_dir=temp_cache, ttl_minutes=60)
            
            # First call - should fetch from API
            result1 = fetcher.get_fear_greed_index()
            assert mock_get.call_count == 1
            
            # Second call - should use cache
            result2 = fetcher.get_fear_greed_index()
            assert mock_get.call_count == 1  # No additional call
            assert result1 == result2
        finally:
            # Cleanup
            shutil.rmtree(temp_cache, ignore_errors=True)
    
    @patch('utils.market_data_fetcher.requests.get')
    def test_get_market_overview_success(self, mock_get):
        """Test successful market overview fetch"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'data': {
                'market_cap_percentage': {'btc': 48.5},
                'total_market_cap': {'usd': 1850000000000},
                'total_volume': {'usd': 95000000000},
                'market_cap_change_percentage_24h_usd': 2.3
            }
        }
        mock_get.return_value = mock_response
        
        fetcher = MarketDataFetcher(cache_ttl=1)
        result = fetcher.get_market_overview()
        
        assert result is not None
        assert result['btc_dominance'] == 48.5
        assert result['market_cap'] == 1850000000000
        assert result['market_cap_change_24h'] == 2.3
        assert result['total_volume_24h'] == 95000000000
    
    @patch('utils.market_data_fetcher.requests.get')
    def test_api_error_handling(self, mock_get):
        """Test graceful handling of API errors"""
        import tempfile
        import shutil
        
        # Create temporary cache directory
        temp_cache = tempfile.mkdtemp()
        
        try:
            # Simulate timeout
            mock_get.side_effect = Exception("Connection timeout")
            
            from utils.news_cache import NewsCache
            fetcher = MarketDataFetcher(cache_ttl=1)
            fetcher.cache = NewsCache(cache_dir=temp_cache, ttl_minutes=1)
            
            result = fetcher.get_fear_greed_index()
            
            # Should return None, not raise exception
            assert result is None
        finally:
            # Cleanup
            shutil.rmtree(temp_cache, ignore_errors=True)
    
    @patch('utils.market_data_fetcher.requests.get')
    def test_cache_expiration(self, mock_get):
        """Test that cache expires after TTL"""
        import tempfile
        import shutil
        import time
        
        # Create temporary cache directory
        temp_cache = tempfile.mkdtemp()
        
        try:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                'data': [{
                    'value': '50',
                    'value_classification': 'Neutral',
                    'timestamp': '1234567890'
                }]
            }
            mock_get.return_value = mock_response
            
            # Use very short TTL for testing
            from utils.news_cache import NewsCache
            fetcher = MarketDataFetcher(cache_ttl=0.01)  # 0.01 minutes = 0.6 seconds
            fetcher.cache = NewsCache(cache_dir=temp_cache, ttl_minutes=0.01)
            
            # First call
            result1 = fetcher.get_fear_greed_index()
            assert mock_get.call_count == 1
            
            # Wait for cache to expire
            time.sleep(1)
            
            # Second call should fetch again
            result2 = fetcher.get_fear_greed_index()
            assert mock_get.call_count == 2  # Additional call made
        finally:
            # Cleanup
            shutil.rmtree(temp_cache, ignore_errors=True)


class TestMarketHelper:
    """Test MarketHelper class"""
    
    def test_init(self):
        """Test initialization"""
        helper = MarketHelper()
        assert helper.data_fetcher is not None
        assert helper.news_cache is not None
    
    @patch('config.config_loader.load_feature_flags')
    def test_is_enabled_when_flags_true(self, mock_load_flags):
        """Test is_enabled returns True when flags are enabled"""
        mock_load_flags.return_value = {
            'fundamental_analysis': {
                'enabled': True,
                'market_integration': True
            }
        }
        
        helper = MarketHelper()
        assert helper.is_enabled() == True
    
    @patch('config.config_loader.load_feature_flags')
    def test_is_disabled_when_flags_false(self, mock_load_flags):
        """Test is_enabled returns False when flags are disabled"""
        mock_load_flags.return_value = {
            'fundamental_analysis': {
                'enabled': False,
                'market_integration': False
            }
        }
        
        helper = MarketHelper()
        assert helper.is_enabled() == False
    
    @patch('config.config_loader.load_feature_flags')
    @patch.object(MarketDataFetcher, 'get_fear_greed_index')
    @patch.object(MarketDataFetcher, 'get_market_overview')
    def test_get_market_fundamentals(self, mock_overview, mock_fear_greed, mock_load_flags):
        """Test get_market_fundamentals aggregates data correctly"""
        # Enable feature
        mock_load_flags.return_value = {
            'fundamental_analysis': {
                'enabled': True,
                'market_integration': True
            }
        }
        
        # Mock data
        mock_fear_greed.return_value = {
            'value': 65,
            'label': 'Greed',
            'timestamp': '123'
        }
        mock_overview.return_value = {
            'btc_dominance': 48.5,
            'market_cap': 1850000000000,
            'market_cap_change_24h': 2.3,
            'total_volume_24h': 95000000000
        }
        
        helper = MarketHelper()
        result = helper.get_market_fundamentals('BTCUSDT')
        
        assert result is not None
        assert 'fear_greed' in result
        assert 'btc_dominance' in result
        assert 'market_cap' in result
        assert result['fear_greed']['value'] == 65
        assert result['btc_dominance'] == 48.5
    
    def test_generate_market_context_bullish(self):
        """Test market context generation for bullish conditions"""
        helper = MarketHelper()
        
        fundamentals = {
            'fear_greed': {
                'value': 65,
                'label': 'Greed'
            },
            'btc_dominance': 48.5
        }
        
        context = helper.generate_market_context(
            fundamentals=fundamentals,
            price_change_24h=3.5,  # Strong buying
            volume_24h=1000000
        )
        
        assert "Strong buying pressure" in context
        assert "Greed" in context
        assert "48.5%" in context
    
    def test_generate_market_context_bearish(self):
        """Test market context generation for bearish conditions"""
        helper = MarketHelper()
        
        fundamentals = {
            'fear_greed': {
                'value': 20,
                'label': 'Extreme Fear'
            },
            'btc_dominance': 55.0
        }
        
        context = helper.generate_market_context(
            fundamentals=fundamentals,
            price_change_24h=-3.5,  # Strong selling
            volume_24h=1000000
        )
        
        assert "Strong selling pressure" in context
        assert "Extreme Fear" in context
        assert "55.0%" in context


class TestFormatting:
    """Test formatting functions"""
    
    def test_format_market_fundamental_section(self):
        """Test complete formatting of fundamental section"""
        fundamentals = {
            'sentiment': {
                'score': 70,
                'label': 'POSITIVE',
                'top_news': [
                    {
                        'title': 'SEC approves Bitcoin ETF',
                        'impact': 20
                    }
                ]
            },
            'fear_greed': {
                'value': 65,
                'label': 'Greed'
            },
            'btc_dominance': 48.5,
            'market_cap': 1850000000000
        }
        
        market_context = "Strong buying pressure in market.\nFear & Greed in \"Greed\" zone - bullish conditions."
        
        result = format_market_fundamental_section(fundamentals, market_context)
        
        assert result != ""
        assert "MARKET SENTIMENT & FUNDAMENTALS" in result
        assert "POSITIVE" in result
        assert "Fear & Greed Index" in result
        assert "65" in result
        assert "48.5%" in result
        assert "1.85T" in result  # Market cap in trillions
        assert "MARKET CONTEXT" in result
        assert "Strong buying pressure" in result
    
    def test_format_returns_empty_when_no_data(self):
        """Test that formatting returns empty string when no data"""
        result = format_market_fundamental_section(None, "")
        assert result == ""
        
        result = format_market_fundamental_section({}, "")
        assert result == ""


if __name__ == '__main__':
    # Run tests
    pytest.main([__file__, '-v'])
