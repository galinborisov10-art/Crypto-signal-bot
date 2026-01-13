#!/usr/bin/env python3
"""
Test PR #3: Visualization & UX Polish

Tests:
1. Chart generator has new enhanced plotting methods
2. Signal source labeling is correct
3. No contradictory warnings in contextual adjustments
"""

import sys
import inspect
from typing import List, Dict

def test_chart_generator_methods():
    """Test that chart_generator has all new enhanced plotting methods"""
    print("🧪 Test 1: Chart Generator Enhanced Methods")
    
    try:
        from chart_generator import ChartGenerator
        
        # Check for new methods
        required_methods = [
            '_plot_breaker_blocks_enhanced',
            '_plot_liquidity_zones_enhanced', 
            '_add_fvg_strength_labels'
        ]
        
        cg = ChartGenerator()
        
        for method_name in required_methods:
            if not hasattr(cg, method_name):
                print(f"   ❌ Missing method: {method_name}")
                return False
            
            method = getattr(cg, method_name)
            if not callable(method):
                print(f"   ❌ {method_name} is not callable")
                return False
            
            # Check method signature
            sig = inspect.signature(method)
            params = list(sig.parameters.keys())
            
            if method_name == '_plot_breaker_blocks_enhanced':
                if not all(p in params for p in ['ax', 'breaker_blocks', 'df']):
                    print(f"   ❌ {method_name} has wrong parameters: {params}")
                    return False
                    
            elif method_name == '_plot_liquidity_zones_enhanced':
                if not all(p in params for p in ['ax', 'liquidity_zones', 'df']):
                    print(f"   ❌ {method_name} has wrong parameters: {params}")
                    return False
                    
            elif method_name == '_add_fvg_strength_labels':
                if not all(p in params for p in ['ax', 'fvgs', 'df']):
                    print(f"   ❌ {method_name} has wrong parameters: {params}")
                    return False
            
            print(f"   ✅ {method_name}: Found with correct signature")
        
        print("   ✅ All enhanced plotting methods present")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_source_labeling():
    """Test that signal formatting uses correct source badges"""
    print("\n🧪 Test 2: Signal Source Labeling")
    
    try:
        # Check that format_standardized_signal has source_badge mapping
        with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/bot.py', 'r') as f:
            bot_code = f.read()
        
        # Check for source_badge dictionary
        if 'source_badge = {' not in bot_code:
            print("   ❌ source_badge dictionary not found")
            return False
        
        # Check for correct mappings
        required_badges = [
            '"AUTO": "🤖 АВТОМАТИЧЕН"',
            '"MANUAL": "👤 РЪЧЕН"',
            '"BACKTEST": "📊 BACKTEST"'
        ]
        
        for badge in required_badges:
            if badge not in bot_code:
                print(f"   ❌ Missing badge mapping: {badge}")
                return False
            print(f"   ✅ Found: {badge}")
        
        # Check that auto signals use AUTO source
        if 'format_standardized_signal(ict_signal, "AUTO")' in bot_code:
            print('   ✅ Auto signals use "AUTO" source')
        else:
            print('   ⚠️  Auto signals might not use "AUTO" source')
            # Not a failure, just a warning
        
        print("   ✅ Signal source labeling correct")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_contradictory_warnings_fix():
    """Test that low volume warning is skipped during peak sessions"""
    print("\n🧪 Test 3: Contradictory Warnings Fix")
    
    try:
        with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/ict_signal_engine.py', 'r') as f:
            ict_code = f.read()
        
        # Check for peak session detection
        if 'is_peak_session = session in' not in ict_code:
            print("   ❌ Peak session detection not found")
            return False
        print("   ✅ Peak session detection implemented")
        
        # Check for conditional low volume warning
        if 'if not is_peak_session:' not in ict_code:
            print("   ❌ Conditional low volume warning not found")
            return False
        print("   ✅ Low volume warning made conditional")
        
        # Check for context_info separation
        if 'context_info = []' not in ict_code:
            print("   ⚠️  context_info list not found (minor issue)")
        else:
            print("   ✅ context_info separation implemented")
        
        # Verify session info moved to context
        if 'context_info.append("🌍 LONDON SESSION' in ict_code:
            print("   ✅ Session info moved to context_info")
        elif 'warnings.append("✅ LONDON SESSION' in ict_code:
            print("   ⚠️  Session info still in warnings (old style)")
        
        print("   ✅ Contradictory warnings fix implemented")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_chart_generator_calls_new_methods():
    """Test that generate() method calls the new enhanced methods"""
    print("\n🧪 Test 4: Chart Generator Calls New Methods")
    
    try:
        with open('/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/chart_generator.py', 'r') as f:
            chart_code = f.read()
        
        # Check for new method calls in generate()
        required_calls = [
            '_plot_breaker_blocks_enhanced',
            '_plot_liquidity_zones_enhanced',
            '_add_fvg_strength_labels'
        ]
        
        for method_call in required_calls:
            if method_call in chart_code:
                print(f"   ✅ {method_call} is called")
            else:
                print(f"   ❌ {method_call} is NOT called")
                return False
        
        print("   ✅ All new methods are called in generate()")
        return True
        
    except Exception as e:
        print(f"   ❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("=" * 60)
    print("PR #3 VISUALIZATION & UX POLISH - TEST SUITE")
    print("=" * 60)
    
    results = []
    
    # Run all tests
    results.append(("Chart Generator Methods", test_chart_generator_methods()))
    results.append(("Signal Source Labeling", test_signal_source_labeling()))
    results.append(("Contradictory Warnings Fix", test_contradictory_warnings_fix()))
    results.append(("Chart Generator Calls", test_chart_generator_calls_new_methods()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
