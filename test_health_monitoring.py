#!/usr/bin/env python3
"""
Test script for PR #10 Health Monitoring System
"""

import asyncio
import os
import sys
import json
from datetime import datetime

# Set BASE_PATH
BASE_PATH = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_PATH)

# Import diagnostic modules
from system_diagnostics import (
    run_full_health_check,
    diagnose_journal_issue,
    diagnose_ml_issue,
    diagnose_disk_space_issue,
    grep_logs,
    load_journal_safe
)
from diagnostic_messages import (
    format_health_summary,
    format_issue_alert,
    format_ml_training_alert,
    get_status_emoji
)


async def test_diagnostics():
    """Test all diagnostic functions"""
    
    print("=" * 80)
    print("🏥 TESTING PR #10: INTELLIGENT HEALTH MONITORING")
    print("=" * 80)
    print()
    
    # Test 1: Load Journal
    print("📝 TEST 1: Load Journal")
    print("-" * 80)
    journal = load_journal_safe(BASE_PATH)
    if journal:
        print(f"✅ Journal loaded successfully")
        print(f"   Total trades: {journal.get('metadata', {}).get('total_trades', 0)}")
        print(f"   Trades in list: {len(journal.get('trades', []))}")
    else:
        print("⚠️ Journal not found or failed to load")
    print()
    
    # Test 2: Journal Diagnostics
    print("📝 TEST 2: Journal Diagnostics")
    print("-" * 80)
    journal_issues = await diagnose_journal_issue(BASE_PATH)
    if journal_issues:
        print(f"⚠️ Found {len(journal_issues)} journal issues:")
        for i, issue in enumerate(journal_issues, 1):
            print(f"\n  Issue #{i}:")
            print(f"    Problem: {issue.get('problem')}")
            print(f"    Root Cause: {issue.get('root_cause')}")
            print(f"    Fix: {issue.get('fix')[:100]}...")
    else:
        print("✅ No journal issues detected")
    print()
    
    # Test 3: ML Diagnostics
    print("🤖 TEST 3: ML Model Diagnostics")
    print("-" * 80)
    ml_issues = await diagnose_ml_issue(BASE_PATH)
    if ml_issues:
        print(f"⚠️ Found {len(ml_issues)} ML issues:")
        for i, issue in enumerate(ml_issues, 1):
            print(f"\n  Issue #{i}:")
            print(f"    Problem: {issue.get('problem')}")
            print(f"    Root Cause: {issue.get('root_cause')}")
            print(f"    Fix: {issue.get('fix')[:100]}...")
    else:
        print("✅ No ML issues detected")
    print()
    
    # Test 4: Disk Space
    print("💾 TEST 4: Disk Space Diagnostics")
    print("-" * 80)
    disk_issues = await diagnose_disk_space_issue(BASE_PATH)
    if disk_issues:
        print(f"⚠️ Found {len(disk_issues)} disk space issues:")
        for i, issue in enumerate(disk_issues, 1):
            print(f"\n  Issue #{i}:")
            print(f"    Problem: {issue.get('problem')}")
            print(f"    Evidence: {issue.get('evidence')}")
    else:
        print("✅ No disk space issues detected")
    print()
    
    # Test 5: Log Parsing (if log file exists)
    print("📋 TEST 5: Log Parsing")
    print("-" * 80)
    log_file = f'{BASE_PATH}/bot.log'
    if os.path.exists(log_file):
        # Test grep_logs function
        auto_signal_logs = grep_logs('auto_signal', hours=24, base_path=BASE_PATH)
        error_logs = grep_logs('ERROR', hours=24, base_path=BASE_PATH)
        
        print(f"   Log file: {log_file}")
        print(f"   Auto signal logs (24h): {len(auto_signal_logs)}")
        print(f"   Error logs (24h): {len(error_logs)}")
        
        if error_logs:
            print(f"\n   Latest error: {error_logs[-1][:200]}...")
    else:
        print("⚠️ Log file not found (will be created when bot runs)")
    print()
    
    # Test 6: Full Health Check
    print("🏥 TEST 6: Full Health Check")
    print("-" * 80)
    health_report = await run_full_health_check(BASE_PATH)
    
    print(f"   Timestamp: {health_report['timestamp']}")
    print(f"   Components checked: {len(health_report['components'])}")
    print()
    
    for component, data in health_report['components'].items():
        status = data['status']
        emoji = get_status_emoji(status)
        issues_count = len(data.get('issues', []))
        
        print(f"   {emoji} {component.upper()}: {status}")
        if issues_count > 0:
            print(f"      Issues: {issues_count}")
    
    print()
    print(f"   Summary: ✅ {health_report['summary']['healthy']} OK, "
          f"⚠️ {health_report['summary']['warning']} WARNING, "
          f"❌ {health_report['summary']['critical']} CRITICAL")
    print()
    
    # Test 7: Message Formatting
    print("💬 TEST 7: Message Formatting")
    print("-" * 80)
    
    # Format health summary
    summary_message = format_health_summary(health_report)
    print("Generated health summary message:")
    print()
    print(summary_message[:500])
    print("...")
    print()
    
    # Test alert formatting if there are issues
    if journal_issues:
        print("Generated journal alert message:")
        print()
        alert_message = format_issue_alert("TRADING JOURNAL", journal_issues[0])
        print(alert_message[:500])
        print("...")
    
    print()
    print("=" * 80)
    print("✅ ALL TESTS COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_diagnostics())
