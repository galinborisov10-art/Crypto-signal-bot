# 🚀 DEPLOY ИНСТРУКЦИИ - Railway.app (Безплатно 24/7)

## ✅ Защо Railway.app?

- ✅ **$5 безплатен кредит месечно**
- ✅ **500 часа работа месечно** (достатъчно за 24/7)
- ✅ **Автоматичен restart** при грешки
- ✅ **GitHub интеграция** - auto-deploy при commit
- ✅ **Без sleep mode** (за разлика от Heroku/Render)
- ✅ **Persistent storage** за JSON файлове

---

## 📋 СТЪПКА 1: Подготовка (ГОТОВО ✅)

Всички необходими файлове са създадени:

- ✅ `Procfile` - Worker definition
- ✅ `runtime.txt` - Python версия
- ✅ `railway.json` - Railway конфигурация
- ✅ `nixpacks.toml` - Build система
- ✅ `requirements.txt` - Python dependencies
- ✅ `start.sh` - Startup script
- ✅ `.gitignore` - Игнорира временни файлове

---

## 🚀 СТЪПКА 2: Deploy на Railway.app

### Вариант А: Web UI (Препоръчително - 2 минути)

1. **Отвори:** https://railway.app/
2. **Login с GitHub**
3. **New Project** → **Deploy from GitHub repo**
4. **Избери:** `galinborisov10-art/Crypto-signal-bot`
5. **Deploy Now**

Railway автоматично:
- Открива `railway.json` конфигурацията
- Инсталира dependencies от `requirements.txt`
- Стартира `python3 bot.py`
- Рестартира при грешки (до 10 пъти)

### Вариант Б: Railway CLI

```bash
# 1. Инсталирай Railway CLI
npm i -g @railway/cli

# 2. Login
railway login

# 3. Link repo
railway link

# 4. Deploy
railway up
```

---

## ⚙️ СТЪПКА 3: Environment Variables (Опционално)

Ако искаш да скриеш API keys от кода:

1. В Railway Dashboard → **Variables**
2. Добави:
   ```
   TELEGRAM_BOT_TOKEN=YOUR_TELEGRAM_BOT_TOKEN_HERE
   OWNER_CHAT_ID=7003238836
   ```

Тогава в `bot.py` промени:
```python
import os
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
OWNER_CHAT_ID = int(os.getenv('OWNER_CHAT_ID'))
```

---

## 📊 СТЪПКА 4: Мониторинг

### Railway Dashboard показва:

- ✅ **Deployment Status** - Running/Building/Crashed
- ✅ **Logs** - Real-time лог streaming
- ✅ **Metrics** - CPU, Memory, Network usage
- ✅ **Build Time** - Време за deploy
- ✅ **Restarts** - Брой рестартирания

### Telegram Notifications:

Ботът автоматично изпраща:
- ✅ Auto-alerts на всеки 5 минути
- ✅ Daily reports в 20:00 BG time
- ✅ Breaking news alerts
- ✅ ML training updates

Ако спреш да получаваш съобщения → проверк Railway logs!

---

## 🔧 СТЪПКА 5: Auto-Deploy Setup

### GitHub Integration (Препоръчително):

Railway автоматично:
1. Следи за commits в `main` branch
2. Auto-deploy при push
3. Rollback при грешка

### Как работи:

```bash
# Правиш промени локално
git add .
git commit -m "Update bot features"
git push origin main

# Railway автоматично:
# 1. Detect push
# 2. Build new version
# 3. Deploy без downtime
# 4. Rollback ако има грешка
```

---

## 💾 СТЪПКА 6: Persistent Storage

Railway предоставя persistent disk за JSON файлове:

### Автоматично се запазват:

- ✅ `bot_stats.json` - Статистика на бота
- ✅ `daily_reports.json` - Дневни отчети
- ✅ `backtest_results.json` - Back-test резултати
- ✅ `ml_training_data.json` - ML training samples
- ✅ `ml_model.pkl` - Trained ML модел
- ✅ `ml_scaler.pkl` - Feature scaler

### Важно:

Railway автоматично монтира volume за `/workspaces/Crypto-signal-bot/`
Файловете са persistent между deploys!

---

## 🔄 СТЪПКА 7: Restart Policies

### Автоматичен Restart:

Railway конфигурацията включва:
```json
"restartPolicyType": "ON_FAILURE",
"restartPolicyMaxRetries": 10
```

Това означава:
- ✅ Рестарт при crash
- ✅ До 10 опита
- ✅ Експоненциален backoff
- ✅ Health check преди declare success

### Ръчен Restart:

В Railway Dashboard:
1. **Settings** → **Restart**
2. Или използвай CLI: `railway restart`

---

## 📈 СТЪПКА 8: Scaling (Ако е нужно)

### Безплатен Plan Limits:

- ✅ 500 часа/месец (достатъчно за 24/7 един bot)
- ✅ 512MB RAM
- ✅ 1GB Storage
- ✅ Unlimited bandwidth

### Upgrade ($5/месец):

- 🚀 Unlimited hours
- 🚀 8GB RAM
- 🚀 100GB Storage
- 🚀 Priority support

---

## 🐛 Troubleshooting

### Проблем: Bot не стартира

**Решение:**
```bash
# Провери logs в Railway
railway logs

# Или в Dashboard → Deployments → View Logs
```

### Проблем: Dependencies error

**Решение:**
```bash
# Обнови requirements.txt
pip freeze > requirements.txt
git add requirements.txt
git commit -m "Update dependencies"
git push
```

### Проблем: Bot crash loop

**Решение:**
1. Провери Railway logs за грешката
2. Fix кода локално
3. Push промените
4. Railway auto-deploys

---

## 📱 Push Notifications Setup

За да получаваш alerts при deploy:

1. Railway → **Settings** → **Integrations**
2. Connect **Telegram** or **Discord**
3. Railway ще изпраща:
   - ✅ Deploy started
   - ✅ Deploy successful
   - ✅ Deploy failed
   - ✅ Service crashed

---

## 🎯 ГОТОВ СИ!

След deploy на Railway:

✅ Ботът работи 24/7
✅ Auto-restart при грешки
✅ Auto-deploy при Git push
✅ Persistent data storage
✅ Free 500 hours/month
✅ No sleep mode

### Проверка:

1. Отвори Telegram
2. Изпрати `/start` на бота
3. Провери дали получаваш auto-alerts
4. Тествай `/reports`

### Мониторинг:

- Railway Dashboard: https://railway.app/dashboard
- Bot Logs: Railway → Deployments → Logs
- Telegram: Auto-alerts на всеки 5 мин

---

## 🚀 АЛТЕРНАТИВИ (ако Railway не работи)

### Render.com (Безплатен):
- ✅ 750 часа/месец
- ❌ Sleep след 15 мин неактивност
- Използвай: `render.yaml` (вече подготвен)

### Fly.io (Безплатен):
- ✅ 3 shared VMs безплатно
- ✅ 160GB bandwidth
- Използвай: `fly.toml` (вече подготвен)

### Heroku (Ограничен):
- ❌ Премахнаха free tier
- Нужна кредитна карта за $5/месец

---

## 📞 Support

Ако имаш проблеми:

1. **Railway Support:** https://railway.app/help
2. **Discord:** https://discord.gg/railway
3. **Docs:** https://docs.railway.app/

---

**🎉 ГОТОВО! Ботът ще работи 24/7 безплатно!** 🎉
