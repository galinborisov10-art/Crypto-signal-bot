# 🚀 DEPLOYMENT ИНСТРУКЦИИ

## Как да направиш deploy и да тествате автоматичния deploy

---

## 📋 ПРЕДИ ДА ЗАПОЧНЕШ

Уверете се че имаш:
- ✅ DigitalOcean сървър с публичен IP
- ✅ SSH достъп до сървъра
- ✅ Git инсталиран на сървъра
- ✅ Python 3.8+ на сървъра
- ✅ PM2 инсталиран (за process management)

---

## 🎯 МЕТОД 1: ПЪРВОНАЧАЛЕН DEPLOY (Manual Setup)

### Стъпка 1: Commit и Push промените

```bash
# На локалната машина/Codespace
cd /workspaces/Crypto-signal-bot

# Добави всички промени
git add .

# Commit с описание
git commit -m "feat: Add 3H timeframe and auto-deployment"

# Push към GitHub
git push origin main
```

### Стъпка 2: Setup на сървъра

```bash
# 1. SSH към сървъра
ssh root@YOUR_SERVER_IP

# 2. Clone проекта (ако още не е)
cd ~
git clone https://github.com/galinborisov10-art/Crypto-signal-bot.git
cd Crypto-signal-bot

# 3. Инсталирай Node.js и PM2
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
apt-get install -y nodejs
npm install -g pm2

# 4. Инсталирай Python dependencies
pip3 install -r requirements.txt

# ВАЖНО: Или използвай нашия скрипт:
./install_dependencies.sh

# 5. Създай .env файл със своите токени
nano .env

# Копирай това и попълни с реални стойности:
TELEGRAM_BOT_TOKEN=your_bot_token_here
OWNER_CHAT_ID=7003238836
BINANCE_PRICE_URL=https://api.binance.com/api/v3/ticker/price
BINANCE_24H_URL=https://api.binance.com/api/v3/ticker/24hr
BINANCE_KLINES_URL=https://api.binance.com/api/v3/klines

# Запази: Ctrl+O, Enter, Ctrl+X

# 6. Направи скриптовете изпълними
chmod +x *.sh

# 7. Стартирай бота с PM2
pm2 start ecosystem.config.js

# 8. Запази PM2 конфигурацията
pm2 save

# 9. Настрой PM2 да стартира при boot
pm2 startup
# ВАЖНО: Копирай командата която ти дава и я изпълни!

# 10. Провери статуса
pm2 status
pm2 logs crypto-bot --lines 50
```

### Готово! Ботът работи! 🎉

---

## 🎯 МЕТОД 2: AUTO-DEPLOY С GITHUB ACTIONS

### Стъпка 1: Генерирай SSH ключ

```bash
# На сървъра
ssh-keygen -t ed25519 -C "github-actions-deploy"

# Просто натискай Enter за default настройки
# Public key:
cat ~/.ssh/id_ed25519.pub

# ВАЖНО: Добави public key към authorized_keys
cat ~/.ssh/id_ed25519.pub >> ~/.ssh/authorized_keys

# Private key (копирай целия output):
cat ~/.ssh/id_ed25519
```

### Стъпка 2: Добави GitHub Secrets

1. Отвори GitHub repo: https://github.com/galinborisov10-art/Crypto-signal-bot
2. Settings → Secrets and variables → Actions
3. Натисни "New repository secret"

Добави следните secrets:

| Name | Value |
|------|-------|
| `DO_HOST` | IP адреса на сървъра (напр. 165.227.123.45) |
| `DO_USERNAME` | `root` (или друг username) |
| `DO_SSH_KEY` | Private key от горе (цялото съдържание!) |
| `DO_PORT` | `22` (или друг SSH port) |

### Стъпка 3: Тествай GitHub Actions

```bash
# На локалната машина
cd /workspaces/Crypto-signal-bot

# Направи малка промяна за тест
echo "# Test auto-deploy" >> README.md

# Commit и push
git add README.md
git commit -m "test: Verify GitHub Actions auto-deploy"
git push origin main

# Провери дали работи:
# 1. Отвори GitHub repo
# 2. Actions tab
# 3. Виж последния workflow
# 4. Трябва да видиш успешен deploy!
```

---

