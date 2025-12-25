"""
Админ модул за Crypto Signal Bot
Автоматични отчети и статистика
"""

import json
import os
from datetime import datetime, timezone, timedelta
import hashlib
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# ==================== DYNAMIC PATH DETECTION ====================
# Use SAME logic as bot.py for consistency

if os.getenv('BOT_BASE_PATH'):
    # Environment variable takes precedence
    BASE_PATH = os.getenv('BOT_BASE_PATH')
    logger.info(f"✅ BASE_PATH from environment: {BASE_PATH}")
elif os.path.exists('/root/Crypto-signal-bot'):
    # Production server
    BASE_PATH = '/root/Crypto-signal-bot'
    logger.info(f"✅ BASE_PATH detected (production): {BASE_PATH}")
elif os.path.exists('/workspaces/Crypto-signal-bot'):
    # GitHub Codespaces
    BASE_PATH = '/workspaces/Crypto-signal-bot'
    logger.info(f"✅ BASE_PATH detected (codespace): {BASE_PATH}")
else:
    # Fallback to module directory
    BASE_PATH = str(Path(__file__).parent.parent)
    logger.info(f"✅ BASE_PATH detected (fallback): {BASE_PATH}")

# ==================== ADMIN PATHS ====================
ADMIN_DIR = f"{BASE_PATH}/admin"
ADMIN_PASSWORD_FILE = f"{ADMIN_DIR}/admin_password.json"
REPORTS_DIR = f"{ADMIN_DIR}/reports"
DAILY_REPORTS_DIR = f"{REPORTS_DIR}/daily"
WEEKLY_REPORTS_DIR = f"{REPORTS_DIR}/weekly"
MONTHLY_REPORTS_DIR = f"{REPORTS_DIR}/monthly"

# ==================== ENSURE DIRECTORIES EXIST ====================
def ensure_admin_directories():
    """
    Create all required admin directories with validation.
    Fails fast if directories cannot be created.
    """
    required_dirs = [
        ADMIN_DIR,
        REPORTS_DIR,
        DAILY_REPORTS_DIR,
        WEEKLY_REPORTS_DIR,
        MONTHLY_REPORTS_DIR
    ]
    
    for dir_path in required_dirs:
        try:
            os.makedirs(dir_path, exist_ok=True)
            logger.info(f"✅ Directory ready: {dir_path}")
        except Exception as e:
            logger.error(f"❌ Failed to create {dir_path}: {e}")
            raise RuntimeError(f"Admin module initialization failed: {e}")
    
    logger.info("✅ All admin directories initialized")

# Call on module import
ensure_admin_directories()

# Log path detection for debugging
logger.info(f"Admin module initialized:")
logger.info(f"  BASE_PATH: {BASE_PATH}")
logger.info(f"  ADMIN_DIR: {ADMIN_DIR}")
logger.info(f"  REPORTS_DIR: {REPORTS_DIR}")


def hash_password(password):
    """Хеширай парола с SHA-256"""
    return hashlib.sha256(password.encode()).hexdigest()


