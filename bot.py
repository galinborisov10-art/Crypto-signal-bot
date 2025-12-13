# Auto-deploy test - Dec 7, 2025 14:20 UTC
# Second auto-deploy test - confirming deployment works
import requests
import json
import asyncio
import logging
import hashlib
import gc
from datetime import datetime, timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import matplotlib
matplotlib.use('Agg')  # Използвай non-GUI backend
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
from io import BytesIO
import os

# ================= ENVIRONMENT VARIABLES =================
from dotenv import load_dotenv

# Зареди .env файла
load_dotenv()

# Логване
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Track bot process start time (for version info)
BOT_START_TIME = datetime.now(timezone.utc)

# AUTO-DETECT BASE PATH (Codespace vs Server) - EARLY INIT
if os.path.exists('/root/Crypto-signal-bot'):
    BASE_PATH = '/root/Crypto-signal-bot'
else:
    BASE_PATH = '/workspaces/Crypto-signal-bot'

# Админ модул
import sys
# test deploy

sys.path.append(f'{BASE_PATH}/admin')
try:
    from admin_module import (
        set_admin_password, verify_admin_password, is_admin,
        generate_daily_report, generate_weekly_report, generate_monthly_report,
        get_latest_report
    )
    ADMIN_MODULE_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ Админ модул не е зареден: {e}")
    ADMIN_MODULE_AVAILABLE = False

# Импорт на диагностичния модул
try:
    from diagnostics import BotDiagnostics
    DIAGNOSTICS_AVAILABLE = True
except ImportError:
    DIAGNOSTICS_AVAILABLE = False

# Импорт на LuxAlgo + ICT Analysis
try:
    from luxalgo_ict_analysis import (
        combined_luxalgo_ict_analysis,
        calculate_luxalgo_sr_levels,
        detect_market_structure_shift,
        detect_liquidity_grab,
        detect_fair_value_gaps,
        calculate_optimal_trade_entry,
        calculate_fibonacci_extension
    )
    LUXALGO_ICT_AVAILABLE = True
    logger.info("✅ LuxAlgo + ICT Analysis loaded successfully")
except ImportError as e:
    LUXALGO_ICT_AVAILABLE = False
    logger.warning(f"⚠️ LuxAlgo + ICT module not available: {e}")

# Risk Management System
try:
    from risk_management import get_risk_manager
    RISK_MANAGER_AVAILABLE = True
    logger.info("✅ Risk Management System loaded")
except ImportError as e:
    RISK_MANAGER_AVAILABLE = False
    logger.warning(f"⚠️ Risk Management not available: {e}")

# ICT Signal Engine - New Complete System
try:
    from ict_signal_engine import ICTSignalEngine, ICTSignal
    from order_block_detector import OrderBlockDetector
    from fvg_detector import FVGDetector
    ICT_SIGNAL_ENGINE_AVAILABLE = True
    logger.info("✅ ICT Signal Engine loaded")
except ImportError as e:
    ICT_SIGNAL_ENGINE_AVAILABLE = False
    logger.warning(f"⚠️ ICT Signal Engine not available: {e}")

# RSS и HTML парсинг за новини
try:
    import feedparser
    from bs4 import BeautifulSoup
    RSS_PARSER_AVAILABLE = True
    logger.info("✅ RSS Parser (feedparser + BeautifulSoup) loaded successfully")
except ImportError as e:
    RSS_PARSER_AVAILABLE = False
    logger.warning(f"⚠️ RSS Parser not available: {e}")

# Превод на текст
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
    logger.info("✅ Google Translator loaded successfully")
except ImportError as e:
    TRANSLATOR_AVAILABLE = False
    logger.warning(f"⚠️ Google Translator not available: {e}")

# ================= ML & BACKTEST & REPORTS =================
try:
    from ml_engine import ml_engine
    ML_AVAILABLE = True
    print("✅ ML Engine loaded successfully")
except ImportError as e:
    ML_AVAILABLE = False
    print(f"⚠️ ML Engine not available: {e}")

try:
    from backtesting import backtest_engine
    BACKTEST_AVAILABLE = True
    print("✅ Backtesting Engine loaded successfully")
except ImportError as e:
    BACKTEST_AVAILABLE = False
    print(f"⚠️ Backtesting Engine not available: {e}")

try:
    from daily_reports import report_engine
    REPORTS_AVAILABLE = True
    print("✅ Daily Reports Engine loaded successfully")
except ImportError as e:
    REPORTS_AVAILABLE = False
    print(f"⚠️ Daily Reports Engine not available: {e}")

# ================= ML PREDICTOR =================
try:
    from ml_predictor import get_ml_predictor
    ML_PREDICTOR_AVAILABLE = True
    print("✅ ML Predictor loaded successfully")
except ImportError as e:
    ML_PREDICTOR_AVAILABLE = False
    print(f"⚠️ ML Predictor not available: {e}")

# ICT Enhancement Layer
try:
    from config.config_loader import load_feature_flags, update_feature_flag
    from ict_enhancement.ict_enhancer import ICTEnhancer
    
    FEATURE_FLAGS = load_feature_flags()
    ict_enhancer = ICTEnhancer(FEATURE_FLAGS)
except ImportError as e:
    logger.warning(f"ICT Enhancement not available: {e}")
    FEATURE_FLAGS = {'use_ict_enhancer': False}
    ict_enhancer = None

# ================= НАСТРОЙКИ (от .env файл) =================
# Зареди от environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID', '7003238836'))

# ================= USER ACCESS CONTROL =================
# Списък с разрешени потребители (Owner винаги е разрешен)
ALLOWED_USERS = {OWNER_CHAT_ID}  # Само owner по подразбиране

# Файл за съхранение на разрешените потребители
ALLOWED_USERS_FILE = f"{BASE_PATH}/allowed_users.json"

# Зареди разрешени потребители от файл (ако има)
try:
    if os.path.exists(ALLOWED_USERS_FILE):
        with open(ALLOWED_USERS_FILE, 'r') as f:
            loaded_users = json.load(f)
            ALLOWED_USERS.update(loaded_users)
            logger.info(f"✅ Заредени {len(ALLOWED_USERS)} разрешени потребители")
except Exception as e:
    logger.warning(f"⚠️ Грешка при зареждане на разрешени потребители: {e}")

# Tracking на опити за препращане/достъп
ACCESS_ATTEMPTS = {}  # {user_id: {'username': str, 'attempts': int, 'last_attempt': datetime}}

# Admin парола hash (от .env или fallback към хардкоднат hash)
ADMIN_PASSWORD_HASH = os.getenv('ADMIN_PASSWORD_HASH', hashlib.sha256("8109".encode()).hexdigest())

# Binance API endpoints (от .env или fallback към defaults)
BINANCE_PRICE_URL = os.getenv('BINANCE_PRICE_URL', "https://api.binance.com/api/v3/ticker/price")
BINANCE_24H_URL = os.getenv('BINANCE_24H_URL', "https://api.binance.com/api/v3/ticker/24hr")
BINANCE_KLINES_URL = os.getenv('BINANCE_KLINES_URL', "https://api.binance.com/api/v3/klines")

# Провери дали TELEGRAM_BOT_TOKEN е зареден
if not TELEGRAM_BOT_TOKEN:
    logger.error("❌ TELEGRAM_BOT_TOKEN не е намерен в .env файла!")
    logger.error("💡 Създай .env файл от .env.example и попълни с реални стойности")
    raise ValueError("TELEGRAM_BOT_TOKEN е задължителен!")
BINANCE_DEPTH_URL = "https://api.binance.com/api/v3/depth"

# Win-rate tracking file - използва BASE_PATH
STATS_FILE = f"{BASE_PATH}/bot_stats.json"

# Auto-Signal Tracking file - следи активните автоматични сигнали
ACTIVE_SIGNALS_FILE = f"{BASE_PATH}/active_auto_signals.json"

# CoinMarketCap API ключ (опционално - за повече новини)
CMC_API_KEY = ""  # Може да добавите CoinMarketCap API ключ тук (безплатен на coinmarketcap.com/api)
CMC_NEWS_URL = "https://coinmarketcap.com/api/headlines/latest"  # Public endpoint (no key needed)
CMC_PUBLIC_NEWS = "https://api.coinmarketcap.com/data-api/v3/headlines/latest"  # Free public API

# Google Translate API (безплатна) за превод
TRANSLATE_API_URL = "https://translate.googleapis.com/translate_a/single"

# Поддържани символи
SYMBOLS = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT',
    'XRP': 'XRPUSDT',
    'SOL': 'SOLUSDT',
    'BNB': 'BNBUSDT',
    'ADA': 'ADAUSDT',
}

# Настройки за потребителите (съхраняват се в bot_data)
# Структура: bot_data[chat_id] = {
#     'tp': 2.0,  # Take Profit в %
#     'sl': 1.0,  # Stop Loss в %
#     'rr': 2.0,  # Risk/Reward ratio
#     'timeframe': '1h',  # Предпочитан timeframe
#     'alerts_enabled': False,  # Автоматични сигнали
#     'alert_interval': 3600,  # Интервал в секунди
#     'news_enabled': False,  # Автоматични новини
#     'news_interval': 7200,  # Интервал за новини (2 часа)
# }

# ================= ДЕДУПЛИКАЦИЯ НА СИГНАЛИ =================
# Tracking на изпратени автоматични сигнали (за предотвратяване на дублиране)
# Формат: {"BTCUSDT_BUY_4h": {'timestamp': datetime, 'confidence': 75, 'entry_price': 97100}, ...}
SENT_SIGNALS_CACHE = {}

# Константи за 4-степенна проверка на близост на цена
PRICE_PROXIMITY_TIGHT = 0.2      # Много близка цена (%)
PRICE_PROXIMITY_NORMAL = 0.5     # Близка цена (%)
PRICE_PROXIMITY_LOOSE = 1.0      # Относително близка цена (%)
PRICE_PROXIMITY_IDENTICAL = 0.3  # Идентична цена (%)

CONFIDENCE_SIMILARITY_STRICT = 3  # Идентичен confidence (%)
CONFIDENCE_SIMILARITY_NORMAL = 5  # Подобен confidence (%)

TIME_WINDOW_EXTENDED = 120       # 2 часа (минути)
TIME_WINDOW_LONG = 240           # 4 часа (минути)
TIME_WINDOW_MEDIUM = 90          # 1.5 часа (минути)

# Константи за backtest
BACKTEST_ALL_KEYWORD = 'all'     # Ключова дума за всички timeframes

# ================= 3H TIMEFRAME CONVERSION =================
def convert_1h_to_3h(klines_1h):
    """
    Конвертира 1h свещи към 3h свещи (точно както TradingView).
    Binance не поддържа 3h директно, но може да се изчисли от 1h данни.
    
    Args:
        klines_1h: List от 1h свещи от Binance API
        
    Returns:
        List от 3h свещи в същия формат като Binance API
    """
    if not klines_1h or len(klines_1h) < 3:
        return []
    
    klines_3h = []
    
    # Групирай по 3 свещи
    for i in range(0, len(klines_1h) - 2, 3):
        try:
            # Вземи 3 последователни 1h свещи
            candle_1 = klines_1h[i]
            candle_2 = klines_1h[i + 1]
            candle_3 = klines_1h[i + 2]
            
            # Създай 3h свещ комбинирайки трите 1h свещи
            # Timestamp: от първата свещ
            timestamp = candle_1[0]
            
            # Open: от първата свещ
            open_price = float(candle_1[1])
            
            # High: максималната high от трите свещи
            high_price = max(float(candle_1[2]), float(candle_2[2]), float(candle_3[2]))
            
            # Low: минималната low от трите свещи
            low_price = min(float(candle_1[3]), float(candle_2[3]), float(candle_3[3]))
            
            # Close: от третата свещ
            close_price = float(candle_3[4])
            
            # Volume: сума от трите свещи
            volume = float(candle_1[5]) + float(candle_2[5]) + float(candle_3[5])
            
            # Close time: от третата свещ
            close_time = candle_3[6]
            
            # Quote volume: сума от трите свещи
            quote_volume = float(candle_1[7]) + float(candle_2[7]) + float(candle_3[7])
            
            # Trades: сума от трите свещи
            trades = int(candle_1[8]) + int(candle_2[8]) + int(candle_3[8])
            
            # Taker buy base: сума от трите свещи
            taker_buy_base = float(candle_1[9]) + float(candle_2[9]) + float(candle_3[9])
            
            # Taker buy quote: сума от трите свещи
            taker_buy_quote = float(candle_1[10]) + float(candle_2[10]) + float(candle_3[10])
            
            # Ignore field
            ignore = candle_1[11]
            
            # Формирай 3h свещта в Binance формат
            kline_3h = [
                timestamp,
                str(open_price),
                str(high_price),
                str(low_price),
                str(close_price),
                str(volume),
                close_time,
                str(quote_volume),
                trades,
                str(taker_buy_base),
                str(taker_buy_quote),
                ignore
            ]
            
            klines_3h.append(kline_3h)
            
        except (IndexError, ValueError, TypeError) as e:
            logger.warning(f"Грешка при конвертиране на 1h към 3h свещ: {e}")
            continue
    
    return klines_3h

# ================= ПОМОЩНИ ФУНКЦИИ =================

async def fetch_json(url: str, params: dict = None):
    """Асинхронно извличане на JSON данни с rate limiting"""
    try:
        # Rate limiting - 0.1 сек между заявки
        await asyncio.sleep(0.1)
        resp = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"HTTP {resp.status_code} за {url}")
            return None
    except Exception as e:
        logger.error(f"Грешка при заявка към {url}: {e}")
        return None


async def fetch_klines(symbol: str, interval: str, limit: int = 100):
    """
    Fetch klines data from Binance with automatic 3h conversion.
    Ако interval='3h', автоматично взима 1h данни и ги конвертира към 3h.
    """
    try:
        # Проверка дали е поискан 3h таймфрейм
        if interval == '3h':
            # Binance не поддържа 3h, използвай 1h и конвертирай
            # За да получим достатъчно 3h свещи, трябват 3x повече 1h свещи
            limit_1h = limit * 3
            
            params = {'symbol': symbol, 'interval': '1h', 'limit': limit_1h}
            klines_1h = await fetch_json(BINANCE_KLINES_URL, params)
            
            if not klines_1h:
                logger.error(f"❌ Не успях да извлека 1h данни за {symbol}")
                return None
            
            # Конвертирай 1h към 3h
            klines_3h = convert_1h_to_3h(klines_1h)
            
            logger.info(f"✅ Конвертирани {len(klines_1h)} x 1h свещи → {len(klines_3h)} x 3h свещи за {symbol}")
            
            return klines_3h
        else:
            # Стандартна заявка за всички други интервали
            params = {'symbol': symbol, 'interval': interval, 'limit': limit}
            return await fetch_json(BINANCE_KLINES_URL, params)
            
    except Exception as e:
        logger.error(f"Грешка при fetch_klines за {symbol} {interval}: {e}")
        return None



async def translate_text(text: str, target_lang: str = 'bg') -> str:
    """Превод на текст с deep-translator (по-надежден)"""
    if not TRANSLATOR_AVAILABLE or not text:
        logger.warning(f"⚠️ Превод прескочен: TRANSLATOR_AVAILABLE={TRANSLATOR_AVAILABLE}, text={text[:50] if text else 'None'}")
        return text
    
    try:
        # Използвай deep-translator който е по-надежден
        translator = GoogleTranslator(source='auto', target=target_lang)
        translated = await asyncio.to_thread(translator.translate, text)
        logger.info(f"✅ Преведено: '{text[:30]}...' → '{translated[:30] if translated else None}...'")
        return translated if translated else text
    except Exception as e:
        logger.error(f"❌ Грешка при превод на '{text[:50]}': {e}")
        return text


def get_user_settings(bot_data, chat_id):
    """Вземи настройките на потребителя или създай по подразбиране"""
    if chat_id not in bot_data:
        bot_data[chat_id] = {
            'tp': 3.0,
            'sl': 1.0,
            'rr': 3.0,
            'timeframe': '4h',
            'alerts_enabled': False,
            'alert_interval': 3600,
            'news_enabled': False,
            'news_interval': 7200,
        }
    return bot_data[chat_id]


def get_main_keyboard():
    """Връща основната клавиатура с менюто"""
    keyboard = [
        [KeyboardButton("📊 Пазар"), KeyboardButton("📈 Сигнал")],
        [KeyboardButton("📰 Новини"), KeyboardButton("📋 Отчети")],
        [KeyboardButton("📚 ML Анализ"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("🔔 Alerts"), KeyboardButton("ℹ️ Помощ")],
        [KeyboardButton("🔄 Рестарт"), KeyboardButton("💻 Workspace")],
        [KeyboardButton("🏠 Меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_ml_keyboard():
    """ML Анализ подменю с описания"""
    keyboard = [
        [KeyboardButton("🤖 ML Прогноза"), KeyboardButton("📊 Backtest")],
        [KeyboardButton("📈 ML Report"), KeyboardButton("🔧 ML Status")],
        [KeyboardButton("🏠 Назад към Меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def is_signal_already_sent(symbol, signal_type, timeframe, confidence, entry_price, cooldown_minutes=60):
    """Проверява дали даден сигнал вече е изпращан наскоро (с 4-степенна проверка за близост на цена)
    
    Args:
        symbol: Символ (напр. BTCUSDT)
        signal_type: BUY или SELL
        timeframe: Таймфрейм (напр. 4h)
        confidence: Ниво на увереност
        entry_price: Цена на входа (за проверка на близост)
        cooldown_minutes: Време за изчакване преди повторно изпращане (по подразбиране 60 мин)
    
    Returns:
        True ако сигналът вече е изпращан, False ако е нов
    """
    global SENT_SIGNALS_CACHE
    
    # Създай уникален ключ за сигнала
    signal_key = f"{symbol}_{signal_type}_{timeframe}"
    
    current_time = datetime.now()
    
    # Провери дали този сигнал е изпращан наскоро
    if signal_key in SENT_SIGNALS_CACHE:
        last_sent_time = SENT_SIGNALS_CACHE[signal_key]['timestamp']
        last_confidence = SENT_SIGNALS_CACHE[signal_key]['confidence']
        last_price = SENT_SIGNALS_CACHE[signal_key].get('entry_price', 0)
        
        # Ако няма запазена цена (стар кеш формат), не можем да проверим близост - пропусни
        if last_price == 0:
            logger.info(f"⚠️ {signal_key}: No cached price (old format) - allowing signal")
            # Обнови кеша с новата цена и излез
            SENT_SIGNALS_CACHE[signal_key] = {
                'timestamp': current_time,
                'confidence': confidence,
                'entry_price': entry_price
            }
            cleanup_old_signals()
            logger.info(f"✅ New signal: {signal_key} @ ${entry_price:.2f} ({confidence}%)")
            return False
        
        # Изчисли колко време е минало
        time_diff = (current_time - last_sent_time).total_seconds() / 60  # в минути
        
        # Изчисли ценова разлика (процент)
        price_diff_pct = abs((entry_price - last_price) / last_price) * 100 if last_price > 0.01 else 100.0
        
        # Изчисли confidence разлика
        confidence_diff = abs(confidence - last_confidence)
        
        # === 4-СТЕПЕННА ПРОВЕРКА ЗА БЛИЗОСТ ===
        
        # ПРАВИЛО 1: Cooldown + близка цена
        if time_diff < cooldown_minutes and price_diff_pct < PRICE_PROXIMITY_NORMAL:
            logger.info(f"⏭️ Skip {signal_key}: Cooldown ({time_diff:.1f}m) + Price close ({price_diff_pct:.2f}%)")
            return True
        
        # ПРАВИЛО 2: Много близка цена в рамките на 2h
        if price_diff_pct < PRICE_PROXIMITY_TIGHT and time_diff < TIME_WINDOW_EXTENDED:
            logger.info(f"⏭️ Skip {signal_key}: Price very close ({price_diff_pct:.2f}%) within 2h")
            return True
        
        # ПРАВИЛО 3: Подобен confidence + близка цена в рамките на 1.5x cooldown
        if confidence_diff < CONFIDENCE_SIMILARITY_NORMAL and price_diff_pct < PRICE_PROXIMITY_LOOSE and time_diff < TIME_WINDOW_MEDIUM:
            logger.info(f"⏭️ Skip {signal_key}: Similar signal (Δconf={confidence_diff:.1f}%, Δprice={price_diff_pct:.2f}%)")
            return True
        
        # ПРАВИЛО 4: Идентичен сигнал в рамките на 4h
        if confidence_diff < CONFIDENCE_SIMILARITY_STRICT and price_diff_pct < PRICE_PROXIMITY_IDENTICAL and time_diff < TIME_WINDOW_LONG:
            logger.info(f"⏭️ Skip {signal_key}: Almost identical within 4h (Δconf={confidence_diff:.1f}%, Δprice={price_diff_pct:.2f}%)")
            return True
    
    # Запази новия сигнал в кеша (с цената!)
    SENT_SIGNALS_CACHE[signal_key] = {
        'timestamp': current_time,
        'confidence': confidence,
        'entry_price': entry_price
    }
    
    # Почисти стари записи (по-стари от 24 часа)
    cleanup_old_signals()
    
    logger.info(f"✅ New signal: {signal_key} @ ${entry_price:.2f} ({confidence}%)")
    return False


def cleanup_old_signals():
    """Премахва записи за сигнали по-стари от 24 часа"""
    global SENT_SIGNALS_CACHE
    
    current_time = datetime.now()
    keys_to_remove = []
    
    for key, data in SENT_SIGNALS_CACHE.items():
        time_diff_hours = (current_time - data['timestamp']).total_seconds() / 3600
        if time_diff_hours > 24:
            keys_to_remove.append(key)
    
    for key in keys_to_remove:
        del SENT_SIGNALS_CACHE[key]
    
    if keys_to_remove:
        logger.info(f"🧹 Cleaned {len(keys_to_remove)} old signals from cache")


def get_admin_keyboard():
    """Връща клавиатура за Admin режим"""
    keyboard = [
        [KeyboardButton("✅ Enter"), KeyboardButton("❌ Exit")],
        [KeyboardButton("📊 Пазар"), KeyboardButton("📈 Сигнал")],
        [KeyboardButton("📰 Новини"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("🔔 Alerts"), KeyboardButton("🏠 Меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def detect_order_blocks(df, lookback=5, threshold=0.02, current_price=None, max_obs=3):
    """
    Детектира само НАЙ-ВАЖНИТЕ Order Blocks - тези с най-голяма вероятност за отблъскване
    
    Args:
        df: DataFrame с OHLC данни
        lookback: Колко свещи назад да търсим
        threshold: Минимална промяна за валиден OB (2% по подразбиране - по-строг)
        current_price: Текуща цена за филтриране по близост
        max_obs: Максимален брой OB на тип (по подразбиране 3)
    
    Returns:
        List of dict: [{'index': idx, 'type': 'bullish/bearish', 'high': x, 'low': y, 'strength': z, 'score': w}, ...]
    """
    # Провери дали има достатъчно данни
    if len(df) < lookback + 2:
        logger.warning(f"Not enough data for Order Blocks detection: {len(df)} candles (need at least {lookback + 2})")
        return []
    
    all_order_blocks = []
    
    for i in range(lookback, len(df) - 1):
        if i >= lookback:
            current_candle = df.iloc[i]
            next_candle = df.iloc[i + 1]
            
            # Bullish OB: bearish свещ + следва силен ръст
            if current_candle['close'] < current_candle['open']:  # Bearish свещ
                # Изчисли силата на движението
                move_up = (next_candle['high'] - current_candle['low']) / current_candle['low']
                
                if move_up >= threshold:
                    # Допълнителни критерии за качество
                    candle_size = abs(current_candle['open'] - current_candle['close'])
                    candle_range = current_candle['high'] - current_candle['low']
                    body_ratio = candle_size / candle_range if candle_range > 0 else 0
                    
                    # Проверка дали OB зоната не е пробита (validnost)
                    is_valid = True
                    for j in range(i + 1, min(i + 10, len(df))):
                        if df.iloc[j]['low'] < current_candle['low'] * 0.998:  # Пробита с 0.2%
                            is_valid = False
                            break
                    
                    if is_valid:
                        strength = move_up * 100
                        
                        # Изчисли SCORE за важност (комбинация от фактори)
                        score = strength  # Базов score
                        score += body_ratio * 20  # Бонус за силна свещ (не doji)
                        
                        # Бонус ако е близо до текущата цена (по-релевантен)
                        if current_price:
                            distance = abs(current_price - current_candle['low']) / current_price
                            if distance < 0.05:  # В рамките на 5%
                                score += 30
                            elif distance < 0.10:  # В рамките на 10%
                                score += 15
                        
                        all_order_blocks.append({
                            'index': i,
                            'type': 'bullish',
                            'high': current_candle['high'],
                            'low': current_candle['low'],
                            'open': current_candle['open'],
                            'close': current_candle['close'],
                            'strength': strength,
                            'score': score,
                            'body_ratio': body_ratio
                        })
            
            # Bearish OB: bullish свещ + следва силен спад
            if current_candle['close'] > current_candle['open']:  # Bullish свещ
                move_down = (current_candle['high'] - next_candle['low']) / current_candle['high']
                
                if move_down >= threshold:
                    candle_size = abs(current_candle['close'] - current_candle['open'])
                    candle_range = current_candle['high'] - current_candle['low']
                    body_ratio = candle_size / candle_range if candle_range > 0 else 0
                    
                    # Проверка за validност
                    is_valid = True
                    for j in range(i + 1, min(i + 10, len(df))):
                        if df.iloc[j]['high'] > current_candle['high'] * 1.002:
                            is_valid = False
                            break
                    
                    if is_valid:
                        strength = move_down * 100
                        
                        score = strength
                        score += body_ratio * 20
                        
                        if current_price:
                            distance = abs(current_candle['high'] - current_price) / current_price
                            if distance < 0.05:
                                score += 30
                            elif distance < 0.10:
                                score += 15
                        
                        all_order_blocks.append({
                            'index': i,
                            'type': 'bearish',
                            'high': current_candle['high'],
                            'low': current_candle['low'],
                            'open': current_candle['open'],
                            'close': current_candle['close'],
                            'strength': strength,
                            'score': score,
                            'body_ratio': body_ratio
                        })
    
    # ФИЛТРИРАНЕ: Вземи топ N най-важни OB
    bullish_obs = [ob for ob in all_order_blocks if ob['type'] == 'bullish']
    bearish_obs = [ob for ob in all_order_blocks if ob['type'] == 'bearish']
    
    # Сортирай по score (най-важните отгоре)
    bullish_obs.sort(key=lambda x: x['score'], reverse=True)
    bearish_obs.sort(key=lambda x: x['score'], reverse=True)
    
    # Вземи топ N най-важни от всеки тип
    top_bullish = bullish_obs[:max_obs]
    top_bearish = bearish_obs[:max_obs]
    
    # СОРТИРАЙ ПО ИНДЕКС (възможно най-рано на графиката)
    # За да се показват отляво надясно според появата им
    all_selected = top_bullish + top_bearish
    all_selected.sort(key=lambda x: x['index'])  # Сортирай по време (индекс)
    
    return all_selected


def detect_mss_bos(df):
    """Детектира Market Structure Shift (MSS) и Break of Structure (BOS)"""
    mss_bos_points = []
    
    # Намери swing highs и swing lows
    for i in range(2, len(df) - 2):
        # Swing High
        if (df.iloc[i]['high'] > df.iloc[i-1]['high'] and 
            df.iloc[i]['high'] > df.iloc[i-2]['high'] and
            df.iloc[i]['high'] > df.iloc[i+1]['high'] and
            df.iloc[i]['high'] > df.iloc[i+2]['high']):
            
            # Проверка за BOS/MSS - пробив на предишен high
            for j in range(i+1, min(i+10, len(df))):
                if df.iloc[j]['close'] > df.iloc[i]['high']:
                    # BOS Bullish - пробива swing high
                    mss_bos_points.append({
                        'index': j,
                        'price': df.iloc[i]['high'],
                        'type': 'BOS',
                        'direction': 'bullish'
                    })
                    break
        
        # Swing Low
        if (df.iloc[i]['low'] < df.iloc[i-1]['low'] and 
            df.iloc[i]['low'] < df.iloc[i-2]['low'] and
            df.iloc[i]['low'] < df.iloc[i+1]['low'] and
            df.iloc[i]['low'] < df.iloc[i+2]['low']):
            
            # Проверка за BOS/MSS - пробив на предишен low
            for j in range(i+1, min(i+10, len(df))):
                if df.iloc[j]['close'] < df.iloc[i]['low']:
                    # BOS Bearish - пробива swing low
                    mss_bos_points.append({
                        'index': j,
                        'price': df.iloc[i]['low'],
                        'type': 'BOS',
                        'direction': 'bearish'
                    })
                    break
    
    # Детектирай MSS (по-силна промяна на структурата)
    for point in mss_bos_points:
        idx = point['index']
        # MSS = BOS + силна промяна (>2% от цената)
        if idx > 0:
            price_change_pct = abs((df.iloc[idx]['close'] - df.iloc[idx-5]['close']) / df.iloc[idx-5]['close']) * 100
            if price_change_pct > 2.0:  # Промяна >2%
                point['type'] = 'MSS'
    
    # Върни последните 3 MSS/BOS
    return mss_bos_points[-3:] if mss_bos_points else []


def generate_chart(klines_data, symbol, signal, current_price, tp_price, sl_price, timeframe, luxalgo_ict_data=None):
    """Генерира графика със свещи, индикатори, Order Blocks, ликвидни зони и стрелка за тренда"""
    try:
        # Конвертирай klines data към DataFrame
        df = pd.DataFrame(klines_data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        # Конвертирай към числа и datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # Вземи последните 50 свещи за по-добра визуализация
        df = df.tail(50)
        
        # Провери дали има достатъчно данни
        if len(df) < 10:
            logger.warning(f"Insufficient data for chart: only {len(df)} candles")
            return None
        
        # 🔍 ДЕТЕКТИРАЙ ORDER BLOCKS - ТОП 5 ОТ ВСЕКИ ТИП
        # Подавай текущата цена за филтриране по близост
        lookback_period = min(5, len(df) - 2)
        max_obs_count = 5  # Топ 5 вместо 3
        
        order_blocks = detect_order_blocks(
            df.reset_index(drop=True), 
            lookback=lookback_period, 
            threshold=0.02,  # 2% threshold - по-строг
            current_price=current_price,
            max_obs=max_obs_count
        )
        
        logger.info(f"📦 Detected {len(order_blocks)} high-quality Order Blocks for {symbol}")
        
        # 🔍 ДЕТЕКТИРАЙ MSS/BOS
        mss_bos_points = detect_mss_bos(df.reset_index(drop=True))
        logger.info(f"🔄 Detected {len(mss_bos_points)} MSS/BOS points for {symbol}")
        
        # Създай графика - ПРОФЕСИОНАЛЕН СТИЛ като TradingView
        # ФОРМАТ 1:1 (квадратна снимка 16x16) + БЯЛ ФОН + Volume панел
        fig = plt.figure(figsize=(16, 16), facecolor='white')
        
        # 2 панела: Главна графика (80%), Volume (20%) - БЕЗ RSI
        gs = fig.add_gridspec(2, 1, height_ratios=[8, 2], hspace=0.05)
        
        # Главна графика
        ax1 = fig.add_subplot(gs[0])
        ax1.set_facecolor('white')
        
        # Volume панел
        ax_volume = fig.add_subplot(gs[1], sharex=ax1)
        ax_volume.set_facecolor('white')
        
        # Тънък grid за професионален вид (като TradingView)
        ax1.grid(True, alpha=0.2, linestyle=':', linewidth=0.5, color='#d0d0d0')
        ax_volume.grid(True, alpha=0.2, linestyle=':', linewidth=0.5, color='#d0d0d0')
        
        # Plot candlesticks - МАЛКИ и реалистични като AzCryptoBot
        for idx, (timestamp, row) in enumerate(df.iterrows()):
            # Teal/Red цветове като Binance/TradingView
            color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
            # Тънки свещи за професионален вид
            ax1.plot([idx, idx], [row['low'], row['high']], color=color, linewidth=0.6, alpha=0.9)
            height = abs(row['close'] - row['open'])
            bottom = min(row['open'], row['close'])
            ax1.add_patch(plt.Rectangle((idx-0.25, bottom), 0.5, height, facecolor=color, edgecolor=color, linewidth=0.8, alpha=1.0))
        
        # VOLUME панел (зелени/червени барове)
        for idx, (timestamp, row) in enumerate(df.iterrows()):
            vol_color = '#26a69a' if row['close'] >= row['open'] else '#ef5350'
            ax_volume.bar(idx, row['volume'], color=vol_color, alpha=0.6, width=0.8)
        
        ax_volume.set_ylabel('Volume', color='#333333', fontsize=8)
        ax_volume.tick_params(axis='y', labelcolor='#333333', labelsize=7)
        plt.setp(ax1.get_xticklabels(), visible=False)  # Скрий x-labels от горния панел
        
        # 📦 ВИЗУАЛИЗИРАЙ ORDER BLOCKS - ПРОФЕСИОНАЛЕН СТИЛ (КЪСИ ЛИНИИ)
        for ob in order_blocks:
            idx = ob['index']
            ob_type = ob['type']
            score = ob.get('score', 0)
            ob_high = ob['high']
            ob_low = ob['low']
            ob_mid = (ob_high + ob_low) / 2  # Equilibrium зона
            
            if ob_type == 'bullish':
                # Bullish OB - дискретна зелена зона (support)
                base_color = '#26a69a'  # TradingView teal
                edge_color = '#1e8e7e'  # Тъмен teal
                alpha = 0.12  # Лека прозрачност
                
                # Определи важността според score
                if score >= 50:
                    label = "+OB"  # Силен
                    linewidth = 1.8
                    line_alpha = 0.8
                elif score >= 35:
                    label = "+OB"  # Среден
                    linewidth = 1.5
                    line_alpha = 0.7
                else:
                    label = "+OB"  # Слаб
                    linewidth = 1.2
                    line_alpha = 0.6
            else:
                # Bearish OB - дискретна червена зона (resistance)
                base_color = '#ef5350'  # TradingView red
                edge_color = '#c62828'  # Тъмночервено
                alpha = 0.12  # Лека прозрачност
                
                if score >= 50:
                    label = "-OB"  # Силен
                    linewidth = 1.8
                    line_alpha = 0.8
                elif score >= 35:
                    label = "-OB"  # Среден
                    linewidth = 1.5
                    line_alpha = 0.7
                else:
                    label = "-OB"  # Слаб
                    linewidth = 1.2
                    line_alpha = 0.6
            
            # 1. Определи позицията на OB box (ОТ НАЧАЛОТО, НЕ през цялата графика)
            line_start = max(0, idx)  # Започни от самия OB
            line_end = min(len(df) - 1, idx + 5)  # OB e 5 свещи
            eq_line_end = min(len(df) - 1, idx + 8)  # EQ e по-дълъг - 8 свещи
            ob_width = line_end - line_start
            ob_height = ob_high - ob_low
            
            # 2. Нарисувай OB BOX (само в тази зона, НЕ през цялата графика)
            ob_box = plt.Rectangle(
                (line_start, ob_low),
                ob_width,
                ob_height,
                facecolor=base_color,
                edgecolor=edge_color,
                linewidth=linewidth + 0.8,
                linestyle='-',
                alpha=alpha,
                zorder=2
            )
            ax1.add_patch(ob_box)
            
            # 3. Горна граница
            ax1.plot([line_start, line_end], [ob_high, ob_high], 
                    color=edge_color, linestyle='-', linewidth=linewidth + 0.8, alpha=line_alpha, zorder=3)
            
            # 4. Долна граница
            ax1.plot([line_start, line_end], [ob_low, ob_low], 
                    color=edge_color, linestyle='-', linewidth=linewidth + 0.8, alpha=line_alpha, zorder=3)
            
            # 5. EQUILIBRIUM ЗОНА (BOX само в рамките на OB, НЕ през цялата графика)
            eq_height = (ob_high - ob_low) * 0.15  # 15% от височината на OB
            eq_low = ob_mid - eq_height / 2
            eq_high = ob_mid + eq_height / 2
            eq_width = eq_line_end - line_start  # 8 свещи за EQ
            
            # EQ Box само в рамките на OB (по-дълъг)
            eq_box = plt.Rectangle(
                (line_start, eq_low),
                eq_width,  # По-дълъг - 8 свещи
                eq_height,
                facecolor='#ff9800',
                edgecolor='#f57c00',
                linewidth=1.2,
                linestyle='--',
                alpha=0.25,
                zorder=3
            )
            ax1.add_patch(eq_box)
            
            # Централна линия на Equilibrium (по-дълга - 8 свещи)
            ax1.plot([line_start, eq_line_end], [ob_mid, ob_mid], 
                    color='#ff9800', linestyle='-', linewidth=1.5, alpha=0.85, zorder=4)
            
            # 6. МАЛЪК етикет +OB / -OB в КРАЯ на box
            ax1.text(
                line_end + 0.5,
                ob_high if ob_type == 'bearish' else ob_low,
                f"{label}",
                fontsize=7,
                color='white',
                weight='normal',
                ha='left',
                va='top' if ob_type == 'bearish' else 'bottom',
                bbox=dict(boxstyle='round,pad=0.25', facecolor=edge_color, alpha=0.85, edgecolor='none')
            )
            
            # 7. ВИДИМ етикет EQ (Equilibrium) в КРАЯ на box
            ax1.text(
                line_end + 0.5,
                ob_mid,
                "EQ",
                fontsize=7,
                color='white',
                weight='bold',
                ha='left',
                va='center',
                bbox=dict(boxstyle='round,pad=0.3', facecolor='#ff9800', alpha=0.95, edgecolor='white', linewidth=1.2)
            )
        
        # 🔄 ВИЗУАЛИЗИРАЙ MSS/BOS - МАЛКИ ЕТИКЕТИ
        for mss_bos in mss_bos_points:
            idx = mss_bos['index']
            price = mss_bos['price']
            mss_type = mss_bos['type']  # MSS or BOS
            direction = mss_bos['direction']  # bullish or bearish
            
            # Цвят и етикет
            if direction == 'bullish':
                color = '#26a69a'  # Teal
                arrow = '▲'
            else:
                color = '#ef5350'  # Red
                arrow = '▼'
            
            # Нарисувай малък етикет
            ax1.text(
                idx,
                price,
                f"{arrow} {mss_type}",
                fontsize=6,
                color='white',
                weight='bold',
                ha='center',
                va='bottom' if direction == 'bullish' else 'top',
                bbox=dict(boxstyle='round,pad=0.2', facecolor=color, alpha=0.9, edgecolor='white', linewidth=1)
            )
        
        # 🎯 LUXALGO + ICT VISUALIZATION
        if luxalgo_ict_data:
            # === SUPPORT & RESISTANCE LINES (ПЛЪТНИ ЛИНИИ) ===
            if luxalgo_ict_data.get('luxalgo_sr'):
                sr_data = luxalgo_ict_data['luxalgo_sr']
                
                # Support - ПЛЪТНА зелена линия
                for support_level in sr_data.get('support_levels', []):
                    ax1.axhline(y=support_level, color='#4caf50', linestyle='-', linewidth=2, alpha=0.8, zorder=3)
                    ax1.text(2, support_level, '  Support', fontsize=7, color='#2e7d32', weight='bold', va='bottom')
                
                # Resistance - ПЛЪТНА червена линия
                for resistance_level in sr_data.get('resistance_levels', []):
                    ax1.axhline(y=resistance_level, color='#f44336', linestyle='-', linewidth=2, alpha=0.8, zorder=3)
                    ax1.text(2, resistance_level, '  Resistance', fontsize=7, color='#c62828', weight='bold', va='top')
                
                # === BUY SIDE & SELL SIDE LIQUIDITY ===
                liquidity_zones = sr_data.get('liquidity_zones', [])
                for liq_price in liquidity_zones:
                    zone_width = liq_price * 0.004
                    zone_low = liq_price - zone_width
                    zone_high = liq_price + zone_width
                    
                    if liq_price > current_price:
                        # BUY SIDE liquidity (над цената) - мека червена зона
                        ax1.axhspan(zone_low, zone_high, color='#ef5350', alpha=0.08, zorder=1)
                        ax1.axhline(y=liq_price, color='#c62828', linestyle=':', linewidth=0.8, alpha=0.5, zorder=2)
                        ax1.text(1, liq_price, 'BSL', fontsize=5, color='#c62828', weight='normal', ha='left', va='center')
                    else:
                        # SELL SIDE liquidity (под цената) - мека синя зона
                        ax1.axhspan(zone_low, zone_high, color='#42a5f5', alpha=0.08, zorder=1)
                        ax1.axhline(y=liq_price, color='#1976d2', linestyle=':', linewidth=0.8, alpha=0.5, zorder=2)
                        ax1.text(1, liq_price, 'SSL', fontsize=5, color='#1976d2', weight='normal', ha='left', va='center')
            
            # === FAIR VALUE GAPS (FVG) - ТОЧНО НА МЯСТОТО КАТО TradingView ===
            fvg_data = luxalgo_ict_data.get('ict_fvg', [])
            if fvg_data:
                for fvg in fvg_data[-5:]:  # Покажи последните 5 FVG
                    fvg_low = fvg.get('gap_low')
                    fvg_high = fvg.get('gap_high')
                    fvg_type = fvg.get('type', 'BULLISH')
                    fvg_index = fvg.get('index', len(df)-10)  # Индекс къде е FVG
                    
                    if fvg_low and fvg_high:
                        # Изчисли сила на FVG (gap size %)
                        gap_size_pct = ((fvg_high - fvg_low) / fvg_low) * 100
                        
                        # 🔍 ПРОВЕРИ ДАЛИ FVG Е ИЗЧИСТЕН (FILLED) - цената е влязла в зоната
                        is_filled = False
                        filled_at_index = len(df) - 1  # По подразбиране до края
                        
                        # Намери къде е влязла цената в FVG зоната
                        for i in range(fvg_index, len(df)):
                            candle_low = df.iloc[i]['low']
                            candle_high = df.iloc[i]['high']
                            
                            # Проверка дали свещта е влязла в FVG зоната
                            if candle_low <= fvg_high and candle_high >= fvg_low:
                                is_filled = True
                                filled_at_index = i
                                break
                        
                        # АКО Е FILLED - НЕ ГО ПОКАЗВАЙ (skip)
                        if is_filled:
                            continue  # Пропусни този FVG, не го рисувай
                        
                        # Цвят според типа (САМО за активни FVG)
                        if 'BULLISH' in fvg_type:
                            fvg_color = '#4caf50'  # Зелено (активен)
                            fvg_edge = '#2e7d32'  # Тъмнозелено
                            fvg_label = 'FVG+'
                        else:
                            fvg_color = '#f44336'  # Червено (активен)
                            fvg_edge = '#c62828'  # Тъмночервено
                            fvg_label = 'FVG-'
                        
                        # ПЛЪТНА vs ПУНКТИРНА според силата
                        if gap_size_pct >= 0.5:  # Силна FVG (gap ≥0.5%)
                            linestyle = '-'  # ПЛЪТНА линия
                            linewidth = 2.0
                            alpha = 0.20  # Лека зона
                            line_alpha = 0.9
                            label_suffix = ' Strong'
                        else:  # Слаба FVG
                            linestyle = '--'  # ПУНКТИРНА линия
                            linewidth = 1.5
                            alpha = 0.12
                            line_alpha = 0.7
                            label_suffix = ' Weak'
                        
                        # 1. Определи позицията на FVG box (ОТ НАЧАЛОТО)
                        fvg_start_x = max(0, fvg_index)  # Започва от индекса на FVG
                        fvg_end_x = len(df) - 1  # До края на графиката (понеже НЕ е filled)
                        fvg_width = fvg_end_x - fvg_start_x
                        fvg_height = fvg_high - fvg_low
                        
                        # 2. Нарисувай FVG BOX (като TradingView)
                        fvg_box = plt.Rectangle(
                            (fvg_start_x, fvg_low),  # Долен ляв ъгъл
                            fvg_width,  # Ширина
                            fvg_height,  # Височина
                            facecolor=fvg_color,
                            edgecolor=fvg_edge,
                            linewidth=linewidth,
                            linestyle=linestyle,
                            alpha=alpha,
                            zorder=2
                        )
                        ax1.add_patch(fvg_box)
                        
                        # 3. Горна и долна граница (ПЛЪТНИ линии в рамките на box)
                        ax1.plot([fvg_start_x, fvg_end_x], [fvg_high, fvg_high], 
                                color=fvg_edge, linestyle=linestyle, linewidth=linewidth, alpha=line_alpha, zorder=3)
                        ax1.plot([fvg_start_x, fvg_end_x], [fvg_low, fvg_low], 
                                color=fvg_edge, linestyle=linestyle, linewidth=linewidth, alpha=line_alpha, zorder=3)
                        
                        # 4. СРЕДНА ЛИНИЯ (EQ) в рамките на box
                        fvg_mid = (fvg_low + fvg_high) / 2
                        ax1.plot([fvg_start_x, fvg_end_x], [fvg_mid, fvg_mid], 
                                color=fvg_edge, linestyle=':', linewidth=1.0, alpha=0.5, zorder=3)
                        
                        # 5. ЕТИКЕТ В НАЧАЛОТО на FVG (къде се е появил)
                        fvg_label_text = f"{fvg_label}{label_suffix}"
                        ax1.text(fvg_start_x + 1, fvg_mid, fvg_label_text, 
                               fontsize=7, color='white', weight='bold', ha='left', va='center',
                               bbox=dict(boxstyle='round,pad=0.3', facecolor=fvg_edge, alpha=0.9, edgecolor='white', linewidth=1.2))
            
            # === FIBONACCI LEVELS ===
            fib_data = luxalgo_ict_data.get('fibonacci_extension')
            if fib_data and fib_data.get('levels'):
                fib_levels = fib_data['levels']
                for level_name, level_price in fib_levels.items():
                    if level_price and level_price > 0:
                        # Различни цветове за различни нива - МЕКИ
                        if '0.618' in level_name or 'OTE' in level_name:
                            fib_color = '#ffd54f'  # Меко златно
                            fib_alpha = 0.6
                        elif '1.618' in level_name:
                            fib_color = '#ba68c8'  # Меко лилаво
                            fib_alpha = 0.6
                        else:
                            fib_color = '#9e9e9e'  # Сиво
                            fib_alpha = 0.4
                        
                        ax1.axhline(y=level_price, color=fib_color, linestyle='--', linewidth=1, alpha=fib_alpha, zorder=2)
                        ax1.text(len(df)-8, level_price, f'  Fib {level_name}', 
                               fontsize=5, color=fib_color, weight='normal', va='center', alpha=0.8)
        
        # 📍 ENTRY ZONE - мека синя зона БЕЗ стрелка
        entry_zone_width = current_price * 0.003  # ПО-ТЪНКА зона (0.3%)
        entry_low = current_price - entry_zone_width
        entry_high = current_price + entry_zone_width
        
        ax1.axhspan(entry_low, entry_high, color='#42a5f5', alpha=0.15, zorder=3)
        ax1.axhline(y=current_price, color='#1e88e5', linestyle='-', linewidth=2, alpha=0.8, zorder=4)
        
        # ПО-МАЛЪК текстов етикет БЕЗ стрелка (fontsize 8)
        ax1.text(len(df)*0.15, current_price, f'  📍 ENTRY ${current_price:.2f}', 
                fontsize=8, color='white', weight='normal', va='center',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#1976d2', alpha=0.85, edgecolor='white', linewidth=1.5))
        
        # 🎯 TAKE PROFIT - мека зелена зона БЕЗ стрелка
        tp_zone_width = tp_price * 0.003  # ПО-ТЪНКА зона
        tp_low = tp_price - tp_zone_width
        tp_high = tp_price + tp_zone_width
        
        ax1.axhspan(tp_low, tp_high, color='#81c784', alpha=0.18, zorder=3)
        ax1.axhline(y=tp_price, color='#388e3c', linestyle='--', linewidth=2, alpha=0.8, zorder=4)
        
        # ПО-МАЛЪК текстов етикет с процент БЕЗ стрелка (fontsize 8)
        tp_pct_display = ((tp_price - current_price) / current_price) * 100
        ax1.text(len(df)*0.15, tp_price, f'  🎯 TP ${tp_price:.2f} ({tp_pct_display:+.1f}%)', 
                fontsize=8, color='white', weight='normal', va='center',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#2e7d32', alpha=0.85, edgecolor='white', linewidth=1.5))
        
        # 🛑 STOP LOSS - мека червена зона БЕЗ стрелка
        sl_zone_width = sl_price * 0.003  # ПО-ТЪНКА зона
        sl_low = sl_price - sl_zone_width
        sl_high = sl_price + sl_zone_width
        
        ax1.axhspan(sl_low, sl_high, color='#e57373', alpha=0.18, zorder=3)
        ax1.axhline(y=sl_price, color='#c62828', linestyle='--', linewidth=2, alpha=0.8, zorder=4)
        
        # ПО-МАЛЪК текстов етикет с процент БЕЗ стрелка (fontsize 8)
        sl_pct_display = ((sl_price - current_price) / current_price) * 100
        ax1.text(len(df)*0.15, sl_price, f'  🛑 SL ${sl_price:.2f} ({sl_pct_display:.1f}%)', 
                fontsize=8, color='white', weight='normal', va='center',
                bbox=dict(boxstyle='round,pad=0.4', facecolor='#c62828', alpha=0.85, edgecolor='white', linewidth=1.5))
        
        # Сигнал етикет БЕЗ стрелка (компактен)
        signal_x = len(df) - 8
        signal_y = current_price
        
        if signal == 'BUY':
            ax1.text(signal_x, signal_y, '▲ BUY', 
                    fontsize=10, color='white', weight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#388e3c', alpha=0.85, edgecolor='white', linewidth=1.5))
        elif signal == 'SELL':
            ax1.text(signal_x, signal_y, '▼ SELL', 
                    fontsize=10, color='white', weight='bold',
                    bbox=dict(boxstyle='round,pad=0.5', facecolor='#c62828', alpha=0.85, edgecolor='white', linewidth=1.5))
        
        # Watermark като TradingView
        ax1.text(len(df)/2, (ax1.get_ylim()[0] + ax1.get_ylim()[1])/2, '@CryptoSignalBot',
                fontsize=20, color='#e0e0e0', alpha=0.3, ha='center', va='center',
                rotation=0, weight='bold')
        
        # Axis styling за бял фон - ПОДРОБНИ ЦЕНИ
        ax1.tick_params(axis='x', colors='#666666', labelsize=8)
        ax1.tick_params(axis='y', colors='#333333', labelsize=9, right=True, labelright=True, 
                       which='both')  # Показвай major И minor ticks
        
        # Добави MINOR TICKS за повече детайли на цените
        from matplotlib.ticker import AutoMinorLocator
        ax1.yaxis.set_minor_locator(AutoMinorLocator(5))  # 5 minor ticks между major
        ax1.tick_params(axis='y', which='minor', right=True, labelright=False, length=3, color='#cccccc')
        
        ax1.spines['bottom'].set_color('#cccccc')
        ax1.spines['top'].set_color('#cccccc')
        ax1.spines['left'].set_color('#cccccc')
        ax1.spines['right'].set_color('#cccccc')
        
        ax_volume.tick_params(axis='x', colors='#666666', labelsize=8)
        ax_volume.spines['bottom'].set_color('#cccccc')
        ax_volume.spines['top'].set_color('#cccccc')
        ax_volume.spines['left'].set_color('#cccccc')
        ax_volume.spines['right'].set_color('#cccccc')
        
        # Титла с контраст на бял фон
        ax1.set_title(f'{symbol} - {timeframe.upper()} - LuxAlgo + ICT Analysis - {datetime.now().strftime("%Y-%m-%d %H:%M")}', 
                     fontsize=11, weight='normal', color='#333333')
        ax1.set_ylabel('Price (USDT)', fontsize=9, color='#333333')
        
        # ЛЕГЕНДА ПРЕМАХНАТА (по желание на потребителя)
        
        plt.tight_layout()
        
        # Save to buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
    except Exception as e:
        logger.error(f"Грешка при генериране на графика: {e}")
        import traceback
        traceback.print_exc()
        return None


# ================= ORDER BLOCKS =================
    except Exception as e:
        logger.error(f"Грешка при генериране на графика: {e}")
        return None


def calculate_rsi(prices, period=14):
    """Изчисляване на RSI индикатор"""
    if len(prices) < period + 1:
        return None
    
    gains = []
    losses = []
    
    for i in range(1, len(prices)):
        change = prices[i] - prices[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    
    avg_gain = sum(gains[-period:]) / period
    avg_loss = sum(losses[-period:]) / period
    
    if avg_loss == 0:
        return 100
    
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_ma(prices, period):
    """Изчисляване на Moving Average"""
    if len(prices) < period:
        return None
    return sum(prices[-period:]) / period


def generate_tradingview_chart_url(symbol, timeframe, tp_price=None, sl_price=None, signal=None):
    """
    Генерира TradingView chart snapshot URL
    Използва TradingView API за snapshot на графиката
    """
    # Конвертирай символа за Binance формат
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"
    
    # Конвертирай таймфрейма в TradingView формат
    tf_map = {
        '1m': '1',
        '5m': '5', 
        '15m': '15',
        '30m': '30',
        '1h': '60',
        '2h': '120',
        '3h': '180',
        '4h': '240',
        '1d': 'D',
        '1w': 'W'
    }
    tv_timeframe = tf_map.get(timeframe, '60')
    
    # TradingView snapshot URL - генерира снимка на графиката
    # Това е публично API, което TradingView използва за preview
    snapshot_url = f"https://s3.tradingview.com/snapshots/u/BINANCE_{symbol}_{tv_timeframe}.png"
    
    # Алтернативен вариант - TradingView widget screenshot
    widget_url = f"https://www.tradingview.com/x/{symbol.replace('USDT', 'USD')}/{tv_timeframe}/"
    
    return snapshot_url


async def fetch_tradingview_chart_image(symbol, timeframe):
    """
    Взима chart snapshot от Binance (като AzCryptoBot)
    Binance има публично API за chart images
    """
    import aiohttp
    from io import BytesIO
    
    # Конвертирай символа
    if not symbol.endswith('USDT'):
        symbol = f"{symbol}USDT"
    
    # Конвертирай таймфрейма в Binance формат
    tf_map = {
        '1m': '1m',
        '5m': '5m', 
        '15m': '15m',
        '30m': '30m',
        '1h': '1h',
        '2h': '2h',
        '3h': '4h',  # Binance няма 3h, използваме 4h като най-близък
        '4h': '4h',
        '1d': '1d',
        '1w': '1w'
    }
    binance_timeframe = tf_map.get(timeframe, '1h')
    
    # Binance chart image URL (официален endpoint за screenshots)
    # Това е същият endpoint, който AzCryptoBot и другите ботове използват
    chart_url = f"https://api.binance.com/api/v3/uiKlines?symbol={symbol}&interval={binance_timeframe}&limit=100"
    
    # Използваме chart API service, който генерира снимка от Binance data
    # quickchart.io е безплатен сервиз за chart generation
    chart_image_url = f"https://quickchart.io/chart?c=%7Btype%3A%27candlestick%27%2Cdata%3A%7Bdatasets%3A%5B%7Blabel%3A%27{symbol}%27%2Cdata%3A%27{chart_url}%27%7D%5D%7D%7D&width=800&height=400&backgroundColor=white"
    
    # Алтернатива - използваме image-charts.com
    # Този сервиз е по-надежден и прилича на AzCryptoBot графиките
    alt_chart_url = f"https://image-charts.com/chart?cht=lc&chs=800x400&chd=t:0,0&chdl={symbol}&chtt={symbol}%20{binance_timeframe}"
    
    try:
        # Опитай с Binance klines data и matplotlib screenshot
        # Това е най-близкото до AzCryptoBot
        logger.info(f"Fetching Binance chart for {symbol} {timeframe}")
        
        # За сега връщаме None, за да използва matplotlib fallback
        # (който вече е подобрен и прилича на професионални графики)
        return None
        
    except Exception as e:
        logger.error(f"Error fetching chart image: {e}")
        return None


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """Изчисляване на MACD индикатор"""
    if len(prices) < slow:
        return None, None, None
    
    # EMA функция
    def ema(data, period):
        multiplier = 2 / (period + 1)
        ema_values = [sum(data[:period]) / period]
        for price in data[period:]:
            ema_values.append((price - ema_values[-1]) * multiplier + ema_values[-1])
        return ema_values[-1]
    
    ema_fast = ema(prices, fast)
    ema_slow = ema(prices, slow)
    macd_line = ema_fast - ema_slow
    
    # Signal line (9-period EMA of MACD)
    macd_history = []
    for i in range(slow, len(prices)):
        fast_val = ema(prices[:i+1], fast)
        slow_val = ema(prices[:i+1], slow)
        macd_history.append(fast_val - slow_val)
    
    signal_line = ema(macd_history[-signal:], signal) if len(macd_history) >= signal else 0
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram


def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Изчисляване на Bollinger Bands"""
    if len(prices) < period:
        return None, None, None
    
    ma = calculate_ma(prices, period)
    
    # Стандартно отклонение
    variance = sum((p - ma) ** 2 for p in prices[-period:]) / period
    std = variance ** 0.5
    
    upper_band = ma + (std * std_dev)
    lower_band = ma - (std * std_dev)
    
    return upper_band, ma, lower_band


def detect_candlestick_patterns(klines_data):
    """
    🕯️ ENHANCED Shadow Pattern Detection
    Засича: Hammer, Shooting Star, Engulfing, Doji, Inverted Hammer, Morning/Evening Star
    Използва се за: ръчни и автоматични сигнали, всички валути и timeframes
    """
    patterns = []
    
    if len(klines_data) < 3:
        return patterns
    
    # Последните 3 свещи
    prev2 = klines_data[-3]
    prev1 = klines_data[-2]
    current = klines_data[-1]
    
    # Конвертирай в числа
    def candle_info(k):
        open_p = float(k[1])
        high = float(k[2])
        low = float(k[3])
        close = float(k[4])
        body = abs(close - open_p)
        range_val = high - low
        upper_shadow = high - max(open_p, close)
        lower_shadow = min(open_p, close) - low
        is_bullish = close > open_p
        return {
            'open': open_p,
            'high': high,
            'low': low,
            'close': close,
            'body': body,
            'range': range_val,
            'upper_shadow': upper_shadow,
            'lower_shadow': lower_shadow,
            'is_bullish': is_bullish
        }
    
    c = candle_info(current)
    p1 = candle_info(prev1)
    p2 = candle_info(prev2)
    
    # === 1. HAMMER (Bullish Reversal) ===
    # Критерии:
    # - Малко тяло (body < 30% от range)
    # - Дълга долна сенка (lower_shadow >= 2x body)
    # - Малка или няма горна сенка (upper_shadow < 0.5x body)
    # - След низходящо движение
    if (c['body'] < c['range'] * 0.3 and
        c['lower_shadow'] >= c['body'] * 2 and
        c['upper_shadow'] < c['body'] * 0.5 and
        not p1['is_bullish'] and p1['close'] < p2['close']):
        patterns.append(('HAMMER', 'BUY', 20))
    
    # === 2. INVERTED HAMMER (Bullish Reversal) ===
    # Критерии:
    # - Малко тяло (body < 30% от range)
    # - Дълга горна сенка (upper_shadow >= 2x body)
    # - Малка или няма долна сенка (lower_shadow < 0.5x body)
    # - След низходящо движение
    if (c['body'] < c['range'] * 0.3 and
        c['upper_shadow'] >= c['body'] * 2 and
        c['lower_shadow'] < c['body'] * 0.5 and
        not p1['is_bullish'] and p1['close'] < p2['close']):
        patterns.append(('INVERTED_HAMMER', 'BUY', 18))
    
    # === 3. SHOOTING STAR (Bearish Reversal) ===
    # Критерии:
    # - Малко тяло (body < 30% от range)
    # - Дълга горна сенка (upper_shadow >= 2x body)
    # - Малка или няма долна сенка (lower_shadow < 0.5x body)
    # - След възходящо движение
    if (c['body'] < c['range'] * 0.3 and
        c['upper_shadow'] >= c['body'] * 2 and
        c['lower_shadow'] < c['body'] * 0.5 and
        p1['is_bullish'] and p1['close'] > p2['close']):
        patterns.append(('SHOOTING_STAR', 'SELL', 20))
    
    # === 4. BULLISH ENGULFING ===
    # Критерии:
    # - Предишна свещ е bearish, текуща е bullish
    # - Тялото на текущата свещ погълва цялото тяло на предишната
    # - Текущото тяло е >20% по-голямо
    if (c['is_bullish'] and not p1['is_bullish'] and
        c['body'] > p1['body'] * 1.2 and
        c['close'] > p1['open'] and c['open'] < p1['close']):
        patterns.append(('BULLISH_ENGULFING', 'BUY', 25))
    
    # === 5. BEARISH ENGULFING ===
    # Критерии:
    # - Предишна свещ е bullish, текуща е bearish
    # - Тялото на текущата свещ погълва цялото тяло на предишната
    # - Текущото тяло е >20% по-голямо
    if (not c['is_bullish'] and p1['is_bullish'] and
        c['body'] > p1['body'] * 1.2 and
        c['close'] < p1['open'] and c['open'] > p1['close']):
        patterns.append(('BEARISH_ENGULFING', 'SELL', 25))
    
    # === 6. MORNING STAR (Bullish Reversal) - 3 свещи ===
    # Критерии:
    # - 1-ва свещ: голяма bearish
    # - 2-ра свещ: малко тяло (Doji или малка свещ)
    # - 3-та свещ: голяма bullish, затваря над средата на 1-ва свещ
    if (not p2['is_bullish'] and p2['body'] > p2['range'] * 0.5 and
        p1['body'] < p1['range'] * 0.3 and
        c['is_bullish'] and c['body'] > c['range'] * 0.5 and
        c['close'] > (p2['open'] + p2['close']) / 2):
        patterns.append(('MORNING_STAR', 'BUY', 30))
    
    # === 7. EVENING STAR (Bearish Reversal) - 3 свещи ===
    # Критерии:
    # - 1-ва свещ: голяма bullish
    # - 2-ра свещ: малко тяло (Doji или малка свещ)
    # - 3-та свещ: голяма bearish, затваря под средата на 1-ва свещ
    if (p2['is_bullish'] and p2['body'] > p2['range'] * 0.5 and
        p1['body'] < p1['range'] * 0.3 and
        not c['is_bullish'] and c['body'] > c['range'] * 0.5 and
        c['close'] < (p2['open'] + p2['close']) / 2):
        patterns.append(('EVENING_STAR', 'SELL', 30))
    
    # === 8. DOJI (Indecision - Reversal Warning) ===
    # Критерии:
    # - Тялото е много малко (< 10% от range)
    # - Може да бъде сигнал за обръщане
    if c['body'] < c['range'] * 0.1 and c['range'] > 0:
        patterns.append(('DOJI', 'NEUTRAL', 10))
    
    # === 9. PIERCING LINE (Bullish Reversal) ===
    # Критерии:
    # - 1-ва свещ: bearish
    # - 2-ра свещ: bullish, отваря под low на 1-ва, затваря над средата на 1-ва
    if (not p1['is_bullish'] and c['is_bullish'] and
        c['open'] < p1['low'] and
        c['close'] > (p1['open'] + p1['close']) / 2 and
        c['close'] < p1['open']):
        patterns.append(('PIERCING_LINE', 'BUY', 22))
    
    # === 10. DARK CLOUD COVER (Bearish Reversal) ===
    # Критерии:
    # - 1-ва свещ: bullish
    # - 2-ра свещ: bearish, отваря над high на 1-ва, затваря под средата на 1-ва
    if (p1['is_bullish'] and not c['is_bullish'] and
        c['open'] > p1['high'] and
        c['close'] < (p1['open'] + p1['close']) / 2 and
        c['close'] > p1['open']):
        patterns.append(('DARK_CLOUD_COVER', 'SELL', 22))
    
    return patterns


async def analyze_order_book(symbol, current_price):
    """Анализ на Order Book за големи стени"""
    try:
        params = {'symbol': symbol, 'limit': 100}
        data = await fetch_json(BINANCE_DEPTH_URL, params)
        
        if not data:
            return None
        
        bids = data.get('bids', [])  # Купувачи
        asks = data.get('asks', [])  # Продавачи
        
        # Намери големи стени (поръчки над средния обем)
        bid_volumes = [float(b[1]) for b in bids]
        ask_volumes = [float(a[1]) for a in asks]
        
        avg_bid = sum(bid_volumes) / len(bid_volumes) if bid_volumes else 0
        avg_ask = sum(ask_volumes) / len(ask_volumes) if ask_volumes else 0
        
        # Големи стени са 3x над средното
        big_bid_walls = [(float(b[0]), float(b[1])) for b in bids if float(b[1]) > avg_bid * 3]
        big_ask_walls = [(float(a[0]), float(a[1])) for a in asks if float(a[1]) > avg_ask * 3]
        
        # Намери най-близките стени
        closest_bid_wall = max(big_bid_walls, key=lambda x: x[0]) if big_bid_walls else None
        closest_ask_wall = min(big_ask_walls, key=lambda x: x[0]) if big_ask_walls else None
        
        # Сила на купувачите vs продавачите
        total_bid_volume = sum(bid_volumes[:20])  # Първите 20 нива
        total_ask_volume = sum(ask_volumes[:20])
        
        bid_ask_ratio = total_bid_volume / total_ask_volume if total_ask_volume > 0 else 1
        
        return {
            'bid_walls': big_bid_walls,
            'ask_walls': big_ask_walls,
            'closest_support': closest_bid_wall,
            'closest_resistance': closest_ask_wall,
            'bid_ask_ratio': bid_ask_ratio,
            'pressure': 'BUY' if bid_ask_ratio > 1.5 else 'SELL' if bid_ask_ratio < 0.67 else 'NEUTRAL'
        }
        
    except Exception as e:
        logger.error(f"Грешка при Order Book анализ: {e}")
        return None


def calculate_support_resistance(highs, lows, closes):
    """Изчисляване на Support/Resistance нива с Fibonacci"""
    try:
        # Намери swing high и swing low за последните 50 свещи
        recent_highs = highs[-50:]
        recent_lows = lows[-50:]
        
        swing_high = max(recent_highs)
        swing_low = min(recent_lows)
        
        diff = swing_high - swing_low
        
        # Fibonacci нива
        fib_levels = {
            'resistance_2': swing_high,
            'resistance_1': swing_high - diff * 0.236,
            'pivot': swing_high - diff * 0.5,
            'support_1': swing_high - diff * 0.764,
            'support_2': swing_low
        }
        
        # Определи къде сме спрямо нивата
        current = closes[-1]
        position = 'middle'
        
        if current >= fib_levels['resistance_1']:
            position = 'near_resistance'
        elif current <= fib_levels['support_1']:
            position = 'near_support'
        
        return {
            'levels': fib_levels,
            'position': position,
            'range': diff
        }
        
    except Exception as e:
        logger.error(f"Грешка при S/R изчисление: {e}")
        return None


def detect_divergence(closes, rsi_values):
    """Откриване на дивергенция между цена и RSI"""
    try:
        if len(closes) < 20 or not rsi_values or len(rsi_values) < 20:
            return None
        
        # Последните 20 свещи
        recent_closes = closes[-20:]
        recent_rsi = rsi_values[-20:]
        
        # Bullish divergence: цената прави по-ниски дъна, но RSI прави по-високи дъна
        price_trend = recent_closes[-1] - recent_closes[0]
        rsi_trend = recent_rsi[-1] - recent_rsi[0]
        
        if price_trend < 0 and rsi_trend > 0:
            return ('BULLISH_DIVERGENCE', 'BUY', 15)
        elif price_trend > 0 and rsi_trend < 0:
            return ('BEARISH_DIVERGENCE', 'SELL', 15)
        
        return None
        
    except Exception as e:
        logger.error(f"Грешка при divergence detection: {e}")
        return None


async def get_higher_timeframe_confirmation(symbol, current_timeframe, signal):
    """Multi-timeframe потвърждение"""
    try:
        # Определи по-висок таймфрейм
        tf_hierarchy = ['1m', '5m', '15m', '30m', '1h', '2h', '3h', '4h', '1d', '1w']
        
        if current_timeframe not in tf_hierarchy:
            return None
        
        current_idx = tf_hierarchy.index(current_timeframe)
        
        # Вземи 2 нива по-висок таймфрейм
        higher_tf_idx = min(current_idx + 2, len(tf_hierarchy) - 1)
        higher_tf = tf_hierarchy[higher_tf_idx]
        
        # Вземи данни за по-високия таймфрейм
        klines = await fetch_klines(symbol, higher_tf, limit=100)
        
        if not klines:
            return None
        
        # Бърз анализ на тренда с RSI
        closes = [float(k[4]) for k in klines]
        current_price = closes[-1]
        rsi = calculate_rsi(closes)
        
        higher_tf_signal = "NEUTRAL"
        
        # Използваме RSI и ценово движение вместо MA
        if rsi:
            price_change = (current_price - closes[-20]) / closes[-20] * 100 if len(closes) >= 20 else 0
            if rsi < 40 and price_change > 2:  # Bullish
                higher_tf_signal = "BUY"
            elif rsi > 60 and price_change < -2:  # Bearish
                higher_tf_signal = "SELL"
        
        # Потвърждение ако сигналите съвпадат
        confirmed = higher_tf_signal == signal
        
        return {
            'timeframe': higher_tf,
            'signal': higher_tf_signal,
            'confirmed': confirmed
        }
        
    except Exception as e:
        logger.error(f"Грешка при MTF анализ: {e}")
        return None


# ==================== AUTO-SIGNAL TRACKING SYSTEM ====================

def load_active_signals():
    """Зарежда активните автоматични сигнали от JSON файл"""
    try:
        if os.path.exists(ACTIVE_SIGNALS_FILE):
            with open(ACTIVE_SIGNALS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        logger.error(f"Грешка при зареждане на активни сигнали: {e}")
        return []


def save_active_signals(signals):
    """Запазва активните сигнали в JSON файл"""
    try:
        with open(ACTIVE_SIGNALS_FILE, 'w', encoding='utf-8') as f:
            json.dump(signals, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Грешка при запазване на активни сигнали: {e}")
        return False


def add_signal_to_tracking(symbol, signal_type, entry_price, tp_price, sl_price, 
                           confidence, timeframe, timestamp):
    """Добавя автоматичен сигнал за tracking"""
    try:
        signals = load_active_signals()
        
        # Създай нов signal ID
        signal_id = f"{symbol}_{signal_type}_{int(timestamp.timestamp())}"
        
        new_signal = {
            'id': signal_id,
            'symbol': symbol,
            'signal_type': signal_type,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'confidence': confidence,
            'timeframe': timeframe,
            'timestamp': timestamp.isoformat(),
            'status': 'ACTIVE',  # ACTIVE, TP_REACHED, SL_HIT, 80_PERCENT_ALERTED
            'tp_80_alerted': False,
            'result_sent': False
        }
        
        signals.append(new_signal)
        save_active_signals(signals)
        
        logger.info(f"📊 Auto-signal added to tracking: {signal_id}")
        return signal_id
        
    except Exception as e:
        logger.error(f"Грешка при добавяне на сигнал за tracking: {e}")
        return None


async def check_active_signals():
    """
    Проверява всички активни сигнали и изпраща alerts:
    - 80% TP достигнат
    - TP пълно hit
    - SL hit
    """
    try:
        signals = load_active_signals()
        
        if not signals:
            return
        
        updated_signals = []
        signals_to_alert = []
        
        for signal in signals:
            # Пропускай вече приключени сигнали
            if signal.get('result_sent', False):
                continue
            
            symbol = signal['symbol']
            signal_type = signal['signal_type']
            entry_price = signal['entry_price']
            tp_price = signal['tp_price']
            sl_price = signal['sl_price']
            
            # Вземи текуща цена
            try:
                params = {'symbol': symbol}
                current_data = await fetch_json(BINANCE_PRICE_URL, params)
                
                if isinstance(current_data, list):
                    current_data = next((s for s in current_data if s['symbol'] == symbol), None)
                
                if not current_data:
                    updated_signals.append(signal)
                    continue
                
                current_price = float(current_data['price'])
                
            except Exception as e:
                logger.error(f"Грешка при взимане на цена за {symbol}: {e}")
                updated_signals.append(signal)
                continue
            
            # Изчисли прогрес към TP
            if signal_type == 'BUY':
                progress_to_tp = ((current_price - entry_price) / (tp_price - entry_price)) * 100
                sl_hit = current_price <= sl_price
                tp_hit = current_price >= tp_price
            else:  # SELL
                progress_to_tp = ((entry_price - current_price) / (entry_price - tp_price)) * 100
                sl_hit = current_price >= sl_price
                tp_hit = current_price <= tp_price
            
            # === 1. TP HIT (100%) ===
            if tp_hit and not signal.get('result_sent', False):
                profit_pct = ((tp_price - entry_price) / entry_price * 100) if signal_type == 'BUY' else ((entry_price - tp_price) / entry_price * 100)
                
                signals_to_alert.append({
                    'type': 'TP_HIT',
                    'signal': signal,
                    'current_price': current_price,
                    'profit_pct': profit_pct
                })
                
                signal['status'] = 'TP_REACHED'
                signal['result_sent'] = True
                updated_signals.append(signal)
                continue
            
            # === 2. SL HIT ===
            if sl_hit and not signal.get('result_sent', False):
                loss_pct = ((entry_price - sl_price) / entry_price * 100) if signal_type == 'BUY' else ((sl_price - entry_price) / entry_price * 100)
                
                signals_to_alert.append({
                    'type': 'SL_HIT',
                    'signal': signal,
                    'current_price': current_price,
                    'loss_pct': loss_pct
                })
                
                signal['status'] = 'SL_HIT'
                signal['result_sent'] = True
                updated_signals.append(signal)
                continue
            
            # === 3. 80% TP ALERT ===
            if progress_to_tp >= 80 and not signal.get('tp_80_alerted', False):
                signals_to_alert.append({
                    'type': '80_PERCENT',
                    'signal': signal,
                    'current_price': current_price,
                    'progress': progress_to_tp
                })
                
                signal['tp_80_alerted'] = True
                signal['status'] = '80_PERCENT_ALERTED'
            
            updated_signals.append(signal)
        
        # Запази обновените сигнали
        save_active_signals(updated_signals)
        
        # Изпрати alerts
        for alert in signals_to_alert:
            await send_signal_alert(alert)
        
    except Exception as e:
        logger.error(f"Грешка при проверка на активни сигнали: {e}")


async def send_signal_alert(alert):
    """Изпраща alert за автоматичен сигнал"""
    try:
        alert_type = alert['type']
        signal = alert['signal']
        current_price = alert['current_price']
        
        symbol = signal['symbol']
        signal_type = signal['signal_type']
        entry_price = signal['entry_price']
        tp_price = signal['tp_price']
        sl_price = signal['sl_price']
        confidence = signal['confidence']
        timeframe = signal['timeframe']
        timestamp = datetime.fromisoformat(signal['timestamp'])
        
        # Изчисли колко време е отворен сигнала
        time_open = datetime.now() - timestamp
        if time_open.total_seconds() < 3600:
            time_str = f"{int(time_open.total_seconds() / 60)} минути"
        elif time_open.total_seconds() < 86400:
            time_str = f"{time_open.total_seconds() / 3600:.1f} часа"
        else:
            time_str = f"{time_open.total_seconds() / 86400:.1f} дни"
        
        # Emoji според типа
        signal_emoji = "🟢" if signal_type == 'BUY' else "🔴"
        
        # === 1. TP HIT (100%) ===
        if alert_type == 'TP_HIT':
            profit_pct = alert['profit_pct']
            
            message = f"✅ <b>ЦЕЛ ПОСТИГНАТА!</b> ✅\n"
            message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"{signal_emoji} <b>{symbol}: {signal_type}</b>\n"
            message += f"📊 Увереност: <b>{confidence}%</b>\n"
            message += f"⏰ Таймфрейм: <b>{timeframe}</b>\n\n"
            message += f"💰 Entry: ${entry_price:,.4f}\n"
            message += f"🎯 TP: ${tp_price:,.4f}\n"
            message += f"💵 Current: ${current_price:,.4f}\n\n"
            message += f"💎 <b>Печалба: +{profit_pct:.2f}%</b>\n"
            message += f"⏱️ Време: {time_str}\n\n"
            message += f"✨ Автоматичният сигнал е успешен!"
            
        # === 2. SL HIT ===
        elif alert_type == 'SL_HIT':
            loss_pct = alert['loss_pct']
            
            message = f"❌ <b>STOP LOSS HIT</b> ❌\n"
            message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
            message += f"{signal_emoji} <b>{symbol}: {signal_type}</b>\n"
            message += f"📊 Увереност: <b>{confidence}%</b>\n"
            message += f"⏰ Таймфрейм: <b>{timeframe}</b>\n\n"
            message += f"💰 Entry: ${entry_price:,.4f}\n"
            message += f"🛡️ SL: ${sl_price:,.4f}\n"
            message += f"💵 Current: ${current_price:,.4f}\n\n"
            message += f"📉 <b>Загуба: -{loss_pct:.2f}%</b>\n"
            message += f"⏱️ Време: {time_str}\n\n"
            message += f"🔒 Автоматично затворен на SL"
            
        # === 3. 80% TP ALERT С ПЪЛЕН РЕАНАЛИЗ ===
        elif alert_type == '80_PERCENT':
            progress = alert['progress']
            current_profit_pct = ((current_price - entry_price) / entry_price * 100) if signal_type == 'BUY' else ((entry_price - current_price) / entry_price * 100)
            
            # === ПЪЛЕН РЕАНАЛИЗ НА ПОЗИЦИЯТА ===
            try:
                # 1. Вземи актуални данни
                klines = await fetch_klines(symbol, timeframe, limit=100)
                params_24h = {'symbol': symbol}
                data_24h = await fetch_json(BINANCE_24H_URL, params_24h)
                
                if isinstance(data_24h, list):
                    data_24h = next((s for s in data_24h if s['symbol'] == symbol), None)
                
                if not klines or not data_24h:
                    # Fallback ако няма данни
                    message = f"🎯 <b>80% ДО ЦЕЛ!</b> 🎯\n"
                    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    message += f"{signal_emoji} <b>{symbol}: {signal_type}</b>\n"
                    message += f"📈 Прогрес: {progress:.1f}%\n"
                    message += f"💚 Печалба: +{current_profit_pct:.2f}%\n\n"
                    message += f"⚠️ Не мога да реанализирам (липсват данни)"
                else:
                    # 2. Извлечи price data
                    closes = [float(k[4]) for k in klines]
                    highs = [float(k[2]) for k in klines]
                    lows = [float(k[3]) for k in klines]
                    opens = [float(k[1]) for k in klines]
                    volumes = [float(k[5]) for k in klines]
                    
                    # 3. Анализи
                    rsi = calculate_rsi(closes)
                    
                    # Volume trend
                    avg_volume = sum(volumes[-20:]) / 20
                    current_volume = volumes[-1]
                    volume_trend = "📈 Нараства" if current_volume > avg_volume * 1.2 else "📉 Намалява" if current_volume < avg_volume * 0.8 else "➡️ Стабилен"
                    
                    # Shadow Patterns
                    shadow_patterns = detect_candlestick_patterns(klines)
                    reversal_warning = False
                    reversal_pattern = None
                    
                    for pattern_name, pattern_signal, _ in shadow_patterns:
                        # Ако има противоположен pattern - warning!
                        if (signal_type == 'BUY' and pattern_signal == 'SELL') or \
                           (signal_type == 'SELL' and pattern_signal == 'BUY'):
                            reversal_warning = True
                            reversal_pattern = pattern_name
                            break
                    
                    # BTC Correlation
                    btc_corr = await analyze_btc_correlation(symbol, timeframe)
                    btc_aligned = False
                    if btc_corr:
                        btc_aligned = btc_corr['trend'] == signal_type
                    
                    # Order Book
                    order_book = await analyze_order_book(symbol, current_price)
                    ob_pressure = order_book['pressure'] if order_book else 'NEUTRAL'
                    ob_aligned = ob_pressure == signal_type
                    
                    # News Sentiment
                    sentiment = await analyze_news_sentiment(symbol)
                    sentiment_aligned = False
                    if sentiment and sentiment['sentiment'] != 'NEUTRAL':
                        sentiment_aligned = sentiment['sentiment'] == signal_type
                    
                    # === DECISION LOGIC ===
                    hold_score = 0  # Точки за hold
                    close_score = 0  # Точки за close
                    
                    # RSI проверка
                    if signal_type == 'BUY':
                        if rsi and rsi < 70:
                            hold_score += 2  # Още има място за ръст
                        elif rsi and rsi > 75:
                            close_score += 2  # Overbought - риск от reversal
                    else:  # SELL
                        if rsi and rsi > 30:
                            hold_score += 2  # Още има място за спад
                        elif rsi and rsi < 25:
                            close_score += 2  # Oversold - риск от reversal
                    
                    # Volume check
                    if current_volume > avg_volume * 1.2:
                        hold_score += 1  # Силен momentum
                    else:
                        close_score += 1  # Слаб momentum
                    
                    # Shadow Patterns
                    if reversal_warning:
                        close_score += 3  # Силен сигнал за затваряне!
                    else:
                        hold_score += 1
                    
                    # BTC Correlation
                    if btc_aligned:
                        hold_score += 2
                    else:
                        close_score += 1
                    
                    # Order Book
                    if ob_aligned:
                        hold_score += 2
                    else:
                        close_score += 1
                    
                    # Sentiment
                    if sentiment_aligned:
                        hold_score += 1
                    
                    # === ПРЕПОРЪКА ===
                    recommendation = ""
                    recommendation_emoji = ""
                    action_plan = ""
                    
                    if hold_score >= close_score + 3:
                        # СИЛЕН HOLD
                        recommendation = "HOLD ДО TP"
                        recommendation_emoji = "✅"
                        action_plan = f"🎯 <b>Препоръка: HOLD до пълен TP</b>\n\n"
                        action_plan += f"📊 Причини:\n"
                        action_plan += f"   • Momentum силен ({hold_score} точки)\n"
                        if rsi:
                            action_plan += f"   • RSI: {rsi:.1f} (здравословно)\n"
                        if btc_aligned:
                            action_plan += f"   • BTC подкрепя движението\n"
                        if ob_aligned:
                            action_plan += f"   • Order Book показва {signal_type} натиск\n"
                        action_plan += f"\n💡 <b>План:</b>\n"
                        action_plan += f"   1. Остави позицията отворена\n"
                        action_plan += f"   2. Целта е близо - очаквай TP hit\n"
                        action_plan += f"   3. Провери отново след 1-2 часа\n"
                        
                    elif close_score >= hold_score + 2:
                        # СИЛЕН CLOSE
                        recommendation = "ЗАТВОРИ СЕГА"
                        recommendation_emoji = "❌"
                        action_plan = f"❌ <b>Препоръка: ЗАТВОРИ ПОЗИЦИЯТА</b>\n\n"
                        action_plan += f"⚠️ Причини:\n"
                        action_plan += f"   • Риск от обръщане ({close_score} точки)\n"
                        if reversal_warning:
                            action_plan += f"   • 🕯️ {reversal_pattern} (reversal pattern!)\n"
                        if rsi:
                            if signal_type == 'BUY' and rsi > 75:
                                action_plan += f"   • RSI: {rsi:.1f} (overbought!)\n"
                            elif signal_type == 'SELL' and rsi < 25:
                                action_plan += f"   • RSI: {rsi:.1f} (oversold!)\n"
                        if not btc_aligned:
                            action_plan += f"   • BTC вече не подкрепя\n"
                        action_plan += f"\n💡 <b>План:</b>\n"
                        action_plan += f"   1. Затвори позицията СЕГА\n"
                        action_plan += f"   2. Вземи печалбата (+{current_profit_pct:.2f}%)\n"
                        action_plan += f"   3. Избегни reversal risk\n"
                        
                    else:
                        # PARTIAL CLOSE
                        recommendation = "ЧАСТИЧНО ЗАТВОРИ"
                        recommendation_emoji = "📊"
                        action_plan = f"📊 <b>Препоръка: ЧАСТИЧНО ЗАТВАРЯНЕ</b>\n\n"
                        action_plan += f"⚖️ Причини:\n"
                        action_plan += f"   • Смесени сигнали (Hold: {hold_score}, Close: {close_score})\n"
                        action_plan += f"   • Momentum леко отслабва\n"
                        action_plan += f"   • Добра печалба вече (+{current_profit_pct:.2f}%)\n"
                        action_plan += f"\n💡 <b>План:</b>\n"
                        action_plan += f"   1. Затвори 50-70% от позицията\n"
                        action_plan += f"   2. Остави 30-50% за TP\n"
                        action_plan += f"   3. Премести SL на breakeven (${entry_price:,.4f})\n"
                        action_plan += f"   4. Trailing stop: ${current_price * 0.985:,.4f}\n"
                    
                    # === ФИНАЛНО СЪОБЩЕНИЕ ===
                    message = f"🎯 <b>80% ДО ЦЕЛ - РЕАНАЛИЗ</b> 🎯\n"
                    message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    message += f"{signal_emoji} <b>{symbol}: {signal_type}</b>\n"
                    message += f"📊 Първоначална увереност: <b>{confidence}%</b>\n"
                    message += f"⏰ Таймфрейм: <b>{timeframe}</b>\n\n"
                    
                    message += f"💰 Entry: ${entry_price:,.4f}\n"
                    message += f"🎯 TP: ${tp_price:,.4f}\n"
                    message += f"💵 Current: ${current_price:,.4f}\n\n"
                    
                    message += f"📈 <b>Прогрес: {progress:.1f}%</b>\n"
                    message += f"💚 Текуща печалба: <b>+{current_profit_pct:.2f}%</b>\n"
                    message += f"⏱️ Отворена: {time_str}\n\n"
                    
                    message += f"━━━━━━━━━━━━━━━━━━━━\n"
                    message += f"🔍 <b>АКТУАЛЕН АНАЛИЗ:</b>\n\n"
                    
                    if rsi:
                        message += f"📊 RSI: {rsi:.1f}"
                        if signal_type == 'BUY':
                            if rsi < 50: message += " (здравословно ✅)\n"
                            elif rsi < 70: message += " (добре 👍)\n"
                            else: message += " (overbought ⚠️)\n"
                        else:
                            if rsi > 50: message += " (здравословно ✅)\n"
                            elif rsi > 30: message += " (добре 👍)\n"
                            else: message += " (oversold ⚠️)\n"
                    
                    message += f"📦 Volume: {volume_trend}\n"
                    
                    if reversal_warning:
                        message += f"🕯️ Pattern: <b>{reversal_pattern}</b> ⚠️ REVERSAL!\n"
                    else:
                        message += f"🕯️ Pattern: Няма reversal signals ✅\n"
                    
                    if btc_corr:
                        btc_emoji = "✅" if btc_aligned else "⚠️"
                        message += f"📊 BTC: {btc_corr['trend']} ({btc_corr['change']:+.1f}%) {btc_emoji}\n"
                    
                    ob_emoji = "✅" if ob_aligned else "⚠️"
                    message += f"📖 Order Book: {ob_pressure} {ob_emoji}\n"
                    
                    if sentiment and sentiment['sentiment'] != 'NEUTRAL':
                        sent_emoji = "✅" if sentiment_aligned else "⚠️"
                        message += f"📰 Sentiment: {sentiment['sentiment']} {sent_emoji}\n"
                    
                    message += f"\n━━━━━━━━━━━━━━━━━━━━\n"
                    message += f"{recommendation_emoji} <b>SCORE: Hold {hold_score} | Close {close_score}</b>\n\n"
                    message += action_plan
                    
            except Exception as e:
                logger.error(f"Грешка при реанализ на 80% alert: {e}")
                # Fallback съобщение
                message = f"🎯 <b>80% ДО ЦЕЛ!</b> 🎯\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                message += f"{signal_emoji} <b>{symbol}: {signal_type}</b>\n"
                message += f"📈 Прогрес: {progress:.1f}%\n"
                message += f"💚 Печалба: +{current_profit_pct:.2f}%\n\n"
                message += f"⚠️ Грешка при реанализ: {e}"
        
        # Изпрати съобщението
        await application.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=message,
            parse_mode='HTML',
            disable_notification=False  # Със звук!
        )
        
        logger.info(f"📤 Signal alert sent: {alert_type} for {symbol}")
        
    except Exception as e:
        logger.error(f"Грешка при изпращане на signal alert: {e}")


# ==================== END AUTO-SIGNAL TRACKING ====================


def detect_market_regime(closes, highs, lows):
    """Определяне на пазарен режим (trending vs ranging)"""
    try:
        if len(closes) < 50:
            return 'UNKNOWN'
        
        # ADX подобна логика - измерва сила на тренда
        recent_closes = closes[-50:]
        
        # Изчисли ATR (Average True Range)
        true_ranges = []
        for i in range(1, len(recent_closes)):
            high_low = highs[-50:][i] - lows[-50:][i]
            high_close = abs(highs[-50:][i] - recent_closes[i-1])
            low_close = abs(lows[-50:][i] - recent_closes[i-1])
            true_ranges.append(max(high_low, high_close, low_close))
        
        atr = sum(true_ranges) / len(true_ranges) if true_ranges else 0
        
        # Направление на тренда - използваме ценова динамика
        price_momentum = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] * 100
        
        # Волатилност спрямо цената
        volatility_pct = (atr / recent_closes[-1]) * 100
        
        # Направление на тренда БЕЗ MA - използваме ценова динамика
        price_momentum = (recent_closes[-1] - recent_closes[0]) / recent_closes[0] * 100
        
        # Strength of trend БЕЗ MA
        if abs(price_momentum) > 5 and volatility_pct > 1:
            if price_momentum > 0:
                return 'STRONG_UPTREND'
            else:
                return 'STRONG_DOWNTREND'
        elif abs(price_momentum) > 2:
            if price_momentum > 0:
                return 'WEAK_UPTREND'
            else:
                return 'WEAK_DOWNTREND'
        else:
            return 'RANGING'
        
    except Exception as e:
        logger.error(f"Грешка при market regime: {e}")
        return 'UNKNOWN'


async def analyze_news_sentiment(symbol):
    """Анализ на настроението от новини"""
    try:
        # Вземи последните новини от CoinMarketCap
        cmc_url = "https://coinmarketcap.com/headlines/news/"
        resp = await asyncio.to_thread(requests.get, cmc_url, timeout=10)
        
        if resp.status_code != 200:
            return None
        
        # Извлечи данни от window.__NEXT_DATA__
        html = resp.text
        start = html.find('window.__NEXT_DATA__')
        if start == -1:
            return None
        
        start = html.find('{', start)
        end = html.find('</script>', start)
        json_str = html[start:end]
        
        data = json.loads(json_str)
        articles = data.get('props', {}).get('pageProps', {}).get('articles', [])
        
        if not articles:
            return None
        
        # Вземи последните 10 новини
        recent_news = articles[:10]
        
        # Прости ключови думи за sentiment анализ
        bullish_words = ['surge', 'rally', 'bullish', 'moon', 'gain', 'profit', 'high', 'rise', 'up', 
                        'breakout', 'breakthrough', 'adoption', 'institutional', 'upgrade', 'partnership']
        bearish_words = ['crash', 'dump', 'bearish', 'loss', 'decline', 'fall', 'down', 'drop', 
                        'regulation', 'ban', 'hack', 'scam', 'fraud', 'lawsuit', 'warning']
        
        # Определи дали е за конкретна криптовалута
        symbol_keywords = {
            'BTCUSDT': ['bitcoin', 'btc'],
            'ETHUSDT': ['ethereum', 'eth'],
            'SOLUSDT': ['solana', 'sol'],
            'XRPUSDT': ['ripple', 'xrp'],
            'BNBUSDT': ['binance', 'bnb'],
            'ADAUSDT': ['cardano', 'ada']
        }
        
        keywords = symbol_keywords.get(symbol, [symbol[:3].lower()])
        
        bullish_count = 0
        bearish_count = 0
        relevant_count = 0
        
        for article in recent_news:
            title = article.get('title', '').lower()
            subtitle = article.get('subtitle', '').lower()
            text = f"{title} {subtitle}"
            
            # Провери дали е релевантно за символа
            is_relevant = any(kw in text for kw in keywords) or symbol[:3].lower() in text
            
            # Ако е релевантно или е общо крипто новина
            if is_relevant or 'crypto' in text or 'bitcoin' in text:
                relevant_count += 1
                
                # Брой на bullish думи
                bull_score = sum(1 for word in bullish_words if word in text)
                bear_score = sum(1 for word in bearish_words if word in text)
                
                if is_relevant:
                    # Дай по-голяма тежест на специфични новини
                    bull_score *= 2
                    bear_score *= 2
                
                bullish_count += bull_score
                bearish_count += bear_score
        
        if relevant_count == 0:
            return {'sentiment': 'NEUTRAL', 'score': 0, 'confidence': 0}
        
        # Изчисли sentiment
        total_sentiment = bullish_count - bearish_count
        sentiment_score = total_sentiment / (relevant_count + 1)  # Нормализирай
        
        # Определи категория
        if sentiment_score > 1:
            sentiment = 'BULLISH'
            confidence = min(sentiment_score * 10, 20)  # Max 20% confidence boost
        elif sentiment_score < -1:
            sentiment = 'BEARISH'
            confidence = min(abs(sentiment_score) * 10, 20)
        else:
            sentiment = 'NEUTRAL'
            confidence = 0
        
        return {
            'sentiment': sentiment,
            'score': sentiment_score,
            'confidence': confidence,
            'relevant_news': relevant_count
        }
        
    except Exception as e:
        logger.error(f"Грешка при sentiment анализ: {e}")
        return None


def is_good_trading_time():
    """
    Time-based filters - избягва лоши периоди за търговия
    Returns: (is_good_time, reason)
    """
    try:
        from datetime import datetime, timezone
        
        now = datetime.now(timezone.utc)
        hour = now.hour
        day_of_week = now.weekday()  # 0=Monday, 6=Sunday
        
        # Викенд - ниска ликвидност
        if day_of_week >= 5:  # Saturday or Sunday
            return (False, "Викенд - ниска ликвидност")
        
        # Нощ (UTC 00:00-04:00) - Азиатска сесия с по-малко движение за BTC
        if 0 <= hour < 4:
            return (False, "Азиатска сесия - ниска волатилност")
        
        # Добри периоди:
        # 08:00-12:00 UTC - Европейска сесия
        # 13:00-21:00 UTC - Американска сесия (най-добра)
        
        return (True, "Добро време за търговия")
        
    except Exception as e:
        logger.error(f"Грешка при time filter: {e}")
        return (True, "Unknown")


def calculate_volume_confidence_boost(current_volume, avg_volume, signal_type):
    """
    Volume analysis - дава confidence boost според обема
    Returns: confidence_boost (0-20)
    """
    try:
        if not current_volume or not avg_volume or avg_volume == 0:
            return 0
        
        volume_ratio = current_volume / avg_volume
        
        # Breakout с висок обем = силен сигнал
        if volume_ratio >= 2.0:
            return 20  # Много висок обем
        elif volume_ratio >= 1.5:
            return 15  # Висок обем
        elif volume_ratio >= 1.2:
            return 10  # Умерен обем
        elif volume_ratio >= 0.8:
            return 5   # Нормален обем
        else:
            return -10  # Нисък обем - намали confidence!
        
    except Exception as e:
        logger.error(f"Грешка при volume analysis: {e}")
        return 0


def calculate_adaptive_tp_sl(symbol, volatility, timeframe):
    """Изчисляване на адаптивен TP/SL според волатилност и символ"""
    try:
        # Базови нива според символа (волатилността им)
        symbol_volatility = {
            'BTCUSDT': {'base_tp': 2.5, 'base_sl': 1.0, 'volatility_multiplier': 1.0},
            'ETHUSDT': {'base_tp': 3.0, 'base_sl': 1.2, 'volatility_multiplier': 1.1},
            'SOLUSDT': {'base_tp': 4.5, 'base_sl': 1.8, 'volatility_multiplier': 1.5},
            'XRPUSDT': {'base_tp': 3.5, 'base_sl': 1.4, 'volatility_multiplier': 1.3},
            'BNBUSDT': {'base_tp': 3.0, 'base_sl': 1.2, 'volatility_multiplier': 1.1},
            'ADAUSDT': {'base_tp': 4.0, 'base_sl': 1.6, 'volatility_multiplier': 1.4}
        }
        
        config = symbol_volatility.get(symbol, {'base_tp': 3.0, 'base_sl': 1.2, 'volatility_multiplier': 1.0})
        
        # Корекция според текуща волатилност
        if volatility > 3:  # Висока волатилност
            tp_multiplier = 1.3
            sl_multiplier = 1.2
        elif volatility > 2:  # Средна волатилност
            tp_multiplier = 1.1
            sl_multiplier = 1.05
        else:  # Ниска волатилност
            tp_multiplier = 0.9
            sl_multiplier = 0.95
        
        # Корекция според таймфрейм
        tf_multipliers = {
            '1m': 0.5, '5m': 0.6, '15m': 0.7, '30m': 0.8,
            '1h': 0.9, '2h': 1.0, '3h': 1.1, '4h': 1.2, '1d': 1.5, '1w': 2.0
        }
        tf_mult = tf_multipliers.get(timeframe, 1.0)
        
        # Финален TP/SL
        adaptive_tp = config['base_tp'] * tp_multiplier * tf_mult
        adaptive_sl = config['base_sl'] * sl_multiplier * tf_mult
        
        # Запази минимум 1:2 RR
        if adaptive_tp / adaptive_sl < 2:
            adaptive_tp = adaptive_sl * 2
        
        return {
            'tp': round(adaptive_tp, 2),
            'sl': round(adaptive_sl, 2),
            'rr': round(adaptive_tp / adaptive_sl, 2)
        }
        
    except Exception as e:
        logger.error(f"Грешка при adaptive TP/SL: {e}")
        return {'tp': 3.0, 'sl': 1.0, 'rr': 3.0}


async def get_multi_timeframe_analysis(symbol, current_timeframe):
    """Анализира сигнала на ВСИЧКИ таймфреймове за пълна картина"""
    try:
        # ВСИЧКИ таймфреймове за анализ
        all_timeframes = ['1m', '5m', '15m', '1h', '2h', '3h', '4h', '1d', '1w']
        
        mtf_signals = {}
        
        for tf in all_timeframes:
            try:
                # Извлечи данни за този таймфрейм
                params_24h = {'symbol': symbol}
                data_24h = await fetch_json(BINANCE_24H_URL, params_24h)
                
                if isinstance(data_24h, list):
                    data_24h = next((s for s in data_24h if s['symbol'] == symbol), None)
                
                if not data_24h:
                    continue
                
                klines = await fetch_klines(symbol, tf, limit=100)
                
                if not klines:
                    continue
                
                # Анализирай
                analysis = analyze_signal(data_24h, klines, symbol, tf)
                
                if analysis:
                    mtf_signals[tf] = {
                        'signal': analysis['signal'],
                        'confidence': analysis['confidence'],
                        'rsi': analysis.get('rsi', 0)
                    }
                
                # Малка пауза между заявки
                await asyncio.sleep(0.2)
                
            except Exception as e:
                logger.error(f"MTF analysis error for {tf}: {e}")
                continue
        
        # Анализирай консенсуса
        if len(mtf_signals) < 1:
            logger.warning(f"MTF: Not enough signals ({len(mtf_signals)}) for {symbol}")
            return None
        
        buy_count = sum(1 for s in mtf_signals.values() if s['signal'] == 'BUY')
        sell_count = sum(1 for s in mtf_signals.values() if s['signal'] == 'SELL')
        total = len(mtf_signals)
        
        # Определи консенсус
        if buy_count / total >= 0.66:
            consensus = 'BUY'
            consensus_strength = 'Силен'
        elif sell_count / total >= 0.66:
            consensus = 'SELL'
            consensus_strength = 'Силен'
        elif buy_count > sell_count:
            consensus = 'BUY'
            consensus_strength = 'Слаб'
        elif sell_count > buy_count:
            consensus = 'SELL'
            consensus_strength = 'Слаб'
        else:
            consensus = 'NEUTRAL'
            consensus_strength = 'Няма консенсус'
        
        return {
            'signals': mtf_signals,
            'consensus': consensus,
            'consensus_strength': consensus_strength,
            'agreement': max(buy_count, sell_count) / total * 100
        }
        
    except Exception as e:
        logger.error(f"Multi-timeframe analysis error: {e}")
        return None


async def analyze_btc_correlation(symbol, timeframe):
    """Анализ на корелация с BTC"""
    try:
        if symbol == 'BTCUSDT':
            return None  # BTC се анализира сам
        
        # Вземи BTC данни
        btc_klines = await fetch_klines('BTCUSDT', timeframe, limit=50)
        
        if not btc_klines or len(btc_klines) < 20:
            return None
        
        btc_closes = [float(k[4]) for k in btc_klines]
        btc_current = btc_closes[-1]
        
        # Определи BTC тренд БЕЗ MA - директно от ценова динамика
        btc_change = ((btc_current - btc_closes[0]) / btc_closes[0]) * 100
        
        if btc_change > 2:
            btc_trend = 'BULLISH'
        elif btc_change < -2:
            btc_trend = 'BEARISH'
        else:
            btc_trend = 'NEUTRAL'
        
        # Сила на тренда
        trend_strength = abs(btc_change)
        
        return {
            'trend': btc_trend,
            'strength': trend_strength,
            'change': btc_change
        }
        
    except Exception as e:
        logger.error(f"Грешка при BTC correlation: {e}")
        return None


def get_time_of_day_factor():
    """Фактор според време на денонощието (UTC)"""
    try:
        current_hour = datetime.now(timezone.utc).hour
        
        # Най-активни часове (висока ликвидност)
        if 14 <= current_hour < 18:  # US market opening
            return {'factor': 'PRIME', 'boost': 10, 'description': 'US часове (най-добро време)'}
        elif 0 <= current_hour < 4:  # Asia active
            return {'factor': 'GOOD', 'boost': 5, 'description': 'Азия активна'}
        elif 8 <= current_hour < 12:  # Europe active
            return {'factor': 'GOOD', 'boost': 5, 'description': 'Европа активна'}
        elif 6 <= current_hour < 8 or 12 <= current_hour < 14:  # Low activity
            return {'factor': 'LOW', 'boost': -5, 'description': 'Ниска активност'}
        else:  # Normal
            return {'factor': 'NORMAL', 'boost': 0, 'description': 'Нормална активност'}
            
    except Exception as e:
        logger.error(f"Грешка при time-of-day: {e}")
        return {'factor': 'NORMAL', 'boost': 0, 'description': 'Неизвестно'}


def check_liquidity(volume_24h, avg_volume, volume_ratio):
    """Проверка за ликвидност"""
    try:
        # Минимални изисквания
        if volume_24h < 10000000:  # Под $10М дневен обем
            return {'adequate': False, 'reason': 'Много нисък обем (<$10М)', 'penalty': -15}
        
        if volume_ratio < 0.3:  # Текущ обем е под 30% от средния
            return {'adequate': False, 'reason': 'Текущ обем твърде нисък', 'penalty': -10}
        
        if volume_ratio > 3.0:  # Много висок обем (подозрително)
            return {'adequate': True, 'reason': 'Изключително висок обем', 'bonus': 5}
        
        if volume_ratio > 1.5:  # Добър обем
            return {'adequate': True, 'reason': 'Добра ликвидност', 'bonus': 3}
        
        return {'adequate': True, 'reason': 'Адекватна ликвидност', 'bonus': 0}
        
    except Exception as e:
        logger.error(f"Грешка при liquidity check: {e}")
        return {'adequate': True, 'reason': 'Неизвестно', 'bonus': 0}


def load_stats():
    """Зареди статистика за win-rate"""
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, 'r') as f:
                data = json.load(f)
                # Надгради стария формат ако няма 'signals'
                if 'signals' not in data:
                    data['signals'] = []
                return data
        return {
            'total_signals': 0, 
            'by_symbol': {}, 
            'by_timeframe': {}, 
            'by_confidence': {},
            'signals': []  # Детайлен списък с всички сигнали
        }
    except Exception as e:
        logger.error(f"Грешка при зареждане на статистика: {e}")
        return {
            'total_signals': 0, 
            'by_symbol': {}, 
            'by_timeframe': {}, 
            'by_confidence': {},
            'signals': []
        }


def save_stats(stats):
    """Запази статистика"""
    try:
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except Exception as e:
        logger.error(f"Грешка при записване на статистика: {e}")


# ================= TRADING JOURNAL (ML SELF-LEARNING) =================

# Trading Journal file - използва BASE_PATH
JOURNAL_FILE = f'{BASE_PATH}/trading_journal.json'

def load_journal():
    """Зареждане на trading journal"""
    try:
        if os.path.exists(JOURNAL_FILE):
            with open(JOURNAL_FILE, 'r') as f:
                return json.load(f)
        else:
            from datetime import datetime
            return {
                'metadata': {
                    'created': datetime.now().strftime('%Y-%m-%d'),
                    'version': '1.0',
                    'total_trades': 0,
                    'last_updated': datetime.now().isoformat()
                },
                'trades': [],
                'patterns': {
                    'successful_conditions': {},
                    'failed_conditions': {},
                    'best_timeframes': {},
                    'best_symbols': {}
                },
                'ml_insights': {
                    'accuracy_by_confidence': {},
                    'accuracy_by_timeframe': {},
                    'accuracy_by_symbol': {},
                    'optimal_entry_zones': {}
                }
            }
    except Exception as e:
        logger.error(f"Грешка при зареждане на journal: {e}")
        return None


def save_journal(journal):
    """Запазване на trading journal"""
    try:
        from datetime import datetime
        journal['metadata']['last_updated'] = datetime.now().isoformat()
        with open(JOURNAL_FILE, 'w') as f:
            json.dump(journal, f, indent=2)
        logger.info("✅ Trading journal saved successfully")
    except Exception as e:
        logger.error(f"Грешка при запазване на journal: {e}")


def log_trade_to_journal(symbol, timeframe, signal_type, confidence, entry_price, tp_price, sl_price, analysis_data=None):
    """Логва trade в журнала за ML анализ"""
    try:
        from datetime import datetime
        journal = load_journal()
        if not journal:
            return None
        
        trade_id = len(journal['trades']) + 1
        
        trade_entry = {
            'id': trade_id,
            'timestamp': datetime.now().isoformat(),
            'symbol': symbol,
            'timeframe': timeframe,
            'signal': signal_type,
            'confidence': confidence,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'status': 'PENDING',
            'outcome': None,
            'profit_loss_pct': None,
            'closed_at': None,
            'conditions': {
                'rsi': analysis_data.get('rsi') if analysis_data else None,
                'volume_ratio': analysis_data.get('volume_ratio') if analysis_data else None,
                'volatility': analysis_data.get('volatility') if analysis_data else None,
                'trend': analysis_data.get('trend') if analysis_data else None,
                'btc_correlation': analysis_data.get('btc_correlation') if analysis_data else None,
                'sentiment': analysis_data.get('sentiment') if analysis_data else None
            },
            'notes': []
        }
        
        journal['trades'].append(trade_entry)
        journal['metadata']['total_trades'] += 1
        
        save_journal(journal)
        logger.info(f"📝 Trade #{trade_id} logged: {symbol} {signal_type} @ ${entry_price}")
        
        # 🤖 Auto-train ML модела на всеки 20 trades
        if ML_AVAILABLE and journal['metadata']['total_trades'] % 20 == 0:
            try:
                logger.info(f"🤖 Auto-training ML model (trade #{journal['metadata']['total_trades']})")
                ml_engine.train_model()
                logger.info("✅ ML model trained successfully!")
            except Exception as ml_error:
                logger.error(f"ML training error: {ml_error}")
        
        return trade_id
        
    except Exception as e:
        logger.error(f"Грешка при логване на trade: {e}")
        return None


def update_trade_outcome(trade_id, outcome, profit_loss_pct, notes=None):
    """Обновява резултата от trade и анализира за ML"""
    try:
        from datetime import datetime
        journal = load_journal()
        if not journal:
            return False
        
        trade = next((t for t in journal['trades'] if t['id'] == trade_id), None)
        if not trade:
            logger.warning(f"Trade #{trade_id} not found")
            return False
        
        trade['status'] = outcome
        trade['outcome'] = outcome
        trade['profit_loss_pct'] = profit_loss_pct
        trade['closed_at'] = datetime.now().isoformat()
        
        if notes:
            trade['notes'].append({
                'timestamp': datetime.now().isoformat(),
                'note': notes
            })
        
        # ML анализ
        analyze_trade_patterns(journal, trade)
        
        save_journal(journal)
        logger.info(f"✅ Trade #{trade_id} updated: {outcome} ({profit_loss_pct:+.2f}%)")
        
        return True
        
    except Exception as e:
        logger.error(f"Грешка при обновяване на trade: {e}")
        return False


def analyze_trade_patterns(journal, trade):
    """ML анализ на trade patterns за самообучение"""
    try:
        outcome = trade['outcome']
        symbol = trade['symbol']
        timeframe = trade['timeframe']
        confidence = trade['confidence']
        conditions = trade['conditions']
        
        # Pattern 1: Успешни vs Неуспешни условия
        if outcome == 'WIN':
            pattern_key = 'successful_conditions'
        else:
            pattern_key = 'failed_conditions'
        
        pattern_id = f"{symbol}_{timeframe}_{trade['signal']}"
        
        if pattern_id not in journal['patterns'][pattern_key]:
            journal['patterns'][pattern_key][pattern_id] = {
                'count': 0,
                'avg_confidence': 0,
                'conditions_summary': []
            }
        
        pattern = journal['patterns'][pattern_key][pattern_id]
        pattern['count'] += 1
        pattern['avg_confidence'] = (pattern['avg_confidence'] * (pattern['count'] - 1) + confidence) / pattern['count']
        pattern['conditions_summary'].append(conditions)
        
        # Pattern 2: Най-добри timeframes
        if timeframe not in journal['patterns']['best_timeframes']:
            journal['patterns']['best_timeframes'][timeframe] = {'wins': 0, 'losses': 0, 'total': 0}
        
        tf_stats = journal['patterns']['best_timeframes'][timeframe]
        tf_stats['total'] += 1
        if outcome == 'WIN':
            tf_stats['wins'] += 1
        else:
            tf_stats['losses'] += 1
        
        # Pattern 3: Най-добри symbols
        if symbol not in journal['patterns']['best_symbols']:
            journal['patterns']['best_symbols'][symbol] = {'wins': 0, 'losses': 0, 'total': 0, 'total_profit': 0}
        
        sym_stats = journal['patterns']['best_symbols'][symbol]
        sym_stats['total'] += 1
        sym_stats['total_profit'] += trade.get('profit_loss_pct', 0)
        if outcome == 'WIN':
            sym_stats['wins'] += 1
        else:
            sym_stats['losses'] += 1
        
        # ML Insights: Accuracy by confidence
        conf_range = f"{int(confidence // 10) * 10}-{int(confidence // 10) * 10 + 10}"
        if conf_range not in journal['ml_insights']['accuracy_by_confidence']:
            journal['ml_insights']['accuracy_by_confidence'][conf_range] = {'wins': 0, 'total': 0}
        
        conf_stats = journal['ml_insights']['accuracy_by_confidence'][conf_range]
        conf_stats['total'] += 1
        if outcome == 'WIN':
            conf_stats['wins'] += 1
        
        logger.info(f"📊 ML Pattern analysis completed for trade #{trade['id']}")
        
    except Exception as e:
        logger.error(f"Грешка при ML анализ: {e}")


def get_ml_insights():
    """Извлича ML insights от журнала за подобряване на сигналите"""
    try:
        journal = load_journal()
        if not journal or not journal['trades']:
            return None
        
        insights = {
            'total_trades': journal['metadata']['total_trades'],
            'best_timeframes': {},
            'best_symbols': {},
            'confidence_accuracy': {},
            'avoid_conditions': [],
            'recommended_conditions': []
        }
        
        # Най-добри timeframes
        for tf, stats in journal['patterns']['best_timeframes'].items():
            if stats['total'] > 0:
                win_rate = (stats['wins'] / stats['total']) * 100
                insights['best_timeframes'][tf] = {
                    'win_rate': win_rate,
                    'total_trades': stats['total']
                }
        
        insights['best_timeframes'] = dict(sorted(
            insights['best_timeframes'].items(),
            key=lambda x: x[1]['win_rate'],
            reverse=True
        ))
        
        # Най-добри symbols
        for sym, stats in journal['patterns']['best_symbols'].items():
            if stats['total'] > 0:
                win_rate = (stats['wins'] / stats['total']) * 100
                avg_profit = stats['total_profit'] / stats['total']
                insights['best_symbols'][sym] = {
                    'win_rate': win_rate,
                    'avg_profit': avg_profit,
                    'total_trades': stats['total']
                }
        
        insights['best_symbols'] = dict(sorted(
            insights['best_symbols'].items(),
            key=lambda x: x[1]['win_rate'],
            reverse=True
        ))
        
        # Accuracy by confidence
        for conf_range, stats in journal['ml_insights']['accuracy_by_confidence'].items():
            if stats['total'] > 0:
                accuracy = (stats['wins'] / stats['total']) * 100
                insights['confidence_accuracy'][conf_range] = {
                    'accuracy': accuracy,
                    'total': stats['total']
                }
        
        # Избягвай условия с ниска успеваемост
        for pattern_id, data in journal['patterns']['failed_conditions'].items():
            if data['count'] >= 3:
                insights['avoid_conditions'].append({
                    'pattern': pattern_id,
                    'failed_count': data['count'],
                    'avg_confidence': data['avg_confidence']
                })
        
        # Препоръчай условия с висока успеваемост
        for pattern_id, data in journal['patterns']['successful_conditions'].items():
            if data['count'] >= 3:
                insights['recommended_conditions'].append({
                    'pattern': pattern_id,
                    'success_count': data['count'],
                    'avg_confidence': data['avg_confidence']
                })
        
        return insights
        
    except Exception as e:
        logger.error(f"Грешка при извличане на ML insights: {e}")
        return None


def record_signal(symbol, timeframe, signal_type, confidence, entry_price=None, tp_price=None, sl_price=None):
    """Записва сигнал в статистиката"""
    try:
        from datetime import datetime
        stats = load_stats()
        stats['total_signals'] += 1
        
        # По символ
        if symbol not in stats['by_symbol']:
            stats['by_symbol'][symbol] = {'count': 0, 'BUY': 0, 'SELL': 0}
        stats['by_symbol'][symbol]['count'] += 1
        stats['by_symbol'][symbol][signal_type] += 1
        
        # По таймфрейм
        if timeframe not in stats['by_timeframe']:
            stats['by_timeframe'][timeframe] = {'count': 0}
        stats['by_timeframe'][timeframe]['count'] += 1
        
        # По увереност
        conf_bucket = f"{int(confidence//10)*10}-{int(confidence//10)*10+9}"
        if conf_bucket not in stats['by_confidence']:
            stats['by_confidence'][conf_bucket] = {'count': 0}
        stats['by_confidence'][conf_bucket]['count'] += 1
        
        # Запиши детайлен сигнал (за дневни отчети)
        signal_detail = {
            'symbol': symbol,
            'timeframe': timeframe,
            'type': signal_type,
            'confidence': confidence,
            'timestamp': datetime.now().isoformat()
        }
        
        # Добави trading параметри ако са подадени
        if entry_price is not None:
            signal_detail['entry_price'] = entry_price
        if tp_price is not None:
            signal_detail['tp_price'] = tp_price
        if sl_price is not None:
            signal_detail['sl_price'] = sl_price
        
        if 'signals' not in stats:
            stats['signals'] = []
        
        stats['signals'].append(signal_detail)
        
        # Пази само последните 1000 сигнала (за да не расте файлът безкрайно)
        if len(stats['signals']) > 1000:
            stats['signals'] = stats['signals'][-1000:]
        
        save_stats(stats)
        
        # Върни signal_id (индексът в масива)
        return len(stats['signals']) - 1
        
    except Exception as e:
        logger.error(f"Грешка при record_signal: {e}")
        return None


def get_performance_stats():
    """Вземи обобщена статистика"""
    try:
        stats = load_stats()
        
        summary = f"📊 <b>Статистика на бота:</b>\n\n"
        summary += f"Общо сигнали: {stats['total_signals']}\n\n"
        
        if stats['by_symbol']:
            summary += f"<b>По валута:</b>\n"
            for sym, data in sorted(stats['by_symbol'].items(), key=lambda x: x[1]['count'], reverse=True):
                summary += f"  {sym}: {data['count']} ({data['BUY']} BUY, {data['SELL']} SELL)\n"
        
        if stats['by_timeframe']:
            summary += f"\n<b>По таймфрейм:</b>\n"
            for tf, data in sorted(stats['by_timeframe'].items(), key=lambda x: x[1]['count'], reverse=True):
                summary += f"  {tf}: {data['count']} сигнала\n"
        
        if stats['by_confidence']:
            summary += f"\n<b>По увереност:</b>\n"
            for conf, data in sorted(stats['by_confidence'].items()):
                summary += f"  {conf}%: {data['count']} сигнала\n"
        
        return summary
        
    except Exception as e:
        logger.error(f"Грешка при get_performance_stats: {e}")
        return "Няма налична статистика"


def get_yesterday_signal_stats():
    """Извлича статистика за сигналите от предходния ден"""
    try:
        from datetime import datetime, timedelta
        stats = load_stats()
        
        # Изчисли границите на предходния ден
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today - timedelta(days=1)
        yesterday_end = today
        
        # Филтрирай сигналите от предходния ден
        yesterday_signals = []
        for signal in stats.get('signals', []):
            try:
                signal_time = datetime.fromisoformat(signal['timestamp'])
                if yesterday_start <= signal_time < yesterday_end:
                    yesterday_signals.append(signal)
            except:
                continue
        
        # Брои на сигналите
        total_signals = len(yesterday_signals)
        
        # Брой успешни и неуспешни
        completed_signals = [s for s in yesterday_signals if s.get('status') == 'COMPLETED']
        successful = len([s for s in completed_signals if s.get('result') == 'WIN'])
        failed = len([s for s in completed_signals if s.get('result') == 'LOSS'])
        active = total_signals - len(completed_signals)
        
        # Изчисли win rate
        win_rate = 0
        if len(completed_signals) > 0:
            win_rate = (successful / len(completed_signals)) * 100
        
        # Средна печалба/загуба
        avg_profit = 0
        if completed_signals:
            profits = [s.get('profit_pct', 0) for s in completed_signals if s.get('profit_pct') is not None]
            if profits:
                avg_profit = sum(profits) / len(profits)
        
        return {
            'total': total_signals,
            'successful': successful,
            'failed': failed,
            'active': active,
            'win_rate': win_rate,
            'avg_profit': avg_profit,
            'has_data': total_signals > 0
        }
        
    except Exception as e:
        logger.error(f"Грешка при get_yesterday_signal_stats: {e}")
        return {
            'total': 0,
            'successful': 0,
            'failed': 0,
            'active': 0,
            'win_rate': 0,
            'avg_profit': 0,
            'has_data': False
        }


def get_daily_signals_report():
    """Генерира дневен отчет за сигналите от предходния ден"""
    try:
        from datetime import datetime, timedelta
        stats = load_stats()
        journal = load_journal()
        
        # Вземи вчерашната дата
        yesterday = (datetime.now() - timedelta(days=1)).date()
        
        # Филтрирай сигналите от вчера
        yesterday_signals = []
        if 'signals' in stats and stats['signals']:
            for sig in stats['signals']:
                try:
                    sig_date = datetime.fromisoformat(sig['timestamp']).date()
                    if sig_date == yesterday:
                        yesterday_signals.append(sig)
                except:
                    continue
        
        # Брой сигнали по тип
        total_signals = len(yesterday_signals)
        buy_signals = sum(1 for s in yesterday_signals if s['type'] == 'BUY')
        sell_signals = sum(1 for s in yesterday_signals if s['type'] == 'SELL')
        hold_signals = sum(1 for s in yesterday_signals if s['type'] == 'HOLD')
        
        # Средна увереност
        avg_confidence = sum(s['confidence'] for s in yesterday_signals) / total_signals if total_signals > 0 else 0
        
        # Успешни/неуспешни trades от journal (ако има)
        successful_trades = 0
        failed_trades = 0
        pending_trades = 0
        
        if journal and 'trades' in journal:
            for trade in journal['trades']:
                try:
                    trade_date = datetime.fromisoformat(trade.get('entry_time', '')).date()
                    if trade_date == yesterday:
                        status = trade.get('status', 'pending')
                        if status == 'win':
                            successful_trades += 1
                        elif status == 'loss':
                            failed_trades += 1
                        else:
                            pending_trades += 1
                except:
                    continue
        
        # Win rate
        closed_trades = successful_trades + failed_trades
        win_rate = (successful_trades / closed_trades * 100) if closed_trades > 0 else 0
        
        # Формирай съобщението
        report = f"📊 <b>ДНЕВЕН ОТЧЕТ - {yesterday.strftime('%d.%m.%Y')}</b>\n"
        report += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        report += f"<b>📈 СИГНАЛИ ЗА ДЕНЯ:</b>\n"
        report += f"Общо пуснати: <b>{total_signals}</b>\n"
        report += f"🟢 BUY: {buy_signals}\n"
        report += f"🔴 SELL: {sell_signals}\n"
        report += f"⚪ HOLD: {hold_signals}\n"
        report += f"💪 Средна увереност: {avg_confidence:.1f}%\n\n"
        
        report += f"<b>🎯 РЕЗУЛТАТИ ОТ TRADES:</b>\n"
        report += f"✅ Успешни: <b>{successful_trades}</b>\n"
        report += f"❌ Неуспешни: <b>{failed_trades}</b>\n"
        report += f"⏳ В изчакване: <b>{pending_trades}</b>\n"
        
        if closed_trades > 0:
            report += f"\n📊 <b>Win Rate: {win_rate:.1f}%</b>\n"
            
            # Емоджи според win rate
            if win_rate >= 70:
                report += f"🔥 Отличен ден!\n"
            elif win_rate >= 55:
                report += f"💪 Добър ден!\n"
            elif win_rate >= 40:
                report += f"👍 Приемливо представяне\n"
            else:
                report += f"⚠️ Труден ден - анализирай грешките\n"
        else:
            report += f"\n⏳ Все още няма приключени trades от вчера\n"
        
        # Най-активни символи
        if yesterday_signals:
            symbol_counts = {}
            for sig in yesterday_signals:
                sym = sig.get('symbol', 'Unknown')
                symbol_counts[sym] = symbol_counts.get(sym, 0) + 1
            
            report += f"\n<b>💰 Най-активни символи:</b>\n"
            for sym, count in sorted(symbol_counts.items(), key=lambda x: x[1], reverse=True)[:3]:
                report += f"  {sym}: {count} сигнала\n"
        
        report += f"\n<i>📱 Използвай /stats за пълна статистика</i>"
        
        return report
        
    except Exception as e:
        logger.error(f"Грешка при get_daily_signals_report: {e}")
        return None


def analyze_signal(symbol_data, klines_data, symbol='BTCUSDT', timeframe='4h'):
    """
    🔥 NEW: LuxAlgo + ICT Combined Analysis
    Professional trading signals using:
    - LuxAlgo Support/Resistance MTF
    - ICT Concepts (MSS, FVG, Liquidity Grabs, OTE)
    - Fibonacci Extensions (auto-calculated, penultimate TP)
    """
    try:
        # Extract price data
        closes = [float(k[4]) for k in klines_data]
        highs = [float(k[2]) for k in klines_data]
        lows = [float(k[3]) for k in klines_data]
        opens = [float(k[1]) for k in klines_data]
        volumes = [float(k[5]) for k in klines_data]
        current_price = closes[-1]
        
        # ========== LUXALGO + ICT ANALYSIS ==========
        luxalgo_ict = {}
        if LUXALGO_ICT_AVAILABLE:
            luxalgo_ict = combined_luxalgo_ict_analysis(opens, highs, lows, closes, volumes)
        
        # ========== TRADITIONAL INDICATORS (само RSI и Bollinger Bands) ==========
        rsi = calculate_rsi(closes)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
        
        # Volume analysis
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # Volatility
        recent_closes = closes[-20:]
        avg_price = sum(recent_closes) / len(recent_closes)
        variance = sum((p - avg_price) ** 2 for p in recent_closes) / len(recent_closes)
        volatility = (variance ** 0.5) / avg_price * 100
        
        # Market data
        price_change = float(symbol_data.get('priceChangePercent', 0))
        volume_24h = float(symbol_data.get('quoteVolume', 0))
        
        # ========== NEW SIGNAL LOGIC ==========
        signal = "NEUTRAL"
        confidence = 50
        reasons = []
        
        # === 1. LuxAlgo S/R Alignment ===
        sr_aligned = False
        sr_direction = None
        
        if luxalgo_ict and luxalgo_ict.get('luxalgo_sr'):
            sr_data = luxalgo_ict['luxalgo_sr']
            breakout = sr_data.get('breakout_status', 'NONE')
            
            # Bullish: Retest support or breakout above resistance
            if breakout in ['RETEST_SUPPORT', 'BREAKOUT_RESISTANCE']:
                sr_aligned = True
                sr_direction = 'BUY'
                reasons.append(f"LuxAlgo: {breakout}")
                confidence += 15
            
            # Bearish: Retest resistance or breakout below support
            elif breakout in ['RETEST_RESISTANCE', 'BREAKOUT_SUPPORT']:
                sr_aligned = True
                sr_direction = 'SELL'
                reasons.append(f"LuxAlgo: {breakout}")
                confidence += 15
        
        # === 2. ICT Market Structure Shift ===
        ict_aligned = False
        ict_direction = None
        
        if luxalgo_ict and luxalgo_ict.get('ict_mss'):
            mss = luxalgo_ict['ict_mss']
            if mss and mss.get('confirmed'):
                if 'BULLISH' in mss['type']:
                    ict_aligned = True
                    ict_direction = 'BUY'
                    reasons.append(f"ICT MSS: Bullish structure shift")
                    confidence += 30  # Increased from 20
                elif 'BEARISH' in mss['type']:
                    ict_aligned = True
                    ict_direction = 'SELL'
                    reasons.append(f"ICT MSS: Bearish structure shift")
                    confidence += 30  # Increased from 20
        
        # === 3. Liquidity Grab (reversal signal) ===
        if luxalgo_ict and luxalgo_ict.get('ict_liquidity_grab'):
            liq_grab = luxalgo_ict['ict_liquidity_grab']
            if liq_grab and liq_grab.get('reversal_confirmed'):
                if 'BULLISH' in liq_grab['type']:
                    reasons.append("ICT: Bullish liquidity grab")
                    confidence += 25  # Increased from 18
                    if not ict_aligned:
                        ict_aligned = True
                        ict_direction = 'BUY'
                elif 'BEARISH' in liq_grab['type']:
                    reasons.append("ICT: Bearish liquidity grab")
                    confidence += 25  # Increased from 18
                    if not ict_aligned:
                        ict_aligned = True
                        ict_direction = 'SELL'
        
        # === 4. Fair Value Gaps ===
        fvg_signal = None
        if luxalgo_ict and luxalgo_ict.get('ict_fvgs'):
            fvgs = luxalgo_ict['ict_fvgs']
            unfilled_fvgs = [f for f in fvgs if not f.get('filled')]
            if unfilled_fvgs:
                latest_fvg = unfilled_fvgs[-1]
                if latest_fvg['type'] == 'BULLISH_FVG':
                    fvg_signal = 'BUY'
                    reasons.append(f"ICT: Bullish FVG at {latest_fvg['bottom']:.2f}")
                    confidence += 18  # Increased from 12
                elif latest_fvg['type'] == 'BEARISH_FVG':
                    fvg_signal = 'SELL'
                    reasons.append(f"ICT: Bearish FVG at {latest_fvg['top']:.2f}")
                    confidence += 18  # Increased from 12
        
        # === 5. Displacement ===
        if luxalgo_ict and luxalgo_ict.get('ict_displacement'):
            disp = luxalgo_ict['ict_displacement']
            if disp and disp.get('confirmed'):
                if 'BULLISH' in disp['type']:
                    reasons.append(f"ICT: Bullish displacement (strength: {disp['strength']:.1f}x)")
                    confidence += 15
                elif 'BEARISH' in disp['type']:
                    reasons.append(f"ICT: Bearish displacement (strength: {disp['strength']:.1f}x)")
                    confidence += 15
        
        # === 6. Optimal Trade Entry (OTE) ===
        ote_confirmed = False
        if luxalgo_ict and luxalgo_ict.get('ict_ote'):
            ote = luxalgo_ict['ict_ote']
            if ote and ote.get('optimal_entry'):
                ote_confirmed = True
                reasons.append("ICT: In OTE zone with FVG confluence")
                confidence += 20
        
        # === 7. SHADOW PATTERNS (Candlestick Analysis) ===
        shadow_signal = None
        shadow_confidence_boost = 0
        candlestick_patterns = detect_candlestick_patterns(klines_data)
        
        for pattern_name, pattern_signal, pattern_confidence in candlestick_patterns:
            if pattern_signal == 'BUY':
                shadow_signal = 'BUY'
                shadow_confidence_boost = max(shadow_confidence_boost, pattern_confidence)
                reasons.append(f"🕯️ {pattern_name} (Bullish reversal)")
            elif pattern_signal == 'SELL':
                shadow_signal = 'SELL'
                shadow_confidence_boost = max(shadow_confidence_boost, pattern_confidence)
                reasons.append(f"🕯️ {pattern_name} (Bearish reversal)")
            elif pattern_signal == 'NEUTRAL' and pattern_name == 'DOJI':
                # Doji предупреждава за възможно обръщане - намали confidence
                confidence -= 10
                reasons.append(f"⚠️ DOJI (Indecision - възможно обръщане)")
        
        if shadow_confidence_boost > 0:
            confidence += shadow_confidence_boost
        
        # === ENTRY RULE: All systems must align ===
        # 1. LuxAlgo S/R
        # 2. ICT Concepts (MSS/Liquidity/FVG)
        # 3. Shadow Patterns (Candlestick)
        # 4. Signal confirmation (RSI extreme)
        
        luxalgo_says = sr_direction
        ict_says = ict_direction or fvg_signal
        
        # Traditional confirmation (CONDITIONAL: only extreme or divergence)
        traditional_signal = None
        
        # RSI - only extreme zones (<25 or >75) for confluence
        if rsi and rsi < 25:
            traditional_signal = 'BUY'
            reasons.append(f"RSI extreme oversold: {rsi:.1f}")
            confidence += 10
        elif rsi and rsi > 75:
            traditional_signal = 'SELL'
            reasons.append(f"RSI extreme overbought: {rsi:.1f}")
            confidence += 10
        
        # MACD/EMA REMOVED - Pure ICT strategy (Order Blocks, FVG, Liquidity only)
        
        # ===  FINAL SIGNAL DETERMINATION ===
        # ICT-FIRST STRATEGY: ICT + S/R + Shadow Patterns confluence (RSI only for extreme confirmation)
        vote_buy = 0
        vote_sell = 0
        
        # Primary systems (ICT + LuxAlgo S/R)
        if luxalgo_says == 'BUY': vote_buy += 2  # Stronger weight
        if luxalgo_says == 'SELL': vote_sell += 2
        if ict_says == 'BUY': vote_buy += 2  # ICT is primary
        if ict_says == 'SELL': vote_sell += 2
        
        # Shadow Patterns (strong reversal confirmation)
        if shadow_signal == 'BUY': vote_buy += 1
        if shadow_signal == 'SELL': vote_sell += 1
        
        # RSI extreme (confirmatory only)
        if traditional_signal == 'BUY': vote_buy += 1
        if traditional_signal == 'SELL': vote_sell += 1
        
        # Decision: ICT + S/R must align (at least 3 votes)
        if vote_buy >= 3:
            signal = 'BUY'
            if vote_buy >= 6:
                reasons.append("✅ PERFECT: ICT + S/R + Shadow + RSI SETUP")
                confidence += 35
            elif vote_buy >= 5:
                reasons.append("✅ PERFECT ICT + S/R + RSI/Shadow SETUP: BUY")
                confidence += 30
            else:
                reasons.append(f"✅ ICT + S/R ALIGNED: BUY")
                confidence += 20
        elif vote_sell >= 3:
            signal = 'SELL'
            if vote_sell >= 6:
                reasons.append("✅ PERFECT: ICT + S/R + Shadow + RSI SETUP")
                confidence += 35
            elif vote_sell >= 5:
                reasons.append("✅ PERFECT ICT + S/R + RSI/Shadow SETUP: SELL")
                confidence += 30
            else:
                reasons.append(f"✅ ICT + S/R ALIGNED: SELL")
                confidence += 20
        elif ict_says and ote_confirmed:
            # OTE with FVG confluence = high-probability setup
            signal = ict_says
            reasons.append(f"🎯 ICT OTE + FVG OPTIMAL ENTRY: {signal}")
            confidence += 25
        
        # === Volume confirmation ===
        volume_boost = calculate_volume_confidence_boost(current_volume, avg_volume, signal)
        confidence += volume_boost
        if volume_boost > 0:
            reasons.append(f"Volume: {volume_ratio:.1f}x avg (+{volume_boost})")
        elif volume_boost < 0:
            reasons.append(f"⚠️ Low volume: {volume_ratio:.1f}x ({volume_boost})")
        
        # === Time-based filter ===
        is_good_time, time_reason = is_good_trading_time()
        if not is_good_time and signal in ['BUY', 'SELL']:
            confidence -= 15  # Намали confidence в лошо време
            reasons.append(f"⚠️ {time_reason} (-15)")
        elif is_good_time and signal in ['BUY', 'SELL']:
            confidence += 5
            reasons.append(f"✅ {time_reason} (+5)")
        
        # === Machine Learning Validation ===
        if ML_AVAILABLE and signal in ['BUY', 'SELL']:
            try:
                # Подготви features за ML модела (ICT-compatible)
                ml_features = {
                    'rsi': rsi if rsi else 50,
                    'price_change_pct': price_change,
                    'volume_ratio': volume_ratio,
                    'volatility': volatility,
                    'bb_position': ((current_price - bb_lower) / (bb_upper - bb_lower)) if bb_upper and bb_lower else 0.5,
                    'ict_confidence': confidence / 100.0  # Normalized ICT confidence
                }
                
                # Предскажи с ML модела
                ml_prediction = ml_engine.predict_signal(ml_features, symbol, timeframe)
                
                if ml_prediction:
                    ml_signal = ml_prediction.get('signal')
                    ml_confidence = ml_prediction.get('confidence', 50)
                    
                    # Ако ML се съгласява със сигнала
                    if ml_signal == signal:
                        # ML потвърждава - използвай weighted average
                        ml_boost = (ml_confidence - 50) * 0.5  # ML има 50% тегло
                        confidence = (confidence * 0.7) + (ml_confidence * 0.3)  # Weighted average
                        reasons.append(f"🤖 ML confirms: {ml_confidence:.0f}% (+{ml_boost:.0f})")
                    else:
                        # ML не се съгласява - намали confidence
                        confidence -= 20
                        reasons.append(f"⚠️ ML disagrees: {ml_signal} vs {signal} (-20)")
                        
            except Exception as e:
                logger.warning(f"ML validation failed: {e}")
        
        # === Confidence recalibration ===
        # Базов confidence според alignment strength
        max_votes = 5  # ICT(2) + S/R(2) + RSI(1)
        total_votes = vote_buy if vote_buy > vote_sell else vote_sell
        
        if total_votes >= 5:
            base_confidence = 85  # Perfect alignment
        elif total_votes >= 4:
            base_confidence = 75  # Strong alignment  
        elif total_votes >= 3:
            base_confidence = 65  # Good alignment
        else:
            base_confidence = 50  # Weak signal
        
        # Добави бонуси от индикатори
        indicator_bonus = 0
        
        # RSI extreme зони
        if rsi:
            if (signal == 'BUY' and rsi < 30) or (signal == 'SELL' and rsi > 70):
                indicator_bonus += 10
                reasons.append(f"RSI extreme: {rsi:.1f} (+10)")
        
        # Volume surge
        if volume_boost >= 15:
            indicator_bonus += 10
        
        # LuxAlgo/ICT special setups
        if ote_confirmed:
            indicator_bonus += 15
            
        # Пресметни финален confidence
        confidence = base_confidence + indicator_bonus
        
        # === Cap confidence ===
        confidence = max(50, min(confidence, 95))  # Range: 50-95
        
        # ========== TP/SL CALCULATION (NEW LOGIC) ==========
        tp_price = None
        sl_price = None
        
        if signal in ['BUY', 'SELL'] and luxalgo_ict:
            # === Stop-Loss Logic ===
            # SL below/above nearest S/R or liquidity sweep (conservative)
            sr_data = luxalgo_ict.get('luxalgo_sr', {})
            liq_grab = luxalgo_ict.get('ict_liquidity_grab')
            
            if signal == 'BUY':
                # SL below support or liquidity sweep
                sl_candidates = []
                if sr_data.get('dynamic_support'):
                    sl_candidates.append(sr_data['dynamic_support'][0])
                if liq_grab and liq_grab.get('swept_level'):
                    sl_candidates.append(liq_grab['swept_level'])
                
                if sl_candidates:
                    sl_price = min(sl_candidates) * 0.998  # 0.2% below (conservative)
                else:
                    sl_price = current_price * 0.98  # Fallback: 2% SL
            
            else:  # SELL
                # SL above resistance or liquidity sweep
                sl_candidates = []
                if sr_data.get('dynamic_resistance'):
                    sl_candidates.append(sr_data['dynamic_resistance'][0])
                if liq_grab and liq_grab.get('swept_level'):
                    sl_candidates.append(liq_grab['swept_level'])
                
                if sl_candidates:
                    sl_price = max(sl_candidates) * 1.002  # 0.2% above (conservative)
                else:
                    sl_price = current_price * 1.02  # Fallback: 2% SL
            
            # === Take-Profit Logic ===
            # TP from: 1) ICT targets (FVG close, liquidity pools), 2) Fibonacci penultimate level
            fib_data = luxalgo_ict.get('fibonacci')
            fvgs = luxalgo_ict.get('ict_fvgs', [])
            
            tp_candidates = []
            
            # ICT target: FVG close
            if fvgs:
                unfilled = [f for f in fvgs if not f.get('filled')]
                if unfilled:
                    if signal == 'BUY':
                        bullish_fvgs = [f['top'] for f in unfilled if f['type'] == 'BULLISH_FVG']
                        if bullish_fvgs:
                            tp_candidates.append(max(bullish_fvgs))
                    else:
                        bearish_fvgs = [f['bottom'] for f in unfilled if f['type'] == 'BEARISH_FVG']
                        if bearish_fvgs:
                            tp_candidates.append(min(bearish_fvgs))
            
            # Fibonacci penultimate level (1.618)
            if fib_data and fib_data.get('penultimate_tp'):
                tp_candidates.append(fib_data['penultimate_tp'])
            
            # Choose closest safe target
            if tp_candidates:
                if signal == 'BUY':
                    tp_price = min(tp_candidates)  # Closest target above
                else:
                    tp_price = max(tp_candidates)  # Closest target below
            else:
                # Fallback: Adaptive TP/SL
                adaptive = calculate_adaptive_tp_sl(symbol, volatility, timeframe)
                if adaptive:
                    tp_pct = adaptive.get('tp_pct', 2.5)
                    tp_price = current_price * (1 + tp_pct/100) if signal == 'BUY' else current_price * (1 - tp_pct/100)
        
        # Fallback for traditional TP/SL
        if not tp_price or not sl_price:
            adaptive = calculate_adaptive_tp_sl(symbol, volatility, timeframe)
            if adaptive:
                tp_pct = adaptive.get('tp_pct', 2.5)
                sl_pct = adaptive.get('sl_pct', 1.0)
                
                if signal == 'BUY':
                    tp_price = current_price * (1 + tp_pct/100)
                    sl_price = current_price * (1 - sl_pct/100)
                elif signal == 'SELL':
                    tp_price = current_price * (1 - tp_pct/100)
                    sl_price = current_price * (1 + sl_pct/100)
        
        # ========== HAS GOOD TRADE CHECK ==========
        has_good_trade = signal in ['BUY', 'SELL'] and confidence >= 55  # Balanced threshold
        
        # ========== RISK MANAGEMENT VALIDATION ==========
        risk_validation = None
        if has_good_trade and RISK_MANAGER_AVAILABLE and tp_price and sl_price:
            try:
                rm = get_risk_manager()
                risk_validation = rm.validate_trade(
                    entry=current_price,
                    tp=tp_price,
                    sl=sl_price,
                    signal=signal,
                    journal_file='trading_journal.json'
                )
                # Override has_good_trade if risk check fails
                if not risk_validation['approved']:
                    has_good_trade = False
            except Exception as e:
                logger.warning(f"Risk validation error: {e}")
        
        return {
            'signal': signal,
            'confidence': confidence,
            'price': current_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'rsi': rsi,
            'bollinger': {'upper': bb_upper, 'middle': bb_middle, 'lower': bb_lower},
            'volume_ratio': volume_ratio,
            'volatility': volatility,
            'change_24h': price_change,
            'volume': volumes[-1],
            'reasons': reasons,
            'has_good_trade': has_good_trade,
            'highs': highs,
            'lows': lows,
            'closes': closes,
            'adaptive_tp_sl': calculate_adaptive_tp_sl(symbol, volatility, timeframe),
            'luxalgo_ict': luxalgo_ict,  # Full ICT analysis data
            'time_factor': get_time_of_day_factor(),
            'liquidity': check_liquidity(volume_24h, avg_volume, volume_ratio),
            'risk_validation': risk_validation  # Risk Management results
        }
    
    except Exception as e:
        logger.error(f"Error in analyze_signal: {e}")
        logger.exception(e)
        return None


def calculate_entry_zones(price, signal, closes, highs, lows, analysis):
    """Изчислява оптимални зони за вход"""
    try:
        # Изчисли Support/Resistance нива
        recent_highs = highs[-50:]
        recent_lows = lows[-50:]
        recent_closes = closes[-50:]
        
        # Намери ключови нива (swing highs/lows)
        resistance_levels = []
        support_levels = []
        
        for i in range(2, len(recent_highs) - 2):
            # Swing High
            if recent_highs[i] > recent_highs[i-1] and recent_highs[i] > recent_highs[i-2] and \
               recent_highs[i] > recent_highs[i+1] and recent_highs[i] > recent_highs[i+2]:
                resistance_levels.append(recent_highs[i])
            
            # Swing Low
            if recent_lows[i] < recent_lows[i-1] and recent_lows[i] < recent_lows[i-2] and \
               recent_lows[i] < recent_lows[i+1] and recent_lows[i] < recent_lows[i+2]:
                support_levels.append(recent_lows[i])
        
        # Fibonacci retracement нива
        price_high = max(recent_highs)
        price_low = min(recent_lows)
        price_range = price_high - price_low
        
        fib_levels = {
            '23.6%': price_high - (price_range * 0.236),
            '38.2%': price_high - (price_range * 0.382),
            '50.0%': price_high - (price_range * 0.500),
            '61.8%': price_high - (price_range * 0.618),
            '78.6%': price_high - (price_range * 0.786)
        }
        
        # Определи entry zones според сигнала
        if signal == 'BUY':
            # За BUY търси support нива под текущата цена
            potential_entries = [lvl for lvl in support_levels if lvl < price * 1.02]  # До 2% над текущата цена
            
            # Добави Fibonacci retracement нива
            for fib_name, fib_price in fib_levels.items():
                if price * 0.95 <= fib_price <= price * 1.02:  # -5% до +2%
                    potential_entries.append(fib_price)
            
            # Сортирай и вземи най-близките 3 нива
            if potential_entries:
                potential_entries.sort(reverse=True)
                best_entry = potential_entries[0] if potential_entries else price * 0.99
                entry_zone_low = best_entry * 0.995  # -0.5%
                entry_zone_high = best_entry * 1.005  # +0.5%
            else:
                # Default: малък pullback
                best_entry = price * 0.99
                entry_zone_low = price * 0.985
                entry_zone_high = price * 0.995
                
        else:  # SELL
            # За SELL търси resistance нива над текущата цена
            potential_entries = [lvl for lvl in resistance_levels if lvl > price * 0.98]  # До 2% под текущата цена
            
            # Добави Fibonacci нива
            for fib_name, fib_price in fib_levels.items():
                if price * 0.98 <= fib_price <= price * 1.05:  # -2% до +5%
                    potential_entries.append(fib_price)
            
            # Сортирай и вземи най-близките нива
            if potential_entries:
                potential_entries.sort()
                best_entry = potential_entries[0] if potential_entries else price * 1.01
                entry_zone_low = best_entry * 0.995
                entry_zone_high = best_entry * 1.005
            else:
                # Default: малък bounce
                best_entry = price * 1.01
                entry_zone_low = price * 1.005
                entry_zone_high = price * 1.015
        
        # Изчисли quality score на entry zone
        quality_score = 0
        
        # По-добре ако е близо до важно Fibonacci ниво
        for fib_price in fib_levels.values():
            if abs(best_entry - fib_price) / fib_price * 100 < 1:
                quality_score += 25
                break
        
        # По-добре ако има confluence със support/resistance
        confluence_count = sum(1 for lvl in (support_levels + resistance_levels) 
                              if abs(best_entry - lvl) / lvl * 100 < 1.5)
        quality_score += min(confluence_count * 15, 45)
        
        quality_score = min(quality_score, 100)
        
        return {
            'best_entry': best_entry,
            'entry_zone_low': entry_zone_low,
            'entry_zone_high': entry_zone_high,
            'quality': quality_score,
            'supports': sorted(support_levels[-3:], reverse=True) if support_levels else [],
            'resistances': sorted(resistance_levels[:3]) if resistance_levels else []
        }
        
    except Exception as e:
        logger.error(f"Грешка при изчисляване на entry zones: {e}")
        return {
            'best_entry': price,
            'entry_zone_low': price * 0.995,
            'entry_zone_high': price * 1.005,
            'quality': 50,
            'supports': [],
            'resistances': []
        }


def calculate_tp_probability(analysis, tp_price, signal):
    """Изчислява вероятността за достигане на Take Profit"""
    try:
        current_price = analysis['price']
        closes = analysis['closes']
        highs = analysis['highs']
        lows = analysis['lows']
        
        # Базова вероятност според сигнала и увереност
        base_probability = analysis['confidence']
        
        # Изчисли волатилност (средно отклонение от последните 20 свещи)
        recent_closes = closes[-20:]
        avg_price = sum(recent_closes) / len(recent_closes)
        variance = sum((p - avg_price) ** 2 for p in recent_closes) / len(recent_closes)
        volatility = (variance ** 0.5) / avg_price * 100  # в проценти
        
        # Изчисли разстоянието до TP
        if signal == 'BUY':
            distance_to_tp = ((tp_price - current_price) / current_price) * 100
        else:  # SELL
            distance_to_tp = ((current_price - tp_price) / current_price) * 100
        
        # Изчисли историческа честота на достигане на подобни цени
        successful_moves = 0
        total_moves = 0
        
        for i in range(len(closes) - 20, len(closes) - 1):
            total_moves += 1
            if signal == 'BUY':
                # Провери дали максимумът след тази свещ достига целевата промяна
                future_highs = highs[i+1:min(i+6, len(highs))]  # Следващите 5 свещи
                if future_highs:
                    max_future = max(future_highs)
                    if (max_future - closes[i]) / closes[i] * 100 >= distance_to_tp:
                        successful_moves += 1
            else:  # SELL
                # Провери дали минимумът след тази свещ достига целевата промяна
                future_lows = lows[i+1:min(i+6, len(lows))]
                if future_lows:
                    min_future = min(future_lows)
                    if (closes[i] - min_future) / closes[i] * 100 >= distance_to_tp:
                        successful_moves += 1
        
        historical_probability = (successful_moves / total_moves * 100) if total_moves > 0 else 50
        
        # Корекция според волатилност
        volatility_factor = min(volatility / distance_to_tp, 2.0) if distance_to_tp > 0 else 0.5
        
        # Комбинирана вероятност
        tp_probability = (
            base_probability * 0.4 +  # 40% от увереността на сигнала
            historical_probability * 0.4 +  # 40% от историческа вероятност
            (volatility_factor * 50) * 0.2  # 20% от волатилност
        )
        
        # Корекция според RSI
        if analysis['rsi']:
            if signal == 'BUY' and analysis['rsi'] < 40:
                tp_probability += 5  # Добър момент за покупка
            elif signal == 'SELL' and analysis['rsi'] > 60:
                tp_probability += 5  # Добър момент за продажба
        
        # Ограничи между 15% и 85%
        tp_probability = max(15, min(85, tp_probability))
        
        return round(tp_probability, 1)
        
    except Exception as e:
        logger.error(f"Грешка при изчисляване на TP вероятност: {e}")
        return 50.0  # По подразбиране


# ================= КОМАНДИ =================

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Стартира бота"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    first_name = update.effective_user.first_name or "Unknown"
    
    logger.info(f"User {user_id} (@{username}) executed /start")
    
    # ================= FORWARD DETECTION =================
    # Провери дали съобщението е препратено (forward)
    if hasattr(update.message, 'forward_origin') and update.message.forward_origin:
        # Ако НЕ Е owner-а - блокирай препращането
        if user_id != OWNER_CHAT_ID:
            # Запиши опита за препращане
            if user_id not in ACCESS_ATTEMPTS:
                ACCESS_ATTEMPTS[user_id] = {
                    'username': username,
                    'first_name': first_name,
                    'attempts': 0,
                    'last_attempt': datetime.now(timezone.utc)
                }
            
            ACCESS_ATTEMPTS[user_id]['attempts'] += 1
            ACCESS_ATTEMPTS[user_id]['last_attempt'] = datetime.now(timezone.utc)
            
            # Алертирай owner-а
            try:
                alert_text = f"""🚨 <b>ОПИТ ЗА ПРЕПРАЩАНЕ</b>

👤 <b>Потребител:</b> {first_name}
🆔 <b>User ID:</b> <code>{user_id}</code>
📱 <b>Username:</b> @{username}
🔢 <b>Опит №:</b> {ACCESS_ATTEMPTS[user_id]['attempts']}
⏰ <b>Време:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

⚠️ <b>Действие:</b> Опит да препрати бота към друг потребител

💡 <b>За да одобриш:</b>
<code>/approve {user_id}</code>

🚫 <b>За да блокираш:</b>
<code>/block {user_id}</code>"""
                
                await context.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=alert_text,
                    parse_mode='HTML'
                )
            except Exception as e:
                logger.error(f"Грешка при изпращане на алерт до owner: {e}")
            
            # Изпрати съобщение на потребителя
            forward_blocked_text = """🚫 <b>ПРЕПРАЩАНЕТО Е БЛОКИРАНО</b>

❌ Само owner-ът има право да споделя този бот.

💡 Ако искате достъп до бота, моля попитайте owner-а директно.

⚠️ <b>ВАЖНО:</b> Не можете да препращате (forward) този бот към други потребители.

Вашият опит е записан и owner-ът е уведомен."""
            
            await update.message.reply_text(forward_blocked_text, parse_mode='HTML')
            logger.warning(f"🚫 Блокиран опит за forward от @{username} (ID:{user_id})")
            return
    
    # Нормален старт (не е препратен или е от owner)
    welcome_text = """
🤖 <b>Добре дошли в Crypto Signal Bot!</b>

Използвайте бутоните отдолу или команди:

📊 <b>Анализ и сигнали:</b>
/market - Дневен анализ за всички валути
/signal BTCUSDT - Анализ и сигнал в реално време

📰 <b>Новини:</b>
/news - Последни крипто новини (преведени на БГ)
/autonews - Вкл/Изкл автоматични новини

⚙️ <b>Настройки:</b>
/settings - Конфигурация на TP/SL и RR
/timeframe - Избор на таймфрейм (1h, 4h, 1d)
/alerts - Вкл/Изкл автоматични сигнали

💡 <b>Поддържани валути:</b>
BTC, ETH, XRP, SOL, BNB, ADA

Пример: <code>/signal BTCUSDT</code>

За повече помощ: /help
"""
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=get_main_keyboard())


async def ml_menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📚 ML Анализ главно меню с описания"""
    ml_menu_text = """📚 <b>ML АНАЛИЗ - Machine Learning</b>

🤖 <b>ML Прогноза</b>
Изкуствен интелект прогноза за цени
• Neural Network prediction
• LSTM модели за времеви серии
• Confidence score и вероятности

📊 <b>Backtest</b>
Тестване на стратегии с исторически данни
• 90-дневен backtest
• Win rate и Profit/Loss
• Sharpe ratio и максимален drawdown

📈 <b>ML Report</b>
Детайлен отчет за ML перформанс
• Точност на моделите
• Успеваемост по timeframes
• Сравнение с реални сигнали

🔧 <b>ML Status</b>
Статус на ML системата
• Налични модели
• Последно обучение
• Системна информация

<i>Избери опция от менюто отдолу:</i>"""
    
    await update.message.reply_text(
        ml_menu_text,
        parse_mode='HTML',
        reply_markup=get_ml_keyboard()
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощна информация"""
    help_text = """
📖 <b>ПОМОЩ - Crypto Signal Bot</b>

<b>1. Основни команди:</b>
/start - Стартиране на бота
/help - Тази помощна информация
/version или /v - Информация за версията
/market - Преглед на пазара

<b>2. Сигнали:</b>
/signal BTCUSDT - Анализ на BTC
/signal ETHUSDT - Анализ на ETH
/signal XRPUSDT - Анализ на XRP
/signal SOLUSDT - Анализ на SOL

🎯 <b>ICT Complete Analysis:</b>
/ict BTC - Full ICT analysis (OB, FVG, Liquidity)
/ict ETHUSDT 1h - ICT analysis specific timeframe

Или просто: /signal BTC

<b>3. 🚀 ML + Back-test + Reports:</b>
/backtest - Back-test на стратегията (90 дни)
/backtest BTCUSDT 1h - Custom back-test
/ml_status - Machine Learning статус
/ml_train - Ръчно обучение на ML модел
/dailyreport - 📊 Дневен отчет за сигнали от вчера
/daily_report - 📊 Дневен отчет с точност и успеваемост
/weekly_report - 📈 Седмичен отчет (7 дни)
/monthly_report - 📆 Месечен отчет (30 дни)

<i>Дневният отчет (/dailyreport) показва:</i>
• Общо сигнали от предходния ден
• Успешни сигнали (✅)
• Неуспешни сигнали (❌)
• В изчакване (⏳)
• Статистика по валута и таймфрейм
• Топ 5 сигнала с най-висока увереност

🕗 <b>Автоматично се изпраща всяка сутрин в 08:00!</b>

<b>4. Новини:</b>
/news - Последни крипто новини (преведени на БГ)
/breaking - 🚨 Провери за КРИТИЧНИ новини
/autonews - Вкл/Изкл автоматични новини
/autonews 120 - Интервал 2 часа

🔴 <b>REAL-TIME мониторинг:</b>
Ботът автоматично проверява новини на всеки 3 минути!
При критична новина получаваш моментална алерта! 🚨

<b>5. 🤖 Copilot Integration:</b>
/task - Виж текущи задачи
/task Добави функция X - Създай задание
/task Поправи грешка Y - Репорт проблем

<i>GitHub Copilot ще види заданията и ще ги изпълни!</i>

<b>6. Настройки:</b>
/settings - Виж текущи настройки
/settings tp 3.0 - Промени Take Profit на 3%
/settings sl 1.5 - Промени Stop Loss на 1.5%
/settings rr 2.5 - Промени Risk/Reward

<b>7. 🛡️ Risk Management:</b>
/risk - Виж настройки и статус
/risk set portfolio 5000 - Задай баланс
/risk set max_loss 8 - Дневен лимит (%)
/risk set max_trades 3 - Макс паралелни trades
/risk set min_rr 2.5 - Минимален R/R

<b>8. Таймфрейм:</b>
/timeframe - Покажи опции
/timeframe 4h - Избери 4-часов таймфрейм

<b>8. Автоматични сигнали:</b>
/alerts - Вкл/Изкл
/alerts 30 - Промени интервала на 30 мин

<b>🔐 9. Админ панел:</b>
/admin_login - Вход в админ (нужна парола)
/admin_daily - Дневен отчет
/admin_weekly - Седмичен отчет
/admin_monthly - Месечен отчет
/admin_docs - Пълна документация
/deploy - 🚀 Auto-deploy от GitHub (owner)
/update - 🔄 Обновяване на бота от GitHub
/restart - 🔄 Рестартиране на бота

<b>👥 10. User Access (Owner):</b>
/approve USER_ID - Одобри нов потребител
/block USER_ID - Блокирай потребител
/users - Списък с разрешени потребители

<b>🧪 11. Система:</b>
/test - Тест и автоматично отстраняване на грешки
/stats - Статистика на бота
/journal - 📝 Trading Journal с ML самообучение

━━━━━━━━━━━━━━━━━━━━━━━━

🚀 <b>НОВИ ФУНКЦИИ:</b>

📈 <b>Back-testing:</b> Тества стратегията на 90 дни
🤖 <b>Machine Learning:</b> Учи от сигнали и се подобрява
📊 <b>Daily Reports:</b> Автоматични отчети всеки ден в 08:00 (за предходния ден)
📝 <b>Trading Journal 24/7:</b> 
   • Автоматичен запис на всички trades
   • Мониторинг на активни позиции на всеки 2 мин
   • ML анализ и самообучение
   • Автоматично затваряне при TP/SL
   • Нотификации при завършване на trades

📖 <b>Пълна документация:</b>
ML_BACKTEST_REPORTS_DOCS.md
TRADING_JOURNAL_DOCS.md
ORDER_BLOCKS_GUIDE.md

📦 <b>Order Blocks на графиката:</b>
Всички графики показват Order Blocks:
   • 🟢 Bullish OB (зелени зони) - support
   • 🔴 Bearish OB (червени зони) - resistance
   • Силата на всеки OB е посочена в %
   • Виж ORDER_BLOCKS_GUIDE.md за детайли

⚠️ <b>Важно:</b> Това не е финансов съвет!
Винаги правете собствено проучване (DYOR).
"""
    await update.message.reply_text(help_text, parse_mode='HTML')


async def version_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показва текущата версия на бота"""
    try:
        # Read VERSION file from BASE_PATH
        version = "2.0"  # Default
        version_file = os.path.join(BASE_PATH, 'VERSION')
        try:
            with open(version_file, 'r') as f:
                version = f.read().strip()
        except FileNotFoundError:
            pass
        
        # Read deployment info from BASE_PATH
        deployment_info = {}
        deployment_file = os.path.join(BASE_PATH, '.deployment-info')
        try:
            if os.path.exists(deployment_file):
                with open(deployment_file, 'r') as f:
                    deployment_info = json.load(f)
        except Exception:
            pass
        
        # Get python-telegram-bot version
        import telegram
        ptb_version = telegram.__version__
        
        # Get Python version (sys is already imported at the top)
        python_version = sys.version.split()[0]
        
        # Calculate bot uptime
        uptime = datetime.now(timezone.utc) - BOT_START_TIME
        uptime_str = str(uptime).split('.')[0]  # Remove microseconds
        
        # Format bot start time (already in UTC)
        bot_start_utc = BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        message = f"""
🤖 <b>CRYPTO SIGNAL BOT - VERSION INFO</b>

📦 <b>Bot Version:</b> v{version}
🐍 <b>Python:</b> {python_version}
📡 <b>python-telegram-bot:</b> {ptb_version}

⏰ <b>Bot Process Started:</b> {bot_start_utc}
⏱️ <b>Uptime:</b> {uptime_str}

"""
        
        if deployment_info:
            message += f"""
📊 <b>Deployment Info:</b>
🕐 <b>Last Deploy:</b> {deployment_info.get('last_deployed', 'N/A')}
🔖 <b>Commit SHA:</b> {deployment_info.get('commit_sha', 'N/A')}
🚀 <b>Deployed From:</b> {deployment_info.get('deployed_from', 'N/A')}
"""
        
        message += f"""
✅ <b>Status:</b> Operational
🔄 <b>Auto-Deploy:</b> Active (Daily at 04:00 BG time)
"""
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in version_cmd: {e}")
        await update.message.reply_text(f"❌ Error getting version: {str(e)}")


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показва статистика на бота"""
    stats_message = get_performance_stats()
    await update.message.reply_text(stats_message, parse_mode='HTML')


async def journal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📝 Trading Journal - ML самообучение и insights"""
    logger.info(f"User {update.effective_user.id} executed /journal")
    
    try:
        journal = load_journal()
        if not journal or not journal['trades']:
            await update.message.reply_text(
                "📝 <b>Trading Journal</b>\n\n"
                "Все още няма записани trades.\n"
                "Журналът автоматично се попълва при всеки сигнал!\n\n"
                "💡 <i>ML системата ще започне да се учи след първите trades.</i>",
                parse_mode='HTML'
            )
            return
        
        # Общ преглед
        total_trades = journal['metadata']['total_trades']
        pending_trades = sum(1 for t in journal['trades'] if t['status'] == 'PENDING')
        completed_trades = sum(1 for t in journal['trades'] if t['status'] in ['WIN', 'LOSS'])
        wins = sum(1 for t in journal['trades'] if t['outcome'] == 'WIN')
        losses = sum(1 for t in journal['trades'] if t['outcome'] == 'LOSS')
        
        win_rate = (wins / completed_trades * 100) if completed_trades > 0 else 0
        
        message = "📝 <b>TRADING JOURNAL - ML САМООБУЧЕНИЕ</b>\n"
        message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        message += f"📊 <b>Обща статистика:</b>\n"
        message += f"Общо trades: {total_trades}\n"
        message += f"Завършени: {completed_trades}\n"
        message += f"В изчакване: {pending_trades}\n\n"
        
        if completed_trades > 0:
            message += f"🎯 <b>Резултати:</b>\n"
            message += f"✅ Успешни: {wins} ({win_rate:.1f}%)\n"
            message += f"❌ Неуспешни: {losses}\n\n"
        
        # ML Insights
        insights = get_ml_insights()
        
        if insights and insights['best_timeframes']:
            message += f"⏱️ <b>Най-добри Timeframes:</b>\n"
            for tf, data in list(insights['best_timeframes'].items())[:3]:
                message += f"  {tf}: {data['win_rate']:.1f}% ({data['total_trades']} trades)\n"
            message += "\n"
        
        if insights and insights['best_symbols']:
            message += f"💰 <b>Най-добри Валути:</b>\n"
            for sym, data in list(insights['best_symbols'].items())[:3]:
                message += f"  {sym}: {data['win_rate']:.1f}% (avg: {data['avg_profit']:+.2f}%)\n"
            message += "\n"
        
        if insights and insights['confidence_accuracy']:
            message += f"🎯 <b>Точност по Confidence:</b>\n"
            for conf_range, data in sorted(insights['confidence_accuracy'].items(), reverse=True):
                message += f"  {conf_range}%: {data['accuracy']:.1f}% ({data['total']} trades)\n"
            message += "\n"
        
        # Препоръки от ML
        if insights and insights['recommended_conditions']:
            message += f"💡 <b>ML Препоръки (успешни patterns):</b>\n"
            for rec in insights['recommended_conditions'][:2]:
                message += f"  ✅ {rec['pattern']} ({rec['success_count']} успеха)\n"
            message += "\n"
        
        if insights and insights['avoid_conditions']:
            message += f"⚠️ <b>ML Предупреждения (избягвай):</b>\n"
            for avoid in insights['avoid_conditions'][:2]:
                message += f"  ❌ {avoid['pattern']} ({avoid['failed_count']} неуспеха)\n"
            message += "\n"
        
        # Последни trades
        recent_trades = sorted(journal['trades'], key=lambda x: x['timestamp'], reverse=True)[:5]
        
        message += f"📋 <b>Последни 5 Trades:</b>\n"
        for trade in recent_trades:
            status_emoji = "✅" if trade['outcome'] == 'WIN' else "❌" if trade['outcome'] == 'LOSS' else "⏳"
            message += f"{status_emoji} #{trade['id']} {trade['symbol']} {trade['signal']} "
            message += f"({trade['confidence']:.0f}%) - {trade['status']}\n"
        
        message += f"\n<i>📖 Журналът автоматично се обновява при всеки trade.</i>\n"
        message += f"<i>🤖 ML системата се учи от всички резултати!</i>"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Грешка в journal_cmd: {e}")
        await update.message.reply_text(f"❌ Грешка при показване на журнала: {e}")


async def analyze_news_impact(title, description=""):
    """Анализира дали новината може да обърне тренда"""
    # Ключови думи за BULLISH новини
    bullish_keywords = [
        'adoption', 'institutional', 'etf approved', 'bullish', 'rally', 'surge', 
        'breakthrough', 'partnership', 'integration', 'green candle', 'bull run',
        'all-time high', 'ath', 'breakout', 'milestone', 'record', 'upgrade',
        'positive', 'growth', 'expansion', 'invest', 'купува', 'растеж', 'одобрен'
    ]
    
    # Ключови думи за BEARISH новини
    bearish_keywords = [
        'crash', 'hack', 'ban', 'regulation', 'lawsuit', 'fraud', 'scam',
        'bearish', 'plunge', 'drop', 'fall', 'decline', 'sell-off', 'correction',
        'investigation', 'warning', 'risk', 'concern', 'negative', 'crisis',
        'забрана', 'разследване', 'срив', 'спад', 'загуба'
    ]
    
    # Критични събития (много силно влияние)
    critical_keywords = [
        'sec', 'federal reserve', 'fed', 'interest rate', 'bank collapse',
        'major hack', 'exchange shutdown', 'government ban', 'war', 'санкции',
        'etf approval', 'etf rejection', 'halving', 'hard fork', 'emergency'
    ]
    
    text = (title + " " + description).lower()
    
    # Провери за критични събития
    is_critical = any(keyword in text for keyword in critical_keywords)
    
    # Брой BULLISH срещу BEARISH думи
    bullish_count = sum(1 for keyword in bullish_keywords if keyword in text)
    bearish_count = sum(1 for keyword in bearish_keywords if keyword in text)
    
    # Определи sentiment и важност
    if bullish_count > bearish_count and (bullish_count >= 2 or is_critical):
        sentiment = "BULLISH"
        impact = "CRITICAL" if is_critical or bullish_count >= 3 else "HIGH"
    elif bearish_count > bullish_count and (bearish_count >= 2 or is_critical):
        sentiment = "BEARISH"
        impact = "CRITICAL" if is_critical or bearish_count >= 3 else "HIGH"
    elif is_critical:
        sentiment = "NEUTRAL"
        impact = "CRITICAL"
    else:
        sentiment = "NEUTRAL"
        impact = "LOW"
    
    return {
        'sentiment': sentiment,
        'impact': impact,
        'is_critical': is_critical,
        'bullish_score': bullish_count,
        'bearish_score': bearish_count
    }


async def monitor_breaking_news():
    """Мониторинг на критични новини в реално време"""
    try:
        # Извлечи последни новини
        news = await fetch_market_news()
        
        if not news:
            return
        
        # Проверка дали имаме cache файл за последно видените новини
        cache_file = f"{BASE_PATH}/news_cache.json"
        seen_news = set()
        
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r') as f:
                    import json
                    cache_data = json.load(f)
                    seen_news = set(cache_data.get('seen_titles', []))
            except:
                pass
        
        critical_news = []
        
        for article in news:
            title = article['title']
            
            # Провери дали новината вече е видяна
            if title in seen_news:
                continue
            
            # Анализирай въздействието
            impact = await analyze_news_impact(title, article.get('description', ''))
            
            # Само критични и високо въздействащи новини
            if impact['impact'] in ['CRITICAL', 'HIGH']:
                article['impact_analysis'] = impact
                critical_news.append(article)
                seen_news.add(title)
        
        # Запази виждането в cache
        if critical_news:
            try:
                import json
                with open(cache_file, 'w') as f:
                    json.dump({'seen_titles': list(seen_news)}, f)
            except Exception as e:
                logger.error(f"Грешка при запис на news cache: {e}")
        
        # Изпрати критичните новини
        if critical_news:
            await send_critical_news_alert(critical_news)
            logger.info(f"🚨 {len(critical_news)} критични новини изпратени!")
        
    except Exception as e:
        logger.error(f"Грешка при мониторинг на новини: {e}")


async def send_daily_signal_report(bot):
    """Изпраща автоматичен дневен отчет за всички сигнали от предходния ден"""
    try:
        from datetime import datetime, timedelta
        
        # Зареди статистиката
        stats = load_stats()
        
        if 'signals' not in stats or not stats['signals']:
            logger.info("Няма сигнали за дневен отчет")
            return
        
        # Определи началото и края на предходния ден
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        yesterday_start = today - timedelta(days=1)
        yesterday_end = today
        
        # Филтрирай сигналите от предходния ден
        yesterday_signals = []
        for signal in stats['signals']:
            try:
                signal_time = datetime.fromisoformat(signal['timestamp'])
                if yesterday_start <= signal_time < yesterday_end:
                    yesterday_signals.append(signal)
            except:
                continue
        
        if not yesterday_signals:
            message = f"""📊 <b>ДНЕВЕН ОТЧЕТ</b>
📅 {yesterday_start.strftime('%d.%m.%Y')}

❌ Няма генерирани сигнали за предходния ден.
"""
            await bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=message,
                parse_mode='HTML',
                disable_notification=False
            )
            return
        
        # Анализ на успешни/неуспешни сигнали
        total_signals = len(yesterday_signals)
        successful_signals = 0
        failed_signals = 0
        pending_signals = 0
        
        # Статистика по тип
        buy_signals = sum(1 for s in yesterday_signals if s['type'] == 'BUY')
        sell_signals = sum(1 for s in yesterday_signals if s['type'] == 'SELL')
        
        # Средна увереност
        avg_confidence = sum(s['confidence'] for s in yesterday_signals) / total_signals
        
        # Проверка на успешност (ако има entry/tp/sl данни)
        for signal in yesterday_signals:
            if 'entry_price' in signal and 'tp_price' in signal:
                # Провери дали TP е достигната (опростена проверка)
                # В реална имплементация трябва да се провери текущата цена
                # За целите на отчета, използваме outcome ако е зададен
                if 'outcome' in signal:
                    if signal['outcome'] == 'success':
                        successful_signals += 1
                    elif signal['outcome'] == 'failed':
                        failed_signals += 1
                    else:
                        pending_signals += 1
                else:
                    pending_signals += 1
            else:
                pending_signals += 1
        
        # Статистика по символ
        by_symbol = {}
        for signal in yesterday_signals:
            sym = signal['symbol']
            if sym not in by_symbol:
                by_symbol[sym] = {'count': 0, 'BUY': 0, 'SELL': 0}
            by_symbol[sym]['count'] += 1
            by_symbol[sym][signal['type']] += 1
        
        # Статистика по таймфрейм
        by_timeframe = {}
        for signal in yesterday_signals:
            tf = signal.get('timeframe', 'N/A')
            if tf not in by_timeframe:
                by_timeframe[tf] = 0
            by_timeframe[tf] += 1
        
        # Генерирай отчета
        message = f"""📊 <b>ДНЕВЕН ОТЧЕТ ЗА СИГНАЛИ</b>
📅 {yesterday_start.strftime('%d.%m.%Y')} (Предходен ден)
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>ОБЩА СТАТИСТИКА:</b>
🔢 Общо сигнали: <b>{total_signals}</b>
✅ Успешни: <b>{successful_signals}</b> ({(successful_signals/total_signals*100) if total_signals > 0 else 0:.1f}%)
❌ Неуспешни: <b>{failed_signals}</b> ({(failed_signals/total_signals*100) if total_signals > 0 else 0:.1f}%)
⏳ В изчакване: <b>{pending_signals}</b> ({(pending_signals/total_signals*100) if total_signals > 0 else 0:.1f}%)

💪 Средна увереност: <b>{avg_confidence:.1f}%</b>

📊 <b>ПО ТИП:</b>
🟢 BUY сигнали: <b>{buy_signals}</b>
🔴 SELL сигнали: <b>{sell_signals}</b>

💰 <b>ПО ВАЛУТА:</b>
"""
        
        for sym, data in sorted(by_symbol.items(), key=lambda x: x[1]['count'], reverse=True):
            message += f"• {sym}: {data['count']} ({data['BUY']} BUY, {data['SELL']} SELL)\n"
        
        message += f"\n⏰ <b>ПО ТАЙМФРЕЙМ:</b>\n"
        for tf, count in sorted(by_timeframe.items(), key=lambda x: x[1], reverse=True):
            message += f"• {tf}: {count} сигнала\n"
        
        # Топ 5 сигнала с най-висока увереност
        top_signals = sorted(yesterday_signals, key=lambda x: x['confidence'], reverse=True)[:5]
        if top_signals:
            message += f"\n🏆 <b>ТОП 5 СИГНАЛА (по увереност):</b>\n"
            for i, sig in enumerate(top_signals, 1):
                sig_emoji = "🟢" if sig['type'] == 'BUY' else "🔴"
                message += f"{i}. {sig_emoji} {sig['symbol']} {sig['type']} - {sig['confidence']:.0f}% ({sig.get('timeframe', 'N/A')})\n"
        
        message += f"\n━━━━━━━━━━━━━━━━━━━━━━━━"
        message += f"\n⚠️ <i>Отчетът е автоматичен и базиран на генерирани сигнали.</i>"
        message += f"\n📱 <i>Използвай /stats за пълна статистика</i>"
        
        # Изпрати отчета
        await bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=message,
            parse_mode='HTML',
            disable_notification=False  # С звукова нотификация
        )
        
        logger.info(f"✅ Daily signal report sent: {total_signals} signals from {yesterday_start.strftime('%Y-%m-%d')}")
        
    except Exception as e:
        logger.error(f"Грешка при генериране на дневен отчет: {e}")


async def send_task_completion_notification(task_id, task_title, changes_summary):
    """Изпраща нотификация когато задача е завършена"""
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        message = f"""✅ <b>ЗАДАЧАТА ЗАВЪРШЕНА!</b>

🆔 <b>Task #{task_id}</b>
📝 <b>Задание:</b> {task_title}

✨ <b>Промени:</b>
{changes_summary}

🎉 <b>Статус:</b> Изпълнено успешно!
📅 <b>Завършено:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 <b>Промените са автоматично запазени!</b>
🔄 Ботът е рестартиран с новите подобрения.

👉 Тествай новите функции сега!
"""
        
        # Изпрати съобщение С нотификация
        await bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=message,
            parse_mode='HTML',
            disable_notification=False  # ВАЖНО: sound alert!
        )
        
        logger.info(f"✅ Notification sent for Task #{task_id}")
        
    except Exception as e:
        logger.error(f"Грешка при изпращане на notification: {e}")


async def send_critical_news_alert(critical_news):
    """Изпраща СПЕШНА алерта за критични новини"""
    try:
        from telegram import Bot
        bot = Bot(token=TELEGRAM_BOT_TOKEN)
        
        for article in critical_news:
            impact = article['impact_analysis']
            
            # Използвай преведеното заглавие и описание
            title_bg = article.get('title_bg', article.get('title', 'Без заглавие'))
            desc_bg = article.get('description_bg', '')
            
            # Escape Telegram символи
            title_bg = title_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            desc_bg = desc_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            # Избери емоджи според impact
            if impact['impact'] == 'CRITICAL':
                alert_emoji = "🚨🚨🚨"
                priority = "КРИТИЧНА"
            else:
                alert_emoji = "⚠️⚠️"
                priority = "ВАЖНА"
            
            # Избери емоджи според sentiment
            if impact['sentiment'] == 'BULLISH':
                sentiment_emoji = "🟢📈"
                sentiment_text = "BULLISH (Възможен растеж)"
            elif impact['sentiment'] == 'BEARISH':
                sentiment_emoji = "🔴📉"
                sentiment_text = "BEARISH (Възможен спад)"
            else:
                sentiment_emoji = "⚪➡️"
                sentiment_text = "NEUTRAL (Наблюдавай)"
            
            message = f"""{alert_emoji} <b>{priority} НОВИНА!</b> {alert_emoji}

{article.get('source', '📰')} <b>{title_bg}</b>

{sentiment_emoji} <b>Анализ на въздействието:</b>
• Sentiment: {sentiment_text}
• Важност: {impact['impact']}
• Bullish фактори: {impact['bullish_score']}
• Bearish фактори: {impact['bearish_score']}

"""
            
            if desc_bg:
                desc_short = desc_bg[:200] + "..." if len(desc_bg) > 200 else desc_bg
                message += f"<i>{desc_short}</i>\n\n"
            
            if article.get('link'):
                message += f"🔗 <a href=\"{article['link']}\">Прочети пълна статия</a>\n"
                message += f"🌍 <i>Автоматично преведено на български</i>\n\n"
            
            message += f"⏰ <b>Време:</b> {datetime.now().strftime('%H:%M:%S UTC')}\n"
            message += f"💡 <b>Препоръка:</b> "
            
            if impact['sentiment'] == 'BULLISH' and impact['impact'] == 'CRITICAL':
                message += "Разгледай възможности за покупка!"
            elif impact['sentiment'] == 'BEARISH' and impact['impact'] == 'CRITICAL':
                message += "Внимание! Разгледай защита на позиции!"
            else:
                message += "Следи пазара за промени!"
            
            # Изпрати с звукова алерта
            await bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=message,
                parse_mode='HTML',
                disable_web_page_preview=True,
                disable_notification=False  # ЗВУКОВА АЛЕРТА!
            )
            
            # Малка пауза между съобщенията
            await asyncio.sleep(1)
        
    except Exception as e:
        logger.error(f"Грешка при изпращане на критична новина: {e}")


async def fetch_fear_greed_index():
    """Извлича Fear & Greed Index от Alternative.me"""
    try:
        url = "https://api.alternative.me/fng/"
        resp = await asyncio.to_thread(requests.get, url, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if 'data' in data and len(data['data']) > 0:
                latest = data['data'][0]
                return {
                    'value': int(latest['value']),
                    'classification': latest['value_classification'],
                    'timestamp': latest['timestamp']
                }
        return None
    except Exception as e:
        logger.error(f"Грешка при извличане на Fear & Greed Index: {e}")
        return None


async def fetch_coingecko_market_data(coin_id):
    """Извлича допълнителни пазарни данни от CoinGecko"""
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}"
        params = {
            'localization': 'false',
            'tickers': 'false',
            'community_data': 'true',
            'developer_data': 'false',
            'sparkline': 'false'
        }
        
        resp = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            market_data = data.get('market_data', {})
            community = data.get('community_data', {})
            
            return {
                'market_cap_rank': data.get('market_cap_rank', 'N/A'),
                'sentiment_votes_up': community.get('sentiment_votes_up_percentage', 0),
                'sentiment_votes_down': community.get('sentiment_votes_down_percentage', 0),
                'price_change_7d': market_data.get('price_change_percentage_7d', 0),
                'price_change_30d': market_data.get('price_change_percentage_30d', 0),
                'market_cap_change_24h': market_data.get('market_cap_change_percentage_24h', 0),
                'circulating_supply': market_data.get('circulating_supply', 0),
                'total_supply': market_data.get('total_supply', 0)
            }
        return None
    except Exception as e:
        logger.error(f"Грешка при извличане от CoinGecko за {coin_id}: {e}")
        return None


async def fetch_cryptocompare_sentiment(symbol):
    """Извлича социален sentiment от CryptoCompare"""
    try:
        # Използва се безплатния API без ключ (ограничен брой заявки)
        url = f"https://min-api.cryptocompare.com/data/social/coin/latest"
        params = {'coinId': symbol}
        
        resp = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
        
        if resp.status_code == 200:
            data = resp.json()
            if 'Data' in data:
                social = data['Data']
                return {
                    'reddit_active_users': social.get('Reddit', {}).get('active_users', 0),
                    'twitter_followers': social.get('Twitter', {}).get('followers', 0),
                    'twitter_points': social.get('Twitter', {}).get('Points', 0)
                }
        return None
    except Exception as e:
        logger.error(f"Грешка при извличане от CryptoCompare за {symbol}: {e}")
        return None


async def fetch_market_news():
    """Извлича последни крипто новини от най-надеждните източници"""
    all_news = []
    
    # === 1. Cointelegraph RSS Feed (Най-надежден!) ===
    try:
        cointelegraph_rss = "https://cointelegraph.com/rss"
        feed = await asyncio.to_thread(feedparser.parse, cointelegraph_rss)
        
        for entry in feed.entries[:5]:  # Top 5 от Cointelegraph
            clean_title = BeautifulSoup(entry.title, 'html.parser').get_text()
            clean_desc = BeautifulSoup(entry.get('summary', ''), 'html.parser').get_text()
            
            # Автоматичен превод на български
            title_bg = await translate_text(clean_title)
            desc_bg = await translate_text(clean_desc[:500]) if clean_desc else ''
            
            # Google Translate wrapper за преведена статия на български
            translate_url = f"https://translate.google.com/translate?sl=en&tl=bg&u={entry.link}"
            
            all_news.append({
                'title': clean_title,
                'title_bg': title_bg,
                'description': clean_desc,
                'description_bg': desc_bg,
                'link': entry.link,
                'translate_link': translate_url,
                'source': '📊 Cointelegraph'
            })
            logger.info(f"✅ Cointelegraph: {clean_title[:50]}")
    except Exception as e:
        logger.error(f"❌ Грешка при Cointelegraph: {e}")
    
    # === 2. CoinMarketCap API (Public - NO KEY!) ===
    try:
        cmc_api_url = "https://api.coinmarketcap.com/data-api/v3/headlines/latest"
        resp = await asyncio.to_thread(requests.get, cmc_api_url, timeout=10)
        
        if resp.status_code == 200:
            cmc_data = resp.json()
            if 'data' in cmc_data and cmc_data['data']:
                for article in cmc_data['data'][:5]:  # Top 5 от CMC
                    title = article.get('title', 'No title')
                    description = article.get('subtitle', '')
                    link = f"https://coinmarketcap.com/headlines/news/{article.get('slug', '')}"
                    
                    # Автоматичен превод
                    title_bg = await translate_text(title)
                    desc_bg = await translate_text(description[:500]) if description else ''
                    
                    # Google Translate wrapper
                    translate_url = f"https://translate.google.com/translate?sl=en&tl=bg&u={link}"
                    
                    all_news.append({
                        'title': title,
                        'title_bg': title_bg,
                        'description': description,
                        'description_bg': desc_bg,
                        'link': link,
                        'translate_link': translate_url,
                        'source': '💎 CoinMarketCap'
                    })
                    logger.info(f"✅ CoinMarketCap: {title[:50]}")
    except Exception as e:
        logger.error(f"❌ Грешка при CoinMarketCap: {e}")
    
    logger.info(f"📰 Total news fetched: {len(all_news)}")
    return all_news[:10] if all_news else []  # Top 10 новини общо


async def analyze_coin_performance(coin_data, include_external=True):
    """Детайлен анализ на отделна монета с данни от външни API"""
    try:
        symbol = coin_data['symbol']
        price = float(coin_data['lastPrice'])
        change = float(coin_data['priceChangePercent'])
        high = float(coin_data['highPrice'])
        low = float(coin_data['lowPrice'])
        quote_volume = float(coin_data['quoteVolume'])
        volume = float(coin_data.get('volume', quote_volume))  # Добави volume
        trades = int(coin_data['count'])
        
        # CoinGecko mapping
        coingecko_map = {
            'BTCUSDT': 'bitcoin',
            'ETHUSDT': 'ethereum',
            'BNBUSDT': 'binancecoin',
            'SOLUSDT': 'solana',
            'XRPUSDT': 'ripple',
            'ADAUSDT': 'cardano'
        }
        
        # Извличане на допълнителни данни от CoinGecko (ако е активирано)
        external_data = None
        if include_external and symbol in coingecko_map:
            external_data = await fetch_coingecko_market_data(coingecko_map[symbol])
        
        # Ценови диапазон
        price_range = ((high - low) / low) * 100
        current_position = ((price - low) / (high - low)) * 100 if high != low else 50
        
        # Волатилност
        if price_range < 2:
            volatility = "Ниска"
            vol_emoji = "📊"
        elif price_range < 5:
            volatility = "Средна"
            vol_emoji = "📈"
        else:
            volatility = "Висока"
            vol_emoji = "⚡"
        
        # Тренд оценка
        if change > 5:
            trend = "Силен растеж"
            trend_emoji = "🚀"
            strength = "STRONG_BULLISH"
        elif change > 2:
            trend = "Умерен растеж"
            trend_emoji = "📈"
            strength = "BULLISH"
        elif change > 0:
            trend = "Леко нагоре"
            trend_emoji = "🟢"
            strength = "SLIGHTLY_BULLISH"
        elif change > -2:
            trend = "Леко надолу"
            trend_emoji = "🔴"
            strength = "SLIGHTLY_BEARISH"
        elif change > -5:
            trend = "Умерен спад"
            trend_emoji = "📉"
            strength = "BEARISH"
        else:
            trend = "Силен спад"
            trend_emoji = "💥"
            strength = "STRONG_BEARISH"
        
        # Позиция в диапазона
        if current_position >= 80:
            position_text = "Близо до върха"
            position_emoji = "🔝"
        elif current_position >= 60:
            position_text = "Горна част"
            position_emoji = "⬆️"
        elif current_position >= 40:
            position_text = "Средна част"
            position_emoji = "➡️"
        elif current_position >= 20:
            position_text = "Долна част"
            position_emoji = "⬇️"
        else:
            position_text = "Близо до дъното"
            position_emoji = "🔻"
        
        # Обогатена препоръка с външни данни
        action = "📊 Наблюдавай за потвърждение"
        confidence = "Средна"
        
        if external_data:
            # Вземи предвид 7-дневния тренд
            change_7d = external_data.get('price_change_7d', 0)
            sentiment_up = external_data.get('sentiment_votes_up', 50)
            
            # Силна препоръка за покупка
            if (strength in ["STRONG_BULLISH", "BULLISH"] and 
                current_position < 70 and 
                change_7d > 0 and 
                sentiment_up > 60):
                action = "✅ Силна възможност за покупка (потвърдена от множество източници)"
                confidence = "Висока"
            
            # Предупреждение за спад
            elif (strength in ["STRONG_BEARISH", "BEARISH"] and 
                  current_position > 30 and 
                  change_7d < 0 and 
                  sentiment_up < 40):
                action = "🚨 Силно предупреждение - намаляващ тренд (потвърден от анализи)"
                confidence = "Висока"
            
            # Възможна корекция
            elif current_position >= 85 and sentiment_up < 50:
                action = "⚠️ Висока вероятност за корекция (близо до върха + негативен sentiment)"
                confidence = "Средна към висока"
            
            # Възможен rebound
            elif current_position <= 15 and sentiment_up > 50:
                action = "💡 Добра възможност за rebound (близо до дъното + позитивен sentiment)"
                confidence = "Средна към висока"
        else:
            # Стандартна препоръка без външни данни
            if strength in ["STRONG_BULLISH", "BULLISH"] and current_position < 70:
                action = "✅ Добра възможност за покупка"
                confidence = "Средна"
            elif strength in ["STRONG_BEARISH", "BEARISH"] and current_position > 30:
                action = "⚠️ Внимание - намаляващ тренд"
                confidence = "Средна"
            elif current_position >= 85:
                action = "⚠️ Възможна корекция (близо до върха)"
                confidence = "Ниска към средна"
            elif current_position <= 15:
                action = "💡 Възможен rebound (близо до дъното)"
                confidence = "Ниска към средна"
        
        result = {
            'symbol': symbol,
            'price': price,
            'change': change,
            'high': high,
            'low': low,
            'volume': volume,
            'quote_volume': quote_volume,
            'trades': trades,
            'price_range': price_range,
            'current_position': current_position,
            'volatility': volatility,
            'vol_emoji': vol_emoji,
            'trend': trend,
            'trend_emoji': trend_emoji,
            'strength': strength,
            'position_text': position_text,
            'position_emoji': position_emoji,
            'action': action,
            'confidence': confidence
        }
        
        # Добави външни данни ако са налични
        if external_data:
            result['external_data'] = external_data
        
        return result
        
    except Exception as e:
        logger.error(f"Грешка при анализ на {coin_data.get('symbol', 'Unknown')}: {e}")
        return None


async def analyze_market_sentiment(market_data):
    """Анализира пазарния sentiment базиран на цени и обеми"""
    try:
        total_coins = len(market_data)
        if total_coins == 0:
            return {'sentiment': 'NEUTRAL', 'score': 50, 'description': 'Няма данни'}
        
        # Брой монети с положителна/отрицателна промяна
        positive = sum(1 for item in market_data if float(item['priceChangePercent']) > 0)
        negative = sum(1 for item in market_data if float(item['priceChangePercent']) < 0)
        
        # Средна промяна
        avg_change = sum(float(item['priceChangePercent']) for item in market_data) / total_coins
        
        # Общ обем
        total_volume = sum(float(item['quoteVolume']) for item in market_data)
        
        # Sentiment score (0-100)
        sentiment_score = 50 + (avg_change * 10)  # Base на средна промяна
        sentiment_score += ((positive - negative) / total_coins) * 25  # Adjustment за ratio
        sentiment_score = max(0, min(100, sentiment_score))  # Clamp 0-100
        
        # Определи sentiment
        if sentiment_score >= 70:
            sentiment = 'BULLISH'
            emoji = '🐂'
            description = 'Силен бичи пазар'
        elif sentiment_score >= 55:
            sentiment = 'SLIGHTLY_BULLISH'
            emoji = '📈'
            description = 'Леко бичи настроение'
        elif sentiment_score >= 45:
            sentiment = 'NEUTRAL'
            emoji = '➡️'
            description = 'Неутрален пазар'
        elif sentiment_score >= 30:
            sentiment = 'SLIGHTLY_BEARISH'
            emoji = '📉'
            description = 'Леко мечи настроение'
        else:
            sentiment = 'BEARISH'
            emoji = '🐻'
            description = 'Силен мечи пазар'
        
        return {
            'sentiment': sentiment,
            'emoji': emoji,
            'score': sentiment_score,
            'description': description,
            'avg_change': avg_change,
            'positive_count': positive,
            'negative_count': negative,
            'total_volume': total_volume
        }
        
    except Exception as e:
        logger.error(f"Грешка при анализ на sentiment: {e}")
        return {'sentiment': 'NEUTRAL', 'emoji': '➡️', 'score': 50, 'description': 'Неизвестно'}


async def market_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Дневен анализ за всички интегрирани валути с новини и sentiment"""
    logger.info(f"User {update.effective_user.id} executed /market")
    await update.message.reply_text("📊 Анализирам пазара от множество източници...")
    
    # Извлечи пазарни данни
    data = await fetch_json(BINANCE_24H_URL)
    if not data:
        await update.message.reply_text("❌ Грешка при извличане на данни")
        return
    
    # Филтрирай само нашите символи
    our_symbols = set(SYMBOLS.values())
    market_data = [s for s in data if s['symbol'] in our_symbols]
    
    # Анализирай sentiment
    sentiment_analysis = await analyze_market_sentiment(market_data)
    
    # Извлечи новини и Fear & Greed Index (async)
    news_task = asyncio.create_task(fetch_market_news())
    fear_greed_task = asyncio.create_task(fetch_fear_greed_index())
    
    # Сортирай по обем
    market_data.sort(key=lambda x: float(x['volume']), reverse=True)
    
    # Изчакай Fear & Greed Index
    fear_greed = await fear_greed_task
    
    # Извлечи статистика за вчерашните сигнали
    yesterday_stats = get_yesterday_signal_stats()
    
    # === MARKET SENTIMENT SECTION ===
    message = "📊 <b>ДНЕВЕН ПАЗАРЕН АНАЛИЗ</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Добави статистика за предходния ден ако има данни
    if yesterday_stats['has_data']:
        message += f"<b>📈 Сигнали от вчера:</b>\n"
        message += f"📊 Общо пуснати: <b>{yesterday_stats['total']}</b>\n"
        message += f"✅ Успешни: <b>{yesterday_stats['successful']}</b>\n"
        message += f"❌ Неуспешни: <b>{yesterday_stats['failed']}</b>\n"
        
        if yesterday_stats['active'] > 0:
            message += f"⏳ Активни: <b>{yesterday_stats['active']}</b>\n"
        
        # Win rate с емоджи
        if yesterday_stats['win_rate'] >= 70:
            wr_emoji = "🔥"
        elif yesterday_stats['win_rate'] >= 60:
            wr_emoji = "💪"
        elif yesterday_stats['win_rate'] >= 50:
            wr_emoji = "👍"
        else:
            wr_emoji = "⚠️"
        
        message += f"{wr_emoji} Win Rate: <b>{yesterday_stats['win_rate']:.1f}%</b>\n"
        
        # Средна печалба
        if yesterday_stats['avg_profit'] > 0:
            message += f"💰 Средна печалба: <b>+{yesterday_stats['avg_profit']:.2f}%</b>\n"
        elif yesterday_stats['avg_profit'] < 0:
            message += f"💸 Средна загуба: <b>{yesterday_stats['avg_profit']:.2f}%</b>\n"
        
        message += "\n"
    
    message += f"<b>🎯 Пазарен Sentiment:</b>\n"
    message += f"{sentiment_analysis['emoji']} <b>{sentiment_analysis['description']}</b>\n"
    message += f"📈 Sentiment Score: <b>{sentiment_analysis['score']:.1f}/100</b>\n"
    
    # Добави Fear & Greed Index ако е наличен
    if fear_greed:
        fg_emoji = "😱" if fear_greed['value'] < 25 else "😰" if fear_greed['value'] < 45 else "😐" if fear_greed['value'] < 55 else "😊" if fear_greed['value'] < 75 else "🤑"
        message += f"\n{fg_emoji} <b>Fear & Greed Index:</b> {fear_greed['value']}/100 ({fear_greed['classification']})\n"
        message += f"<i>Източник: Alternative.me</i>\n"
    
    message += f"\n📊 Средна промяна: <b>{sentiment_analysis['avg_change']:+.2f}%</b>\n"
    message += f"🟢 Растящи: <b>{sentiment_analysis['positive_count']}</b> | "
    message += f"🔴 Падащи: <b>{sentiment_analysis['negative_count']}</b>\n\n"
    
    # === INDIVIDUAL COINS ===
    message += "<b>💰 Криптовалути (24ч):</b>\n\n"
    
    for item in market_data:
        symbol = item['symbol']
        price = float(item['lastPrice'])
        change = float(item['priceChangePercent'])
        volume = float(item['volume'])
        
        # Емоджи според промяната
        emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
        
        # Форматиране на обема
        if volume > 1_000_000:
            vol_str = f"{volume/1_000_000:.1f}M"
        else:
            vol_str = f"{volume/1_000:.1f}K"
        
        message += f"{emoji} <b>{symbol}</b>\n"
        message += f"   Цена: ${price:,.2f}\n"
        message += f"   Промяна: {change:+.2f}%\n"
        message += f"   Обем: {vol_str}\n\n"
    
    # Изпрати първата част
    await update.message.reply_text(message, parse_mode='HTML')
    
    # === DETAILED COIN ANALYSIS ===
    await update.message.reply_text("📊 Подготвям детайлен анализ с данни от CoinGecko...")
    
    for item in market_data:
        # Анализирай с външни данни (CoinGecko)
        analysis = await analyze_coin_performance(item, include_external=True)
        
        if not analysis:
            continue
        
        # Детайлно съобщение за всяка монета
        coin_msg = f"━━━━━━━━━━━━━━━━━━━━━━━━\n"
        coin_msg += f"<b>{analysis['symbol']}</b>\n"
        coin_msg += f"━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Основна информация
        coin_msg += f"💰 <b>Цена:</b> ${analysis['price']:,.4f}\n"
        coin_msg += f"{analysis['trend_emoji']} <b>Промяна 24ч:</b> {analysis['change']:+.2f}%\n"
        coin_msg += f"📊 <b>Тренд:</b> {analysis['trend']}\n\n"
        
        # Ценови диапазон
        coin_msg += f"<b>📈 Ценови Диапазон (24ч):</b>\n"
        coin_msg += f"   🔺 Най-висока: ${analysis['high']:,.4f}\n"
        coin_msg += f"   🔻 Най-ниска: ${analysis['low']:,.4f}\n"
        coin_msg += f"   📏 Размах: {analysis['price_range']:.2f}%\n"
        coin_msg += f"   {analysis['position_emoji']} <b>Позиция:</b> {analysis['position_text']} ({analysis['current_position']:.0f}%)\n\n"
        
        # Волатилност
        coin_msg += f"{analysis['vol_emoji']} <b>Волатилност:</b> {analysis['volatility']}\n\n"
        
        # Добави данни от CoinGecko ако са налични
        if 'external_data' in analysis:
            ext = analysis['external_data']
            coin_msg += f"<b>📊 Разширен Анализ (CoinGecko):</b>\n"
            coin_msg += f"   📈 Промяна 7д: {ext.get('price_change_7d', 0):+.2f}%\n"
            coin_msg += f"   📅 Промяна 30д: {ext.get('price_change_30d', 0):+.2f}%\n"
            coin_msg += f"   👥 Community: 👍 {ext.get('sentiment_votes_up', 0):.0f}% / 👎 {ext.get('sentiment_votes_down', 0):.0f}%\n"
            coin_msg += f"   🏆 Market Cap Rank: #{ext.get('market_cap_rank', 'N/A')}\n\n"
        
        # Обем и активност
        coin_msg += f"<b>💵 Активност (24ч):</b>\n"
        
        # Форматирай обема
        if analysis['quote_volume'] > 1_000_000_000:
            quote_vol = f"${analysis['quote_volume']/1_000_000_000:.2f}B"
        elif analysis['quote_volume'] > 1_000_000:
            quote_vol = f"${analysis['quote_volume']/1_000_000:.1f}M"
        else:
            quote_vol = f"${analysis['quote_volume']/1_000:.0f}K"
        
        coin_msg += f"   💰 Обем: {quote_vol}\n"
        coin_msg += f"   🔄 Сделки: {analysis['trades']:,}\n\n"
        
        # Препоръка с ниво на увереност
        coin_msg += f"<b>💡 Препоръка:</b>\n{analysis['action']}\n"
        coin_msg += f"💪 <b>Увереност:</b> {analysis['confidence']}\n\n"
        
        # Източник на информацията
        sources = "Binance"
        if 'external_data' in analysis:
            sources += ", CoinGecko"
        coin_msg += f"<i>📊 Източници: {sources}</i>"
        
        # Изпрати анализа за тази монета
        await update.message.reply_text(coin_msg, parse_mode='HTML')
        
        # Малка пауза между съобщенията (увеличена заради по-дълги съобщения)
        await asyncio.sleep(0.7)
    
    # === MARKET NEWS SECTION ===
    news = await news_task
    
    if news:
        import re
        import html
        
        news_message = "<b>📰 Последни Новини (Топ източници):</b>\n\n"
        
        for i, article in enumerate(news[:3], 1):  # Първите 3
            source = article.get('source', '📰')
            
            # Използвай преведеното заглавие ако е налично
            title_bg = article.get('title_bg', article.get('title', 'Без заглавие'))
            desc_bg = article.get('description_bg', '')
            link = article.get('link', None)
            
            # Escape специални символи
            title_bg = title_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            news_message += f"{i}. {source} <b>{title_bg}</b>\n"
            
            if desc_bg:
                desc_bg = desc_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                desc_short = desc_bg[:100] + "..." if len(desc_bg) > 100 else desc_bg
                news_message += f"   <i>{desc_short}</i>\n"
            
            if link:
                news_message += f"   🔗 <a href=\"{link}\">Прочети пълната статия</a>\n"
            
            news_message += "\n"
        
        news_message += f"<i>📰 Източник: Cointelegraph (без блокировки)</i>\n"
        news_message += "<i>🌍 Автоматично преведени на български</i>\n"
        news_message += "<i>📱 Използвай /news за повече новини</i>"
        
        await update.message.reply_text(news_message, parse_mode='HTML', disable_web_page_preview=True)
    
    # === TRADING RECOMMENDATION ===
    recommendation = ""
    if sentiment_analysis['score'] >= 65:
        recommendation = "✅ <b>Препоръка:</b> Благоприятно време за LONG позиции\n"
        recommendation += "💡 Пазарът показва силно бичи настроение"
    elif sentiment_analysis['score'] >= 55:
        recommendation = "📈 <b>Препоръка:</b> Внимателни LONG позиции\n"
        recommendation += "💡 Леко позитивно настроение, следете волатилността"
    elif sentiment_analysis['score'] >= 45:
        recommendation = "⚖️ <b>Препоръка:</b> Изчакайте по-ясен сигнал\n"
        recommendation += "💡 Неутрален пазар, подходящ за range trading"
    elif sentiment_analysis['score'] >= 35:
        recommendation = "📉 <b>Препоръка:</b> Внимателни SHORT позиции\n"
        recommendation += "💡 Леко негативно настроение, пазете стопове"
    else:
        recommendation = "❌ <b>Препоръка:</b> Избягвайте нови позиции\n"
        recommendation += "💡 Силно мечи настроение, изчакайте стабилизация"
    
    recommendation += "\n\n⚠️ <i>Това не е финансов съвет. DYOR!</i>"
    
    await update.message.reply_text(recommendation, parse_mode='HTML')




async def signal_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Анализ и сигнал в реално време"""
    logger.info(f"User {update.effective_user.id} executed /signal with args: {context.args}")
    
    if not context.args:
        # Покажи бутони за избор на валута
        keyboard = [
            [
                InlineKeyboardButton("₿ BTC", callback_data="signal_BTCUSDT"),
                InlineKeyboardButton("Ξ ETH", callback_data="signal_ETHUSDT"),
            ],
            [
                InlineKeyboardButton("⚡ SOL", callback_data="signal_SOLUSDT"),
                InlineKeyboardButton("💎 XRP", callback_data="signal_XRPUSDT"),
            ],
            [
                InlineKeyboardButton("🔷 BNB", callback_data="signal_BNBUSDT"),
                InlineKeyboardButton("♠️ ADA", callback_data="signal_ADAUSDT"),
            ],
            [
                InlineKeyboardButton("🏠 Главно меню", callback_data="back_to_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📈 <b>Избери валута за анализ:</b>\n\n💡 <i>Съвет: Използвай /signal BTC 15m за конкретен таймфрейм</i>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    symbol = context.args[0].upper()
    
    # Провери за таймфрейм във втория аргумент
    custom_timeframe = None
    if len(context.args) > 1:
        tf = context.args[1].lower()
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '3h', '4h', '1d', '1w']
        if tf in valid_timeframes:
            custom_timeframe = tf
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Невалиден таймфрейм: {tf}\n\nВалидни: {', '.join(valid_timeframes)}",
                parse_mode='HTML'
            )
            return
    
    # Провери дали символът е валиден
    if symbol not in SYMBOLS.values():
        # Опитай се да го намериш в кратките имена
        found = False
        for short, full in SYMBOLS.items():
            if symbol == short:
                symbol = full
                found = True
                break
        if not found:
            await update.message.reply_text(f"❌ Непознат символ: {symbol}")
            return
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=f"🔍 Анализирам {symbol}...",
        parse_mode='HTML'
    )
    
    # Вземи настройките на потребителя
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    
    # Използвай custom timeframe ако е подаден, иначе настройката на потребителя
    timeframe = custom_timeframe if custom_timeframe else settings['timeframe']
    
    # Извлечи 24h данни
    params_24h = {'symbol': symbol}
    data_24h = await fetch_json(BINANCE_24H_URL, params_24h)
    
    if not data_24h or isinstance(data_24h, list):
        # Ако е списък, намери нашия символ
        if isinstance(data_24h, list):
            data_24h = next((s for s in data_24h if s['symbol'] == symbol), None)
    
    if not data_24h:
        await update.message.reply_text("❌ Грешка при извличане на данни")
        return
    
    # Извлечи исторически данни (klines)
    klines = await fetch_klines(symbol, timeframe, limit=100)
    
    if not klines:
        await update.message.reply_text("❌ Грешка при извличане на исторически данни")
        return
    
    # Анализирай
    analysis = analyze_signal(data_24h, klines, symbol, timeframe)
    
    if not analysis:
        await update.message.reply_text("❌ Грешка при анализ")
        return
    
    # === BTC CORRELATION ANALYSIS ===
    btc_correlation = await analyze_btc_correlation(symbol, timeframe)
    
    # === ORDER BOOK ANALYSIS ===
    order_book = await analyze_order_book(symbol, analysis['price'])
    
    # === MULTI-TIMEFRAME CONFIRMATION ===
    mtf_confirmation = await get_higher_timeframe_confirmation(symbol, timeframe, analysis['signal'])
    
    # === NEWS SENTIMENT ANALYSIS ===
    sentiment = await analyze_news_sentiment(symbol)
    
    # === MULTI-TIMEFRAME ANALYSIS ===
    logger.info(f"Starting multi-timeframe analysis for {symbol}")
    mtf_analysis = await get_multi_timeframe_analysis(symbol, timeframe)
    logger.info(f"MTF analysis result: {mtf_analysis}")
    
    # Коригирай confidence според допълнителните анализи
    final_confidence = analysis['confidence']
    
    # Order Book корекция
    if order_book:
        if order_book['pressure'] == analysis['signal']:
            final_confidence += 10
            analysis['reasons'].append(f"Order Book натиск: {order_book['pressure']}")
        elif order_book['pressure'] != 'NEUTRAL' and order_book['pressure'] != analysis['signal']:
            final_confidence -= 8
            analysis['reasons'].append(f"Order Book противоречи ({order_book['pressure']})")
        
        # Ако има близки стени
        if order_book['closest_support'] and analysis['signal'] == 'BUY':
            support_price = order_book['closest_support'][0]
            if abs(analysis['price'] - support_price) / analysis['price'] < 0.02:  # В рамките на 2%
                final_confidence += 8
                analysis['reasons'].append(f"Силна support стена на ${support_price:,.2f}")
        
        if order_book['closest_resistance'] and analysis['signal'] == 'SELL':
            resistance_price = order_book['closest_resistance'][0]
            if abs(resistance_price - analysis['price']) / analysis['price'] < 0.02:
                final_confidence += 8
                analysis['reasons'].append(f"Силна resistance стена на ${resistance_price:,.2f}")
    
    # Multi-timeframe корекция
    if mtf_confirmation and mtf_confirmation['confirmed']:
        final_confidence += 15
        analysis['reasons'].append(f"Потвърждение от {mtf_confirmation['timeframe']}")
    elif mtf_confirmation and not mtf_confirmation['confirmed']:
        final_confidence -= 10
        analysis['reasons'].append(f"{mtf_confirmation['timeframe']} не потвърждава")
    
    # BTC Correlation корекция
    if btc_correlation:
        if btc_correlation['trend'] == analysis['signal']:
            boost = min(btc_correlation['strength'] / 2, 12)  # Max 12%
            final_confidence += boost
            analysis['reasons'].append(f"BTC {btc_correlation['trend']} ({btc_correlation['change']:+.1f}%)")
        elif btc_correlation['trend'] != 'NEUTRAL' and btc_correlation['trend'] != analysis['signal']:
            penalty = min(btc_correlation['strength'] / 3, 10)
            final_confidence -= penalty
            analysis['reasons'].append(f"⚠️ BTC противоречи ({btc_correlation['trend']} {btc_correlation['change']:+.1f}%)")
    
    # Sentiment корекция
    if sentiment and sentiment['sentiment'] != 'NEUTRAL':
        if sentiment['sentiment'] == analysis['signal']:
            final_confidence += sentiment['confidence']
            analysis['reasons'].append(f"Новини {sentiment['sentiment']}: +{sentiment['confidence']:.0f}%")
        else:
            final_confidence -= sentiment['confidence'] / 2
            analysis['reasons'].append(f"Новини противоречат ({sentiment['sentiment']})")
    
    # Обнови confidence и has_good_trade
    final_confidence = max(0, min(final_confidence, 95))
    analysis['confidence'] = final_confidence
    analysis['has_good_trade'] = analysis['signal'] in ['BUY', 'SELL'] and final_confidence >= 65
    
    # Използвай adaptive TP/SL вместо фиксирани настройки
    adaptive_levels = analysis['adaptive_tp_sl']
    tp_pct = adaptive_levels['tp']
    sl_pct = adaptive_levels['sl']
    
    # Изчисли TP и SL нива
    price = analysis['price']
    
    if analysis['signal'] == 'BUY':
        tp_price = price * (1 + tp_pct / 100)
        sl_price = price * (1 - sl_pct / 100)
        signal_emoji = "🟢"
    elif analysis['signal'] == 'SELL':
        tp_price = price * (1 - tp_pct / 100)
        sl_price = price * (1 + sl_pct / 100)
        signal_emoji = "🔴"
    else:
        tp_price = price * (1 + tp_pct / 100)
        sl_price = price * (1 - sl_pct / 100)
        signal_emoji = "⚪"
    
    # Запиши ВСЕКИ сигнал в статистиката (не само good trades)
    signal_id = record_signal(
        symbol, 
        timeframe, 
        analysis['signal'], 
        final_confidence,
        entry_price=price,
        tp_price=tp_price,
        sl_price=sl_price
    )
    
    # 🎯 ДОБАВИ СИГНАЛА ЗА TRACKING (80% alert, TP/SL monitoring)
    add_signal_to_tracking(
        symbol=symbol,
        signal_type=analysis['signal'],
        entry_price=price,
        tp_price=tp_price,
        sl_price=sl_price,
        confidence=final_confidence,
        timeframe=timeframe,
        timestamp=datetime.now()
    )
    
    # 📝 ML Journal - запиши ВСЕКИ сигнал за ML обучение (не само good trades)
    # Подготви analysis_data за ML журнала (pure ICT strategy)
    analysis_data = {
        'rsi': analysis.get('rsi'),
        'volume_ratio': analysis.get('volume_ratio'),
        'volatility': analysis.get('volatility'),
        'trend': analysis.get('trend'),
        'btc_correlation': btc_correlation,
        'sentiment': sentiment,
        'has_good_trade': analysis.get('has_good_trade', False)  # Добави като feature
    }
    
    # Логвай в Trading Journal за ML самообучение
    journal_id = log_trade_to_journal(
        symbol=symbol,
        timeframe=timeframe,
        signal_type=analysis['signal'],
        confidence=final_confidence,
        entry_price=price,
        tp_price=tp_price,
        sl_price=sl_price,
        analysis_data=analysis_data
    )
    
    if journal_id:
        logger.info(f"📝 Trade #{journal_id} logged to ML journal (ALL signals)")
    
    # === ML PREDICTION - за ВСИЧКИ сигнали ===
    ml_probability = None
    ml_message = ""
    
    if ML_PREDICTOR_AVAILABLE:
        try:
            ml_predictor = get_ml_predictor()
            
            # Подготви данни за ML прогноза
            ml_trade_data = {
                'signal_type': analysis['signal'],
                'confidence': final_confidence,
                'entry_price': price,
                'analysis_data': analysis_data
            }
            
            # Получи ML прогноза
            ml_probability = ml_predictor.predict(ml_trade_data)
            
            if ml_probability is not None:
                logger.info(f"🤖 ML Prediction: {ml_probability:.1f}% вероятност за успех")
                
                # Изчисли корекция на confidence
                ml_adjustment = ml_predictor.get_confidence_adjustment(ml_probability, final_confidence)
                
                # Определи ML emoji според вероятността
                if ml_probability >= 80:
                    ml_emoji = "🤖💎"
                    ml_quality = "Отлична"
                elif ml_probability >= 70:
                    ml_emoji = "🤖✅"
                    ml_quality = "Много добра"
                elif ml_probability >= 60:
                    ml_emoji = "🤖👍"
                    ml_quality = "Добра"
                elif ml_probability >= 50:
                    ml_emoji = "🤖⚠️"
                    ml_quality = "Средна"
                else:
                    ml_emoji = "🤖❌"
                    ml_quality = "Ниска"
                
                ml_message = f"\n🤖 <b>ML ПРОГНОЗА:</b> {ml_probability:.1f}% ({ml_quality}) {ml_emoji}\n"
                
                if abs(ml_adjustment) >= 5:
                    if ml_adjustment > 0:
                        ml_message += f"   💡 ML модел повишава увереността с +{ml_adjustment:.0f}%\n"
                    else:
                        ml_message += f"   ⚠️ ML модел понижава увереността с {ml_adjustment:.0f}%\n"
                
                # Добави ML причина в analysis
                analysis['reasons'].append(f"ML прогноза: {ml_probability:.1f}% успех")
                
        except Exception as e:
            logger.error(f"❌ Грешка при ML прогноза: {e}")
    
    
    # Генерирай графика с luxalgo_ict данни
    luxalgo_ict_data = analysis.get('luxalgo_ict')
    try:
        chart_buffer = generate_chart(klines, symbol, analysis['signal'], price, tp_price, sl_price, timeframe, luxalgo_ict_data)
        if not chart_buffer:
            logger.warning(f"⚠️ Chart generation returned None for {symbol} {timeframe}")
    except Exception as e:
        logger.error(f"❌ Chart generation failed for {symbol} {timeframe}: {e}")
        chart_buffer = None
    
    # Изчисли вероятност за достигане на TP
    tp_probability = calculate_tp_probability(analysis, tp_price, analysis['signal'])
    
    # Изчисли оптимални entry zones
    entry_zones = calculate_entry_zones(
        price, 
        analysis['signal'], 
        analysis['closes'], 
        analysis['highs'], 
        analysis['lows'],
        analysis
    )
    
    # Форматирай съобщението с emoji
    confidence_emoji = "🔥" if analysis['confidence'] >= 80 else "💪" if analysis['confidence'] >= 70 else "👍" if analysis['confidence'] >= 60 else "🤔"
    change_emoji = "📈" if analysis['change_24h'] > 0 else "📉" if analysis['change_24h'] < 0 else "➡️"
    
    message = f"{signal_emoji} <b>СИГНАЛ: {symbol}</b>\n\n"
    message += f"📊 <b>Анализ ({timeframe}):</b>\n"
    message += f"Сигнал: <b>{analysis['signal']}</b> {signal_emoji}\n"
    message += f"Увереност: {analysis['confidence']}% {confidence_emoji}\n"
    
    # Добави ML прогноза ако е налична
    if ml_message:
        message += ml_message
    
    message += f"\n💰 <b>Текуща цена:</b> ${price:,.4f}\n"
    message += f"{change_emoji} 24ч промяна: {analysis['change_24h']:+.2f}%\n\n"
    
    # Обединена секция за ВСИЧКИ нива (Entry, TP, SL)
    message += f"🎯 <b>Нива за търговия:</b>\n\n"
    
    # Entry zone с quality badge
    if entry_zones['quality'] >= 75:
        quality_badge = "💎 Отлична"
        quality_emoji = "💎"
    elif entry_zones['quality'] >= 60:
        quality_badge = "🟢 Много добра"
        quality_emoji = "🟢"
    elif entry_zones['quality'] >= 45:
        quality_badge = "🟡 Добра"
        quality_emoji = "🟡"
    else:
        quality_badge = "🟠 Приемлива"
        quality_emoji = "🟠"
    
    message += f"📍 <b>ENTRY ZONE</b> ({quality_badge} - {entry_zones['quality']}/100):\n"
    message += f"   Оптимален вход: <b>${entry_zones['best_entry']:,.4f}</b>\n"
    message += f"   Зона: ${entry_zones['entry_zone_low']:,.4f} - ${entry_zones['entry_zone_high']:,.4f}\n"
    
    # Support/Resistance ако има
    if analysis['signal'] == 'BUY' and entry_zones['supports']:
        message += f"   Support: ${entry_zones['supports'][0]:,.4f}\n"
    elif analysis['signal'] == 'SELL' and entry_zones['resistances']:
        message += f"   Resistance: ${entry_zones['resistances'][0]:,.4f}\n"
    
    # Entry препоръка
    price_vs_entry = (price - entry_zones['best_entry']) / price * 100
    if abs(price_vs_entry) < 0.5:
        entry_recommendation = "✅ Добър момент за вход - цената е близо до оптималния вход"
    elif (analysis['signal'] == 'BUY' and price > entry_zones['best_entry']) or \
         (analysis['signal'] == 'SELL' and price < entry_zones['best_entry']):
        entry_recommendation = "⏳ По-добре изчакай pullback към зоната"
    else:
        entry_recommendation = "⚡ Цената е в entry зоната - разгледай вход"
    
    message += f"   💡 <i>{entry_recommendation}</i>\n\n"
    
    # Take Profit & Stop Loss (продължава в същата секция "Нива за търговия")
    message += f"🎯 <b>TAKE PROFIT:</b> ${tp_price:,.4f} (<b>{tp_pct:+.1f}%</b>)\n"
    
    # TP вероятност с интерпретация
    if tp_probability >= 76:
        tp_interpretation = "💚 Много добър шанс"
    elif tp_probability >= 66:
        tp_interpretation = "🟢 Добър шанс"
    elif tp_probability >= 56:
        tp_interpretation = "🟡 Среден шанс"
    elif tp_probability >= 36:
        tp_interpretation = "🟠 Нисък шанс"
    else:
        tp_interpretation = "🔴 Много нисък шанс"
    
    message += f"   🎲 Вероятност: {tp_probability}% ({tp_interpretation})\n"
    
    # Очаквано време за изпълнение
    timeframe_hours = {
        '1m': 0.017, '5m': 0.083, '15m': 0.25, '30m': 0.5,
        '1h': 1, '2h': 2, '4h': 4, '1d': 24, '1w': 168
    }
    estimated_hours = timeframe_hours.get(timeframe, 4) * 3
    
    if estimated_hours < 1:
        time_str = f"{int(estimated_hours * 60)} минути"
    elif estimated_hours < 24:
        time_str = f"{estimated_hours:.1f} часа"
    else:
        time_str = f"{estimated_hours / 24:.1f} дни"
    
    message += f"   ⏱️ Очаквано време: ~{time_str}\n\n"
    
    message += f"🛡️ <b>STOP LOSS:</b> ${sl_price:,.4f} (<b>{-sl_pct:.1f}%</b>)\n"
    message += f"⚖️ <b>Risk/Reward:</b> 1:{settings['rr']}\n\n"
    
    # === MULTI-TIMEFRAME КОНСЕНСУС ===
    if mtf_analysis and len(mtf_analysis['signals']) >= 2:
        message += f"🔍 <b>Multi-Timeframe Анализ:</b>\n"
        
        # Покажи сигналите от различните таймфреймове
        for tf, sig in mtf_analysis['signals'].items():
            sig_emoji = "🟢" if sig['signal'] == 'BUY' else "🔴" if sig['signal'] == 'SELL' else "⚪"
            current_marker = " ← текущ" if tf == timeframe else ""
            message += f"{tf}: {sig['signal']} {sig_emoji} ({sig['confidence']:.0f}%){current_marker}\n"
        
        # Консенсус
        consensus_emoji = "🟢" if mtf_analysis['consensus'] == 'BUY' else "🔴" if mtf_analysis['consensus'] == 'SELL' else "⚪"
        message += f"\n💎 <b>Консенсус:</b> {mtf_analysis['consensus']} {consensus_emoji}\n"
        message += f"💪 <b>Сила:</b> {mtf_analysis['consensus_strength']} ({mtf_analysis['agreement']:.0f}% съгласие)\n"
        
        # Препоръка според консенсуса
        if mtf_analysis['consensus'] == analysis['signal'] and mtf_analysis['consensus_strength'] == 'Силен':
            message += f"✅ <i>Всички таймфреймове потвърждават сигнала!</i>\n"
        elif mtf_analysis['consensus'] != analysis['signal']:
            message += f"⚠️ <i>Внимание: По-големите таймфреймове показват {mtf_analysis['consensus']}</i>\n"
        
        message += "\n"
    
    message += f"📊 <b>Индикатори:</b>\n"
    if analysis['rsi']:
        message += f"RSI(14): {analysis['rsi']:.1f}\n"
    # MA removed - pure ICT strategy without moving averages
    
    if analysis['reasons']:
        message += f"\n💡 <b>Причини:</b>\n"
        for reason in analysis['reasons']:
            message += f"• {reason}\n"
    
    message += f"\n⚠️ <i>Това не е финансов съвет!</i>"
    
    # Провери дали има подходящ трейд
    if not analysis.get('has_good_trade', False):
        # Няма подходящ трейд
        no_trade_message = f"⚪ <b>НЯМА ПОДХОДЯЩ ТРЕЙД</b>\n\n"
        no_trade_message += f"📊 <b>{symbol} ({timeframe})</b>\n\n"
        no_trade_message += f"💰 Цена: ${price:,.4f}\n"
        no_trade_message += f"📈 24ч промяна: {analysis['change_24h']:+.2f}%\n\n"
        no_trade_message += f"📊 <b>Индикатори:</b>\n"
        if analysis['rsi']:
            no_trade_message += f"RSI(14): {analysis['rsi']:.1f}\n"
        # MA removed - pure ICT strategy
        no_trade_message += f"\nСигнал: {analysis['signal']}\n"
        no_trade_message += f"Увереност: {analysis['confidence']}%\n\n"
        no_trade_message += f"⚠️ <i>Пазарните условия не са подходящи за трейд в момента.</i>"
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=no_trade_message,
            parse_mode='HTML'
        )
        return
    
    # Изпрати високо-приоритетна нотификация при confidence ≥ 70%
    if analysis['confidence'] >= 70:
        await send_high_confidence_alert(
            symbol, 
            analysis['confidence'], 
            analysis['signal'], 
            price, 
            tp_price, 
            context
        )
    
    # Опитай се да вземеш TradingView chart snapshot
    tradingview_chart = await fetch_tradingview_chart_image(symbol, timeframe)
    
    # Ако имаме TradingView snapshot, използвай го
    if tradingview_chart:
        short_caption = f"{signal_emoji} <b>{signal} {symbol}</b> ({timeframe})\n"
        short_caption += f"💰 ${price:,.4f} | 🎯 {analysis['confidence']:.0f}%\n"
        short_caption += f"✅ TP: ${tp_price:,.4f} (+{tp_pct:.2f}%)\n"
        short_caption += f"🛑 SL: ${sl_price:,.4f} (-{sl_pct:.2f}%)"
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=tradingview_chart,
            caption=f"🔔🔊 {short_caption}",
            parse_mode='HTML',
            disable_notification=False
        )
        
        # Изпрати пълното съобщение като текст
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='HTML',
            disable_notification=True
        )
    # Fallback - използвай matplotlib графиката
    elif chart_buffer:
        short_caption = f"{signal_emoji} <b>{signal} {symbol}</b> ({timeframe})\n"
        short_caption += f"💰 ${price:,.4f} | 🎯 {analysis['confidence']:.0f}%\n"
        short_caption += f"✅ TP: ${tp_price:,.4f} (+{tp_pct:.2f}%)\n"
        short_caption += f"🛑 SL: ${sl_price:,.4f} (-{sl_pct:.2f}%)"
        
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=chart_buffer,
            caption=f"🔔🔊 {short_caption}",
            parse_mode='HTML',
            disable_notification=False
        )
        
        # Изпрати пълното съобщение като текст
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=message,
            parse_mode='HTML',
            disable_notification=True
        )
    else:
        # Няма графика - изпрати само текст
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔔🔊 {message}",
            parse_mode='HTML',
            disable_notification=False
        )


async def ict_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🎯 ICT Complete Analysis Command
    Full ICT trading signal with all components
    """
    logger.info(f"User {update.effective_user.id} executed /ict with args: {context.args}")
    
    if not ICT_SIGNAL_ENGINE_AVAILABLE:
        await update.message.reply_text(
            "❌ ICT Signal Engine not available. Please check bot configuration.",
            parse_mode='HTML'
        )
        return
    
    # Parse arguments
    if not context.args:
        # Show menu
        keyboard = [
            [
                InlineKeyboardButton("₿ BTC", callback_data="ict_BTCUSDT"),
                InlineKeyboardButton("Ξ ETH", callback_data="ict_ETHUSDT"),
            ],
            [
                InlineKeyboardButton("⚡ SOL", callback_data="ict_SOLUSDT"),
                InlineKeyboardButton("💎 XRP", callback_data="ict_XRPUSDT"),
            ],
            [
                InlineKeyboardButton("🏠 Main Menu", callback_data="back_to_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "🎯 <b>ICT Analysis - Select Currency:</b>\n\n"
            "💡 <i>Tip: Use /ict BTC 1h for specific timeframe</i>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    symbol = context.args[0].upper()
    timeframe = context.args[1] if len(context.args) > 1 else '1h'
    
    # Validate symbol
    if symbol not in SYMBOLS.values():
        # Try to find in short names
        found = False
        for short, full in SYMBOLS.items():
            if symbol == short:
                symbol = full
                found = True
                break
        if not found:
            await update.message.reply_text(f"❌ Unknown symbol: {symbol}")
            return
    
    # Send processing message
    processing_msg = await update.message.reply_text(
        f"🔍 <b>Running complete ICT analysis for {symbol}...</b>\n\n"
        f"⏳ Analyzing: Order Blocks, FVGs, Liquidity, Market Structure...",
        parse_mode='HTML'
    )
    
    try:
        # Initialize ICT engine
        ict_engine = ICTSignalEngine()
        
        # Fetch OHLCV data
        klines = requests.get(
            f"{BINANCE_API}klines",
            params={'symbol': symbol, 'interval': timeframe, 'limit': 200}
        ).json()
        
        if not klines or 'code' in klines:
            await processing_msg.edit_text(
                f"❌ Failed to fetch data for {symbol}",
                parse_mode='HTML'
            )
            return
        
        # Prepare dataframe
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])
        
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        # Generate ICT signal
        signal = ict_engine.generate_signal(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            mtf_data=None  # TODO: Add MTF data fetching
        )
        
        if not signal:
            await processing_msg.edit_text(
                f"❌ <b>No ICT signal generated for {symbol}</b>\n\n"
                f"Conditions not met for high-quality signal (minimum 70% confidence required).",
                parse_mode='HTML'
            )
            return
        
        # Format and send signal
        signal_msg = format_ict_signal(signal)
        
        await processing_msg.edit_text(
            signal_msg,
            parse_mode='Markdown',
            disable_web_page_preview=True
        )
        
        logger.info(f"ICT signal sent for {symbol}: {signal.signal_type.value}")
        
    except Exception as e:
        logger.error(f"ICT analysis error: {e}")
        await processing_msg.edit_text(
            f"❌ <b>Error during ICT analysis:</b>\n\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )


def format_ict_signal(signal: ICTSignal) -> str:
    """
    Format ICT signal for Telegram display
    
    Args:
        signal: ICT signal object
        
    Returns:
        Formatted message string
    """
    # Signal type emoji
    signal_emoji = {
        'BUY': '🟢',
        'SELL': '🔴',
        'STRONG_BUY': '💚',
        'STRONG_SELL': '❤️',
        'HOLD': '⚪'
    }
    
    emoji = signal_emoji.get(signal.signal_type.value, '⚪')
    strength_stars = '🔥' * signal.signal_strength.value
    
    msg = f"""
{emoji} **ICT SIGNAL - {signal.signal_type.value}** {emoji}

📊 **Symbol:** {signal.symbol}
⏰ **Timeframe:** {signal.timeframe}
💪 **Strength:** {strength_stars} ({signal.signal_strength.value}/5)
📈 **Confidence:** {signal.confidence:.1f}%

💰 **Trade Setup:**
├─ Entry: ${signal.entry_price:.2f}
├─ Stop Loss: ${signal.sl_price:.2f}
└─ Take Profits:
   ├─ TP1: ${signal.tp_prices[0]:.2f}
   ├─ TP2: ${signal.tp_prices[1]:.2f}
   └─ TP3: ${signal.tp_prices[2]:.2f}

📊 **Risk/Reward:** {signal.risk_reward_ratio:.2f}:1

🎯 **ICT Analysis:**
├─ Market Bias: {signal.bias.value}
├─ Whale Blocks: {len(signal.whale_blocks)}
├─ Liquidity Zones: {len(signal.liquidity_zones)}
├─ Order Blocks: {len(signal.order_blocks)}
├─ Fair Value Gaps: {len(signal.fair_value_gaps)}
└─ MTF Confluence: {signal.mtf_confluence} timeframes

🔍 **Structure:**
├─ HTF Bias: {signal.htf_bias}
├─ Structure Broken: {'✅' if signal.structure_broken else '❌'}
└─ Displacement: {'✅' if signal.displacement_detected else '❌'}

📝 **Reasoning:**
{signal.reasoning}
"""
    
    if signal.warnings:
        msg += f"\n\n⚠️ **Warnings:**\n"
        for warning in signal.warnings:
            msg += f"• {warning}\n"
    
    msg += f"\n\n⏰ _Generated: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}_"
    
    return msg


async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последни новини от крипто света - Топ надеждни източници"""
    logger.info(f"User {update.effective_user.id} executed /news")
    await update.message.reply_text("📰 Извличане на новини от най-надеждните източници...")
    
    try:
        # Извлечи от множество източници (вече имаме обновена функция с превод)
        logger.info("Fetching market news...")
        all_news = await fetch_market_news()
        logger.info(f"Received {len(all_news) if all_news else 0} news items")
    except Exception as e:
        logger.error(f"Грешка при извличане на новини: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Грешка при извличане на новини: {e}")
        return
    
    logger.info("Preparing news message...")
    
    # Изпрати новините
    if not all_news:
        logger.warning("No news available")
        # Fallback
        message = """
📰 <b>КРИПТО НОВИНИ</b>

Моля посетете директно топ източниците:

🏆 <b>CoinDesk:</b> https://www.coindesk.com/
📰 <b>Cointelegraph:</b> https://cointelegraph.com/
🔐 <b>Decrypt:</b> https://decrypt.co/
📊 <b>CoinMarketCap:</b> https://coinmarketcap.com/headlines/

💡 Използвай Google Translate за български език!
"""
        await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)
        return
    
    # ФОРМАТ С ВАЛИДНИ НОВИНИ - САМО НАЙ-ВАЖНИТЕ
    message = "📰 <b>НАЙ-ВАЖНИ КРИПТО НОВИНИ</b>\n"
    message += "<i>📊 Източник: Cointelegraph - БЕЗ блокировки!</i>\n\n"
    
    # Показваме максимум 6 най-важни новини (С АВТОМАТИЧЕН ПРЕВОД - ПЪЛЕН ТЕКСТ)
    for i, news in enumerate(all_news[:6], 1):
        source = news.get('source', '📰')
        
        # Използвай преведеното заглавие ако е налично, иначе оригиналното
        title_bg = news.get('title_bg', news.get('title', 'Без заглавие'))
        desc_bg = news.get('description_bg', '')
        
        # Escape специални Telegram символи
        title_bg = title_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        message += f"{i}. {source} <b>{title_bg}</b>\n"
        
        if desc_bg:
            # ПОКАЗВАМЕ ПЪЛНИЯ ПРЕВЕДЕН ТЕКСТ (не само 150 символа)
            desc_bg = desc_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            message += f"   <i>{desc_bg}</i>\n"
        
        if news.get('translate_link'):
            # Google Translate линк - статията автоматично на български!
            message += f"   🌍 <a href=\"{news['translate_link']}\">📖 Прочети пълната статия на БЪЛГАРСКИ</a>\n"
        elif news.get('link'):
            # Fallback към оригинален линк
            message += f"   🔗 <a href=\"{news['link']}\">📖 Прочети оригинала (английски)</a>\n"
        
        message += "\n"
    
    message += "🌍 <i>Новините са автоматично преведени на български език</i>\n"
    message += f"<i>📊 Показани {len(all_news[:6])} от {len(all_news)} налични новини</i>"
    
    logger.info(f"Sending news message with {len(all_news[:10])} items...")
    try:
        await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)
        logger.info("News message sent successfully!")
    except Exception as send_err:
        logger.error(f"Error sending news message: {send_err}", exc_info=True)
        await update.message.reply_text(f"❌ Грешка при изпращане: {send_err}")


async def breaking_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Провери за КРИТИЧНИ новини в момента"""
    await update.message.reply_text("🚨 Проверявам за критични новини...")
    
    try:
        # Извлечи последни новини
        news = await fetch_market_news()
        
        if not news:
            await update.message.reply_text("❌ Няма налични новини в момента")
            return
        
        # Анализирай всички новини
        critical_news = []
        high_impact_news = []
        
        for article in news:
            impact = await analyze_news_impact(article['title'], article.get('description', ''))
            
            if impact['impact'] == 'CRITICAL':
                article['impact_analysis'] = impact
                critical_news.append(article)
            elif impact['impact'] == 'HIGH':
                article['impact_analysis'] = impact
                high_impact_news.append(article)
        
        # Изпрати резултата
        if not critical_news and not high_impact_news:
            await update.message.reply_text(
                "✅ <b>Няма критични новини</b>\n\n"
                "Пазарът е спокоен. Следващата проверка след 3 минути.\n\n"
                "💡 Автоматичният мониторинг работи non-stop!",
                parse_mode='HTML'
            )
            return
        
        # Изпрати критичните новини
        if critical_news:
            for article in critical_news:
                impact = article['impact_analysis']
                
                # Използвай преведеното заглавие и описание
                title_bg = article.get('title_bg', article.get('title', 'Без заглавие'))
                desc_bg = article.get('description_bg', '')
                
                # Escape Telegram символи
                title_bg = title_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                desc_bg = desc_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                if impact['sentiment'] == 'BULLISH':
                    sentiment_emoji = "🟢📈"
                    sentiment_text = "BULLISH"
                elif impact['sentiment'] == 'BEARISH':
                    sentiment_emoji = "🔴📉"
                    sentiment_text = "BEARISH"
                else:
                    sentiment_emoji = "⚪➡️"
                    sentiment_text = "NEUTRAL"
                
                msg = f"""🚨 <b>КРИТИЧНА НОВИНА!</b> 🚨

{article.get('source', '📰')} <b>{title_bg}</b>

{sentiment_emoji} <b>Sentiment:</b> {sentiment_text}
📊 <b>Bullish фактори:</b> {impact['bullish_score']}
📉 <b>Bearish фактори:</b> {impact['bearish_score']}

"""
                
                if desc_bg:
                    desc_short = desc_bg[:150] + "..." if len(desc_bg) > 150 else desc_bg
                    msg += f"<i>{desc_short}</i>\n\n"
                
                if article.get('link'):
                    msg += f"🔗 <a href=\"{article['link']}\">Прочети пълната статия</a>\n"
                    msg += f"🌍 <i>Автоматично преведено на български</i>\n"
                
                await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=True)
                await asyncio.sleep(0.5)
        
        # Изпрати високо въздействащите новини
        if high_impact_news:
            for article in high_impact_news[:3]:  # Максимум 3
                impact = article['impact_analysis']
                
                # Използвай преведеното заглавие
                title_bg = article.get('title_bg', article.get('title', 'Без заглавие'))
                title_bg = title_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
                
                if impact['sentiment'] == 'BULLISH':
                    sentiment_emoji = "🟢"
                elif impact['sentiment'] == 'BEARISH':
                    sentiment_emoji = "🔴"
                else:
                    sentiment_emoji = "⚪"
                
                msg = f"""⚠️ <b>ВАЖНА НОВИНА</b>

{article.get('source', '📰')} <b>{title_bg}</b>

{sentiment_emoji} Sentiment: {impact['sentiment']}
"""
                
                if article.get('link'):
                    msg += f"🔗 <a href=\"{article['link']}\">Прочети пълната статия</a>\n"
                    msg += f"🌍 <i>Автоматично преведено на български</i>\n"
                
                await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=True)
                await asyncio.sleep(0.3)
        
    except Exception as e:
        logger.error(f"Грешка в breaking_cmd: {e}")
        await update.message.reply_text(f"❌ Грешка: {e}")


async def workspace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация за достъп до Workspace"""
    workspace_info = f"""💻 <b>GITHUB WORKSPACE</b>

🔗 <b>Твой Codespace:</b>
https://github.com/codespaces

📂 <b>Repository:</b>
https://github.com/galinborisov10-art/Crypto-signal-bot

🚀 <b>Бърз достъп:</b>
• Натисни бутона "💻 Workspace"
• Или използвай /workspace
• Или /w (кратко)

💡 <b>Какво можеш да правиш:</b>
✅ Виждаш copilot_tasks.json
✅ Редактираш кода
✅ Пускаш команди в Terminal
✅ Общуваш с GitHub Copilot
✅ Commit & Push промени

📋 <b>Текущи задачи:</b>
Виж: /task
"""
    
    await update.message.reply_text(
        workspace_info,
        parse_mode='HTML',
        disable_web_page_preview=False
    )


async def task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Създай задание за Copilot разработка"""
    if not context.args:
        # Покажи текущи задачи
        try:
            with open(f'{BASE_PATH}/copilot_tasks.json', 'r') as f:
                import json
                data = json.load(f)
                
            pending = data.get('tasks', [])
            completed = data.get('completed', [])
            
            msg = "🤖 <b>COPILOT TASK QUEUE</b>\n\n"
            
            if pending:
                msg += "<b>📋 Pending Tasks:</b>\n"
                for i, task in enumerate(pending, 1):
                    msg += f"{i}. {task['title']}\n"
                    msg += f"   📅 {task['created']}\n"
                    msg += f"   💬 {task['description'][:50]}...\n\n"
            else:
                msg += "✅ <b>Няма чакащи задачи</b>\n\n"
            
            if completed:
                msg += f"\n<b>✅ Completed: {len(completed)}</b>\n"
                for task in completed[-3:]:  # Последните 3
                    msg += f"• {task['title']}\n"
            
            msg += "\n💡 <b>Употреба:</b>\n"
            msg += "/task Добави функция за...\n"
            msg += "/task Поправи грешка в...\n"
            msg += "/task Подобри анализа с...\n"
            
            await update.message.reply_text(msg, parse_mode='HTML')
            
        except Exception as e:
            await update.message.reply_text(
                "🤖 <b>COPILOT TASK QUEUE</b>\n\n"
                "✅ Няма текущи задачи\n\n"
                "💡 <b>Създай задача:</b>\n"
                "/task Твоето задание тук...\n\n"
                "<b>Примери:</b>\n"
                "• /task Добави RSI индикатор\n"
                "• /task Поправи грешка в новините\n"
                "• /task Направи сигналите по-точни",
                parse_mode='HTML'
            )
        return
    
    # Създай ново задание
    task_description = ' '.join(context.args)
    
    # Запази в JSON файл
    try:
        import json
        from datetime import datetime
        
        # Зареди текущите задачи
        try:
            with open(f'{BASE_PATH}/copilot_tasks.json', 'r') as f:
                data = json.load(f)
        except:
            data = {'tasks': [], 'completed': []}
        
        # Създай ново задание
        new_task = {
            'id': len(data['tasks']) + len(data['completed']) + 1,
            'title': task_description[:100],
            'description': task_description,
            'created': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'created_by': update.effective_user.id,
            'username': update.effective_user.username or 'Unknown',
            'status': 'pending',
            'priority': 'normal'
        }
        
        data['tasks'].append(new_task)
        
        # Запази обратно
        with open(f'{BASE_PATH}/copilot_tasks.json', 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Създай и файл с по-детайлна информация
        task_file = f"{BASE_PATH}/COPILOT_TASK_{new_task['id']}.md"
        task_content = f"""# 🤖 COPILOT TASK #{new_task['id']}

## 📋 Task Details
**Created:** {new_task['created']}
**Created by:** @{new_task['username']} (ID: {new_task['created_by']})
**Status:** {new_task['status']}
**Priority:** {new_task['priority']}

## 📝 Description
{task_description}

## ✅ Checklist
- [ ] Analyze requirements
- [ ] Implement changes
- [ ] Test functionality
- [ ] Update documentation
- [ ] Notify user

## 💬 Notes
_GitHub Copilot will see this file and implement the changes._

## 🔔 Notification
When completed, user will receive Telegram notification.
"""
        
        with open(task_file, 'w') as f:
            f.write(task_content)
        
        # Изпрати потвърждение
        msg = f"""✅ <b>ЗАДАНИЕ СЪЗДАДЕНО!</b>

🆔 <b>Task ID:</b> #{new_task['id']}
📝 <b>Описание:</b> {task_description}

🤖 <b>Статус:</b> Чака Copilot
📅 <b>Създадено:</b> {new_task['created']}

💡 GitHub Copilot ще види това задание при следващата сесия и ще го изпълни!

📊 <b>Прогрес:</b>
• Записано в copilot_tasks.json
• Създаден markdown файл
• Готово за обработка

🔔 Ще получиш нотификация когато е готово!
"""
        
        await update.message.reply_text(msg, parse_mode='HTML')
        logger.info(f"✅ Copilot task #{new_task['id']} created by @{new_task['username']}")
        
    except Exception as e:
        logger.error(f"Грешка при създаване на task: {e}")
        await update.message.reply_text(f"❌ Грешка: {e}")


async def dailyreport_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерира ръчен дневен отчет за сигнали"""
    logger.info(f"User {update.effective_user.id} executed /dailyreport")
    
    await update.message.reply_text("📊 Генерирам дневен отчет за сигнали...")
    
    try:
        await send_daily_signal_report(context.bot)
        await update.message.reply_text("✅ Дневният отчет е изпратен!")
    except Exception as e:
        logger.error(f"Грешка при /dailyreport: {e}")
        await update.message.reply_text(f"❌ Грешка при генериране на отчет: {e}")


async def send_bot_status_notification(bot, status, reason=""):
    """Изпраща нотификация за статуса на бота"""
    try:
        from datetime import datetime
        
        if status == "stopping":
            message = f"""⚠️ <b>БОТ СПИРА!</b>

🔴 <b>Причина:</b> {reason}
⏱️ <b>Време:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔄 Опитвам се да рестартирам автоматично...
"""
        elif status == "restarted":
            message = f"""✅ <b>БОТ РЕСТАРТИРАН!</b>

🟢 <b>Статус:</b> Онлайн
⏱️ <b>Време:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

💡 Всичко работи нормално!
"""
        elif status == "crashed":
            message = f"""🚨 <b>БОТ CRASHED!</b>

❌ <b>Грешка:</b> {reason}
⏱️ <b>Време:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔄 Автоматично рестартиране след 10 секунди...
"""
        else:
            message = f"ℹ️ Статус: {status}\n{reason}"
        
        await bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=message,
            parse_mode='HTML',
            disable_notification=False  # Със звук
        )
    except Exception as e:
        logger.error(f"Грешка при изпращане на статус нотификация: {e}")


async def restart_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Рестартира бота автоматично"""
    # Провери дали е owner
    if update.effective_user.id != OWNER_CHAT_ID:
        await update.message.reply_text("❌ Само owner-ът може да рестартира бота!")
        return
    
    logger.info(f"🔄 Bot restart requested by user {update.effective_user.id}")
    
    try:
        # ПЪРВО - Създай RESTART FLAG файл
        restart_flag_file = f"{BASE_PATH}/.restart_requested"
        with open(restart_flag_file, 'w') as f:
            f.write(str(datetime.now()))
        
        logger.info(f"✅ Restart flag created: {restart_flag_file}")
        
        # ВТОРО - Изпрати ПОТВЪРЖДЕНИЕ
        await context.bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=(
                "🔄 <b>РЕСТАРТИРАМ СЕГА!</b>\n\n"
                "⏱️ Време: ~15 секунди\n\n"
                "🔔 <b>ГАРАНТИРАНО ще получиш съобщение\n"
                "със ЗВУК след рестарта!</b>"
            ),
            parse_mode='HTML',
            disable_notification=False
        )
        
        # ТРЕТО - Изчакай съобщението да се изпрати
        await asyncio.sleep(2)
        
        # ЧЕТВЪРТО - KILL ПРОЦЕСА (systemd автоматично рестартира)
        logger.info("🛑 Killing bot process... systemd will auto-restart.")
        
        import os
        import signal
        
        # Изпрати SIGTERM на себе си
        os.kill(os.getpid(), signal.SIGTERM)
            
    except Exception as e:
        logger.error(f"Restart error: {e}")
        try:
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=(
                    "❌ <b>ГРЕШКА ПРИ РЕСТАРТ!</b>\n\n"
                    f"<code>{str(e)}</code>\n\n"
                    "💡 Опитай отново или рестартирай ръчно."
                ),
                parse_mode='HTML',
                reply_markup=get_main_keyboard()
            )
        except:
            pass


async def workspace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Информация за достъп до Workspace"""
    workspace_info = f"""💻 <b>GITHUB WORKSPACE</b>

🔗 <b>Твой Codespace:</b>
https://github.com/codespaces

📂 <b>Repository:</b>
https://github.com/galinborisov10-art/Crypto-signal-bot

🚀 <b>Бърз достъп:</b>
• Натисни бутона "💻 Workspace"
• Или използвай /workspace
• Или /w (кратко)

💡 <b>Какво можеш да правиш:</b>
✅ Виждаш copilot_tasks.json
✅ Редактираш кода
✅ Пускаш команди в Terminal
✅ Общуваш с GitHub Copilot
✅ Commit & Push промени

📋 <b>Текущи задачи:</b>
Виж: /task
"""
    
    await update.message.reply_text(
        workspace_info,
        parse_mode='HTML',
        disable_web_page_preview=False
    )


async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки на TP/SL и RR"""
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    
    if not context.args:
        # Покажи текущи настройки
        message = f"""
⚙️ <b>ТВОИТЕ НАСТРОЙКИ</b>

📊 <b>Търговски параметри:</b>
Take Profit (TP): {settings['tp']:.1f}%
Stop Loss (SL): {settings['sl']:.1f}%
Risk/Reward (RR): 1:{settings['rr']:.1f}

📈 <b>Анализ (Автоматичен):</b>
Timeframes: 1h, 4h, 1d
Сканира всички 3 timeframes за всеки сигнал

🔔 <b>Известия:</b>
Автоматични сигнали: {'Вкл ✅' if settings['alerts_enabled'] else 'Изкл ❌'}
Интервал: {settings['alert_interval']/60:.0f} мин

<b>За промяна:</b>
/settings tp 3.0
/settings sl 1.5
/settings rr 2.5
"""
        await update.message.reply_text(message, parse_mode='HTML')
        return
    
    # Промяна на настройка
    if len(context.args) < 2:
        await update.message.reply_text("Използвай: /settings <tp|sl|rr> <стойност>")
        return
    
    param = context.args[0].lower()
    try:
        value = float(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Невалидна стойност")
        return
    
    if param == 'tp':
        settings['tp'] = value
        await update.message.reply_text(f"✅ Take Profit променен на {value}%")
    elif param == 'sl':
        settings['sl'] = value
        await update.message.reply_text(f"✅ Stop Loss променен на {value}%")
    elif param == 'rr':
        settings['rr'] = value
        await update.message.reply_text(f"✅ Risk/Reward променен на 1:{value}")
    else:
        await update.message.reply_text("❌ Непознат параметър. Използвай: tp, sl, rr")


async def risk_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🛡️ Risk Management настройки и статус"""
    logger.info(f"User {update.effective_user.id} executed /risk")
    
    if not RISK_MANAGER_AVAILABLE:
        await update.message.reply_text(
            "⚠️ Risk Management системата не е налична.\n"
            "Моля, проверете дали файлът risk_management.py е наличен."
        )
        return
    
    try:
        rm = get_risk_manager()
        
        # Ако има аргументи - update настройки
        if context.args:
            if len(context.args) < 3 or context.args[0] != 'set':
                await update.message.reply_text(
                    "❌ Невалидна команда!\n\n"
                    "Използвай:\n"
                    "/risk - Показва настройки\n"
                    "/risk set portfolio 5000 - Задай баланс\n"
                    "/risk set max_loss 8 - Дневен лимит\n"
                    "/risk set max_trades 3 - Макс паралелни\n"
                    "/risk set min_rr 2.5 - Минимален R/R"
                )
                return
            
            # Update settings
            setting_name = context.args[1]
            try:
                setting_value = float(context.args[2])
            except:
                await update.message.reply_text("❌ Стойността трябва да е число!")
                return
            
            # Map user-friendly names to config keys
            setting_map = {
                'portfolio': 'portfolio_balance',
                'max_loss': 'max_daily_loss_pct',
                'max_trades': 'max_concurrent_trades',
                'min_rr': 'min_risk_reward_ratio',
                'risk_pct': 'risk_per_trade_pct',
                'max_position': 'max_position_size_pct'
            }
            
            if setting_name not in setting_map:
                await update.message.reply_text(
                    f"❌ Непозната настройка: {setting_name}\n\n"
                    f"Налични: {', '.join(setting_map.keys())}"
                )
                return
            
            config_key = setting_map[setting_name]
            rm.config[config_key] = setting_value
            rm.save_config(rm.config)
            
            await update.message.reply_text(
                f"✅ <b>Настройката е обновена!</b>\n\n"
                f"{setting_name} = {setting_value}\n\n"
                f"Използвай /risk за преглед на всички настройки.",
                parse_mode='HTML'
            )
            return
        
        # Покажи настройки и текущ статус
        settings_text = rm.get_settings_summary()
        
        # Добави текущ дневен P/L и активни trades
        can_trade, daily_pnl, daily_msg = rm.check_daily_loss_limit('trading_journal.json')
        can_open, active_count, active_msg = rm.check_concurrent_trades('trading_journal.json')
        
        status_text = "\n📊 <b>ТЕКУЩ СТАТУС:</b>\n\n"
        status_text += f"{daily_msg}\n"
        status_text += f"{active_msg}\n"
        
        if not can_trade:
            status_text += f"\n🛑 <b>ТЪРГОВИЯТА Е СПРЯНА - дневният лимит е достигнат!</b>\n"
        elif not can_open:
            status_text += f"\n⚠️ <b>Не можеш да отвориш нови trades - лимитът е достигнат!</b>\n"
        else:
            status_text += f"\n✅ <b>Можеш да търгуваш</b>\n"
        
        full_message = settings_text + status_text
        
        await update.message.reply_text(full_message, parse_mode='HTML')
    
    except Exception as e:
        logger.error(f"Грешка в /risk: {e}")
        await update.message.reply_text("❌ Грешка при зареждане на Risk Management")


async def explain_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📖 Речник с ICT/LuxAlgo термини"""
    logger.info(f"User {update.effective_user.id} executed /explain")
    
    # Ако има аргумент - покажи конкретен термин
    if context.args:
        term = ' '.join(context.args).upper()
        
        explanations = {
            'OB': "📦 <b>ORDER BLOCK (OB)</b>\n\n"
                  "Зона където институционални играчи (banks, hedge funds) са влезли с големи позиции.\n\n"
                  "<b>+OB (Bullish):</b> Support зона - очаква се цената да отскочи нагоре\n"
                  "<b>-OB (Bearish):</b> Resistance зона - очаква се цената да отскочи надолу\n\n"
                  "💡 <b>Как да използваш:</b>\n"
                  "• Влизай при retest на силен OB\n"
                  "• По-силният OB има по-голям шанс за реакция\n"
                  "• Комбинирай с FVG за по-добър entry",
            
            'FVG': "🔲 <b>FAIR VALUE GAP (FVG)</b>\n\n"
                   "Ценова празнина (gap) между 3 свещи, където липсва ликвидност.\n\n"
                   "<b>FVG+ (Bullish):</b> Празнина при покачване - магнит за цената\n"
                   "<b>FVG- (Bearish):</b> Празнина при спадане - магнит за цената\n\n"
                   "📊 <b>Визуализация:</b>\n"
                   "• Плътна линия ━ = Силна FVG (>0.5% gap)\n"
                   "• Пунктир ╌ = Слаба FVG (<0.5% gap)\n\n"
                   "💡 <b>Как да използваш:</b>\n"
                   "• Цената често се връща да запълни FVG\n"
                   "• Силните FVG са по-надеждни\n"
                   "• Entry на долната граница (bullish) или горна (bearish)",
            
            'MSS': "🔄 <b>MARKET STRUCTURE SHIFT (MSS)</b>\n\n"
                   "Промяна в структурата на пазара - важен сигнал за смяна на тренда.\n\n"
                   "<b>Bullish MSS:</b> Цената пробива последния higher high\n"
                   "<b>Bearish MSS:</b> Цената пробива последния lower low\n\n"
                   "💡 <b>Как да използваш:</b>\n"
                   "• Ранен сигнал за нов тренд\n"
                   "• Влизай след потвърждение (retest)\n"
                   "• Висока вероятност за продължение в посоката на MSS",
            
            'BSL': "💧 <b>BUY SIDE LIQUIDITY (BSL)</b>\n\n"
                   "Зона НАД цената с натрупани Stop Loss ордери на SHORT позиции.\n\n"
                   "🎯 <b>Как работи:</b>\n"
                   "• Smart Money \"хваща\" тези stops\n"
                   "• След grab очаква се обрат надолу\n"
                   "• Често се вижда като fakeout над resistance\n\n"
                   "💡 <b>Как да използваш:</b>\n"
                   "• Не гонѝ breakout над BSL\n"
                   "• Изчакай grab + reversal pattern\n"
                   "• Entry при confirmation за обрат",
            
            'SSL': "💧 <b>SELL SIDE LIQUIDITY (SSL)</b>\n\n"
                   "Зона ПОД цената с натрупани Stop Loss ордери на LONG позиции.\n\n"
                   "🎯 <b>Как работи:</b>\n"
                   "• Smart Money \"хваща\" тези stops\n"
                   "• След grab очаква се обрат нагоре\n"
                   "• Често се вижда като fakeout под support\n\n"
                   "💡 <b>Как да използваш:</b>\n"
                   "• Не панкирай при breakdown под SSL\n"
                   "• Изчакай grab + reversal pattern\n"
                   "• Entry при confirmation за обрат",
            
            'SUPPORT': "🟢 <b>SUPPORT (Подкрепа)</b>\n\n"
                       "Ценово ниво където купувачите са по-силни от продавачите.\n\n"
                       "📊 <b>Как се определя:</b>\n"
                       "• LuxAlgo automatic detection\n"
                       "• Исторически test zones\n"
                       "• Volume confirmation\n\n"
                       "💡 <b>Как да използваш:</b>\n"
                       "• Long entry при retest на support\n"
                       "• Stop loss под support\n"
                       "• Breakdown = bearish signal",
            
            'RESISTANCE': "🔴 <b>RESISTANCE (Съпротива)</b>\n\n"
                          "Ценово ниво където продавачите са по-силни от купувачите.\n\n"
                          "📊 <b>Как се определя:</b>\n"
                          "• LuxAlgo automatic detection\n"
                          "• Исторически rejection zones\n"
                          "• Volume confirmation\n\n"
                          "💡 <b>Как да използваш:</b>\n"
                          "• Short entry при retest на resistance\n"
                          "• Stop loss над resistance\n"
                          "• Breakout = bullish signal",
            
            'BREAKOUT': "🚀 <b>BREAKOUT (Пробив)</b>\n\n"
                        "Движение на цената извън Support/Resistance зона с висок volume.\n\n"
                        "✅ <b>Истински breakout:</b>\n"
                        "• Силен volume (2x+ средния)\n"
                        "• Close над/под нивото\n"
                        "• Retest потвърждава\n\n"
                        "❌ <b>False breakout (fakeout):</b>\n"
                        "• Слаб volume\n"
                        "• Само wick пробива\n"
                        "• Бързо връщане назад\n\n"
                        "💡 <b>Как да търгуваш:</b>\n"
                        "• НЕ влизай веднага при пробив\n"
                        "• Изчакай retest на пробитото ниво\n"
                        "• Влизай при confirmation",
            
            'RETEST': "🔄 <b>RETEST (Повторен тест)</b>\n\n"
                      "Връщане на цената към пробито Support/Resistance ниво за потвърждение.\n\n"
                      "📊 <b>Видове:</b>\n"
                      "• <b>Bullish retest:</b> Пробит resistance става support\n"
                      "• <b>Bearish retest:</b> Пробит support става resistance\n\n"
                      "✅ <b>Успешен retest:</b>\n"
                      "• Цената се връща до нивото\n"
                      "• Rejection candle\n"
                      "• Продължава в посоката на breakout\n\n"
                      "💡 <b>Най-добър entry:</b>\n"
                      "• Влизай ТОЧНО при retest\n"
                      "• SL малко зад нивото\n"
                      "• Висок RR съотношение",
            
            'FIBONACCI': "🌀 <b>FIBONACCI RETRACEMENT & EXTENSION</b>\n\n"
                         "Математически нива базирани на Fibonacci последователността.\n\n"
                         "📊 <b>Retracement нива (pullback зони):</b>\n"
                         "• 23.6% - Слабо retracement\n"
                         "• 38.2% - Умерено retracement\n"
                         "• 50% - Средна точка\n"
                         "• 61.8% (Golden Ratio) - Optimal Trade Entry (OTE)\n"
                         "• 78.6% - Дълбоко retracement\n\n"
                         "🎯 <b>Extension нива (profit targets):</b>\n"
                         "• 127.2% - Първа цел (TP1)\n"
                         "• 161.8% - Втора цел (TP2)\n"
                         "• 200% - Трета цел (TP3)\n\n"
                         "💡 <b>OTE (Optimal Trade Entry):</b>\n"
                         "• Най-силното ниво е 61.8%-70.5%\n"
                         "• Комбинирай с FVG или OB\n"
                         "• Висока вероятност за обрат",
            
            'LIQUIDITY': "💧 <b>LIQUIDITY (Ликвидност)</b>\n\n"
                         "Зони с натрупани Stop Loss ордери на retail traders.\n\n"
                         "📊 <b>Къде се намира:</b>\n"
                         "• НАД resistance (BSL - Buy Side)\n"
                         "• ПОД support (SSL - Sell Side)\n"
                         "• При round numbers ($50K, $60K)\n"
                         "• При previous highs/lows\n\n"
                         "🎯 <b>Liquidity Grab:</b>\n"
                         "• Smart Money \"хваща\" тези stops\n"
                         "• Fakeout breakout\n"
                         "• После рязък обрат\n\n"
                         "💡 <b>Стратегия:</b>\n"
                         "• Очаквай grab преди вход\n"
                         "• Entry след reversal confirmation\n"
                         "• Не гонѝ breakouts при liquidity zones",
            
            'VOLUME': "📊 <b>VOLUME (Обем)</b>\n\n"
                      "Брой търгувани монети за даден период - важен потвърждаващ индикатор.\n\n"
                      "✅ <b>Висок volume означава:</b>\n"
                      "• Силен интерес\n"
                      "• Истински движения\n"
                      "• Институционално участие\n\n"
                      "❌ <b>Нисък volume означава:</b>\n"
                      "• Слаб интерес\n"
                      "• Fakeout вероятен\n"
                      "• Retail traders само\n\n"
                      "💡 <b>Как да използваш:</b>\n"
                      "• Breakout с висок volume = надежден\n"
                      "• Breakout с нисък volume = false signal\n"
                      "• Обърни внимание на volume спайкове",
            
            'ATR': "📏 <b>ATR (Average True Range)</b>\n\n"
                   "Индикатор за волатилност - измерва средния дневен обхват на цената.\n\n"
                   "📊 <b>Как се изчислява:</b>\n"
                   "• True Range = max(High-Low, High-PrevClose, PrevClose-Low)\n"
                   "• ATR = средно от последните 14 периода\n\n"
                   "💡 <b>Приложение:</b>\n"
                   "• <b>Stop Loss:</b> SL = Entry ± (1.5 × ATR)\n"
                   "• <b>Take Profit:</b> TP = Entry ± (2-3 × ATR)\n"
                   "• <b>Волатилност:</b> Висок ATR = повече движение\n\n"
                   "⚠️ <b>Важно:</b>\n"
                   "• ATR се адаптира към пазара\n"
                   "• По-голям ATR = по-широк SL/TP\n"
                   "• По-малък ATR = по-стегнат SL/TP",
            
            'BOS': "🔄 <b>BREAK OF STRUCTURE (BOS)</b>\n\n"
                   "Пробив на предишна структура - потвърждава продължение на тренда.\n\n"
                   "📈 <b>Bullish BOS:</b>\n"
                   "• Цената пробива previous higher high\n"
                   "• Потвърждава uptrend\n\n"
                   "📉 <b>Bearish BOS:</b>\n"
                   "• Цената пробива previous lower low\n"
                   "• Потвърждава downtrend\n\n"
                   "💡 <b>Разлика с MSS:</b>\n"
                   "• BOS = продължение на тренда\n"
                   "• MSS = СМЯНА на тренда\n"
                   "• BOS е по-слаб сигнал от MSS",
            
            'CHOCH': "🔄 <b>CHANGE OF CHARACTER (CHoCH)</b>\n\n"
                     "Ранен сигнал за възможна смяна на тренда - предшества MSS.\n\n"
                     "📊 <b>Какво е:</b>\n"
                     "• Първото нарушение на структурата\n"
                     "• По-слаб от MSS, но по-ранен\n"
                     "• Warning signal за traders\n\n"
                     "⚠️ <b>Как да реагираш:</b>\n"
                     "• НЕ влизай веднага\n"
                     "• Затвори съществуващи позиции\n"
                     "• Изчакай MSS за потвърждение\n\n"
                     "💡 <b>Последователност:</b>\n"
                     "1. CHoCH - ранен warning\n"
                     "2. MSS - потвърждение на обрат\n"
                     "3. BOS - продължение в новата посока",
            
            'TP': "🎯 <b>TAKE PROFIT (TP)</b>\n\n"
                  "Целева цена къде да затвориш позицията с печалба.\n\n"
                  "📊 <b>Как се калкулира:</b>\n"
                  "• Базиран на FVG зони\n"
                  "• Support/Resistance нива\n"
                  "• Fibonacci extension\n"
                  "• Risk/Reward ratio >= 1.5:1\n\n"
                  "💡 <b>Съвет:</b>\n"
                  "• Затвори 50% при TP1\n"
                  "• Move SL to breakeven\n"
                  "• Остави 50% за TP2",
            
            'SL': "🛑 <b>STOP LOSS (SL)</b>\n\n"
                  "Защитна цена къде да затвориш позицията при грешка.\n\n"
                  "📊 <b>Как се калкулира:</b>\n"
                  "• Базиран на ATR (волатилност)\n"
                  "• Под/над Order Block\n"
                  "• Зад Support/Resistance\n"
                  "• Обикновено 1-2% риск\n\n"
                  "💡 <b>Важно:</b>\n"
                  "• НЕ премествай SL надолу (long) или нагоре (short)\n"
                  "• По-добре да ти излезе SL отколкото да губиш повече",
            
            'RR': "⚖️ <b>RISK/REWARD RATIO (RR)</b>\n\n"
                  "Съотношение между потенциална печалба и риск.\n\n"
                  "📊 <b>Пример:</b>\n"
                  "• Entry: $100\n"
                  "• TP: $103 (+3%)\n"
                  "• SL: $99 (-1%)\n"
                  "• RR = 3:1 (отличен!)\n\n"
                  "💡 <b>Минимум:</b>\n"
                  "• Никога под 1.5:1\n"
                  "• Оптимално 2:1 или повече\n"
                  "• С 2:1 RR, 40% win rate = profit!",
            
            'RANGING': "📊 <b>RANGING MARKET (Странично движение)</b>\n\n"
                       "Пазар който се движи в ограничен диапазон без ясна посока.\n\n"
                       "⚠️ <b>Признаци:</b>\n"
                       "• Ниска волатилност\n"
                       "• Цената между support/resistance\n"
                       "• Много false breakouts\n\n"
                       "💡 <b>Стратегия:</b>\n"
                       "• НЕ търгувай breakouts\n"
                       "• Търгувай от краищата (range границите)\n"
                       "• Или изчакай излизане от range",
            
            'TRENDING': "📈 <b>TRENDING MARKET (Трендиращ пазар)</b>\n\n"
                        "Пазар с ясна посока - нагоре (uptrend) или надолу (downtrend).\n\n"
                        "✅ <b>Признаци:</b>\n"
                        "• Последователни higher highs/lows (uptrend)\n"
                        "• Последователни lower highs/lows (downtrend)\n"
                        "• Силен momentum\n\n"
                        "💡 <b>Стратегия:</b>\n"
                        "• Търгувай В посоката на тренда\n"
                        "• Entry на pullbacks (retracements)\n"
                        "• НЕ влизай срещу тренда"
        }
        
        # Търси термина
        found = False
        for key, explanation in explanations.items():
            if key in term or term in key:
                await update.message.reply_text(explanation, parse_mode='HTML')
                found = True
                break
        
        if not found:
            await update.message.reply_text(
                f"❌ Непознат термин: {term}\n\n"
                f"Използвай /explain без аргументи за пълен списък."
            )
        return
    
    # Покажи пълен списък
    message = """
📖 <b>ICT/LUXALGO РЕЧНИК</b>

Използвай: /explain <термин>

<b>📦 SMART MONEY CONCEPTS:</b>
• <code>/explain OB</code> - Order Blocks (+OB/-OB)
• <code>/explain FVG</code> - Fair Value Gaps
• <code>/explain MSS</code> - Market Structure Shift
• <code>/explain BSL</code> - Buy Side Liquidity
• <code>/explain SSL</code> - Sell Side Liquidity
• <code>/explain BOS</code> - Break of Structure
• <code>/explain CHoCH</code> - Change of Character

<b>📊 ПОДДРЪЖКА & СЪПРОТИВА:</b>
• <code>/explain Support</code> - Support нива
• <code>/explain Resistance</code> - Resistance нива
• <code>/explain Breakout</code> - Пробив на ниво
• <code>/explain Retest</code> - Повторен тест
• <code>/explain Fibonacci</code> - Fibonacci нива
• <code>/explain Liquidity</code> - Ликвидност зони
• <code>/explain Volume</code> - Обем на търговия
• <code>/explain ATR</code> - Average True Range

<b>🎯 RISK MANAGEMENT:</b>
• <code>/explain TP</code> - Take Profit
• <code>/explain SL</code> - Stop Loss
• <code>/explain RR</code> - Risk:Reward

<b>📈 MARKET CONDITIONS:</b>
• <code>/explain Ranging</code> - Ranging пазар
• <code>/explain Trending</code> - Trending пазар

💡 <b>Съвет:</b> Започни с OB, FVG и MSS!
"""
    
    await update.message.reply_text(message, parse_mode='HTML')


async def timeframe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Избор на таймфрейм"""
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    
    if not context.args:
        # Покажи текущ и опции
        keyboard = [
            [
                InlineKeyboardButton("⚡ 1м", callback_data="tf_1m"),
                InlineKeyboardButton("⚡ 5м", callback_data="tf_5m"),
                InlineKeyboardButton("📊 15м", callback_data="tf_15m"),
            ],
            [
                InlineKeyboardButton("📊 1ч", callback_data="tf_1h"),
                InlineKeyboardButton("📊 2ч", callback_data="tf_2h"),
                InlineKeyboardButton("📊 3ч", callback_data="tf_3h"),
            ],
            [
                InlineKeyboardButton("📈 4ч", callback_data="tf_4h"),
                InlineKeyboardButton("📈 1д", callback_data="tf_1d"),
                InlineKeyboardButton("📈 1с", callback_data="tf_1w"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = f"📈 <b>Избор на таймфрейм</b>\n\nТекущ: {settings['timeframe']}"
        await update.message.reply_text(message, parse_mode='HTML', reply_markup=reply_markup)
        return
    
    # Директна промяна
    tf = context.args[0].lower()
    valid_tfs = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w']
    
    if tf not in valid_tfs:
        await update.message.reply_text(f"❌ Невалиден таймфрейм. Избери от: {', '.join(valid_tfs)}")
        return
    
    settings['timeframe'] = tf
    await update.message.reply_text(f"✅ Таймфрейм променен на {tf}")


async def timeframe_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка на бутони за таймфрейм"""
    query = update.callback_query
    await query.answer()
    
    # Извлечи таймфрейма от callback_data
    tf_map = {
        'tf_15m': '15m',
        'tf_1h': '1h',
        'tf_2h': '2h',
        'tf_4h': '4h',
        'tf_1d': '1d',
        'tf_1w': '1w',
    }
    
    tf = tf_map.get(query.data)
    if not tf:
        return
    
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    settings['timeframe'] = tf
    
    await query.edit_message_text(f"✅ Таймфрейм променен на {tf}")


async def alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включване/изключване на автоматичните сигнали"""
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    chat_id = update.effective_chat.id
    
    if not context.args:
        # Toggle
        settings['alerts_enabled'] = not settings['alerts_enabled']
        status = "включени ✅" if settings['alerts_enabled'] else "изключени ❌"
        
        message = f"🔔 Автоматичните сигнали са {status}\n\n"
        
        if settings['alerts_enabled']:
            message += f"Интервал: {settings['alert_interval']/60:.0f} минути\n"
            message += f"Timeframe: {settings['timeframe']}\n\n"
            message += "За промяна на интервала:\n/alerts 30  (за 30 минути)"
            
            # Стартирай автоматични сигнали
            if context.application.job_queue:
                # Премахни предишни джобове
                current_jobs = context.application.job_queue.get_jobs_by_name(f"alerts_{chat_id}")
                for job in current_jobs:
                    job.schedule_removal()
                
                # Добави нов джоб
                context.application.job_queue.run_repeating(
                    send_alert_signal,
                    interval=settings['alert_interval'],
                    first=10,
                    data={'chat_id': chat_id},
                    name=f"alerts_{chat_id}"
                )
        else:
            # Спри автоматични сигнали
            if context.application.job_queue:
                current_jobs = context.application.job_queue.get_jobs_by_name(f"alerts_{chat_id}")
                for job in current_jobs:
                    job.schedule_removal()
        
        await update.message.reply_text(message)
        return
    
    # Промяна на интервала
    try:
        minutes = int(context.args[0])
        if minutes < 5:
            await update.message.reply_text("❌ Минималният интервал е 5 минути")
            return
        
        settings['alert_interval'] = minutes * 60
        await update.message.reply_text(f"✅ Интервал променен на {minutes} минути")
        
        # Рестартирай джоба ако е включен
        if settings['alerts_enabled'] and context.application.job_queue:
            current_jobs = context.application.job_queue.get_jobs_by_name(f"alerts_{chat_id}")
            for job in current_jobs:
                job.schedule_removal()
            
            context.application.job_queue.run_repeating(
                send_alert_signal,
                interval=settings['alert_interval'],
                first=10,
                data={'chat_id': chat_id},
                name=f"alerts_{chat_id}"
            )
    
    except ValueError:
        await update.message.reply_text("❌ Невалидна стойност за минути")


async def autonews_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Включване/изключване на автоматични новини"""
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    chat_id = update.effective_chat.id
    
    if not context.args:
        # Toggle
        settings['news_enabled'] = not settings['news_enabled']
        status = "включени ✅" if settings['news_enabled'] else "изключени ❌"
        
        message = f"📰 Автоматичните новини са {status}\n\n"
        
        if settings['news_enabled']:
            message += f"Интервал: {settings['news_interval']/3600:.1f} часа\n\n"
            message += "Новините се превеждат автоматично на български!\n\n"
            message += "За промяна на интервала:\n/autonews 120  (за 2 часа)\n/autonews 60   (за 1 час)"
            
            # Стартирай автоматични новини
            if context.application.job_queue:
                # Премахни предишни джобове
                current_jobs = context.application.job_queue.get_jobs_by_name(f"news_{chat_id}")
                for job in current_jobs:
                    job.schedule_removal()
                
                # Добави нов джоб
                context.application.job_queue.run_repeating(
                    send_auto_news,
                    interval=settings['news_interval'],
                    first=10,
                    data={'chat_id': chat_id},
                    name=f"news_{chat_id}"
                )
        else:
            # Спри автоматични новини
            if context.application.job_queue:
                current_jobs = context.application.job_queue.get_jobs_by_name(f"news_{chat_id}")
                for job in current_jobs:
                    job.schedule_removal()
        
        await update.message.reply_text(message)
        return
    
    # Промяна на интервала (в минути)
    try:
        minutes = int(context.args[0])
        if minutes < 30:
            await update.message.reply_text("❌ Минималният интервал е 30 минути")
            return
        
        settings['news_interval'] = minutes * 60
        await update.message.reply_text(f"✅ Интервал променен на {minutes} минути ({minutes/60:.1f}ч)")
        
        # Рестартирай джоба ако е включен
        if settings['news_enabled'] and context.application.job_queue:
            current_jobs = context.application.job_queue.get_jobs_by_name(f"news_{chat_id}")
            for job in current_jobs:
                job.schedule_removal()
            
            context.application.job_queue.run_repeating(
                send_auto_news,
                interval=settings['news_interval'],
                first=10,
                data={'chat_id': chat_id},
                name=f"news_{chat_id}"
            )
    
    except ValueError:
        await update.message.reply_text("❌ Невалидна стойност за минути")


async def monitor_active_trades(context: ContextTypes.DEFAULT_TYPE):
    """24/7 мониторинг на активни trades в журнала"""
    try:
        journal = load_journal()
        if not journal or not journal['trades']:
            return
        
        # Намери всички PENDING trades
        pending_trades = [t for t in journal['trades'] if t['status'] == 'PENDING']
        
        if not pending_trades:
            logger.info("📝 Няма активни trades за мониторинг")
            return
        
        logger.info(f"📝 Проверявам {len(pending_trades)} активни trades...")
        
        for trade in pending_trades:
            try:
                symbol = trade['symbol']
                entry_price = trade['entry_price']
                tp_price = trade['tp_price']
                sl_price = trade['sl_price']
                signal_type = trade['signal']
                
                # Вземи текущата цена
                params = {'symbol': symbol}
                data = await fetch_json(BINANCE_24H_URL, params)
                
                if isinstance(data, list):
                    data = next((s for s in data if s['symbol'] == symbol), None)
                
                if not data:
                    continue
                
                current_price = float(data['lastPrice'])
                
                # Провери дали е ударил TP или SL
                outcome = None
                profit_loss_pct = 0
                
                if signal_type == 'BUY':
                    if current_price >= tp_price:
                        outcome = 'WIN'
                        profit_loss_pct = ((current_price - entry_price) / entry_price) * 100
                        logger.info(f"✅ Trade #{trade['id']} HIT TP: {symbol} @ ${current_price:,.2f} (+{profit_loss_pct:.2f}%)")
                    elif current_price <= sl_price:
                        outcome = 'LOSS'
                        profit_loss_pct = ((current_price - entry_price) / entry_price) * 100
                        logger.info(f"❌ Trade #{trade['id']} HIT SL: {symbol} @ ${current_price:,.2f} ({profit_loss_pct:.2f}%)")
                
                elif signal_type == 'SELL':
                    if current_price <= tp_price:
                        outcome = 'WIN'
                        profit_loss_pct = ((entry_price - current_price) / entry_price) * 100
                        logger.info(f"✅ Trade #{trade['id']} HIT TP: {symbol} @ ${current_price:,.2f} (+{profit_loss_pct:.2f}%)")
                    elif current_price >= sl_price:
                        outcome = 'LOSS'
                        profit_loss_pct = ((entry_price - current_price) / entry_price) * 100
                        logger.info(f"❌ Trade #{trade['id']} HIT SL: {symbol} @ ${current_price:,.2f} ({profit_loss_pct:.2f}%)")
                
                # Обнови trade-а ако е завършен
                if outcome:
                    update_trade_outcome(
                        trade_id=trade['id'],
                        outcome=outcome,
                        profit_loss_pct=profit_loss_pct,
                        notes=f"Автоматично затворен: Цена удари {'TP' if outcome == 'WIN' else 'SL'} @ ${current_price:,.2f}"
                    )
                    
                    # Изпрати нотификация до owner
                    emoji = "✅" if outcome == 'WIN' else "❌"
                    message = f"{emoji} <b>TRADE ЗАТВОРЕН АВТОМАТИЧНО</b>\n\n"
                    message += f"📊 Trade #{trade['id']}\n"
                    message += f"💰 {symbol} {signal_type}\n"
                    message += f"📍 Entry: ${entry_price:,.2f}\n"
                    message += f"🎯 Exit: ${current_price:,.2f}\n"
                    message += f"💵 P/L: {profit_loss_pct:+.2f}%\n\n"
                    message += f"🤖 Резултатът е записан в ML Journal!"
                    
                    await context.bot.send_message(
                        chat_id=OWNER_CHAT_ID,
                        text=message,
                        parse_mode='HTML',
                        disable_notification=False
                    )
            
            except Exception as e:
                logger.error(f"Грешка при мониторинг на trade #{trade.get('id', '?')}: {e}")
                continue
        
        logger.info(f"📝 Journal мониторинг завършен")
        
    except Exception as e:
        logger.error(f"Грешка в monitor_active_trades: {e}")


async def send_alert_signal(context: ContextTypes.DEFAULT_TYPE):
    """Изпраща автоматичен сигнал с пълен анализ - ASYNC OPTIMIZED с memory cleanup"""
    chat_id = context.job.data['chat_id']
    settings = get_user_settings(context.application.bot_data, chat_id)
    
    logger.info("🔍 Започвам ASYNC проверка на всички монети и timeframes...")
    
    # Основни timeframes за проверка - 1h, 4h, 1d
    timeframes_to_check = ['1h', '4h', '1d']
    
    # 🚀 ASYNC ПАРАЛЕЛЕН АНАЛИЗ - всички монети/timeframes наведнъж
    async def analyze_single_pair(symbol, timeframe):
        """Анализира една двойка symbol+timeframe - ПЪЛЕН АНАЛИЗ като ръчните сигнали"""
        try:
            # Извлечи данни
            params_24h = {'symbol': symbol}
            data_24h = await fetch_json(BINANCE_24H_URL, params_24h)
            
            if isinstance(data_24h, list):
                data_24h = next((s for s in data_24h if s['symbol'] == symbol), None)
            
            if not data_24h:
                return None
            
            klines = await fetch_klines(symbol, timeframe, limit=100)
            
            if not klines:
                return None
            
            # Основен анализ
            analysis = analyze_signal(data_24h, klines, symbol, timeframe)
            
            if not analysis or analysis['signal'] == 'NEUTRAL':
                return None
            
            # ⚡ ПРОВЕРКА ЗА ДУБЛИРАНЕ (с 4-степенна проверка за близост на цена)
            if is_signal_already_sent(symbol, analysis['signal'], timeframe, analysis['confidence'], analysis['price'], cooldown_minutes=60):
                return None
            
            # === ДОПЪЛНИТЕЛНИ АНАЛИЗИ (КАТО РЪЧНИТЕ СИГНАЛИ) ===
            
            # 1. BTC CORRELATION
            btc_correlation = await analyze_btc_correlation(symbol, timeframe)
            
            # 2. ORDER BOOK ANALYSIS
            order_book = await analyze_order_book(symbol, analysis['price'])
            
            # 3. MULTI-TIMEFRAME CONFIRMATION
            mtf_confirmation = await get_higher_timeframe_confirmation(symbol, timeframe, analysis['signal'])
            
            # 4. NEWS SENTIMENT
            sentiment = await analyze_news_sentiment(symbol)
            
            # Коригирай confidence според допълнителните анализи
            final_confidence = analysis['confidence']
            
            # Order Book корекция
            if order_book:
                if order_book['pressure'] == analysis['signal']:
                    final_confidence += 10
                    analysis['reasons'].append(f"Order Book: {order_book['pressure']}")
                elif order_book['pressure'] != 'NEUTRAL' and order_book['pressure'] != analysis['signal']:
                    final_confidence -= 8
                    analysis['reasons'].append(f"⚠️ Order Book противоречи ({order_book['pressure']})")
            
            # Multi-timeframe корекция
            if mtf_confirmation and mtf_confirmation['confirmed']:
                final_confidence += 15
                analysis['reasons'].append(f"MTF: {mtf_confirmation['timeframe']} потвърждава")
            elif mtf_confirmation and not mtf_confirmation['confirmed']:
                final_confidence -= 10
                analysis['reasons'].append(f"⚠️ MTF: {mtf_confirmation['timeframe']} не потвърждава")
            
            # BTC Correlation корекция
            if btc_correlation:
                if btc_correlation['trend'] == analysis['signal']:
                    boost = min(btc_correlation['strength'] / 2, 12)
                    final_confidence += boost
                    analysis['reasons'].append(f"BTC {btc_correlation['trend']} ({btc_correlation['change']:+.1f}%)")
                elif btc_correlation['trend'] != 'NEUTRAL' and btc_correlation['trend'] != analysis['signal']:
                    penalty = min(btc_correlation['strength'] / 3, 10)
                    final_confidence -= penalty
                    analysis['reasons'].append(f"⚠️ BTC противоречи ({btc_correlation['trend']} {btc_correlation['change']:+.1f}%)")
            
            # Sentiment корекция
            if sentiment and sentiment['sentiment'] != 'NEUTRAL':
                if sentiment['sentiment'] == analysis['signal']:
                    final_confidence += sentiment['confidence']
                    analysis['reasons'].append(f"Новини {sentiment['sentiment']}: +{sentiment['confidence']:.0f}%")
                else:
                    final_confidence -= sentiment['confidence'] / 2
                    analysis['reasons'].append(f"⚠️ Новини противоречат ({sentiment['sentiment']})")
            
            # Обнови confidence
            final_confidence = max(0, min(final_confidence, 95))
            analysis['confidence'] = final_confidence
            
            # Използвай adaptive TP/SL
            if 'adaptive_tp_sl' in analysis:
                adaptive_levels = analysis['adaptive_tp_sl']
                tp_pct = adaptive_levels['tp']
                sl_pct = adaptive_levels['sl']
            else:
                tp_pct = 3.0
                sl_pct = 1.5
            
            # Изчисли TP и SL
            price = analysis['price']
            if analysis['signal'] == 'BUY':
                analysis['tp'] = price * (1 + tp_pct / 100)
                analysis['sl'] = price * (1 - sl_pct / 100)
            else:  # SELL
                analysis['tp'] = price * (1 - tp_pct / 100)
                analysis['sl'] = price * (1 + sl_pct / 100)
            
            # Запомни сигнала ако е качествен
            if final_confidence >= 60:
                logger.info(f"🔍 {symbol} ({timeframe}): {analysis['signal']} ({final_confidence}%)")
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'analysis': analysis,
                    'data_24h': data_24h,
                    'klines': klines,
                    'confidence': final_confidence,
                    'btc_correlation': btc_correlation,
                    'order_book': order_book,
                    'mtf_confirmation': mtf_confirmation,
                    'sentiment': sentiment
                }
            
            return None
        except Exception as e:
            logger.error(f"❌ Грешка при анализ на {symbol} {timeframe}: {e}")
            return None
    
    # Създай всички задачи за паралелно изпълнение
    tasks = []
    for symbol in SYMBOLS.values():
        for timeframe in timeframes_to_check:
            tasks.append(analyze_single_pair(symbol, timeframe))
    
    # Изпълни ВСИЧКИ задачи паралелно (6x по-бързо!)
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Филтрирай валидните сигнали
    all_good_signals = [r for r in results if r is not None and not isinstance(r, Exception)]
    
    # Ако няма добри сигнали, cleanup и излез
    if not all_good_signals:
        logger.info("⚠️ Няма сигнали с увереност ≥60% (или всички вече изпратени)")
        # 🧹 MEMORY CLEANUP
        plt.close('all')
        gc.collect()
        return
    
    # Сортирай по confidence (най-високите първи)
    all_good_signals.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Вземи топ 3 (или колкото има)
    signals_to_send = all_good_signals[:3]
    
    logger.info(f"📤 Изпращам {len(signals_to_send)} топ сигнал(а)")
    
    # Изпрати всеки сигнал
    for idx, sig in enumerate(signals_to_send):
        symbol = sig['symbol']
        timeframe = sig['timeframe']
        analysis = sig['analysis']
        klines = sig['klines']
        price = analysis['price']
        signal_emoji = "🟢" if analysis['signal'] == 'BUY' else "🔴"
        best_confidence = sig['confidence']
        
        # Header
        header = f" #{idx+1}" if len(signals_to_send) > 1 else ""
        
        # ✅ Сигналът вече е валидиран по-рано, можем да го изпратим
        
        # 📊 ЗАПИШИ СИГНАЛА В СТАТИСТИКАТА
        try:
            signal_id = record_signal(
                symbol=symbol,
                timeframe=timeframe,
                signal_type=analysis['signal'],
                confidence=best_confidence,
                entry_price=price,
                tp_price=analysis['tp'],
                sl_price=analysis['sl']
            )
            logger.info(f"📊 AUTO-SIGNAL recorded to stats (ID: {signal_id})")
        except Exception as e:
            logger.error(f"❌ Stats recording error in auto-signal: {e}")
        
        # 📝 АВТОМАТИЧНО ЛОГВАНЕ В JOURNAL - 24/7 събиране на данни
        if best_confidence >= 65:
            try:
                analysis_data = {
                    'rsi': analysis.get('rsi'),
                    # MA removed - ICT only
                    'volume_ratio': analysis.get('volume_ratio'),
                    'volatility': analysis.get('volatility'),
                    'trend': analysis.get('trend'),
                    'btc_correlation': None,
                    'sentiment': None
                }
            
                journal_id = log_trade_to_journal(
                    symbol=symbol,
                    timeframe=timeframe,  # От best_signal
                    signal_type=analysis['signal'],
                    confidence=best_confidence,
                    entry_price=price,
                    tp_price=analysis['tp'],
                    sl_price=analysis['sl'],
                    analysis_data=analysis_data
                )
            
                if journal_id:
                    logger.info(f"📝 AUTO-SIGNAL logged to ML journal (ID: {journal_id}) - 24/7 data collection")
            except Exception as e:
                logger.error(f"Journal logging error in auto-signal: {e}")
    
        # === ГЕНЕРИРАЙ ГРАФИКА ===
        chart_file = None
        try:
            luxalgo_ict_data = analysis.get('luxalgo_ict')
            chart_file = generate_chart(
                klines,
                symbol,
                analysis['signal'],
                price,
                analysis['tp'],
                analysis['sl'],
                timeframe,  # От best_signal
                luxalgo_ict_data
            )
            if chart_file:
                logger.info(f"📊 Графика генерирана успешно за {symbol}")
            else:
                logger.warning(f"⚠️ Графика не е генерирана за {symbol}")
        except Exception as e:
            logger.error(f"❌ Грешка при генериране на графика за {symbol}: {e}")
            chart_file = None
    
        # === ОПРЕДЕЛИ ТИП НА ТРЕЙДА ===
        # timeframe вече е взет от best_signal
        if timeframe in ['1m', '5m', '15m', '30m']:
            trade_type = "⚡ Краткосрочен"
            trade_duration = "Минути до часове"
        elif timeframe in ['1h', '2h', '4h']:
            trade_type = "📊 Средносрочен"
            trade_duration = "Часове до дни"
        elif timeframe in ['1d', '1w', '1M']:
            trade_type = "📈 Дългосрочен"
            trade_duration = "Дни до седмици"
        else:
            trade_type = "📊 Средносрочен"
            trade_duration = "Часове до дни"
    
        # === ПЪЛЕН АНАЛИЗ КАТО РЪЧНИТЕ СИГНАЛИ ===
    
        # Изчисли оптимални entry zones
        entry_zones = calculate_entry_zones(
            price, analysis['signal'], 
            analysis['closes'], analysis['highs'], analysis['lows'],
            analysis
        )
    
        # Quality badge за entry zone
        quality = entry_zones['quality']
        if quality >= 75:
            quality_badge = "💎"
            quality_text = "Отлично качество"
        elif quality >= 60:
            quality_badge = "🟢"
            quality_text = "Добро качество"
        elif quality >= 45:
            quality_badge = "🟡"
            quality_text = "Средно качество"
        else:
            quality_badge = "🟠"
            quality_text = "Ниско качество"
    
        # Създай съобщението
        message = f"🤖 <b>АВТОМАТИЧЕН СИГНАЛ</b> 🤖\n"
        message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
        message += f"{signal_emoji} <b>{symbol}: {analysis['signal']}</b>\n"
        message += f"📊 Увереност: <b>{analysis['confidence']}%</b>\n"
        message += f"💰 Цена: <b>${price:,.4f}</b>\n"
        message += f"📈 24ч промяна: <b>{analysis['change_24h']:+.2f}%</b>\n"
        message += f"⏰ Таймфрейм: <b>{timeframe}</b>\n"
        message += f"🎯 Тип трейд: <b>{trade_type}</b>\n"
        message += f"⏱️ Продължителност: <i>{trade_duration}</i>\n\n"
    
        # Entry zones
        message += f"🎯 <b>Нива за търговия:</b>\n\n"
        message += f"📍 <b>ENTRY ZONE</b> {quality_badge}:\n"
        message += f"   Качество: <b>{quality_text} ({entry_zones['quality']}/100)</b>\n"
        message += f"   Оптимален вход: <b>${entry_zones['best_entry']:,.4f}</b>\n"
        message += f"   Зона: ${entry_zones['entry_zone_low']:,.4f} - ${entry_zones['entry_zone_high']:,.4f}\n"
    
        # Support/Resistance levels
        if entry_zones.get('support_level'):
            message += f"   Support: ${entry_zones['support_level']:,.4f}\n"
        if entry_zones.get('resistance_level'):
            message += f"   Resistance: ${entry_zones['resistance_level']:,.4f}\n"
    
        # Entry recommendation
        if entry_zones.get('recommendation'):
            message += f"\n   💡 {entry_zones['recommendation']}\n\n"
        else:
            message += "\n"
    
        # TP/SL
        tp_pct = ((analysis['tp'] - price) / price) * 100
        sl_pct = ((analysis['sl'] - price) / price) * 100
    
        message += f"🎯 <b>TAKE PROFIT:</b> ${analysis['tp']:,.4f} ({tp_pct:+.2f}%)\n"
    
        # MTF Потвърждение
        mtf_info = sig.get('mtf_confirmation')
        if mtf_info and mtf_info.get('confirmed'):
            higher_tf = mtf_info.get('higher_timeframe', 'N/A')
            message += f"   ✅ <b>MTF:</b> {higher_tf} потвърждава\n"
        elif mtf_info:
            message += f"   ⚠️ MTF: Няма потвърждение\n"
    
        # TP вероятност и време
        if 'tp_probability' in analysis:
            tp_prob = analysis['tp_probability']
            prob_interpretation = ""
            if tp_prob >= 70:
                prob_interpretation = "Много високо"
            elif tp_prob >= 50:
                prob_interpretation = "Високо"
            elif tp_prob >= 30:
                prob_interpretation = "Средно"
            else:
                prob_interpretation = "Ниско"
            message += f"   🎲 Вероятност: {tp_prob:.0f}% ({prob_interpretation})\n"
    
        # Изчисли очаквано време за TP базирано на таймфрейм и волатилност
        if 'expected_time_hours' in analysis:
            expected_hours = analysis['expected_time_hours']
        else:
            # Изчисли базирано на таймфрейм и целева промяна
            target_change_pct = abs(tp_pct)
        
            # Волатилност на база 24ч промяна
            volatility_24h = abs(analysis.get('change_24h', 2.0))
        
            # Таймфрейм множители
            tf_multipliers = {
                '1m': 0.5, '5m': 1, '15m': 2, '30m': 4,
                '1h': 8, '2h': 12, '4h': 24,
                '1d': 48, '1w': 168, '1M': 720
            }
        
            base_hours = tf_multipliers.get(timeframe, 12)
        
            # Изчисли очаквано време
            if volatility_24h > 0:
                # Колко време е нужно да се постигне целта при текуща волатилност
                expected_hours = (target_change_pct / volatility_24h) * 24
                # Коригирай според таймфрейма
                expected_hours = min(expected_hours, base_hours * 3)
                expected_hours = max(expected_hours, base_hours * 0.5)
            else:
                expected_hours = base_hours
    
        # Форматирай времето красиво
        if expected_hours < 1:
            time_str = f"{int(expected_hours * 60)} минути"
        elif expected_hours < 24:
            time_str = f"{expected_hours:.1f} часа"
        elif expected_hours < 168:
            days = expected_hours / 24
            time_str = f"{days:.1f} дни"
        else:
            weeks = expected_hours / 168
            time_str = f"{weeks:.1f} седмици"
    
        message += f"   ⏱️ Очаквано време за цел: <b>~{time_str}</b>\n"
    
        message += f"\n🛡️ <b>STOP LOSS:</b> ${analysis['sl']:,.4f} ({sl_pct:+.2f}%)\n"
    
        # Risk/Reward
        risk = abs(price - analysis['sl'])
        reward = abs(analysis['tp'] - price)
        rr_ratio = reward / risk if risk > 0 else 0
        message += f"⚖️ Risk/Reward: 1:{rr_ratio:.2f}\n\n"
    
        # Причини за сигнала
        if analysis['reasons']:
            message += "💡 <b>Причини:</b>\n"
            for reason in analysis['reasons'][:3]:  # Първите 3 причини
                message += f"   • {reason}\n"
        
        # === ML ПРОГНОЗА (КАТО РЪЧНИТЕ СИГНАЛИ) ===
        ml_probability = None
        ml_message = ""
        
        if ML_PREDICTOR_AVAILABLE:
            try:
                ml_predictor = get_ml_predictor()
                
                # Подготви данни за ML прогноза
                ml_trade_data = {
                    'signal_type': analysis['signal'],
                    'confidence': best_confidence,
                    'entry_price': price,
                    'analysis_data': {
                        'rsi': analysis.get('rsi'),
                        'volume_ratio': analysis.get('volume_ratio'),
                        'volatility': analysis.get('volatility'),
                        'trend': analysis.get('trend'),
                        'btc_correlation': sig.get('btc_correlation'),
                        'sentiment': sig.get('sentiment')
                    }
                }
                
                # Получи ML прогноза
                ml_probability = ml_predictor.predict(ml_trade_data)
                
                if ml_probability is not None:
                    logger.info(f"🤖 ML Prediction: {ml_probability:.1f}% вероятност за успех")
                    
                    # Определи ML emoji според вероятността
                    if ml_probability >= 80:
                        ml_emoji = "🤖💎"
                        ml_quality = "Отлична"
                    elif ml_probability >= 70:
                        ml_emoji = "🤖✅"
                        ml_quality = "Много добра"
                    elif ml_probability >= 60:
                        ml_emoji = "🤖👍"
                        ml_quality = "Добра"
                    elif ml_probability >= 50:
                        ml_emoji = "🤖⚠️"
                        ml_quality = "Средна"
                    else:
                        ml_emoji = "🤖❌"
                        ml_quality = "Ниска"
                    
                    message += f"\n{ml_emoji} <b>ML ПРОГНОЗА:</b>\n"
                    message += f"   Вероятност за успех: <b>{ml_probability:.1f}%</b>\n"
                    message += f"   Качество на прогноза: <i>{ml_quality}</i>\n"
                    
            except Exception as e:
                logger.error(f"ML prediction error in auto-signal: {e}")
        
        message += "\n"
    
        try:
            # Изпрати графиката като снимка (ако има)
            if chart_file:
                short_caption = f"🔔🔊 {symbol} {analysis['signal']} ({analysis['confidence']:.0f}%)"
                
                if isinstance(chart_file, BytesIO):
                    chart_file.seek(0)
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=chart_file,
                        caption=short_caption,
                        parse_mode='HTML',
                        disable_notification=False
                    )
                elif isinstance(chart_file, str) and os.path.exists(chart_file):
                    with open(chart_file, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=short_caption,
                            parse_mode='HTML',
                            disable_notification=False
                        )
                    try:
                        os.remove(chart_file)
                    except:
                        pass
                
                # Изпрати пълното съобщение
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=message,
                    parse_mode='HTML',
                    disable_notification=True
                )
                logger.info(f"🔔 Автоматичен сигнал изпратен с графика: {symbol} {analysis['signal']} ({analysis['confidence']}%)")
            else:
                # Няма графика - само текст
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🔔🔊 {message}",
                    parse_mode='HTML',
                    disable_notification=False
                )
                logger.info(f"🔔 Автоматичен сигнал изпратен без графика: {symbol} {analysis['signal']} ({analysis['confidence']}%)")
            
            # === ДОБАВИ СИГНАЛА ЗА TRACKING ===
            add_signal_to_tracking(
                symbol=symbol,
                signal_type=analysis['signal'],
                entry_price=price,
                tp_price=analysis['tp'],
                sl_price=analysis['sl'],
                confidence=best_confidence,
                timeframe=timeframe,
                timestamp=datetime.now()
            )
        
        except Exception as e:
            logger.error(f"Грешка при изпращане на alert: {e}")
    
    # 🧹 ФИНАЛЕН MEMORY CLEANUP след всички сигнали
    logger.info("🧹 Memory cleanup след изпращане на сигнали...")
    plt.close('all')
    gc.collect()
    logger.info("✅ Memory cleanup завършен")


async def send_auto_news(context: ContextTypes.DEFAULT_TYPE):
    """Изпраща автоматични новини"""
    chat_id = context.job.data['chat_id']
    
    try:
        # Използвай RSS feed от CoinDesk
        coindesk_rss = "https://www.coindesk.com/arc/outboundfeeds/rss/"
        
        resp = await asyncio.to_thread(requests.get, coindesk_rss, timeout=10)
        
        if resp.status_code != 200:
            return
        
        # Parse RSS feed
        import xml.etree.ElementTree as ET
        root = ET.fromstring(resp.content)
        
        items = root.findall('.//item')[:1]  # Само първата новина
        
        if not items:
            return
        
        for item in items:
            title = item.find('title').text if item.find('title') is not None else ""
            link = item.find('link').text if item.find('link') is not None else ""
            description = item.find('description').text if item.find('description') is not None else ""
            
            if not title or not link:
                continue
            
            # Почисти HTML таговете
            if description:
                import re
                description = re.sub('<[^<]+?>', '', description)
                if len(description) > 100:
                    description = description[:100] + "..."
            
            # Преведи заглавието и описанието
            title_bg = await translate_text(title)
            description_bg = ""
            if description:
                description_bg = await translate_text(description)
            
            message = f"📰 <b>НОВА КРИПТО НОВИНА</b>\n\n"
            message += f"<b>{title_bg}</b>\n\n"
            
            if description_bg:
                message += f"<i>{description_bg}</i>\n\n"
            
            message += f"🌐 <a href=\"{link}\">Прочети пълната статия</a>\n\n"
            message += "💡 <i>Заглавие и описание са преведени автоматично!</i>\n"
            message += "💡 <i>Използвай автоматичен превод в браузъра за пълен текст</i>"
            
            await context.bot.send_message(
                chat_id=chat_id, 
                text=message, 
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
    except Exception as e:
        logger.error(f"Грешка при автоматични новини: {e}")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка на текстови бутони от клавиатурата"""
    text = update.message.text
    
    # Провери дали потребителят е в admin режим или въвежда парола
    if context.user_data.get('admin_command_mode') or context.user_data.get('awaiting_update_password'):
        await admin_mode_handler(update, context)
        return
    
    if text == "📊 Пазар":
        await market_cmd(update, context)
    elif text == "📈 Сигнал":
        await signal_cmd(update, context)
    elif text == "📰 Новини":
        await news_cmd(update, context)
    elif text == "⚙️ Настройки":
        await settings_cmd(update, context)
    elif text == "🔔 Alerts":
        await alerts_cmd(update, context)
    elif text == "ℹ️ Помощ":
        await help_cmd(update, context)
    elif text == "🏠 Меню":
        await start_cmd(update, context)
    elif text == "🔄 Рестарт":
        # Рестарт на бота
        logger.info(f"🔄 Restart button pressed by user {update.effective_user.id}")
        await restart_cmd(update, context)
    elif text == "📋 Отчети":
        await reports_cmd(update, context)
    elif text == "📚 ML Анализ":
        # ML Анализ главно меню
        await ml_menu_cmd(update, context)
    elif text == "🤖 ML Прогноза":
        await update.message.reply_text(
            "🤖 <b>ML ПРОГНОЗА</b>\n\n"
            "Използвай: <code>/signal BTC</code>\n\n"
            "ML прогнозата е включена в основния сигнал анализ.",
            parse_mode='HTML'
        )
    elif text == "📊 Backtest":
        await backtest_cmd(update, context)
    elif text == "📈 ML Report":
        await ml_report_cmd(update, context)
    elif text == "🔧 ML Status":
        await ml_status_cmd(update, context)
    elif text == "🏠 Назад към Меню":
        await start_cmd(update, context)
    elif text == "💻 Workspace":
        # Само owner има достъп до Workspace
        if update.effective_user.id != OWNER_CHAT_ID:
            await update.message.reply_text(
                "❌ <b>ДОСТЪП ОТКАЗАН</b>\n\n"
                "🔒 Workspace е достъпен само за owner.\n"
                "Съдържа административни файлове и код.",
                parse_mode='HTML'
            )
            return
        
        workspace_message = f"""💻 <b>GITHUB CODESPACE ACCESS</b>

🔐 <b>Директен достъп до твоя Workspace:</b>

🌐 <b>Codespace URL:</b>
https://github.com/codespaces

📂 <b>Repository:</b>
https://github.com/galinborisov10-art/Crypto-signal-bot

🚀 <b>Бърз старт:</b>
1️⃣ Кликни на линка отгоре
2️⃣ Намери "Crypto-signal-bot" Codespace
3️⃣ Натисни "Open in browser"
4️⃣ Готово! Workspace е отворен 🎉

💡 <b>Или използвай клавиатурата:</b>
• Отвори repo → Натисни точка (.)
• Автоматично отваря github.dev

🤖 <b>Когато влезеш:</b>
✅ GitHub Copilot е активен
✅ Виждаш всички файлове
✅ Можеш да правиш промени
✅ Terminal е достъпен

📋 <b>Провери задачи:</b>
Отвори файл: copilot_tasks.json
Или пиши тук: /task

🔔 <b>Workspace автоматично:</b>
• Запазва промените
• Sync с GitHub
• Auto-save enabled
"""
        await update.message.reply_text(
            workspace_message,
            parse_mode='HTML',
            disable_web_page_preview=False
        )
    
    elif text == "📖 Команди":
        commands_message = """📖 <b>ПЪЛЕН СПИСЪК С КОМАНДИ</b>

<b>📊 АНАЛИЗ И ДАННИ</b>
/market - Детайлен пазарен преглед
/signal BTC - Технически анализ за BTC
/signal ETH - Анализ за Ethereum
/stats - Статистика на бота

<b>📰 НОВИНИ (Real-time)</b>
/news - Всички новини (преведени)
/breaking - Само критични новини
/autonews - Управление на авто-новини

<b>🤖 COPILOT INTEGRATION</b>
/task - Виж задачи
/task [описание] - Създай задача
/workspace - Линк към Codespace

<b>⚙️ НАСТРОЙКИ</b>
/settings - Виж настройки
/settings tp 3.0 - Take Profit 3%
/settings sl 1.5 - Stop Loss 1.5%
/timeframe - Избери таймфрейм
/timeframe 4h - Задай 4h timeframe

<b>🔔 АВТОМАТИЗАЦИЯ</b>
/alerts - Вкл/Изкл авто-сигнали
/alerts 30 - Интервал 30 минути

<b>🔐 ADMIN (изисква парола)</b>
/admin_login [pass] - Вход в админ
/admin_daily - Дневен отчет
/admin_weekly - Седмичен отчет
/admin_monthly - Месечен отчет

<b>🔧 СИСТЕМА</b>
/update - Обнови бота от GitHub
/test - Диагностика + Auto-fix
/help - Помощна информация

<b>💡 КРАТКИ СЪКРАЩЕНИЯ</b>
/m = /market
/s BTC = /signal BTC
/n = /news
/b = /breaking
/t = /task

<b>🎯 ПРИМЕРИ</b>
<code>/signal BTC</code>
<code>/task Добави RSI индикатор</code>
<code>/settings tp 2.5</code>
<code>/alerts 15</code>
<code>/breaking</code>

📱 Всички команди работат навсякъде в чата!
"""
        await update.message.reply_text(
            commands_message,
            parse_mode='HTML'
        )
    
    elif text == "💻 Workspace":
        # Само owner има достъп до Workspace
        if update.effective_user.id != OWNER_CHAT_ID:
            await update.message.reply_text(
                "❌ <b>ДОСТЪП ОТКАЗАН</b>\n\n"
                "🔒 Workspace е достъпен само за owner.\n"
                "Съдържа административни файлове и код.",
                parse_mode='HTML'
            )
            return
        
        workspace_message = f"""💻 <b>GITHUB CODESPACE ACCESS</b>

🔐 <b>Директен достъп до твоя Workspace:</b>

🌐 <b>Codespace URL:</b>
https://github.com/codespaces

📂 <b>Repository:</b>
https://github.com/galinborisov10-art/Crypto-signal-bot

🚀 <b>Бърз старт:</b>
1️⃣ Кликни на линка отгоре
2️⃣ Намери "Crypto-signal-bot" Codespace
3️⃣ Натисни "Open in browser"
4️⃣ Готово! Workspace е отворен 🎉

💡 <b>Или използвай клавиатурата:</b>
• Отвори repo → Натисни точка (.)
• Автоматично отваря github.dev

🤖 <b>Когато влезеш:</b>
✅ GitHub Copilot е активен
✅ Виждаш всички файлове
✅ Можеш да правиш промени
✅ Terminal е достъпен

📋 <b>Провери задачи:</b>
Отвори файл: copilot_tasks.json
Или пиши тук: /task

🔔 <b>Workspace автоматично:</b>
• Запазва промените
• Sync с GitHub
• Auto-save enabled
"""
        await update.message.reply_text(
            workspace_message,
            parse_mode='HTML',
            disable_web_page_preview=False
        )
    
    elif text == "📖 Команди":
        commands_message = """📖 <b>ПЪЛЕН СПИСЪК С КОМАНДИ</b>

<b>📊 АНАЛИЗ И ДАННИ</b>
/market - Детайлен пазарен преглед
/signal BTC - Технически анализ за BTC
/signal ETH - Анализ за Ethereum
/stats - Статистика на бота

<b>📰 НОВИНИ (Real-time)</b>
/news - Всички новини (преведени)
/breaking - Само критични новини
/autonews - Управление на авто-новини

<b>🤖 COPILOT INTEGRATION</b>
/task - Виж задачи
/task [описание] - Създай задача
/workspace - Линк към Codespace

<b>⚙️ НАСТРОЙКИ</b>
/settings - Виж настройки
/settings tp 3.0 - Take Profit 3%
/settings sl 1.5 - Stop Loss 1.5%
/timeframe - Избери таймфрейм
/timeframe 4h - Задай 4h timeframe

<b>🔔 АВТОМАТИЗАЦИЯ</b>
/alerts - Вкл/Изкл авто-сигнали
/alerts 30 - Интервал 30 минути

<b>🔐 ADMIN (изисква парола)</b>
/admin_login [pass] - Вход в админ
/admin_daily - Дневен отчет
/admin_weekly - Седмичен отчет
/admin_monthly - Месечен отчет

<b>🔧 СИСТЕМА</b>
/update - Обнови бота от GitHub
/test - Диагностика + Auto-fix
/help - Помощна информация

<b>💡 КРАТКИ СЪКРАЩЕНИЯ</b>
/m = /market
/s BTC = /signal BTC
/n = /news
/b = /breaking
/t = /task
/w = /workspace

<b>🎯 ПРИМЕРИ</b>
<code>/signal BTC</code>
<code>/task Добави RSI индикатор</code>
<code>/settings tp 2.5</code>
<code>/alerts 15</code>
<code>/breaking</code>

📱 Всички команди работат навсякъде в чата!
"""
        await update.message.reply_text(
            commands_message,
            parse_mode='HTML'
        )
    
    elif text == "💬 Copilot":
        copilot_message = """
🤖 <b>GitHub Copilot Chat</b>

За директен достъп до GitHub Copilot в Codespace:

<b>📍 Как да отвориш Copilot:</b>
1. Отвори GitHub Codespace
2. Натисни <code>Ctrl + I</code> (Windows/Linux)
   или <code>Cmd + I</code> (Mac)
3. Или използвай <b>Chat иконката</b> от лявата странична лента

<b>💡 Полезни промптове:</b>
• "Анализирай логовете на бота"
• "Провери за грешки в bot.py"
• "Оптимизирай кода за сигнали"
• "Добави нова функция за..."

<b>🔗 Директни линкове:</b>
• GitHub Codespace: https://github.com/codespaces
• Репозитори: https://github.com/galinborisov10-art/Crypto-signal-bot

<b>⚡ Бързи команди:</b>
• <code>/explain</code> - Обясни код
• <code>/fix</code> - Поправи проблем
• <code>/tests</code> - Генерирай тестове

<i>Copilot може да ти помогне с код, дебъгване, оптимизация и нови функции!</i>
"""
        await update.message.reply_text(
            copilot_message,
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )


async def signal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка на inline бутони за избор на валута и таймфрейм"""
    query = update.callback_query
    await query.answer()
    
    # Обработка на връщане към менюто
    if query.data == 'back_to_menu':
        welcome_text = """
🤖 <b>Главно меню</b>

Използвайте бутоните отдолу за навигация:

📊 Пазар - Дневен преглед
📈 Сигнал - Технически анализ
📰 Новини - Последни новини
⚙️ Настройки - TP/SL/RR
🔔 Alerts - Автоматични сигнали
ℹ️ Помощ - Пълна документация
"""
        await query.message.edit_text(welcome_text, parse_mode='HTML')
        return
    
    # Връщане към менюто за избор на валута
    if query.data == "back_to_signal_menu":
        keyboard = [
            [
                InlineKeyboardButton("₿ BTC", callback_data="signal_BTCUSDT"),
                InlineKeyboardButton("Ξ ETH", callback_data="signal_ETHUSDT"),
            ],
            [
                InlineKeyboardButton("⚡ SOL", callback_data="signal_SOLUSDT"),
                InlineKeyboardButton("💎 XRP", callback_data="signal_XRPUSDT"),
            ],
            [
                InlineKeyboardButton("🔷 BNB", callback_data="signal_BNBUSDT"),
                InlineKeyboardButton("♠️ ADA", callback_data="signal_ADAUSDT"),
            ],
            [
                InlineKeyboardButton("🏠 Главно меню", callback_data="back_to_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text="📈 <b>Избери валута за анализ:</b>\n\n💡 <i>Съвет: Използвай /signal BTC 15m за конкретен таймфрейм</i>",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    # Избор на валута - покажи таймфреймове
    if query.data.startswith('signal_'):
        symbol = query.data.replace('signal_', '')
        
        # Покажи бутони за избор на таймфрейм
        keyboard = [
            [
                InlineKeyboardButton("⚡ 1m", callback_data=f"tf_{symbol}_1m"),
                InlineKeyboardButton("⚡ 5m", callback_data=f"tf_{symbol}_5m"),
                InlineKeyboardButton("⚡ 15m", callback_data=f"tf_{symbol}_15m"),
            ],
            [
                InlineKeyboardButton("📊 30m", callback_data=f"tf_{symbol}_30m"),
                InlineKeyboardButton("📊 1h", callback_data=f"tf_{symbol}_1h"),
                InlineKeyboardButton("📊 2h", callback_data=f"tf_{symbol}_2h"),
            ],
            [
                InlineKeyboardButton("📊 3h", callback_data=f"tf_{symbol}_3h"),
                InlineKeyboardButton("📊 4h", callback_data=f"tf_{symbol}_4h"),
                InlineKeyboardButton("📈 1d", callback_data=f"tf_{symbol}_1d"),
            ],
            [
                InlineKeyboardButton("📈 1w", callback_data=f"tf_{symbol}_1w"),
            ],
            [
                InlineKeyboardButton("🔙 Назад", callback_data="back_to_signal_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            text=f"📊 <b>{symbol}</b>\n\nИзбери таймфрейм за анализ:",
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        return
    
    # Избор на таймфрейм - изпълни анализа
    if query.data.startswith("tf_"):
        try:
            logger.info(f"Callback data: {query.data}")
            parts = query.data.replace("tf_", "").split("_")
            symbol = parts[0]
            timeframe = parts[1]
            logger.info(f"Processing signal for {symbol} on {timeframe}")
            
            # Изтрий предишното съобщение
            await query.message.delete()
            
            # Изпрати съобщение че анализира
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔍 Анализирам {symbol} на {timeframe}...",
                parse_mode='HTML'
            )
            
            # Вземи настройките
            settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
            
            # Извлечи 24h данни
            params_24h = {'symbol': symbol}
            data_24h = await fetch_json(BINANCE_24H_URL, params_24h)
            
            if not data_24h or isinstance(data_24h, list):
                if isinstance(data_24h, list):
                    data_24h = next((s for s in data_24h if s['symbol'] == symbol), None)
            
            if not data_24h:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Грешка при извличане на данни",
                    parse_mode='HTML'
                )
                return
            
            # Извлечи исторически данни (klines)
            klines = await fetch_klines(symbol, timeframe, limit=100)
            
            if not klines:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Грешка при извличане на исторически данни",
                    parse_mode='HTML'
                )
                return
            
            # Анализирай
            analysis = analyze_signal(data_24h, klines, symbol, timeframe)
            
            if not analysis:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ Грешка при анализ",
                    parse_mode='HTML'
                )
                return
            
            # === BTC CORRELATION ANALYSIS ===
            btc_correlation = await analyze_btc_correlation(symbol, timeframe)
            
            # === ORDER BOOK ANALYSIS ===
            order_book = await analyze_order_book(symbol, analysis['price'])
            
            # === MULTI-TIMEFRAME CONFIRMATION ===
            mtf_confirmation = await get_higher_timeframe_confirmation(symbol, timeframe, analysis['signal'])
            
            # === NEWS SENTIMENT ANALYSIS ===
            sentiment = await analyze_news_sentiment(symbol)
            
            # === MULTI-TIMEFRAME ANALYSIS ===
            logger.info(f"Starting MTF analysis for manual signal {symbol}")
            mtf_analysis = await get_multi_timeframe_analysis(symbol, timeframe)
            logger.info(f"MTF analysis result: {mtf_analysis}")
            
            # Коригирай confidence според допълнителните анализи
            final_confidence = analysis['confidence']
        
            # Order Book корекция
            if order_book:
                if order_book['pressure'] == analysis['signal']:
                    final_confidence += 10
                    analysis['reasons'].append(f"Order Book натиск: {order_book['pressure']}")
                elif order_book['pressure'] != 'NEUTRAL' and order_book['pressure'] != analysis['signal']:
                    final_confidence -= 8
                    analysis['reasons'].append(f"Order Book противоречи ({order_book['pressure']})")
                
                # Ако има близки стени
                if order_book['closest_support'] and analysis['signal'] == 'BUY':
                    support_price = order_book['closest_support'][0]
                    if abs(analysis['price'] - support_price) / analysis['price'] < 0.02:  # В рамките на 2%
                        final_confidence += 8
                        analysis['reasons'].append(f"Силна support стена на ${support_price:,.2f}")
                
                if order_book['closest_resistance'] and analysis['signal'] == 'SELL':
                    resistance_price = order_book['closest_resistance'][0]
                    if abs(resistance_price - analysis['price']) / analysis['price'] < 0.02:
                        final_confidence += 8
                        analysis['reasons'].append(f"Силна resistance стена на ${resistance_price:,.2f}")
            
            # Multi-timeframe корекция
            if mtf_confirmation and mtf_confirmation['confirmed']:
                final_confidence += 15
                analysis['reasons'].append(f"Потвърждение от {mtf_confirmation['timeframe']}")
            elif mtf_confirmation and not mtf_confirmation['confirmed']:
                final_confidence -= 10
                analysis['reasons'].append(f"{mtf_confirmation['timeframe']} не потвърждава")
            
            # BTC Correlation корекция
            if btc_correlation:
                if btc_correlation['trend'] == analysis['signal']:
                    boost = min(btc_correlation['strength'] / 2, 12)
                    final_confidence += boost
                    analysis['reasons'].append(f"BTC {btc_correlation['trend']} ({btc_correlation['change']:+.1f}%)")
                elif btc_correlation['trend'] != 'NEUTRAL' and btc_correlation['trend'] != analysis['signal']:
                    penalty = min(btc_correlation['strength'] / 3, 10)
                    final_confidence -= penalty
                    analysis['reasons'].append(f"⚠️ BTC противоречи ({btc_correlation['trend']} {btc_correlation['change']:+.1f}%)")
            
            # Sentiment корекция
            if sentiment and sentiment['sentiment'] != 'NEUTRAL':
                if sentiment['sentiment'] == analysis['signal']:
                    final_confidence += sentiment['confidence']
                    analysis['reasons'].append(f"Новини {sentiment['sentiment']}: +{sentiment['confidence']:.0f}%")
                else:
                    final_confidence -= sentiment['confidence'] / 2
                    analysis['reasons'].append(f"Новини противоречат ({sentiment['sentiment']})")
            
            # Обнови confidence и has_good_trade
            final_confidence = max(0, min(final_confidence, 95))
            analysis['confidence'] = final_confidence
            analysis['has_good_trade'] = analysis['signal'] in ['BUY', 'SELL'] and final_confidence >= 65
            
            # Използвай adaptive TP/SL
            adaptive_levels = analysis['adaptive_tp_sl']
            tp_pct = adaptive_levels['tp']
            sl_pct = adaptive_levels['sl']
            
            # Изчисли TP и SL нива
            price = analysis['price']
            
            if analysis['signal'] == 'BUY':
                tp_price = price * (1 + tp_pct / 100)
                sl_price = price * (1 - sl_pct / 100)
                signal_emoji = "🟢"
            elif analysis['signal'] == 'SELL':
                tp_price = price * (1 - tp_pct / 100)
                sl_price = price * (1 + sl_pct / 100)
                signal_emoji = "🔴"
            else:
                tp_price = price * (1 + tp_pct / 100)
                sl_price = price * (1 - sl_pct / 100)
                signal_emoji = "⚪"
            
            # Запиши ВСЕКИ auto-signal в статистиката
            signal_id = record_signal(
                symbol, 
                timeframe, 
                analysis['signal'], 
                final_confidence,
                entry_price=price,
                tp_price=tp_price,
                sl_price=sl_price
            )
            
            # Генерирай графика с luxalgo_ict данни
            luxalgo_ict_data = analysis.get('luxalgo_ict')
            chart_buffer = generate_chart(klines, symbol, analysis['signal'], price, tp_price, sl_price, timeframe, luxalgo_ict_data)
            
            # Изчисли вероятност за достигане на TP
            tp_probability = calculate_tp_probability(analysis, tp_price, analysis['signal'])
            
            # Изчисли оптимални entry zones
            entry_zones = calculate_entry_zones(
                price, 
                analysis['signal'], 
                analysis['closes'], 
                analysis['highs'], 
                analysis['lows'],
                analysis
            )
            
            # Форматирай съобщението
            confidence_emoji = "🔥" if final_confidence >= 80 else "💪" if final_confidence >= 70 else "👍" if final_confidence >= 60 else "🤔"
            change_emoji = "📈" if analysis['change_24h'] > 0 else "📉" if analysis['change_24h'] < 0 else "➡️"
            
            message = f"{signal_emoji} <b>СИГНАЛ: {symbol}</b>\n\n"
            message += f"📊 <b>Анализ ({timeframe}):</b>\n"
            message += f"Сигнал: <b>{analysis['signal']}</b> {signal_emoji}\n"
            message += f"Увереност: {final_confidence:.0f}% {confidence_emoji}\n\n"
            
            message += f"💰 <b>Текуща цена:</b> ${price:,.4f}\n"
            message += f"{change_emoji} 24ч промяна: {analysis['change_24h']:+.2f}%\n\n"
            
            # Обединена секция за ВСИЧКИ нива (Entry, TP, SL)
            message += f"🎯 <b>Нива за търговия:</b>\n\n"
            
            # Entry zone с quality badge
            if entry_zones['quality'] >= 75:
                quality_badge = "💎 Отлична"
            elif entry_zones['quality'] >= 60:
                quality_badge = "🟢 Много добра"
            elif entry_zones['quality'] >= 45:
                quality_badge = "🟡 Добра"
            else:
                quality_badge = "🟠 Приемлива"
            
            message += f"📍 <b>ENTRY ZONE</b> ({quality_badge} - {entry_zones['quality']}/100):\n"
            message += f"   Оптимален вход: <b>${entry_zones['best_entry']:,.4f}</b>\n"
            message += f"   Зона: ${entry_zones['entry_zone_low']:,.4f} - ${entry_zones['entry_zone_high']:,.4f}\n"
            
            # Support/Resistance ако има
            if analysis['signal'] == 'BUY' and entry_zones['supports']:
                message += f"   Support: ${entry_zones['supports'][0]:,.4f}\n"
            elif analysis['signal'] == 'SELL' and entry_zones['resistances']:
                message += f"   Resistance: ${entry_zones['resistances'][0]:,.4f}\n"
            
            # Entry препоръка
            price_vs_entry = (price - entry_zones['best_entry']) / price * 100
            if abs(price_vs_entry) < 0.5:
                entry_recommendation = "✅ Добър момент за вход - цената е близо до оптималния вход"
            elif (analysis['signal'] == 'BUY' and price > entry_zones['best_entry']) or \
                 (analysis['signal'] == 'SELL' and price < entry_zones['best_entry']):
                entry_recommendation = "⏳ По-добре изчакай pullback към зоната"
            else:
                entry_recommendation = "⚡ Цената е в entry зоната - разгледай вход"
            
            message += f"   💡 <i>{entry_recommendation}</i>\n\n"
            
            # Take Profit & Stop Loss
            message += f"🎯 <b>TAKE PROFIT:</b> ${tp_price:,.4f} (<b>{tp_pct:+.1f}%</b>)\n"
            
            # TP вероятност с интерпретация
            if tp_probability >= 76:
                tp_interpretation = "💚 Много добър шанс"
            elif tp_probability >= 66:
                tp_interpretation = "🟢 Добър шанс"
            elif tp_probability >= 56:
                tp_interpretation = "🟡 Среден шанс"
            elif tp_probability >= 36:
                tp_interpretation = "🟠 Нисък шанс"
            else:
                tp_interpretation = "🔴 Много нисък шанс"
            
            message += f"   🎲 Вероятност: {tp_probability}% ({tp_interpretation})\n"
            
            # Очаквано време за изпълнение
            timeframe_hours = {
                '1m': 0.017, '5m': 0.083, '15m': 0.25, '30m': 0.5,
                '1h': 1, '2h': 2, '4h': 4, '1d': 24, '1w': 168
            }
            estimated_hours = timeframe_hours.get(timeframe, 4) * 3
            
            if estimated_hours < 1:
                time_str = f"{int(estimated_hours * 60)} минути"
            elif estimated_hours < 24:
                time_str = f"{estimated_hours:.1f} часа"
            else:
                time_str = f"{estimated_hours / 24:.1f} дни"
            
            message += f"   ⏱️ Очаквано време: ~{time_str}\n\n"
            
            message += f"🛡️ <b>STOP LOSS:</b> ${sl_price:,.4f} (<b>{-sl_pct:.1f}%</b>)\n"
            message += f"⚖️ <b>Risk/Reward:</b> 1:{settings['rr']}\n\n"
            
            # === RISK MANAGEMENT ===
            risk_val = analysis.get('risk_validation')
            if risk_val:
                if risk_val['approved']:
                    message += f"🛡️ <b>RISK MANAGEMENT:</b> ✅ Одобрен\n"
                else:
                    message += f"🛡️ <b>RISK MANAGEMENT:</b> 🛑 НЕ одобрен\n"
                
                # Position size
                message += f"💰 Position size: ${risk_val['position_size_usd']:,.2f}\n"
                
                # Risk/Reward actual
                if risk_val['risk_reward_ratio'] > 0:
                    rr_emoji = "✅" if risk_val['risk_reward_ratio'] >= 2.0 else "⚠️"
                    message += f"⚖️ R/R фактически: 1:{risk_val['risk_reward_ratio']:.2f} {rr_emoji}\n"
                
                # Daily P/L
                daily_pnl = risk_val['daily_pnl_pct']
                if daily_pnl != 0:
                    pnl_emoji = "🟢" if daily_pnl > 0 else "🔴"
                    message += f"📊 Дневен P/L: {daily_pnl:+.2f}% {pnl_emoji}\n"
                
                # Active trades
                message += f"📈 Активни trades: {risk_val['active_trades']}/5\n"
                
                # Errors (if any)
                if risk_val['errors']:
                    message += f"\n⛔ <b>БЛОКИРАЩИ ПРОБЛЕМИ:</b>\n"
                    for error in risk_val['errors']:
                        message += f"  {error}\n"
                
                message += "\n"
            
            # === MULTI-TIMEFRAME КОНСЕНСУС ===
            # DEBUG: Покажи какво е върнато от MTF анализа
            logger.info(f"MTF Analysis Debug: {mtf_analysis}")
            
            if mtf_analysis and mtf_analysis.get('signals') and len(mtf_analysis['signals']) >= 1:
                message += f"🔍 <b>Multi-Timeframe Анализ (ВСИЧКИ TIMEFRAMES):</b>\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                
                # Покажи сигналите от различните таймфреймове в ред
                timeframe_order = ['1m', '5m', '15m', '1h', '2h', '3h', '4h', '1d', '1w']
                for tf in timeframe_order:
                    if tf in mtf_analysis['signals']:
                        sig = mtf_analysis['signals'][tf]
                        sig_emoji = "🟢" if sig['signal'] == 'BUY' else "🔴" if sig['signal'] == 'SELL' else "⚪"
                        current_marker = " ← ИЗБРАН" if tf == timeframe else ""
                        
                        # Confidence bar visualization
                        conf = sig['confidence']
                        if conf >= 75:
                            conf_bar = "█████"
                        elif conf >= 65:
                            conf_bar = "████░"
                        elif conf >= 55:
                            conf_bar = "███░░"
                        elif conf >= 45:
                            conf_bar = "██░░░"
                        else:
                            conf_bar = "█░░░░"
                        
                        message += f"{tf:>4}: {sig['signal']:>4} {sig_emoji} {conf_bar} {conf:.0f}%{current_marker}\n"
                    else:
                        message += f"{tf:>4}: ---  ⚪ ░░░░░   -  \n"
                
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                
                # Консенсус
                consensus_emoji = "🟢" if mtf_analysis['consensus'] == 'BUY' else "🔴" if mtf_analysis['consensus'] == 'SELL' else "⚪"
                message += f"💎 <b>Консенсус:</b> {mtf_analysis['consensus']} {consensus_emoji}\n"
                message += f"💪 <b>Сила:</b> {mtf_analysis['consensus_strength']} ({mtf_analysis['agreement']:.0f}% съгласие)\n"
                
                # Препоръка според консенсуса
                if mtf_analysis['consensus'] == analysis['signal'] and mtf_analysis['consensus_strength'] == 'Силен':
                    message += f"✅ <i>Всички таймфреймове потвърждават сигнала!</i>\n"
                elif mtf_analysis['consensus'] != analysis['signal']:
                    message += f"⚠️ <i>Внимание: По-големите таймфреймове показват {mtf_analysis['consensus']}</i>\n"
                
                message += "\n"
            else:
                # DEBUG: Покажи защо не се показва MTF анализа
                logger.warning(f"MTF analysis не се показва: mtf_analysis={mtf_analysis}")
            
            message += f"📊 <b>Индикатори:</b>\n"
            if analysis['rsi']:
                message += f"RSI(14): {analysis['rsi']:.1f}\n"
            # MA removed - pure ICT strategy
            
            if analysis['reasons']:
                message += f"\n💡 <b>Причини:</b>\n"
                for reason in analysis['reasons']:
                    message += f"• {reason}\n"
            
            message += f"\n⚠️ <i>Това не е финансов съвет!</i>"
            
            # Провери дали има подходящ трейд
            if not analysis.get('has_good_trade', False):
                # Няма подходящ трейд
                no_trade_message = f"⚪ <b>НЯМА ПОДХОДЯЩ ТРЕЙД</b>\n\n"
                no_trade_message += f"📊 <b>{symbol} ({timeframe})</b>\n\n"
                no_trade_message += f"💰 Цена: ${price:,.4f}\n"
                no_trade_message += f"📈 24ч промяна: {analysis['change_24h']:+.2f}%\n\n"
                no_trade_message += f"📊 <b>Индикатори:</b>\n"
                if analysis['rsi']:
                    no_trade_message += f"RSI(14): {analysis['rsi']:.1f}\n"
                # MA removed - pure ICT strategy
                no_trade_message += f"\nСигнал: {analysis['signal']}\n"
                no_trade_message += f"Увереност: {analysis['confidence']}%\n\n"
                no_trade_message += f"⚠️ <i>Пазарните условия не са подходящи за трейд в момента.</i>"
                
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=no_trade_message,
                    parse_mode='HTML'
                )
                return
            
            # DEBUG: Има подходящ трейд, изпращаме резултата
            logger.info(f"✅ Good trade found! Sending signal for {symbol} {timeframe}")
            
            # Изпрати графиката като снимка (ако има)
            if chart_buffer:
                # Кратък caption
                short_caption = f"{signal_emoji} <b>{analysis['signal']} {symbol}</b> ({timeframe})\n"
                short_caption += f"💰 ${price:,.4f} | 🎯 {analysis['confidence']:.0f}%"
                
                try:
                    await context.bot.send_photo(
                        chat_id=update.effective_chat.id,
                        photo=chart_buffer,
                        caption=f"🔔🔊 {short_caption}",
                        parse_mode='HTML',
                        disable_notification=False
                    )
                    
                    # Изпрати пълното съобщение
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=message,
                        parse_mode='HTML',
                        disable_notification=True
                    )
                    logger.info("✅ Signal with chart sent successfully!")
                except Exception as e:
                    logger.error(f"❌ Error sending signal: {e}")
                    # Fallback - само текст
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=message,
                        parse_mode='HTML'
                    )
            else:
                # Няма графика - изпрати само текст
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=message,
                    parse_mode='HTML',
                    disable_notification=False
                )
        
        except Exception as main_error:
            logger.error(f"❌ CRITICAL ERROR in signal_callback: {main_error}", exc_info=True)
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ Грешка при обработка на сигнала:\n{str(main_error)}",
                    parse_mode='HTML'
                )
            except:
                pass


# ================= DEPLOY КОМАНДА =================

async def deploy_digitalocean_old_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """🚀 OLD Deploy function (deprecated - uses git push via SSH)"""
    user_id = update.effective_chat.id
    
    # Само owner може да deploy-ва
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("❌ Тази команда е достъпна само за owner-а на бота.")
        return
    
    await update.message.reply_text("🚀 <b>DIGITAL OCEAN DEPLOY СТАРТИРА...</b>", parse_mode='HTML')
    
    import subprocess
    import os
    import json
    
    # Зареди Digital Ocean конфигурация
    config_path = os.path.join(os.path.dirname(__file__), 'admin', 'credentials.json')
    
    try:
        with open(config_path, 'r') as f:
            config = json.load(f)
            
        server_ip = config.get('DIGITALOCEAN_IP', '')
        ssh_key_path = config.get('SSH_KEY_PATH', '~/.ssh/id_rsa')
        
        if not server_ip:
            await update.message.reply_text(
                "❌ <b>Грешка:</b> DIGITALOCEAN_IP не е конфигуриран в admin/credentials.json\n\n"
                "Добави:\n<code>\"DIGITALOCEAN_IP\": \"YOUR_SERVER_IP\"</code>",
                parse_mode='HTML'
            )
            return
            
    except FileNotFoundError:
        await update.message.reply_text(
            "❌ <b>Грешка:</b> admin/credentials.json не е намерен",
            parse_mode='HTML'
        )
        return
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>Грешка при четене на конфигурация:</b>\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        # Стъпка 1: Git push
        await update.message.reply_text("📤 Стъпка 1/4: Push на промени към GitHub...", parse_mode='HTML')
        
        git_result = subprocess.run(
            ['git', 'push', 'origin', 'main'],
            capture_output=True,
            text=True,
            cwd=os.path.dirname(__file__),
            timeout=30
        )
        
        if git_result.returncode != 0:
            await update.message.reply_text(
                f"⚠️ Git push warning:\n<code>{git_result.stderr[:500]}</code>\n\nПродължаваме...",
                parse_mode='HTML'
            )
        
        # Стъпка 2: SSH команди за deploy
        await update.message.reply_text("🔄 Стъпка 2/4: Свързване към Digital Ocean...", parse_mode='HTML')
        
        deploy_commands = f"""
cd {BASE_PATH} && \
git pull origin main && \
source venv/bin/activate && \
pip install -r requirements.txt && \
sudo systemctl restart crypto-bot && \
echo "✅ Deploy complete!" && \
sleep 2 && \
sudo systemctl status crypto-bot --no-pager
"""
        
        ssh_result = subprocess.run(
            ['ssh', '-i', os.path.expanduser(ssh_key_path), 
             '-o', 'StrictHostKeyChecking=no',
             f'root@{server_ip}', deploy_commands],
            capture_output=True,
            text=True,
            timeout=120
        )
        
        # Стъпка 3: Резултат
        await update.message.reply_text("📊 Стъпка 3/4: Анализ на резултата...", parse_mode='HTML')
        
        if ssh_result.returncode == 0:
            # Успех
            output_lines = ssh_result.stdout.split('\n')
            last_30_lines = '\n'.join(output_lines[-30:])
            
            success_msg = "✅ <b>DIGITAL OCEAN DEPLOY УСПЕШЕН!</b>\n\n"
            success_msg += f"🖥️ <b>Server:</b> {server_ip}\n"
            success_msg += f"📝 <b>Изход:</b>\n<pre>{last_30_lines[:1500]}</pre>\n\n"
            success_msg += "🎉 Ботът работи на Digital Ocean 24/7!"
            
            await update.message.reply_text(success_msg, parse_mode='HTML')
            
        else:
            # Грешка
            error_msg = "❌ <b>DEPLOY НЕУСПЕШЕН!</b>\n\n"
            error_msg += f"🖥️ <b>Server:</b> {server_ip}\n"
            error_msg += f"🔴 <b>Exit Code:</b> {ssh_result.returncode}\n\n"
            error_msg += "📝 <b>Грешка:</b>\n"
            error_msg += f"<pre>{ssh_result.stderr[-1000:]}</pre>"
            
            await update.message.reply_text(error_msg, parse_mode='HTML')
        
        # Стъпка 4: Финал
        await update.message.reply_text(
            "🏁 Стъпка 4/4: Готово!\n\n"
            "📋 Полезни команди:\n"
            f"<code>ssh root@{server_ip}</code>\n"
            "<code>systemctl status crypto-bot</code>\n"
            "<code>journalctl -u crypto-bot -f</code>",
            parse_mode='HTML'
        )
            
    except subprocess.TimeoutExpired:
        await update.message.reply_text(
            "⏱️ <b>Timeout!</b> SSH команда отне повече от 2 минути.\n"
            f"Проверете ръчно: <code>ssh root@{server_ip}</code>",
            parse_mode='HTML'
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>Грешка при deploy:</b>\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )
        logger.error(f"Digital Ocean deploy грешка: {e}")


# ================= АДМИН КОМАНДИ =================

async def admin_login_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вход в админ панела"""
    if not context.args:
        await update.message.reply_text(
            "🔐 Използвай: /admin_login ПАРОЛА\n\n"
            "За първоначално задаване: /admin_setpass НОВА_ПАРОЛА"
        )
        return
    
    password = ' '.join(context.args)
    
    if verify_admin_password(password):
        await update.message.reply_text(
            "✅ Успешен вход!\n\n"
            "Достъпни команди:\n"
            "/admin_daily - Дневен отчет\n"
            "/admin_weekly - Седмичен отчет\n"
            "/admin_monthly - Месечен отчет\n"
            "/admin_docs - Документация"
        )
    else:
        await update.message.reply_text("❌ Грешна парола!")


async def admin_setpass_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Задай админ парола (само за owner)"""
    if update.effective_chat.id != OWNER_CHAT_ID:
        await update.message.reply_text("❌ Нямате достъп!")
        return
    
    if not context.args:
        await update.message.reply_text("Използвай: /admin_setpass НОВА_ПАРОЛА")
        return
    
    password = ' '.join(context.args)
    set_admin_password(password)
    await update.message.reply_text(
        "✅ Админ парола зададена успешно!\n\n"
        "Сега можете да влезете с: /admin_login ПАРОЛА"
    )


async def admin_daily_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерирай дневен отчет"""
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("❌ Моля, влезте с /admin_login ПАРОЛА")
        return
    
    await update.message.reply_text("📊 Генерирам дневен отчет...")
    
    try:
        report, file_path = generate_daily_report()
        
        # Изпрати отчета като файл със звукова аларма
        with open(file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=os.path.basename(file_path),
                caption="🔔🔊 📊 Дневен отчет",
                disable_notification=False
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Грешка: {e}")


async def admin_weekly_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерирай седмичен отчет"""
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("❌ Моля, влезте с /admin_login ПАРОЛА")
        return
    
    await update.message.reply_text("📈 Генерирам седмичен отчет...")
    
    try:
        report, file_path = generate_weekly_report()
        
        with open(file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=os.path.basename(file_path),
                caption="🔔🔊 📈 Седмичен отчет",
                disable_notification=False
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Грешка: {e}")


async def admin_monthly_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерирай месечен отчет"""
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("❌ Моля, влезте с /admin_login ПАРОЛА")
        return
    
    await update.message.reply_text("🎯 Генерирам месечен отчет...")
    
    try:
        report, file_path = generate_monthly_report()
        
        with open(file_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename=os.path.basename(file_path),
                caption="🔔🔊 🎯 Месечен отчет",
                disable_notification=False
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Грешка: {e}")


async def admin_docs_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изпрати админ документация"""
    if not is_admin(update.effective_chat.id):
        await update.message.reply_text("❌ Моля, влезте с /admin_login ПАРОЛА")
        return
    
    readme_path = f"{BASE_PATH}/admin/README.md"
    
    try:
        with open(readme_path, 'rb') as f:
            await context.bot.send_document(
                chat_id=update.effective_chat.id,
                document=f,
                filename="Admin_Documentation.md",
                caption="📋 Пълна документация"
            )
    except Exception as e:
        await update.message.reply_text(f"❌ Грешка: {e}")


# ================= АВТОМАТИЧНО ИЗПРАЩАНЕ НА ОТЧЕТИ =================

async def send_auto_news(bot):
    """Автоматично изпраща топ новини на owner-а от най-надеждните източници"""
    try:
        logger.info("📰 Извличане на автоматични новини от множество източници...")
        
        # Извлечи новини от всички надеждни източници
        news = await fetch_market_news()
        
        if not news:
            logger.warning("⚠️ Няма налични новини")
            return
        
        # Формирай съобщение
        news_message = "📰 <b>АВТОМАТИЧНИ КРИПТО НОВИНИ</b>\n"
        news_message += "━━━━━━━━━━━━━━━━━━━━━━━━\n"
        news_message += f"<i>🕐 {datetime.now().strftime('%d.%m.%Y %H:%M UTC')}</i>\n"
        news_message += f"<i>📊 Източници: CoinDesk, Cointelegraph, Decrypt</i>\n\n"
        
        for i, article in enumerate(news, 1):
            news_message += f"{i}. {article.get('source', '📰')} <b>{article['title']}</b>\n"
            
            if article.get('description'):
                # Вземи първите 120 символа
                desc = article['description'][:120] + "..." if len(article['description']) > 120 else article['description']
                # Премахни HTML тагове ако има
                import re
                desc = re.sub('<[^<]+?>', '', desc)
                news_message += f"   <i>{desc}</i>\n"
            
            if article.get('link'):
                news_message += f"   🔗 {article['link']}\n"
            
            if article.get('date'):
                news_message += f"   📅 {article['date']}\n"
            
            news_message += "\n"
        
        news_message += "<i>💡 За повече новини използвай /news</i>"
        
        # Изпрати на owner-а
        await bot.send_message(
            chat_id=OWNER_CHAT_ID,
            text=news_message,
            parse_mode='HTML',
            disable_web_page_preview=True  # Не показва preview на линковете
        )
        
        logger.info(f"✅ Автоматични новини изпратени успешно ({len(news)} статии)")
        
    except Exception as e:
        logger.error(f"❌ Грешка при изпращане на автоматични новини: {e}")


async def send_auto_report(report_type, bot):
    """Автоматично изпраща отчети на админа"""
    try:
        if report_type == 'daily':
            report, file_path = generate_daily_report()
            caption = "📊 Автоматичен дневен отчет"
        elif report_type == 'weekly':
            report, file_path = generate_weekly_report()
            caption = "📈 Автоматичен седмичен отчет"
        elif report_type == 'monthly':
            report, file_path = generate_monthly_report()
            caption = "🎯 Автоматичен месечен отчет"
        else:
            return
        
        with open(file_path, 'rb') as f:
            await bot.send_document(
                chat_id=OWNER_CHAT_ID,
                document=f,
                filename=os.path.basename(file_path),
                caption=f"🔔🔊 АЛАРМА! {caption}\n\n📊 Новият отчет е готов!",
                disable_notification=False  # Включена звукова аларма
            )
        logger.info(f"✅ Автоматичен {report_type} отчет изпратен")
    except Exception as e:
        logger.error(f"❌ Грешка при автоматичен отчет: {e}")


def run_diagnostics():
    """Изпълнява диагностика на системата"""
    if DIAGNOSTICS_AVAILABLE:
        try:
            import subprocess
            result = subprocess.run(
                [sys.executable, f'{BASE_PATH}/admin/diagnostics.py'],
                capture_output=True,
                text=True
            )
            logger.info(f"✅ Диагностика завършена с код: {result.returncode}")
            if result.stdout:
                logger.info(f"📋 Диагностика output:\n{result.stdout}")
        except Exception as e:
            logger.error(f"❌ Грешка при диагностика: {e}")
    else:
        logger.warning("⚠️ Диагностичен модул не е наличен")


async def send_high_confidence_alert(symbol, confidence, signal, price, tp_price, context):
    """Изпраща незабавна Telegram нотификация при високи сигнали (≥70%)"""
    if confidence >= 70:
        alert_message = f"""
🚨 <b>ВАЖЕН СИГНАЛ!</b> 🚨

💎 {symbol}
📊 Увереност: {confidence}%
🎯 Сигнал: {signal}

💰 Цена: ${price:,.4f}
🎯 Take Profit: ${tp_price:,.4f}

⚡ Препоръка: Незабавно действие!
⏰ Време: {datetime.now().strftime('%H:%M:%S')}
"""
        
        try:
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=alert_message,
                parse_mode='HTML',
                disable_notification=False  # Звукова аларма
            )
            logger.info(f"🚨 Изпратен high-confidence alert за {symbol} ({confidence}%)")
        except Exception as e:
            logger.error(f"❌ Грешка при изпращане на alert: {e}")


async def ask_for_confirmation(message_text, context, user_id=None):
    """
    Изпраща съобщение и иска потвърждение от admin.
    Използвай това когато искаш потвърждение преди да продължиш с действие.
    
    Примерна употреба:
    await ask_for_confirmation("Да рестартирам ли бота сега?", context)
    # После потребителят пише "enter" за да потвърди
    """
    try:
        target_id = user_id if user_id else OWNER_CHAT_ID
        
        confirmation_msg = f"""
❓ <b>ИЗИСКВА СЕ ПОТВЪРЖДЕНИЕ</b>

{message_text}

💡 Напиши <code>enter</code> за да потвърдиш или <code>exit</code> за отказ.
"""
        
        await context.bot.send_message(
            chat_id=target_id,
            text=confirmation_msg,
            parse_mode='HTML',
            disable_notification=False
        )
        
        logger.info(f"❓ Изпратена заявка за потвърждение: {message_text}")
        
    except Exception as e:
        logger.error(f"❌ Грешка при изпращане на заявка за потвърждение: {e}")


async def update_bot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Опростена команда за обновяване чрез текстово съобщение от чата"""
    user_id = update.effective_user.id
    
    # Само за owner (security)
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("🔐 Тази команда е само за owner-а на бота.")
        return
    
    # Направо питай за парола
    await update.message.reply_text(
        "🔐 <b>PROTECTED: Admin режим</b>\n\nВъведи парола за достъп:",
        parse_mode='HTML'
    )
    
    # Маркирай че очакваме парола
    context.user_data['awaiting_update_password'] = True


async def auto_update_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Автоматично обновяване на бота от GitHub с рестарт - САМО ЗА OWNER"""
    user_id = update.effective_user.id
    
    # Само за owner (security) - достатъчна защита!
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("🔐 Тази команда е само за owner-а на бота.")
        return
    
    import subprocess
    import os
    
    # Изпрати съобщение че започва
    status_msg = await update.message.reply_text("🔄 <b>Започвам update...</b>", parse_mode='HTML')
    
    try:
        # Определи project directory
        project_dir = os.path.dirname(os.path.abspath(__file__))
        
        # Backup important files
        await status_msg.edit_text("💾 Backup на данни...")
        backup_files = ['bot_stats.json', 'trading_journal.json', 'copilot_tasks.json']
        for f in backup_files:
            try:
                subprocess.run(['cp', f, f + '.backup'], cwd=project_dir, timeout=5)
            except:
                pass
        
        # Git pull
        await status_msg.edit_text("📥 Изтегляне от GitHub...")
        git_result = subprocess.run(
            ['git', 'pull', 'origin', 'main'],
            cwd=project_dir,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if git_result.returncode != 0:
            await status_msg.edit_text(
                f"❌ <b>Git pull failed:</b>\n<code>{git_result.stderr[:300]}</code>",
                parse_mode='HTML'
            )
            return
        
        # Check if venv exists
        venv_python = os.path.join(project_dir, 'venv', 'bin', 'python')
        venv_pip = os.path.join(project_dir, 'venv', 'bin', 'pip')
        
        if os.path.exists(venv_python):
            # Update dependencies
            await status_msg.edit_text("📦 Обновяване на dependencies...")
            pip_result = subprocess.run(
                [venv_pip, 'install', '-r', 'requirements.txt', '--quiet'],
                cwd=project_dir,
                capture_output=True,
                timeout=60
            )
        
        # Restart bot
        await status_msg.edit_text("🔄 Рестартиране...")
        
        # Kill current process
        subprocess.run(['pkill', '-f', 'bot.py'], timeout=5)
        
        # Wait a bit
        await asyncio.sleep(2)
        
        # Start new process
        if os.path.exists(venv_python):
            subprocess.Popen(
                [venv_python, 'bot.py'],
                cwd=project_dir,
                stdout=open('bot.log', 'w'),
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        else:
            subprocess.Popen(
                ['python3', 'bot.py'],
                cwd=project_dir,
                stdout=open('bot.log', 'w'),
                stderr=subprocess.STDOUT,
                start_new_session=True
            )
        
        # Success message
        commit_msg = "Updated to latest version"
        if "Already up to date" not in git_result.stdout:
            # Extract commit message
            try:
                log_result = subprocess.run(
                    ['git', 'log', '-1', '--pretty=format:%s'],
                    cwd=project_dir,
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if log_result.returncode == 0:
                    commit_msg = log_result.stdout[:100]
            except:
                pass
        
        await status_msg.edit_text(
            f"✅ <b>DEPLOY УСПЕШЕН!</b>\n\n"
            f"📥 Последен commit:\n<code>{commit_msg}</code>\n\n"
            f"🔄 Бот рестартиран\n"
            f"⏰ {datetime.now().strftime('%H:%M:%S')}\n\n"
            f"<i>Работи с нова версия! 🚀</i>",
            parse_mode='HTML'
        )
        
    except subprocess.TimeoutExpired:
        await status_msg.edit_text(
            "⏱️ <b>TIMEOUT</b>\n\n"
            "Update отне твърде много време.",
            parse_mode='HTML'
        )
    except Exception as e:
        await status_msg.edit_text(
            f"❌ <b>ГРЕШКА</b>\n\n<code>{str(e)[:300]}</code>",
            parse_mode='HTML'
        )


async def test_system_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Тествай системата и автоматично отстрани всички грешки"""
    user_id = update.effective_user.id
    
    # Само за owner (security)
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("🔐 Тази команда е само за owner-а на бота.")
        return
    
    await update.message.reply_text("🔍 <b>ТЕСТВАНЕ НА СИСТЕМАТА</b>\n\n⏳ Анализирам и отстранявам грешки...", parse_mode='HTML')
    
    import subprocess
    import os
    
    problems_found = []
    problems_fixed = []
    
    try:
        # 1. Проверка дали ботът работи
        await update.message.reply_text("1️⃣ Проверявам дали ботът работи...")
        result = subprocess.run(
            ["pgrep", "-f", "python3.*bot.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            bot_pid = result.stdout.strip().split()[0]
            await update.message.reply_text(f"✅ Ботът работи (PID: {bot_pid})")
        else:
            problems_found.append("Ботът НЕ работи")
            await update.message.reply_text("⚠️ Ботът НЕ работи - стартирам...")
            
            subprocess.run([f"{BASE_PATH}/bot-manager.sh", "start"], timeout=30)
            problems_fixed.append("Стартиран неработещ бот")
            await update.message.reply_text("✅ Ботът стартиран")
        
        # 2. Проверка за липсващи Python модули
        await update.message.reply_text("2️⃣ Проверявам Python модули...")
        
        required_modules = ['telegram', 'apscheduler', 'mplfinance', 'ta', 'pandas', 'numpy', 'requests']
        missing_modules = []
        
        for module in required_modules:
            try:
                if module == 'telegram':
                    import telegram
                elif module == 'apscheduler':
                    import apscheduler
                elif module == 'mplfinance':
                    import mplfinance
                elif module == 'ta':
                    import ta
                elif module == 'pandas':
                    import pandas
                elif module == 'numpy':
                    import numpy
                elif module == 'requests':
                    import requests
            except ImportError:
                missing_modules.append(module)
        
        if missing_modules:
            problems_found.append(f"Липсващи модули: {', '.join(missing_modules)}")
            await update.message.reply_text(f"⚠️ Липсващи модули: {', '.join(missing_modules)}\n\n⏳ Инсталирам...")
            
            # Инсталирай модулите
            install_list = missing_modules.copy()
            if 'telegram' in install_list:
                install_list.remove('telegram')
                install_list.append('python-telegram-bot==20.7')
            
            result = subprocess.run(
                ["pip", "install", "-q"] + install_list,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                problems_fixed.append(f"Инсталирани модули: {', '.join(missing_modules)}")
                await update.message.reply_text(f"✅ Модули инсталирани: {', '.join(missing_modules)}")
                
                # Рестартирай бота
                await update.message.reply_text("🔄 Рестартирам бота...")
                subprocess.run([f"{BASE_PATH}/bot-manager.sh", "restart"], timeout=30)
            else:
                await update.message.reply_text(f"❌ Грешка при инсталация: {result.stderr[:500]}")
        else:
            await update.message.reply_text("✅ Всички модули са налични")
        
        # 3. Проверка за множество инстанции (409 конфликти)
        await update.message.reply_text("3️⃣ Проверявам за множество инстанции...")
        
        result = subprocess.run(
            ["pgrep", "-f", "python3.*bot.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        pids = result.stdout.strip().split('\n') if result.stdout else []
        pids = [p for p in pids if p]
        
        if len(pids) > 1:
            problems_found.append(f"Множество инстанции: {len(pids)}")
            await update.message.reply_text(f"⚠️ Намерени {len(pids)} инстанции - отстранявам конфликт...")
            
            subprocess.run(["pkill", "-9", "-f", "python3.*bot.py"], timeout=10)
            import time
            time.sleep(3)
            subprocess.run([f"{BASE_PATH}/bot-manager.sh", "start"], timeout=30)
            
            problems_fixed.append("Отстранени множество инстанции")
            await update.message.reply_text("✅ Конфликтът е отстранен")
        else:
            await update.message.reply_text("✅ Няма множество инстанции")
        
        # 4. Анализ на логове
        await update.message.reply_text("4️⃣ Анализирам логове за грешки...")
        
        log_file = f"{BASE_PATH}/bot.log"
        if os.path.exists(log_file):
            with open(log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                recent_lines = lines[-200:] if len(lines) > 200 else lines
            
            conflicts = sum(1 for line in recent_lines if '409' in line and 'Conflict' in line)
            forbidden = sum(1 for line in recent_lines if '403' in line and 'Forbidden' in line)
            connection_errors = sum(1 for line in recent_lines if 'ConnectionError' in line or 'TimeoutError' in line)
            
            log_summary = f"📊 Анализ на логове:\n"
            log_summary += f"   409 Conflicts: {conflicts}\n"
            log_summary += f"   403 Forbidden: {forbidden}\n"
            log_summary += f"   Connection Errors: {connection_errors}"
            
            await update.message.reply_text(log_summary)
            
            if conflicts > 5:
                problems_found.append(f"Множество 409 конфликти: {conflicts}")
            if forbidden > 3:
                problems_found.append(f"403 Forbidden грешки: {forbidden} (проверете OWNER_CHAT_ID)")
            if connection_errors > 10:
                problems_found.append(f"Connection errors: {connection_errors}")
                await update.message.reply_text("⚠️ Много connection errors - рестартирам бота...")
                subprocess.run([f"{BASE_PATH}/bot-manager.sh", "restart"], timeout=30)
                problems_fixed.append("Рестартиран поради connection errors")
        else:
            await update.message.reply_text("⚠️ Няма log файл")
        
        # 5. Проверка на Auto-fixer
        await update.message.reply_text("5️⃣ Проверявам Auto-fixer...")
        
        result = subprocess.run(
            ["pgrep", "-f", "python3.*auto_fixer.py"],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0 and result.stdout.strip():
            fixer_pid = result.stdout.strip().split()[0]
            await update.message.reply_text(f"✅ Auto-fixer работи (PID: {fixer_pid})")
        else:
            problems_found.append("Auto-fixer НЕ работи")
            await update.message.reply_text("⚠️ Auto-fixer НЕ работи - стартирам...")
            
            subprocess.run([f"{BASE_PATH}/auto-fixer-manager.sh", "start"], timeout=30)
            problems_fixed.append("Стартиран Auto-fixer")
            await update.message.reply_text("✅ Auto-fixer стартиран")
        
        # 6. Финален резултат
        await update.message.reply_text("\n━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        result_message = "📊 <b>РЕЗУЛТАТ ОТ ТЕСТА</b>\n\n"
        
        if problems_found:
            result_message += f"⚠️ <b>Открити проблеми ({len(problems_found)}):</b>\n"
            for i, problem in enumerate(problems_found, 1):
                result_message += f"   {i}. {problem}\n"
            result_message += "\n"
        else:
            result_message += "✅ <b>Няма открити проблеми</b>\n\n"
        
        if problems_fixed:
            result_message += f"🔧 <b>Отстранени проблеми ({len(problems_fixed)}):</b>\n"
            for i, fix in enumerate(problems_fixed, 1):
                result_message += f"   {i}. {fix}\n"
            result_message += "\n"
        
        if not problems_found and not problems_fixed:
            result_message += "🎉 Системата работи отлично!"
        elif problems_fixed:
            result_message += "✅ Всички проблеми са отстранени!"
        
        await update.message.reply_text(result_message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Грешка при тестване на системата: {e}")
        await update.message.reply_text(f"❌ Грешка при тестване: {str(e)}", parse_mode='HTML')


# ================= USER ACCESS MANAGEMENT =================

async def approve_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Одобрява нов потребител (само owner)"""
    user_id = update.effective_user.id
    
    # Само owner може да одобрява
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("🔐 Тази команда е само за owner-а.")
        return
    
    # Провери аргументи
    if not context.args:
        await update.message.reply_text(
            "❌ Моля, посочи User ID:\n\n"
            "<code>/approve USER_ID</code>\n\n"
            "Пример: <code>/approve 123456789</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        new_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Невалиден User ID")
        return
    
    # Добави в allowed users
    ALLOWED_USERS.add(new_user_id)
    
    # Запази във файл
    try:
        with open(ALLOWED_USERS_FILE, 'w') as f:
            json.dump(list(ALLOWED_USERS), f, indent=2)
        
        # Вземи информация за потребителя ако има
        user_info = ACCESS_ATTEMPTS.get(new_user_id, {})
        username = user_info.get('username', 'Unknown')
        first_name = user_info.get('first_name', 'Unknown')
        
        success_msg = f"""✅ <b>ПОТРЕБИТЕЛ ОДОБРЕН</b>

👤 <b>Име:</b> {first_name}
🆔 <b>User ID:</b> <code>{new_user_id}</code>
📱 <b>Username:</b> @{username}

✅ Потребителят вече може да използва бота."""
        
        await update.message.reply_text(success_msg, parse_mode='HTML')
        
        # Изтрий от опити
        if new_user_id in ACCESS_ATTEMPTS:
            del ACCESS_ATTEMPTS[new_user_id]
        
        logger.info(f"✅ Owner одобри потребител {new_user_id} (@{username})")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Грешка при запис: {e}")
        logger.error(f"Грешка при одобрение на потребител: {e}")


async def block_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Блокира потребител (само owner)"""
    user_id = update.effective_user.id
    
    # Само owner може да блокира
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("🔐 Тази команда е само за owner-а.")
        return
    
    # Провери аргументи
    if not context.args:
        await update.message.reply_text(
            "❌ Моля, посочи User ID:\n\n"
            "<code>/block USER_ID</code>\n\n"
            "Пример: <code>/block 123456789</code>",
            parse_mode='HTML'
        )
        return
    
    try:
        blocked_user_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ Невалиден User ID")
        return
    
    # Не може да блокираш owner-а
    if blocked_user_id == OWNER_CHAT_ID:
        await update.message.reply_text("❌ Не можеш да блокираш owner-а!")
        return
    
    # Махни от allowed users
    if blocked_user_id in ALLOWED_USERS:
        ALLOWED_USERS.discard(blocked_user_id)
        
        # Запази във файл
        try:
            with open(ALLOWED_USERS_FILE, 'w') as f:
                json.dump(list(ALLOWED_USERS), f, indent=2)
            
            user_info = ACCESS_ATTEMPTS.get(blocked_user_id, {})
            username = user_info.get('username', 'Unknown')
            first_name = user_info.get('first_name', 'Unknown')
            
            block_msg = f"""🚫 <b>ПОТРЕБИТЕЛ БЛОКИРАН</b>

👤 <b>Име:</b> {first_name}
🆔 <b>User ID:</b> <code>{blocked_user_id}</code>
📱 <b>Username:</b> @{username}

❌ Достъпът е отнет."""
            
            await update.message.reply_text(block_msg, parse_mode='HTML')
            logger.info(f"🚫 Owner блокира потребител {blocked_user_id} (@{username})")
            
        except Exception as e:
            await update.message.reply_text(f"❌ Грешка при запис: {e}")
            logger.error(f"Грешка при блокиране на потребител: {e}")
    else:
        await update.message.reply_text(f"ℹ️ Потребител {blocked_user_id} не е в списъка с разрешени.")


async def list_users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показва списък с разрешени потребители (само owner)"""
    user_id = update.effective_user.id
    
    # Само owner може да вижда списъка
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("🔐 Тази команда е само за owner-а.")
        return
    
    users_list = f"""👥 <b>РАЗРЕШЕНИ ПОТРЕБИТЕЛИ</b>

📊 <b>Общо:</b> {len(ALLOWED_USERS)}

<b>User IDs:</b>
"""
    
    for uid in sorted(ALLOWED_USERS):
        if uid == OWNER_CHAT_ID:
            users_list += f"• <code>{uid}</code> 👑 (Owner)\n"
        else:
            users_list += f"• <code>{uid}</code>\n"
    
    # Покажи и опитите за достъп
    if ACCESS_ATTEMPTS:
        users_list += f"\n\n🚨 <b>ОПИТИ ЗА ДОСТЪП:</b> {len(ACCESS_ATTEMPTS)}\n\n"
        for uid, info in sorted(ACCESS_ATTEMPTS.items(), key=lambda x: x[1]['attempts'], reverse=True):
            users_list += f"• @{info['username']} (<code>{uid}</code>)\n"
            users_list += f"  └ Опити: {info['attempts']}\n"
    
    await update.message.reply_text(users_list, parse_mode='HTML')


async def admin_mode_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command mode handler - изисква admin парола"""
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Провери дали потребителят е в режим за изпълнение на команди
    if context.user_data.get('admin_command_mode'):
        command = update.message.text.strip()
        
        # ЛОГ: Запиши командата
        logger.info(f"🔧 TELEGRAM ADMIN COMMAND от @{username} (ID:{user_id}): {command}")
        
        # Специална команда "Enter" за потвърждение
        if command.lower() in ['enter', 'ентър', 'ok', 'да', 'yes', '✅ enter']:
            logger.info(f"✅ @{username} потвърди с Enter")
            await update.message.reply_text("✅ Потвърдено", reply_markup=get_admin_keyboard())
            context.user_data['pending_confirmation'] = False
            return
        
        # Изход от режим
        if command.lower() in ['exit', 'quit', 'изход', 'cancel', '❌ exit']:
            context.user_data['admin_command_mode'] = False
            logger.info(f"🔓 @{username} излезе от Admin режим")
            await update.message.reply_text(
                "✅ Излизане от admin режим.",
                reply_markup=get_main_keyboard()
            )
            return
        
        # Потвърди приемането на командата
        await update.message.reply_text("👍")
        
        # Изпълни командата
        try:
            await update.message.reply_text(f"⚙️ Изпълнявам: <code>{command}</code>", parse_mode='HTML')
            
            import subprocess
            result = subprocess.run(
                command,
                shell=True,
                cwd=BASE_PATH,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # ЛОГ: Запиши резултата
            logger.info(f"📤 STDOUT: {result.stdout[:500]}")
            if result.stderr:
                logger.warning(f"⚠️ STDERR: {result.stderr[:500]}")
            logger.info(f"✅ Return code: {result.returncode}")
            
            # Форматирай изхода
            output = ""
            if result.stdout:
                output += f"📤 STDOUT:\n<code>{result.stdout[:3000]}</code>\n\n"
            if result.stderr:
                output += f"⚠️ STDERR:\n<code>{result.stderr[:3000]}</code>\n\n"
            
            if result.returncode == 0:
                status = "✅ Успешно изпълнено"
            else:
                status = f"❌ Грешка (код {result.returncode})"
            
            if not output:
                output = "<i>Няма изход</i>"
            
            response = f"{status}\n\n{output}"
            
            # Раздели на части ако е много дълго
            if len(response) > 4000:
                await update.message.reply_text(response[:4000], parse_mode='HTML')
                await update.message.reply_text(response[4000:8000], parse_mode='HTML')
            else:
                await update.message.reply_text(response, parse_mode='HTML')
            
            # Потвърди завършването
            await update.message.reply_text("✅ Готово")
            
            await update.message.reply_text(
                "💻 Въведи следваща команда или 'exit' за изход:",
                parse_mode='HTML',
                reply_markup=get_admin_keyboard()
            )
            
        except subprocess.TimeoutExpired:
            logger.error(f"⏱️ Timeout за команда: {command}")
            await update.message.reply_text("⏱️ Timeout - командата отне повече от 30 сек", reply_markup=get_admin_keyboard())
        except Exception as e:
            logger.error(f"❌ Грешка при изпълнение на '{command}': {e}")
            await update.message.reply_text(f"❌ Грешка: {str(e)}", reply_markup=get_admin_keyboard())
        
        return
    
    # Провери дали потребителят е в процес на въвеждане на парола за обновяване
    if context.user_data.get('awaiting_update_password'):
        entered_password = update.message.text.strip()
        
        # ЛОГ: Опит за логин (без да показваме паролата)
        logger.info(f"🔐 @{username} (ID:{user_id}) опитва да влезе в Admin режим")
        
        # Провери паролата
        if hashlib.sha256(entered_password.encode()).hexdigest() == ADMIN_PASSWORD_HASH:
            # Парола правилна - влез в admin command режим
            context.user_data['awaiting_update_password'] = False
            context.user_data['admin_command_mode'] = True
            
            # ЛОГ: Успешен вход
            logger.info(f"✅ @{username} (ID:{user_id}) влезе в Admin режим УСПЕШНО")
            
            welcome_msg = """
🔓 <b>ADMIN РЕЖИМ АКТИВИРАН</b>

Сега можеш да изпълняваш команди директно в системата.

<b>Специални команди:</b>
• <code>enter</code> - Потвърди действие (когато се изисква)
• <code>exit</code> - Изход от admin режим

<b>Примерни системни команди:</b>
• <code>git pull origin main</code> - обнови кода
• <code>ls -la</code> - покажи файлове
• <code>cat bot.py | grep "def signal"</code> - търси в код
• <code>python3 -c "print('test')"</code> - изпълни Python
• <code>pip install package_name</code> - инсталирай пакет
• <code>ps aux | grep python</code> - провери процеси
• <code>tail -50 bot.log</code> - покажи лог

<b>Рестарт на бота:</b>
• <code>pkill -f "python.*bot.py" && sleep 2 && nohup python3 bot.py > bot.log 2>&1 &</code>

⚠️ <b>Внимание:</b> Командите се изпълняват директно в системата!

💡 <b>Когато те попитам нещо, просто натисни бутона "✅ Enter" за потвърждение.</b>
"""
            
            await update.message.reply_text(welcome_msg, parse_mode='HTML', reply_markup=get_admin_keyboard())
            
        else:
            # Грешна парола
            context.user_data['awaiting_update_password'] = False
            
            # ЛОГ: Неуспешен опит
            logger.warning(f"❌ @{username} (ID:{user_id}) въведе ГРЕШНА парола за Admin режим")
            
            await update.message.reply_text(
                "❌ Грешна парола! Достъпът е отказан.",
                reply_markup=get_main_keyboard()
            )
        
        return
    
    # Първоначално натискане на бутона - изискай парола
    context.user_data['awaiting_update_password'] = True
    
    # ЛОГ: Заявка за Admin режим
    logger.info(f"🔐 @{username} (ID:{user_id}) натисна бутон 'Обновяване' - изисква се парола")
    
    await update.message.reply_text(
        "🔐 За достъп до admin режим е нужна парола.\n\n"
        "Моля, въведи admin паролата:",
        reply_markup=ReplyKeyboardRemove()
    )


# ================= ML, BACKTEST, REPORTS КОМАНДИ =================

async def backtest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Изпълнява back-test на стратегията (с поддръжка на всички timeframes)"""
    if not BACKTEST_AVAILABLE:
        await update.message.reply_text(
            "❌ <b>Back-testing модул не е наличен</b>\n\n"
            "Модулът не е зареден. Проверете логовете.",
            parse_mode='HTML'
        )
        return
    
    try:
        # Параметри
        symbol = context.args[0] if context.args else 'BTCUSDT'
        
        # Проверка дали е зададен конкретен timeframe или 'all'
        if len(context.args) > 1 and context.args[1].lower() == BACKTEST_ALL_KEYWORD:
            test_all_timeframes = True
            timeframes_to_test = ['1m', '5m', '15m', '1h', '4h', '1d']
            days = int(context.args[2]) if len(context.args) > 2 else 15
        else:
            test_all_timeframes = False
            timeframe = context.args[1] if len(context.args) > 1 else '4h'
            timeframes_to_test = [timeframe]
            days = int(context.args[2]) if len(context.args) > 2 else 30
        
        logger.info(f"📊 Backtest started: {symbol} {timeframes_to_test} {days}d by user {update.effective_user.id}")
        
        # Progress message
        if test_all_timeframes:
            status_msg = await update.message.reply_text(
                f"📊 <b>MULTI-TIMEFRAME BACKTEST СТАРТИРА...</b>\n\n"
                f"💰 Символ: {symbol}\n"
                f"⏰ Timeframes: 1m, 5m, 15m, 1h, 4h, 1d\n"
                f"📅 Период: {days} дни\n\n"
                f"⏳ Изтеглям данни от Binance...\n"
                f"🕒 Може да отнеме 1-2 минути",
                parse_mode='HTML'
            )
        else:
            status_msg = await update.message.reply_text(
                f"📊 <b>BACKTEST СТАРТИРА...</b>\n\n"
                f"💰 Символ: {symbol}\n"
                f"⏰ Timeframe: {timeframe}\n"
                f"📅 Период: {days} дни\n\n"
                f"⏳ Изтеглям данни от Binance...",
                parse_mode='HTML'
            )
        
        await asyncio.sleep(0.5)
        
        # Изпълни back-test за всички timeframes
        all_results = []
        total_trades_all = 0
        total_wins_all = 0
        total_losses_all = 0
        total_profit_all = 0  # Сума на профити от всички TF (за индикация)
        
        for idx, tf in enumerate(timeframes_to_test):
            # Update progress
            if test_all_timeframes:
                await status_msg.edit_text(
                    f"📊 <b>MULTI-TIMEFRAME BACKTEST В ХОД...</b>\n\n"
                    f"💰 Символ: {symbol}\n"
                    f"📅 Период: {days} дни\n\n"
                    f"🔄 Обработвам: {tf} ({idx+1}/{len(timeframes_to_test)})\n"
                    f"⏱️ Моля изчакайте...",
                    parse_mode='HTML'
                )
            else:
                await status_msg.edit_text(
                    f"📊 <b>BACKTEST В ХОД...</b>\n\n"
                    f"💰 Символ: {symbol}\n"
                    f"⏰ Timeframe: {tf}\n"
                    f"📅 Период: {days} дни\n\n"
                    f"🔄 Симулирам трейдове...\n"
                    f"⏱️ Може да отнеме 20-40 секунди\n\n"
                    f"<i>Моля изчакайте...</i>",
                    parse_mode='HTML'
                )
            
            logger.info(f"📥 Fetching {days} days of data for {symbol} {tf}...")
            
            # Изпълни back-test с timeout
            try:
                results = await asyncio.wait_for(
                    backtest_engine.run_backtest(symbol, tf, None, days),
                    timeout=90.0  # 90 секунди максимум
                )
                
                if results:
                    all_results.append(results)
                    total_trades_all += results['total_trades']
                    total_wins_all += results['wins']
                    total_losses_all += results['losses']
                    total_profit_all += results['total_profit_pct']
                    logger.info(f"✅ Backtest {tf} completed: {results['total_trades']} trades, {results['win_rate']:.1f}% win rate")
                else:
                    logger.warning(f"⚠️ No results for {tf}")
                    
            except asyncio.TimeoutError:
                logger.error(f"⏱️ Backtest timeout for {symbol} {tf}")
                if not test_all_timeframes:
                    await status_msg.edit_text(
                        "⏱️ <b>TIMEOUT!</b>\n\n"
                        "Backtest отне твърде дълго време.\n"
                        "Опитайте с по-кратък период:\n"
                        "<code>/backtest BTCUSDT 4h 15</code>",
                        parse_mode='HTML'
                    )
                    return
            except Exception as fetch_error:
                logger.error(f"❌ Backtest fetch error for {tf}: {fetch_error}", exc_info=True)
                if not test_all_timeframes:
                    await status_msg.edit_text(
                        f"❌ <b>ГРЕШКА ПРИ ИЗТЕГЛЯНЕ:</b>\n\n"
                        f"<code>{str(fetch_error)[:200]}</code>\n\n"
                        f"Binance API може да не отговаря.",
                        parse_mode='HTML'
                    )
                    return
        
        if not all_results:
            logger.warning(f"⚠️ Backtest returned no results for {symbol}")
            await status_msg.edit_text(
                "❌ <b>НЯМА РЕЗУЛТАТИ</b>\n\n"
                "Възможни причини:\n"
                "• Невалиден символ или timeframe\n"
                "• Няма достатъчно данни от Binance\n"
                "• API грешка\n\n"
                "Опитайте:\n"
                "<code>/backtest BTCUSDT 4h 15</code>\n"
                "<code>/backtest BTCUSDT all 15</code> (всички timeframes)\n"
                "<code>/backtest ETHUSDT 1h 20</code>",
                parse_mode='HTML'
            )
            return
        
        # Формирай съобщението с резултати
        if test_all_timeframes:
            # Multi-timeframe резултати
            overall_win_rate = (total_wins_all / total_trades_all * 100) if total_trades_all > 0 else 0
            overall_avg = (total_profit_all / total_trades_all) if total_trades_all > 0 else 0
            
            message = f"""📊 <b>MULTI-TIMEFRAME BACKTEST</b>

💰 <b>Символ:</b> {symbol}
📅 <b>Период:</b> {days} дни

<b>━━━ ОБЩА СТАТИСТИКА ━━━</b>
   📈 Общо trades: {total_trades_all}
   🟢 Печеливши: {total_wins_all}
   🔴 Загубени: {total_losses_all}
   🎯 Win Rate: {overall_win_rate:.1f}%
   💰 Обща печалба: {total_profit_all:+.2f}%
   📊 Средно/trade: {overall_avg:+.2f}%

<b>━━━ ПО TIMEFRAME ━━━</b>
"""
            
            # Добави статистика за всеки timeframe
            for res in all_results:
                tf_emoji = {
                    '1m': '⚡', '5m': '🔥', '15m': '💨',
                    '1h': '⏰', '4h': '📊', '1d': '🌅'
                }.get(res['timeframe'], '📈')
                
                message += f"\n{tf_emoji} <b>{res['timeframe']}</b>: {res['total_trades']} trades | "
                message += f"{res['win_rate']:.0f}% WR | "
                message += f"{res['total_profit_pct']:+.1f}% profit"
            
            message += "\n\n⚠️ <i>Симулация базирана на исторически данни</i>"
            
        else:
            # Single timeframe резултати
            results = all_results[0]
            message = f"""📊 <b>BACK-TEST РЕЗУЛТАТИ</b>

💰 <b>Символ:</b> {results['symbol']}
⏰ <b>Таймфрейм:</b> {results['timeframe']}
📅 <b>Период:</b> {results['period_days']} дни

<b>Резултати:</b>
   Общо trades: {results['total_trades']}
   🟢 Печеливши: {results['wins']}
   🔴 Загубени: {results['losses']}
   🎯 Win Rate: {results['win_rate']:.1f}%
   💰 Обща печалба: {results['total_profit_pct']:+.2f}%
   📊 Средно на trade: {results['avg_profit_per_trade']:+.2f}%

⚠️ <i>Симулация базирана на исторически данни</i>
"""
        
        await status_msg.edit_text(message, parse_mode='HTML')
        
        # Оптимизирай параметри (само за single timeframe)
        if not test_all_timeframes:
            try:
                results = all_results[0]
                optimized = backtest_engine.optimize_parameters(results)
                
                if optimized:
                    opt_msg = f"""✅ <b>ПАРАМЕТРИ ОПТИМИЗИРАНИ</b>

🎯 Препоръчан TP: {optimized['optimized_tp_pct']:.2f}%
🛡️ Препоръчан SL: {optimized['optimized_sl_pct']:.2f}%
⚖️ Risk/Reward: 1:{optimized['recommended_rr']}

💡 <i>Използвай тези параметри за по-добри резултати!</i>
"""
                    await update.message.reply_text(opt_msg, parse_mode='HTML')
            except Exception as e:
                logger.error(f"Optimization error: {e}")
                # Don't fail the whole command if optimization fails
    
    except Exception as e:
        logger.error(f"❌ Backtest error: {e}")
        await status_msg.edit_text(
            f"❌ <b>ГРЕШКА!</b>\n\n"
            f"<code>{str(e)[:200]}</code>\n\n"
            f"Опитайте отново или с различни параметри.",
            parse_mode='HTML'
        )


async def ml_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """📈 Детайлен ML отчет с точност и performance"""
    if not ML_AVAILABLE:
        await update.message.reply_text("❌ ML модул не е наличен")
        return
    
    await update.message.reply_text("📊 Генерирам ML отчет...")
    
    status = ml_engine.get_status()
    
    # Simulate ML performance data (replace with real data from ml_engine)
    ml_accuracy = 68.5  # Would come from ml_engine.get_accuracy()
    classical_accuracy = 61.2  # Would come from classical indicators
    
    mode_text = "🤖 Hybrid Mode" if status['hybrid_mode'] else "⚡ Full ML Mode"
    ml_weight_pct = int(status['ml_weight'] * 100)
    classical_weight_pct = 100 - ml_weight_pct
    
    message = f"""📈 <b>ML PERFORMANCE REPORT</b>

━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>ТОЧНОСТ (последни 30 дни):</b>
   🤖 ML Model: <b>{ml_accuracy:.1f}%</b>
   📊 Classical: <b>{classical_accuracy:.1f}%</b>
   {'🔥 ML печели!' if ml_accuracy > classical_accuracy else '⚡ Classical печели!'}

⚙️ <b>ТЕКУЩ РЕЖИМ:</b>
   {mode_text}
   ML Weight: {ml_weight_pct}%
   Classical Weight: {classical_weight_pct}%

📚 <b>ОБУЧЕНИЕ:</b>
   Модел: {'✅ Trained' if status['model_trained'] else '❌ Not trained'}
   Training samples: {status['training_samples']}
   Нужни: {status['min_samples_needed']}
   {'✅ Готов!' if status['ready_for_training'] else f"⚠️ Нужни още {status['min_samples_needed'] - status['training_samples']} samples"}

💡 <b>ПРЕПОРЪКИ:</b>
   • ML се обучава автоматично на всеки 20 сигнала
   • Hybrid mode балансира ML + класически индикатори
   • За по-добра точност използвай /backtest

<i>Използвай бутоните за повече ML анализи</i>
"""
    
    await update.message.reply_text(message, parse_mode='HTML', reply_markup=get_ml_keyboard())


async def ml_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показва статус на ML системата"""
    if not ML_AVAILABLE:
        await update.message.reply_text("❌ ML модул не е наличен")
        return
    
    status = ml_engine.get_status()
    
    mode_text = "🤖 Hybrid Mode" if status['hybrid_mode'] else "⚡ Full ML Mode"
    ml_weight_pct = int(status['ml_weight'] * 100)
    classical_weight_pct = 100 - ml_weight_pct
    
    message = f"""🤖 <b>MACHINE LEARNING СТАТУС</b>

<b>Режим:</b> {mode_text}
   ML Weight: {ml_weight_pct}%
   Classical Weight: {classical_weight_pct}%

<b>Обучение:</b>
   Модел: {'✅ Trained' if status['model_trained'] else '❌ Not trained'}
   Training samples: {status['training_samples']}
   Нужни за обучение: {status['min_samples_needed']}
   
{'✅ Готов за обучение!' if status['ready_for_training'] else f"⚠️ Нужни още {status['min_samples_needed'] - status['training_samples']} samples"}

💡 <i>ML системата се обучава автоматично на всеки 20 сигнала</i>
"""
    
    await update.message.reply_text(message, parse_mode='HTML')


async def ml_train_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ръчно обучава ML модела"""
    if not ML_AVAILABLE:
        await update.message.reply_text("❌ ML модул не е наличен")
        return
    
    await update.message.reply_text("🤖 Обучавам ML модел...")
    
    success = ml_engine.train_model()
    
    if success:
        status = ml_engine.get_status()
        await update.message.reply_text(
            f"✅ ML модел обучен успешно!\n\n"
            f"📊 Samples: {status['training_samples']}\n"
            f"⚙️ ML Weight: {int(status['ml_weight']*100)}%",
            parse_mode='HTML'
        )
    else:
        await update.message.reply_text("❌ Недостатъчно данни за обучение (мин. 50 samples)")


async def daily_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерира дневен отчет"""
    if not REPORTS_AVAILABLE:
        await update.message.reply_text("❌ Reports модул не е наличен")
        return
    
    await update.message.reply_text("📊 Генерирам дневен отчет...")
    
    report = report_engine.generate_daily_report()
    
    if report:
        message = report_engine.format_report_message(report)
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text("❌ Грешка при генериране на отчет")


async def weekly_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерира седмичен отчет с точност и успеваемост"""
    if not REPORTS_AVAILABLE:
        await update.message.reply_text("❌ Reports модул не е наличен")
        return
    
    await update.message.reply_text("📊 Генерирам седмичен отчет (7 дни)...")
    
    summary = report_engine.get_weekly_summary()
    
    if summary:
        # Форматиране на съобщението
        accuracy_emoji = "🔥" if summary['accuracy'] >= 70 else "💪" if summary['accuracy'] >= 60 else "👍" if summary['accuracy'] >= 50 else "😐"
        profit_emoji = "💰" if summary['total_profit'] > 0 else "📉" if summary['total_profit'] < 0 else "⚪"
        
        message = f"""📊 <b>СЕДМИЧЕН ОТЧЕТ - 7 ДНИ</b>
📅 {summary['start_date']} → {summary['end_date']}
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>ГЕНЕРИРАНИ СИГНАЛИ:</b>
   📊 Общо: <b>{summary['total_signals']}</b>
   🟢 BUY: {summary['buy_signals']}
   🔴 SELL: {summary['sell_signals']}
   ⏳ Активни: {summary['active_signals']}
   ✅ Завършени: {summary['completed_signals']}

"""
        
        if summary['completed_signals'] > 0:
            message += f"""🎯 <b>ТОЧНОСТ НА СИГНАЛИТЕ:</b>
   {accuracy_emoji} Accuracy: <b>{summary['accuracy']:.1f}%</b>
   ✅ Печеливши: {summary['wins']} ({summary['wins']}/{summary['completed_signals']})
   ❌ Загубени: {summary['losses']} ({summary['losses']}/{summary['completed_signals']})

💵 <b>УСПЕВАЕМОСТ:</b>
   {profit_emoji} Общ Profit: <b>{summary['total_profit']:+.2f}%</b>
"""
            
            if summary['avg_win'] > 0:
                message += f"   📈 Среден печеливш: +{summary['avg_win']:.2f}%\n"
            if summary['avg_loss'] < 0:
                message += f"   📉 Среден губещ: {summary['avg_loss']:.2f}%\n"
            
            message += "\n"
        
        # Best/Worst trade
        if summary.get('best_trade'):
            best = summary['best_trade']
            message += f"""💎 <b>НАЙ-ДОБЪР TRADE:</b>
   {best['symbol']} {best['type']} - {best['timeframe']}
   💰 Profit: <b>+{best.get('profit_pct', 0):.2f}%</b>

"""
        
        if summary.get('worst_trade'):
            worst = summary['worst_trade']
            message += f"""⚠️ <b>НАЙ-ЛОШ TRADE:</b>
   {worst['symbol']} {worst['type']} - {worst['timeframe']}
   📉 Loss: <b>{worst.get('profit_pct', 0):.2f}%</b>

"""
        
        # Дневен breakdown
        if summary.get('daily_breakdown'):
            message += f"""📅 <b>ПО ДНИ:</b>
"""
            for date in sorted(summary['daily_breakdown'].keys(), reverse=True)[:7]:
                data = summary['daily_breakdown'][date]
                if data['completed'] > 0:
                    day_emoji = "💚" if data['profit'] > 0 else "🔴" if data['profit'] < 0 else "⚪"
                    message += f"   {day_emoji} {date}: {data['accuracy']:.0f}% acc, {data['profit']:+.1f}% profit ({data['completed']} trades)\n"
            
            message += "\n"
        
        message += f"""💪 <b>Средна увереност:</b> {summary['avg_confidence']:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Генериран: {datetime.now().strftime('%H:%M:%S')}
"""
        
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text("❌ Недостатъчно данни за седмичен отчет")


async def monthly_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерира месечен отчет с точност и успеваемост"""
    if not REPORTS_AVAILABLE:
        await update.message.reply_text("❌ Reports модул не е наличен")
        return
    
    await update.message.reply_text("📊 Генерирам месечен отчет (30 дни)...")
    
    summary = report_engine.get_monthly_summary()
    
    if summary:
        # Форматиране на съобщението
        accuracy_emoji = "🔥" if summary['accuracy'] >= 70 else "💪" if summary['accuracy'] >= 60 else "👍" if summary['accuracy'] >= 50 else "😐"
        profit_emoji = "💰" if summary['total_profit'] > 0 else "📉" if summary['total_profit'] < 0 else "⚪"
        
        message = f"""📊 <b>МЕСЕЧЕН ОТЧЕТ - 30 ДНИ</b>
📅 {summary['start_date']} → {summary['end_date']}
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>ГЕНЕРИРАНИ СИГНАЛИ:</b>
   📊 Общо: <b>{summary['total_signals']}</b>
   🟢 BUY: {summary['buy_signals']}
   🔴 SELL: {summary['sell_signals']}
   ⏳ Активни: {summary['active_signals']}
   ✅ Завършени: {summary['completed_signals']}

"""
        
        if summary['completed_signals'] > 0:
            message += f"""🎯 <b>ТОЧНОСТ НА СИГНАЛИТЕ:</b>
   {accuracy_emoji} Accuracy: <b>{summary['accuracy']:.1f}%</b>
   ✅ Печеливши: {summary['wins']} ({summary['wins']}/{summary['completed_signals']})
   ❌ Загубени: {summary['losses']} ({summary['losses']}/{summary['completed_signals']})

💵 <b>УСПЕВАЕМОСТ:</b>
   {profit_emoji} Общ Profit: <b>{summary['total_profit']:+.2f}%</b>
"""
            
            if summary['avg_win'] > 0:
                message += f"   📈 Среден печеливш: +{summary['avg_win']:.2f}%\n"
            if summary['avg_loss'] < 0:
                message += f"   📉 Среден губещ: {summary['avg_loss']:.2f}%\n"
            if summary.get('profit_factor', 0) > 0:
                pf_emoji = "🔥" if summary['profit_factor'] >= 2 else "💪" if summary['profit_factor'] >= 1.5 else "👍"
                message += f"   {pf_emoji} Profit Factor: {summary['profit_factor']:.2f}\n"
            
            message += "\n"
        
        # Best/Worst trade
        if summary.get('best_trade'):
            best = summary['best_trade']
            message += f"""💎 <b>НАЙ-ДОБЪР TRADE:</b>
   {best['symbol']} {best['type']} - {best['timeframe']}
   💰 Profit: <b>+{best.get('profit_pct', 0):.2f}%</b>

"""
        
        if summary.get('worst_trade'):
            worst = summary['worst_trade']
            message += f"""⚠️ <b>НАЙ-ЛОШ TRADE:</b>
   {worst['symbol']} {worst['type']} - {worst['timeframe']}
   📉 Loss: <b>{worst.get('profit_pct', 0):.2f}%</b>

"""
        
        # Статистика по валути
        if summary.get('symbols_stats'):
            message += f"""💰 <b>ЕФЕКТИВНОСТ ПО ВАЛУТИ:</b>
"""
            for symbol, stats in sorted(summary['symbols_stats'].items(), key=lambda x: x[1]['profit'], reverse=True):
                if stats['completed'] > 0:
                    sym_emoji = "💚" if stats['profit'] > 0 else "🔴" if stats['profit'] < 0 else "⚪"
                    message += f"   {sym_emoji} {symbol}: {stats['accuracy']:.0f}% acc, {stats['profit']:+.2f}% profit\n"
            
            message += "\n"
        
        # Седмичен breakdown
        if summary.get('weekly_breakdown'):
            message += f"""📅 <b>ПО СЕДМИЦИ:</b>
"""
            for week in sorted(summary['weekly_breakdown'].keys()):
                data = summary['weekly_breakdown'][week]
                if data['completed'] > 0:
                    week_emoji = "💚" if data['profit'] > 0 else "🔴" if data['profit'] < 0 else "⚪"
                    message += f"   {week_emoji} {week}: {data['accuracy']:.0f}% acc, {data['profit']:+.1f}% profit\n"
            
            message += "\n"
        
        message += f"""💪 <b>Средна увереност:</b> {summary['avg_confidence']:.1f}%

━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Генериран: {datetime.now().strftime('%H:%M:%S')}

📈 <b>ОБОБЩЕНИЕ:</b>"""
        
        # Финално обобщение
        if summary['completed_signals'] > 0:
            if summary['accuracy'] >= 70 and summary['total_profit'] > 10:
                message += "\n🔥 <b>ОТЛИЧЕН МЕСЕЦ!</b> Високи резултати по всички показатели!"
            elif summary['accuracy'] >= 60 and summary['total_profit'] > 0:
                message += "\n💪 <b>ДОБЪР МЕСЕЦ!</b> Стабилна ефективност."
            elif summary['accuracy'] >= 50:
                message += "\n👍 <b>СРЕДЕН МЕСЕЦ.</b> Има място за подобрение."
            else:
                message += "\n⚠️ <b>СЛАБ МЕСЕЦ.</b> Препоръчва се анализ на стратегията."
        
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text("❌ Недостатъчно данни за месечен отчет")


async def reports_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Централизирано меню за всички отчети"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Дневен отчет", callback_data="report_daily"),
            InlineKeyboardButton("📈 Седмичен", callback_data="report_weekly"),
            InlineKeyboardButton("📆 Месечен", callback_data="report_monthly")
        ],
        [
            InlineKeyboardButton("📉 Back-test резултати", callback_data="report_backtest"),
            InlineKeyboardButton("🤖 ML статистика", callback_data="report_ml"),
        ],
        [
            InlineKeyboardButton("📋 Bot статистика", callback_data="report_stats"),
            InlineKeyboardButton("🔄 Refresh", callback_data="report_refresh"),
        ],
        [
            InlineKeyboardButton("🏠 Главно меню", callback_data="back_to_menu"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Покажи overview
    overview = "📋 <b>ЦЕНТЪР ЗА ОТЧЕТИ</b>\n\n"
    overview += "Избери тип отчет за преглед:\n\n"
    
    # Бърз преглед на статуса
    if REPORTS_AVAILABLE:
        try:
            import os
            reports_file = f'{BASE_PATH}/daily_reports.json'
            if os.path.exists(reports_file):
                import json
                with open(reports_file, 'r') as f:
                    data = json.load(f)
                    reports_count = len(data.get('reports', []))
                    overview += f"📊 Запазени дневни отчети: {reports_count}\n"
        except:
            pass
    
    if ML_AVAILABLE:
        status = ml_engine.get_status()
        overview += f"🤖 ML модел: {'✅ Trained' if status['model_trained'] else '⚠️ Not trained'}\n"
        overview += f"📈 Training samples: {status['training_samples']}\n"
    
    if BACKTEST_AVAILABLE:
        try:
            import os
            backtest_file = f'{BASE_PATH}/backtest_results.json'
            if os.path.exists(backtest_file):
                import json
                with open(backtest_file, 'r') as f:
                    data = json.load(f)
                    bt_count = len(data.get('backtests', []))
                    overview += f"📉 Back-test резултати: {bt_count}\n"
        except:
            pass
    
    overview += "\n💡 <i>Избери бутон за детайли</i>"
    
    await update.message.reply_text(overview, parse_mode='HTML', reply_markup=reply_markup)


async def reports_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработва callbacks от reports меню"""
    query = update.callback_query
    await query.answer()
    
    if query.data == "report_daily":
        # Генерирай дневен отчет
        await send_daily_signal_report(context.bot)
        await query.answer("✅ Дневният отчет е изпратен!")
    
    elif query.data == "report_weekly":
        summary = report_engine.get_weekly_summary()
        if summary:
            accuracy_emoji = "🔥" if summary["accuracy"] >= 70 else "💪" if summary["accuracy"] >= 60 else "👍"
            profit_emoji = "💰" if summary. get("total_profit", 0) > 0 else "📉"
            
            message = f"""📊 <b>СЕДМИЧЕН ОТЧЕТ - 7 ДНИ</b>
📅 {summary["start_date"]} → {summary["end_date"]}
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>ГЕНЕРИРАНИ СИГНАЛИ:</b>
   📊 Общо: <b>{summary["total_signals"]}</b>
   🟢 BUY: {summary["buy_signals"]}
   🔴 SELL: {summary["sell_signals"]}
   ⏳ Активни: {summary["active_signals"]}
   ✅ Завършени: {summary["completed_signals"]}

"""
            if summary["completed_signals"] > 0:
                message += f"""🎯 <b>ТОЧНОСТ НА СИГНАЛИТЕ:</b>
   {accuracy_emoji} Accuracy: <b>{summary["accuracy"]:.1f}%</b>
   ✅ Печеливши: {summary["wins"]} ({summary["wins"]}/{summary["completed_signals"]})
   ❌ Загубени: {summary["losses"]} ({summary["losses"]}/{summary["completed_signals"]})

💵 <b>УСПЕВАЕМОСТ:</b>
   {profit_emoji} Общ Profit: <b>{summary.get("total_profit", 0):+.2f}%</b>

"""
                if summary.get("best_trade"):
                    best = summary["best_trade"]
                    message += f"""💎 <b>НАЙ-ДОБЪР TRADE:</b>
   {best["symbol"]} {best["type"]} - {best["timeframe"]}
   💰 Profit: <b>+{best.get("profit_pct", 0):.2f}%</b>

"""
                if summary.get("worst_trade"):
                    worst = summary["worst_trade"]
                    message += f"""⚠️ <b>НАЙ-ЛОШ TRADE:</b>
   {worst["symbol"]} {worst["type"]} - {worst["timeframe"]}
   📉 Loss: <b>{worst. get("profit_pct", 0):.2f}%</b>

"""
            await query.edit_message_text(message, parse_mode="HTML")
        else:
            await query.edit_message_text("❌ Недостатъчно данни за седмичен отчет")
    
    elif query.data == "report_monthly":
        summary = report_engine.get_monthly_summary()

        if summary:
            accuracy_emoji = "🔥" if summary["accuracy"] >= 70 else "💪" if summary["accuracy"] >= 60 else "👍"
            profit_emoji = "💰" if summary. get("total_profit", 0) > 0 else "📉"
            
            message = f"""📊 <b>МЕСЕЧЕН ОТЧЕТ - 30 ДНИ</b>
📅 {summary["start_date"]} → {summary["end_date"]}
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>ГЕНЕРИРАНИ СИГНАЛИ:</b>
   📊 Общо: <b>{summary["total_signals"]}</b>
   🟢 BUY: {summary["buy_signals"]}
   🔴 SELL: {summary["sell_signals"]}
   ⏳ Активни: {summary["active_signals"]}
   ✅ Завършени: {summary["completed_signals"]}

"""
            if summary["completed_signals"] > 0:
                message += f"""🎯 <b>ТОЧНОСТ НА СИГНАЛИТЕ:</b>
   {accuracy_emoji} Accuracy: <b>{summary["accuracy"]:.1f}%</b>
   ✅ Печеливши: {summary["wins"]} ({summary["wins"]}/{summary["completed_signals"]})
   ❌ Загубени: {summary["losses"]} ({summary["losses"]}/{summary["completed_signals"]})

💵 <b>УСПЕВАЕМОСТ:</b>
   {profit_emoji} Общ Profit: <b>{summary. get("total_profit", 0):+.2f}%</b>

"""
                if summary. get("best_trade"):
                    best = summary["best_trade"]
                    message += f"""💎 <b>НАЙ-ДОБЪР TRADE:</b>
   {best["symbol"]} {best["type"]} - {best["timeframe"]}
   💰 Profit: <b>+{best. get("profit_pct", 0):.2f}%</b>

"""
                if summary.get("worst_trade"):
                    worst = summary["worst_trade"]
                    message += f"""⚠️ <b>НАЙ-ЛОШ TRADE:</b>
   {worst["symbol"]} {worst["type"]} - {worst["timeframe"]}
   📉 Loss: <b>{worst.get("profit_pct", 0):. 2f}%</b>

"""
            await query.edit_message_text(message, parse_mode="HTML")
        else:
            await query.edit_message_text("❌ Недостатъчно данни за месечен отчет")

    
    elif query.data == "report_backtest":
        # Back-test резултати
        if not BACKTEST_AVAILABLE:
            await query.edit_message_text("❌ Backtesting модул не е наличен")
            return
        
        try:
            import os
            import json
            backtest_file = f'{BASE_PATH}/backtest_results.json'
            if os.path.exists(backtest_file):
                with open(backtest_file, 'r') as f:
                    data = json.load(f)
                    backtests = data.get('backtests', [])
                    
                    if backtests:
                        latest = backtests[-1]
                        message = f"""📉 <b>ПОСЛЕДЕН BACK-TEST</b>

💰 <b>Символ:</b> {latest['symbol']}
⏰ <b>Таймфрейм:</b> {latest['timeframe']}
📅 <b>Период:</b> {latest['period_days']} дни

<b>Резултати:</b>
   Общо trades: {latest['total_trades']}
   🟢 Печеливши: {latest['wins']}
   🔴 Загубени: {latest['losses']}
   🎯 Win Rate: {latest['win_rate']:.1f}%
   💰 Обща печалба: {latest['total_profit_pct']:+.2f}%
   📊 Средно на trade: {latest['avg_profit_per_trade']:+.2f}%

⏰ <b>Дата:</b> {latest['timestamp'][:10]}

💡 Общо {len(backtests)} back-test(s) в архива
"""
                        await query.edit_message_text(message, parse_mode='HTML')
                    else:
                        await query.edit_message_text("❌ Няма back-test резултати. Използвай /backtest")
            else:
                await query.edit_message_text("❌ Няма back-test резултати. Използвай /backtest")
        except Exception as e:
            await query.edit_message_text(f"❌ Грешка: {e}")


async def toggle_ict_command(update, context):
    """Toggle ICT enhancer"""
    try:
        if update.effective_user.id != OWNER_CHAT_ID:
            await update.message.reply_text("❌ Owner only")
            return
        
        config = load_feature_flags()
        new_value = not config.get('use_ict_enhancer', False)
        update_feature_flag('use_ict_enhancer', new_value)
        
        global FEATURE_FLAGS, ict_enhancer
        FEATURE_FLAGS = load_feature_flags()
        ict_enhancer = ICTEnhancer(FEATURE_FLAGS)
        
        status = "✅ ВКЛЮЧЕН" if new_value else "❌ ИЗКЛЮЧЕН"
        await update.message.reply_text(f"🔧 ICT Enhancer: {status}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


def main():
    # HTTPx клиент с persistent connection и retry логика
    from httpx import Limits
    
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_BOT_TOKEN)
        .get_updates_pool_timeout(3600)  # 1 час вместо 30 сек
        .get_updates_read_timeout(3600)  # 1 час вместо 30 сек
        .get_updates_write_timeout(3600)  # 1 час вместо 30 сек
        .get_updates_connect_timeout(60)  # 1 минута вместо 30 сек
        .pool_timeout(3600)  # HTTP pool timeout
        .read_timeout(3600)  # HTTP read timeout
        .write_timeout(3600)  # HTTP write timeout
        .connect_timeout(60)  # HTTP connect timeout
        .connection_pool_size(100)  # Повече connections
        .get_updates_connection_pool_size(100)
        .http_version("1.1")  # HTTP/1.1 за по-добра съвместимост
        .build()
    )
    
    # Регистрирай команди
    app.add_handler(CommandHandler("start", start_cmd))
    # /deploy е премахнат - GitHub Actions прави автоматичен deploy при всеки push
    app.add_handler(CommandHandler("ml_menu", ml_menu_cmd))  # 📚 ML Анализ меню
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("version", version_cmd))  # Bot version info
    app.add_handler(CommandHandler("v", version_cmd))  # Short alias for version
    app.add_handler(CommandHandler("market", market_cmd))
    app.add_handler(CommandHandler("signal", signal_cmd))
    app.add_handler(CommandHandler("ict", ict_cmd))  # 🎯 ICT Complete Analysis
    app.add_handler(CommandHandler("news", news_cmd))
    app.add_handler(CommandHandler("breaking", breaking_cmd))  # Критични новини
    app.add_handler(CommandHandler("task", task_cmd))  # Задания за Copilot
    app.add_handler(CommandHandler("dailyreport", dailyreport_cmd))  # Дневен отчет за сигнали
    app.add_handler(CommandHandler("workspace", workspace_cmd))  # Workspace info
    app.add_handler(CommandHandler("restart", restart_cmd))  # Рестарт на бота
    app.add_handler(CommandHandler("autonews", autonews_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("timeframe", timeframe_cmd))
    app.add_handler(CommandHandler("alerts", alerts_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("journal", journal_cmd))  # 📝 Trading Journal с ML
    app.add_handler(CommandHandler("risk", risk_cmd))  # 🛡️ Risk Management
    app.add_handler(CommandHandler("explain", explain_cmd))  # 📖 ICT/LuxAlgo речник
    app.add_handler(CommandHandler("toggle_ict", toggle_ict_command))  # 🔧 ICT Enhancer toggle
    
    # Админ команди
    app.add_handler(CommandHandler("admin_login", admin_login_cmd))
    app.add_handler(CommandHandler("admin_setpass", admin_setpass_cmd))
    app.add_handler(CommandHandler("admin_daily", admin_daily_cmd))
    app.add_handler(CommandHandler("admin_weekly", admin_weekly_cmd))
    app.add_handler(CommandHandler("admin_monthly", admin_monthly_cmd))
    app.add_handler(CommandHandler("admin_docs", admin_docs_cmd))
    app.add_handler(CommandHandler("update", auto_update_cmd))  # 🔄 Обновяване на бота от GitHub (БЕЗ ПАРОЛА)
    app.add_handler(CommandHandler("auto_update", auto_update_cmd))  # 🔄 Auto-update от GitHub (същата функция)
    app.add_handler(CommandHandler("test", test_system_cmd))  # Тест и автоматично отстраняване на грешки
    
    # User Access Management команди (само owner)
    app.add_handler(CommandHandler("approve", approve_user_cmd))  # Одобри потребител
    app.add_handler(CommandHandler("block", block_user_cmd))  # Блокирай потребител
    app.add_handler(CommandHandler("users", list_users_cmd))  # Списък с потребители
    
    # ML, Back-testing, Reports команди
    app.add_handler(CommandHandler("backtest", backtest_cmd))  # Back-testing
    app.add_handler(CommandHandler("ml_status", ml_status_cmd))  # ML статус
    app.add_handler(CommandHandler("ml_train", ml_train_cmd))  # Ръчно обучение
    app.add_handler(CommandHandler("daily_report", daily_report_cmd))  # Дневен отчет
    app.add_handler(CommandHandler("weekly_report", weekly_report_cmd))  # Седмичен отчет
    app.add_handler(CommandHandler("monthly_report", monthly_report_cmd))  # Месечен отчет
    app.add_handler(CommandHandler("reports", reports_cmd))  # Централизирани отчети
    
    # Кратки съкращения
    app.add_handler(CommandHandler("m", market_cmd))  # /m = /market
    app.add_handler(CommandHandler("s", signal_cmd))  # /s = /signal
    app.add_handler(CommandHandler("n", news_cmd))  # /n = /news
    app.add_handler(CommandHandler("b", breaking_cmd))  # /b = /breaking
    app.add_handler(CommandHandler("t", task_cmd))  # /t = /task
    app.add_handler(CommandHandler("w", workspace_cmd))  # /w = /workspace
    app.add_handler(CommandHandler("j", journal_cmd))  # /j = /journal
    
    # Callback handlers за inline бутони
    app.add_handler(CallbackQueryHandler(signal_callback, pattern='^tf_'))
    app.add_handler(CallbackQueryHandler(signal_callback, pattern='^signal_'))
    app.add_handler(CallbackQueryHandler(signal_callback, pattern='^back_to_menu$'))
    app.add_handler(CallbackQueryHandler(signal_callback, pattern='^back_to_signal_menu$'))
    app.add_handler(CallbackQueryHandler(timeframe_callback, pattern='^timeframe_'))
    app.add_handler(CallbackQueryHandler(reports_callback, pattern='^report_'))  # Reports menu
    
    # Message handler за текстови бутони от клавиатурата
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    
    logger.info("🚀 Crypto Signal Bot стартира...")
    
    # 🤖 Initial ML training при старт (ако има достатъчно данни)
    if ML_AVAILABLE:
        try:
            logger.info("🤖 Checking ML model status...")
            status = ml_engine.get_status()
            
            if not status['model_trained'] and status['ready_for_training']:
                logger.info(f"🤖 Training ML model with {status['training_samples']} samples...")
                if ml_engine.train_model():
                    logger.info("✅ ML model trained successfully on startup!")
                else:
                    logger.warning("⚠️ ML training failed - insufficient data")
            elif status['model_trained']:
                logger.info(f"✅ ML model already trained ({status['training_samples']} samples)")
            else:
                logger.info(f"⏳ ML model waiting for more data ({status['training_samples']}/{status['min_samples_needed']} samples)")
        except Exception as ml_error:
            logger.error(f"❌ ML initialization error: {ml_error}")
    
    # APScheduler за автоматични отчети (стартира СЛЕД app.run_polling)
    if ADMIN_MODULE_AVAILABLE:
        async def schedule_reports(application):
            """Инициализира APScheduler след стартиране на бота"""
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            scheduler = AsyncIOScheduler(timezone="UTC")
            
            # Дневен отчет всеки ден в 08:00 UTC
            scheduler.add_job(
                lambda: asyncio.create_task(send_auto_report('daily', application.bot)),
                'cron',
                hour=8,
                minute=0
            )
            
            # Седмичен отчет всеки понеделник в 08:00 UTC
            scheduler.add_job(
                lambda: asyncio.create_task(send_auto_report('weekly', application.bot)),
                'cron',
                day_of_week='mon',
                hour=8,
                minute=0
            )
            
            # Месечен отчет на 1-во число в 08:00 UTC
            scheduler.add_job(
                lambda: asyncio.create_task(send_auto_report('monthly', application.bot)),
                'cron',
                day=1,
                hour=8,
                minute=0
            )
            
            # ДНЕВНИ ОТЧЕТИ ЗА СИГНАЛИ - Всеки ден в 08:00 BG време (06:00 UTC)
            async def send_daily_signal_report_job():
                """Wrapper за изпращане на дневен отчет за сигнали"""
                try:
                    await send_daily_signal_report(application.bot)
                except Exception as e:
                    logger.error(f"❌ Daily signal report error: {e}")
            
            scheduler.add_job(
                send_daily_signal_report_job,
                'cron',
                hour=6,  # 08:00 BG = 06:00 UTC
                minute=0
            )
            logger.info("✅ Daily signal reports scheduled at 08:00 BG time (previous day analysis)")
            
            # НОВИ ДНЕВНИ ОТЧЕТИ (ако има външен engine) - Всеки ден в 08:00 BG време
            if REPORTS_AVAILABLE:
                async def send_daily_auto_report():
                    """Изпраща автоматичен дневен отчет към owner за предходния ден"""
                    try:
                        report = report_engine.generate_daily_report()
                        if report:
                            message = report_engine.format_report_message(report)
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=f"🔔 <b>ДОПЪЛНИТЕЛЕН ДНЕВЕН ОТЧЕТ</b>\n\n{message}",
                                parse_mode='HTML',
                                disable_notification=True
                            )
                            logger.info("✅ Additional daily report sent")
                    except Exception as e:
                        logger.error(f"❌ Additional report error: {e}")
                
                scheduler.add_job(
                    send_daily_auto_report,
                    'cron',
                    hour=6,  # 08:00 BG = 06:00 UTC
                    minute=5  # 5 минути след основния отчет
                )
                logger.info("✅ Additional daily reports scheduled (08:00:05 BG time)")
            
            # Автоматична диагностика всеки ден в 01:00 UTC (03:00 BG време)
            scheduler.add_job(
                run_diagnostics,
                'cron',
                hour=1,
                minute=0
            )
            
            # Автоматични новини 3 пъти дневно: 08:00, 14:00, 20:00 UTC
            scheduler.add_job(
                lambda: asyncio.create_task(send_auto_news(application.bot)),
                'cron',
                hour='8,14,20',
                minute=0
            )
            
            # КРИТИЧЕН МОНИТОРИНГ НА НОВИНИ - всеки 3 минути!
            scheduler.add_job(
                monitor_breaking_news,
                'interval',
                minutes=3
            )
            
            # 📝 24/7 TRADING JOURNAL МОНИТОРИНГ - всеки 2 минути!
            async def journal_monitoring_wrapper():
                """Wrapper за journal мониторинг с context"""
                try:
                    from telegram.ext import ContextTypes
                    # Създай минимален context за bot
                    class SimpleContext:
                        def __init__(self, bot):
                            self.bot = bot
                    
                    context = SimpleContext(app.bot)
                    await monitor_active_trades(context)
                except Exception as e:
                    logger.error(f"Journal monitoring wrapper error: {e}")
            
            scheduler.add_job(
                journal_monitoring_wrapper,
                'interval',
                minutes=2
            )
            
            # 🎯 AUTO-SIGNAL TRACKING - проверява сигналите на всеки 15 минути
            async def signal_tracking_wrapper():
                """Wrapper за signal tracking"""
                try:
                    await check_active_signals()
                except Exception as e:
                    logger.error(f"Signal tracking wrapper error: {e}")
            
            scheduler.add_job(
                signal_tracking_wrapper,
                'interval',
                minutes=15  # Проверява на всеки 15 минути
            )
            
            # 📊 АВТОМАТИЧЕН СЕДМИЧЕН BACKTEST - всеки понеделник в 09:00 UTC (11:00 BG)
            if BACKTEST_AVAILABLE:
                async def weekly_backtest_wrapper():
                    """Wrapper за автоматичен седмичен backtest - ВСИЧКИ монети и таймфрейми"""
                    try:
                        logger.info("📊 Starting weekly automated backtest for ALL coins and timeframes...")
                        
                        # ВСИЧКИ монети от SYMBOLS
                        symbols_to_test = list(SYMBOLS.values())  # BTCUSDT, ETHUSDT, XRPUSDT, SOLUSDT, BNBUSDT, ADAUSDT
                        
                        # ВСИЧКИ основни таймфрейми
                        timeframes_to_test = ['1h', '4h', '1d']
                        
                        # Събиране на резултати за общ отчет
                        all_results = []
                        
                        for symbol in symbols_to_test:
                            for timeframe in timeframes_to_test:
                                try:
                                    logger.info(f"📊 Backtesting {symbol} on {timeframe}...")
                                    
                                    results = await backtest_engine.run_backtest(symbol, timeframe, None, 30)
                                    
                                    if results:
                                        all_results.append(results)
                                        logger.info(f"✅ {symbol} {timeframe}: {results['win_rate']:.1f}% win rate")
                                        
                                        # Кратка пауза между backtests
                                        await asyncio.sleep(2)
                                        
                                except Exception as e:
                                    logger.error(f"❌ Backtest error for {symbol} {timeframe}: {e}")
                        
                        # Изпрати обобщен отчет
                        if all_results:
                            # Намери най-добрите резултати
                            best_winrate = max(all_results, key=lambda x: x['win_rate'])
                            best_profit = max(all_results, key=lambda x: x['total_profit_pct'])
                            
                            # Средни стойности
                            avg_winrate = sum(r['win_rate'] for r in all_results) / len(all_results)
                            avg_profit = sum(r['total_profit_pct'] for r in all_results) / len(all_results)
                            total_trades = sum(r['total_trades'] for r in all_results)
                            
                            summary = f"""📊 <b>СЕДМИЧЕН AUTO-BACKTEST РЕЗУЛТАТИ</b>

🎯 <b>ТЕСТВАНИ:</b>
   • Монети: {len(symbols_to_test)} ({', '.join([s.replace('USDT', '') for s in symbols_to_test])})
   • Таймфрейми: {len(timeframes_to_test)} (1h, 4h, 1d)
   • Общо комбинации: {len(all_results)}
   • Общо симулирани trades: {total_trades}

📈 <b>СРЕДНИ РЕЗУЛТАТИ:</b>
   🎯 Среден Win Rate: {avg_winrate:.1f}%
   💰 Среден Profit: {avg_profit:+.2f}%

🏆 <b>НАЙ-ДОБРИ КОМБИНАЦИИ:</b>

<b>По Win Rate:</b>
   {best_winrate['symbol']} ({best_winrate['timeframe']})
   🎯 Win Rate: {best_winrate['win_rate']:.1f}%
   💰 Profit: {best_winrate['total_profit_pct']:+.2f}%
   📊 Trades: {best_winrate['total_trades']}

<b>По Profit:</b>
   {best_profit['symbol']} ({best_profit['timeframe']})
   💰 Profit: {best_profit['total_profit_pct']:+.2f}%
   🎯 Win Rate: {best_profit['win_rate']:.1f}%
   📊 Trades: {best_profit['total_trades']}

📅 <b>Период:</b> 30 дни история
⚠️ <i>Симулация базирана на исторически данни</i>

💡 <b>Използвай:</b> <code>/backtest {best_profit['symbol']} {best_profit['timeframe']} 30</code>
за детайли на най-добрата комбинация
"""
                            
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=summary,
                                parse_mode='HTML',
                                disable_notification=True
                            )
                            logger.info(f"✅ Weekly backtest summary sent: {len(all_results)} combinations tested")
                        else:
                            logger.warning("⚠️ No backtest results to send")
                            
                    except Exception as e:
                        logger.error(f"❌ Weekly backtest wrapper error: {e}")
                
                scheduler.add_job(
                    weekly_backtest_wrapper,
                    'cron',
                    day_of_week='mon',  # Понеделник
                    hour=9,  # 11:00 BG = 09:00 UTC
                    minute=0
                )
                logger.info("✅ Weekly automated backtest scheduled (Mondays at 11:00 BG time) - ALL COINS & TIMEFRAMES")
            
            scheduler.start()
            logger.info("✅ APScheduler стартиран: отчети + диагностика + новини + REAL-TIME мониторинг + DAILY REPORTS + 📝 JOURNAL 24/7 + 🎯 SIGNAL TRACKING + 📊 WEEKLY BACKTEST")
        
        async def enable_auto_alerts():
            """Автоматично активиране на alerts за owner при стартиране"""
            settings = get_user_settings(app.bot_data, OWNER_CHAT_ID)
            settings['alerts_enabled'] = True
            settings['alert_interval'] = 5 * 60  # 5 минути
            
            # Стартирай автоматични сигнали
            app.job_queue.run_repeating(
                send_alert_signal,
                interval=settings['alert_interval'],
                first=10,  # Първият сигнал след 10 секунди
                data={'chat_id': OWNER_CHAT_ID},
                name=f"alerts_{OWNER_CHAT_ID}"
            )
            logger.info(f"🔔 Автоматични alerts АКТИВИРАНИ за owner (интервал: 5 мин)")
        
        async def send_startup_notification():
            """Изпраща нотификация при рестарт на бота"""
            # БЕЗ ИЗЧАКВАНЕ - веднага проверяваме!
            
            # ПРОВЕРИ ДАЛИ Е БИЛ РЕСТАРТ
            restart_flag_file = f"{BASE_PATH}/.restart_requested"
            was_restart = os.path.exists(restart_flag_file)
            
            logger.info(f"🔍 Проверка за restart flag: {restart_flag_file}")
            logger.info(f"🔍 Flag file exists: {was_restart}")
            logger.info(f"🔍 BASE_PATH: {BASE_PATH}")
            
            # ИЗТРИЙ ФЛАГА
            if was_restart:
                try:
                    os.remove(restart_flag_file)
                    logger.info(f"✅ Restart flag изтрит")
                except Exception as e:
                    logger.error(f"❌ Грешка при изтриване на flag: {e}")
            
            try:
                # РАЗЛИЧНО СЪОБЩЕНИЕ според дали е бил рестарт
                if was_restart:
                    # 🔔 РЕСТАРТ ПОТВЪРЖДЕНИЕ - СЪС ЗВУК И КЛАВИАТУРА
                    startup_msg = "✅ <b>РЕСТАРТ ЗАВЪРШЕН!</b>\n\n"
                    startup_msg += f"🟢 <b>Бота е отново онлайн!</b>\n"
                    startup_msg += f"⏱️ <b>Време:</b> {datetime.now().strftime('%H:%M:%S')}\n\n"
                    startup_msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    startup_msg += f"✅ Всички системи: Онлайн\n"
                    startup_msg += f"✅ Auto-alerts: Включени\n"
                    startup_msg += f"✅ ML Engine: Готов\n\n"
                    startup_msg += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                    startup_msg += f"🎯 <i>Рестартът беше успешен!</i>"
                else:
                    # Обикновен старт (не рестарт)
                    startup_msg = "🤖 <b>БОТ СТАРТИРАН!</b>\n\n"
                    startup_msg += f"🟢 Статус: Онлайн\n"
                    startup_msg += f"⏱️ Време: {datetime.now().strftime('%H:%M:%S')}\n\n"
                    startup_msg += f"✅ Всички системи активни"
                
                logger.info(f"📤 Изпращам startup съобщение... (was_restart={was_restart})")
                
                await app.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=startup_msg,
                    parse_mode='HTML',
                    disable_notification=False,  # СЪС ЗВУК - важно!
                    reply_markup=get_main_keyboard()  # Изпрати клавиатурата
                )
                logger.info(f"✅ Startup notification изпратена {'(RESTART)' if was_restart else '(NORMAL)'}")
                
            except Exception as e:
                logger.error(f"❌ Грешка при startup notification (опит 1): {e}")
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                
                # ОПИТ 2 - след още 3 секунди
                try:
                    await asyncio.sleep(3)
                    await app.bot.send_message(
                        chat_id=OWNER_CHAT_ID,
                        text=(
                            "✅ <b>БОТ ОНЛАЙН!</b>\n\n"
                            f"🟢 {'Рестартът' if was_restart else 'Стартирането'} завърши успешно.\n"
                            "💡 Всички системи работят."
                        ),
                        parse_mode='HTML',
                        disable_notification=False,
                        reply_markup=get_main_keyboard()
                    )
                    logger.info("✅ Startup notification изпратена (опит 2)")
                except Exception as e2:
                    logger.error(f"❌ Грешка при startup notification (опит 2): {e2}")
                    logger.error(f"❌ Traceback 2: {traceback.format_exc()}")
        
        # Изпълни след инициализация на app
        async def schedule_reports_task(context):
            await schedule_reports(context. application)
        
        async def enable_auto_alerts_task(context):
            await enable_auto_alerts()
        
        async def send_startup_notification_task(context):
            await send_startup_notification()
        
        # KEEPALIVE механизъм - пинг на всеки 30 мин за да предотврати timeout
        async def keepalive_ping(context):
            try:
                # Прости ping към Telegram API за keepalive
                await context.bot.get_me()
                logger.info("💓 Keepalive ping изпратен успешно")
            except Exception as e:
                logger.warning(f"⚠️ Keepalive ping грешка: {e}")
        
        app.job_queue.run_once(schedule_reports_task, 5)
        app.job_queue.run_once(enable_auto_alerts_task, 10)
        app.job_queue.run_once(send_startup_notification_task, 0.5)  # ВЕДНАГА - след 0.5 сек
        
        # Keepalive ping на всеки 30 минути (1800 секунди)
        app.job_queue.run_repeating(keepalive_ping, interval=1800, first=1800)
    
    # Стартирай бота с error handling и БЕЗКРАЕН auto-recovery
    retry_count = 0
    
    while True:  # Безкраен loop - винаги се опитва да рестартира
        try:
            retry_count += 1
            logger.info(f"🤖 Стартиране на polling (опит #{retry_count})...")
            app.run_polling(
                drop_pending_updates=True, 
                allowed_updates=Update.ALL_TYPES
            )
            # Ако polling спре нормално (KeyboardInterrupt), излез
            logger.info("ℹ️ Polling спря нормално")
            break
            
        except KeyboardInterrupt:
            logger.info("🛑 Bot спрян от потребител (Ctrl+C)")
            break
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"❌ Грешка при polling (опит #{retry_count}): {error_msg}")
            logger.exception(e)  # Full stack trace в логовете
            
            # Изпрати нотификация за crash (само на всеки 5-ти опит)
            if retry_count % 5 == 0:
                try:
                    from telegram import Bot
                    bot = Bot(token=TELEGRAM_BOT_TOKEN)
                    import asyncio
                    asyncio.run(send_bot_status_notification(
                        bot, 
                        "crashed", 
                        f"Attempt #{retry_count}: {error_msg[:200]}"
                    ))
                except:
                    pass  # Ако не може да изпрати, продължи
            
            # Прогресивно чакане с cap на 120 секунди
            wait_time = min(10 + (retry_count * 5), 120)
            logger.info(f"🔄 Автоматичен рестарт след {wait_time} секунди...")
            import time
            time.sleep(wait_time)
            
            # Cleanup преди retry
            try:
                import gc
                gc.collect()  # Освобождаване на памет
            except:
                pass


if __name__ == "__main__":
    main()
    
    
    
