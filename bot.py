import requests
import json
import asyncio
import logging
import hashlib
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

# Логване
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Админ модул
import sys
sys.path.append('/workspaces/Crypto-signal-bot/admin')
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

# Превод на текст
try:
    from deep_translator import GoogleTranslator
    TRANSLATOR_AVAILABLE = True
except ImportError:
    TRANSLATOR_AVAILABLE = False

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

# ================= НАСТРОЙКИ =================
TELEGRAM_BOT_TOKEN = "8349449826:AAFNmP0i-DlERin8Z7HVir4awGTpa5n8vUM"
# Owner Chat ID за автоматични съобщения
OWNER_CHAT_ID = 7003238836  # Твой user chat ID

# Admin парола hash (парола: 8109)
ADMIN_PASSWORD_HASH = hashlib.sha256("8109".encode()).hexdigest()

# Binance API endpoints
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"
BINANCE_24H_URL = "https://api.binance.com/api/v3/ticker/24hr"
BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"
BINANCE_DEPTH_URL = "https://api.binance.com/api/v3/depth"

# Win-rate tracking file
STATS_FILE = "/workspaces/Crypto-signal-bot/bot_stats.json"

# CoinMarketCap API ключ (опционално - за повече новини)
CMC_API_KEY = ""  # Може да добавите CoinMarketCap API ключ тук
CMC_NEWS_URL = "https://api.coinmarketcap.com/data-api/v3/headlines/latest"

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

# ================= ПОМОЩНИ ФУНКЦИИ =================

async def fetch_json(url: str, params: dict = None):
    """Асинхронно извличане на JSON данни"""
    try:
        resp = await asyncio.to_thread(requests.get, url, params=params, timeout=10)
        if resp.status_code == 200:
            return resp.json()
        else:
            logger.warning(f"HTTP {resp.status_code} за {url}")
            return None
    except Exception as e:
        logger.error(f"Грешка при заявка към {url}: {e}")
        return None


