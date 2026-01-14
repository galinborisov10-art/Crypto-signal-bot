"""
Bulgarian Message Templates for Enhanced Signals (PR #8)
Localization for obstacle warnings, news sentiment, and smart TP strategies
"""

from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


# ════════════════════════════════════════════════════════════════
# OBSTACLE TYPE TRANSLATIONS
# ════════════════════════════════════════════════════════════════

OBSTACLE_TEMPLATES = {
    'BEARISH_OB': 'Bearish Order Block',
    'BEARISH_FVG': 'Bearish Fair Value Gap',
    'RESISTANCE': 'Съпротива',
    'SUPPORT': 'Подкрепа',
    'BEARISH_WHALE': 'Bearish Whale Block',
    'BULLISH_OB': 'Bullish Order Block',
    'BULLISH_FVG': 'Bullish Fair Value Gap',
    'BULLISH_WHALE': 'Bullish Whale Block',
    'MITIGATION': 'Mitigation Block',
    'BREAKER': 'Breaker Block',
}

# ════════════════════════════════════════════════════════════════
# STRENGTH CATEGORIES (Bulgarian)
# ════════════════════════════════════════════════════════════════

STRENGTH_CATEGORIES_BG = {
    'VERY_STRONG': 'МНОГО СИЛНА',
    'STRONG': 'СИЛНА',
    'MODERATE': 'СРЕДНА',
    'WEAK': 'СЛАБА',
}

# ════════════════════════════════════════════════════════════════
# PREDICTION TEMPLATES (Bulgarian)
# ════════════════════════════════════════════════════════════════

PREDICTION_BG = {
    'VERY_LIKELY_REJECT': 'МНОГО ВЕРОЯТНО ОТБЛЪСКВАНЕ',
    'LIKELY_REJECT': 'ВЕРОЯТНО ОТБЛЪСКВАНЕ',
    'UNCERTAIN': 'НЕСИГУРНО',
    'LIKELY_BREAK': 'ВЕРОЯТНО ПРОБИВАНЕ',
}


def get_strength_category_bg(strength: float) -> str:
    """
    Get Bulgarian strength category from numerical strength
    
    Args:
        strength: Obstacle strength (0-100)
        
    Returns:
        Bulgarian strength category string
    """
    if strength >= 75:
        return STRENGTH_CATEGORIES_BG['VERY_STRONG']
    elif strength >= 60:
        return STRENGTH_CATEGORIES_BG['STRONG']
    elif strength >= 45:
        return STRENGTH_CATEGORIES_BG['MODERATE']
    else:
        return STRENGTH_CATEGORIES_BG['WEAK']


def get_prediction_bg(strength: float, will_reject: bool) -> str:
    """
    Get Bulgarian prediction from obstacle evaluation
    
    Args:
        strength: Obstacle strength (0-100)
        will_reject: Whether obstacle will likely reject price
        
    Returns:
        Bulgarian prediction string
    """
    if will_reject:
        if strength >= 75:
            return PREDICTION_BG['VERY_LIKELY_REJECT']
        else:
            return PREDICTION_BG['LIKELY_REJECT']
    else:
        if strength < 45:
            return PREDICTION_BG['LIKELY_BREAK']
        else:
            return PREDICTION_BG['UNCERTAIN']


