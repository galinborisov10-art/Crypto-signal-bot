
import requests
import json
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ================= НАСТРОЙКИ =================
TELEGRAM_BOT_TOKEN ="8349449826:AAFNmP0i-DlERin8Z7HVir4awGTpa5n8vUM"
OWNER_CHAT_ID = 8349449826


# Template URL for Binance price endpoint — we will format with symbol (e.g. BTCUSDT)
BITGET_URL_TEMPLATE = "https://api.binance.com/api/v3/ticker/price?symbol={symbol}"

# Map short names to Binance symbols. Users can use 'BTC', 'ETH', 'XRP', 'SOL' (case-insensitive).
SYMBOL_ALIASES = {
    'BTC': 'BTCUSDT',
    'ETH': 'ETHUSDT',
    'XRP': 'XRPUSDT',
    'SOL': 'SOLUSDT',
}

def normalize_symbol(name: str) -> str:
    if not name:
        return SYMBOL_ALIASES['BTC']
    s = name.strip().upper()
    # special keyword to request all supported symbols in one message
    if s == 'ALL' or s == '*':
        return 'ALL'
    # allow full symbol like BTCUSDT as-is
    if s.endswith('USDT'):
        return s
    return SYMBOL_ALIASES.get(s, s)


def _format_compact_price(p: float) -> str:
    """Format price compactly, trim trailing zeros."""
    return f"{p:.8f}".rstrip('0').rstrip('.')

# Default auto interval (seconds) — 10 minutes
AUTO_INTERVAL = 600

# Set up basic logging
import logging
import os
import threading
import time
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ------------------ Helpers ------------------
async def fetch_price_raw(symbol: str = 'BTCUSDT'):
    """Fetch raw response using requests inside a thread to avoid blocking.

    `symbol` should be a Binance symbol like 'BTCUSDT'.
    """
    url = BITGET_URL_TEMPLATE.format(symbol=symbol)
    try:
        r = await asyncio.to_thread(requests.get, url, timeout=10)
        return r
    except Exception:
        logger.exception("HTTP request failed for %s", symbol)
        raise

async def parse_price_from_response_text(resp_text: str):
    try:
        data = json.loads(resp_text)
    except Exception:
        # attempt to salvage first JSON object
        try:
            first_json = resp_text.split('}\n')[0] + '}' if '}\n' in resp_text else resp_text
            data = json.loads(first_json)
        except Exception:
            raise
    if isinstance(data, dict) and "price" in data:
        return float(data["price"]), data
    if isinstance(data, list):
        btc = next((item for item in data if item.get("symbol") == "BTCUSDT" and "price" in item), None)
        if btc:
            return float(btc["price"]), data
    raise KeyError("price")

