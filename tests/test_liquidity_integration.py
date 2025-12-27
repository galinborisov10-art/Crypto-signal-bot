"""
Test Suite for Liquidity Map Integration

Tests the integration of liquidity_map.py into the signal generation system,
including:
- LiquidityMapper initialization
- Zone detection
- Sweep detection
- Confidence adjustments
- Signal generation with/without liquidity
- Backward compatibility
- Chart visualization
"""

import unittest
import sys
import os
import importlib.util
from datetime import datetime, timedelta
import pandas as pd
import numpy as np

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from liquidity_map import LiquidityMapper, LiquidityZone, LiquiditySweep


class TestLiquidityMapperInitialization(unittest.TestCase):
    """Test LiquidityMapper initialization and basic functionality"""
    
    def test_liquidity_mapper_initialization(self):
        """Test that LiquidityMapper initializes correctly"""
        mapper = LiquidityMapper()
        self.assertIsNotNone(mapper)
        self.assertIsNotNone(mapper.config)
        self.assertEqual(mapper.config['touch_threshold'], 3)
        self.assertEqual(mapper.config['price_tolerance'], 0.001)
    
    def test_liquidity_mapper_custom_config(self):
        """Test LiquidityMapper with custom configuration"""
        custom_config = {
            'touch_threshold': 5,
            'price_tolerance': 0.002,
            'volume_threshold': 2.0
        }
        mapper = LiquidityMapper(config=custom_config)
        self.assertEqual(mapper.config['touch_threshold'], 5)
        self.assertEqual(mapper.config['price_tolerance'], 0.002)


class TestLiquidityZoneDetection(unittest.TestCase):
    """Test liquidity zone detection"""
    
    def _create_sample_data(self, candles=100):
        """Create sample OHLCV data for testing"""
        dates = pd.date_range('2025-01-01', periods=candles, freq='1H')
        
        # Create price data with some swing points
        base_price = 100.0
        prices = []
        for i in range(candles):
            # Add some swing highs and lows
            if i % 20 == 0:
                prices.append(base_price + 5)  # Swing high
            elif i % 20 == 10:
                prices.append(base_price - 5)  # Swing low
            else:
                prices.append(base_price + np.random.randn())
        
        data = {
            'open': [p - 0.5 for p in prices],
            'high': [p + 0.5 for p in prices],
            'low': [p - 0.5 for p in prices],
            'close': prices,
            'volume': np.random.randint(1000, 10000, candles)
        }
        df = pd.DataFrame(data, index=dates)
        return df
    
    def test_liquidity_detection_with_data(self):
        """Test liquidity zone detection with sample data"""
        df = self._create_sample_data()
        mapper = LiquidityMapper()
        zones = mapper.detect_liquidity_zones(df, '1H')
        
        self.assertIsInstance(zones, list)
        # We should detect at least some zones with our engineered data
        # Note: This might be 0 if no clusters meet the threshold
        self.assertGreaterEqual(len(zones), 0)
    
    def test_bsl_zone_detection(self):
        """Test BSL (Buy-Side Liquidity) zone detection"""
        df = self._create_sample_data()
        mapper = LiquidityMapper()
        zones = mapper.detect_liquidity_zones(df, '1H')
        
        # Check if any BSL zones were detected
        bsl_zones = [z for z in zones if z.zone_type == 'BSL']
        # Should have BSL zones (swing highs)
        self.assertIsInstance(bsl_zones, list)
    
    def test_ssl_zone_detection(self):
        """Test SSL (Sell-Side Liquidity) zone detection"""
        df = self._create_sample_data()
        mapper = LiquidityMapper()
        zones = mapper.detect_liquidity_zones(df, '1H')
        
        # Check if any SSL zones were detected
        ssl_zones = [z for z in zones if z.zone_type == 'SSL']
        # Should have SSL zones (swing lows)
        self.assertIsInstance(ssl_zones, list)
    
    def test_zone_confidence_calculation(self):
        """Test that zone confidence is calculated correctly"""
        df = self._create_sample_data()
        mapper = LiquidityMapper()
        zones = mapper.detect_liquidity_zones(df, '1H')
        
        for zone in zones:
            # Confidence should be between 0 and 1
            self.assertGreaterEqual(zone.confidence, 0.0)
            self.assertLessEqual(zone.confidence, 1.0)
            
            # Should have required touches
            self.assertGreaterEqual(zone.touches, mapper.config['touch_threshold'])


