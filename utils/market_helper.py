"""
Market Helper Module
Provides market context analysis and formatting for the /market command
"""

import logging
import sys
import os
from typing import Dict, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.market_data_fetcher import MarketDataFetcher
from utils.news_cache import NewsCache

logger = logging.getLogger(__name__)


class MarketHelper:
    """
    Helper class for market fundamental analysis and formatting
    """
    
    def __init__(self):
        """Initialize market helper with data fetchers"""
        self.data_fetcher = MarketDataFetcher(cache_ttl=15)
        self.news_cache = NewsCache(cache_dir='cache', ttl_minutes=60)
        
        # Try to import sentiment analyzer (optional)
        try:
            from fundamental.sentiment_analyzer import SentimentAnalyzer
            self.sentiment_analyzer = SentimentAnalyzer(cache_ttl=3600)
            self.sentiment_available = True
        except ImportError:
            logger.warning("SentimentAnalyzer not available")
            self.sentiment_analyzer = None
            self.sentiment_available = False
        
        logger.info("MarketHelper initialized")
    
    def is_enabled(self) -> bool:
        """
        Check if market fundamental analysis is enabled via feature flags
        
        Returns:
            True if enabled, False otherwise
        """
        try:
            from config.config_loader import load_feature_flags
            
            flags = load_feature_flags()
            fundamental = flags.get('fundamental_analysis', {})
            
            # Check required flags
            enabled = all([
                fundamental.get('enabled', False),
                fundamental.get('market_integration', False)
            ])
            
            logger.debug(f"Market integration enabled: {enabled}")
            return enabled
            
        except Exception as e:
            logger.warning(f"Error checking feature flags: {e}")
            return False
    
    def get_market_fundamentals(self, symbol: str) -> Optional[Dict]:
        """
        Get comprehensive market fundamentals
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            
        Returns:
            {
                'sentiment': {...},
                'fear_greed': {...},
                'btc_dominance': 48.5,
                'market_cap': {...}
            }
            Returns None if analysis fails or is disabled
        """
        if not self.is_enabled():
            logger.debug("Market fundamental analysis disabled")
            return None
        
        try:
            result = {}
            
            # Get news sentiment if available
            if self.sentiment_available and self.sentiment_analyzer:
                news = self.news_cache.get_cached_news(symbol)
                if news:
                    sentiment = self.sentiment_analyzer.analyze_news(news)
                    if sentiment:
                        result['sentiment'] = sentiment
                        logger.debug(f"Sentiment analysis added: {sentiment['label']}")
            
            # Get Fear & Greed Index
            fear_greed = self.data_fetcher.get_fear_greed_index()
            if fear_greed:
                result['fear_greed'] = fear_greed
                logger.debug(f"Fear & Greed added: {fear_greed['value']}")
            
            # Get market overview
            market_data = self.data_fetcher.get_market_overview()
            if market_data:
                result['btc_dominance'] = market_data.get('btc_dominance', 0)
                result['market_cap'] = market_data.get('market_cap', 0)
                result['market_cap_change'] = market_data.get('market_cap_change_24h', 0)
                result['total_volume'] = market_data.get('total_volume_24h', 0)
                logger.debug(f"Market overview added: BTC dom={result['btc_dominance']:.1f}%")
            
            if not result:
                logger.warning("No market fundamental data available")
                return None
            
            logger.info(f"Market fundamentals retrieved: {list(result.keys())}")
            return result
            
        except Exception as e:
            logger.error(f"Error getting market fundamentals: {e}")
            return None
    
    def generate_market_context(
        self,
        fundamentals: Dict,
        price_change_24h: float,
        volume_24h: float
    ) -> str:
        """
        Generate intelligent market context analysis
        
        Args:
            fundamentals: Market fundamental data
            price_change_24h: 24h price change %
            volume_24h: 24h trading volume
            
        Returns:
            Multi-line context text
        """
        try:
            lines = []
            
            # Price action assessment
            if price_change_24h > 2:
                lines.append("✅ Силен купувачески натиск в пазара.")
            elif price_change_24h > 0:
                lines.append("✅ Умерен купувачески натиск.")
            elif price_change_24h > -2:
                lines.append("⚠️ Умерен продавачески натиск.")
            else:
                lines.append("❌ Силен продавачески натиск в пазара.")
            
            # Sentiment context
            if 'sentiment' in fundamentals:
                sent = fundamentals['sentiment']
                top_news_count = len(sent.get('top_news', []))
                if top_news_count > 0:
                    lines.append(f"Позитивен новинарски sentiment с {top_news_count} важни статии.")
            
            # Fear & Greed context
            if 'fear_greed' in fundamentals:
                fg = fundamentals['fear_greed']
                label = fg['label']
                value = fg['value']
                
                if value >= 75:
                    lines.append(f"Fear & Greed в зона \"{label}\" - потенциално препродадени условия.")
                elif value >= 55:
                    lines.append(f"Fear & Greed в зона \"{label}\" - бичи условия.")
                elif value >= 45:
                    lines.append(f"Fear & Greed в зона \"{label}\" - балансиран пазар.")
                elif value >= 25:
                    lines.append(f"Fear & Greed в зона \"{label}\" - мечи sentiment.")
                else:
                    lines.append(f"Fear & Greed в зона \"{label}\" - потенциална възможност за покупка.")
            
            # BTC Dominance context
            if 'btc_dominance' in fundamentals:
                dom = fundamentals['btc_dominance']
                if dom > 50:
                    lines.append(f"BTC доминация висока на {dom:.1f}% - BTC води пазара.")
                elif dom > 45:
                    lines.append(f"BTC доминация стабилна на {dom:.1f}% - здравословно участие на altcoins.")
                else:
                    lines.append(f"BTC доминация ниска на {dom:.1f}% - altseason условия.")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"Error generating market context: {e}")
            return "Пазарен анализ завършен."