# ------------------ Auto job ------------------
async def auto_send_price(context: ContextTypes.DEFAULT_TYPE):
    # Determine target chat and symbol from job data (passed when scheduling)
    target_chat = None
    symbol = 'BTCUSDT'
    try:
        job_data = getattr(context.job, 'data', None) if hasattr(context, 'job') else None
        if isinstance(job_data, dict):
            target_chat = job_data.get('chat_id')
            symbol = job_data.get('symbol', symbol)
        else:
            target_chat = job_data
    except Exception:
        target_chat = None

    try:
        r = await fetch_price_raw(symbol)
    except Exception as e:
        logger.error("Auto job HTTP error for %s: %s", symbol, e)
        return

    if r.status_code != 200:
        logger.warning("Binance returned HTTP %s in auto job for %s", r.status_code, symbol)
        return

    # If symbol == 'ALL', fetch all supported symbols and send a single combined message
    if symbol == 'ALL':
        # Build compact multi-line message: one short symbol per line
        lines = []
        for short, full in SYMBOL_ALIASES.items():
            try:
                rr = await fetch_price_raw(full)
            except Exception:
                lines.append(f"{short}: error")
                continue
            if rr is None or rr.status_code != 200:
                # log the failing URL/status for debugging
                try:
                    url = BITGET_URL_TEMPLATE.format(symbol=full)
                except Exception:
                    url = full
                resp_snip = getattr(rr, 'text', '')[:300] if rr is not None else '(no response)'
                logger.warning("Binance request failed for %s -> %s (HTTP %s). Resp: %s", url, short, getattr(rr, 'status_code', 'N/A'), resp_snip)
                lines.append(f"{short}: unavailable")
                continue
            try:
                p, _ = await parse_price_from_response_text(rr.text)
                lines.append(f"{short}: {_format_compact_price(p)}")
            except Exception:
                lines.append(f"{short}: parse error")
            # slightly larger delay to reduce chance of 400s/rate-limits
            await asyncio.sleep(0.25)
        text = "\n".join(lines) if lines else "(no prices available)"
        try:
            send_to = target_chat or OWNER_CHAT_ID
            await context.bot.send_message(chat_id=send_to, text=text)
            logger.info("Auto send (ALL): chat=%s symbols=%s", send_to, ",".join(SYMBOL_ALIASES.keys()))
        except Exception:
            logger.exception("Failed to send auto combined message")
        return

    try:
        price, parsed = await parse_price_from_response_text(r.text)
    except Exception as e:
        logger.exception("Auto job parse error for %s", symbol)
        try:
            # notify owner and, if available, the target chat
            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=f"⚠️ Auto job parse error ({symbol}): {e}\nRaw: {r.text}")
            if target_chat:
                await context.bot.send_message(chat_id=target_chat, text=f"⚠️ Auto job parse error ({symbol}): {e}\nRaw: {r.text}")
        except Exception:
            logger.exception("Failed to notify owner about parse error")
        return

    try:
        send_to = target_chat or OWNER_CHAT_ID
        await context.bot.send_message(chat_id=send_to, text=f"🤖 Auto {symbol}: {price:.2f}")
        logger.info("Auto send: chat=%s symbol=%s price=%s", send_to, symbol, price)
    except Exception:
        logger.exception("Failed to send auto message")


# Direct fallback auto sender (when JobQueue unavailable)
def _direct_auto_worker(token: str, chat_id: int, interval: int, stop_event: threading.Event, symbol: str = 'BTCUSDT'):
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    fetch_url = BITGET_URL_TEMPLATE.format(symbol=symbol)
    while not stop_event.is_set():
        try:
            if symbol == 'ALL':
                lines = []
                for short, full in SYMBOL_ALIASES.items():
                    try:
                        r = requests.get(BITGET_URL_TEMPLATE.format(symbol=full), timeout=10)
                    except Exception:
                        lines.append(f"{short}: error")
                        continue
                    if r.status_code != 200:
                        url = BITGET_URL_TEMPLATE.format(symbol=full)
                        resp_snip = getattr(r, 'text', '')[:300]
                        logger.warning("Direct Binance request failed for %s -> %s (HTTP %s). Resp: %s", url, short, r.status_code, resp_snip)
                        lines.append(f"{short}: unavailable")
                        continue
                    try:
                        d = r.json()
                        if isinstance(d, dict) and 'price' in d:
                            p = float(d['price'])
                        elif isinstance(d, list) and d:
                            el = d[0]
                            p = float(el.get('price') or el.get('last'))
                        else:
                            lines.append(f"{short}: no price")
                            continue
                        lines.append(f"{short}: {_format_compact_price(p)}")
                    except Exception:
                        lines.append(f"{short}: parse error")
                        logger.exception("Direct worker failed parsing %s response snippet: %s", full, getattr(r, 'text', '')[:300])
                    # throttling between requests
                    time.sleep(0.25)
                text = "\n".join(lines) if lines else "(no prices available)"
                try:
                    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
                    logger.info("Direct auto sent (ALL): chat=%s symbols=%s", chat_id, ",".join(SYMBOL_ALIASES.keys()))
                except Exception:
                    logger.exception("Direct auto: failed to send combined message")
            else:
                r = requests.get(fetch_url, timeout=10)
                price = None
                if r.status_code == 200:
                    try:
                        data = r.json()
                        if isinstance(data, dict) and 'price' in data:
                            price = float(data['price'])
                        elif isinstance(data, list) and data:
                            el = data[0]
                            price = float(el.get('price') or el.get('last'))
                    except Exception:
                        price = None
                text = f"🤖 Auto {symbol}: {price:.2f}" if price is not None else f"🤖 Auto {symbol}: (price unavailable)"
                try:
                    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
                    logger.info("Direct auto sent: chat=%s symbol=%s price=%s", chat_id, symbol, price)
                except Exception:
                    logger.exception("Direct auto: failed to send message")
        except Exception:
            logger.exception("Direct auto: failed to fetch/send for %s", symbol)
        stop_event.wait(interval)


