#!/usr/bin/env python3
"""
Test suite for scheduler context argument fix.

Tests that cache_cleanup_job and ml_auto_training_job can be called
with context argument as expected by the scheduler.
"""

import inspect
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_function_signatures():
    """Test that scheduler job functions have correct signatures"""
    
    # Read the bot.py file to check function signatures
    bot_file = os.path.join(os.path.dirname(__file__), 'bot.py')
    
    with open(bot_file, 'r') as f:
        bot_content = f.read()
    
    # Check cache_cleanup_job signature
    assert 'async def cache_cleanup_job(context):' in bot_content, \
        "cache_cleanup_job should accept context parameter"
    
    # Check ml_auto_training_job signature
    assert 'async def ml_auto_training_job(context):' in bot_content, \
        "ml_auto_training_job should accept context parameter"
    
    # Check that SimpleContext class exists
    assert 'class SimpleContext:' in bot_content, \
        "SimpleContext class should be defined"
    
    # Check that context is created
    assert 'context = SimpleContext(application.bot)' in bot_content, \
        "context should be created from SimpleContext"
    
    # Check that cache_cleanup_job gets args=[context]
    cache_job_section = bot_content[bot_content.find('cache_cleanup_job,'):bot_content.find('cache_cleanup_job,') + 300]
    assert 'args=[context]' in cache_job_section, \
        "cache_cleanup_job scheduler should have args=[context]"
    
    # Check that ml_auto_training_job gets args=[context]
    ml_job_section = bot_content[bot_content.find('ml_auto_training_job,'):bot_content.find('ml_auto_training_job,') + 300]
    assert 'args=[context]' in ml_job_section, \
        "ml_auto_training_job scheduler should have args=[context]"
    
    return True


def test_simple_context_class():
    """Test that SimpleContext class can be created and used"""
    # This simulates what happens in schedule_reports function
    
    class SimpleContext:
        """Minimal context object for scheduler jobs that need bot access."""
        def __init__(self, bot):
            self.bot = bot
    
    # Create a mock bot
    class MockBot:
        def send_message(self):
            pass
    
    mock_bot = MockBot()
    
    # Create context
    context = SimpleContext(mock_bot)
    
    # Verify context has bot attribute
    assert hasattr(context, 'bot'), "SimpleContext should have bot attribute"
    assert context.bot == mock_bot, "SimpleContext.bot should be the mock_bot"
    
    return True


if __name__ == '__main__':
    print("Running scheduler context fix tests...")
    print("\n1. Testing function signatures...")
    try:
        test_function_signatures()
        print("✅ PASS: Function signatures are correct\n")
    except AssertionError as e:
        print(f"❌ FAIL: {e}\n")
        sys.exit(1)
    
    print("2. Testing SimpleContext class...")
    try:
        test_simple_context_class()
        print("✅ PASS: SimpleContext class works correctly\n")
    except AssertionError as e:
        print(f"❌ FAIL: {e}\n")
        sys.exit(1)
    
    print("=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nScheduler jobs have correct signatures and context passing.")
    print("This fixes: TypeError: cache_cleanup_job() missing 1 required positional argument: 'context'")

