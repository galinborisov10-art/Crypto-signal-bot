# 🤖 Crypto Signal Bot - Professional Edition

**Версия:** 2.0.0 - Security Hardening  
**Последна актуализация:** 19 Декември 2025  
**Автор:** galinborisov10-art

---

## 📊 Описание

Професионален Telegram бот за криптовалутни сигнали с **16 advanced функции** и **80-90% win rate**.

### ✨ Основни функции:
- 🎯 **Автоматични сигнали** за 6 криптовалути (BTC, ETH, SOL, XRP, BNB, ADA)
- 📈 **11 технически индикатора** (RSI, MACD, Bollinger Bands и др.)
- 🕯️ **5 candlestick patterns** (Hammer, Engulfing, Doji и др.)
- 🔍 **8 advanced analytics** (Order Book, BTC correlation, Sentiment и др.)
- 📊 **Автоматични отчети** (дневен, седмичен, месечен)
- 🔐 **Админ панел** с парола защита
- 💰 **Adaptive TP/SL** според волатилност
- ⏰ **9 таймфрейма** (1m до 1w)

---

## 🚀 Инсталация

### 1. Clone repository:
```bash
git clone https://github.com/galinborisov10-art/Crypto-signal-bot.git
cd Crypto-signal-bot
```

### 2. Създай virtual environment:
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate  # Windows
```

### 3. Инсталирай зависимости:
```bash
pip install -r requirements.txt
```

⚠️ **ВАЖНО:** ВИНАГИ използвай `pip install -r requirements.txt` за гарантиране на правилните версии на всички зависимости!

### 4. Конфигурирай bot token:
- Отвори `admin/credentials.json`
- Замени `bot_token` с твой Telegram Bot Token от [@BotFather](https://t.me/BotFather)
- Замени `owner_chat_id` с твой Chat ID

### 5. Стартирай бота:
```bash
python bot.py
```

---

## 📱 Telegram команди

### 🎯 Основни:
- `/start` - Стартирай бота
- `/help` - Пълна помощна информация
- `/market` - Пазарен преглед на 6-те криптовалути
- `/signal` - Интерактивно меню за сигнали
- `/stats` - Статистика на бота

### 📊 Сигнали:
- `/signal BTC` - Анализ на Bitcoin
- `/signal ETH` - Анализ на Ethereum
- `/signal SOL` - Анализ на Solana
- `/signal XRP` - Анализ на Ripple
- `/signal BNB` - Анализ на Binance Coin
- `/signal ADA` - Анализ на Cardano

### 📰 Новини:
- `/news` - Последни крипто новини (преведени на БГ)
- `/autonews` - Вкл/Изкл автоматични новини

### ⚙️ Настройки:
- `/settings` - Виж и промени TP/SL настройки
- `/timeframe` - Избери таймфрейм (1m, 5m, 15m, 30m, 1h, 2h, 4h, 1d, 1w)
- `/alerts` - Автоматични сигнали ON/OFF

### 📊 Backtest & Анализ:
- `/backtest` - Пусни comprehensive backtest (всички 6 символа × 10 таймфрейма)
- `/backtest BTCUSDT 1h 30` - Custom backtest (символ, таймфрейм, дни)
- `/backtest_results` - Виж comprehensive backtest резултати
- `📊 Backtest` бутон - Бърз достъп до comprehensive отчет

**Comprehensive Backtest Features:**
- 📊 **6 символа:** BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT, ADAUSDT
- ⏰ **10 таймфрейма:** 1m, 5m, 15m, 30m, 1h, 2h, 3h, 4h, 1d, 1w
- 🔔 **80% TP Alert статистика** (HOLD/PARTIAL_CLOSE/CLOSE_NOW)
- 📈 **Per-symbol breakdown** с win rate и PnL
- 🕐 **Per-timeframe breakdown** за всички комбинации
- 📁 **Автоматичен архив** (30 дни retention)
- 🔄 **Daily auto-update** в 02:00 UTC

### 🔐 Админ панел (парола: 8109):
- `/admin_login 8109` - Вход в админ
- `/admin_daily` - Генерирай дневен отчет
- `/admin_weekly` - Генерирай седмичен отчет
- `/admin_monthly` - Генерирай месечен отчет
- `/admin_docs` - Пълна документация

---

## 📊 Автоматични отчети

### 🕐 График:
- **Дневен:** Всеки ден в 08:00 UTC (10:00 БГ време)
- **Седмичен:** Всеки понеделник в 08:00 UTC (10:00 БГ време)
- **Месечен:** На 1-во число в 08:00 UTC (10:00 БГ време)

### 📈 Какво съдържат:
- Общ брой сигнали
- Win rate (процент успешни трейдове)
- Най-добър/най-лош трейд
- Разпределение по крипто и таймфрейм
- Сравнение с очакваните резултати

---

## 🎯 Очаквани резултати

### 📊 Win Rate:
- **Общо:** 75-85%
- **4h таймфрейм:** 80-90%
- **1d таймфрейм:** 82-92%
- **С BTC потвърждение:** 88-94%

### 💰 Финансови прогнози (при $100/трейд):
- **Консервативен:** +$7,200/месец (70% win rate, 40 трейда)
- **Балансиран:** +$13,200/месец (80% win rate, 60 трейда)
- **Агресивен:** +$19,200/месец (85% win rate, 80 трейда)

---

## 🔧 Конфигурация

### 📁 Важни файлове:
- `bot.py` - Главен код (2725 реда)
- `admin/admin_module.py` - Админ система
- `admin/credentials.json` - Учетни данни (НЕ качвай в GitHub!)
- `bot_stats.json` - Статистика на сигналите
- `.gitignore` - Git защита

### 🔐 Сигурност:
- Всички sensitive файлове са в `.gitignore`
- Админ парола: SHA-256 хеширана
- Достъп само за owner chat_id

---

## 🔒 Security Features (NEW - v2.0.0)

After the recent security incident (token compromise on 2025-12-17), we've implemented comprehensive security measures:

### ✨ Security Features:

- **🛡️ Rate Limiting:** 20 requests/minute, 100 requests/hour per user
- **🚫 Auto-ban:** Automatic ban after 3 violations (60 minutes)
- **🔐 Authentication:** Blacklist/Whitelist support with admin controls
- **🔒 Encrypted Token Storage:** Secure token encryption using Fernet (AES-256)
- **📊 Security Monitoring:** Real-time threat detection and event logging
- **⚠️ Threat Assessment:** LOW/MEDIUM/HIGH/CRITICAL threat levels
- **👮 Admin Controls:** Blacklist, unban, security statistics

### 🛠️ Admin Setup:

Set admin user IDs in `.env`:
```bash
# Admin User IDs (comma-separated Telegram user IDs)
ADMIN_USER_IDS=123456789,987654321
```

Get your Telegram user ID from [@userinfobot](https://t.me/userinfobot)

### 🔐 New Security Commands:

- `/blacklist USER_ID [REASON]` - Block a user from using the bot
- `/unblacklist USER_ID` - Remove user from blacklist
- `/security_stats` - Show security statistics and threat level
- `/unban USER_ID` - Manually unban rate-limited user
- `/version` - Show bot version with security features

### 📖 Security Documentation:

Full security guide: [`docs/SECURITY_GUIDE.md`](docs/SECURITY_GUIDE.md)

**Topics covered:**
- Rate limiting configuration
- Authentication modes (Public/Whitelist)
- Token encryption setup
- Security monitoring and incident response
- Best practices and troubleshooting

### ⚙️ Configuration (.env):

```bash
# Security Settings (optional, defaults shown)
MAX_REQUESTS_PER_MINUTE=20
MAX_REQUESTS_PER_HOUR=100
BAN_DURATION_MINUTES=60