def start_direct_auto(app, chat_id: int, interval: int, symbol: str = 'BTCUSDT'):
    bot_data = app.bot_data
    job_key = f"auto_job_{chat_id}"
    stop_key = f"direct_auto_stop_{chat_id}"
    if bot_data.get(stop_key):
        return
    stop_event = threading.Event()
    t = threading.Thread(target=_direct_auto_worker, args=(TELEGRAM_BOT_TOKEN, chat_id, interval, stop_event, symbol), daemon=True)
    bot_data[stop_key] = stop_event
    bot_data[job_key] = {'type': 'direct', 'thread': t}
    # store symbol for this chat's auto mode
    bot_data[f"auto_symbol_{chat_id}"] = symbol
    t.start()


def stop_direct_auto(app, chat_id: int):
    bot_data = app.bot_data
    job_key = f"auto_job_{chat_id}"
    stop_key = f"direct_auto_stop_{chat_id}"
    stop_event = bot_data.get(stop_key)
    if stop_event and isinstance(stop_event, threading.Event):
        stop_event.set()
        bot_data.pop(stop_key, None)
    job = bot_data.get(job_key)
    if isinstance(job, dict) and job.get('type') == 'direct':
        bot_data.pop(job_key, None)
    # remove stored symbol
    bot_data.pop(f"auto_symbol_{chat_id}", None)


