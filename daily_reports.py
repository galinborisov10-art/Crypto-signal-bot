"""
📊 DAILY REPORTS ENGINE
Автоматични дневни отчети за ефективността
"""

from datetime import datetime, timedelta
import json
import os

class DailyReportEngine:
    def __init__(self):
        self.stats_path = '/workspaces/Crypto-signal-bot/bot_stats.json'
        self.reports_path = '/workspaces/Crypto-signal-bot/daily_reports.json'
    
    def generate_daily_report(self):
        """Генерира дневен отчет с анализ на точност и успеваемост"""
        try:
            # Зареди статистика
            if not os.path.exists(self.stats_path):
                return None
            
            with open(self.stats_path, 'r') as f:
                stats = json.load(f)
            
            # Филтрирай днешни сигнали
            today = datetime.now().date()
            today_signals = [
                s for s in stats['signals']
                if datetime.fromisoformat(s['timestamp']).date() == today
            ]
            
            if not today_signals:
                return self._generate_no_signals_report()
            
            # === ОСНОВНИ СТАТИСТИКИ ===
            total = len(today_signals)
            buy_signals = len([s for s in today_signals if s['type'] == 'BUY'])
            sell_signals = len([s for s in today_signals if s['type'] == 'SELL'])
            
            # === АНАЛИЗ НА ТОЧНОСТ ===
            completed_signals = [s for s in today_signals if s.get('status') == 'COMPLETED']
            active_signals = [s for s in today_signals if s.get('status') == 'ACTIVE']
            
            # Точност (Accuracy) - колко сигнала са завършени успешно
            if completed_signals:
                wins = len([s for s in completed_signals if s.get('result') == 'WIN'])
                losses = len([s for s in completed_signals if s.get('result') == 'LOSS'])
                breakeven = len([s for s in completed_signals if s.get('result') == 'BREAKEVEN'])
                
                accuracy = (wins / len(completed_signals) * 100) if completed_signals else 0
                win_rate = (wins / len(completed_signals) * 100) if completed_signals else 0
            else:
                wins = losses = breakeven = 0
                accuracy = win_rate = 0
            
            # === УСПЕВАЕМОСТ (Performance) ===
            total_profit = 0
            avg_win = 0
            avg_loss = 0
            best_trade = None
            worst_trade = None
            
            if completed_signals:
                profitable_trades = [s for s in completed_signals if s.get('profit_pct', 0) > 0]
                losing_trades = [s for s in completed_signals if s.get('profit_pct', 0) < 0]
                
                # Общ profit
                total_profit = sum([s.get('profit_pct', 0) for s in completed_signals])
                
                # Среден печеливш и губещ trade
                if profitable_trades:
                    avg_win = sum([s['profit_pct'] for s in profitable_trades]) / len(profitable_trades)
                    best_trade = max(profitable_trades, key=lambda x: x['profit_pct'])
                
                if losing_trades:
                    avg_loss = sum([s['profit_pct'] for s in losing_trades]) / len(losing_trades)
                    worst_trade = min(losing_trades, key=lambda x: x['profit_pct'])
            
            # === СТАТИСТИКА ПО CONFIDENCE ===
            avg_confidence = sum([s['confidence'] for s in today_signals]) / total if total > 0 else 0
            
            # Точност по confidence ranges
            confidence_accuracy = {}
            for range_name in ['60-69', '70-79', '80-89', '90-100']:
                range_signals = [s for s in completed_signals 
                                if self._in_confidence_range(s['confidence'], range_name)]
                if range_signals:
                    range_wins = len([s for s in range_signals if s.get('result') == 'WIN'])
                    confidence_accuracy[range_name] = {
                        'total': len(range_signals),
                        'wins': range_wins,
                        'accuracy': (range_wins / len(range_signals) * 100)
                    }
            
            # === СТАТИСТИКА ПО СИМВОЛИ ===
            symbols_stats = {}
            symbols_traded = list(set([s['symbol'] for s in today_signals]))
            
            for symbol in symbols_traded:
                symbol_signals = [s for s in today_signals if s['symbol'] == symbol]
                symbol_completed = [s for s in symbol_signals if s.get('status') == 'COMPLETED']
                
                if symbol_completed:
                    symbol_wins = len([s for s in symbol_completed if s.get('result') == 'WIN'])
                    symbol_accuracy = (symbol_wins / len(symbol_completed) * 100)
                    symbol_profit = sum([s.get('profit_pct', 0) for s in symbol_completed])
                else:
                    symbol_wins = 0
                    symbol_accuracy = 0
                    symbol_profit = 0
                
                symbols_stats[symbol] = {
                    'total': len(symbol_signals),
                    'completed': len(symbol_completed),
                    'wins': symbol_wins,
                    'accuracy': symbol_accuracy,
                    'profit': symbol_profit
                }
            
            # === ML СТАТИСТИКА ===
            ml_signals = [s for s in today_signals if s.get('ml_mode')]
            ml_completed = [s for s in ml_signals if s.get('status') == 'COMPLETED']
            
            if ml_completed:
                ml_wins = len([s for s in ml_completed if s.get('result') == 'WIN'])
                ml_accuracy = (ml_wins / len(ml_completed) * 100)
            else:
                ml_wins = 0
                ml_accuracy = 0
            
            report = {
                'date': today.isoformat(),
                'timestamp': datetime.now().isoformat(),
                
                # Основни данни
                'total_signals': total,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'active_signals': len(active_signals),
                'completed_signals': len(completed_signals),
                
                # Точност
                'wins': wins,
                'losses': losses,
                'breakeven': breakeven,
                'accuracy': accuracy,
                'win_rate': win_rate,
                
                # Успеваемост
                'total_profit': total_profit,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'profit_factor': abs(avg_win / avg_loss) if avg_loss != 0 else 0,
                
                # Confidence
                'avg_confidence': avg_confidence,
                'confidence_accuracy': confidence_accuracy,
                
                # Символи
                'symbols_traded': symbols_traded,
                'symbols_stats': symbols_stats,
                
                # ML
                'ml_signals_count': len(ml_signals),
                'ml_completed': len(ml_completed),
                'ml_accuracy': ml_accuracy
            }
            
            # Запази отчета
            self._save_report(report)
            
            return report
            
        except Exception as e:
            print(f"❌ Report generation error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _in_confidence_range(self, confidence, range_name):
        """Проверява дали confidence е в даден range"""
        if range_name == '60-69':
            return 60 <= confidence < 70
        elif range_name == '70-79':
            return 70 <= confidence < 80
        elif range_name == '80-89':
            return 80 <= confidence < 90
        elif range_name == '90-100':
            return 90 <= confidence <= 100
        return False
    
    def _generate_no_signals_report(self):
        """Генерира отчет без сигнали"""
        today = datetime.now().date()
        report = {
            'date': today.isoformat(),
            'timestamp': datetime.now().isoformat(),
            'total_signals': 0,
            'message': 'Няма сигнали за днес'
        }
        self._save_report(report)
        return report
    
    def _save_report(self, report):
        """Запазва отчета"""
        try:
            if os.path.exists(self.reports_path):
                with open(self.reports_path, 'r') as f:
                    all_reports = json.load(f)
            else:
                all_reports = {'reports': []}
            
            all_reports['reports'].append(report)
            
            # Пази само последните 30 дни
            if len(all_reports['reports']) > 30:
                all_reports['reports'] = all_reports['reports'][-30:]
            
            with open(self.reports_path, 'w') as f:
                json.dump(all_reports, f, indent=2)
            
        except Exception as e:
            print(f"❌ Save report error: {e}")
    
    def format_report_message(self, report):
        """Форматира отчета за Telegram с детайлна точност и успеваемост"""
        if not report:
            return "❌ Грешка при генериране на отчет"
        
        if report.get('total_signals', 0) == 0:
            return f"""📊 <b>ДНЕВЕН ОТЧЕТ</b>
📅 {report['date']}

⚪ <i>Няма сигнали за днес</i>

💡 Пазарът е спокоен. Използвай /signal за ръчен анализ."""
        
        message = f"""📊 <b>ДНЕВЕН ОТЧЕТ - АНАЛИЗ НА ЕФЕКТИВНОСТ</b>
📅 {report['date']}
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>ГЕНЕРИРАНИ СИГНАЛИ:</b>
   📊 Общо: <b>{report['total_signals']}</b>
   🟢 BUY: {report['buy_signals']}
   🔴 SELL: {report['sell_signals']}
   ⏳ Активни: {report['active_signals']}
   ✅ Завършени: {report['completed_signals']}

"""
        
        # === ТОЧНОСТ (ACCURACY) ===
        if report['completed_signals'] > 0:
            accuracy_emoji = "🔥" if report['accuracy'] >= 70 else "💪" if report['accuracy'] >= 60 else "👍" if report['accuracy'] >= 50 else "😐" if report['accuracy'] >= 40 else "⚠️"
            
            message += f"""🎯 <b>ТОЧНОСТ НА СИГНАЛИТЕ:</b>
   {accuracy_emoji} Accuracy: <b>{report['accuracy']:.1f}%</b>
   ✅ Печеливши: {report['wins']} ({report['wins']}/{report['completed_signals']})
   ❌ Загубени: {report['losses']} ({report['losses']}/{report['completed_signals']})
"""
            if report.get('breakeven', 0) > 0:
                message += f"   ⚖️ Breakeven: {report['breakeven']}\n"
            
            message += "\n"
        else:
            message += f"""🎯 <b>ТОЧНОСТ НА СИГНАЛИТЕ:</b>
   ⏳ Всички сигнали все още са активни
   💡 Проверка на резултатите след 24ч

"""
        
        # === УСПЕВАЕМОСТ (PERFORMANCE) ===
        if report['completed_signals'] > 0 and report['total_profit'] != 0:
            profit_emoji = "💰" if report['total_profit'] > 0 else "📉"
            
            message += f"""💵 <b>УСПЕВАЕМОСТ (PROFIT/LOSS):</b>
   {profit_emoji} Общ Profit: <b>{report['total_profit']:+.2f}%</b>
"""
            
            if report['avg_win'] > 0:
                message += f"   📈 Среден печеливш trade: +{report['avg_win']:.2f}%\n"
            
            if report['avg_loss'] < 0:
                message += f"   📉 Среден губещ trade: {report['avg_loss']:.2f}%\n"
            
            if report.get('profit_factor', 0) > 0:
                pf_emoji = "🔥" if report['profit_factor'] >= 2 else "💪" if report['profit_factor'] >= 1.5 else "👍"
                message += f"   {pf_emoji} Profit Factor: {report['profit_factor']:.2f}\n"
            
            message += "\n"
        
        # === BEST/WORST TRADE ===
        if report.get('best_trade'):
            best = report['best_trade']
            message += f"""💎 <b>НАЙ-ДОБЪР TRADE:</b>
   {best['symbol']} {best['type']} - {best['timeframe']}
   💰 Profit: <b>+{best.get('profit_pct', 0):.2f}%</b>
   💪 Confidence: {best['confidence']}%

"""
        
        if report.get('worst_trade'):
            worst = report['worst_trade']
            message += f"""⚠️ <b>НАЙ-ЛОШ TRADE:</b>
   {worst['symbol']} {worst['type']} - {worst['timeframe']}
   📉 Loss: <b>{worst.get('profit_pct', 0):.2f}%</b>
   💪 Confidence: {worst['confidence']}%

"""
        
        # === ТОЧНОСТ ПО CONFIDENCE RANGES ===
        if report.get('confidence_accuracy'):
            message += f"""📊 <b>ТОЧНОСТ ПО УВЕРЕНОСТ:</b>
"""
            for range_name in ['90-100', '80-89', '70-79', '60-69']:
                if range_name in report['confidence_accuracy']:
                    data = report['confidence_accuracy'][range_name]
                    acc_emoji = "🔥" if data['accuracy'] >= 70 else "💪" if data['accuracy'] >= 60 else "👍" if data['accuracy'] >= 50 else "😐"
                    message += f"   {acc_emoji} {range_name}%: {data['accuracy']:.1f}% ({data['wins']}/{data['total']})\n"
            
            message += "\n"
        
        # === СТАТИСТИКА ПО СИМВОЛИ ===
        if report.get('symbols_stats'):
            message += f"""💰 <b>ЕФЕКТИВНОСТ ПО ВАЛУТИ:</b>
"""
            for symbol, stats in sorted(report['symbols_stats'].items(), key=lambda x: x[1]['profit'], reverse=True):
                if stats['completed'] > 0:
                    profit_emoji = "💚" if stats['profit'] > 0 else "🔴" if stats['profit'] < 0 else "⚪"
                    message += f"   {profit_emoji} {symbol}: {stats['accuracy']:.0f}% accuracy, {stats['profit']:+.2f}% profit ({stats['completed']} trades)\n"
                else:
                    message += f"   ⏳ {symbol}: {stats['total']} активни\n"
            
            message += "\n"
        
        # === CONFIDENCE ===
        conf_emoji = "🔥" if report['avg_confidence'] >= 75 else "💪" if report['avg_confidence'] >= 65 else "👍"
        message += f"""{conf_emoji} <b>Средна увереност:</b> {report['avg_confidence']:.1f}%

"""
        
        # === ML ИЗПОЛЗВАНЕ ===
        if report.get('ml_signals_count', 0) > 0:
            ml_pct = (report['ml_signals_count'] / report['total_signals']) * 100
            message += f"""🤖 <b>MACHINE LEARNING:</b>
   Използван в {report['ml_signals_count']} сигнала ({ml_pct:.0f}%)
"""
            
            if report.get('ml_completed', 0) > 0:
                ml_emoji = "🔥" if report['ml_accuracy'] >= 70 else "💪" if report['ml_accuracy'] >= 60 else "👍"
                message += f"   {ml_emoji} ML Accuracy: {report['ml_accuracy']:.1f}%\n"
            
            message += "\n"
        
        message += f"""━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Генериран: {datetime.now().strftime('%H:%M:%S')}
💡 Следващ отчет: Утре в 20:00

📈 <b>ОБОБЩЕНИЕ:</b>"""
        
        # Финално обобщение
        if report['completed_signals'] > 0:
            if report['accuracy'] >= 70:
                message += "\n🔥 <b>Отличен ден!</b> Високата точност показва качествени сигнали."
            elif report['accuracy'] >= 60:
                message += "\n💪 <b>Добър ден!</b> Стабилна ефективност на сигналите."
            elif report['accuracy'] >= 50:
                message += "\n👍 <b>Среден ден.</b> Има място за подобрение."
            else:
                message += "\n⚠️ <b>Слаб ден.</b> Преразгледай стратегията."
            
            if report['total_profit'] > 5:
                message += "\n💰 Силна печалба днес!"
            elif report['total_profit'] > 0:
                message += "\n💵 Позитивен резултат."
            elif report['total_profit'] < -5:
                message += "\n📉 Значителна загуба - внимавай!"
        else:
            message += "\n⏳ Чакаме завършване на активните trades за оценка."
        
        return message
    
    def get_weekly_summary(self):
        """Седмичен обобщен отчет с точност и успеваемост"""
        try:
            if not os.path.exists(self.stats_path):
                return None
            
            with open(self.stats_path, 'r') as f:
                stats = json.load(f)
            
            # Последните 7 дни
            week_ago = datetime.now().date() - timedelta(days=7)
            weekly_signals = [
                s for s in stats['signals']
                if datetime.fromisoformat(s['timestamp']).date() >= week_ago
            ]
            
            if not weekly_signals:
                return None
            
            # Основни статистики
            total_signals = len(weekly_signals)
            buy_signals = len([s for s in weekly_signals if s['type'] == 'BUY'])
            sell_signals = len([s for s in weekly_signals if s['type'] == 'SELL'])
            
            # Завършени trades
            completed = [s for s in weekly_signals if s.get('status') == 'COMPLETED']
            active = [s for s in weekly_signals if s.get('status') == 'ACTIVE']
            
            # Точност
            if completed:
                wins = len([s for s in completed if s.get('result') == 'WIN'])
                losses = len([s for s in completed if s.get('result') == 'LOSS'])
                accuracy = (wins / len(completed) * 100)
            else:
                wins = losses = 0
                accuracy = 0
            
            # Успеваемост
            total_profit = sum([s.get('profit_pct', 0) for s in completed])
            
            if completed:
                profitable = [s for s in completed if s.get('profit_pct', 0) > 0]
                losing = [s for s in completed if s.get('profit_pct', 0) < 0]
                
                avg_win = sum([s['profit_pct'] for s in profitable]) / len(profitable) if profitable else 0
                avg_loss = sum([s['profit_pct'] for s in losing]) / len(losing) if losing else 0
                best_trade = max(completed, key=lambda x: x.get('profit_pct', 0)) if completed else None
                worst_trade = min(completed, key=lambda x: x.get('profit_pct', 0)) if completed else None
            else:
                avg_win = avg_loss = 0
                best_trade = worst_trade = None
            
            # Confidence
            avg_confidence = sum([s['confidence'] for s in weekly_signals]) / total_signals
            
            # По дни
            daily_breakdown = {}
            for i in range(7):
                day = datetime.now().date() - timedelta(days=i)
                day_signals = [s for s in weekly_signals 
                             if datetime.fromisoformat(s['timestamp']).date() == day]
                day_completed = [s for s in day_signals if s.get('status') == 'COMPLETED']
                
                if day_completed:
                    day_wins = len([s for s in day_completed if s.get('result') == 'WIN'])
                    day_accuracy = (day_wins / len(day_completed) * 100)
                    day_profit = sum([s.get('profit_pct', 0) for s in day_completed])
                else:
                    day_accuracy = 0
                    day_profit = 0
                
                daily_breakdown[day.isoformat()] = {
                    'total': len(day_signals),
                    'completed': len(day_completed),
                    'accuracy': day_accuracy,
                    'profit': day_profit
                }
            
            return {
                'period': '7 дни',
                'start_date': week_ago.isoformat(),
                'end_date': datetime.now().date().isoformat(),
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'active_signals': len(active),
                'completed_signals': len(completed),
                'wins': wins,
                'losses': losses,
                'accuracy': accuracy,
                'total_profit': total_profit,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'avg_confidence': avg_confidence,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'daily_breakdown': daily_breakdown
            }
            
        except Exception as e:
            print(f"❌ Weekly summary error: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def get_monthly_summary(self):
        """Месечен обобщен отчет с точност и успеваемост"""
        try:
            if not os.path.exists(self.stats_path):
                return None
            
            with open(self.stats_path, 'r') as f:
                stats = json.load(f)
            
            # Последните 30 дни
            month_ago = datetime.now().date() - timedelta(days=30)
            monthly_signals = [
                s for s in stats['signals']
                if datetime.fromisoformat(s['timestamp']).date() >= month_ago
            ]
            
            if not monthly_signals:
                return None
            
            # Основни статистики
            total_signals = len(monthly_signals)
            buy_signals = len([s for s in monthly_signals if s['type'] == 'BUY'])
            sell_signals = len([s for s in monthly_signals if s['type'] == 'SELL'])
            
            # Завършени trades
            completed = [s for s in monthly_signals if s.get('status') == 'COMPLETED']
            active = [s for s in monthly_signals if s.get('status') == 'ACTIVE']
            
            # Точност
            if completed:
                wins = len([s for s in completed if s.get('result') == 'WIN'])
                losses = len([s for s in completed if s.get('result') == 'LOSS'])
                accuracy = (wins / len(completed) * 100)
            else:
                wins = losses = 0
                accuracy = 0
            
            # Успеваемост
            total_profit = sum([s.get('profit_pct', 0) for s in completed])
            
            if completed:
                profitable = [s for s in completed if s.get('profit_pct', 0) > 0]
                losing = [s for s in completed if s.get('profit_pct', 0) < 0]
                
                avg_win = sum([s['profit_pct'] for s in profitable]) / len(profitable) if profitable else 0
                avg_loss = sum([s['profit_pct'] for s in losing]) / len(losing) if losing else 0
                best_trade = max(completed, key=lambda x: x.get('profit_pct', 0)) if completed else None
                worst_trade = min(completed, key=lambda x: x.get('profit_pct', 0)) if completed else None
                profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            else:
                avg_win = avg_loss = profit_factor = 0
                best_trade = worst_trade = None
            
            # Confidence
            avg_confidence = sum([s['confidence'] for s in monthly_signals]) / total_signals
            
            # Статистика по символи
            symbols_stats = {}
            symbols = list(set([s['symbol'] for s in monthly_signals]))
            
            for symbol in symbols:
                symbol_signals = [s for s in monthly_signals if s['symbol'] == symbol]
                symbol_completed = [s for s in symbol_signals if s.get('status') == 'COMPLETED']
                
                if symbol_completed:
                    symbol_wins = len([s for s in symbol_completed if s.get('result') == 'WIN'])
                    symbol_accuracy = (symbol_wins / len(symbol_completed) * 100)
                    symbol_profit = sum([s.get('profit_pct', 0) for s in symbol_completed])
                else:
                    symbol_wins = 0
                    symbol_accuracy = 0
                    symbol_profit = 0
                
                symbols_stats[symbol] = {
                    'total': len(symbol_signals),
                    'completed': len(symbol_completed),
                    'wins': symbol_wins,
                    'accuracy': symbol_accuracy,
                    'profit': symbol_profit
                }
            
            # По седмици
            weekly_breakdown = {}
            for week in range(4):
                week_start = datetime.now().date() - timedelta(days=(week + 1) * 7)
                week_end = datetime.now().date() - timedelta(days=week * 7)
                
                week_signals = [s for s in monthly_signals 
                              if week_start <= datetime.fromisoformat(s['timestamp']).date() < week_end]
                week_completed = [s for s in week_signals if s.get('status') == 'COMPLETED']
                
                if week_completed:
                    week_wins = len([s for s in week_completed if s.get('result') == 'WIN'])
                    week_accuracy = (week_wins / len(week_completed) * 100)
                    week_profit = sum([s.get('profit_pct', 0) for s in week_completed])
                else:
                    week_accuracy = 0
                    week_profit = 0
                
                weekly_breakdown[f'Week {4-week}'] = {
                    'total': len(week_signals),
                    'completed': len(week_completed),
                    'accuracy': week_accuracy,
                    'profit': week_profit
                }
            
            return {
                'period': '30 дни',
                'start_date': month_ago.isoformat(),
                'end_date': datetime.now().date().isoformat(),
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'active_signals': len(active),
                'completed_signals': len(completed),
                'wins': wins,
                'losses': losses,
                'accuracy': accuracy,
                'total_profit': total_profit,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'profit_factor': profit_factor,
                'avg_confidence': avg_confidence,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'symbols_stats': symbols_stats,
                'weekly_breakdown': weekly_breakdown
            }
            
        except Exception as e:
            print(f"❌ Monthly summary error: {e}")
            import traceback
            traceback.print_exc()
            return None


# Global report instance
report_engine = DailyReportEngine()
