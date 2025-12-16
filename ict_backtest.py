"""
🎯 ICT Strategy Backtest Engine
Tests optimized SL logic with structure awareness
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from typing import Dict, List
from ict_signal_engine import ICTSignalEngine, MarketBias

class ICTBacktestEngine: 
    def __init__(self):
        self. ict_engine = ICTSignalEngine()
        
    async def fetch_klines(self, symbol: str, timeframe: str, days: int = 30):
        """Fetch historical klines from Binance"""
        interval_minutes = {
            '1m': 1, '5m': 5, '15m':  15, '30m': 30,
            '1h':  60, '4h': 240, '1d': 1440
        }
        
        minutes = interval_minutes.get(timeframe, 5)
        limit = min(int((days * 24 * 60) / minutes), 1000)
        
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': timeframe,
            'limit': limit
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session. get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        df = pd.DataFrame(data, columns=[
                            'timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                            'taker_buy_quote', 'ignore'
                        ])
                        
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            df[col] = df[col].astype(float)
                        
                        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                        return df
                    else:
                        print(f"❌ Binance API error: {resp.status}")
                        return None
        except Exception as e:
            print(f"❌ Fetch error: {e}")
            return None
    
    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add ATR and other indicators"""
        # ATR
        df['tr1'] = df['high'] - df['low']
        df['tr2'] = abs(df['high'] - df['close'].shift(1))
        df['tr3'] = abs(df['low'] - df['close'].shift(1))
        df['tr'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)
        df['atr'] = df['tr'].rolling(14).mean()
        
        return df
    
    def simulate_trade(self, entry:  float, sl: float, tp_levels: List[float], 
                      future_df: pd.DataFrame, bias: MarketBias) -> Dict:
        """Simulate trade execution"""
        for idx, row in future_df.iterrows():
            high = row['high']
            low = row['low']
            
            if bias == MarketBias. BULLISH:
                # Check SL first
                if low <= sl: 
                    pnl_pct = ((sl - entry) / entry) * 100
                    return {'result': 'LOSS', 'pnl_pct': pnl_pct, 'exit_price': sl}
                
                # Check TPs
                for i, tp in enumerate(tp_levels):
                    if high >= tp:
                        pnl_pct = ((tp - entry) / entry) * 100
                        return {'result': f'TP{i+1}', 'pnl_pct':  pnl_pct, 'exit_price': tp}
            
            else:  # BEARISH
                if high >= sl:
                    pnl_pct = ((entry - sl) / entry) * 100
                    return {'result':  'LOSS', 'pnl_pct': pnl_pct, 'exit_price': sl}
                
                for i, tp in enumerate(tp_levels):
                    if low <= tp:
                        pnl_pct = ((entry - tp) / entry) * 100
                        return {'result':  f'TP{i+1}', 'pnl_pct': pnl_pct, 'exit_price':  tp}
        
        return {'result': 'TIMEOUT', 'pnl_pct': 0, 'exit_price': entry}
    
    async def run_backtest(self, symbol: str, timeframe: str, days: int = 30) -> Dict:
        """Run ICT backtest"""
        print(f"\n📊 ICT Backtest:  {symbol} {timeframe} ({days} days)")
        
        # Fetch data
        df = await self.fetch_klines(symbol, timeframe, days)
        if df is None or len(df) < 50:
            return {'error': 'Insufficient data'}
        
        df = self.add_indicators(df)
        
        trades = []
        lookback = 50
        lookahead = 20
        
        for i in range(lookback, len(df) - lookahead, 5):  # Every 5 candles
            past_df = df.iloc[: i+1]. copy()
            future_df = df.iloc[i+1:i+lookahead+1].copy()
            
            # Try to generate signal
            try:
                signal = self. ict_engine.generate_signal(past_df, symbol, timeframe)
                
                if signal and signal. entry_price: 
                    # Simulate trade
                    result = self.simulate_trade(
                        entry=signal.entry_price,
                        sl=signal.sl_price,
                        tp_levels=[signal.tp1_price, signal.tp2_price, signal.tp3_price],
                        future_df=future_df,
                        bias=signal.bias
                    )
                    
                    trades.append({
                        'timestamp': past_df.iloc[-1]['timestamp'],
                        'bias': signal.bias. value,
                        'entry':  signal.entry_price,
                        'sl': signal.sl_price,
                        'tp3': signal.tp3_price,
                        'result': result['result'],
                        'pnl_pct':  result['pnl_pct']
                    })
                    
            except Exception as e:
                continue
        
        # Calculate stats
        if not trades:
            return {'total_trades': 0, 'win_rate': 0, 'total_pnl': 0, 'avg_rr': 0}
        
        wins = [t for t in trades if 'TP' in t['result']]
        losses = [t for t in trades if t['result'] == 'LOSS']
        
        win_rate = (len(wins) / len(trades)) * 100 if trades else 0
        total_pnl = sum(t['pnl_pct'] for t in trades)
        avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
        avg_loss = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
        
        return {
            'total_trades': len(trades),
            'wins': len(wins),
            'losses': len(losses),
            'win_rate': win_rate,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'avg_rr':  abs(avg_win / avg_loss) if avg_loss != 0 else 0,
            'trades': trades
        }

# Test script
async def main():
    engine = ICTBacktestEngine()
    
    symbols = ['SOLUSDT', 'ETHUSDT', 'BTCUSDT']
    timeframes = ['5m', '15m']
    
    all_results = {}
    
    for symbol in symbols:
        for tf in timeframes:
            result = await engine.run_backtest(symbol, tf, days=30)
            
            key = f"{symbol}_{tf}"
            all_results[key] = result
            
            print(f"\n✅ {symbol} {tf}:")
            print(f"   Trades: {result. get('total_trades', 0)}")
            print(f"   Win Rate: {result.get('win_rate', 0):.1f}%")
            print(f"   Total PnL: {result.get('total_pnl', 0):.2f}%")
            print(f"   Avg RR: {result.get('avg_rr', 0):.2f}")
    
    # Save
    with open('ict_backtest_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'results': all_results
        }, f, indent=2)
    
    print("\n✅ Results saved to ict_backtest_results.json")

if __name__ == '__main__':
    asyncio. run(main())
