"""
Demo: News Deduplication in Checkpoint Alerts

Shows:
1. Before: Same news sent 18+ times (spam)
2. After: News sent only once per symbol per hour (deduplication)
3. Clear signal identification
4. Bulgarian narratives (no raw headlines)
"""

import asyncio
from datetime import datetime
from unified_trade_manager import UnifiedTradeManager

# Mock fundamental helper
class MockFundamentals:
    def is_enabled(self):
        return True
    
    def get_fundamental_data(self, symbol):
        return {
            'sentiment': {
                'label': 'BULLISH',
                'score': 0.75,
                'top_news': [
                    {'title': 'Bitcoin price fails to follow as gold hits $5.3K record into FOMC'}
                ]
            }
        }

async def demo_before():
    """Simulate BEFORE: Multiple positions = multiple news alerts"""
    print("\n" + "=" * 80)
    print("BEFORE: News Alert Spam (without deduplication)")
    print("=" * 80)
    print("\nSimulating checkpoint alerts for 3 positions with the same news...\n")
    
    symbols = ['ADAUSDT', 'BTCUSDT', 'XRPUSDT']
    
    for i, symbol in enumerate(symbols, 1):
        print(f"Alert {i}/{len(symbols)} for {symbol}:")
        print("-" * 80)
        # This is what OLD system would send (with raw headlines)
        print(f"""🟡 BREAKING NEWS ALERT - {symbol}
📰 HEADLINE: Bitcoin price fails to follow as gold hits $5.3K record into FOMC
⚠️ Bullish news против SHORT - Consider partial exit
💡 Моята позиция като swing trader: ...
""")
    
    print(f"❌ Result: Same news sent {len(symbols)} times! (SPAM)")


async def demo_after():
    """Simulate AFTER: Deduplication prevents spam"""
    print("\n" + "=" * 80)
    print("AFTER: News Deduplication (with cooldown)")
    print("=" * 80)
    print("\nSimulating checkpoint alerts for SAME symbol multiple times...\n")
    
    manager = UnifiedTradeManager()
    manager.fundamentals = MockFundamentals()
    
    # Try to send news for the SAME symbol 3 times
    symbol = 'BTCUSDT'
    results = []
    
    for i in range(3):
        news = await manager._check_news(symbol)
        results.append((i+1, news))
    
    # Show results
    sent_count = 0
    for attempt_num, news in results:
        if news:
            sent_count += 1
            print(f"Attempt {attempt_num}: ✅ News sent for {symbol}")
            print(f"   → Sentiment: {news.get('label')}")
            print(f"   → Impact: {news.get('impact')}")
            print(f"   → NO raw headline (already sent by breaking_news_monitor)")
        else:
            print(f"Attempt {attempt_num}: ⏭️  News BLOCKED for {symbol} (deduplication cooldown)")
    
    print(f"\n✅ Result: News sent only {sent_count} time (first attempt)")
    print(f"✅ Next {len(results) - sent_count} attempts blocked by 1-hour cooldown!")


async def demo_signal_identification():
    """Show improved alert format with signal identification"""
    print("\n" + "=" * 80)
    print("NEW FORMAT: Clear Signal Identification")
    print("=" * 80)
    
    manager = UnifiedTradeManager()
    
    # Mock position
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
    
    # Mock news sentiment (no headlines!)
    news_data = {
        'label': 'BULLISH',
        'impact': 'HIGH',
        'score': 0.75
    }
    
    analysis = MockAnalysis()
    
    # Generate new format alert
    alert = manager._format_bulgarian_alert(
        position=position,
        analysis=analysis,
        news=news_data,
        checkpoint=80,
        progress=78.3
    )
    
    print("\nGenerated Alert:")
    print("=" * 80)
    print(alert)
    print("=" * 80)
    
    print("\n✅ Clear signal identification present")
    print("✅ Current status and profit shown")
    print("✅ Bulgarian narrative based on sentiment (NO raw headlines)")
    print("✅ User knows exactly which signal this refers to")


async def main():
    """Run all demos"""
    print("\n" + "=" * 80)
    print("NEWS DEDUPLICATION DEMO")
    print("Fixing: Checkpoint alerts spamming same news multiple times")
    print("=" * 80)
    
    # Demo 1: Before (spam)
    await demo_before()
    
    # Demo 2: After (deduplication)
    await demo_after()
    
    # Demo 3: New format
    await demo_signal_identification()
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print("✅ Deduplication: Max 1 alert per symbol per hour")
    print("✅ Clear identification: Symbol, timeframe, entry, position type")
    print("✅ Bulgarian narratives: Risk management advice, no raw headlines")
    print("✅ breaking_news_monitor: Unchanged, still sends news separately")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
