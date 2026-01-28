"""
🎯 NARRATIVE TEMPLATES - Professional Swing Trader Voice

This module provides professional, educational Bulgarian narratives for checkpoint alerts.
Characteristics:
- First-person perspective ("Виждам че...", "Бих направил...")
- Explains REASONING, not just facts
- Context and market environment awareness
- Multiple scenarios and thought process
- Risk management focus
- Honest about uncertainty
- Professional but conversational tone
- Teaches while alerting

Author: galinborisov10-art
Date: 2026-01-28
PR: #214 - Enhanced Checkpoint Monitoring System
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class SwingTraderNarrative:
    """
    Professional Swing Trader Narrative Generator
    
    Generates educational, context-aware alerts in Bulgarian
    with first-person swing trader perspective.
    """
    
    @staticmethod
    def checkpoint_all_good(
        position: Dict,
        analysis: Any,
        checkpoint: int,
        progress: float,
        current_price: float
    ) -> str:
        """
        Narrative for checkpoint when everything is on track
        
        Args:
            position: Position dictionary
            analysis: CheckpointAnalysis object
            checkpoint: Checkpoint level (25, 50, 75, 85)
            progress: Current progress percentage
            current_price: Current market price
            
        Returns:
            Bulgarian narrative message
        """
        symbol = position['symbol']
        confidence = analysis.current_confidence if analysis else 0
        rr_ratio = analysis.current_rr_ratio if analysis else 0
        
        # Different messages for different checkpoints
        if checkpoint == 25:
            message = f"""
✅ {checkpoint}% CHECKPOINT - {symbol}

Добър старт! Position се развива както очаквам.

Какво виждам:
• Структурата е валидна - все още нямаме BOS
• HTF bias остава същият (momentum продължава)
• Confidence: {confidence:.0f}% - stable
• R:R сега е {rr_ratio:.1f}:1

💡 Моята позиция като swing trader:

ЗАДРЪЖАМ 100% от позицията. Това е ранен етап и структурата
показва continuation pattern. Smart money все още купува/продава
в нашата посока.

Watch for: Следващ checkpoint @ 50%, HTF structure breaks

Progress: {progress:.1f}% към TP1 @ {position['tp1_price']}
"""
        elif checkpoint == 85:
            message = f"""
💎 {checkpoint}% CHECKPOINT - {symbol}

Почти там! Excellent execution до момента.

Какво виждам:
• {progress:.1f}% progress към TP1 - outstanding
• Структурата здрава - няма signs за reversal
• HTF bias непроменен - trend е жив
• Confidence: {confidence:.0f}%

💡 Моята позиция като swing trader:

1️⃣ Затварям 50-60% СЕГА при {current_price:.2f}
   → Lock in profit (вече е почти TP1)
   → Risk management - не давам back gains

2️⃣ SL премества на {position['entry_price']:.2f} (breakeven)
   → Guaranteed win от тук нататък

3️⃣ Остатък 40-50% оставам за TP1
   → Trail до TP1 @ {position['tp1_price']:.2f}
   → Ако структурата се счупи → EXIT instantly

Why this approach:
85% е зоната където institutional traders вземат partial profit.
Не искам да бъда greedy. Half the position is already excellent
profit, остатъка е "free money" за TP1.

Watch for: TP1 hit, структура break, новини
"""
        else:  # 50% or 75%
            message = f"""
💎 {checkpoint}% CHECKPOINT - {symbol}

Позицията продължава в права посока.

Текущо състояние:
• Progress: {progress:.1f}% към TP1
• Структура: Валидна ✅
• HTF Bias: Непроменен ✅
• Confidence: {confidence:.0f}%
• R:R: {rr_ratio:.1f}:1

💡 ЗАДРЪЖАМ позицията.

Всичко е как трябва. Структурата е здрава, HTF bias подкрепя
позицията, и momentum продължава. Това е класически swing trade
в development.

Next checkpoint @ {checkpoint + 25 if checkpoint < 85 else 'TP1'}%