def format_market_fundamental_section(
    fundamentals: Dict,
    market_context: str
) -> str:
    """
    Format market fundamentals for Telegram message
    
    Args:
        fundamentals: Market fundamental data
        market_context: Generated market context text
        
    Returns:
        Formatted HTML message section
    """
    if not fundamentals:
        return ""
    
    try:
        lines = []
        
        # Section separator
        lines.append("\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("📰 <b>MARKET SENTIMENT & FUNDAMENTALS:</b>\n")
        
        # Overall sentiment
        if 'sentiment' in fundamentals:
            sent = fundamentals['sentiment']
            score = sent['score']
            label = sent['label']
            emoji = "✅" if label == 'POSITIVE' else "⚪" if label == 'NEUTRAL' else "❌"
            
            lines.append(f"🌐 <b>Overall Sentiment:</b> {label} ({score:.0f}/100) {emoji}")
        
        # Fear & Greed
        if 'fear_greed' in fundamentals:
            fg = fundamentals['fear_greed']
            value = fg['value']
            label = fg['label']
            
            # Color emoji based on value
            if value >= 75:
                emoji = "🔴"  # Extreme Greed
            elif value >= 55:
                emoji = "🟢"  # Greed
            elif value >= 45:
                emoji = "🟡"  # Neutral
            elif value >= 25:
                emoji = "🟠"  # Fear
            else:
                emoji = "🔴"  # Extreme Fear
            
            lines.append(f"📊 <b>Fear & Greed Index:</b> {value} ({label}) {emoji}")
            
            # Add timestamp if available
            if 'timestamp' in fg:
                from datetime import datetime
                try:
                    ts = int(fg['timestamp'])
                    now = int(datetime.now().timestamp())
                    minutes_ago = (now - ts) // 60
                    
                    if minutes_ago < 1:
                        time_str = "току-що"
                    elif minutes_ago < 60:
                        time_str = f"преди {minutes_ago} мин"
                    else:
                        hours_ago = minutes_ago // 60
                        time_str = f"преди {hours_ago} ч"
                    
                    lines.append(f"   <i>Обновено: {time_str}</i>")
                except:
                    pass
        
        # BTC Dominance
        if 'btc_dominance' in fundamentals:
            dom = fundamentals['btc_dominance']
            lines.append(f"💹 <b>BTC Dominance:</b> {dom:.1f}% (stable)")
        
        # Market Cap with 24h change
        if 'market_cap' in fundamentals:
            mcap = fundamentals['market_cap']
            mcap_t = mcap / 1_000_000_000_000  # Convert to trillions
            
            # Get market cap change
            mcap_change = fundamentals.get('market_cap_change', 0)
            mcap_emoji = "📈" if mcap_change > 0 else "📉" if mcap_change < 0 else "➡️"
            
            if mcap_change != 0:
                lines.append(f"💰 <b>Total Market Cap:</b> ${mcap_t:.2f}T ({mcap_change:+.1f}% 24h) {mcap_emoji}")
            else:
                lines.append(f"💰 <b>Total Market Cap:</b> ${mcap_t:.2f}T")
        
        # Total Volume with 24h change
        if 'total_volume' in fundamentals:
            volume = fundamentals['total_volume']
            volume_b = volume / 1_000_000_000  # Convert to billions
            
            # Calculate volume change (if available)
            # For now, we'll skip the change since we don't have historical volume
            lines.append(f"📊 <b>Total Volume 24h:</b> ${volume_b:.1f}B")
        
        # Top news
        if 'sentiment' in fundamentals and fundamentals['sentiment'].get('top_news'):
            lines.append("\n<b>Top Market News (Last 24h):</b>")
            for news in fundamentals['sentiment']['top_news'][:2]:
                title = news['title'][:60] + "..." if len(news['title']) > 60 else news['title']
                impact = news.get('impact', 0)
                emoji = "✅" if impact > 0 else "❌"
                lines.append(f" {emoji} \"{title}\" ({impact:+.0f} impact)")
        
        # Market context
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n")
        lines.append("💡 <b>MARKET CONTEXT:</b>\n")
        lines.append(market_context)
        
        lines.append("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        return "\n".join(lines)
        
    except Exception as e:
        logger.error(f"Error formatting market fundamental section: {e}")
        return ""