def format_obstacle_warning_bg(
    obstacle: Dict,
    evaluation: Dict,
    obstacle_number: int,
    entry_price: float
) -> str:
    """
    Format obstacle warning in Bulgarian
    
    Args:
        obstacle: Obstacle data dict with type, price, strength, description
        evaluation: Evaluation result with strength, will_likely_reject, confidence, decision, reasoning
        obstacle_number: Sequential number of obstacle
        entry_price: Entry price for calculating distance %
        
    Returns:
        Formatted Bulgarian obstacle warning message
        
    Example output:
    
    🔴 OBSTACLE #1: Bearish Order Block @ $2.45 (+20.0%)
       Тип: Институционална продажба
       Сила: 95/100 (МНОГО СИЛНА) 🔴
       Оценка: МНОГО ВЕРОЯТНО ОТБЛЪСКВАНЕ (85%)
       
       📊 Анализ:
       ├─ HTF bias подкрепя зоната ⚠️
       ├─ Висок volume в зоната ⚠️
       ├─ MTF потвърждение (4H+1D) ⚠️
       └─ Заключение: Силна съпротива, ще отблъсне
       
       💡 Действие: TP2 ПРЕДИ тази зона ($2.43)
    """
    try:
        obstacle_type = obstacle.get('type', 'UNKNOWN')
        obstacle_price = obstacle.get('price', 0)
        obstacle_strength = obstacle.get('strength', 0)
        obstacle_desc = obstacle.get('description', '')
        
        eval_strength = evaluation.get('strength', 0)
        will_reject = evaluation.get('will_likely_reject', False)
        confidence = evaluation.get('confidence', 0)
        decision = evaluation.get('decision', '')
        reasoning = evaluation.get('reasoning', '')
        
        # Calculate distance from entry
        if entry_price > 0:
            distance_pct = ((obstacle_price - entry_price) / entry_price) * 100
            distance_str = f"+{distance_pct:.1f}%" if distance_pct > 0 else f"{distance_pct:.1f}%"
        else:
            distance_str = "N/A"
        
        # Get strength category and emoji
        strength_category = get_strength_category_bg(eval_strength)
        if eval_strength >= 75:
            strength_emoji = "🔴"
        elif eval_strength >= 60:
            strength_emoji = "🟠"
        elif eval_strength >= 45:
            strength_emoji = "🟡"
        else:
            strength_emoji = "🟢"
        
        # Get prediction
        prediction = get_prediction_bg(eval_strength, will_reject)
        
        # Get translated obstacle type
        obstacle_type_bg = OBSTACLE_TEMPLATES.get(obstacle_type, obstacle_type)
        
        # Build message
        message = f"\n{'='*50}\n"
        message += f"🔴 OBSTACLE #{obstacle_number}: {obstacle_type_bg} @ ${obstacle_price:.2f} ({distance_str})\n"
        message += f"   Тип: {obstacle_desc}\n"
        message += f"   Сила: {int(eval_strength)}/100 ({strength_category}) {strength_emoji}\n"
        message += f"   Оценка: {prediction} ({int(confidence)}%)\n"
        message += f"\n"
        message += f"   📊 Анализ:\n"
        
        # Parse reasoning into bullet points
        reasoning_lines = reasoning.split('\n') if reasoning else [decision]
        for i, line in enumerate(reasoning_lines):
            if line.strip():
                if i < len(reasoning_lines) - 1:
                    message += f"   ├─ {line.strip()}\n"
                else:
                    message += f"   └─ {line.strip()}\n"
        
        # Add action recommendation
        if will_reject and eval_strength >= 60:
            action_price = obstacle_price * (1 - 0.003)  # 0.3% buffer
            message += f"\n"
            message += f"   💡 Действие: TP ПРЕДИ тази зона (${action_price:.2f})\n"
        else:
            message += f"\n"
            message += f"   💡 Действие: TP СЛЕД тази зона (вероятно ще пробие)\n"
        
        message += f"{'='*50}\n"
        
        return message
        
    except Exception as e:
        logger.error(f"Error formatting obstacle warning: {e}")
        return f"\n⚠️ Грешка при форматиране на obstacle #{obstacle_number}\n"


