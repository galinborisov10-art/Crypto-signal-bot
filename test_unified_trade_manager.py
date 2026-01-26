"""
Test suite for UnifiedTradeManager

Validates:
1. Progress calculation (BUY/SELL)
2. Checkpoint detection
3. Bulgarian alert formatting
4. Manager initialization
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_manager_initialization():
    """Test UnifiedTradeManager initialization"""
    from unified_trade_manager import UnifiedTradeManager
    
    manager = UnifiedTradeManager()
    
    assert manager.reanalysis_engine is not None, "ReanalysisEngine should be initialized"
    assert manager.position_manager is not None, "PositionManager should be initialized"
    
    print("✅ Manager initialization test passed")


def test_progress_calculation():
    """Test progress calculation for BUY and SELL signals"""
    from unified_trade_manager import UnifiedTradeManager
    
    manager = UnifiedTradeManager()
    
    # BUY signal test: Entry $100, TP1 $110, Current $105
    # Expected: 50% progress
    progress_buy = manager._calculate_progress(
        entry_price=100.0,
        tp1_price=110.0,
        current_price=105.0,
        signal_type='BUY'
    )
    
    assert 49.0 <= progress_buy <= 51.0, f"BUY progress should be ~50%, got {progress_buy}%"
    
    # SELL signal test: Entry $100, TP1 $90, Current $95
    # Expected: 50% progress
    progress_sell = manager._calculate_progress(
        entry_price=100.0,
        tp1_price=90.0,
        current_price=95.0,
        signal_type='SELL'
    )
    
    assert 49.0 <= progress_sell <= 51.0, f"SELL progress should be ~50%, got {progress_sell}%"
    
    # Edge case: 0% progress
    progress_zero = manager._calculate_progress(
        entry_price=100.0,
        tp1_price=110.0,
        current_price=100.0,
        signal_type='BUY'
    )
    
    assert progress_zero == 0.0, f"0% progress expected, got {progress_zero}%"
    
    # Edge case: 100% progress
    progress_full = manager._calculate_progress(
        entry_price=100.0,
        tp1_price=110.0,
        current_price=110.0,
        signal_type='BUY'
    )
    
    assert progress_full == 100.0, f"100% progress expected, got {progress_full}%"
    
    print("✅ Progress calculation test passed")


def test_checkpoint_detection():
    """Test checkpoint level detection"""
    from unified_trade_manager import UnifiedTradeManager
    
    manager = UnifiedTradeManager()
    
    # Test 25% checkpoint
    assert manager._get_checkpoint_level(23.0) == None, "23% should not trigger checkpoint"
    assert manager._get_checkpoint_level(24.9) == None, "24.9% should not trigger checkpoint"
    assert manager._get_checkpoint_level(25.0) == '25%', "25% should trigger 25% checkpoint"
    assert manager._get_checkpoint_level(26.0) == '25%', "26% should trigger 25% checkpoint"
    assert manager._get_checkpoint_level(48.0) == '25%', "48% should still be 25% checkpoint"
    
    # Test 50% checkpoint
    assert manager._get_checkpoint_level(49.9) == '25%', "49.9% should still be 25% checkpoint"
    assert manager._get_checkpoint_level(50.0) == '50%', "50% should trigger 50% checkpoint"
    assert manager._get_checkpoint_level(52.0) == '50%', "52% should trigger 50% checkpoint"
    assert manager._get_checkpoint_level(74.9) == '50%', "74.9% should still be 50% checkpoint"
    
    # Test 75% checkpoint
    assert manager._get_checkpoint_level(75.0) == '75%', "75% should trigger 75% checkpoint"
    assert manager._get_checkpoint_level(77.0) == '75%', "77% should trigger 75% checkpoint"
    assert manager._get_checkpoint_level(84.9) == '75%', "84.9% should still be 75% checkpoint"
    
    # Test 85% checkpoint
    assert manager._get_checkpoint_level(85.0) == '85%', "85% should trigger 85% checkpoint"
    assert manager._get_checkpoint_level(90.0) == '85%', "90% should trigger 85% checkpoint"
    assert manager._get_checkpoint_level(100.0) == '85%', "100% should trigger 85% checkpoint"
    
    # Test low progress
    assert manager._get_checkpoint_level(15.0) == None, "15% should not trigger any checkpoint"
    assert manager._get_checkpoint_level(0.0) == None, "0% should not trigger any checkpoint"
    
    print("✅ Checkpoint detection test passed")


def test_checkpoint_price_calculation():
    """Test checkpoint price calculation"""
    from unified_trade_manager import UnifiedTradeManager
    
    manager = UnifiedTradeManager()
    
    # BUY signal: Entry $100, TP1 $110
    # 25% checkpoint should be at $102.50
    checkpoint_25_buy = manager._calculate_checkpoint_price(
        entry_price=100.0,
        tp1_price=110.0,
        checkpoint_percent=0.25,
        signal_type='BUY'
    )
    
    assert 102.4 <= checkpoint_25_buy <= 102.6, f"BUY 25% checkpoint should be ~$102.50, got ${checkpoint_25_buy}"
    
    # SELL signal: Entry $100, TP1 $90
    # 25% checkpoint should be at $97.50
    checkpoint_25_sell = manager._calculate_checkpoint_price(
        entry_price=100.0,
        tp1_price=90.0,
        checkpoint_percent=0.25,
        signal_type='SELL'
    )
    
    assert 97.4 <= checkpoint_25_sell <= 97.6, f"SELL 25% checkpoint should be ~$97.50, got ${checkpoint_25_sell}"
    
    print("✅ Checkpoint price calculation test passed")


def test_bulgarian_alert_formatting():
    """Test Bulgarian alert message formatting"""
    from unified_trade_manager import UnifiedTradeManager
    from trade_reanalysis_engine import CheckpointAnalysis, RecommendationType
    
    manager = UnifiedTradeManager()
    
    # Create mock analysis
    analysis = CheckpointAnalysis(
        checkpoint_level='25%',
        checkpoint_price=102.5,
        current_price=102.5,
        distance_to_tp=7.3,
        distance_to_sl=2.4,
        original_confidence=78.0,
        current_confidence=76.0,
        confidence_delta=-2.0,
        htf_bias_changed=False,
        structure_broken=False,
        valid_components_count=5,
        current_rr_ratio=3.0,
        recommendation=RecommendationType.HOLD,
        reasoning="Структурата е стабилна, confidence-а е почти същият."
    )
    
    # Mock position
    position = {
        'symbol': 'BTCUSDT',
        'entry_price': 100.0,
        'tp1_price': 110.0,
        'sl_price': 95.0,
        'signal_type': 'BUY'
    }
    
    # Generate Bulgarian alert
    alert = manager._format_basic_alert_bulgarian(
        checkpoint='25%',
        analysis=analysis,
        news=None,
        position=position,
        current_price=102.5
    )
    
    # Validate alert contains key elements
    assert '25%' in alert, "Alert should contain checkpoint level"
    assert 'BTCUSDT' in alert, "Alert should contain symbol"
    assert 'Confidence' in alert or 'Увереност' in alert, "Alert should contain confidence info"
    assert 'ПРЕПОРЪКА' in alert, "Alert should contain recommendation"
    assert '💎' in alert or '🟡' in alert or '🔴' in alert, "Alert should contain status icon"
    
    print("✅ Bulgarian alert formatting test passed")


if __name__ == '__main__':
    print("🧪 Running UnifiedTradeManager tests...\n")
    
    try:
        test_manager_initialization()
        test_progress_calculation()
        test_checkpoint_detection()
        test_checkpoint_price_calculation()
        test_bulgarian_alert_formatting()
        
        print("\n🎉 All tests passed!")
        sys.exit(0)
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
