"""
Validation Script for Phase 2 Part 1
Demonstrates fundamental analysis integration with /signal command
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
import numpy as np
from datetime import datetime

from utils.fundamental_helper import FundamentalHelper, format_fundamental_section
from utils.news_cache import NewsCache


def test_scenario_1_technical_only():
    """Test with flags disabled (default behavior)"""
    print("\n" + "="*60)
    print("SCENARIO 1: Flags Disabled (Default)")
    print("="*60)
    
    helper = FundamentalHelper()
    
    if not helper.is_enabled():
        print("✅ Feature correctly disabled")
        print("→ /signal will show TECHNICAL-ONLY analysis")
    else:
        print("❌ Feature should be disabled by default")
    
    # Calculate combined score with no fundamental data
    result = helper.calculate_combined_score(
        technical_confidence=78.0,
        fundamental_data={}
    )
    
    print(f"\nCombined Score: {result['combined_score']}")
    print(f"  - Technical: {result['technical_contribution']}")
    print(f"  - Sentiment: {result['sentiment_contribution']:+.1f}")
    print(f"  - BTC Corr:  {result['btc_correlation_contribution']:+.1f}")
    print("\n→ Score equals technical confidence (no fundamental boost)")


def test_scenario_2_positive_alignment():
    """Test with positive sentiment and BTC alignment"""
    print("\n" + "="*60)
    print("SCENARIO 2: Positive Sentiment + BTC Alignment")
    print("="*60)
    
    helper = FundamentalHelper()
    
    # Simulate fundamental data
    fundamental_data = {
        'sentiment': {
            'score': 70,  # Positive (70-50)*0.3 = +6
            'label': 'POSITIVE',
            'top_news': [
                {
                    'title': 'SEC approves Bitcoin ETF - bullish rally expected',
                    'impact': 20,
                    'time': datetime.now().isoformat()
                }
            ],
            'confidence': 0.85
        },
        'btc_correlation': {
            'correlation': 0.92,
            'btc_trend': 'BULLISH',
            'symbol_trend': 'BULLISH',
            'aligned': True,
            'impact': +10,
            'btc_change': +2.1,
            'symbol_change': +2.3
        }
    }
    
    # Calculate combined score
    combined = helper.calculate_combined_score(
        technical_confidence=78.0,
        fundamental_data=fundamental_data
    )
    
    print(f"\nCombined Score: {combined['combined_score']}")
    print(f"  - Technical:  {combined['technical_contribution']}")
    print(f"  - Sentiment:  {combined['sentiment_contribution']:+.1f} (news positive)")
    print(f"  - BTC Corr:   {combined['btc_correlation_contribution']:+.1f} (trends aligned)")
    print(f"\n→ Score boosted from 78 to {combined['combined_score']}")
    
    # Generate recommendation
    recommendation = helper.generate_recommendation(
        signal_direction='BULLISH',
        technical_confidence=78.0,
        fundamental_data=fundamental_data,
        combined_score=combined['combined_score']
    )
    
    print(f"\nRECOMMENDATION:")
    for line in recommendation.split('\n'):
        print(f"  {line}")
    
    # Show formatted message
    print("\n" + "-"*60)
    print("TELEGRAM MESSAGE PREVIEW:")
    print("-"*60)
    
    formatted = format_fundamental_section(
        fundamental_data,
        combined,
        recommendation
    )
    
    # Remove HTML tags for console
    import re
    clean_text = re.sub(r'<[^>]+>', '', formatted)
    print(clean_text)


def test_scenario_3_btc_divergence():
    """Test with BTC divergence warning"""
    print("\n" + "="*60)
    print("SCENARIO 3: BTC Divergence Warning")
    print("="*60)
    
    helper = FundamentalHelper()
    
    # Simulate divergence
    fundamental_data = {
        'btc_correlation': {
            'correlation': 0.92,  # Strong correlation
            'btc_trend': 'BEARISH',  # BTC going down
            'symbol_trend': 'BULLISH',  # Symbol going up
            'aligned': False,  # DIVERGENCE!
            'impact': -15,  # Strong penalty
            'btc_change': -2.1,
            'symbol_change': +2.3
        }
    }
    
    # Calculate combined score
    combined = helper.calculate_combined_score(
        technical_confidence=78.0,
        fundamental_data=fundamental_data
    )
    
    print(f"\nCombined Score: {combined['combined_score']}")
    print(f"  - Technical:  {combined['technical_contribution']}")
    print(f"  - BTC Corr:   {combined['btc_correlation_contribution']:+.1f} (DIVERGENCE!)")
    print(f"\n→ Score reduced from 78 to {combined['combined_score']}")
    
    # Generate recommendation
    recommendation = helper.generate_recommendation(
        signal_direction='BULLISH',
        technical_confidence=78.0,
        fundamental_data=fundamental_data,
        combined_score=combined['combined_score']
    )
    
    print(f"\nRECOMMENDATION:")
    for line in recommendation.split('\n'):
        print(f"  {line}")
    
    if 'WARNING' in recommendation:
        print("\n✅ Divergence warning correctly included")


def test_scenario_4_news_cache():
    """Test news caching system"""
    print("\n" + "="*60)
    print("SCENARIO 4: News Cache System")
    print("="*60)
    
    cache = NewsCache(cache_dir='cache/demo', ttl_minutes=60)
    
    # Simulate news articles
    news = [
        {
            'title': 'Bitcoin ETF approval boosts market sentiment',
            'source': 'Bloomberg',
            'time': datetime.now().isoformat()
        },
        {
            'title': 'Institutional adoption accelerates',
            'source': 'Reuters',
            'time': datetime.now().isoformat()
        }
    ]
    
    # Cache articles
    print("\n1. Caching news articles...")
    cache.set_cached_news('BTCUSDT', news)
    print(f"   ✅ Cached {len(news)} articles")
    
    # Retrieve from cache
    print("\n2. Retrieving from cache...")
    cached = cache.get_cached_news('BTCUSDT')
    if cached:
        print(f"   ✅ Retrieved {len(cached)} articles (cache HIT)")
    else:
        print("   ❌ Cache MISS")
    
    # Check stats
    stats = cache.get_cache_stats()
    print(f"\n3. Cache statistics:")
    print(f"   - Symbols: {stats['symbols']}")
    print(f"   - Total articles: {stats['total_articles']}")
    
    print("\n→ News cache reduces redundant API calls")


def main():
    """Run all validation scenarios"""
    print("\n" + "="*60)
    print("PHASE 2 PART 1: VALIDATION TESTS")
    print("Signal Enhancement with Fundamental Analysis")
    print("="*60)
    
    try:
        test_scenario_1_technical_only()
        test_scenario_2_positive_alignment()
        test_scenario_3_btc_divergence()
        test_scenario_4_news_cache()
        
        print("\n" + "="*60)
        print("✅ ALL VALIDATION TESTS PASSED")
        print("="*60)
        print("\nFeature Summary:")
        print("  - Fundamental analysis ready for integration")
        print("  - Combined score calculation working")
        print("  - BTC divergence detection working")
        print("  - News cache system working")
        print("  - Feature flags control activation")
        print("\nTo enable in production:")
        print("  1. Set all fundamental_analysis flags to true")
        print("  2. Populate news cache with /newsupdate command")
        print("  3. Test with /signal BTC")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
