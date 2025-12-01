#!/usr/bin/env python3
import html
import os
import re
import subprocess

from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext

TOKEN = os.environ.get("TG_BOT_TOKEN")
ALLOWED_ADMIN_IDS = {123456789}  # replace with your numeric Telegram id

# Validate branch names to prevent command injection
BRANCH_PATTERN = re.compile(r'^[a-zA-Z0-9._/-]+$')


def deploy_cmd(update: Update, context: CallbackContext):
    user_id = update.effective_user.id
    if user_id not in ALLOWED_ADMIN_IDS:
        update.message.reply_text("Not authorized.")
        return
    branch = "main"
    if context.args:
        branch = context.args[0]
        if not BRANCH_PATTERN.match(branch) or len(branch) > 100:
            update.message.reply_text("Invalid branch name.")
            return
    update.message.reply_text(f"Starting deploy (branch={branch})...")
    try:
        res = subprocess.run(["/usr/local/bin/crypto-deploy.sh", branch],
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=900)
        out = html.escape(res.stdout)
        update.message.reply_text(f"Deploy finished:\n<pre>{out[:3000]}</pre>", parse_mode="HTML")
    except Exception as e:
        update.message.reply_text(f"Deploy error: {e}")


def main():
    if not TOKEN:
        print("TG_BOT_TOKEN not set")
        return
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("autodeploy", deploy_cmd))
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
