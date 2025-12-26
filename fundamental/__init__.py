"""
Fundamental Analysis Module
Provides sentiment analysis and BTC correlation for trading signals
"""

__version__ = '1.0.0'
__all__ = ['SentimentAnalyzer', 'BTCCorrelator']

from .sentiment_analyzer import SentimentAnalyzer
from .btc_correlator import BTCCorrelator