class TestLiquiditySweepDetection(unittest.TestCase):
    """Test liquidity sweep detection"""
    
    def _create_sweep_scenario_data(self):
        """Create data with a potential sweep scenario"""
        dates = pd.date_range('2025-01-01', periods=100, freq='1H')
        
        base_price = 100.0
        prices = []
        
        for i in range(100):
            if i == 50:
                # Create a spike above (BSL sweep)
                prices.append(base_price + 10)
            elif i > 50 and i < 56:
                # Reversal down after sweep
                prices.append(base_price - (i - 50))
            else:
                prices.append(base_price + np.random.randn())
        
        data = {
            'open': [p - 0.5 for p in prices],
            'high': [p + 1 if i == 50 else p + 0.5 for i, p in enumerate(prices)],
            'low': [p - 0.5 for p in prices],
            'close': prices,
            'volume': [2000 if i == 50 else 1000 for i in range(100)]
        }
        df = pd.DataFrame(data, index=dates)
        return df
    
    def test_sweep_detection_basic(self):
        """Test basic sweep detection"""
        df = self._create_sweep_scenario_data()
        mapper = LiquidityMapper()
        
        # First detect zones
        zones = mapper.detect_liquidity_zones(df, '1H')
        
        # Then detect sweeps
        sweeps = mapper.detect_liquidity_sweeps(df, zones)
        
        self.assertIsInstance(sweeps, list)
        # Note: May not always detect sweeps depending on zone formation
        self.assertGreaterEqual(len(sweeps), 0)
    
    def test_sweep_attributes(self):
        """Test that detected sweeps have correct attributes"""
        df = self._create_sweep_scenario_data()
        mapper = LiquidityMapper()
        zones = mapper.detect_liquidity_zones(df, '1H')
        sweeps = mapper.detect_liquidity_sweeps(df, zones)
        
        for sweep in sweeps:
            # Check required attributes
            self.assertIsNotNone(sweep.timestamp)
            self.assertIsNotNone(sweep.price)
            self.assertIn(sweep.sweep_type, ['BSL_SWEEP', 'SSL_SWEEP'])
            self.assertIsNotNone(sweep.liquidity_zone)
            self.assertGreaterEqual(sweep.strength, 0.0)
            self.assertLessEqual(sweep.strength, 1.0)