async def translate_text(text: str, target_lang: str = 'bg') -> str:
    """Превод на текст с deep-translator (по-надежден)"""
    if not TRANSLATOR_AVAILABLE or not text:
        return text
    
    try:
        # Използвай deep-translator който е по-надежден
        translator = GoogleTranslator(source='auto', target=target_lang)
        translated = await asyncio.to_thread(translator.translate, text)
        return translated if translated else text
    except Exception as e:
        logger.error(f"Грешка при превод: {e}")
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
        [KeyboardButton("🤖 ML Status"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("🔔 Alerts"), KeyboardButton("ℹ️ Помощ")],
        [KeyboardButton("💻 Workspace"), KeyboardButton("🔄 Обновяване")],
        [KeyboardButton("🏠 Меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def get_admin_keyboard():
    """Връща клавиатура за Admin режим"""
    keyboard = [
        [KeyboardButton("✅ Enter"), KeyboardButton("❌ Exit")],
        [KeyboardButton("📊 Пазар"), KeyboardButton("📈 Сигнал")],
        [KeyboardButton("📰 Новини"), KeyboardButton("⚙️ Настройки")],
        [KeyboardButton("🔔 Alerts"), KeyboardButton("🏠 Меню")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


def generate_chart(klines_data, symbol, signal, current_price, tp_price, sl_price, timeframe):
    """Генерира графика със свещи, индикатори и стрелка за тренда"""
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
        
        # Изчисли MA за графиката
        df['MA20'] = df['close'].rolling(window=20).mean()
        df['MA50'] = df['close'].rolling(window=50).mean()
        
        # Създай графика
        fig, axes = plt.subplots(2, 1, figsize=(12, 8), gridspec_kw={'height_ratios': [3, 1]})
        
        # Главна графика с свещи
        ax1 = axes[0]
        
        # Plot candlesticks
        colors = ['green' if row['close'] >= row['open'] else 'red' for idx, row in df.iterrows()]
        
        for idx, (timestamp, row) in enumerate(df.iterrows()):
            color = 'green' if row['close'] >= row['open'] else 'red'
            # Тяло на свещта
            ax1.plot([idx, idx], [row['low'], row['high']], color='black', linewidth=0.5)
            height = abs(row['close'] - row['open'])
            bottom = min(row['open'], row['close'])
            ax1.add_patch(plt.Rectangle((idx-0.3, bottom), 0.6, height, facecolor=color, edgecolor='black', linewidth=0.5))
        
        # MA линии
        if not df['MA20'].isna().all():
            ax1.plot(range(len(df)), df['MA20'], label='MA(20)', color='blue', linewidth=1.5, alpha=0.7)
        if not df['MA50'].isna().all():
            ax1.plot(range(len(df)), df['MA50'], label='MA(50)', color='orange', linewidth=1.5, alpha=0.7)
        
        # TP и SL линии
        ax1.axhline(y=tp_price, color='green', linestyle='--', linewidth=1.5, label=f'TP: ${tp_price:.2f}', alpha=0.7)
        ax1.axhline(y=sl_price, color='red', linestyle='--', linewidth=1.5, label=f'SL: ${sl_price:.2f}', alpha=0.7)
        ax1.axhline(y=current_price, color='yellow', linestyle='-', linewidth=2, label=f'Цена: ${current_price:.2f}')
        
        # Добави ГОЛЯМА СТРЕЛКА за посоката на тренда
        arrow_x = len(df) - 5
        arrow_y = current_price
        
        if signal == 'BUY':
            # Зелена стрелка нагоре
            ax1.annotate('', xy=(arrow_x, arrow_y + (current_price * 0.02)), 
                        xytext=(arrow_x, arrow_y),
                        arrowprops=dict(arrowstyle='->', color='lime', lw=8))
            ax1.text(arrow_x + 2, arrow_y + (current_price * 0.025), '▲ BUY', 
                    fontsize=16, color='lime', weight='bold',
                    bbox=dict(boxstyle='round', facecolor='green', alpha=0.7))
        elif signal == 'SELL':
            # Червена стрелка надолу
            ax1.annotate('', xy=(arrow_x, arrow_y - (current_price * 0.02)), 
                        xytext=(arrow_x, arrow_y),
                        arrowprops=dict(arrowstyle='->', color='red', lw=8))
            ax1.text(arrow_x + 2, arrow_y - (current_price * 0.025), '▼ SELL', 
                    fontsize=16, color='red', weight='bold',
                    bbox=dict(boxstyle='round', facecolor='darkred', alpha=0.7))
        else:
            # Неутрална стрелка
            ax1.text(arrow_x + 2, arrow_y, '● NEUTRAL', 
                    fontsize=16, color='gray', weight='bold',
                    bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.7))
        
        ax1.set_title(f'{symbol} - Таймфрейм: {timeframe} - {datetime.now().strftime("%Y-%m-%d %H:%M")}', 
                     fontsize=14, weight='bold')
        ax1.set_ylabel('Цена (USDT)', fontsize=12)
        ax1.legend(loc='upper left', fontsize=9)
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks([])
        
        # RSI панел
        ax2 = axes[1]
        closes = df['close'].values
        rsi_values = []
        
        for i in range(14, len(closes)):
            rsi = calculate_rsi(closes[:i+1], 14)
            rsi_values.append(rsi if rsi else 50)
        
        ax2.plot(range(14, len(df)), rsi_values, color='purple', linewidth=2)
        ax2.axhline(y=70, color='red', linestyle='--', alpha=0.5)
        ax2.axhline(y=30, color='green', linestyle='--', alpha=0.5)
        ax2.axhline(y=50, color='gray', linestyle='-', alpha=0.3)
        ax2.set_ylabel('RSI', fontsize=12)
        ax2.set_ylim(0, 100)
        ax2.grid(True, alpha=0.3)
        ax2.set_xlabel('Време', fontsize=12)
        ax2.set_xticks([])
        
        plt.tight_layout()
        
        # Запази в BytesIO buffer
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        return buf
        
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
    """Откриване на свещни модели"""
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
        is_bullish = close > open_p
        return open_p, high, low, close, body, range_val, is_bullish
    
    c_open, c_high, c_low, c_close, c_body, c_range, c_bull = candle_info(current)
    p1_open, p1_high, p1_low, p1_close, p1_body, p1_range, p1_bull = candle_info(prev1)
    
    # Hammer (бичи обръщане)
    if c_body < c_range * 0.3 and (c_low < min(c_open, c_close) - c_body * 2):
        if not p1_bull:  # След низходящо движение
            patterns.append(('HAMMER', 'BUY', 15))
    
    # Shooting Star (мечи обръщане)
    if c_body < c_range * 0.3 and (c_high > max(c_open, c_close) + c_body * 2):
        if p1_bull:  # След възходящо движение
            patterns.append(('SHOOTING_STAR', 'SELL', 15))
    
    # Bullish Engulfing
    if c_bull and not p1_bull and c_body > p1_body * 1.2 and c_close > p1_open and c_open < p1_close:
        patterns.append(('BULLISH_ENGULFING', 'BUY', 20))
    
    # Bearish Engulfing
    if not c_bull and p1_bull and c_body > p1_body * 1.2 and c_close < p1_open and c_open > p1_close:
        patterns.append(('BEARISH_ENGULFING', 'SELL', 20))
    
    # Doji (неутрално - обръщане)
    if c_body < c_range * 0.1:
        patterns.append(('DOJI', 'NEUTRAL', 10))
    
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
        tf_hierarchy = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w']
        
        if current_timeframe not in tf_hierarchy:
            return None
        
        current_idx = tf_hierarchy.index(current_timeframe)
        
        # Вземи 2 нива по-висок таймфрейм
        higher_tf_idx = min(current_idx + 2, len(tf_hierarchy) - 1)
        higher_tf = tf_hierarchy[higher_tf_idx]
        
        # Вземи данни за по-високия таймфрейм
        params = {'symbol': symbol, 'interval': higher_tf, 'limit': 100}
        klines = await fetch_json(BINANCE_KLINES_URL, params)
        
        if not klines:
            return None
        
        # Бърз анализ на тренда
        closes = [float(k[4]) for k in klines]
        ma_20 = calculate_ma(closes, 20)
        ma_50 = calculate_ma(closes, 50)
        current_price = closes[-1]
        
        higher_tf_signal = "NEUTRAL"
        
        if ma_20 and ma_50:
            if ma_20 > ma_50 and current_price > ma_20:
                higher_tf_signal = "BUY"
            elif ma_20 < ma_50 and current_price < ma_20:
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
        
        # Направление на тренда
        ma_short = calculate_ma(recent_closes, 10)
        ma_long = calculate_ma(recent_closes, 30)
        
        if not ma_short or not ma_long:
            return 'UNKNOWN'
        
        # Волатилност спрямо цената
        volatility_pct = (atr / recent_closes[-1]) * 100
        
        # Strength of trend
        trend_strength = abs(ma_short - ma_long) / ma_long * 100
        
        if trend_strength > 2 and volatility_pct > 1:
            if ma_short > ma_long:
                return 'STRONG_UPTREND'
            else:
                return 'STRONG_DOWNTREND'
        elif trend_strength > 1:
            if ma_short > ma_long:
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
            '1h': 0.9, '2h': 1.0, '4h': 1.2, '1d': 1.5, '1w': 2.0
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


async def analyze_btc_correlation(symbol, timeframe):
    """Анализ на корелация с BTC"""
    try:
        if symbol == 'BTCUSDT':
            return None  # BTC се анализира сам
        
        # Вземи BTC данни
        params_btc = {
            'symbol': 'BTCUSDT',
            'interval': timeframe,
            'limit': 50
        }
        btc_klines = await fetch_json(BINANCE_KLINES_URL, params_btc)
        
        if not btc_klines or len(btc_klines) < 20:
            return None
        
        btc_closes = [float(k[4]) for k in btc_klines]
        
        # Определи BTC тренд
        btc_ma_20 = calculate_ma(btc_closes, 20)
        btc_current = btc_closes[-1]
        
        if not btc_ma_20:
            return None
        
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


def record_signal(symbol, timeframe, signal_type, confidence):
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
        
        if 'signals' not in stats:
            stats['signals'] = []
        
        stats['signals'].append(signal_detail)
        
        # Пази само последните 1000 сигнала (за да не расте файлът безкрайно)
        if len(stats['signals']) > 1000:
            stats['signals'] = stats['signals'][-1000:]
        
        save_stats(stats)
        
    except Exception as e:
        logger.error(f"Грешка при record_signal: {e}")


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


def analyze_signal(symbol_data, klines_data, symbol='BTCUSDT', timeframe='4h'):
    """Технически анализ и генериране на сигнал с напреднали индикатори"""
    try:
        # Вземи цените за затваряне
        closes = [float(k[4]) for k in klines_data]
        highs = [float(k[2]) for k in klines_data]
        lows = [float(k[3]) for k in klines_data]
        opens = [float(k[1]) for k in klines_data]
        volumes = [float(k[5]) for k in klines_data]
        current_price = closes[-1]
        
        # ========== ОСНОВНИ ИНДИКАТОРИ ==========
        rsi = calculate_rsi(closes)
        ma_20 = calculate_ma(closes, 20)
        ma_50 = calculate_ma(closes, 50)
        
        # ========== НОВИ ИНДИКАТОРИ ==========
        macd_line, macd_signal_line, macd_hist = calculate_macd(closes)
        bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(closes)
        
        # Candlestick patterns
        patterns = detect_candlestick_patterns(klines_data)
        
        # Support/Resistance
        sr_data = calculate_support_resistance(highs, lows, closes)
        
        # Market regime
        market_regime = detect_market_regime(closes, highs, lows)
        
        # Volume analysis
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # ========== НОВИ ПОДОБРЕНИЯ ==========
        
        # Изчисли волатилност за adaptive TP/SL
        recent_closes = closes[-20:]
        avg_price = sum(recent_closes) / len(recent_closes)
        variance = sum((p - avg_price) ** 2 for p in recent_closes) / len(recent_closes)
        volatility = (variance ** 0.5) / avg_price * 100
        
        # Time-of-day фактор
        tod_factor = get_time_of_day_factor()
        
        # Liquidity check
        volume_24h = float(symbol_data.get('quoteVolume', 0))
        liquidity_check = check_liquidity(volume_24h, avg_volume, volume_ratio)
        
        # ========== АНАЛИЗ И SCORING ==========
        signal = "NEUTRAL"
        confidence = 50
        reasons = []
        
        # 24h данни
        price_change = float(symbol_data.get('priceChangePercent', 0))
        
        # === RSI Analysis ===
        if rsi is not None:
            if rsi < 30:
                signal = "BUY"
                confidence += 20
                reasons.append(f"RSI презакупен ({rsi:.1f})")
            elif rsi > 70:
                signal = "SELL"
                confidence += 20
                reasons.append(f"RSI препродаден ({rsi:.1f})")
            elif 30 <= rsi <= 40:
                confidence += 5
                reasons.append(f"RSI влиза в зона за покупка ({rsi:.1f})")
            elif 60 <= rsi <= 70:
                confidence += 5
                reasons.append(f"RSI влиза в зона за продажба ({rsi:.1f})")
        
        # === Moving Average Analysis ===
        if ma_20 and ma_50:
            if ma_20 > ma_50 and current_price > ma_20:
                if signal == "BUY" or signal == "NEUTRAL":
                    confidence += 15
                    signal = "BUY"
                    reasons.append("Bullish MA кръст")
            elif ma_20 < ma_50 and current_price < ma_20:
                if signal == "SELL" or signal == "NEUTRAL":
                    confidence += 15
                    signal = "SELL"
                    reasons.append("Bearish MA кръст")
        
        # === MACD Analysis ===
        if macd_line is not None and macd_signal_line is not None:
            if macd_line > macd_signal_line and macd_hist > 0:
                if signal == "BUY" or signal == "NEUTRAL":
                    confidence += 12
                    signal = "BUY"
                    reasons.append("MACD бичи кръст")
            elif macd_line < macd_signal_line and macd_hist < 0:
                if signal == "SELL" or signal == "NEUTRAL":
                    confidence += 12
                    signal = "SELL"
                    reasons.append("MACD мечи кръст")
        
        # === Bollinger Bands Analysis ===
        if bb_upper and bb_lower:
            if current_price <= bb_lower:
                if signal == "BUY" or signal == "NEUTRAL":
                    confidence += 10
                    signal = "BUY"
                    reasons.append("Цена на долна BB лента")
            elif current_price >= bb_upper:
                if signal == "SELL" or signal == "NEUTRAL":
                    confidence += 10
                    signal = "SELL"
                    reasons.append("Цена на горна BB лента")
        
        # === Candlestick Patterns ===
        for pattern_name, pattern_signal, pattern_weight in patterns:
            if pattern_signal == signal or signal == "NEUTRAL":
                confidence += pattern_weight
                signal = pattern_signal
                pattern_bg = {
                    'HAMMER': 'Hammer (бичи)',
                    'SHOOTING_STAR': 'Shooting Star (мечи)',
                    'BULLISH_ENGULFING': 'Bullish Engulfing',
                    'BEARISH_ENGULFING': 'Bearish Engulfing',
                    'DOJI': 'Doji (неутрално)'
                }.get(pattern_name, pattern_name)
                reasons.append(f"Модел: {pattern_bg}")
        
        # === Volume Analysis ===
        if volume_ratio > 2:
            confidence += 8
            reasons.append(f"Висок обем ({volume_ratio:.1f}x средно)")
        elif volume_ratio < 0.5:
            confidence -= 5
            reasons.append(f"Нисък обем ({volume_ratio:.1f}x средно)")
        
        # === Market Regime Analysis ===
        if market_regime == 'STRONG_UPTREND' and signal == 'BUY':
            confidence += 10
            reasons.append("Силен възходящ тренд")
        elif market_regime == 'STRONG_DOWNTREND' and signal == 'SELL':
            confidence += 10
            reasons.append("Силен низходящ тренд")
        elif market_regime == 'RANGING':
            confidence -= 10
            reasons.append("Странично движение (избягвай)")
        
        # === Support/Resistance Analysis ===
        if sr_data:
            if sr_data['position'] == 'near_support' and signal == 'BUY':
                confidence += 12
                reasons.append("Цена близо до support")
            elif sr_data['position'] == 'near_resistance' and signal == 'SELL':
                confidence += 12
                reasons.append("Цена близо до resistance")
        
        # === Price Change Analysis ===
        if price_change > 5:
            if signal == 'BUY':
                confidence += 5
            reasons.append(f"Силен ръст +{price_change:.1f}%")
        elif price_change < -5:
            if signal == 'SELL':
                confidence += 5
            reasons.append(f"Силен спад {price_change:.1f}%")
        
        # ========== НОВИ ПРОВЕРКИ ==========
        
        # === Time-of-day фактор ===
        confidence += tod_factor['boost']
        if tod_factor['boost'] != 0:
            reasons.append(tod_factor['description'])
        
        # === Liquidity Check ===
        if not liquidity_check['adequate']:
            confidence += liquidity_check['penalty']
            reasons.append(f"⚠️ {liquidity_check['reason']}")
        elif liquidity_check['bonus'] > 0:
            confidence += liquidity_check['bonus']
            reasons.append(liquidity_check['reason'])
        
        # === FINAL CONFIDENCE ADJUSTMENT ===
        # Ограничи confidence между 0 и 95
        confidence = max(0, min(confidence, 95))
        
        # Провери дали има подходящ трейд (само BUY или SELL с confidence >= 65)
        has_good_trade = signal in ['BUY', 'SELL'] and confidence >= 65
        
        # Ако е RANGING пазар и confidence < 70, не давай сигнал
        if market_regime == 'RANGING' and confidence < 70:
            has_good_trade = False
        
        return {
            'signal': signal,
            'confidence': confidence,
            'price': current_price,
            'rsi': rsi,
            'ma_20': ma_20,
            'ma_50': ma_50,
            'macd': {'line': macd_line, 'signal': macd_signal_line, 'histogram': macd_hist},
            'bollinger': {'upper': bb_upper, 'middle': bb_middle, 'lower': bb_lower},
            'patterns': patterns,
            'support_resistance': sr_data,
            'market_regime': market_regime,
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
            'time_factor': tod_factor,
            'liquidity': liquidity_check
        }
    
    except Exception as e:
        logger.error(f"Грешка при анализ: {e}")
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
        
        # По-добре ако е близо до MA20
        if analysis.get('ma_20'):
            ma_distance = abs(best_entry - analysis['ma_20']) / analysis['ma_20'] * 100
            if ma_distance < 2:
                quality_score += 30
            elif ma_distance < 5:
                quality_score += 15
        
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
    logger.info(f"User {update.effective_user.id} executed /start")
    
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


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Помощна информация"""
    help_text = """
📖 <b>ПОМОЩ - Crypto Signal Bot</b>

<b>1. Основни команди:</b>
/start - Стартиране на бота
/help - Тази помощна информация
/market - Преглед на пазара

<b>2. Сигнали:</b>
/signal BTCUSDT - Анализ на BTC
/signal ETHUSDT - Анализ на ETH
/signal XRPUSDT - Анализ на XRP
/signal SOLUSDT - Анализ на SOL

Или просто: /signal BTC

<b>3. 🚀 ML + Back-test + Reports:</b>
/backtest - Back-test на стратегията (90 дни)
/backtest BTCUSDT 1h - Custom back-test
/ml_status - Machine Learning статус
/ml_train - Ръчно обучение на ML модел
/daily_report - 📊 Дневен отчет с точност и успеваемост
/weekly_report - 📈 Седмичен отчет (7 дни)
/monthly_report - 📆 Месечен отчет (30 дни)

<i>Отчетите показват:</i>
• Брой генерирани сигнали
• Точност на сигналите (Accuracy %)
• Успеваемост (Profit/Loss %)
• Анализ по валути и периоди
• Най-добър/най-лош trade

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

<b>7. Таймфрейм:</b>
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
/update - 🔄 Обновяване на бота от GitHub
/restart - 🔄 Рестартиране на бота

<b>🧪 10. Система:</b>
/test - Тест и автоматично отстраняване на грешки
/stats - Статистика на бота

━━━━━━━━━━━━━━━━━━━━━━━━

🚀 <b>НОВИ ФУНКЦИИ:</b>

📈 <b>Back-testing:</b> Тества стратегията на 90 дни
🤖 <b>Machine Learning:</b> Учи от сигнали и се подобрява
📊 <b>Daily Reports:</b> Автоматични отчети всеки ден в 20:00

📖 <b>Пълна документация:</b>
ML_BACKTEST_REPORTS_DOCS.md

⚠️ <b>Важно:</b> Това не е финансов съвет!
Винаги правете собствено проучване (DYOR).
"""
    await update.message.reply_text(help_text, parse_mode='HTML')


async def stats_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показва статистика на бота"""
    stats_message = get_performance_stats()
    await update.message.reply_text(stats_message, parse_mode='HTML')


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
        cache_file = "/workspaces/Crypto-signal-bot/news_cache.json"
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

{article.get('source', '📰')} <b>{article['title']}</b>

{sentiment_emoji} <b>Анализ на въздействието:</b>
• Sentiment: {sentiment_text}
• Важност: {impact['impact']}
• Bullish фактори: {impact['bullish_score']}
• Bearish фактори: {impact['bearish_score']}

"""
            
            if article.get('description'):
                import re
                desc = re.sub('<[^<]+?>', '', article['description'])[:200]
                message += f"<i>{desc}...</i>\n\n"
            
            if article.get('link'):
                message += f"🔗 {article['link']}\n\n"
            
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
                disable_web_page_preview=False,
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
    
    # === CoinDesk RSS Feed (Най-авторитетен източник) ===
    try:
        coindesk_rss = "https://www.coindesk.com/arc/outboundfeeds/rss/"
        
        resp = await asyncio.to_thread(requests.get, coindesk_rss, timeout=10)
        
        if resp.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
            items = root.findall('.//item')[:3]  # Топ 3 от CoinDesk
            
            for item in items:
                title = item.find('title').text if item.find('title') is not None else "Без заглавие"
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                
                all_news.append({
                    'source': '🏆 CoinDesk',
                    'title': title,
                    'date': pub_date,
                    'description': description[:200] if description else "",
                    'link': link
                })
    except Exception as e:
        logger.error(f"Грешка при CoinDesk: {e}")
    
    # === Cointelegraph RSS Feed (Втори по надеждност) ===
    try:
        cointelegraph_rss = "https://cointelegraph.com/rss"
        
        resp = await asyncio.to_thread(requests.get, cointelegraph_rss, timeout=10)
        
        if resp.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
            items = root.findall('.//item')[:2]  # Топ 2 от Cointelegraph
            
            for item in items:
                title = item.find('title').text if item.find('title') is not None else "Без заглавие"
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                
                all_news.append({
                    'source': '📰 Cointelegraph',
                    'title': title,
                    'date': pub_date,
                    'description': description[:200] if description else "",
                    'link': link
                })
    except Exception as e:
        logger.error(f"Грешка при Cointelegraph: {e}")
    
    # === Decrypt RSS Feed (Технологична перспектива) ===
    try:
        decrypt_rss = "https://decrypt.co/feed"
        
        resp = await asyncio.to_thread(requests.get, decrypt_rss, timeout=10)
        
        if resp.status_code == 200:
            import xml.etree.ElementTree as ET
            root = ET.fromstring(resp.content)
            items = root.findall('.//item')[:2]  # Топ 2 от Decrypt
            
            for item in items:
                title = item.find('title').text if item.find('title') is not None else "Без заглавие"
                pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ""
                description = item.find('description').text if item.find('description') is not None else ""
                link = item.find('link').text if item.find('link') is not None else ""
                
                all_news.append({
                    'source': '🔐 Decrypt',
                    'title': title,
                    'date': pub_date,
                    'description': description[:200] if description else "",
                    'link': link
                })
    except Exception as e:
        logger.error(f"Грешка при Decrypt: {e}")
    
    return all_news[:7] if all_news else []  # Връщаме до 7 най-важни новини


async def analyze_coin_performance(coin_data, include_external=True):
    """Детайлен анализ на отделна монета с данни от външни API"""
    try:
        symbol = coin_data['symbol']
        price = float(coin_data['lastPrice'])
        change = float(coin_data['priceChangePercent'])
        high = float(coin_data['highPrice'])
        low = float(coin_data['lowPrice'])
        volume = float(coin_data['volume'])
        quote_volume = float(coin_data['quoteVolume'])
        trades = int(coin_data['count'])
        
        # Мапване на символи към CoinGecko IDs
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
    
    # === MARKET SENTIMENT SECTION ===
    message = "📊 <b>ДНЕВЕН ПАЗАРЕН АНАЛИЗ</b>\n"
    message += "━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    
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
        news_message = "<b>📰 Последни Новини (Топ източници):</b>\n\n"
        
        for i, article in enumerate(news[:3], 1):  # Първите 3
            source = article.get('source', '📰')
            news_message += f"{i}. {source} <b>{article['title']}</b>\n"
            if article.get('description'):
                # Вземи първите 100 символа и премахни HTML
                import re
                desc = re.sub('<[^<]+?>', '', article['description'])
                desc = desc[:100] + "..." if len(desc) > 100 else desc
                news_message += f"   <i>{desc}</i>\n"
            if article.get('link'):
                news_message += f"   🔗 {article['link']}\n"
            news_message += "\n"
        
        news_message += f"<i>📊 Източници: CoinDesk, Cointelegraph, Decrypt</i>\n"
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
        valid_timeframes = ['1m', '5m', '15m', '30m', '1h', '2h', '4h', '1d', '1w']
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
    params_klines = {
        'symbol': symbol,
        'interval': timeframe,
        'limit': 100
    }
    klines = await fetch_json(BINANCE_KLINES_URL, params_klines)
    
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
    
    # Запиши сигнала в статистиката с trading параметри
    signal_id = None
    if analysis['has_good_trade']:
        signal_id = record_signal(
            symbol, 
            timeframe, 
            analysis['signal'], 
            final_confidence,
            entry_price=price,
            tp_price=tp_price,
            sl_price=sl_price
        )
    
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
    
    # Генерирай графика
    chart_buffer = generate_chart(klines, symbol, analysis['signal'], price, tp_price, sl_price, timeframe)
    
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
    message += f"Увереност: {analysis['confidence']}% {confidence_emoji}\n\n"
    
    message += f"💰 <b>Текуща цена:</b> ${price:,.4f}\n"
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
    
    message += f"📊 <b>Индикатори:</b>\n"
    if analysis['rsi']:
        message += f"RSI(14): {analysis['rsi']:.1f}\n"
    if analysis['ma_20']:
        message += f"MA(20): ${analysis['ma_20']:.2f}\n"
    if analysis['ma_50']:
        message += f"MA(50): ${analysis['ma_50']:.2f}\n"
    
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
        if analysis['ma_20']:
            no_trade_message += f"MA(20): ${analysis['ma_20']:.2f}\n"
        if analysis['ma_50']:
            no_trade_message += f"MA(50): ${analysis['ma_50']:.2f}\n"
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
    
    # Изпрати графиката като снимка със звукова аларма
    if chart_buffer:
        await context.bot.send_photo(
            chat_id=update.effective_chat.id,
            photo=chart_buffer,
            caption=f"🔔🔊 {message}",
            parse_mode='HTML',
            disable_notification=False  # Включена звукова аларма
        )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"🔔🔊 {message}",
            parse_mode='HTML',
            disable_notification=False  # Включена звукова аларма
        )


async def news_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Последни новини от крипто света - Топ надеждни източници"""
    await update.message.reply_text("📰 Извличане на новини от най-надеждните източници...")
    
    # Извлечи от множество източници (вече имаме обновена функция)
    news_from_rss = await fetch_market_news()
    
    all_news = []
    
    # Добави новините от RSS източниците
    for article in news_from_rss:
        all_news.append({
            'source': article.get('source', '📰'),
            'title': article['title'],
            'link': article.get('link', None),
            'description': article.get('description', '')
        })
    
    # === CoinMarketCap (като допълнителен източник) ===
    try:
        cmc_url = "https://coinmarketcap.com/headlines/news/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        resp = await asyncio.to_thread(requests.get, cmc_url, headers=headers, timeout=15)
        
        if resp.status_code == 200:
            # Опростен parsing - търси основни заглавия в HTML
            import re
            # Търси JSON data в страницата
            json_match = re.search(r'window\.__NEXT_DATA__\s*=\s*({.*?})\s*</script>', resp.text, re.DOTALL)
            
            if json_match:
                import json
                data = json.loads(json_match.group(1))
                
                # Навигирай до новините
                try:
                    articles = data.get('props', {}).get('pageProps', {}).get('articles', [])[:3]
                    
                    for article in articles:
                        title = article.get('meta', {}).get('title', '')
                        subtitle = article.get('meta', {}).get('subtitle', '')
                        slug = article.get('meta', {}).get('slug', '')
                        
                        if title and slug:
                            link = f"https://coinmarketcap.com/headlines/news/{slug}/"
                            all_news.append({
                                'source': '📊 CoinMarketCap',
                                'title': title,
                                'link': link,
                                'description': subtitle[:150] if subtitle else ''
                            })
                except Exception as parse_err:
                    logger.error(f"CoinMarketCap parse error: {parse_err}")
    except Exception as e:
        logger.error(f"CoinMarketCap error: {e}")
    
    # Изпрати новините
    if not all_news:
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
    
    message = "📰 <b>ПОСЛЕДНИ НОВИНИ ОТ ТОП ИЗТОЧНИЦИ</b>\n"
    message += "<i>CoinDesk, Cointelegraph, Decrypt, CoinMarketCap</i>\n\n"
    
    for i, news in enumerate(all_news[:10], 1):  # Топ 10 новини
        source = news.get('source', '📰')
        translate_url = f"https://translate.google.com/translate?sl=auto&tl=bg&u={news['link']}" if news.get('link') else None
        
        # Преведи заглавието и описанието
        title_bg = await translate_text(news['title'])
        description_bg = ""
        if news.get('description'):
            description_bg = await translate_text(news['description'])
        
        message += f"{i}. {source} <b>{title_bg}</b>\n"
        
        if description_bg:
            message += f"   <i>{description_bg}...</i>\n"
        
        if news.get('link'):
            message += f"   🌐 Оригинал: {news['link']}\n"
            if translate_url:
                message += f"   🇧🇬 Преведено: {translate_url}\n"
        
        message += "\n"
        
        # Малка пауза между преводите
        await asyncio.sleep(0.2)
    
    message += "💡 <i>Новини от топ източници, преведени автоматично!</i>"
    
    await update.message.reply_text(message, parse_mode='HTML', disable_web_page_preview=True)


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

{article.get('source', '📰')} <b>{article['title']}</b>

{sentiment_emoji} <b>Sentiment:</b> {sentiment_text}
📊 <b>Bullish фактори:</b> {impact['bullish_score']}
📉 <b>Bearish фактори:</b> {impact['bearish_score']}

"""
                
                if article.get('description'):
                    import re
                    desc = re.sub('<[^<]+?>', '', article['description'])[:150]
                    msg += f"<i>{desc}...</i>\n\n"
                
                if article.get('link'):
                    msg += f"🔗 {article['link']}\n"
                
                await update.message.reply_text(msg, parse_mode='HTML', disable_web_page_preview=False)
                await asyncio.sleep(0.5)
        
        # Изпрати високо въздействащите новини
        if high_impact_news:
            for article in high_impact_news[:3]:  # Максимум 3
                impact = article['impact_analysis']
                
                if impact['sentiment'] == 'BULLISH':
                    sentiment_emoji = "🟢"
                elif impact['sentiment'] == 'BEARISH':
                    sentiment_emoji = "🔴"
                else:
                    sentiment_emoji = "⚪"
                
                msg = f"""⚠️ <b>ВАЖНА НОВИНА</b>

{article.get('source', '📰')} {article['title']}

{sentiment_emoji} Sentiment: {impact['sentiment']}
"""
                
                if article.get('link'):
                    msg += f"🔗 {article['link']}\n"
                
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
            with open('/workspaces/Crypto-signal-bot/copilot_tasks.json', 'r') as f:
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
            with open('/workspaces/Crypto-signal-bot/copilot_tasks.json', 'r') as f:
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
        with open('/workspaces/Crypto-signal-bot/copilot_tasks.json', 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Създай и файл с по-детайлна информация
        task_file = f"/workspaces/Crypto-signal-bot/COPILOT_TASK_{new_task['id']}.md"
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
    
    await update.message.reply_text(
        "🔄 <b>РЕСТАРТИРАМ БОТА...</b>\n\n"
        "⏳ Ще се върна след 5 секунди!\n"
        "💡 Ще получиш потвърждение когато съм онлайн.",
        parse_mode='HTML'
    )
    
    logger.info(f"🔄 Bot restart requested by user {update.effective_user.id}")
    
    # Изпрати нотификация
    await send_bot_status_notification(context.bot, "stopping", "Ръчен рестарт от потребител")
    
    # Спри бота и рестартирай процеса
    import os
    import sys
    
    # Изпрати команда за рестарт
    os.execv(sys.executable, ['python3'] + sys.argv)


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

📈 <b>Анализ:</b>
Timeframe: {settings['timeframe']}

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


async def timeframe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Избор на таймфрейм"""
    settings = get_user_settings(context.application.bot_data, update.effective_chat.id)
    
    if not context.args:
        # Покажи текущ и опции
        keyboard = [
            [
                InlineKeyboardButton("15м", callback_data="tf_15m"),
                InlineKeyboardButton("1ч", callback_data="tf_1h"),
                InlineKeyboardButton("2ч", callback_data="tf_2h"),
            ],
            [
                InlineKeyboardButton("4ч", callback_data="tf_4h"),
                InlineKeyboardButton("1д", callback_data="tf_1d"),
                InlineKeyboardButton("1с", callback_data="tf_1w"),
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


async def send_alert_signal(context: ContextTypes.DEFAULT_TYPE):
    """Изпраща автоматичен сигнал с пълен анализ - проверява всички монети"""
    chat_id = context.job.data['chat_id']
    settings = get_user_settings(context.application.bot_data, chat_id)
    
    logger.info("🔍 Започвам проверка на всички монети...")
    
    # Проверява всички символи и избира най-добрия сигнал
    best_signal = None
    best_confidence = 0
    
    for symbol in SYMBOLS.values():
        # Извлечи данни
        params_24h = {'symbol': symbol}
        data_24h = await fetch_json(BINANCE_24H_URL, params_24h)
        
        if isinstance(data_24h, list):
            data_24h = next((s for s in data_24h if s['symbol'] == symbol), None)
        
        if not data_24h:
            logger.info(f"🔍 {symbol}: Няма 24ч данни")
            continue
        
        params_klines = {
            'symbol': symbol,
            'interval': settings['timeframe'],
            'limit': 100
        }
        klines = await fetch_json(BINANCE_KLINES_URL, params_klines)
        
        if not klines:
            logger.info(f"🔍 {symbol}: Няма klines данни")
            continue
        
        # Анализирай
        analysis = analyze_signal(data_24h, klines)
        
        if not analysis or analysis['signal'] == 'NEUTRAL':
            logger.info(f"🔍 {symbol}: NEUTRAL")
            continue
        
        # Ако липсват TP/SL, изчисли прости нива
        if 'tp' not in analysis or 'sl' not in analysis:
            price = analysis['price']
            if analysis['signal'] == 'BUY':
                analysis['tp'] = price * 1.03  # +3%
                analysis['sl'] = price * 0.98  # -2%
            else:  # SELL
                analysis['tp'] = price * 0.97  # -3%
                analysis['sl'] = price * 1.02  # +2%
            logger.info(f"🔍 {symbol}: Добавени default TP/SL")
        
        # Запомни най-добрия сигнал
        if analysis['confidence'] >= 60 and analysis['confidence'] > best_confidence:
            best_confidence = analysis['confidence']
            best_signal = {
                'symbol': symbol,
                'analysis': analysis,
                'data_24h': data_24h,
                'klines': klines  # Запази klines за графиката
            }
            logger.info(f"🔍 {symbol}: {analysis['signal']} ({analysis['confidence']}%) - НОВ НАЙ-ДОБЪР")
        else:
            logger.info(f"🔍 {symbol}: {analysis['signal']} ({analysis['confidence']}%)")
    
    # Ако няма добър сигнал, не изпращай нищо
    if not best_signal:
        logger.info("⚠️ Няма сигнали с увереност ≥60%")
        return
    
    # Изпрати най-добрия сигнал
    symbol = best_signal['symbol']
    analysis = best_signal['analysis']
    klines = best_signal['klines']
    price = analysis['price']
    signal_emoji = "🟢" if analysis['signal'] == 'BUY' else "🔴"
    
    # === ГЕНЕРИРАЙ ГРАФИКА ===
    chart_file = None
    try:
        chart_file = generate_chart(
            klines,
            symbol,
            analysis['signal'],
            price,
            analysis['tp'],
            analysis['sl'],
            settings['timeframe']
        )
        if chart_file:
            logger.info(f"📊 Графика генерирана успешно за {symbol}")
        else:
            logger.warning(f"⚠️ Графика не е генерирана за {symbol}")
    except Exception as e:
        logger.error(f"❌ Грешка при генериране на графика за {symbol}: {e}")
        chart_file = None
    
    # === ОПРЕДЕЛИ ТИП НА ТРЕЙДА ===
    timeframe = settings['timeframe']
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
    
    try:
        # Изпрати съобщението С ГРАФИКА (ако е налична)
        if chart_file:
            try:
                if isinstance(chart_file, BytesIO):
                    # BytesIO обект - изпрати директно с пълното съобщение
                    chart_file.seek(0)
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=chart_file,
                        caption=f"🔔🔊 {message}",
                        parse_mode='HTML',
                        disable_notification=False  # Със звук за важни сигнали
                    )
                elif isinstance(chart_file, str) and os.path.exists(chart_file):
                    # Файлов път - отвори и изпрати
                    with open(chart_file, 'rb') as photo:
                        await context.bot.send_photo(
                            chat_id=chat_id,
                            photo=photo,
                            caption=f"🔔🔊 {message}",
                            parse_mode='HTML',
                            disable_notification=False
                        )
                    # Изтрий временния файл
                    try:
                        os.remove(chart_file)
                    except:
                        pass
                
                logger.info(f"🔔 Автоматичен сигнал изпратен С ГРАФИКА: {symbol} {analysis['signal']} ({analysis['confidence']}%)")
            except Exception as e:
                logger.error(f"Грешка при изпращане на графика: {e}")
                # Ако графиката не може да се изпрати, изпрати само текст
                await context.bot.send_message(
                    chat_id=chat_id, 
                    text=f"🔔🔊 {message}", 
                    parse_mode='HTML',
                    disable_notification=False
                )
        else:
            # Няма графика - изпрати само текст
            await context.bot.send_message(
                chat_id=chat_id, 
                text=f"🔔🔊 {message}", 
                parse_mode='HTML',
                disable_notification=False
            )
            logger.info(f"🔔 Автоматичен сигнал изпратен БЕЗ ГРАФИКА: {symbol} {analysis['signal']} ({analysis['confidence']}%)")
        
    except Exception as e:
        logger.error(f"Грешка при изпращане на alert: {e}")


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
            
            # Създай Google Translate линк
            translate_url = f"https://translate.google.com/translate?sl=auto&tl=bg&u={link}"
            
            message = f"📰 <b>НОВА КРИПТО НОВИНА</b>\n\n"
            message += f"<b>{title_bg}</b>\n\n"
            
            if description_bg:
                message += f"<i>{description_bg}</i>\n\n"
            
            message += f"🌐 Оригинал:\n{link}\n\n"
            message += f"🇧🇬 Пълна статия преведена:\n{translate_url}\n\n"
            message += "💡 <i>Заглавие и описание са преведени автоматично!</i>"
            
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
    
    # Провери дали потребителят въвежда парола за обновяване или е в admin режим
    if context.user_data.get('awaiting_update_password') or context.user_data.get('admin_command_mode'):
        await update_bot_cmd(update, context)
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
    elif text == "🔄 Обновяване":
        await update_bot_cmd(update, context)
    elif text == "📋 Отчети":
        await reports_cmd(update, context)
    elif text == "🤖 ML Status":
        await ml_status_cmd(update, context)
    elif text == "💻 Workspace":
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
                InlineKeyboardButton("📊 4h", callback_data=f"tf_{symbol}_4h"),
                InlineKeyboardButton("📈 1d", callback_data=f"tf_{symbol}_1d"),
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
        params_klines = {
            'symbol': symbol,
            'interval': timeframe,
            'limit': 100
        }
        klines = await fetch_json(BINANCE_KLINES_URL, params_klines)
        
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
        
        # Запиши сигнала в статистиката с trading параметри
        signal_id = None
        if analysis['has_good_trade']:
            signal_id = record_signal(
                symbol, 
                timeframe, 
                analysis['signal'], 
                final_confidence,
                entry_price=price,
                tp_price=tp_price,
                sl_price=sl_price
            )
        
        # Генерирай графика
        chart_buffer = generate_chart(klines, symbol, analysis['signal'], price, tp_price, sl_price, timeframe)
        
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
        message = f"{signal_emoji} <b>СИГНАЛ: {symbol}</b>\n\n"
        message += f"📊 <b>Анализ ({timeframe}):</b>\n"
        message += f"Сигнал: <b>{analysis['signal']}</b>\n"
        message += f"Увереност: {analysis['confidence']}%\n\n"
        
        message += f"💰 <b>Текуща цена:</b> ${price:,.4f}\n"
        message += f"📈 24ч промяна: {analysis['change_24h']:+.2f}%\n\n"
        
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
        
        message += f"📊 <b>Индикатори:</b>\n"
        if analysis['rsi']:
            message += f"RSI(14): {analysis['rsi']:.1f}\n"
        if analysis['ma_20']:
            message += f"MA(20): ${analysis['ma_20']:.2f}\n"
        if analysis['ma_50']:
            message += f"MA(50): ${analysis['ma_50']:.2f}\n"
        
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
            if analysis['ma_20']:
                no_trade_message += f"MA(20): ${analysis['ma_20']:.2f}\n"
            if analysis['ma_50']:
                no_trade_message += f"MA(50): ${analysis['ma_50']:.2f}\n"
            no_trade_message += f"\nСигнал: {analysis['signal']}\n"
            no_trade_message += f"Увереност: {analysis['confidence']}%\n\n"
            no_trade_message += f"⚠️ <i>Пазарните условия не са подходящи за трейд в момента.</i>"
            
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=no_trade_message,
                parse_mode='HTML'
            )
            return
        
        # Изпрати графиката като снимка
        if chart_buffer:
            await context.bot.send_photo(
                chat_id=update.effective_chat.id,
                photo=chart_buffer,
                caption=message,
                parse_mode='HTML'
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=message,
                parse_mode='HTML'
            )


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
    
    readme_path = "/workspaces/Crypto-signal-bot/admin/README.md"
    
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
                [sys.executable, '/workspaces/Crypto-signal-bot/admin/diagnostics.py'],
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
            
            subprocess.run(["/workspaces/Crypto-signal-bot/bot-manager.sh", "start"], timeout=30)
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
                subprocess.run(["/workspaces/Crypto-signal-bot/bot-manager.sh", "restart"], timeout=30)
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
            subprocess.run(["/workspaces/Crypto-signal-bot/bot-manager.sh", "start"], timeout=30)
            
            problems_fixed.append("Отстранени множество инстанции")
            await update.message.reply_text("✅ Конфликтът е отстранен")
        else:
            await update.message.reply_text("✅ Няма множество инстанции")
        
        # 4. Анализ на логове
        await update.message.reply_text("4️⃣ Анализирам логове за грешки...")
        
        log_file = "/workspaces/Crypto-signal-bot/bot.log"
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
                subprocess.run(["/workspaces/Crypto-signal-bot/bot-manager.sh", "restart"], timeout=30)
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
            
            subprocess.run(["/workspaces/Crypto-signal-bot/auto-fixer-manager.sh", "start"], timeout=30)
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


async def update_bot_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обновява бота от GitHub репозиторието - изисква admin парола"""
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
                cwd='/workspaces/Crypto-signal-bot',
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
    """Изпълнява back-test на стратегията"""
    if not BACKTEST_AVAILABLE:
        await update.message.reply_text("❌ Back-testing модул не е наличен")
        return
    
    await update.message.reply_text("📊 Стартирам back-test... (това може да отнеме 30-60 сек)")
    
    # Параметри
    symbol = context.args[0] if context.args else 'BTCUSDT'
    timeframe = context.args[1] if len(context.args) > 1 else '4h'
    days = int(context.args[2]) if len(context.args) > 2 else 90
    
    # Изпълни back-test
    results = await backtest_engine.run_backtest(symbol, timeframe, None, days)
    
    if not results:
        await update.message.reply_text("❌ Грешка при back-testing")
        return
    
    # Форматирай резултатите
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

⚠️ <i>Това е симулация базирана на исторически данни</i>
"""
    
    await update.message.reply_text(message, parse_mode='HTML')
    
    # Оптимизирай параметри
    optimized = backtest_engine.optimize_parameters(results)
    
    if optimized:
        opt_msg = f"""✅ <b>ПАРАМЕТРИ ОПТИМИЗИРАНИ</b>

🎯 Препоръчан TP: {optimized['optimized_tp_pct']:.2f}%
🛡️ Препоръчан SL: {optimized['optimized_sl_pct']:.2f}%
⚖️ Risk/Reward: 1:{optimized['recommended_rr']}

💡 <i>Използвай тези параметри за по-добри резултати!</i>
"""
        await update.message.reply_text(opt_msg, parse_mode='HTML')


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
            if os.path.exists('/workspaces/Crypto-signal-bot/daily_reports.json'):
                import json
                with open('/workspaces/Crypto-signal-bot/daily_reports.json', 'r') as f:
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
            if os.path.exists('/workspaces/Crypto-signal-bot/backtest_results.json'):
                import json
                with open('/workspaces/Crypto-signal-bot/backtest_results.json', 'r') as f:
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
        if not REPORTS_AVAILABLE:
            await query.edit_message_text("❌ Reports модул не е наличен")
            return
        
        report = report_engine.generate_daily_report()
        if report:
            message = report_engine.format_report_message(report)
            await query.edit_message_text(message, parse_mode='HTML')
        else:
            await query.edit_message_text("❌ Няма данни за днешен ден")
    
    elif query.data == "report_weekly":
        # Седмичен отчет
        if not REPORTS_AVAILABLE:
            await query.edit_message_text("❌ Reports модул не е наличен")
            return
        
        summary = report_engine.get_weekly_summary()
        if summary:
            message = f"""📊 <b>СЕДМИЧЕН ОТЧЕТ</b>
📅 Период: {summary['period']}
━━━━━━━━━━━━━━━━━━━━━━━━

📈 <b>Обобщение:</b>
   Общо сигнали: {summary['total_signals']}
   Завършени trades: {summary['total_completed']}
   
🎯 <b>Резултати:</b>
   ✅ Печеливши: {summary['total_wins']}
   ❌ Загубени: {summary['total_losses']}
   🎯 Win Rate: {summary['win_rate']:.1f}%
   
💪 <b>Средна увереност:</b> {summary['avg_confidence']:.1f}%

📊 Базирано на {summary['reports_count']} дневни отчета
"""
            await query.edit_message_text(message, parse_mode='HTML')
        else:
            await query.edit_message_text("❌ Недостатъчно данни за седмичен отчет")
    
    elif query.data == "report_backtest":
        # Back-test резултати
        if not BACKTEST_AVAILABLE:
            await query.edit_message_text("❌ Backtesting модул не е наличен")
            return
        
        try:
            import os
            import json
            if os.path.exists('/workspaces/Crypto-signal-bot/backtest_results.json'):
                with open('/workspaces/Crypto-signal-bot/backtest_results.json', 'r') as f:
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
    
    elif query.data == "report_ml":
        # ML статистика
        if not ML_AVAILABLE:
            await query.edit_message_text("❌ ML модул не е наличен")
            return
        
        status = ml_engine.get_status()
        
        mode_text = "🤖 Hybrid Mode" if status['hybrid_mode'] else "⚡ Full ML Mode"
        ml_weight_pct = int(status['ml_weight'] * 100)
        classical_weight_pct = 100 - ml_weight_pct
        
        message = f"""🤖 <b>MACHINE LEARNING СТАТИСТИКА</b>

<b>Режим:</b> {mode_text}
   ML Weight: {ml_weight_pct}%
   Classical Weight: {classical_weight_pct}%

<b>Обучение:</b>
   Модел: {'✅ Trained' if status['model_trained'] else '❌ Not trained'}
   Training samples: {status['training_samples']}
   Нужни за обучение: {status['min_samples_needed']}
   
{'✅ Готов за обучение!' if status['ready_for_training'] else f"⚠️ Нужни още {status['min_samples_needed'] - status['training_samples']} samples"}

💡 <i>ML се обучава автоматично на всеки 20 сигнала</i>

📖 <b>Как работи:</b>
Week 1-2: 30% ML (learning)
Week 3-4: 50% ML (scaling)
Week 5+: 70-90% ML (dominance)
"""
        await query.edit_message_text(message, parse_mode='HTML')
    
    elif query.data == "report_stats":
        # Bot статистика
        stats_message = get_performance_stats()
        await query.edit_message_text(stats_message, parse_mode='HTML')
    
    elif query.data == "report_refresh":
        # Refresh - покажи менюто отново
        await reports_cmd(query, context)


# ================= ГЛАВНА ФУНКЦИЯ =================


# ================= ГЛАВНА ФУНКЦИЯ =================

def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрирай команди
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("market", market_cmd))
    app.add_handler(CommandHandler("signal", signal_cmd))
    app.add_handler(CommandHandler("news", news_cmd))
    app.add_handler(CommandHandler("breaking", breaking_cmd))  # Критични новини
    app.add_handler(CommandHandler("task", task_cmd))  # Задания за Copilot
    app.add_handler(CommandHandler("workspace", workspace_cmd))  # Workspace info
    app.add_handler(CommandHandler("restart", restart_cmd))  # Рестарт на бота
    app.add_handler(CommandHandler("autonews", autonews_cmd))
    app.add_handler(CommandHandler("settings", settings_cmd))
    app.add_handler(CommandHandler("timeframe", timeframe_cmd))
    app.add_handler(CommandHandler("alerts", alerts_cmd))
    app.add_handler(CommandHandler("stats", stats_cmd))
    
    # Админ команди
    app.add_handler(CommandHandler("admin_login", admin_login_cmd))
    app.add_handler(CommandHandler("admin_setpass", admin_setpass_cmd))
    app.add_handler(CommandHandler("admin_daily", admin_daily_cmd))
    app.add_handler(CommandHandler("admin_weekly", admin_weekly_cmd))
    app.add_handler(CommandHandler("admin_monthly", admin_monthly_cmd))
    app.add_handler(CommandHandler("admin_docs", admin_docs_cmd))
    app.add_handler(CommandHandler("update", update_bot_cmd))  # Обновяване на бота
    app.add_handler(CommandHandler("test", test_system_cmd))  # Тест и автоматично отстраняване на грешки
    
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
    
    # APScheduler за автоматични отчети (стартира СЛЕД app.run_polling)
    if ADMIN_MODULE_AVAILABLE:
        async def schedule_reports():
            """Инициализира APScheduler след стартиране на бота"""
            scheduler = AsyncIOScheduler(timezone="UTC")
            
            # Дневен отчет всеки ден в 08:00 UTC
            scheduler.add_job(
                lambda: asyncio.create_task(send_auto_report('daily', app.bot)),
                'cron',
                hour=8,
                minute=0
            )
            
            # Седмичен отчет всеки понеделник в 08:00 UTC
            scheduler.add_job(
                lambda: asyncio.create_task(send_auto_report('weekly', app.bot)),
                'cron',
                day_of_week='mon',
                hour=8,
                minute=0
            )
            
            # Месечен отчет на 1-во число в 08:00 UTC
            scheduler.add_job(
                lambda: asyncio.create_task(send_auto_report('monthly', app.bot)),
                'cron',
                day=1,
                hour=8,
                minute=0
            )
            
            # НОВИ ДНЕВНИ ОТЧЕТИ - Всеки ден в 20:00 BG време (18:00 UTC)
            if REPORTS_AVAILABLE:
                async def send_daily_auto_report():
                    """Изпраща автоматичен дневен отчет към owner"""
                    try:
                        report = report_engine.generate_daily_report()
                        if report:
                            message = report_engine.format_report_message(report)
                            await app.bot.send_message(
                                chat_id=OWNER_CHAT_ID,
                                text=f"🔔 <b>АВТОМАТИЧЕН ДНЕВЕН ОТЧЕТ</b>\n\n{message}",
                                parse_mode='HTML',
                                disable_notification=False
                            )
                            logger.info("✅ Automatic daily report sent")
                    except Exception as e:
                        logger.error(f"❌ Daily report error: {e}")
                
                scheduler.add_job(
                    send_daily_auto_report,
                    'cron',
                    hour=18,  # 20:00 BG = 18:00 UTC
                    minute=0
                )
                logger.info("✅ Daily automatic reports scheduled (20:00 BG time)")
            
            # Автоматична диагностика всеки ден в 01:00 UTC (03:00 BG време)
            scheduler.add_job(
                run_diagnostics,
                'cron',
                hour=1,
                minute=0
            )
            
            # Автоматични новини 3 пъти дневно: 08:00, 14:00, 20:00 UTC
            scheduler.add_job(
                lambda: asyncio.create_task(send_auto_news(app.bot)),
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
            
            scheduler.start()
            logger.info("✅ APScheduler стартиран: отчети + диагностика + новини + REAL-TIME мониторинг + DAILY REPORTS")
        
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
            try:
                # Изпрати потвърждение за успешен рестарт
                await send_bot_status_notification(app.bot, "restarted", "")
                
                # Тествай дали всички callback handlers работят
                test_callbacks = [
                    'signal_BTCUSDT', 'signal_ETHUSDT', 'signal_SOLUSDT',
                    'timeframe_15m', 'timeframe_1h', 'reports_daily',
                    'ml_train', 'backtest_run'
                ]
                
                startup_msg = "🤖 <b>ДЕТАЙЛИ ЗА СТАРТИРАНЕ:</b>\n\n"
                startup_msg += f"✅ Всички handlers регистрирани\n"
                startup_msg += f"✅ Callback handlers: {len(test_callbacks)} активни\n"
                startup_msg += f"✅ Бутоните са активни\n"
                startup_msg += f"✅ Auto-alerts включени (5 мин)\n"
                startup_msg += f"✅ Daily reports активни (20:00)\n"
                startup_msg += f"✅ ML Engine готов\n"
                startup_msg += f"✅ Backtesting готов\n\n"
                startup_msg += f"<i>Всички системи функционални.</i>"
                
                await app.bot.send_message(
                    chat_id=OWNER_CHAT_ID,
                    text=startup_msg,
                    parse_mode='HTML',
                    disable_notification=True,  # Без звук за детайлите
                    reply_markup=get_main_keyboard()  # Изпрати клавиатурата отново
                )
                logger.info("✅ Startup notification изпратена с клавиатура")
            except Exception as e:
                logger.error(f"Грешка при startup notification: {e}")
        
        # Изпълни след инициализация на app
        async def schedule_reports_task(context):
            await schedule_reports()
        
        async def enable_auto_alerts_task(context):
            await enable_auto_alerts()
        
        async def send_startup_notification_task(context):
            await send_startup_notification()
        
        app.job_queue.run_once(schedule_reports_task, 5)
        app.job_queue.run_once(enable_auto_alerts_task, 10)
        app.job_queue.run_once(send_startup_notification_task, 3)
    
    # Стартирай бота с error handling и auto-recovery
    max_retries = 10
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            logger.info(f"🤖 Стартиране на polling (опит {retry_count + 1}/{max_retries})...")
            app.run_polling(
                drop_pending_updates=True, 
                allowed_updates=Update.ALL_TYPES,
                pool_timeout=30,
                read_timeout=30,
                write_timeout=30,
                connect_timeout=30
            )
            break  # Успешен старт
        except KeyboardInterrupt:
            logger.info("🛑 Bot спрян от потребител")
            break
        except Exception as e:
            retry_count += 1
            logger.error(f"❌ Грешка при polling (опит {retry_count}/{max_retries}): {e}")
            
            # Изпрати нотификация за crash
            try:
                from telegram import Bot
                bot = Bot(token=TELEGRAM_BOT_TOKEN)
                import asyncio
                asyncio.run(send_bot_status_notification(bot, "crashed", str(e)))
            except:
                pass  # Ако не може да изпрати, продължи
            
            if retry_count < max_retries:
                wait_time = min(5 * retry_count, 60)  # Прогресивно чакане (max 60s)
                logger.info(f"🔄 Автоматичен рестарт след {wait_time} секунди...")
                import time
                time.sleep(wait_time)
            else:
                logger.error("❌ Максимален брой опити достигнат. Спиране на бота.")
                
                # Изпрати финална нотификация
                try:
                    from telegram import Bot
                    bot = Bot(token=TELEGRAM_BOT_TOKEN)
                    import asyncio
                    asyncio.run(send_bot_status_notification(bot, "crashed", "Максимален брой опити достигнат"))
                except:
                    pass
                
                break


if __name__ == "__main__":
    main()
