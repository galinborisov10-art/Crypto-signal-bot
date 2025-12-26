#!/usr/bin/env python3
"""
Validation script for Phase 2 Part 2: Market Integration
Tests the market data fetcher and helper classes independently
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.market_data_fetcher import MarketDataFetcher
from utils.market_helper import MarketHelper, format_market_fundamental_section


def test_market_data_fetcher():
    """Test MarketDataFetcher"""
    print("=" * 60)
    print("Testing MarketDataFetcher")
    print("=" * 60)
    
    fetcher = MarketDataFetcher(cache_ttl=60)
    
    # Test Fear & Greed Index
    print("\n1. Fetching Fear & Greed Index...")
    fear_greed = fetcher.get_fear_greed_index()
    if fear_greed:
        print(f"   ✅ Value: {fear_greed['value']}")
        print(f"   ✅ Label: {fear_greed['label']}")
        print(f"   ✅ Timestamp: {fear_greed['timestamp']}")
    else:
        print("   ❌ Failed to fetch Fear & Greed Index")
    
    # Test Market Overview
    print("\n2. Fetching Market Overview...")
    market_data = fetcher.get_market_overview()
    if market_data:
        print(f"   ✅ BTC Dominance: {market_data['btc_dominance']:.2f}%")
        print(f"   ✅ Market Cap: ${market_data['market_cap']/1e12:.2f}T")
        print(f"   ✅ 24h Change: {market_data['market_cap_change_24h']:+.2f}%")
        print(f"   ✅ Total Volume: ${market_data['total_volume_24h']/1e9:.2f}B")
    else:
        print("   ❌ Failed to fetch Market Overview")
    
    return fear_greed, market_data


def test_market_helper():
    """Test MarketHelper"""
    print("\n" + "=" * 60)
    print("Testing MarketHelper")
    print("=" * 60)
    
    helper = MarketHelper()
    
    # Test is_enabled
    print("\n1. Checking if feature is enabled...")
    enabled = helper.is_enabled()
    print(f"   {'✅' if enabled else '⚠️'} Feature enabled: {enabled}")
    
    if not enabled:
        print("   ℹ️  Feature is disabled in config. To enable:")
        print("      Edit config/feature_flags.json")
        print("      Set 'fundamental_analysis.enabled' = true")
        print("      Set 'fundamental_analysis.market_integration' = true")
        return None
    
    # Test get_market_fundamentals
    print("\n2. Getting market fundamentals...")
    fundamentals = helper.get_market_fundamentals('BTCUSDT')
    
    if fundamentals:
        print(f"   ✅ Retrieved {len(fundamentals)} data points")
        
        if 'fear_greed' in fundamentals:
            fg = fundamentals['fear_greed']
            print(f"   ✅ Fear & Greed: {fg['value']} ({fg['label']})")
        
        if 'btc_dominance' in fundamentals:
            print(f"   ✅ BTC Dominance: {fundamentals['btc_dominance']:.2f}%")
        
        if 'market_cap' in fundamentals:
            print(f"   ✅ Market Cap: ${fundamentals['market_cap']/1e12:.2f}T")
    else:
        print("   ❌ Failed to get market fundamentals")
    
    return fundamentals


def test_market_context(fundamentals):
    """Test market context generation"""
    if not fundamentals:
        print("\n⚠️  Skipping market context test (no fundamentals)")
        return
    
    print("\n" + "=" * 60)
    print("Testing Market Context Generation")
    print("=" * 60)
    
    helper = MarketHelper()
    
    # Generate context for bullish scenario
    print("\n1. Bullish Scenario (price +3.5%)...")
    context = helper.generate_market_context(
        fundamentals=fundamentals,
        price_change_24h=3.5,
        volume_24h=1000000
    )
    print(context)
    
    # Generate context for bearish scenario
    print("\n2. Bearish Scenario (price -3.5%)...")
    context = helper.generate_market_context(
        fundamentals=fundamentals,
        price_change_24h=-3.5,
        volume_24h=1000000
    )
    print(context)


def test_formatting(fundamentals):
    """Test message formatting"""
    if not fundamentals:
        print("\n⚠️  Skipping formatting test (no fundamentals)")
        return
    
    print("\n" + "=" * 60)
    print("Testing Message Formatting")
    print("=" * 60)
    
    helper = MarketHelper()
    
    context = helper.generate_market_context(
        fundamentals=fundamentals,
        price_change_24h=2.5,
        volume_24h=1000000
    )
    
    formatted = format_market_fundamental_section(fundamentals, context)
    
    print("\n📱 Formatted Message (HTML):")
    print(formatted)


def main():
    """Main validation function"""
    print("🔍 Phase 2 Part 2 Validation Script")
    print("=" * 60)
    
    try:
        # Test MarketDataFetcher
        fear_greed, market_data = test_market_data_fetcher()
        
        # Test MarketHelper
        fundamentals = test_market_helper()
        
        # Test context generation
        test_market_context(fundamentals)
        
        # Test formatting
        test_formatting(fundamentals)
        
        # Summary
        print("\n" + "=" * 60)
        print("✅ Validation Complete")
        print("=" * 60)
        
        if fear_greed and market_data:
            print("✅ MarketDataFetcher: Working")
        else:
            print("⚠️  MarketDataFetcher: Partial failure")
        
        if fundamentals:
            print("✅ MarketHelper: Working")
        else:
            print("⚠️  MarketHelper: Feature disabled or failed")
        
        print("\nℹ️  To use in production:")
        print("   1. Enable feature flags in config/feature_flags.json")
        print("   2. Restart the bot")
        print("   3. Send /market command in Telegram")
        
    except Exception as e:
        print(f"\n❌ Validation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
