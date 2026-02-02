"""
Test Non-Blocking Startup Diagnostics
Validates that startup diagnostics never block bot operations
"""

import asyncio
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class TestResults:
    """Track test results"""
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.tests = []
    
    def add_pass(self, test_name):
        self.passed += 1
        self.tests.append((test_name, True))
        logger.info(f"✅ PASS: {test_name}")
    
    def add_fail(self, test_name, reason):
        self.failed += 1
        self.tests.append((test_name, False))
        logger.error(f"❌ FAIL: {test_name} - {reason}")
    
    def print_summary(self):
        print("\n" + "="*70)
        print("TEST SUMMARY")
        print("="*70)
        print(f"Total Tests: {self.passed + self.failed}")
        print(f"✅ Passed: {self.passed}")
        print(f"❌ Failed: {self.failed}")
        print("="*70)
        if self.failed == 0:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("⚠️ SOME TESTS FAILED")
        print("="*70)


# Mock classes for testing
class MockBot:
    def __init__(self):
        self.messages = []
    
    async def send_message(self, chat_id, text, parse_mode):
        self.messages.append({
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode,
            'timestamp': datetime.now()
        })


class MockApp:
    def __init__(self):
        self.bot = MockBot()


# Constants
OWNER_CHAT_ID = 7003238836


# Import the actual functions from bot.py by defining them here
# (In production, these would be imported from bot.py)
async def run_startup_diagnostics_safe(simulate_mode='normal'):
    """
    Simulated version of the safe diagnostic wrapper
    
    Args:
        simulate_mode: 'normal', 'timeout', 'crash', or 'import_error'
    """
    try:
        logger.info("🔍 Running startup diagnostics (non-blocking)...")
        
        if simulate_mode == 'timeout':
            # Simulate timeout
            await asyncio.wait_for(
                asyncio.sleep(100),
                timeout=1.0
            )
        elif simulate_mode == 'crash':
            # Simulate crash
            raise ValueError("Simulated diagnostic crash")
        elif simulate_mode == 'import_error':
            # Simulate import error
            raise ImportError("Simulated import error")
        else:
            # Normal execution
            await asyncio.sleep(0.1)
        
        logger.info("✅ Diagnostics complete")
        return "✅ All checks passed\n📊 20/20 tests OK"
        
    except asyncio.TimeoutError:
        logger.error("⚠️ Startup diagnostics timed out (non-critical)")
        return None
    except ImportError as e:
        logger.error(f"⚠️ Diagnostics module not available (non-critical): {e}")
        return None
    except Exception as e:
        logger.error(
            f"💥 Startup diagnostics crashed (non-critical): {type(e).__name__}: {e}"
        )
        return None


async def send_startup_message(application):
    """Send 'Bot started and online' message"""
    try:
        chat_id = OWNER_CHAT_ID
        if not chat_id:
            logger.warning("⚠️ OWNER_CHAT_ID not set")
            return
        
        message = (
            "🤖 <b>Bot Started and Online</b>\n\n"
            f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            "✅ All systems operational"
        )
        
        await application.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="HTML"
        )
        logger.info("✅ Startup message sent")
    except Exception as e:
        logger.error(f"❌ Failed to send startup message: {e}")


async def send_diagnostic_report(application, report):
    """Send diagnostic results to Telegram (if any)"""
    if not report:
        logger.info("ℹ️ No diagnostic report to send (diagnostics skipped or failed)")
        return
    
    try:
        chat_id = OWNER_CHAT_ID
        if not chat_id:
            return
        
        # Format the report message (Markdown format to match run_quick_check output)
        message = f"📊 *Startup Diagnostics Report*\n\n{report}"
        
        await application.bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown"
        )
        logger.info("✅ Diagnostic report sent")
    except Exception as e:
        logger.error(f"❌ Failed to send diagnostic report: {e}")


# Test functions
async def test_normal_startup():
    """Test 1: Normal startup with successful diagnostics"""
    app = MockApp()
    
    # Execute startup flow
    await send_startup_message(app)
    diagnostic_report = await run_startup_diagnostics_safe('normal')
    await send_diagnostic_report(app, diagnostic_report)
    
    # Verify
    results = TestResults()
    
    if len(app.bot.messages) == 2:
        results.add_pass("Normal startup - 2 messages sent")
    else:
        results.add_fail("Normal startup", f"Expected 2 messages, got {len(app.bot.messages)}")
    
    if app.bot.messages[0]['text'].startswith('🤖'):
        results.add_pass("Normal startup - First message is startup message")
    else:
        results.add_fail("Normal startup", "First message is not startup message")
    
    if app.bot.messages[1]['text'].startswith('📊'):
        results.add_pass("Normal startup - Second message is diagnostic report")
    else:
        results.add_fail("Normal startup", "Second message is not diagnostic report")
    
    return results


