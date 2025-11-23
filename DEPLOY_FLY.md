# 🚀 Fly.io Deployment Guide - Crypto Signal Bot

## 🎯 ЗАЩО FLY.IO?

✅ **100% БЕЗПЛАТНО** - 3 free VM-та forever  
✅ **БЕЗ ИМЕЙЛ ПРОБЛЕМИ** - Login само с GitHub  
✅ **160GB трафик/месец** - Повече от достатъчно  
✅ **Amsterdam сървър** - Близо до България (по-бърз)  
✅ **Persistent Storage** - JSON файловете се запазват  
✅ **Auto-restart** - Автоматично рестартиране при грешка  

---

## 📋 ПРЕДВАРИТЕЛНИ ИЗИСКВАНИЯ

1. **GitHub акаунт** ✅ (вече имаш)
2. **Git repository** ✅ (Crypto-signal-bot)
3. **Telegram Bot Token** ✅ (вече имаш)

---

## 🚀 DEPLOYMENT СТЪПКИ (Много лесно!)

### 1️⃣ **Инсталирай Fly CLI**

**Windows (PowerShell):**
```powershell
iwr https://fly.io/install.ps1 -useb | iex
```

**Mac/Linux:**
```bash
curl -L https://fly.io/install.sh | sh
```

**Проверка:**
```bash
flyctl version
```

---

### 2️⃣ **Login с GitHub**

```bash
flyctl auth login
```

- Ще се отвори браузър
- Избери **"Sign in with GitHub"**
- Authorize Fly.io
- ✅ Готово! БЕЗ имейл потвърждение!

---

### 3️⃣ **DeployBot на Fly.io**

**В терминала (от Codespace):**

```bash
cd /workspaces/Crypto-signal-bot
flyctl launch
```

**Отговори на въпросите:**
- App Name: `crypto-signal-bot-<твоето_име>` (уникално име)
- Region: **Amsterdam (ams)** ✅
- Setup PostgreSQL? → **NO**
- Setup Redis? → **NO**
- Deploy now? → **NO** (първо добавяме secrets)

---

### 4️⃣ **Добави Environment Variables (Secrets)**

```bash
flyctl secrets set TELEGRAM_BOT_TOKEN="8349449826:AAFNmP0i-DlERin8Z7HVir4awGTpa5n8vUM"
flyctl secrets set OWNER_CHAT_ID="7003238836"
```

**Проверка:**
```bash
flyctl secrets list
```

---

### 5️⃣ **Deploy Бота!**

```bash
flyctl deploy
```

**Това прави:**
1. Build Docker image
2. Push към Fly.io
3. Deploy в Amsterdam
4. Start bot автоматично

⏱️ **Време:** 2-3 минути

---

### 6️⃣ **Провери Статус**

```bash
flyctl status
```

**Очаквам:**
```
NAME                  STATUS   CHECKS  RESTARTS  CREATED
crypto-signal-bot-v1  running  1 total 0         1m ago
```

✅ **Ботът е LIVE!**

---

## 📊 УПРАВЛЕНИЕ НА БОТА

### Виж Logs (Real-time):
```bash
flyctl logs
```

### Restart Bot:
```bash
flyctl apps restart crypto-signal-bot
```

### SSH в машината:
```bash
flyctl ssh console
```

### Scaling (ако трябва повече resources):
```bash
flyctl scale count 1
flyctl scale vm shared-cpu-1x
```

### Спри бота (temporary):
```bash
flyctl scale count 0
```

### Пусни го отново:
```bash
flyctl scale count 1
```

---

## 🔧 AUTO-DEPLOY ОТ GITHUB

### Setup GitHub Actions (Auto-deploy при push):

1. **Генерирай Fly API Token:**
```bash
flyctl auth token
```

2. **Добави в GitHub Secrets:**
- Отвори: https://github.com/galinborisov10-art/Crypto-signal-bot/settings/secrets/actions
- New repository secret
- Name: `FLY_API_TOKEN`
- Value: `<token от стъпка 1>`

