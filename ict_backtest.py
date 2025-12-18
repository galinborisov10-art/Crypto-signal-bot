"""
🎯 ICT Strategy Backtest Engine
Tests optimized SL logic with structure awareness
Includes 80% TP alerts and final WIN/LOSS tracking
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from pathlib import Path
from ict_signal_engine import ICTSignalEngine, MarketBias

# Import 80% Alert Handler
try:
    from ict_80_alert_handler import ICT80AlertHandler
    ALERT_HANDLER_AVAILABLE = True
except ImportError:
    ALERT_HANDLER_AVAILABLE = False
    print("⚠️ ICT 80% Alert Handler not available")

class ICTBacktestEngine: 
    def __init__(self):
        self.ict_engine = ICTSignalEngine()
        self.alert_handler = ICT80AlertHandler(self.ict_engine) if ALERT_HANDLER_AVAILABLE else None
        self.active_trades = {}  # Track active trades for 80% TP alerts
        self.trade_counter = 0  # Unique trade ID counter
        
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
    
    def _df_to_klines(self, df: pd.DataFrame) -> List:
        """Convert DataFrame to klines list format"""
        klines = []
        for idx, row in df.iterrows():
            timestamp = row.get('timestamp', idx)
            if isinstance(timestamp, pd.Timestamp):
                ts_ms = int(timestamp.timestamp() * 1000)
            elif isinstance(timestamp, datetime):
                ts_ms = int(timestamp.timestamp() * 1000)
            else:
                ts_ms = 0
            
            kline = [
                ts_ms,
                str(row['open']),
                str(row['high']),
                str(row['low']),
                str(row['close']),
                str(row.get('volume', 0)),
                0, 0, 0, 0, 0, 0
            ]
            klines.append(kline)
        return klines
    
    def open_trade(self, signal, entry_price: float, timestamp) -> Dict:
        """Open a new trade based on signal"""
        self.trade_counter += 1
        trade_id = f"trade_{self.trade_counter}"
        
        # Determine direction
        if hasattr(signal, 'signal_type'):
            direction = 'BUY' if 'BUY' in str(signal.signal_type.value) else 'SELL'
        elif hasattr(signal, 'bias'):
            direction = 'BUY' if signal.bias == MarketBias.BULLISH else 'SELL'
        else:
            direction = 'HOLD'
        
        # Get TP (use first TP if multiple)
        if hasattr(signal, 'tp_prices') and signal.tp_prices:
            tp = signal.tp_prices[0]
        elif hasattr(signal, 'tp1_price'):
            tp = signal.tp1_price
        else:
            tp = entry_price * 1.02 if direction == 'BUY' else entry_price * 0.98
        
        # Get SL
        if hasattr(signal, 'sl_price'):
            sl = signal.sl_price
        else:
            sl = entry_price * 0.99 if direction == 'BUY' else entry_price * 1.01
        
        trade = {
            'id': trade_id,
            'symbol': signal.symbol,
            'direction': direction,
            'entry_price': entry_price,
            'entry_time': timestamp,
            'tp': tp,
            'sl': sl,
            'confidence': getattr(signal, 'confidence', 70),
            'status': 'OPEN',
            'alert_80_triggered': False
        }
        
        return trade
    
    def check_trade_closure(self, current_price: float, timestamp) -> List[Dict]:
        """Check if any trades should be closed"""
        closed_trades = []
        
        for trade_id, trade in list(self.active_trades.items()):
            if trade['direction'] == 'BUY':
                if current_price >= trade['tp']:
                    trade['result'] = 'WIN'
                    trade['exit_price'] = current_price
                    trade['exit_time'] = timestamp
                    trade['profit_percent'] = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                    closed_trades.append(trade)
                elif current_price <= trade['sl']:
                    trade['result'] = 'LOSS'
                    trade['exit_price'] = current_price
                    trade['exit_time'] = timestamp
                    trade['profit_percent'] = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
                    closed_trades.append(trade)
            
            elif trade['direction'] == 'SELL':
                if current_price <= trade['tp']:
                    trade['result'] = 'WIN'
                    trade['exit_price'] = current_price
                    trade['exit_time'] = timestamp
                    trade['profit_percent'] = ((trade['entry_price'] - current_price) / trade['entry_price']) * 100
                    closed_trades.append(trade)
                elif current_price >= trade['sl']:
                    trade['result'] = 'LOSS'
                    trade['exit_price'] = current_price
                    trade['exit_time'] = timestamp
                    trade['profit_percent'] = ((trade['entry_price'] - current_price) / trade['entry_price']) * 100
                    closed_trades.append(trade)
        
        return closed_trades
    
    def generate_final_alert(self, trade: Dict) -> Dict:
        """Generate final WIN/LOSS alert"""
        result_emoji = "✅" if trade['result'] == 'WIN' else "❌"
        
        # Calculate duration
        if isinstance(trade['entry_time'], pd.Timestamp):
            entry_dt = trade['entry_time'].to_pydatetime()
        elif isinstance(trade['entry_time'], datetime):
            entry_dt = trade['entry_time']
        else:
            entry_dt = datetime.now()
        
        if isinstance(trade['exit_time'], pd.Timestamp):
            exit_dt = trade['exit_time'].to_pydatetime()
        elif isinstance(trade['exit_time'], datetime):
            exit_dt = trade['exit_time']
        else:
            exit_dt = datetime.now()
        
        duration_hours = (exit_dt - entry_dt).total_seconds() / 3600
        
        alert = {
            'trade_id': trade['id'],
            'symbol': trade['symbol'],
            'result': trade['result'],
            'entry_price': trade['entry_price'],
            'exit_price': trade['exit_price'],
            'profit_percent': trade['profit_percent'],
            'entry_time': str(entry_dt),
            'exit_time': str(exit_dt),
            'duration_hours': duration_hours
        }
        
        print(f"\n{result_emoji} FINAL ALERT: {trade['symbol']}")
        print(f"   Result: {trade['result']}")
        print(f"   Entry: {trade['entry_price']} → Exit: {trade['exit_price']}")
        print(f"   Profit: {trade['profit_percent']:.2f}%")
        print(f"   Duration: {duration_hours:.1f}h")
        
        return alert
    
    def save_backtest_results(self, symbol: str, timeframe: str, results: Dict):
        """Save backtest results to JSON"""
        results_dir = Path("backtest_results")
        results_dir.mkdir(exist_ok=True)
        
        filename = results_dir / f"{symbol}_{timeframe}_backtest.json"
        
        # Convert to serializable format
        serializable_results = {
            'symbol': symbol,
            'timeframe': timeframe,
            'total_trades': len(results['trades']),
            'total_win': results['total_win'],
            'total_loss': results['total_loss'],
            'win_rate': (results['total_win'] / len(results['trades']) * 100) if results['trades'] else 0,
            'alerts_80_count': len(results['alerts_80']),
            'final_alerts_count': len(results['final_alerts']),
            'trades': self._serialize_trades(results['trades']),
            'alerts_80': results['alerts_80'],
            'final_alerts': results['final_alerts']
        }
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved: {filename}")
    
    def _serialize_trades(self, trades: List[Dict]) -> List[Dict]:
        """Convert trades to JSON-serializable format"""
        serialized = []
        for trade in trades:
            t = {}
            for key, value in trade.items():
                if isinstance(value, (pd.Timestamp, datetime)):
                    t[key] = str(value)
                elif isinstance(value, (np.integer, np.floating)):
                    t[key] = float(value)
                else:
                    t[key] = value
            serialized.append(t)
        return serialized
    
    def simulate_trade(self, entry: float, sl: float, tp_levels: List[float], 
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
        """Run ICT backtest with 80% TP alerts and final WIN/LOSS tracking"""
        print(f"\n📊 ICT Backtest: {symbol} {timeframe} ({days} days)")
        
        # Fetch data
        df = await self.fetch_klines(symbol, timeframe, days)
        if df is None or len(df) < 50:
            return {'error': 'Insufficient data'}
        
        df = self.add_indicators(df)
        df.set_index('timestamp', inplace=True, drop=False)
        
        results = {
            'trades': [],
            'alerts_80': [],  # 80% TP alerts
            'final_alerts': [],  # Final WIN/LOSS alerts
            'total_win': 0,
            'total_loss': 0
        }
        
        lookback = 50
        
        for i in range(lookback, len(df)):
            current_bar = df.iloc[:i+1].copy()
            current_price = df.iloc[i]['close']
            current_timestamp = df.iloc[i]['timestamp']
            
            # Check for 80% TP on active trades
            for trade_id, trade in list(self.active_trades.items()):
                entry_price = trade['entry_price']
                tp_price = trade['tp']
                
                # Calculate distance to TP
                if trade['direction'] == 'BUY':
                    distance_to_tp = tp_price - entry_price
                    current_distance = current_price - entry_price
                elif trade['direction'] == 'SELL':
                    distance_to_tp = entry_price - tp_price
                    current_distance = entry_price - current_price
                else:
                    continue
                
                percent_to_tp = (current_distance / distance_to_tp) * 100 if distance_to_tp > 0 else 0
                
                # Trigger at 80% (+/- 5%)
                if 75 <= percent_to_tp <= 85 and not trade.get('alert_80_triggered'):
                    trade['alert_80_triggered'] = True
                    
                    # Use ICT 80 Alert Handler for re-analysis if available
                    if self.alert_handler:
                        klines_list = self._df_to_klines(df.iloc[max(0, i-100):i+1])
                        
                        alert_result = await self.alert_handler.analyze_position(
                            symbol=symbol,
                            timeframe=timeframe,
                            signal_type=trade['direction'],
                            entry_price=entry_price,
                            tp_price=tp_price,
                            current_price=current_price,
                            original_confidence=trade['confidence'],
                            klines=klines_list
                        )
                    else:
                        alert_result = {
                            'recommendation': 'HOLD',
                            'confidence': trade['confidence'],
                            'reasoning': 'Alert handler not available',
                            'score_hold': 0,
                            'score_close': 0
                        }
                    
                    alert = {
                        'trade_id': trade_id,
                        'symbol': symbol,
                        'timestamp': str(current_timestamp),
                        'current_price': current_price,
                        'percent_to_tp': percent_to_tp,
                        'recommendation': alert_result.get('recommendation', 'HOLD'),
                        'confidence': alert_result.get('confidence', 0),
                        'reasoning': alert_result.get('reasoning', ''),
                        'score_hold': alert_result.get('score_hold', 0),
                        'score_close': alert_result.get('score_close', 0)
                    }
                    
                    results['alerts_80'].append(alert)
                    
                    print(f"\n🔔 80% TP ALERT: {symbol}")
                    print(f"   Trade: {trade['direction']} @ {entry_price}")
                    print(f"   Current: {current_price} ({percent_to_tp:.1f}% to TP)")
                    print(f"   📊 Recommendation: {alert['recommendation']}")
                    print(f"   Confidence: {alert['confidence']:.1f}%")
            
            # Check for trade closure
            closed_trades = self.check_trade_closure(current_price, current_timestamp)
            for closed_trade in closed_trades:
                final_alert = self.generate_final_alert(closed_trade)
                results['final_alerts'].append(final_alert)
                results['trades'].append(closed_trade)
                
                if closed_trade['result'] == 'WIN':
                    results['total_win'] += 1
                else:
                    results['total_loss'] += 1
                
                del self.active_trades[closed_trade['id']]
            
            # Generate new signals every 5 candles
            if i % 5 == 0:
                try:
                    signal = self.ict_engine.generate_signal(current_bar, symbol, timeframe)
                    
                    if signal and signal.entry_price and signal.confidence >= 70:
                        trade = self.open_trade(signal, current_price, current_timestamp)
                        self.active_trades[trade['id']] = trade
                        
                except Exception as e:
                    continue
        
        # Close any remaining active trades
        for trade_id, trade in list(self.active_trades.items()):
            trade['result'] = 'TIMEOUT'
            trade['exit_price'] = df.iloc[-1]['close']
            trade['exit_time'] = df.iloc[-1]['timestamp']
            trade['profit_percent'] = 0
            results['trades'].append(trade)
            del self.active_trades[trade_id]
        
        # Save results to JSON
        self.save_backtest_results(symbol, timeframe, results)
        
        # Calculate stats
        total_trades = len(results['trades'])
        win_rate = (results['total_win'] / total_trades * 100) if total_trades > 0 else 0
        
        return {
            'total_trades': total_trades,
            'wins': results['total_win'],
            'losses': results['total_loss'],
            'win_rate': win_rate,
            'total_pnl': sum(t.get('profit_percent', 0) for t in results['trades']),
            'alerts_80_count': len(results['alerts_80']),
            'final_alerts_count': len(results['final_alerts']),
            'trades': results['trades']
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