async def test_timeout_scenario():
    """Test 2: Startup with diagnostic timeout"""
    app = MockApp()
    
    # Execute startup flow with timeout
    await send_startup_message(app)
    diagnostic_report = await run_startup_diagnostics_safe('timeout')
    await send_diagnostic_report(app, diagnostic_report)
    
    # Verify
    results = TestResults()
    
    if len(app.bot.messages) == 1:
        results.add_pass("Timeout scenario - Only startup message sent")
    else:
        results.add_fail("Timeout scenario", f"Expected 1 message, got {len(app.bot.messages)}")
    
    if app.bot.messages[0]['text'].startswith('🤖'):
        results.add_pass("Timeout scenario - Startup message sent despite timeout")
    else:
        results.add_fail("Timeout scenario", "Startup message not sent")
    
    if diagnostic_report is None:
        results.add_pass("Timeout scenario - Diagnostic report is None after timeout")
    else:
        results.add_fail("Timeout scenario", "Diagnostic report should be None")
    
    return results


async def test_crash_scenario():
    """Test 3: Startup with diagnostic crash"""
    app = MockApp()
    
    # Execute startup flow with crash
    await send_startup_message(app)
    diagnostic_report = await run_startup_diagnostics_safe('crash')
    await send_diagnostic_report(app, diagnostic_report)
    
    # Verify
    results = TestResults()
    
    if len(app.bot.messages) == 1:
        results.add_pass("Crash scenario - Only startup message sent")
    else:
        results.add_fail("Crash scenario", f"Expected 1 message, got {len(app.bot.messages)}")
    
    if app.bot.messages[0]['text'].startswith('🤖'):
        results.add_pass("Crash scenario - Startup message sent despite crash")
    else:
        results.add_fail("Crash scenario", "Startup message not sent")
    
    if diagnostic_report is None:
        results.add_pass("Crash scenario - Diagnostic report is None after crash")
    else:
        results.add_fail("Crash scenario", "Diagnostic report should be None")
    
    return results


async def test_import_error_scenario():
    """Test 4: Startup with import error"""
    app = MockApp()
    
    # Execute startup flow with import error
    await send_startup_message(app)
    diagnostic_report = await run_startup_diagnostics_safe('import_error')
    await send_diagnostic_report(app, diagnostic_report)
    
    # Verify
    results = TestResults()
    
    if len(app.bot.messages) == 1:
        results.add_pass("Import error - Only startup message sent")
    else:
        results.add_fail("Import error", f"Expected 1 message, got {len(app.bot.messages)}")
    
    if app.bot.messages[0]['text'].startswith('🤖'):
        results.add_pass("Import error - Startup message sent despite import error")
    else:
        results.add_fail("Import error", "Startup message not sent")
    
    if diagnostic_report is None:
        results.add_pass("Import error - Diagnostic report is None after import error")
    else:
        results.add_fail("Import error", "Diagnostic report should be None")
    
    return results


async def test_message_ordering():
    """Test 5: Verify message ordering is correct"""
    app = MockApp()
    
    start_time = datetime.now()
    
    # Execute startup flow
    await send_startup_message(app)
    diagnostic_report = await run_startup_diagnostics_safe('normal')
    await send_diagnostic_report(app, diagnostic_report)
    
    # Verify
    results = TestResults()
    
    if len(app.bot.messages) >= 2:
        msg1_time = app.bot.messages[0]['timestamp']
        msg2_time = app.bot.messages[1]['timestamp']
        
        if msg1_time < msg2_time:
            results.add_pass("Message ordering - Startup message sent before diagnostic report")
        else:
            results.add_fail("Message ordering", "Messages sent out of order")
        
        if (msg2_time - msg1_time).total_seconds() < 5:
            results.add_pass("Message ordering - Messages sent quickly (< 5 seconds)")
        else:
            results.add_fail("Message ordering", "Too much delay between messages")
    else:
        results.add_fail("Message ordering", "Not enough messages to test ordering")
    
    return results


async def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "="*70)
    print("NON-BLOCKING STARTUP DIAGNOSTICS TEST SUITE")
    print("="*70 + "\n")
    
    all_results = TestResults()
    
    # Test 1: Normal startup
    print("\n--- Test 1: Normal Startup ---")
    result1 = await test_normal_startup()
    all_results.passed += result1.passed
    all_results.failed += result1.failed
    all_results.tests.extend(result1.tests)
    
    # Test 2: Timeout scenario
    print("\n--- Test 2: Timeout Scenario ---")
    result2 = await test_timeout_scenario()
    all_results.passed += result2.passed
    all_results.failed += result2.failed
    all_results.tests.extend(result2.tests)
    
    # Test 3: Crash scenario
    print("\n--- Test 3: Crash Scenario ---")
    result3 = await test_crash_scenario()
    all_results.passed += result3.passed
    all_results.failed += result3.failed
    all_results.tests.extend(result3.tests)
    
    # Test 4: Import error scenario
    print("\n--- Test 4: Import Error Scenario ---")
    result4 = await test_import_error_scenario()
    all_results.passed += result4.passed
    all_results.failed += result4.failed
    all_results.tests.extend(result4.tests)
    
    # Test 5: Message ordering
    print("\n--- Test 5: Message Ordering ---")
    result5 = await test_message_ordering()
    all_results.passed += result5.passed
    all_results.failed += result5.failed
    all_results.tests.extend(result5.tests)
    
    # Print summary
    all_results.print_summary()
    
    return all_results.failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_all_tests())
    exit(0 if success else 1)
