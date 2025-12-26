"""
Sentiment Analyzer for Crypto News
Uses keyword-based analysis to determine market sentiment
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class SentimentAnalyzer:
    """Analyzes crypto news sentiment using keyword matching"""
    
    # Positive keywords (bullish signals)
    POSITIVE_KEYWORDS = [
        'approve', 'approved', 'bullish', 'buy', 'rally', 'surge', 
        'gain', 'up', 'rise', 'rising', 'adoption', 'partnership',
        'etf', 'institutional', 'accumulate', 'moon', 'pump',
        'breakout', 'support', 'investment', 'upgrade', 'launch',
        'growth', 'positive', 'strong', 'momentum', 'recovery'
    ]
    
    # Negative keywords (bearish signals)
    NEGATIVE_KEYWORDS = [
        'ban', 'banned', 'bearish', 'sell', 'crash', 'dump',
        'down', 'fall', 'falling', 'decline', 'regulation', 'hack',
        'scam', 'lawsuit', 'probe', 'investigation', 'fear',
        'collapse', 'breakdown', 'resistance', 'warning', 'risk',
        'negative', 'weak', 'concern', 'threat', 'attack'
    ]
    
    # Source credibility weights
    SOURCE_WEIGHTS = {
        'bloomberg': 1.5,
        'reuters': 1.5,
        'coindesk': 1.3,
        'cointelegraph': 1.2,
        'cryptopanic': 1.0,
        'default': 0.8
    }
    
    def __init__(self, cache_ttl: int = 3600):
        """
        Initialize sentiment analyzer
        
        Args:
            cache_ttl: Cache time-to-live in seconds (default: 1 hour)
        """
        self.cache_ttl = cache_ttl
        self._cache = {}
        
    def analyze_news(self, news_articles: List[Dict]) -> Dict:
        """
        Analyze sentiment of news articles
        
        Args:
            news_articles: List of news dicts with 'title', 'source', 'time'
            
        Returns:
            {
                'score': 60,  # 0-100 (0=extreme bearish, 50=neutral, 100=extreme bullish)
                'label': 'POSITIVE',  # POSITIVE/NEGATIVE/NEUTRAL
                'top_news': [...],  # Top 3 impactful news
                'confidence': 0.85
            }
        """
        if not news_articles:
            logger.warning("No news articles provided for sentiment analysis")
            return self._neutral_sentiment()
        
        # Filter recent news (last 24 hours)
        recent_news = self._filter_recent_news(news_articles, hours=24)
        
        if not recent_news:
            logger.info("No recent news found (last 24h)")
            return self._neutral_sentiment()
        
        # Analyze each article
        sentiments = []
        for article in recent_news:
            score = self._analyze_text(article.get('title', ''))
            weight = self._get_source_weight(article.get('source', ''))
            
            sentiments.append({
                'title': article.get('title', ''),
                'score': score,
                'weight': weight,
                'impact': (score - 50) * weight,  # Normalized impact
                'time': article.get('time', '')
            })
        
        # Calculate weighted average
        if not sentiments:
            return self._neutral_sentiment()
        
        total_weight = sum(s['weight'] for s in sentiments)
        weighted_score = sum(s['score'] * s['weight'] for s in sentiments) / total_weight
        
        # Get top impactful news
        top_news = sorted(sentiments, key=lambda x: abs(x['impact']), reverse=True)[:3]
        
        return {
            'score': round(weighted_score, 1),
            'label': self._get_label(weighted_score),
            'top_news': top_news,
            'confidence': self._calculate_confidence(len(sentiments)),
            'analyzed_count': len(sentiments)
        }
    
    def _analyze_text(self, text: str) -> float:
        """
        Analyze text using keyword matching
        
        Args:
            text: Text to analyze (usually news title)
            
        Returns:
            Sentiment score (0-100)
        """
        if not text:
            return 50.0  # Neutral
        
        text_lower = text.lower()
        
        # Count keyword occurrences
        pos_count = sum(1 for word in self.POSITIVE_KEYWORDS if word in text_lower)
        neg_count = sum(1 for word in self.NEGATIVE_KEYWORDS if word in text_lower)
        
        if pos_count + neg_count == 0:
            return 50.0  # Neutral (no keywords found)
        
        # Calculate sentiment ratio
        ratio = pos_count / (pos_count + neg_count)
        
        # Convert to 0-100 scale with amplification
        # ratio 0.0 (all negative) -> 0
        # ratio 0.5 (neutral) -> 50
        # ratio 1.0 (all positive) -> 100
        score = ratio * 100
        
        # Amplify extreme sentiments
        if score < 30:
            score = max(0, score - 10)  # Make bearish more extreme
        elif score > 70:
            score = min(100, score + 10)  # Make bullish more extreme
        
        return round(score, 1)
    
    def _get_source_weight(self, source: str) -> float:
        """Get credibility weight for news source"""
        source_lower = source.lower()
        
        for key, weight in self.SOURCE_WEIGHTS.items():
            if key in source_lower:
                return weight
        
        return self.SOURCE_WEIGHTS['default']
    
    def _filter_recent_news(self, news_articles: List[Dict], hours: int = 24) -> List[Dict]:
        """Filter news from last N hours"""
        try:
            cutoff = datetime.now() - timedelta(hours=hours)
            
            recent = []
            for article in news_articles:
                # Try to parse timestamp
                time_str = article.get('time', '')
                if time_str:
                    try:
                        article_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                        if article_time >= cutoff:
                            recent.append(article)
                    except:
                        # If parsing fails, include it (better safe than sorry)
                        recent.append(article)
                else:
                    recent.append(article)
            
            return recent
        except Exception as e:
            logger.warning(f"Error filtering recent news: {e}")
            return news_articles  # Return all if filtering fails
    
    def _get_label(self, score: float) -> str:
        """Convert score to label"""
        if score >= 60:
            return 'POSITIVE'
        elif score <= 40:
            return 'NEGATIVE'
        else:
            return 'NEUTRAL'
    
    def _calculate_confidence(self, article_count: int) -> float:
        """Calculate confidence based on number of articles analyzed"""
        if article_count >= 5:
            return 0.9
        elif article_count >= 3:
            return 0.75
        elif article_count >= 1:
            return 0.6
        else:
            return 0.3
    
    def _neutral_sentiment(self) -> Dict:
        """Return neutral sentiment (fallback)"""
        return {
            'score': 50.0,
            'label': 'NEUTRAL',
            'top_news': [],
            'confidence': 0.3,
            'analyzed_count': 0
        }