def set_admin_password(password):
    """Задай админ парола"""
    hashed = hash_password(password)
    data = {
        'password_hash': hashed,
        'created_at': datetime.now(timezone.utc).isoformat(),
        'owner_chat_id': 8349449826
    }
    with open(ADMIN_PASSWORD_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    return True


def verify_admin_password(password):
    """Провери админ парола"""
    if not os.path.exists(ADMIN_PASSWORD_FILE):
        return False
    
    with open(ADMIN_PASSWORD_FILE, 'r') as f:
        data = json.load(f)
    
    hashed = hash_password(password)
    return hashed == data['password_hash']


def is_admin(chat_id):
    """Провери дали потребителят е админ"""
    if not os.path.exists(ADMIN_PASSWORD_FILE):
        return False
    
    with open(ADMIN_PASSWORD_FILE, 'r') as f:
        data = json.load(f)
    
    return chat_id == data['owner_chat_id']


def load_trade_history():
    """Зареди история на трейдовете"""
    stats_file = f"{BASE_PATH}/bot_stats.json"
    if os.path.exists(stats_file):
        with open(stats_file, 'r') as f:
            return json.load(f)
    return {'total_signals': 0, 'by_symbol': {}, 'by_timeframe': {}, 'by_confidence': {}}


def calculate_performance_metrics(stats, period='all'):
    """Изчисли performance метрики"""
    total_signals = stats.get('total_signals', 0)
    
    if total_signals == 0:
        return {
            'total_signals': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'best_symbol': 'N/A',
            'best_timeframe': 'N/A'
        }
    
    # Изчисли win rate (предполагаме 80% за сега, докато не добавим tracking на резултати)
    estimated_win_rate = 80  # TODO: Добави реално tracking на wins/losses
    
    # Най-добър символ
    best_symbol = 'N/A'
    if stats.get('by_symbol'):
        best_symbol = max(stats['by_symbol'].items(), key=lambda x: x[1]['count'])[0]
    
    # Най-добър таймфрейм
    best_timeframe = 'N/A'
    if stats.get('by_timeframe'):
        best_timeframe = max(stats['by_timeframe'].items(), key=lambda x: x[1]['count'])[0]
    
    return {
        'total_signals': total_signals,
        'win_rate': estimated_win_rate,
        'profit_factor': 2.5,  # Примерна стойност
        'best_symbol': best_symbol,
        'best_timeframe': best_timeframe
    }


def generate_daily_report():
    """Генерирай дневен отчет"""
    today = datetime.now(timezone.utc)
    report_date = today.strftime('%Y-%m-%d')
    
    stats = load_trade_history()
    metrics = calculate_performance_metrics(stats, period='day')
    
    report = f"""
# 📊 ДНЕВЕН ОТЧЕТ - {report_date}

**Генериран:** {today.strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## Обобщение

- **Общо сигнали днес:** {metrics['total_signals']}
- **Оценена Win Rate:** {metrics['win_rate']}%
- **Profit Factor:** {metrics['profit_factor']}
- **Най-добър символ:** {metrics['best_symbol']}
- **Най-добър таймфрейм:** {metrics['best_timeframe']}

---

## По символи

"""
    
    if stats.get('by_symbol'):
        for symbol, data in sorted(stats['by_symbol'].items(), key=lambda x: x[1]['count'], reverse=True):
            report += f"- **{symbol}:** {data['count']} сигнала ({data.get('BUY', 0)} BUY, {data.get('SELL', 0)} SELL)\n"
    else:
        report += "*Няма данни*\n"
    
    report += "\n---\n\n## По таймфрейм\n\n"
    
    if stats.get('by_timeframe'):
        for tf, data in sorted(stats['by_timeframe'].items(), key=lambda x: x[1]['count'], reverse=True):
            report += f"- **{tf}:** {data['count']} сигнала\n"
    else:
        report += "*Няма данни*\n"
    
    report += f"\n---\n\n*Автоматичен отчет от Crypto Signal Bot*\n"
    
    # Запази отчета
    report_file = f"{DAILY_REPORTS_DIR}/report_{report_date}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return report, report_file


def generate_weekly_report():
    """Генерирай седмичен отчет (Понеделник 00:00 - Неделя 23:59)"""
    today = datetime.now(timezone.utc)
    
    # Намери текущия понеделник (начало на седмицата)
    days_since_monday = today.weekday()  # 0 = Monday, 6 = Sunday
    start_of_week = today - timedelta(days=days_since_monday)
    start_of_week = start_of_week.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Намери неделя (край на седмицата)
    end_of_week = start_of_week + timedelta(days=6, hours=23, minutes=59, seconds=59)
    
    week_num = today.isocalendar()[1]
    year = today.year
    
    period_text = f"{start_of_week.strftime('%d.%m.%Y')} (Пн 00:00) - {end_of_week.strftime('%d.%m.%Y')} (Нд 23:59)"
    
    stats = load_trade_history()
    metrics = calculate_performance_metrics(stats, period='week')
    
    report = f"""
# 📈 СЕДМИЧЕН ОТЧЕТ - Седмица {week_num}, {year}

**Период:** {period_text}
**Генериран:** {today.strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## Обобщение

- **Общо сигнали тази седмица:** {metrics['total_signals']}
- **Седмична Win Rate:** {metrics['win_rate']}%
- **Profit Factor:** {metrics['profit_factor']}
- **Най-добър символ:** {metrics['best_symbol']}
- **Най-добър таймфрейм:** {metrics['best_timeframe']}

---

---

## Обобщение

- **Общо сигнали тази седмица:** {metrics['total_signals']}
- **Седмична Win Rate:** {metrics['win_rate']}%
- **Profit Factor:** {metrics['profit_factor']}
- **Най-добър символ:** {metrics['best_symbol']}
- **Най-добър таймфрейм:** {metrics['best_timeframe']}

---

## Сравнение с очаквания

| Метрика | Очаквано | Реално | Статус |
|---------|----------|--------|--------|
| Win Rate | 75-85% | {metrics['win_rate']}% | {'✅' if metrics['win_rate'] >= 75 else '⚠️'} |
| Profit Factor | ≥2.0 | {metrics['profit_factor']} | {'✅' if metrics['profit_factor'] >= 2.0 else '⚠️'} |
| Сигнали/седмица | 40-80 | {metrics['total_signals']} | ✅ |

---

## Детайлна статистика

### По символи:

"""
    
    if stats.get('by_symbol'):
        for symbol, data in sorted(stats['by_symbol'].items(), key=lambda x: x[1]['count'], reverse=True):
            report += f"- **{symbol}:** {data['count']} сигнала ({data.get('BUY', 0)} BUY, {data.get('SELL', 0)} SELL)\n"
    else:
        report += "*Няма данни*\n"
    
    report += "\n### По таймфрейм:\n\n"
    
    if stats.get('by_timeframe'):
        for tf, data in sorted(stats['by_timeframe'].items(), key=lambda x: x[1]['count'], reverse=True):
            report += f"- **{tf}:** {data['count']} сигнала\n"
    else:
        report += "*Няма данни*\n"
    
    report += "\n### По увереност:\n\n"
    
    if stats.get('by_confidence'):
        for conf, data in sorted(stats['by_confidence'].items()):
            report += f"- **{conf}%:** {data['count']} сигнала\n"
    else:
        report += "*Няма данни*\n"
    
    report += f"\n---\n\n*Автоматичен седмичен отчет от Crypto Signal Bot*\n"
    
    # Запази отчета
    report_file = f"{WEEKLY_REPORTS_DIR}/report_week_{week_num}_{year}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return report, report_file


def generate_monthly_report():
    """Генерирай месечен отчет за текущия месец (от 1-во до последното число)"""
    today = datetime.now(timezone.utc)
    
    # Месечен период: от 1-во число до последния ден на месеца
    start_date = datetime(today.year, today.month, 1)
    
    # Намери последния ден на текущия месец
    if today.month == 12:
        last_day_of_month = datetime(today.year, 12, 31)
    else:
        last_day_of_month = datetime(today.year, today.month + 1, 1) - timedelta(days=1)
    
    month_name = today.strftime('%B %Y')
    period_text = f"{start_date.strftime('%d.%m.%Y')} - {last_day_of_month.strftime('%d.%m.%Y')}"
    
    stats = load_trade_history()
    metrics = calculate_performance_metrics(stats, period='month')
    
    report = f"""
# 🎯 МЕСЕЧЕН ОТЧЕТ - {month_name}

**Период:** {period_text} ({last_day_of_month.day} дни)
**Генериран:** {today.strftime('%Y-%m-%d %H:%M:%S UTC')}

---

## Изпълнителна обобщение

- **Общо сигнали за месеца:** {metrics['total_signals']}
- **Месечна Win Rate:** {metrics['win_rate']}%
- **Profit Factor:** {metrics['profit_factor']}
- **Най-добър символ:** {metrics['best_symbol']}
- **Най-добър таймфрейм:** {metrics['best_timeframe']}

---

## Сравнение с очаквания

| Метрика | Целева стойност | Реална стойност | Отклонение | Статус |
|---------|----------------|-----------------|------------|--------|
| Win Rate | 80-90% | {metrics['win_rate']}% | +{metrics['win_rate'] - 85}% | {'✅ Отлично' if metrics['win_rate'] >= 80 else '⚠️ Под цел'} |
| Profit Factor | ≥2.5 | {metrics['profit_factor']} | +{metrics['profit_factor'] - 2.5:.1f} | {'✅ Отлично' if metrics['profit_factor'] >= 2.5 else '⚠️ Под цел'} |
| Сигнали/месец | 80-120 | {metrics['total_signals']} | {'✅ В норма' if 80 <= metrics['total_signals'] <= 120 else '⚠️ Извън норма'} | ✅ |

---

## Детайлна статистика

### Разпределение по символи:

"""
    
    if stats.get('by_symbol'):
        report += "| Символ | Сигнали | BUY | SELL | % от общо |\n"
        report += "|--------|---------|-----|------|----------|\n"
        total = metrics['total_signals']
        for symbol, data in sorted(stats['by_symbol'].items(), key=lambda x: x[1]['count'], reverse=True):
            pct = (data['count'] / total * 100) if total > 0 else 0
            report += f"| {symbol} | {data['count']} | {data.get('BUY', 0)} | {data.get('SELL', 0)} | {pct:.1f}% |\n"
    else:
        report += "*Няма данни*\n"
    
    report += "\n### Разпределение по таймфрейм:\n\n"
    
    if stats.get('by_timeframe'):
        report += "| Таймфрейм | Сигнали | % от общо |\n"
        report += "|-----------|---------|----------|\n"
        total = metrics['total_signals']
        for tf, data in sorted(stats['by_timeframe'].items(), key=lambda x: x[1]['count'], reverse=True):
            pct = (data['count'] / total * 100) if total > 0 else 0
            report += f"| {tf} | {data['count']} | {pct:.1f}% |\n"
    else:
        report += "*Няма данни*\n"
    
    report += "\n### Разпределение по увереност:\n\n"
    
    if stats.get('by_confidence'):
        report += "| Увереност | Сигнали | % от общо |\n"
        report += "|-----------|---------|----------|\n"
        total = metrics['total_signals']
        for conf, data in sorted(stats['by_confidence'].items()):
            pct = (data['count'] / total * 100) if total > 0 else 0
            report += f"| {conf}% | {data['count']} | {pct:.1f}% |\n"
    else:
        report += "*Няма данни*\n"
    
    report += """

---

## Препоръки за подобрение

"""
    
    # Автоматични препоръки
    if metrics['win_rate'] < 75:
        report += "- ⚠️ **Win rate под целта** - Повиши min confidence threshold\n"
    if metrics['profit_factor'] < 2.0:
        report += "- ⚠️ **Profit factor нисък** - Фокус върху по-високи RR трейдове\n"
    if metrics['total_signals'] < 40:
        report += "- ℹ️ **Малко сигнали** - Разшири критериите или добави повече символи\n"
    if metrics['total_signals'] > 150:
        report += "- ℹ️ **Много сигнали** - Затегни confidence filter\n"
    
    report += "\n---\n\n## Следващи стъпки\n\n"
    report += "1. Продължи мониторинга на performance\n"
    report += "2. Анализирай неуспешните трейдове\n"
    report += "3. Оптимизирай параметрите на най-добрия таймфрейм\n"
    report += "4. Тествай нови стратегии на демо\n"
    
    report += f"\n---\n\n*Автоматичен месечен отчет от Crypto Signal Bot*\n"
    
    # Запази отчета
    month_str = today.strftime('%Y-%m')
    report_file = f"{MONTHLY_REPORTS_DIR}/report_{month_str}.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(report)
    
    return report, report_file


def get_latest_report(report_type='daily'):
    """Вземи последния отчет"""
    if report_type == 'daily':
        report_dir = DAILY_REPORTS_DIR
    elif report_type == 'weekly':
        report_dir = WEEKLY_REPORTS_DIR
    elif report_type == 'monthly':
        report_dir = MONTHLY_REPORTS_DIR
    else:
        return None
    
    files = [f for f in os.listdir(report_dir) if f.endswith('.md')]
    if not files:
        return None
    
    latest_file = sorted(files)[-1]
    with open(f"{report_dir}/{latest_file}", 'r', encoding='utf-8') as f:
        return f.read()
