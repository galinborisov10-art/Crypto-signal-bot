# 🔧 FIX SSH DEPLOY - КОПИРАЙ КОМАНДИТЕ ДИРЕКТНО

## ПРОБЛЕМ:
SSH ключът в GitHub Secret `DO_SSH_KEY` е невалиден. Затова Auto Deploy failва с:
```
Load key "/home/runner/.ssh/deploy_key": error in libcrypto
Permission denied (publickey,password)
```

## РЕШЕНИЕ:
Използвай ТОЗИ нов валиден SSH ключ:

---

## 🔑 СТЪПКА 1: Добави PUBLIC ключа на DigitalOcean сървъра

Отвори PowerShell и изпълни:

```powershell
ssh root@YOUR_SERVER_IP
```

След като влезеш на сървъра, изпълни:

```bash
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIB18mLmW6eXdhcjam9Io0HzfPUqsjnTvQQhzlZ+XYyRC github-actions-auto" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
echo "✅ SSH ключ инсталиран!"
exit
```

---

## 🔐 СТЪПКА 2: Обнови GitHub Secret

1. Отиди на: https://github.com/galinborisov10-art/Crypto-signal-bot/settings/secrets/actions

2. Намери `DO_SSH_KEY` → натисни **Update**

3. Изтрий старото съдържание и копирай ЦЕЛИЯ текст долу (включително BEGIN/END редовете):

```
-----BEGIN OPENSSH PRIVATE KEY-----
b3BlbnNzaC1rZXktdjEAAAAABG5vbmUAAAAEbm9uZQAAAAAAAAABAAAAMwAAAAtzc2gtZW
QyNTUxOQAAACAdfJi5lunl3YXI2pvSKNB83z1KrI5070EIc5Wfl2MkQgAAAJhz1sjbc9bI
2wAAAAtzc2gtZWQyNTUxOQAAACAdfJi5lunl3YXI2pvSKNB83z1KrI5070EIc5Wfl2MkQg
AAAECqsAHDBErBuIPUigBOzPzGWO8abm2/TzbfCkmXFxEDWh18mLmW6eXdhcjam9Io0Hzf
PUqsjnTvQQhzlZ+XYyRCAAAAE2dpdGh1Yi1hY3Rpb25zLWF1dG8BAg==
-----END OPENSSH PRIVATE KEY-----
```

4. Натисни **Update secret**

---

## ✅ СТЪПКА 3: Тествай Auto Deploy

След като направиш горните 2 стъпки, направи ПРОИЗВОЛНА промяна и push:

```bash
cd /workspaces/Crypto-signal-bot
echo "# Test deploy" >> README.md
git add README.md
git commit -m "Test auto-deploy"
git push
```

GitHub Actions автоматично ще deploy-не на сървъра! 🚀

---

## 🎯 АЛТЕРНАТИВА (АКО НЕ РАБОТИ):

Ако горното не работи, провери:
1. Че си копирал ЦЕЛИЯ private key с BEGIN/END редовете
2. Че няма празни редове преди/след ключа
3. Че public key-а е добавен на сървъра правилно

Можеш да тестваш SSH връзката с:
```bash
ssh -i /tmp/test_key root@YOUR_SERVER_IP "echo SSH works!"
```

---

**ЩОМ НАПРАВИШ ТЕЗИ 2 СТЪПКИ, AUTO-DEPLOY ЩЕ РАБОТИ АВТОМАТИЧНО! ✅**