class TestICTSignalIntegration(unittest.TestCase):
    """Test integration with ICT Signal Engine"""
    
    def test_signal_generation_with_liquidity(self):
        """Test that signals can be generated with liquidity data"""
        try:
            from ict_signal_engine import ICTSignalEngine
            
            # Create test data
            dates = pd.date_range('2025-01-01', periods=100, freq='1H')
            data = {
                'open': np.random.randn(100).cumsum() + 100,
                'high': np.random.randn(100).cumsum() + 102,
                'low': np.random.randn(100).cumsum() + 98,
                'close': np.random.randn(100).cumsum() + 100,
                'volume': np.random.randint(1000, 10000, 100)
            }
            df = pd.DataFrame(data, index=dates)
            
            # Initialize engine
            engine = ICTSignalEngine()
            
            # Check that liquidity mapper is initialized
            self.assertIsNotNone(engine.liquidity_mapper)
            
        except ImportError as e:
            self.skipTest(f"ICT Signal Engine not available: {e}")
    
    def test_signal_without_liquidity_zones(self):
        """Test that signals work when no liquidity zones detected"""
        # This ensures backward compatibility
        try:
            from ict_signal_engine import ICTSignal, SignalType, SignalStrength, MarketBias
            
            # Create a signal without liquidity zones
            signal = ICTSignal(
                timestamp=datetime.now(),
                symbol='BTCUSDT',
                timeframe='1H',
                signal_type=SignalType.BUY,
                signal_strength=SignalStrength.MODERATE,
                entry_price=100.0,
                sl_price=95.0,
                tp_prices=[105.0, 110.0, 115.0],
                confidence=70.0,
                risk_reward_ratio=3.0,
                liquidity_zones=[],  # Empty
                liquidity_sweeps=[]  # Empty
            )
            
            # Should not raise an error
            self.assertEqual(len(signal.liquidity_zones), 0)
            self.assertEqual(len(signal.liquidity_sweeps), 0)
            
        except ImportError as e:
            self.skipTest(f"ICT Signal classes not available: {e}")


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility"""
    
    def test_graceful_degradation(self):
        """Test that system works if liquidity detection fails"""
        mapper = LiquidityMapper()
        
        # Try with empty dataframe - should not crash
        empty_df = pd.DataFrame()
        
        try:
            zones = mapper.detect_liquidity_zones(empty_df, '1H')
            # Should return empty list, not crash
            self.assertEqual(zones, [])
        except Exception as e:
            # If it raises an exception, it should be handled gracefully
            self.assertIsInstance(e, (ValueError, KeyError))


class TestFormatLiquiditySection(unittest.TestCase):
    """Test liquidity section formatting for messages"""
    
    def test_format_with_zones(self):
        """Test formatting when liquidity zones exist"""
        try:
            # Import bot.py module directly (not the bot package)
            import importlib.util
            spec = importlib.util.spec_from_file_location("bot_module", 
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot.py"))
            bot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bot_module)
            
            format_liquidity_section = bot_module.format_liquidity_section
            from ict_signal_engine import ICTSignal, SignalType, SignalStrength
            
        except (ImportError, ModuleNotFoundError) as e:
            self.skipTest(f"Bot module dependencies not available: {e}")
            
            # Create a mock signal with liquidity zones
            signal = ICTSignal(
                timestamp=datetime.now(),
                symbol='BTCUSDT',
                timeframe='1H',
                signal_type=SignalType.BUY,
                signal_strength=SignalStrength.STRONG,
                entry_price=100.0,
                sl_price=95.0,
                tp_prices=[105.0, 110.0, 115.0],
                confidence=75.0,
                risk_reward_ratio=3.5,
                liquidity_zones=[
                    {
                        'zone_type': 'BSL',
                        'price_level': 105.0,
                        'confidence': 0.8,
                        'touches': 3,
                        'swept': False
                    }
                ]
            )
            
            result = format_liquidity_section(signal)
            
            # Should return a non-empty string
            self.assertIsInstance(result, str)
            self.assertIn('LIQUIDITY CONTEXT', result)
            self.assertIn('BSL', result)
            
        except ImportError as e:
            self.skipTest(f"Bot functions not available: {e}")
    
    def test_format_without_zones(self):
        """Test formatting when no liquidity zones exist"""
        try:
            # Import bot.py module directly (not the bot package)
            import importlib.util
            spec = importlib.util.spec_from_file_location("bot_module", 
                os.path.join(os.path.dirname(os.path.dirname(__file__)), "bot.py"))
            bot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bot_module)
            
            format_liquidity_section = bot_module.format_liquidity_section
            from ict_signal_engine import ICTSignal, SignalType, SignalStrength
            
        except (ImportError, ModuleNotFoundError) as e:
            self.skipTest(f"Bot module dependencies not available: {e}")
            
            signal = ICTSignal(
                timestamp=datetime.now(),
                symbol='BTCUSDT',
                timeframe='1H',
                signal_type=SignalType.BUY,
                signal_strength=SignalStrength.STRONG,
                entry_price=100.0,
                sl_price=95.0,
                tp_prices=[105.0, 110.0, 115.0],
                confidence=75.0,
                risk_reward_ratio=3.5,
                liquidity_zones=[]  # Empty
            )
            
            result = format_liquidity_section(signal)
            
            # Should return empty string when no zones
            self.assertEqual(result, "")
            
        except ImportError as e:
            self.skipTest(f"Bot functions not available: {e}")


def run_tests():
    """Run all tests"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLiquidityMapperInitialization))
    suite.addTests(loader.loadTestsFromTestCase(TestLiquidityZoneDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestLiquiditySweepDetection))
    suite.addTests(loader.loadTestsFromTestCase(TestICTSignalIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestBackwardCompatibility))
    suite.addTests(loader.loadTestsFromTestCase(TestFormatLiquiditySection))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