async def signal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    parsed = None
    try:
        # Determine symbol from args (e.g. /signal ETH) or default to BTC
        symbol = SYMBOL_ALIASES['BTC']
        if context.args:
            symbol = normalize_symbol(context.args[0])
        # Use async helper to avoid blocking
        r = await fetch_price_raw(symbol)
        if r.status_code != 200:
            await update.message.reply_text(f"⚠️ Binance API error: HTTP {r.status_code}")
            return
        try:
            parsed = r.json()
        except Exception:
            # try salvage
            try:
                first_json = r.text.split('}\n')[0] + '}' if '}\n' in r.text else r.text
                parsed = json.loads(first_json)
            except Exception as e2:
                import traceback
                tb = traceback.format_exc()
                await update.message.reply_text(f"⚠️ JSON parse error (extra): {e2}\nRaw: {r.text}\nTrace:\n{tb}")
                return
        # extract price with flexible fallbacks
        price = None
        # direct price
        if isinstance(parsed, dict) and "price" in parsed:
            price = float(parsed["price"])
        # nested 'data' field (some APIs wrap result)
        elif isinstance(parsed, dict) and "data" in parsed:
            inner = parsed["data"]
            if isinstance(inner, dict) and "price" in inner:
                price = float(inner["price"])
            elif isinstance(inner, list):
                # try find symbol or take first element
                btc = next((item for item in inner if item.get("symbol") == "BTCUSDT" and ("price" in item or "last" in item)), None)
                if btc:
                    if "price" in btc:
                        price = float(btc["price"])
                    else:
                        price = float(btc.get("last"))
                elif inner and isinstance(inner[0], dict):
                    # fallback to first element
                    elem = inner[0]
                    if "price" in elem:
                        price = float(elem["price"])
                    elif "last" in elem:
                        price = float(elem["last"])
        elif isinstance(parsed, list):
            btc = next((item for item in parsed if item.get("symbol") == "BTCUSDT" and ("price" in item or "last" in item)), None)
            if btc:
                if "price" in btc:
                    price = float(btc["price"])
                else:
                    price = float(btc.get("last"))
            elif parsed and isinstance(parsed[0], dict):
                elem = parsed[0]
                if "price" in elem:
                    price = float(elem["price"])
                elif "last" in elem:
                    price = float(elem["last"])
        if price is None:
            raise KeyError("price")
        await update.message.reply_text(f"📈 {symbol} price: {price:.2f}")
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        # send concise message to user and detailed to owner
        try:
            await update.message.reply_text(f"⚠️ Error: {e}")
        except Exception:
            pass
        try:
            await context.bot.send_message(chat_id=OWNER_CHAT_ID, text=f"⚠️ /signal error: {e}\nRaw: {getattr(r, 'text', None)}\nParsed: {repr(parsed)}\nTrace:\n{tb}")
        except Exception:
            logger.exception("Failed to send error to owner")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # First, determine auto-mode status for this chat and report it regardless of API success
    try:
        app = context.application
        bot_data = app.bot_data
        chat = update.effective_chat
        chat_id = chat.id if chat is not None else OWNER_CHAT_ID
        auto_mode_key = f"auto_mode_{chat_id}"
        interval_key = f"auto_interval_{chat_id}"
        job_key = f"auto_job_{chat_id}"
        auto_mode = bot_data.get(auto_mode_key, False)
        auto_interval = bot_data.get(interval_key)
        auto_status = "ON" if auto_mode else "OFF"
        interval_part = f" (interval: {auto_interval}s)" if auto_interval else ""
        # Try to fetch price for this chat's configured symbol (if any); if it fails, still show auto status
        try:
            symbol_key = f"auto_symbol_{chat_id}"
            symbol = bot_data.get(symbol_key, SYMBOL_ALIASES['BTC'])
            r = await fetch_price_raw(symbol)
            if r.status_code != 200:
                await update.message.reply_text(f"🟢 Bot status: RUNNING\nAuto mode: {auto_status}{interval_part}\n⚠️ Binance API error: HTTP {r.status_code}")
                return
            try:
                data = r.json()
            except Exception as json_err:
                await update.message.reply_text(f"🟢 Bot status: RUNNING\nAuto mode: {auto_status}{interval_part}\n⚠️ JSON parse error: {json_err}\nRaw: {r.text}")
                return
            # include price if available
            displayed = f"{symbol}:"
            if isinstance(data, dict) and "price" in data:
                try:
                    price = float(data["price"])
                    await update.message.reply_text(f"🟢 Bot status: RUNNING\nAuto mode: {auto_status}{interval_part}\n{displayed} {price:.2f}")
                except Exception:
                    await update.message.reply_text(f"🟢 Bot status: RUNNING\nAuto mode: {auto_status}{interval_part}\n⚠️ Invalid price format: {data.get('price')}")
            elif isinstance(data, list):
                found = next((item for item in data if item.get("symbol") == symbol), None)
                if found and "price" in found:
                    try:
                        price = float(found["price"])
                        await update.message.reply_text(f"🟢 Bot status: RUNNING\nAuto mode: {auto_status}{interval_part}\n{displayed} {price:.2f}")
                    except Exception:
                        await update.message.reply_text(f"🟢 Bot status: RUNNING\nAuto mode: {auto_status}{interval_part}\n⚠️ Invalid price format: {found.get('price')}")
                else:
                    await update.message.reply_text(f"🟢 Bot status: RUNNING\nAuto mode: {auto_status}{interval_part}\n⚠️ {symbol} not found in Binance response")
        except Exception as e:
            await update.message.reply_text(f"🟢 Bot status: RUNNING\nAuto mode: {auto_status}{interval_part}\n⚠️ Failed to fetch price: {e}")
        # Additionally, show a summary of active auto jobs across chats
        try:
            active = []
            for k, v in bot_data.items():
                if k.startswith("auto_mode_") and v:
                    cid = k.split("auto_mode_")[1]
                    interval = bot_data.get(f"auto_interval_{cid}")
                    active.append((cid, interval))
            if active:
                lines = [f"Active auto jobs ({len(active)}):"]
                for cid, interval in active:
                    lines.append(f"- chat_id: {cid}, interval: {interval}s")
                await update.message.reply_text("\n".join(lines))
        except Exception:
            logger.exception("Failed to build autolist in status")
    except Exception as e:
        await update.message.reply_text(f"⚠️ Error getting status: {e}")