3. **Създай `.github/workflows/fly.yml`:**
```yaml
name: Deploy to Fly.io

on:
  push:
    branches:
      - main

jobs:
  deploy:
    name: Deploy app
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: superfly/flyctl-actions/setup-flyctl@master
      - run: flyctl deploy --remote-only
        env:
          FLY_API_TOKEN: ${{ secrets.FLY_API_TOKEN }}
```

Сега всеки `git push` автоматично deploy-ва бота! 🚀

---

## 💾 PERSISTENT STORAGE

Ботът използва **Fly Volume** за persistent storage:

```bash
flyctl volumes create crypto_bot_data --region ams --size 1
```

**JSON файловете се запазват тук:**
- `/data/bot_stats.json`
- `/data/copilot_tasks.json`
- `/data/ml_model.pkl`

---

## 🆘 TROUBLESHOOTING

### Ботът не работи?

**1. Виж логове:**
```bash
flyctl logs
```

**2. Провери secrets:**
```bash
flyctl secrets list
```

**3. Restart:**
```bash
flyctl apps restart crypto-signal-bot
```

**4. SSH debug:**
```bash
flyctl ssh console
cd /app
python3 bot.py
```

---

### Health check не минава?

**Провери health endpoint:**
```bash
curl https://crypto-signal-bot.fly.dev/health
```

Очаквам: `OK`

---

### Достигнах free tier лимита?

**Провери usage:**
```bash
flyctl status
```

**Free tier включва:**
- 3 VM-та (shared-cpu-1x, 256MB RAM)
- 3GB persistent storage
- 160GB outbound traffic/месец

За този бот е **повече от достатъчно!** ✅

---

## 📈 МОНИТОРИНГ

### Fly Dashboard:
https://fly.io/dashboard

Тук виждаш:
- CPU usage
- Memory usage
- Network traffic
- Crash reports
- Health checks

---

## 🔐 SECURITY

### Secrets Management:
- ✅ **НЕ** commit-вай secrets в GitHub
- ✅ Използвай `flyctl secrets set`
- ✅ Secrets се криптират в Fly.io

### Update Secrets:
```bash
flyctl secrets set TELEGRAM_BOT_TOKEN="<нов_токен>"
```

Ботът автоматично рестартира с новите secrets.

---

## 💰 РАЗХОДИ

**FREE TIER (ЗАВИНАГИ):**
- 3 shared-cpu-1x VMs (256MB RAM)
- 3GB persistent storage
- 160GB transfer/месец

**За този бот = $0.00/месец** ✅

---

## 📝 ПОЛЕЗНИ КОМАНДИ

```bash
# Status
flyctl status

# Logs (real-time)
flyctl logs

# Restart
flyctl apps restart crypto-signal-bot

# SSH
flyctl ssh console

# Secrets
flyctl secrets list
flyctl secrets set KEY="VALUE"

# Deploy
flyctl deploy

# Scale
flyctl scale count 1
flyctl scale vm shared-cpu-1x

# Regions
flyctl regions list
flyctl regions add ams

# Dashboard
flyctl dashboard
```

---

## 🎉 ГОТОВО!

Сега ботът работи **24/7** на Fly.io:

✅ БЕЗ имейл проблеми  
✅ БЕЗ Codespace 30-min timeout  
✅ БЕЗ sleep mode  
✅ БЕЗ payment след free tier  
✅ Auto-restart при crash  
✅ Persistent storage  
✅ Amsterdam сървър (бърз)  

---

## 🔗 ЛИНКОВЕ

- **Fly.io Dashboard:** https://fly.io/dashboard
- **Fly.io Docs:** https://fly.io/docs
- **GitHub Repo:** https://github.com/galinborisov10-art/Crypto-signal-bot
- **Support:** https://community.fly.io

---

## 📞 НУЖДАЕШ СЕ ОТ ПОМОЩ?

Използвай `/task` в Telegram за да създадеш задача за Copilot!

Пример:
```
/task Помогни ми с Fly.io deployment
```

---

**Създадено от GitHub Copilot** 🤖  
**Дата:** 23 ноември 2025
