"""
Helper functions for ICT signal entry zone validation and formatting.
Extracted from bot.py to enable independent testing.
"""


def _validate_signal_timing(signal_data: dict, entry_zone: dict, entry_status: str) -> tuple:
    """
    Validate if signal should be sent based on entry zone timing.
    
    CRITICAL RULES:
    1. Block signal if status == 'TOO_LATE'
    2. Block signal if status == 'NO_ZONE'
    3. Allow signal if status == 'VALID_WAIT' or 'VALID_NEAR'
    
    Returns:
        (should_send: bool, message: str)
    """
    if entry_status == 'TOO_LATE':
        return False, "❌ Закъснял сигнал - цената вече е минала entry зоната"
    
    if entry_status == 'NO_ZONE':
        return False, "❌ Няма валидна entry зона в допустимия диапазон"
    
    if entry_status == 'VALID_WAIT':
        distance = entry_zone['distance_pct']
        center = entry_zone['center']
        return True, f"⏳ ЧАКАЙ pullback към ${center:.4f} ({distance:.1f}% разстояние)"
    
    if entry_status == 'VALID_NEAR':
        center = entry_zone['center']
        return True, f"🎯 Цената се приближава към entry зоната (${center:.4f})"
    
    return False, "❌ Неизвестен entry статус"


def _format_entry_guidance(entry_zone: dict, entry_status: str, current_price: float, direction: str) -> str:
    """
    Format entry guidance section for signal message.
    
    CRITICAL RULES:
    1. Show entry zone details (source, range, quality)
    2. Show current price position and distance
    3. Provide clear instructions based on status:
       - VALID_WAIT: "⏳ ЧАКАЙ pullback" + warning + alert suggestion
       - VALID_NEAR: "🎯 ПРИБЛИЖАВА" + preparation instructions
    4. Use visual indicators: ⬆️ for SELL, ⬇️ for BUY
    """
    # Determine arrow based on direction
    if 'BEARISH' in direction.upper() or 'SELL' in direction.upper():
        arrow = "⬆️"  # Price needs to go UP to entry zone for SELL
        direction_text = "нагоре"
    else:
        arrow = "⬇️"  # Price needs to go DOWN to entry zone for BUY
        direction_text = "надолу"
    
    # Build base structure
    guidance = "\n━━━━━━━━━━━━━━━━━━━━\n"
    guidance += "🎯 <b>ENTRY GUIDANCE:</b>\n\n"
    
    guidance += f"📍 <b>Entry Zone ({entry_zone['source']}):</b>\n"
    guidance += f"   Center: <b>${entry_zone['center']:,.4f}</b>\n"
    guidance += f"   Range: ${entry_zone['low']:,.4f} - ${entry_zone['high']:,.4f}\n"
    guidance += f"   Quality: {entry_zone['quality']}/100\n\n"
    
    guidance += f"📊 <b>Current Position:</b>\n"
    guidance += f"   Price: ${current_price:,.4f}\n"
    guidance += f"   Distance: {arrow} {entry_zone['distance_pct']:.1f}% (${abs(entry_zone['distance_price']):,.2f})\n\n"
    
    # Status-specific guidance
    if entry_status == 'VALID_WAIT':
        guidance += "⏳ <b>STATUS: WAIT FOR PULLBACK</b>\n\n"
        guidance += "   ⚠️ <b>НЕ влизай веднага!</b>\n\n"
        guidance += f"   ✅ <b>Чакай цената да:</b>\n"
        guidance += f"   • Се върне {arrow} към entry зоната\n"
        guidance += "   • Покаже rejection candle pattern\n"
        guidance += "   • Има volume confirmation\n\n"
        guidance += f"   🔔 Настрой alert на: <b>${entry_zone['center']:,.4f}</b>\n"
    
    elif entry_status == 'VALID_NEAR':
        guidance += "🎯 <b>STATUS: APPROACHING ENTRY</b>\n\n"
        guidance += "   ⚡ <b>Цената е близо до entry зоната!</b>\n\n"
        guidance += "   ✅ <b>Подготви се за вход при:</b>\n"
        guidance += "   • Влизане в entry зоната\n"
        guidance += f"   • Rejection от {entry_zone['source']}\n"
        guidance += "   • Volume spike + candle confirmation\n\n"
        guidance += "   ⏱️ <b>Очаквано време:</b> 15-60 мин\n"
    
    return guidance