Watch for: BOS на HTF, inducement wicks, новини
"""
        
        return message
    
    @staticmethod
    def checkpoint_bias_changed(
        position: Dict,
        analysis: Any,
        checkpoint: int,
        progress: float,
        current_price: float,
        old_bias: str,
        new_bias: str
    ) -> str:
        """
        Narrative for HTF bias change (CRITICAL scenario)
        
        Args:
            position: Position dictionary
            analysis: CheckpointAnalysis object
            checkpoint: Checkpoint level
            progress: Current progress
            current_price: Current price
            old_bias: Previous HTF bias
            new_bias: New HTF bias
            
        Returns:
            Bulgarian narrative with bias change explanation
        """
        symbol = position['symbol']
        confidence = analysis.current_confidence if analysis else 0
        confidence_delta = analysis.confidence_delta if analysis else 0
        
        message = f"""
⚠️ {checkpoint}% CHECKPOINT - {symbol}

Хей, имаме промяна тук. Attention needed.

Какво се случва:
• HTF bias се промени от {old_bias} на {new_bias}
• Confidence: {confidence:.0f}% (Δ{confidence_delta:+.0f}%)
• Виждам inducement pattern на последните candles
• Структурата НЕ Е счупена (още), но momentum спира

Critical observation:
Това е класически sign че {old_bias.lower()} momentum губи контрол.
Все още нямаме BOS (break of structure), но HTF показва
{new_bias.lower()} sentiment. Smart money започва да се обръща.

💡 Моята позиция като swing trader:

1️⃣ Затварям 40-50% СЕГА (при {current_price:.2f})
   → Защитавам unrealized profit
   → Reducing risk exposure преди евентуален full reversal

2️⃣ SL премества на breakeven ({position['entry_price']:.2f})
   → No loss scenario от тук нататък
   → Peace of mind

3️⃣ Остатък 50-60% оставам в позицията, НО:
   → Ако видя BOS на H1/H4 → излизам ВЕДНАГА
   → Ако се появи нов HH/HL в {old_bias} → остavam за TP1
   → Ако излязат critical {new_bias.lower()} news → exit remaining

Why this approach:
Това не е panic exit. Структурата е жива. Но HTF bias change
е HUGE red flag. Като trader искам да lock profit и да не давам
back gains ако momentum се обърне напълно.

Risk/Reward сега е {analysis.current_rr_ratio:.1f}:1 което е все още solid
за remaining position.

Watch for: BOS на H1, sweep на entry liquidity, reversal patterns
"""
        
        return message
    
    @staticmethod
    def checkpoint_structure_broken(
        position: Dict,
        analysis: Any,
        checkpoint: int,
        progress: float,
        current_price: float
    ) -> str:
        """
        Narrative for structure break (URGENT EXIT scenario)
        
        Args:
            position: Position dictionary
            analysis: CheckpointAnalysis object
            checkpoint: Checkpoint level
            progress: Current progress
            current_price: Current price
            
        Returns:
            Bulgarian narrative with urgent exit recommendation
        """
        symbol = position['symbol']
        is_long = position['signal_type'] in ['BUY', 'STRONG_BUY']
        
        message = f"""
🚨 {checkpoint}% CHECKPOINT - {symbol}

СТРУКТУРАТА Е СЧУПЕНА! Reversal confirmation.

Какво се случи:
• BOS (Break of Structure) confirmed
• {'Bearish' if is_long else 'Bullish'} candles взеха control
• Inducement sweep е вече completed
• HTF bias вече е {'BEARISH' if is_long else 'BULLISH'}

Critical reality check:
След BOS, вероятността position да стигне TP1 е <30% според
ICT methodology. Smart money вече е exited и reversed.

💡 Моята позиция като swing trader:

🔴 ИЗЛИЗАМ 100% СЕГА при {current_price:.2f}

Why full exit:
Това не е "hope" play. Структурата е счупена, което значи
reversal е confirmed. Като swing trader, правилото ми е:
"BOS = EXIT immediately, no questions asked."

Profit до момента: {progress:.1f}% от TP1 distance
{'✅ Все още profit' if progress > 0 else '⚠️ At/near breakeven'}

What I learned:
BOS не е "може би". Когато се случи, position е invalidated.
По-добре да изляза early с малко profit/breakeven, отколкото
да чакам и да хвана full reversal.

