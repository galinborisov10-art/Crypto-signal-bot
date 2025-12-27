"""
Market Data Fetcher Module
Fetches market data from external APIs (Fear & Greed Index, BTC dominance, market cap)
"""

import json
import logging
import requests
from typing import Dict, Optional
from datetime import datetime
from utils.news_cache import NewsCache

logger = logging.getLogger(__name__)

# API Endpoints (Free, no API key required)
FEAR_GREED_API = "https://api.alternative.me/fng/"
COINGECKO_GLOBAL = "https://api.coingecko.com/api/v3/global"


class MarketDataFetcher:
    """
    Fetches market data from external APIs with caching
    """
    
    def __init__(self, cache_ttl: int = 15):
        """
        Initialize market data fetcher
        
        Args:
            cache_ttl: Cache time-to-live in minutes (default: 15)
        """
        self.cache = NewsCache(cache_dir='cache/market', ttl_minutes=cache_ttl)
        self.cache_ttl = cache_ttl
        logger.info(f"MarketDataFetcher initialized with {cache_ttl}min cache TTL")
    
    def get_fear_greed_index(self) -> Optional[Dict]:
        """
        Fetch Fear & Greed Index (0-100)
        
        Returns:
            {
                'value': 65,
                'label': 'Greed',  # Extreme Fear, Fear, Neutral, Greed, Extreme Greed
                'timestamp': '...'
            }
            Returns None on error
        """
        try:
            # Check cache first
            cached = self.cache.get_cached_news('fear_greed')
            if cached:
                logger.debug("Fear & Greed Index retrieved from cache")
                return cached
            
            # Fetch from API
            logger.info("Fetching Fear & Greed Index from Alternative.me API")
            response = requests.get(FEAR_GREED_API, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'data' not in data or not data['data']:
                logger.warning("Invalid Fear & Greed API response format")
                return None
            
            api_data = data['data'][0]
            
            result = {
                'value': int(api_data['value']),
                'label': api_data['value_classification'],
                'timestamp': api_data.get('timestamp', str(int(datetime.now().timestamp())))
            }
            
            # Cache result
            self.cache.set_cached_news('fear_greed', result)
            logger.info(f"Fear & Greed Index: {result['value']} ({result['label']})")
            
            return result
            
        except requests.exceptions.Timeout:
            logger.warning("Fear & Greed API timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"Fear & Greed API request failed: {e}")
            return None
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"Error parsing Fear & Greed API response: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Fear & Greed Index: {e}")
            return None
    
    def get_market_overview(self) -> Optional[Dict]:
        """
        Fetch global market data (BTC dominance, market cap)
        
        Returns:
            {
                'btc_dominance': 48.5,
                'market_cap': 1850000000000,
                'market_cap_change_24h': +2.3,
                'total_volume_24h': 95000000000
            }
            Returns None on error
        """
        try:
            # Check cache first
            cached = self.cache.get_cached_news('market_overview')
            if cached:
                logger.debug("Market overview retrieved from cache")
                return cached
            
            # Fetch from CoinGecko API
            logger.info("Fetching market overview from CoinGecko API")
            response = requests.get(COINGECKO_GLOBAL, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if 'data' not in data:
                logger.warning("Invalid CoinGecko API response format")
                return None
            
            global_data = data['data']
            
            # Extract market data
            market_cap_percentage = global_data.get('market_cap_percentage', {})
            total_market_cap = global_data.get('total_market_cap', {})
            total_volume = global_data.get('total_volume', {})
            market_cap_change = global_data.get('market_cap_change_percentage_24h_usd', 0)
            
            result = {
                'btc_dominance': market_cap_percentage.get('btc', 0.0),
                'market_cap': total_market_cap.get('usd', 0),
                'market_cap_change_24h': market_cap_change,
                'total_volume_24h': total_volume.get('usd', 0)
            }
            
            # Cache result
            self.cache.set_cached_news('market_overview', result)
            logger.info(f"Market overview: BTC dominance={result['btc_dominance']:.1f}%, "
                       f"Market cap=${result['market_cap']/1e12:.2f}T")
            
            return result
            
        except requests.exceptions.Timeout:
            logger.warning("CoinGecko API timeout")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"CoinGecko API request failed: {e}")
            return None
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing CoinGecko API response: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching market overview: {e}")
            return None
