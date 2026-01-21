"""
Regression tests for confidence bounds (ESB implicit contract)

ESB v1.0 implicitly requires that confidence scores are percentage-like:
- Range: 0-100
- Used for display as "увереност" (confidence %)
- Compared against thresholds (60%, 85%)

These tests verify this contract BEFORE adding clamping logic.
If these tests fail, it indicates the scoring system needs adjustment.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from ict_signal_engine import ICTSignalEngine, MarketBias


class TestConfidenceBounds:
    """Test that confidence respects implicit 0-100 bounds"""
    
    @pytest.fixture
    def engine(self):
        """Create ICT Signal Engine instance"""
        return ICTSignalEngine()
    
    @pytest.fixture
    def sample_df(self):
        """Create sample DataFrame with OHLCV data"""
        dates = pd.date_range(start='2025-01-01', periods=100, freq='1h')
        
        df = pd.DataFrame({
            'timestamp': dates,
            'open': np.linspace(50000, 51000, 100),
            'high': np.linspace(50100, 51100, 100),
            'low': np.linspace(49900, 50900, 100),
            'close': np.linspace(50000, 51000, 100),
            'volume': np.random.randint(1000, 10000, 100),
        })
        
        df.set_index('timestamp', inplace=True)
        return df
    
    def test_confidence_never_exceeds_100(self, engine, sample_df):
        """
        Test: Confidence should NEVER exceed 100
        
        ESB Contract: Confidence is displayed as percentage (0-100%)
        This test uses MAXIMUM confluence scenario:
        - All ICT components present
        - Maximum boosts (LuxAlgo, Fibonacci, context)
        - ML confidence boost
        
        Expected: confidence <= 100.0
        """
        # Create maximum confluence components
        ict_components = {
            'whale_blocks': [{'strength': 90} for _ in range(5)],  # Max whale blocks
            'liquidity_zones': [{'price': 50000} for _ in range(10)],  # Max liquidity
            'order_blocks': [{'strength': 85} for _ in range(5)],  # Max OBs
            'fvgs': [{'strength': 80} for _ in range(5)],  # Max FVGs
            'breaker_blocks': [{'strength': 75} for _ in range(3)],
            'mitigation_blocks': [{'strength': 70} for _ in range(3)],
            'sibi_ssib_zones': [{'strength': 65} for _ in range(3)],
            'luxalgo_sr': {
                'support_zones': [{'price': 49000}],
                'resistance_zones': [{'price': 51000}]
            },
            'luxalgo_combined': {'entry_valid': True, 'bias': 'BULLISH'},
            'fibonacci_data': {'in_ote_zone': True}
        }
        
        mtf_analysis = {'confluence_count': 5}
        
        # Calculate confidence
        confidence = engine._calculate_signal_confidence(
            ict_components=ict_components,
            mtf_analysis=mtf_analysis,
            bias=MarketBias.BULLISH,
            structure_broken=True,
            displacement_detected=True,
            risk_reward_ratio=5.0
        )
        
        # Assert: confidence MUST NOT exceed 100
        assert confidence <= 100.0, (
            f"Confidence {confidence:.2f}% exceeds maximum 100%. "
            f"This violates ESB implicit contract (confidence as percentage)."
        )
        
        print(f"✅ Maximum confluence confidence: {confidence:.2f}% (≤ 100)")
    
    def test_confidence_never_negative(self, engine, sample_df):
        """
        Test: Confidence should NEVER be negative
        
        ESB Contract: Confidence represents confluence quality (0-100%)
        This test uses MINIMUM confluence scenario:
        - Minimal ICT components
        - Negative adjustments (volume, bias penalty)
        - No boosts
        
        Expected: confidence >= 0.0
        """
        # Create minimal confluence components
        ict_components = {
            'whale_blocks': [],
            'liquidity_zones': [],
            'order_blocks': [],
            'fvgs': [],
            'breaker_blocks': [],
            'mitigation_blocks': [],
            'sibi_ssib_zones': [],
            'luxalgo_sr': {},
            'luxalgo_combined': {},
            'fibonacci_data': {}
        }
        
        mtf_analysis = None  # No MTF confluence
        
        # Calculate confidence with penalties
        confidence = engine._calculate_signal_confidence(
            ict_components=ict_components,
            mtf_analysis=mtf_analysis,
            bias=MarketBias.RANGING,  # Applies 0.8 penalty
            structure_broken=False,
            displacement_detected=False,
            risk_reward_ratio=1.0  # Low RR
        )
        
        # Assert: confidence MUST NOT be negative
        assert confidence >= 0.0, (
            f"Confidence {confidence:.2f}% is negative. "
            f"This violates ESB implicit contract (confidence as percentage)."
        )
        
        print(f"✅ Minimum confluence confidence: {confidence:.2f}% (≥ 0)")
