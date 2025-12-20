"""
Админ модул за Crypto Signal Bot
Автоматични отчети и статистика
"""

import json
import os
from datetime import datetime, timezone, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)

ADMIN_DIR = "/workspaces/Crypto-signal-bot/admin"
ADMIN_PASSWORD_FILE = f"{ADMIN_DIR}/admin_password.json"
REPORTS_DIR = f"{ADMIN_DIR}/reports"
DAILY_REPORTS_DIR = f"{REPORTS_DIR}/daily"
WEEKLY_REPORTS_DIR = f"{REPORTS_DIR}/weekly"
MONTHLY_REPORTS_DIR = f"{REPORTS_DIR}/monthly"

# Създай необходимите директории
for dir_path in [ADMIN_DIR, REPORTS_DIR, DAILY_REPORTS_DIR, WEEKLY_REPORTS_DIR, MONTHLY_REPORTS_DIR]:
    os.makedirs(dir_path, exist_ok=True)


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
    stats_file = "/workspaces/Crypto-signal-bot/bot_stats.json"
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