async def auto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle auto mode ON/OFF.

    - Allowed for anyone in a private chat with the bot.
    - In groups, only the OWNER_CHAT_ID may toggle.
    """
    user_id = update.effective_user.id if update.effective_user else None
    chat = update.effective_chat
    is_private = chat is not None and chat.type == "private"
    # allowed if private chat, or owner
    if not is_private and user_id != OWNER_CHAT_ID:
        await update.message.reply_text("⚠️ Only the owner can toggle auto mode in groups.")
        return

    app = context.application
    bot_data = app.bot_data
    chat_id = chat.id if chat is not None else OWNER_CHAT_ID
    key = f"auto_job_{chat_id}"
    interval_key = f"auto_interval_{chat_id}"
    auto_mode_key = f"auto_mode_{chat_id}"

    auto_mode = bot_data.get(auto_mode_key, False)
    if not auto_mode:
        # enable
        interval = AUTO_INTERVAL
        symbol = SYMBOL_ALIASES['BTC']
        # allow user to pass seconds and/or symbol as arguments
        if context.args:
            # two forms supported: /auto <seconds> <SYMBOL>  or /auto <SYMBOL>  or /auto <seconds>
            if len(context.args) == 1:
                # try integer first, otherwise treat as symbol
                try:
                    interval = int(context.args[0])
                except Exception:
                    symbol = normalize_symbol(context.args[0])
            else:
                # first arg interval, second arg symbol
                try:
                    interval = int(context.args[0])
                except Exception:
                    interval = AUTO_INTERVAL
                symbol = normalize_symbol(context.args[1])

        # set mode/interval/symbol so /status immediately reflects the new state
        bot_data[auto_mode_key] = True
        bot_data[interval_key] = interval
        bot_data[f"auto_symbol_{chat_id}"] = symbol
        # schedule job with chat_id and symbol as context so auto_send_price knows target
        if getattr(app, 'job_queue', None) is not None:
            job = app.job_queue.run_repeating(auto_send_price, interval=interval, first=0, data={'chat_id': chat_id, 'symbol': symbol})
            bot_data[key] = job
            logger.info("Auto mode enabled (job_queue): chat_id=%s interval=%s symbol=%s", chat_id, interval, symbol)
        else:
            # fallback: start direct thread-based sender
            start_direct_auto(app, chat_id, interval, symbol)
            logger.info("Auto mode enabled (direct): chat_id=%s interval=%s symbol=%s", chat_id, interval, symbol)
        await update.message.reply_text(f"✅ Auto mode enabled for this chat. Interval: {interval}s Symbol: {symbol}")
    else:
        job = bot_data.get(key)
        if job:
            # job from JobQueue
            try:
                job.schedule_removal()
            except Exception:
                # maybe a direct job dict
                pass
        else:
            # maybe direct thread
            try:
                stop_direct_auto(app, chat_id)
            except Exception:
                pass
        bot_data[auto_mode_key] = False
        bot_data.pop(key, None)
        bot_data.pop(interval_key, None)
        bot_data.pop(f"auto_symbol_{chat_id}", None)
        logger.info("Auto mode disabled: chat_id=%s", chat_id)
        await update.message.reply_text("⛔ Auto mode disabled for this chat.")


async def auto_cmd_cyr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cyrillic alias '/ауто' — default interval 10 minutes if no arg provided."""
    # if no args provided, default to 600 seconds (10 minutes)
    if not context.args:
        context.args = [str(600)]
    await auto_cmd(update, context)


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello — bot is running. Use /signal to get price, /auto to toggle auto mode.")


async def whoami_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Return caller's Telegram user id and chat info."""
    user = update.effective_user
    chat = update.effective_chat
    if not user:
        await update.message.reply_text("Could not determine user info.")
        return
    username = f"@{user.username}" if getattr(user, 'username', None) else '(no username)'
    first = getattr(user, 'first_name', '') or ''
    last = getattr(user, 'last_name', '') or ''
    chat_id = chat.id if chat is not None else 'N/A'
    chat_type = chat.type if chat is not None else 'N/A'
    text = (
        f"Your Telegram info:\n"
        f"- user_id: {user.id}\n"
        f"- username: {username}\n"
        f"- name: {first} {last}\n"
        f"Chat info:\n"
        f"- chat_id: {chat_id}\n"
        f"- chat_type: {chat_type}"
    )
    await update.message.reply_text(text)