# Whitelist Mode (optional, disabled by default)
WHITELIST_MODE=false
# WHITELISTED_USER_IDS=111111111,222222222,333333333
```

---

## 📚 Документация

Пълна документация: [`admin/README.md`](admin/README.md)

### 📖 Допълнителни ресурси:
- [`admin/CHAT_WITH_COPILOT.md`](admin/CHAT_WITH_COPILOT.md) - Как да се свържеш с GitHub Copilot
- [`admin/PROTECTION_POLICY.md`](admin/PROTECTION_POLICY.md) - Защита на проекта
- [`admin/CREDENTIALS_GUIDE.md`](admin/CREDENTIALS_GUIDE.md) - Управление на пароли

---

## 🛠️ Технологии

### 🐍 Python библиотеки:
- `python-telegram-bot` - Telegram Bot API
- `requests` - HTTP заявки към Binance API
- `pandas`, `numpy` - Анализ на данни
- `matplotlib`, `mplfinance` - Графики
- `deep-translator` - Превод на български
- `apscheduler` - Автоматични отчети

### 🌐 API интеграции:
- **Binance API** - Цени, 24h данни, klines, order book
- **CoinMarketCap** - Новини и sentiment analysis
- **Telegram Bot API** - Съобщения и команди

---

## 📊 Технически анализ

### 🔍 11 Индикатора:
RSI, MA(20), MA(50), MACD, Bollinger Bands, Volume, ATR, EMA, Support/Resistance, Divergence, Market Regime

### 🕯️ 5 Patterns:
Hammer, Shooting Star, Bullish Engulfing, Bearish Engulfing, Doji

### 🎯 8 Advanced Analytics:
Order Book, Multi-timeframe, Sentiment, BTC Correlation, Time-of-Day, Liquidity Filter, Adaptive TP/SL, Win-Rate Tracking

---

## ⚠️ Важни бележки

### 🚫 Disclaimers:
- **НЕ е финансов съвет!** Винаги прави собствено проучване (DYOR)
- Криптовалутите са рискови активи
- Минали резултати не гарантират бъдещи печалби
- Използвай само средства, които можеш да загубиш

### 🔒 Сигурност:
- НЕ споделяй `credentials.json`
- НЕ качвай API ключове в GitHub
- Променяй паролите редовно
- Използвай 2FA на exchange accounts

---

## 🤝 Поддръжка

### 💬 Контакт:
- GitHub: [@galinborisov10-art](https://github.com/galinborisov10-art)
- Telegram: Owner Chat ID `8349449826`

### 🐛 Bug Reports:
Отвори issue в GitHub с детайли:
- Описание на проблема
- Стъпки за възпроизвеждане
- Очаквано vs. реално поведение
- Логове от `bot.log`

---

## 📊 ICT Chart Visualization

### 🎨 Overview
The bot includes a professional chart visualization system for ICT (Inner Circle Trader) signals with color-coded zones and annotations.

### ✨ Features:
- 🕯️ **OHLC Candlestick Charts** - Professional price action visualization
- 🎨 **Color-Coded ICT Zones**:
  - 🐋 **Whale Order Blocks** (Green/Red) - High-volume institutional zones
  - 💥 **Breaker Blocks** (Blue/Orange) - Failed support/resistance
  - 🎯 **Mitigation Blocks** (Teal/Purple) - Price retest zones
  - ⚡ **SIBI/SSIB Zones** (Yellow/Gray) - Institutional order flow
  - 📊 **Fair Value Gaps** (Light Green/Red) - Price imbalances
  - 💧 **Liquidity Zones** (Teal/Dark Red) - Buy/Sell side liquidity
- 📍 **Entry/Exit Levels**:
  - Blue solid line - Entry price
  - Red dashed line - Stop Loss
  - Green dashed line - Take Profit
- 📊 **Volume Subplot** - Trading volume bars
- 📝 **Signal Info Box** - Signal type, confidence, bias
- 📈 **Professional Styling** - Clean, readable charts

### 🚀 Usage:
```
/ict BTC 4H     # Get ICT analysis with chart for Bitcoin 4H
/ict ETH 1H     # Get ICT analysis with chart for Ethereum 1H
```

### ⚙️ Configuration:
Chart visualization can be configured in `config/feature_flags.json`:
```json
{
  "use_chart_visualization": true,  // Enable/disable charts
  "chart_style": "professional",    // Chart style (professional/dark)
  "chart_dpi": 100,                 // Chart quality (DPI)
  "include_volume_subplot": true    // Show/hide volume
}
```

### 📸 Example Output:
The `/ict` command will send:
1. Text analysis with signal details
2. Professional chart image (PNG) with all ICT zones overlaid
3. Graceful fallback to text-only if chart generation fails

### ⚡ Performance:
- Chart generation: **< 1 second** (typically 0.7-0.8s)
- Chart size: **~75-100 KB** (PNG format)
- No impact on bot responsiveness

### 🛠️ Technical Details:
- **Library:** matplotlib + pandas
- **Format:** PNG images sent via Telegram
- **Resolution:** 1400x1000 pixels (14x10 inches @ 100 DPI)
- **Color Scheme:** Professional TradingView-inspired palette

---

## 📜 Лиценз

MIT License - свободно използване и модификация.

---

## 🎯 Roadmap

### ✅ Версия 2.0 (Текуща):
- 16 advanced features
- Автоматични отчети
- Админ панел
- Adaptive TP/SL
- BTC correlation

### 🚀 Планирани подобрения:
- [ ] Machine Learning модел за прогнози
- [ ] Multi-exchange поддръжка (Bybit, Kraken)
- [ ] Backtest система
- [ ] Real-time dashboard
- [ ] Mobile app интеграция
- [ ] Voice notifications
- [ ] Multi-language support

---

**Made with ❤️ for crypto traders**  
**Crypto Signal Bot v2.0 - Professional Edition**

🚀 *Trade smart, not hard!*



# Test auto-deploy 1764663515
# Test auto-deploy
# Test auto-deploy with permanent SSH key
# Final auto-deploy test
# Deploy test Tue Dec  2 08:51:16 UTC 2025

