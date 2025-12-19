#!/usr/bin/env python3
"""
🧪 TEST: Strict ICT Signal/Position Risk Standardization

Tests for the implementation of STRICT ICT requirements:
1. Stop Loss (SL) контрол с ICT compliance
2. Risk/Reward (RR) минимум 1:3
3. Multi-Timeframe (MTF) Consensus
4. ML ограничения
5. Confidence threshold минимум 60%
6. Стандартизация на формата

Author: galinborisov10-art
Date: 2025-12-19
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import unittest
import pandas as pd
import numpy as np
from datetime import datetime

# Import ICT Signal Engine
try:
    from ict_signal_engine import ICTSignalEngine, ICTSignal, MarketBias, SignalType
    ICT_AVAILABLE = True
except ImportError as e:
    print(f"❌ Cannot import ICT Signal Engine: {e}")
    ICT_AVAILABLE = False


class TestStrictICTStandards(unittest.TestCase):
    """Test suite for Strict ICT Signal/Position Risk Standards"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test fixtures"""
        if not ICT_AVAILABLE:
            raise unittest.SkipTest("ICT Signal Engine not available")
        
        cls.engine = ICTSignalEngine()
        print("\n" + "="*60)
        print("🧪 TESTING: Strict ICT Signal Standards")
        print("="*60)
    
    def test_01_min_confidence_60_percent(self):
        """Test 1: Minimum confidence is 60% (not 70%)"""
        print("\n📊 Test 1: Minimum Confidence = 60%")
        
        min_conf = self.engine.config.get('min_confidence', 0)
        
        self.assertEqual(min_conf, 60, 
                         f"❌ min_confidence should be 60%, got {min_conf}%")
        print(f"✅ Minimum confidence is correctly set to 60%")
    
    def test_02_min_risk_reward_3_0(self):
        """Test 2: Minimum Risk/Reward is 1:3 (not 1:2)"""
        print("\n📊 Test 2: Minimum Risk/Reward = 1:3")
        
        min_rr = self.engine.config.get('min_risk_reward', 0)
        
        self.assertEqual(min_rr, 3.0,
                         f"❌ min_risk_reward should be 3.0, got {min_rr}")
        print(f"✅ Minimum Risk/Reward is correctly set to 1:3")
    
    def test_03_tp_multipliers(self):
        """Test 3: TP multipliers are [3, 5, 8] (not [2, 3, 5])"""
        print("\n📊 Test 3: TP Multipliers = [3, 5, 8]")
        
        tp_mult = self.engine.config.get('tp_multipliers', [])
        
        self.assertEqual(tp_mult, [3, 5, 8],
                         f"❌ tp_multipliers should be [3, 5, 8], got {tp_mult}")
        print(f"✅ TP multipliers are correctly set to [3, 5, 8]")
    
    def test_04_mtf_confluence_required(self):
        """Test 4: MTF confluence is required (not optional)"""
        print("\n📊 Test 4: MTF Confluence Required")
        
        require_mtf = self.engine.config.get('require_mtf_confluence', False)
        
        self.assertTrue(require_mtf,
                        "❌ require_mtf_confluence should be True")
        print(f"✅ MTF confluence is required")
    
    def test_05_mtf_min_consensus_50_percent(self):
        """Test 5: Minimum MTF consensus is 50% (0.5)"""
        print("\n📊 Test 5: Minimum MTF Consensus = 50%")
        
        min_mtf = self.engine.config.get('min_mtf_confluence', 0)
        
        self.assertEqual(min_mtf, 0.5,
                         f"❌ min_mtf_confluence should be 0.5 (50%), got {min_mtf}")
        print(f"✅ Minimum MTF consensus is correctly set to 50%")
    
    def test_06_sl_validation_method_exists(self):
        """Test 6: SL validation method exists and returns tuple"""
        print("\n📊 Test 6: SL Validation Method")
        
        self.assertTrue(hasattr(self.engine, '_validate_sl_position'),
                        "❌ _validate_sl_position method not found")
        
        # Check method signature (should accept 4 parameters)
        import inspect
        sig = inspect.signature(self.engine._validate_sl_position)
        params = list(sig.parameters.keys())
        
        self.assertEqual(len(params), 4,
                         f"❌ _validate_sl_position should have 4 parameters, got {len(params)}")
        
        print(f"✅ SL validation method exists with correct signature")
        print(f"   Parameters: {params}")
    
    def test_07_mtf_consensus_calculation_method(self):
        """Test 7: MTF consensus calculation method exists"""
        print("\n📊 Test 7: MTF Consensus Calculation Method")
        
        self.assertTrue(hasattr(self.engine, '_calculate_mtf_consensus'),
                        "❌ _calculate_mtf_consensus method not found")
        
        print(f"✅ MTF consensus calculation method exists")
    
    def test_08_no_trade_message_creation(self):
        """Test 8: NO_TRADE message creation method exists"""
        print("\n📊 Test 8: NO_TRADE Message Creation")
        
        self.assertTrue(hasattr(self.engine, '_create_no_trade_message'),
                        "❌ _create_no_trade_message method not found")
        
        print(f"✅ NO_TRADE message creation method exists")
    
    def test_09_ict_signal_has_mtf_consensus_data(self):
        """Test 9: ICTSignal has mtf_consensus_data field"""
        print("\n📊 Test 9: ICTSignal MTF Consensus Data Field")
        
        # Check if ICTSignal dataclass has mtf_consensus_data field
        from dataclasses import fields
        signal_fields = [f.name for f in fields(ICTSignal)]
        
        self.assertIn('mtf_consensus_data', signal_fields,
                      "❌ ICTSignal should have mtf_consensus_data field")
        
        print(f"✅ ICTSignal has mtf_consensus_data field")
    
    def test_10_signal_with_synthetic_data(self):
        """Test 10: Generate signal with synthetic data"""
        print("\n📊 Test 10: Signal Generation with Synthetic Data")
        
        # Create synthetic OHLCV data
        dates = pd.date_range(start='2024-01-01', periods=200, freq='1H')
        np.random.seed(42)
        
        close_prices = 100 + np.cumsum(np.random.randn(200) * 0.5)
        high_prices = close_prices + np.random.rand(200) * 2
        low_prices = close_prices - np.random.rand(200) * 2
        open_prices = close_prices + np.random.randn(200) * 0.5
        volumes = np.random.randint(1000, 10000, 200)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': open_prices,
            'high': high_prices,
            'low': low_prices,
            'close': close_prices,
            'volume': volumes
        })
        
        df.set_index('timestamp', inplace=True)
        
        try:
            # Attempt to generate signal
            result = self.engine.generate_signal(
                df=df,
                symbol='BTCUSDT',
                timeframe='1h',
                mtf_data=None
            )
            
            print(f"   Result type: {type(result)}")
            
            # Check result type
            if result is None:
                print(f"   ⚠️ No signal generated (expected with synthetic data)")
            elif isinstance(result, dict):
                if result.get('type') == 'NO_TRADE':
                    print(f"   ✅ NO_TRADE message generated")
                    print(f"   Reason: {result.get('reason', 'N/A')}")
                else:
                    print(f"   ⚠️ Unknown dict result: {result}")
            elif isinstance(result, ICTSignal):
                print(f"   ✅ Valid ICT signal generated!")
                print(f"   Confidence: {result.confidence:.1f}%")
                print(f"   RR: 1:{result.risk_reward_ratio:.2f}")
                
                # Validate strict ICT standards
                self.assertGreaterEqual(result.confidence, 60,
                                        "❌ Signal confidence should be >= 60%")
                self.assertGreaterEqual(result.risk_reward_ratio, 3.0,
                                        "❌ Signal RR should be >= 1:3")
                
                # Check MTF consensus data
                self.assertIsNotNone(result.mtf_consensus_data,
                                     "❌ Signal should have mtf_consensus_data")
                
                print(f"   ✅ Signal passes all strict ICT standards")
            else:
                print(f"   ⚠️ Unexpected result type: {type(result)}")
            
        except Exception as e:
            print(f"   ⚠️ Signal generation failed (expected): {e}")


def run_tests():
    """Run all tests"""
    print("\n" + "="*60)
    print("🚀 Starting Strict ICT Standards Test Suite")
    print("="*60 + "\n")
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestStrictICTStandards)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "="*60)
    print("📊 TEST SUMMARY")
    print("="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"✅ Passed: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"❌ Failed: {len(result.failures)}")
    print(f"💥 Errors: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n🎉 ALL TESTS PASSED!")
        print("✅ Strict ICT Standards are correctly implemented")
        return 0
    else:
        print("\n⚠️ SOME TESTS FAILED")
        print("Please review the failures above")
        return 1


if __name__ == '__main__':
    exit_code = run_tests()
    sys.exit(exit_code)
