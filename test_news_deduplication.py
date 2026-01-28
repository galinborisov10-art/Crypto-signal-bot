"""
Test script for news deduplication in UnifiedTradeManager

Tests:
- News deduplication per symbol
- 1-hour cooldown enforcement
- Clear signal identification in alerts
- Bulgarian narrative generation
- No raw headlines in checkpoint alerts
"""

import sys
import asyncio
from datetime import datetime, timedelta
sys.path.insert(0, '.')

def test_deduplication_init():
    """Test that deduplication tracking is initialized"""
    print("=" * 60)
    print("TEST 1: Deduplication Initialization")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        manager = UnifiedTradeManager()
        
        # Check deduplication attributes exist
        assert hasattr(manager, '_sent_news_alerts'), "Missing _sent_news_alerts attribute"
        assert hasattr(manager, '_news_cooldown'), "Missing _news_cooldown attribute"
        
        # Check initial state
        assert isinstance(manager._sent_news_alerts, dict), "_sent_news_alerts should be a dict"
        assert manager._news_cooldown == 3600, "Cooldown should be 3600 seconds (1 hour)"
        
        print("✅ Deduplication tracking initialized")
        print(f"   → _sent_news_alerts: {type(manager._sent_news_alerts)}")
        print(f"   → _news_cooldown: {manager._news_cooldown}s")
        
        return True
        
    except Exception as e:
        print(f"❌ Initialization test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_deduplication_logic():
    """Test that news deduplication actually works"""
    print("\n" + "=" * 60)
    print("TEST 2: Deduplication Logic")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        
        # Create manager instance
        manager = UnifiedTradeManager()
        
        # Mock fundamental helper to return test data
        class MockFundamentals:
            def is_enabled(self):
                return True
            
            def get_fundamental_data(self, symbol):
                return {
                    'sentiment': {
                        'label': 'BULLISH',
                        'score': 0.8,
                        'top_news': [
                            {'title': 'Test headline about Bitcoin'}
                        ]
                    }
                }
        
        manager.fundamentals = MockFundamentals()
        
        # First call - should return news data
        print("\n1. First news check (should return data):")
        news1 = await manager._check_news('BTCUSDT')
        assert news1 is not None, "First call should return news data"
        print(f"✅ News returned: {news1}")
        
        # Verify news data structure (NO raw headlines)
        assert 'label' in news1, "News should contain sentiment label"
        assert 'impact' in news1, "News should contain impact level"
        assert 'headline' not in news1, "News should NOT contain raw headline"
        assert 'top_news' not in news1, "News should NOT contain top_news list"
        print("✅ News data structure is correct (no raw headlines)")
        
        # Second call immediately - should be blocked by deduplication
        print("\n2. Second news check (should be blocked):")
        news2 = await manager._check_news('BTCUSDT')
        assert news2 is None, "Second call should be blocked by deduplication"
        print("✅ Duplicate news blocked (cooldown active)")
        
        # Third call for different symbol - should succeed
        print("\n3. News check for different symbol (should succeed):")
        news3 = await manager._check_news('ETHUSDT')
        assert news3 is not None, "Different symbol should get news"
        print(f"✅ Different symbol got news: {news3}")
        
        # Simulate time passing by manually clearing cooldown
        print("\n4. Simulate cooldown expiry:")
        manager._sent_news_alerts['BTCUSDT'] = {
            'Test headline about Bitcoin': datetime.now() - timedelta(hours=2)
        }
        news4 = await manager._check_news('BTCUSDT')
        assert news4 is not None, "After cooldown expiry, news should be sent again"
        print("✅ After cooldown expiry, news sent again")
        
        return True
        
    except Exception as e:
        print(f"❌ Deduplication logic test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_signal_identification():
    """Test that alerts include clear signal identification"""
    print("\n" + "=" * 60)
    print("TEST 3: Signal Identification in Alerts")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        manager = UnifiedTradeManager()
        
        # Mock position with all required fields
        position = {
            'symbol': 'XRPUSDT',
            'timeframe': '4h',
            'entry_price': 2.0236,
            'signal_type': 'SELL',
            'timestamp': '2026-01-25 14:30:15',
            'tp1_price': 1.8500,
            'sl_price': 2.1500
        }
        
        # Mock analysis
        class MockAnalysis:
            def __init__(self):
                self.original_confidence = 85.0
                self.current_confidence = 82.1
                self.confidence_delta = -2.9
                self.current_price = 1.8845
                self.reasoning = [
                    "✅ ICT bias maintains SELL",
                    "✅ Structure break confirmed",
                    "✅ Displacement strong"
                ]
        
        analysis = MockAnalysis()
        
        # Generate alert
        alert = manager._format_bulgarian_alert(
            position=position,
            analysis=analysis,
            news=None,
            checkpoint=80,
            progress=78.3
        )
        
        print("\nGenerated Alert:")
        print("-" * 60)
        print(alert)
        print("-" * 60)
        
        # Verify signal identification is present
        assert 'SIGNAL DETAILS:' in alert, "Alert should have SIGNAL DETAILS section"
        assert 'Symbol: XRPUSDT' in alert, "Alert should show symbol"
        assert 'Timeframe: 4h' in alert, "Alert should show timeframe"
        assert 'Entry: $2.0236' in alert, "Alert should show entry price"
        assert 'Position Type: SELL' in alert, "Alert should show position type"
        assert 'Opened: 2026-01-25 14:30' in alert, "Alert should show timestamp"
        
        # Verify current status section
        assert 'CURRENT STATUS:' in alert, "Alert should have CURRENT STATUS section"
        assert 'Progress to TP:' in alert, "Alert should show progress"
        assert 'Current Price:' in alert, "Alert should show current price"
        assert 'Current Profit:' in alert, "Alert should show profit"
        
        # Verify ICT re-analysis section
        assert 'ICT RE-ANALYSIS:' in alert, "Alert should have ICT RE-ANALYSIS section"
        assert 'Recommendation:' in alert, "Alert should show recommendation"
        
        print("\n✅ All signal identification fields present")
        print("✅ Alert structure is clear and complete")
        
        return True
        
    except Exception as e:
        print(f"❌ Signal identification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_bulgarian_narrative():
    """Test Bulgarian narrative generation for different scenarios"""
    print("\n" + "=" * 60)
    print("TEST 4: Bulgarian Narrative Generation")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        manager = UnifiedTradeManager()
        
        # Test Case 1: Contradicting news (LONG + BEARISH)
        print("\n1. Contradicting news (LONG position + BEARISH sentiment):")
        print("-" * 60)
        narrative1 = manager._format_news_narrative(
            sentiment_label='BEARISH',
            impact='HIGH',
            position_type='BUY'
        )
        print(narrative1)
        assert 'Противоречи на LONG' in narrative1, "Should mention contradiction"
        assert 'Затварям 20-30%' in narrative1, "Should suggest risk reduction"
        assert 'BREAKING NEWS' not in narrative1, "Should NOT have news header"
        assert 'HEADLINE' not in narrative1, "Should NOT have headline text"
        print("✅ Contradicting narrative correct")
        
        # Test Case 2: Contradicting news (SHORT + BULLISH)
        print("\n2. Contradicting news (SHORT position + BULLISH sentiment):")
        print("-" * 60)
        narrative2 = manager._format_news_narrative(
            sentiment_label='BULLISH',
            impact='HIGH',
            position_type='SELL'
        )
        print(narrative2)
        assert 'Противоречи на SHORT' in narrative2, "Should mention contradiction"
        assert 'Затварям 20-30%' in narrative2, "Should suggest risk reduction"
        print("✅ Contradicting narrative correct")
        
        # Test Case 3: Neutral news
        print("\n3. Neutral or mixed news:")
        print("-" * 60)
        narrative3 = manager._format_news_narrative(
            sentiment_label='NEUTRAL',
            impact='MEDIUM',
            position_type='BUY'
        )
        print(narrative3)
        assert 'неутрален или смесен' in narrative3, "Should mention neutral"
        assert 'Затварям малка част (10-15%)' in narrative3, "Should suggest small reduction"
        print("✅ Neutral narrative correct")
        
        # Test Case 4: Supportive news (LONG + BULLISH)
        print("\n4. Supportive news (LONG position + BULLISH sentiment):")
        print("-" * 60)
        narrative4 = manager._format_news_narrative(
            sentiment_label='BULLISH',
            impact='HIGH',
            position_type='BUY'
        )
        print(narrative4)
        assert 'supports текущата позиция' in narrative4, "Should mention support"
        assert 'Продължавам по план' in narrative4, "Should suggest continuation"
        print("✅ Supportive narrative correct")
        
        # Verify all narratives have Bulgarian trader perspective
        for i, narrative in enumerate([narrative1, narrative2, narrative3, narrative4], 1):
            assert '💡 Моята позиция като swing trader:' in narrative, \
                f"Narrative {i} should have Bulgarian trader perspective"
        
        print("\n✅ All Bulgarian narratives are correct")
        print("✅ No raw headlines in any narrative")
        
        return True
        
    except Exception as e:
        print(f"❌ Bulgarian narrative test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_profit_calculation():
    """Test profit percentage calculation"""
    print("\n" + "=" * 60)
    print("TEST 5: Profit Calculation")
    print("=" * 60)
    
    try:
        from unified_trade_manager import UnifiedTradeManager
        manager = UnifiedTradeManager()
        
        # Test LONG position profit
        long_position = {
            'entry_price': 40000.0,
            'signal_type': 'BUY'
        }
        
        profit_at_41k = manager._calculate_profit_pct(long_position, 41000.0)
        profit_at_42k = manager._calculate_profit_pct(long_position, 42000.0)
        profit_at_38k = manager._calculate_profit_pct(long_position, 38000.0)
        
        print(f"\nLONG position (entry $40,000):")
        print(f"  Price $41,000 → Profit: {profit_at_41k:+.2f}% (expected: +2.50%)")
        print(f"  Price $42,000 → Profit: {profit_at_42k:+.2f}% (expected: +5.00%)")
        print(f"  Price $38,000 → Profit: {profit_at_38k:+.2f}% (expected: -5.00%)")
        
        assert abs(profit_at_41k - 2.5) < 0.01, "LONG profit at +2.5% incorrect"
        assert abs(profit_at_42k - 5.0) < 0.01, "LONG profit at +5% incorrect"
        assert abs(profit_at_38k - (-5.0)) < 0.01, "LONG loss at -5% incorrect"
        print("✅ LONG position profit calculation correct")
        
        # Test SHORT position profit
        short_position = {
            'entry_price': 44000.0,
            'signal_type': 'SELL'
        }
        
        profit_at_43k = manager._calculate_profit_pct(short_position, 43000.0)
        profit_at_42k = manager._calculate_profit_pct(short_position, 42000.0)
        profit_at_45k = manager._calculate_profit_pct(short_position, 45000.0)
        
        print(f"\nSHORT position (entry $44,000):")
        print(f"  Price $43,000 → Profit: {profit_at_43k:+.2f}% (expected: +2.27%)")
        print(f"  Price $42,000 → Profit: {profit_at_42k:+.2f}% (expected: +4.55%)")
        print(f"  Price $45,000 → Profit: {profit_at_45k:+.2f}% (expected: -2.27%)")
        
        assert abs(profit_at_43k - 2.27) < 0.01, "SHORT profit at +2.27% incorrect"
        assert abs(profit_at_42k - 4.55) < 0.01, "SHORT profit at +4.55% incorrect"
        assert abs(profit_at_45k - (-2.27)) < 0.01, "SHORT loss at -2.27% incorrect"
        print("✅ SHORT position profit calculation correct")
        
        return True
        
    except Exception as e:
        print(f"❌ Profit calculation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """Run all tests and report results"""
    print("\n" + "=" * 60)
    print("NEWS DEDUPLICATION TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Deduplication Initialization", test_deduplication_init),
        ("Deduplication Logic", test_deduplication_logic),
        ("Signal Identification", test_signal_identification),
        ("Bulgarian Narrative", test_bulgarian_narrative),
        ("Profit Calculation", test_profit_calculation),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            # Handle async tests
            if asyncio.iscoroutinefunction(test_func):
                result = asyncio.run(test_func())
            else:
                result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ Test '{name}' crashed: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print("=" * 60)
    print(f"Results: {passed}/{total} tests passed")
    print("=" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