Next action:
Чакам за нов setup. Re-entry САМО ако видя нов valid ICT signal
с clear structure на HTF.
"""
        
        return message
    
    @staticmethod
    def critical_news_alert(
        position: Dict,
        news_data: Dict,
        current_price: float,
        impact_assessment: str
    ) -> str:
        """
        Narrative for critical news between checkpoints
        
        Args:
            position: Position dictionary
            news_data: News data with headline, sentiment, impact
            current_price: Current price
            impact_assessment: Impact vs position assessment
            
        Returns:
            Bulgarian narrative with news impact analysis
        """
        symbol = position['symbol']
        headline = news_data.get('headline', 'Breaking market news')
        sentiment = news_data.get('sentiment_label', 'NEUTRAL')
        priority = news_data.get('priority', 'important')
        
        is_long = position['signal_type'] in ['BUY', 'STRONG_BUY']
        
        # Determine urgency
        is_critical = priority == 'critical'
        emoji = "🔴" if is_critical else "🟡"
        
        message = f"""
{emoji} BREAKING NEWS ALERT - {symbol}

📰 HEADLINE: {headline}

News Impact Analysis:
• Sentiment: {sentiment}
• Impact Level: {priority.upper()}
• {impact_assessment}

💡 Моята позиция като swing trader:

Current price: {current_price:.2f}
Position type: {'LONG' if is_long else 'SHORT'}
"""
        
        # Add specific action based on impact
        if 'CRITICAL' in impact_assessment or 'HIGH REVERSAL RISK' in impact_assessment:
            message += f"""
🚨 IMMEDIATE ACTION REQUIRED:

Новината contradicts нашата позиция! Това е high reversal risk.

1️⃣ Затварям 60-80% СЕГА
   → Exit majority преди market реагира напълно
   → Protecting capital е priority #1

2️⃣ SL премества to breakeven instantly
   → Guaranteed no loss на remaining position

3️⃣ Monitoring constantly
   → Ако price action confirms reversal → exit 100%
   → Ако се окаже false alarm → може да re-enter

Why this approach:
Critical news може да обърне trend за hours/days. След години
trading, научих че е по-добре да exit early при critical news
contradicting позицията, отколкото да "hope" че няма да се обърне.

Next 1-2 hours са crucial - watch price action closely!
"""
        elif 'подкрепя' in impact_assessment or 'Momentum в наша полза' in impact_assessment:
            message += f"""
✅ POSITIVE DEVELOPMENT:

Новината подкрепя нашата позиция! Momentum confirmation.

ЗАДРЪЖАМ 100% от позицията.

Това е добър sign. Fundamentals сега align с technical analysis.
Вероятността за TP1 hit се увеличава.

Watch for: Price action reaction в следващите candles, volume spike
"""
        else:
            message += f"""
⚠️ NEUTRAL/MIXED IMPACT:

Новината може да създаде volatility, но не е clear contradiction.

Затварям 20-30% за risk reduction
Остатък оставам, НО с tight monitoring.

Watch closely: Price reaction в следващите 30-60 min
"""
        
        return message
    
    @staticmethod
    def checkpoint_with_critical_news(
        position: Dict,
        analysis: Any,
        news_data: Dict,
        checkpoint: int,
        progress: float,
        current_price: float,
        impact_assessment: str
    ) -> str:
        """
        Narrative for checkpoint + critical news combination
        
        Args:
            position: Position dictionary
            analysis: CheckpointAnalysis object
            news_data: News data
            checkpoint: Checkpoint level
            progress: Current progress
            current_price: Current price
            impact_assessment: Impact assessment
            
        Returns:
            Combined narrative addressing both checkpoint and news
        """
        symbol = position['symbol']
        headline = news_data.get('headline', 'Market news')
        sentiment = news_data.get('sentiment_label', 'NEUTRAL')
        confidence = analysis.current_confidence if analysis else 0
        
        message = f"""
⚠️ {checkpoint}% CHECKPOINT + BREAKING NEWS - {symbol}

Двойно attention needed: Checkpoint + Critical News

📊 Checkpoint Analysis:
• Progress: {progress:.1f}% към TP1
• Confidence: {confidence:.0f}%
• Структура: {'Валидна ✅' if not (analysis and analysis.structure_broken) else 'Счупена ❌'}

