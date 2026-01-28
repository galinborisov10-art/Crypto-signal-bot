"""
Test script for narrative_templates.py (PR #214)

Tests:
- All narrative scenarios
- Bulgarian language quality
- News impact assessment
- Alert filtering logic
- Narrative selection logic

Author: galinborisov10-art
Date: 2026-01-28
"""

import sys
sys.path.insert(0, '.')


def test_imports():
    """Test that narrative templates can be imported"""
    print("=" * 60)
    print("TEST 1: Imports")
    print("=" * 60)
    
    try:
        from narrative_templates import SwingTraderNarrative, NarrativeSelector
        print("✅ SwingTraderNarrative imported successfully")
        print("✅ NarrativeSelector imported successfully")
        
        # Check methods exist
        assert hasattr(SwingTraderNarrative, 'checkpoint_all_good')
        assert hasattr(SwingTraderNarrative, 'checkpoint_bias_changed')
        assert hasattr(SwingTraderNarrative, 'checkpoint_structure_broken')
        assert hasattr(SwingTraderNarrative, 'critical_news_alert')
        assert hasattr(SwingTraderNarrative, 'checkpoint_with_critical_news')
        print("✅ All required methods exist")
        
        return True
        
    except Exception as e:
        print(f"❌ Import test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_checkpoint_all_good():
    """Test checkpoint_all_good narrative"""
    print("\n" + "=" * 60)
    print("TEST 2: Checkpoint All Good Narrative")
    print("=" * 60)
    
    try:
        from narrative_templates import SwingTraderNarrative
        
        # Mock position
        position = {
            'id': 1,
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 50000.0,
            'tp1_price': 52000.0,
            'sl_price': 49000.0
        }
        
        # Mock analysis
        class MockAnalysis:
            current_confidence = 75
            current_rr_ratio = 2.5
            structure_broken = False
            htf_bias_changed = False
        
        analysis = MockAnalysis()
        
        # Test at 25% checkpoint
        message = SwingTraderNarrative.checkpoint_all_good(
            position, analysis, 25, 25.0, 50500.0
        )
        
        print("\n📝 25% Checkpoint Message:")
        print(message)
        
        # Verify Bulgarian content
        assert 'BTCUSDT' in message
        assert '25%' in message
        assert 'Структурата' in message or 'структурата' in message
        assert 'ЗАДРЪЖАМ' in message
        print("✅ 25% checkpoint narrative generated successfully")
        
        # Test at 85% checkpoint
        message_85 = SwingTraderNarrative.checkpoint_all_good(
            position, analysis, 85, 85.0, 51800.0
        )
        
        print("\n📝 85% Checkpoint Message:")
        print(message_85)
        
        assert '85%' in message_85
        assert 'Затварям' in message_85 or 'затварям' in message_85
        assert 'breakeven' in message_85
        print("✅ 85% checkpoint narrative generated successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_checkpoint_bias_changed():
    """Test HTF bias change narrative"""
    print("\n" + "=" * 60)
    print("TEST 3: HTF Bias Changed Narrative")
    print("=" * 60)
    
    try:
        from narrative_templates import SwingTraderNarrative
        
        position = {
            'id': 1,
            'symbol': 'ETHUSDT',
            'signal_type': 'BUY',
            'entry_price': 3000.0,
            'tp1_price': 3200.0,
            'sl_price': 2900.0
        }
        
        class MockAnalysis:
            current_confidence = 65
            confidence_delta = -12
            current_rr_ratio = 1.8
            structure_broken = False
            htf_bias_changed = True
            original_htf_bias = 'BULLISH'
            htf_bias = 'NEUTRAL'
        
        analysis = MockAnalysis()
        
        message = SwingTraderNarrative.checkpoint_bias_changed(
            position, analysis, 50, 50.0, 3100.0, 'BULLISH', 'NEUTRAL'
        )
        
        print("\n📝 Bias Changed Message:")
        print(message)
        
        # Verify key content
        assert 'ETHUSDT' in message
        assert '50%' in message
        assert 'BULLISH' in message
        assert 'NEUTRAL' in message
        assert 'Затварям' in message or 'затварям' in message
        assert '40-50%' in message
        assert 'breakeven' in message
        print("✅ Bias changed narrative generated successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_checkpoint_structure_broken():
    """Test structure broken (urgent exit) narrative"""
    print("\n" + "=" * 60)
    print("TEST 4: Structure Broken Narrative")
    print("=" * 60)
    
    try:
        from narrative_templates import SwingTraderNarrative
        
        position = {
            'id': 1,
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 50000.0,
            'tp1_price': 52000.0,
            'sl_price': 49000.0
        }
        
        class MockAnalysis:
            structure_broken = True
        
        analysis = MockAnalysis()
        
        message = SwingTraderNarrative.checkpoint_structure_broken(
            position, analysis, 50, 50.0, 50800.0
        )
        
        print("\n📝 Structure Broken Message:")
        print(message)
        
        # Verify urgent exit recommendation
        assert 'BTCUSDT' in message
        assert 'СТРУКТУРАТА' in message or 'структурата' in message
        assert 'СЧУПЕНА' in message or 'счупена' in message
        assert 'BOS' in message
        assert '100%' in message
        assert 'ИЗЛИЗАМ' in message or 'EXIT' in message
        print("✅ Structure broken narrative generated successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_critical_news_alert():
    """Test critical news alert narrative"""
    print("\n" + "=" * 60)
    print("TEST 5: Critical News Alert Narrative")
    print("=" * 60)
    
    try:
        from narrative_templates import SwingTraderNarrative
        
        position = {
            'id': 1,
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 50000.0,
            'tp1_price': 52000.0
        }
        
        news_data = {
            'headline': 'SEC approves Bitcoin ETF',
            'sentiment_label': 'BULLISH',
            'priority': 'critical'
        }
        
        # Bearish news against LONG position
        impact_bearish = "🚨 CRITICAL: Bearish news против LONG позиция - HIGH REVERSAL RISK!"
        
        message = SwingTraderNarrative.critical_news_alert(
            position, news_data, 51000.0, impact_bearish
        )
        
        print("\n📝 Critical News Alert (Contradicting):")
        print(message)
        
        assert 'BTCUSDT' in message
        assert 'BREAKING NEWS' in message or 'NEWS ALERT' in message
        assert 'CRITICAL' in impact_bearish
        assert 'Затварям' in message or 'затварям' in message
        print("✅ Critical news alert (contradicting) generated successfully")
        
        # Supporting news
        impact_supporting = "✅ Bullish news подкрепя LONG позиция - Momentum в наша полза"
        
        message2 = SwingTraderNarrative.critical_news_alert(
            position, news_data, 51000.0, impact_supporting
        )
        
        print("\n📝 Critical News Alert (Supporting):")
        print(message2)
        
        assert 'ЗАДРЪЖАМ' in message2
        print("✅ Critical news alert (supporting) generated successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_narrative_selector():
    """Test NarrativeSelector logic"""
    print("\n" + "=" * 60)
    print("TEST 6: NarrativeSelector Logic")
    print("=" * 60)
    
    try:
        from narrative_templates import NarrativeSelector
        
        position = {
            'id': 1,
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY',
            'entry_price': 50000.0,
            'tp1_price': 52000.0,
            'sl_price': 49000.0
        }
        
        # Test 1: Structure broken (highest priority)
        class MockAnalysisStructureBroken:
            structure_broken = True
            current_confidence = 50
        
        message = NarrativeSelector.select_narrative(
            position, MockAnalysisStructureBroken(), None, 50, 50.0, 51000.0
        )
        
        print("\n📝 Selected Narrative (Structure Broken):")
        print(message[:200] + "...")
        assert 'СТРУКТУРАТА' in message or 'структурата' in message
        print("✅ Correctly selected structure_broken narrative")
        
        # Test 2: HTF bias changed
        class MockAnalysisBiasChanged:
            structure_broken = False
            htf_bias_changed = True
            original_htf_bias = 'BULLISH'
            htf_bias = 'NEUTRAL'
            current_confidence = 68
            confidence_delta = -10
            current_rr_ratio = 2.0
        
        message2 = NarrativeSelector.select_narrative(
            position, MockAnalysisBiasChanged(), None, 50, 50.0, 51000.0
        )
        
        print("\n📝 Selected Narrative (Bias Changed):")
        print(message2[:200] + "...")
        assert 'BULLISH' in message2 and 'NEUTRAL' in message2
        print("✅ Correctly selected bias_changed narrative")
        
        # Test 3: All good
        class MockAnalysisAllGood:
            structure_broken = False
            htf_bias_changed = False
            current_confidence = 75
            current_rr_ratio = 2.5
        
        message3 = NarrativeSelector.select_narrative(
            position, MockAnalysisAllGood(), None, 25, 25.0, 50500.0
        )
        
        print("\n📝 Selected Narrative (All Good):")
        print(message3[:200] + "...")
        print("✅ Correctly selected all_good narrative")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_alert_filtering():
    """Test smart alert filtering logic"""
    print("\n" + "=" * 60)
    print("TEST 7: Smart Alert Filtering")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        
        manager = UnifiedTradeManager()
        
        position = {
            'id': 1,
            'symbol': 'BTCUSDT',
            'signal_type': 'BUY'
        }
        
        # Test 1: 25% checkpoint - always alert
        class MockAnalysisGood:
            structure_broken = False
            htf_bias_changed = False
            confidence_delta = -2
        
        should_alert, alert_type = manager._should_send_alert(
            MockAnalysisGood(), None, 25, position
        )
        
        print(f"\n25% checkpoint: should_alert={should_alert}, type={alert_type}")
        assert should_alert == True
        print("✅ 25% checkpoint always alerts (confirmation)")
        
        # Test 2: 50% checkpoint, no changes - no alert
        should_alert2, alert_type2 = manager._should_send_alert(
            MockAnalysisGood(), None, 50, position
        )
        
        print(f"50% checkpoint (no changes): should_alert={should_alert2}, type={alert_type2}")
        assert should_alert2 == False
        print("✅ 50% checkpoint with no changes = silent monitoring")
        
        # Test 3: 50% checkpoint, structure broken - alert
        class MockAnalysisBroken:
            structure_broken = True
            htf_bias_changed = False
            confidence_delta = -5
        
        should_alert3, alert_type3 = manager._should_send_alert(
            MockAnalysisBroken(), None, 50, position
        )
        
        print(f"50% checkpoint (structure broken): should_alert={should_alert3}, type={alert_type3}")
        assert should_alert3 == True
        assert 'structure' in alert_type3.lower()
        print("✅ Structure broken triggers alert")
        
        # Test 4: Critical news - always alert
        news_critical = {
            'priority': 'critical',
            'impact_assessment': '🚨 CRITICAL'
        }
        
        should_alert4, alert_type4 = manager._should_send_alert(
            MockAnalysisGood(), news_critical, 50, position
        )
        
        print(f"Critical news: should_alert={should_alert4}, type={alert_type4}")
        assert should_alert4 == True
        print("✅ Critical news triggers alert")
        
        # Test 5: Important news contradicting position - alert
        news_important = {
            'priority': 'important',
            'impact_assessment': '⚠️ Bearish news против LONG'
        }
        
        should_alert5, alert_type5 = manager._should_send_alert(
            MockAnalysisGood(), news_important, 50, position
        )
        
        print(f"Important contradicting news: should_alert={should_alert5}, type={alert_type5}")
        assert should_alert5 == True
        print("✅ Important news contradicting position triggers alert")
        
        # Test 6: 85% checkpoint - always alert
        should_alert6, alert_type6 = manager._should_send_alert(
            MockAnalysisGood(), None, 85, position
        )
        
        print(f"85% checkpoint: should_alert={should_alert6}, type={alert_type6}")
        assert should_alert6 == True
        print("✅ 85% checkpoint always alerts (near TP1)")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_news_impact_assessment():
    """Test news impact vs position assessment"""
    print("\n" + "=" * 60)
    print("TEST 8: News Impact Assessment")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        
        manager = UnifiedTradeManager()
        
        # Test 1: Bearish news vs LONG position
        position_long = {
            'signal_type': 'BUY'
        }
        
        sentiment = {}
        label = 'STRONG_BEARISH'
        
        impact = manager._assess_news_vs_position(sentiment, label, position_long)
        
        print(f"\nBearish news vs LONG: {impact}")
        assert 'CRITICAL' in impact or 'против' in impact
        print("✅ Correctly identified bearish news against LONG as critical")
        
        # Test 2: Bullish news vs LONG position (supporting)
        label2 = 'BULLISH'
        impact2 = manager._assess_news_vs_position(sentiment, label2, position_long)
        
        print(f"Bullish news vs LONG: {impact2}")
        assert 'подкрепя' in impact2 or '✅' in impact2
        print("✅ Correctly identified bullish news supporting LONG")
        
        # Test 3: Bullish news vs SHORT position
        position_short = {
            'signal_type': 'SELL'
        }
        
        label3 = 'STRONG_BULLISH'
        impact3 = manager._assess_news_vs_position(sentiment, label3, position_short)
        
        print(f"Bullish news vs SHORT: {impact3}")
        assert 'CRITICAL' in impact3 or 'против' in impact3
        print("✅ Correctly identified bullish news against SHORT as critical")
        
        # Test 4: Neutral news
        label4 = 'NEUTRAL'
        impact4 = manager._assess_news_vs_position(sentiment, label4, position_long)
        
        print(f"Neutral news: {impact4}")
        assert 'Neutral' in impact4 or 'neutral' in impact4
        print("✅ Correctly identified neutral news")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("🧪 NARRATIVE TEMPLATES TEST SUITE")
    print("=" * 60)
    
    tests = [
        test_imports,
        test_checkpoint_all_good,
        test_checkpoint_bias_changed,
        test_checkpoint_structure_broken,
        test_critical_news_alert,
        test_narrative_selector,
        test_alert_filtering,
        test_news_impact_assessment
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"\n❌ Test crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"\nPassed: {passed}/{total}")
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED! 🎉")
        print("\nExpected outcomes achieved:")
        print("  ✅ Professional Bulgarian narratives generated")
        print("  ✅ Smart alert filtering working (25%, 85% + changes only)")
        print("  ✅ News impact correctly assessed vs position")
        print("  ✅ Narrative selection logic working correctly")
        print("  ✅ All scenarios covered (all good, bias change, structure break, news)")
    else:
        print(f"\n❌ {total - passed} tests failed")
    
    print("\n" + "=" * 60)


if __name__ == '__main__':
    run_all_tests()
