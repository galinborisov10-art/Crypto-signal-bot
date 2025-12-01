# Deploy instructions

This PR adds a GitHub Actions workflow and helper scripts to deploy the project to a DigitalOcean Droplet managed via systemd. It does NOT add any secrets or keys. Before using the workflow, follow these manual steps:

1. Add the deploy public key to the Droplet
   - Generate an SSH keypair locally (if you don't have one) and add the private key as the repository secret `DO_SSH_KEY` in GitHub.
   - Copy the public key into `/root/.ssh/authorized_keys` on the Droplet (append, do not remove other keys).

2. Add required GitHub repository secrets (Settings → Secrets and variables → Actions):
   - `DO_SSH_KEY` (private key content)
   - `DO_HOST` (Droplet IP or hostname)
   - `DO_USER` (user to SSH as, e.g., `root`)
   - `TELEGRAM_BOT_TOKEN` (for notifications)
   - `TELEGRAM_CHAT_ID` (chat id for notifications)

3. (Optional) If you want Telegram-triggered deploys from the server, create the systemd service for `telegram_deploy_handler.py` and set `TG_BOT_TOKEN` via an environment file or systemd EnvironmentFile. Ensure `ALLOWED_ADMIN_IDS` contains your Telegram numeric id.

4. On the server: copy `scripts/crypto-deploy.sh` to `/usr/local/bin/crypto-deploy.sh`, make it executable (`chmod 755`), and optionally set up a systemd drop-in file to run the bot via `crypto-bot.service`.

5. Test locally on the server before relying on Actions:
   - `cd /root/Crypto-signal-bot && git fetch --prune origin main && git reset --hard origin/main`
   - `source venv/bin/activate && pip install -r requirements.txt` (if venv exists)
   - `sudo systemctl restart crypto-bot.service && sudo systemctl status crypto-bot.service`

6. After you add secrets and the public key, push or merge this PR; GitHub Actions will run on pushes to `main` and attempt to deploy.

---

**IMPORTANT**: Do NOT store any private keys or tokens in the repository. Add them only as GitHub repository secrets. The deploy public key must be manually appended to `/root/.ssh/authorized_keys` on the Droplet.
