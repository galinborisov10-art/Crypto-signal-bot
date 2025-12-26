"""
Unit tests for fundamental analysis modules
"""

import pytest
from datetime import datetime, timedelta
from fundamental.sentiment_analyzer import SentimentAnalyzer
from fundamental.btc_correlator import BTCCorrelator
import pandas as pd
import numpy as np


class TestSentimentAnalyzer:
    """Test sentiment analyzer"""
    
    def test_positive_sentiment(self):
        """Test detection of positive news"""
        analyzer = SentimentAnalyzer()
        
        news = [
            {
                'title': 'SEC approves Bitcoin ETF - bullish rally expected',
                'source': 'Bloomberg',
                'time': datetime.now().isoformat()
            }
        ]
        
        result = analyzer.analyze_news(news)
        
        assert result['score'] > 60, "Should detect positive sentiment"
        assert result['label'] == 'POSITIVE'
        assert result['confidence'] > 0.5
    
    def test_negative_sentiment(self):
        """Test detection of negative news"""
        analyzer = SentimentAnalyzer()
        
        news = [
            {
                'title': 'China bans crypto trading - market crash feared',
                'source': 'Reuters',
                'time': datetime.now().isoformat()
            }
        ]
        
        result = analyzer.analyze_news(news)
        
        assert result['score'] < 40, "Should detect negative sentiment"
        assert result['label'] == 'NEGATIVE'
    
    def test_neutral_sentiment(self):
        """Test neutral news"""
        analyzer = SentimentAnalyzer()
        
        news = [
            {
                'title': 'Bitcoin price remains stable at current levels',
                'source': 'CoinDesk',
                'time': datetime.now().isoformat()
            }
        ]
        
        result = analyzer.analyze_news(news)
        
        assert 40 <= result['score'] <= 60, "Should detect neutral sentiment"
        assert result['label'] == 'NEUTRAL'
    
    def test_empty_news(self):
        """Test handling of empty news list"""
        analyzer = SentimentAnalyzer()
        
        result = analyzer.analyze_news([])
        
        assert result['score'] == 50.0, "Should return neutral for empty news"
        assert result['label'] == 'NEUTRAL'


class TestBTCCorrelator:
    """Test BTC correlator"""
    
    def test_positive_correlation_aligned(self):
        """Test strong positive correlation with aligned trends"""
        correlator = BTCCorrelator(window=30)
        
        # Generate correlated data
        dates = pd.date_range(end=datetime.now(), periods=50, freq='1h')
        base_prices = np.linspace(100, 110, 50)  # Uptrend
        noise = np.random.normal(0, 0.5, 50)
        
        btc_df = pd.DataFrame({
            'close': base_prices + noise
        }, index=dates)
        
        symbol_df = pd.DataFrame({
            'close': base_prices * 0.5 + noise * 0.3  # Correlated
        }, index=dates)
        
        result = correlator.calculate_correlation('ETHUSDT', symbol_df, btc_df)
        
        assert result is not None
        assert result['correlation'] > 0.7, "Should detect strong correlation"
        assert result['aligned'] == True, "Trends should be aligned"
        assert result['impact'] > 0, "Should boost confidence"
    
    def test_skip_btc_symbol(self):
        """Test that BTC symbol is skipped"""
        correlator = BTCCorrelator()
        
        df = pd.DataFrame({'close': [100, 101, 102]})
        
        result = correlator.calculate_correlation('BTCUSDT', df, df)
        
        assert result is None, "Should skip BTC symbol"
