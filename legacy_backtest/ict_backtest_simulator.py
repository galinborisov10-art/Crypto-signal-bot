"""
🎯 ICT Strategy Backtest Engine
Tests optimized SL logic with structure awareness
Now includes 80% TP alerts and final WIN/LOSS tracking

✨ ENHANCED FEATURES:
- ALL 10 timeframes: 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 1d, 1w
- ALL 6 symbols: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT
- Rate limiting: 0.5s between API calls
- Retry logic with exponential backoff
- Archive system for historical results
- Auto-cleanup of old archives (30 days)
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
import json
import pandas as pd
import numpy as np
from typing import Dict, List
from pathlib import Path
import shutil
from ict_signal_engine import ICTSignalEngine, MarketBias
from ict_80_alert_handler import ICT80AlertHandler

class ICTBacktestEngine: 
    def __init__(self):
        self.ict_engine = ICTSignalEngine()
        self.alert_handler = ICT80AlertHandler(self.ict_engine)
        self.active_trades = {}  # Track active trades for 80% alerts
        
    async def fetch_klines(self, symbol: str, timeframe: str, days: int = 30):
        """Fetch historical klines from Binance with retry logic"""
        interval_minutes = {
            '1m': 1, '5m': 5, '15m': 15, '30m': 30,
            '1h': 60, '2h': 120, '3h': 180, '4h': 240,
            '1d': 1440, '1w': 10080
        }
        
        minutes = interval_minutes.get(timeframe, 5)
        limit = min(int((days * 24 * 60) / minutes), 1000)
        
        url = "https://api.binance.com/api/v3/klines"
        params = {
            'symbol': symbol,
            'interval': timeframe,
            'limit': limit
        }
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Rate limiting: 0.5 second between requests
                if attempt > 0:
                    await asyncio.sleep(0.5 * (2 ** attempt))
                else:
                    await asyncio.sleep(0.5)
                
                async with aiohttp.ClientSession() as session:
                    async with session.get(url, params=params) as resp:
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
                        elif resp.status == 429:  # Rate limit
                            print(f"⚠️ Rate limited, retrying... (attempt {attempt + 1}/{max_retries})")
                            await asyncio.sleep(2)
                            continue
                        else:
                            print(f"❌ Binance API error: {resp.status}")
                            if attempt < max_retries - 1:
                                continue
                            return None
            except Exception as e:
                print(f"❌ Fetch error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    continue
                return None
        
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
        """Run ICT backtest with 80% TP alerts and final WIN/LOSS tracking"""
        print(f"\n📊 ICT Backtest:  {symbol} {timeframe} ({days} days)")
        
        # Fetch data
        df = await self.fetch_klines(symbol, timeframe, days)
        if df is None or len(df) < 50:
            return {'error': 'Insufficient data'}
        
        df = self.add_indicators(df)
        
        trades = []
        alerts_80 = []
        final_alerts = []
        total_win = 0
        total_loss = 0
        lookback = 50
        lookahead = 20
        
        for i in range(lookback, len(df) - lookahead, 5):  # Every 5 candles
            past_df = df.iloc[:i + 1].copy()
            future_df = df.iloc[i + 1:i + lookahead + 1].copy()
            current_price = df.iloc[i]['close']
            current_timestamp = df.iloc[i]['timestamp']
            
            # Check for 80% TP on active trades
            for trade_id, trade in list(self.active_trades.items()):
                entry_price = trade['entry_price']
                tp_price = trade['tp']
                
                # Calculate distance to TP
                if trade['direction'] == 'BULLISH':
                    distance_to_tp = tp_price - entry_price
                    current_distance = current_price - entry_price
                elif trade['direction'] == 'BEARISH':
                    distance_to_tp = entry_price - tp_price
                    current_distance = entry_price - current_price
                else:
                    continue
                
                percent_to_tp = (current_distance / distance_to_tp) * 100 if distance_to_tp > 0 else 0
                
                # Trigger at 80% (+/- 5%)
                if 75 <= percent_to_tp <= 85 and not trade.get('alert_80_triggered'):
                    # Use ICT 80 Alert Handler for re-analysis
                    klines_list = self._df_to_klines(df.iloc[max(0, i-100):i+1])
                    
                    alert_result = await self.alert_handler.analyze_position(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal_type=trade['direction'],
                        entry_price=trade['entry_price'],
                        tp_price=trade['tp'],
                        current_price=current_price,
                        original_confidence=trade['confidence'],
                        klines=klines_list
                    )
                    
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
                    
                    alerts_80.append(alert)
                    trade['alert_80_triggered'] = True
                    
                    print(f"\n🔔 80% TP ALERT: {symbol}")
                    print(f"   Trade: {trade['direction']} @ {trade['entry_price']}")
                    print(f"   Current: {current_price} ({percent_to_tp:.1f}% to TP)")
                    print(f"   📊 Recommendation: {alert['recommendation']}")
                    print(f"   Confidence: {alert['confidence']:.1f}%")
            
            # Try to generate signal
            try:
                signal = self.ict_engine.generate_signal(past_df, symbol, timeframe)
                
                if signal and signal.entry_price: 
                    # Open new trade
                    trade_id = f"{symbol}_{int(current_timestamp.timestamp())}"
                    tp_prices = [signal.tp1_price, signal.tp2_price, signal.tp3_price] if hasattr(signal, 'tp1_price') else signal.tp_prices
                    
                    trade = {
                        'id': trade_id,
                        'symbol': symbol,
                        'direction': signal.bias.value,
                        'entry_price': signal.entry_price,
                        'entry_time': current_timestamp,
                        'tp': tp_prices[0] if tp_prices else signal.entry_price * 1.02,
                        'sl': signal.sl_price,
                        'confidence': signal.confidence,
                        'status': 'OPEN',
                        'ict_setup': 'ICT',
                        'alert_80_triggered': False
                    }
                    
                    self.active_trades[trade_id] = trade
                    
                    # Simulate trade on future data
                    result = self.simulate_trade(
                        entry=signal.entry_price,
                        sl=signal.sl_price,
                        tp_levels=tp_prices if tp_prices else [signal.entry_price * 1.02],
                        future_df=future_df,
                        bias=signal.bias
                    )
                    
                    # Record trade result
                    trade_record = {
                        'id': trade_id,
                        'timestamp': str(current_timestamp),
                        'bias': signal.bias.value,
                        'entry':  signal.entry_price,
                        'sl': signal.sl_price,
                        'tp': trade['tp'],
                        'result': result['result'],
                        'pnl_pct': result['pnl_pct'],
                        'exit_price': result.get('exit_price', signal.entry_price)
                    }
                    
                    trades.append(trade_record)
                    
                    # Generate final alert
                    if 'TP' in result['result']:
                        final_alert = {
                            'trade_id': trade_id,
                            'symbol': symbol,
                            'result': 'WIN',
                            'entry_price': signal.entry_price,
                            'exit_price': result['exit_price'],
                            'profit_percent': result['pnl_pct'],
                            'entry_time': str(current_timestamp),
                            'ict_setup': 'ICT'
                        }
                        total_win += 1
                        print(f"\n✅ FINAL ALERT: {symbol} - WIN")
                        print(f"   Entry: {signal.entry_price} → Exit: {result['exit_price']}")
                        print(f"   Profit: {result['pnl_pct']:.2f}%")
                    elif result['result'] == 'LOSS':
                        final_alert = {
                            'trade_id': trade_id,
                            'symbol': symbol,
                            'result': 'LOSS',
                            'entry_price': signal.entry_price,
                            'exit_price': result['exit_price'],
                            'profit_percent': result['pnl_pct'],
                            'entry_time': str(current_timestamp),
                            'ict_setup': 'ICT'
                        }
                        total_loss += 1
                        print(f"\n❌ FINAL ALERT: {symbol} - LOSS")
                        print(f"   Entry: {signal.entry_price} → Exit: {result['exit_price']}")
                        print(f"   Loss: {result['pnl_pct']:.2f}%")
                    else:
                        continue
                    
                    final_alerts.append(final_alert)
                    
                    # Remove from active trades
                    if trade_id in self.active_trades:
                        del self.active_trades[trade_id]
                    
            except Exception as e:
                continue
        
        # Calculate stats
        if not trades:
            results = {
                'total_trades': 0,
                'wins': 0,
                'losses': 0,
                'win_rate': 0,
                'total_pnl': 0,
                'avg_rr': 0,
                'alerts_80': alerts_80,
                'final_alerts': final_alerts,
                'total_win': 0,
                'total_loss': 0
            }
        else:
            wins = [t for t in trades if 'TP' in t['result']]
            losses = [t for t in trades if t['result'] == 'LOSS']
            
            win_rate = (len(wins) / len(trades)) * 100 if trades else 0
            total_pnl = sum(t['pnl_pct'] for t in trades)
            avg_win = np.mean([t['pnl_pct'] for t in wins]) if wins else 0
            avg_loss = np.mean([t['pnl_pct'] for t in losses]) if losses else 0
            
            results = {
                'total_trades': len(trades),
                'wins': len(wins),
                'losses': len(losses),
                'win_rate': win_rate,
                'total_pnl': total_pnl,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'avg_rr':  abs(avg_win / avg_loss) if avg_loss != 0 else 0,
                'trades': trades,
                'alerts_80': alerts_80,
                'final_alerts': final_alerts,
                'total_win': total_win,
                'total_loss': total_loss
            }
        
        # Save results to JSON
        self.save_backtest_results(symbol, timeframe, results)
        
        return results
    
    def _df_to_klines(self, df):
        """Convert DataFrame to klines list format"""
        klines = []
        for idx, row in df.iterrows():
            kline = [
                int(idx.timestamp() * 1000) if hasattr(idx, 'timestamp') else int(row['timestamp'].timestamp() * 1000),
                str(row['open']),
                str(row['high']),
                str(row['low']),
                str(row['close']),
                str(row['volume']),
                0, 0, 0, 0, 0, 0
            ]
            klines.append(kline)
        return klines
    
    def save_backtest_results(self, symbol: str, timeframe: str, results: Dict):
        """Save backtest results to JSON"""
        results_dir = Path("backtest_results")
        results_dir.mkdir(exist_ok=True)
        
        filename = results_dir / f"{symbol}_{timeframe}_backtest.json"
        
        # Convert to serializable format
        serializable_results = {
            'symbol': symbol,
            'timeframe': timeframe,
            'timestamp': datetime.now().isoformat(),
            'total_trades': results.get('total_trades', 0),
            'total_win': results.get('total_win', 0),
            'total_loss': results.get('total_loss', 0),
            'win_rate': results.get('win_rate', 0),
            'total_pnl': results.get('total_pnl', 0),
            'alerts_80_count': len(results.get('alerts_80', [])),
            'final_alerts_count': len(results.get('final_alerts', [])),
            'trades': results.get('trades', []),
            'alerts_80': results.get('alerts_80', []),
            'final_alerts': results.get('final_alerts', [])
        }
        
        with open(filename, 'w') as f:
            json.dump(serializable_results, f, indent=2, default=str)
        
        print(f"\n💾 Results saved: {filename}")

# ==================== ARCHIVE MANAGEMENT ====================

def archive_backtest_results():
    """
    Archive current backtest results to backtest_archive/YYYY-MM-DD/
    Called before each daily auto-update
    """
    try:
        results_dir = Path("backtest_results")
        if not results_dir.exists() or not any(results_dir.glob("*.json")):
            print("ℹ️ No backtest results to archive")
            return False
        
        # Create archive directory with current date
        archive_date = datetime.now().strftime("%Y-%m-%d")
        archive_dir = Path("backtest_archive") / archive_date
        archive_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all JSON files to archive
        archived_count = 0
        for result_file in results_dir.glob("*.json"):
            dest_file = archive_dir / result_file.name
            shutil.copy2(result_file, dest_file)
            archived_count += 1
        
        # Save archive metadata
        metadata = {
            'archive_date': archive_date,
            'timestamp': datetime.now().isoformat(),
            'files_archived': archived_count,
            'files': [f.name for f in results_dir.glob("*.json")]
        }
        
        metadata_file = archive_dir / "_metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        print(f"✅ Archived {archived_count} backtest results to {archive_dir}")
        return True
        
    except Exception as e:
        print(f"❌ Archive error: {e}")
        return False


def cleanup_old_archives(max_age_days: int = 30):
    """
    Delete archive directories older than max_age_days
    Default: 30 days retention
    """
    try:
        archive_base = Path("backtest_archive")
        if not archive_base.exists():
            print("ℹ️ No archive directory found")
            return 0
        
        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        deleted_count = 0
        
        for archive_dir in archive_base.iterdir():
            if not archive_dir.is_dir():
                continue
            
            try:
                # Parse directory name as date (YYYY-MM-DD)
                dir_date = datetime.strptime(archive_dir.name, "%Y-%m-%d")
                
                if dir_date < cutoff_date:
                    shutil.rmtree(archive_dir)
                    deleted_count += 1
                    print(f"🗑️ Deleted old archive: {archive_dir.name}")
                    
            except ValueError:
                # Skip directories that don't match date format
                continue
        
        if deleted_count > 0:
            print(f"✅ Cleaned up {deleted_count} old archives (older than {max_age_days} days)")
        else:
            print(f"ℹ️ No archives older than {max_age_days} days found")
        
        return deleted_count
        
    except Exception as e:
        print(f"❌ Cleanup error: {e}")
        return 0


async def run_comprehensive_backtest():
    """
    Run comprehensive backtest across all symbols and timeframes
    Used by daily auto-update scheduler
    """
    print(f"\n{'='*60}")
    print(f"🔄 DAILY AUTO-UPDATE - Starting comprehensive backtest")
    print(f"⏰ Timestamp: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")
    
    # Archive old results first
    print("📦 Archiving previous results...")
    archive_backtest_results()
    
    # Cleanup old archives
    print("\n🧹 Cleaning up old archives...")
    cleanup_old_archives(max_age_days=30)
    
    # Run comprehensive backtest
    print("\n🚀 Running new backtest...\n")
    await main()
    
    print(f"\n{'='*60}")
    print("✅ DAILY AUTO-UPDATE COMPLETE")
    print(f"⏰ Completed: {datetime.now().isoformat()}")
    print(f"{'='*60}\n")

# ==================== MAIN BACKTEST SCRIPT ====================

# Test script
async def main():
    """
    Comprehensive backtest across all major coins and timeframes
    Symbols: BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT
    Timeframes: All 10 supported (1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 1d, 1w)
    """
    engine = ICTBacktestEngine()
    
    # ALL 6 SYMBOLS including XRPUSDT
    symbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'SOLUSDT', 'XRPUSDT', 'ADAUSDT']
    
    # ALL 10 TIMEFRAMES
    timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '3h', '4h', '1d', '1w']
    
    all_results = {}
    total_tests = len(symbols) * len(timeframes)
    current_test = 0
    
    print(f"\n{'='*60}")
    print(f"🎯 ICT BACKTEST - COMPREHENSIVE RUN")
    print(f"{'='*60}")
    print(f"📊 Symbols: {len(symbols)} - {', '.join(symbols)}")
    print(f"⏰ Timeframes: {len(timeframes)} - {', '.join(timeframes)}")
    print(f"🔢 Total tests: {total_tests}")
    print(f"{'='*60}\n")
    
    for symbol in symbols:
        for tf in timeframes:
            current_test += 1
            print(f"\n[{current_test}/{total_tests}] Testing {symbol} {tf}...")
            
            result = await engine.run_backtest(symbol, tf, days=30)
            
            key = f"{symbol}_{tf}"
            all_results[key] = result
            
            print(f"✅ {symbol} {tf}:")
            print(f"   Trades: {result.get('total_trades', 0)}")
            print(f"   Win Rate: {result.get('win_rate', 0):.1f}%")
            print(f"   Total PnL: {result.get('total_pnl', 0):.2f}%")
            print(f"   Avg RR: {result.get('avg_rr', 0):.2f}")
            print(f"   80% Alerts: {result.get('alerts_80_count', 0)}")
    
    # Save comprehensive results
    with open('ict_backtest_results.json', 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'symbols': symbols,
            'timeframes': timeframes,
            'total_tests': total_tests,
            'results': all_results
        }, f, indent=2, default=str)
    
    print(f"\n{'='*60}")
    print("✅ COMPREHENSIVE BACKTEST COMPLETE")
    print(f"💾 Results saved to ict_backtest_results.json")
    print(f"📁 Individual results in backtest_results/ directory")
    print(f"{'='*60}\n")

if __name__ == '__main__':
    asyncio. run(main())