def format_news_sentiment_bg(news_check: Dict) -> str:
    """
    Format news sentiment analysis in Bulgarian
    
    Args:
        news_check: News check result with sentiment_score, critical_news, reasoning
        
    Returns:
        Formatted Bulgarian news sentiment message
        
    Example output:
    
    📰 ФУНДАМЕНТАЛЕН АНАЛИЗ
    ━━━━━━━━━━━━━━━━━━━━━━
    
    ✅ Позитивни новини (Sentiment: +75)
    
    Скорошни новини:
    🔴 CRITICAL (2h ago):
       "Major institution announces $500M BTC purchase"
    
    💡 ОЦЕНКА: Новините СИЛНО поддържат LONG позиция
              Очакван краткосрочен rally (+5-10%)
    """
    try:
        sentiment_score = news_check.get('sentiment_score', 0)
        critical_news = news_check.get('critical_news', [])
        reasoning = news_check.get('reasoning', '')
        
        message = f"\n{'━'*50}\n"
        message += f"📰 ФУНДАМЕНТАЛЕН АНАЛИЗ\n"
        message += f"{'━'*50}\n\n"
        
        # Sentiment indicator
        if sentiment_score > 30:
            sentiment_emoji = "✅"
            sentiment_label = "Позитивни новини"
        elif sentiment_score < -30:
            sentiment_emoji = "❌"
            sentiment_label = "Негативни новини"
        elif sentiment_score > 10:
            sentiment_emoji = "🟢"
            sentiment_label = "Леко позитивни новини"
        elif sentiment_score < -10:
            sentiment_emoji = "🔴"
            sentiment_label = "Леко негативни новини"
        else:
            sentiment_emoji = "⚪"
            sentiment_label = "Неутрални новини"
        
        message += f"{sentiment_emoji} {sentiment_label} (Sentiment: {sentiment_score:+d})\n\n"
        
        # Critical news (if any)
        if critical_news:
            message += "Скорошни новини:\n"
            for news_item in critical_news[:3]:  # Show max 3 news items
                importance = news_item.get('importance', 'NORMAL')
                time_ago = news_item.get('time_ago', 'N/A')
                title = news_item.get('title', 'No title')
                
                if importance == 'CRITICAL':
                    news_emoji = "🔴"
                elif importance == 'IMPORTANT':
                    news_emoji = "🟠"
                else:
                    news_emoji = "🔵"
                
                message += f"{news_emoji} {importance} ({time_ago}):\n"
                message += f"   \"{title}\"\n\n"
        
        # Reasoning
        message += f"💡 ОЦЕНКА: {reasoning}\n"
        message += f"{'━'*50}\n"
        
        return message
        
    except Exception as e:
        logger.error(f"Error formatting news sentiment: {e}")
        return f"\n⚠️ Грешка при форматиране на новини\n"


def format_smart_tp_strategy_bg(
    entry_price: float,
    tp_prices: List[float],
    obstacles: List[Dict],
    signal_direction: str
) -> str:
    """
    Format recommended TP strategy in Bulgarian
    
    Args:
        entry_price: Entry price
        tp_prices: List of [TP1, TP2, TP3]
        obstacles: List of obstacles that affected TP placement
        signal_direction: 'BUY' or 'SELL'
        
    Returns:
        Formatted Bulgarian TP strategy message
        
    Example output:
    
    📈 ПРЕПОРЪЧАНА СТРАТЕГИЯ
    ━━━━━━━━━━━━━━━━━━━━━━
    
    🎯 КОНСЕРВАТИВЕН ПОДХОД:
    1. Вход @ $2.04
    2. Затвори 50% @ $2.43 (TP2)
       → Сигурна печалба +19.3% преди силна зона
    3. Премести SL на breakeven
    4. Остави 50% за TP1 @ $2.50
       → Ако пробие $2.45, има потенциал
    
    Очакван резултат: +20-22% средно ✅
    """
    try:
        if len(tp_prices) < 3:
            return ""
        
        tp1, tp2, tp3 = tp_prices[0], tp_prices[1], tp_prices[2]
        
        message = f"\n{'━'*50}\n"
        message += f"📈 ПРЕПОРЪЧАНА СТРАТЕГИЯ\n"
        message += f"{'━'*50}\n\n"
        
        # Calculate profit percentages
        if signal_direction == 'BUY':
            tp1_pct = ((tp1 - entry_price) / entry_price) * 100
            tp2_pct = ((tp2 - entry_price) / entry_price) * 100
            tp3_pct = ((tp3 - entry_price) / entry_price) * 100
        else:
            tp1_pct = ((entry_price - tp1) / entry_price) * 100
            tp2_pct = ((entry_price - tp2) / entry_price) * 100
            tp3_pct = ((entry_price - tp3) / entry_price) * 100
        
        message += f"🎯 КОНСЕРВАТИВЕН ПОДХОД:\n"
        message += f"1. Вход @ ${entry_price:.2f}\n"
        message += f"2. Затвори 50% @ ${tp1:.2f} (TP1)\n"
        message += f"   → Сигурна печалба +{tp1_pct:.1f}%\n"
        
        # Check if TP1 was adjusted for obstacles
        if obstacles:
            strong_obstacles = [o for o in obstacles if o.get('strength', 0) >= 60]
            if strong_obstacles:
                message += f"   → Позиционирано ПРЕДИ силна зона\n"
        
        message += f"3. Премести SL на breakeven\n"
        message += f"4. Остави 50% за TP2 @ ${tp2:.2f}\n"
        message += f"   → Потенциална печалба +{tp2_pct:.1f}%\n"
        
        # Calculate expected average
        avg_profit = (tp1_pct * 0.5 + tp2_pct * 0.25 + tp3_pct * 0.25)
        
        message += f"\nОчакван резултат: +{avg_profit:.1f}% средно ✅\n"
        message += f"{'━'*50}\n"
        
        return message
        
    except Exception as e:
        logger.error(f"Error formatting TP strategy: {e}")
        return f"\n⚠️ Грешка при форматиране на стратегия\n"


