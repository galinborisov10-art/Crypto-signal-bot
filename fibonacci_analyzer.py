"""
🎯 FIBONACCI ANALYZER
Provides Fibonacci retracement and extension analysis for ICT signal optimization

Features:
- Retracement levels: 0.236, 0.382, 0.5, 0.618, 0.786
- Extension levels: 1.272, 1.414, 1.618, 2.0, 2.618
- OTE (Optimal Trade Entry) zone: 0.62-0.79
- Automatic swing point detection
- TP alignment with Fibonacci targets

Author: galinborisov10-art
Date: 2025-12-19
"""

import pandas as pd
import numpy as np
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class FibonacciLevel:
    """Represents a single Fibonacci level"""
    level: float  # 0.236, 0.382, etc.
    price: float
    type: str  # 'retracement' or 'extension'
    description: str
    
    def to_dict(self) -> Dict:
        return {
            'level': self.level,
            'price': self.price,
            'type': self.type,
            'description': self.description
        }


class FibonacciAnalyzer:
    """
    Fibonacci Analysis for ICT Trading
    
    Calculates retracement and extension levels based on swing points.
    Identifies OTE zones for optimal entries.
    Provides TP targets aligned with Fibonacci levels.
    
    Args:
        retracement_levels: List of Fibonacci retracement levels (default: [0.236, 0.382, 0.5, 0.618, 0.786])
        extension_levels: List of Fibonacci extension levels (default: [1.272, 1.414, 1.618, 2.0, 2.618])
        ote_range: Tuple defining OTE zone range (default: (0.62, 0.79))
        
    Example:
        >>> analyzer = FibonacciAnalyzer()
        >>> result = analyzer.analyze(df, bias='BULLISH', lookback=50)
        >>> print(f"In OTE Zone: {result['in_ote_zone']}")
    """
    
    def __init__(
        self,
        retracement_levels: Optional[List[float]] = None,
        extension_levels: Optional[List[float]] = None,
        ote_range: Tuple[float, float] = (0.62, 0.79)
    ):
        """
        Initialize Fibonacci Analyzer
        
        Args:
            retracement_levels: Custom retracement levels (default: standard Fib levels)
            extension_levels: Custom extension levels (default: standard Fib extensions)
            ote_range: OTE zone range (default: 0.62-0.79)
        """
        self.retracement_levels = retracement_levels or [0.236, 0.382, 0.5, 0.618, 0.786]
        self.extension_levels = extension_levels or [1.272, 1.414, 1.618, 2.0, 2.618]
        self.ote_range = ote_range
        
        logger.info(f"FibonacciAnalyzer initialized - Retracement: {self.retracement_levels}, "
                   f"Extension: {self.extension_levels}, OTE: {self.ote_range}")
    
    def analyze(
        self,
        df: pd.DataFrame,
        bias: str,
        lookback: int = 50
    ) -> Dict:
        """
        Perform complete Fibonacci analysis
        
        Args:
            df: OHLCV DataFrame
            bias: Market bias ('BULLISH' or 'BEARISH')
            lookback: Number of candles to analyze for swing points
            
        Returns:
            Dictionary with Fibonacci analysis results
        """
        try:
            # Ensure we have enough data
            if len(df) < lookback:
                logger.warning(f"Insufficient data for Fibonacci analysis: {len(df)} < {lookback}")
                return self._empty_analysis()
            
            # Find swing points
            swing_high, swing_low = self._find_swing_points(df, lookback)
            
            if not swing_high or not swing_low:
                logger.warning("No valid swing points found")
                return self._empty_analysis()
            
            # Calculate retracements
            retracements = self._calculate_retracement(
                swing_high['price'],
                swing_low['price'],
                bias
            )
            
            # Calculate extensions
            extensions = self._calculate_extensions(
                swing_high['price'],
                swing_low['price'],
                bias
            )
            
            # Calculate OTE zone
            ote_zone = self._calculate_ote_zone(
                swing_high['price'],
                swing_low['price'],
                bias
            )
            
            # Get current price
            current_price = df['close'].iloc[-1]
            
            # Find nearest levels
            all_levels = retracements + extensions
            nearest_level = self._find_nearest_level(current_price, all_levels)
            
            analysis = {
                'swing_high': swing_high,
                'swing_low': swing_low,
                'retracements': [level.to_dict() for level in retracements],
                'extensions': [level.to_dict() for level in extensions],
                'ote_zone': ote_zone,
                'nearest_level': nearest_level.to_dict() if nearest_level else None,
                'current_price': current_price,
                'in_ote_zone': self._is_price_in_ote(current_price, ote_zone)
            }
            
            logger.info(f"Fibonacci analysis complete - Swing H: {swing_high['price']:.2f}, "
                       f"L: {swing_low['price']:.2f}, In OTE: {analysis['in_ote_zone']}")
            
            return analysis
            
        except Exception as e:
            logger.error(f"Fibonacci analysis error: {e}")
            return self._empty_analysis()
    
    def _find_swing_points(
        self,
        df: pd.DataFrame,
        lookback: int
    ) -> Tuple[Optional[Dict], Optional[Dict]]:
        """
        Find swing high and swing low points
        
        Args:
            df: OHLCV DataFrame
            lookback: Number of candles to look back
            
        Returns:
            Tuple of (swing_high_dict, swing_low_dict)
        """
        try:
            # Use last N candles
            recent_df = df.tail(lookback)
            
            # Find swing high (highest high in period)
            swing_high_idx = recent_df['high'].idxmax()
            swing_high = {
                'price': recent_df.loc[swing_high_idx, 'high'],
                'index': swing_high_idx,
                'timestamp': recent_df.loc[swing_high_idx, 'timestamp'] if 'timestamp' in recent_df.columns else None
            }
            
            # Find swing low (lowest low in period)
            swing_low_idx = recent_df['low'].idxmin()
            swing_low = {
                'price': recent_df.loc[swing_low_idx, 'low'],
                'index': swing_low_idx,
                'timestamp': recent_df.loc[swing_low_idx, 'timestamp'] if 'timestamp' in recent_df.columns else None
            }
            
            logger.info(f"Swing points found - High: {swing_high['price']:.2f}, Low: {swing_low['price']:.2f}")
            
            return swing_high, swing_low
            
        except Exception as e:
            logger.error(f"Error finding swing points: {e}")
            return None, None
    
    def _calculate_retracement(
        self,
        swing_high: float,
        swing_low: float,
        bias: str
    ) -> List[FibonacciLevel]:
        """
        Calculate Fibonacci retracement levels
        
        Args:
            swing_high: Swing high price
            swing_low: Swing low price
            bias: Market bias
            
        Returns:
            List of FibonacciLevel objects
        """
        retracements = []
        swing_range = swing_high - swing_low
        
        for level in self.retracement_levels:
            if bias.upper() == 'BULLISH':
                # For bullish: measure from low to high, then retrace down
                price = swing_high - (swing_range * level)
                description = f"Bullish {level*100:.1f}% retracement"
            else:
                # For bearish: measure from high to low, then retrace up
                price = swing_low + (swing_range * level)
                description = f"Bearish {level*100:.1f}% retracement"
            
            retracements.append(FibonacciLevel(
                level=level,
                price=price,
                type='retracement',
                description=description
            ))
        
        return retracements
    
    def _calculate_extensions(
        self,
        swing_high: float,
        swing_low: float,
        bias: str
    ) -> List[FibonacciLevel]:
        """
        Calculate Fibonacci extension levels
        
        Args:
            swing_high: Swing high price
            swing_low: Swing low price
            bias: Market bias
            
        Returns:
            List of FibonacciLevel objects
        """
        extensions = []
        swing_range = swing_high - swing_low
        
        for level in self.extension_levels:
            if bias.upper() == 'BULLISH':
                # For bullish: extend above swing high
                price = swing_high + (swing_range * (level - 1.0))
                description = f"Bullish {level:.3f} extension"
            else:
                # For bearish: extend below swing low
                price = swing_low - (swing_range * (level - 1.0))
                description = f"Bearish {level:.3f} extension"
            
            extensions.append(FibonacciLevel(
                level=level,
                price=price,
                type='extension',
                description=description
            ))
        
        return extensions
    
    def _calculate_ote_zone(
        self,
        swing_high: float,
        swing_low: float,
        bias: str
    ) -> Dict:
        """
        Calculate Optimal Trade Entry (OTE) zone
        
        The OTE zone is between 0.62 and 0.79 Fibonacci retracement levels.
        This is considered the optimal entry zone in ICT methodology.
        
        Args:
            swing_high: Swing high price
            swing_low: Swing low price
            bias: Market bias
            
        Returns:
            Dictionary with OTE zone details
        """
        swing_range = swing_high - swing_low
        ote_low, ote_high = self.ote_range
        
        if bias.upper() == 'BULLISH':
            # For bullish: OTE zone is below swing high
            upper = swing_high - (swing_range * ote_low)  # 0.62 level
            lower = swing_high - (swing_range * ote_high)  # 0.79 level
        else:
            # For bearish: OTE zone is above swing low
            lower = swing_low + (swing_range * ote_low)  # 0.62 level
            upper = swing_low + (swing_range * ote_high)  # 0.79 level
        
        return {
            'upper': upper,
            'lower': lower,
            'range': abs(upper - lower),
            'midpoint': (upper + lower) / 2,
            'bias': bias,
            'description': f"OTE zone ({ote_low}-{ote_high})"
        }
    
    def _find_nearest_level(
        self,
        current_price: float,
        all_levels: List[FibonacciLevel]
    ) -> Optional[FibonacciLevel]:
        """
        Find the Fibonacci level nearest to current price
        
        Args:
            current_price: Current market price
            all_levels: List of all Fibonacci levels
            
        Returns:
            Nearest FibonacciLevel or None
        """
        if not all_levels:
            return None
        
        nearest = min(all_levels, key=lambda level: abs(level.price - current_price))
        return nearest
    
    def _is_price_in_ote(self, price: float, ote_zone: Dict) -> bool:
        """Check if price is within OTE zone"""
        return ote_zone['lower'] <= price <= ote_zone['upper']
    
    def _empty_analysis(self) -> Dict:
        """Return empty analysis structure"""
        return {
            'swing_high': None,
            'swing_low': None,
            'retracements': [],
            'extensions': [],
            'ote_zone': None,
            'nearest_level': None,
            'current_price': None,
            'in_ote_zone': False
        }
    
    def get_tp_targets_from_fibonacci(
        self,
        entry_price: float,
        bias: str,
        fibonacci_data: Dict
    ) -> List[float]:
        """
        Get TP targets aligned with Fibonacci levels
        
        Args:
            entry_price: Entry price for the trade
            bias: Market bias ('BULLISH' or 'BEARISH')
            fibonacci_data: Fibonacci analysis results
            
        Returns:
            List of TP target prices
        """
        tp_targets = []
        
        try:
            extensions = fibonacci_data.get('extensions', [])
            
            if not extensions:
                logger.warning("No Fibonacci extensions available for TP targets")
                return []
            
            # Select appropriate extension levels based on bias
            if bias.upper() == 'BULLISH':
                # For bullish: use extensions above entry
                for ext in extensions:
                    ext_price = ext.get('price') if isinstance(ext, dict) else ext.price
                    if ext_price > entry_price:
                        tp_targets.append(ext_price)
            else:
                # For bearish: use extensions below entry
                for ext in extensions:
                    ext_price = ext.get('price') if isinstance(ext, dict) else ext.price
                    if ext_price < entry_price:
                        tp_targets.append(ext_price)
            
            # Sort and take up to 3 targets
            tp_targets.sort(reverse=(bias.upper() == 'BEARISH'))
            
            logger.info(f"Generated {len(tp_targets)} Fibonacci TP targets")
            
            return tp_targets[:3]
            
        except Exception as e:
            logger.error(f"Error generating Fibonacci TP targets: {e}")
            return []
