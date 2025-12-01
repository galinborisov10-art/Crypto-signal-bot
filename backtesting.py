"""
📈 BACK-TESTING ENGINE
Тестване на стратегии върху исторически данни
"""

import asyncio
import aiohttp
from datetime import datetime, timedelta
import json
import os

class BacktestEngine:
    def __init__(self):
        # Динамични пътища
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.results_path = os.path.join(base_dir, 'backtest_results.json')
        self.optimized_params_path = os.path.join(base_dir, 'optimized_params.json')
    
    async def fetch_historical_data(self, symbol, timeframe, days=90):
        """Извлича исторически klines данни"""
        try:
            # Binance позволява до 1000 candles на заявка
            interval_minutes = {
                '1m': 1, '5m': 5, '15m': 15, '30m': 30,
                '1h': 60, '2h': 120, '4h': 240,
                '1d': 1440, '1w': 10080
            }
            
            minutes = interval_minutes.get(timeframe, 240)
            candles_needed = int((days * 24 * 60) / minutes)
            
            # Ограничи до 1000
            limit = min(candles_needed, 1000)
            
            url = f"https://api.binance.com/api/v3/klines"
            params = {
                'symbol': symbol,
                'interval': timeframe,
                'limit': limit
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        print(f"✅ Fetched {len(data)} candles for {symbol} ({timeframe})")
                        return data
                    else:
                        print(f"❌ Failed to fetch data: {resp.status}")
                        return None
                        
        except Exception as e:
            print(f"❌ Historical data fetch error: {e}")
            return None
    
    def simulate_trade(self, entry_price, tp_price, sl_price, future_prices, signal):
        """Симулира трейд и връща резултата"""
        try:
            for price_data in future_prices:
                # price_data = [timestamp, open, high, low, close, volume, ...]
                high = float(price_data[2])
                low = float(price_data[3])
                
                if signal == 'BUY':
                    # Провери за TP
                    if high >= tp_price:
                        return 'WIN', ((tp_price - entry_price) / entry_price) * 100
                    # Провери за SL
                    if low <= sl_price:
                        return 'LOSS', ((sl_price - entry_price) / entry_price) * 100
                        
                elif signal == 'SELL':
                    # Провери за TP
                    if low <= tp_price:
                        return 'WIN', ((entry_price - tp_price) / entry_price) * 100
                    # Провери за SL
                    if high >= sl_price:
                        return 'LOSS', ((entry_price - sl_price) / entry_price) * 100
            
            # Не е достигнал нито TP, нито SL
            return 'TIMEOUT', 0
            
        except Exception as e:
            print(f"❌ Trade simulation error: {e}")
            return 'ERROR', 0
    
    async def run_backtest(self, symbol, timeframe, strategy_func, days=90):
        """Изпълнява back-test на стратегията"""
        try:
            print(f"\n📊 Starting backtest for {symbol} ({timeframe}) - {days} days")
            
            # Извлечи данни
            historical_data = await self.fetch_historical_data(symbol, timeframe, days)
            
            if not historical_data or len(historical_data) < 50:
                print("❌ Insufficient historical data")
                return None
            
            trades = []
            wins = 0
            losses = 0
            total_profit = 0
            
            # Симулирай trades на всеки 10-ти candle (за да не е прекалено)
            for i in range(0, len(historical_data) - 20, 10):
                # Вземи данни до момента
                past_data = historical_data[:i+1]
                future_data = historical_data[i+1:i+21]  # Следващите 20 candles
                
                if len(past_data) < 50:
                    continue
                
                # Симулирай анализ (опростен - реалната функция е сложна)
                current_price = float(past_data[-1][4])  # Close price
                
                # Изчисли RSI (опростен)
                closes = [float(c[4]) for c in past_data[-14:]]
                gains = [closes[i] - closes[i-1] for i in range(1, len(closes)) if closes[i] > closes[i-1]]
                losses_list = [closes[i-1] - closes[i] for i in range(1, len(closes)) if closes[i] < closes[i-1]]
                
                avg_gain = sum(gains) / 14 if gains else 0
                avg_loss = sum(losses_list) / 14 if losses_list else 0.01
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))
                
                # Генерирай сигнал
                signal = 'HOLD'
                if rsi < 30:
                    signal = 'BUY'
                elif rsi > 70:
                    signal = 'SELL'
                
                if signal == 'HOLD':
                    continue
                
                # Симулирай trade
                tp_pct = 2.5
                sl_pct = 1.2
                
                if signal == 'BUY':
                    tp_price = current_price * (1 + tp_pct / 100)
                    sl_price = current_price * (1 - sl_pct / 100)
                else:
                    tp_price = current_price * (1 - tp_pct / 100)
                    sl_price = current_price * (1 + sl_pct / 100)
                
                result, profit_pct = self.simulate_trade(
                    current_price, tp_price, sl_price, future_data, signal
                )
                
                if result == 'WIN':
                    wins += 1
                    total_profit += profit_pct
                elif result == 'LOSS':
                    losses += 1
                    total_profit += profit_pct  # Вече е негативен
                
                trades.append({
                    'timestamp': past_data[-1][0],
                    'signal': signal,
                    'entry_price': current_price,
                    'tp_price': tp_price,
                    'sl_price': sl_price,
                    'result': result,
                    'profit_pct': profit_pct
                })
            
            # Резултати
            total_trades = wins + losses
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            results = {
                'symbol': symbol,
                'timeframe': timeframe,
                'period_days': days,
                'total_trades': total_trades,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'total_profit_pct': total_profit,
                'avg_profit_per_trade': total_profit / total_trades if total_trades > 0 else 0,
                'timestamp': datetime.now().isoformat(),
                'trades': trades[-20:]  # Само последните 20 trades
            }
            
            # Запази резултатите
            self.save_results(results)
            
            print(f"\n✅ BACKTEST COMPLETED")
            print(f"📊 Total Trades: {total_trades}")
            print(f"🟢 Wins: {wins}")
            print(f"🔴 Losses: {losses}")
            print(f"🎯 Win Rate: {win_rate:.1f}%")
            print(f"💰 Total Profit: {total_profit:+.2f}%")
            
            return results
            
        except Exception as e:
            print(f"❌ Backtest error: {e}")
            return None
    
    def save_results(self, results):
        """Запазва резултатите от back-test"""
        try:
            # Зареди предишни резултати
            if os.path.exists(self.results_path):
                with open(self.results_path, 'r') as f:
                    all_results = json.load(f)
            else:
                all_results = {'backtests': []}
            
            # Добави нов
            all_results['backtests'].append(results)
            
            # Запази
            with open(self.results_path, 'w') as f:
                json.dump(all_results, f, indent=2)
            
            print(f"✅ Results saved to {self.results_path}")
            
        except Exception as e:
            print(f"❌ Save results error: {e}")
    
    def optimize_parameters(self, backtest_results):
        """Оптимизира TP/SL параметри базирано на резултатите"""
        try:
            if not backtest_results or backtest_results['total_trades'] < 10:
                print("⚠️ Not enough trades for optimization")
                return None
            
            # Анализирай trades
            trades = backtest_results['trades']
            
            # Изчисли оптимални TP/SL
            wins = [t for t in trades if t['result'] == 'WIN']
            losses = [t for t in trades if t['result'] == 'LOSS']
            
            if wins and losses:
                avg_win = sum([t['profit_pct'] for t in wins]) / len(wins)
                avg_loss = abs(sum([t['profit_pct'] for t in losses]) / len(losses))
                
                # Оптимални параметри за 2:1 RR
                optimized_tp = avg_win * 0.9  # 90% от средната печалба
                optimized_sl = optimized_tp / 2  # 2:1 RR
                
                optimized = {
                    'symbol': backtest_results['symbol'],
                    'timeframe': backtest_results['timeframe'],
                    'optimized_tp_pct': optimized_tp,
                    'optimized_sl_pct': optimized_sl,
                    'recommended_rr': 2.0,
                    'based_on_trades': len(trades),
                    'timestamp': datetime.now().isoformat()
                }
                
                # Запази
                with open(self.optimized_params_path, 'w') as f:
                    json.dump(optimized, f, indent=2)
                
                print(f"\n✅ PARAMETERS OPTIMIZED")
                print(f"🎯 Optimal TP: {optimized_tp:.2f}%")
                print(f"🛡️ Optimal SL: {optimized_sl:.2f}%")
                
                return optimized
            else:
                print("⚠️ Insufficient win/loss data")
                return None
                
        except Exception as e:
            print(f"❌ Optimization error: {e}")
            return None


# Global backtest instance
backtest_engine = BacktestEngine()
