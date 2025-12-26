"""
BTC Correlation Analyzer
Calculates correlation between symbol and BTC for divergence detection
"""

import logging
from typing import Dict, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class BTCCorrelator:
    """Calculates correlation between trading symbol and BTC"""
    
    def __init__(self, window: int = 30):
        """
        Initialize correlator
        
        Args:
            window: Rolling window for correlation calculation (default: 30 candles)
        """
        self.window = window
    
    def calculate_correlation(
        self, 
        symbol: str,
        symbol_df: pd.DataFrame,
        btc_df: pd.DataFrame
    ) -> Optional[Dict]:
        """
        Calculate correlation between symbol and BTC
        
        Args:
            symbol: Trading symbol (e.g., 'ETHUSDT')
            symbol_df: DataFrame with symbol price data
            btc_df: DataFrame with BTC price data
            
        Returns:
            {
                'correlation': 0.92,  # Pearson correlation coefficient (-1 to 1)
                'btc_trend': 'BULLISH',  # BTC trend direction
                'symbol_trend': 'BULLISH',  # Symbol trend direction
                'aligned': True,  # Whether trends are aligned
                'impact': +10,  # Confidence adjustment (-15 to +10)
                'btc_change': +2.5,  # BTC % change (recent)
                'symbol_change': +2.3  # Symbol % change (recent)
            }
        """
        # Skip for BTC itself
        if 'BTC' in symbol.upper():
            logger.info("Skipping BTC correlation for BTC symbol")
            return None
        
        try:
            # Ensure dataframes have same length
            min_len = min(len(symbol_df), len(btc_df))
            if min_len < self.window:
                logger.warning(f"Insufficient data for correlation (need {self.window}, have {min_len})")
                return None
            
            # Align dataframes
            symbol_df = symbol_df.tail(min_len)
            btc_df = btc_df.tail(min_len)
            
            # Calculate returns
            symbol_returns = symbol_df['close'].pct_change().dropna()
            btc_returns = btc_df['close'].pct_change().dropna()
            
            # Calculate correlation (last N candles)
            correlation = symbol_returns.tail(self.window).corr(btc_returns.tail(self.window))
            
            # Calculate recent trends (last 10 candles)
            btc_change = ((btc_df['close'].iloc[-1] / btc_df['close'].iloc[-10]) - 1) * 100
            symbol_change = ((symbol_df['close'].iloc[-1] / symbol_df['close'].iloc[-10]) - 1) * 100
            
            # Determine trends
            btc_trend = 'BULLISH' if btc_change > 0 else 'BEARISH'
            symbol_trend = 'BULLISH' if symbol_change > 0 else 'BEARISH'
            
            # Check alignment
            aligned = (btc_trend == symbol_trend)
            
            # Calculate confidence impact
            impact = self._calculate_impact(correlation, aligned)
            
            result = {
                'correlation': round(correlation, 3),
                'btc_trend': btc_trend,
                'symbol_trend': symbol_trend,
                'aligned': aligned,
                'impact': impact,
                'btc_change': round(btc_change, 2),
                'symbol_change': round(symbol_change, 2)
            }
            
            logger.info(f"BTC correlation calculated: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Error calculating BTC correlation: {e}")
            return None
    
    def _calculate_impact(self, correlation: float, aligned: bool) -> int:
        """
        Calculate confidence impact based on correlation and alignment
        
        Args:
            correlation: Pearson correlation coefficient
            aligned: Whether BTC and symbol trends are aligned
            
        Returns:
            Confidence adjustment (-15 to +10)
        """
        # Strong correlation (abs > 0.8)
        if abs(correlation) > 0.8:
            if aligned:
                return +10  # Strong positive signal
            else:
                return -15  # CRITICAL WARNING - divergence!
        
        # Moderate correlation (0.5 - 0.8)
        elif abs(correlation) > 0.5:
            if aligned:
                return +5  # Moderate positive signal
            else:
                return -8  # Warning signal
        
        # Weak correlation (< 0.5)
        else:
            return 0  # No significant impact
