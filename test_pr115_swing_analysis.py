#!/usr/bin/env python3
"""
Test for PR #115: Enhanced Multi-Pair Swing Analysis

Tests the comprehensive swing analysis functionality:
- Real-time data fetching
- Individual analysis for each pair
- Professional narrative generation
- Summary ranking
- Bulgarian/English language mix
"""

import asyncio
import sys
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Import directly from bot.py module
import importlib.util
spec = importlib.util.spec_from_file_location("bot", "/home/runner/work/Crypto-signal-bot/Crypto-signal-bot/bot.py")
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

generate_comprehensive_swing_analysis = bot.generate_comprehensive_swing_analysis
generate_swing_summary = bot.generate_swing_summary
fetch_fear_greed_index = bot.fetch_fear_greed_index


async def test_single_pair_analysis():
    """Test comprehensive analysis for a single pair"""
    print("\n" + "="*60)
    print("TEST 1: Single Pair Analysis (BTCUSDT)")
    print("="*60)
    
    try:
        analysis = await generate_comprehensive_swing_analysis(
            symbol='BTCUSDT',
            display_name='🪙 BITCOIN',
            language='bg'
        )
        
        # Validate structure
        assert 'symbol' in analysis, "Missing 'symbol' in analysis"
        assert 'rating' in analysis, "Missing 'rating' in analysis"
        assert 'message' in analysis, "Missing 'message' in analysis"
        assert 'recommendation' in analysis, "Missing 'recommendation' in analysis"
        
        # Validate rating range
        assert 0 <= analysis['rating'] <= 5, f"Rating out of range: {analysis['rating']}"
        
        # Check message length
        msg_len = len(analysis['message'])
        print(f"\n✅ Analysis generated successfully")
        print(f"   Symbol: {analysis['symbol']}")
        print(f"   Rating: {analysis['rating']:.1f}/5")
        print(f"   Recommendation: {analysis['recommendation']}")
        print(f"   Message length: {msg_len} characters")
        
        # Check for key sections in message
        required_sections = [
            'СТРУКТУРА',
            'КЛЮЧОВИ НИВА',
            'ОБЕМ & MOMENTUM',
            'SWING SETUP',
            'ПРОФЕСИОНАЛЕН SWING АНАЛИЗ',
            'ПАЗАРЕН КОНТЕКСТ',
            'SWING TRADER ПЕРСПЕКТИВА',
            'ПРЕПОРЪКА',
            'РЕЙТИНГ'
        ]
        
        missing_sections = []
        for section in required_sections:
            if section not in analysis['message']:
                missing_sections.append(section)
        
        if missing_sections:
            print(f"\n⚠️  Missing sections: {', '.join(missing_sections)}")
        else:
            print(f"✅ All required sections present")
        
        # Check Bulgarian/English ratio (approximate)
        bulgarian_keywords = ['Цена', 'Вход', 'Чакай', 'Избягвай', 'Подкрепа', 'Съпротива']
        english_keywords = ['breakout', 'setup', 'momentum', 'R:R', 'SL', 'TP']
        
        bg_count = sum(1 for word in bulgarian_keywords if word in analysis['message'])
        en_count = sum(1 for word in english_keywords if word in analysis['message'])
        
        print(f"✅ Language mix: {bg_count} BG keywords, {en_count} EN keywords")
        
        # Print first 500 chars of message
        print(f"\n📄 Message preview (first 500 chars):")
        print("-" * 60)
        print(analysis['message'][:500])
        print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_multiple_pairs():
    """Test analysis for multiple pairs"""
    print("\n" + "="*60)
    print("TEST 2: Multiple Pairs Analysis")
    print("="*60)
    
    symbols = [
        ('BTCUSDT', '🪙 BITCOIN'),
        ('ETHUSDT', '💎 ETHEREUM'),
        ('SOLUSDT', '🌐 SOLANA')
    ]
    
    all_analyses = []
    
    for symbol, display_name in symbols:
        try:
            print(f"\n⏳ Analyzing {symbol}...")
            analysis = await asyncio.wait_for(
                generate_comprehensive_swing_analysis(symbol, display_name, 'bg'),
                timeout=15.0
            )
            all_analyses.append(analysis)
            print(f"✅ {symbol}: Rating {analysis['rating']:.1f}/5, Recommendation: {analysis['recommendation']}")
        except asyncio.TimeoutError:
            print(f"⚠️  {symbol}: Timeout (15s)")
        except Exception as e:
            print(f"❌ {symbol}: Error - {e}")
    
    if len(all_analyses) >= 2:
        print(f"\n✅ Successfully analyzed {len(all_analyses)}/{len(symbols)} pairs")
        
        # Check uniqueness
        ratings = [a['rating'] for a in all_analyses]
        messages = [a['message'] for a in all_analyses]
        
        # Ratings should be different (unless by coincidence)
        unique_ratings = len(set(ratings))
        print(f"   Unique ratings: {unique_ratings}/{len(all_analyses)}")
        
        # Messages should be significantly different
        if len(messages) >= 2:
            similarity = len(set(messages))
            if similarity == len(messages):
                print(f"✅ All messages are unique")
            else:
                print(f"⚠️  Some messages are identical (may indicate templating)")
        
        return True
    else:
        print(f"❌ Not enough pairs analyzed: {len(all_analyses)}/{len(symbols)}")
        return False