async def autolist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all chats that have auto-mode enabled and their intervals."""
    app = context.application
    bot_data = app.bot_data
    active = []
    for k, v in bot_data.items():
        if k.startswith("auto_mode_") and v:
            cid = k.split("auto_mode_")[1]
            interval = bot_data.get(f"auto_interval_{cid}")
            active.append((cid, interval))
    if not active:
        await update.message.reply_text("No active auto jobs.")
        return
    lines = [f"Active auto jobs ({len(active)}):"]
    for cid, interval in active:
        lines.append(f"- chat_id: {cid}, interval: {interval}s")
    await update.message.reply_text("\n".join(lines))


async def symbols_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show the list of supported symbols and usage examples."""
    lines = ["Supported symbols:"]
    for short, full in SYMBOL_ALIASES.items():
        lines.append(f"- {short}: {full}")
    lines.append("")
    lines.append("Usage examples:")
    lines.append("- /signal ETH  — get current ETH/USDT price")
    lines.append("- /auto 600 SOL  — enable auto every 600s for SOL")
    await update.message.reply_text("\n".join(lines))


async def prices_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Fetch prices for all supported symbols and send one combined message."""
    def _fmt(p: float) -> str:
        s = f"{p:.8f}".rstrip('0').rstrip('.')
        return s

    parts = []
    for short, full in SYMBOL_ALIASES.items():
        try:
            r = await fetch_price_raw(full)
        except Exception as e:
            parts.append(f"{short}: error")
            continue
        if r is None or r.status_code != 200:
            # log URL, status and a short response snippet for debugging
            try:
                url = BITGET_URL_TEMPLATE.format(symbol=full)
            except Exception:
                url = full
            resp_snip = getattr(r, 'text', '')[:300] if r is not None else '(no response)'
            logger.warning("/prices: Binance request failed for %s -> %s (HTTP %s). Resp: %s", url, short, getattr(r, 'status_code', 'N/A'), resp_snip)
            parts.append(f"{short}: unavailable")
            continue
        try:
            data = r.json()
            price = None
            if isinstance(data, dict) and 'price' in data:
                price = float(data['price'])
            elif isinstance(data, list) and data:
                el = data[0]
                price = float(el.get('price') or el.get('last'))
            if price is None:
                parts.append(f"{short}: price not found")
            else:
                parts.append(f"{short}: { _fmt(price) }")
            # small delay to reduce chance of rate limits on user-triggered /prices
            await asyncio.sleep(0.25)
        except Exception:
            parts.append(f"{short}: parse error")

    if not parts:
        await update.message.reply_text("No prices available.")
        return
    await update.message.reply_text("\n".join(parts))


async def dumpbotdata_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Owner-only: dump bot_data keys and values relevant to this chat for debugging."""
    user_id = update.effective_user.id if update.effective_user else None
    if user_id != OWNER_CHAT_ID:
        await update.message.reply_text("⚠️ Only the owner can use this command.")
        return
    app = context.application
    bot_data = app.bot_data
    chat = update.effective_chat
    cid = chat.id if chat is not None else 'N/A'
    # gather keys that mention this chat
    related = {k: bot_data.get(k) for k in bot_data.keys() if str(cid) in k}
    # include general auto_mode keys too
    summary = [f"bot_data keys for chat {cid}:"]
    if not related:
        summary.append("(no direct keys found)")
    else:
        for k, v in related.items():
            summary.append(f"- {k}: {type(v).__name__}")
    # Also show global auto_mode keys
    global_active = []
    for k, v in bot_data.items():
        if k.startswith("auto_mode_") and v:
            global_active.append(k)
    summary.append(f"\nGlobal active auto_mode keys: {len(global_active)}")
    for k in global_active:
        summary.append(f"- {k}")
    await update.message.reply_text("\n".join(summary))