def format_checkpoint_recommendation_bg(
    checkpoint_level: str,
    recommendation: str,
    reasoning: str,
    news_impact: Optional[Dict] = None
) -> str:
    """
    Format checkpoint recommendation in Bulgarian
    
    Args:
        checkpoint_level: Checkpoint level (e.g., "50%", "75%")
        recommendation: Recommendation type (HOLD, MOVE_SL, PARTIAL_CLOSE, CLOSE_NOW)
        reasoning: Reasoning for recommendation
        news_impact: Optional news sentiment impact data
        
    Returns:
        Formatted Bulgarian checkpoint recommendation
    """
    try:
        message = f"\n{'='*50}\n"
        message += f"🔄 CHECKPOINT {checkpoint_level} - ПРЕПОРЪКА\n"
        message += f"{'='*50}\n\n"
        
        # Recommendation with emoji
        rec_emojis = {
            'HOLD': '✅',
            'MOVE_SL': '🔄',
            'PARTIAL_CLOSE': '⚠️',
            'CLOSE_NOW': '❌'
        }
        
        rec_labels_bg = {
            'HOLD': 'ЗАДЪРЖИ',
            'MOVE_SL': 'ПРЕМЕСТИ SL',
            'PARTIAL_CLOSE': 'ЧАСТИЧНО ЗАТВАРЯНЕ',
            'CLOSE_NOW': 'ЗАТВОРИ СЕГА'
        }
        
        emoji = rec_emojis.get(recommendation, '❓')
        label_bg = rec_labels_bg.get(recommendation, recommendation)
        
        message += f"{emoji} ПРЕПОРЪКА: {label_bg}\n\n"
        message += f"💡 Обосновка:\n{reasoning}\n"
        
        # Add news impact if present
        if news_impact:
            sentiment_changed = news_impact.get('sentiment_turned_negative', False)
            critical_appeared = news_impact.get('critical_news_appeared', False)
            
            if sentiment_changed or critical_appeared:
                message += f"\n📰 НОВИНИ:\n"
                if critical_appeared:
                    message += f"   🔴 Критични новини се появиха!\n"
                if sentiment_changed:
                    message += f"   ⚠️ Sentiment се обърна срещу позицията\n"
        
        message += f"\n{'='*50}\n"
        
        return message
        
    except Exception as e:
        logger.error(f"Error formatting checkpoint recommendation: {e}")
        return f"\n⚠️ Грешка при форматиране на препоръка\n"


# Export main formatting functions
__all__ = [
    'format_obstacle_warning_bg',
    'format_news_sentiment_bg',
    'format_smart_tp_strategy_bg',
    'format_checkpoint_recommendation_bg',
    'OBSTACLE_TEMPLATES',
    'STRENGTH_CATEGORIES_BG',
    'PREDICTION_BG',
]
