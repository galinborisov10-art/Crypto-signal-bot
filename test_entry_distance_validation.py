"""
Unit Tests for Entry Distance Validation Fix
Tests that signals with unrealistic entry distances are rejected based on timeframe limits
"""

import os
import sys
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ict_signal_engine import ICTSignalEngine


class TestEntryDistanceValidation:
    """Test entry distance validation against timeframe-based limits"""
    
    def __init__(self):
        """Create ICTSignalEngine instance for testing"""
        self.engine = ICTSignalEngine()
    
    def test_4h_signal_20pct_away_rejected(self):
        """Test that 4h signal with 20.5% entry distance is REJECTED (exceeds 7.5% limit)"""
        current_price = 100.0
        
        # Create a zone 20.5% away (should be rejected for 4h timeframe)
        fvg_zones = [{
            'type': 'BULLISH',
            'low': 79.5,  # 20.5% below current price
            'high': 80.0,
            'quality': 85
        }]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=current_price,
            direction='BULLISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={},
            timeframe='4h'
        )
        
        # Should be rejected as TOO_FAR
        assert entry_zone is None, "Entry zone should be None for TOO_FAR status"
        assert status == 'TOO_FAR', f"Expected 'TOO_FAR' but got '{status}'"
        print("✅ 4h signal with 20.5% entry distance REJECTED (exceeds 7.5% limit)")
    
    def test_4h_signal_5pct_away_accepted(self):
        """Test that 4h signal with 5% entry distance is ACCEPTED (within 7.5% limit)"""
        current_price = 100.0
        
        # Create a zone 5% away (should be accepted for 4h timeframe)
        fvg_zones = [{
            'type': 'BULLISH',
            'low': 95.0,  # 5% below current price
            'high': 95.5,
            'quality': 85
        }]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=current_price,
            direction='BULLISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={},
            timeframe='4h'
        )
        
        # Should be accepted as VALID_WAIT
        assert entry_zone is not None, "Entry zone should not be None for valid distance"
        assert status == 'VALID_WAIT', f"Expected 'VALID_WAIT' but got '{status}'"
        print("✅ 4h signal with 5% entry distance ACCEPTED (within 7.5% limit)")
    
    def test_1h_signal_6pct_away_rejected(self):
        """Test that 1h signal with 6% entry distance is REJECTED (exceeds 5% limit)"""
        current_price = 100.0
        
        # Create a zone 6% away (should be rejected for 1h timeframe)
        fvg_zones = [{
            'type': 'BULLISH',
            'low': 94.0,  # 6% below current price
            'high': 94.5,
            'quality': 85
        }]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=current_price,
            direction='BULLISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={},
            timeframe='1h'
        )
        
        # Should be rejected as TOO_FAR
        assert entry_zone is None, "Entry zone should be None for TOO_FAR status"
        assert status == 'TOO_FAR', f"Expected 'TOO_FAR' but got '{status}'"
        print("✅ 1h signal with 6% entry distance REJECTED (exceeds 5% limit)")
    
    def test_1h_signal_4pct_away_accepted(self):
        """Test that 1h signal with 4% entry distance is ACCEPTED (within 5% limit)"""
        current_price = 100.0
        
        # Create a zone 4% away (should be accepted for 1h timeframe)
        fvg_zones = [{
            'type': 'BULLISH',
            'low': 96.0,  # 4% below current price
            'high': 96.5,
            'quality': 85
        }]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=current_price,
            direction='BULLISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={},
            timeframe='1h'
        )
        
        # Should be accepted as VALID_WAIT
        assert entry_zone is not None, "Entry zone should not be None for valid distance"
        assert status == 'VALID_WAIT', f"Expected 'VALID_WAIT' but got '{status}'"
        print("✅ 1h signal with 4% entry distance ACCEPTED (within 5% limit)")
    
    def test_1d_signal_9pct_away_accepted(self):
        """Test that 1d signal with 9% entry distance is ACCEPTED (within 10% limit)"""
        current_price = 100.0
        
        # Create a zone 9% away (should be accepted for 1d timeframe)
        fvg_zones = [{
            'type': 'BULLISH',
            'low': 91.0,  # 9% below current price
            'high': 91.5,
            'quality': 85
        }]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=current_price,
            direction='BULLISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={},
            timeframe='1d'
        )
        
        # Should be accepted as VALID_WAIT
        assert entry_zone is not None, "Entry zone should not be None for valid distance"
        assert status == 'VALID_WAIT', f"Expected 'VALID_WAIT' but got '{status}'"
        print("✅ 1d signal with 9% entry distance ACCEPTED (within 10% limit)")
    
    def test_1d_signal_11pct_away_rejected(self):
        """Test that 1d signal with 11% entry distance is REJECTED (exceeds 10% limit)"""
        current_price = 100.0
        
        # Create a zone 11% away (should be rejected for 1d timeframe)
        fvg_zones = [{
            'type': 'BULLISH',
            'low': 89.0,  # 11% below current price
            'high': 89.5,
            'quality': 85
        }]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=current_price,
            direction='BULLISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={},
            timeframe='1d'
        )
        
        # Should be rejected as TOO_FAR
        assert entry_zone is None, "Entry zone should be None for TOO_FAR status"
        assert status == 'TOO_FAR', f"Expected 'TOO_FAR' but got '{status}'"
        print("✅ 1d signal with 11% entry distance REJECTED (exceeds 10% limit)")
    
    def run_all_tests(self):
        """Run all tests"""
        tests = [
            self.test_4h_signal_20pct_away_rejected,
            self.test_4h_signal_5pct_away_accepted,
            self.test_1h_signal_6pct_away_rejected,
            self.test_1h_signal_4pct_away_accepted,
            self.test_1d_signal_9pct_away_accepted,
            self.test_1d_signal_11pct_away_rejected,
        ]
        
        print("\n" + "="*70)
        print("🧪 Running Entry Distance Validation Tests")
        print("="*70 + "\n")
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                print(f"\n▶ Running: {test.__name__}")
                test()
                passed += 1
            except AssertionError as e:
                print(f"❌ FAILED: {test.__name__}")
                print(f"   Error: {e}")
                failed += 1
            except Exception as e:
                print(f"❌ ERROR: {test.__name__}")
                print(f"   Error: {e}")
                failed += 1
        
        print("\n" + "="*70)
        print(f"📊 Test Results: {passed} passed, {failed} failed")
        print("="*70 + "\n")
        
        return failed == 0


if __name__ == '__main__':
    tester = TestEntryDistanceValidation()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)

