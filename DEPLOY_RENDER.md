# 🚀 Render.com Deployment Guide

## 🆓 НАПЪЛНО БЕЗПЛАТНО (750h месечно)

### ✅ Предимства на Render.com:
- ✅ **750 часа FREE месечно** (повече от Railway)
- ✅ **БЕЗ кредитна карта**
- ✅ **Auto-deploy от GitHub**
- ✅ **Persistent storage**
- ✅ **Auto-restart при crash**
- ✅ **Лесно setup** (като Railway)

---

## 📋 Deployment Стъпки

### **1️⃣ Отвори Render.com**
```
https://render.com/
```

### **2️⃣ Login с GitHub**
- Натисни **"Get Started for Free"**
- Избери **"GitHub"**
- Authorize Render да достъпва твоя GitHub
- ✅ БЕЗ кредитна карта!

### **3️⃣ Създай нов Web Service**
1. От Dashboard → **"New +"** → **"Web Service"**
2. Избери **"Build and deploy from a Git repository"**
3. Свържи GitHub акаунта (ако не е свързан)
4. Търси и избери: **`Crypto-signal-bot`**

### **4️⃣ Конфигурация (AUTO)**
Render автоматично разпознава `render.yaml`:

```yaml
✅ Name: crypto-signal-bot
✅ Region: Frankfurt (най-близо до България)
✅ Branch: main
✅ Runtime: Python 3.12
✅ Build Command: pip install -r requirements.txt
✅ Start Command: python3 bot.py
✅ Plan: Free
```

**Натисни "Next"**

### **5️⃣ Environment Variables**
⚠️ **ВАЖНО:** Добави тези променливи:

1. Натисни **"Advanced"** → **"Add Environment Variable"**

2. Добави:
   ```
   TELEGRAM_BOT_TOKEN = 8349449826:AAFNmP0i-DlERin8Z7HVir4awGTpa5n8vUM
   ```

3. Добави:
   ```
   OWNER_CHAT_ID = 7003238836
   ```

4. Добави (optional):
   ```
   PYTHON_VERSION = 3.12.0
   ```

### **6️⃣ Deploy**
- Натисни **"Create Web Service"**
- Изчакай 2-3 минути
- ✅ Готово!

---

## 🎉 Резултат

### **Автоматично получаваш:**
- 🌐 **Public URL:** `https://crypto-signal-bot.onrender.com`
- 📊 **Real-time logs** в Dashboard
- 🔄 **Auto-restart** при crash (unlimited)
- 📦 **Persistent storage** за JSON файлове
- 🔔 **Telegram notification** при startup
- ⚡ **24/7 работа** (750h free месечно = ~31 дни)

---

## 📊 Мониторинг

### **Render Dashboard:**
1. Logs → Real-time логове
2. Metrics → CPU, Memory usage
3. Events → Deploy history

### **Telegram:**
- Получаваш startup notification
- Auto-alerts на всеки 5 минути
- Бутоните работят ВИНАГИ

---

## 🆚 Render vs Railway

| Функция | Render.com | Railway.app |
|---------|------------|-------------|
| **Free часове** | 750h/месец | 500h/месец |
| **Кредитна карта** | ❌ НЕ | ❌ НЕ |
| **Auto-deploy** | ✅ ДА | ✅ ДА |
| **Persistent storage** | ✅ FREE | ✅ FREE |
| **Sleep mode** | ❌ НЯМА | ❌ НЯМА |
| **Auto-restart** | ✅ Unlimited | ✅ 10 retries |
| **Region** | 🇪🇺 Frankfurt | 🇺🇸 US West |

**Render.com е по-добър за България!** 🇧🇬

---

## 🔧 Troubleshooting

### **Проблем 1: Bot не стартира**
✅ Провери Logs → търси грешки
✅ Провери Environment Variables
✅ Рестартирай: Settings → Manual Deploy → Deploy Latest

### **Проблем 2: Бутоните не работят**
✅ Ботът автоматично изпраща startup notification
✅ Проверка в Logs: "🔄 BOT RESTARTED"

### **Проблем 3: Free часове изтичат**
750h = 31.25 дни = целия месец!
Ако изтекат → чакаш следващия месец (auto-reset)

---

## 🚀 Auto-Deploy от GitHub

### **Как работи:**
1. Правиш промени в кода
2. Push to GitHub: `git push origin main`
3. Render автоматично deploy-ва новата версия
4. Бот рестартира с новия код
5. Telegram notification потвърждава

**Никакви ръчни действия не са нужни!**

---

## 📱 Следващи Стъпки

### **Веднага след deploy:**
1. ✅ Провери Render Logs за "Application started"
2. ✅ Провери Telegram за "🔄 BOT RESTARTED"
3. ✅ Тествай бутоните (/signal, /market, etc.)
4. ✅ Провери auto-alerts (на всеки 5 мин)

### **За production:**
- ✅ Ботът работи 24/7
- ✅ Бутоните винаги функционират
- ✅ Auto-recovery при crash
- ✅ **НАПЪЛНО БЕЗПЛАТНО!**

---

## 🎯 Заключение

**Render.com е идеалното безплатно решение за този бот!**

✅ Повече free часове от Railway
✅ БЕЗ кредитна карта
✅ По-близък сървър (Frankfurt vs US)
✅ Лесно setup (2-3 минути)
✅ Auto-deploy от GitHub

**Готов за deploy? Отиди на https://render.com/ сега!** 🚀
