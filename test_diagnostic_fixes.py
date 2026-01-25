#!/usr/bin/env python3
"""
Test script for PR: Fix system diagnostics false alarms
Tests the fixes for:
1. Daily report date logic (checks yesterday, not today)
2. Auto Signal crash detection (checks for crashes before missing logs)
"""

import asyncio
import os
import sys
import json
from datetime import datetime, timedelta

# Set BASE_PATH
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

# Import diagnostic modules
from system_diagnostics import (
    diagnose_daily_report_issue,
    diagnose_journal_issue,
    grep_logs
)


async def test_daily_report_date_logic():
    """Test that daily report check looks for yesterday's date, not today's"""
    
    print("=" * 80)
    print("🧪 TEST 1: Daily Report Date Logic")
    print("=" * 80)
    print()
    
    # Get current time
    now = datetime.now()
    yesterday = (now - timedelta(days=1)).strftime('%Y-%m-%d')
    day_before_yesterday = (now - timedelta(days=2)).strftime('%Y-%m-%d')
    
    print(f"📅 Current date: {now.strftime('%Y-%m-%d')}")
    print(f"📅 Current time: {now.strftime('%H:%M:%S')}")
    print(f"📅 Yesterday: {yesterday}")
    print(f"📅 Day before yesterday: {day_before_yesterday}")
    print()
    
    # Determine expected date to check
    if now.hour < 8:
        expected_date = day_before_yesterday
        print(f"⏰ Before 08:00 → Should check for: {expected_date}")
    else:
        expected_date = yesterday
        print(f"⏰ After 08:00 → Should check for: {expected_date}")
    print()
    
    # Run the diagnostic
    issues = await diagnose_daily_report_issue(BASE_PATH)
    
    if not issues:
        print(f"✅ SUCCESS: No issues found (report for {expected_date} exists)")
    else:
        print(f"⚠️  Issues found:")
        for issue in issues:
            print(f"   Problem: {issue['problem']}")
            print(f"   Evidence: {issue['evidence']}")
            
            # Verify the error message mentions the correct date
            if yesterday in issue['problem'] or yesterday in issue['evidence']:
                print(f"✅ CORRECT: Error mentions yesterday ({yesterday})")
            else:
                print(f"❌ WRONG: Error doesn't mention yesterday ({yesterday})")
    
    print()
    print("-" * 80)
    print()
    
    return issues


async def test_auto_signal_crash_detection():
    """Test that journal diagnostic checks for crashes BEFORE missing logs"""
    
    print("=" * 80)
    print("🧪 TEST 2: Auto Signal Crash Detection")
    print("=" * 80)
    print()
    
    # Check for Auto Signal crashes in logs
    auto_signal_errors = grep_logs('Auto Signal.*raised an exception', hours=24, base_path=BASE_PATH)
    
    if auto_signal_errors:
        print(f"🔍 Found {len(auto_signal_errors)} Auto Signal crashes in last 24h")
        print(f"   Last crash: {auto_signal_errors[-1][:150]}...")
        print()
    else:
        print("✅ No Auto Signal crashes detected in last 24h")
        print()
    
    # Run the journal diagnostic
    issues = await diagnose_journal_issue(BASE_PATH)
    
    if not issues:
        print("✅ No journal issues detected")
    else:
        print(f"⚠️  Found {len(issues)} journal issues:")
        for i, issue in enumerate(issues, 1):
            print(f"\n  Issue #{i}:")
            print(f"    Problem: {issue['problem']}")
            print(f"    Root Cause: {issue['root_cause']}")
            
            # Check if crash detection is working
            if auto_signal_errors and 'crashing' in issue['problem'].lower():
                print("    ✅ CORRECT: Issue mentions crashes (not just 'not running')")
                if 'Total crashes' in issue['evidence']:
                    print("    ✅ CORRECT: Evidence includes crash count")
            elif auto_signal_errors and 'NOT running' in issue['root_cause']:
                print("    ❌ WRONG: Should detect crashes, not just 'not running'")
            
            print(f"    Evidence: {issue['evidence'][:200]}...")
    
    print()
    print("-" * 80)
    print()
    
    return issues


async def test_datetime_parsing():
    """Test that datetime parsing handles timezone info correctly"""
    
    print("=" * 80)
    print("🧪 TEST 3: Datetime Parsing with Timezone Info")
    print("=" * 80)
    print()
    
    # Test various timestamp formats
    test_timestamps = [
        "2026-01-25T12:34:56.123456",
        "2026-01-25T12:34:56.123456789",  # More than 6 digits
        "2026-01-25T12:34:56.123456+00:00",  # With timezone
        "2026-01-25 12:34:56",  # Simple format
    ]
    
    for ts in test_timestamps:
        try:
            # Simulate the parsing logic
            timestamp_str = ts
            if '+' in timestamp_str:
                timestamp_str = timestamp_str.split('+')[0]
            if 'T' in timestamp_str and '.' in timestamp_str:
                parts = timestamp_str.split('.')
                if len(parts) == 2 and len(parts[1]) > 6:
                    timestamp_str = parts[0] + '.' + parts[1][:6]
            
            parsed = datetime.fromisoformat(timestamp_str)
            print(f"✅ Parsed: {ts[:50]:50s} → {parsed}")
        except Exception as e:
            print(f"❌ Failed: {ts[:50]:50s} → {e}")
    
    print()
    print("-" * 80)
    print()


async def main():
    """Run all tests"""
    
    print()
    print("=" * 80)
    print("🏥 TESTING SYSTEM DIAGNOSTICS FIXES")
    print("=" * 80)
    print()
    
    # Test 1: Daily report date logic
    await test_daily_report_date_logic()
    
    # Test 2: Auto Signal crash detection
    await test_auto_signal_crash_detection()
    
    # Test 3: Datetime parsing
    await test_datetime_parsing()
    
    print()
    print("=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)
    print()


if __name__ == "__main__":
    asyncio.run(main())
