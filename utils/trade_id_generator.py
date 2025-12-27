"""
Trade ID Generator for Multi-Stage Alerts
Generates unique, human-readable trade identifiers

Format: #{SYMBOL}-{YYYYMMDD}-{HHMMSS}
Example: #BTC-20251227-143022
"""

from datetime import datetime, timezone


class TradeIDGenerator:
    """
    Generates unique trade IDs for position tracking
    """
    
    @staticmethod
    def generate(symbol: str, timeframe: str = None) -> str:
        """
        Generate unique trade ID
        
        Args:
            symbol: Trading symbol (e.g., BTCUSDT, ETHUSDT)
            timeframe: Optional timeframe (e.g., 4h, 1d) - not used in ID but kept for API consistency
            
        Returns:
            Trade ID in format: #SYMBOL-YYYYMMDD-HHMMSS
            Example: #BTC-20251227-143022
        """
        # Clean symbol (remove USDT, BUSD, etc.)
        clean_symbol = (
            symbol
            .replace('USDT', '')
            .replace('BUSD', '')
            .replace('USDC', '')
            .replace('USD', '')
            .replace('BTC', '')  # Remove BTC pairs like ETHBTC -> ETH
            .upper()
        )
        
        # If symbol is BTC itself, keep it
        if symbol.upper().startswith('BTC'):
            clean_symbol = 'BTC'
        
        # Get current timestamp in UTC
        now = datetime.now(timezone.utc)
        date_str = now.strftime('%Y%m%d')
        time_str = now.strftime('%H%M%S')
        
        # Build trade ID
        trade_id = f"#{clean_symbol}-{date_str}-{time_str}"
        
        return trade_id
    
    @staticmethod
    def parse(trade_id: str) -> dict:
        """
        Parse trade ID to extract components
        
        Args:
            trade_id: Trade ID (e.g., #BTC-20251227-143022)
            
        Returns:
            Dictionary with:
                - symbol: Extracted symbol
                - date: Date string (YYYYMMDD)
                - time: Time string (HHMMSS)
                - datetime: Parsed datetime object
        """
        try:
            # Remove # prefix
            id_str = trade_id.lstrip('#')
            
            # Split by dash
            parts = id_str.split('-')
            
            if len(parts) != 3:
                raise ValueError(f"Invalid trade ID format: {trade_id}")
            
            symbol, date_str, time_str = parts
            
            # Parse datetime
            dt_str = f"{date_str}{time_str}"
            dt = datetime.strptime(dt_str, '%Y%m%d%H%M%S')
            dt = dt.replace(tzinfo=timezone.utc)
            
            return {
                'symbol': symbol,
                'date': date_str,
                'time': time_str,
                'datetime': dt
            }
            
        except Exception as e:
            raise ValueError(f"Failed to parse trade ID '{trade_id}': {e}")
