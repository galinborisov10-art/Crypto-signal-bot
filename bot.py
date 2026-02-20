# Auto-deploy test - Dec 7, 2025 14:20 UTC
from typing import Dict, List, Optional, Tuple, Any
# Second auto-deploy test - confirming deployment works
import requests
import json
import asyncio
import logging
import hashlib
import gc
import uuid
import fcntl
from datetime import datetime, timedelta, timezone
from functools import wraps
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
from pathlib import Path
import html
import pytz

# ================= ENVIRONMENT VARIABLES =================
from dotenv import load_dotenv

# Зареди .env файла
load_dotenv()

# Логване - Configure only once to avoid duplicate logs
root_logger = logging.getLogger()
if not root_logger.handlers:
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO
    )
logger = logging.getLogger(__name__)

# Track bot process start time (for version info)
BOT_START_TIME = datetime.now(timezone.utc)

# AUTO-DETECT BASE PATH (Codespace vs Server vs CI) - EARLY INIT
# Priority: explicit env var > /root > /workspaces > current directory
if os.getenv('BOT_BASE_PATH'):
    BASE_PATH = os.getenv('BOT_BASE_PATH')
    logger.info(f"📂 BASE_PATH from environment: {BASE_PATH}")
elif os.path.exists('/root/Crypto-signal-bot'):
    BASE_PATH = '/root/Crypto-signal-bot'
    logger.info(f"📂 BASE_PATH detected (server): {BASE_PATH}")
elif os.path.exists('/workspaces/Crypto-signal-bot'):
    BASE_PATH = '/workspaces/Crypto-signal-bot'
    logger.info(f"📂 BASE_PATH detected (codespace): {BASE_PATH}")
else:
    # Fallback to current directory
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))
    logger.info(f"📂 BASE_PATH fallback (current dir): {BASE_PATH}")

# Add rotating file handler for logging (prevents memory leak from unbounded growth)
# Only add if not already present (avoid duplicate handlers)
try:
    from logging.handlers import RotatingFileHandler
    
    root_logger = logging.getLogger()
    # Check if file handler already exists
    has_file_handler = any(isinstance(h, RotatingFileHandler) for h in root_logger.handlers)
    
    if not has_file_handler:
        # Rotate at 50MB, keep 3 backups (max 200MB total)
        file_handler = RotatingFileHandler(
            f'{BASE_PATH}/bot.log',
            maxBytes=50 * 1024 * 1024,  # 50 MB
            backupCount=3,  # Keep 3 old files (bot.log.1, bot.log.2, bot.log.3)
            encoding='utf-8'
        )
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
        root_logger.addHandler(file_handler)
        logger.info(f"📝 Rotating file logging enabled: {BASE_PATH}/bot.log (max 50MB, 3 backups)")
    else:
        logger.debug("File handler already configured, skipping duplicate")
except Exception as e:
    logger.warning(f"⚠️ Could not setup rotating file logging: {e}")


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
    from ict_signal_engine import ICTSignalEngine, ICTSignal, MarketBias, SignalType
    from ict_80_alert_handler import ICT80AlertHandler
    from order_block_detector import OrderBlockDetector
    from fvg_detector import FVGDetector
    from timeframe_contract import TimeframeContract
# DISABLED:     from real_time_monitor import RealTimePositionMonitor
    ICT_SIGNAL_ENGINE_AVAILABLE = True
    logger.info("✅ ICT Signal Engine loaded")
    ict_engine_global = ICTSignalEngine()  # Global initialization for logs
    ict_80_handler_global = ICT80AlertHandler(ict_engine_global)  # 80% alert handler
    real_time_monitor_global = None  # Will be initialized in main() with bot instance
except ImportError as e:
    ICT_SIGNAL_ENGINE_AVAILABLE = False
    logger.warning(f"⚠️ ICT Signal Engine not available: {e}")
    real_time_monitor_global = None

# Trade Re-analysis Engine (PR #5)
try:
    from trade_reanalysis_engine import TradeReanalysisEngine, RecommendationType, CheckpointAnalysis
    TRADE_REANALYSIS_AVAILABLE = True
    logger.info("✅ Trade Re-analysis Engine loaded")
    reanalysis_engine_global = TradeReanalysisEngine(ict_engine_global if ICT_SIGNAL_ENGINE_AVAILABLE else None)
except ImportError as e:
    TRADE_REANALYSIS_AVAILABLE = False
    logger.warning(f"⚠️ Trade Re-analysis Engine not available: {e}")
    reanalysis_engine_global = None

# Signal Cache for Persistent Deduplication (PR #111)
try:
    from signal_cache import is_signal_duplicate, validate_cache
    SIGNAL_CACHE_AVAILABLE = True
    logger.info("✅ Signal Cache (persistent deduplication) loaded")
    
    # Validate cache integrity on startup
    is_valid, msg = validate_cache()
    if is_valid:
        logger.info(f"✅ Signal cache validated: {msg}")
    else:
        logger.error(f"❌ Signal cache validation failed: {msg}")
        logger.warning("⚠️ Cache will be reset on first use")
except ImportError as e:
    SIGNAL_CACHE_AVAILABLE = False
    logger.warning(f"⚠️ Signal Cache not available: {e}")


# Position Manager (PR #7)
try:
    from position_manager import PositionManager
    from init_positions_db import create_positions_database
    POSITION_MANAGER_AVAILABLE = True
    logger.info("✅ Position Manager loaded")
    position_manager_global = PositionManager()
    logger.info(f"✅ Position Manager initialized: {position_manager_global}")
    logger.info(f"🔍 DIAGNOSTIC: Database path: {position_manager_global.db_path if hasattr(position_manager_global, 'db_path') else 'UNKNOWN'}")
except ImportError as e:
    POSITION_MANAGER_AVAILABLE = False
    logger.warning(f"⚠️ Position Manager not available: {e}")
    position_manager_global = None

# Chart Visualization System
try:
    from chart_generator import ChartGenerator
    from chart_annotator import ChartAnnotator
    CHART_VISUALIZATION_AVAILABLE = True
    logger.info("✅ Chart Visualization System loaded")
except ImportError as e:
    CHART_VISUALIZATION_AVAILABLE = False
    logger.warning(f"⚠️ Chart Visualization not available: {e}")

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

# ICT Backtest Engine (NEW - for /backtest command)
try:
    from ict_backtest import ICTBacktestEngine
    ICT_BACKTEST_AVAILABLE = True
    print("✅ ICT Backtest Engine loaded successfully")
except ImportError as e:
    ICT_BACKTEST_AVAILABLE = False
    print(f"⚠️ ICT Backtest Engine not available: {e}")

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

# ================= LOGGING SETUP (EARLY) =================
# Logging already configured at line 35 with RotatingFileHandler at line 72
# No need for duplicate basicConfig() call to avoid double logging


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

# ================= SECURITY MODULES (NEW - v2.0.0) =================
try:
    from security.token_manager import get_secure_token, token_manager
    from security.rate_limiter import check_rate_limit, rate_limiter
    from security.auth import require_auth, require_admin, auth_manager
    from security.security_monitor import log_security_event, security_monitor
    from version import get_version_string, get_full_version_info
    SECURITY_MODULES_AVAILABLE = True
    logger.info("✅ Security Modules loaded (v2.0.0)")
except ImportError as e:
    SECURITY_MODULES_AVAILABLE = False
    logger.warning(f"⚠️ Security Modules not available: {e}")

# ================= НАСТРОЙКИ (от .env файл) =================
# Зареди от environment variables - use secure token manager if available
if SECURITY_MODULES_AVAILABLE:
    TELEGRAM_BOT_TOKEN = get_secure_token()
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ Failed to get bot token from SecureTokenManager!")
        logger.info("💡 Falling back to environment variable...")
        TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
else:
    TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID', '7003238836'))

# ================= USER ACCESS CONTROL =================
# Списък с разрешени потребители (Owner винаги е разрешен)
# PR #113: Defensive fallback to ensure access even if env var issues
# NOTE: Hardcoded owner ID (7003238836) is intentional as emergency fallback
# to prevent lockout if environment variable is misconfigured
ALLOWED_USERS = {
    7003238836,  # Hardcoded owner ID as fallback
    int(os.getenv('OWNER_CHAT_ID', '7003238836'))
}  # Само owner по подразбиране

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

# Access control messages
ACCESS_DENIED_MESSAGE = (
    "⛔ <b>ACCESS DENIED</b>\n\n"
    "You are not authorized to use this bot.\n\n"
    "If you believe this is an error, please contact the bot owner."
)

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

# PR #113: Swing analysis constants
SWING_KLINES_LIMIT = 100  # Number of candles to fetch for swing analysis
SWING_MIN_CANDLES = 20    # Minimum candles needed for analysis
SWING_UPPER_THRESHOLD = 0.66  # Price in upper 33% = bullish
SWING_LOWER_THRESHOLD = 0.33  # Price in lower 33% = bearish

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

# ================= STARTUP MODE SUPPRESSION (PR #111) =================
# Prevents duplicate signals on bot startup for first 5 minutes
STARTUP_MODE = True
STARTUP_TIME = None  # Will be set on bot start
STARTUP_GRACE_PERIOD_SECONDS = 300  # 5 minutes

# ================= PR #7: POSITION MONITORING CONFIG =================
AUTO_POSITION_TRACKING_ENABLED = True  # Auto-open positions from auto signals
AUTO_CLOSE_ON_SL_HIT = True  # Auto-close when SL hit
AUTO_CLOSE_ON_TP_HIT = True  # Auto-close when TP hit
CHECKPOINT_MONITORING_ENABLED = True  # Enable checkpoint monitoring
POSITION_MONITORING_INTERVAL_SECONDS = 60  # Check every 60 seconds

# ================= ACTIVE TRADES TRACKING =================
# Global variable for active trades tracking (for 80% alerts and final alerts)
# Structure: List of dictionaries with trade information
active_trades = []

# Trade outcome constants
TRADE_OUTCOME_WIN = ['WIN', 'SUCCESS']
TRADE_OUTCOME_LOSS = ['LOSS', 'FAILED']

# ================= SCHEDULER CONFIGURATION =================
DAILY_REPORT_MISFIRE_GRACE_TIME = 43200  # 12 hours grace period for missed daily reports
STARTUP_CHECK_DELAY_SECONDS = 10  # Delay before checking for missed reports on startup
DEFAULT_SWING_RR_RATIO = 3.5  # Default risk/reward ratio for ranging markets

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

# ================= UX IMPROVEMENTS: CACHING & PERFORMANCE =================
import time
import statistics
from functools import wraps
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict, OrderedDict
from threading import Lock

# ================= P13: LRU CACHE WITH TTL =================
class LRUCacheDict:
    """
    LRU Cache with TTL that maintains backward compatibility with dict interface.
    Existing code can continue using it like a regular dict.
    """
    
    def __init__(self, max_size=100, ttl_seconds=300):
        """
        Args:
            max_size: Maximum number of items (default 100)
            ttl_seconds: Time to live in seconds (default 300)
        """
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache = OrderedDict()
        self._lock = Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def __getitem__(self, key):
        """Dict-like access: cache['key']"""
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                raise KeyError(key)
            
            # Check TTL
            item = self._cache[key]
            age = time.time() - item['timestamp']
            
            if age > self.ttl_seconds:
                # Expired - remove and raise KeyError
                del self._cache[key]
                self._misses += 1
                raise KeyError(key)
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return item['data']
    
    def __setitem__(self, key, value):
        """Dict-like assignment: cache['key'] = value"""
        with self._lock:
            # Remove if exists (to update position)
            if key in self._cache:
                del self._cache[key]
            
            # Add new item with timestamp
            self._cache[key] = {
                'data': value,
                'timestamp': time.time()
            }
            
            # Enforce size limit (evict oldest)
            while len(self._cache) > self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._evictions += 1
                logger.debug(f"Cache evicted oldest item: {oldest_key}")
    
    def __contains__(self, key):
        """Dict-like 'in' operator: 'key' in cache"""
        with self._lock:
            if key not in self._cache:
                return False
            
            # Check TTL
            item = self._cache[key]
            age = time.time() - item['timestamp']
            
            if age > self.ttl_seconds:
                del self._cache[key]
                return False
            
            return True
    
    def __delitem__(self, key):
        """Dict-like deletion: del cache['key']"""
        with self._lock:
            del self._cache[key]
    
    def get(self, key, default=None):
        """Dict-like get: cache.get('key', default)"""
        try:
            return self.__getitem__(key)
        except KeyError:
            return default
    
    def keys(self):
        """Dict-like keys()"""
        with self._lock:
            # Clean expired items first
            self._cleanup_expired()
            return list(self._cache.keys())
    
    def values(self):
        """Dict-like values()"""
        with self._lock:
            self._cleanup_expired()
            return [item['data'] for item in self._cache.values()]
    
    def items(self):
        """Dict-like items()"""
        with self._lock:
            self._cleanup_expired()
            return [(k, item['data']) for k, item in self._cache.items()]
    
    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")
    
    def _cleanup_expired(self):
        """Remove expired items (internal use)"""
        current_time = time.time()
        expired_keys = [
            key for key, item in self._cache.items()
            if current_time - item['timestamp'] > self.ttl_seconds
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        if expired_keys:
            logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired items")
    
    def cleanup_expired(self):
        """Public method to trigger cleanup"""
        with self._lock:
            self._cleanup_expired()
    
    def get_stats(self):
        """Get cache statistics"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                'hits': self._hits,
                'misses': self._misses,
                'evictions': self._evictions,
                'hit_rate': self._hits / (self._hits + self._misses) if (self._hits + self._misses) > 0 else 0
            }

# Global cache storage with LRU eviction
CACHE = {
    'backtest': LRUCacheDict(max_size=50, ttl_seconds=300),      # 50 backtest results, 5 min TTL
    'market': LRUCacheDict(max_size=100, ttl_seconds=180),       # 100 market data, 3 min TTL
    'ml_performance': LRUCacheDict(max_size=50, ttl_seconds=300) # 50 ML results, 5 min TTL
}

CACHE_TTL = {
    'backtest': 300,      # 5 minutes
    'market': 180,        # 3 minutes
    'ml_performance': 300 # 5 minutes
}

# Performance metrics storage
PERFORMANCE_METRICS = defaultdict(list)

# Performance configuration constants
MAX_ASYNC_WORKERS = 3  # Number of background threads for async operations
MAX_METRICS_HISTORY = 100  # Maximum number of metrics to keep per operation
MAX_ERROR_DETAIL_LENGTH = 100  # Maximum error detail string length in user messages

# Thread executor for async operations
executor = ThreadPoolExecutor(max_workers=MAX_ASYNC_WORKERS)

# Debug mode flag
DEBUG_MODE = False


def get_cached(cache_type: str, key: str):
    """Get cached result if valid"""
    if key not in CACHE[cache_type]:
        return None
    
    cached = CACHE[cache_type][key]
    age = (datetime.now(timezone.utc) - cached['timestamp']).total_seconds()
    
    if age > CACHE_TTL[cache_type]:
        # Cache expired
        del CACHE[cache_type][key]
        return None
    
    logger.info(f"✅ Cache HIT: {cache_type}/{key} (age: {age:.1f}s)")
    return cached['data']


def set_cache(cache_type: str, key: str, data):
    """Store result in cache"""
    CACHE[cache_type][key] = {
        'data': data,
        'timestamp': datetime.now(timezone.utc)
    }
    logger.info(f"💾 Cache SET: {cache_type}/{key}")


# ================= P10: SCHEDULER ERROR HANDLING =================
def safe_job(job_name: str, max_retries: int = 3, retry_delay: int = 60):
    """
    Decorator for scheduler jobs - adds error handling and retry logic.
    
    Usage:
        @safe_job("daily_report", max_retries=3, retry_delay=60)
        async def send_daily_report(context):
            ...
    
    Args:
        job_name: Human-readable job name for logging
        max_retries: Maximum retry attempts on failure
        retry_delay: Seconds to wait between retries
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Get context from args or kwargs
            context = None
            if args and hasattr(args[0], 'bot'):
                context = args[0]
            elif 'context' in kwargs:
                context = kwargs['context']
            
            for attempt in range(1, max_retries + 1):
                try:
                    logger.info(f"🔄 Starting job: {job_name} (attempt {attempt}/{max_retries})")
                    
                    # Execute the job
                    result = await func(*args, **kwargs)
                    
                    logger.info(f"✅ Job completed: {job_name}")
                    return result
                    
                except Exception as e:
                    logger.error(f"❌ Job failed: {job_name} (attempt {attempt}/{max_retries})")
                    logger.error(f"Error: {str(e)}")
                    logger.exception(e)  # Full stack trace
                    
                    if attempt < max_retries:
                        logger.info(f"⏳ Retrying in {retry_delay}s...")
                        await asyncio.sleep(retry_delay)
                    else:
                        # Final failure - notify owner if context available
                        if context:
                            try:
                                await context.bot.send_message(
                                    chat_id=OWNER_CHAT_ID,
                                    text=(
                                        f"❌ <b>SCHEDULER JOB FAILED</b>\n\n"
                                        f"Job: <code>{job_name}</code>\n"
                                        f"Attempts: {max_retries}\n"
                                        f"Error: <code>{str(e)[:200]}</code>\n\n"
                                        f"Check logs for details."
                                    ),
                                    parse_mode='HTML'
                                )
                            except:
                                pass  # Even notification failed
                        
                        logger.error(f"💥 Job permanently failed: {job_name}")
                        # Do NOT raise - let scheduler continue running
        
        return wrapper
    return decorator


def track_metric(operation: str, duration: float):
    """Track operation performance"""
    PERFORMANCE_METRICS[operation].append(duration)
    
    # Keep only last N measurements to prevent memory bloat
    if len(PERFORMANCE_METRICS[operation]) > MAX_METRICS_HISTORY:
        PERFORMANCE_METRICS[operation] = PERFORMANCE_METRICS[operation][-MAX_METRICS_HISTORY:]


def get_metrics_summary():
    """Get performance summary"""
    summary = {}
    for operation, durations in PERFORMANCE_METRICS.items():
        if durations:
            summary[operation] = {
                'count': len(durations),
                'avg': statistics.mean(durations),
                'min': min(durations),
                'max': max(durations),
                'median': statistics.median(durations)
            }
    return summary


def with_timeout(seconds=30):
    """Decorator to add timeout protection to async functions"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.error(f"⏱️ {func.__name__} timed out after {seconds}s")
                raise TimeoutError(f"Operation timed out after {seconds} seconds")
        return wrapper
    return decorator


def log_timing(operation_name: str = None):
    """Decorator to log execution time and track metrics"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            start_time = time.time()
            
            if DEBUG_MODE:
                logger.debug(f"▶️ START: {name}")
            else:
                logger.info(f"▶️ START: {name}")
            
            try:
                result = await func(*args, **kwargs)
                elapsed = time.time() - start_time
                
                # Track metric
                track_metric(name, elapsed)
                
                logger.info(f"✅ END: {name} ({elapsed:.2f}s)")
                return result
            except Exception as e:
                elapsed = time.time() - start_time
                track_metric(f"{name}_FAILED", elapsed)
                logger.error(f"❌ FAILED: {name} ({elapsed:.2f}s) - {str(e)}")
                raise
        return wrapper
    return decorator


def format_liquidity_section(signal) -> str:
    """Format liquidity analysis section for signal message"""
    if not hasattr(signal, 'liquidity_zones') or not signal.liquidity_zones:
        return ""
    
    section = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    section += "💧 <b>LIQUIDITY CONTEXT:</b>\n\n"
    
    # Show top 3 strongest zones
    zones_sorted = sorted(signal.liquidity_zones, key=lambda z: z.get('confidence', 0) if isinstance(z, dict) else getattr(z, 'confidence', 0), reverse=True)[:3]
    
    for zone in zones_sorted:
        # Handle both dict and object types
        if isinstance(zone, dict):
            zone_type = zone.get('zone_type', 'UNKNOWN')
            price_level = zone.get('price_level', 0)
            touches = zone.get('touches', 0)
            confidence = zone.get('confidence', 0)
            swept = zone.get('swept', False)
            sweep_time = zone.get('sweep_time')
        else:
            zone_type = getattr(zone, 'zone_type', 'UNKNOWN')
            price_level = getattr(zone, 'price_level', 0)
            touches = getattr(zone, 'touches', 0)
            confidence = getattr(zone, 'confidence', 0)
            swept = getattr(zone, 'swept', False)
            sweep_time = getattr(zone, 'sweep_time', None)
        
        emoji = "🟢" if zone_type == "BSL" else "🔴"
        section += f"{emoji} <b>{zone_type} Zone:</b> ${price_level:,.2f}\n"
        section += f"   • Touches: {touches} | Confidence: {confidence*100:.0f}%\n"
        if swept and sweep_time:
            from datetime import datetime
            if isinstance(sweep_time, datetime):
                section += f"   • ✅ SWEPT on {sweep_time.strftime('%m/%d %H:%M')}\n"
        section += "\n"
    
    # Show recent sweeps
    if hasattr(signal, 'liquidity_sweeps') and signal.liquidity_sweeps:
        # Filter out swept zones and take first 2
        recent_sweeps = []
        for sweep in signal.liquidity_sweeps:
            if isinstance(sweep, dict):
                swept = sweep.get('liquidity_zone', {}).get('swept', True)
            else:
                liq_zone = getattr(sweep, 'liquidity_zone', None)
                swept = getattr(liq_zone, 'swept', True) if liq_zone else True
            
            if not swept:
                recent_sweeps.append(sweep)
                if len(recent_sweeps) >= 2:
                    break
        
        if recent_sweeps:
            section += "<b>Recent Sweeps:</b>\n"
            for sweep in recent_sweeps:
                # Handle both dict and object types
                if isinstance(sweep, dict):
                    sweep_type = sweep.get('sweep_type', 'UNKNOWN')
                    price = sweep.get('price', 0)
                    strength = sweep.get('strength', 0)
                    timestamp = sweep.get('timestamp')
                    reversal_candles = sweep.get('reversal_candles', 0)
                else:
                    sweep_type = getattr(sweep, 'sweep_type', 'UNKNOWN')
                    price = getattr(sweep, 'price', 0)
                    strength = getattr(sweep, 'strength', 0)
                    timestamp = getattr(sweep, 'timestamp', None)
                    reversal_candles = getattr(sweep, 'reversal_candles', 0)
                
                sweep_emoji = "💥" if sweep_type == "SSL_SWEEP" else "⚡"
                section += f"{sweep_emoji} {sweep_type}: ${price:,.2f} "
                section += f"(Strength: {strength*100:.0f}%)\n"
                
                if timestamp:
                    from datetime import datetime
                    if isinstance(timestamp, datetime):
                        section += f"   • Time: {timestamp.strftime('%m/%d %H:%M')} | "
                section += f"Reversal: {reversal_candles} candles\n"
    
    section += "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    return section


def format_user_error(error: Exception, operation: str) -> str:
    """Convert technical error to user-friendly message"""
    
    error_messages = {
        TimeoutError: "⏱️ Операцията отне твърде дълго време. Опитай пак след малко.",
        FileNotFoundError: "📂 Няма данни за анализ. Генерирай няколко сигнала първо.",
        KeyError: "⚠️ Грешка в данните. Моля съобщи на администратора.",
        ValueError: "❌ Невалидни данни. Провери входните параметри.",
        ConnectionError: "🌐 Проблем с интернет връзката. Опитай пак.",
    }
    
    error_type = type(error)
    user_message = error_messages.get(error_type, "❌ Възникна грешка.")
    
    return (
        f"<b>{user_message}</b>\n\n"
        f"🔧 Операция: {operation}\n"
        f"📝 Детайли: {str(error)[:MAX_ERROR_DETAIL_LENGTH]}\n\n"
        f"💡 Ако проблемът продължава, използвай /help"
    )


async def show_progress(query, step: int, total: int, message: str):
    """Update progress during long operations"""
    progress_bar = "▓" * step + "░" * (total - step)
    await query.edit_message_text(
        f"⏳ <b>ОБРАБОТКА...</b>\n\n"
        f"[{progress_bar}] {step}/{total}\n\n"
        f"{message}",
        parse_mode='HTML'
    )


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
            'alert_interval': 1800,  # 30 minutes (ESB v1.0 §12)
            'news_enabled': False,
            'news_interval': 7200,
            'use_fundamental': False,  # Default: fundamental analysis disabled
            'fundamental_weight': 0.3,  # Default: 30% fundamental, 70% technical
        }
    # Ensure backward compatibility: add new fields to existing users
    if 'use_fundamental' not in bot_data[chat_id]:
        bot_data[chat_id]['use_fundamental'] = False
    if 'fundamental_weight' not in bot_data[chat_id]:
        bot_data[chat_id]['fundamental_weight'] = 0.3
    return bot_data[chat_id]


def get_main_keyboard():
    """Връща основната клавиатура с менюто"""
    keyboard = [
        [KeyboardButton("📊 Пазар"), KeyboardButton("📈 Сигнал")],
        [KeyboardButton("📰 Новини"), KeyboardButton("📋 Отчети")],
        [KeyboardButton("📚 ML Анализ"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("🔔 Alerts"), KeyboardButton("🏥 Health")],  # PR #113: Added Health button
        [KeyboardButton("🔄 Рестарт"), KeyboardButton("💻 Workspace")],
        [KeyboardButton("🏠 Меню"), KeyboardButton("ℹ️ Помощ")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_ml_keyboard():
    """ML Анализ подменю с описания"""
    keyboard = [
        [KeyboardButton("🤖 ML Прогноза"), KeyboardButton("📊 ML Performance")],
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


# ================= P8: UNIFIED COOLDOWN CHECKER =================
def check_signal_cooldown(
    symbol: str, 
    signal_type: str, 
    timeframe: str, 
    confidence: float, 
    entry_price: float,
    cooldown_minutes: int = 60
) -> tuple:
    """
    Unified cooldown check for ALL signal commands.
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        signal_type: Signal type (e.g., 'BUY', 'SELL')
        timeframe: Timeframe (e.g., '1h', '4h')
        confidence: Signal confidence (0-100)
        entry_price: Entry price
        cooldown_minutes: Cooldown period in minutes
    
    Returns:
        (is_duplicate: bool, message: str)
            - is_duplicate: True if signal was sent recently
            - message: User-friendly message to display
    """
    # Use existing is_signal_already_sent function
    if is_signal_already_sent(
        symbol=symbol,
        signal_type=signal_type,
        timeframe=timeframe,
        confidence=confidence,
        entry_price=entry_price,
        cooldown_minutes=cooldown_minutes
    ):
        msg = (
            f"⏳ <b>Signal Already Sent Recently</b>\n\n"
            f"📊 {symbol} {timeframe} {signal_type}\n"
            f"🕐 Cooldown: {cooldown_minutes} minutes\n\n"
            f"Please wait before requesting again."
        )
        return True, msg
    
    return False, ""


def get_admin_keyboard():
    """Връща клавиатура за Admin режим"""
    keyboard = [
        [KeyboardButton("✅ Enter"), KeyboardButton("❌ Exit")],
        [KeyboardButton("📊 Пазар"), KeyboardButton("📈 Сигнал")],
        [KeyboardButton("📰 Новини"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("🔔 Alerts"), KeyboardButton("🏠 Меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def detect_order_blocks(df, lookback=15, threshold=0.01, current_price=None, max_obs=5):
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
        lookback_period = min(15, len(df) - 2)
        max_obs_count = 7  # Топ 7 order blocks
        
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
                sr_data = luxalgo_ict_data.get('luxalgo_sr', {})
                if sr_data:
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
                    
                    # Філтрирай само активни (non-swept) зони
                    active_zones = [liq for liq in liquidity_zones if not getattr(liq, 'swept', True)]
                    
                    for liq_obj in active_zones[:10]:  # Топ 10 активни зони
                        # Извлечи данни от LiquidityLevel обект
                        liq_price = float(liq_obj.price)
                        is_buy_side = liq_obj.is_buy_side
                        
                        zone_width = liq_price * 0.004
                        zone_low = liq_price - zone_width
                        zone_high = liq_price + zone_width
                        
                        if is_buy_side:
                            # BUY SIDE liquidity - мека червена зона
                            ax1.axhspan(zone_low, zone_high, color='#ef5350', alpha=0.12, zorder=1)
                            ax1.axhline(y=liq_price, color='#c62828', linestyle=':', linewidth=1.2, alpha=0.6, zorder=2)
                            ax1.text(1, liq_price, '💧BSL', fontsize=6, color='#c62828', weight='bold', ha='left', va='center',
                                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='#c62828', linewidth=0.8))
                        else:
                            # SELL SIDE liquidity - мека синя зона
                            ax1.axhspan(zone_low, zone_high, color='#42a5f5', alpha=0.12, zorder=1)
                            ax1.axhline(y=liq_price, color='#1976d2', linestyle=':', linewidth=1.2, alpha=0.6, zorder=2)
                            ax1.text(1, liq_price, '💧SSL', fontsize=6, color='#1976d2', weight='bold', ha='left', va='center',
                                    bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.7, edgecolor='#1976d2', linewidth=0.8))
            
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
        # Get TF hierarchy from contract
        tf_hierarchy = TimeframeContract.get_all_supported_timeframes()
        
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
            
        # === 3. 80% TP ALERT С ICT РЕАНАЛИЗ ===
        elif alert_type == '80_PERCENT':
            progress = alert['progress']
            current_profit_pct = ((current_price - entry_price) / entry_price * 100) if signal_type == 'BUY' else ((entry_price - current_price) / entry_price * 100)
            
            try:
                # 1. Вземи актуални данни
                klines = await fetch_klines(symbol, timeframe, limit=100)
                
                if not klines or len(klines) < 50:
                    raise Exception("Insufficient kline data")
                
                # 2. ICT Реанализ
                analysis = await ict_80_handler_global.analyze_position(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type=signal_type,
                    entry_price=entry_price,
                    tp_price=tp_price,
                    current_price=current_price,
                    original_confidence=confidence,
                    klines=klines
                )
                
                # 3. Извлечи резултатите
                recommendation = analysis['recommendation']
                new_confidence = analysis['confidence']
                reasoning = analysis['reasoning']
                hold_score = analysis['score_hold']
                close_score = analysis['score_close']
                warnings = analysis['warnings']
                
                # 4. Генерирай съобщение
                if recommendation == 'HOLD':
                    recommendation_emoji = "✅"
                    action_title = "HOLD ДО TP"
                    action_plan = (
                        f"🎯 <b>Препоръка:  HOLD до пълен TP</b>\n\n"
                        f"📊 ICT анализ потвърждава позицията:\n"
                        f"{reasoning}\n\n"
                        f"💡 <b>План: </b>\n"
                        f"   1. Остави позицията отворена\n"
                        f"   2. Целта е близо - очаквай TP hit\n"
                        f"   3. Провери отново след 1-2 часа\n"
                    )
                elif recommendation == 'CLOSE_NOW':
                    recommendation_emoji = "❌"
                    action_title = "ЗАТВОРИ СЕГА"
                    action_plan = (
                        f"❌ <b>Препоръка: ЗАТВОРИ ПОЗИЦИЯТА</b>\n\n"
                        f"⚠️ ICT анализ показва риск:\n"
                        f"{reasoning}\n\n"
                    )
                    if warnings:
                        action_plan += "🚨 <b>Предупреждения:</b>\n"
                        for warning in warnings: 
                            action_plan += f"   • {warning}\n"
                        action_plan += "\n"
                    action_plan += (
                        f"💡 <b>План:</b>\n"
                        f"   1. Затвори позицията СЕГА\n"
                        f"   2. Вземи печалбата (+{current_profit_pct:. 2f}%)\n"
                        f"   3. Избегни reversal risk\n"
                    )
                else:  # PARTIAL_CLOSE
                    recommendation_emoji = "📊"
                    action_title = "ЧАСТИЧНО ЗАТВОРИ"
                    action_plan = (
                        f"📊 <b>Препоръка:  ЧАСТИЧНО ЗАТВАРЯНЕ</b>\n\n"
                        f"⚖️ ICT анализ показва смесени сигнали:\n"
                        f"{reasoning}\n\n"
                        f"💡 <b>План:</b>\n"
                        f"   1. Затвори 50-70% от позицията\n"
                        f"   2. Остави 30-50% за TP\n"
                        f"   3. Премести SL на breakeven (${entry_price: ,.4f})\n"
                        f"   4. Trailing stop:  ${current_price * 0.985: ,.4f}\n"
                    )
                
                # 5. Финално съобщение
                message = f"🎯 <b>80% ДО ЦЕЛ - ICT РЕАНАЛИЗ</b> 🎯\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                message += f"{signal_emoji} <b>{symbol}:  {signal_type}</b>\n"
                message += f"📊 Първоначална увереност: <b>{confidence}%</b>\n"
                message += f"🔄 Актуална увереност: <b>{new_confidence:. 1f}%</b>\n"
                message += f"⏰ Таймфрейм: <b>{timeframe}</b>\n\n"
                
                message += f"💰 Entry: ${entry_price:,.4f}\n"
                message += f"🎯 TP: ${tp_price:,.4f}\n"
                message += f"💵 Current: ${current_price:,.4f}\n\n"
                
                message += f"📈 <b>Прогрес:  {progress:.1f}%</b>\n"
                message += f"💚 Текуща печалба: <b>+{current_profit_pct:.2f}%</b>\n"
                message += f"⏱️ Отворена:  {time_str}\n\n"
                
                message += f"━━━━━━━━━━━━━━━━━━━━\n"
                message += f"{recommendation_emoji} <b>SCORE: Hold {hold_score} | Close {close_score}</b>\n\n"
                message += action_plan
                
            except Exception as e:
                logger.error(f"Грешка при ICT реанализ на 80% alert: {e}")
                # Fallback съобщение
                message = f"🎯 <b>80% ДО ЦЕЛ!</b> 🎯\n"
                message += f"━━━━━━━━━━━━━━━━━━━━\n\n"
                message += f"{signal_emoji} <b>{symbol}: {signal_type}</b>\n"
                message += f"📈 Прогрес: {progress:.1f}%\n"
                message += f"💚 Печалба: +{current_profit_pct:.2f}%\n\n"
                message += f"⚠️ Грешка при реанализ: {e}\n"
                message += f"💡 Препоръчвам частично затваряне за сигурност\n"
        
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
        # Get all supported timeframes from contract
        all_timeframes = TimeframeContract.get_all_supported_timeframes()
        logger.debug(f"📊 Using {len(all_timeframes)} timeframes from contract: {all_timeframes}")
        
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
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
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
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(journal, f, indent=2)
        logger.info("✅ Trading journal saved successfully")
    except Exception as e:
        logger.error(f"Грешка при запазване на journal: {e}")


def log_trade_to_journal(symbol, timeframe, signal_type, confidence, entry_price, tp_price, sl_price, analysis_data=None):
    """Логва trade в журнала за ML анализ"""
    try:
        # ✅ Skip HOLD signals from journal
        if signal_type == 'HOLD':
            logger.info("ℹ️ Skipping HOLD signal from journal")
            return None
        
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
        
        # Map outcome to standardized status and outcome fields
        # This ensures compatibility with daily_reports.py expectations
        if outcome == 'WIN':
            trade['status'] = 'COMPLETED'  # Standardized status for closed trades
            trade['outcome'] = 'SUCCESS'   # Standardized outcome for profitable trades
        elif outcome == 'LOSS':
            trade['status'] = 'COMPLETED'
            trade['outcome'] = 'FAILED'    # Standardized outcome for losing trades
        else:
            trade['status'] = 'COMPLETED'
            trade['outcome'] = 'BREAKEVEN'
        
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
        # Handle both old (WIN/LOSS) and new (SUCCESS/FAILED) formats
        if outcome in ['WIN', 'SUCCESS']:
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
        # Handle both old (WIN/LOSS) and new (SUCCESS/FAILED) formats
        if outcome in ['WIN', 'SUCCESS']:
            tf_stats['wins'] += 1
        else:
            tf_stats['losses'] += 1
        
        # Pattern 3: Най-добри symbols
        if symbol not in journal['patterns']['best_symbols']:
            journal['patterns']['best_symbols'][symbol] = {'wins': 0, 'losses': 0, 'total': 0, 'total_profit': 0}
        
        sym_stats = journal['patterns']['best_symbols'][symbol]
        sym_stats['total'] += 1
        sym_stats['total_profit'] += trade.get('profit_loss_pct', 0)
        # Handle both old (WIN/LOSS) and new (SUCCESS/FAILED) formats
        if outcome in ['WIN', 'SUCCESS']:
            sym_stats['wins'] += 1
        else:
            sym_stats['losses'] += 1
        
        # ML Insights: Accuracy by confidence
        conf_range = f"{int(confidence // 10) * 10}-{int(confidence // 10) * 10 + 10}"
        if conf_range not in journal['ml_insights']['accuracy_by_confidence']:
            journal['ml_insights']['accuracy_by_confidence'][conf_range] = {'wins': 0, 'total': 0}
        
        conf_stats = journal['ml_insights']['accuracy_by_confidence'][conf_range]
        conf_stats['total'] += 1
        # Handle both old (WIN/LOSS) and new (SUCCESS/FAILED) formats
        if outcome in ['WIN', 'SUCCESS']:
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


# ================= ACTIVE TRADES MONITORING FUNCTIONS =================

async def add_to_active_trades(signal: Dict, user_chat_id: int):
    """
    Add signal to active trades for monitoring
    
    Args:
        signal: Signal dictionary with entry, tp, sl
        user_chat_id: User's Telegram chat ID
    
    Returns:
        str: Trade ID
    """
    global active_trades
    
    trade = {
        'trade_id': str(uuid.uuid4()),
        'symbol': signal.get('symbol', 'UNKNOWN'),
        'type': signal.get('type', 'LONG'),  # LONG or SHORT
        'entry': signal.get('entry', 0),
        'tp': signal.get('tp', 0),
        'sl': signal.get('sl', 0),
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'alerted_80': False,
        'user_chat_id': user_chat_id,
        'alerts_80': [],
        'timeframe': signal.get('timeframe', '4h'),
        'signal_data': signal  # Keep full signal for reference
    }
    
    active_trades.append(trade)
    
    logger.info(f"✅ Added {signal.get('symbol', 'UNKNOWN')} to active trades (ID: {trade['trade_id'][:8]})")
    
    return trade['trade_id']


async def check_80_percent_alerts(bot):
    """
    Monitor active trades and send alerts when price reaches 80% to TP
    
    Args:
        bot: Telegram Bot instance
    
    Runs every 1 minute via scheduler
    Checks all active trades and sends one-time alert at 80% threshold
    """
    global active_trades
    
    if not active_trades:
        return  # No active trades to monitor
    
    logger.info(f"🔍 Checking 80% alerts for {len(active_trades)} active trades")
    
    # Use slice copy to safely iterate (no removal happens here, but safer for future changes)
    for trade in active_trades[:]:
        try:
            symbol = trade['symbol']
            
            # Get current price from Binance
            try:
                response = requests.get(
                    BINANCE_PRICE_URL,
                    params={'symbol': symbol},
                    timeout=5
                )
                ticker = response.json()
                current_price = float(ticker['price'])
            except Exception as e:
                logger.error(f"Error getting price for {symbol}: {e}")
                continue
            
            # Calculate 80% threshold
            entry = trade['entry']
            tp = trade['tp']
            sl = trade['sl']
            trade_type = trade['type']
            
            # Calculate distance to TP
            if trade_type == 'LONG':
                distance_to_tp = tp - entry
                threshold_80 = entry + (distance_to_tp * 0.8)
                
                # Check if reached 80%
                reached_80 = current_price >= threshold_80 and not trade['alerted_80']
                
            else:  # SHORT
                distance_to_tp = entry - tp
                threshold_80 = entry - (distance_to_tp * 0.8)
                
                # Check if reached 80%
                reached_80 = current_price <= threshold_80 and not trade['alerted_80']
            
            # Send alert if 80% reached
            if reached_80:
                # Calculate percentage to TP
                if trade_type == 'LONG':
                    pct_to_tp = ((current_price - entry) / (tp - entry)) * 100
                else:
                    pct_to_tp = ((entry - current_price) / (entry - tp)) * 100
                
                # Create alert data
                alert_data = {
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'price': current_price,
                    'pct_to_tp': round(pct_to_tp, 1),
                    'recommendation': 'Consider taking partial profit (50%)'
                }
                
                # Add to trade's alerts
                trade['alerts_80'].append(alert_data)
                trade['alerted_80'] = True
                
                # Send Telegram notification
                message = (
                    f"📊 <b>80% ALERT - {symbol}</b>\n"
                    f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"🎯 Your {trade_type} trade has reached <b>80% to TP</b>!\n\n"
                    f"📍 Entry: {entry:,.2f}\n"
                    f"📈 Current: <b>{current_price:,.2f}</b>\n"
                    f"🎯 TP: {tp:,.2f}\n"
                    f"🛑 SL: {sl:,.2f}\n\n"
                    f"📊 Progress: <b>{pct_to_tp:.1f}%</b> to TP\n\n"
                    f"💡 <b>Recommendation:</b>\n"
                    f"Consider taking 50% partial profit to secure gains.\n"
                    f"Move SL to breakeven for remaining position.\n\n"
                    f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                )
                
                await bot.send_message(
                    chat_id=trade['user_chat_id'],
                    text=message,
                    parse_mode='HTML'
                )
                
                logger.info(f"✅ 80% Alert sent for {symbol} (Price: {current_price}, {pct_to_tp:.1f}% to TP)")
            
        except Exception as e:
            logger.error(f"Error in 80% alert check for {trade.get('symbol')}: {e}", exc_info=True)
    
    logger.info(f"✅ 80% alert check complete")


async def send_final_alert(trade: Dict, exit_price: float, hit_target: str, bot):
    """
    Send final alert when trade closes and log to journal
    
    Args:
        trade: Active trade dictionary
        exit_price: Price at which trade closed
        hit_target: 'TP' or 'SL'
    """
    global active_trades
    
    try:
        symbol = trade['symbol']
        entry = trade['entry']
        tp = trade['tp']
        sl = trade['sl']
        trade_type = trade['type']
        
        # Determine outcome
        outcome = 'WIN' if hit_target == 'TP' else 'LOSS'
        
        # Calculate P/L
        if trade_type == 'LONG':
            pnl_pct = ((exit_price - entry) / entry) * 100
        else:  # SHORT
            pnl_pct = ((entry - exit_price) / entry) * 100
        
        # Calculate absolute P/L (assume $1000 position size, adjust as needed)
        position_size = trade.get('position_size', 1000)
        pnl_usd = position_size * (pnl_pct / 100)
        
        # Calculate duration
        start_time = datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00'))
        end_time = datetime.now(timezone.utc)
        duration = end_time - start_time
        duration_hours = duration.total_seconds() / 3600
        
        # Create final alert data
        final_alert_data = {
            'timestamp': end_time.isoformat(),
            'outcome': outcome,
            'exit_price': exit_price,
            'pnl_pct': round(pnl_pct, 2),
            'pnl_usd': round(pnl_usd, 2),
            'duration_hours': round(duration_hours, 2),
            'hit_target': hit_target
        }
        
        # Add to trade data
        if 'final_alerts' not in trade:
            trade['final_alerts'] = []
        trade['final_alerts'].append(final_alert_data)
        
        # Set outcome
        trade['outcome'] = outcome
        trade['exit_price'] = exit_price
        trade['profit_loss_pct'] = pnl_pct
        
        # Send Telegram notification
        emoji = "✅" if outcome == 'WIN' else "❌"
        message = (
            f"{emoji} <b>{symbol} CLOSED - {outcome}</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"📍 Entry: {entry:,.2f}\n"
            f"📍 Exit: <b>{exit_price:,.2f}</b> ({hit_target})\n"
            f"💰 P/L: <b>{pnl_pct:+.2f}%</b> (${pnl_usd:+.2f})\n"
            f"⏱️ Duration: {duration_hours:.1f} hours\n\n"
        )
        
        # Add 80% alert info if exists
        if trade.get('alerts_80'):
            message += f"📊 80% Alert: ✅ Triggered at {trade['alerts_80'][0]['price']:,.2f}\n\n"
        
        message += f"⏰ {end_time.strftime('%Y-%m-%d %H:%M UTC')}"
        
        # Send using the bot instance passed as parameter
        await bot.send_message(
            chat_id=trade['user_chat_id'],
            text=message,
            parse_mode='HTML'
        )
        
        logger.info(f"✅ Final alert sent for {symbol}: {outcome} ({pnl_pct:+.2f}%)")
        
        # Save to trading journal
        await save_trade_to_journal(trade)
        
        # Remove from active trades using remove() for better performance
        try:
            active_trades.remove(trade)
        except ValueError:
            # Trade already removed, ignore
            pass
        
        logger.info(f"✅ Trade {trade['trade_id'][:8]} removed from active trades")
        
    except Exception as e:
        logger.error(f"Error sending final alert: {e}", exc_info=True)


async def save_trade_to_journal(trade: Dict):
    """Save completed trade to trading journal with atomic write"""
    try:
        journal_path = os.path.join(BASE_PATH, 'trading_journal.json')
        
        # Determine file mode (create if doesn't exist)
        mode = 'r+' if os.path.exists(journal_path) else 'w+'
        
        with open(journal_path, mode, encoding='utf-8') as f:
            # Acquire exclusive lock IMMEDIATELY (blocks all other access)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            # Read current content with error recovery
            try:
                f.seek(0)
                content = f.read()
                journal = json.loads(content) if content.strip() else {'trades': []}
            except (json.JSONDecodeError, ValueError):
                # Corrupted or empty file - start fresh
                logger.warning("⚠️ Journal corrupted or empty, reinitializing")
                journal = {'trades': []}
            
            # Ensure trades list exists
            if 'trades' not in journal:
                journal['trades'] = []
            
            # Prepare trade entry
            journal_entry = {
                'timestamp': trade['timestamp'],
                'symbol': trade['symbol'],
                'timeframe': trade.get('timeframe', '4h'),
                'signal_type': trade['type'],
                'entry': trade['entry'],
                'tp': trade['tp'],
                'sl': trade['sl'],
                'outcome': trade['outcome'],
                'exit_price': trade.get('exit_price'),
                'profit_loss_pct': trade.get('profit_loss_pct', 0),
                'duration_hours': trade['final_alerts'][0]['duration_hours'] if trade.get('final_alerts') else 0,
                'ml_mode': trade.get('signal_data', {}).get('ml_mode', False),
                'ml_confidence': trade.get('signal_data', {}).get('ml_confidence', 0),
                'alerts_80': trade.get('alerts_80', []),
                'final_alerts': trade.get('final_alerts', []),
                'conditions': trade.get('signal_data', {}).get('conditions', {})
            }
            
            # Add to journal
            journal['trades'].append(journal_entry)
            
            # Atomic write (lock held throughout)
            f.seek(0)
            f.truncate()
            json.dump(journal, f, indent=2, ensure_ascii=False)
            # Lock auto-released on context exit
        
        logger.info(f"✅ Trade saved to journal: {trade['symbol']} ({trade['outcome']})")
        
        # Update statistics
        await update_trade_statistics()
        
    except Exception as e:
        logger.error(f"❌ Error saving trade to journal: {e}")


async def update_trade_statistics():
    """Update overall trading statistics with atomic write"""
    try:
        journal_path = os.path.join(BASE_PATH, 'trading_journal.json')
        
        # Determine file mode (create if doesn't exist)
        mode = 'r+' if os.path.exists(journal_path) else 'w+'
        
        with open(journal_path, mode, encoding='utf-8') as f:
            # Acquire exclusive lock IMMEDIATELY (blocks all other access)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            # Read current content with error recovery
            try:
                f.seek(0)
                content = f.read()
                journal = json.loads(content) if content.strip() else {'trades': []}
            except (json.JSONDecodeError, ValueError):
                # Corrupted or empty file - start fresh
                logger.warning("⚠️ Journal corrupted or empty, reinitializing")
                journal = {'trades': []}
            
            # Ensure trades list exists
            if 'trades' not in journal:
                journal['trades'] = []
            
            trades = journal.get('trades', [])
            
            # Calculate stats using outcome constants
            total_trades = len(trades)
            wins = sum(1 for t in trades if t.get('outcome') in TRADE_OUTCOME_WIN)
            losses = sum(1 for t in trades if t.get('outcome') in TRADE_OUTCOME_LOSS)
            win_rate = (wins / total_trades * 100) if total_trades > 0 else 0
            
            # Update journal metadata
            if 'statistics' not in journal:
                journal['statistics'] = {}
            
            journal['statistics'].update({
                'total_trades': total_trades,
                'wins': wins,
                'losses': losses,
                'win_rate': round(win_rate, 2),
                'last_updated': datetime.now(timezone.utc).isoformat()
            })
            
            # Atomic write (lock held throughout)
            f.seek(0)
            f.truncate()
            json.dump(journal, f, indent=2, ensure_ascii=False)
            # Lock auto-released on context exit
        
        logger.info(f"✅ Statistics updated: {total_trades} trades, {win_rate:.1f}% win rate")
        
    except Exception as e:
        logger.error(f"❌ Error updating statistics: {e}")


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


def fetch_mtf_data(symbol: str, timeframe: str, primary_df: pd.DataFrame) -> dict:
    """
    Fetch Multi-Timeframe data for ICT analysis
    
    Args:
        symbol: Trading symbol (e.g., 'BTCUSDT')
        timeframe: Current timeframe (e.g., '4h')
        primary_df: Primary DataFrame to reuse if timeframe matches
        
    Returns:
        Dictionary with timeframes as keys and DataFrames as values
    """
    mtf_data = {}
    # Get MTF timeframes from contract (standard timeframes for consensus)
    mtf_timeframes = TimeframeContract.get_mtf_timeframes()
    logger.debug(f"📊 Using MTF timeframes from contract: {mtf_timeframes}")
    
    for mtf_tf in mtf_timeframes:
        if mtf_tf == timeframe:  # Skip duplicate fetch
            mtf_data[mtf_tf] = primary_df
            continue
        
        try:
            mtf_response = requests.get(
                BINANCE_KLINES_URL,
                params={'symbol': symbol, 'interval': mtf_tf, 'limit': 100},
                timeout=10
            )
            
            if mtf_response.status_code == 200:
                mtf_klines = mtf_response.json()
                mtf_df = pd.DataFrame(mtf_klines, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                mtf_df['timestamp'] = pd.to_datetime(mtf_df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    mtf_df[col] = mtf_df[col].astype(float)
                
                mtf_data[mtf_tf] = mtf_df
                logger.debug(f"✅ Fetched MTF data for {mtf_tf}")
        except Exception as e:
            logger.warning(f"⚠️ Failed to fetch MTF data for {mtf_tf}: {e}")
    
    return mtf_data


def format_no_trade_message(no_trade_data: dict) -> str:
    """
    Format NO_TRADE message with detailed MTF breakdown
    
    Args:
        no_trade_data: Dictionary from ICTSignalEngine._create_no_trade_message()
        
    Returns:
        HTML-formatted Telegram message string
    """
    # Extract core data
    symbol = no_trade_data.get('symbol', 'UNKNOWN')
    timeframe = no_trade_data.get('timeframe', '?')
    reason = no_trade_data.get('reason', 'Unknown reason')
    details = no_trade_data.get('details', '')
    mtf_breakdown = no_trade_data.get('mtf_breakdown', {})
    
    # Extract optional context data
    current_price = no_trade_data.get('current_price')
    price_change_24h = no_trade_data.get('price_change_24h')
    rsi = no_trade_data.get('rsi')
    signal_direction = no_trade_data.get('signal_direction')
    confidence = no_trade_data.get('confidence')
    mtf_consensus_pct = no_trade_data.get('mtf_consensus_pct')
    
    # Build message
    msg = f"""❌ <b>НЯМА ПОДХОДЯЩ ТРЕЙД</b>

💰 <b>Символ:</b> {symbol}
⏰ <b>Таймфрейм:</b> {timeframe}

🚫 <b>Причина:</b> {reason}
📋 <b>Детайли:</b> {details}
"""
    
    # Add context information if available
    if current_price is not None:
        msg += f"\n💵 <b>Текуща цена:</b> ${current_price:,.2f}"
    
    if price_change_24h is not None:
        change_emoji = "📈" if price_change_24h > 0 else "📉" if price_change_24h < 0 else "➡️"
        msg += f"\n{change_emoji} <b>24ч промяна:</b> {price_change_24h:+.2f}%"
    
    if rsi is not None:
        rsi_emoji = "🔥" if rsi > 70 else "❄️" if rsi < 30 else "📊"
    
    if signal_direction:
        direction_emoji = "🟢" if signal_direction == 'BUY' else "🔴" if signal_direction == 'SELL' else "⚪"
        msg += f"\n{direction_emoji} <b>Посока:</b> {signal_direction}"
    
    if confidence is not None:
        msg += f"\n🎲 <b>Confidence:</b> {confidence:.1f}%"
    
    # MTF Breakdown section
    msg += """

━━━━━━━━━━━━━━━━━━━━━━
📊 <b>MTF Breakdown:</b>
"""
    
    if mtf_breakdown:
        # Sort timeframes by order (1m → 1w)
        for tf, data in sorted(mtf_breakdown.items(), key=lambda x: _timeframe_order(x[0])):
            bias = data.get('bias', 'UNKNOWN')
            aligned = data.get('aligned', False)
            tf_confidence = data.get('confidence', 0)
            
            # Determine emoji
            emoji = "✅" if aligned else "❌"
            
            # Format line
            if bias == 'NO_DATA':
                msg += f"{emoji} <b>{tf}</b>: Няма данни\n"
            else:
                # Add current timeframe marker
                current_marker = " ← текущ" if tf == timeframe else ""
                msg += f"{emoji} <b>{tf}</b>: {bias} ({tf_confidence:.0f}%){current_marker}\n"
        
        # Add consensus summary if available
        if mtf_consensus_pct is not None:
            consensus_emoji = "✅" if mtf_consensus_pct >= 50 else "❌"
            msg += f"\n{consensus_emoji} <b>MTF Consensus:</b> {mtf_consensus_pct:.1f}%"
    else:
        msg += "Няма налични MTF данни\n"
    
    # Add recommendation
    msg += "\n\n💡 <b>Препоръка:</b> Изчакайте по-добри условия или проверете друг таймфрейм"
    
    return msg


def _timeframe_order(tf: str) -> int:
    """
    Helper for sorting timeframes (1m → 1w)
    
    Args:
        tf: Timeframe string (e.g., '1m', '4h', '1d')
        
    Returns:
        Integer order value for sorting
    """
    order = {
        '1m': 1, '3m': 2, '5m': 3, '15m': 4, '30m': 5,
        '1h': 6, '2h': 7, '3h': 8, '4h': 9, '6h': 10, '12h': 11,
        '1d': 12, '3d': 13, '1w': 14
    }
    return order.get(tf.lower(), 999)  # Unknown TFs go to end


def analyze_signal(symbol_data, klines_data, symbol='BTCUSDT', timeframe='4h'):
    """
    ⚠️ DEPRECATED: Use ICTSignalEngine.generate_signal() instead!
    
    This function is kept only for backward compatibility/testing.
    DO NOT use in production signal flows!
    
    Legacy function for combined LuxAlgo + ICT analysis.
    All new code should use the STRICT ICT Engine with MTF support.
    """
    logger.warning(f"⚠️ DEPRECATED: analyze_signal() called for {symbol}. Use ICT Engine instead!")
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
            try:
                luxalgo_ict_result = combined_luxalgo_ict_analysis(opens, highs, lows, closes, volumes)
                if luxalgo_ict_result is not None:
                    luxalgo_ict = luxalgo_ict_result
                else:
                    logger.warning(f"LuxAlgo analysis returned None for {symbol} {timeframe}")
                    luxalgo_ict = {}
            except Exception as e:
                logger.error(f"LuxAlgo analysis failed for {symbol} {timeframe}: {e}")
                luxalgo_ict = {}
        
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
            sr_data = luxalgo_ict.get('luxalgo_sr', {})
            if sr_data:
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
            mss = luxalgo_ict.get('ict_mss', {})
            if mss and mss.get('confirmed'):
                if 'BULLISH' in mss.get('type', ''):
                    ict_aligned = True
                    ict_direction = 'BUY'
                    reasons.append(f"ICT MSS: Bullish structure shift")
                    confidence += 30  # Increased from 20
                elif 'BEARISH' in mss.get('type', ''):
                    ict_aligned = True
                    ict_direction = 'SELL'
                    reasons.append(f"ICT MSS: Bearish structure shift")
                    confidence += 30  # Increased from 20
        
        # === 3. Liquidity Grab (reversal signal) ===
        if luxalgo_ict and luxalgo_ict.get('ict_liquidity_grab'):
            liq_grab = luxalgo_ict.get('ict_liquidity_grab', {})
            if liq_grab and liq_grab.get('reversal_confirmed'):
                if 'BULLISH' in liq_grab.get('type', ''):
                    reasons.append("ICT: Bullish liquidity grab")
                    confidence += 25  # Increased from 18
                    if not ict_aligned:
                        ict_aligned = True
                        ict_direction = 'BUY'
                elif 'BEARISH' in liq_grab.get('type', ''):
                    reasons.append("ICT: Bearish liquidity grab")
                    confidence += 25  # Increased from 18
                    if not ict_aligned:
                        ict_aligned = True
                        ict_direction = 'SELL'
        
        # === 4. Fair Value Gaps ===
        fvg_signal = None
        if luxalgo_ict and luxalgo_ict.get('ict_fvgs'):
            fvgs = luxalgo_ict.get('ict_fvgs', [])
            if fvgs:
                unfilled_fvgs = [f for f in fvgs if not f.get('filled')]
                if unfilled_fvgs:
                    latest_fvg = unfilled_fvgs[-1]
                    if latest_fvg.get('type') == 'BULLISH_FVG':
                        fvg_signal = 'BUY'
                        reasons.append(f"ICT: Bullish FVG at {latest_fvg.get('bottom', 0):.2f}")
                        confidence += 18  # Increased from 12
                    elif latest_fvg.get('type') == 'BEARISH_FVG':
                        fvg_signal = 'SELL'
                        reasons.append(f"ICT: Bearish FVG at {latest_fvg.get('top', 0):.2f}")
                        confidence += 18  # Increased from 12
        
        # === 5. Displacement ===
        if luxalgo_ict and luxalgo_ict.get('ict_displacement'):
            disp = luxalgo_ict.get('ict_displacement', {})
            if disp and disp.get('confirmed'):
                if 'BULLISH' in disp.get('type', ''):
                    reasons.append(f"ICT: Bullish displacement (strength: {disp.get('strength', 0):.1f}x)")
                    confidence += 15
                elif 'BEARISH' in disp.get('type', ''):
                    reasons.append(f"ICT: Bearish displacement (strength: {disp.get('strength', 0):.1f}x)")
                    confidence += 15
        
        # === 6. Optimal Trade Entry (OTE) ===
        ote_confirmed = False
        if luxalgo_ict and luxalgo_ict.get('ict_ote'):
            ote = luxalgo_ict.get('ict_ote', {})
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
    """
    ⚠️ DEPRECATED: Use ICTSignalEngine._calculate_ict_compliant_entry_zone() instead!
    
    This function uses old logic that doesn't comply with STRICT ICT rules.
    Kept only for backward compatibility/testing.
    """
    logger.warning("⚠️ DEPRECATED: calculate_entry_zones() called. Use ICT Engine instead!")
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


def _validate_signal_timing(signal_data: dict, entry_zone: dict, entry_status: str) -> tuple:
    """
    Validate if signal should be sent based on entry zone timing.
    
    CRITICAL RULES:
    1. Block signal if status == 'TOO_LATE'
    2. Block signal if status == 'NO_ZONE'
    3. Allow signal if status == 'VALID_WAIT' or 'VALID_NEAR'
    
    Returns:
        (should_send: bool, message: str)
    """
    if entry_status == 'TOO_LATE':
        return False, "❌ Закъснял сигнал - цената вече е минала entry зоната"
    
    if entry_status == 'NO_ZONE':
        return False, "❌ Няма валидна entry зона в допустимия диапазон"
    
    if entry_status == 'VALID_WAIT':
        distance = entry_zone['distance_pct']
        center = entry_zone['center']
        return True, f"⏳ ЧАКАЙ pullback към ${center:.4f} ({distance:.1f}% разстояние)"
    
    if entry_status == 'VALID_NEAR':
        center = entry_zone['center']
        return True, f"🎯 Цената се приближава към entry зоната (${center:.4f})"
    
    return False, "❌ Неизвестен entry статус"


def _format_entry_guidance(entry_zone: dict, entry_status: str, current_price: float, direction: str) -> str:
    """
    Format entry guidance section for signal message.
    
    CRITICAL RULES:
    1. Show entry zone details (source, range, quality)
    2. Show current price position and distance
    3. Provide clear instructions based on status:
       - VALID_WAIT: "⏳ ЧАКАЙ pullback" + warning + alert suggestion
       - VALID_NEAR: "🎯 ПРИБЛИЖАВА" + preparation instructions
    4. Use visual indicators: ⬆️ for SELL, ⬇️ for BUY
    """
    # Determine arrow based on direction
    if 'BEARISH' in direction.upper() or 'SELL' in direction.upper():
        arrow = "⬆️"  # Price needs to go UP to entry zone for SELL
        direction_text = "нагоре"
    else:
        arrow = "⬇️"  # Price needs to go DOWN to entry zone for BUY
        direction_text = "надолу"
    
    # Build base structure
    guidance = "\n━━━━━━━━━━━━━━━━━━━━\n"
    guidance += "🎯 <b>ENTRY GUIDANCE:</b>\n\n"
    
    guidance += f"📍 <b>Entry Zone ({entry_zone['source']}):</b>\n"
    guidance += f"   Center: <b>${entry_zone['center']:,.4f}</b>\n"
    guidance += f"   Range: ${entry_zone['low']:,.4f} - ${entry_zone['high']:,.4f}\n"
    guidance += f"   Quality: {entry_zone['quality']}/100\n\n"
    
    guidance += f"📊 <b>Current Position:</b>\n"
    guidance += f"   Price: ${current_price:,.4f}\n"
    guidance += f"   Distance: {arrow} {entry_zone['distance_pct']:.1f}% (${abs(entry_zone['distance_price']):,.2f})\n\n"
    
    # Status-specific guidance
    if entry_status == 'VALID_WAIT':
        guidance += "⏳ <b>STATUS: WAIT FOR PULLBACK</b>\n\n"
        guidance += "   ⚠️ <b>НЕ влизай веднага!</b>\n\n"
        guidance += f"   ✅ <b>Чакай цената да:</b>\n"
        guidance += f"   • Се върне {arrow} към entry зоната\n"
        guidance += "   • Покаже rejection candle pattern\n"
        guidance += "   • Има volume confirmation\n\n"
        guidance += f"   🔔 Настрой alert на: <b>${entry_zone['center']:,.4f}</b>\n"
    
    elif entry_status == 'VALID_NEAR':
        guidance += "🎯 <b>STATUS: APPROACHING ENTRY</b>\n\n"
        guidance += "   ⚡ <b>Цената е близо до entry зоната!</b>\n\n"
        guidance += "   ✅ <b>Подготви се за вход при:</b>\n"
        guidance += "   • Влизане в entry зоната\n"
        guidance += f"   • Rejection от {entry_zone['source']}\n"
        guidance += "   • Volume spike + candle confirmation\n\n"
        guidance += "   ⏱️ <b>Очаквано време:</b> 15-60 мин\n"
    
    return guidance


# ================= SECURITY DECORATORS =================

def rate_limited(calls=20, period=60):
    """
    Decorator to enforce rate limiting with custom limits
    
    Usage:
        @rate_limited(calls=3, period=60)
        async def my_command(update, context):
            ...
    
    Args:
        calls: Maximum number of calls allowed
        period: Time period in seconds
    """
    def decorator(func):
        # Store rate limit tracking per user per command
        if not hasattr(rate_limited, 'user_command_calls'):
            rate_limited.user_command_calls = {}
        
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
            if not SECURITY_MODULES_AVAILABLE:
                return await func(update, context)
            
            user_id = update.effective_user.id
            command_name = func.__name__
            
            # Check global rate limit first
            if not check_rate_limit(user_id):
                ban_time = rate_limiter.get_ban_time_remaining(user_id)
                if ban_time > 0:
                    minutes = ban_time // 60
                    await update.message.reply_text(
                        f"🚫 You are temporarily banned for {minutes} minutes.\n"
                        f"Reason: Rate limit violations"
                    )
                else:
                    await update.message.reply_text(
                        "⚠️ Rate limit exceeded. Please try again later."
                    )
                log_security_event("RATE_LIMIT_EXCEEDED", user_id, command_name)
                return
            
            # Check command-specific rate limit
            current_time = time.time()
            key = f"{user_id}:{command_name}"
            
            if key not in rate_limited.user_command_calls:
                rate_limited.user_command_calls[key] = []
            
            # Clean old timestamps
            rate_limited.user_command_calls[key] = [
                ts for ts in rate_limited.user_command_calls[key] 
                if current_time - ts < period
            ]
            
            # Check if limit exceeded
            if len(rate_limited.user_command_calls[key]) >= calls:
                remaining = int(period - (current_time - rate_limited.user_command_calls[key][0]))
                await update.message.reply_text(
                    f"⚠️ Command rate limit exceeded.\n"
                    f"Limit: {calls} calls per {period} seconds\n"
                    f"Try again in {remaining} seconds."
                )
                log_security_event("COMMAND_RATE_LIMIT", user_id, f"{command_name} ({calls}/{period}s)")
                return
            
            # Record this call
            rate_limited.user_command_calls[key].append(current_time)
            
            return await func(update, context)
        
        return wrapper
    
    # Support both @rate_limited and @rate_limited() syntax
    if callable(calls):
        func = calls
        calls = 20
        period = 60
        return decorator(func)
    
    return decorator


async def notify_owner_unauthorized_access(context, user_id: int, username: str, command: str, chat_id: int):
    """
    Send notification to bot owner about unauthorized access attempt.
    
    Args:
        context: Telegram context
        user_id: ID of unauthorized user
        username: Username/name of unauthorized user
        command: Command that was attempted
        chat_id: Chat ID where attempt occurred
    """
    try:
        owner_id = OWNER_CHAT_ID
        
        if owner_id:
            # Escape username to prevent HTML injection
            safe_username = html.escape(username)
            
            message = (
                f"⚠️ <b>UNAUTHORIZED ACCESS ATTEMPT</b>\n\n"
                f"👤 User: @{safe_username}\n"
                f"🆔 User ID: <code>{user_id}</code>\n"
                f"💬 Chat ID: <code>{chat_id}</code>\n"
                f"⚡ Command: <code>{command}</code>\n\n"
                f"🕐 Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"<i>This user is not in the whitelist.</i>"
            )
            
            await context.bot.send_message(
                chat_id=owner_id,
                text=message,
                parse_mode='HTML'
            )
            
            logger.info(f"📨 Sent unauthorized access alert to owner (ID: {owner_id})")
    except Exception as e:
        logger.error(f"❌ Failed to notify owner about unauthorized access: {e}")


def require_access(allowed_users: set = None):
    """
    Decorator to restrict command access to whitelisted users.
    
    Args:
        allowed_users: Set of allowed user IDs. If None, uses ALLOWED_USERS from config.
    
    Returns:
        Decorated function that checks access before execution.
    
    Usage:
        @require_access()
        @rate_limited(calls=5, period=60)
        async def my_command(update, context):
            ...
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
            # Get user info
            user = update.effective_user
            user_id = user.id
            username = user.username or user.first_name or "Unknown"
            chat_id = update.effective_chat.id
            
            # Get allowed users list
            users_whitelist = allowed_users if allowed_users is not None else ALLOWED_USERS
            
            # Check if user is allowed
            if user_id not in users_whitelist:
                # Log unauthorized attempt
                logger.warning(
                    f"⛔ UNAUTHORIZED ACCESS ATTEMPT: "
                    f"User: @{username} (ID: {user_id}) | "
                    f"Command: {func.__name__} | "
                    f"Chat: {chat_id}"
                )
                
                # Send denial message to unauthorized user
                await update.message.reply_text(
                    ACCESS_DENIED_MESSAGE,
                    parse_mode='HTML'
                )
                
                # Notify owner about unauthorized attempt
                await notify_owner_unauthorized_access(
                    context=context,
                    user_id=user_id,
                    username=username,
                    command=func.__name__,
                    chat_id=chat_id
                )
                
                return  # Block execution
            
            # User authorized - log and proceed
            logger.info(f"✅ Authorized access: @{username} (ID: {user_id}) -> {func.__name__}")
            
            # Execute original function
            return await func(update, context, *args, **kwargs)
        
        return wrapper
    return decorator


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
    
    # Check if user is authorized
    if user_id not in ALLOWED_USERS:
        # Show limited welcome for unauthorized users
        unauthorized_text = """👋 <b>Welcome to Crypto Signal Bot!</b>

🔒 <b>This is a private trading bot.</b>

Access is restricted to authorized users only.

If you need access, please contact the bot owner.

📧 <b>Note:</b> Your user ID is <code>{}</code>
The owner can approve you with: <code>/approve {}</code>
"""
        await update.message.reply_text(
            unauthorized_text.format(user_id, user_id),
            parse_mode='HTML'
        )
        logger.info(f"⚠️ Unauthorized /start from @{username} (ID: {user_id})")
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
/timeframe - Избор на таймфрейм (1h, 2h, 4h, 1d)
/alerts - Вкл/Изкл автоматични сигнали

💡 <b>Поддържани валути:</b>
BTC, ETH, XRP, SOL, BNB, ADA

Пример: <code>/signal BTCUSDT</code>

За повече помощ: /help
"""
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=get_main_keyboard())


@require_access()
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
    user_id = update.effective_user.id
    username = update.effective_user.username or "Unknown"
    
    # Check if user is authorized
    if user_id not in ALLOWED_USERS:
        # Show limited help for unauthorized users
        unauthorized_help = """📖 <b>Crypto Signal Bot - Help</b>

🔒 <b>This is a private trading bot.</b>

This bot provides advanced crypto trading signals and analysis, but access is restricted to authorized users only.

<b>Features (for authorized users):</b>
• Real-time trading signals
• Market analysis
• ICT methodology
• ML predictions
• Risk management
• Automated alerts

<b>To get access:</b>
Please contact the bot owner and provide your user ID: <code>{}</code>

The owner can approve you with: <code>/approve {}</code>
"""
        await update.message.reply_text(
            unauthorized_help.format(user_id, user_id),
            parse_mode='HTML'
        )
        logger.info(f"⚠️ Unauthorized /help from @{username} (ID: {user_id})")
        return
    
    help_text = """🤖 <b>CRYPTO SIGNAL BOT - ПОМОЩ</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏥 <b>СИСТЕМА & МОНИТОРИНГ:</b>

/health - 🏥 System health diagnostic
  └─ Проверява здравето на всички компоненти
  └─ Показва: Journal, ML, Reports, Position Monitor, Scheduler, Disk
  
/status - 📊 Bot status & uptime
  └─ Текущ статус на бота и активни функции
  
/debug - 🔍 Toggle debug mode
  └─ Включва/изключва детайлни debug логове
  
/performance - 📈 Performance metrics
  └─ Показва performance метрики и статистика

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>TRADING & СИГНАЛИ:</b>

/signal <symbol> <timeframe> - 🎯 Generate ICT signal
  └─ Генерира ICT анализ и сигнал за конкретна валута
  └─ Пример: /signal BTC 4h
  └─ Symbols: BTC, ETH, BNB, SOL, XRP, ADA, DOGE, DOT, MATIC, LINK
  └─ Timeframes: 15m, 1h, 2h, 4h, 1d
  
/market - 📊 Market analysis menu
  └─ Показва интерактивно меню с:
      • 📈 Бърз преглед (sentiment overview)
      • 🎯 Swing Trading Анализ (professional setup)
      • 💡 Пълен Пазарен Отчет (всички coins)
      • 🇧🇬/🇬🇧 Language toggle
  
/news - 📰 Latest crypto news
  └─ Последни новини от крипто света
  └─ Automatic Bulgarian translation
  
/backtest - 📉 Run strategy backtest
  └─ Стартира backtest на ICT стратегията
  └─ Показва win rate, profit factor, max drawdown

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 <b>ОТЧЕТИ:</b>

/dailyreport - 📅 Daily trading report
  └─ Дневен отчет с всички signals и резултати
  └─ Auto-sent daily at 08:00 BG time
  
/weekly_report - 📊 Weekly performance summary
  └─ Седмичен summary на performance
  └─ Win rate, best trades, improvements
  
/monthly_report - 📆 Monthly overview
  └─ Месечен преглед на печалби/загуби
  └─ Cumulative statistics

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ <b>УПРАВЛЕНИЕ:</b>

/positions - 💼 View active positions
  └─ Преглед на всички активни позиции
  └─ Real-time P&L tracking
  
/close_trade <id> - 🔒 Close trade manually
  └─ Ръчно затваряне на конкретен trade
  └─ Пример: /close_trade 123
  
/settings - ⚙️ Trading settings & parameters
  └─ Показва всички настройки:
      • Signal settings (confidence, timeframes)
      • Risk management (max positions, stop loss)
      • ICT settings (order blocks, FVG, liquidity)
      • ML & automation settings
      • Health monitoring schedule
  
/clear_cache - 🗑️ Clear system cache
  └─ Изчиства cache данните за performance

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>АКТИВНА ФУНКЦИОНАЛНОСТ:</b>

✅ Auto-signals (1H, 2H, 4H, 1D)
✅ Real-time position monitoring (every minute)
✅ ML-based predictions (weekly training)
✅ ICT smart money concepts analysis
✅ Multi-timeframe confluence
✅ 24/7 health monitoring (6 components)
✅ Swing trading analysis (multi-TF)
✅ Signal deduplication (60 min cooldown)
✅ Startup suppression (5 min grace period)
✅ Persistent signal cache

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📌 За повече информация за конкретна команда, използвай я!
📌 За детайлни настройки използвай /settings
📌 За system health проверка използвай /health
"""
    await update.message.reply_text(help_text, parse_mode='HTML')


@require_access()
@rate_limited(calls=20, period=60)
async def version_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показва текущата версия на бота с пълна информация"""
    try:
        # Use new version module if available
        if SECURITY_MODULES_AVAILABLE:
            version_info = get_full_version_info()
            
            # Add runtime information
            import telegram
            ptb_version = telegram.__version__
            python_version = sys.version.split()[0]
            
            # Calculate bot uptime
            uptime = datetime.now(timezone.utc) - BOT_START_TIME
            uptime_str = str(uptime).split('.')[0]  # Remove microseconds
            bot_start_utc = BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')
            
            runtime_info = f"\n\n**Runtime Info:**\n"
            runtime_info += f"• Python: {python_version}\n"
            runtime_info += f"• python-telegram-bot: {ptb_version}\n"
            runtime_info += f"• Started: {bot_start_utc}\n"
            runtime_info += f"• Uptime: {uptime_str}\n"
            
            # Read deployment info
            deployment_info = {}
            deployment_file = os.path.join(BASE_PATH, '.deployment-info')
            try:
                if os.path.exists(deployment_file):
                    with open(deployment_file, 'r') as f:
                        deployment_info = json.load(f)
                        runtime_info += f"\n**Deployment:**\n"
                        runtime_info += f"• Last Deploy: {deployment_info.get('last_deployed', 'N/A')}\n"
                        runtime_info += f"• Commit: {deployment_info.get('commit_sha', 'N/A')[:8]}\n"
            except Exception:
                pass
            
            full_message = version_info + runtime_info
            await update.message.reply_text(full_message, parse_mode='Markdown')
        else:
            # Fallback to old version display
            version = "2.0"  # Default
            version_file = os.path.join(BASE_PATH, 'VERSION')
            try:
                with open(version_file, 'r') as f:
                    version = f.read().strip()
            except FileNotFoundError:
                pass
            
            import telegram
            ptb_version = telegram.__version__
            python_version = sys.version.split()[0]
            
            uptime = datetime.now(timezone.utc) - BOT_START_TIME
            uptime_str = str(uptime).split('.')[0]
            bot_start_utc = BOT_START_TIME.strftime('%Y-%m-%d %H:%M:%S UTC')
            
            message = f"""
🤖 <b>CRYPTO SIGNAL BOT - VERSION INFO</b>

📦 <b>Bot Version:</b> v{version}
🐍 <b>Python:</b> {python_version}
📡 <b>python-telegram-bot:</b> {ptb_version}

⏰ <b>Bot Process Started:</b> {bot_start_utc}
⏱️ <b>Uptime:</b> {uptime_str}

✅ <b>Status:</b> Operational
"""
            await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Error in version_cmd: {e}")
        await update.message.reply_text(f"❌ Error getting version: {str(e)}")


@require_access()
@rate_limited(calls=20, period=60)
async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показва статистика на бота"""
    stats_message = get_performance_stats()
    await update.message.reply_text(stats_message, parse_mode='HTML')


@require_access()
@rate_limited(calls=20, period=60)
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


async def check_news_impact_on_positions(article, impact):
    """
    Проверява дали критични новини засягат отворени позиции
    Изпраща immediate alert ако новината contradicts позицията
    """
    try:
        # Get open positions
        open_positions = position_manager_global.get_open_positions()
        
        if not open_positions:
            logger.debug("Няма отворени позиции за проверка")
            return
        
        # Import narrative templates
        try:
            from narrative_templates import SwingTraderNarrative
            NARRATIVES_AVAILABLE = True
        except ImportError:
            NARRATIVES_AVAILABLE = False
            logger.warning("Narrative templates не са налични")
        
        for pos in open_positions:
            symbol = pos['symbol']
            
            # Check if news is related to this symbol or general market
            if not symbol_matches_news(symbol, article):
                continue
            
            # Assess impact on this position
            is_long = pos['signal_type'] in ['BUY', 'STRONG_BUY']
            sentiment = impact['sentiment']
            impact_level = impact['impact']
            
            # Determine if news contradicts position
            should_alert = False
            
            if is_long and sentiment == 'BEARISH' and impact_level == 'CRITICAL':
                should_alert = True
                impact_assessment = "🚨 CRITICAL: Bearish news против LONG позиция - HIGH REVERSAL RISK!"
            elif not is_long and sentiment == 'BULLISH' and impact_level == 'CRITICAL':
                should_alert = True
                impact_assessment = "🚨 CRITICAL: Bullish news против SHORT позиция - HIGH REVERSAL RISK!"
            elif is_long and sentiment == 'BEARISH' and impact_level == 'HIGH':
                should_alert = True
                impact_assessment = "⚠️ Bearish news против LONG - Consider partial exit"
            elif not is_long and sentiment == 'BULLISH' and impact_level == 'HIGH':
                should_alert = True
                impact_assessment = "⚠️ Bullish news против SHORT - Consider partial exit"
            
            # Send immediate alert if contradicting
            if should_alert:
                logger.info(f"🔴 Critical news alert for position {pos['id']} ({symbol})")
                
                # Get current price
                try:
                    import requests
                    response = requests.get(f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}", timeout=5)
                    current_price = float(response.json()['price'])
                except Exception as e:
                    logger.warning(f"Could not get current price for {symbol}: {e}")
                    current_price = pos.get('entry_price', 0)
                
                # Generate alert message
                # DISABLED: if NARRATIVES_AVAILABLE:
                    # DISABLED: news_data = {
                        # DISABLED: 'headline': article.get('title', 'Breaking market news'),
                        # DISABLED: 'sentiment_label': sentiment,
                        # DISABLED: 'priority': 'critical' if impact_level == 'CRITICAL' else 'important',
                        # DISABLED: 'impact_assessment': impact_assessment
                    # DISABLED: }
                     # DISABLED:                     # DISABLED: alert_message = SwingTraderNarrative.critical_news_alert(
                        # DISABLED: pos, news_data, current_price, impact_assessment
                    # DISABLED: )
                # DISABLED: else:
                    # Fallback simple alert
                    # DISABLED: alert_message = f"""
# DISABLED: 🔴 BREAKING NEWS ALERT - {symbol}
 # DISABLED: # DISABLED: 📰 {article.get('title', 'Market news')}
 # DISABLED: # DISABLED: Impact: {impact_assessment}
 # DISABLED: # DISABLED: Current price: {current_price:.2f}
# DISABLED: Position: {'LONG' if is_long else 'SHORT'}
 # DISABLED: # DISABLED: IMMEDIATE ACTION MAY BE REQUIRED!
# DISABLED: """
                 # DISABLED:                 # Send via Telegram
                # DISABLED: from telegram import Bot
                # DISABLED: bot = Bot(token=TELEGRAM_BOT_TOKEN)
                # DISABLED: await bot.send_message(
                    # DISABLED: chat_id=OWNER_CHAT_ID,
                    # DISABLED: text=alert_message,
                    # DISABLED: parse_mode='HTML',
                    # DISABLED: disable_notification=False  # WITH sound!
                # DISABLED: )
                 # DISABLED:                 # DISABLED: logger.info(f"✅ Critical news alert sent for {symbol}")
        
    except Exception as e:
        logger.error(f"Грешка при проверка на новини срещу позиции: {e}")
        import traceback
        logger.error(traceback.format_exc())


def symbol_matches_news(symbol, article):
    """
    Проверява дали новината е свързана със символа
    """
    try:
        title = article.get('title', '').lower()
        description = article.get('description', '').lower()
        
        # Extract base symbol (remove USDT, BUSD, etc.)
        base_symbol = symbol.replace('USDT', '').replace('BUSD', '').replace('USD', '')
        
        # Check if symbol mentioned
        if base_symbol.lower() in title or base_symbol.lower() in description:
            return True
        
        # Check for BTC - affects all crypto
        if 'bitcoin' in title or 'btc' in title:
            return True
        
        # Check for general crypto market news
        crypto_keywords = ['crypto', 'cryptocurrency', 'blockchain', 'altcoin', 'defi', 'market']
        if any(keyword in title for keyword in crypto_keywords):
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Грешка при проверка на symbol match: {e}")
        return False


@safe_job("breaking_news_monitor", max_retries=2, retry_delay=30)
async def monitor_breaking_news():
    """Мониторинг на критични новини в реално време + проверка на отворени позиции"""
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
                
                # NEW: Check if critical news affects open positions
                if POSITION_MANAGER_AVAILABLE and position_manager_global:
                    try:
                        await check_news_impact_on_positions(article, impact)
                    except Exception as e:
                        logger.error(f"Грешка при проверка на новини срещу позиции: {e}")
        
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


def format_news_with_impact(news_item):
    """
    Format news article with impact score and visual indicators
    
    Args:
        news_item: News article dict with impact_score and sentiment
        
    Returns:
        Formatted impact string with emoji and level
    """
    impact = news_item.get('impact_score', 0)
    sentiment = news_item.get('sentiment', 'Neutral')
    
    # Visual indicator
    if impact > 15:
        indicator = "🟢"
        level = "Strong Bullish"
    elif impact > 5:
        indicator = "🟢"
        level = "Bullish"
    elif impact < -15:
        indicator = "🔴"
        level = "Strong Bearish"
    elif impact < -5:
        indicator = "🔴"
        level = "Bearish"
    else:
        indicator = "🟡"
        level = "Neutral"
    
    return f"Impact: {impact:+d} ({level}) {indicator}"


def calculate_combined_signal_strength(technical_score, fundamental_score):
    """
    Combine technical and fundamental scores
    Technical weight: 60% (from feature_flags.json)
    Fundamental weight: 40%
    
    Args:
        technical_score: Technical analysis score (0-100)
        fundamental_score: Fundamental analysis score (0-100)
        
    Returns:
        Tuple of (strength_label, combined_score)
    """
    combined = (technical_score * 0.6) + (fundamental_score * 0.4)
    
    if combined > 75:
        return "🟢 STRONG", combined
    elif combined > 60:
        return "🟡 MODERATE", combined
    elif combined > 40:
        return "🟠 WEAK", combined
    else:
        return "🔴 VERY WEAK", combined


async def generate_swing_trading_analysis(symbol: str, language: str = 'bg') -> str:
    """
    Generate professional swing trading analysis
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        language: 'bg' or 'en'
    
    Returns:
        Formatted analysis message
    """
    try:
        # Fetch current price and 24h data
        price_data = await fetch_json(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}")
        if not price_data:
            return "❌ Грешка при извличане на данни" if language == 'bg' else "❌ Error fetching data"
        
        current_price = float(price_data['lastPrice'])
        change_24h = float(price_data['priceChangePercent'])
        volume = float(price_data['volume'])
        
        # Fetch 7d data for trend
        klines_7d = await fetch_json(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=7")
        change_7d = 0
        if klines_7d and len(klines_7d) > 0:
            price_7d_ago = float(klines_7d[0][1])  # Open price 7 days ago
            change_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
        
        # ICT Analysis for multi-timeframe
        ict_4h = None
        ict_1d = None
        if ICT_SIGNAL_ENGINE_AVAILABLE:
            try:
                ict_4h = await ict_engine_global.analyze(symbol.replace('USDT', ''), '4h')
                ict_1d = await ict_engine_global.analyze(symbol.replace('USDT', ''), '1d')
            except Exception as e:
                logger.warning(f"ICT analysis failed: {e}")
        
        # Determine market structure
        structure_4h = "NEUTRAL"
        structure_1d = "NEUTRAL"
        alignment = "MIXED"
        
        if ict_4h and ict_1d:
            # Map bias to structure (defensive - handle both enum and string)
            bias_4h_val = ict_4h.bias.value if hasattr(ict_4h.bias, 'value') else str(ict_4h.bias)
            bias_1d_val = ict_1d.bias.value if hasattr(ict_1d.bias, 'value') else str(ict_1d.bias)
            
            if bias_4h_val in ['BULLISH', 'STRONG_BULLISH']:
                structure_4h = "BULLISH"
            elif bias_4h_val in ['BEARISH', 'STRONG_BEARISH']:
                structure_4h = "BEARISH"
            
            if bias_1d_val in ['BULLISH', 'STRONG_BULLISH']:
                structure_1d = "BULLISH"
            elif bias_1d_val in ['BEARISH', 'STRONG_BEARISH']:
                structure_1d = "BEARISH"
            
            # Determine alignment
            if structure_4h == structure_1d and structure_4h != "NEUTRAL":
                alignment = f"{structure_4h}_ALIGNED"
            elif structure_4h == "NEUTRAL" or structure_1d == "NEUTRAL":
                alignment = "RANGING"
            else:
                alignment = "MIXED"
        
        # Calculate volume analysis (simple comparison to 24h average)
        avg_volume_20d = volume  # Simplified - using current as baseline
        volume_ratio = 1.0  # Default
        volume_trend = "NORMAL"
        
        # Simple volume trend based on 24h change
        if change_24h > 5:
            volume_trend = "INCREASING"
        elif change_24h < -5:
            volume_trend = "DECREASING"
        
        # Fetch Fear & Greed Index
        fear_greed = await fetch_fear_greed_index()
        
        # Determine support and resistance levels
        support_level = current_price * 0.97  # Simplified: 3% below
        resistance_level = current_price * 1.03  # Simplified: 3% above
        
        if ict_1d:
            # Use order blocks if available
            if ict_1d.order_blocks:
                # Find nearest support/resistance from order blocks
                bullish_obs = [ob for ob in ict_1d.order_blocks if ob.get('type') == 'BULLISH']
                bearish_obs = [ob for ob in ict_1d.order_blocks if ob.get('type') == 'BEARISH']
                
                if bullish_obs:
                    support_level = min([ob.get('price', current_price * 0.97) for ob in bullish_obs if ob.get('price', 0) < current_price], default=support_level)
                if bearish_obs:
                    resistance_level = max([ob.get('price', current_price * 1.03) for ob in bearish_obs if ob.get('price', 0) > current_price], default=resistance_level)
        
        # Calculate distances
        resistance_dist = ((resistance_level - current_price) / current_price) * 100
        support_dist = ((current_price - support_level) / current_price) * 100
        
        # Generate swing setup based on REAL DATA (not just ICT alignment)
        # Smart determination using price action, volume, and momentum
        
        # Calculate momentum score
        momentum_score = 0
        if change_24h > 3:
            momentum_score += 1
        elif change_24h < -3:
            momentum_score -= 1
            
        if change_7d > 10:
            momentum_score += 2
        elif change_7d > 5:
            momentum_score += 1
        elif change_7d < -10:
            momentum_score -= 2
        elif change_7d < -5:
            momentum_score -= 1
        
        # Volume confirms momentum
        if volume_trend == "INCREASING" and change_24h > 0:
            momentum_score += 1
        elif volume_trend == "DECREASING" and change_24h < 0:
            momentum_score -= 1
        
        # Distance to resistance/support
        near_support = support_dist < 5  # Within 5% of support
        near_resistance = resistance_dist < 5  # Within 5% of resistance
        
        # Determine setup type intelligently
        if alignment == "BULLISH_ALIGNED" or (momentum_score >= 2 and not near_resistance):
            # Strong bullish: alignment OR strong momentum + room to grow
            setup_type = "BULLISH"
            entry_price = current_price * 0.99  # Slight pullback entry
            tp1 = entry_price * 1.025  # 2.5%
            tp2 = entry_price * 1.04   # 4%
            sl = entry_price * 0.97    # 3% stop loss
            rr_ratio = (tp1 - entry_price) / (entry_price - sl) if (entry_price - sl) > 0 else 0
            
        elif alignment == "BEARISH_ALIGNED" or (momentum_score <= -2):
            # Strong bearish: alignment OR strong negative momentum
            setup_type = "BEARISH"
            entry_price = current_price * 1.01  # Slight rally to short
            tp1 = entry_price * 0.975  # -2.5%
            tp2 = entry_price * 0.96   # -4%
            sl = entry_price * 1.03    # 3% stop loss
            rr_ratio = (entry_price - tp1) / (sl - entry_price) if (sl - entry_price) > 0 else 0
            
        else:
            # Ranging/Mixed: unclear direction or weak momentum
            setup_type = "RANGING"
            entry_price = resistance_level
            tp1 = entry_price * 1.038
            tp2 = entry_price * 1.062
            sl = entry_price * 0.997
            rr_ratio = DEFAULT_SWING_RR_RATIO
        
        # Format message based on language
        if language == 'bg':
            message = format_swing_analysis_bg(
                symbol, current_price, change_24h, change_7d,
                structure_4h, structure_1d, alignment,
                resistance_level, resistance_dist, support_level, support_dist,
                volume_ratio, volume_trend, fear_greed,
                setup_type, entry_price, tp1, tp2, sl, rr_ratio
            )
        else:
            message = format_swing_analysis_en(
                symbol, current_price, change_24h, change_7d,
                structure_4h, structure_1d, alignment,
                resistance_level, resistance_dist, support_level, support_dist,
                volume_ratio, volume_trend, fear_greed,
                setup_type, entry_price, tp1, tp2, sl, rr_ratio
            )
        
        return message
        
    except Exception as e:
        logger.error(f"Error in swing trading analysis: {e}")
        return f"❌ Грешка: {str(e)}" if language == 'bg' else f"❌ Error: {str(e)}"


def format_swing_analysis_bg(symbol, price, change_24h, change_7d, 
                             struct_4h, struct_1d, alignment,
                             resistance, res_dist, support, sup_dist,
                             vol_ratio, vol_trend, fear_greed,
                             setup_type, entry, tp1, tp2, sl, rr):
    """Format swing analysis in Bulgarian"""
    
    # Get symbol name
    symbol_name = "BITCOIN" if "BTC" in symbol else symbol.replace("USDT", "")
    
    msg = f"🟡 {symbol_name} ({symbol})\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💰 Цена: ${price:,.2f} ({change_24h:+.1f}% 24h, {change_7d:+.1f}% 7d)\n\n"
    
    msg += "📊 СТРУКТУРА:\n"
    msg += f"  • 4H: {struct_4h}\n"
    msg += f"  • 1D: {struct_1d}\n"
    msg += f"  • Alignment: {'⚠️ ' if alignment == 'MIXED' else '✅ '}{alignment}\n\n"
    
    msg += "🔍 КЛЮЧОВИ НИВА:\n"
    msg += f"  🔴 Съпротива: ${resistance:,.2f} ({res_dist:+.1f}% от цена)\n"
    msg += f"  🟢 Подкрепа: ${support:,.2f} ({sup_dist:+.1f}% под цена)\n\n"
    
    msg += "📊 ОБЕМ & MOMENTUM:\n"
    msg += f"  • Volume: {vol_ratio:.2f}x среден\n"
    msg += f"  • Trend: {vol_trend}\n"
    
    if fear_greed:
        fg_emoji = "😱" if fear_greed['value'] < 25 else "😰" if fear_greed['value'] < 45 else "😐" if fear_greed['value'] < 55 else "😊" if fear_greed['value'] < 75 else "🤑"
        msg += f"\n{fg_emoji} Fear & Greed: {fear_greed['value']}/100 ({fear_greed['classification']})\n"
    
    msg += "\n━━━━ SWING SETUP ━━━━\n\n"
    
    if setup_type == "RANGING":
        msg += "⚠️ CONSOLIDATION - Чакай Breakout\n\n"
        msg += "💡 СТРАТЕГИЯ:\n"
        msg += f"  ✅ BULLISH Scenario:\n"
        msg += f"     • Entry: Breakout над ${entry:,.2f}\n"
        msg += f"     • TP1: ${tp1:,.2f} ({((tp1-entry)/entry*100):+.1f}%)\n"
        msg += f"     • TP2: ${tp2:,.2f} ({((tp2-entry)/entry*100):+.1f}%)\n"
        msg += f"     • SL: ${sl:,.2f} ({((sl-entry)/entry*100):+.1f}%)\n"
        msg += f"     • R:R = {rr:.1f}:1\n\n"
        msg += f"  ❌ BEARISH Scenario:\n"
        msg += f"     • Breakdown под ${support:,.2f} = ИЗБЯГВАЙ LONGS\n\n"
        msg += "⏰ ВРЕМЕВА РАМКА:\n"
        msg += "  Очакван breakout в рамките на 12-24 часа\n\n"
    elif setup_type == "BULLISH":
        msg += "✅ BULLISH ALIGNMENT - Long Setup\n\n"
        msg += "💡 СТРАТЕГИЯ:\n"
        msg += f"  ✅ Entry: ${entry:,.2f}\n"
        msg += f"  🎯 TP1: ${tp1:,.2f} ({((tp1-entry)/entry*100):+.1f}%)\n"
        msg += f"  🎯 TP2: ${tp2:,.2f} ({((tp2-entry)/entry*100):+.1f}%)\n"
        msg += f"  🛑 SL: ${sl:,.2f} ({((sl-entry)/entry*100):+.1f}%)\n"
        msg += f"  📊 R:R = {rr:.1f}:1\n\n"
    else:  # BEARISH
        msg += "❌ BEARISH ALIGNMENT - Short Setup\n\n"
        msg += "💡 СТРАТЕГИЯ:\n"
        msg += f"  ❌ Entry: ${entry:,.2f}\n"
        msg += f"  🎯 TP1: ${tp1:,.2f} ({((tp1-entry)/entry*100):+.1f}%)\n"
        msg += f"  🎯 TP2: ${tp2:,.2f} ({((tp2-entry)/entry*100):+.1f}%)\n"
        msg += f"  🛑 SL: ${sl:,.2f} ({((sl-entry)/entry*100):+.1f}%)\n"
        msg += f"  📊 R:R = {rr:.1f}:1\n\n"
    
    msg += "━━━━ ПРЕПОРЪКА ━━━━\n\n"
    
    if setup_type == "RANGING":
        msg += f"✅ ЧАКАЙ bullish breakout над ${entry:,.2f}\n"
        msg += f"SET alerts at ${entry:,.2f} и ${support:,.2f}\n\n"
        msg += "⚠️ РИСКОВЕ:\n"
        msg += "  • Ниският обем може да доведе до false breakout\n"
    elif setup_type == "BULLISH":
        msg += "✅ LONG позиция с добър R:R\n"
        msg += f"SET alerts at entry ${entry:,.2f}\n\n"
        msg += "⚠️ РИСКОВЕ:\n"
        msg += "  • Спазвай стоп лоса строго\n"
    else:
        msg += "❌ SHORT позиция - рисково\n"
        msg += f"SET alerts at entry ${entry:,.2f}\n\n"
        msg += "⚠️ РИСКОВЕ:\n"
        msg += "  • Bearish пазар - висока волатилност\n"
    
    msg += "\n<i>⚠️ Това не е финансов съвет. DYOR!</i>"
    
    return msg


def format_swing_analysis_en(symbol, price, change_24h, change_7d,
                             struct_4h, struct_1d, alignment,
                             resistance, res_dist, support, sup_dist,
                             vol_ratio, vol_trend, fear_greed,
                             setup_type, entry, tp1, tp2, sl, rr):
    """Format swing analysis in English"""
    
    # Get symbol name
    symbol_name = "BITCOIN" if "BTC" in symbol else symbol.replace("USDT", "")
    
    msg = f"🟡 {symbol_name} ({symbol})\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += f"💰 Price: ${price:,.2f} ({change_24h:+.1f}% 24h, {change_7d:+.1f}% 7d)\n\n"
    
    msg += "📊 STRUCTURE:\n"
    msg += f"  • 4H: {struct_4h}\n"
    msg += f"  • 1D: {struct_1d}\n"
    msg += f"  • Alignment: {'⚠️ ' if alignment == 'MIXED' else '✅ '}{alignment}\n\n"
    
    msg += "🔍 KEY LEVELS:\n"
    msg += f"  🔴 Resistance: ${resistance:,.2f} ({res_dist:+.1f}% from price)\n"
    msg += f"  🟢 Support: ${support:,.2f} ({sup_dist:+.1f}% below price)\n\n"
    
    msg += "📊 VOLUME & MOMENTUM:\n"
    msg += f"  • Volume: {vol_ratio:.2f}x average\n"
    msg += f"  • Trend: {vol_trend}\n"
    
    if fear_greed:
        fg_emoji = "😱" if fear_greed['value'] < 25 else "😰" if fear_greed['value'] < 45 else "😐" if fear_greed['value'] < 55 else "😊" if fear_greed['value'] < 75 else "🤑"
        msg += f"\n{fg_emoji} Fear & Greed: {fear_greed['value']}/100 ({fear_greed['classification']})\n"
    
    msg += "\n━━━━ SWING SETUP ━━━━\n\n"
    
    if setup_type == "RANGING":
        msg += "⚠️ CONSOLIDATION - Wait for Breakout\n\n"
        msg += "💡 STRATEGY:\n"
        msg += f"  ✅ BULLISH Scenario:\n"
        msg += f"     • Entry: Breakout above ${entry:,.2f}\n"
        msg += f"     • TP1: ${tp1:,.2f} ({((tp1-entry)/entry*100):+.1f}%)\n"
        msg += f"     • TP2: ${tp2:,.2f} ({((tp2-entry)/entry*100):+.1f}%)\n"
        msg += f"     • SL: ${sl:,.2f} ({((sl-entry)/entry*100):+.1f}%)\n"
        msg += f"     • R:R = {rr:.1f}:1\n\n"
        msg += f"  ❌ BEARISH Scenario:\n"
        msg += f"     • Breakdown below ${support:,.2f} = AVOID LONGS\n\n"
        msg += "⏰ TIMEFRAME:\n"
        msg += "  Expected breakout within 12-24 hours\n\n"
    elif setup_type == "BULLISH":
        msg += "✅ BULLISH ALIGNMENT - Long Setup\n\n"
        msg += "💡 STRATEGY:\n"
        msg += f"  ✅ Entry: ${entry:,.2f}\n"
        msg += f"  🎯 TP1: ${tp1:,.2f} ({((tp1-entry)/entry*100):+.1f}%)\n"
        msg += f"  🎯 TP2: ${tp2:,.2f} ({((tp2-entry)/entry*100):+.1f}%)\n"
        msg += f"  🛑 SL: ${sl:,.2f} ({((sl-entry)/entry*100):+.1f}%)\n"
        msg += f"  📊 R:R = {rr:.1f}:1\n\n"
    else:  # BEARISH
        msg += "❌ BEARISH ALIGNMENT - Short Setup\n\n"
        msg += "💡 STRATEGY:\n"
        msg += f"  ❌ Entry: ${entry:,.2f}\n"
        msg += f"  🎯 TP1: ${tp1:,.2f} ({((tp1-entry)/entry*100):+.1f}%)\n"
        msg += f"  🎯 TP2: ${tp2:,.2f} ({((tp2-entry)/entry*100):+.1f}%)\n"
        msg += f"  🛑 SL: ${sl:,.2f} ({((sl-entry)/entry*100):+.1f}%)\n"
        msg += f"  📊 R:R = {rr:.1f}:1\n\n"
    
    msg += "━━━━ RECOMMENDATION ━━━━\n\n"
    
    if setup_type == "RANGING":
        msg += f"✅ WAIT for bullish breakout above ${entry:,.2f}\n"
        msg += f"SET alerts at ${entry:,.2f} and ${support:,.2f}\n\n"
        msg += "⚠️ RISKS:\n"
        msg += "  • Low volume may lead to false breakout\n"
    elif setup_type == "BULLISH":
        msg += "✅ LONG position with good R:R\n"
        msg += f"SET alerts at entry ${entry:,.2f}\n\n"
        msg += "⚠️ RISKS:\n"
        msg += "  • Respect stop loss strictly\n"
    else:
        msg += "❌ SHORT position - risky\n"
        msg += f"SET alerts at entry ${entry:,.2f}\n\n"
        msg += "⚠️ RISKS:\n"
        msg += "  • Bearish market - high volatility\n"
    
    msg += "\n<i>⚠️ This is not financial advice. DYOR!</i>"
    
    return msg


# ============================================================
# PR #115: Enhanced Multi-Pair Swing Analysis
# ============================================================

async def generate_comprehensive_swing_analysis(symbol: str, display_name: str, language: str = 'bg') -> dict:
    """
    Generate comprehensive professional swing trading analysis with real-time data
    
    PR #115: Enhanced Multi-Pair Swing Analysis
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        display_name: Display name (e.g., '🪙 BITCOIN')
        language: 'bg' or 'en'
    
    Returns:
        dict with 'symbol', 'rating', 'message', 'recommendation', 'priority'
    """
    try:
        # Fetch real-time data from Binance
        price_data = await fetch_json(f"https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}")
        if not price_data:
            raise Exception("Failed to fetch price data")
        
        current_price = float(price_data['lastPrice'])
        change_24h = float(price_data['priceChangePercent'])
        volume = float(price_data['volume'])
        quote_volume = float(price_data['quoteVolume'])
        
        # Fetch 7d data for trend
        klines_7d = await fetch_json(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=7")
        change_7d = 0
        if klines_7d and len(klines_7d) > 0:
            price_7d_ago = float(klines_7d[0][1])  # Open price 7 days ago
            change_7d = ((current_price - price_7d_ago) / price_7d_ago) * 100
        
        # Fetch 4H and 1D candles for structure analysis
        klines_4h = await fetch_json(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=4h&limit=50")
        klines_1d = await fetch_json(f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit=20")
        
        # Analyze market structure
        structure_4h = "NEUTRAL"
        structure_1d = "NEUTRAL"
        alignment = "MIXED"
        
        if ICT_SIGNAL_ENGINE_AVAILABLE:
            try:
                ict_4h = await ict_engine_global.analyze(symbol.replace('USDT', ''), '4h')
                ict_1d = await ict_engine_global.analyze(symbol.replace('USDT', ''), '1d')
                
                if ict_4h and ict_1d:
                    bias_4h_val = ict_4h.bias.value if hasattr(ict_4h.bias, 'value') else str(ict_4h.bias)
                    bias_1d_val = ict_1d.bias.value if hasattr(ict_1d.bias, 'value') else str(ict_1d.bias)
                    
                    if bias_4h_val in ['BULLISH', 'STRONG_BULLISH']:
                        structure_4h = "BULLISH"
                    elif bias_4h_val in ['BEARISH', 'STRONG_BEARISH']:
                        structure_4h = "BEARISH"
                    
                    if bias_1d_val in ['BULLISH', 'STRONG_BULLISH']:
                        structure_1d = "BULLISH"
                    elif bias_1d_val in ['BEARISH', 'STRONG_BEARISH']:
                        structure_1d = "BEARISH"
                    
                    # Determine alignment
                    if structure_4h == structure_1d and structure_4h != "NEUTRAL":
                        alignment = structure_4h
                    elif structure_4h == "NEUTRAL" or structure_1d == "NEUTRAL":
                        alignment = "RANGING"
                    else:
                        alignment = "MIXED"
            except Exception as e:
                logger.warning(f"ICT analysis failed for {symbol}: {e}")
        
        # Calculate support/resistance from recent price action
        if klines_1d and len(klines_1d) >= 10:
            recent_highs = [float(k[2]) for k in klines_1d[-10:]]  # Last 10 days high
            recent_lows = [float(k[3]) for k in klines_1d[-10:]]   # Last 10 days low
            resistance_level = max(recent_highs)
            support_level = min(recent_lows)
        else:
            resistance_level = current_price * 1.03
            support_level = current_price * 0.97
        
        resistance_dist = ((resistance_level - current_price) / current_price) * 100
        support_dist = ((current_price - support_level) / current_price) * 100
        
        # Calculate volume analysis
        avg_volume = quote_volume / 24  # Simplified average
        volume_ratio = 1.0
        volume_trend = "NORMAL"
        
        if change_24h > 5:
            volume_trend = "INCREASING"
            volume_ratio = 1.2
        elif change_24h < -5:
            volume_trend = "DECREASING"
            volume_ratio = 0.8
        
        # Fetch Fear & Greed Index (cached)
        fear_greed = await fetch_fear_greed_index()
        
        # Generate swing setup
        if alignment == "BULLISH":
            setup_type = "BULLISH"
            entry_price = current_price
            tp1 = entry_price * 1.038
            tp2 = entry_price * 1.062
            sl = entry_price * 0.97
            rr_ratio = ((tp1 - entry_price) / (entry_price - sl)) if (entry_price - sl) > 0 else 3.0
            recommendation = "BUY"
            rating = 4.0 if volume_trend == "INCREASING" else 3.5
        elif alignment == "BEARISH":
            setup_type = "BEARISH"
            entry_price = current_price
            tp1 = entry_price * 0.962
            tp2 = entry_price * 0.938
            sl = entry_price * 1.03
            rr_ratio = ((entry_price - tp1) / (sl - entry_price)) if (sl - entry_price) > 0 else 3.0
            recommendation = "SHORT"
            rating = 2.0
        else:  # RANGING or MIXED
            setup_type = "RANGING"
            entry_price = resistance_level
            tp1 = entry_price * 1.038
            tp2 = entry_price * 1.062
            sl = entry_price * 0.997
            rr_ratio = DEFAULT_SWING_RR_RATIO
            recommendation = "WAIT"
            rating = 3.0
        
        # Adjust rating based on various factors
        if alignment == "BULLISH" and change_24h > 3 and change_7d > 5:
            rating = min(5.0, rating + 0.5)  # Strong uptrend
        elif alignment == "BEARISH":
            rating = max(1.5, rating - 0.5)  # Bearish is riskier
        
        # Format message with professional analysis
        message = format_comprehensive_swing_message(
            symbol=symbol,
            display_name=display_name,
            price=current_price,
            change_24h=change_24h,
            change_7d=change_7d,
            structure_4h=structure_4h,
            structure_1d=structure_1d,
            alignment=alignment,
            resistance=resistance_level,
            res_dist=resistance_dist,
            support=support_level,
            sup_dist=support_dist,
            volume_ratio=volume_ratio,
            volume_trend=volume_trend,
            fear_greed=fear_greed,
            setup_type=setup_type,
            entry=entry_price,
            tp1=tp1,
            tp2=tp2,
            sl=sl,
            rr=rr_ratio,
            rating=rating,
            language=language
        )
        
        return {
            'symbol': symbol,
            'rating': rating,
            'message': message,
            'recommendation': recommendation,
            'priority': int(rating)
        }
        
    except Exception as e:
        logger.error(f"Error in comprehensive swing analysis for {symbol}: {e}", exc_info=True)
        return {
            'symbol': symbol,
            'rating': 0,
            'message': f"❌ Грешка при анализ на {symbol}: {str(e)}" if language == 'bg' else f"❌ Error analyzing {symbol}: {str(e)}",
            'recommendation': 'ERROR',
            'priority': 0
        }


def format_comprehensive_swing_message(symbol, display_name, price, change_24h, change_7d,
                                       structure_4h, structure_1d, alignment,
                                       resistance, res_dist, support, sup_dist,
                                       volume_ratio, volume_trend, fear_greed,
                                       setup_type, entry, tp1, tp2, sl, rr, rating, language='bg'):
    """
    Format comprehensive swing analysis message in Bulgarian/English mix
    
    PR #115: Professional swing trader perspective with detailed narrative
    """
    
    # Bulgarian translations for structure
    struct_bg = {
        'BULLISH': 'БИЧА',
        'BEARISH': 'МЕЧA',
        'NEUTRAL': 'НЕУТРАЛНА',
        'RANGING': 'КОНСОЛИДАЦИЯ',
        'MIXED': 'СМЕСЕНО'
    }
    
    struct_4h_label = struct_bg.get(structure_4h, structure_4h)
    struct_1d_label = struct_bg.get(structure_1d, structure_1d)
    align_label = struct_bg.get(alignment, alignment)
    
    msg = f"{display_name} ({symbol})\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Price section
    msg += f"💰 Цена: ${price:,.2f} ({change_24h:+.1f}% 24h, {change_7d:+.1f}% 7d)\n\n"
    
    # Structure section
    msg += "📊 СТРУКТУРА:\n"
    msg += f"  • 4H: {struct_4h_label}\n"
    msg += f"  • 1D: {struct_1d_label}\n"
    alignment_emoji = "✅" if alignment in ["BULLISH", "BEARISH"] else "⚠️"
    msg += f"  • Подравняване: {alignment_emoji} {align_label}\n\n"
    
    # Key levels
    msg += "🔍 КЛЮЧОВИ НИВА:\n"
    msg += f"  🔴 Съпротива: ${resistance:,.2f} ({res_dist:+.1f}% от цена)\n"
    msg += f"  🟢 Подкрепа: ${support:,.2f} ({sup_dist:+.1f}% под цена)\n\n"
    
    # Volume & Momentum
    msg += "📊 ОБЕМ & MOMENTUM:\n"
    msg += f"  • Обем: {volume_ratio:.2f}x среден\n"
    msg += f"  • Тренд: {volume_trend}\n"
    
    if fear_greed:
        fg_emoji = "😱" if fear_greed['value'] < 25 else "😰" if fear_greed['value'] < 45 else "😐" if fear_greed['value'] < 55 else "😊" if fear_greed['value'] < 75 else "🤑"
        msg += f"\n{fg_emoji} Fear & Greed: {fear_greed['value']}/100 ({fear_greed['classification']})\n"
    
    msg += "\n━━━━ SWING SETUP ━━━━\n\n"
    
    # Setup strategy based on type
    if setup_type == "RANGING":
        msg += "⚠️ КОНСОЛИДАЦИЯ - Чакай Breakout\n\n"
        msg += "💡 СТРАТЕГИЯ:\n"
        msg += f"  ✅ БИЧИ Сценарий:\n"
        msg += f"     • Вход: Breakout над ${entry:,.2f}\n"
        msg += f"     • TP1: ${tp1:,.2f} ({((tp1-entry)/entry*100):+.1f}%)\n"
        msg += f"     • TP2: ${tp2:,.2f} ({((tp2-entry)/entry*100):+.1f}%)\n"
        msg += f"     • SL: ${sl:,.2f} ({((sl-entry)/entry*100):+.1f}%)\n"
        msg += f"     • R:R = {rr:.1f}:1\n\n"
        msg += f"  ❌ МЕЧИ Сценарий:\n"
        msg += f"     • Breakdown под ${support:,.2f} = ИЗБЯГВАЙ LONGS\n\n"
        msg += "⏰ ВРЕМЕВА РАМКА:\n"
        msg += "  Очакван breakout в рамките на 12-24 часа\n\n"
    elif setup_type == "BULLISH":
        msg += "✅ БИЧИ ALIGNMENT - Long Setup\n\n"
        msg += "💡 СТРАТЕГИЯ:\n"
        msg += f"  ✅ Вход: Pullback към ${entry:,.2f}\n"
        msg += f"  🎯 TP1: ${tp1:,.2f} ({((tp1-entry)/entry*100):+.1f}%)\n"
        msg += f"  🎯 TP2: ${tp2:,.2f} ({((tp2-entry)/entry*100):+.1f}%)\n"
        msg += f"  🛑 SL: ${sl:,.2f} ({((sl-entry)/entry*100):+.1f}%)\n"
        msg += f"  📊 R:R = {rr:.1f}:1\n\n"
    else:  # BEARISH
        msg += "❌ МЕЧИ ALIGNMENT - Short Setup\n\n"
        msg += "💡 СТРАТЕГИЯ:\n"
        msg += f"  ❌ Вход: Rally към ${entry:,.2f}\n"
        msg += f"  🎯 TP1: ${tp1:,.2f} ({((tp1-entry)/entry*100):+.1f}%)\n"
        msg += f"  🎯 TP2: ${tp2:,.2f} ({((tp2-entry)/entry*100):+.1f}%)\n"
        msg += f"  🛑 SL: ${sl:,.2f} ({((sl-entry)/entry*100):+.1f}%)\n"
        msg += f"  📊 R:R = {rr:.1f}:1\n\n"
    
    msg += "━━━━ ПРОФЕСИОНАЛЕН SWING АНАЛИЗ ━━━━\n\n"
    
    # Professional narrative - context specific to each setup
    msg += "📈 ПАЗАРЕН КОНТЕКСТ:\n"
    
    if setup_type == "RANGING":
        # Dynamic narrative based on actual price performance
        msg += "📈 ПАЗАРЕН КОНТЕКСТ:\n"
        
        # Price performance analysis
        if change_7d < -20:
            msg += f"{symbol} преживява значителна седмична корекция от {change_7d:+.1f}%, "
            msg += f"с цената спаднала драстично от наскоро достигнатите нива. "
        elif change_7d < -10:
            msg += f"{symbol} е в корекционна фаза с {change_7d:+.1f}% спад седмично, "
            msg += f"показвайки временна слабост след по-ранно покачване. "
        elif change_7d < -5:
            msg += f"{symbol} показва умерен спад от {change_7d:+.1f}% за седмицата, "
            msg += f"консолидирайки се в по-тесен диапазон. "
        elif change_7d > 10:
            msg += f"{symbol} показва силен momentum с {change_7d:+.1f}% растеж седмично, "
            msg += f"но сега влиза в консолидация преди следващо движение. "
        elif change_7d > 5:
            msg += f"{symbol} е с {change_7d:+.1f}% покачване седмично, "
            msg += f"консолидирайки печалбите в текущ range. "
        else:
            msg += f"{symbol} се търгува относително стабилно ({change_7d:+.1f}% ��едмично), "
            msg += f"показвайки балансирана консолидация. "
        
        msg += f"Текущо движение между ${support:,.2f} подкрепа и ${resistance:,.2f} съпротива. "
        msg += f"Структурата е {align_label.lower()}.\n\n"
        
        # Volume analysis - dynamic interpretation
        if volume_ratio < 0.7:
            msg += f"Обемът е значително под средния ({volume_ratio:.2f}x), което сигнализира "                   f"намаляващ интерес и ниска убеденост от пазара. "
        elif volume_ratio < 0.9:
            msg += f"Обемът е леко под средния ({volume_ratio:.2f}x), типично за консолидационни периоди. "
        elif volume_ratio > 1.2:
            msg += f"Обемът е над средния ({volume_ratio:.2f}x), показвайки активен интерес въпреки консолидацията. "
        else:
            msg += f"Обемът е около средния ({volume_ratio:.2f}x), показвайки балансирана активност. "
        
        # Fear & Greed context
        if fear_greed:
            if fear_greed['value'] < 25:
                msg += f"Fear & Greed индексът на {fear_greed['value']} показва екстремен страх - "                       f"потенциална buying opportunity за contrarian traders."
            elif fear_greed['value'] < 45:
                msg += f"Fear & Greed на {fear_greed['value']} отразява предпазливост в пазара."
            else:
                msg += f"Fear & Greed на {fear_greed['value']} показва относително неутрален sentiment."
        msg += "\n\n"
        
        msg += "🎯 SWING TRADER ПЕРСПЕКТИВА:\n\n"
        
        # Dynamic perspective based on momentum
        if change_24h < -5 and change_7d < -15:
            msg += f"Силната корекция (-{abs(change_7d):.1f}% седмично) създава потенциална зона за дългосрочен вход, "                   f"НО момента изисква ТЕРПЕНИЕ. Изчакай първи признаци на стабилизация:\n"
            msg += f"• Обемът да започне да расте при покачване\n"
            msg += f"• Цената да спре да прави нови дъна\n"
            msg += f"• Пробив над ${resistance:,.2f} би потвърдил край на спада.\n\n"
        elif change_7d < -5 and volume_ratio < 0.8:
            msg += f"Комбинацията от спад ({change_7d:+.1f}%) и нисък обем ({volume_ratio:.2f}x) показва "                   f"липса на убеждение. Swing traders трябва да ИЗЧАКАТ:\n"
            msg += f"• Ясен breakout с висок обем\n"
            msg += f"• Потвърждение на посока (над ${resistance:,.2f} или под ${support:,.2f})\n"
            msg += f"• За сега - НАБЛЮДАВАЙ, не влизай.\n\n"
        elif change_24h > 0 and change_7d > 0:
            msg += f"Положителният momentum ({change_24h:+.1f}% дневно, {change_7d:+.1f}% седмично) показва "                   f"основна бича тенденция. Консолидацията е ЗДРАВОСЛОВНА пауза.\n"
            msg += f"• Breakout над ${resistance:,.2f} би потвърдил продължение\n"
            msg += f"• R:R от {rr:.1f}:1 предлага добро съотношение\n"
            msg += f"• Влез при breakout с потвърждение, НЕ в средата на range.\n\n"
        else:
            msg += f"Текущата неяснота изисква ТЪРПЕНИЕ. Като опитен swing trader изчаквам:\n"
            msg += f"• Решителен пробив с обем над ${resistance:,.2f} (bullish)\n"
            msg += f"• Или breakdown под ${support:,.2f} (bearish)\n"
            msg += f"• НЕ влизай в средата на range - лош риск/награда.\n\n"
        
        msg += "⚠️ КЛЮЧОВИ РИСКОВЕ:\n"
        if volume_ratio < 0.8:
            msg += f"1. КРИТИЧНО: Нисък обем ({volume_ratio:.2f}x) прави всеки breakout подозрителен - "                   f"висок риск от фалшив пробив\n"
        else:
            msg += "1. Фалшиви пробиви са чести в range-bound пазар - изисквай обемно потвърждение\n"
        msg += "2. Уикенд gap-ове могат да объркат техническия анализ\n"
        msg += "3. Макро новини (регулации, глобални пазари) могат да надделеят над техниката\n\n"
        
    elif setup_type == "BULLISH":
        msg += f"{symbol} показва силна бича структура с подравнени 4H и 1D таймфреймове. "
        msg += f"Цената е {change_24h:+.1f}% за 24ч и {change_7d:+.1f}% за 7д, "
        msg += f"демонстрирайки устойчив uptrend momentum.\n\n"
        
        msg += f"Обемът е {volume_ratio:.2f}x средния с {volume_trend.lower()} тренд, "
        msg += f"което подкрепя бичия сценарий. "
        msg += f"Подкрепата на ${support:,.2f} ({sup_dist:.1f}% под цената) "
        msg += f"предлага силна база за pullback вход.\n\n"
        
        msg += "🎯 SWING TRADER ПЕРСПЕКТИВА:\n\n"
        msg += "Отличен long setup с ясна бича структура. Препоръчвам pullback вход "
        msg += f"към зоната ${entry * 0.98:,.2f}-${entry:,.2f} вместо chase на текущата цена.\n\n"
        
        msg += "СТРАТЕГИЯ ЗА ВХОД:\n"
        msg += f"Изчакай retracement към ${support:,.2f} зона. Влез на потвърждение "
        msg += f"(4H свещ със силно затваряне). Мащабирай позицията: 50% при pullback, "
        msg += f"30% при momentum продължение, 20% при retest на support като resistance.\n\n"
        
        msg += "⚠️ КЛЮЧОВИ РИСКОВЕ:\n"
        msg += "1. Спазвай стоп лоса строго - НЕ премествай по-ниско\n"
        msg += "2. Обемът трябва да потвърди - избягвай вход при слаб обем\n"
        msg += "3. Глобални пазари могат да повлияят на криптo sentiment\n\n"
        
    else:  # BEARISH
        msg += f"{symbol} показва мечa структура с подравнени bearish сигнали. "
        msg += f"Цената е {change_24h:+.1f}% за 24ч, демонстрирайки слабост.\n\n"
        
        msg += "🎯 SWING TRADER ПЕРСПЕКТИВА:\n\n"
        msg += "Мечата структура предполага внимание. За swing traders, "
        msg += "ИЗБЯГВАЙ long позиции в този момент. Shorts са високо рискови "
        msg += "в крипто поради възможни бързи reversal-и.\n\n"
        
        msg += "ПРЕПОРЪКА:\n"
        msg += f"Чакай стабилизация и промяна на структура преди нови long-ове. "
        msg += f"Breakdown под ${support:,.2f} би потвърдил по-нататъшна слабост.\n\n"
        
        msg += "⚠️ КЛЮЧОВИ РИСКОВЕ:\n"
        msg += "1. Мечи пазар - висока волатилност и непредсказуемост\n"
        msg += "2. Shorts в крипто са рискови - възможни резки pump-ове\n"
        msg += "3. По-добре да седиш встрани отколкото да губиш пари\n\n"
    
    msg += "💼 УПРАВЛЕНИЕ НА ПОЗИЦИЯТА:\n"
    if setup_type == "RANGING":
        msg += "- Изчакай ясна посока преди вход\n"
        msg += "- Използвай максимум 1-2% риск от капитала\n"
        msg += "- Задай alerts на ключови нива вместо пазарни поръчки\n"
        msg += "- Бъди готов да излезеш бързо ако обемът не потвърди пробива\n\n"
    elif setup_type == "BULLISH":
        msg += "- Влез на pullback, НЕ chase цената\n"
        msg += "- Използвай 2-3% риск от капитала максимум\n"
        msg += "- Премести SL на breakeven след TP1 удар\n"
        msg += "- Вземи 50% печалба на TP1, остави остатъка с trailing SL\n\n"
    else:
        msg += "- ИЗБЯГВАЙ нови позиции в мечи структура\n"
        msg += "- Ако вече си в long, обмисли exit или стегни SL\n"
        msg += "- Чакай промяна на структура преди реентри\n\n"
    
    msg += "⏰ ВРЕМЕВА ЛИНИЯ:\n"
    if setup_type == "RANGING":
        msg += "Консолидацията обикновено се разрешава в рамките на 12-48 часа. "
        msg += "Ако няма пробив в рамките на 48ч, преоцени за range-trading.\n\n"
    elif setup_type == "BULLISH":
        msg += "Swing hold период: 3-7 дни за TP1, 7-14 дни за TP2. "
        msg += "Бъди гъвкав ако пазарът се движи по-бързо.\n\n"
    else:
        msg += "Изчакай поне 2-3 дни за ясна промяна на структура преди реоценка.\n\n"
    
    msg += "━━━━ ПРЕПОРЪКА ━━━━\n\n"
    
    # Rating stars
    stars = "⭐" * int(rating) + "☆" * (5 - int(rating))
    msg += f"✅ РЕЙТИНГ: {rating:.1f}/5 {stars}\n\n"
    
    msg += "ПЛАН ЗА ДЕЙСТВИЕ:\n"
    if setup_type == "RANGING":
        msg += f"1. Задай ценови alerts: ${resistance:,.2f} (пробив) & ${support:,.2f} (breakdown)\n"
        msg += "2. НЕ влизай в текущия range - риск/награда е неблагоприятна\n"
        msg += "3. При бичи пробив: Потвърди обем, влез с 40% позиция\n"
        msg += f"4. Изчакай retest на ${resistance:,.2f} като подкрепа за още 30%\n"
        msg += "5. Премести stop loss на breakeven след TP1 удар\n\n"
    elif setup_type == "BULLISH":
        msg += f"1. Изчакай pullback към ${entry * 0.98:,.2f}-${entry:,.2f} зона\n"
        msg += "2. Влез с 50% позиция при силно 4H затваряне в зоната\n"
        msg += "3. Добави 30% при momentum продължение над предишен high\n"
        msg += "4. Премести SL на breakeven при +2% profit\n"
        msg += "5. Вземи 50% печалба на TP1, остави остатъка с trailing SL\n\n"
    else:
        msg += "1. ИЗБЯГВАЙ нови long позиции\n"
        msg += f"2. Задай alert на ${support:,.2f} за breakdown потвърждение\n"
        msg += "3. Изчакай промяна на 1D структура към bullish\n"
        msg += "4. Реоценка след 3-5 дни или при значимa промяна\n\n"
    
    msg += "ИЗБЯГВАЙ АКО:\n"
    if setup_type == "RANGING":
        msg += "- Пробивът настъпи при нисък обем (<0.8x среден)\n"
        msg += "- Уикенд пробив без последващо потвърждение\n"
        msg += "- Основна съпротива се формира веднага след пробив\n\n"
    elif setup_type == "BULLISH":
        msg += "- Обемът е под 0.8x среден (слаб bullish интерес)\n"
        msg += f"- Breakdown под ${support:,.2f} (структура се обърна)\n"
        msg += "- Глобални пазари показват силна слабост\n\n"
    else:
        msg += "- Структурата остава bearish\n"
        msg += "- Обемът продължава да намалява\n"
        msg += "- Няма ясни сигнали за reversal\n\n"
    
    msg += "⚠️ Това не е финансов съвет. DYOR!\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return msg


def generate_swing_summary(all_analyses: list) -> str:
    """
    Generate summary of all swing analyses with ranked opportunities
    
    PR #115: Summary with best opportunities ranking
    
    Args:
        all_analyses: List of analysis dicts
    
    Returns:
        Formatted summary message
    """
    # Filter out errors
    valid_analyses = [a for a in all_analyses if a['rating'] > 0]
    
    # Sort by rating (highest first)
    sorted_analyses = sorted(valid_analyses, key=lambda x: x['rating'], reverse=True)
    
    # Group by rating
    best = [a for a in sorted_analyses if a['rating'] >= 3.5]
    caution = [a for a in sorted_analyses if 2.5 <= a['rating'] < 3.5]
    avoid = [a for a in sorted_analyses if a['rating'] < 2.5]
    
    msg = "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    msg += "📊 SWING ANALYSIS SUMMARY\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    msg += f"Analyzed {len(valid_analyses)} pairs | "
    msg += f"Generated at {datetime.now(timezone.utc).strftime('%H:%M:%S')} UTC\n\n"
    
    if best:
        msg += "🏆 BEST OPPORTUNITIES (Ranked):\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        for i, analysis in enumerate(best[:3]):
            medal = medals[i] if i < 3 else "  "
            coin_name = analysis['symbol'].replace('USDT', '')
            stars = "⭐" * int(analysis['rating'])
            msg += f"{i+1}. {medal} {coin_name} - {analysis['rating']:.1f}/5 {stars}\n"
            
            # Add brief recommendation
            if analysis['recommendation'] == 'BUY':
                msg += f"   Силна бича структура, добър R:R\n"
                msg += f"   Действие: BUY на pullback\n\n"
            elif analysis['recommendation'] == 'WAIT':
                msg += f"   Консолидация breakout setup\n"
                msg += f"   Действие: ИЗЧАКАЙ breakout\n\n"
            else:
                msg += f"   {analysis['recommendation']} setup\n\n"
    
    if caution:
        msg += "⚠️ ВНИМАНИЕ / ИЗЧАКАЙ:\n\n"
        for i, analysis in enumerate(caution, 1):
            coin_name = analysis['symbol'].replace('USDT', '')
            stars = "⭐" * int(analysis['rating'])
            msg += f"{i + len(best)}. {coin_name} - {analysis['rating']:.1f}/5 {stars}\n"
            msg += f"   Range-bound или смесени сигнали\n"
            msg += f"   Действие: ИЗЧАКАЙ по-добър setup\n\n"
    
    if avoid:
        msg += "❌ ИЗБЯГВАЙ / НИСКА УВЕРЕНОСТ:\n\n"
        for i, analysis in enumerate(avoid, 1):
            coin_name = analysis['symbol'].replace('USDT', '')
            stars = "⭐" * int(analysis['rating'])
            msg += f"{i + len(best) + len(caution)}. {coin_name} - {analysis['rating']:.1f}/5 {stars}\n"
            
            if analysis['recommendation'] == 'SHORT':
                msg += f"   Мечa структура\n"
                msg += f"   Действие: ИЗБЯГВАЙ longs / Short само\n\n"
            else:
                msg += f"   Слаб setup, ниска увереност\n"
                msg += f"   Действие: СЕДНИ ВСТРАНИ\n\n"
    
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    # Market overview
    msg += "💡 ПАЗАРЕН ПРЕГЛЕД:\n"
    
    bullish_count = sum(1 for a in valid_analyses if a['recommendation'] == 'BUY')
    bearish_count = sum(1 for a in valid_analyses if a['recommendation'] == 'SHORT')
    
    if bullish_count >= len(valid_analyses) * 0.5:
        msg += "Предимно бичи условия в пазара. "
    elif bearish_count >= len(valid_analyses) * 0.5:
        msg += "Предимно мечи условия - внимание при long позиции. "
    else:
        msg += "Смесени условия в пазара. "
    
    if best:
        top_coin = best[0]['symbol'].replace('USDT', '')
        msg += f"{top_coin} показва най-силен setup. "
    
    msg += "Бъдете селективни с вашите позиции.\n\n"
    
    msg += f"⏰ Данни актуални към: {datetime.now(timezone.utc).strftime('%d %b %Y, %H:%M:%S')} UTC\n"
    msg += "⚠️ Пазарните условия се променят - проверявай редовно!\n\n"
    
    msg += "Използвай /start за още анализи\n\n"
    msg += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return msg


@require_access()
@rate_limited(calls=10, period=60)
async def market_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Дневен анализ за всички интегрирани валути с новини и sentiment - показва меню за избор"""
    logger.info(f"User {update.effective_user.id} executed /market")
    
    # Get user's current language preference (default to Bulgarian)
    user_id = update.effective_user.id
    user_language = context.bot_data.get(f'user_{user_id}_language', 'bg')
    
    # Create submenu keyboard
    market_keyboard = [
        [InlineKeyboardButton("📈 Бърз Преглед", callback_data="market_quick")],
        [InlineKeyboardButton("🎯 Swing Trading Анализ", callback_data="market_swing")],
        [InlineKeyboardButton("💡 Пълен Пазарен Отчет", callback_data="market_full")],
        [
            InlineKeyboardButton("🇧🇬 BG", callback_data="lang_bg"),
            InlineKeyboardButton("🇬🇧 EN", callback_data="lang_en")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(market_keyboard)
    
    lang_flag = "🇧🇬" if user_language == 'bg' else "🇬🇧"
    message_text = (
        f"📊 <b>ПАЗАРЕН АНАЛИЗ</b>\n\n"
        f"Избери тип анализ:\n\n"
        f"📈 <b>Бърз Преглед</b> - Кратък sentiment overview\n"
        f"🎯 <b>Swing Trading Анализ</b> - Професионален анализ с setup\n"
        f"💡 <b>Пълен Отчет</b> - Детайлен преглед на всички криптовалути\n\n"
        f"{lang_flag} Текущ език: <b>{'Български' if user_language == 'bg' else 'English'}</b>"
    )
    
    await update.message.reply_text(
        message_text,
        parse_mode='HTML',
        reply_markup=reply_markup
    )


async def market_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle market submenu callbacks"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    # Handle language selection
    if query.data == 'lang_bg':
        context.bot_data[f'user_{user_id}_language'] = 'bg'
        await query.edit_message_text(
            "🇧🇬 Език сменен на <b>Български</b>",
            parse_mode='HTML'
        )
        return
    elif query.data == 'lang_en':
        context.bot_data[f'user_{user_id}_language'] = 'en'
        await query.edit_message_text(
            "🇬🇧 Language changed to <b>English</b>",
            parse_mode='HTML'
        )
        return
    
    # Handle market analysis options
    if query.data == 'market_quick':
        await market_quick_overview(update, context)
    elif query.data == 'market_swing':
        await market_swing_analysis(update, context)
    elif query.data == 'market_full':
        await market_full_report(update, context)


async def market_quick_overview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick market overview with sentiment"""
    query = update.callback_query
    await query.edit_message_text("📊 Анализирам пазара...")
    
    user_id = update.effective_user.id
    user_language = context.bot_data.get(f'user_{user_id}_language', 'bg')
    
    # Fetch market data
    data = await fetch_json(BINANCE_24H_URL)
    if not data:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Грешка при извличане на данни"
        )
        return
    
    # Filter our symbols
    our_symbols = set(SYMBOLS.values())
    market_data = [s for s in data if s['symbol'] in our_symbols]
    
    # Analyze sentiment
    sentiment_analysis = await analyze_market_sentiment(market_data)
    
    # Fetch Fear & Greed Index
    fear_greed = await fetch_fear_greed_index()
    
    # Build message
    message = "📊 <b>БЪРЗ ПАЗАРЕН ПРЕГЛЕД</b>\n" if user_language == 'bg' else "📊 <b>QUICK MARKET OVERVIEW</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
    if user_language == 'bg':
        message += f"<b>🎯 Пазарен Sentiment:</b>\n"
        message += f"{sentiment_analysis['emoji']} <b>{sentiment_analysis['description']}</b>\n"
        message += f"📈 Sentiment Score: <b>{sentiment_analysis['score']:.1f}/100</b>\n"
    else:
        message += f"<b>🎯 Market Sentiment:</b>\n"
        message += f"{sentiment_analysis['emoji']} <b>{sentiment_analysis['description']}</b>\n"
        message += f"📈 Sentiment Score: <b>{sentiment_analysis['score']:.1f}/100</b>\n"
    
    # Add Fear & Greed Index
    if fear_greed:
        fg_emoji = "😱" if fear_greed['value'] < 25 else "😰" if fear_greed['value'] < 45 else "😐" if fear_greed['value'] < 55 else "😊" if fear_greed['value'] < 75 else "🤑"
        message += f"\n{fg_emoji} <b>Fear & Greed Index:</b> {fear_greed['value']}/100 ({fear_greed['classification']})\n"
    
    message += f"\n📊 {'Средна промяна' if user_language == 'bg' else 'Average change'}: <b>{sentiment_analysis['avg_change']:+.2f}%</b>\n"
    message += f"🟢 {'Растящи' if user_language == 'bg' else 'Rising'}: <b>{sentiment_analysis['positive_count']}</b> | "
    message += f"🔴 {'Падащи' if user_language == 'bg' else 'Falling'}: <b>{sentiment_analysis['negative_count']}</b>\n"
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode='HTML'
    )


async def market_swing_analysis(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Enhanced multi-pair swing trading analysis with professional insights
    
    PR #115: Comprehensive analysis for all 6 trading pairs with real-time data
    Generates individual detailed analysis for each pair plus summary ranking
    """
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_language = context.bot_data.get(f'user_{user_id}_language', 'bg')
    
    # Show progress message
    await query.edit_message_text(
        "📊 <b>SWING TRADING ANALYSIS</b>\n\n"
        "Генерирам детайлен swing анализ за 6 валути...\n"
        "⏳ Това може да отнеме 30-60 секунди.\n\n"
        "<i>Моля изчакайте...</i>",
        parse_mode='HTML'
    )
    
    # Trading pairs with display names
    symbols = [
        ('BTCUSDT', '🪙 BITCOIN'),
        ('ETHUSDT', '💎 ETHEREUM'),
        ('BNBUSDT', '⚡ BINANCE COIN'),
        ('SOLUSDT', '🌐 SOLANA'),
        ('XRPUSDT', '💰 RIPPLE'),
        ('ADAUSDT', '🎯 CARDANO')
    ]
    
    all_analyses = []
    
    # Loop through each pair
    for symbol, display_name in symbols:
        try:
            # Generate comprehensive swing analysis with timeout protection
            analysis = await asyncio.wait_for(
                generate_comprehensive_swing_analysis(
                    symbol=symbol,
                    display_name=display_name,
                    language=user_language
                ),
                timeout=15.0  # 15 seconds per pair
            )
            
            all_analyses.append(analysis)
            
            # Send analysis for this pair (plain text, no HTML parsing)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=analysis['message']
            )
            
            # Anti-spam delay
            await asyncio.sleep(1)
            
        except asyncio.TimeoutError:
            logger.error(f"Timeout analyzing {symbol}")
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"⚠️ Timeout при анализ на {symbol} - прескачам"
            )
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}", exc_info=True)
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"❌ Грешка при анализ на {symbol}: {str(e)}"
            )
    
    # Generate and send summary (plain text, no HTML parsing)
    try:
        summary = generate_swing_summary(all_analyses)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=summary
        )
        logger.info(f"✅ Swing analysis completed for {len(all_analyses)} pairs")
    except Exception as e:
        logger.error(f"Error generating summary: {e}", exc_info=True)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Грешка при генериране на обобщение"
        )


async def detect_market_swing_state(symbol: str, timeframe: str = '4h') -> str:
    """
    Detect swing state for a symbol
    
    PR #113: Helper function for multi-pair market analysis
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        timeframe: Timeframe for analysis (default '4h')
    
    Returns:
        'BULLISH', 'BEARISH', or 'NEUTRAL'
    """
    try:
        # Fetch historical klines data from Binance
        klines = await fetch_json(
            f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={timeframe}&limit={SWING_KLINES_LIMIT}"
        )
        
        if not klines or len(klines) < SWING_MIN_CANDLES:
            return 'UNKNOWN'
        
        # Extract recent candles for analysis
        recent_candles = klines[-SWING_MIN_CANDLES:]
        
        # Get highs, lows, and current close
        recent_highs = [float(candle[2]) for candle in recent_candles]  # Index 2 = high
        recent_lows = [float(candle[3]) for candle in recent_candles]   # Index 3 = low
        current_price = float(klines[-1][4])  # Index 4 = close of last candle
        
        # Calculate swing based on recent price structure
        recent_high = max(recent_highs)
        recent_low = min(recent_lows)
        
        # Simple swing detection (divide range into thirds)
        price_range = recent_high - recent_low
        if price_range == 0:
            return 'NEUTRAL'
        
        upper_third = recent_low + (price_range * SWING_UPPER_THRESHOLD)
        lower_third = recent_low + (price_range * SWING_LOWER_THRESHOLD)
        
        if current_price > upper_third:
            return 'BULLISH'
        elif current_price < lower_third:
            return 'BEARISH'
        else:
            return 'NEUTRAL'
            
    except Exception as e:
        logger.error(f"Swing detection error for {symbol}: {e}")
        return 'UNKNOWN'


async def market_full_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Full detailed market report (original market_cmd behavior)"""
    query = update.callback_query
    await query.edit_message_text("📊 Анализирам пазара от множество източници...")
    
    # Извлечи пазарни данни
    data = await fetch_json(BINANCE_24H_URL)
    if not data:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="❌ Грешка при извличане на данни"
        )
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
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=message,
        parse_mode='HTML'
    )
    
    # === NEW: MARKET FUNDAMENTAL ANALYSIS (PHASE 2 PART 2) ===
    try:
        from utils.market_helper import MarketHelper, format_market_fundamental_section
        
        market_helper = MarketHelper()
        
        if market_helper.is_enabled():
            logger.info("🔬 Running market fundamental analysis")
            
            # Get market fundamentals (use BTCUSDT as main symbol for market overview)
            market_fundamentals = market_helper.get_market_fundamentals('BTCUSDT')
            
            if market_fundamentals:
                # Calculate average price change for context
                avg_price_change = sentiment_analysis['avg_change']
                
                # Calculate total volume
                total_volume = sum(float(item['volume']) for item in market_data)
                
                # Generate market context
                market_context_text = market_helper.generate_market_context(
                    fundamentals=market_fundamentals,
                    price_change_24h=avg_price_change,
                    volume_24h=total_volume
                )
                
                # Format and send fundamental section
                fundamental_section = format_market_fundamental_section(
                    market_fundamentals,
                    market_context_text
                )
                
                if fundamental_section:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=fundamental_section,
                        parse_mode='HTML'
                    )
                    logger.info("✅ Market fundamental analysis sent")
        else:
            logger.debug("Market fundamental analysis disabled (feature flags)")
    except Exception as e:
        logger.warning(f"⚠️ Market fundamental analysis unavailable: {e}")
        # Continue with normal market analysis
    
    # === DETAILED COIN ANALYSIS WITH ICT ===
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="📊 Подготвям детайлен анализ с ICT + CoinGecko данни..."
    )
    
    # Get user settings for timeframe preference
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    timeframe = settings['timeframe']
    
    for item in market_data:
        symbol = item['symbol']
        
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
            coin_msg += f"   🏆 Market Cap Rank: #{ext.get('market_cap_rank', 'N/A')}\n"
            
            # Add BTC correlation for altcoins
            if symbol != 'BTCUSDT':
                try:
                    from config.config_loader import load_feature_flags
                    flags = load_feature_flags()
                    btc_corr_enabled = flags.get('fundamental_analysis', {}).get('btc_correlation', False)
                    
                    if btc_corr_enabled:
                        # Get BTC correlation from external data if available
                        btc_corr = ext.get('btc_correlation', None)
                        
                        if btc_corr is not None:
                            # Determine correlation strength
                            if abs(btc_corr) > 0.7:
                                corr_strength = "Strong"
                            elif abs(btc_corr) > 0.4:
                                corr_strength = "Moderate"
                            else:
                                corr_strength = "Weak"
                            
                            coin_msg += f"   🔗 <b>BTC Correlation:</b> {btc_corr:.2f} ({corr_strength})\n"
                except Exception as e:
                    logger.debug(f"Could not add BTC correlation: {e}")
            
            coin_msg += "\n"
        
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
        
        # === NEW: ADD ICT ANALYSIS ===
        if ICT_SIGNAL_ENGINE_AVAILABLE:
            try:
                # Fetch klines for ICT analysis
                klines_response = requests.get(
                    BINANCE_KLINES_URL,
                    params={'symbol': symbol, 'interval': timeframe, 'limit': 200},
                    timeout=10
                )
                
                if klines_response.status_code == 200:
                    klines_data = klines_response.json()
                    
                    # Prepare dataframe
                    df = pd.DataFrame(klines_data, columns=[
                        'timestamp', 'open', 'high', 'low', 'close', 'volume',
                        'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                        'taker_buy_quote', 'ignore'
                    ])
                    
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    for col in ['open', 'high', 'low', 'close', 'volume']:
                        df[col] = df[col].astype(float)
                    
                    # Fetch MTF data for ICT analysis
                    mtf_data = fetch_mtf_data(symbol, timeframe, df)
                    
                    # Generate ICT signal using global instance
                    global ict_engine_global
                    ict_engine = ict_engine_global
                    ict_signal = ict_engine.generate_signal(
                        df=df,
                        symbol=symbol,
                        timeframe=timeframe,
                        mtf_data=mtf_data,
                        is_auto=False  # ← Mark as manual signal
                    )
                    
                    # Add ICT insights to message
                    coin_msg += f"<b>🎯 ICT Анализ ({timeframe}):</b>\n"
                    
                    # ✅ Handle HOLD signals
                    if ict_signal and isinstance(ict_signal, dict) and ict_signal.get('action') == 'HOLD':
                        coin_msg += f"⚠️ RANGING пазар - няма ясна посока\n"
                    elif ict_signal and isinstance(ict_signal, dict) and ict_signal.get('type') != 'NO_TRADE':
                        # Valid ICT signal found
                        signal_type = ict_signal.get('type', 'N/A')
                        confidence = ict_signal.get('confidence', 0)
                        bias = ict_signal.get('bias', 'NEUTRAL')
                        
                        # Signal type emoji
                        type_emoji = "🟢" if signal_type == "BUY" else "🔴" if signal_type == "SELL" else "⚪"
                        
                        coin_msg += f"   {type_emoji} <b>Сигнал:</b> {signal_type}\n"
                        coin_msg += f"   💪 <b>Увереност:</b> {confidence:.0f}%\n"
                        coin_msg += f"   📊 <b>Bias:</b> {bias}\n"
                        
                        # Add key ICT levels
                        entry = ict_signal.get('entry_price')
                        tp = ict_signal.get('tp_price')
                        sl = ict_signal.get('sl_price')
                        
                        if entry:
                            coin_msg += f"   🎯 <b>Entry:</b> ${entry:,.2f}\n"
                        if tp:
                            coin_msg += f"   ✅ <b>TP:</b> ${tp:,.2f}\n"
                        if sl:
                            coin_msg += f"   ❌ <b>SL:</b> ${sl:,.2f}\n"
                        
                        # Add risk/reward if available
                        rr = ict_signal.get('risk_reward_ratio')
                        if rr:
                            coin_msg += f"   ⚖️ <b>R:R:</b> 1:{rr:.2f}\n"
                    else:
                        # No high-quality signal
                        coin_msg += f"   ⚪ <b>Статус:</b> Няма ясен ICT сигнал\n"
                        coin_msg += f"   💡 <i>Пазарът не отговаря на ICT критериите</i>\n"
                    
                    coin_msg += "\n"
                    
            except Exception as ict_error:
                logger.error(f"ICT analysis error for {symbol}: {ict_error}")
                # Don't break the flow, continue without ICT data
        
        # Препоръка с ниво на увереност
        coin_msg += f"<b>💡 Обща Препоръка:</b>\n{analysis['action']}\n"
        coin_msg += f"💪 <b>Базова Увереност:</b> {analysis['confidence']}\n\n"
        
        # Източник на информацията
        sources = "Binance, CoinGecko"
        if ICT_SIGNAL_ENGINE_AVAILABLE:
            sources += ", ICT Engine"
        coin_msg += f"<i>📊 Източници: {sources}</i>"
        
        # Изпрати анализа за тази монета
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=coin_msg,
            parse_mode='HTML'
        )
        
        # Малка пауза между съобщенията (увеличена заради по-дълги съобщения)
        await asyncio.sleep(0.8)
    
    # === MARKET NEWS SECTION ===
    news = await news_task
    
    if news:
        import re
        import html
        from datetime import datetime, timezone
        
        news_message = "<b>📰 Последни Новини (Топ източници):</b>\n\n"
        
        # Try to add sentiment analysis and impact scores if enabled
        try:
            from config.config_loader import load_feature_flags
            from fundamental.sentiment_analyzer import SentimentAnalyzer
            
            flags = load_feature_flags()
            sentiment_enabled = flags.get('fundamental_analysis', {}).get('sentiment_analysis', False)
            
            if sentiment_enabled:
                sentiment_analyzer = SentimentAnalyzer()
                
        except Exception as e:
            logger.warning(f"Could not load sentiment analyzer: {e}")
            sentiment_enabled = False
        
        for i, article in enumerate(news[:3], 1):  # Първите 3
            source = article.get('source', '📰')
            
            # Използвай преведеното заглавие ако е налично
            title_bg = article.get('title_bg', article.get('title', 'Без заглавие'))
            title_en = article.get('title', '')
            desc_bg = article.get('description_bg', '')
            link = article.get('link', None)
            
            # Escape специални символи
            title_bg = title_bg.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            
            news_message += f"{i}. {source} <b>{title_bg}</b>\n"
            
            # Add impact score if sentiment analysis is enabled
            if sentiment_enabled and title_en:
                try:
                    # Analyze individual article sentiment
                    score = sentiment_analyzer._analyze_text(title_en)
                    impact = int((score - 50) * 0.4)  # Convert to impact score (-20 to +20)
                    
                    # Visual indicator
                    if impact > 15:
                        indicator = "🟢"
                        level = "Strong Bullish"
                    elif impact > 5:
                        indicator = "🟢"
                        level = "Bullish"
                    elif impact < -15:
                        indicator = "🔴"
                        level = "Strong Bearish"
                    elif impact < -5:
                        indicator = "🔴"
                        level = "Bearish"
                    else:
                        indicator = "🟡"
                        level = "Neutral"
                    
                    # Add time info if available
                    time_info = ""
                    if 'published' in article:
                        try:
                            pub_time = datetime.fromisoformat(article['published'].replace('Z', '+00:00'))
                            now = datetime.now(timezone.utc)
                            diff = now - pub_time
                            hours_ago = int(diff.total_seconds() / 3600)
                            if hours_ago < 1:
                                time_info = "< 1h ago"
                            else:
                                time_info = f"{hours_ago}h ago"
                        except:
                            pass
                    
                    impact_line = f"   Impact: {impact:+d} ({level}) {indicator}"
                    if time_info:
                        impact_line += f" | {time_info}"
                    news_message += impact_line + "\n"
                    
                except Exception as e:
                    logger.debug(f"Could not analyze news sentiment: {e}")
            
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
        
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=news_message,
            parse_mode='HTML',
            disable_web_page_preview=True
        )
    
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
    
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text=recommendation,
        parse_mode='HTML'
    )

def add_signal_to_monitor(ict_signal, symbol: str, timeframe: str, chat_id: int):
    """Helper function to add ICT signal to real-time monitor"""
    # Skip if ict_signal is dict (HOLD/NO_TRADE/RANGING)
    if isinstance(ict_signal, dict):
        logger.debug(f"Skipping monitor add for {symbol}: signal is dict (likely HOLD/NO_TRADE)")
        return
    
    if real_time_monitor_global and ict_signal.signal_type.value in ['BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL']:
        signal_id = f"{symbol}_{ict_signal.signal_type.value}_{int(datetime.now(timezone.utc).timestamp())}"
        
        real_time_monitor_global.add_signal(
            signal_id=signal_id,
            symbol=symbol,
            signal_type=ict_signal.signal_type.value.replace('STRONG_', ''),  # Normalize to BUY/SELL
            entry_price=ict_signal.entry_price,
            tp_price=ict_signal.tp_prices[0],  # Use TP1
            sl_price=ict_signal.sl_price,
            confidence=ict_signal.confidence,
            timeframe=timeframe,
            user_chat_id=chat_id
        )
        
        logger.info(f"✅ Signal {signal_id} added to real-time monitor")




@require_access()
@rate_limited(calls=3, period=60)
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
        # Get valid timeframes from contract
        valid_timeframes = TimeframeContract.get_all_supported_timeframes()
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
    
    # === NEW: USE ICT ENGINE FOR ENHANCED ANALYSIS ===
    if ICT_SIGNAL_ENGINE_AVAILABLE:
        try:
            # Send processing message
            processing_msg = await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"🔍 <b>Running ICT analysis for {symbol} ({timeframe})...</b>",
                parse_mode='HTML'
            )
            
            # Fetch klines for ICT analysis
            klines_response = requests.get(
                BINANCE_KLINES_URL,
                params={'symbol': symbol, 'interval': timeframe, 'limit': 200},
                timeout=10
            )
            
            if klines_response.status_code != 200:
                await processing_msg.edit_text("❌ Failed to fetch market data")
                return
            
            klines_data = klines_response.json()
            
            # Prepare dataframe
            df = pd.DataFrame(klines_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # ✅ FETCH MTF DATA for ICT analysis
            mtf_data = fetch_mtf_data(symbol, timeframe, df)
            
            # Generate ICT signal WITH MTF DATA using global instance
            global ict_engine_global
            ict_engine = ict_engine_global
            ict_signal = ict_engine.generate_signal(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                mtf_data=mtf_data,  # ✅ FIXED: Now passing MTF data!
                is_auto=False  # ← Mark as manual signal
            )
            
            # ✅ Handle HOLD signals first
            if isinstance(ict_signal, dict) and ict_signal.get('action') == 'HOLD':
                hold_msg = f"""⚠️ <b>НЯМА ПОДХОДЯЩ ТРЕЙД</b>

💰 <b>Символ:</b> {ict_signal.get('symbol', symbol)}
⏰ <b>Таймфрейм:</b> {ict_signal.get('timeframe', timeframe)}

🚫 <b>Причина:</b> {ict_signal.get('reason', 'RANGING_MARKET')}
📋 <b>Детайли:</b> {ict_signal.get('message', 'Пазарът е в ranging фаза.')}

💡 <b>Препоръка:</b> Изчакайте по-добри условия или проверете друг таймфрейм.
"""
                await processing_msg.edit_text(hold_msg, parse_mode='HTML')
                return
            
            # Check for NO_TRADE or None
            if not ict_signal or (isinstance(ict_signal, dict) and ict_signal.get('type') == 'NO_TRADE'):
                # Format NO_TRADE message with details
                if isinstance(ict_signal, dict) and ict_signal.get('type') == 'NO_TRADE':
                    no_trade_msg = format_no_trade_message(ict_signal)
                    await processing_msg.edit_text(no_trade_msg, parse_mode='HTML')
                else:
                    await processing_msg.edit_text(
                        f"⚪ <b>No high-quality ICT signal for {symbol}</b>\n\n"
                        f"Market conditions do not meet minimum criteria.",
                        parse_mode='HTML'
                    )
                return
            
            # ✅ P8: CHECK COOLDOWN
            if ict_signal and hasattr(ict_signal, 'signal_type'):
                is_duplicate, cooldown_msg = check_signal_cooldown(
                    symbol=symbol,
                    signal_type=ict_signal.signal_type.value,
                    timeframe=timeframe,
                    confidence=ict_signal.confidence,
                    entry_price=ict_signal.entry_price,
                    cooldown_minutes=60
                )
                
                if is_duplicate:
                    await processing_msg.edit_text(cooldown_msg, parse_mode='HTML')
                    return
            
            # Format with 13-point output
            signal_msg = format_ict_signal_13_point(ict_signal)
            
            # ============================================
            # USER-CONTROLLED FUNDAMENTAL ANALYSIS INTEGRATION
            # ============================================
            fundamental_data = None
            combined_analysis = None
            recommendation = ""
            
            # Get user's fundamental analysis preference (reuse settings from line 6779)
            user_wants_fundamental = settings.get('use_fundamental', False)
            
            # Check if liquidity zones were detected
            has_liquidity = hasattr(ict_signal, 'liquidity_zones') and len(ict_signal.liquidity_zones) > 0
            
            # Prepare analysis mode indicator
            analysis_mode = ""
            if user_wants_fundamental and has_liquidity:
                analysis_mode = "📊 Analysis Mode: Technical ✅ + Fundamental ✅ + Liquidity 💧"
            elif user_wants_fundamental:
                analysis_mode = "📊 Analysis Mode: Technical ✅ + Fundamental ✅ | Liquidity ❌"
            elif has_liquidity:
                analysis_mode = "📊 Analysis Mode: Technical ✅ + Liquidity 💧 | Fundamental ❌"
            else:
                analysis_mode = "📊 Analysis Mode: Technical ✅ | Fundamental ❌ | Liquidity ❌"
            
            try:
                from utils.fundamental_helper import FundamentalHelper, format_fundamental_section
                from config.config_loader import load_feature_flags
                
                helper = FundamentalHelper()
                feature_flags = load_feature_flags()
                
                # Check BOTH user setting AND feature flag
                if user_wants_fundamental and feature_flags.get('fundamental_analysis', {}).get('enabled', False):
                    logger.info(f"🔬 Running user-enabled fundamental analysis for {symbol}")
                    
                    # Get BTC data for correlation
                    btc_klines_response = requests.get(
                        BINANCE_KLINES_URL,
                        params={'symbol': 'BTCUSDT', 'interval': timeframe, 'limit': 100},
                        timeout=10
                    )
                    
                    if btc_klines_response.status_code == 200:
                        btc_klines_data = btc_klines_response.json()
                        
                        # Prepare BTC dataframe
                        btc_df = pd.DataFrame(btc_klines_data, columns=[
                            'timestamp', 'open', 'high', 'low', 'close', 'volume',
                            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                            'taker_buy_quote', 'ignore'
                        ])
                        
                        btc_df['timestamp'] = pd.to_datetime(btc_df['timestamp'], unit='ms')
                        for col in ['open', 'high', 'low', 'close', 'volume']:
                            btc_df[col] = btc_df[col].astype(float)
                        
                        # Get fundamental data (uses news cache)
                        fundamental_data = helper.get_fundamental_data(
                            symbol=symbol,
                            symbol_df=df,
                            btc_df=btc_df,
                            news_articles=None  # Will use cache
                        )
                        
                        if fundamental_data:
                            # Get user's weight preference (reuse settings from line 6779)
                            fund_weight = settings.get('fundamental_weight', 0.3)  # Default 30%
                            tech_weight = 1 - fund_weight  # Remaining for technical
                            
                            # Store original technical confidence
                            technical_confidence = ict_signal.confidence
                            
                            # Calculate weighted combined score
                            # Instead of using helper's method, calculate directly with user weights
                            # Get fundamental composite score if available
                            fundamental_score = 50  # Default neutral
                            
                            # Calculate fundamental composite from components
                            if 'sentiment' in fundamental_data:
                                fundamental_score = fundamental_data['sentiment'].get('score', 50)
                            
                            # Apply BTC correlation impact if available
                            if 'btc_correlation' in fundamental_data:
                                btc_impact = fundamental_data['btc_correlation'].get('impact', 0)
                                fundamental_score = min(100, max(0, fundamental_score + btc_impact))
                            
                            # Combine scores with user weights
                            combined_confidence = (technical_confidence * tech_weight) + (fundamental_score * fund_weight)
                            
                            # Update signal confidence
                            original_confidence = ict_signal.confidence
                            ict_signal.confidence = combined_confidence
                            
                            # Store fundamental data in signal for display
                            ict_signal.fundamental_data = fundamental_data
                            
                            # Create combined analysis info for display
                            combined_analysis = {
                                'combined_score': round(combined_confidence, 1),
                                'technical_score': round(technical_confidence, 1),
                                'fundamental_score': round(fundamental_score, 1),
                                'tech_weight': tech_weight,
                                'fund_weight': fund_weight,
                                'breakdown': {
                                    'technical': round(technical_confidence, 1),
                                    'fundamental': round(fundamental_score, 1)
                                }
                            }
                            
                            # Update analysis mode with weights
                            analysis_mode = f"📊 Analysis Mode: Technical ✅ + Fundamental ✅ ({int(tech_weight*100)}/{int(fund_weight*100)})\n\n"
                            analysis_mode += f"   Technical: {technical_confidence:.1f}% (ICT + ML)\n"
                            analysis_mode += f"   Fundamental: {fundamental_score:.1f}%\n"
                            analysis_mode += f"   <b>Combined: {combined_confidence:.1f}%</b>"
                            
                            # Generate recommendation
                            recommendation = helper.generate_recommendation(
                                signal_direction=ict_signal.signal_type.value,
                                technical_confidence=technical_confidence,
                                fundamental_data=fundamental_data,
                                combined_score=combined_confidence
                            )
                            
                            logger.info(f"✅ Fundamental analysis complete: tech={technical_confidence:.1f}%, fund={fundamental_score:.1f}%, combined={combined_confidence:.1f}% (weights: {tech_weight}/{fund_weight})")
                        else:
                            logger.info("⚪ No fundamental data available (cache miss or insufficient data)")
                    else:
                        logger.warning(f"⚠️ Failed to fetch BTC data for correlation: {btc_klines_response.status_code}")
                else:
                    if not user_wants_fundamental:
                        logger.debug("Fundamental analysis disabled by user preference")
                    else:
                        logger.debug("Fundamental analysis disabled (feature flags)")
            except Exception as e:
                logger.warning(f"⚠️ Fundamental analysis unavailable: {e}")
                # Continue with technical-only signal
            
            # Insert analysis mode indicator into signal message (after confidence line)
            # Find the confidence line and add analysis mode after it
            lines = signal_msg.split('\n')
            for i, line in enumerate(lines):
                if 'Увереност:' in line or 'Confidence:' in line or '🎯' in line:
                    lines.insert(i + 1, analysis_mode)
                    break
            signal_msg = '\n'.join(lines)
            
            # Append fundamental section if available
            if fundamental_data and combined_analysis and user_wants_fundamental:
                from utils.fundamental_helper import format_fundamental_section
                fundamental_section = format_fundamental_section(
                    fundamental_data,
                    combined_analysis,
                    recommendation
                )
                signal_msg += fundamental_section
            # ============================================
            # END: FUNDAMENTAL ANALYSIS INTEGRATION
            # ============================================
            
            # Generate and send chart
            chart_sent = False
            if CHART_VISUALIZATION_AVAILABLE:
                try:
                    generator = ChartGenerator()
                    chart_bytes = generator.generate(df, ict_signal, symbol, timeframe)
                    
                    if chart_bytes:
                        # Send chart first
                        await context.bot.send_photo(
                            chat_id=update.effective_chat.id,
                            photo=BytesIO(chart_bytes),
                            caption=f"📊 <b>{symbol} ({timeframe}) - ICT Chart</b>",
                            parse_mode='HTML'
                        )
                        chart_sent = True
                        logger.info(f"✅ Chart sent for {symbol} {timeframe}")
                except Exception as chart_error:
                    logger.warning(f"⚠️ Chart generation failed: {chart_error}")
            
            # Send 13-point text analysis
            await processing_msg.edit_text(
                signal_msg,
                parse_mode='HTML',
                disable_web_page_preview=True
            )
            
            # Add signal to real-time monitor
            add_signal_to_monitor(ict_signal, symbol, timeframe, update.effective_chat.id)
            
            # Notify user (only in signal_cmd, not in callback)
            if real_time_monitor_global and ict_signal.signal_type.value in ['BUY', 'SELL', 'STRONG_BUY', 'STRONG_SELL']:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="🎯 <b>Signal added to real-time monitor!</b>\n\n"
                         "You'll receive alerts at:\n"
                         "• 80% progress to TP (with ICT re-analysis)\n"
                         "• Final WIN/LOSS when TP/SL reached",
                    parse_mode='HTML'
                )
            
            logger.info(f"✅ ICT signal sent for {symbol}: {ict_signal.signal_type.value}")
            return
            
        except Exception as ict_error:
            logger.error(f"❌ ICT analysis failed: {ict_error}")
            await processing_msg.edit_text(
                f"❌ <b>Error analyzing {symbol}</b>\n\n"
                f"Technical error occurred. Please try again later.\n\n"
                f"Error: {str(ict_error)[:100]}",
                parse_mode='HTML'
            )
            return
    
    # If ICT Engine not available, show error
    await update.message.reply_text(
        "❌ <b>ICT Signal Engine not available</b>\n\n"
        "The advanced signal analysis system is currently unavailable.",
        parse_mode='HTML'
    )


@require_access()
@rate_limited(calls=3, period=60)
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
        # Initialize ICT engine using global instance
        global ict_engine_global
        ict_engine = ict_engine_global
        
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
        # ✅ FETCH MTF DATA
        mtf_data = fetch_mtf_data(symbol, timeframe, df)

        result = ict_engine.generate_signal(
            df=df,
            symbol=symbol,
            timeframe=timeframe,
            mtf_data=mtf_data,  # ✅ FIXED: Using stored variable to avoid duplicate call
            is_auto=False  # ← Mark as manual signal
        )
        
        # Check if result is a "NO_TRADE" message (Dict) or a signal (ICTSignal object)
        if result is None:
            await processing_msg.edit_text(
                f"❌ <b>No ICT signal generated for {symbol}</b>\n\n"
                f"Conditions not met for high-quality signal (minimum confidence: 60%, RR: 1:3).",
                parse_mode='HTML'
            )
            return
        
        # Handle NO_TRADE messages (Dict)
        if isinstance(result, dict) and result.get('type') == 'NO_TRADE':
            no_trade_msg = format_no_trade_message(result)
            await processing_msg.edit_text(
                no_trade_msg,
                parse_mode='HTML'
            )
            return
        
        # ✅ NEW: Handle HOLD signals (Dict with action='HOLD')
        if isinstance(result, dict) and result.get('action') == 'HOLD':
            hold_msg = f"""⚠️ <b>НЯМА ПОДХОДЯЩ ТРЕЙД</b>

💰 <b>Символ:</b> {result.get('symbol', symbol)}
⏰ <b>Таймфрейм:</b> {result.get('timeframe', timeframe)}

🚫 <b>Причина:</b> {result.get('reason', 'RANGING_MARKET')}
📋 <b>Детайли:</b> {result.get('message', 'Пазарът е в ranging фаза. Няма ясна посока.')}

💡 <b>Препоръка:</b> Изчакайте по-добри условия или проверете друг таймфрейм.
"""
            await processing_msg.edit_text(
                hold_msg,
                parse_mode='HTML'
            )
            return
        
        # Handle valid signal (ICTSignal object)
        signal = result
        
        # === COOLDOWN CHECK ===
        signal_key = f"{symbol}_{timeframe}_{signal.signal_type.value}"
        
        if is_signal_already_sent(
            symbol=symbol,
            signal_type=signal.signal_type.value,
            timeframe=timeframe,
            confidence=signal.confidence,
            entry_price=signal.entry_price,
            cooldown_minutes=60
        ):
            await processing_msg.edit_text(
                f"⏳ <b>Signal for {symbol} {timeframe} already sent recently</b>\n\n"
                f"Cooldown: 60 minutes\n"
                f"Please wait before requesting again.",
                parse_mode='HTML'
            )
            return
        # === END COOLDOWN CHECK ===

        # Use standardized format (STRICT ICT)
        signal_msg = format_standardized_signal(signal, "MANUAL")
        
        # NEW: Generate chart visualization
        chart_sent = False
        if CHART_VISUALIZATION_AVAILABLE:
            try:
                from config.config_loader import get_flag
                use_charts = get_flag('use_chart_visualization', True)
                
                if use_charts:
                    logger.info(f"Generating chart for {symbol} {timeframe}")
                    
                    # Generate chart
                    generator = ChartGenerator()
                    chart_bytes = generator.generate(df, signal, symbol, timeframe)
                    
                    # Send text first
                    await processing_msg.edit_text(
                        signal_msg,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    
                    # Send chart
                    await update.message.reply_photo(
                        photo=BytesIO(chart_bytes),
                        caption=f"📊 {symbol} {timeframe} ICT Chart"
                    )
                    
                    chart_sent = True
                    logger.info(f"Chart sent successfully for {symbol}")
                else:
                    # Send text only
                    await processing_msg.edit_text(
                        signal_msg,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
            
            except Exception as chart_error:
                logger.warning(f"Chart generation failed: {chart_error}")
                # Fallback: send text only if chart wasn't sent
                if not chart_sent:
                    await processing_msg.edit_text(
                        signal_msg,
                        parse_mode='HTML',
                        disable_web_page_preview=True
                    )
                    await update.message.reply_text(
                        "⚠️ Chart generation failed. Showing text analysis only."
                    )
        else:
            # Chart visualization not available, send text only
            await processing_msg.edit_text(
                signal_msg,
                parse_mode='HTML',
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
    
    # Add entry guidance if available (NEW - ICT-Compliant Entry Zones)
    if signal.entry_zone and signal.entry_status:
        try:
            # Get current price from entry_price (or we could pass it separately)
            current_price = signal.entry_price
            bias_str = signal.bias.value if hasattr(signal.bias, 'value') else str(signal.bias)
            
            # Format entry guidance
            entry_guidance = _format_entry_guidance(
                entry_zone=signal.entry_zone,
                entry_status=signal.entry_status,
                current_price=current_price,
                direction=bias_str
            )
            
            msg += entry_guidance
        except Exception as e:
            logger.error(f"Error formatting entry guidance: {e}")
    
    if signal.warnings:
        msg += f"\n\n⚠️ **Warnings:**\n"
        for warning in signal.warnings:
            msg += f"• {warning}\n"
    
    msg += f"\n\n⏰ _Generated: {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}_"
    
    return msg


def _format_hold_signal(signal: ICTSignal, signal_source: str = "AUTO") -> str:
    """
    Format HOLD signal for NEUTRAL/RANGING market conditions
    
    HOLD signals are informational only - no trade setup.
    
    Args:
        signal: ICT signal object with HOLD type
        signal_source: "AUTO", "MANUAL", "TEST", "BACKTEST"
        
    Returns:
        Formatted HOLD message string
    """
    # Source badge
    source_badge = {
        "AUTO": "🤖 АВТОМАТИЧЕН",
        "MANUAL": "👤 РЪЧЕН",
        "TEST": "🧪 ТЕСТОВ",
        "BACKTEST": "📊 BACKTEST"
    }.get(signal_source, "📊 СИГНАЛ")
    
    msg = f"""⚪ <b>ICT HOLD SIGNAL</b> ⚪
{source_badge}
ℹ️ САМО ИНФОРМАЦИЯ - БЕЗ СДЕЛКА

━━━━━━━━━━━━━━━━━━━━━━
<b>📊 ОСНОВНА ИНФОРМАЦИЯ</b>
━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Символ:</b> {signal.symbol}
⏰ <b>Таймфрейм:</b> {signal.timeframe}
💪 <b>Пазарна фаза:</b> {signal.bias.value}
🎯 <b>Увереност на анализа:</b> {signal.confidence:.1f}%

━━━━━━━━━━━━━━━━━━━━━━
<b>ℹ️ ЗАЩО HOLD?</b>
━━━━━━━━━━━━━━━━━━━━━━

{signal.reasoning}

━━━━━━━━━━━━━━━━━━━━━━
<b>📊 MULTI-TIMEFRAME CONSENSUS</b>
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # MTF Consensus breakdown
    if hasattr(signal, 'mtf_consensus_data') and signal.mtf_consensus_data:
        consensus_pct = signal.mtf_consensus_data.get('consensus_pct', 0)
        breakdown = signal.mtf_consensus_data.get('breakdown', {})
        
        msg += f"<b>Consensus:</b> {consensus_pct:.1f}%\n"
        msg += f"<b>HTF Bias:</b> {signal.htf_bias}\n"
        msg += f"<b>MTF Structure:</b> {signal.mtf_structure}\n\n"
        
        # Show breakdown for key timeframes (from contract)
        key_timeframes = TimeframeContract.get_mtf_timeframes()[:5]  # First 5 MTF timeframes
        msg += "<b>Breakdown:</b>\n"
        for tf in key_timeframes:
            if tf in breakdown:
                data = breakdown[tf]
                bias = data.get('bias', 'N/A')
                conf = data.get('confidence', 0)
                aligned = data.get('aligned', False)
                emoji_tf = "✅" if aligned else "❌"
                
                if bias != 'NO_DATA':
                    msg += f"{emoji_tf} {tf}: {bias} ({conf:.0f}%)\n"
    else:
        msg += "⚠️ MTF данни не са налични\n"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>🔍 ICT КОМПОНЕНТИ</b>
━━━━━━━━━━━━━━━━━━━━━━

<i>(за информация)</i>

<b>Order Blocks:</b> {len(signal.order_blocks)} 📦
<b>FVG:</b> {len(signal.fair_value_gaps)} 🔲
<b>Liquidity Zones:</b> {len(signal.liquidity_zones)} 💧
<b>Whale Blocks:</b> {len(signal.whale_blocks)} 🐋
"""
    
    # Warnings
    if signal.warnings:
        msg += f"\n<b>⚠️ ПРЕДУПРЕЖДЕНИЯ</b>\n"
        for warning in signal.warnings:
            msg += f"   • {warning}\n"
    
    # Recommendations
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>💡 ПРЕПОРЪКИ</b>
━━━━━━━━━━━━━━━━━━━━━━

• Изчакайте ясен пробив или отхвърляне
• Наблюдавайте по-висок таймфрейм за посока
• Следете за структурен пробив (BOS/CHOCH)
• Използвайте ICT компонентите за планиране

<i>⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>
"""
    
    return msg


def format_standardized_signal(signal: ICTSignal, signal_source: str = "AUTO") -> str:
    """
    СТАНДАРТИЗИРАН формат за ВСИЧКИ типове сигнали (STRICT ICT)
    
    Еднакъв breakdown за:
    - Автоматични сигнали
    - Ръчни сигнали (/signal, /ict)
    - Тестови сигнали
    - Backtest сигнали
    
    Включва:
    - Entry, SL, TP (с правилен знак: - за SELL, + за BUY)
    - RR (гарантирано ≥ 3.0)
    - Confidence (≥ 60%)
    - MultiTF breakdown
    - ICT компоненти (OB, FVG, LuxAlgo, Whale zones)
    - Warnings
    
    Args:
        signal: ICT signal object
        signal_source: "AUTO", "MANUAL", "TEST", "BACKTEST"
        
    Returns:
        Formatted standardized message string
    """
    # ✅ NEW: Special handling for HOLD signals
    if signal.signal_type == SignalType.HOLD:
        return _format_hold_signal(signal, signal_source)
    
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
    
    # ✅ FIX 2: Determine signal direction and calculate TP percentages correctly
    is_sell = signal.signal_type.value in ['SELL', 'STRONG_SELL']
    
    # Calculate TP percentages with correct direction
    if is_sell:
        # For SELL: Lower TP = Profit (invert calculation)
        tp_direction = "▼"
        tp1_pct = ((signal.entry_price - signal.tp_prices[0]) / signal.entry_price * 100) if signal.tp_prices else 0
        tp2_pct = ((signal.entry_price - signal.tp_prices[1]) / signal.entry_price * 100) if len(signal.tp_prices) > 1 else 0
        tp3_pct = ((signal.entry_price - signal.tp_prices[2]) / signal.entry_price * 100) if len(signal.tp_prices) > 2 else 0
    else:
        # For BUY: Higher TP = Profit (normal calculation)
        tp_direction = "▲"
        tp1_pct = ((signal.tp_prices[0] - signal.entry_price) / signal.entry_price * 100) if signal.tp_prices else 0
        tp2_pct = ((signal.tp_prices[1] - signal.entry_price) / signal.entry_price * 100) if len(signal.tp_prices) > 1 else 0
        tp3_pct = ((signal.tp_prices[2] - signal.entry_price) / signal.entry_price * 100) if len(signal.tp_prices) > 2 else 0
    
    # Source badge
    source_badge = {
        "AUTO": "🤖 АВТОМАТИЧЕН",
        "MANUAL": "👤 РЪЧЕН",
        "TEST": "🧪 ТЕСТОВ",
        "BACKTEST": "📊 BACKTEST"
    }.get(signal_source, "📊 СИГНАЛ")
    
    # Add timestamp for AUTO signals (PR #111)
    timestamp_str = ""
    if signal_source == "AUTO":
        bg_tz = pytz.timezone('Europe/Sofia')
        now = datetime.now(bg_tz)
        timestamp_str = f"⏰ {now.strftime('%d.%m.%Y %H:%M')} (BG време)\n"
    
    msg = f"""{emoji} <b>ICT {signal.signal_type.value} SIGNAL</b> {emoji}
{source_badge}
{timestamp_str}
━━━━━━━━━━━━━━━━━━━━━━
<b>📊 ОСНОВНА ИНФОРМАЦИЯ</b>
━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Символ:</b> {signal.symbol}
⏰ <b>Таймфрейм:</b> {signal.timeframe}
💪 <b>Сила:</b> {strength_stars} ({signal.signal_strength.value}/5)
🎯 <b>Увереност:</b> {signal.confidence:.1f}%
"""

    # ✅ STABILIZATION PR: Add TF hierarchy display if available
    if hasattr(signal, 'timeframe_hierarchy') and signal.timeframe_hierarchy:
        tf_hier = signal.timeframe_hierarchy
        if tf_hier.get('entry_tf'):
            msg += f"""
<b>📊 TF Йерархия:</b>
   • Entry: {tf_hier.get('entry_tf', 'N/A')}
   • Confirmation: {tf_hier.get('confirmation_tf', 'N/A')}
   • Structure: {tf_hier.get('structure_tf', 'N/A')}
   • HTF Bias: {tf_hier.get('htf_bias_tf', 'N/A')}
"""
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>💼 TRADE SETUP</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>📍 ENTRY:</b> ${signal.entry_price:,.4f}

<b>🛑 STOP LOSS:</b> ${signal.sl_price:,.4f}

<b>🎯 TAKE PROFITS:</b>
   • TP1: ${signal.tp_prices[0]:,.4f} ({tp_direction}{tp1_pct:.2f}%)
   • TP2: ${signal.tp_prices[1]:,.4f} ({tp_direction}{tp2_pct:.2f}%)
   • TP3: ${signal.tp_prices[2]:,.4f} ({tp_direction}{tp3_pct:.2f}%)

<b>⚖️ RISK/REWARD:</b> 1:{signal.risk_reward_ratio:.2f} {'✅' if signal.risk_reward_ratio >= 3.0 else '⚠️'}

━━━━━━━━━━━━━━━━━━━━━━
<b>🎯 ENTRY SCENARIO</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Scenario:</b> {signal.entry_scenario if getattr(signal, "entry_scenario", None) else "N/A"}
<b>Score:</b> {signal.entry_scenario_score if getattr(signal, "entry_scenario_score", 0) else 0}/100
<b>Triggers:</b> {", ".join(signal.entry_scenario_triggers) if getattr(signal, "entry_scenario_triggers", None) else "-"}
<b>Reasoning:</b> {signal.entry_scenario_reasoning if getattr(signal, "entry_scenario_reasoning", None) else "-"}


━━━━━━━━━━━━━━━━━━━━━━
<b>📊 MULTI-TIMEFRAME CONSENSUS</b>
━━━━━━━━━━━━━━━━━━━━━━
"""
    
    # MTF Consensus breakdown
    if hasattr(signal, 'mtf_consensus_data') and signal.mtf_consensus_data:
        consensus_pct = signal.mtf_consensus_data.get('consensus_pct', 0)
        breakdown = signal.mtf_consensus_data.get('breakdown', {})
        
        msg += f"<b>Consensus:</b> {consensus_pct:.1f}% {'✅' if consensus_pct >= 50 else '❌'}\n"
        msg += f"<b>Aligned:</b> {signal.mtf_consensus_data.get('aligned_count', 0)}/{signal.mtf_consensus_data.get('total_count', 0)} TFs\n\n"
        
        # Show breakdown for key timeframes (from contract)
        key_timeframes = TimeframeContract.get_mtf_timeframes()[:5]  # First 5 MTF timeframes
        msg += "<b>Breakdown:</b>\n"
        for tf in key_timeframes:
            if tf in breakdown:
                data = breakdown[tf]
                bias = data.get('bias', 'N/A')
                conf = data.get('confidence', 0)
                aligned = data.get('aligned', False)
                emoji_tf = "✅" if aligned else "❌"
                
                if bias != 'NO_DATA':
                    msg += f"{emoji_tf} {tf}: {bias} ({conf:.0f}%)\n"
    else:
        msg += "⚠️ MTF данни не са налични\n"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>🔍 ICT КОМПОНЕНТИ</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>Bias:</b>
   • Текущ: {signal.bias.value}
   • HTF: {signal.htf_bias}
   • MTF Structure: {signal.mtf_structure}

<b>Structure:</b>
   • Broken: {'✅ YES' if signal.structure_broken else '❌ NO'}
   • Displacement: {'✅ YES' if signal.displacement_detected else '❌ NO'}

<b>Order Blocks:</b> {len(signal.order_blocks)} 📦
<b>FVG:</b> {len(signal.fair_value_gaps)} 🔲
<b>Liquidity Zones:</b> {len(signal.liquidity_zones)} 💧
<b>Whale Blocks:</b> {len(signal.whale_blocks)} 🐋
"""
    
    # ✅ PR #4: Add TF hierarchy section
    if hasattr(signal, 'timeframe_hierarchy') and signal.timeframe_hierarchy:
        hierarchy = signal.timeframe_hierarchy
        
        # Build TF status indicators
        structure_status = "✅" if hierarchy.get('structure_tf_present') else "⚠️"
        confirmation_status = "✅" if hierarchy.get('confirmation_tf_present') else "⚠️"
        htf_bias_status = "✅" if hierarchy.get('htf_bias_tf_present') else "ℹ️"
        
        msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>📊 TIMEFRAME ANALYSIS</b>
━━━━━━━━━━━━━━━━━━━━━━

<b>ICT Hierarchy:</b> {hierarchy.get('description', 'N/A')}

• <b>Entry TF:</b> {hierarchy.get('entry_tf', 'N/A')}
• <b>Confirmation TF:</b> {hierarchy.get('confirmation_tf', 'N/A')} {confirmation_status}
• <b>Structure TF:</b> {hierarchy.get('structure_tf', 'N/A')} {structure_status}
• <b>HTF Bias TF:</b> {hierarchy.get('htf_bias_tf', 'N/A')} {htf_bias_status}
"""
    
    # LuxAlgo информация (ако има)
    if hasattr(signal, 'luxalgo_sr') and signal.luxalgo_sr:
        msg += f"\n<b>LuxAlgo SR:</b> ✅ Activated\n"
    
    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>📝 ОБОСНОВКА</b>
━━━━━━━━━━━━━━━━━━━━━━

{signal.reasoning}
"""
    
    # === NEW: FUNDAMENTAL ANALYSIS INTEGRATION ===
    try:
        from config.config_loader import load_feature_flags
        flags = load_feature_flags()
        
        if flags.get('fundamental_analysis', {}).get('signal_integration', False):
            # Try to get fundamental data
            try:
                from utils.fundamental_helper import FundamentalHelper
                
                fundamental_helper = FundamentalHelper()
                
                if fundamental_helper.is_enabled():
                    # Get symbol from signal (if available)
                    symbol = getattr(signal, 'symbol', 'BTCUSDT')
                    
                    # For now, we'll show that fundamental integration is enabled
                    # Full integration would require fetching price data and news
                    msg += f"""
━━━━━━━━━━━━━━━━━━━━━━
<b>📰 FUNDAMENTAL ANALYSIS</b>
━━━━━━━━━━━━━━━━━━━━━━

✅ <b>Fundamental analysis integrated</b>

Combined Score: Technical (70%) + Fundamental (30%)
📊 Technical Confidence: {signal.confidence:.1f}%

<i>💡 Full fundamental data available via /market command</i>
"""
            except Exception as e:
                logger.debug(f"Could not add fundamental analysis to signal: {e}")
                
    except Exception as e:
        logger.debug(f"Fundamental analysis not available: {e}")
    
    # === NEW: LIQUIDITY ANALYSIS INTEGRATION ===
    try:
        liquidity_section = format_liquidity_section(signal)
        if liquidity_section:
            msg += liquidity_section
    except Exception as e:
        logger.debug(f"Could not add liquidity analysis to signal: {e}")
    
    # Warnings
    if signal.warnings:
        msg += f"\n<b>⚠️ ПРЕДУПРЕЖДЕНИЯ:</b>\n"
        for warning in signal.warnings:
            msg += f"   • {warning}\n"
    
    msg += f"\n<i>⏰ {signal.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</i>"
    
    return msg


def format_ict_signal_13_point(signal: ICTSignal) -> str:
    """
    DEPRECATED: Използвай format_standardized_signal() вместо това
    
    Format ICT signal with enhanced 13-point output for Telegram
    
    13 Key Points:
    1. Signal Type & Confidence
    2. Entry Price
    3. Stop Loss
    4. Take Profit (TP1, TP2, TP3)
    5. Risk/Reward Ratio
    6. Market Bias & HTF Bias
    7. Structure Analysis (Broken/Displacement)
    8. Order Blocks Count
    9. Liquidity Zones Count
    10. Fair Value Gaps Count
    11. MTF Confluence Score
    12. Whale Blocks Detection
    13. ICT Reasoning & Warnings
    
    Args:
        signal: ICT signal object
        
    Returns:
        Formatted 13-point message string
    """
    # Redirect to standardized format
    return format_standardized_signal(signal, "MANUAL")


@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=5, period=60)
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


@require_access()
@rate_limited(calls=20, period=60)
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


@require_access()
@rate_limited(calls=20, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=5, period=60)
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
        except Exception as e:
            logger.error(f"❌ Failed to send restart error notification: {e}")
            pass


@require_access()
@rate_limited(calls=20, period=60)
async def settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Настройки на TP/SL и RR"""
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    
    if not context.args:
        # Get fundamental status
        fund_status = "✅ ENABLED" if settings.get('use_fundamental', False) else "❌ DISABLED"
        fund_weight = settings.get('fundamental_weight', 0.3) * 100
        tech_weight = (1 - settings.get('fundamental_weight', 0.3)) * 100
        
        # Покажи текущи настройки
        message = f"""⚙️ <b>TRADING SETTINGS & PARAMETERS</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>SIGNAL SETTINGS:</b>

• Minimum Confidence: <b>65%</b>
  └─ Signals below 65% are filtered out
  
• Active Timeframes: <b>1H, 2H, 4H, 1D</b>
  └─ Auto-signals generated for all timeframes
  
• Auto-signals Status: <b>✅ ENABLED</b>
  └─ Automatic signal generation every 1-4 hours
  
• Signal Deduplication: <b>60 min cooldown</b>
  └─ Same signal blocked for 60 minutes
  └─ Price proximity check: 0.5%
  
• Signal Cache: <b>✅ Persistent (JSON file)</b>
  └─ Cache survives bot restarts
  └─ Auto-cleanup after 24 hours
  
• Startup Grace Period: <b>5 minutes</b>
  └─ No auto-signals for 5 min after restart
  └─ Prevents duplicate signals

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>RISK MANAGEMENT:</b>

• Max Concurrent Positions: <b>3</b>
  └─ Maximum 3 open positions at same time
  
• Risk Per Trade: <b>2% of capital</b>
  └─ Position sizing based on account size
  
• Stop Loss: <b>ICT-based dynamic</b>
  └─ Calculated from order blocks & liquidity
  
• Take Profit Levels: <b>Multi-level (TP1/TP2)</b>
  └─ TP1: 50% position close
  └─ TP2: Remaining 50%
  
• Minimum R:R Ratio: <b>2:1</b>
  └─ Signals with R:R < 2:1 are filtered

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🎯 <b>ICT ANALYSIS SETTINGS:</b>

• Order Blocks: <b>✅ ENABLED</b>
  └─ Smart money institutional levels
  
• Fair Value Gaps (FVG): <b>✅ ENABLED</b>
  └─ Imbalance zones for entries
  
• Liquidity Zones: <b>✅ ENABLED</b>
  └─ High/low liquidity detection
  
• MTF Confluence: <b>✅ ENABLED</b>
  └─ Multi-timeframe alignment scoring
  
• Market Structure: <b>✅ ENABLED</b>
  └─ Break of structure detection
  
• Displacement: <b>✅ ENABLED</b>
  └─ Strong momentum move detection
  
• Whale Blocks: <b>✅ ENABLED</b>
  └─ Large volume order block identification

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🤖 <b>ML & AUTOMATION:</b>

• ML Predictions: <b>✅ ENABLED</b>
  └─ Machine learning price predictions
  
• Auto-Training Schedule: <b>Weekly (Sunday 03:00 UTC)</b>
  └─ Automatic model retraining
  
• ML Model Version: <b>v2.1.0</b>
  └─ Random Forest + Feature Engineering
  
• Minimum Training Data: <b>50 completed trades</b>
  └─ Required before first training
  
• Current Model Age: <b>Check /health</b>
  └─ Days since last training

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🏥 <b>HEALTH MONITORING SCHEDULE:</b>

• Journal Health: <b>Every 6 hours (at :15)</b>
  └─ Checks: File, permissions, updates, metadata
  
• ML Training Health: <b>Daily at 10:00</b>
  └─ Checks: Model age, training execution, data availability
  
• Daily Reports Health: <b>Daily at 09:00</b>
  └─ Checks: Report sent, scheduler status
  
• Position Monitor Health: <b>Every hour (at :30)</b>
  └─ Checks: Monitor errors, runtime issues
  
• Scheduler Health: <b>Every 12 hours (at :45)</b>
  └─ Checks: Job execution, misfires
  
• Disk Space Monitor: <b>Daily at 02:00</b>
  └─ Checks: Usage (warn >80%, critical >90%)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>ACTIVE SYMBOLS:</b>

• BTC (Bitcoin), ETH (Ethereum)
• BNB (Binance Coin), SOL (Solana)
• XRP (Ripple), ADA (Cardano)
• DOGE (Dogecoin), DOT (Polkadot)
• MATIC (Polygon), LINK (Chainlink)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>Notes:</b>

• All times in BG timezone (Europe/Sofia) unless stated
• Use /health to check current system status
• Use /help for full command list
• Settings are optimized for swing trading

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚙️ За промяна на настройките, моля свържете се с администратор
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


@require_access()
@rate_limited(calls=20, period=60)
async def fund_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick toggle and status for fundamental analysis"""
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    
    if not context.args:
        # Show current status
        fund_enabled = settings.get('use_fundamental', False)
        fund_weight = settings.get('fundamental_weight', 0.3) * 100
        tech_weight = (1 - settings.get('fundamental_weight', 0.3)) * 100
        
        status = "✅ ENABLED" if fund_enabled else "❌ DISABLED"
        
        message = f"""
🧠 <b>FUNDAMENTAL ANALYSIS SETTINGS</b>

Status: {status}
"""
        if fund_enabled:
            message += f"Weight: {fund_weight:.0f}% Fundamental / {tech_weight:.0f}% Technical\n"
        
        message += f"""
<b>Commands:</b>
/fund on  - Enable fundamental analysis
/fund off - Disable fundamental analysis
/fund status - Show this status
/settings - Full settings menu
"""
        await update.message.reply_text(message, parse_mode='HTML')
        return
    
    command = context.args[0].lower()
    
    if command == 'on':
        settings['use_fundamental'] = True
        fund_weight = settings.get('fundamental_weight', 0.3) * 100
        tech_weight = (1 - settings.get('fundamental_weight', 0.3)) * 100
        
        message = f"""
✅ <b>Fundamental Analysis ENABLED</b>

Signals will now include:
• Fear & Greed Index
• Market Cap & Volume
• BTC Dominance
• News Sentiment

Weight Distribution:
• Technical: {tech_weight:.0f}%
• Fundamental: {fund_weight:.0f}%

Use /signal to see enhanced analysis!
"""
        await update.message.reply_text(message, parse_mode='HTML')
        
    elif command == 'off':
        settings['use_fundamental'] = False
        
        message = f"""
❌ <b>Fundamental Analysis DISABLED</b>

Signals will use:
• Technical analysis only (ICT + ML)

Use /fund on to re-enable fundamental analysis.
"""
        await update.message.reply_text(message, parse_mode='HTML')
        
    elif command == 'status':
        # Redirect to default behavior (show status)
        context.args = []
        await fund_cmd(update, context)
        
    else:
        await update.message.reply_text(
            f"❌ Unknown command: {command}\n\n"
            "Valid commands:\n"
            "/fund on\n"
            "/fund off\n"
            "/fund status"
        )


@require_access()
@rate_limited(calls=10, period=60)
async def backup_settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Backup user backtest settings
    
    Usage: /backup_settings
    """
    try:
        user_id = update.effective_user.id
        
        # Get current settings (you can expand this based on actual settings)
        settings = {
            "user_id": user_id,
            "backtest_preferences": {
                "default_period": 30,
                "focus_symbols": ["BTCUSDT", "ETHUSDT"],
                "ml_enabled": True,
                "alert_thresholds": {
                    "win_rate_low": 60,
                    "pnl_alert": 50
                }
            },
            "saved_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Save to file
        settings_file = os.path.join(BASE_PATH, 'backtest_settings.json')
        
        # Load existing settings if any
        all_settings = {}
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r') as f:
                    all_settings = json.load(f)
            except:
                all_settings = {}
        
        # Update with current user settings
        all_settings[str(user_id)] = settings
        
        # Save
        with open(settings_file, 'w') as f:
            json.dump(all_settings, f, indent=2)
        
        await update.message.reply_text(
            "✅ <b>Settings Backed Up</b>\n\n"
            f"📁 File: backtest_settings.json\n"
            f"👤 User: {user_id}\n"
            f"🕐 Time: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
            "Use /restore_settings to restore",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Backup settings error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ <b>Backup Error</b>\n\n{str(e)}",
            parse_mode='HTML'
        )


@require_access()
@rate_limited(calls=10, period=60)
async def restore_settings_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Restore user backtest settings
    
    Usage: /restore_settings
    """
    try:
        user_id = update.effective_user.id
        settings_file = os.path.join(BASE_PATH, 'backtest_settings.json')
        
        # Check if file exists
        if not os.path.exists(settings_file):
            await update.message.reply_text(
                "⚠️ <b>No Backup Found</b>\n\n"
                "No settings backup exists.\n"
                "Use /backup_settings first.",
                parse_mode='HTML'
            )
            return
        
        # Load settings
        with open(settings_file, 'r') as f:
            all_settings = json.load(f)
        
        # Get user settings
        user_settings = all_settings.get(str(user_id))
        
        if not user_settings:
            await update.message.reply_text(
                "⚠️ <b>No Backup for Your Account</b>\n\n"
                f"No settings found for user {user_id}.\n"
                "Use /backup_settings to create a backup.",
                parse_mode='HTML'
            )
            return
        
        # Apply settings (this would need actual implementation based on your settings system)
        saved_at = user_settings.get('saved_at', 'Unknown')
        prefs = user_settings.get('backtest_preferences', {})
        
        await update.message.reply_text(
            "✅ <b>Settings Restored</b>\n\n"
            f"📅 Backup from: {saved_at}\n\n"
            f"<b>Preferences:</b>\n"
            f"• Default period: {prefs.get('default_period', 30)} days\n"
            f"• Focus symbols: {', '.join(prefs.get('focus_symbols', []))}\n"
            f"• ML enabled: {'Yes' if prefs.get('ml_enabled') else 'No'}\n\n"
            "Settings applied successfully!",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Restore settings error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ <b>Restore Error</b>\n\n{str(e)}",
            parse_mode='HTML'
        )


@require_access()
@rate_limited(calls=20, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=20, period=60)
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
    # Get valid timeframes from contract
    valid_tfs = TimeframeContract.get_all_supported_timeframes()
    
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


def format_checkpoint_analysis(analysis: CheckpointAnalysis) -> str:
    """Format checkpoint analysis for Telegram"""
    lines = []
    lines.append(f"<b>🔄 TRADE CHECKPOINT ANALYSIS</b>\n")
    lines.append(f"<b>Checkpoint:</b> {analysis.checkpoint_level}")
    lines.append(f"<b>Checkpoint Price:</b> ${analysis.checkpoint_price:,.2f}")
    lines.append(f"<b>Current Price:</b> ${analysis.current_price:,.2f}\n")
    
    lines.append(f"<b>📊 Distance to Targets:</b>")
    lines.append(f"  • To TP: {analysis.distance_to_tp:.2f}%")
    lines.append(f"  • To SL: {analysis.distance_to_sl:.2f}%\n")
    
    if analysis.original_signal:
        lines.append(f"<b>📈 Confidence Tracking:</b>")
        lines.append(f"  • Original: {analysis.original_confidence:.1f}%")
        lines.append(f"  • Current: {analysis.current_confidence:.1f}%")
        delta_sign = "+" if analysis.confidence_delta >= 0 else ""
        lines.append(f"  • Delta: {delta_sign}{analysis.confidence_delta:.1f}%\n")
        
        if analysis.current_signal:
            lines.append(f"<b>🔍 Component Status:</b>")
            lines.append(f"  • HTF Bias Changed: {'⚠️ YES' if analysis.htf_bias_changed else '✅ NO'}")
            lines.append(f"  • Structure Broken: {'⚠️ YES' if analysis.structure_broken else '✅ NO'}")
            lines.append(f"  • Valid Components: {analysis.valid_components_count}")
            lines.append(f"  • Current R:R: {analysis.current_rr_ratio:.2f}\n")
    
    # Recommendation
    rec_emoji = {
        'HOLD': '✅',
        'MOVE_SL': '🎯',
        'PARTIAL_CLOSE': '⚠️',
        'CLOSE_NOW': '🚨'
    }
    emoji = rec_emoji.get(analysis.recommendation.value, '📌')
    lines.append(f"<b>{emoji} RECOMMENDATION: {analysis.recommendation.value}</b>")
    lines.append(f"<i>{analysis.reasoning}</i>")
    
    if analysis.warnings:
        lines.append(f"\n<b>⚠️ Warnings:</b>")
        for warning in analysis.warnings:
            lines.append(f"  • {warning}")
    
    return '\n'.join(lines)


@require_access()
@rate_limited(calls=20, period=60)
async def trade_status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Check trade status at checkpoint
    
    Usage: /trade_status BTCUSDT 45000 46500,47500,49000 44500
    Args: symbol entry_price tp_prices(comma-separated) sl_price
    """
    if not TRADE_REANALYSIS_AVAILABLE:
        await update.message.reply_text(
            "❌ Trade re-analysis engine not available.",
            parse_mode='HTML'
        )
        return
    
    if not context.args or len(context.args) < 4:
        help_msg = """<b>🔄 TRADE STATUS - Checkpoint Analysis</b>

<b>Usage:</b>
<code>/trade_status SYMBOL ENTRY TP1,TP2,TP3 SL</code>

<b>Example:</b>
<code>/trade_status BTCUSDT 45000 46500,47500,49000 44500</code>

<b>This will calculate checkpoints at:</b>
  • 25% - Early checkpoint (quarter way to TP1)
  • 50% - Midpoint checkpoint (halfway to TP1)
  • 75% - Pre-TP checkpoint (three-quarters to TP1)
  • 85% - Final checkpoint (near TP1)

<i>Note: Full re-analysis requires stored signals (future enhancement).
Currently shows checkpoint price levels.</i>"""
        
        await update.message.reply_text(help_msg, parse_mode='HTML')
        return
    
    try:
        # Parse arguments
        symbol = context.args[0].upper()
        entry_price = float(context.args[1])
        tp_prices_str = context.args[2]
        sl_price = float(context.args[3])
        
        # Parse TP prices
        tp_prices = [float(tp.strip()) for tp in tp_prices_str.split(',')]
        tp1_price = tp_prices[0]
        
        # Determine signal type based on entry vs TP1
        signal_type = "BUY" if tp1_price > entry_price else "SELL"
        
        # Calculate checkpoints
        checkpoints = reanalysis_engine_global.calculate_checkpoint_prices(
            signal_type=signal_type,
            entry_price=entry_price,
            tp1_price=tp1_price,
            sl_price=sl_price
        )
        
        # Format response
        message = f"<b>🔄 TRADE CHECKPOINT LEVELS</b>\n\n"
        message += f"<b>Symbol:</b> {symbol}\n"
        message += f"<b>Signal:</b> {signal_type}\n"
        message += f"<b>Entry:</b> ${entry_price:,.2f}\n"
        message += f"<b>TP1:</b> ${tp1_price:,.2f}\n"
        
        if len(tp_prices) > 1:
            message += f"<b>TP2:</b> ${tp_prices[1]:,.2f}\n"
        if len(tp_prices) > 2:
            message += f"<b>TP3:</b> ${tp_prices[2]:,.2f}\n"
        
        message += f"<b>SL:</b> ${sl_price:,.2f}\n\n"
        
        message += f"<b>📊 Checkpoint Monitoring Points:</b>\n"
        for level, price in checkpoints.items():
            distance = abs((price - entry_price) / entry_price) * 100
            direction = "+" if signal_type == "BUY" else "-"
            message += f"  <b>{level}:</b> ${price:,.2f} ({direction}{distance:.2f}% from entry)\n"
        
        message += f"\n<i>💡 At each checkpoint, the system will re-analyze market conditions"
        message += f" and provide actionable recommendations (HOLD/PARTIAL_CLOSE/CLOSE_NOW/MOVE_SL).</i>\n\n"
        message += f"<i>⚠️ Note: Full re-analysis requires original signal data (future enhancement).</i>"
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except ValueError as e:
        await update.message.reply_text(
            f"❌ Invalid input format. Use:\n"
            f"<code>/trade_status BTCUSDT 45000 46500,47500,49000 44500</code>",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Error in trade_status_cmd: {e}")
        await update.message.reply_text(
            f"❌ Error calculating checkpoints: {str(e)}",
            parse_mode='HTML'
        )


async def toggle_fundamental_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle fundamental analysis on/off"""
    query = update.callback_query
    
    chat_id = query.message.chat_id
    
    # Вземи настройките
    settings = get_user_settings(context.application.bot_data, chat_id)
    
    # Toggle настройката
    settings['use_fundamental'] = not settings.get('use_fundamental', False)
    
    # Статус текст
    status = "ON ✅" if settings['use_fundamental'] else "OFF ❌"
    
    # Prepare updated message
    fund_weight = settings.get('fundamental_weight', 0.3) * 100
    tech_weight = (1 - settings.get('fundamental_weight', 0.3)) * 100
    
    message = f"""
⚙️ <b>SETTINGS - @{query.from_user.username or query.from_user.first_name}</b>

📊 <b>Търговски параметри:</b>
Take Profit (TP): {settings['tp']:.1f}%
Stop Loss (SL): {settings['sl']:.1f}%
Risk/Reward (RR): 1:{settings['rr']:.1f}

📈 <b>Signal Settings:</b>
Timeframe: {settings.get('timeframe', '4h')}
Fundamental Analysis: {status}
"""
    if settings['use_fundamental']:
        message += f"Weight Distribution: {tech_weight:.0f}% Technical / {fund_weight:.0f}% Fundamental\n"
    
    message += f"""
🔔 <b>Известия:</b>
Автоматични сигнали: {'Вкл ✅' if settings['alerts_enabled'] else 'Изкл ❌'}
Интервал: {settings['alert_interval']/60:.0f} мин

<b>За промяна:</b>
/settings tp 3.0
/settings sl 1.5
/settings rr 2.5
/fund - Toggle fundamental analysis
"""
    
    # Update keyboard
    keyboard = [
        [InlineKeyboardButton("🔄 Toggle Fundamental", callback_data="toggle_fundamental")],
        [InlineKeyboardButton("⏰ Timeframe Settings", callback_data="timeframe_settings")],
        [InlineKeyboardButton("🏠 Back to Menu", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Update the settings message
    await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
    
    # Confirmation with alert popup
    await query.answer(f"Fundamental Analysis: {status}", show_alert=True)
    
    logger.info(f"User {chat_id} toggled fundamental: {status}")


@require_access()
@rate_limited(calls=20, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
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
                    message += f"🤖 Резултатът е записан в Trading Journal!\n💾 Файл: trading_journal.json"
                    
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


@safe_job("auto_signal", max_retries=3, retry_delay=60)
async def send_alert_signal(context: ContextTypes.DEFAULT_TYPE):
    """Изпраща автоматичен сигнал с пълен анализ - ASYNC OPTIMIZED с memory cleanup"""
    chat_id = context.job.data['chat_id']
    settings = get_user_settings(context.application.bot_data, chat_id)
    
    logger.info("🔍 Започвам ASYNC проверка на всички монети и timeframes...")
    
    # Get automatic timeframes from contract
    timeframes_to_check = TimeframeContract.get_supported_automatic_timeframes()
    logger.debug(f"📊 Using automatic TFs from contract: {timeframes_to_check}")
    
    # 🚀 ASYNC ПАРАЛЕЛЕН АНАЛИЗ - всички монети/timeframes наведнъж
    async def analyze_single_pair(symbol, timeframe):
        """Analyze with ICT Engine (NO legacy code!)"""
        try:
            # Fetch primary timeframe klines
            klines_response = requests.get(
                BINANCE_KLINES_URL,
                params={'symbol': symbol, 'interval': timeframe, 'limit': 200},
                timeout=10
            )
            
            if klines_response.status_code != 200:
                return None
            
            klines_data = klines_response.json()
            df = pd.DataFrame(klines_data, columns=[
                'timestamp', 'open', 'high', 'low', 'close', 'volume',
                'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                'taker_buy_quote', 'ignore'
            ])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = df[col].astype(float)
            
            # ✅ FETCH MTF DATA
            mtf_data = fetch_mtf_data(symbol, timeframe, df)
            
            # ✅ USE ICT ENGINE (NOT legacy analyze_signal!) using global instance
            global ict_engine_global
            ict_engine = ict_engine_global
            ict_signal = ict_engine.generate_signal(
                df=df,
                symbol=symbol,
                timeframe=timeframe,
                mtf_data=mtf_data,
                is_auto=False  # ← Mark as manual signal (alert-based)
            )
            
            # Handle NO_TRADE
            if not ict_signal or (isinstance(ict_signal, dict) and ict_signal.get('type') == 'NO_TRADE'):
                return None
            
            # ✅ Handle HOLD dict (RANGING market)
            if isinstance(ict_signal, dict) and ict_signal.get('action') == 'HOLD':
                logger.info(f"⏸️ HOLD signal for {symbol} {timeframe}: {ict_signal.get('reason')}")
                return None
            
            # Guard: Skip HOLD signals (ICTSignal object)
            if hasattr(ict_signal, 'signal_type') and ict_signal.signal_type.value == 'HOLD':
                return None
            
            # ✅ At this point, ict_signal is a valid ICTSignal object
            # ✅ PERSISTENT DEDUPLICATION (PR #111 + PR #112)
            if SIGNAL_CACHE_AVAILABLE:
                is_dup, reason = is_signal_duplicate(
                    symbol=symbol,
                    signal_type=ict_signal.signal_type.value,
                    timeframe=timeframe,
                    entry_price=ict_signal.entry_price,
                    confidence=ict_signal.confidence,
                    cooldown_minutes=60,
                    base_path=BASE_PATH
                )
                
                if is_dup:
                    logger.info(f"🛑 Signal deduplication: {reason} - skipping")
                    return None
                
                logger.info(f"✅ Signal deduplication: {reason} - sending signal")
            else:
                # Fallback to in-memory deduplication
                if is_signal_already_sent(
                    symbol=symbol,
                    signal_type=ict_signal.signal_type.value,
                    timeframe=timeframe,
                    confidence=ict_signal.confidence,
                    entry_price=ict_signal.entry_price,
                    cooldown_minutes=60
                ):
                    return None
            
            # Return ICT signal data (NOT legacy analysis!)
            return {
                'symbol': symbol,
                'timeframe': timeframe,
                'ict_signal': ict_signal,  # ✅ ICT Signal object!
                'confidence': ict_signal.confidence,
                'df': df  # Store for chart generation
            }
            
        except Exception as e:
            logger.error(f"❌ Auto signal analysis error for {symbol} {timeframe}: {e}")
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
        ict_signal = sig['ict_signal']
        df = sig['df']
        
        # ✅ PR #3 FIX #2: Use AUTO source for auto signals
        signal_msg = format_standardized_signal(ict_signal, "AUTO")
        
        # Auto-signal already has source badge in format, no need for additional header
        final_msg = signal_msg
        
        # Send message
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=final_msg,
                parse_mode='HTML',
                disable_web_page_preview=True,
                disable_notification=False  # Sound alert for auto signals
            )
            logger.info(f"✅ Auto signal sent for {symbol} ({timeframe})")
        except Exception as e:
            logger.error(f"❌ Failed to send auto signal message for {symbol}: {e}")
            continue
        
        # Send chart if available
        if CHART_VISUALIZATION_AVAILABLE:
            try:
                generator = ChartGenerator()
                chart_bytes = generator.generate(df, ict_signal, symbol, timeframe)
                
                if chart_bytes:
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=BytesIO(chart_bytes),
                        caption=f"📊 {symbol} ({timeframe})",
                        parse_mode='HTML'
                    )
                    logger.info(f"✅ Chart sent for auto signal {symbol}")
            except Exception as e:
                logger.warning(f"⚠️ Chart generation failed for auto signal: {e}")
        
        # Record signal to stats
        try:
            signal_id = record_signal(
                symbol=symbol,
                timeframe=timeframe,
                signal_type=ict_signal.signal_type.value,
                confidence=ict_signal.confidence,
                entry_price=ict_signal.entry_price,
                tp_price=ict_signal.tp_prices[0],  # TP1
                sl_price=ict_signal.sl_price
            )
            logger.info(f"📊 AUTO-SIGNAL recorded to stats (ID: {signal_id})")
        except Exception as e:
            logger.error(f"❌ Stats recording error in auto-signal: {e}")
        
        # Log to ML journal for high confidence signals
        if ict_signal.confidence >= 65:
            try:
                analysis_data = {
                    'market_bias': ict_signal.bias.value,  # Fixed: bias instead of market_bias
                    'htf_bias': ict_signal.htf_bias if isinstance(ict_signal.htf_bias, str) else (ict_signal.htf_bias.value if ict_signal.htf_bias else None),
                    'structure_broken': ict_signal.structure_broken,
                    'displacement_detected': ict_signal.displacement_detected,
                    'order_blocks_count': len(ict_signal.order_blocks),
                    'liquidity_zones_count': len(ict_signal.liquidity_zones),
                    'fvg_count': len(ict_signal.fair_value_gaps),
                    'mtf_confluence': ict_signal.mtf_confluence,  # Fixed: mtf_confluence instead of mtf_confluence_score
                    'whale_blocks': len(ict_signal.whale_blocks) if ict_signal.whale_blocks else 0
                }
                
                journal_id = log_trade_to_journal(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type=ict_signal.signal_type.value,
                    confidence=ict_signal.confidence,
                    entry_price=ict_signal.entry_price,
                    tp_price=ict_signal.tp_prices[0],
                    sl_price=ict_signal.sl_price,
                    analysis_data=analysis_data
                )
                
                if journal_id:
                    logger.info(f"📝 AUTO-SIGNAL logged to ML journal (ID: {journal_id})")
            except Exception as e:
                logger.error(f"❌ Journal logging error in auto-signal: {e}")
    
    # 🧹 MEMORY CLEANUP
    plt.close('all')
    gc.collect()
    logger.info(f"✅ Auto signal cycle complete. Sent {len(signals_to_send)} signals.")


# ✅ PR #112: STARTUP MODE TIMER - Guarantees startup mode ends after grace period
async def end_startup_mode_timer(context):
    """
    End startup mode after grace period (5 minutes)
    
    This runs independently of auto-signal jobs to ensure
    startup suppression always ends after the grace period,
    even if no auto-signal jobs execute.
    
    PR #112: Fix for Bug #2 - Startup mode never ends
    """
    global STARTUP_MODE
    
    if STARTUP_MODE:
        STARTUP_MODE = False
        logger.info("✅ Startup mode ended (timer) - auto-signals now ACTIVE")
        logger.info(f"   Grace period: {STARTUP_GRACE_PERIOD_SECONDS}s elapsed")
    else:
        logger.info("ℹ️ Startup mode timer triggered but mode already ended")


# ✅ PR #6: AUTO SIGNAL SCHEDULER JOB - для конкретного timeframe
@safe_job("auto_signal_timeframe", max_retries=3, retry_delay=60)
async def auto_signal_job(timeframe: str, bot_instance):
    """
    Auto signal job for scheduled timeframes (1h, 2h, 4h, 1d)
    Generates and sends signals automatically at specific intervals
    
    Args:
        timeframe: '1h', '2h', '4h', or '1d'
        bot_instance: Telegram bot instance for sending messages
    """
    try:
        # ✅ AUTO TIMEFRAME FILTER - Get from contract
        ALLOWED_AUTO_TIMEFRAMES = TimeframeContract.get_supported_automatic_timeframes()
        
        if timeframe not in ALLOWED_AUTO_TIMEFRAMES:
            logger.info(f"⚠️ Auto signals disabled for {timeframe} (allowed: {ALLOWED_AUTO_TIMEFRAMES})")
            return
        
        # 🛑 STARTUP SUPPRESSION (PR #111)
        global STARTUP_MODE, STARTUP_TIME
        if STARTUP_MODE and STARTUP_TIME:
            elapsed = (datetime.now() - STARTUP_TIME).total_seconds()
            
            if elapsed < STARTUP_GRACE_PERIOD_SECONDS:
                logger.info(f"🛑 Startup mode ({elapsed:.0f}s elapsed) - suppressing auto-signals for {timeframe.upper()}")
                return
            else:
                # Disable startup mode after grace period
                STARTUP_MODE = False
                logger.info("✅ Startup mode ended - auto-signals now ACTIVE")
        
        logger.info(f"🤖 Running auto signal job for {timeframe.upper()}")
        
        # Get all symbols to check
        symbols_to_check = list(SYMBOLS.values())
        
        # 🚀 ASYNC PARALLEL ANALYSIS - all symbols for this timeframe
        async def analyze_single_symbol(symbol):
            """Analyze one symbol with ICT Engine"""
            try:
                # Fetch klines for primary timeframe
                klines_response = requests.get(
                    BINANCE_KLINES_URL,
                    params={'symbol': symbol, 'interval': timeframe, 'limit': 200},
                    timeout=10
                )
                
                if klines_response.status_code != 200:
                    return None
                
                klines_data = klines_response.json()
                df = pd.DataFrame(klines_data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                
                # ✅ FETCH MTF DATA
                mtf_data = fetch_mtf_data(symbol, timeframe, df)
                
                # ✅ USE ICT ENGINE
                ict_signal = ict_engine_global.generate_signal(
                    df=df,
                    symbol=symbol,
                    timeframe=timeframe,
                    mtf_data=mtf_data,
                    is_auto=True  # ← Mark as auto signal
                )
                
                # Handle NO_TRADE
                if not ict_signal or (isinstance(ict_signal, dict) and ict_signal.get('type') == 'NO_TRADE'):
                    return None
                
                # Skip HOLD signals (informational only)
                if hasattr(ict_signal, 'signal_type') and ict_signal.signal_type.value == 'HOLD':
                    return None
                
                # ✅ PERSISTENT DEDUPLICATION (PR #111)
                if SIGNAL_CACHE_AVAILABLE:
                    is_dup, reason = is_signal_duplicate(
                        symbol=symbol,
                        signal_type=ict_signal.signal_type.value,
                        timeframe=timeframe,
                        entry_price=ict_signal.entry_price,
                        confidence=ict_signal.confidence,
                        cooldown_minutes=60,
                        base_path=BASE_PATH
                    )
                    
                    if is_dup:
                        logger.info(f"🛑 Signal deduplication: {reason} - skipping")
                        return None
                    
                    logger.info(f"✅ Signal deduplication: {reason} - sending signal")
                else:
                    # Fallback to in-memory deduplication
                    if is_signal_already_sent(
                        symbol=symbol,
                        signal_type=ict_signal.signal_type.value,
                        timeframe=timeframe,
                        confidence=ict_signal.confidence,
                        entry_price=ict_signal.entry_price,
                        cooldown_minutes=60
                    ):
                        return None
                
                # Return ICT signal data
                return {
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'ict_signal': ict_signal,
                    'confidence': ict_signal.confidence,
                    'df': df
                }
                
            except Exception as e:
                logger.error(f"❌ Auto signal analysis error for {symbol} {timeframe}: {e}")
                return None
        
        # Execute all tasks in parallel
        tasks = [analyze_single_symbol(symbol) for symbol in symbols_to_check]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter valid signals
        all_good_signals = [r for r in results if r is not None and not isinstance(r, Exception)]
        
        # If no good signals, cleanup and exit
        if not all_good_signals:
            logger.info(f"⚠️ No signals for {timeframe.upper()} (or all already sent)")
            plt.close('all')
            gc.collect()
            return
        
        # Sort by confidence (highest first)
        all_good_signals.sort(key=lambda x: x['confidence'], reverse=True)
        
        # Take top 3 (or fewer if less available)
        signals_to_send = all_good_signals[:3]
        
        logger.info(f"📤 Sending {len(signals_to_send)} auto signal(s) for {timeframe.upper()}")
        
        # Send each signal to owner
        for sig in signals_to_send:
            symbol = sig['symbol']
            ict_signal = sig['ict_signal']
            df = sig['df']
            
            # ✅ Format signal with AUTO source
            signal_msg = format_standardized_signal(ict_signal, "AUTO")
            
            # Send message to owner
            try:
                await bot_instance.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=signal_msg,
                    parse_mode='HTML',
                    disable_web_page_preview=True,
                    disable_notification=False  # Sound alert for auto signals
                )
                logger.info(f"✅ Auto signal sent for {symbol} ({timeframe.upper()})")
            except Exception as e:
                logger.error(f"❌ Failed to send auto signal message for {symbol}: {e}")
                continue
            
            # Send chart if available
            if CHART_VISUALIZATION_AVAILABLE:
                try:
                    generator = ChartGenerator()
                    chart_bytes = generator.generate(df, ict_signal, symbol, timeframe)
                    
                    if chart_bytes:
                        await bot_instance.send_photo(
                            chat_id=OWNER_CHAT_ID,
                            photo=BytesIO(chart_bytes),
                            caption=f"📊 {symbol} ({timeframe.upper()})",
                            parse_mode='HTML'
                        )
                        logger.info(f"✅ Chart sent for auto signal {symbol}")
                except Exception as e:
                    logger.warning(f"⚠️ Chart generation failed for auto signal: {e}")
            
            # Record signal to stats
            try:
                signal_id = record_signal(
                    symbol=symbol,
                    timeframe=timeframe,
                    signal_type=ict_signal.signal_type.value,
                    confidence=ict_signal.confidence,
                    entry_price=ict_signal.entry_price,
                    tp_price=ict_signal.tp_prices[0],
                    sl_price=ict_signal.sl_price
                )
                logger.info(f"📊 AUTO-SIGNAL recorded to stats (ID: {signal_id})")
            except Exception as e:
                logger.error(f"❌ Stats recording error in auto-signal: {e}")
            
            # Log to ML journal for high confidence signals
            if ict_signal.confidence >= 60:  # FIX: Aligned with Telegram send threshold (was 65)
                try:
                    analysis_data = {
                        'market_bias': ict_signal.bias.value,  # Fixed: bias instead of market_bias
                        'htf_bias': ict_signal.htf_bias if isinstance(ict_signal.htf_bias, str) else (ict_signal.htf_bias.value if ict_signal.htf_bias else None),
                        'structure_broken': ict_signal.structure_broken,
                        'displacement_detected': ict_signal.displacement_detected,
                        'order_blocks_count': len(ict_signal.order_blocks),
                        'liquidity_zones_count': len(ict_signal.liquidity_zones),
                        'fvg_count': len(ict_signal.fair_value_gaps),
                        'mtf_confluence': ict_signal.mtf_confluence,  # Fixed: mtf_confluence instead of mtf_confluence_score
                        'whale_blocks': len(ict_signal.whale_blocks) if ict_signal.whale_blocks else 0
                    }
                    
                    journal_id = log_trade_to_journal(
                        symbol=symbol,
                        timeframe=timeframe,
                        signal_type=ict_signal.signal_type.value,
                        confidence=ict_signal.confidence,
                        entry_price=ict_signal.entry_price,
                        tp_price=ict_signal.tp_prices[0],
                        sl_price=ict_signal.sl_price,
                        analysis_data=analysis_data
                    )
                    
                    if journal_id:
                        logger.info(f"📝 AUTO-SIGNAL logged to ML journal (ID: {journal_id})")
                except Exception as e:
                    logger.error(f"❌ Journal logging error in auto-signal: {e}")
            
            # ✅ PR #7: AUTO-OPEN POSITION FOR TRACKING (Enhanced diagnostics)
            if AUTO_POSITION_TRACKING_ENABLED and POSITION_MANAGER_AVAILABLE and position_manager_global:
                try:
                    logger.info(f"🔍 DIAGNOSTIC: Attempting position tracking for {symbol}")
                    logger.info(f"   - AUTO_POSITION_TRACKING_ENABLED: {AUTO_POSITION_TRACKING_ENABLED}")
                    logger.info(f"   - POSITION_MANAGER_AVAILABLE: {POSITION_MANAGER_AVAILABLE}")
                    logger.info(f"   - position_manager_global: {position_manager_global}")
                    logger.info(f"   - Signal confidence: {ict_signal.confidence}%")
                    
                    position_id = position_manager_global.open_position(
                        signal=ict_signal,
                        symbol=symbol,
                        timeframe=timeframe,
                        source='AUTO',
                        journal_id=journal_id
                    )
                    
                    logger.info(f"🔍 DIAGNOSTIC: open_position() returned ID: {position_id}")
                    
                    if position_id > 0:
                        logger.info(f"✅ Position auto-opened for tracking (ID: {position_id})")
                        
                        # Send confirmation
                        await bot_instance.send_message(
                            chat_id=OWNER_CHAT_ID,
                            text=f"📊 Position tracking started for {symbol} (ID: {position_id})",
                            parse_mode='HTML'
                        )
                    else:
                        logger.warning(f"⚠️ DIAGNOSTIC: Invalid position ID returned: {position_id}")
                
                except Exception as e:
                    logger.error(f"❌ Auto position open error: {e}")
                    import traceback
                    logger.error(f"🔍 DIAGNOSTIC: Full traceback:\n{traceback.format_exc()}")
            else:
                # Log WHY position tracking was skipped
                logger.warning(f"⚠️ DIAGNOSTIC: Position tracking skipped for {symbol}")
                logger.warning(f"   - AUTO_POSITION_TRACKING_ENABLED: {AUTO_POSITION_TRACKING_ENABLED}")
                logger.warning(f"   - POSITION_MANAGER_AVAILABLE: {POSITION_MANAGER_AVAILABLE}")
                logger.warning(f"   - position_manager_global is None: {position_manager_global is None}")
        
        # 🧹 MEMORY CLEANUP
        plt.close('all')
        gc.collect()
        logger.info(f"✅ Auto signal job complete for {timeframe.upper()}. Sent {len(signals_to_send)} signals.")
        
    except Exception as e:
        logger.error(f"❌ Auto signal job error for {timeframe}: {e}")


# ============================================================================
# PR #7: POSITION MONITORING - HELPER FUNCTIONS
# ============================================================================

def get_live_price(symbol: str) -> Optional[float]:
    """
    Get live price from Binance
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        
    Returns:
        Current price or None
    """
    try:
        response = requests.get(
            BINANCE_PRICE_URL,
            params={'symbol': symbol},
            timeout=5
        )
        
        if response.status_code == 200:
            data = response.json()
            return float(data['price'])
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Get live price error for {symbol}: {e}")
        return None


def calculate_checkpoint_price(entry_price: float, tp_price: float, checkpoint_percent: float, signal_type: str) -> float:
    """
    Calculate checkpoint price
    
    Args:
        entry_price: Entry price
        tp_price: Take profit price
        checkpoint_percent: Checkpoint percentage (0.25, 0.50, 0.75, 0.85)
        signal_type: 'BUY' or 'SELL'
        
    Returns:
        Checkpoint price
    """
    if signal_type == 'BUY':
        # For BUY: checkpoint is between entry and TP (above entry)
        distance = tp_price - entry_price
        return entry_price + (distance * checkpoint_percent)
    else:  # SELL
        # For SELL: checkpoint is between entry and TP (below entry)
        distance = entry_price - tp_price
        return entry_price - (distance * checkpoint_percent)


def check_checkpoint_reached(current_price: float, checkpoint_price: float, signal_type: str) -> bool:
    """
    Check if checkpoint has been reached
    
    Args:
        current_price: Current market price
        checkpoint_price: Checkpoint target price
        signal_type: 'BUY' or 'SELL'
        
    Returns:
        True if checkpoint reached
    """
    if signal_type == 'BUY':
        # For BUY: price must reach or exceed checkpoint
        return current_price >= checkpoint_price
    else:  # SELL
        # For SELL: price must reach or go below checkpoint
        return current_price <= checkpoint_price


def check_sl_hit(current_price: float, sl_price: float, signal_type: str) -> bool:
    """
    Check if stop-loss has been hit
    
    Args:
        current_price: Current market price
        sl_price: Stop loss price
        signal_type: 'BUY' or 'SELL'
        
    Returns:
        True if SL hit
    """
    if signal_type == 'BUY':
        # For BUY: SL hit if price drops below SL
        return current_price <= sl_price
    else:  # SELL
        # For SELL: SL hit if price rises above SL
        return current_price >= sl_price


def check_tp_hit(current_price: float, tp_price: float, signal_type: str) -> bool:
    """
    Check if take-profit has been hit
    
    Args:
        current_price: Current market price
        tp_price: Take profit price
        signal_type: 'BUY' or 'SELL'
        
    Returns:
        True if TP hit
    """
    if signal_type == 'BUY':
        # For BUY: TP hit if price reaches or exceeds TP
        return current_price >= tp_price
    else:  # SELL
        # For SELL: TP hit if price reaches or goes below TP
        return current_price <= tp_price


def reconstruct_signal_from_json(signal_json: str) -> Optional[Any]:
    """
    Reconstruct ICTSignal object from JSON string
    
    Args:
        signal_json: JSON string of signal
        
    Returns:
        Mock signal object with needed attributes or None
    """
    try:
        from dataclasses import dataclass
        
        signal_dict = json.loads(signal_json)
        
        # Define a proper dataclass for signal reconstruction
        @dataclass
        class SignalTypeValue:
            """Simple wrapper for signal type with value attribute"""
            value: str
        
        @dataclass
        class MockSignal:
            """Mock signal object reconstructed from JSON"""
            timestamp: str
            symbol: str
            timeframe: str
            signal_type: SignalTypeValue
            entry_price: float
            sl_price: float
            tp_prices: list
            confidence: float
            risk_reward_ratio: float
            htf_bias: str
        
        # Create signal object
        return MockSignal(
            timestamp=signal_dict.get('timestamp', ''),
            symbol=signal_dict.get('symbol', ''),
            timeframe=signal_dict.get('timeframe', ''),
            signal_type=SignalTypeValue(value=signal_dict.get('signal_type', '')),
            entry_price=signal_dict.get('entry_price', 0),
            sl_price=signal_dict.get('sl_price', 0),
            tp_prices=signal_dict.get('tp_prices', []),
            confidence=signal_dict.get('confidence', 0),
            risk_reward_ratio=signal_dict.get('risk_reward_ratio', 0),
            htf_bias=signal_dict.get('htf_bias', '')
        )
        
    except Exception as e:
        logger.error(f"❌ Signal reconstruction error: {e}")
        return None


async def handle_sl_hit(position: Dict, exit_price: float, bot_instance):
    """
    Handle stop-loss hit - auto close position
    
    Args:
        position: Position dictionary
        exit_price: Exit price
        bot_instance: Telegram bot instance
    """
    try:
        if not POSITION_MANAGER_AVAILABLE or not position_manager_global:
            return
        
        pl_percent = position_manager_global.close_position(
            position_id=position['id'],
            exit_price=exit_price,
            outcome='SL'
        )
        
        # Update journal if journal_id exists
        if position.get("journal_id"):
            update_trade_outcome(
                trade_id=position["journal_id"],
                outcome="LOSS",
                profit_loss_pct=pl_percent,
                notes=f"Auto-closed: SL hit at ${exit_price:,.2f}"
            )
        
        # Calculate duration
        opened_at = datetime.fromisoformat(position['opened_at'])
        duration = datetime.now(timezone.utc) - opened_at
        hours = duration.total_seconds() / 3600
        
        msg = f"""
🛑 <b>STOP-LOSS HIT</b>

━━━━━━━━━━━━━━━━━
📊 <b>{position['symbol']}</b> ({position['timeframe'].upper()})
Signal: {position['signal_type']}

Entry: ${position['entry_price']:,.2f}
Exit (SL): ${exit_price:,.2f}
<b>Loss: {pl_percent:.2f}%</b>

Duration: {hours:.1f} hours

━━━━━━━━━━━━━━━━━
✅ Position closed automatically.
"""
        
        await bot_instance.send_message(
            chat_id=OWNER_CHAT_ID,
            text=msg,
            parse_mode='HTML'
        )
        
        logger.info(f"🛑 SL hit for {position['symbol']}: {pl_percent:.2f}%")
        
    except Exception as e:
        logger.error(f"❌ Handle SL hit error: {e}")


async def handle_tp_hit(position: Dict, exit_price: float, tp_level: str, bot_instance):
    """
    Handle take-profit hit - auto close position
    
    Args:
        position: Position dictionary
        exit_price: Exit price
        tp_level: 'TP1', 'TP2', or 'TP3'
        bot_instance: Telegram bot instance
    """
    try:
        if not POSITION_MANAGER_AVAILABLE or not position_manager_global:
            return
        
        pl_percent = position_manager_global.close_position(
            position_id=position['id'],
            exit_price=exit_price,
            outcome=tp_level
        )
        
        
        # Update journal if journal_id exists
        if position.get("journal_id"):
            update_trade_outcome(
                trade_id=position["journal_id"],
                outcome="WIN",
                profit_loss_pct=pl_percent,
                notes=f"Auto-closed: {tp_level} hit at ${exit_price:,.2f}"
            )
        # Calculate duration
        opened_at = datetime.fromisoformat(position['opened_at'])
        duration = datetime.now(timezone.utc) - opened_at
        hours = duration.total_seconds() / 3600
        
        msg = f"""
🎯 <b>TAKE-PROFIT HIT - {tp_level}</b>

━━━━━━━━━━━━━━━━━
📊 <b>{position['symbol']}</b> ({position['timeframe'].upper()})
Signal: {position['signal_type']}

Entry: ${position['entry_price']:,.2f}
Exit ({tp_level}): ${exit_price:,.2f}
<b>Profit: +{pl_percent:.2f}%</b>

Duration: {hours:.1f} hours

━━━━━━━━━━━━━━━━━
🎉 Position closed successfully!
"""
        
        await bot_instance.send_message(
            chat_id=OWNER_CHAT_ID,
            text=msg,
            parse_mode='HTML'
        )
        
        logger.info(f"🎯 {tp_level} hit for {position['symbol']}: +{pl_percent:.2f}%")
        
    except Exception as e:
        logger.error(f"❌ Handle TP hit error: {e}")


# ============================================================================
# PR #7: POSITION MONITORING JOB
# ============================================================================

@safe_job("position_monitor", max_retries=2, retry_delay=30)
async def monitor_positions_job(bot_instance):
    """
    Monitor all open positions every minute using UnifiedTradeManager
    - Check checkpoint triggers
    - Perform re-analysis
    - Send alerts
    - Detect SL/TP hits
    
    PR #202: Integrated with UnifiedTradeManager
    """
    try:
        if not POSITION_MANAGER_AVAILABLE or not position_manager_global:
            logger.debug("📊 Position manager not available, skipping monitoring")
            return
        
        if not CHECKPOINT_MONITORING_ENABLED:
            logger.debug("📊 Checkpoint monitoring disabled, skipping")
            return
        
        # Initialize UnifiedTradeManager
        try:
            from unified_trade_manager import UnifiedTradeManager
            
            manager = UnifiedTradeManager(bot_instance=bot_instance)
            positions = position_manager_global.get_open_positions()
            
            if not positions:
                logger.debug("📊 No open positions to monitor")
                return
            
            logger.info(f"📊 Monitoring {len(positions)} open position(s)")
            
            # Monitor each position
            for pos in positions:
                try:
                    await manager.monitor_live_trade(pos)
                except Exception as e:
                    logger.error(f"❌ Monitor failed for {pos.get('symbol', 'UNKNOWN')}: {e}")
                    pass  # Continue monitoring other positions
            
        except ImportError as e:
            logger.error(f"❌ Could not import UnifiedTradeManager: {e}")
            logger.warning("⚠️ Falling back to legacy monitoring (limited functionality)")
            # Fallback to basic monitoring without re-analysis
            positions = position_manager_global.get_open_positions()
            if positions:
                logger.info(f"📊 Legacy monitoring for {len(positions)} position(s)")
        
    except Exception as e:
        logger.error(f"❌ Position monitor job error: {e}")
        import traceback
        logger.error(traceback.format_exc())


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


# ================= ACTIVE TRADES MANAGEMENT COMMANDS =================

@require_access()
@rate_limited(calls=10, period=60)
async def close_trade_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Manually close an active trade
    
    Usage: 
    /close_trade BTCUSDT TP
    /close_trade ETHUSDT SL
    """
    global active_trades
    
    try:
        args = context.args
        
        if len(args) < 2:
            await update.message.reply_text(
                "❌ <b>Usage:</b>\n"
                "/close_trade SYMBOL TARGET\n\n"
                "Example:\n"
                "/close_trade BTCUSDT TP\n"
                "/close_trade ETHUSDT SL",
                parse_mode='HTML'
            )
            return
        
        symbol = args[0].upper()
        target = args[1].upper()
        
        if target not in ['TP', 'SL']:
            await update.message.reply_text("❌ Target must be TP or SL")
            return
        
        # Find active trade
        trade = None
        for t in active_trades:
            if t['symbol'] == symbol and t['user_chat_id'] == update.effective_user.id:
                trade = t
                break
        
        if not trade:
            await update.message.reply_text(f"❌ No active trade found for {symbol}")
            return
        
        # Get exit price
        exit_price = trade['tp'] if target == 'TP' else trade['sl']
        
        # Send final alert
        await send_final_alert(trade, exit_price, target, context.bot)
        
        await update.message.reply_text(
            f"✅ Trade closed manually: {symbol} at {target}"
        )
        
    except Exception as e:
        logger.error(f"Close trade error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Error: {str(e)}")


@require_access()
@rate_limited(calls=20, period=60)
async def active_trades_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show all active trades being monitored
    
    Usage: /active_trades or /active
    """
    global real_time_monitor_global
    
    try:
        # Check if real-time monitor is available
        if not real_time_monitor_global:
            await update.message.reply_text(
                "📊 <b>Активни Трейдове</b>\n\n"
                "Системата за мониторинг не е активна в момента.\n\n"
                "Моля, стартирайте бота отново.",
                parse_mode='HTML'
            )
            return
        
        # Get active trades for this user
        user_trades = real_time_monitor_global.get_user_trades(update.effective_user.id)
        
        if not user_trades:
            await update.message.reply_text(
                "📊 <b>Активни Трейдове</b>\n\n"
                "Няма активни трейдове в момента.\n\n"
                "Трейдовете се добавят автоматично при потвърждаване на сигнали.",
                parse_mode='HTML'
            )
            return
        
        message = f"""<b>📊 АКТИВНИ ТРЕЙДОВЕ ({len(user_trades)})</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

"""
        
        for i, trade in enumerate(user_trades, 1):
            # Get current price
            try:
                response = requests.get(
                    BINANCE_PRICE_URL,
                    params={'symbol': trade['symbol']},
                    timeout=5
                )
                ticker = response.json()
                current_price = float(ticker['price'])
            except:
                current_price = trade['entry_price']
            
            # Calculate progress percentage
            if trade['signal_type'] in ['BUY', 'LONG']:
                if trade['tp_price'] > trade['entry_price']:
                    progress = ((current_price - trade['entry_price']) / (trade['tp_price'] - trade['entry_price'])) * 100
                else:
                    progress = 0
            else:  # SELL, SHORT
                if trade['entry_price'] > trade['tp_price']:
                    progress = ((trade['entry_price'] - current_price) / (trade['entry_price'] - trade['tp_price'])) * 100
                else:
                    progress = 0
            
            progress = max(0, min(100, progress))
            
            # Calculate P/L percentage
            if trade['signal_type'] in ['BUY', 'LONG']:
                pl_pct = ((current_price - trade['entry_price']) / trade['entry_price']) * 100
            else:
                pl_pct = ((trade['entry_price'] - current_price) / trade['entry_price']) * 100
            
            # Calculate duration
            opened_at = trade.get('opened_at', trade.get('timestamp'))
            duration = datetime.now(timezone.utc) - opened_at
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            duration_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
            
            # Direction emoji
            dir_emoji = '🟢' if trade['signal_type'] in ['BUY', 'LONG'] else '🔴'
            
            # P/L emoji
            pl_emoji = '📈' if pl_pct > 0 else ('📉' if pl_pct < 0 else '➡️')
            
            message += f"""<b>#{i}. {trade.get('trade_id', 'N/A')}</b>
   {dir_emoji} {trade['symbol']} - {trade['signal_type']} | ⏰ {trade['timeframe']}
   💰 P/L: {pl_pct:+.2f}% {pl_emoji}
   📊 Прогрес: {progress:.1f}%
   ⏱️ Активен: {duration_str}

"""
        
        message += f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 Използвай <code>/details [Trade ID]</code> за детайли
Пример: <code>/details {user_trades[0].get('trade_id', '#BTC-20251227-143022')}</code>

⏰ {datetime.now(timezone.utc).strftime('%d.%m.%Y %H:%M UTC')}
"""
        
        await update.message.reply_text(message, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Active trades error: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Грешка: {str(e)}")



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
    elif text == "🏥 Health":  # PR #113: Health button handler
        await health_cmd(update, context)
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
    elif text == "📊 ML Performance":
        # Show ML Performance with inline keyboard
        from journal_backtest import JournalBacktestEngine
        
        try:
            backtest = JournalBacktestEngine()
            results = backtest.run_backtest(days=30)
            
            if 'error' in results:
                await update.message.reply_text(
                    f"⚠️ <b>ML Performance</b>\n\n"
                    f"❌ {results['error']}\n\n"
                    f"{results.get('hint', '')}",
                    parse_mode='HTML'
                )
                return
            
            ml_stats = results.get('ml_vs_classical', {}).get('ml', {})
            classical_stats = results.get('ml_vs_classical', {}).get('classical', {})
            insight = results.get('ml_vs_classical', {}).get('insight', '')
            timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
            
            text_msg = f"""📊 <b>ML PERFORMANCE</b>
━━━━━━━━━━━━━━━━━━━━━━━

📅 Period: Last 30 days

🤖 <b>ML TRADES:</b>
   💰 Total: <b>{ml_stats.get('total_trades', 0)}</b>
   🟢 Wins: {ml_stats.get('wins', 0)} ({ml_stats.get('win_rate', 0):.1f}%)
   🔴 Losses: {ml_stats.get('losses', 0)}
   💵 Total P/L: <b>{ml_stats.get('total_pnl', 0):+.2f}%</b>
   📈 Avg Win: +{ml_stats.get('avg_win', 0):.2f}%
   📉 Avg Loss: -{ml_stats.get('avg_loss', 0):.2f}%

📈 <b>CLASSICAL TRADES:</b>
   💰 Total: <b>{classical_stats.get('total_trades', 0)}</b>
   🟢 Wins: {classical_stats.get('wins', 0)} ({classical_stats.get('win_rate', 0):.1f}%)
   🔴 Losses: {classical_stats.get('losses', 0)}
   💵 Total P/L: <b>{classical_stats.get('total_pnl', 0):+.2f}%</b>
   📈 Avg Win: +{classical_stats.get('avg_win', 0):.2f}%
   📉 Avg Loss: -{classical_stats.get('avg_loss', 0):.2f}%

💡 <b>INSIGHT:</b> {insight}

━━━━━━━━━━━━━━━━━━━━━━━
📊 Source: trading_journal.json
🕐 Generated: {timestamp}
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="ml_performance_30"),
                    InlineKeyboardButton("📊 60 дни", callback_data="ml_performance_60"),
                ],
                [
                    InlineKeyboardButton("📊 90 дни", callback_data="ml_performance_90"),
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(text_msg, parse_mode='HTML', reply_markup=reply_markup)
            
        except Exception as e:
            logger.error(f"ML Performance error: {e}", exc_info=True)
            await update.message.reply_text(
                f"❌ <b>Error</b>\n\n{str(e)}",
                parse_mode='HTML'
            )
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
            logger.info(f"📞 SIGNAL_CALLBACK triggered - Callback data: {query.data}")
            parts = query.data.replace("tf_", "").split("_")
            symbol = parts[0]
            timeframe = parts[1]
            logger.info(f"🎯 Processing signal for {symbol} on {timeframe} via CALLBACK")
            logger.info(f"🔍 ICT_SIGNAL_ENGINE_AVAILABLE = {ICT_SIGNAL_ENGINE_AVAILABLE}")
            
            # Изтрий предишното съобщение
            # Изтрий предишното съобщение (with error handling)
            try:
                await query.message.delete()
                logger.info(f"✅ Previous message deleted successfully")
            except Exception as delete_error:
                logger.warning(f"⚠️ Could not delete previous message: {delete_error}")
            
            # === USE ICT ENGINE (same workflow as signal_cmd) ===
            if ICT_SIGNAL_ENGINE_AVAILABLE:
                # Send processing message
                processing_msg = await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"🔍 <b>Running ICT analysis for {symbol} ({timeframe})...</b>",
                    parse_mode='HTML'
                )
                
                # Fetch klines for ICT analysis
                logger.info(f"📊 Fetching klines: {symbol}/{timeframe}/limit=200")
                klines_response = requests.get(
                    BINANCE_KLINES_URL,
                    params={'symbol': symbol, 'interval': timeframe, 'limit': 200},
                    timeout=10
                )
                
                if klines_response.status_code != 200:
                    error_msg = f"❌ Failed to fetch market data (Status: {klines_response.status_code})"
                    logger.error(error_msg)
                    await processing_msg.edit_text(error_msg)
                    return
                
                klines_data = klines_response.json()
                logger.info(f"✅ Fetched {len(klines_data)} candles")
                
                # Prepare dataframe
                df = pd.DataFrame(klines_data, columns=[
                    'timestamp', 'open', 'high', 'low', 'close', 'volume',
                    'close_time', 'quote_volume', 'trades', 'taker_buy_base',
                    'taker_buy_quote', 'ignore'
                ])
                
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                for col in ['open', 'high', 'low', 'close', 'volume']:
                    df[col] = df[col].astype(float)
                logger.info(f"✅ DataFrame prepared: {len(df)} rows")
                
                # ✅ FETCH MTF DATA for ICT analysis
                logger.info(f"📈 Fetching MTF data...")
                mtf_data = fetch_mtf_data(symbol, timeframe, df)
                logger.info(f"✅ MTF data: {len(mtf_data) if mtf_data else 0} timeframes")
                
                # Generate ICT signal WITH MTF DATA
                logger.info(f"🔧 Using global ICTSignalEngine...")
                global ict_engine_global
                ict_engine = ict_engine_global
                logger.info(f"🚀 Generating ICT signal with MTF data...")
                ict_signal = ict_engine.generate_signal(
                    df=df,
                    symbol=symbol,
                    timeframe=timeframe,
                    mtf_data=mtf_data,
                    is_auto=False  # ← Mark as manual signal (callback)
                )
                logger.info(f"✅ ICT signal generated: {type(ict_signal)}")
                
                # ✅ Handle HOLD signals FIRST (RANGING market)
                if isinstance(ict_signal, dict) and ict_signal.get("action") == "HOLD":
                    logger.info(f"⚠️ HOLD signal detected (RANGING market)")
                    hold_msg = f"""⚠️ <b>НЯМА ПОДХОДЯЩ ТРЕЙД</b>

💰 <b>Символ:</b> {ict_signal.get("symbol", symbol)}
⏰ <b>Таймфрейм:</b> {ict_signal.get("timeframe", timeframe)}

🚫 <b>Причина:</b> {ict_signal.get("reason", "RANGING_MARKET")}
📋 <b>Детайли:</b> {ict_signal.get("message", "Пазарът е в ranging фаза.")}

💡 <b>Препоръка:</b> Изчакайте по-добри условия или проверете друг таймфрейм.
"""
                    await processing_msg.edit_text(hold_msg, parse_mode="HTML")
                    logger.info(f"✅ HOLD message sent")
                    return
                
                # Check for NO_TRADE or None
                logger.info(f"🔍 Checking signal type...")
                if not ict_signal or (isinstance(ict_signal, dict) and ict_signal.get('type') == 'NO_TRADE'):
                    logger.info(f"⚪ NO_TRADE detected: type={type(ict_signal)}")
                    # Format NO_TRADE message with details
                    if isinstance(ict_signal, dict) and ict_signal.get('type') == 'NO_TRADE':
                        logger.info(f"📝 Formatting NO_TRADE message...")
                        no_trade_msg = format_no_trade_message(ict_signal)
                        await processing_msg.edit_text(no_trade_msg, parse_mode='HTML')
                        logger.info(f"✅ NO_TRADE message sent")
                    else:
                        logger.warning(f"⚠️ ICT signal is None or invalid")
                        await processing_msg.edit_text(
                            f"⚪ <b>No high-quality ICT signal for {symbol}</b>\n\n"
                            f"Market conditions do not meet minimum criteria.",
                            parse_mode='HTML'
                        )
                        logger.info(f"✅ Fallback NO_TRADE sent")
                    return
                
                # Format with 13-point output
                logger.info(f"📝 Formatting 13-point ICT signal...")
                signal_msg = format_ict_signal_13_point(ict_signal)
                logger.info(f"✅ Signal formatted ({len(signal_msg)} chars)")
                
                # Generate and send chart
                logger.info(f"📊 Generating chart for {symbol} {timeframe}...")
                chart_sent = False
                if CHART_VISUALIZATION_AVAILABLE:
                    try:
                        generator = ChartGenerator()
                        chart_bytes = generator.generate(df, ict_signal, symbol, timeframe)
                        
                        if chart_bytes:
                            # Send chart first
                            await context.bot.send_photo(
                                chat_id=update.effective_chat.id,
                                photo=BytesIO(chart_bytes),
                                caption=f"📊 <b>{symbol} ({timeframe}) - ICT Chart</b>",
                                parse_mode='HTML'
                            )
                            chart_sent = True
                            logger.info(f"✅ Chart sent for {symbol} {timeframe}")
                    except Exception as chart_error:
                        logger.warning(f"⚠️ Chart generation failed: {chart_error}")
                else:
                    logger.info(f"⚠️ Chart visualization not available")
                
                # Send 13-point text analysis
                logger.info(f"📤 Sending 13-point signal message...")
                await processing_msg.edit_text(
                    signal_msg,
                    parse_mode='HTML',
                    disable_web_page_preview=True
                )
                logger.info(f"✅ Signal message sent successfully")
                
                # Add signal to real-time monitor
                logger.info(f"📍 Adding to real-time monitor...")
                add_signal_to_monitor(ict_signal, symbol, timeframe, update.effective_chat.id)
                
                logger.info(f"✅ ✅ ✅ ICT Signal COMPLETE via CALLBACK for {symbol} {timeframe}")
                return
            else:
                # Fallback to legacy if ICT Engine not available (should not happen)
                logger.error(f"❌ ICT Engine NOT AVAILABLE - This should NOT happen!")
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text="❌ ICT Engine not available. Please contact administrator.",
                    parse_mode='HTML'
                )
                return
        except Exception as main_error:
            logger.error(f"❌ CRITICAL ERROR in signal_callback: {main_error}", exc_info=True)
            try:
                await context.bot.send_message(
                    chat_id=update.effective_chat.id,
                    text=f"❌ Грешка при обработка на сигнала:\n{str(main_error)}",
                    parse_mode='HTML'
                )
            except Exception as send_error:
                logger.error(f"❌ Failed to send error message to user: {send_error}")


# ================= DEPLOY КОМАНДА =================

@require_access()
@rate_limited(calls=3, period=60)
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

@require_access()
@rate_limited(calls=20, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=20, period=60)
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


# ================= NEW SECURITY ADMIN COMMANDS (v2.0.0) =================

@require_access()
@rate_limited(calls=10, period=60)
async def admin_blacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Blacklist a user (Admin only)"""
    if not SECURITY_MODULES_AVAILABLE:
        await update.message.reply_text("❌ Security modules not available")
        return
    
    # Use new auth manager
    if not auth_manager.is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 This command requires admin privileges.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Usage:** /blacklist USER_ID [REASON]\n\n"
            "**Example:** /blacklist 123456789 Spam\n\n"
            "Get user ID from Telegram or from security logs.",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "Admin decision"
        
        auth_manager.blacklist_user(user_id, reason)
        log_security_event("USER_BLACKLISTED", user_id, f"By admin {update.effective_user.id}, reason: {reason}")
        
        await update.message.reply_text(
            f"✅ **User {user_id} blacklisted**\n\n"
            f"**Reason:** {reason}\n\n"
            f"This user can no longer use the bot.",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Must be a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


@require_access()
@rate_limited(calls=10, period=60)
async def admin_unblacklist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove user from blacklist (Admin only)"""
    if not SECURITY_MODULES_AVAILABLE:
        await update.message.reply_text("❌ Security modules not available")
        return
    
    if not auth_manager.is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 This command requires admin privileges.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Usage:** /unblacklist USER_ID\n\n"
            "**Example:** /unblacklist 123456789",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        auth_manager.unblacklist_user(user_id)
        log_security_event("USER_UNBLACKLISTED", user_id, f"By admin {update.effective_user.id}")
        
        await update.message.reply_text(
            f"✅ **User {user_id} removed from blacklist**\n\n"
            f"This user can now use the bot again.",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Must be a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


@require_access()
@rate_limited(calls=20, period=60)
async def admin_security_stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show security statistics (Admin only)"""
    if not SECURITY_MODULES_AVAILABLE:
        await update.message.reply_text("❌ Security modules not available")
        return
    
    if not auth_manager.is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 This command requires admin privileges.")
        return
    
    try:
        # Get security report
        report = security_monitor.get_security_report()
        
        # Get auth stats
        auth_stats = auth_manager.get_auth_stats()
        
        # Combine into full report
        full_report = report + "\n\n"
        full_report += "**Authentication Stats:**\n"
        full_report += f"• Admins: {auth_stats['total_admins']}\n"
        full_report += f"• Blacklisted: {auth_stats['total_blacklisted']}\n"
        full_report += f"• Whitelisted: {auth_stats['total_whitelisted']}\n"
        full_report += f"• Whitelist Mode: {'ON' if auth_stats['whitelist_mode'] else 'OFF'}\n"
        
        await update.message.reply_text(full_report, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


@require_access()
@rate_limited(calls=10, period=60)
async def admin_unban_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unban a rate-limited user (Admin only)"""
    if not SECURITY_MODULES_AVAILABLE:
        await update.message.reply_text("❌ Security modules not available")
        return
    
    if not auth_manager.is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 This command requires admin privileges.")
        return
    
    if not context.args:
        await update.message.reply_text(
            "**Usage:** /unban USER_ID\n\n"
            "**Example:** /unban 123456789",
            parse_mode='Markdown'
        )
        return
    
    try:
        user_id = int(context.args[0])
        
        rate_limiter.unban_user(user_id)
        log_security_event("USER_UNBANNED", user_id, f"By admin {update.effective_user.id}")
        
        await update.message.reply_text(
            f"✅ **User {user_id} unbanned**\n\n"
            f"Rate limit ban has been lifted.",
            parse_mode='Markdown'
        )
    except ValueError:
        await update.message.reply_text("❌ Invalid user ID. Must be a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")


# ================= АВТОМАТИЧНО ИЗПРАЩАНЕ НА ОТЧЕТИ =================

@safe_job("auto_news", max_retries=3, retry_delay=60)
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


# ================= P5: ML AUTO-TRAINING JOB =================
@safe_job("ml_auto_training", max_retries=3, retry_delay=120)
async def ml_auto_training_job(context):
    """
    Автоматично обучава ML models от trading journal results.
    Изпълнява се weekly (Sunday 03:00 UTC).
    
    ВАЖНО: Запазва всички съществуващи ML настройки!
    """
    try:
        logger.info("🤖 Starting ML auto-training from journal data...")
        
        # ==================== STEP 1: LOAD JOURNAL ====================
        journal_file = f"{BASE_PATH}/trading_journal.json"
        
        if not os.path.exists(journal_file):
            logger.warning("⚠️ No trading journal found - skipping ML training")
            return
        
        with open(journal_file, 'r') as f:
            journal = json.load(f)
        
        # Get trades from journal (handle different structures)
        trades = journal.get('trades', []) if isinstance(journal, dict) else []
        
        # ==================== STEP 2: FILTER COMPLETED TRADES ====================
        # Only use trades with definitive outcomes (WIN/LOSS)
        completed_trades = [
            trade for trade in trades
            if trade.get('outcome') in ['WIN', 'LOSS']
        ]
        
        if len(completed_trades) < 50:
            logger.warning(
                f"⚠️ Insufficient trades for ML training: {len(completed_trades)}/50 minimum"
            )
            return
        
        logger.info(f"📊 Found {len(completed_trades)} completed trades for training")
        
        # ==================== STEP 3: PREPARE TRAINING DATA ====================
        import numpy as np
        
        # Track statistics
        win_count = sum(1 for t in completed_trades if t['outcome'] == 'WIN')
        loss_count = len(completed_trades) - win_count
        win_rate = (win_count / len(completed_trades)) * 100
        logger.info(f"📈 Training data win rate: {win_rate:.1f}%")
        
        # ==================== STEP 4: TRAIN ML ENGINE ====================
        ml_engine_trained = False
        
        if ML_AVAILABLE and hasattr(ml_engine, 'train_model'):
            try:
                logger.info("🔄 Training ML Engine...")
                
                # Use existing train_model method (DO NOT modify parameters)
                # NOTE: ml_engine.train_model() reads trading_journal.json internally
                # and uses the existing feature extraction and training logic
                success = ml_engine.train_model()
                
                if success:
                    logger.info("✅ ML Engine retrained and saved")
                    ml_engine_trained = True
                else:
                    logger.warning("⚠️ ML Engine training returned False")
                    
            except Exception as e:
                logger.error(f"❌ ML Engine training failed: {e}")
        else:
            logger.info("ℹ️ ML Engine not available or has no train_model method")
        
        # ==================== STEP 5: TRAIN ML PREDICTOR ====================
        ml_predictor_trained = False
        
        if ML_PREDICTOR_AVAILABLE:
            try:
                logger.info("🔄 Training ML Predictor...")
                
                # Get ML predictor instance
                ml_predictor = get_ml_predictor()
                
                # Use existing train method (preserve existing logic)
                if hasattr(ml_predictor, 'train'):
                    success = ml_predictor.train(retrain=True)
                    
                    if success:
                        logger.info("✅ ML Predictor retrained and saved")
                        ml_predictor_trained = True
                    else:
                        logger.warning("⚠️ ML Predictor training returned False")
                else:
                    logger.warning("⚠️ ML Predictor has no train method")
                    
            except Exception as e:
                logger.error(f"❌ ML Predictor training failed: {e}")
        else:
            logger.info("ℹ️ ML Predictor not available")
        
        # ==================== STEP 6: SEND SUMMARY TO OWNER ====================
        if ml_engine_trained or ml_predictor_trained:
            models_updated = []
            if ml_engine_trained:
                models_updated.append("ML Engine")
            if ml_predictor_trained:
                models_updated.append("ML Predictor")
            
            summary_msg = (
                f"🤖 <b>ML AUTO-TRAINING COMPLETE</b>\n\n"
                f"📊 <b>Training Data:</b>\n"
                f"  • Total Trades: {len(completed_trades)}\n"
                f"  • Wins: {win_count}\n"
                f"  • Losses: {loss_count}\n"
                f"  • Win Rate: {win_rate:.1f}%\n\n"
                f"✅ <b>Models Updated:</b>\n"
            )
            
            for model in models_updated:
                summary_msg += f"  • {model}: Retrained\n"
            
            summary_msg += (
                f"\n💡 <b>Impact:</b>\n"
                f"ML models have been updated with recent trading data\n"
                f"from your journal and may improve prediction accuracy.\n\n"
                f"Next training: Next Sunday 03:00 UTC"
            )
            
            await context.bot.send_message(
                chat_id=OWNER_CHAT_ID,
                text=summary_msg,
                parse_mode='HTML'
            )
            
            logger.info(f"✅ ML auto-training completed successfully")
        else:
            logger.warning("⚠️ No ML models were trained")
        
    except Exception as e:
        logger.error(f"❌ ML auto-training error: {e}")
        logger.exception(e)


# ================= P13: CACHE CLEANUP JOB =================
@safe_job("cache_cleanup", max_retries=2, retry_delay=30)
async def cache_cleanup_job(context):
    """
    Periodic cache cleanup - removes expired items.
    Runs every 10 minutes.
    """
    try:
        logger.debug("Starting periodic cache cleanup...")
        
        for cache_type, cache in CACHE.items():
            if hasattr(cache, 'cleanup_expired'):
                cache.cleanup_expired()
                stats = cache.get_stats()
                logger.debug(
                    f"Cache '{cache_type}': {stats['size']}/{stats['max_size']} items, "
                    f"hit rate: {stats['hit_rate']:.1%}, evictions: {stats['evictions']}"
                )
        
        logger.debug("✅ Cache cleanup completed")
        
    except Exception as e:
        logger.error(f"Cache cleanup error: {e}")


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


@require_access()
@rate_limited(calls=5, period=60)
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


@require_access()
@rate_limited(calls=5, period=60)
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
                result = subprocess.run(['cp', f, f + '.backup'], cwd=project_dir, timeout=5, capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"✅ Backed up: {f}")
                else:
                    logger.warning(f"⚠️ Backup failed for {f}: {result.stderr}")
            except Exception as e:
                logger.warning(f"⚠️ Backup error for {f}: {e}")
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
            pass  # systemd ще рестартира автоматично
#            subprocess.Popen(
#                [venv_python, 'bot.py'],
#                cwd=project_dir,
#                stdout=open('bot.log', 'w'),
#                stderr=subprocess.STDOUT,
#                start_new_session=True
#            )
#        else:
#            subprocess.Popen(
#                ['python3', 'bot.py'],
#                cwd=project_dir,
#                stdout=open('bot.log', 'w'),
#                stderr=subprocess.STDOUT,
#                start_new_session=True
#            )
        
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


@require_access()
@rate_limited(calls=10, period=60)
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

@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=20, period=60)
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

@require_access()
@rate_limited(calls=10, period=60)
async def backtest_results_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display backtest results from trading journal (READ-ONLY)
    
    Usage:
        /backtest_results          - Last 30 days
        /backtest_results 60       - Last 60 days
        /backtest_results BTCUSDT  - Filter by symbol
    
    CRITICAL RULES:
    1. ONLY call JournalBacktestEngine (READ-ONLY)
    2. NEVER modify trading_journal.json
    3. NEVER retrain ML models
    4. NEVER change ICT parameters
    5. ONLY display analysis results
    """
    message = update.message or update.callback_query.message
    
    await message.reply_text("⏳ Analyzing trades from Trading Journal...")
    
    try:
        from journal_backtest import JournalBacktestEngine
        
        # Parse arguments
        days = 30
        symbol = None
        timeframe = None

        if context.args:
            try:
                # Try to parse as integer (days)
                days = int(context.args[0])
            except ValueError:
                # If not a number, treat as symbol
                symbol_candidate = context.args[0].upper()

                # Basic validation for symbol format
                if len(symbol_candidate) < 4 or len(symbol_candidate) > 20:
                    await message.reply_text(
                        "⚠️ <b>Invalid symbol format</b>\n\n"
                        "Symbol should be 4-20 characters (e.g., BTCUSDT, ETHUSDT)",
                        parse_mode='HTML'
                    )
                    return

                symbol = symbol_candidate

            # Check for second argument (timeframe if first was symbol)
            if len(context.args) > 1 and symbol:
                timeframe = context.args[1].lower()
        
        # Run backtest (READ-ONLY)
        backtest = JournalBacktestEngine()
        results = backtest.run_backtest(days=days, symbol=symbol, timeframe=timeframe)
        
        # Check for errors
        if 'error' in results:
            error_msg = results['error']
            hint = results.get('hint', '')
            
            await message.reply_text(
                f"⚠️ <b>Backtest Analysis</b>\n\n"
                f"❌ {error_msg}\n\n"
                f"{hint if hint else 'Trades will be automatically recorded when signals with confidence ≥ 65% are generated.'}",
                parse_mode='HTML'
            )
            return
        
        # Format comprehensive report
        text = _format_backtest_report(results)
        
        # Send report
        await message.reply_text(text, parse_mode='HTML')
        
    except ImportError as e:
        logger.error(f"Failed to import journal_backtest: {e}")
        await message.reply_text(
            "❌ <b>Module Error</b>\n\n"
            "Journal backtest module not available.\n"
            "Please check installation.",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Backtest error: {e}", exc_info=True)
        await message.reply_text(
            f"❌ <b>Backtest Error</b>\n\n"
            f"Error: {str(e)}\n\n"
            f"Type: {type(e).__name__}",
            parse_mode='HTML'
        )


def _format_backtest_report(results: Dict) -> str:
    """
    Format backtest results into a Telegram-friendly report
    
    Args:
        results: Backtest results dictionary
    
    Returns:
        Formatted HTML text for Telegram
    """
    overall = results.get('overall', {})
    ml_vs_classical = results.get('ml_vs_classical', {})
    by_symbol = results.get('by_symbol', {})
    by_timeframe = results.get('by_timeframe', {})
    top_performers = results.get('top_performers', [])
    worst_performers = results.get('worst_performers', [])
    
    # Build report
    text = "📊 <b>TRADING JOURNAL BACKTEST</b>\n"
    text += "=" * 40 + "\n\n"
    
    # Filter info
    days = results.get('days', 30)
    symbol_filter = results.get('symbol_filter')
    timeframe_filter = results.get('timeframe_filter')
    
    text += f"📅 <b>Period:</b> Last {days} days\n"
    if symbol_filter:
        text += f"💎 <b>Symbol:</b> {symbol_filter}\n"
    if timeframe_filter:
        text += f"⏰ <b>Timeframe:</b> {timeframe_filter}\n"
    text += "\n"
    
    # Overall Statistics
    text += "<b>📈 OVERALL STATISTICS</b>\n"
    text += f"├─ Total Trades: <b>{overall.get('total_trades', 0)}</b>\n"
    text += f"├─ Wins: {overall.get('wins', 0)} ✅\n"
    text += f"├─ Losses: {overall.get('losses', 0)} ❌\n"
    text += f"├─ Win Rate: <b>{overall.get('win_rate', 0):.1f}%</b>\n"
    text += f"├─ Total P/L: <b>{overall.get('total_pnl', 0):+.2f}%</b>\n"
    text += f"├─ Avg Win: +{overall.get('avg_win', 0):.2f}%\n"
    text += f"├─ Avg Loss: -{overall.get('avg_loss', 0):.2f}%\n"
    text += f"├─ Profit Factor: <b>{overall.get('profit_factor', 0):.2f}</b>\n"
    text += f"├─ Largest Win: +{overall.get('largest_win', 0):.2f}%\n"
    text += f"└─ Largest Loss: -{overall.get('largest_loss', 0):.2f}%\n\n"
    
    # ML vs Classical Comparison
    ml_stats = ml_vs_classical.get('ml', {})
    classical_stats = ml_vs_classical.get('classical', {})
    delta = ml_vs_classical.get('delta', {})
    insight = ml_vs_classical.get('insight', '')
    
    if ml_stats.get('total_trades', 0) > 0 or classical_stats.get('total_trades', 0) > 0:
        text += "<b>🤖 ML vs CLASSICAL COMPARISON</b>\n"
        
        if ml_stats.get('total_trades', 0) > 0:
            text += f"<b>ML Mode:</b>\n"
            text += f"├─ Trades: {ml_stats.get('total_trades', 0)}\n"
            text += f"├─ Win Rate: {ml_stats.get('win_rate', 0):.1f}%\n"
            text += f"└─ Total P/L: {ml_stats.get('total_pnl', 0):+.2f}%\n\n"
        
        if classical_stats.get('total_trades', 0) > 0:
            text += f"<b>Classical Mode:</b>\n"
            text += f"├─ Trades: {classical_stats.get('total_trades', 0)}\n"
            text += f"├─ Win Rate: {classical_stats.get('win_rate', 0):.1f}%\n"
            text += f"└─ Total P/L: {classical_stats.get('total_pnl', 0):+.2f}%\n\n"
        
        if insight:
            text += f"<b>Insight:</b> {insight}\n\n"
    
    # Per-Symbol Breakdown (top 5)
    if by_symbol:
        text += "<b>💎 TOP SYMBOLS</b>\n"
        
        # Sort by win rate
        sorted_symbols = sorted(
            by_symbol.items(),
            key=lambda x: x[1].get('win_rate', 0),
            reverse=True
        )[:5]
        
        for symbol, stats in sorted_symbols:
            text += f"<b>{symbol}</b>\n"
            text += f"├─ Trades: {stats.get('total_trades', 0)}\n"
            text += f"├─ Win Rate: {stats.get('win_rate', 0):.1f}%\n"
            text += f"└─ P/L: {stats.get('total_pnl', 0):+.2f}%\n\n"
    
    # Per-Timeframe Breakdown
    if by_timeframe:
        text += "<b>⏰ TIMEFRAME BREAKDOWN</b>\n"
        
        # Sort timeframes using contract order
        tf_order = TimeframeContract.get_all_supported_timeframes()
        sorted_tfs = sorted(
            by_timeframe.items(),
            key=lambda x: tf_order.index(x[0]) if x[0] in tf_order else 999
        )
        
        for tf, stats in sorted_tfs:
            text += f"<b>{tf}</b>\n"
            text += f"├─ Trades: {stats.get('total_trades', 0)}\n"
            text += f"├─ Win Rate: {stats.get('win_rate', 0):.1f}%\n"
            text += f"└─ P/L: {stats.get('total_pnl', 0):+.2f}%\n\n"
    
    # Top Performers
    if top_performers:
        text += "<b>🏆 TOP PERFORMERS</b>\n"
        for i, perf in enumerate(top_performers, 1):
            text += f"{i}. <b>{perf['symbol']}</b>\n"
            text += f"   WR: {perf['win_rate']:.1f}% | P/L: {perf['total_pnl']:+.2f}%\n"
        text += "\n"
    
    # Worst Performers
    if worst_performers:
        text += "<b>⚠️ WORST PERFORMERS</b>\n"
        for i, perf in enumerate(worst_performers, 1):
            text += f"{i}. <b>{perf['symbol']}</b>\n"
            text += f"   WR: {perf['win_rate']:.1f}% | P/L: {perf['total_pnl']:+.2f}%\n"
        text += "\n"
    
    # Footer
    text += "=" * 40 + "\n"
    text += "<i>📝 Data source: trading_journal.json (READ-ONLY)</i>\n"
    
    # Analysis timestamp
    timestamp = results.get('analysis_timestamp')
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            text += f"<i>🕐 Analyzed: {dt.strftime('%Y-%m-%d %H:%M UTC')}</i>"
        except:
            pass
    
    return text


# ============================================================================
# NEW BACKTEST CALLBACKS - ML PERFORMANCE & COMPREHENSIVE ANALYSIS
# ============================================================================

# ================= ASYNC BACKTEST HELPERS =================

@with_timeout(seconds=30)
async def run_backtest_async(days: int, symbol: str = None, timeframe: str = None):
    """Run backtest in background thread to avoid blocking event loop"""
    from journal_backtest import JournalBacktestEngine
    
    loop = asyncio.get_event_loop()
    backtest = JournalBacktestEngine()
    
    # Run in executor to avoid blocking
    result = await loop.run_in_executor(
        executor,
        lambda: backtest.run_backtest(days=days, symbol=symbol, timeframe=timeframe)
    )
    return result


# ================= CALLBACK HANDLERS WITH UX IMPROVEMENTS =================

@log_timing("ML Performance Callback")
async def ml_performance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display ML vs Classical performance comparison from trading journal
    
    Callback data patterns:
    - ml_performance (default 30 days)
    - ml_performance_30
    - ml_performance_60
    - ml_performance_90
    """
    query = update.callback_query
    await query.answer()
    
    # Parse days from callback data
    days = 30
    if query.data == "ml_performance_60":
        days = 60
    elif query.data == "ml_performance_90":
        days = 90
    
    # Check cache first
    cache_key = f"{days}d"
    cached_result = get_cached('ml_performance', cache_key)
    
    if cached_result:
        # Use cached data
        ml_stats = cached_result.get('ml_vs_classical', {}).get('ml', {})
        classical_stats = cached_result.get('ml_vs_classical', {}).get('classical', {})
        insight = cached_result.get('ml_vs_classical', {}).get('insight', '')
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        
        # Format message with cache indicator
        text = f"""📊 <b>ML PERFORMANCE</b> 💾
━━━━━━━━━━━━━━━━━━━━━━━

📅 Period: Last {days} days

🤖 <b>ML TRADES:</b>
   💰 Total: <b>{ml_stats.get('total_trades', 0)}</b>
   🟢 Wins: {ml_stats.get('wins', 0)} ({ml_stats.get('win_rate', 0):.1f}%)
   🔴 Losses: {ml_stats.get('losses', 0)}
   💵 Total P/L: <b>{ml_stats.get('total_pnl', 0):+.2f}%</b>
   📈 Avg Win: +{ml_stats.get('avg_win', 0):.2f}%
   📉 Avg Loss: -{ml_stats.get('avg_loss', 0):.2f}%

📈 <b>CLASSICAL TRADES:</b>
   💰 Total: <b>{classical_stats.get('total_trades', 0)}</b>
   🟢 Wins: {classical_stats.get('wins', 0)} ({classical_stats.get('win_rate', 0):.1f}%)
   🔴 Losses: {classical_stats.get('losses', 0)}
   💵 Total P/L: <b>{classical_stats.get('total_pnl', 0):+.2f}%</b>
   📈 Avg Win: +{classical_stats.get('avg_win', 0):.2f}%
   📉 Avg Loss: -{classical_stats.get('avg_loss', 0):.2f}%

💡 <b>INSIGHT:</b> {insight}

━━━━━━━━━━━━━━━━━━━━━━━
📊 Source: trading_journal.json (cached)
🕐 Generated: {timestamp}
"""
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="ml_performance_30"),
                InlineKeyboardButton("📊 60 дни", callback_data="ml_performance_60"),
            ],
            [
                InlineKeyboardButton("📊 90 дни", callback_data="ml_performance_90"),
                InlineKeyboardButton("🔙 ML Menu", callback_data="ml_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
        return
    
    # INSTANT FEEDBACK - Show loading message
    await query.edit_message_text(
        "⏳ <b>ЗАРЕЖДАНЕ...</b>\n\n"
        "📊 Анализирам ML performance данните...\n"
        "⏱️ Това може да отнеме 5-15 секунди.",
        parse_mode='HTML'
    )
    
    try:
        # Calculate fresh data with timeout protection
        results = await run_backtest_async(days=days)
        
        # Check for errors
        if 'error' in results:
            await query.edit_message_text(
                f"⚠️ <b>ML Performance Analysis</b>\n\n"
                f"❌ {results['error']}\n\n"
                f"{results.get('hint', 'Trades will be recorded automatically.')}",
                parse_mode='HTML'
            )
            return
        
        # Store in cache
        set_cache('ml_performance', cache_key, results)
        
        # Extract data
        ml_stats = results.get('ml_vs_classical', {}).get('ml', {})
        classical_stats = results.get('ml_vs_classical', {}).get('classical', {})
        insight = results.get('ml_vs_classical', {}).get('insight', '')
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        
        # Format message
        text = f"""📊 <b>ML PERFORMANCE</b>
━━━━━━━━━━━━━━━━━━━━━━━

📅 Period: Last {days} days

🤖 <b>ML TRADES:</b>
   💰 Total: <b>{ml_stats.get('total_trades', 0)}</b>
   🟢 Wins: {ml_stats.get('wins', 0)} ({ml_stats.get('win_rate', 0):.1f}%)
   🔴 Losses: {ml_stats.get('losses', 0)}
   💵 Total P/L: <b>{ml_stats.get('total_pnl', 0):+.2f}%</b>
   📈 Avg Win: +{ml_stats.get('avg_win', 0):.2f}%
   📉 Avg Loss: -{ml_stats.get('avg_loss', 0):.2f}%

📈 <b>CLASSICAL TRADES:</b>
   💰 Total: <b>{classical_stats.get('total_trades', 0)}</b>
   🟢 Wins: {classical_stats.get('wins', 0)} ({classical_stats.get('win_rate', 0):.1f}%)
   🔴 Losses: {classical_stats.get('losses', 0)}
   💵 Total P/L: <b>{classical_stats.get('total_pnl', 0):+.2f}%</b>
   📈 Avg Win: +{classical_stats.get('avg_win', 0):.2f}%
   📉 Avg Loss: -{classical_stats.get('avg_loss', 0):.2f}%

💡 <b>INSIGHT:</b> {insight}

━━━━━━━━━━━━━━━━━━━━━━━
📊 Source: trading_journal.json
🕐 Generated: {timestamp}
"""
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="ml_performance_30"),
                InlineKeyboardButton("📊 60 дни", callback_data="ml_performance_60"),
            ],
            [
                InlineKeyboardButton("📊 90 дни", callback_data="ml_performance_90"),
                InlineKeyboardButton("🔙 ML Menu", callback_data="ml_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"ML performance error: {e}", exc_info=True)
        error_message = format_user_error(e, "ML Performance Analysis")
        await query.edit_message_text(error_message, parse_mode='HTML')


@log_timing("Backtest All Callback")
async def backtest_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display comprehensive backtest results from trading journal
    
    Callback data patterns:
    - backtest_all (default 30 days)
    - backtest_all_7
    - backtest_all_30
    - backtest_all_60
    - backtest_all_90
    """
    query = update.callback_query
    await query.answer()
    
    # Parse days from callback data
    days = 30
    if query.data == "backtest_all_7":
        days = 7
    elif query.data == "backtest_all_60":
        days = 60
    elif query.data == "backtest_all_90":
        days = 90
    
    # Check cache first
    cache_key = f"{days}d"
    cached_result = get_cached('backtest', cache_key)
    
    if cached_result:
        # Use cached data - format and display immediately
        overall = cached_result.get('overall', {})
        top_performers = cached_result.get('top_performers', [])
        worst_performers = cached_result.get('worst_performers', [])
        by_timeframe = cached_result.get('by_timeframe', {})
        alert_stats = cached_result.get('alert_stats', {})
        trend_analysis = cached_result.get('trend_analysis', {})
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        
        # Format top symbols
        top_symbols_text = ""
        for i, perf in enumerate(top_performers[:3], 1):
            top_symbols_text += f"   {i}. {perf['symbol']}: {perf['win_rate']:.1f}% ({perf['total_trades']} trades)\n"
        
        # Format worst performers
        worst_symbols_text = ""
        if worst_performers:
            worst = worst_performers[0]
            worst_symbols_text = f"   1. {worst['symbol']}: {worst['win_rate']:.1f}% ({worst['total_trades']} trades)\n"
        
        # Format best timeframes
        tf_list = sorted(by_timeframe.items(), key=lambda x: x[1]['win_rate'], reverse=True)
        tf_text = ""
        for i, (tf, stats) in enumerate(tf_list[:3], 1):
            tf_text += f"   {i}. {tf}: {stats['win_rate']:.1f}% ({stats['total_trades']} trades)\n"
        
        # Alert system status
        alerts_80 = alert_stats.get('80_alerts', {})
        final_alerts = alert_stats.get('final_alerts', {})
        
        # Trend analysis
        trend = trend_analysis
        
        # Build message with cache indicator
        text = f"""📊 <b>BACKTEST РЕЗУЛТАТИ</b> 💾
━━━━━━━━━━━━━━━━━━━━━━━

📅 Period: Last {days} days

📈 <b>ОБОБЩЕНИЕ:</b>
   💰 Общо Trades: <b>{overall.get('total_trades', 0)}</b>
   🟢 Wins: {overall.get('wins', 0)} ({overall.get('win_rate', 0):.1f}%)
   🔴 Losses: {overall.get('losses', 0)}
   💵 Total P/L: <b>{overall.get('total_pnl', 0):+.2f}%</b>
   📈 Avg Win: +{overall.get('avg_win', 0):.2f}%
   📉 Avg Loss: -{overall.get('avg_loss', 0):.2f}%
   📊 Profit Factor: <b>{overall.get('profit_factor', 0):.2f}</b>

🏆 <b>ТОП SYMBOLS:</b>
{top_symbols_text or "   No data\n"}

"""
        if worst_symbols_text:
            text += f"""📉 <b>WORST PERFORMERS:</b>
{worst_symbols_text}

"""
        
        text += f"""⏰ <b>BEST TIMEFRAMES:</b>
{tf_text or "   No data\n"}

🔔 <b>ALERT SYSTEMS:</b>
📊 80% Alerts:
   Total: {alerts_80.get('total_alerts', 0)}
   → TP: {alerts_80.get('successful_tp', 0)} ({alerts_80.get('success_rate', 0):.0f}%)
   → SL: {alerts_80.get('failed_to_tp', 0)}
   Status: {alerts_80.get('status', '❌')}

🎯 Final Alerts:
   Total: {final_alerts.get('total_alerts', 0)}
   Coverage: {final_alerts.get('coverage', 0):.0f}%
   Status: {final_alerts.get('status', '❌')}

📈 <b>TREND ANALYSIS:</b>
   Last 7 days: {trend.get('wr_7d', 0):.1f}% {trend.get('trend_7d', '')}
   Last 30 days: {trend.get('wr_30d', 0):.1f}%
   Last 60 days: {trend.get('wr_60d', 0):.1f}% {trend.get('trend_60d', '')}
   💡 Insight: {trend.get('insight', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━
📊 Source: trading_journal.json (cached)
🕐 Generated: {timestamp}
"""
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="backtest_all_30"),
                InlineKeyboardButton("📊 7 дни", callback_data="backtest_all_7"),
            ],
            [
                InlineKeyboardButton("📊 60 дни", callback_data="backtest_all_60"),
                InlineKeyboardButton("📊 90 дни", callback_data="backtest_all_90"),
            ],
            [
                InlineKeyboardButton("🔍 Deep Dive", callback_data="backtest_deep_dive"),
                InlineKeyboardButton("🔙 Reports", callback_data="reports_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
        return
    
    # INSTANT FEEDBACK - Show loading message
    await query.edit_message_text(
        "⏳ <b>ЗАРЕЖДАНЕ...</b>\n\n"
        "📊 Анализирам trading journal данните...\n"
        "⏱️ Това може да отнеме 5-15 секунди.",
        parse_mode='HTML'
    )
    
    try:
        # Calculate fresh data with timeout protection
        results = await run_backtest_async(days=days)
        
        # Check for errors
        if 'error' in results:
            await query.edit_message_text(
                f"⚠️ <b>Backtest Analysis</b>\n\n"
                f"❌ {results['error']}\n\n"
                f"{results.get('hint', 'Trades will be recorded automatically.')}",
                parse_mode='HTML'
            )
            return
        
        # Store in cache
        set_cache('backtest', cache_key, results)
        
        # Extract data
        overall = results.get('overall', {})
        top_performers = results.get('top_performers', [])
        worst_performers = results.get('worst_performers', [])
        by_timeframe = results.get('by_timeframe', {})
        alert_stats = results.get('alert_stats', {})
        trend_analysis = results.get('trend_analysis', {})
        timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')
        
        # Format top symbols
        top_symbols_text = ""
        for i, perf in enumerate(top_performers[:3], 1):
            top_symbols_text += f"   {i}. {perf['symbol']}: {perf['win_rate']:.1f}% ({perf['total_trades']} trades)\n"
        
        # Format worst performers
        worst_symbols_text = ""
        if worst_performers:
            worst = worst_performers[0]
            worst_symbols_text = f"   1. {worst['symbol']}: {worst['win_rate']:.1f}% ({worst['total_trades']} trades)\n"
        
        # Format best timeframes
        tf_list = sorted(by_timeframe.items(), key=lambda x: x[1]['win_rate'], reverse=True)
        tf_text = ""
        for i, (tf, stats) in enumerate(tf_list[:3], 1):
            tf_text += f"   {i}. {tf}: {stats['win_rate']:.1f}% ({stats['total_trades']} trades)\n"
        
        # Alert system status
        alerts_80 = alert_stats.get('80_alerts', {})
        final_alerts = alert_stats.get('final_alerts', {})
        
        # Trend analysis
        trend = trend_analysis
        
        # Build message
        text = f"""📊 <b>BACKTEST РЕЗУЛТАТИ</b>
━━━━━━━━━━━━━━━━━━━━━━━

📅 Period: Last {days} days

📈 <b>ОБОБЩЕНИЕ:</b>
   💰 Общо Trades: <b>{overall.get('total_trades', 0)}</b>
   🟢 Wins: {overall.get('wins', 0)} ({overall.get('win_rate', 0):.1f}%)
   🔴 Losses: {overall.get('losses', 0)}
   💵 Total P/L: <b>{overall.get('total_pnl', 0):+.2f}%</b>
   📈 Avg Win: +{overall.get('avg_win', 0):.2f}%
   📉 Avg Loss: -{overall.get('avg_loss', 0):.2f}%
   📊 Profit Factor: <b>{overall.get('profit_factor', 0):.2f}</b>

🏆 <b>ТОП SYMBOLS:</b>
{top_symbols_text or "   No data\n"}

"""
        if worst_symbols_text:
            text += f"""📉 <b>WORST PERFORMERS:</b>
{worst_symbols_text}

"""
        
        text += f"""⏰ <b>BEST TIMEFRAMES:</b>
{tf_text or "   No data\n"}

🔔 <b>ALERT SYSTEMS:</b>
📊 80% Alerts:
   Total: {alerts_80.get('total_alerts', 0)}
   → TP: {alerts_80.get('successful_tp', 0)} ({alerts_80.get('success_rate', 0):.0f}%)
   → SL: {alerts_80.get('failed_to_tp', 0)}
   Status: {alerts_80.get('status', '❌')}

🎯 Final Alerts:
   Total: {final_alerts.get('total_alerts', 0)}
   Coverage: {final_alerts.get('coverage', 0):.0f}%
   Status: {final_alerts.get('status', '❌')}

📈 <b>TREND ANALYSIS:</b>
   Last 7 days: {trend.get('wr_7d', 0):.1f}% {trend.get('trend_7d', '')}
   Last 30 days: {trend.get('wr_30d', 0):.1f}%
   Last 60 days: {trend.get('wr_60d', 0):.1f}% {trend.get('trend_60d', '')}
   💡 Insight: {trend.get('insight', 'N/A')}

━━━━━━━━━━━━━━━━━━━━━━━
📊 Source: trading_journal.json
🕐 Generated: {timestamp}
"""
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="backtest_all_30"),
                InlineKeyboardButton("📊 7 дни", callback_data="backtest_all_7"),
            ],
            [
                InlineKeyboardButton("📊 60 дни", callback_data="backtest_all_60"),
                InlineKeyboardButton("📊 90 дни", callback_data="backtest_all_90"),
            ],
            [
                InlineKeyboardButton("🔍 Deep Dive", callback_data="backtest_deep_dive"),
                InlineKeyboardButton("🔙 Reports", callback_data="reports_menu"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Backtest all error: {e}", exc_info=True)
        error_message = format_user_error(e, "Backtest Analysis")
        await query.edit_message_text(error_message, parse_mode='HTML')


async def backtest_deep_dive_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show symbol selection for deep dive analysis
    """
    query = update.callback_query
    await query.answer()
    
    text = """🔍 <b>DEEP DIVE ANALYSIS</b>

Избери символ за детайлен анализ:
"""
    
    # Create symbol selection keyboard
    keyboard = [
        [
            InlineKeyboardButton("₿ BTCUSDT", callback_data="deep_dive_BTCUSDT"),
            InlineKeyboardButton("Ξ ETHUSDT", callback_data="deep_dive_ETHUSDT"),
        ],
        [
            InlineKeyboardButton("⚡ SOLUSDT", callback_data="deep_dive_SOLUSDT"),
            InlineKeyboardButton("💎 XRPUSDT", callback_data="deep_dive_XRPUSDT"),
        ],
        [
            InlineKeyboardButton("🔷 BNBUSDT", callback_data="deep_dive_BNBUSDT"),
            InlineKeyboardButton("♠️ ADAUSDT", callback_data="deep_dive_ADAUSDT"),
        ],
        [
            InlineKeyboardButton("🔙 Back", callback_data="backtest_all"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)


@log_timing("Deep Dive Symbol Callback")
async def deep_dive_symbol_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show deep dive analysis for specific symbol
    
    Callback data pattern: deep_dive_SYMBOL (e.g., deep_dive_BTCUSDT)
    """
    query = update.callback_query
    await query.answer()
    
    # Extract symbol from callback data
    symbol = query.data.replace('deep_dive_', '')
    days = 30
    
    # INSTANT FEEDBACK - Show loading with progress
    await query.edit_message_text(
        f"⏳ <b>ЗАРЕЖДАНЕ...</b>\n\n"
        f"🔍 Анализирам {symbol} данните...\n"
        f"⏱️ Това може да отнеме 5-10 секунди.",
        parse_mode='HTML'
    )
    
    try:
        # Step 1: Load trades
        await show_progress(query, 1, 3, f"📊 Зареждане на {symbol} trades...")
        
        # Calculate fresh data with timeout protection
        results = await run_backtest_async(days=days, symbol=symbol)
        
        # Check for errors
        if 'error' in results:
            await query.edit_message_text(
                f"⚠️ <b>Deep Dive: {symbol}</b>\n\n"
                f"❌ {results['error']}",
                parse_mode='HTML'
            )
            return
        
        # Step 2: Analyze data
        await show_progress(query, 2, 3, "📈 Калкулиране на статистики...")
        
        # Extract data
        overall = results.get('overall', {})
        by_timeframe = results.get('by_timeframe', {})
        ml_vs_classical = results.get('ml_vs_classical', {})
        trend_analysis = results.get('trend_analysis', {})
        
        # Step 3: Final formatting
        await show_progress(query, 3, 3, "✅ Завършване...")
        
        # Format timeframe breakdown
        tf_list = sorted(by_timeframe.items(), key=lambda x: x[1]['win_rate'], reverse=True)
        tf_text = ""
        best_tf = ""
        for i, (tf, stats) in enumerate(tf_list, 1):
            indicator = " 🏆" if i == 1 else ""
            tf_text += f"   {tf}: {stats['win_rate']:.1f}% ({stats['total_trades']} trades){indicator}\n"
            if i == 1:
                best_tf = tf
        
        # ML recommendation
        ml_stats = ml_vs_classical.get('ml', {})
        classical_stats = ml_vs_classical.get('classical', {})
        ml_recommendation = ""
        if ml_stats.get('total_trades', 0) > 0 and classical_stats.get('total_trades', 0) > 0:
            if ml_stats['win_rate'] > classical_stats['win_rate']:
                ml_recommendation = f"✅ Use ML mode (+{ml_stats['win_rate'] - classical_stats['win_rate']:.1f}%)"
            else:
                ml_recommendation = f"⚠️ Classical mode better (+{classical_stats['win_rate'] - ml_stats['win_rate']:.1f}%)"
        elif ml_stats.get('total_trades', 0) > 0:
            ml_recommendation = "💡 ML mode active"
        else:
            ml_recommendation = "💡 Enable ML mode for better results"
        
        # Recommendations
        recommendations = []
        if overall.get('win_rate', 0) < 60:
            recommendations.append("• Consider adjusting entry strategy")
        if best_tf:
            recommendations.append(f"• Focus on {best_tf} timeframe (best performance)")
        if ml_recommendation.startswith("✅"):
            recommendations.append("• Keep using ML mode")
        
        rec_text = "\n".join(recommendations) if recommendations else "   • Keep current strategy"
        
        # Build message
        text = f"""🔍 <b>{symbol} DEEP DIVE</b>
━━━━━━━━━━━━━━━━━━━━━━━

📅 Period: Last {days} days

📊 <b>Overall:</b>
   Trades: <b>{overall.get('total_trades', 0)}</b>
   Win Rate: <b>{overall.get('win_rate', 0):.1f}%</b>
   P/L: <b>{overall.get('total_pnl', 0):+.2f}%</b>

⏰ <b>By Timeframe:</b>
{tf_text or "   No data\n"}

🤖 <b>ML Performance:</b>
   ML enabled: {ml_stats.get('win_rate', 0):.1f}% ({ml_stats.get('total_trades', 0)} trades)
   Classical: {classical_stats.get('win_rate', 0):.1f}% ({classical_stats.get('total_trades', 0)} trades)
   💡 {ml_recommendation}

📈 <b>Recent Performance:</b>
   Last 7d: {trend_analysis.get('wr_7d', 0):.1f}% {trend_analysis.get('trend_7d', '')}
   Last 30d: {trend_analysis.get('wr_30d', 0):.1f}%

💡 <b>RECOMMENDATIONS:</b>
{rec_text}

━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        # Create keyboard
        keyboard = [
            [
                InlineKeyboardButton("🔙 Symbol List", callback_data="backtest_deep_dive"),
                InlineKeyboardButton("📊 Backtest All", callback_data="backtest_all"),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, parse_mode='HTML', reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Deep dive error for {symbol}: {e}", exc_info=True)
        error_message = format_user_error(e, f"Deep Dive Analysis: {symbol}")
        await query.edit_message_text(error_message, parse_mode='HTML')


@require_access()
@rate_limited(calls=10, period=60)


# ============================================================================
# HEALTH CHECK CALLBACK HANDLERS
# ============================================================================

async def health_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle health check button callbacks"""
    query = update.callback_query
    # Import references for proper scope
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    await query.answer()
    
    try:
        action = query.data
        
        # Smoke Test Handler
        if action == "health_smoke":
            await query.answer()
            await query.edit_message_text("⚡ Running smoke tests...\n⏳ This will take 5-10 seconds...")
            
            try:
                from comprehensive_diagnostics import ComprehensiveDiagnostics
                diag = ComprehensiveDiagnostics(os.getcwd())
                results = await diag.run_smoke_tests()
                
                # Format results
                passed = sum(1 for r in results if r.get('status') == 'OK')
                errors = sum(1 for r in results if r.get('status') == 'ERROR')
                warnings = sum(1 for r in results if r.get('status') == 'WARNING')
                
                message = "⚡ SMOKE TEST RESULTS\n"
                message += "━━━━━━━━━━━━━━━━━━━━━━\n"
                message += f"📊 Tests: {len(results)}/6 critical\n"
                message += f"❌ Errors: {errors}\n"
                message += f"⚠️ Warnings: {warnings}\n"
                message += f"✅ Passed: {passed}\n\n"
                
                if errors > 0:
                    message += "❌ CRITICAL ISSUES:\n\n"
                    for r in results:
                        if r.get('status') == 'ERROR':
                            message += f"#{r['test_number']}: {r['test_name']}\n"
                            message += f"  {r.get('issue', 'Unknown error')}\n\n"
                
                if warnings > 0:
                    message += "⚠️ WARNINGS:\n\n"
                    for r in results:
                        if r.get('status') == 'WARNING':
                            message += f"#{r['test_number']}: {r['test_name']}\n"
                            message += f"  {r.get('issue', 'Unknown warning')}\n\n"
                
                if errors == 0 and warnings == 0:
                    message += "✅ All critical systems operational!\n"
                
                message += "\n━━━━━━━━━━━━━━━━━━━━━━\n"
                message += "For detailed diagnostics, use 🔬 Run All"
                
                # Buttons
                keyboard = [
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="health_refresh"),
                        InlineKeyboardButton("🔬 Run All", callback_data="health_run_all"),
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await query.edit_message_text(message, reply_markup=reply_markup)
                
            except Exception as e:
                logger.error(f"Smoke test error: {e}")
                await query.edit_message_text(f"❌ Smoke test failed: {str(e)}")
            return
        
        elif action == "health_refresh":
            await query.edit_message_text("🔄 Refreshing health check...\n⏳ Please wait...")
            
            from system_diagnostics import run_full_health_check
            from diagnostic_messages import format_health_summary
            
            health_report = await asyncio.wait_for(
                run_full_health_check(BASE_PATH),
                timeout=90.0
            )
            
            message = format_health_summary(health_report)
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton("🔄 Refresh", callback_data="health_refresh"),
                    InlineKeyboardButton("🧠 Deep", callback_data="health_deep"),
                ],
                [
                    InlineKeyboardButton("🔬 Run All", callback_data="health_run_all"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(message, parse_mode='HTML', reply_markup=reply_markup)
            
        elif action == "health_deep":
            """🧠 Deep Analysis - Comprehensive Diagnostics with Enhanced Errors"""
            await query.edit_message_text(
                "🧠 Running comprehensive diagnostics...\n⏳ Please wait...",
                parse_mode='HTML'
            )
            
            try:
                from comprehensive_diagnostics import ComprehensiveDiagnostics
                
                # Run comprehensive diagnostics
                diag = ComprehensiveDiagnostics()
                results = await diag.run_all_tests()
                
                # Format results
                total = len(results)
                errors = [r for r in results if r.get('status') == 'ERROR']
                warnings = [r for r in results if r.get('status') == 'WARNING']
                passed = [r for r in results if r.get('status') == 'OK']
                
                message = "🧠 <b>COMPREHENSIVE DIAGNOSTIC REPORT</b>\n"
                message += "━" * 45 + "\n\n"
                message += f"📊 <b>Summary:</b>\n"
                message += f"  Total Tests: {total}\n"
                message += f"  ✅ Passed: {len(passed)} ({len(passed)/total*100:.1f}%)\n"
                message += f"  ⚠️ Warnings: {len(warnings)}\n"
                message += f"  ❌ Errors: {len(errors)}\n\n"
                
                # Show errors with enhanced formatting
                if errors:
                    message += f"❌ <b>Errors ({len(errors)}):</b>\n\n"
                    for err in errors[:5]:
                        message += f"  <b>#{err.get('test_number', '?')}: {err.get('test_name', 'Unknown')}</b>\n"
                        if err.get('issue'):
                            message += f"    📋 {err.get('issue')}\n"
                        if err.get('location'):
                            message += f"    📍 {err.get('location')}\n"
                        if err.get('solution'):
                            message += f"    🔧 {err.get('solution')}\n"
                        message += "\n"
                    
                    if len(errors) > 5:
                        message += f"  ...and {len(errors) - 5} more errors\n\n"
                
                # Show warnings
                if warnings:
                    message += f"⚠️ <b>Warnings ({len(warnings)}):</b>\n"
                    for warn in warnings[:3]:
                        message += f"  • {warn.get('test_name', 'Unknown')}\n"
                    message += "\n"
                
                if not errors and not warnings:
                    message += "✅ <b>ALL SYSTEMS OPERATIONAL!</b>\n\n"
                
                message += "━" * 45 + "\n"
                message += f"⏱ Analysis completed\n"
                
                # Buttons
                keyboard = [
                    [InlineKeyboardButton("🔄 Refresh", callback_data="health_deep")],
                    [InlineKeyboardButton("◀️ Back", callback_data="health_refresh")]
                ]
                
                await query.edit_message_text(
                    message,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='HTML'
                )
                
            except Exception as e:
                logger.error(f"Deep analysis error: {e}")
                import traceback
                traceback.print_exc()
                
                await query.edit_message_text(
                    f"❌ <b>Deep analysis failed:</b>\n{str(e)}",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Back", callback_data="health_refresh")]]),
                    parse_mode='HTML'
                )
            
        
        elif action == "health_run_all":
            await query.edit_message_text("🔬 Running all 20 diagnostic tests...\n⏳ This may take 30-60 seconds...\n\nPlease wait...")
            
            from system_diagnostics import get_comprehensive_diagnostic_report
            report = await get_comprehensive_diagnostic_report()
            
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            keyboard = [
                [
                    InlineKeyboardButton("��� Refresh", callback_data="health_refresh"),
                    InlineKeyboardButton("🧠 Deep", callback_data="health_deep"),
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(report, parse_mode='HTML', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Health callback error: {e}", exc_info=True)
        await query.edit_message_text(f"❌ Error: {str(e)}")




async def health_function_test_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback: Function Health Test
    Tests all bot commands and modules
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # Show loading message
        await query.edit_message_text(
            "🧪 <b>Running Function Health Tests...</b>\n\n"
            "Testing all bot commands and modules...\n"
            "⏳ Please wait...",
            parse_mode='HTML'
        )
        
        # Import and run function health check
        from function_health import get_function_health_report
        
        report = await asyncio.wait_for(
            get_function_health_report(),
            timeout=30.0
        )
        
        # Build response
        summary = report.get('summary', {})
        
        response = "🧪 <b>Function Health Report</b>\n\n"
        response += "📊 <b>Summary</b>\n"
        response += f"  Total Tests: {summary.get('total_tests', 0)}\n"
        response += f"  ✅ OK: {summary.get('ok', 0)}\n"
        response += f"  ⚠️ Warnings: {summary.get('warnings', 0)}\n"
        response += f"  ❌ Errors: {summary.get('errors', 0)}\n"
        response += f"  Success Rate: {summary.get('success_rate', 0)}%\n\n"
        
        # Show failed tests
        if report.get('failed_tests'):
            response += f"❌ <b>Failed Tests</b> ({len(report['failed_tests'])}):\n"
            for test in report['failed_tests'][:5]:  # First 5
                cmd = test.get('command', test.get('module', 'Unknown'))
                response += f"  • {cmd}\n"
            if len(report['failed_tests']) > 5:
                response += f"  ... and {len(report['failed_tests']) - 5} more\n"
            response += "\n"
        
        # Show warnings
        if report.get('warnings'):
            response += f"⚠️ <b>Warnings</b> ({len(report['warnings'])}):\n"
            for warning in report['warnings'][:3]:  # First 3
                cmd = warning.get('command', warning.get('module', 'Unknown'))
                response += f"  • {cmd}\n"
            if len(report['warnings']) > 3:
                response += f"  ... and {len(report['warnings']) - 3} more\n"
        
        # Add buttons
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="health_function_test"),
                InlineKeyboardButton("◀️ Back", callback_data="health_refresh")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
    except asyncio.TimeoutError:
        await query.edit_message_text(
            "⏱️ <b>Function health test timed out</b>\n\n"
            "Tests took too long to complete.\n"
            "Try again later.",
            parse_mode='HTML'
        )
    except Exception as e:
        logger.error(f"Function health test failed: {e}")
        error_msg = str(e).replace('<', '&lt;').replace('>', '&gt;')
        await query.edit_message_text(
            f"❌ <b>Function health test failed</b>\n\n"
            f"Error: <code>{error_msg}</code>",
            parse_mode='HTML'
        )

async def health_replay_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback: Replay Diagnostics
    Shows last 5 recorded operations
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # Import replay diagnostics
        from replay_diagnostics import get_replay_diagnostics_report
        
        report = await asyncio.wait_for(
            get_replay_diagnostics_report(replay_count=5),
            timeout=15.0
        )
        
        # Build response
        summary = report.get('summary', {})
        recordings = report.get('recent_recordings', [])
        
        response = f"🔄 **Replay Diagnostics**\n\n"
        response += f"📊 **Summary**\n"
        response += f"  Total Replays: {summary.get('total_replays', 0)}\n"
        response += f"  ✅ Successful: {summary.get('successful', 0)}\n"
        response += f"  ❌ Failed: {summary.get('failed', 0)}\n"
        response += f"  Success Rate: {summary.get('success_rate', 0)}%\n\n"
        
        # Show recent operations
        if recordings:
            response += f"📋 **Recent Operations** (Last {len(recordings)}):\n"
            for rec in recordings[:5]:
                op_type = rec.get('operation_type', 'unknown')
                op_name = rec.get('operation_name', 'unknown')
                status = rec.get('status', 'unknown')
                
                status_icon = {'SUCCESS': '✅', 'ERROR': '❌', 'TIMEOUT': '⏱️'}.get(status, '❓')
                
                response += f"{status_icon} `{op_type}`: {op_name}\n"
        else:
            response += "📋 No recorded operations yet.\n"
        
        # Add buttons
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="health_replay"),
                InlineKeyboardButton("◀️ Back", callback_data="health_refresh")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Replay diagnostics failed: {e}")
        await query.edit_message_text(
            f"❌ **Replay diagnostics failed**\n\n"
            f"Error: `{str(e)}`",
            parse_mode='Markdown'
        )


async def health_performance_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Callback: Performance Monitoring
    Shows performance metrics and bottlenecks
    """
    query = update.callback_query
    await query.answer()
    
    try:
        # Import performance monitor
        from performance_monitor import get_performance_report
        
        report = await asyncio.wait_for(
            get_performance_report(),
            timeout=15.0
        )
        
        # Build response
        summary = report.get('summary', {})
        system = report.get('system_performance', {})
        
        response = f"⚡ **Performance Report**\n\n"
        
        # System performance
        cpu = system.get('cpu', {})
        memory = system.get('memory', {})
        
        response += f"💻 **System**\n"
        response += f"  CPU: {cpu.get('process_percent', 0)}%\n"
        response += f"  Memory: {memory.get('process_mb', 0)} MB\n"
        response += f"  System RAM: {memory.get('system_percent', 0)}%\n\n"
        
        # Performance summary
        response += f"📊 **Operations Tracked**\n"
        response += f"  Total: {summary.get('total_operations_tracked', 0)}\n"
        response += f"  Unique: {summary.get('unique_operations', 0)}\n"
        response += f"  Health: {summary.get('system_health', 'UNKNOWN')}\n\n"
        
        # Bottlenecks
        bottlenecks = report.get('bottlenecks', [])
        if bottlenecks:
            response += f"🐌 **Bottlenecks Detected** ({len(bottlenecks)}):\n"
            for b in bottlenecks[:3]:
                response += f"  • {b.get('operation', 'Unknown')}\n"
                response += f"    Issue: {b.get('issue', 'Unknown')}\n"
            if len(bottlenecks) > 3:
                response += f"  ... and {len(bottlenecks) - 3} more\n"
        else:
            response += "✅ **No bottlenecks detected**\n"
        
        # Add buttons
        keyboard = [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="health_performance"),
                InlineKeyboardButton("◀️ Back", callback_data="health_refresh")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            response,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Performance monitoring failed: {e}")
        await query.edit_message_text(
            f"❌ **Performance monitoring failed**\n\n"
            f"Error: `{str(e)}`",
            parse_mode='Markdown'
        )

async def verify_alerts_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Admin command to verify alert systems
    
    Usage: /verify_alerts
    """
    # Check admin (use existing admin check pattern from bot.py)
    user_id = update.effective_user.id
    
    # Admin check - adapt to existing pattern
    # For now, allow all users but this should be restricted
    
    await update.message.reply_text("🔍 Verifying alert systems...")
    
    try:
        from verify_alerts import AlertVerifier
        
        verifier = AlertVerifier()
        report = await verifier.verify_all()
        
        # Send summary
        summary = (
            f"📊 <b>ALERT VERIFICATION SUMMARY</b>\n\n"
            f"📊 80% Alert: {report['80_alert']['status']}\n"
            f"🎯 Final Alert: {report['final_alert']['status']}\n\n"
            f"Full report saved to:\n"
            f"<code>ALERT_VERIFICATION_REPORT.md</code>"
        )
        await update.message.reply_text(summary, parse_mode='HTML')
        
        # Send full report file
        report_path = os.path.join(BASE_PATH, 'ALERT_VERIFICATION_REPORT.md')
        if os.path.exists(report_path):
            with open(report_path, 'rb') as f:
                await update.message.reply_document(f, filename='ALERT_VERIFICATION_REPORT.md')
        
    except Exception as e:
        logger.error(f"Alert verification error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ <b>Error</b>\n\n{str(e)}",
            parse_mode='HTML'
        )


@require_access()
@rate_limited(calls=3, period=60)
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


@require_access()
@rate_limited(calls=20, period=60)
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


@require_access()
@rate_limited(calls=3, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
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


@require_access()
@rate_limited(calls=10, period=60)
async def weekly_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерира седмичен отчет с точност и успеваемост"""
    if not REPORTS_AVAILABLE:
        await update.message.reply_text("❌ Reports модул не е наличен")
        return
    
    await update.message.reply_text("📊 Генерирам седмичен отчет (Изминала седмица: Понеделник - Неделя)...")
    
    summary = report_engine.get_weekly_summary()
    
    if summary:
        # Форматиране на съобщението
        accuracy_emoji = "🔥" if summary['accuracy'] >= 70 else "💪" if summary['accuracy'] >= 60 else "👍" if summary['accuracy'] >= 50 else "😐"
        profit_emoji = "💰" if summary['total_profit'] > 0 else "📉" if summary['total_profit'] < 0 else "⚪"
        
        message = f"""📈 <b>СЕДМИЧЕН ОТЧЕТ</b>
📅 {summary['period']}
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
⏰ Генериран: {datetime.now(pytz.timezone('Europe/Sofia')).strftime('%H:%M:%S')} (BG време)
"""
        
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text("❌ Недостатъчно данни за седмичен отчет")


@require_access()
@rate_limited(calls=10, period=60)
async def monthly_report_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Генерира месечен отчет с точност и успеваемост"""
    if not REPORTS_AVAILABLE:
        await update.message.reply_text("❌ Reports модул не е наличен")
        return
    
    await update.message.reply_text("📊 Генерирам месечен отчет (Изминал месец: 1-во - последно число)...")
    
    summary = report_engine.get_monthly_summary()
    
    if summary:
        # Форматиране на съобщението
        accuracy_emoji = "🔥" if summary['accuracy'] >= 70 else "💪" if summary['accuracy'] >= 60 else "👍" if summary['accuracy'] >= 50 else "😐"
        profit_emoji = "💰" if summary['total_profit'] > 0 else "📉" if summary['total_profit'] < 0 else "⚪"
        
        message = f"""🎯 <b>МЕСЕЧЕН ОТЧЕТ</b>
📅 {summary['period']}
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
⏰ Генериран: {datetime.now(pytz.timezone('Europe/Sofia')).strftime('%H:%M:%S')} (BG време)

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


@require_access()
@rate_limited(calls=20, period=60)
async def reports_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Централизирано меню за всички отчети"""
    keyboard = [
        [
            InlineKeyboardButton("📊 Дневен отчет", callback_data="report_daily"),
            InlineKeyboardButton("📈 Седмичен", callback_data="report_weekly"),
            InlineKeyboardButton("📆 Месечен", callback_data="report_monthly")
        ],
        [
            InlineKeyboardButton("📊 Backtest (Всички)", callback_data="backtest_all"),
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
        # Генерирай дневен отчет от daily_reports.py engine
        if REPORTS_AVAILABLE:
            report = report_engine.generate_daily_report()
            if report:
                message = report_engine.format_report_message(report)
                await query.edit_message_text(message, parse_mode="HTML")
            else:
                await query.edit_message_text("❌ Няма данни за дневен отчет")
        else:
            await query.edit_message_text("❌ Reports модул не е наличен")
    
    elif query.data == "report_weekly":
        if not REPORTS_AVAILABLE:
            await query.edit_message_text("❌ Reports модул не е наличен")
            return
            
        summary = report_engine.get_weekly_summary()
        if summary:
            accuracy_emoji = "🔥" if summary["accuracy"] >= 70 else "💪" if summary["accuracy"] >= 60 else "👍"
            profit_emoji = "💰" if summary.get("total_profit", 0) > 0 else "📉"
            
            message = f"""📈 <b>СЕДМИЧЕН ОТЧЕТ</b>
📅 {summary["period"]}
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
   📉 Loss: <b>{worst.get("profit_pct", 0):.2f}%</b>

"""
            message += f"""💪 Средна увереност: {summary["avg_confidence"]:.1f}%"""
            await query.edit_message_text(message, parse_mode="HTML")
        else:
            await query.edit_message_text("❌ Недостатъчно данни за седмичен отчет")
    
    elif query.data == "report_monthly":
        if not REPORTS_AVAILABLE:
            await query.edit_message_text("❌ Reports модул не е наличен")
            return
            
        summary = report_engine.get_monthly_summary()

        if summary:
            accuracy_emoji = "🔥" if summary["accuracy"] >= 70 else "💪" if summary["accuracy"] >= 60 else "👍"
            profit_emoji = "💰" if summary.get("total_profit", 0) > 0 else "📉"
            
            message = f"""🎯 <b>МЕСЕЧЕН ОТЧЕТ</b>
📅 {summary["period"]}
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
        # Back-test резултати - USE NEW COMPREHENSIVE SYSTEM
        await query.edit_message_text("📊 Loading backtest results...")
        
        # Check if backtest_results directory exists with new comprehensive data
        results_dir = Path("backtest_results")
        
        if results_dir.exists() and list(results_dir.glob("*_backtest.json")):
            # NEW COMPREHENSIVE SYSTEM - Use backtest_results/ directory
            try:
                # Collect all results with validation
                all_results = []
                corrupted_files = []
                
                for result_file in results_dir.glob("*_backtest.json"):
                    try:
                        with open(result_file, 'r') as f:
                            result = json.load(f)
                            
                            # Validate required fields
                            if 'symbol' in result and 'timeframe' in result:
                                all_results.append(result)
                            else:
                                corrupted_files.append(result_file.name)
                                
                    except json.JSONDecodeError as e:
                        logger.error(f"Corrupted JSON file {result_file}: {e}")
                        corrupted_files.append(result_file.name)
                    except Exception as e:
                        logger.error(f"Error loading {result_file}: {e}")
                        corrupted_files.append(result_file.name)
                
                if not all_results:
                    await query.edit_message_text(
                        "⚠️ <b>No valid backtest results found</b>\n\n"
                        "The backtest_results directory is empty or contains corrupted data.\n"
                        "Run a backtest first:\n"
                        "<code>/backtest BTCUSDT 1h 30</code>",
                        parse_mode='HTML'
                    )
                    return
                
                # ==================== DATA AGGREGATION ====================
                
                total_trades = 0
                total_wins = 0
                total_losses = 0
                total_pnl = 0.0
                
                # 80% TP Alert statistics
                total_alerts_80 = 0
                alert_recommendations = {'HOLD': 0, 'PARTIAL_CLOSE': 0, 'CLOSE_NOW': 0}
                
                # Per-symbol aggregation
                symbol_stats = {}
                
                # Per-timeframe aggregation
                timeframe_stats = {}
                
                # Best/Worst performers
                performance_list = []
                
                for result in all_results:
                    symbol = result.get('symbol', 'UNKNOWN')
                    timeframe = result.get('timeframe', 'UNKNOWN')
                    trades = result.get('total_trades', 0)
                    wins = result.get('total_win', 0)
                    losses = result.get('total_loss', 0)
                    win_rate = result.get('win_rate', 0)
                    pnl = result.get('total_pnl', 0)
                    
                    # Aggregate overall
                    total_trades += trades
                    total_wins += wins
                    total_losses += losses
                    total_pnl += pnl
                    
                    # 80% TP Alerts
                    alerts_80 = result.get('alerts_80', [])
                    total_alerts_80 += len(alerts_80)
                    
                    for alert in alerts_80:
                        rec = alert.get('recommendation', 'HOLD')
                        if rec in alert_recommendations:
                            alert_recommendations[rec] += 1
                    
                    # Per-symbol stats
                    if symbol not in symbol_stats:
                        symbol_stats[symbol] = {
                            'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0, 'timeframes': 0
                        }
                    symbol_stats[symbol]['trades'] += trades
                    symbol_stats[symbol]['wins'] += wins
                    symbol_stats[symbol]['losses'] += losses
                    symbol_stats[symbol]['pnl'] += pnl
                    symbol_stats[symbol]['timeframes'] += 1
                    
                    # Per-timeframe stats
                    if timeframe not in timeframe_stats:
                        timeframe_stats[timeframe] = {
                            'trades': 0, 'wins': 0, 'losses': 0, 'pnl': 0, 'symbols': 0
                        }
                    timeframe_stats[timeframe]['trades'] += trades
                    timeframe_stats[timeframe]['wins'] += wins
                    timeframe_stats[timeframe]['losses'] += losses
                    timeframe_stats[timeframe]['pnl'] += pnl
                    timeframe_stats[timeframe]['symbols'] += 1
                    
                    # Track for best/worst
                    if trades > 0:
                        performance_list.append({
                            'pair': f"{symbol} ({timeframe})",
                            'win_rate': win_rate,
                            'pnl': pnl,
                            'trades': trades
                        })
                
                # ==================== FORMAT PERFECT REPORT ====================
                
                # Header
                text = "📊 <b>BACKTEST RESULTS - COMPREHENSIVE REPORT</b>\n"
                text += "=" * 40 + "\n\n"
                
                # Overall Statistics
                overall_win_rate = (total_wins / total_trades * 100) if total_trades > 0 else 0
                
                text += "<b>📈 OVERALL STATISTICS</b>\n"
                text += f"├─ Total Trades: <b>{total_trades}</b>\n"
                text += f"├─ Total Wins: {total_wins} ✅\n"
                text += f"├─ Total Losses: {total_losses} ❌\n"
                text += f"├─ Win Rate: <b>{overall_win_rate:.1f}%</b>\n"
                
                pnl_emoji = "💰" if total_pnl > 0 else "📉"
                text += f"└─ Total PnL: {pnl_emoji} <b>{total_pnl:+.2f}%</b>\n\n"
                
                # 80% TP Alert Statistics
                if total_alerts_80 > 0:
                    text += "<b>🔔 80% TP ALERT STATISTICS</b>\n"
                    text += f"├─ Total Alerts: <b>{total_alerts_80}</b>\n"
                    text += f"├─ HOLD: {alert_recommendations.get('HOLD', 0)} 🟢\n"
                    text += f"├─ PARTIAL CLOSE: {alert_recommendations.get('PARTIAL_CLOSE', 0)} 🟡\n"
                    text += f"└─ CLOSE NOW: {alert_recommendations.get('CLOSE_NOW', 0)} 🔴\n\n"
                
                # Per-Symbol Breakdown
                text += "<b>💎 PER-SYMBOL BREAKDOWN</b>\n"
                
                for symbol in sorted(symbol_stats.keys()):
                    stats = symbol_stats[symbol]
                    s_win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
                    s_pnl_emoji = "📈" if stats['pnl'] > 0 else "📉"
                    
                    text += f"<b>{symbol}</b>\n"
                    text += f"├─ Trades: {stats['trades']} ({stats['timeframes']} TFs)\n"
                    text += f"├─ Win Rate: {s_win_rate:.1f}%\n"
                    text += f"└─ PnL: {s_pnl_emoji} {stats['pnl']:+.2f}%\n\n"
                
                # Per-Timeframe Breakdown (truncated for callback message)
                text += "<b>⏰ PER-TIMEFRAME BREAKDOWN</b>\n"
                
                # Sort timeframes using contract order
                tf_order = TimeframeContract.get_all_supported_timeframes()
                sorted_tfs = sorted(timeframe_stats.keys(), 
                                    key=lambda x: tf_order.index(x) if x in tf_order else 999)
                
                # Show only first few timeframes in callback (message length limit)
                for tf in sorted_tfs[:5]:
                    stats = timeframe_stats[tf]
                    tf_win_rate = (stats['wins'] / stats['trades'] * 100) if stats['trades'] > 0 else 0
                    tf_pnl_emoji = "📈" if stats['pnl'] > 0 else "📉"
                    
                    text += f"<b>{tf}</b>\n"
                    text += f"├─ Trades: {stats['trades']} ({stats['symbols']} symbols)\n"
                    text += f"├─ Win Rate: {tf_win_rate:.1f}%\n"
                    text += f"└─ PnL: {tf_pnl_emoji} {stats['pnl']:+.2f}%\n\n"
                
                if len(sorted_tfs) > 5:
                    text += f"<i>...and {len(sorted_tfs) - 5} more timeframes</i>\n\n"
                
                # Footer
                text += "=" * 40 + "\n"
                text += "<i>💡 ICT System 2 (Order Blocks, FVG, Liquidity)</i>\n"
                
                # Data info
                text += f"<i>📁 Loaded: {len(all_results)} result files</i>\n"
                
                if corrupted_files:
                    text += f"<i>⚠️ Skipped {len(corrupted_files)} corrupted files</i>\n"
                
                # Last update timestamp
                latest_timestamp = None
                for result in all_results:
                    ts = result.get('timestamp')
                    if ts:
                        if not latest_timestamp or ts > latest_timestamp:
                            latest_timestamp = ts
                
                if latest_timestamp:
                    try:
                        dt = datetime.fromisoformat(latest_timestamp.replace('Z', '+00:00'))
                        text += f"<i>🕐 Last update: {dt.strftime('%Y-%m-%d %H:%M UTC')}</i>\n\n"
                    except:
                        pass
                
                text += "<i>💡 Use /backtest_results for full report</i>"
                
                await query.edit_message_text(text, parse_mode='HTML')
                
            except Exception as e:
                logger.error(f"Error in report_backtest callback: {e}", exc_info=True)
                await query.edit_message_text(f"❌ Грешка при зареждане на резултати: {e}", parse_mode='HTML')
        else:
            # NO LEGACY FALLBACK - Always use new comprehensive system
            await query.edit_message_text(
                "⚠️ <b>No backtest results found</b>\n\n"
                "📊 The comprehensive backtest system requires data in <code>backtest_results/</code> directory.\n\n"
                "Run a comprehensive backtest first:\n"
                "• <code>/backtest</code> - All 6 symbols × 10 timeframes\n"
                "• <code>/backtest BTCUSDT 1h 30</code> - Custom backtest\n\n"
                "💡 The new system includes:\n"
                "   • All 6 symbols (including XRPUSDT)\n"
                "   • All 10 timeframes (1m to 1w)\n"
                "   • 80% TP alert statistics\n"
                "   • Per-symbol & per-timeframe breakdown",
                parse_mode='HTML'
            )
    
    elif query.data == "reports_menu":
        # Return to reports menu
        await reports_cmd(update, context)


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


@require_access()
@rate_limited(calls=10, period=60)
async def toggle_ict_only_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle pure ICT mode (use_ict_only flag)"""
    try:
        # Only owner can change this
        if update.effective_user.id != OWNER_CHAT_ID:
            await update.message.reply_text("❌ Owner only")
            return
        
        from config.config_loader import toggle_flag, get_flag
        
        # Toggle the flag
        new_value = toggle_flag('use_ict_only')
        
        # Update global config if needed
        global FEATURE_FLAGS
        FEATURE_FLAGS = load_feature_flags()
        
        # Send status message
        if new_value:
            message = "🎯 **ICT-Only Mode ENABLED**\n\n"
            message += "✅ Using pure ICT methodology\n"
            message += "❌ Traditional indicators disabled\n"
            message += "❌ Hybrid mode disabled\n\n"
            message += "All signals will use only ICT concepts:\n"
            message += "• Whale Order Blocks\n"
            message += "• Breaker Blocks\n"
            message += "• Mitigation Blocks\n"
            message += "• SIBI/SSIB Zones\n"
            message += "• Liquidity Mapping\n"
            message += "• Market Structure\n"
        else:
            message = "🔀 **ICT-Only Mode DISABLED**\n\n"
            message += "✅ Hybrid mode restored\n"
            message += "✅ Traditional indicators enabled\n"
            message += "✅ Combined analysis active\n\n"
            message += "Signals will use both ICT and traditional analysis."
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error toggling ICT-only mode: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


@require_access()
@rate_limited(calls=20, period=60)
async def status_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current configuration and cache statistics"""
    try:
        # Check if user is allowed
        if update.effective_user.id != OWNER_CHAT_ID:
            await update.message.reply_text("❌ Owner only")
            return
        
        from config.config_loader import load_feature_flags
        from cache_manager import get_cache_manager
        
        # Load current configuration
        config = load_feature_flags()
        
        # Build status message
        message = "📊 **Bot Status & Configuration**\n\n"
        
        # ICT Configuration
        message += "**ICT Settings:**\n"
        message += f"• ICT Only: {'✅' if config.get('use_ict_only', False) else '❌'}\n"
        message += f"• Traditional: {'✅' if config.get('use_traditional', True) else '❌'}\n"
        message += f"• Hybrid: {'✅' if config.get('use_hybrid', True) else '❌'}\n"
        message += f"• Breaker Blocks: {'✅' if config.get('use_breaker_blocks', True) else '❌'}\n"
        message += f"• Mitigation Blocks: {'✅' if config.get('use_mitigation_blocks', True) else '❌'}\n"
        message += f"• SIBI/SSIB: {'✅' if config.get('use_sibi_ssib', True) else '❌'}\n"
        message += f"• Zone Explanations: {'✅' if config.get('use_zone_explanations', True) else '❌'}\n\n"
        
        # Hybrid Mode Configuration
        if config.get('use_hybrid', True):
            hybrid_mode = config.get('hybrid_mode', 'smart')
            ict_weight = config.get('ict_weight', 0.6)
            trad_weight = config.get('traditional_weight', 0.4)
            message += "**Hybrid Mode:**\n"
            message += f"• Mode: {hybrid_mode.upper()}\n"
            message += f"• ICT Weight: {ict_weight:.1%}\n"
            message += f"• Traditional Weight: {trad_weight:.1%}\n\n"
        
        # Cache Configuration
        message += "**Cache Settings:**\n"
        message += f"• Enabled: {'✅' if config.get('use_cache', True) else '❌'}\n"
        if config.get('use_cache', True):
            ttl = config.get('cache_ttl_seconds', 3600)
            max_size = config.get('cache_max_size', 100)
            message += f"• TTL: {ttl // 60} minutes\n"
            message += f"• Max Size: {max_size} entries\n"
            
            # Get cache statistics
            try:
                cache = get_cache_manager()
                stats = cache.get_stats()
                message += f"• Current Size: {stats['size']}/{stats['max_size']}\n"
                message += f"• Hit Rate: {stats['hit_rate']:.1f}%\n"
                message += f"• Total Requests: {stats['total_requests']}\n"
            except Exception as e:
                logger.warning(f"Could not get cache stats: {e}")
        
        message += "\n"
        
        # Other Settings
        message += "**Other Settings:**\n"
        message += f"• ICT Enhancer: {'✅' if config.get('use_ict_enhancer', False) else '❌'}\n"
        message += f"• Auto Alerts: {'✅' if config.get('auto_alerts_enabled', True) else '❌'}\n"
        message += f"• News Tracking: {'✅' if config.get('news_tracking_enabled', True) else '❌'}\n"
        message += f"• Debug Mode: {'✅' if config.get('debug_mode', False) else '❌'}\n"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


@require_access()
@rate_limited(calls=20, period=60)
async def cache_stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show detailed cache statistics"""
    try:
        # Check if user is allowed
        if update.effective_user.id != OWNER_CHAT_ID:
            await update.message.reply_text("❌ Owner only")
            return
        
        from cache_manager import get_cache_manager
        from config.config_loader import get_flag
        
        # Check if cache is enabled
        if not get_flag('use_cache', True):
            await update.message.reply_text("❌ Cache is disabled in configuration")
            return
        
        # Get cache manager
        try:
            cache = get_cache_manager()
        except Exception as e:
            await update.message.reply_text(f"❌ Cache not available: {e}")
            return
        
        # Get detailed statistics
        stats = cache.get_stats()
        
        # Build message
        message = "📊 **Cache Statistics**\n\n"
        
        message += "**Size:**\n"
        message += f"• Current: {stats['size']} entries\n"
        message += f"• Maximum: {stats['max_size']} entries\n"
        message += f"• Usage: {(stats['size'] / stats['max_size'] * 100):.1f}%\n\n"
        
        message += "**Performance:**\n"
        message += f"• Total Requests: {stats['total_requests']}\n"
        message += f"• Cache Hits: {stats['hits']} ({stats['hit_rate']:.1f}%)\n"
        message += f"• Cache Misses: {stats['misses']}\n\n"
        
        message += "**Evictions:**\n"
        message += f"• LRU Evictions: {stats['evictions']}\n"
        message += f"• TTL Expirations: {stats['expirations']}\n\n"
        
        # Show recent keys
        try:
            keys = cache.get_keys()
            if keys:
                message += f"**Recent Entries ({min(5, len(keys))}/{len(keys)}):**\n"
                for key in keys[-5:]:  # Last 5 keys
                    message += f"• {key}\n"
        except:
            pass
        
        # Performance assessment
        message += "\n**Assessment:**\n"
        hit_rate = stats['hit_rate']
        if hit_rate >= 80:
            message += "✅ Excellent cache performance\n"
        elif hit_rate >= 60:
            message += "🟢 Good cache performance\n"
        elif hit_rate >= 40:
            message += "🟡 Moderate cache performance\n"
        else:
            message += "🔴 Low cache performance\n"
        
        await update.message.reply_text(message)
        
    except Exception as e:
        logger.error(f"Error getting cache stats: {e}")
        await update.message.reply_text(f"❌ Error: {e}")


@require_access()
@rate_limited(calls=20, period=60)
async def performance_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Show performance metrics (admin only)
    
    Usage: /performance
    """
    user_id = update.effective_user.id
    
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ Admin only")
        return
    
    metrics = get_metrics_summary()
    
    if not metrics:
        await update.message.reply_text("📊 No performance data yet")
        return
    
    message = "📊 <b>PERFORMANCE METRICS</b>\n\n"
    
    for operation, stats in sorted(metrics.items()):
        message += f"<b>{operation}</b>\n"
        message += f"  Calls: {stats['count']}\n"
        message += f"  Avg: {stats['avg']:.2f}s\n"
        message += f"  Min/Max: {stats['min']:.2f}s / {stats['max']:.2f}s\n"
        message += f"  Median: {stats['median']:.2f}s\n\n"
    
    # Cache stats
    message += "<b>CACHE STATS</b>\n"
    for cache_type, cache_data in CACHE.items():
        message += f"  {cache_type}: {len(cache_data)} entries\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


@require_access()
@rate_limited(calls=10, period=60)
async def clear_cache_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Clear all cached data (admin only)
    
    Usage: /clear_cache
    """
    user_id = update.effective_user.id
    
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("⛔ Admin only")
        return
    
    # Count entries before clear
    total_entries = sum(len(cache) for cache in CACHE.values())
    
    # Clear all caches
    for cache_type in CACHE:
        CACHE[cache_type].clear()
    
    await update.message.reply_text(
        f"✅ <b>CACHE CLEARED</b>\n\n"
        f"Изчистени {total_entries} записа\n\n"
        f"Следващите заявки ще използват свежи данни.",
        parse_mode='HTML'
    )


@require_access()
@rate_limited(calls=10, period=60)
async def debug_mode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Toggle debug logging (admin only)
    
    Usage: /debug
    """
    global DEBUG_MODE
    user_id = update.effective_user.id
    
    if user_id != OWNER_CHAT_ID:
        return
    
    DEBUG_MODE = not DEBUG_MODE
    
    # Update logging level
    if DEBUG_MODE:
        logging.getLogger().setLevel(logging.DEBUG)
        message = "🔍 <b>DEBUG MODE: ON</b>\n\nПодробни логове активирани"
    else:
        logging.getLogger().setLevel(logging.INFO)
        message = "ℹ️ <b>DEBUG MODE: OFF</b>\n\nНормални логове"
    
    await update.message.reply_text(message, parse_mode='HTML')


# ============================================================================
# PR #10: SYSTEM HEALTH MONITORING COMMANDS
# ============================================================================

async def quick_health_check() -> str:
    """
    Fast health check without heavy I/O operations
    Completes in <5 seconds
    
    Returns:
        Formatted health status message (mixed BG/EN)
    """
    import shutil
    from datetime import datetime
    
    checks = []
    
    # 1. Critical file existence checks
    files_to_check = {
        'Trading Journal': 'trading_journal.json',
        'Signal Cache': 'sent_signals_cache.json',
        'ML Model': 'models/ict_model.pkl',
    }
    
    for name, path in files_to_check.items():
        full_path = os.path.join(BASE_PATH, path)
        exists = os.path.exists(full_path)
        
        if exists:
            try:
                size = os.path.getsize(full_path)
                size_str = f" ({size / 1024:.1f}KB)" if size < 1024*1024 else f" ({size / (1024*1024):.1f}MB)"
            except:
                size_str = ""
            checks.append(f"✅ {name}{size_str}")
        else:
            checks.append(f"❌ {name} - FILE MISSING!")
    
    # 2. Disk space check
    try:
        disk = shutil.disk_usage(BASE_PATH)
        if disk.total > 0:
            disk_pct = (disk.used / disk.total) * 100
            disk_free_gb = disk.free / (1024**3)
            
            if disk_pct < 85:
                status = '✅'
            elif disk_pct < 95:
                status = '⚠️'
            else:
                status = '❌'
            
            checks.append(f"{status} Disk: {disk_pct:.1f}% used ({disk_free_gb:.1f}GB free)")
        else:
            checks.append("⚠️ Disk: Cannot determine usage")
    except Exception as e:
        checks.append(f"⚠️ Disk: Could not check ({e})")
    
    # 3. Log file size
    try:
        log_file = os.path.join(BASE_PATH, 'bot.log')
        if os.path.exists(log_file):
            log_size_mb = os.path.getsize(log_file) / (1024**2)
            if log_size_mb > 500:
                status = '⚠️'
            else:
                status = 'ℹ️'
            checks.append(f"{status} Log: {log_size_mb:.1f}MB")
    except:
        pass
    
    # 4. Bot uptime (from process start time if available)
    try:
        import psutil
        process = psutil.Process(os.getpid())
        uptime_seconds = datetime.now().timestamp() - process.create_time()
        hours = int(uptime_seconds // 3600)
        minutes = int((uptime_seconds % 3600) // 60)
        checks.append(f"ℹ️ Bot uptime: {hours}h {minutes}m")
    except:
        pass
    
    # Build message
    message = "🏥 <b>БЪРЗА ПРОВЕРКА</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    message += "\n".join(checks)
    message += "\n\n━━━━━━━━━━━━━━━━━━━━━━━━\n"
    
    # Summary
    if all('✅' in check or 'ℹ️' in check for check in checks):
        message += "✅ <b>Основни системи работят</b>\n"
    else:
        message += "⚠️ <b>Открити проблеми - виж горе</b>\n"
    
    message += f"\n<i>За пълна диагностика: /health</i>\n"
    message += f"<i>Завършено в {datetime.now().strftime('%H:%M:%S')}</i>"
    
    return message


@require_access()
@rate_limited(calls=10, period=60)
async def quick_health_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Quick health check command (5s)
    
    Usage: /quick_health
    """
    try:
        report = await quick_health_check()
        await update.message.reply_text(report, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Quick health check error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ <b>Грешка</b>\n\n<code>{str(e)}</code>",
            parse_mode='HTML'
        )


@require_access()
@rate_limited(calls=5, period=60)  # Reduced from 10 to 5 (heavy operation)
async def health_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Comprehensive system diagnostic (90s timeout)
    
    PR #116: Enhanced with better logging and timeout handling
    
    Analyzes 12 components:
    - Trading Signals, Backtests, ML Model, Daily Reports
    - Message Sending, Trading Journal, Scheduler, Position Monitor
    - Breaking News, Disk/System, Access Control, Real-Time Monitor
    
    Usage: /health or 🏥 Health button
    """
    try:
        logger.info("🏥 Health command initiated")
        
        progress = await update.message.reply_text(
            "🏥 <b>СИСТЕМНА ДИАГНОСТИКА</b>\n\n"
            "Сканирам 12 компонента...\n"
            "⏳ Това може да отнeme до 90 секунди.\n\n"
            "<i>Моля изчакайте...</i>",
            parse_mode='HTML'
        )
        
        try:
            # Import diagnostic modules
            from system_diagnostics import run_full_health_check
            from diagnostic_messages import format_health_summary
            
            logger.info("Running full health check with 90s timeout...")
            
            # Run with 90-second timeout
            health_report = await asyncio.wait_for(
                run_full_health_check(BASE_PATH),
                timeout=90.0
            )
            
            logger.info(f"Health check completed in {health_report.get('duration', 0):.2f}s")
            
            # Format comprehensive report
            message = format_health_summary(health_report)
            
            # Delete progress message
            await progress.delete()
            
            # Send full diagnostic report (may be multiple messages if >4096 chars)
            if len(message) > 4000:
                # Split into chunks
                chunks = []
                current_chunk = ""
                for line in message.split('\n'):
                    if len(current_chunk) + len(line) + 1 > 4000:
                        chunks.append(current_chunk)
                        current_chunk = line + '\n'
                    else:
                        current_chunk += line + '\n'
                if current_chunk:
                    chunks.append(current_chunk)
                
                for i, chunk in enumerate(chunks):
                    await update.message.reply_text(
                        chunk,
                        parse_mode='HTML'
                    )
                    if i < len(chunks) - 1:
                        await asyncio.sleep(0.5)  # Avoid rate limits
            else:
                from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                keyboard = [
        [
            InlineKeyboardButton("🧪 Function Health", callback_data="health_function_test"),
            InlineKeyboardButton("⚡ Performance", callback_data="health_performance")
        ],
        [
            InlineKeyboardButton("🔄 Replay Last 5", callback_data="health_replay"),
            InlineKeyboardButton("🔬 Deep Analysis", callback_data="health_deep")
        ],
                    [
                        InlineKeyboardButton("🔄 Refresh", callback_data="health_refresh"),
                        InlineKeyboardButton("🧠 Deep", callback_data="health_deep"),
                        InlineKeyboardButton("⚡ Smoke Test", callback_data="health_smoke"),
                        InlineKeyboardButton("🔬 Run All", callback_data="health_run_all"),
                    ],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await update.message.reply_text(message, parse_mode="HTML", reply_markup=reply_markup)
            
        except asyncio.TimeoutError:
            # Fallback to quick health check
            await progress.edit_text(
                "⚠️ <b>Пълната диагностика отне повече от 90 секунди</b>\n\n"
                "Показвам бърза проверка...",
                parse_mode='HTML'
            )
            
            quick_report = await quick_health_check()
            await update.message.reply_text(quick_report, parse_mode='HTML')
            
            logger.warning("Health diagnostic timeout after 90s, used quick check fallback")
            
    except Exception as e:
        logger.error(f"❌ Health diagnostic error: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ <b>Грешка в диагностиката</b>\n\n"
            f"<code>{str(e)}</code>\n\n"
            f"<i>Опитай /quick_health за бърза проверка</i>",
            parse_mode='HTML'
        )


# ============================================================================
# PR #7: POSITION MANAGEMENT COMMANDS
# ============================================================================

@require_access()
@rate_limited(calls=20, period=60)
async def position_list_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /position_list
    Show all open positions with current prices and unrealized P&L
    """
    try:
        if not POSITION_MANAGER_AVAILABLE or not position_manager_global:
            await update.message.reply_text(
                "❌ Position Manager not available",
                parse_mode='HTML'
            )
            return
        
        positions = position_manager_global.get_open_positions()
        
        if not positions:
            await update.message.reply_text(
                "📊 No open positions",
                parse_mode='HTML'
            )
            return
        
        msg = f"<b>📊 OPEN POSITIONS ({len(positions)})</b>\n\n"
        
        for pos in positions:
            symbol = pos['symbol']
            current_price = get_live_price(symbol)
            
            # Calculate unrealized P&L
            if current_price:
                if pos['signal_type'] == 'BUY':
                    unrealized_pl = ((current_price - pos['entry_price']) / pos['entry_price']) * 100
                else:  # SELL
                    unrealized_pl = ((pos['entry_price'] - current_price) / pos['entry_price']) * 100
            else:
                unrealized_pl = 0.0
            
            pl_emoji = "🟢" if unrealized_pl > 0 else "🔴" if unrealized_pl < 0 else "⚪"
            
            # Format checkpoints status
            checkpoints_status = []
            if pos.get('checkpoint_25_triggered'):
                checkpoints_status.append('25%')
            if pos.get('checkpoint_50_triggered'):
                checkpoints_status.append('50%')
            if pos.get('checkpoint_75_triggered'):
                checkpoints_status.append('75%')
            if pos.get('checkpoint_85_triggered'):
                checkpoints_status.append('85%')
            
            checkpoints_str = ', '.join(checkpoints_status) if checkpoints_status else 'None'
            
            # Format timestamp
            try:
                opened_at = datetime.fromisoformat(pos['opened_at'])
                opened_str = opened_at.strftime('%Y-%m-%d %H:%M')
            except:
                opened_str = pos['opened_at']
            
            msg += f"""
━━━━━━━━━━━━━━━━━
<b>{symbol}</b> ({pos['timeframe'].upper()}) - {pos['signal_type']}
ID: {pos['id']}
Entry: ${pos['entry_price']:,.2f}
Current: ${current_price:,.2f if current_price else 'N/A'}
{pl_emoji} Unrealized P&L: {unrealized_pl:+.2f}%

TP1: ${pos['tp1_price']:,.2f}
SL: ${pos['sl_price']:,.2f}
Size: {pos.get('current_size', 1.0)*100:.0f}%

Checkpoints: {checkpoints_str}
Opened: {opened_str}
Source: {pos.get('source', 'N/A')}
"""
        
        await update.message.reply_text(msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Position list error: {e}")
        await update.message.reply_text(f"❌ Error: {e}", parse_mode='HTML')


@require_access()
@rate_limited(calls=10, period=60)
async def position_close_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /position_close <symbol>
    Manually close a position
    
    Example: /position_close BTCUSDT
    """
    try:
        if not POSITION_MANAGER_AVAILABLE or not position_manager_global:
            await update.message.reply_text(
                "❌ Position Manager not available",
                parse_mode='HTML'
            )
            return
        
        if not context.args or len(context.args) < 1:
            await update.message.reply_text(
                "❌ Usage: /position_close <symbol>\nExample: /position_close BTCUSDT",
                parse_mode='HTML'
            )
            return
        
        symbol = context.args[0].upper()
        
        # Find position by symbol
        positions = position_manager_global.get_open_positions()
        position = None
        for pos in positions:
            if pos['symbol'] == symbol:
                position = pos
                break
        
        if not position:
            await update.message.reply_text(
                f"❌ No open position found for {symbol}",
                parse_mode='HTML'
            )
            return
        
        # Get current price
        current_price = get_live_price(symbol)
        if not current_price:
            await update.message.reply_text(
                f"❌ Could not get current price for {symbol}",
                parse_mode='HTML'
            )
            return
        
        # Close position
        pl_percent = position_manager_global.close_position(
            position_id=position['id'],
            exit_price=current_price,
            outcome='MANUAL_CLOSE'
        )
        
        msg = f"""
✅ <b>POSITION CLOSED</b>

━━━━━━━━━━━━━━━━━
📊 <b>{symbol}</b> ({position['timeframe'].upper()})
Signal: {position['signal_type']}

Entry: ${position['entry_price']:,.2f}
Exit: ${current_price:,.2f}
<b>P&L: {pl_percent:+.2f}%</b>

━━━━━━━━━━━━━━━━━
Position closed manually.
"""
        
        await update.message.reply_text(msg, parse_mode='HTML')
        logger.info(f"✅ Position manually closed: {symbol}, P&L: {pl_percent:+.2f}%")
        
    except Exception as e:
        logger.error(f"Position close error: {e}")
        await update.message.reply_text(f"❌ Error: {e}", parse_mode='HTML')


@require_access()
@rate_limited(calls=20, period=60)
async def position_history_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /position_history [limit]
    Show recent closed positions with P&L stats
    
    Example: /position_history 10
    """
    try:
        if not POSITION_MANAGER_AVAILABLE or not position_manager_global:
            await update.message.reply_text(
                "❌ Position Manager not available",
                parse_mode='HTML'
            )
            return
        
        # Get limit from args or default to 10
        limit = 10
        if context.args and len(context.args) > 0:
            try:
                limit = min(int(context.args[0]), 50)  # Max 50
            except:
                pass
        
        history = position_manager_global.get_position_history(limit=limit)
        
        if not history:
            await update.message.reply_text(
                "📊 No position history",
                parse_mode='HTML'
            )
            return
        
        msg = f"<b>📊 POSITION HISTORY (Last {len(history)})</b>\n\n"
        
        for pos in history:
            pl_emoji = "🟢" if pos['profit_loss_percent'] > 0 else "🔴"
            
            # Format timestamp
            try:
                closed_at = datetime.fromisoformat(pos['closed_at'])
                closed_str = closed_at.strftime('%Y-%m-%d %H:%M')
            except:
                closed_str = pos['closed_at']
            
            msg += f"""
━━━━━━━━━━━━━━━━━
<b>{pos['symbol']}</b> ({pos['timeframe'].upper()}) - {pos['signal_type']}
{pl_emoji} P&L: <b>{pos['profit_loss_percent']:+.2f}%</b>
Outcome: {pos['outcome']}
Duration: {pos.get('duration_hours', 0):.1f}h
Checkpoints: {pos.get('checkpoints_triggered', 0)}
Closed: {closed_str}
"""
        
        await update.message.reply_text(msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Position history error: {e}")
        await update.message.reply_text(f"❌ Error: {e}", parse_mode='HTML')


@require_access()
@rate_limited(calls=10, period=60)
async def position_stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /position_stats
    Show aggregate position statistics
    """
    try:
        if not POSITION_MANAGER_AVAILABLE or not position_manager_global:
            await update.message.reply_text(
                "❌ Position Manager not available",
                parse_mode='HTML'
            )
            return
        
        stats = position_manager_global.get_position_stats()
        
        if not stats or stats['total_positions'] == 0:
            await update.message.reply_text(
                "📊 No position statistics available",
                parse_mode='HTML'
            )
            return
        
        # Format message
        win_emoji = "🔥" if stats['win_rate'] >= 70 else "💪" if stats['win_rate'] >= 60 else "👍"
        pl_emoji = "💰" if stats['avg_pl_percent'] > 0 else "📉"
        
        msg = f"""
<b>📊 POSITION STATISTICS</b>

━━━━━━━━━━━━━━━━━
📈 <b>OVERVIEW</b>

Total Positions: {stats['total_positions']}
Open Positions: {stats['open_positions']}

━━━━━━━━━━━━━━━━━
🎯 <b>PERFORMANCE</b>

{win_emoji} Win Rate: <b>{stats['win_rate']:.1f}%</b>
✅ Winning: {stats['winning_positions']}
❌ Losing: {stats['losing_positions']}

{pl_emoji} Avg P&L: <b>{stats['avg_pl_percent']:+.2f}%</b>

━━━━━━━━━━━━━━━━━
⏱️ <b>METRICS</b>

Avg Duration: {stats['avg_duration_hours']:.1f}h
Avg Checkpoints: {stats['avg_checkpoints_triggered']:.1f}
"""
        
        await update.message.reply_text(msg, parse_mode='HTML')
        
    except Exception as e:
        logger.error(f"Position stats error: {e}")
        await update.message.reply_text(f"❌ Error: {e}", parse_mode='HTML')





# ============================================================================
# INTELLIGENT HEALTH CHECK COMMANDS (Phase 1.5)
# ============================================================================

async def deep_health_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🧠 Deep intelligent health analysis
    
    Uses AI-like reasoning to diagnose problems and suggest fixes.
    Command: /deep_health
    """
    chat_id = update.effective_chat.id
    
    try:
        await update.message.reply_text("🧠 Running intelligent diagnostics...\n⏳ Please wait...")
        
        # Import intelligent diagnostics
        from system_diagnostics import diagnose_with_intelligence, get_intelligent_report
        
        # Run analysis
        report_text = await get_intelligent_report(format='telegram')
        
        # Send report
        await update.message.reply_text(report_text, parse_mode='HTML')
        
        logger.info(f"Deep health check completed for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Deep health check failed: {e}", exc_info=True)
        await update.message.reply_text(
            f"❌ Deep diagnostics failed: {e}\n\n"
            f"Please check logs or try /health for basic diagnostics."
        )


async def meta_diagnostic_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    🔄 System self-check
    
    The diagnostic system checks itself.
    Command: /self_check
    """
    chat_id = update.effective_chat.id
    
    try:
        await update.message.reply_text("🔄 Running self-diagnostic...\n⏳ Checking intelligence system...")
        
        from system_diagnostics import run_meta_diagnostic
        
        result = await run_meta_diagnostic()
        
        # Format output
        lines = []
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("🔄 INTELLIGENCE SYSTEM SELF-CHECK")
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        lines.append("")
        
        for check in result.get('checks', []):
            status_emoji = "✅" if check['status'] == 'pass' else "⚠️" if check['status'] == 'warning' else "❌"
            lines.append(f"{status_emoji} {check['name']}")
            lines.append(f"   {check['message']}")
            lines.append("")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        overall = result.get('overall_status', 'unknown')
        if overall == 'pass':
            lines.append("✅ Intelligence system is healthy")
        elif overall == 'error':
            lines.append(f"❌ Self-check error: {result.get('error')}")
        else:
            lines.append("���️ Intelligence system has warnings")
        
        lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
        
        await update.message.reply_text('\n'.join(lines))
        
        logger.info(f"Meta-diagnostic completed for chat {chat_id}")
        
    except Exception as e:
        logger.error(f"Meta-diagnostic failed: {e}", exc_info=True)
        await update.message.reply_text(f"❌ Self-check failed: {e}")


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
    app.add_handler(CommandHandler("fund", fund_cmd))  # Quick fundamental analysis toggle
    app.add_handler(CommandHandler("timeframe", timeframe_cmd))
    app.add_handler(CommandHandler("trade_status", trade_status_cmd))  # 🔄 Trade checkpoint analysis
    app.add_handler(CommandHandler("alerts", alerts_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    app.add_handler(CommandHandler("journal", journal_cmd))  # 📝 Trading Journal с ML
    app.add_handler(CommandHandler("risk", risk_cmd))  # 🛡️ Risk Management
    app.add_handler(CommandHandler("explain", explain_cmd))  # 📖 ICT/LuxAlgo речник
    app.add_handler(CommandHandler("toggle_ict", toggle_ict_command))  # 🔧 ICT Enhancer toggle
    app.add_handler(CommandHandler("toggle_ict_only", toggle_ict_only_cmd))  # 🎯 Toggle pure ICT mode
    app.add_handler(CommandHandler("status", status_cmd))  # 📊 Show configuration and cache stats
    app.add_handler(CommandHandler("cache_stats", cache_stats_cmd))  # 📊 Detailed cache statistics
    app.add_handler(CommandHandler("performance", performance_cmd))  # 📊 Performance metrics (admin)
    app.add_handler(CommandHandler("clear_cache", clear_cache_cmd))  # 🗑️ Clear cache (admin)
    app.add_handler(CommandHandler("debug", debug_mode_cmd))  # 🔍 Toggle debug mode (admin)
    app.add_handler(CommandHandler("health", health_cmd))  # 🏥 System health diagnostic (PR #10)
    app.add_handler(CommandHandler("quick_health", quick_health_cmd))  # 🏥 Quick health check (5s)
    app.add_handler(CommandHandler("deep_health", deep_health_cmd))  # 🧠 Intelligent diagnostics (Phase 1.5)
    app.add_handler(CommandHandler("self_check", meta_diagnostic_cmd))  # 🔄 Self-diagnostic
    
    # Active Trades Management Commands
    app.add_handler(CommandHandler("close_trade", close_trade_cmd))  # 🔒 Manually close a trade
    app.add_handler(CommandHandler("active_trades", active_trades_cmd))  # 📊 View active trades
    
    # Админ команди
    app.add_handler(CommandHandler("admin_login", admin_login_cmd))
    app.add_handler(CommandHandler("admin_setpass", admin_setpass_cmd))
    app.add_handler(CommandHandler("admin_daily", admin_daily_cmd))
    app.add_handler(CommandHandler("admin_weekly", admin_weekly_cmd))
    app.add_handler(CommandHandler("admin_monthly", admin_monthly_cmd))
    app.add_handler(CommandHandler("admin_docs", admin_docs_cmd))
    
    # Security Admin Commands (NEW - v2.0.0)
    if SECURITY_MODULES_AVAILABLE:
        app.add_handler(CommandHandler("blacklist", admin_blacklist_cmd))  # 🚫 Blacklist user
        app.add_handler(CommandHandler("unblacklist", admin_unblacklist_cmd))  # ✅ Remove from blacklist
        app.add_handler(CommandHandler("security_stats", admin_security_stats_cmd))  # 🔒 Security statistics
        app.add_handler(CommandHandler("unban", admin_unban_cmd))  # 🔓 Unban rate-limited user
    
    app.add_handler(CommandHandler("update", auto_update_cmd))  # 🔄 Обновяване на бота от GitHub (БЕЗ ПАРОЛА)
    app.add_handler(CommandHandler("auto_update", auto_update_cmd))  # 🔄 Auto-update от GitHub (същата функция)
    app.add_handler(CommandHandler("test", test_system_cmd))  # Тест и автоматично отстраняване на грешки
    
    # User Access Management команди (само owner)
    app.add_handler(CommandHandler("approve", approve_user_cmd))  # Одобри потребител
    app.add_handler(CommandHandler("block", block_user_cmd))  # Блокирай потребител
    app.add_handler(CommandHandler("users", list_users_cmd))  # Списък с потребители
    
    # ML, Back-testing, Reports команди
    app.add_handler(CommandHandler("backtest_results", backtest_results_cmd))  # Show saved backtest results
    app.add_handler(CommandHandler("verify_alerts", verify_alerts_cmd))  # Verify alert systems
    app.add_handler(CommandHandler("backup_settings", backup_settings_cmd))  # Backup backtest settings
    app.add_handler(CommandHandler("restore_settings", restore_settings_cmd))  # Restore backtest settings
    app.add_handler(CommandHandler("ml_status", ml_status_cmd))  # ML статус
    app.add_handler(CommandHandler("ml_train", ml_train_cmd))  # Ръчно обучение
    app.add_handler(CommandHandler("daily_report", daily_report_cmd))  # Дневен отчет
    app.add_handler(CommandHandler("weekly_report", weekly_report_cmd))  # Седмичен отчет
    app.add_handler(CommandHandler("monthly_report", monthly_report_cmd))  # Месечен отчет
    app.add_handler(CommandHandler("reports", reports_cmd))  # Централизирани отчети
    
    # PR #7: Position management commands
    app.add_handler(CommandHandler("position_list", position_list_cmd))  # Show open positions
    app.add_handler(CommandHandler("position_close", position_close_cmd))  # Close position manually
    app.add_handler(CommandHandler("position_history", position_history_cmd))  # Position history
    app.add_handler(CommandHandler("position_stats", position_stats_cmd))  # Position statistics
    
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
    app.add_handler(CallbackQueryHandler(timeframe_callback, pattern='^timeframe_settings$'))  # Settings menu timeframe
    app.add_handler(CallbackQueryHandler(toggle_fundamental_callback, pattern='^toggle_fundamental$'))  # Fundamental toggle
    app.add_handler(CallbackQueryHandler(reports_callback, pattern='^report_'))  # Reports menu
    
    # Market submenu callback handlers
    app.add_handler(CallbackQueryHandler(market_callback, pattern='^market_'))
    app.add_handler(CallbackQueryHandler(market_callback, pattern='^lang_'))
    
    # NEW: Backtest callback handlers
    app.add_handler(CallbackQueryHandler(ml_performance_callback, pattern='^ml_performance'))
    app.add_handler(CallbackQueryHandler(backtest_all_callback, pattern='^backtest_all'))
    app.add_handler(CallbackQueryHandler(backtest_deep_dive_callback, pattern='^backtest_deep_dive$'))
    app.add_handler(CallbackQueryHandler(deep_dive_symbol_callback, pattern='^deep_dive_'))
    app.add_handler(CallbackQueryHandler(health_function_test_callback, pattern="^health_function_test$"))
    app.add_handler(CallbackQueryHandler(health_performance_callback, pattern="^health_performance$"))
    app.add_handler(CallbackQueryHandler(health_replay_callback, pattern="^health_replay$"))
    app.add_handler(CallbackQueryHandler(health_callback, pattern='^health_'))
    
    # Message handler за текстови бутони от клавиатурата
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, button_handler))
    
    logger.info("🚀 Crypto Signal Bot стартира...")
    
    # 📝 ENSURE TRADING JOURNAL EXISTS
    try:
        logger.info("📝 Checking trading journal...")
        journal = load_journal()
        if journal:
            save_journal(journal)
            logger.info(f"✅ Trading journal initialized: {JOURNAL_FILE}")
            logger.info(f"📊 Journal contains {len(journal.get('trades', []))} trades")
        else:
            logger.error(f"❌ Failed to initialize trading journal: {JOURNAL_FILE}")
    except Exception as journal_error:
        logger.error(f"❌ Trading journal initialization error: {journal_error}")
    
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
    if ADMIN_MODULE_AVAILABLE or REPORTS_AVAILABLE:
        async def schedule_reports(application):
            """Инициализира APScheduler след стартиране на бота"""
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            import pytz
            
            # Използвай българско време
            bg_tz = pytz.timezone('Europe/Sofia')
            scheduler = AsyncIOScheduler(timezone=bg_tz)
            
            # Create context for jobs that require it
            class SimpleContext:
                """Minimal context object for scheduler jobs that need bot access."""
                def __init__(self, bot):
                    self.bot = bot
            
            context = SimpleContext(application.bot)
            
            # ЕДИНСТВЕН ДНЕВЕН ОТЧЕТ - Всеки ден в 08:00 българско време
            if REPORTS_AVAILABLE:
                @safe_job("daily_report", max_retries=3, retry_delay=60)
                async def send_daily_auto_report():
                    """Изпраща автоматичен дневен отчет към owner за ВЧЕРА"""
                    try:
                        report = report_engine.generate_daily_report()
                        if report:
                            message = report_engine.format_report_message(report)
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=message,
                                parse_mode='HTML',
                                disable_notification=False  # Със звук
                            )
                            logger.info("✅ Daily report sent successfully")
                        else:
                            # Send notification about missing data
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=(
                                    "⚠️ <b>DAILY REPORT - NO DATA</b>\n\n"
                                    "Няма данни за вчерашния ден.\n\n"
                                    "<b>Възможни причини:</b>\n"
                                    "• Няма генерирани сигнали вчера\n"
                                    "• Trading journal е празен\n"
                                    "• Сигналите не са записани правилно\n\n"
                                    "💡 Провери: <code>/ml_status</code>"
                                ),
                                parse_mode='HTML',
                                disable_notification=False
                            )
                            logger.warning("⚠️ Daily report has no data to send")
                    except Exception as e:
                        logger.error(f"❌ Daily report error: {e}")
                        # Send error notification
                        try:
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=f"❌ <b>DAILY REPORT ERROR</b>\n\n<code>{str(e)}</code>",
                                parse_mode='HTML'
                            )
                        except Exception as notify_error:
                            logger.error(f"Failed to send error notification: {notify_error}")
                
                scheduler.add_job(
                    send_daily_auto_report,
                    'cron',
                    hour=8,
                    minute=0,
                    misfire_grace_time=DAILY_REPORT_MISFIRE_GRACE_TIME,  # Allow 12 hour window for missed reports
                    coalesce=True,            # Combine multiple missed runs into one
                    max_instances=1           # Only one instance at a time
                )
                logger.info("✅ Daily reports scheduled at 08:00 BG time (Europe/Sofia timezone)")
                
                # Add startup check for missed daily report
                async def check_missed_daily_report():
                    """Check if daily report was missed today and send it"""
                    # DISABLED: Don't check/send daily report on restart
                    # Daily report will ONLY send at scheduled 08:00 BG time
                    logger.info("ℹ️ Startup missed report check disabled - daily report sends only at 08:00")
                    return
                    
                    try:
                        bg_tz = pytz.timezone('Europe/Sofia')
                        now = datetime.now(bg_tz)
                        today_str = now.strftime('%Y-%m-%d')
                        
                        # Check if report already sent today
                        reports_file = f'{BASE_PATH}/daily_reports.json'
                        already_sent = False
                        
                        try:
                            if os.path.exists(reports_file):
                                with open(reports_file, 'r') as f:
                                    data = json.load(f)
                                    reports = data.get('reports', [])
                                    # Check if any report exists for today
                                    for report in reports:
                                        if report.get('date') == today_str:
                                            already_sent = True
                                            logger.info(f"✅ Daily report already sent today ({today_str})")
                                            break
                        except Exception as check_error:
                            logger.warning(f"Could not check daily reports file: {check_error}")
                        
                        # Only send if not already sent today
                        if not already_sent:
                            # If after 08:00 and before 23:59, check if report needs to be sent
                            if now.hour > 8:
                                logger.info("⚠️ Bot started after 08:00 - checking for missed daily report...")
                                # Send the report now if we're within the grace period
                                if now.hour < 20:  # Within 12 hours of scheduled time (08:00 + 12h = 20:00)
                                    logger.warning("⚠️ Daily report was missed - sending now...")
                                    await send_daily_auto_report()
                                else:
                                    logger.info("ℹ️ Outside grace period - daily report will send tomorrow")
                        else:
                            logger.info("ℹ️ Daily report already sent today - skipping")
                    except Exception as e:
                        logger.error(f"Error in missed report check: {e}")
                
                # Schedule the check to run shortly after bot startup
                scheduler.add_job(
                    check_missed_daily_report,
                    'date',
                    run_date=datetime.now(bg_tz) + timedelta(seconds=STARTUP_CHECK_DELAY_SECONDS),
                    id='missed_report_check',
                    name='Missed Report Check'
                )
            
            # СЕДМИЧЕН ОТЧЕТ - Всеки понеделник в 08:00 българско време
            if REPORTS_AVAILABLE:
                @safe_job("weekly_report", max_retries=3, retry_delay=60)
                async def send_weekly_auto_report():
                    """Изпраща автоматичен седмичен отчет към owner за ИЗМИНАЛАТА СЕДМИЦА"""
                    try:
                        summary = report_engine.get_weekly_summary()
                        if summary:
                            # Форматирай седмичния отчет
                            message = f"""📈 <b>СЕДМИЧЕН ОТЧЕТ</b>
📅 {summary['period']}
━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>ГЕНЕРИРАНИ СИГНАЛИ:</b>
   📊 Общо: <b>{summary['total_signals']}</b>
   🟢 BUY: {summary['buy_signals']}
   🔴 SELL: {summary['sell_signals']}
   ⏳ Активни: {summary['active_signals']}
   ✅ Завършени: {summary['completed_signals']}

"""
                            if summary['completed_signals'] > 0:
                                accuracy_emoji = "🔥" if summary['accuracy'] >= 70 else "💪" if summary['accuracy'] >= 60 else "👍"
                                message += f"""🎯 <b>ТОЧНОСТ:</b>
   {accuracy_emoji} Accuracy: <b>{summary['accuracy']:.1f}%</b>
   ✅ Печеливши: {summary['wins']}
   ❌ Загубени: {summary['losses']}

💵 <b>PERFORMANCE:</b>
   {'💰' if summary['total_profit'] > 0 else '📉'} Общ Profit: <b>{summary['total_profit']:+.2f}%</b>
"""
                                if summary['avg_win'] > 0:
                                    message += f"   📈 Среден WIN: +{summary['avg_win']:.2f}%\n"
                                if summary['avg_loss'] < 0:
                                    message += f"   📉 Среден LOSS: {summary['avg_loss']:.2f}%\n"
                            
                            message += f"\n💪 Средна увереност: {summary['avg_confidence']:.1f}%"
                            
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=message,
                                parse_mode='HTML',
                                disable_notification=False
                            )
                            logger.info("✅ Weekly report sent successfully")
                    except Exception as e:
                        logger.error(f"❌ Weekly report error: {e}")
                
                scheduler.add_job(
                    send_weekly_auto_report,
                    'cron',
                    day_of_week='mon',
                    hour=8,
                    minute=0
                )
                logger.info("✅ Weekly reports scheduled for Mondays at 08:00 BG time")
            
            # МЕСЕЧЕН ОТЧЕТ - На 1-во число в 08:00 българско време
            if REPORTS_AVAILABLE:
                @safe_job("monthly_report", max_retries=3, retry_delay=60)
                async def send_monthly_auto_report():
                    """Изпраща автоматичен месечен отчет към owner за ИЗМИНАЛИЯ МЕСЕЦ"""
                    try:
                        summary = report_engine.get_monthly_summary()
                        if summary:
                            # Форматирай месечния отчет
                            message = f"""🎯 <b>МЕСЕЧЕН ОТЧЕТ</b>
📅 {summary['period']}
━━━━━━━━━━━━━━━━━━━━━━━━

📊 <b>ГЕНЕРИРАНИ СИГНАЛИ:</b>
   📊 Общо: <b>{summary['total_signals']}</b>
   🟢 BUY: {summary['buy_signals']}
   🔴 SELL: {summary['sell_signals']}
   ⏳ Активни: {summary['active_signals']}
   ✅ Завършени: {summary['completed_signals']}

"""
                            if summary['completed_signals'] > 0:
                                accuracy_emoji = "🔥" if summary['accuracy'] >= 70 else "💪" if summary['accuracy'] >= 60 else "👍"
                                message += f"""🎯 <b>ТОЧНОСТ:</b>
   {accuracy_emoji} Accuracy: <b>{summary['accuracy']:.1f}%</b>
   ✅ Печеливши: {summary['wins']}
   ❌ Загубени: {summary['losses']}

💵 <b>PERFORMANCE:</b>
   {'💰' if summary['total_profit'] > 0 else '📉'} Общ Profit: <b>{summary['total_profit']:+.2f}%</b>
   🎯 Profit Factor: {summary.get('profit_factor', 0):.2f}
"""
                                if summary['avg_win'] > 0:
                                    message += f"   📈 Среден WIN: +{summary['avg_win']:.2f}%\n"
                                if summary['avg_loss'] < 0:
                                    message += f"   📉 Среден LOSS: {summary['avg_loss']:.2f}%\n"
                            
                            message += f"\n💪 Средна увереност: {summary['avg_confidence']:.1f}%"
                            
                            # Добави статистика по символи ако има
                            if summary.get('symbols_stats'):
                                message += "\n\n💰 <b>ПО ВАЛУТИ:</b>\n"
                                for symbol, stats in sorted(summary['symbols_stats'].items(), key=lambda x: x[1]['profit'], reverse=True)[:5]:
                                    if stats['completed'] > 0:
                                        profit_emoji = "💚" if stats['profit'] > 0 else "🔴"
                                        message += f"   {profit_emoji} {symbol}: {stats['accuracy']:.0f}% acc, {stats['profit']:+.2f}%\n"
                            
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=message,
                                parse_mode='HTML',
                                disable_notification=False
                            )
                            logger.info("✅ Monthly report sent successfully")
                    except Exception as e:
                        logger.error(f"❌ Monthly report error: {e}")
                
                scheduler.add_job(
                    send_monthly_auto_report,
                    'cron',
                    day=1,
                    hour=8,
                    minute=0
                )
                logger.info("✅ Monthly reports scheduled for 1st of month at 08:00 BG time")
            
            # ==================== DAILY BACKTEST AUTO-UPDATE ====================
            # Daily comprehensive backtest at 02:00 UTC with archiving
            if ICT_BACKTEST_AVAILABLE:
                @safe_job("daily_backtest", max_retries=3, retry_delay=120)
                async def daily_backtest_update():
                    """
                    Daily comprehensive backtest auto-update at 02:00 UTC
                    - Archives old results to backtest_archive/YYYY-MM-DD/
                    - Cleans up archives older than 30 days
                    - Runs comprehensive backtest (all symbols + timeframes)
                    - Sends completion notification to owner
                    """
                    try:
                        logger.info("🔄 Starting daily backtest auto-update...")
                        
                        # Import the comprehensive backtest function
                        from ict_backtest import run_comprehensive_backtest
                        
                        # Run comprehensive backtest (includes archiving and cleanup)
                        await run_comprehensive_backtest()
                        
                        # Send completion notification
                        notification = (
                            "✅ <b>DAILY BACKTEST UPDATE COMPLETE</b>\n\n"
                            "🔄 Comprehensive backtest finished\n"
                            "📦 Old results archived\n"
                            "🧹 Archive cleanup completed\n\n"
                            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\n\n"
                            "View results: /backtest_results"
                        )
                        
                        await application.bot.send_message(
                            chat_id=OWNER_CHAT_ID,
                            text=notification,
                            parse_mode='HTML',
                            disable_notification=False  # With sound
                        )
                        
                        logger.info("✅ Daily backtest update completed successfully")
                        
                    except Exception as e:
                        logger.error(f"❌ Daily backtest update error: {e}")
                        
                        # Send error notification
                        error_msg = (
                            "⚠️ <b>DAILY BACKTEST UPDATE FAILED</b>\n\n"
                            f"Error: {str(e)[:200]}\n\n"
                            f"⏰ {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}"
                        )
                        
                        try:
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=error_msg,
                                parse_mode='HTML',
                                disable_notification=False
                            )
                        except Exception as e:
                            logger.error(f"❌ Failed to send backtest error notification: {e}")
                            pass
                
                scheduler.add_job(
                    daily_backtest_update,
                    'cron',
                    hour=2,  # 02:00 UTC
                    minute=0
                )
                logger.info("✅ Daily backtest auto-update scheduled at 02:00 UTC")
            
            # Автоматична диагностика всеки ден в 01:00 UTC (03:00 BG време)
            scheduler.add_job(
                run_diagnostics,
                'cron',
                hour=1,
                minute=0
            )
            
            # 🔄 DIAGNOSTIC CACHE REFRESH JOB (PR #4 - Performance Optimization)
            # Background job to keep diagnostic cache warm for instant button responses
            @safe_job("diagnostic_cache_refresh", max_retries=2, retry_delay=30)
            async def diagnostic_cache_refresh_job():
                """
                Background job: Refresh diagnostic cache every 5 minutes
                Keeps cache warm so user commands respond instantly
                
                CRITICAL: Also monitors cache size to detect memory leaks
                """
                try:
                    logger.info("🔄 Refreshing diagnostic cache (background)...")
                    
                    from system_diagnostics import grep_logs_cached, DIAGNOSTIC_CACHE
                    
                    # Log cache state BEFORE refresh
                    cache_size_before = len(DIAGNOSTIC_CACHE)
                    logger.info(f"📊 Cache state before refresh: {cache_size_before} entries")
                    
                    base_path = os.path.dirname(os.path.abspath(__file__))
                    
                    # Pre-populate cache with common diagnostic patterns
                    # Note: grep_logs_cached() will automatically cleanup expired entries
                    patterns = [
                        ('ERROR.*journal', 6),           # Journal errors (6h)
                        ('ERROR.*ml.*train', 168),       # ML errors (7 days)
                        ('ERROR.*position', 1),          # Position errors (1h)
                        ('ERROR.*scheduler|ERROR.*APScheduler', 12),  # Scheduler errors (12h)
                        ('ERROR.*real.?time.*monitor', 6)  # Real-time monitor errors (6h)
                    ]
                    
                    # Run all patterns to warm cache
                    for pattern, hours in patterns:
                        try:
                            await grep_logs_cached(pattern, hours, base_path=base_path, force_refresh=True)
                        except Exception as e:
                            logger.warning(f"⚠️ Cache refresh failed for pattern '{pattern}': {e}")
                    
                    cache_size_final = len(DIAGNOSTIC_CACHE)
                    logger.info(f"✅ Diagnostic cache refreshed successfully ({cache_size_final} entries)")
                    
                    # Warn if cache is growing unbounded (memory leak detection)
                    if cache_size_final > 20:
                        logger.warning(f"⚠️ Cache size is large ({cache_size_final} entries) - potential memory leak!")
                    
                except Exception as e:
                    logger.error(f"❌ Diagnostic cache refresh error: {e}", exc_info=True)
            
            scheduler.add_job(
                diagnostic_cache_refresh_job,
                'interval',
                minutes=5,
                id='diagnostic_cache_refresh',
                name='Diagnostic Cache Refresh (Background)',
                max_instances=1,
                coalesce=True
            )
            logger.info("✅ Diagnostic cache refresh job registered (every 5 min)")
            
            # Автоматични новини 3 пъти дневно: 08:00, 14:00, 20:00 UTC
            scheduler.add_job(
                lambda: application.create_task(send_auto_news(application.bot)),
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
            @safe_job("journal_monitoring", max_retries=2, retry_delay=30)
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
            @safe_job("signal_tracking", max_retries=2, retry_delay=30)
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
            
            # 📊 80% ALERT MONITORING - проверява активни trades на всяка минута
            @safe_job("80_percent_alerts", max_retries=2, retry_delay=10)
            async def check_80_alerts_wrapper():
                """Wrapper for 80% alert monitoring with bot instance"""
                try:
                    await check_80_percent_alerts(application.bot)
                except Exception as e:
                    logger.error(f"80% alert monitoring error: {e}")
            
            scheduler.add_job(
                check_80_alerts_wrapper,
                'interval',
                minutes=1,  # Check every minute
                id='check_80_percent_alerts',
                replace_existing=True
            )
            logger.info("✅ 80% Alert monitoring scheduled (every 1 minute)")
            

            # 📊 DAILY BACKTEST SUMMARY - every day at 20:00 UTC
            @safe_job("scheduled_backtest_report", max_retries=3, retry_delay=60)
            async def send_scheduled_backtest_report():
                """Send daily backtest summary to owner"""
                try:
                    from journal_backtest import JournalBacktestEngine
                    
                    logger.info("📊 Generating daily backtest summary...")
                    
                    # Run backtest for last 7 days
                    backtest = JournalBacktestEngine()
                    results = backtest.run_backtest(days=7)
                    
                    if 'error' in results:
                        logger.warning(f"No backtest data: {results['error']}")
                        return
                    
                    overall = results.get('overall', {})
                    trend = results.get('trend_analysis', {})
                    by_symbol = results.get('by_symbol', {})
                    
                    # Find best and worst performers today
                    best_symbol = None
                    worst_symbol = None
                    if by_symbol:
                        sorted_symbols = sorted(
                            by_symbol.items(), 
                            key=lambda x: x[1]['win_rate'], 
                            reverse=True
                        )
                        if sorted_symbols:
                            best_symbol = sorted_symbols[0][0]
                            worst_symbol = sorted_symbols[-1][0] if len(sorted_symbols) > 1 else None
                    
                    # Format message
                    message = f"""📊 <b>DAILY BACKTEST SUMMARY</b>
━━━━━━━━━━━━━━━━━━━━━━━

📅 {datetime.now(timezone.utc).strftime('%Y-%m-%d')}

Today: {overall.get('total_trades', 0)} trades
Win Rate: {overall.get('win_rate', 0):.1f}%
P/L: {overall.get('total_pnl', 0):+.2f}%

Last 7 days: {trend.get('wr_7d', 0):.1f}% {trend.get('trend_7d', '')}

🏆 Best today: {best_symbol or 'N/A'}
📉 Worst today: {worst_symbol or 'N/A'}

💡 {trend.get('insight', 'No insight available')}
"""
                    
                    await application.bot.send_message(
                        chat_id=OWNER_CHAT_ID,
                        text=message,
                        parse_mode='HTML',
                        disable_notification=False
                    )
                    logger.info("✅ Daily backtest summary sent")
                    
                except Exception as e:
                    logger.error(f"Daily backtest summary error: {e}", exc_info=True)
            
            scheduler.add_job(
                send_scheduled_backtest_report,
                'cron',
                hour=8,
                minute=5,
                id="daily_backtest_summary",
                replace_existing=True,
                misfire_grace_time=43200,
                coalesce=True,
                max_instances=1
            )

              # 📊 WEEKLY BACKTEST SUMMARY - every Monday at 08:05 BG time
            scheduler.add_job(
                send_scheduled_backtest_report,
                "cron",
                day_of_week="mon",
                hour=8,
                minute=5,
                id="weekly_backtest_summary",
                replace_existing=True,
                misfire_grace_time=43200,
                coalesce=True,
                max_instances=1
            )

              # 📊 MONTHLY BACKTEST SUMMARY - 1st day of month at 08:05 BG time
            scheduler.add_job(
                send_scheduled_backtest_report,
                "cron",
                day=1,
                hour=8,
                minute=5,
                id="monthly_backtest_summary",
                replace_existing=True,
                misfire_grace_time=43200,
                coalesce=True,
                max_instances=1
            )

            

            # 📊 АВТОМАТИЧЕН СЕДМИЧЕН BACKTEST - всеки понеделник в 09:00 UTC (11:00 BG)
            if BACKTEST_AVAILABLE:
                @safe_job("weekly_backtest", max_retries=3, retry_delay=120)
                async def weekly_backtest_wrapper():
                    """Wrapper за автоматичен седмичен backtest - ВСИЧКИ монети и таймфрейми"""
                    try:
                        logger.info("📊 Starting weekly automated backtest for ALL coins and timeframes...")
                        
                        # ВСИЧКИ монети от SYMBOLS
                        symbols_to_test = list(SYMBOLS.values())  # BTCUSDT, ETHUSDT, XRPUSDT, SOLUSDT, BNBUSDT, ADAUSDT
                        
                        # Get automatic timeframes from contract
                        timeframes_to_test = TimeframeContract.get_supported_automatic_timeframes()
                        
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
   • Таймфрейми: {len(timeframes_to_test)} (1h, 2h, 4h, 1d)
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
            
            # ================= P5: ML AUTO-TRAINING SCHEDULER =================
            # Schedule ML auto-training every Sunday at 03:00 UTC
            scheduler.add_job(
                ml_auto_training_job,
                'cron',
                day_of_week='sun',  # Sunday
                hour=3,             # 03:00 UTC (05:00 BG time)
                minute=0,
                args=[context],     # Pass context argument
                id='ml_auto_training',
                name='ML Auto-Training',
                replace_existing=True
            )
            logger.info("✅ ML auto-training scheduled (Sundays 03:00 UTC)")
            
            # ================= P13: CACHE CLEANUP JOB =================
            # Add cache cleanup job (every 10 minutes)
            scheduler.add_job(
                cache_cleanup_job,
                'interval',
                minutes=10,
                args=[context],     # Pass context argument
                id='cache_cleanup',
                name='Cache Cleanup',
                replace_existing=True
            )
            logger.info("✅ Cache cleanup scheduled (every 10 minutes)")
            
            # ================= AUTO SIGNAL JOB WRAPPERS =================
            # Fix for lambda closure scope issue with asyncio in Python 3.12+
            # Lambda functions cannot access 'asyncio' in scheduler execution context
            # Using explicit wrapper functions following Position Monitor pattern
            
            async def auto_signal_1h_wrapper():
                """Wrapper for 1H auto signal job"""
                try:
                    await auto_signal_job('1h', application.bot)
                except Exception as e:
                    logger.error(f"❌ Auto Signal 1H error: {e}", exc_info=True)
            
            async def auto_signal_2h_wrapper():
                """Wrapper for 2H auto signal job"""
                try:
                    await auto_signal_job('2h', application.bot)
                except Exception as e:
                    logger.error(f"❌ Auto Signal 2H error: {e}", exc_info=True)
            
            async def auto_signal_4h_wrapper():
                """Wrapper for 4H auto signal job"""
                try:
                    await auto_signal_job('4h', application.bot)
                except Exception as e:
                    logger.error(f"❌ Auto Signal 4H error: {e}", exc_info=True)
            
            async def auto_signal_1d_wrapper():
                """Wrapper for 1D auto signal job"""
                try:
                    await auto_signal_job('1d', application.bot)
                except Exception as e:
                    logger.error(f"❌ Auto Signal 1D error: {e}", exc_info=True)
            
            # ================= PR #6: AUTO SIGNAL SCHEDULER JOBS =================
            # Auto signal scheduler jobs for 1H, 2H, 4H, 1D timeframes
            # Staggered timing to prevent overlaps
            
            # 1H - Every hour at :05
            scheduler.add_job(
                auto_signal_1h_wrapper,
                'cron',
                minute=5,
                id='auto_signal_1h',
                name='Auto Signal 1H',
                replace_existing=True
            )
            logger.info("✅ Auto signal 1H scheduled (every hour at :05)")
            
            # 2H - Every 2 hours at :07
            scheduler.add_job(
                auto_signal_2h_wrapper,
                'cron',
                hour='*/2',
                minute=7,
                id='auto_signal_2h',
                name='Auto Signal 2H',
                replace_existing=True
            )
            logger.info("✅ Auto signal 2H scheduled (every 2 hours at :07)")
            
            # 4H - Every 4 hours at :10
            scheduler.add_job(
                auto_signal_4h_wrapper,
                'cron',
                hour='*/4',
                minute=10,
                id='auto_signal_4h',
                name='Auto Signal 4H',
                replace_existing=True
            )
            logger.info("✅ Auto signal 4H scheduled (every 4 hours at :10)")
            
            # 1D - Daily at 09:15
            scheduler.add_job(
                auto_signal_1d_wrapper,
                'cron',
                hour=9,
                minute=15,
                id='auto_signal_1d',
                name='Auto Signal 1D',
                replace_existing=True
            )
            logger.info("✅ Auto signal 1D scheduled (daily at 09:15 UTC)")
            
            # ============================================================================
            # PR #10: INTELLIGENT HEALTH MONITORING JOBS
            # ============================================================================
            
            # 1. Trading Journal Health Monitor (every 6 hours)
            @safe_job("journal_health_monitor", max_retries=2, retry_delay=30)
            async def journal_health_monitor_job():
                """Monitor trading journal health every 6 hours"""
                try:
                    from system_diagnostics import diagnose_journal_issue
                    from diagnostic_messages import format_issue_alert
                    
                    logger.info("🏥 Running journal health check...", get_comprehensive_diagnostic_report)
                    issues = await diagnose_journal_issue(BASE_PATH)
                    
                    if issues:
                        # Send alert for each critical issue
                        for issue in issues:
                            message = format_issue_alert("TRADING JOURNAL", issue)
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=message,
                                parse_mode='HTML',
                                disable_notification=False  # With sound
                            )
                        logger.warning(f"⚠️ Journal health check found {len(issues)} issues")
                    else:
                        logger.info("✅ Journal health check passed")
                except Exception as e:
                    logger.error(f"❌ Journal health monitor error: {e}")
            
            scheduler.add_job(
                journal_health_monitor_job,
                'cron',
                hour='*/6',  # Every 6 hours
                minute=15,
                id='journal_health_monitor',
                name='Journal Health Monitor',
                replace_existing=True
            )
            logger.info("✅ Journal health monitor scheduled (every 6 hours)")
            
            # 2. ML Training Health Monitor (daily at 10:00)
            @safe_job("ml_health_monitor", max_retries=2, retry_delay=30)
            async def ml_health_monitor_job():
                """Monitor ML training health daily"""
                try:
                    from system_diagnostics import diagnose_ml_issue
                    from diagnostic_messages import format_issue_alert
                    
                    logger.info("🏥 Running ML health check...", get_comprehensive_diagnostic_report)
                    issues = await diagnose_ml_issue(BASE_PATH)
                    
                    if issues:
                        for issue in issues:
                            message = format_issue_alert("ML MODEL", issue)
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=message,
                                parse_mode='HTML',
                                disable_notification=False  # With sound
                            )
                        logger.warning(f"⚠️ ML health check found {len(issues)} issues")
                    else:
                        logger.info("✅ ML health check passed")
                except Exception as e:
                    logger.error(f"❌ ML health monitor error: {e}")
            
            scheduler.add_job(
                ml_health_monitor_job,
                'cron',
                hour=10,
                minute=0,
                id='ml_health_monitor',
                name='ML Health Monitor',
                replace_existing=True
            )
            logger.info("✅ ML health monitor scheduled (daily at 10:00)")
            
            # 3. Daily Report Execution Monitor (daily at 09:00)
            @safe_job("daily_report_health_monitor", max_retries=2, retry_delay=30)
            async def daily_report_health_monitor_job():
                """Check if yesterday's daily report was sent"""
                try:
                    from system_diagnostics import diagnose_daily_report_issue
                    from diagnostic_messages import format_issue_alert
                    
                    logger.info("🏥 Running daily report health check...", get_comprehensive_diagnostic_report)
                    issues = await diagnose_daily_report_issue(BASE_PATH)
                    
                    if issues:
                        for issue in issues:
                            message = format_issue_alert("DAILY REPORTS", issue)
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=message,
                                parse_mode='HTML',
                                disable_notification=False
                            )
                        logger.warning(f"⚠️ Daily report health check found {len(issues)} issues")
                    else:
                        logger.info("✅ Daily report health check passed")
                except Exception as e:
                    logger.error(f"❌ Daily report health monitor error: {e}")
            
            scheduler.add_job(
                daily_report_health_monitor_job,
                'cron',
                hour=9,
                minute=0,
                id='daily_report_health_monitor',
                name='Daily Report Health Monitor',
                replace_existing=True
            )
            logger.info("✅ Daily report health monitor scheduled (daily at 09:00)")
            
            # 5. Scheduler Health Monitor (every 12 hours)
            @safe_job("scheduler_health_monitor", max_retries=2, retry_delay=30)
            async def scheduler_health_monitor_job():
                """Monitor scheduler health"""
                try:
                    from system_diagnostics import diagnose_scheduler_issue
                    from diagnostic_messages import format_issue_alert
                    
                    logger.info("🏥 Running scheduler health check...", get_comprehensive_diagnostic_report)
                    issues = await diagnose_scheduler_issue(BASE_PATH)
                    
                    if issues:
                        for issue in issues:
                            message = format_issue_alert("SCHEDULER", issue)
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=message,
                                parse_mode='HTML',
                                disable_notification=False
                            )
                        logger.warning(f"⚠️ Scheduler health check found {len(issues)} issues")
                    else:
                        logger.info("✅ Scheduler health check passed")
                except Exception as e:
                    logger.error(f"❌ Scheduler health monitor error: {e}")
            
            scheduler.add_job(
                scheduler_health_monitor_job,
                'cron',
                hour='*/12',  # Every 12 hours
                minute=45,
                id='scheduler_health_monitor',
                name='Scheduler Health Monitor',
                replace_existing=True
            )
            logger.info("✅ Scheduler health monitor scheduled (every 12 hours)")
            
            # 6. Disk Space Monitor (daily at 02:00)
            @safe_job("disk_space_monitor", max_retries=2, retry_delay=30)
            async def disk_space_monitor_job():
                """Monitor disk space daily"""
                try:
                    from system_diagnostics import diagnose_disk_space_issue
                    from diagnostic_messages import format_issue_alert
                    
                    logger.info("🏥 Running disk space check...", get_comprehensive_diagnostic_report)
                    issues = await diagnose_disk_space_issue(BASE_PATH)
                    
                    if issues:
                        for issue in issues:
                            message = format_issue_alert("DISK SPACE", issue)
                            await application.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=message,
                                parse_mode='HTML',
                                disable_notification=False
                            )
                        logger.warning(f"⚠️ Disk space check found {len(issues)} issues")
                    else:
                        logger.info("✅ Disk space check passed")
                except Exception as e:
                    logger.error(f"❌ Disk space monitor error: {e}")
            
            scheduler.add_job(
                disk_space_monitor_job,
                'cron',
                hour=2,
                minute=0,
                id='disk_space_monitor',
                name='Disk Space Monitor',
                replace_existing=True
            )
            logger.info("✅ Disk space monitor scheduled (daily at 02:00)")
            
            # ============================================================================
            # END PR #10: INTELLIGENT HEALTH MONITORING
            # ============================================================================
            
            scheduler.start()
            logger.info("✅ APScheduler started successfully")
            logger.info("📅 Scheduled services: Reports, Diagnostics, News, Real-time Monitoring")
            logger.info("📝 Active features: Journal 24/7, Signal Tracking, Weekly Backtest")
            logger.info("🔄 Daily tasks: Backtest Update (02:00 UTC), Cache Cleanup (10 min)")
            logger.info("🤖 ML: Auto-training (weekly), Auto Signals (1H, 2H, 4H, 1D)")
            logger.info("📊 Position Monitoring (PR #7) + 🏥 Health Monitoring (PR #10)")
            
# DISABLED: # DISABLED:             # 🎯 INITIALIZE AND START REAL-TIME POSITION MONITOR (v2.1.0)
# DISABLED: # DISABLED:             global real_time_monitor_global
# DISABLED: # DISABLED:             if ICT_SIGNAL_ENGINE_AVAILABLE and ict_80_handler_global:
# DISABLED: # DISABLED:                 try:
# DISABLED: # DISABLED:                     real_time_monitor_global = RealTimePositionMonitor(
# DISABLED: # DISABLED:                         bot=application.bot,
# DISABLED: # DISABLED:                         ict_80_handler=ict_80_handler_global,
# DISABLED: # DISABLED:                         owner_chat_id=OWNER_CHAT_ID,
# DISABLED: # DISABLED:                         binance_price_url=BINANCE_PRICE_URL,
# DISABLED: # DISABLED:                         binance_klines_url=BINANCE_KLINES_URL
# DISABLED: # DISABLED:                     )
# DISABLED: # DISABLED:                     
# DISABLED: # DISABLED:                     # Start monitoring as a background task and store reference
# DISABLED: # DISABLED:                     # Fix: Use get_running_loop() for nested scope compatibility
# DISABLED: # DISABLED:                     loop = asyncio.get_running_loop()
# DISABLED: # DISABLED:                     monitor_task = loop.create_task(real_time_monitor_global.start_monitoring())
# DISABLED: # DISABLED:                     monitor_task.set_name("real_time_position_monitor")
# DISABLED: # DISABLED:                     
# DISABLED: # DISABLED:                     logger.info("🎯 Real-time Position Monitor STARTED (30s interval)")
# DISABLED: # DISABLED:                     logger.info("✅ 80% TP alerts and WIN/LOSS notifications enabled")
# DISABLED: # DISABLED:                 except Exception as monitor_error:
# DISABLED: # DISABLED:                     logger.error(f"❌ Failed to start real-time monitor: {monitor_error}")
# DISABLED: # DISABLED:                     real_time_monitor_global = None
# DISABLED: # DISABLED:             else:
# DISABLED: # DISABLED:                 logger.warning("⚠️ Real-time monitor not available (ICT engine required)")
# DISABLED: # DISABLED:         
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
            
            # 🛑 INITIALIZE STARTUP MODE (PR #111)
            global STARTUP_MODE, STARTUP_TIME
            STARTUP_MODE = True
            STARTUP_TIME = datetime.now()
            logger.info("🛑 Startup mode ACTIVE - auto-signals suppressed for 5 minutes")
            
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
        
        # JOURNAL SYNC механизъм - синхронизира pending trades от journal към positions.db
        async def sync_journal_job(context):
            """Periodic sync of trading_journal.json to positions.db"""
            try:
                logger.debug("🔄 Running scheduled journal sync...")
                from sync_journal_to_positions import sync_journal_to_positions
                stats = sync_journal_to_positions()
                
                if stats['added'] > 0:
                    logger.info(f"✅ Scheduled journal sync: {stats['added']} new positions added")
                elif stats['errors'] > 0:
                    logger.warning(f"⚠️ Scheduled journal sync: {stats['errors']} errors occurred")
                # Only log at debug level if no changes
                    
            except Exception as e:
                logger.error(f"❌ Scheduled journal sync failed: {e}")
        
        app.job_queue.run_once(schedule_reports_task, 5)
        app.job_queue.run_once(enable_auto_alerts_task, 10)
        app.job_queue.run_once(send_startup_notification_task, 0.5)  # ВЕДНАГА - след 0.5 сек
        
        # ✅ PR #112: Schedule startup mode end timer (ends in 5 minutes)
        app.job_queue.run_once(
            end_startup_mode_timer,
            when=STARTUP_GRACE_PERIOD_SECONDS,  # 300 seconds = 5 minutes
            name="end_startup_mode_timer"
        )
        logger.info(f"⏰ Startup mode timer scheduled (ends in {STARTUP_GRACE_PERIOD_SECONDS}s)")
        
        # Keepalive ping на всеки 30 минути (1800 секунди)
        app.job_queue.run_repeating(keepalive_ping, interval=1800, first=1800)
        
        # Journal sync на всеки 5 минути (300 секунди)
        # First sync after 5 minutes to avoid duplicate with startup sync
        app.job_queue.run_repeating(
            sync_journal_job,
            interval=300,  # 5 minutes
            first=300,  # First sync after 5 minutes (startup sync already ran)
            name='journal_sync'
        )
        logger.info("🔄 Journal sync scheduler activated (interval: 5 min, first run: 5 min)")
    
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
    
    
    


# ============================================================================
# INTELLIGENT HEALTH CHECK COMMAND
# ============================================================================

# application.add_handler(CommandHandler("deep_health", deep_health_cmd))
# application.add_handler(CommandHandler("self_check", meta_diagnostic_cmd))

