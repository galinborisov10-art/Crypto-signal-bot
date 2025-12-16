import re

with open('bot.py', 'r') as f:
    content = f.read()

# Find the location after signal generation (before "Format and send signal")
cooldown_check = '''
        # === COOLDOWN CHECK ===
        signal_key = f"{symbol}_{timeframe}_{signal. signal_type.value}"
        
        if is_signal_already_sent(
            symbol=symbol,
            signal_type=signal.signal_type. value,
            timeframe=timeframe,
            confidence=signal. confidence,
            entry_price=signal.entry_price,
            cooldown_minutes=60
        ):
            await processing_msg.edit_text(
                f"⏳ <b>Signal for {symbol} {timeframe} already sent recently</b>\\n\\n"
                f"Cooldown:  60 minutes\\n"
                f"Please wait before requesting again.",
                parse_mode='HTML'
            )
            return
        # === END COOLDOWN CHECK ===
        
'''

# Find pattern:  after "if not signal:" block, before "# Format and send signal"
pattern = r'(            return\n\n)(        # Format and send signal)'
replacement = cooldown_check + r'\2'

if re.search(pattern, content):
    content = re.sub(pattern, replacement, content, count=1)
    print("✅ Added cooldown check to ICT command")
    
    with open('bot.py', 'w') as f:
        f.write(content)
    print("✅ bot.py updated successfully!")
else:
    print("❌ Pattern not found - checking alternate location")
    
    # Try alternate pattern
    pattern2 = r'(        if not signal:.*?return\n)(        # Format and send signal)'
    if re.search(pattern2, content, re.DOTALL):
        content = re.sub(pattern2, cooldown_check + r'\2', content, flags=re.DOTALL, count=1)
        print("✅ Added cooldown check (alternate location)")
        
        with open('bot.py', 'w') as f:
            f.write(content)
        print("✅ bot.py updated successfully!")
    else:
        print("❌ Could not find insertion point")
        print("Manual insertion needed before line 5985")

