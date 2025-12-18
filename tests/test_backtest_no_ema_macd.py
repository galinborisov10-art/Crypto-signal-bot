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
    
    banned_patterns = [
        'ema', 'macd', 'ewm', 
        'exponential moving average',
        '.ewm(', 'df.ewm', 'pd.ewm'
    ]
    all_passed = True
    
    for filename in files_to_check:
        filepath = Path(__file__).parent.parent / filename
        
        if not filepath.exists():
            print(f"⏭️  Skipping {filename} (doesn't exist)")
            continue
        
        with open(filepath, 'r') as f:
            lines = f.readlines()
        
        found_issues = []
        for line_num, line in enumerate(lines, 1):
            # Skip comments and docstrings
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            
            # Check for banned terms (case insensitive)
            line_lower = line.lower()
            for term in banned_patterns:
                if term in line_lower:
                    # Additional checks to avoid false positives
                    # Skip if it's part of a longer word (e.g., "Manager" contains "ema")
                    if term in ['ema', 'macd']:
                        # Check if it's a standalone usage (calculation or variable)
                        if f"'{term}'" in line_lower or f'"{term}"' in line_lower:
                            # It's in quotes, likely a column name - this is OK in comments/docs
                            continue
                        if f'_{term}' in line_lower or f'{term}_' in line_lower or f'{term}(' in line_lower:
                            found_issues.append(f"Line {line_num}: {line.strip()}")
                    else:
                        found_issues.append(f"Line {line_num}: {line.strip()}")
        
        if found_issues:
            print(f"❌ FAILED: {filename}")
            for issue in found_issues[:5]:  # Show first 5 issues
                print(f"   - {issue}")
            if len(found_issues) > 5:
                print(f"   - ... and {len(found_issues) - 5} more")
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

if __name__ == "__main__":
    test1 = test_no_ema_macd_in_files()
    test2 = test_uses_ict_engine()
    
    if test1 and test2:
        print("\n🎉 All tests PASSED!")
        sys.exit(0)
    else:
        print("\n❌ Some tests FAILED!")
        sys.exit(1)
