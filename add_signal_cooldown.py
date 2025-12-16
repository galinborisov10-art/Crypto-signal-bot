import re

with open('bot.py', 'r') as f:
    content = f.read()

# Find the line with signal_data dict creation (around line where we save signal)
# Add cooldown check before sending signal

cooldown_code = '''
# === SIGNAL COOLDOWN CHECK ===
MIN_SIGNAL_INTERVAL = 3600  # 1 hour cooldown per symbol+timeframe
signal_key = f"{symbol}_{timeframe}"

if not hasattr(context. bot_data, 'last_signals'):
    context.bot_data['last_signals'] = {}

last_signal_time = context.bot_data['last_signals'].get(signal_key, 0)
current_time = time.time()

if current_time - last_signal_time < MIN_SIGNAL_INTERVAL:
    logger.info(f"⏳ Skipping duplicate signal for {signal_key} (cooldown: {int((MIN_SIGNAL_INTERVAL - (current_time - last_signal_time)) / 60)} min remaining)")
    return

context.bot_data['last_signals'][signal_key] = current_time
# === END COOLDOWN CHECK ===

'''

# Find where we send ICT signal (search for "async def send_ict_signal")
pattern = r'(async def send_ict_signal.*?:\n)(.*? )(    # Create signal message)'
replacement = r'\1' + cooldown_code + r'\n\3'

if re.search(pattern, content, re.DOTALL):
    content = re.sub(pattern, replacement, content, flags=re. DOTALL)
    print("✅ Added cooldown check")
else:
    print("❌ Pattern not found")
    # Try alternate location
    pattern2 = r'(async def send_ict_signal.*?:\n)(.*?)(    signal_data = {)'
    if re.search(pattern2, content, re.DOTALL):
        replacement2 = r'\1' + cooldown_code + r'\n\3'
        content = re.sub(pattern2, replacement2, content, flags=re. DOTALL, count=1)
        print("✅ Added cooldown check (alt location)")

# Add import for time module
if 'import time' not in content:
    content = content.replace('import asyncio', 'import asyncio\nimport time')
    print("✅ Added time import")

with open('bot.py', 'w') as f:
    f.write(content)

print("✅ Signal cooldown mechanism added!")