## 🎯 МЕТОД 3: MANUAL UPDATE SCRIPT

### Използване на update_bot.sh

```bash
# SSH към сървъра
ssh root@YOUR_SERVER_IP

# Отиди в проекта
cd ~/Crypto-signal-bot

# Изпълни update скрипта
./update_bot.sh

# Скриптът автоматично:
# ✅ Прави backup
# ✅ Pull-ва от GitHub
# ✅ Обновява dependencies (ако има промени)
# ✅ Рестартира PM2
# ✅ Показва статус
```

---

## 🎯 МЕТОД 4: TELEGRAM AUTO-UPDATE

### Използване на /auto_update команда

1. **Влез като админ:**
   ```
   /admin_login
   ```
   Въведи парола: `8109`

2. **Изпълни update:**
   ```
   /auto_update
   ```

3. **Виж резултата:**
   - Ботът ще покаже статус в реално време
   - Ще видиш backup, pull, install, restart
   - След това нов бот версия работи!

---

## ✅ ТЕСТВАНЕ НА НОВИЯ 3H TIMEFRAME

### След deploy, тествай:

1. **Изпрати в Telegram:**
   ```
   /signal
   ```

2. **Избери BTC или друга монета**

3. **Избери 3H timeframe** (новият бутон!)

4. **Трябва да видиш:**
   - 📊 Анализ за 3-часов период
   - Графика с 3H кендели
   - RSI, MA, Volume за 3H
   - Сигнали за BUY/SELL на 3H basis

---

## 🔍 МОНИТОРИНГ И DEBUGGING

### Проверка на PM2 статус:
```bash
pm2 status
pm2 logs crypto-bot
pm2 monit  # Real-time monitoring
```

### Проверка на логове:
```bash
# Bot логове
tail -f ~/Crypto-signal-bot/bot.log

# PM2 логове
tail -f ~/Crypto-signal-bot/logs/pm2-out.log
tail -f ~/Crypto-signal-bot/logs/pm2-error.log
```

### Restart ботът:
```bash
pm2 restart crypto-bot
```

### Stop бота:
```bash
pm2 stop crypto-bot
```

### Delete от PM2:
```bash
pm2 delete crypto-bot
pm2 start ecosystem.config.js  # Започни отначало
```

---

## 🆘 TROUBLESHOOTING

### Проблем: Bot не стартира

**Решение:**
```bash
cd ~/Crypto-signal-bot
python3 bot.py  # Тествай директно
# Виж грешките

# Ако има import errors:
./install_dependencies.sh
```

### Проблем: Git pull конфликт

**Решение:**
```bash
git stash  # Запази локални промени
git pull   # Pull от GitHub
git stash pop  # Върни локални промени
```

### Проблем: Dependencies липсват

**Решение:**
```bash
./install_dependencies.sh
# или
pip3 install -r requirements.txt --upgrade
```

### Проблем: PM2 не се стартира при reboot

**Решение:**
```bash
pm2 startup
# Копирай командата която дава и я изпълни
pm2 save
```

---

## 📊 VERIFICATION CHECKLIST

След deployment, провери:

- [ ] PM2 показва crypto-bot като `online`
- [ ] Bot отговаря на `/start` в Telegram
- [ ] `/signal` команда работи
- [ ] 3H timeframe се вижда в менюто
- [ ] 3H графика се генерира правилно
- [ ] `/auto_update` работи (ако си admin)
- [ ] GitHub Actions deploy workflow минава успешно

---

## 🎉 ГОТОВО!

Ако всички горни checklist точки са ✅, deployment е успешен!

Сега имаш:
- ✅ Working bot на production сървър
- ✅ 3H timeframe функционалност
- ✅ 3 метода за auto-deployment
- ✅ PM2 auto-restart при crash
- ✅ Пълен мониторинг

---

## 💡 ПОЛЕЗНИ КОМАНДИ

```bash
# SSH
ssh root@YOUR_SERVER_IP

# Status
pm2 status

# Логове (real-time)
pm2 logs crypto-bot

# Мониторинг
pm2 monit

# Restart
pm2 restart crypto-bot

# Update от GitHub
./update_bot.sh

# Check dependencies
./install_dependencies.sh

# Git pull
git pull origin main
```

---

**Успех с deployment! 🚀**
