"""
Fundamental Helper Module
Integrates fundamental analysis (sentiment + BTC correlation) with technical signals
"""

import logging
import os
import sys
from typing import Dict, List, Optional, Any
import pandas as pd

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fundamental.sentiment_analyzer import SentimentAnalyzer
from fundamental.btc_correlator import BTCCorrelator
from utils.news_cache import NewsCache

logger = logging.getLogger(__name__)


class FundamentalHelper:
    """
    Helper class for integrating fundamental analysis with trading signals
    Combines sentiment analysis and BTC correlation for enhanced signals
    """
    
    def __init__(self):
        """Initialize fundamental helper with analyzers"""
        self.sentiment_analyzer = SentimentAnalyzer(cache_ttl=3600)
        self.btc_correlator = BTCCorrelator(window=30)
        self.news_cache = NewsCache(cache_dir='cache', ttl_minutes=60)
        
        logger.info("FundamentalHelper initialized")
    
    def is_enabled(self) -> bool:
        """
        Check if fundamental analysis integration is enabled
        
        Returns:
            True if all required feature flags are enabled
        """
        try:
            # Import here to avoid circular dependency
            from config.config_loader import load_feature_flags
            
            flags = load_feature_flags()
            fundamental_flags = flags.get('fundamental_analysis', {})
            
            # All required flags must be enabled
            required = [
                fundamental_flags.get('enabled', False),
                fundamental_flags.get('sentiment_analysis', False),
                fundamental_flags.get('btc_correlation', False),
                fundamental_flags.get('signal_integration', False)
            ]
            
            enabled = all(required)
            logger.info(f"Fundamental analysis enabled: {enabled}")
            return enabled
            
        except Exception as e:
            logger.warning(f"Error checking feature flags: {e}")
            return False
    
    def get_fundamental_data(
        self,
        symbol: str,
        symbol_df: pd.DataFrame,
        btc_df: pd.DataFrame,
        news_articles: Optional[List[Dict]] = None
    ) -> Optional[Dict]:
        """
        Get fundamental analysis data (sentiment + BTC correlation)
        
        Args:
            symbol: Trading symbol (e.g., 'ETHUSDT')
            symbol_df: DataFrame with symbol price data
            btc_df: DataFrame with BTC price data
            news_articles: Optional list of news articles (uses cache if None)
            
        Returns:
            {
                'sentiment': {
                    'score': 65,
                    'label': 'POSITIVE',
                    'top_news': [...],
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
            Returns None if analysis fails
        """
        try:
            result = {}
            
            # Get sentiment analysis
            sentiment_data = self._get_sentiment(symbol, news_articles)
            if sentiment_data:
                result['sentiment'] = sentiment_data
            
            # Get BTC correlation
            correlation_data = self.btc_correlator.calculate_correlation(
                symbol=symbol,
                symbol_df=symbol_df,
                btc_df=btc_df
            )
            if correlation_data:
                result['btc_correlation'] = correlation_data
            
            if not result:
                logger.warning(f"No fundamental data available for {symbol}")
                return None
            
            logger.info(f"Fundamental data retrieved for {symbol}: {list(result.keys())}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting fundamental data: {e}")
            return None
    
    def _get_sentiment(
        self,
        symbol: str,
        news_articles: Optional[List[Dict]]
    ) -> Optional[Dict]:
        """
        Get sentiment analysis using cache or provided articles
        
        Args:
            symbol: Trading symbol
            news_articles: Optional news articles (uses cache if None)
            
        Returns:
            Sentiment analysis result or None
        """
        try:
            # Use provided articles or try cache
            if news_articles is None:
                news_articles = self.news_cache.get_cached_news(symbol)
            
            # If still no articles, return None (no API calls in signal)
            if not news_articles:
                logger.info(f"No news articles available for {symbol} (cache miss)")
                return None
            
            # Analyze sentiment
            sentiment = self.sentiment_analyzer.analyze_news(news_articles)
            return sentiment
            
        except Exception as e:
            logger.error(f"Error getting sentiment: {e}")
            return None
    
    def calculate_combined_score(
        self,
        technical_confidence: float,
        fundamental_data: Dict
    ) -> Dict:
        """
        Calculate combined score from technical and fundamental analysis
        
        Formula:
            combined = technical_confidence
                     + (sentiment_score - 50) * 0.3    # ±15 max
                     + btc_correlation_impact          # -15 to +10
            Clamped to 0-100
        
        Args:
            technical_confidence: Technical analysis confidence (0-100)
            fundamental_data: Dict with 'sentiment' and/or 'btc_correlation'
            
        Returns:
            {
                'combined_score': 72,
                'technical_contribution': 78,
                'sentiment_contribution': +6,
                'btc_correlation_contribution': +10,
                'breakdown': {
                    'technical': 78,
                    'sentiment_impact': +6,
                    'btc_impact': +10
                }
            }
        """
        try:
            # Start with technical confidence
            combined = float(technical_confidence)
            sentiment_impact = 0.0
            btc_impact = 0.0
            
            # Add sentiment impact (max ±15)
            if 'sentiment' in fundamental_data:
                sentiment_score = fundamental_data['sentiment']['score']
                sentiment_impact = (sentiment_score - 50) * 0.3
                combined += sentiment_impact
            
            # Add BTC correlation impact (-15 to +10)
            if 'btc_correlation' in fundamental_data:
                btc_impact = fundamental_data['btc_correlation']['impact']
                combined += btc_impact
            
            # Clamp to valid range
            combined = max(0, min(100, combined))
            
            result = {
                'combined_score': round(combined, 1),
                'technical_contribution': round(technical_confidence, 1),
                'sentiment_contribution': round(sentiment_impact, 1),
                'btc_correlation_contribution': round(btc_impact, 1),
                'breakdown': {
                    'technical': round(technical_confidence, 1),
                    'sentiment_impact': round(sentiment_impact, 1),
                    'btc_impact': round(btc_impact, 1)
                }
            }
            
            logger.info(f"Combined score calculated: {result['combined_score']} "
                       f"(tech={technical_confidence}, sent={sentiment_impact:+.1f}, btc={btc_impact:+.1f})")
            
            return result
            
        except Exception as e:
            logger.error(f"Error calculating combined score: {e}")
            # Fallback to technical only
            return {
                'combined_score': round(technical_confidence, 1),
                'technical_contribution': round(technical_confidence, 1),
                'sentiment_contribution': 0.0,
                'btc_correlation_contribution': 0.0,
                'breakdown': {
                    'technical': round(technical_confidence, 1),
                    'sentiment_impact': 0.0,
                    'btc_impact': 0.0
                }
            }
    
    def generate_recommendation(
        self,
        signal_direction: str,
        technical_confidence: float,
        fundamental_data: Dict,
        combined_score: float
    ) -> str:
        """
        Generate intelligent trading recommendation
        
        Args:
            signal_direction: 'BULLISH' or 'BEARISH'
            technical_confidence: Technical confidence (0-100)
            fundamental_data: Fundamental analysis data
            combined_score: Combined score from calculate_combined_score
            
        Returns:
            Recommendation text (multi-line)
        """
        try:
            lines = []
            
            # Overall assessment based on combined score
            if combined_score >= 70:
                strength = "Strong"
            elif combined_score >= 60:
                strength = "Favorable"
            elif combined_score >= 50:
                strength = "Moderate"
            else:
                strength = "Weak"
            
            direction_text = "LONG" if signal_direction in ['BULLISH', 'BUY', 'STRONG_BUY'] else "SHORT"
            lines.append(f"✅ {strength} conditions for {direction_text} positions.")
            
            # Check alignment between technical and fundamental
            technical_bullish = signal_direction in ['BULLISH', 'BUY', 'STRONG_BUY']
            
            sentiment_aligned = True
            btc_aligned = True
            
            if 'sentiment' in fundamental_data:
                sentiment_positive = fundamental_data['sentiment']['score'] >= 50
                sentiment_aligned = (technical_bullish == sentiment_positive)
            
            if 'btc_correlation' in fundamental_data:
                btc_aligned = fundamental_data['btc_correlation']['aligned']
            
            # Overall alignment message
            if sentiment_aligned and btc_aligned:
                lines.append("Both technical and fundamental analysis support the signal.")
            elif not sentiment_aligned or not btc_aligned:
                lines.append("Mixed signals detected - exercise caution.")
            
            # Sentiment details
            if 'sentiment' in fundamental_data:
                sent = fundamental_data['sentiment']
                lines.append(f"News sentiment {sent['label'].lower()}, providing {'support' if sentiment_aligned else 'conflicting signal'}.")
            
            # BTC correlation warning
            if 'btc_correlation' in fundamental_data:
                btc = fundamental_data['btc_correlation']
                if abs(btc['correlation']) > 0.8 and not btc['aligned']:
                    lines.append(f"⚠️ WARNING: Strong BTC divergence detected! "
                               f"BTC {btc['btc_trend']} vs {btc['symbol_trend']}.")
            
            # Technical notes
            if technical_confidence >= 75:
                lines.append(f"High technical confidence ({technical_confidence:.0f}%) reinforces the signal.")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error generating recommendation: {e}")
            return "Analysis complete. Review all data before trading."


