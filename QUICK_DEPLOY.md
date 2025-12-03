# 🚀 QUICK DEPLOYMENT GUIDE

## Когато трябва да deploy-неш нова версия:

### ⚡ ВАРИАНТ 1: Telegram (Най-бърз)
```
/deploy
```

---

### 🔧 ВАРИАНТ 2: SSH - Една команда
```bash
ssh root@YOUR_SERVER_IP "cd /root/Crypto-signal-bot && git pull origin main && pip install -r requirements.txt && systemctl restart crypto-bot"
```

---

### 📋 ВАРИАНТ 3: SSH - Стъпка по стъпка

**Влез в сървъра:**
```bash
ssh root@YOUR_SERVER_IP
```

**Изпълни deployment:**
```bash
cd /root/Crypto-signal-bot
./manual_deploy.sh
```

**Или ръчно:**
```bash
cd /root/Crypto-signal-bot
git pull origin main
pip install -r requirements.txt
systemctl restart crypto-bot
```

---

## 🔍 ПРОВЕРКИ СЛЕД DEPLOYMENT

### Провери дали бота работи:
```bash
systemctl status crypto-bot
```

### Виж логовете:
```bash
journalctl -u crypto-bot -f
```

### Или само последните 50 реда:
```bash
journalctl -u crypto-bot -n 50
```

---

## 📲 TELEGRAM КОМАНДИ СЛЕД DEPLOYMENT

### Тествай новите функции:
```
/start          - Рестарт на интерфейса
/refresh        - Обнови бутоните (нова команда!)
/ml_status      - ML система статус
/alerts         - Auto-alerts статус
/journal        - Trading Journal
/stats          - Статистика
```

---

## ❌ АКО НЕЩО НЕ РАБОТИ

### GitHub Actions не deploy-ва:
1. Провери: https://github.com/galinborisov10-art/Crypto-signal-bot/actions
2. Виж логовете на failed workflow
3. Провери GitHub Secrets

### Бутоните не са активни:
```
/start
```
или
```
/refresh
```

### Бота не стартира:
```bash
systemctl status crypto-bot
journalctl -u crypto-bot -n 100
```

---

## 🔐 SSH INFO

**Ако забравиш IP адреса:**
- Digital Ocean Dashboard → Droplets → Виж IP
- Или провери GitHub Secrets → DO_HOST

**Ако забравиш SSH key:**
- Използвай ключа от GitHub Secrets → DO_SSH_KEY
- Или личния си SSH ключ

---

## 📊 НОВАТА ВЕРСИЯ v2.5.0 ВКЛЮЧВА:

✅ Async паралелен анализ (6x по-бързо)
✅ Memory cleanup (няма leak)
✅ Rate limiting (няма API грешки)
✅ Watchdog 120s timeout (няма чести рестарти)
✅ /refresh команда (fix за бутони)
✅ Auto cleanup при startup
✅ Графики 16x16 (по-големи)
✅ Премахнати MA/MACD (само leading indicators)
✅ /explain команда (ICT термини)
✅ 3 timeframes auto-alerts (1h, 4h, 1d)

---

## 🎯 ПЪРВИ СТЪПКИ СЛЕД DEPLOYMENT

1. `/start` - Рестарт на интерфейса
2. `/refresh` - Тест на новата команда
3. `/ml_status` - Провери ML
4. `/alerts` - Провери auto-alerts
5. Натисни "🔄 Обновяване" бутона

---

**Запази този файл за бърза справка!**

Version: 2.5.0
Date: 3 Dec 2025
