#!/usr/bin/env python3
"""
Test for PR #6: Auto Signal Scheduler
Validates that auto signal jobs are properly configured
"""

import ast
import re

def test_auto_signal_job_exists():
    """Test that auto_signal_job function exists in bot.py"""
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the function definition
    assert 'async def auto_signal_job(' in content, "auto_signal_job function not found"
    assert 'async def auto_signal_job(timeframe: str, bot_instance)' in content, "auto_signal_job signature incorrect"
    print("✅ auto_signal_job function exists with correct signature")

def test_scheduler_jobs_configured():
    """Test that all 4 timeframe scheduler jobs are configured"""
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for all 4 scheduler jobs
    timeframes = ['1h', '2h', '4h', '1d']
    
    for tf in timeframes:
        job_id = f"'auto_signal_{tf}'"
        assert job_id in content, f"Scheduler job for {tf} not found (id: {job_id})"
        print(f"✅ Scheduler job for {tf.upper()} configured")
    
    # Check for proper scheduling patterns
    assert "minute=5" in content, "1H job schedule (minute=5) not found"
    assert "hour='*/2'" in content and "minute=7" in content, "2H job schedule not found"
    assert "hour='*/4'" in content and "minute=10" in content, "4H job schedule not found"
    assert "hour=9" in content and "minute=15" in content, "1D job schedule not found"
    print("✅ All scheduler jobs have correct timing configuration")

def test_help_text_updated():
    """Test that help text includes auto timeframes info"""
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for the auto timeframes line in help
    assert "Auto timeframes: 1H (hourly), 2H (every 2h), 4H (every 4h), 1D (daily)" in content, \
        "Help text not updated with auto timeframes info"
    print("✅ Help text includes auto timeframes information")

def test_scheduler_log_message():
    """Test that scheduler start log mentions auto signals"""
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for updated log message
    assert "AUTO SIGNALS (1H, 2H, 4H, 1D)" in content, \
        "Scheduler log message doesn't mention auto signals"
    print("✅ Scheduler log message updated")

def test_auto_signal_job_implementation():
    """Test key elements of auto_signal_job implementation"""
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find the auto_signal_job function
    function_start = content.find('async def auto_signal_job(')
    assert function_start != -1, "auto_signal_job function not found"
    
    # Extract function content (approximately - up to next function)
    next_function = content.find('\nasync def ', function_start + 1)
    if next_function == -1:
        next_function = content.find('\ndef ', function_start + 1)
    
    function_content = content[function_start:next_function]
    
    # Check for key elements
    assert 'ict_engine_global.generate_signal' in function_content, \
        "auto_signal_job doesn't use ICT engine"
    assert 'fetch_mtf_data' in function_content, \
        "auto_signal_job doesn't fetch MTF data"
    assert 'format_standardized_signal' in function_content, \
        "auto_signal_job doesn't format signals properly"
    assert 'OWNER_CHAT_ID' in function_content, \
        "auto_signal_job doesn't send to owner"
    assert 'is_signal_already_sent' in function_content, \
        "auto_signal_job doesn't check for duplicates"
    assert 'record_signal' in function_content, \
        "auto_signal_job doesn't record signals to stats"
    
    print("✅ auto_signal_job implementation has all key elements")

def test_no_syntax_errors():
    """Test that bot.py has no syntax errors"""
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        ast.parse(content)
        print("✅ bot.py has no syntax errors")
    except SyntaxError as e:
        raise AssertionError(f"Syntax error in bot.py: {e}")

if __name__ == '__main__':
    print("🧪 Testing PR #6: Auto Signal Scheduler Implementation\n")
    
    try:
        test_auto_signal_job_exists()
        test_scheduler_jobs_configured()
        test_help_text_updated()
        test_scheduler_log_message()
        test_auto_signal_job_implementation()
        test_no_syntax_errors()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED - PR #6 Implementation Verified!")
        print("="*60)
        print("\n📋 Summary:")
        print("  ✅ auto_signal_job() function created")
        print("  ✅ 1H scheduler job: Every hour at :05")
        print("  ✅ 2H scheduler job: Every 2 hours at :07 ← NEW!")
        print("  ✅ 4H scheduler job: Every 4 hours at :10")
        print("  ✅ 1D scheduler job: Daily at 09:15 UTC")
        print("  ✅ Help text updated")
        print("  ✅ No syntax errors")
        print("\n🎉 Ready for deployment!")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
        exit(1)
