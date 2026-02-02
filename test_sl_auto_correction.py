#!/usr/bin/env python3
"""
🧪 TEST: SL Auto-Correction (Fix for redundant strict checks)

Tests that _validate_sl_position auto-corrects invalid SL placements
instead of rejecting them.

This test validates the fix for the issue where:
- BULLISH signals with SL >= OB bottom were rejected instead of corrected
- BEARISH signals with SL <= OB top were rejected instead of corrected

Expected behavior after fix:
- Invalid SL placements are auto-corrected
- Signals are sent with corrected SL values
- No premature rejections

Author: galinborisov10-art
Date: 2026-02-02
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import unittest
from unittest.mock import MagicMock

# Import ICT Signal Engine
try:
    from ict_signal_engine import ICTSignalEngine, MarketBias
    ICT_AVAILABLE = True
except ImportError as e:
    print(f"❌ Cannot import ICT Signal Engine: {e}")
    ICT_AVAILABLE = False


class TestSLAutoCorrection(unittest.TestCase):
    """Test suite for SL auto-correction behavior"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        if not ICT_AVAILABLE:
            raise unittest.SkipTest("ICT Signal Engine not available")
        
        cls.engine = ICTSignalEngine()
        print("\n" + "="*70)
        print("🧪 TESTING: SL Auto-Correction (No Premature Rejections)")
        print("="*70)
    
    def test_01_bullish_sl_inside_ob_autocorrects(self):
        """Test 1: BULLISH - SL inside/above OB should auto-correct, not reject"""
        print("\n📊 Test 1: BULLISH - SL inside OB auto-corrects")
        
        # Create mock order block
        order_block = {
            'zone_low': 100000.0,  # OB bottom
            'zone_high': 101000.0  # OB top
        }
        
        # Test case: SL is ABOVE OB bottom (invalid, should be corrected)
        sl_price = 100500.0  # Inside OB
        entry_price = 101500.0  # Entry above OB
        
        # Call validation
        corrected_sl, is_valid = self.engine._validate_sl_position(
            sl_price=sl_price,
            order_block=order_block,
            direction='BULLISH',
            entry_price=entry_price
        )
        
        # Assertions
        self.assertTrue(is_valid, "❌ SL validation should succeed (auto-correct)")
        self.assertIsNotNone(corrected_sl, "❌ Corrected SL should not be None")
        self.assertLess(corrected_sl, order_block['zone_low'],
                       f"❌ BULLISH SL should be BELOW OB bottom")
        
        expected_sl = order_block['zone_low'] * (1 - 0.003)  # 0.3% buffer
        self.assertAlmostEqual(corrected_sl, expected_sl, places=2,
                              msg=f"❌ SL should be corrected to {expected_sl:.2f}")
        
        print(f"   ✅ Original SL: {sl_price:.2f} (inside OB)")
        print(f"   ✅ Corrected SL: {corrected_sl:.2f} (below OB with buffer)")
        print(f"   ✅ OB bottom: {order_block['zone_low']:.2f}")
        print(f"   ✅ Validation: PASSED (auto-corrected)")
    
    def test_02_bullish_sl_at_ob_bottom_autocorrects(self):
        """Test 2: BULLISH - SL exactly at OB bottom should auto-correct"""
        print("\n📊 Test 2: BULLISH - SL at OB bottom auto-corrects")
        
        order_block = {
            'zone_low': 100000.0,
            'zone_high': 101000.0
        }
        
        # SL exactly at OB bottom
        sl_price = 100000.0
        entry_price = 101500.0
        
        corrected_sl, is_valid = self.engine._validate_sl_position(
            sl_price=sl_price,
            order_block=order_block,
            direction='BULLISH',
            entry_price=entry_price
        )
        
        self.assertTrue(is_valid, "❌ Should auto-correct, not reject")
        self.assertLess(corrected_sl, order_block['zone_low'],
                       "❌ Corrected SL should be below OB")
        
        print(f"   ✅ Original SL: {sl_price:.2f} (at OB bottom)")
        print(f"   ✅ Corrected SL: {corrected_sl:.2f}")
        print(f"   ✅ Auto-correction: SUCCESS")
    
    def test_03_bearish_sl_inside_ob_autocorrects(self):
        """Test 3: BEARISH - SL inside/below OB should auto-correct, not reject"""
        print("\n📊 Test 3: BEARISH - SL inside OB auto-corrects")
        
        order_block = {
            'zone_low': 94000.0,  # OB bottom
            'zone_high': 95000.0  # OB top
        }
        
        # Test case: SL is BELOW OB top (invalid, should be corrected)
        sl_price = 82009.45  # Way below OB (from real example in issue)
        entry_price = 93500.0  # Entry below OB
        
        # Call validation
        corrected_sl, is_valid = self.engine._validate_sl_position(
            sl_price=sl_price,
            order_block=order_block,
            direction='BEARISH',
            entry_price=entry_price
        )
        
        # Assertions
        self.assertTrue(is_valid, "❌ SL validation should succeed (auto-correct)")
        self.assertIsNotNone(corrected_sl, "❌ Corrected SL should not be None")
        self.assertGreater(corrected_sl, order_block['zone_high'],
                          f"❌ BEARISH SL should be ABOVE OB top")
        
        expected_sl = order_block['zone_high'] * (1 + 0.003)  # 0.3% buffer
        self.assertAlmostEqual(corrected_sl, expected_sl, places=2,
                              msg=f"❌ SL should be corrected to {expected_sl:.2f}")
        
        print(f"   ✅ Original SL: {sl_price:.2f} (inside OB)")
        print(f"   ✅ Corrected SL: {corrected_sl:.2f} (above OB with buffer)")
        print(f"   ✅ OB top: {order_block['zone_high']:.2f}")
        print(f"   ✅ Validation: PASSED (auto-corrected)")
    
    def test_04_bearish_sl_at_ob_top_autocorrects(self):
        """Test 4: BEARISH - SL exactly at OB top should auto-correct"""
        print("\n📊 Test 4: BEARISH - SL at OB top auto-corrects")
        
        order_block = {
            'zone_low': 94000.0,
            'zone_high': 95000.0
        }
        
        # SL exactly at OB top
        sl_price = 95000.0
        entry_price = 93500.0
        
        corrected_sl, is_valid = self.engine._validate_sl_position(
            sl_price=sl_price,
            order_block=order_block,
            direction='BEARISH',
            entry_price=entry_price
        )
        
        self.assertTrue(is_valid, "❌ Should auto-correct, not reject")
        self.assertGreater(corrected_sl, order_block['zone_high'],
                          "❌ Corrected SL should be above OB")
        
        print(f"   ✅ Original SL: {sl_price:.2f} (at OB top)")
        print(f"   ✅ Corrected SL: {corrected_sl:.2f}")
        print(f"   ✅ Auto-correction: SUCCESS")
    
    def test_05_bullish_sl_already_valid_unchanged(self):
        """Test 5: BULLISH - Already valid SL should remain unchanged"""
        print("\n📊 Test 5: BULLISH - Valid SL remains unchanged")
        
        order_block = {
            'zone_low': 100000.0,
            'zone_high': 101000.0
        }
        
        # SL already valid (below OB with buffer)
        sl_price = 99700.0  # 0.3% below OB
        entry_price = 101500.0
        
        corrected_sl, is_valid = self.engine._validate_sl_position(
            sl_price=sl_price,
            order_block=order_block,
            direction='BULLISH',
            entry_price=entry_price
        )
        
        self.assertTrue(is_valid, "❌ Valid SL should pass validation")
        self.assertEqual(corrected_sl, sl_price,
                        "❌ Valid SL should not be changed")
        
        print(f"   ✅ SL: {sl_price:.2f} (already valid)")
        print(f"   ✅ No correction needed")
    
    def test_06_bearish_sl_already_valid_unchanged(self):
        """Test 6: BEARISH - Already valid SL should remain unchanged"""
        print("\n📊 Test 6: BEARISH - Valid SL remains unchanged")
        
        order_block = {
            'zone_low': 94000.0,
            'zone_high': 95000.0
        }
        
        # SL already valid (above OB with buffer)
        sl_price = 95285.0  # 0.3% above OB
        entry_price = 93500.0
        
        corrected_sl, is_valid = self.engine._validate_sl_position(
            sl_price=sl_price,
            order_block=order_block,
            direction='BEARISH',
            entry_price=entry_price
        )
        
        self.assertTrue(is_valid, "❌ Valid SL should pass validation")
        self.assertEqual(corrected_sl, sl_price,
                        "❌ Valid SL should not be changed")
        
        print(f"   ✅ SL: {sl_price:.2f} (already valid)")
        print(f"   ✅ No correction needed")
    
    def test_07_real_world_example_from_issue(self):
        """Test 7: Real-world example from the issue (BEARISH signal)"""
        print("\n📊 Test 7: Real-world example from issue")
        
        # Real data from issue:
        # ❌ BEARISH SL 82009.45 <= OB top 94789.08 - FORBIDDEN
        # Expected: Auto-correct to 94789.08 * 1.003 = 95073.42
        
        order_block = {
            'zone_low': 93000.0,
            'zone_high': 94789.08
        }
        
        sl_price = 82009.45  # Way below OB
        entry_price = 93500.0
        
        corrected_sl, is_valid = self.engine._validate_sl_position(
            sl_price=sl_price,
            order_block=order_block,
            direction='BEARISH',
            entry_price=entry_price
        )
        
        # Should auto-correct to above OB with buffer
        expected_sl = 94789.08 * (1 + 0.003)  # 95073.42
        
        self.assertTrue(is_valid, 
                       "❌ CRITICAL: Should auto-correct, not reject (this was the bug)")
        self.assertIsNotNone(corrected_sl, "❌ Corrected SL should not be None")
        self.assertGreater(corrected_sl, order_block['zone_high'],
                          "❌ Corrected SL should be above OB top")
        self.assertAlmostEqual(corrected_sl, expected_sl, places=2,
                              msg=f"❌ Should correct to {expected_sl:.2f}")
        
        print(f"   ✅ Original SL: {sl_price:.2f} (INVALID - below OB)")
        print(f"   ✅ OB top: {order_block['zone_high']:.2f}")
        print(f"   ✅ Corrected SL: {corrected_sl:.2f} (VALID - above OB)")
        print(f"   ✅ Expected: {expected_sl:.2f}")
        print(f"   ✅ AUTO-CORRECTION: SUCCESS ✨")
        print(f"   ℹ️  This signal would have been REJECTED before the fix!")


def run_tests():
    """Run all tests"""
    print("\n" + "="*70)
    print("🚀 Starting SL Auto-Correction Test Suite")
    print("="*70 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSLAutoCorrection)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*70)
    print("📊 TEST SUMMARY")
    print("="*70)
    print(f"Tests run: {result.testsRun}")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ SL Auto-correction is working correctly")
        print("✅ No premature signal rejections")
        print("✅ Invalid SL placements are auto-corrected")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("Please review the failures above")
        return 1


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)
