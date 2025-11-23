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
        """Генерира дневен отчет"""
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
            
            # Анализ
            total = len(today_signals)
            buy_signals = len([s for s in today_signals if s['type'] == 'BUY'])
            sell_signals = len([s for s in today_signals if s['type'] == 'SELL'])
            
            # Вземи последните резултати (ако има)
            completed_signals = [s for s in today_signals if 'result' in s]
            
            if completed_signals:
                wins = len([s for s in completed_signals if s['result'] == 'WIN'])
                losses = len([s for s in completed_signals if s['result'] == 'LOSS'])
                win_rate = (wins / len(completed_signals) * 100) if completed_signals else 0
            else:
                wins = losses = 0
                win_rate = 0
            
            # Най-добър и най-лош trade
            best_trade = None
            worst_trade = None
            
            if completed_signals:
                trades_with_profit = [s for s in completed_signals if 'profit_pct' in s]
                if trades_with_profit:
                    best_trade = max(trades_with_profit, key=lambda x: x['profit_pct'])
                    worst_trade = min(trades_with_profit, key=lambda x: x['profit_pct'])
            
            # Средна confidence
            avg_confidence = sum([s['confidence'] for s in today_signals]) / total if total > 0 else 0
            
            # ML статистика
            ml_signals = [s for s in today_signals if 'ml_mode' in s]
            ml_used = len(ml_signals)
            
            report = {
                'date': today.isoformat(),
                'timestamp': datetime.now().isoformat(),
                'total_signals': total,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'completed_trades': len(completed_signals),
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
                'avg_confidence': avg_confidence,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'ml_signals_count': ml_used,
                'symbols_traded': list(set([s['symbol'] for s in today_signals]))
            }
            
            # Запази отчета
            self._save_report(report)
            
            return report
            
        except Exception as e:
            print(f"❌ Report generation error: {e}")
            return None
    
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
        """Форматира отчета за Telegram"""
        if not report:
            return "❌ Грешка при генериране на отчет"
        
        if report.get('total_signals', 0) == 0:
            return f"""📊 <b>ДНЕВЕН ОТЧЕТ</b>
📅 {report['date']}

⚪ <i>Няма сигнали за днес</i>

💡 Пазарът е спокоен. Използвай /signal за ръчен анализ."""
        
        message = f"""📊 <b>ДНЕВЕН ОТЧЕТ</b>
📅 {report['date']}
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>Сигнали:</b>
   Общо: {report['total_signals']}
   🟢 BUY: {report['buy_signals']}
   🔴 SELL: {report['sell_signals']}

"""
        
        # Завършени trades
        if report['completed_trades'] > 0:
            emoji = "🔥" if report['win_rate'] >= 70 else "💪" if report['win_rate'] >= 60 else "👍" if report['win_rate'] >= 50 else "😐"
            
            message += f"""🎯 <b>Резултати:</b>
   Trades: {report['completed_trades']}
   ✅ Печеливши: {report['wins']}
   ❌ Загубени: {report['losses']}
   {emoji} Win Rate: {report['win_rate']:.1f}%

"""
        
        # Confidence
        conf_emoji = "🔥" if report['avg_confidence'] >= 75 else "💪" if report['avg_confidence'] >= 65 else "👍"
        message += f"""{conf_emoji} <b>Средна увереност:</b> {report['avg_confidence']:.1f}%

"""
        
        # Best/Worst trade
        if report.get('best_trade'):
            best = report['best_trade']
            message += f"""💎 <b>Най-добър trade:</b>
   {best['symbol']} {best['type']}
   Profit: {best.get('profit_pct', 0):+.2f}%

"""
        
        if report.get('worst_trade'):
            worst = report['worst_trade']
            message += f"""⚠️ <b>Най-лош trade:</b>
   {worst['symbol']} {worst['type']}
   Loss: {worst.get('profit_pct', 0):+.2f}%

"""
        
        # ML използване
        if report.get('ml_signals_count', 0) > 0:
            ml_pct = (report['ml_signals_count'] / report['total_signals']) * 100
            message += f"""🤖 <b>Machine Learning:</b>
   Използван в {report['ml_signals_count']} сигнала ({ml_pct:.0f}%)

"""
        
        # Символи
        symbols = ', '.join(report.get('symbols_traded', []))
        message += f"""💰 <b>Търгувани:</b> {symbols}

━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Генериран: {datetime.now().strftime('%H:%M:%S')}
💡 Следващ отчет: Утре в 20:00"""
        
        return message
    
    def get_weekly_summary(self):
        """Седмичен обобщен отчет"""
        try:
            if not os.path.exists(self.reports_path):
                return None
            
            with open(self.reports_path, 'r') as f:
                all_reports = json.load(f)
            
            # Последните 7 дни
            week_ago = datetime.now().date() - timedelta(days=7)
            weekly_reports = [
                r for r in all_reports['reports']
                if datetime.fromisoformat(r['date']).date() >= week_ago
            ]
            
            if not weekly_reports:
                return None
            
            # Агрегирай
            total_signals = sum([r.get('total_signals', 0) for r in weekly_reports])
            total_completed = sum([r.get('completed_trades', 0) for r in weekly_reports])
            total_wins = sum([r.get('wins', 0) for r in weekly_reports])
            total_losses = sum([r.get('losses', 0) for r in weekly_reports])
            
            weekly_win_rate = (total_wins / total_completed * 100) if total_completed > 0 else 0
            avg_confidence = sum([r.get('avg_confidence', 0) for r in weekly_reports]) / len(weekly_reports)
            
            return {
                'period': '7 дни',
                'total_signals': total_signals,
                'total_completed': total_completed,
                'total_wins': total_wins,
                'total_losses': total_losses,
                'win_rate': weekly_win_rate,
                'avg_confidence': avg_confidence,
                'reports_count': len(weekly_reports)
            }
            
        except Exception as e:
            print(f"❌ Weekly summary error: {e}")
            return None


# Global report instance
report_engine = DailyReportEngine()
