"""
Тестване на новите функции за отчети
"""

import json
import os
from datetime import datetime, timedelta
from daily_reports import DailyReportEngine

# Auto-detect base path
if os.path.exists('/root/Crypto-signal-bot'):
    BASE_PATH = '/root/Crypto-signal-bot'
elif os.path.exists('/workspaces/Crypto-signal-bot'):
    BASE_PATH = '/workspaces/Crypto-signal-bot'
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

# Създай тестови данни
def create_test_signals():
    stats = {
        "total_signals": 0,
        "by_symbol": {},
        "by_timeframe": {},
        "by_confidence": {},
        "signals": []
    }
    
    # Създай 20 тестови сигнала за последните 7 дни
    symbols = ['BTCUSDT', 'ETHUSDT', 'XRPUSDT', 'SOLUSDT']
    
    # Използвай българско време
    import pytz
    bg_tz = pytz.timezone('Europe/Sofia')
    now_bg = datetime.now(bg_tz)
    
    for i in range(20):
        days_ago = i % 7
        signal_time = now_bg - timedelta(days=days_ago, hours=i)
        
        symbol = symbols[i % len(symbols)]
        signal_type = 'BUY' if i % 2 == 0 else 'SELL'
        confidence = 65 + (i % 30)
        
        # Симулирай entry и exit цени
        entry_price = 50000 + (i * 100)
        
        # Симулирай резултати - 70% печеливши
        if i % 10 < 7:  # 70% печеливши
            result = 'WIN'
            profit_pct = 2.5 + (i % 5) * 0.5
            exit_price = entry_price * (1 + profit_pct / 100)
        else:
            result = 'LOSS'
            profit_pct = -(1.0 + (i % 3) * 0.3)
            exit_price = entry_price * (1 + profit_pct / 100)
        
        signal = {
            'id': i + 1,
            'symbol': symbol,
            'timeframe': '4h',
            'type': signal_type,
            'confidence': confidence,
            'timestamp': signal_time.isoformat(),
            'entry_price': entry_price,
            'tp_price': entry_price * 1.03,
            'sl_price': entry_price * 0.98,
            'status': 'COMPLETED',
            'result': result,
            'exit_price': exit_price,
            'profit_pct': profit_pct,
            'exit_timestamp': (signal_time + timedelta(hours=12)).isoformat()
        }
        
        stats['signals'].append(signal)
    
    # Добави няколко активни сигнала
    for i in range(3):
        signal_time = datetime.now() - timedelta(hours=i)
        
        signal = {
            'id': 21 + i,
            'symbol': 'BTCUSDT',
            'timeframe': '1h',
            'type': 'BUY',
            'confidence': 75,
            'timestamp': signal_time.isoformat(),
            'entry_price': 51000,
            'tp_price': 51000 * 1.02,
            'sl_price': 51000 * 0.99,
            'status': 'ACTIVE',
            'result': None,
            'exit_price': None,
            'profit_pct': None,
            'exit_timestamp': None
        }
        
        stats['signals'].append(signal)
    
    # Запази
    with open(f'{BASE_PATH}/bot_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    print("✅ Тестови данни създадени!")
    print(f"   Общо сигнали: {len(stats['signals'])}")
    print(f"   Завършени: {len([s for s in stats['signals'] if s['status'] == 'COMPLETED'])}")
    print(f"   Активни: {len([s for s in stats['signals'] if s['status'] == 'ACTIVE'])}")


def test_daily_report():
    print("\n📊 ТЕСТ НА ДНЕВЕН ОТЧЕТ:")
    print("=" * 50)
    
    engine = DailyReportEngine()
    try:
        report = engine.generate_daily_report()
        
        if report:
            print("✅ Отчет генериран успешно!")
            print(f"\nОсновни данни:")
            print(f"  - Общо сигнали: {report['total_signals']}")
            print(f"  - Завършени: {report['completed_signals']}")
            print(f"  - Точност: {report['accuracy']:.1f}%")
            print(f"  - Общ profit: {report['total_profit']:+.2f}%")
            
            # Форматирано съобщение
            print("\n" + "=" * 50)
            print("ФОРМАТИРАНО СЪОБЩЕНИЕ:")
            print("=" * 50)
            message = engine.format_report_message(report)
            print(message)
        else:
            print("❌ Грешка при генериране на отчет")
    except Exception as e:
        print(f"❌ Грешка при генериране на отчет: {e}")
        import traceback
        traceback.print_exc()


def test_weekly_report():
    print("\n📊 ТЕСТ НА СЕДМИЧЕН ОТЧЕТ:")
    print("=" * 50)
    
    engine = DailyReportEngine()
    summary = engine.get_weekly_summary()
    
    if summary:
        print("✅ Седмичен отчет генериран успешно!")
        print(f"\nОсновни данни:")
        print(f"  - Общо сигнали: {summary['total_signals']}")
        print(f"  - Завършени: {summary['completed_signals']}")
        print(f"  - Точност: {summary['accuracy']:.1f}%")
        print(f"  - Общ profit: {summary['total_profit']:+.2f}%")
        
        if summary.get('daily_breakdown'):
            print(f"\n  Дневен breakdown:")
            for date, data in sorted(summary['daily_breakdown'].items(), reverse=True)[:5]:
                if data['completed'] > 0:
                    print(f"    {date}: {data['accuracy']:.0f}% acc, {data['profit']:+.1f}% profit")
    else:
        print("❌ Грешка при генериране на седмичен отчет")


def test_monthly_report():
    print("\n📊 ТЕСТ НА МЕСЕЧЕН ОТЧЕТ:")
    print("=" * 50)
    
    engine = DailyReportEngine()
    try:
        summary = engine.get_monthly_summary()
        
        if summary:
            print("✅ Месечен отчет генериран успешно!")
            print(f"\nОсновни данни:")
            print(f"  - Общо сигнали: {summary['total_signals']}")
            print(f"  - Завършени: {summary['completed_signals']}")
            print(f"  - Точност: {summary['accuracy']:.1f}%")
            print(f"  - Общ profit: {summary['total_profit']:+.2f}%")
            print(f"  - Profit Factor: {summary.get('profit_factor', 0):.2f}")
            
            if summary.get('symbols_stats'):
                print(f"\n  Статистика по валути:")
                for symbol, stats in summary['symbols_stats'].items():
                    if stats['completed'] > 0:
                        print(f"    {symbol}: {stats['accuracy']:.0f}% acc, {stats['profit']:+.2f}% profit")
        else:
            print("❌ Грешка при генериране на месечен отчет")
    except Exception as e:
        print(f"❌ Грешка при генериране на месечен отчет: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("🧪 ТЕСТВАНЕ НА REPORTS СИСТЕМА")
    print("=" * 50)
    
    # Създай тестови данни
    create_test_signals()
    
    # Тествай отчетите
    test_daily_report()
    test_weekly_report()
    test_monthly_report()
    
    print("\n" + "=" * 50)
    print("✅ ВСИЧКИ ТЕСТОВЕ ЗАВЪРШЕНИ!")
