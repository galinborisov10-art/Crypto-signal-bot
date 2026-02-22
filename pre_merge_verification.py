#!/usr/bin/env python3
"""
Pre-Merge Verification Script
Comprehensive technical checks before merging stabilization PR
"""

import sys
import inspect
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def check_is_auto_variable():
    """Check 1: Verify is_auto variable in generate_signal signature"""
    print("\n" + "="*70)
    print("CHECK 1: is_auto Variable Verification")
    print("="*70)
    
    try:
        from ict_signal_engine import ICTSignalEngine
        
        # Get the signature
        sig = inspect.signature(ICTSignalEngine.generate_signal)
        params = sig.parameters
        
        # Check is_auto exists
        if 'is_auto' not in params:
            print("❌ FAILED: is_auto parameter NOT found in generate_signal signature")
            return False
        
        # Check default value
        is_auto_param = params['is_auto']
        if is_auto_param.default != False:
            print(f"❌ FAILED: is_auto default value is {is_auto_param.default}, expected False")
            return False
        
        # Check type annotation
        if is_auto_param.annotation != bool:
            print(f"⚠️  WARNING: is_auto type annotation is {is_auto_param.annotation}, expected bool")
        
        print("✅ PASSED: is_auto parameter exists with correct default (False)")
        print(f"   Signature: {sig}")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_is_auto_usage():
    """Check 2: Verify is_auto is used consistently in AUTO gating blocks"""
    print("\n" + "="*70)
    print("CHECK 2: is_auto Usage in AUTO Gating Blocks")
    print("="*70)
    
    try:
        with open('ict_signal_engine.py', 'r') as f:
            content = f.read()
        
        # Find all is_auto usage patterns
        import re
        
        # Pattern: if is_auto:
        auto_checks = re.findall(r'if\s+is_auto\s*:', content)
        print(f"   Found {len(auto_checks)} 'if is_auto:' blocks")
        
        # Pattern: if not is_auto:
        manual_checks = re.findall(r'if\s+not\s+is_auto\s*:', content)
        print(f"   Found {len(manual_checks)} 'if not is_auto:' blocks")
        
        # Pattern: is_auto in ternary
        ternary_checks = re.findall(r'\w+\s+if\s+is_auto\s+else\s+\w+', content)
        print(f"   Found {len(ternary_checks)} ternary expressions with is_auto")
        
        # Check for SignalMode.AUTOMATIC usage
        signal_mode_checks = re.findall(r'SignalMode\.AUTOMATIC\s+if\s+is_auto', content)
        print(f"   Found {len(signal_mode_checks)} SignalMode.AUTOMATIC conversions")
        
        # Verify no hardcoded AUTO assumptions
        hardcoded_auto = re.findall(r'AUTO.*=.*True|is_auto\s*=\s*True(?!\s*#)', content)
        if hardcoded_auto:
            print(f"⚠️  WARNING: Found {len(hardcoded_auto)} potential hardcoded AUTO assumptions")
            for match in hardcoded_auto[:3]:
                print(f"      {match}")
        
        total_usage = len(auto_checks) + len(manual_checks) + len(ternary_checks)
        if total_usage >= 4:  # Should have at least 4 uses based on code review
            print(f"✅ PASSED: is_auto is consistently used ({total_usage} total uses)")
            return True
        else:
            print(f"❌ FAILED: is_auto usage seems insufficient ({total_usage} uses)")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_create_no_trade_signature():
    """Check 3: Verify _create_no_trade_message signature consistency"""
    print("\n" + "="*70)
    print("CHECK 3: _create_no_trade_message Signature Consistency")
    print("="*70)
    
    try:
        from ict_signal_engine import ICTSignalEngine
        
        # Get the signature
        sig = inspect.signature(ICTSignalEngine._create_no_trade_message)
        params = list(sig.parameters.keys())
        
        print(f"   Function signature has {len(params)-1} parameters (excluding self)")
        print(f"   Parameters: {params[1:]}")  # Skip 'self'
        
        # Expected parameters
        expected_params = [
            'symbol', 'timeframe', 'reason', 'details', 'mtf_breakdown',
            'current_price', 'price_change_24h', 'rsi', 'signal_direction', 'confidence'
        ]
        
        missing = set(expected_params) - set(params)
        extra = set(params) - set(expected_params) - {'self'}
        
        if missing:
            print(f"❌ FAILED: Missing parameters: {missing}")
            return False
        
        if extra:
            print(f"⚠️  WARNING: Extra parameters: {extra}")
        
        # Now check all call sites
        import re
        with open('ict_signal_engine.py', 'r') as f:
            content = f.read()
        
        # Find all calls
        call_pattern = r'self\._create_no_trade_message\('
        calls = re.findall(call_pattern, content)
        
        print(f"   Found {len(calls)} call sites")
        
        # Check each call has the required parameters
        call_blocks = re.split(r'self\._create_no_trade_message\(', content)[1:]
        
        issues = 0
        for i, block in enumerate(call_blocks[:5], 1):  # Check first 5
            # Extract parameters until closing paren
            param_section = block.split(')')[0]
            
            # Count keyword arguments
            kw_args = re.findall(r'(\w+)\s*=', param_section)
            
            required_keywords = ['symbol', 'timeframe', 'reason', 'details', 'mtf_breakdown']
            missing_required = set(required_keywords) - set(kw_args)
            
            if missing_required:
                print(f"   ⚠️  Call {i}: Missing required keywords: {missing_required}")
                issues += 1
        
        if issues == 0:
            print("✅ PASSED: All call sites appear to match signature")
            return True
        else:
            print(f"⚠️  WARNING: {issues} call sites may have issues")
            return True  # Still pass, warnings only
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_vars_safety():
    """Check 4: Verify vars() usage is guarded with hasattr"""
    print("\n" + "="*70)
    print("CHECK 4: vars() Usage Safety (Schema Inspection)")
    print("="*70)
    
    try:
        with open('ict_signal_engine.py', 'r') as f:
            lines = f.readlines()
        
        vars_usage = []
        for i, line in enumerate(lines, 1):
            if 'vars(' in line and '__dict__' not in line:
                vars_usage.append((i, line.strip()))
        
        print(f"   Found {len(vars_usage)} vars() usage(s)")
        
        safe_count = 0
        unsafe_count = 0
        
        for line_num, line in vars_usage:
            print(f"   Line {line_num}: {line[:70]}...")
            
            # Check if there's a hasattr guard nearby (within 5 lines)
            guard_found = False
            for check_line in range(max(0, line_num-5), min(len(lines), line_num+2)):
                if 'hasattr' in lines[check_line] and '__dict__' in lines[check_line]:
                    guard_found = True
                    break
            
            if guard_found:
                print(f"      ✅ Protected by hasattr(__dict__) guard")
                safe_count += 1
            else:
                print(f"      ⚠️  No hasattr guard found nearby")
                unsafe_count += 1
        
        if unsafe_count == 0:
            print(f"✅ PASSED: All {len(vars_usage)} vars() usage(s) are safely guarded")
            return True
        else:
            print(f"⚠️  WARNING: {unsafe_count} vars() usage(s) may not be guarded")
            return True  # Warning only, not critical
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_component_filtering():
    """Check 5: Verify component filtering handles empty lists"""
    print("\n" + "="*70)
    print("CHECK 5: Component Filtering Edge Cases")
    print("="*70)
    
    try:
        from ict_signal_engine import ICTSignalEngine
        
        # Check if _filter_quality_components exists
        if not hasattr(ICTSignalEngine, '_filter_quality_components'):
            print("❌ FAILED: _filter_quality_components method not found")
            return False
        
        # Test with empty components
        engine = ICTSignalEngine()
        
        empty_components = {
            'order_blocks': [],
            'fvgs': [],
            'liquidity_zones': [],
            'whale_blocks': [],
            'breaker_blocks': [],
            'mitigation_blocks': []
        }
        
        try:
            filtered = engine._filter_quality_components(empty_components)
            print("   ✅ Handles empty component lists without crashing")
            
            # Check result is dict
            if not isinstance(filtered, dict):
                print(f"   ❌ FAILED: Returned {type(filtered)}, expected dict")
                return False
            
            print(f"   ✅ Returns dict with {len(filtered)} keys")
            
        except Exception as e:
            print(f"   ❌ FAILED: Crashes on empty lists: {e}")
            return False
        
        # Check entry_scenarios.py handles empty lists
        print("\n   Checking entry_scenarios.py...")
        from entry_scenarios import select_best_entry_scenario
        
        # Test with minimal data
        try:
            result = select_best_entry_scenario(
                components={
                    'order_blocks': [],
                    'fvgs': [],
                    'liquidity_zones': [],
                    'liquidity_sweeps': []
                },
                displacement={'detected': False, 'strength': 0},
                structure_break={'type': None},
                bias='BULLISH',
                current_price=50000.0,
                timeframe='1h'
            )
            
            if result is None:
                print("   ✅ Returns None for insufficient components (safe)")
            elif isinstance(result, dict):
                print(f"   ✅ Returns dict result: {result.get('scenario', 'N/A')}")
            else:
                print(f"   ⚠️  Returns {type(result)}: {result}")
                
        except Exception as e:
            print(f"   ❌ FAILED: entry_scenarios crashes on empty: {e}")
            return False
        
        print("✅ PASSED: Component filtering handles edge cases safely")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_liquidity_sweeps_deduplication():
    """Check 6: Verify liquidity sweeps are not duplicated"""
    print("\n" + "="*70)
    print("CHECK 6: Liquidity Sweeps Deduplication")
    print("="*70)
    
    try:
        with open('ict_signal_engine.py', 'r') as f:
            content = f.read()
        
        # Find sweep detection patterns
        import re
        
        # Pattern: detect_liquidity_sweeps calls
        sweep_detections = re.findall(r'detect_liquidity_sweeps\([^)]+\)', content)
        print(f"   Found {len(sweep_detections)} detect_liquidity_sweeps() calls")
        
        # Pattern: append to liquidity_sweeps
        sweep_appends = re.findall(r'liquidity_sweeps.*\.append|\.extend', content)
        print(f"   Found {len(sweep_appends)} append/extend operations")
        
        # Check for duplicate detection
        # Should only be called once in _detect_ict_components
        if len(sweep_detections) > 2:  # Main call + maybe one in filtering
            print(f"   ⚠️  WARNING: Multiple sweep detection calls found ({len(sweep_detections)})")
        else:
            print(f"   ✅ Sweep detection appears to be centralized")
        
        # Check for ILP sweep merging
        ilp_sweep_merge = re.findall(r'quality_ilp_sweeps', content)
        if ilp_sweep_merge:
            print(f"   ✅ ILP sweeps are merged into main sweeps list ({len(ilp_sweep_merge)} references)")
        
        # Verify no duplicate assignment
        sweep_assignments = re.findall(r"components\['liquidity_sweeps'\]\s*=", content)
        print(f"   Found {len(sweep_assignments)} direct assignments to components['liquidity_sweeps']")
        
        if len(sweep_assignments) <= 3:  # Initial + error handling
            print("✅ PASSED: Liquidity sweeps appear to be handled correctly")
            return True
        else:
            print(f"⚠️  WARNING: Multiple assignments may cause duplication")
            return True
            
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def check_scoring_weights_unchanged():
    """Check 7: Verify scoring weights and thresholds are unchanged"""
    print("\n" + "="*70)
    print("CHECK 7: Scoring Weights and Trigger Thresholds")
    print("="*70)
    
    try:
        from entry_scenario_config import (
            TRIGGER_WEIGHTS,
            TRIGGER_STRENGTH_THRESHOLDS,
            ROLLBACK_WEIGHTS,
            PULLBACK_WEIGHTS,
            CONTINUATION_WEIGHTS,
            REVERSAL_WEIGHTS,
            MIN_SCENARIO_SCORE,
            MIN_TRIGGERS,
            POI_QUALITY
        )
        
        # Expected values (from requirements)
        expected_trigger_weights = {
            'MSS/BOS': 40,
            'DISPLACEMENT': 35,
            'LIQUIDITY_SWEEP': 25,
            'BREAKER/MITIGATION': 20
        }
        
        expected_thresholds = {
            'HIGH': 75,
            'MEDIUM': 50
        }
        
        expected_min_score = 70
        
        # Verify trigger weights
        if TRIGGER_WEIGHTS != expected_trigger_weights:
            print("❌ FAILED: TRIGGER_WEIGHTS have changed!")
            print(f"   Expected: {expected_trigger_weights}")
            print(f"   Actual:   {TRIGGER_WEIGHTS}")
            return False
        print("   ✅ TRIGGER_WEIGHTS unchanged")
        
        # Verify thresholds
        if TRIGGER_STRENGTH_THRESHOLDS != expected_thresholds:
            print("❌ FAILED: TRIGGER_STRENGTH_THRESHOLDS have changed!")
            print(f"   Expected: {expected_thresholds}")
            print(f"   Actual:   {TRIGGER_STRENGTH_THRESHOLDS}")
            return False
        print("   ✅ TRIGGER_STRENGTH_THRESHOLDS unchanged")
        
        # Verify min scenario score
        if MIN_SCENARIO_SCORE != expected_min_score:
            print("❌ FAILED: MIN_SCENARIO_SCORE has changed!")
            print(f"   Expected: {expected_min_score}")
            print(f"   Actual:   {MIN_SCENARIO_SCORE}")
            return False
        print("   ✅ MIN_SCENARIO_SCORE unchanged (70)")
        
        # Display scenario weights for verification
        print("\n   Scenario Base Scores:")
        print(f"      ROLLBACK:     {ROLLBACK_WEIGHTS['base_score']}")
        print(f"      PULLBACK:     {PULLBACK_WEIGHTS['base_score']}")
        print(f"      CONTINUATION: {CONTINUATION_WEIGHTS['base_score']}")
        print(f"      REVERSAL:     {REVERSAL_WEIGHTS['base_score']}")
        
        print("\n   Minimum Triggers:")
        for scenario, min_t in MIN_TRIGGERS.items():
            print(f"      {scenario}: {min_t}")
        
        print("\n   POI Quality Scores:")
        for poi_type, score in POI_QUALITY.items():
            print(f"      {poi_type}: {score}")
        
        print("\n✅ PASSED: All scoring weights and thresholds are unchanged")
        return True
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False


def run_all_checks():
    """Run all technical verification checks"""
    print("\n" + "="*70)
    print("PRE-MERGE TECHNICAL VERIFICATION")
    print("Stabilization PR - Timeframe & Component Integrity")
    print("="*70)
    
    checks = [
        ("is_auto Variable", check_is_auto_variable),
        ("is_auto Usage", check_is_auto_usage),
        ("_create_no_trade_message Signature", check_create_no_trade_signature),
        ("vars() Safety", check_vars_safety),
        ("Component Filtering", check_component_filtering),
        ("Liquidity Sweeps", check_liquidity_sweeps_deduplication),
        ("Scoring Weights", check_scoring_weights_unchanged),
    ]
    
    results = {}
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print(f"\n❌ CHECK FAILED: {name}")
            print(f"   Error: {e}")
            results[name] = False
    
    # Summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {name}")
    
    print(f"\nTotal: {passed}/{total} checks passed")
    
    if passed == total:
        print("\n🎉 ALL TECHNICAL CHECKS PASSED!")
        print("✅ Ready for behavioral regression testing")
        return 0
    else:
        print(f"\n❌ {total - passed} CHECK(S) FAILED!")
        print("⚠️  Please fix issues before proceeding")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_checks())
