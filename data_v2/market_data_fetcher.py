"""
📥 MARKET DATA FETCHER V2
OHLCV market data retrieval for the V2 pipeline.

Fetches candlestick data from exchanges via ccxt (if available)
or falls back to Binance REST API directly.

Author: galinborisov10-art
Version: 2.0
"""

import logging
import time
from typing import Optional, Dict, Any

import pandas as pd

logger = logging.getLogger(__name__)

_BINANCE_BASE = "https://api.binance.com"
_CCXT_AVAILABLE = False
try:
    import ccxt  # type: ignore
    _CCXT_AVAILABLE = True
except ImportError:
    pass

# Timeframe to Binance interval mapping
_TF_MAP = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1H": "1h",
    "2H": "2h",
    "4H": "4h",
    "6H": "6h",
    "8H": "8h",
    "12H": "12h",
    "1D": "1d",
    "3D": "3d",
    "1W": "1w",
}


class MarketDataFetcherV2:
    """
    V2 Market Data Fetcher

    Provides OHLCV DataFrames for a symbol/timeframe pair.
    Prefers ccxt if available; falls back to direct Binance REST API.

    Args:
        exchange_id: ccxt exchange id (default 'binance')
        timeout_ms: Request timeout in milliseconds (default 10000)
        max_retries: Number of retry attempts on failure (default 3)
    """

    def __init__(
        self,
        exchange_id: str = "binance",
        timeout_ms: int = 10_000,
        max_retries: int = 3,
    ):
        self.exchange_id = exchange_id
        self.timeout_ms = timeout_ms
        self.max_retries = max_retries
        self._exchange = None

        if _CCXT_AVAILABLE:
            try:
                self._exchange = getattr(ccxt, exchange_id)(
                    {"timeout": timeout_ms, "enableRateLimit": True}
                )
                logger.info(f"MarketDataFetcherV2: using ccxt/{exchange_id}")
            except Exception as e:
                logger.warning(f"MarketDataFetcherV2: ccxt init failed ({e}), using REST")
        else:
            logger.info("MarketDataFetcherV2: ccxt not available, using Binance REST")

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1H",
        limit: int = 300,
    ) -> Optional[pd.DataFrame]:
        """
        Fetch OHLCV candles for a symbol/timeframe.

        Args:
            symbol: Trading pair (e.g. 'BTC/USDT' or 'BTCUSDT')
            timeframe: Chart timeframe (e.g. '1H', '4H', '1D')
            limit: Number of candles to fetch (default 300)

        Returns:
            DataFrame with columns [open, high, low, close, volume]
            indexed by datetime, or None on failure.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                if self._exchange and _CCXT_AVAILABLE:
                    df = self._fetch_ccxt(symbol, timeframe, limit)
                else:
                    df = self._fetch_rest(symbol, timeframe, limit)

                if df is not None and len(df) > 0:
                    logger.debug(
                        f"MarketDataFetcherV2: fetched {len(df)} candles "
                        f"for {symbol} {timeframe}"
                    )
                    return df
            except Exception as e:
                logger.warning(
                    f"MarketDataFetcherV2: attempt {attempt}/{self.max_retries} "
                    f"failed for {symbol} {timeframe}: {e}"
                )
                if attempt < self.max_retries:
                    time.sleep(1.0 * attempt)

        logger.error(
            f"MarketDataFetcherV2: all {self.max_retries} attempts failed "
            f"for {symbol} {timeframe}"
        )
        return None

    def _fetch_ccxt(
        self, symbol: str, timeframe: str, limit: int
    ) -> Optional[pd.DataFrame]:
        """Fetch via ccxt"""
        raw = self._exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
        if not raw:
            return None
        df = pd.DataFrame(
            raw, columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        return df

    def _fetch_rest(
        self, symbol: str, timeframe: str, limit: int
    ) -> Optional[pd.DataFrame]:
        """Fetch via Binance REST API"""
        import requests  # imported here to avoid top-level dependency

        # Normalise symbol
        binance_symbol = symbol.replace("/", "")
        interval = _TF_MAP.get(timeframe, "1h")
        url = (
            f"{_BINANCE_BASE}/api/v3/klines"
            f"?symbol={binance_symbol}&interval={interval}&limit={limit}"
        )
        resp = requests.get(url, timeout=self.timeout_ms / 1000)
        resp.raise_for_status()
        raw = resp.json()

        if not raw:
            return None

        df = pd.DataFrame(
            raw,
            columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "close_time", "quote_volume", "trades",
                "taker_buy_base", "taker_buy_quote", "ignore",
            ],
        )
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df.set_index("timestamp", inplace=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col])
        return df[["open", "high", "low", "close", "volume"]]
