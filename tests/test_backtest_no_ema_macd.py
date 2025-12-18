"""
Test: Verify backtest doesn't use EMA/MACD
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

def test_no_ema_macd_in_files():
    """Verify no EMA/MACD in backtest files"""
    print("🧪 Testing: Backtest WITHOUT EMA/MACD\n")
    
    files_to_check = [
        'ict_backtest.py',
        'hybrid_backtest.py',
        'ict_signal_engine.py'
    ]
    
    banned_terms = ['ema', 'macd', 'ewm']
    # Exclude patterns that contain banned terms but are not indicators
    exclude_patterns = ['schema', 'remark', 'remain', 'cachemanager', 'no ema', 'no macd', 'critical: no ema/macd']
    all_passed = True
    
    for filename in files_to_check:
        filepath = Path(__file__).parent.parent / filename
        
        if not filepath.exists():
            print(f"⏭️  Skipping {filename} (doesn't exist)")
            continue
        
        with open(filepath, 'r') as f:
            content = f.read().lower()
        
        found_issues = []
        for term in banned_terms:
            # Count occurrences but exclude comments that say "NO EMA/MACD"
            lines = content.split('\n')
            count = 0
            for line in lines:
                if term in line.lower():
                    # Skip if line contains any exclude pattern
                    if any(pattern in line.lower() for pattern in exclude_patterns):
                        continue
                    count += 1
            
            if count > 0:
                found_issues.append(f"Found '{term}' {count} times")
        
        if found_issues:
            print(f"❌ FAILED: {filename}")
            for issue in found_issues:
                print(f"   - {issue}")
            all_passed = False
        else:
            print(f"✅ PASSED: {filename} - No EMA/MACD")
    
    return all_passed

def test_uses_ict_engine():
    """Verify backtest uses ICT Engine"""
    print("\n🧪 Testing: Uses ICT Engine\n")
    
    files_to_check = ['ict_backtest.py', 'hybrid_backtest.py']
    found_ict = False
    
    for filename in files_to_check:
        filepath = Path(__file__).parent.parent / filename
        
        if not filepath.exists():
            continue
        
        with open(filepath, 'r') as f:
            content = f.read()
        
        if 'ICTSignalEngine' in content:
            print(f"✅ PASSED: {filename} uses ICT Signal Engine")
            found_ict = True
    
    if not found_ict:
        print("❌ FAILED: ICT Signal Engine not found")
    
    return found_ict

def test_has_80_alert_integration():
    """Verify 80% TP alert system is integrated"""
    print("\n🧪 Testing: 80% TP Alert Integration\n")
    
    filepath = Path(__file__).parent.parent / 'ict_backtest.py'
    
    if not filepath.exists():
        print("❌ FAILED: ict_backtest.py not found")
        return False
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    required_features = [
        'ICT80AlertHandler',
        'alerts_80',
        'final_alerts',
        'percent_to_tp',
        'save_backtest_results'
    ]
    
    all_found = True
    for feature in required_features:
        if feature in content:
            print(f"✅ Found: {feature}")
        else:
            print(f"❌ Missing: {feature}")
            all_found = False
    
    return all_found

if __name__ == "__main__":
    test1 = test_no_ema_macd_in_files()
    test2 = test_uses_ict_engine()
    test3 = test_has_80_alert_integration()
    
    print("\n" + "=" * 50)
    if test1 and test2 and test3:
        print("🎉 All tests PASSED!")
        sys.exit(0)
    else:
        print("❌ Some tests FAILED!")
        sys.exit(1)
