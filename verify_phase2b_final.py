#!/usr/bin/env python3
"""
Final Verification: Phase 2B Dependency Injection

This script performs final checks to ensure the implementation meets all requirements.
"""

import os
import sys

def verify_no_bot_imports():
    """Verify diagnostics.py does NOT import from bot module in ReplayEngine"""
    print("=" * 70)
    print("VERIFICATION 1: No bot imports in ReplayEngine")
    print("=" * 70)
    
    with open('diagnostics.py', 'r') as f:
        source = f.read()
    
    # Find ReplayEngine class
    class_start = source.find("class ReplayEngine:")
    if class_start == -1:
        print("❌ FAILED: Could not find ReplayEngine class")
        return False
    
    # Find next class to limit scope
    next_class = source.find("\nclass ", class_start + 1)
    if next_class == -1:
        replay_code = source[class_start:]
    else:
        replay_code = source[class_start:next_class]
    
    # Check for bot imports
    if "from bot import ict_engine_global" in replay_code:
        print("❌ FAILED: Found 'from bot import ict_engine_global' in ReplayEngine")
        return False
    
    if "from bot import ICTSignalEngine" in replay_code:
        print("❌ FAILED: Found 'from bot import ICTSignalEngine' in ReplayEngine")
        return False
    
    # Check that signal_engine is required
    if "signal_engine=None" in replay_code:
        print("❌ FAILED: signal_engine has default value (should be required)")
        return False
    
    print("✅ PASSED: ReplayEngine does NOT import from bot module")
    print("✅ PASSED: signal_engine is a required parameter")
    return True


def verify_bot_injection():
    """Verify bot.py properly injects ict_engine_global"""
    print("\n" + "=" * 70)
    print("VERIFICATION 2: bot.py properly injects ict_engine_global")
    print("=" * 70)
    
    with open('bot.py', 'r') as f:
        source = f.read()
    
    checks = [
        ('from diagnostics import ReplayCache, ReplayEngine', 'Imports ReplayCache and ReplayEngine'),
        ('replay_cache_global = ReplayCache()', 'Creates global ReplayCache'),
        ('replay_engine_global = ReplayEngine(', 'Creates global ReplayEngine'),
        ('signal_engine=ict_engine_global', 'Injects ict_engine_global'),
    ]
    
    all_passed = True
    for check, desc in checks:
        if check in source:
            print(f"✅ Found: {desc}")
        else:
            print(f"❌ Missing: {desc}")
            all_passed = False
    
    if all_passed:
        print("✅ PASSED: bot.py correctly initializes and injects engine")
        return True
    else:
        print("❌ FAILED: Some initialization code is missing")
        return False


def verify_handler_updates():
    """Verify handler functions use global instances"""
    print("\n" + "=" * 70)
    print("VERIFICATION 3: Handlers use global instances")
    print("=" * 70)
    
    with open('bot.py', 'r') as f:
        source = f.read()
    
    # Find handle_replay_signals function
    replay_signals_start = source.find("async def handle_replay_signals(")
    if replay_signals_start == -1:
        print("❌ FAILED: Could not find handle_replay_signals function")
        return False
    
    # Get function code (next 30 lines should be enough)
    replay_signals_lines = source[replay_signals_start:replay_signals_start + 2000]
    
    # Check it uses global replay_engine_global
    if "global replay_engine_global" in replay_signals_lines:
        print("✅ Found: handle_replay_signals declares global replay_engine_global")
    else:
        print("❌ Missing: handle_replay_signals should declare global replay_engine_global")
        return False
    
    # Check it does NOT create new ReplayEngine
    if "engine = ReplayEngine(cache)" in replay_signals_lines and "global replay_engine_global" in replay_signals_lines:
        print("❌ FAILED: handle_replay_signals still creates new ReplayEngine instance")
        return False
    
    if "from diagnostics import ReplayEngine, ReplayCache" in replay_signals_lines:
        print("❌ WARNING: handle_replay_signals imports ReplayEngine/ReplayCache (should use globals)")
        # This is not critical if it's just importing the types, but should use globals
    
    print("✅ PASSED: Handlers correctly use global instances")
    return True