def main():
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()

    # Temporary: support forcing auto enable for a single chat via env var
    # Format: FORCE_ENABLE_AUTO="<chat_id>:<seconds>"
    try:
        force = os.getenv("FORCE_ENABLE_AUTO")
        if force:
            parts = force.split(":")
            # Support formats: <chat_id>:<interval> or <chat_id>:<interval>:<duration>
            if len(parts) >= 2:
                target_cid = int(parts[0])
                interval_seconds = int(parts[1])
                duration_seconds = int(parts[2]) if len(parts) >= 3 else interval_seconds
                bot_data = app.bot_data
                auto_mode_key = f"auto_mode_{target_cid}"
                interval_key = f"auto_interval_{target_cid}"
                job_key = f"auto_job_{target_cid}"

                def _schedule_when_ready():
                    # wait for the application's job_queue to be available
                    for _ in range(100):
                        if getattr(app, 'job_queue', None) is not None:
                            break
                        time.sleep(0.1)
                    if getattr(app, 'job_queue', None) is None:
                        logger.error("[FORCE] job_queue not available, cannot schedule forced auto")
                        return
                    try:
                        # set flags
                        bot_data[auto_mode_key] = True
                        bot_data[interval_key] = interval_seconds
                        job = app.job_queue.run_repeating(auto_send_price, interval=interval_seconds, first=0, data={'chat_id': target_cid, 'symbol': SYMBOL_ALIASES['BTC']})
                        bot_data[job_key] = job
                        logger.info("[FORCE] Auto mode enabled for %s interval=%ss duration=%ss", target_cid, interval_seconds, duration_seconds)

                        # schedule disable after duration_seconds
                        async def _disable_once(ctx: ContextTypes.DEFAULT_TYPE):
                            try:
                                j = bot_data.get(job_key)
                                if j:
                                    j.schedule_removal()
                                bot_data[auto_mode_key] = False
                                bot_data.pop(job_key, None)
                                bot_data.pop(interval_key, None)
                                logger.info("[FORCE] Auto mode disabled for %s after test", target_cid)
                                try:
                                    await ctx.bot.send_message(chat_id=target_cid, text="⛔ Auto mode disabled (test finished)")
                                except Exception:
                                    pass
                            except Exception:
                                logger.exception("Failed disabling forced auto")

                        app.job_queue.run_once(_disable_once, when=duration_seconds, data=None)
                    except Exception:
                        logger.exception("Failed to schedule forced auto")

                t = threading.Thread(target=_schedule_when_ready, daemon=True)
                t.start()
    except Exception:
        logger.exception("Failed to process FORCE_ENABLE_AUTO")

    # register handlers
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("signal", signal))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("auto", auto_cmd))
    app.add_handler(CommandHandler("whoami", whoami_cmd))
    app.add_handler(CommandHandler("autolist", autolist_cmd))
    app.add_handler(CommandHandler("symbols", symbols_cmd))
    app.add_handler(CommandHandler("prices", prices_cmd))
    app.add_handler(CommandHandler("dumpbotdata", dumpbotdata_cmd))
    # (no Cyrillic alias registered)

    # --- Auto-enable for requesting user (owner requested): enable for chat with optional env override
    try:
        # PREENABLE_AUTO env var supports: <chat_id>:<interval>:<SYMBOL>
        pre = os.getenv("PREENABLE_AUTO")
        if pre:
            parts = pre.split(":")
            if len(parts) >= 2:
                target_chat_to_enable = int(parts[0])
                interval_val = int(parts[1])
                symbol_val = normalize_symbol(parts[2]) if len(parts) >= 3 else SYMBOL_ALIASES['BTC']
            else:
                target_chat_to_enable = 7003238836
                interval_val = AUTO_INTERVAL
                symbol_val = SYMBOL_ALIASES['BTC']
        else:
            target_chat_to_enable = 7003238836
            interval_val = AUTO_INTERVAL
            symbol_val = SYMBOL_ALIASES['BTC']

        bot_data = app.bot_data
        auto_mode_key = f"auto_mode_{target_chat_to_enable}"
        interval_key = f"auto_interval_{target_chat_to_enable}"
        job_key = f"auto_job_{target_chat_to_enable}"

        bot_data[auto_mode_key] = True
        bot_data[interval_key] = interval_val
        bot_data[f"auto_symbol_{target_chat_to_enable}"] = symbol_val
        if getattr(app, 'job_queue', None) is not None:
            job = app.job_queue.run_repeating(auto_send_price, interval=interval_val, first=0, data={'chat_id': target_chat_to_enable, 'symbol': symbol_val})
            bot_data[job_key] = job
            logger.info("Auto mode pre-enabled (job_queue) for %s interval=%s symbol=%s", target_chat_to_enable, interval_val, symbol_val)
        else:
            start_direct_auto(app, target_chat_to_enable, interval_val, symbol_val)
            logger.info("Auto mode pre-enabled (direct) for %s interval=%s symbol=%s", target_chat_to_enable, interval_val, symbol_val)
    except Exception:
        logger.exception("Failed to auto-enable for target chat")

    # start polling
    logger.info("Starting bot")
    app.run_polling()


if __name__ == "__main__":
    main()