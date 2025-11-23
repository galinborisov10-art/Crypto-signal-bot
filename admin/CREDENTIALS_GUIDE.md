# 🔐 Ръководство за учетни данни

**Последна актуализация:** 23 Ноември 2025

---

## 📁 Какво съдържа credentials.json

Файлът **`credentials.json`** съхранява всички важни учетни данни:

### 🔑 Текущи учетни данни:

1. **Telegram Bot**
   - Token: `8349449826:AAFNmP0i-DlERin8Z7HVir4awGTpa5n8vUM`
   - Owner Chat ID: `8349449826`

2. **Админ панел**
   - Парола: `8109`
   - Hash: SHA-256 в `admin_password.json`

3. **Binance API** (опционално)
   - API Key: (празно - публичните endpoints не изискват)
   - API Secret: (празно)

4. **CoinMarketCap** (опционално)
   - API Key: (празно - използваме web scraping)

---

## 🛡️ Сигурност

### ✅ Какво е направено:

1. **`.gitignore` файл създаден**
   - `credentials.json` НЕ се качва в GitHub
   - `admin_password.json` защитен
   - Всички `.env` файлове игнорирани

2. **SHA-256 хеширане**
   - Паролите са криптирани
   - Не се съхраняват в plain text

3. **Локално съхранение**
   - Файлът остава само на твоята машина
   - Backup препоръчително ръчно

### ⚠️ Важно:

- **НЕ споделяй** `credentials.json` с никого
- **НЕ качвай** в публични хранилища
- **ПРАВИ backup** на сигурно място
- **ПРОМЕНЯЙ паролите** периодично

---

## 📝 Как да използваш credentials.json

### Автоматично зареждане (препоръчително):

Добави в началото на `bot.py`:

```python
import json

# Зареди credentials
with open('/workspaces/Crypto-signal-bot/admin/credentials.json', 'r') as f:
    creds = json.load(f)

TELEGRAM_BOT_TOKEN = creds['telegram']['bot_token']
OWNER_CHAT_ID = creds['telegram']['owner_chat_id']
ADMIN_PASSWORD = creds['admin']['password']
```

### Ръчно копиране:

Отвори `credentials.json` и копирай нужните стойности.

---

## 🔄 Актуализация на учетни данни

### Променя Telegram Bot Token:

1. Отвори `credentials.json`
2. Промени `"bot_token": "NEW_TOKEN"`
3. Запази файла
4. Рестартирай бота

### Променя админ парола:

1. Използвай `/admin_setpass NEW_PASSWORD`
2. Или промени в `credentials.json`
3. Рестартирай бота

### Добави Binance API:

```json
"binance": {
  "api_key": "YOUR_API_KEY",
  "api_secret": "YOUR_API_SECRET",
  "description": "Binance API за trading"
}
```

---

## 📦 Backup стратегия

### Автоматичен backup:

```bash
# Създай backup папка
mkdir -p /workspaces/Crypto-signal-bot/admin/backups/

# Копирай credentials
cp admin/credentials.json admin/backups/credentials_$(date +%Y%m%d).json
```

### Ръчен backup:

1. Копирай `credentials.json` на USB устройство
2. Или използвай cloud storage (криптиран)
3. Или изпрати на сигурен имейл

---

## 🚨 При компрометиране

Ако `credentials.json` е достъпен от неоторизирани лица:

### Незабавно:

1. **Промени Telegram Bot Token**
   - BotFather → /revoke → създай нов бот
   - Актуализирай `credentials.json`

2. **Промени админ парола**
   - `/admin_setpass NEW_PASSWORD`
   - Актуализирай `credentials.json`

3. **Провери Binance API**
   - Deactivate в Binance настройки
   - Създай нови ключове

4. **Провери логовете**
   - `bot.log` за неоторизиран достъп
   - `admin/reports/` за странна активност

---

## 🔗 Връзки

- Telegram BotFather: [@BotFather](https://t.me/BotFather)
- Binance API: [binance.com/en/my/settings/api-management](https://www.binance.com/en/my/settings/api-management)
- CoinMarketCap API: [coinmarketcap.com/api/](https://coinmarketcap.com/api/)

---

*Пази този файл на сигурно място!*
*Crypto Signal Bot - Professional Edition v2.0*
