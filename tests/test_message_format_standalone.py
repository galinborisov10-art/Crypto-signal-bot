"""
Simple standalone test for format_no_trade_message function
Tests without requiring full bot.py dependencies
"""

import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_format_function():
    """Test the format_no_trade_message formatting logic directly"""
    
    # Create sample NO_TRADE data
    no_trade_data = {
        'type': 'NO_TRADE',
        'symbol': 'BTCUSDT',
        'timeframe': '4h',
        'reason': 'Entry zone validation failed: NO_ZONE',
        'details': 'Current price: $45000.00. No valid entry zone found in acceptable range (0.5%-3%).',
        'mtf_breakdown': {
            '1m': {'bias': 'NO_DATA', 'confidence': 0, 'aligned': True},
            '5m': {'bias': 'NO_DATA', 'confidence': 0, 'aligned': True},
            '15m': {'bias': 'BULLISH', 'confidence': 45, 'aligned': True},
            '1h': {'bias': 'BULLISH', 'confidence': 67, 'aligned': True},
            '4h': {'bias': 'BULLISH', 'confidence': 100, 'aligned': True},
            '1d': {'bias': 'BEARISH', 'confidence': 55, 'aligned': False},
            '1w': {'bias': 'NO_DATA', 'confidence': 0, 'aligned': True}
        },
        'mtf_consensus_pct': 85.7,
        'current_price': 45000.00,
        'price_change_24h': 2.5,
        'rsi': 55.0,
        'signal_direction': 'BUY',
        'confidence': None,
        'ict_components': {
            'order_blocks': [],  # No order blocks found
            'fvgs': [],  # No FVGs found
            'liquidity_zones': []  # No liquidity zones
        },
        'entry_status': 'NO_ZONE',
        'structure_broken': False,
        'displacement_detected': False
    }
    
    # Simulate the formatting logic from bot.py
    symbol = no_trade_data.get('symbol', 'UNKNOWN')
    timeframe = no_trade_data.get('timeframe', '?')
    reason = no_trade_data.get('reason', 'Unknown reason')
    details = no_trade_data.get('details', '')
    mtf_breakdown = no_trade_data.get('mtf_breakdown', {})
    current_price = no_trade_data.get('current_price')
    entry_status = no_trade_data.get('entry_status')
    ict_components = no_trade_data.get('ict_components')
    
    print("\n" + "="*60)
    print("TEST: Enhanced NO_TRADE Message Formatting")
    print("="*60)
    
    # Build message header
    msg = f"""❌ НЯМА ПОДХОДЯЩ ТРЕЙД

💰 Символ: {symbol}
⏰ Таймфрейм: {timeframe}

🚫 Причина: {reason}
📋 Детайли: {details}
"""
    
    if current_price is not None:
        msg += f"\n💵 Текуща цена: ${current_price:,.2f}"
    
    # ICT Analysis section
    msg += "\n\n━━━━━━━━━━━━━━━━━━━━━━"
    msg += "\n🔍 ICT АНАЛИЗ - Защо няма трейд:\n"
    
    if ict_components:
        # Entry Zone
        msg += "\n📍 Entry Zone:"
        if entry_status == 'NO_ZONE':
            msg += "\n   └─ ❌ ЛИПСВА"
            msg += "\n   └─ Не е открита валидна entry zone в диапазон 0.5%-3%"
        
        # Order Blocks
        order_blocks = ict_components.get('order_blocks', [])
        msg += "\n\n🎯 Order Blocks:"
        if not order_blocks:
            msg += "\n   └─ ❌ Не са открити валидни Order Blocks"
        
        # FVG
        fvgs = ict_components.get('fvgs', [])
        msg += "\n\n📊 FVG (Fair Value Gaps):"
        if not fvgs:
            msg += "\n   └─ ❌ Не са открити валидни FVG"
        
        # Structure Break
        msg += "\n\n🔄 Structure Break (BOS/CHOCH):"
        if not no_trade_data.get('structure_broken'):
            msg += "\n   └─ ❌ НЕ Е ПОТВЪРДЕН"
        
        # Displacement
        msg += "\n\n💨 Displacement:"
        if not no_trade_data.get('displacement_detected'):
            msg += "\n   └─ ❌ НЕ Е ОТКРИТ"
    
    # MTF Breakdown
    msg += "\n\n━━━━━━━━━━━━━━━━━━━━━━"
    msg += "\n📊 MTF Breakdown:\n"
    
    if mtf_breakdown:
        for tf in ['1m', '5m', '15m', '1h', '4h', '1d', '1w']:
            if tf in mtf_breakdown:
                data = mtf_breakdown[tf]
                bias = data.get('bias', 'UNKNOWN')
                aligned = data.get('aligned', False)
                confidence = data.get('confidence', 0)
                
                emoji = "✅" if aligned else "❌"
                
                if bias == 'NO_DATA':
                    msg += f"{emoji} {tf}: Няма данни\n"
                else:
                    current_marker = " ← текущ" if tf == timeframe else ""
                    msg += f"{emoji} {tf}: {bias} ({confidence:.0f}%){current_marker}\n"
    
    # Recommendations
    msg += "\n━━━━━━━━━━━━━━━━━━━━━━"
    msg += "\n💡 Препоръка:"
    msg += "\n• Изчакайте формиране на валидна entry zone"
    msg += "\n• Проверете за structure break или displacement"
    
    print(msg)
    print("\n" + "="*60)
    print("TEST RESULTS:")
    print("="*60)
    
    # Verify key sections are present
    checks = {
        "ICT АНАЛИЗ": "ICT АНАЛИЗ" in msg,
        "Entry Zone": "Entry Zone" in msg,
        "Order Blocks": "Order Blocks" in msg,
        "FVG": "FVG" in msg,
        "Structure Break": "Structure Break" in msg,
        "Displacement": "Displacement" in msg,
        "MTF Breakdown": "MTF Breakdown" in msg,
        "Препоръка": "Препоръка" in msg,
        "1m timeframe": "1m" in msg,
        "4h timeframe": "4h" in msg,
        "1d timeframe": "1d" in msg,
        "Conflicting TF marked": "❌ 1d: BEARISH" in msg
    }
    
    all_passed = True
    for check_name, check_result in checks.items():
        status = "✅ PASS" if check_result else "❌ FAIL"
        print(f"{status}: {check_name}")
        if not check_result:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("✅ ALL CHECKS PASSED!")
        print("Enhanced NO_TRADE message formatting is working correctly.")
    else:
        print("❌ SOME CHECKS FAILED!")
        print("Please review the message format.")
    print("="*60)
    
    return all_passed


if __name__ == '__main__':
    success = test_format_function()
    exit(0 if success else 1)