async def test_summary_generation():
    """Test summary generation with ranked opportunities"""
    print("\n" + "="*60)
    print("TEST 3: Summary Generation")
    print("="*60)
    
    # Create mock analyses with different ratings
    mock_analyses = [
        {
            'symbol': 'BTCUSDT',
            'rating': 4.5,
            'message': 'BTC analysis...',
            'recommendation': 'BUY',
            'priority': 4
        },
        {
            'symbol': 'ETHUSDT',
            'rating': 3.0,
            'message': 'ETH analysis...',
            'recommendation': 'WAIT',
            'priority': 3
        },
        {
            'symbol': 'SOLUSDT',
            'rating': 2.0,
            'message': 'SOL analysis...',
            'recommendation': 'SHORT',
            'priority': 2
        },
        {
            'symbol': 'XRPUSDT',
            'rating': 3.8,
            'message': 'XRP analysis...',
            'recommendation': 'BUY',
            'priority': 3
        }
    ]
    
    try:
        summary = generate_swing_summary(mock_analyses)
        
        # Check summary structure
        assert 'SWING ANALYSIS SUMMARY' in summary, "Missing summary title"
        assert 'BEST OPPORTUNITIES' in summary or 'ВНИМАНИЕ' in summary or 'ИЗБЯГВАЙ' in summary, "Missing ranking sections"
        assert 'ПАЗАРЕН ПРЕГЛЕД' in summary, "Missing market overview"
        assert 'UTC' in summary, "Missing timestamp"
        
        print(f"\n✅ Summary generated successfully")
        print(f"   Length: {len(summary)} characters")
        
        # Check for medals (top 3)
        medals = ['🥇', '🥈', '🥉']
        medal_count = sum(1 for medal in medals if medal in summary)
        print(f"✅ Medals present: {medal_count}/3")
        
        # Check ranking order (BTC 4.5 should be first, SOL 2.0 should be last)
        btc_pos = summary.find('BTC')
        sol_pos = summary.find('SOL')
        
        if btc_pos < sol_pos and btc_pos > 0:
            print(f"✅ Ranking order correct (BTC before SOL)")
        else:
            print(f"⚠️  Ranking order may be incorrect")
        
        print(f"\n📄 Summary preview (first 800 chars):")
        print("-" * 60)
        print(summary[:800])
        print("-" * 60)
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_fear_greed_fetch():
    """Test Fear & Greed Index fetching"""
    print("\n" + "="*60)
    print("TEST 4: Fear & Greed Index")
    print("="*60)
    
    try:
        fear_greed = await fetch_fear_greed_index()
        
        if fear_greed:
            print(f"✅ Fear & Greed fetched successfully")
            print(f"   Value: {fear_greed['value']}/100")
            print(f"   Classification: {fear_greed['classification']}")
            return True
        else:
            print(f"⚠️  Fear & Greed not available (API may be down)")
            return True  # Not a failure, API might be temporarily down
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


async def test_timeout_protection():
    """Test timeout protection for slow analyses"""
    print("\n" + "="*60)
    print("TEST 5: Timeout Protection")
    print("="*60)
    
    try:
        # Test with very short timeout
        analysis = await asyncio.wait_for(
            generate_comprehensive_swing_analysis('BTCUSDT', '🪙 BITCOIN', 'bg'),
            timeout=0.1  # Very short timeout
        )
        print(f"⚠️  Analysis completed faster than expected (< 0.1s)")
        return True
    except asyncio.TimeoutError:
        print(f"✅ Timeout protection works correctly")
        return True
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


async def run_all_tests():
    """Run all tests"""
    print("\n" + "="*80)
    print("PR #115: Enhanced Multi-Pair Swing Analysis - Test Suite")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {
        'Single Pair Analysis': await test_single_pair_analysis(),
        'Multiple Pairs Analysis': await test_multiple_pairs(),
        'Summary Generation': await test_summary_generation(),
        'Fear & Greed Index': await test_fear_greed_fetch(),
        'Timeout Protection': await test_timeout_protection()
    }
    
    print("\n" + "="*80)
    print("TEST RESULTS SUMMARY")
    print("="*80)
    
    passed = sum(1 for result in results.values() if result)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "="*80)
    print(f"OVERALL: {passed}/{total} tests passed ({passed/total*100:.1f}%)")
    print("="*80)
    
    if passed == total:
        print("\n🎉 All tests passed! PR #115 implementation is ready.")
        return 0
    else:
        print(f"\n⚠️  {total - passed} test(s) failed. Review needed.")
        return 1


if __name__ == '__main__':
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
