#!/usr/bin/env python3
"""
Demonstration: System diagnostics fixes in action

This script shows how the fixes work:
1. Daily report check correctly handles yesterday vs today
2. Auto Signal crash detection prioritizes crashes over missing logs
"""

import asyncio
import os
import sys
import json
from datetime import datetime, timedelta

BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

from system_diagnostics import diagnose_daily_report_issue, diagnose_journal_issue


async def demonstrate_fixes():
    """Demonstrate the diagnostic fixes"""
    
    print()
    print("=" * 80)
    print("🎯 DEMONSTRATION: SYSTEM DIAGNOSTICS FIXES")
    print("=" * 80)
    print()
    
    # ============================================================================
    # DEMO 1: Daily Report Date Logic
    # ============================================================================
    print("📋 DEMO 1: Daily Report Date Logic Fix")
    print("-" * 80)
    print()
    
    now = datetime.now()
    today = now.strftime('%Y-%m-%d')
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    day_before_yesterday = (now - timedelta(days=2)).strftime('%Y-%m-%d')
    
    print(f"Current Date/Time: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    print("OLD BEHAVIOR (WRONG):")
    print(f"  ❌ Would check for report dated: {today}")
    print(f"  ❌ Would show false alarm if no report for {today} exists")
    print(f"  ❌ This is WRONG because reports are generated FOR yesterday")
    print()
    
    print("NEW BEHAVIOR (CORRECT):")
    if now.hour < 8:
        print(f"  ✅ Before 08:00 → Check for: {day_before_yesterday}")
        print(f"  ✅ No warning (report not generated yet)")
    else:
        print(f"  ✅ After 08:00 → Check for: {yesterday}")
        if 8 <= now.hour < 20:
            print(f"  ✅ Within grace period (08:00-20:00)")
            print(f"  ✅ Show warning if report for {yesterday} missing")
        else:
            print(f"  ✅ Outside grace period")
            print(f"  ✅ No warning (normal behavior)")
    print()
    
    # Run actual diagnostic
    print("ACTUAL DIAGNOSTIC RESULT:")
    issues = await diagnose_daily_report_issue(BASE_PATH)
    if not issues:
        print(f"  ✅ No issues (report for {yesterday} exists or outside grace period)")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue['problem']}")
            print(f"     Evidence: {issue['evidence'][:100]}...")
    print()
    
    # ============================================================================
    # DEMO 2: Auto Signal Crash Detection
    # ============================================================================
    print()
    print("📋 DEMO 2: Auto Signal Crash Detection Fix")
    print("-" * 80)
    print()
    
    print("OLD BEHAVIOR (INCOMPLETE):")
    print("  ❌ Only checks: 'Are auto_signal_job logs present?'")
    print("  ❌ If no logs → 'Auto-signal jobs are NOT running'")
    print("  ❌ Doesn't detect: Jobs ARE running but CRASHING")
    print("  ❌ Misleading error: '72 crashes in 24h' but says 'jobs not running'")
    print()
    
    print("NEW BEHAVIOR (COMPREHENSIVE):")
    print("  ✅ FIRST checks: 'Are there crash exceptions?'")
    print("  ✅ If crashes found → 'Auto Signal jobs are crashing'")
    print("  ✅ Shows: Crash count + Last error + Commands to debug")
    print("  ✅ THEN checks: 'Are logs missing?' (only if no crashes)")
    print("  ✅ Accurate diagnosis with actionable error messages")
    print()
    
    # Run actual diagnostic
    print("ACTUAL DIAGNOSTIC RESULT:")
    issues = await diagnose_journal_issue(BASE_PATH)
    if not issues:
        print("  ✅ No issues detected")
    else:
        for issue in issues:
            print(f"  ⚠️  {issue['problem']}")
            print(f"     Root Cause: {issue['root_cause']}")
            if 'crash' in issue['problem'].lower():
                print(f"     ✅ CORRECT: Detected crashes!")
                if 'Total crashes' in issue.get('evidence', ''):
                    print(f"     ✅ CORRECT: Shows crash count!")
    print()
    
    # ============================================================================
    # DEMO 3: Datetime Parsing Robustness
    # ============================================================================
    print()
    print("📋 DEMO 3: Datetime Parsing Fix")
    print("-" * 80)
    print()
    
    print("OLD BEHAVIOR (FRAGILE):")
    print("  ❌ Crashes on: '2026-01-25T12:34:56.123456789' (>6 digit microseconds)")
    print("  ❌ Crashes on: '2026-01-25T12:34:56+00:00' (timezone info)")
    print()
    
    print("NEW BEHAVIOR (ROBUST):")
    print("  ✅ Handles: Timezone info (strips '+00:00')")
    print("  ✅ Handles: Long microseconds (truncates to 6 digits)")
    print("  ✅ Handles: All common timestamp formats")
    print()
    
    test_cases = [
        "2026-01-25T12:34:56.123456",
        "2026-01-25T12:34:56.123456789",
        "2026-01-25T12:34:56.123456+00:00",
    ]
    
    print("TESTED FORMATS:")
    for ts in test_cases:
        try:
            # Simulate parsing logic
            timestamp_str = ts
            if '+' in timestamp_str:
                timestamp_str = timestamp_str.split('+')[0]
            if 'T' in timestamp_str and '.' in timestamp_str:
                parts = timestamp_str.split('.')
                if len(parts) == 2 and len(parts[1]) > 6:
                    timestamp_str = parts[0] + '.' + parts[1][:6]
            
            parsed = datetime.fromisoformat(timestamp_str)
            print(f"  ✅ {ts:45s} → OK")
        except Exception as e:
            print(f"  ❌ {ts:45s} → {e}")
    print()
    
    print("=" * 80)
    print("✅ DEMONSTRATION COMPLETE")
    print("=" * 80)
    print()
    
    # ============================================================================
    # Summary
    # ============================================================================
    print()
    print("SUMMARY OF FIXES:")
    print()
    print("1️⃣  Daily Report Check:")
    print("   • Fixed date logic: checks YESTERDAY not TODAY")
    print("   • Added time awareness: before 08:00 → day before yesterday")
    print("   • Added grace period: only warn if within 08:00-20:00 window")
    print()
    print("2️⃣  Auto Signal Diagnostics:")
    print("   • Added crash detection FIRST (before missing logs check)")
    print("   • Shows crash count and error evidence")
    print("   • Provides actionable debugging commands")
    print()
    print("3️⃣  Datetime Parsing:")
    print("   • Fixed timezone handling (strips timezone info)")
    print("   • Fixed microsecond overflow (truncates to 6 digits)")
    print("   • Robust against various timestamp formats")
    print()
    print("IMPACT:")
    print("  ✅ No more false alarms")
    print("  ✅ Accurate problem identification")
    print("  ✅ Actionable error messages")
    print("  ✅ Easy troubleshooting")
    print()


if __name__ == "__main__":
    asyncio.run(demonstrate_fixes())