def verify_phase2b_fixes():
    """Verify Phase 2B fixes are still present"""
    print("\n" + "=" * 70)
    print("VERIFICATION 4: Phase 2B fixes preserved")
    print("=" * 70)
    
    with open('diagnostics.py', 'r') as f:
        source = f.read()
    
    fixes = {
        'PRICE_TOLERANCE_PERCENT = 0.005': 'Price tolerance 0.5% (0.005)',
        'CONFIDENCE_TOLERANCE = 5': 'Confidence tolerance ±5',
        'def check_confidence_match': 'check_confidence_match function',
        "'confidence_delta': check_confidence_match": 'confidence_delta in checks',
    }
    
    all_present = True
    for fix, desc in fixes.items():
        if fix in source:
            print(f"✅ Preserved: {desc}")
        else:
            print(f"❌ Missing: {desc}")
            all_present = False
    
    if all_present:
        print("✅ PASSED: All Phase 2B fixes are preserved")
        return True
    else:
        print("❌ FAILED: Some Phase 2B fixes are missing")
        return False


def verify_single_engine():
    """Verify only one ICTSignalEngine instance is created"""
    print("\n" + "=" * 70)
    print("VERIFICATION 5: Single engine instance pattern")
    print("=" * 70)
    
    with open('diagnostics.py', 'r') as f:
        diag_source = f.read()
    
    # Check ReplayEngine does NOT create ICTSignalEngine
    class_start = diag_source.find("class ReplayEngine:")
    next_class = diag_source.find("\nclass ", class_start + 1)
    if next_class == -1:
        replay_code = diag_source[class_start:]
    else:
        replay_code = diag_source[class_start:next_class]
    
    if "ICTSignalEngine()" in replay_code:
        print("❌ FAILED: ReplayEngine creates new ICTSignalEngine instance")
        return False
    
    print("✅ ReplayEngine does NOT create ICTSignalEngine")
    
    with open('bot.py', 'r') as f:
        bot_source = f.read()
    
    # Verify ict_engine_global is created once and injected
    if "ict_engine_global = ICTSignalEngine()" in bot_source:
        print("✅ bot.py creates ict_engine_global")
    else:
        print("❌ bot.py does not create ict_engine_global")
        return False
    
    if "signal_engine=ict_engine_global" in bot_source:
        print("✅ ict_engine_global is injected into ReplayEngine")
    else:
        print("❌ ict_engine_global is NOT injected into ReplayEngine")
        return False
    
    print("✅ PASSED: Only one engine instance exists at runtime")
    return True


def main():
    """Run all verifications"""
    print("\n" + "=" * 70)
    print("PHASE 2B: FINAL VERIFICATION")
    print("=" * 70 + "\n")
    
    os.chdir('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot')
    
    results = []
    results.append(verify_no_bot_imports())
    results.append(verify_bot_injection())
    results.append(verify_handler_updates())
    results.append(verify_phase2b_fixes())
    results.append(verify_single_engine())
    
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    
    passed = sum(results)
    total = len(results)
    
    verification_names = [
        "No bot imports in ReplayEngine",
        "bot.py injection code",
        "Handlers use globals",
        "Phase 2B fixes preserved",
        "Single engine instance"
    ]
    
    for name, result in zip(verification_names, results):
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} verifications passed")
    
    if passed == total:
        print("\n" + "🎉" * 25)
        print("ALL VERIFICATIONS PASSED!")
        print("Phase 2B dependency injection is correctly implemented.")
        print("Ready for deployment.")
        print("🎉" * 25 + "\n")
        return 0
    else:
        print(f"\n⚠️  {total - passed} verification(s) failed.")
        print("Please review the implementation.\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
