"""
📊 DAILY REPORTS ENGINE
Автоматични дневни отчети за ефективността
"""

from datetime import datetime, timedelta
import json
import os
import logging

logger = logging.getLogger(__name__)

class DailyReportEngine:
    def __init__(self):
        # Auto-detect base path (works on Codespace AND server)
        if os.path.exists('/root/Crypto-signal-bot'):
            base_path = '/root/Crypto-signal-bot'
        else:
            base_path = '/workspaces/Crypto-signal-bot'
        
        # НОВО: Главен източник е ml_journal.json
        self.journal_path = f'{base_path}/ml_journal.json'
        # Резервен към bot_stats.json
        self.stats_path = f'{base_path}/bot_stats.json'
        self.reports_path = f'{base_path}/daily_reports.json'
    
    def generate_daily_report(self):
        """Генерира дневен отчет с анализ на точност и успеваемост"""
        try:
            logger.info("📊 Starting daily report generation...")
            
            # Зареди данни от ml_journal.json първо, резервно bot_stats.json
            stats = None
            
            # Try ml_journal.json first (preferred)
            if os.path.exists(self.journal_path):
                try:
                    logger.debug(f"Loading data from ml_journal.json: {self.journal_path}")
                    with open(self.journal_path, 'r') as f:
                        journal = json.load(f)
                    stats = {'signals': journal.get('trades', [])}
                    logger.info(f"✅ Loaded {len(stats['signals'])} trades from ml_journal.json")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load ml_journal.json: {e}")
            
            # Fallback to bot_stats.json
            if not stats and os.path.exists(self.stats_path):
                try:
                    logger.debug(f"Fallback: Loading data from bot_stats.json: {self.stats_path}")
                    with open(self.stats_path, 'r') as f:
                        stats = json.load(f)
                    logger.info(f"✅ Loaded {len(stats.get('signals', []))} signals from bot_stats.json")
                except Exception as e:
                    logger.error(f"❌ Failed to load bot_stats.json: {e}")
            
            if not stats:
                logger.warning("⚠️ No data source available for report")
                return None
            
            # Филтрирай ВЧЕРАШНИ сигнали (не днешни!)
            today = datetime.now().date()
            yesterday = today - timedelta(days=1)
            logger.debug(f"Filtering trades for yesterday: {yesterday}")
            
            yesterday_signals = [
                s for s in stats.get('signals', [])
                if datetime.fromisoformat(s['timestamp']).date() == yesterday
            ]
            
            logger.info(f"📅 Found {len(yesterday_signals)} signals for yesterday ({yesterday})")
            
            if not yesterday_signals:
                logger.info("No signals for yesterday, generating empty report")
                return self._generate_no_signals_report(yesterday)
            
            # === ОСНОВНИ СТАТИСТИКИ ===
            total = len(yesterday_signals)
            buy_signals = len([s for s in yesterday_signals if s['type'] == 'BUY'])
            sell_signals = len([s for s in yesterday_signals if s['type'] == 'SELL'])
            logger.debug(f"Basic stats: Total={total}, BUY={buy_signals}, SELL={sell_signals}")
            
            # === АНАЛИЗ НА ТОЧНОСТ ===
            # Използвай status: WIN/LOSS/PENDING или outcome: WIN/LOSS
            completed_signals = [
                s for s in yesterday_signals 
                if s.get('status') in ['WIN', 'LOSS'] or s.get('outcome') in ['WIN', 'LOSS']
            ]
            active_signals = [
                s for s in yesterday_signals 
                if s.get('status') == 'PENDING' or (s.get('status') not in ['WIN', 'LOSS'] and s.get('outcome') not in ['WIN', 'LOSS'])
            ]
            
            logger.debug(f"Completed: {len(completed_signals)}, Active: {len(active_signals)}")
            
            # Точност (Accuracy) - колко сигнала са завършени успешно
            if completed_signals:
                wins = len([
                    s for s in completed_signals 
                    if s.get('status') == 'WIN' or s.get('outcome') == 'WIN' or s.get('result') == 'WIN'
                ])
                losses = len([
                    s for s in completed_signals 
                    if s.get('status') == 'LOSS' or s.get('outcome') == 'LOSS' or s.get('result') == 'LOSS'
                ])
                breakeven = len([s for s in completed_signals if s.get('result') == 'BREAKEVEN'])
                
                accuracy = (wins / len(completed_signals) * 100) if completed_signals else 0
                win_rate = (wins / len(completed_signals) * 100) if completed_signals else 0
                logger.info(f"🎯 Accuracy: {accuracy:.1f}% (Wins: {wins}, Losses: {losses})")
            else:
                wins = losses = breakeven = 0
                accuracy = win_rate = 0
                logger.info("⏳ No completed trades yet")
            
            # === УСПЕВАЕМОСТ (Performance) ===
            total_profit = 0
            avg_win = 0
            avg_loss = 0
            best_trade = None
            worst_trade = None
            
            if completed_signals:
                profitable_trades = [s for s in completed_signals if s.get('profit_loss_pct', s.get('profit_pct', 0)) > 0]
                losing_trades = [s for s in completed_signals if s.get('profit_loss_pct', s.get('profit_pct', 0)) < 0]
                
                # Общ profit (използвай profit_loss_pct или profit_pct)
                total_profit = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in completed_signals])
                
                # Среден печеливш и губещ trade
                if profitable_trades:
                    avg_win = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in profitable_trades]) / len(profitable_trades)
                    best_trade = max(profitable_trades, key=lambda x: x.get('profit_loss_pct', x.get('profit_pct', 0)))
                
                if losing_trades:
                    avg_loss = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in losing_trades]) / len(losing_trades)
                    worst_trade = min(losing_trades, key=lambda x: x.get('profit_loss_pct', x.get('profit_pct', 0)))
                
                logger.info(f"💰 Total profit: {total_profit:+.2f}%, Avg win: +{avg_win:.2f}%, Avg loss: {avg_loss:.2f}%")
            
            # === СТАТИСТИКА ПО CONFIDENCE ===
            avg_confidence = sum([s['confidence'] for s in yesterday_signals]) / total if total > 0 else 0
            
            # Точност по confidence ranges
            confidence_accuracy = {}
            for range_name in ['60-69', '70-79', '80-89', '90-100']:
                range_signals = [s for s in completed_signals 
                                if self._in_confidence_range(s['confidence'], range_name)]
                if range_signals:
                    range_wins = len([
                        s for s in range_signals 
                        if s.get('status') == 'WIN' or s.get('outcome') == 'WIN' or s.get('result') == 'WIN'
                    ])
                    confidence_accuracy[range_name] = {
                        'total': len(range_signals),
                        'wins': range_wins,
                        'accuracy': (range_wins / len(range_signals) * 100)
                    }
            
            # === СТАТИСТИКА ПО СИМВОЛИ ===
            symbols_stats = {}
            symbols_traded = list(set([s['symbol'] for s in yesterday_signals]))
            
            for symbol in symbols_traded:
                symbol_signals = [s for s in yesterday_signals if s['symbol'] == symbol]
                symbol_completed = [
                    s for s in symbol_signals 
                    if s.get('status') in ['WIN', 'LOSS'] or s.get('outcome') in ['WIN', 'LOSS']
                ]
                
                if symbol_completed:
                    symbol_wins = len([
                        s for s in symbol_completed 
                        if s.get('status') == 'WIN' or s.get('outcome') == 'WIN' or s.get('result') == 'WIN'
                    ])
                    symbol_accuracy = (symbol_wins / len(symbol_completed) * 100)
                    symbol_profit = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in symbol_completed])
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
            ml_signals = [s for s in yesterday_signals if s.get('ml_mode')]
            ml_completed = [
                s for s in ml_signals 
                if s.get('status') in ['WIN', 'LOSS'] or s.get('outcome') in ['WIN', 'LOSS']
            ]
            
            if ml_completed:
                ml_wins = len([
                    s for s in ml_completed 
                    if s.get('status') == 'WIN' or s.get('outcome') == 'WIN' or s.get('result') == 'WIN'
                ])
                ml_accuracy = (ml_wins / len(ml_completed) * 100)
            else:
                ml_wins = 0
                ml_accuracy = 0
            
            report = {
                'date': yesterday.isoformat(),  # Вчерашна дата!
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
            
            logger.info(f"✅ Daily report generated successfully for {yesterday}")
            return report
            
        except Exception as e:
            logger.error(f"❌ Report generation error: {e}", exc_info=True)
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
    
    def _generate_no_signals_report(self, report_date=None):
        """Генерира отчет без сигнали"""
        if report_date is None:
            report_date = (datetime.now().date() - timedelta(days=1))
        
        report = {
            'date': report_date.isoformat(),
            'timestamp': datetime.now().isoformat(),
            'total_signals': 0,
            'message': f'Няма сигнали за {report_date.strftime("%d.%m.%Y")}'
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
        """Седмичен обобщен отчет за ИЗМИНАЛАТА СЕДМИЦА (Понеделник-Неделя)"""
        try:
            logger.info("📅 Starting weekly summary generation...")
            
            # Зареди данни от ml_journal.json първо, резервно bot_stats.json
            stats = None
            
            # Try ml_journal.json first (preferred)
            if os.path.exists(self.journal_path):
                try:
                    logger.debug(f"Loading data from ml_journal.json: {self.journal_path}")
                    with open(self.journal_path, 'r') as f:
                        journal = json.load(f)
                    stats = {'signals': journal.get('trades', [])}
                    logger.info(f"✅ Loaded {len(stats['signals'])} trades from ml_journal.json")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load ml_journal.json: {e}")
            
            # Fallback to bot_stats.json
            if not stats and os.path.exists(self.stats_path):
                try:
                    logger.debug(f"Fallback: Loading data from bot_stats.json: {self.stats_path}")
                    with open(self.stats_path, 'r') as f:
                        stats = json.load(f)
                    logger.info(f"✅ Loaded {len(stats.get('signals', []))} signals from bot_stats.json")
                except Exception as e:
                    logger.error(f"❌ Failed to load bot_stats.json: {e}")
            
            if not stats:
                logger.warning("⚠️ No data source available for weekly summary")
                return None
            
            # Изчисли ИЗМИНАЛАТА СЕДМИЦА (Понеделник-Неделя)
            today = datetime.now().date()
            days_since_monday = today.weekday()  # 0 = понеделник
            last_monday = today - timedelta(days=days_since_monday + 7)
            last_sunday = last_monday + timedelta(days=6)
            
            logger.info(f"📅 Weekly period: {last_monday} (Mon) - {last_sunday} (Sun)")
            
            weekly_signals = [
                s for s in stats.get('signals', [])
                if last_monday <= datetime.fromisoformat(s['timestamp']).date() <= last_sunday
            ]
            
            logger.info(f"Found {len(weekly_signals)} signals for the week")
            
            if not weekly_signals:
                logger.warning("No signals for last week")
                return None
            
            # Основни статистики
            total_signals = len(weekly_signals)
            buy_signals = len([s for s in weekly_signals if s['type'] == 'BUY'])
            sell_signals = len([s for s in weekly_signals if s['type'] == 'SELL'])
            
            # Завършени trades (използвай status: WIN/LOSS/PENDING или outcome)
            completed = [
                s for s in weekly_signals 
                if s.get('status') in ['WIN', 'LOSS'] or s.get('outcome') in ['WIN', 'LOSS']
            ]
            active = [
                s for s in weekly_signals 
                if s.get('status') == 'PENDING' or (s.get('status') not in ['WIN', 'LOSS'] and s.get('outcome') not in ['WIN', 'LOSS'])
            ]
            
            # Точност
            if completed:
                wins = len([
                    s for s in completed 
                    if s.get('status') == 'WIN' or s.get('outcome') == 'WIN' or s.get('result') == 'WIN'
                ])
                losses = len([
                    s for s in completed 
                    if s.get('status') == 'LOSS' or s.get('outcome') == 'LOSS' or s.get('result') == 'LOSS'
                ])
                accuracy = (wins / len(completed) * 100)
                logger.info(f"🎯 Weekly accuracy: {accuracy:.1f}% (Wins: {wins}, Losses: {losses})")
            else:
                wins = losses = 0
                accuracy = 0
                logger.info("⏳ No completed trades for the week")
            
            # Успеваемост (използвай profit_loss_pct или profit_pct)
            total_profit = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in completed])
            
            if completed:
                profitable = [s for s in completed if s.get('profit_loss_pct', s.get('profit_pct', 0)) > 0]
                losing = [s for s in completed if s.get('profit_loss_pct', s.get('profit_pct', 0)) < 0]
                
                avg_win = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in profitable]) / len(profitable) if profitable else 0
                avg_loss = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in losing]) / len(losing) if losing else 0
                best_trade = max(completed, key=lambda x: x.get('profit_loss_pct', x.get('profit_pct', 0))) if completed else None
                worst_trade = min(completed, key=lambda x: x.get('profit_loss_pct', x.get('profit_pct', 0))) if completed else None
            else:
                avg_win = avg_loss = 0
                best_trade = worst_trade = None
            
            # Confidence
            avg_confidence = sum([s['confidence'] for s in weekly_signals]) / total_signals
            
            # TOP 3 СИМВОЛА по печалба
            symbols_profit = {}
            symbols = list(set([s['symbol'] for s in weekly_signals]))
            
            for symbol in symbols:
                symbol_signals = [s for s in weekly_signals if s['symbol'] == symbol]
                symbol_completed = [
                    s for s in symbol_signals 
                    if s.get('status') in ['WIN', 'LOSS'] or s.get('outcome') in ['WIN', 'LOSS']
                ]
                
                if symbol_completed:
                    symbol_profit = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in symbol_completed])
                    symbols_profit[symbol] = symbol_profit
            
            # Сортирай и вземи топ 3
            top_symbols = sorted(symbols_profit.items(), key=lambda x: x[1], reverse=True)[:3]
            top_symbols_str = ""
            for i, (symbol, profit) in enumerate(top_symbols, 1):
                top_symbols_str += f" {i}. {symbol}: {profit:+.2f}%\n"
            
            if not top_symbols_str:
                top_symbols_str = " Няма данни\n"
            
            # Дневен breakdown (по 7 дни)
            daily_breakdown = {}
            for i in range(7):
                day = last_monday + timedelta(days=i)
                day_name = ['Понеделник', 'Вторник', 'Сряда', 'Четвъртък', 'Петък', 'Събота', 'Неделя'][i]
                
                day_signals = [s for s in weekly_signals 
                             if datetime.fromisoformat(s['timestamp']).date() == day]
                day_completed = [
                    s for s in day_signals 
                    if s.get('status') in ['WIN', 'LOSS'] or s.get('outcome') in ['WIN', 'LOSS']
                ]
                
                if day_completed:
                    day_wins = len([
                        s for s in day_completed 
                        if s.get('status') == 'WIN' or s.get('outcome') == 'WIN' or s.get('result') == 'WIN'
                    ])
                    day_accuracy = (day_wins / len(day_completed) * 100)
                    day_profit = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in day_completed])
                else:
                    day_accuracy = 0
                    day_profit = 0
                
                daily_breakdown[day_name] = {
                    'date': day.isoformat(),
                    'total': len(day_signals),
                    'completed': len(day_completed),
                    'accuracy': day_accuracy,
                    'profit': day_profit
                }
            
            logger.info(f"✅ Weekly summary generated successfully")
            
            return {
                'period': 'Изминала седмица',
                'period_start': last_monday.strftime('%d.%m.%Y'),
                'period_end': last_sunday.strftime('%d.%m.%Y'),
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'pending': len(active),
                'wins': wins,
                'losses': losses,
                'accuracy': accuracy,
                'total_profit': total_profit,
                'avg_win': avg_win,
                'avg_loss': avg_loss,
                'avg_confidence': avg_confidence,
                'best_trade': best_trade,
                'worst_trade': worst_trade,
                'daily_breakdown': daily_breakdown,
                'top_symbols_str': top_symbols_str
            }
            
        except Exception as e:
            logger.error(f"❌ Weekly summary error: {e}", exc_info=True)
            return None
    
    def get_monthly_summary(self):
        """Месечен обобщен отчет за ИЗМИНАЛИЯ МЕСЕЦ (1-во - последно число)"""
        try:
            logger.info("📆 Starting monthly summary generation...")
            
            # Зареди данни от ml_journal.json първо, резервно bot_stats.json
            stats = None
            
            # Try ml_journal.json first (preferred)
            if os.path.exists(self.journal_path):
                try:
                    logger.debug(f"Loading data from ml_journal.json: {self.journal_path}")
                    with open(self.journal_path, 'r') as f:
                        journal = json.load(f)
                    stats = {'signals': journal.get('trades', [])}
                    logger.info(f"✅ Loaded {len(stats['signals'])} trades from ml_journal.json")
                except Exception as e:
                    logger.warning(f"⚠️ Failed to load ml_journal.json: {e}")
            
            # Fallback to bot_stats.json
            if not stats and os.path.exists(self.stats_path):
                try:
                    logger.debug(f"Fallback: Loading data from bot_stats.json: {self.stats_path}")
                    with open(self.stats_path, 'r') as f:
                        stats = json.load(f)
                    logger.info(f"✅ Loaded {len(stats.get('signals', []))} signals from bot_stats.json")
                except Exception as e:
                    logger.error(f"❌ Failed to load bot_stats.json: {e}")
            
            if not stats:
                logger.warning("⚠️ No data source available for monthly summary")
                return None
            
            # Изчисли ИЗМИНАЛИЯ МЕСЕЦ (1-во - последно число)
            today = datetime.now().date()
            first_day_this_month = today.replace(day=1)
            last_day_prev_month = first_day_this_month - timedelta(days=1)
            first_day_prev_month = last_day_prev_month.replace(day=1)
            
            month_name = first_day_prev_month.strftime('%B %Y')
            
            logger.info(f"📆 Monthly period: {first_day_prev_month} - {last_day_prev_month}")
            
            monthly_signals = [
                s for s in stats.get('signals', [])
                if first_day_prev_month <= datetime.fromisoformat(s['timestamp']).date() <= last_day_prev_month
            ]
            
            logger.info(f"Found {len(monthly_signals)} signals for the month")
            
            if not monthly_signals:
                logger.warning("No signals for last month")
                return None
            
            # Основни статистики
            total_signals = len(monthly_signals)
            buy_signals = len([s for s in monthly_signals if s['type'] == 'BUY'])
            sell_signals = len([s for s in monthly_signals if s['type'] == 'SELL'])
            
            # Завършени trades (използвай status: WIN/LOSS/PENDING или outcome)
            completed = [
                s for s in monthly_signals 
                if s.get('status') in ['WIN', 'LOSS'] or s.get('outcome') in ['WIN', 'LOSS']
            ]
            active = [
                s for s in monthly_signals 
                if s.get('status') == 'PENDING' or (s.get('status') not in ['WIN', 'LOSS'] and s.get('outcome') not in ['WIN', 'LOSS'])
            ]
            
            # Точност
            if completed:
                wins = len([
                    s for s in completed 
                    if s.get('status') == 'WIN' or s.get('outcome') == 'WIN' or s.get('result') == 'WIN'
                ])
                losses = len([
                    s for s in completed 
                    if s.get('status') == 'LOSS' or s.get('outcome') == 'LOSS' or s.get('result') == 'LOSS'
                ])
                accuracy = (wins / len(completed) * 100)
                logger.info(f"🎯 Monthly accuracy: {accuracy:.1f}% (Wins: {wins}, Losses: {losses})")
            else:
                wins = losses = 0
                accuracy = 0
                logger.info("⏳ No completed trades for the month")
            
            # Успеваемост (използвай profit_loss_pct или profit_pct)
            total_profit = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in completed])
            
            if completed:
                profitable = [s for s in completed if s.get('profit_loss_pct', s.get('profit_pct', 0)) > 0]
                losing = [s for s in completed if s.get('profit_loss_pct', s.get('profit_pct', 0)) < 0]
                
                avg_win = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in profitable]) / len(profitable) if profitable else 0
                avg_loss = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in losing]) / len(losing) if losing else 0
                best_trade = max(completed, key=lambda x: x.get('profit_loss_pct', x.get('profit_pct', 0))) if completed else None
                worst_trade = min(completed, key=lambda x: x.get('profit_loss_pct', x.get('profit_pct', 0))) if completed else None
                profit_factor = abs(avg_win / avg_loss) if avg_loss != 0 else 0
            else:
                avg_win = avg_loss = profit_factor = 0
                best_trade = worst_trade = None
            
            # Confidence
            avg_confidence = sum([s['confidence'] for s in monthly_signals]) / total_signals
            
            # TOP 3 СИМВОЛА по печалба
            symbols_profit = {}
            symbols = list(set([s['symbol'] for s in monthly_signals]))
            
            for symbol in symbols:
                symbol_signals = [s for s in monthly_signals if s['symbol'] == symbol]
                symbol_completed = [
                    s for s in symbol_signals 
                    if s.get('status') in ['WIN', 'LOSS'] or s.get('outcome') in ['WIN', 'LOSS']
                ]
                
                if symbol_completed:
                    symbol_profit = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in symbol_completed])
                    symbols_profit[symbol] = symbol_profit
            
            # Сортирай и вземи топ 3
            top_symbols = sorted(symbols_profit.items(), key=lambda x: x[1], reverse=True)[:3]
            top_symbols_str = ""
            for i, (symbol, profit) in enumerate(top_symbols, 1):
                top_symbols_str += f" {i}. {symbol}: {profit:+.2f}%\n"
            
            if not top_symbols_str:
                top_symbols_str = " Няма данни\n"
            
            # Седмичен breakdown (разбий месеца на седмици)
            weekly_breakdown = {}
            current_week_start = first_day_prev_month
            week_num = 1
            
            while current_week_start <= last_day_prev_month:
                # Изчисли края на седмицата (неделя или край на месеца)
                current_week_end = min(
                    current_week_start + timedelta(days=6),
                    last_day_prev_month
                )
                
                week_signals = [
                    s for s in monthly_signals 
                    if current_week_start <= datetime.fromisoformat(s['timestamp']).date() <= current_week_end
                ]
                week_completed = [
                    s for s in week_signals 
                    if s.get('status') in ['WIN', 'LOSS'] or s.get('outcome') in ['WIN', 'LOSS']
                ]
                
                if week_completed:
                    week_wins = len([
                        s for s in week_completed 
                        if s.get('status') == 'WIN' or s.get('outcome') == 'WIN' or s.get('result') == 'WIN'
                    ])
                    week_accuracy = (week_wins / len(week_completed) * 100)
                    week_profit = sum([s.get('profit_loss_pct', s.get('profit_pct', 0)) for s in week_completed])
                else:
                    week_accuracy = 0
                    week_profit = 0
                
                weekly_breakdown[f'Седмица {week_num}'] = {
                    'period': f"{current_week_start.strftime('%d.%m')} - {current_week_end.strftime('%d.%m')}",
                    'total': len(week_signals),
                    'completed': len(week_completed),
                    'accuracy': week_accuracy,
                    'profit': week_profit
                }
                
                current_week_start = current_week_end + timedelta(days=1)
                week_num += 1
            
            logger.info(f"✅ Monthly summary generated successfully")
            
            return {
                'period': 'Изминал месец',
                'month_name': month_name,
                'period_start': first_day_prev_month.strftime('%d.%m.%Y'),
                'period_end': last_day_prev_month.strftime('%d.%m.%Y'),
                'total_signals': total_signals,
                'buy_signals': buy_signals,
                'sell_signals': sell_signals,
                'pending': len(active),
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
                'weekly_breakdown': weekly_breakdown,
                'top_symbols_str': top_symbols_str
            }
            
        except Exception as e:
            logger.error(f"❌ Monthly summary error: {e}", exc_info=True)
            return None
    
    def format_weekly_message(self, summary):
        """Форматира седмичния отчет за Telegram"""
        if not summary:
            return "⚠️ Няма данни за седмичен отчет"
        
        msg = f"""📅 <b>СЕДМИЧЕН ОТЧЕТ</b>
📆 {summary['period_start']} - {summary['period_end']}

━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ОБЩА СТАТИСТИКА:</b>
🔢 Общо сигнали: {summary['total_signals']}
🟢 КУПУВА: {summary['buy_signals']}
🔴 ПРОДАВА: {summary['sell_signals']}
✅ Успешни: {summary['wins']} ({summary['accuracy']:.1f}%)
❌ Неуспешни: {summary['losses']}
⏳ В изчакване: {summary['pending']}

💰 <b>ЕФЕКТИВНОСТ:</b>
📈 Обща печалба/загуба: <b>{summary['total_profit']:+.2f}%</b>
💎 Среден печеливш trade: <b>+{summary['avg_win']:.2f}%</b>
💔 Среден губещ trade: <b>{summary['avg_loss']:.2f}%</b>
💪 Средна увереност: {summary['avg_confidence']:.1f}%

💰 <b>ТОП СИМВОЛИ:</b>
{summary['top_symbols_str']}

━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Генериран: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        return msg
    
    def format_monthly_message(self, summary):
        """Форматира месечен отчет за Telegram"""
        if not summary:
            return "⚠️ Няма данни за месечен отчет"
        
        # Weekly breakdown formatting
        weekly_str = ""
        if summary.get('weekly_breakdown'):
            for week_name, week_data in summary['weekly_breakdown'].items():
                weekly_str += f" • {week_name} ({week_data['period']}): {week_data['completed']} trades, {week_data['profit']:+.2f}%\n"
        
        msg = f"""📆 <b>МЕСЕЧЕН ОТЧЕТ</b>
🗓️ {summary['month_name']}
📅 {summary['period_start']} - {summary['period_end']}

━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ОБЩА СТАТИСТИКА:</b>
🔢 Общо сигнали: {summary['total_signals']}
🟢 КУПУВА: {summary['buy_signals']}
🔴 ПРОДАВА: {summary['sell_signals']}
✅ Успешни: {summary['wins']} ({summary['accuracy']:.1f}%)
❌ Неуспешни: {summary['losses']}
⏳ В изчакване: {summary['pending']}

💰 <b>ЕФЕКТИВНОСТ:</b>
📈 Обща печалба/загуба: <b>{summary['total_profit']:+.2f}%</b>
💎 Среден печеливш trade: <b>+{summary['avg_win']:.2f}%</b>
💔 Среден губещ trade: <b>{summary['avg_loss']:.2f}%</b>
⚖️ Фактор печалба: <b>{summary['profit_factor']:.2f}</b>
💪 Средна увереност: {summary['avg_confidence']:.1f}%

📊 <b>ПО СЕДМИЦИ:</b>
{weekly_str}

💰 <b>ТОП 3 СИМВОЛА:</b>
{summary['top_symbols_str']}

━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Генериран: {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        return msg


# Global report instance
report_engine = DailyReportEngine()
