#!/usr/bin/env python3
"""
Integration test: Verify signal_cache works with realistic bot flow
Simulates how bot.py would use signal_cache in production
"""

import os
import sys
import tempfile
from datetime import datetime

# Import as bot.py would
from signal_cache import is_signal_duplicate, validate_cache, load_sent_signals

def test_realistic_signal_flow():
    """Test a realistic signal processing flow"""
    print("=" * 60)
    print("🔬 INTEGRATION TEST: Realistic Signal Flow")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        print("\n1️⃣ Bot Startup - Validate Cache")
        is_valid, msg = validate_cache(tmpdir)
        assert is_valid, f"Cache validation failed: {msg}"
        print(f"   ✅ {msg}")
        
        print("\n2️⃣ Process First Signal")
        is_dup, msg = is_signal_duplicate(
            symbol="BTCUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=50000.0,
            confidence=85,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        assert not is_dup, "First signal should NOT be duplicate"
        print(f"   ✅ First signal allowed: {msg}")
        
        print("\n3️⃣ Try Duplicate Signal (should be blocked)")
        is_dup, msg = is_signal_duplicate(
            symbol="BTCUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=50000.0,
            confidence=85,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        assert is_dup, "Duplicate signal should be blocked"
        print(f"   ✅ Duplicate blocked: {msg}")
        
        print("\n4️⃣ Different Entry Price (should be allowed)")
        is_dup, msg = is_signal_duplicate(
            symbol="BTCUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=51000.0,  # Different entry
            confidence=85,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        assert not is_dup, "Different entry price should be allowed"
        print(f"   ✅ Different entry allowed: {msg}")
        
        print("\n5️⃣ Different Symbol (should be allowed)")
        is_dup, msg = is_signal_duplicate(
            symbol="ETHUSDT",  # Different symbol
            signal_type="BUY",
            timeframe="4h",
            entry_price=3500.0,
            confidence=88,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        assert not is_dup, "Different symbol should be allowed"
        print(f"   ✅ Different symbol allowed: {msg}")
        
        print("\n6️⃣ Check Cache Contents")
        cache = load_sent_signals(tmpdir)
        expected_count = 3  # BTCUSDT@50k, BTCUSDT@51k, ETHUSDT@3.5k
        assert len(cache) == expected_count, f"Cache should have {expected_count} entries, got {len(cache)}"
        print(f"   ✅ Cache has correct number of entries: {len(cache)}")
        
        print("\n7️⃣ Verify Cache Keys")
        keys = sorted(cache.keys())
        print(f"   Cache keys:")
        for key in keys:
            entry = cache[key]
            print(f"     - {key}")
            print(f"       Timestamp: {entry['timestamp']}")
            print(f"       Entry Price: {entry['entry_price']}")
            print(f"       Confidence: {entry['confidence']}")
        
        # Verify key format includes entry price
        assert "BTCUSDT_BUY_4h_50000.0" in keys, "BTCUSDT@50k should be in cache"
        assert "BTCUSDT_BUY_4h_51000.0" in keys, "BTCUSDT@51k should be in cache"
        assert "ETHUSDT_BUY_4h_3500.0" in keys, "ETHUSDT@3.5k should be in cache"
        
        print("\n8️⃣ Bot Restart - Verify Persistence")
        # Simulate bot restart by loading cache again
        cache_after_restart = load_sent_signals(tmpdir)
        assert len(cache_after_restart) == expected_count, "Cache should persist after restart"
        print(f"   ✅ Cache persisted after restart: {len(cache_after_restart)} entries")
        
        print("\n9️⃣ Verify Duplicate Still Blocked After Restart")
        is_dup, msg = is_signal_duplicate(
            symbol="BTCUSDT",
            signal_type="BUY",
            timeframe="4h",
            entry_price=50000.0,
            confidence=85,
            cooldown_minutes=60,
            base_path=tmpdir
        )
        assert is_dup, "Duplicate should still be blocked after restart"
        print(f"   ✅ Duplicate still blocked: {msg}")
        
        print("\n" + "=" * 60)
        print("✅ INTEGRATION TEST PASSED")
        print("=" * 60)
        print("\n📊 Summary:")
        print(f"   • Cache validation: Working")
        print(f"   • Duplicate detection: Working")
        print(f"   • Entry price distinction: Working")
        print(f"   • Cache persistence: Working")
        print(f"   • Bot restart handling: Working")
        print("\n🎉 All integration tests passed!")
        
        return True


def test_production_scenario():
    """Test a realistic production scenario with multiple signals"""
    print("\n" + "=" * 60)
    print("🔬 PRODUCTION SCENARIO TEST")
    print("=" * 60)
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Simulate a busy day of trading
        signals = [
            ("BTCUSDT", "BUY", "4h", 50000.0, 85),
            ("ETHUSDT", "BUY", "1d", 3500.0, 88),
            ("XRPUSDT", "BUY", "4h", 2.0357, 82),
            ("BTCUSDT", "BUY", "4h", 50000.0, 85),  # Duplicate
            ("XRPUSDT", "BUY", "4h", 2.1500, 80),  # Different entry
            ("ADAUSDT", "BUY", "1d", 0.4407, 75),
            ("ETHUSDT", "BUY", "1d", 3500.0, 88),  # Duplicate
            ("XRPUSDT", "BUY", "4h", 2.0357, 82),  # Duplicate
        ]
        
        allowed = 0
        blocked = 0
        
        print("\n📤 Processing signals:")
        for i, (symbol, sig_type, tf, entry, conf) in enumerate(signals, 1):
            is_dup, msg = is_signal_duplicate(
                symbol=symbol,
                signal_type=sig_type,
                timeframe=tf,
                entry_price=entry,
                confidence=conf,
                cooldown_minutes=60,
                base_path=tmpdir
            )
            
            status = "🔴 BLOCKED" if is_dup else "✅ ALLOWED"
            print(f"   {i}. {symbol} {sig_type} {tf} @ ${entry:,.2f} - {status}")
            
            if is_dup:
                blocked += 1
            else:
                allowed += 1
        
        print(f"\n📊 Results:")
        print(f"   ✅ Allowed: {allowed} signals")
        print(f"   🔴 Blocked: {blocked} duplicates")
        print(f"   📈 Duplicate rate: {blocked/(allowed+blocked)*100:.1f}%")
        
        # Expected: 5 allowed, 3 blocked
        assert allowed == 5, f"Should allow 5 signals, allowed {allowed}"
        assert blocked == 3, f"Should block 3 duplicates, blocked {blocked}"
        
        print("\n✅ Production scenario test PASSED")
        
        return True


if __name__ == "__main__":
    try:
        test_realistic_signal_flow()
        test_production_scenario()
        
        print("\n" + "=" * 60)
        print("🎊 ALL INTEGRATION TESTS PASSED!")
        print("=" * 60)
        print("\n✅ Signal cache is ready for production!")
        
        sys.exit(0)
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
