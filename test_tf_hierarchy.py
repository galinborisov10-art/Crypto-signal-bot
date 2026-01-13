"""
Test script for PR #4: Timeframe Hierarchy validation

Tests:
1. Config loading from JSON
2. Default fallback when config missing
3. TF hierarchy validation logic
4. Penalty application
"""

import sys
import json
from pathlib import Path

def test_config_loading():
    """Test 1: Verify timeframe_hierarchy.json loads correctly"""
    print("=" * 60)
    print("TEST 1: Config Loading")
    print("=" * 60)
    
    config_path = Path(__file__).parent / 'config' / 'timeframe_hierarchy.json'
    
    if not config_path.exists():
        print(f"❌ FAILED: Config file not found at {config_path}")
        return False
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
        
        # Verify structure
        assert 'hierarchies' in hierarchy, "Missing 'hierarchies' key"
        assert 'validation_rules' in hierarchy, "Missing 'validation_rules' key"
        
        # Verify timeframes
        required_tfs = ['1h', '2h', '4h', '1d']
        for tf in required_tfs:
            assert tf in hierarchy['hierarchies'], f"Missing timeframe: {tf}"
            
            # Verify TF structure
            tf_config = hierarchy['hierarchies'][tf]
            assert 'entry_tf' in tf_config, f"{tf}: Missing entry_tf"
            assert 'confirmation_tf' in tf_config, f"{tf}: Missing confirmation_tf"
            assert 'structure_tf' in tf_config, f"{tf}: Missing structure_tf"
            assert 'htf_bias_tf' in tf_config, f"{tf}: Missing htf_bias_tf"
            
        # Verify validation rules
        rules = hierarchy['validation_rules']
        assert 'confirmation_penalty_if_missing' in rules, "Missing confirmation penalty"
        assert 'structure_penalty_if_missing' in rules, "Missing structure penalty"
        assert rules['confirmation_penalty_if_missing'] == 0.15, "Wrong confirmation penalty"
        assert rules['structure_penalty_if_missing'] == 0.25, "Wrong structure penalty"
        
        print("✅ PASSED: Config loaded successfully")
        print(f"   - Found {len(hierarchy['hierarchies'])} timeframes")
        print(f"   - Confirmation penalty: {rules['confirmation_penalty_if_missing']*100}%")
        print(f"   - Structure penalty: {rules['structure_penalty_if_missing']*100}%")
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ FAILED: JSON decode error: {e}")
        return False
    except AssertionError as e:
        print(f"❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False


def test_hierarchy_mappings():
    """Test 2: Verify TF hierarchy mappings are correct"""
    print("\n" + "=" * 60)
    print("TEST 2: Hierarchy Mappings")
    print("=" * 60)
    
    config_path = Path(__file__).parent / 'config' / 'timeframe_hierarchy.json'
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            hierarchy = json.load(f)
        
        hierarchies = hierarchy['hierarchies']
        
        # Test 1H hierarchy
        assert hierarchies['1h']['entry_tf'] == '1h', "1h: Wrong entry TF"
        assert hierarchies['1h']['confirmation_tf'] == '2h', "1h: Wrong confirmation TF"
        assert hierarchies['1h']['structure_tf'] == '4h', "1h: Wrong structure TF"
        assert hierarchies['1h']['htf_bias_tf'] == '1d', "1h: Wrong HTF bias TF"
        
        # Test 2H hierarchy
        assert hierarchies['2h']['entry_tf'] == '2h', "2h: Wrong entry TF"
        assert hierarchies['2h']['confirmation_tf'] == '4h', "2h: Wrong confirmation TF"
        assert hierarchies['2h']['structure_tf'] == '1d', "2h: Wrong structure TF"
        assert hierarchies['2h']['htf_bias_tf'] == '1d', "2h: Wrong HTF bias TF"
        
        # Test 4H hierarchy
        assert hierarchies['4h']['entry_tf'] == '4h', "4h: Wrong entry TF"
        assert hierarchies['4h']['confirmation_tf'] == '4h', "4h: Wrong confirmation TF"
        assert hierarchies['4h']['structure_tf'] == '1d', "4h: Wrong structure TF"
        assert hierarchies['4h']['htf_bias_tf'] == '1w', "4h: Wrong HTF bias TF"
        
        # Test 1D hierarchy
        assert hierarchies['1d']['entry_tf'] == '1d', "1d: Wrong entry TF"
        assert hierarchies['1d']['confirmation_tf'] == '1d', "1d: Wrong confirmation TF"
        assert hierarchies['1d']['structure_tf'] == '1w', "1d: Wrong structure TF"
        assert hierarchies['1d']['htf_bias_tf'] == '1w', "1d: Wrong HTF bias TF"
        
        print("✅ PASSED: All TF mappings correct")
        print("   - 1H: Entry(1h) → Conf(2h) → Struct(4h) → Bias(1d)")
        print("   - 2H: Entry(2h) → Conf(4h) → Struct(1d) → Bias(1d)")
        print("   - 4H: Entry(4h) → Conf(4h) → Struct(1d) → Bias(1w)")
        print("   - 1D: Entry(1d) → Conf(1d) → Struct(1w) → Bias(1w)")
        return True
        
    except AssertionError as e:
        print(f"❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        return False


def test_ict_signal_engine_integration():
    """Test 3: Verify ICTSignalEngine can load the config"""
    print("\n" + "=" * 60)
    print("TEST 3: ICTSignalEngine Integration")
    print("=" * 60)
    
    try:
        from ict_signal_engine import ICTSignalEngine
        
        # Initialize engine
        engine = ICTSignalEngine()
        
        # Verify TF hierarchy loaded
        assert hasattr(engine, 'tf_hierarchy'), "Engine missing tf_hierarchy attribute"
        assert 'hierarchies' in engine.tf_hierarchy, "Missing hierarchies in loaded config"
        
        hierarchies = engine.tf_hierarchy.get('hierarchies', {})
        assert len(hierarchies) > 0, "No hierarchies loaded"
        
        print("✅ PASSED: ICTSignalEngine loaded TF hierarchy")
        print(f"   - Loaded {len(hierarchies)} timeframes")
        print(f"   - Available TFs: {list(hierarchies.keys())}")
        
        # Test validation method exists
        assert hasattr(engine, '_validate_mtf_hierarchy'), "Missing _validate_mtf_hierarchy method"
        print("   - Validation method available: ✅")
        
        return True
        
    except ImportError as e:
        print(f"❌ FAILED: Could not import ICTSignalEngine: {e}")
        return False
    except AssertionError as e:
        print(f"❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"❌ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_validation_logic():
    """Test 4: Test TF hierarchy validation logic"""
    print("\n" + "=" * 60)
    print("TEST 4: Validation Logic")
    print("=" * 60)
    
    try:
        from ict_signal_engine import ICTSignalEngine
        
        engine = ICTSignalEngine()
        
        # Test Case 1: All TFs present (no penalties)
        print("\n   Test Case 1: All TFs present")
        mtf_analysis = {
            '1h': {'bias': 'BULLISH', 'confidence': 70},
            '2h': {'bias': 'BULLISH', 'confidence': 75},
            '4h': {'bias': 'BULLISH', 'confidence': 80},
            '1d': {'bias': 'BULLISH', 'confidence': 85}
        }
        
        confidence, warnings, hierarchy_info = engine._validate_mtf_hierarchy(
            entry_tf='1h',
            mtf_analysis=mtf_analysis,
            confidence=80.0
        )
        
        assert confidence == 80.0, f"Expected confidence 80.0, got {confidence}"
        assert len(warnings) == 0, f"Expected no warnings, got {len(warnings)}"
        assert hierarchy_info.get('confirmation_tf_present') == True, "Confirmation TF should be present"
        assert hierarchy_info.get('structure_tf_present') == True, "Structure TF should be present"
        
        print("      ✅ No penalties applied (all TFs present)")
        
        # Test Case 2: Missing Confirmation TF (15% penalty)
        print("\n   Test Case 2: Missing Confirmation TF")
        mtf_analysis = {
            '1h': {'bias': 'BULLISH', 'confidence': 70},
            '4h': {'bias': 'BULLISH', 'confidence': 80},
            '1d': {'bias': 'BULLISH', 'confidence': 85}
        }
        
        confidence, warnings, hierarchy_info = engine._validate_mtf_hierarchy(
            entry_tf='1h',
            mtf_analysis=mtf_analysis,
            confidence=80.0
        )
        
        expected_confidence = 80.0 - 0.15
        assert abs(confidence - expected_confidence) < 0.01, f"Expected confidence {expected_confidence}, got {confidence}"
        assert len(warnings) == 1, f"Expected 1 warning, got {len(warnings)}"
        assert hierarchy_info.get('confirmation_tf_present') == False, "Confirmation TF should be missing"
        
        print(f"      ✅ Confirmation penalty applied: {confidence:.2f}% (was 80.0%)")
        
        # Test Case 3: Missing Structure TF (25% penalty)
        print("\n   Test Case 3: Missing Structure TF")
        mtf_analysis = {
            '1h': {'bias': 'BULLISH', 'confidence': 70},
            '2h': {'bias': 'BULLISH', 'confidence': 75},
            '1d': {'bias': 'BULLISH', 'confidence': 85}
        }
        
        confidence, warnings, hierarchy_info = engine._validate_mtf_hierarchy(
            entry_tf='1h',
            mtf_analysis=mtf_analysis,
            confidence=80.0
        )
        
        expected_confidence = 80.0 - 0.25
        assert abs(confidence - expected_confidence) < 0.01, f"Expected confidence {expected_confidence}, got {confidence}"
        assert len(warnings) == 1, f"Expected 1 warning, got {len(warnings)}"
        assert hierarchy_info.get('structure_tf_present') == False, "Structure TF should be missing"
        
        print(f"      ✅ Structure penalty applied: {confidence:.2f}% (was 80.0%)")
        
        # Test Case 4: Both missing (40% penalty total)
        print("\n   Test Case 4: Both Confirmation and Structure TFs missing")
        mtf_analysis = {
            '1h': {'bias': 'BULLISH', 'confidence': 70},
            '1d': {'bias': 'BULLISH', 'confidence': 85}
        }
        
        confidence, warnings, hierarchy_info = engine._validate_mtf_hierarchy(
            entry_tf='1h',
            mtf_analysis=mtf_analysis,
            confidence=80.0
        )
        
        expected_confidence = 80.0 - 0.15 - 0.25
        assert abs(confidence - expected_confidence) < 0.01, f"Expected confidence {expected_confidence}, got {confidence}"
        assert len(warnings) == 2, f"Expected 2 warnings, got {len(warnings)}"
        
        print(f"      ✅ Both penalties applied: {confidence:.2f}% (was 80.0%)")
        
        print("\n✅ PASSED: All validation logic tests")
        return True
        
    except AssertionError as e:
        print(f"\n❌ FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n❌ FAILED: Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all tests"""
    print("\n" + "🔬" * 30)
    print("PR #4: TIMEFRAME HIERARCHY - TEST SUITE")
    print("🔬" * 30 + "\n")
    
    results = []
    
    # Run tests
    results.append(("Config Loading", test_config_loading()))
    results.append(("Hierarchy Mappings", test_hierarchy_mappings()))
    results.append(("ICTSignalEngine Integration", test_ict_signal_engine_integration()))
    results.append(("Validation Logic", test_validation_logic()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print("\n" + "=" * 60)
    print(f"TOTAL: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED!")
        print("=" * 60)
        return 0
    else:
        print("⚠️ SOME TESTS FAILED")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
