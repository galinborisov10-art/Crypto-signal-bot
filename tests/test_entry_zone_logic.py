"""
Unit Tests for ICT-Compliant Entry Zone Logic

Tests the new _calculate_ict_compliant_entry_zone() method to ensure:
- SELL signals have entry zones ABOVE current price
- BUY signals have entry zones BELOW current price
- Signals are blocked if TOO_LATE or NO_ZONE
- Distance limits are enforced (0.5% - 3.0%)
"""

import sys
import os
import unittest
from unittest.mock import Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ict_signal_engine import ICTSignalEngine, MarketBias


class TestEntryZoneLogic(unittest.TestCase):
    """Test ICT-compliant entry zone calculation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = ICTSignalEngine()
        self.current_price = 124.78  # SOLUSDT example price
    
    def test_sell_entry_above_current_price(self):
        """Test that SELL entry zones are ABOVE current price"""
        # Create a bearish FVG above current price
        fvg_zones = [
            {
                'type': 'BEARISH_FVG',
                'bottom': 126.50,  # Above current price
                'top': 127.00,
                'strength': 80
            }
        ]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={}
        )
        
        # Assertions
        self.assertIsNotNone(entry_zone, "Entry zone should be found")
        self.assertIn(status, ['VALID_WAIT', 'VALID_NEAR'], "Status should be valid")
        self.assertGreater(entry_zone['low'], self.current_price, 
                          "SELL entry zone LOW must be ABOVE current price")
        self.assertGreater(entry_zone['high'], self.current_price,
                          "SELL entry zone HIGH must be ABOVE current price")
        self.assertGreater(entry_zone['center'], self.current_price,
                          "SELL entry zone CENTER must be ABOVE current price")
    
    def test_buy_entry_below_current_price(self):
        """Test that BUY entry zones are BELOW current price"""
        # Create a bullish FVG below current price
        fvg_zones = [
            {
                'type': 'BULLISH_FVG',
                'bottom': 122.00,  # Below current price
                'top': 122.50,
                'strength': 80
            }
        ]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BULLISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={}
        )
        
        # Assertions
        self.assertIsNotNone(entry_zone, "Entry zone should be found")
        self.assertIn(status, ['VALID_WAIT', 'VALID_NEAR'], "Status should be valid")
        self.assertLess(entry_zone['low'], self.current_price,
                       "BUY entry zone LOW must be BELOW current price")
        self.assertLess(entry_zone['high'], self.current_price,
                       "BUY entry zone HIGH must be BELOW current price")
        self.assertLess(entry_zone['center'], self.current_price,
                       "BUY entry zone CENTER must be BELOW current price")
    
    def test_too_late_signal_rejected(self):
        """Test that signals are blocked if price already passed entry zone"""
        # Create a bearish FVG BELOW current price (too late for SELL)
        fvg_zones = [
            {
                'type': 'BEARISH_FVG',
                'bottom': 123.00,  # Below current price (124.78)
                'top': 123.50,
                'strength': 80
            }
        ]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={}
        )
        
        # Assertions
        self.assertIsNone(entry_zone, "Entry zone should be None for TOO_LATE")
        self.assertEqual(status, 'TOO_LATE', "Status should be TOO_LATE")
    
    def test_entry_zone_distance_limits(self):
        """Test that entry zones respect 0.5% - 3.0% distance limits"""
        # Test minimum distance (0.6% - slightly above 0.5% to pass > check)
        min_price = self.current_price * 1.006  # 0.6% above
        
        fvg_zones = [
            {
                'type': 'BEARISH_FVG',
                'bottom': min_price,
                'top': min_price + 0.50,
                'strength': 70
            }
        ]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={}
        )
        
        self.assertIsNotNone(entry_zone, "Entry zone at min distance should be found")
        self.assertGreaterEqual(entry_zone['distance_pct'], 0.5,
                               "Distance should be at least 0.5%")
        
        # Test maximum distance (2.9% - slightly below 3.0%)
        max_price = self.current_price * 1.029  # 2.9% above
        
        fvg_zones_max = [
            {
                'type': 'BEARISH_FVG',
                'bottom': max_price,
                'top': max_price + 0.50,
                'strength': 70
            }
        ]
        
        entry_zone_max, status_max = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=fvg_zones_max,
            order_blocks=[],
            sr_levels={}
        )
        
        self.assertIsNotNone(entry_zone_max, "Entry zone at max distance should be found")
        self.assertLessEqual(entry_zone_max['distance_pct'], 3.0,
                            "Distance should be at most 3.0%")
        
        # Test beyond maximum distance (should be rejected)
        too_far_price = self.current_price * 1.04  # 4% above (too far)
        
        fvg_zones_far = [
            {
                'type': 'BEARISH_FVG',
                'bottom': too_far_price,
                'top': too_far_price + 0.50,
                'strength': 70
            }
        ]
        
        entry_zone_far, status_far = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=fvg_zones_far,
            order_blocks=[],
            sr_levels={}
        )
        
        self.assertIsNone(entry_zone_far, "Entry zone beyond 3% should be rejected")
        self.assertEqual(status_far, 'NO_ZONE', "Status should be NO_ZONE for too far zones")
    
    def test_entry_zone_source_priority(self):
        """Test that FVG > OB > S/R priority is respected"""
        # Create all three types at similar distances using dict format
        fvg_zones = [
            {
                'type': 'BEARISH_FVG',
                'bottom': self.current_price * 1.01,  # 1% above
                'top': self.current_price * 1.015,
                'strength': 70
            }
        ]
        
        order_blocks = [
            {
                'type': 'BEARISH',
                'zone_low': self.current_price * 1.01,
                'zone_high': self.current_price * 1.015,
                'strength': 75
            }
        ]
        
        sr_levels = {
            'resistance_zones': [
                {
                    'price': self.current_price * 1.01,
                    'strength': 60
                }
            ]
        }
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=fvg_zones,
            order_blocks=order_blocks,
            sr_levels=sr_levels
        )
        
        # With similar distances, priority should be: OB (75) > FVG (70) > S/R (60)
        # Since OB has highest quality
        self.assertIsNotNone(entry_zone, "Entry zone should be found")
        self.assertEqual(entry_zone['source'], 'OB', 
                        "Order Block should have priority due to higher quality")
    
    def test_valid_wait_status(self):
        """Test VALID_WAIT status when distance > 1.5%"""
        # Create FVG 2% above current price
        fvg_zones = [
            {
                'type': 'BEARISH_FVG',
                'bottom': self.current_price * 1.02,  # 2% above
                'top': self.current_price * 1.025,
                'strength': 80
            }
        ]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={}
        )
        
        self.assertEqual(status, 'VALID_WAIT', 
                        "Status should be VALID_WAIT when distance > 1.5%")
        self.assertGreater(entry_zone['distance_pct'], 1.5,
                          "Distance should be greater than 1.5%")
    
    def test_valid_near_status(self):
        """Test VALID_NEAR status when 0.5% < distance < 1.5%"""
        # Create FVG 1% above current price
        fvg_zones = [
            {
                'type': 'BEARISH_FVG',
                'bottom': self.current_price * 1.01,  # 1% above
                'top': self.current_price * 1.015,
                'strength': 80
            }
        ]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=fvg_zones,
            order_blocks=[],
            sr_levels={}
        )
        
        self.assertEqual(status, 'VALID_NEAR',
                        "Status should be VALID_NEAR when 0.5% < distance < 1.5%")
        self.assertGreater(entry_zone['distance_pct'], 0.5,
                          "Distance should be greater than 0.5%")
        self.assertLessEqual(entry_zone['distance_pct'], 1.5,
                            "Distance should be at most 1.5%")
    
    def test_no_zone_in_range(self):
        """Test NO_ZONE when no zones exist in acceptable range"""
        # Empty zones
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=[],
            order_blocks=[],
            sr_levels={}
        )
        
        self.assertIsNone(entry_zone, "Entry zone should be None when no zones found")
        self.assertEqual(status, 'NO_ZONE', "Status should be NO_ZONE")
    
    def test_order_block_entry_above_for_sell(self):
        """Test that Order Block entry zones work correctly for SELL"""
        # Create bearish OB above current price using dict format
        order_blocks = [
            {
                'type': 'BEARISH',
                'zone_low': 126.00,  # Above current price
                'zone_high': 127.00,
                'strength': 85
            }
        ]
        
        entry_zone, status = self.engine._calculate_ict_compliant_entry_zone(
            current_price=self.current_price,
            direction='BEARISH',
            fvg_zones=[],
            order_blocks=order_blocks,
            sr_levels={}
        )
        
        self.assertIsNotNone(entry_zone, "Entry zone should be found from OB")
        self.assertEqual(entry_zone['source'], 'OB', "Source should be Order Block")
        self.assertGreater(entry_zone['center'], self.current_price,
                          "OB entry zone must be ABOVE current price for SELL")


class TestSignalTimingValidation(unittest.TestCase):
    """Test signal timing validation logic"""
    
    def test_too_late_blocks_signal(self):
        """Test that TOO_LATE status blocks signal"""
        from signal_helpers import _validate_signal_timing
        
        signal_data = {'symbol': 'SOLUSDT'}
        entry_zone = {'center': 123.00, 'distance_pct': 1.5}
        entry_status = 'TOO_LATE'
        
        should_send, message = _validate_signal_timing(signal_data, entry_zone, entry_status)
        
        self.assertFalse(should_send, "Signal should NOT be sent for TOO_LATE")
        self.assertIn("Закъснял", message, "Message should mention late signal")
    
    def test_no_zone_blocks_signal(self):
        """Test that NO_ZONE status blocks signal"""
        from signal_helpers import _validate_signal_timing
        
        signal_data = {'symbol': 'SOLUSDT'}
        entry_zone = None
        entry_status = 'NO_ZONE'
        
        should_send, message = _validate_signal_timing(signal_data, entry_zone, entry_status)
        
        self.assertFalse(should_send, "Signal should NOT be sent for NO_ZONE")
        self.assertIn("Няма валидна", message, "Message should mention no zone")
    
    def test_valid_wait_allows_signal(self):
        """Test that VALID_WAIT status allows signal"""
        from signal_helpers import _validate_signal_timing
        
        signal_data = {'symbol': 'SOLUSDT'}
        entry_zone = {'center': 126.50, 'distance_pct': 2.0}
        entry_status = 'VALID_WAIT'
        
        should_send, message = _validate_signal_timing(signal_data, entry_zone, entry_status)
        
        self.assertTrue(should_send, "Signal SHOULD be sent for VALID_WAIT")
        self.assertIn("ЧАКАЙ", message, "Message should mention waiting")
    
    def test_valid_near_allows_signal(self):
        """Test that VALID_NEAR status allows signal"""
        from signal_helpers import _validate_signal_timing
        
        signal_data = {'symbol': 'SOLUSDT'}
        entry_zone = {'center': 125.50, 'distance_pct': 1.0}
        entry_status = 'VALID_NEAR'
        
        should_send, message = _validate_signal_timing(signal_data, entry_zone, entry_status)
        
        self.assertTrue(should_send, "Signal SHOULD be sent for VALID_NEAR")
        self.assertIn("приближава", message, "Message should mention approaching")


class TestEntryGuidanceFormatting(unittest.TestCase):
    """Test entry guidance message formatting"""
    
    def test_sell_guidance_shows_up_arrow(self):
        """Test that SELL signals show upward arrow"""
        from signal_helpers import _format_entry_guidance
        
        entry_zone = {
            'source': 'FVG',
            'center': 126.50,
            'low': 126.30,
            'high': 126.70,
            'quality': 85,
            'distance_pct': 1.5,
            'distance_price': 1.72
        }
        
        guidance = _format_entry_guidance(entry_zone, 'VALID_WAIT', 124.78, 'BEARISH')
        
        self.assertIn("⬆️", guidance, "SELL guidance should show upward arrow")
        self.assertIn("FVG", guidance, "Should show source")
        self.assertIn("126.50", guidance, "Should show center price")
    
    def test_buy_guidance_shows_down_arrow(self):
        """Test that BUY signals show downward arrow"""
        from signal_helpers import _format_entry_guidance
        
        entry_zone = {
            'source': 'OB',
            'center': 122.50,
            'low': 122.30,
            'high': 122.70,
            'quality': 80,
            'distance_pct': 1.8,
            'distance_price': 2.28
        }
        
        guidance = _format_entry_guidance(entry_zone, 'VALID_WAIT', 124.78, 'BULLISH')
        
        self.assertIn("⬇️", guidance, "BUY guidance should show downward arrow")
        self.assertIn("OB", guidance, "Should show source")
        self.assertIn("122.50", guidance, "Should show center price")
    
    def test_wait_status_shows_warning(self):
        """Test that VALID_WAIT shows proper warning"""
        from signal_helpers import _format_entry_guidance
        
        entry_zone = {
            'source': 'FVG',
            'center': 126.50,
            'low': 126.30,
            'high': 126.70,
            'quality': 85,
            'distance_pct': 2.0,
            'distance_price': 1.72
        }
        
        guidance = _format_entry_guidance(entry_zone, 'VALID_WAIT', 124.78, 'BEARISH')
        
        self.assertIn("НЕ влизай веднага", guidance, "Should warn against immediate entry")
        self.assertIn("WAIT FOR PULLBACK", guidance, "Should show wait status")
        self.assertIn("alert", guidance.lower(), "Should suggest setting alert")
    
    def test_near_status_shows_preparation(self):
        """Test that VALID_NEAR shows preparation instructions"""
        from signal_helpers import _format_entry_guidance
        
        entry_zone = {
            'source': 'OB',
            'center': 125.50,
            'low': 125.30,
            'high': 125.70,
            'quality': 80,
            'distance_pct': 0.8,
            'distance_price': 0.72
        }
        
        guidance = _format_entry_guidance(entry_zone, 'VALID_NEAR', 124.78, 'BEARISH')
        
        self.assertIn("APPROACHING", guidance, "Should show approaching status")
        self.assertIn("Подготви се", guidance, "Should show preparation instructions")
        self.assertIn("15-60 мин", guidance, "Should show estimated time")


if __name__ == '__main__':
    unittest.main()
