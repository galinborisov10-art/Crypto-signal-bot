#!/usr/bin/env python3
"""
Production Verification Script for LuxAlgo Integration Fix

This script verifies that the fix is working correctly in production.
Run this after deployment to ensure:
1. No NoneType errors in recent logs
2. LuxAlgo is producing valid results
3. Structured logging is present
4. BUY/SELL signals are being generated (when market allows)
"""

import sys
import subprocess
from datetime import datetime

def check_log_for_errors(log_file='bot.log', lines=1000):
    """Check for NoneType errors in recent logs"""
    print(f"\n{'='*70}")
    print("1. CHECKING FOR NONETYPE ERRORS IN LAST {lines} LINES")
    print('='*70)
    
    try:
        result = subprocess.run(
            ['tail', f'-{lines}', log_file],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"⚠️  Could not read log file: {log_file}")
            return
        
        log_content = result.stdout
        
        # Check for NoneType errors
        nonetype_errors = [line for line in log_content.split('\n') if "NoneType" in line]
        luxalgo_errors = [line for line in nonetype_errors if "luxalgo" in line.lower() or "LuxAlgo" in line]
        
        print(f"Total NoneType errors found: {len(nonetype_errors)}")
        print(f"LuxAlgo-related NoneType errors: {len(luxalgo_errors)}")
        
        if len(luxalgo_errors) == 0:
            print("✅ PASS: No LuxAlgo NoneType errors found")
        else:
            print(f"❌ FAIL: Found {len(luxalgo_errors)} LuxAlgo NoneType errors")
            print("\nFirst 3 errors:")
            for error in luxalgo_errors[:3]:
                print(f"  - {error[:100]}...")
        
    except Exception as e:
        print(f"⚠️  Error checking logs: {e}")


def check_luxalgo_logging(log_file='bot.log', lines=500):
    """Check for new LuxAlgo structured logging"""
    print(f"\n{'='*70}")
    print(f"2. CHECKING FOR LUXALGO STRUCTURED LOGGING IN LAST {lines} LINES")
    print('='*70)
    
    try:
        result = subprocess.run(
            ['tail', f'-{lines}', log_file],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"⚠️  Could not read log file: {log_file}")
            return
        
        log_content = result.stdout
        
        # Check for new logging format
        luxalgo_results = [line for line in log_content.split('\n') if "LuxAlgo result:" in line]
        
        print(f"LuxAlgo result logs found: {len(luxalgo_results)}")
        
        if len(luxalgo_results) > 0:
            print("✅ PASS: New structured logging is present")
            print("\nRecent LuxAlgo results:")
            for log in luxalgo_results[-3:]:
                print(f"  - {log.split('LuxAlgo result:')[1].strip()}")
        else:
            print("⚠️  WARNING: No LuxAlgo result logs found (bot may not have run yet)")
        
    except Exception as e:
        print(f"⚠️  Error checking logs: {e}")


def check_signal_generation(log_file='bot.log', lines=1000):
    """Check for BUY/SELL signal generation"""
    print(f"\n{'='*70}")
    print(f"3. CHECKING SIGNAL GENERATION IN LAST {lines} LINES")
    print('='*70)
    
    try:
        result = subprocess.run(
            ['tail', f'-{lines}', log_file],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode != 0:
            print(f"⚠️  Could not read log file: {log_file}")
            return
        
        log_content = result.stdout
        
        # Count signal types
        buy_signals = len([line for line in log_content.split('\n') if "Generated BUY signal" in line])
        sell_signals = len([line for line in log_content.split('\n') if "Generated SELL signal" in line])
        hold_signals = len([line for line in log_content.split('\n') if "Generated HOLD signal" in line])
        
        total_signals = buy_signals + sell_signals + hold_signals
        
        print(f"BUY signals:  {buy_signals}")
        print(f"SELL signals: {sell_signals}")
        print(f"HOLD signals: {hold_signals}")
        print(f"Total signals: {total_signals}")
        
        if total_signals == 0:
            print("⚠️  WARNING: No signals generated (bot may not have run yet)")
        elif buy_signals + sell_signals == 0:
            print("⚠️  WARNING: Only HOLD signals generated (check market conditions)")
        else:
            diversity = ((buy_signals + sell_signals) / total_signals) * 100
            print(f"✅ PASS: Signal diversity: {diversity:.1f}% actionable signals")
        
    except Exception as e:
        print(f"⚠️  Error checking logs: {e}")


def run_unit_tests():
    """Run the unit tests"""
    print(f"\n{'='*70}")
    print("4. RUNNING UNIT TESTS")
    print('='*70)
    
    try:
        result = subprocess.run(
            ['python3', '-m', 'pytest', 'test_luxalgo_integration_fix.py', '-v'],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        # Check for passed tests
        if "6 passed" in result.stdout:
            print("✅ PASS: All 6 unit tests passed")
        else:
            print("❌ FAIL: Some tests failed")
            print(result.stdout)
        
    except Exception as e:
        print(f"⚠️  Error running tests: {e}")


def main():
    """Main verification function"""
    print("\n" + "="*70)
    print("LUXALGO INTEGRATION FIX - PRODUCTION VERIFICATION")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*70)
    
    # Run all checks
    check_log_for_errors()
    check_luxalgo_logging()
    check_signal_generation()
    run_unit_tests()
    
    # Final summary
    print(f"\n{'='*70}")
    print("VERIFICATION COMPLETE")
    print('='*70)
    print("\nNext steps:")
    print("1. Review any warnings or failures above")
    print("2. Monitor logs for 'LuxAlgo result:' entries")
    print("3. Confirm BUY/SELL signals are generated when market allows")
    print("4. Report any issues to the development team")
    print()


if __name__ == '__main__':
    main()