📰 News:
• {headline}
• Sentiment: {sentiment}
• {impact_assessment}

💡 Combined Assessment като swing trader:

Когато checkpoint analysis + critical news се случат едновременно,
трябва да взема под внимание И двете.

Technical: {'✅ Структурата е OK' if not (analysis and analysis.structure_broken) else '❌ BOS detected'}
Fundamental: {'✅ News подкрепя позицията' if 'подкрепа' in impact_assessment else '⚠️ News е против позицията'}
"""
        
        # Determine action based on combination
        structure_broken = analysis and analysis.structure_broken
        news_contradicts = 'против' in impact_assessment or 'REVERSAL RISK' in impact_assessment
        
        if structure_broken and news_contradicts:
            message += f"""
🔴 DOUBLE RED FLAG - EXIT NOW:

И technical И fundamental са против нас. Това е clear reversal.

ЗАТВАРЯМ 100% СЕГА при {current_price:.2f}

Няма смисъл да се "надявам" когато И structure И news са bearish/bullish
против позицията.
"""
        elif structure_broken or news_contradicts:
            message += f"""
🟡 PARTIAL EXIT:

Имаме един червен флаг ({'technical BOS' if structure_broken else 'contradicting news'}).

Затварям 50-60% СЕГА
SL to breakeven на остатъка
Watch closely за следващите 1-2 hours
"""
        else:
            message += f"""
✅ ЗАДРЪЖАМ:

И technical И fundamental са OK. Position продължава.

Monitoring внимателно заради новината, но засега няма
причина за exit.
"""
        
        message += f"""

Current price: {current_price:.2f}
Watch for: Price reaction, volume, HTF structure
"""
        
        return message


class NarrativeSelector:
    """
    Selects appropriate narrative based on checkpoint analysis
    """
    
    @staticmethod
    def select_narrative(
        position: Dict,
        analysis: Any,
        news_data: Optional[Dict],
        checkpoint: int,
        progress: float,
        current_price: float
    ) -> str:
        """
        Select and generate appropriate narrative
        
        Args:
            position: Position dictionary
            analysis: CheckpointAnalysis object
            news_data: Optional news data
            checkpoint: Checkpoint level
            progress: Current progress
            current_price: Current price
            
        Returns:
            Appropriate Bulgarian narrative
        """
        try:
            # Check for structure break (highest priority)
            if analysis and hasattr(analysis, 'structure_broken') and analysis.structure_broken:
                return SwingTraderNarrative.checkpoint_structure_broken(
                    position, analysis, checkpoint, progress, current_price
                )
            
            # Check for critical news
            has_critical_news = (
                news_data and 
                news_data.get('priority') in ['critical', 'important'] and
                news_data.get('impact_assessment')
            )
            
            # Check for HTF bias change
            has_bias_change = (
                analysis and 
                hasattr(analysis, 'htf_bias_changed') and 
                analysis.htf_bias_changed
            )
            
            # Combined: checkpoint + critical news
            if has_critical_news and (checkpoint in [25, 50, 75, 85]):
                return SwingTraderNarrative.checkpoint_with_critical_news(
                    position, analysis, news_data, checkpoint, progress, 
                    current_price, news_data.get('impact_assessment', '')
                )
            
            # HTF bias changed
            if has_bias_change:
                old_bias = getattr(analysis, 'original_htf_bias', 'UNKNOWN')
                new_bias = getattr(analysis, 'htf_bias', 'UNKNOWN')
                return SwingTraderNarrative.checkpoint_bias_changed(
                    position, analysis, checkpoint, progress, current_price,
                    old_bias, new_bias
                )
            
            # All good scenario
            return SwingTraderNarrative.checkpoint_all_good(
                position, analysis, checkpoint, progress, current_price
            )
            
        except Exception as e:
            logger.error(f"❌ Narrative selection failed: {e}")
            # Fallback to simple message
            return f"""
💎 {checkpoint}% CHECKPOINT - {position['symbol']}

Progress: {progress:.1f}% към TP1

Позицията се развива. Monitoring продължава.
"""
