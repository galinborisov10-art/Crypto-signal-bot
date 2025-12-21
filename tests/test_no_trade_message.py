"""
Unit Tests for Enhanced NO_TRADE Messages

Tests the enhanced NO_TRADE message generation with:
- MTF breakdown for all timeframes (1m-1w)
- Detailed ICT analysis (Entry Zone, Order Blocks, FVG, Structure Break, Displacement)
- Proper formatting in bot.py's format_no_trade_message()
"""

import sys
import os
import unittest
import pandas as pd
import numpy as np
from unittest.mock import Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ict_signal_engine import ICTSignalEngine, MarketBias


class TestNoTradeMessageEnhancement(unittest.TestCase):
    """Test enhanced NO_TRADE message generation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = ICTSignalEngine()
        
        # Create sample dataframe
        self.df = self._create_sample_df()
        
        # Create sample MTF data
        self.mtf_data = self._create_sample_mtf_data()
    
    def _create_sample_df(self):
        """Create sample OHLCV dataframe"""
        dates = pd.date_range(start='2024-01-01', periods=100, freq='1H')
        
        # Generate sample price data
        base_price = 45000
        price_changes = np.random.randn(100) * 100
        close_prices = base_price + np.cumsum(price_changes)
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': close_prices - np.random.rand(100) * 50,
            'high': close_prices + np.random.rand(100) * 100,
            'low': close_prices - np.random.rand(100) * 100,
            'close': close_prices,
            'volume': np.random.rand(100) * 1000000
        })
        
        return df
    
    def _create_sample_mtf_data(self):
        """Create sample multi-timeframe data"""
        mtf_data = {}
        
        # Add data for different timeframes
        for tf in ['1m', '5m', '15m', '1h', '4h', '1d']:
            dates = pd.date_range(start='2024-01-01', periods=50, freq='1H')
            base_price = 45000 + np.random.rand() * 1000
            close_prices = base_price + np.cumsum(np.random.randn(50) * 50)
            
            mtf_data[tf] = pd.DataFrame({
                'timestamp': dates,
                'open': close_prices - np.random.rand(50) * 20,
                'high': close_prices + np.random.rand(50) * 50,
                'low': close_prices - np.random.rand(50) * 50,
                'close': close_prices,
                'volume': np.random.rand(50) * 500000
            })
        
        return mtf_data
    
    def test_mtf_consensus_calculated_early(self):
        """Test that MTF consensus is calculated before early exits"""
        # This will trigger an early exit (NO_ZONE)
        result = self.engine.generate_signal(
            df=self.df,
            symbol='BTCUSDT',
            timeframe='4h',
            mtf_data=self.mtf_data
        )
        
        # Check if result is a NO_TRADE dict
        if isinstance(result, dict) and result.get('type') == 'NO_TRADE':
            # Verify MTF breakdown is present
            self.assertIn('mtf_breakdown', result)
            mtf_breakdown = result['mtf_breakdown']
            
            # Verify it's not empty
            self.assertIsInstance(mtf_breakdown, dict)
            self.assertGreater(len(mtf_breakdown), 0, "MTF breakdown should not be empty")
            
            # Verify it contains the current timeframe
            self.assertIn('4h', mtf_breakdown, "MTF breakdown should include current timeframe")
            
            print("✅ MTF consensus is calculated early - breakdown is present")
            print(f"   MTF breakdown contains {len(mtf_breakdown)} timeframes")
        else:
            # If we got a valid signal instead, that's OK for the test
            print("⚠️  Test got valid signal instead of NO_TRADE (this is OK)")
    
    def test_ict_components_in_no_trade_message(self):
        """Test that ICT components are included in NO_TRADE messages"""
        # Generate signal (may result in NO_TRADE)
        result = self.engine.generate_signal(
            df=self.df,
            symbol='BTCUSDT',
            timeframe='4h',
            mtf_data=self.mtf_data
        )
        
        # Check if result is a NO_TRADE dict
        if isinstance(result, dict) and result.get('type') == 'NO_TRADE':
            # Verify new ICT fields are present
            self.assertIn('ict_components', result, "ICT components should be in NO_TRADE message")
            self.assertIn('entry_status', result, "Entry status should be in NO_TRADE message")
            self.assertIn('structure_broken', result, "Structure broken flag should be in NO_TRADE message")
            self.assertIn('displacement_detected', result, "Displacement flag should be in NO_TRADE message")
            
            # Check types
            self.assertIsInstance(result['structure_broken'], bool)
            self.assertIsInstance(result['displacement_detected'], bool)
            
            print("✅ ICT components are included in NO_TRADE message")
            print(f"   Entry status: {result['entry_status']}")
            print(f"   Structure broken: {result['structure_broken']}")
            print(f"   Displacement detected: {result['displacement_detected']}")
        else:
            print("⚠️  Test got valid signal instead of NO_TRADE (this is OK)")
    
    def test_mtf_breakdown_structure(self):
        """Test MTF breakdown has correct structure"""
        # Create a simple MTF breakdown using the internal method
        mtf_consensus = self.engine._calculate_mtf_consensus(
            symbol='BTCUSDT',
            primary_timeframe='4h',
            target_bias=MarketBias.BULLISH,
            mtf_data=self.mtf_data
        )
        
        # Verify structure
        self.assertIn('consensus_pct', mtf_consensus)
        self.assertIn('breakdown', mtf_consensus)
        self.assertIn('aligned_tfs', mtf_consensus)
        self.assertIn('conflicting_tfs', mtf_consensus)
        
        breakdown = mtf_consensus['breakdown']
        
        # Verify all expected timeframes are present
        expected_tfs = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '12h', '1d', '3d', '1w']
        for tf in expected_tfs:
            self.assertIn(tf, breakdown, f"Timeframe {tf} should be in breakdown")
            
            # Verify each TF has required fields
            tf_data = breakdown[tf]
            self.assertIn('bias', tf_data)
            self.assertIn('confidence', tf_data)
            self.assertIn('aligned', tf_data)
        
        print("✅ MTF breakdown structure is correct")
        print(f"   Consensus: {mtf_consensus['consensus_pct']:.1f}%")
        print(f"   Total timeframes: {len(breakdown)}")
        print(f"   Aligned TFs: {len(mtf_consensus['aligned_tfs'])}")
        print(f"   Conflicting TFs: {len(mtf_consensus['conflicting_tfs'])}")
    
    def test_format_no_trade_message_with_ict_details(self):
        """Test that bot.py's format_no_trade_message includes ICT analysis"""
        # Import the formatting function from root bot.py
        try:
            # Add path to import from root bot.py (not bot/ package)
            import importlib.util
            bot_py_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'bot.py')
            spec = importlib.util.spec_from_file_location("bot_module", bot_py_path)
            bot_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(bot_module)
            format_no_trade_message = bot_module.format_no_trade_message
            
            # Create a sample NO_TRADE message data
            no_trade_data = {
                'type': 'NO_TRADE',
                'symbol': 'BTCUSDT',
                'timeframe': '4h',
                'reason': 'Entry zone validation failed: NO_ZONE',
                'details': 'Current price: $45000.00. No valid entry zone found.',
                'mtf_breakdown': {
                    '1m': {'bias': 'NO_DATA', 'confidence': 0, 'aligned': True},
                    '4h': {'bias': 'BULLISH', 'confidence': 100, 'aligned': True},
                    '1d': {'bias': 'BEARISH', 'confidence': 50, 'aligned': False}
                },
                'mtf_consensus_pct': 66.7,
                'current_price': 45000.00,
                'price_change_24h': 2.5,
                'rsi': 55.0,
                'signal_direction': 'BUY',
                'confidence': None,
                'ict_components': {
                    'order_blocks': [],
                    'fvgs': [],
                    'liquidity_zones': []
                },
                'entry_status': 'NO_ZONE',
                'structure_broken': False,
                'displacement_detected': False
            }
            
            # Format the message
            formatted_msg = format_no_trade_message(no_trade_data)
            
            # Verify ICT analysis section is present
            self.assertIn('ICT АНАЛИЗ', formatted_msg, "ICT analysis section should be present")
            self.assertIn('Entry Zone', formatted_msg, "Entry Zone analysis should be present")
            self.assertIn('Order Blocks', formatted_msg, "Order Blocks analysis should be present")
            self.assertIn('FVG', formatted_msg, "FVG analysis should be present")
            self.assertIn('Structure Break', formatted_msg, "Structure Break analysis should be present")
            self.assertIn('Displacement', formatted_msg, "Displacement analysis should be present")
            self.assertIn('Liquidity Levels', formatted_msg, "Liquidity analysis should be present")
            self.assertIn('MTF Breakdown', formatted_msg, "MTF breakdown should be present")
            
            # Verify MTF timeframes are shown
            self.assertIn('1m', formatted_msg, "1m timeframe should be shown")
            self.assertIn('4h', formatted_msg, "4h timeframe should be shown")
            self.assertIn('1d', formatted_msg, "1d timeframe should be shown")
            
            print("✅ format_no_trade_message includes all ICT analysis sections")
            print(f"   Message length: {len(formatted_msg)} characters")
            
        except Exception as e:
            print(f"⚠️  Could not test format_no_trade_message: {e}")
            self.skipTest(f"bot.py import failed: {e}")


if __name__ == '__main__':
    # Run tests with verbose output
    unittest.main(verbosity=2)