def format_fundamental_section(
    fundamental_data: Dict,
    combined_analysis: Dict,
    recommendation: str
) -> str:
    """
    Format fundamental analysis section for Telegram message
    
    Args:
        fundamental_data: Dict with sentiment and/or btc_correlation
        combined_analysis: Dict with combined score and breakdown
        recommendation: Recommendation text from generate_recommendation
        
    Returns:
        Formatted HTML message section
    """
    if not fundamental_data:
        return ""
    
    try:
        lines = []
        
        # Section separator
        lines.append("\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("📰 <b>FUNDAMENTAL ANALYSIS:</b>\n")
        
        # Sentiment section
        if 'sentiment' in fundamental_data:
            sent = fundamental_data['sentiment']
            score = sent['score']
            label = sent['label']
            
            # Emoji based on sentiment
            emoji = "✅" if label == 'POSITIVE' else "❌" if label == 'NEGATIVE' else "⚪"
            
            lines.append(f"🌐 <b>Sentiment:</b> {label} ({score:.0f}/100) {emoji}")
            
            # Top news
            if sent.get('top_news'):
                lines.append("Top News:")
                for news in sent['top_news'][:3]:  # Max 3
                    title = news['title'][:60] + "..." if len(news['title']) > 60 else news['title']
                    impact = news.get('impact', 0)
                    impact_sign = "+" if impact > 0 else ""
                    # Parse time for relative display
                    lines.append(f" {emoji} \"{title}\"")
                    lines.append(f"    Impact: {impact_sign}{impact:.0f}")
        
        # BTC Correlation section
        if 'btc_correlation' in fundamental_data:
            btc = fundamental_data['btc_correlation']
            corr = btc['correlation']
            
            # Correlation strength
            if abs(corr) > 0.8:
                strength = "Strong"
            elif abs(corr) > 0.5:
                strength = "Moderate"
            else:
                strength = "Weak"
            
            aligned_emoji = "✅" if btc['aligned'] else "❌"
            
            lines.append(f"\n📊 <b>BTC Correlation:</b> {corr:.2f} ({strength})")
            lines.append(f"BTC: {btc['btc_trend']} ({btc['btc_change']:+.1f}%) | "
                        f"Symbol: {btc['symbol_trend']} ({btc['symbol_change']:+.1f}%)")
            lines.append(f"Trends aligned: {aligned_emoji} {'YES' if btc['aligned'] else 'NO'}")
        
        # Combined analysis section
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("🎲 <b>COMBINED ANALYSIS:</b>\n")
        
        tech = combined_analysis['technical_contribution']
        sent_contrib = combined_analysis['sentiment_contribution']
        btc_contrib = combined_analysis['btc_correlation_contribution']
        combined = combined_analysis['combined_score']
        
        # Determine bias from technical score
        tech_bias = "BULLISH" if tech >= 50 else "BEARISH"
        tech_emoji = "✅" if tech >= 60 else "⚪" if tech >= 40 else "❌"
        
        lines.append(f"Technical: {tech:.0f}% {tech_bias} {tech_emoji}")
        
        if 'sentiment' in fundamental_data:
            sent = fundamental_data['sentiment']
            sent_emoji = "✅" if sent['score'] >= 60 else "⚪" if sent['score'] >= 40 else "❌"
            lines.append(f"Fundamental: {sent['score']:.0f}% {sent['label']} {sent_emoji}")
        
        # Overall score assessment
        if combined >= 70:
            assessment = "STRONG CONDITIONS"
        elif combined >= 60:
            assessment = "FAVORABLE CONDITIONS"
        elif combined >= 50:
            assessment = "MODERATE CONDITIONS"
        else:
            assessment = "WEAK CONDITIONS"
        
        lines.append(f"\n<b>OVERALL SCORE: {combined:.0f}% - {assessment}</b>")
        
        # Recommendation section
        lines.append("\n💡 <b>RECOMMENDATION:</b>")
        lines.append(recommendation)
        
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error formatting fundamental section: {e}")
        return ""
