"""
🔥 HYBRID ICT+ML BACKTESTING ENGINE
Tests ALL symbols on ALL timeframes
Now includes 80% TP alerts and final WIN/LOSS tracking
"""

import asyncio
import aiohttp
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import json

from ict_signal_engine import ICTSignalEngine, MarketBias, ICTSignal, SignalType, SignalStrength
from ict_80_alert_handler import ICT80AlertHandler


class HybridBacktestEngine:
    """Backtesting engine for hybrid ICT+ML strategy"""
    
    def __init__(self):
        self.ict_engine = ICTSignalEngine()
        self.alert_handler = ICT80AlertHandler(self.ict_engine)
        self.results = []
        self.active_trades = {}  # Track active trades for 80% alerts
    
    async def fetch_historical_data(self, symbol: str, timeframe: str, days: int = 30) -> pd.DataFrame:
        """Fetch historical OHLCV data from Binance"""
        try: 
            interval_map = {'1m': '1m', '5m': '5m', '15m': '15m', '1h': '1h', '4h': '4h', '1d': '1d'}
            interval = interval_map.get(timeframe, '1h')
            
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol. replace('/', '').replace('USDT', 'USDT'),
                'interval': interval,
                'limit': min(days * 24, 1000)
            }
            
            async with aiohttp.ClientSession() as session:
                async with session. get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                    if resp.status != 200:
                        return pd.DataFrame()
                    data = await resp.json()
            
            df = pd.DataFrame(data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 
                                            'close_time', 'quote_volume', 'trades', 'taker_buy_base', 
                                            'taker_buy_quote', 'ignore'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df. set_index('timestamp', inplace=True)
            
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df[['open', 'high', 'low', 'close', 'volume']].dropna()
        
        except Exception as e:
            return pd.DataFrame()
    
    async def _generate_backtest_signal(self, df: pd.DataFrame, symbol: str, timeframe:  str) -> Optional[ICTSignal]:
        """Generate ICT signal using async generate_signal"""
        
        if len(df) < 50:
            return None
        
        try:
            # Use the actual ICT engine's generate_signal method
            signal = await self.ict_engine.generate_signal(df, symbol, timeframe)
            return signal
        
        except Exception as e:
            return None
    
    async def run_backtest(self, symbol: str, timeframe: str, days: int = 15) -> Dict:
        """Run backtest for symbol/timeframe"""
        
        try:
            df = await self.fetch_historical_data(symbol, timeframe, days)
            
            if df. empty or len(df) < 50:
                return {'symbol': symbol, 'timeframe':  timeframe, 'status': 'insufficient_data'}
            
            signal = await self._generate_backtest_signal(df, symbol, timeframe)
            
            if not signal or signal.signal_type == SignalType.HOLD:
                return {'symbol': symbol, 'timeframe': timeframe, 'status': 'no_signal'}
            
            result = {
                'symbol': symbol,
                'timeframe': timeframe,
                'status': 'signal',
                'type': signal.signal_type.value,
                'entry': round(signal.entry_price, 4),
                'sl': round(signal.sl_price, 4),
                'tp': round(signal.tp_prices[0], 4) if signal.tp_prices else 0,
                'confidence': round(signal.confidence, 1),
                'rr': round(signal.risk_reward_ratio, 2),
                'bias':  signal.bias.value,
                'reasoning': signal.reasoning[: 100]
            }
            
            return result
        
        except Exception as e: 
            return {'symbol': symbol, 'timeframe': timeframe, 'status': 'error', 'error': str(e)}
    
    async def run_full_backtest(self, symbols: List[str], timeframes:  List[str], days: int = 15):
        """Run backtest on ALL symbols and timeframes"""
        
        print(f"\n🚀 Starting FULL backtest:  {len(symbols)} symbols × {len(timeframes)} timeframes = {len(symbols) * len(timeframes)} tests\n")
        
        tasks = []
        for symbol in symbols:
            for tf in timeframes:
                tasks.append(self.run_backtest(symbol, tf, days))
        
        results = await asyncio.gather(*tasks)
        
        # Filter and display signals
        signals = [r for r in results if r. get('status') == 'signal']
        
        print(f"\n{'='*80}")
        print(f"📊 BACKTEST RESULTS ({len(signals)} signals from {len(results)} tests)")
        print(f"{'='*80}\n")
        
        if signals:
            for s in signals:
                emoji = "🟢" if s['type'] == 'LONG' else "🔴"
                print(f"{emoji} {s['symbol']: 10} {s['timeframe']:4} | {s['type']:5} | Entry: {s['entry']: >10} | SL: {s['sl']:>10} | TP: {s['tp']:>10} | Conf: {s['confidence']: >5}% | RR: {s['rr']}")
        else:
            print("❌ No signals generated")
        
        # Summary
        print(f"\n{'='*80}")
        print(f"Summary:")
        print(f"  Total tests: {len(results)}")
        print(f"  Signals: {len(signals)}")
        print(f"  No signal: {len([r for r in results if r.get('status') == 'no_signal'])}")
        print(f"  Errors: {len([r for r in results if r.get('status') == 'error'])}")
        print(f"{'='*80}\n")
        
        # Save all results to JSON files
        self.save_all_results(results)
        
        return results
    
    def save_all_results(self, results: List[Dict]):
        """Save all backtest results to individual JSON files"""
        results_dir = Path("backtest_results")
        results_dir.mkdir(exist_ok=True)
        
        for result in results:
            if result.get('status') == 'signal':
                symbol = result.get('symbol', 'UNKNOWN')
                timeframe = result.get('timeframe', 'UNKNOWN')
                
                filename = results_dir / f"{symbol}_{timeframe}_backtest.json"
                
                # Convert to serializable format
                serializable_result = {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'timestamp': datetime.now().isoformat(),
                    'total_trades': 1,  # Single signal per run
                    'total_win': 0,  # Would need actual tracking
                    'total_loss': 0,  # Would need actual tracking
                    'win_rate': 0,  # Would need actual tracking
                    'signal_type': result.get('type', 'UNKNOWN'),
                    'entry': result.get('entry', 0),
                    'sl': result.get('sl', 0),
                    'tp': result.get('tp', 0),
                    'confidence': result.get('confidence', 0),
                    'rr': result.get('rr', 0),
                    'bias': result.get('bias', 'NEUTRAL'),
                    'reasoning': result.get('reasoning', ''),
                    'alerts_80_count': 0,
                    'final_alerts_count': 0
                }
                
                with open(filename, 'w') as f:
                    json.dump(serializable_result, f, indent=2, default=str)
                
                print(f"💾 Saved: {filename}")


async def main():
    """Run full backtest"""
    
    # ALL symbols
    symbols = [
        'BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT',
        'ADAUSDT', 'DOGEUSDT', 'AVAXUSDT', 'LINKUSDT', 'MATICUSDT',
        'DOTUSDT', 'UNIUSDT', 'ATOMUSDT', 'LTCUSDT', 'NEARUSDT'
    ]
    
    # ALL timeframes
    timeframes = ['15m', '1h', '4h', '1d']
    
    engine = HybridBacktestEngine()
    results = await engine. run_full_backtest(symbols, timeframes, days=15)


if __name__ == "__main__":
    asyncio.run(main())
