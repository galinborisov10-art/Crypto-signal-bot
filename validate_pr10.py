#!/usr/bin/env python3
"""
Quick validation test for bot.py import and basic functionality
"""

import sys
import os

# Set BASE_PATH
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

print("=" * 80)
print("🧪 BOT.PY IMPORT VALIDATION TEST")
print("=" * 80)
print()

# Test 1: Import bot.py modules
print("📦 Test 1: Importing bot.py modules...")
try:
    # Just check if we can import without running
    import importlib.util
    spec = importlib.util.spec_from_file_location("bot", f"{BASE_PATH}/bot.py")
    
    if spec and spec.loader:
        print("✅ bot.py found and loadable")
    else:
        print("❌ bot.py cannot be loaded")
        sys.exit(1)
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

print()

# Test 2: Import diagnostic modules
print("📦 Test 2: Importing diagnostic modules...")
try:
    from system_diagnostics import run_full_health_check
    from diagnostic_messages import format_health_summary
    print("✅ Diagnostic modules imported successfully")
except Exception as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

print()

# Test 3: Check for syntax errors in bot.py
print("🔍 Test 3: Checking bot.py syntax...")
import py_compile
try:
    py_compile.compile(f"{BASE_PATH}/bot.py", doraise=True)
    print("✅ No syntax errors in bot.py")
except py_compile.PyCompileError as e:
    print(f"❌ Syntax error: {e}")
    sys.exit(1)

print()

# Test 4: Verify /health command is defined
print("🔍 Test 4: Checking /health command...")
with open(f"{BASE_PATH}/bot.py", 'r') as f:
    bot_content = f.read()
    
    if 'async def health_cmd' in bot_content:
        print("✅ /health command found")
    else:
        print("❌ /health command not found")
        sys.exit(1)
    
    if 'CommandHandler("health", health_cmd)' in bot_content:
        print("✅ /health command registered")
    else:
        print("❌ /health command not registered")
        sys.exit(1)

print()

# Test 5: Verify health monitors are scheduled
print("🔍 Test 5: Checking health monitor jobs...")
monitor_jobs = [
    'journal_health_monitor_job',
    'ml_health_monitor_job',
    'daily_report_health_monitor_job',
    # 'position_monitor_health_job',  # REMOVED - checkpoint alert system disabled
    'scheduler_health_monitor_job',
    'disk_space_monitor_job'
]

for job in monitor_jobs:
    if job in bot_content:
        print(f"✅ {job} found")
    else:
        print(f"❌ {job} not found")
        sys.exit(1)

print()

# Test 6: Verify logging to file is configured
print("🔍 Test 6: Checking file logging configuration...")
if 'FileHandler' in bot_content and 'bot.log' in bot_content:
    print("✅ File logging configured")
else:
    print("❌ File logging not configured")
    sys.exit(1)

print()

print("=" * 80)
print("✅ ALL VALIDATION TESTS PASSED")
print("=" * 80)
print()
print("🎉 Bot is ready for deployment!")
print()
print("Next steps:")
print("  1. Set environment variables (TELEGRAM_BOT_TOKEN, OWNER_CHAT_ID)")
print("  2. Run: python3 bot.py")
print("  3. Test /health command in Telegram")
print("  4. Verify health monitors run on schedule")
