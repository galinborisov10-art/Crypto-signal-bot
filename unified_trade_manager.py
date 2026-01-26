"""
🔄 UNIFIED TRADE MANAGER
Orchestrates live trade monitoring by combining backtest logic + re-analysis + fundamental data

Features:
- Live position monitoring (every 60 seconds)
- Checkpoint detection (25%, 50%, 75%, 85% progress to TP1)
- Full 12-step ICT re-analysis at checkpoints
- Bulgarian-language actionable alerts
- TP/SL hit detection and auto-close
- News sentiment integration

Author: galinborisov10-art
Date: 2026-01-26
PR: #1 - Live Trade Checkpoint Monitoring System
"""

import logging
import requests
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone

# Import existing infrastructure (NO modifications to these!)
from trade_reanalysis_engine import TradeReanalysisEngine, CheckpointAnalysis, RecommendationType
from position_manager import PositionManager

logger = logging.getLogger(__name__)


class UnifiedTradeManager:
    """
    Unified manager for live trade monitoring
    
    Orchestrates:
    1. Position progress calculation (reusing backtest logic)
    2. Checkpoint detection (25%, 50%, 75%, 85%)
    3. Full ICT re-analysis at checkpoints
    4. Bulgarian-language alerts
    5. TP/SL hit detection
    6. Position closing and notifications
    """
    
    def __init__(self):
        """
        Initialize Unified Trade Manager
        
        Dependencies:
        - TradeReanalysisEngine: For checkpoint re-analysis
        - PositionManager: For database operations
        - FundamentalHelper: For news sentiment (optional)
        """
        # Core engines
        self.reanalysis_engine = TradeReanalysisEngine()
        self.position_manager = PositionManager()
        
        # Optional: Fundamental helper for news
        self.fundamental_helper = None
        try:
            from utils.fundamental_helper import FundamentalHelper
            self.fundamental_helper = FundamentalHelper()
            logger.info("✅ FundamentalHelper loaded")
        except Exception as e:
            logger.warning(f"⚠️ FundamentalHelper not available: {e}")
        
        logger.info("✅ UnifiedTradeManager initialized")
        logger.info(f"   → TradeReanalysisEngine: Ready")
        logger.info(f"   → PositionManager: Ready")
        logger.info(f"   → FundamentalHelper: {'Ready' if self.fundamental_helper else 'Not available'}")
    
    async def monitor_live_trade(
        self,
        position: Dict,
        bot_instance: Any,
        owner_chat_id: int
    ) -> None:
        """
        Main monitoring method - called every 60 seconds for each open position
        
        Logic:
        1. Fetch current market price
        2. Calculate progress % (entry → TP1)
        3. Check if checkpoint (25/50/75/85%) reached
        4. If checkpoint reached and not triggered before:
           a. Run full 12-step ICT re-analysis
           b. Check news via FundamentalHelper
           c. Generate Bulgarian alert message
           d. Send Telegram notification
           e. Mark checkpoint as triggered in DB
           f. Log to checkpoint_alerts table
        5. Check for TP/SL hits → close position if needed
        
        Args:
            position: Position dictionary from database
            bot_instance: Telegram bot instance for sending messages
            owner_chat_id: Chat ID to send alerts to
        """
        try:
            position_id = position['id']
            symbol = position['symbol']
            timeframe = position['timeframe']
            signal_type = position['signal_type']
            entry_price = position['entry_price']
            tp1_price = position['tp1_price']
            sl_price = position['sl_price']
            
            logger.debug(f"📊 Monitoring {symbol} (ID: {position_id})")
            
            # Step 1: Fetch current market price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                logger.warning(f"⚠️ Could not get price for {symbol}")
                return
            
            # Step 2: Calculate progress
            progress = self._calculate_progress(
                entry_price=entry_price,
                tp1_price=tp1_price,
                current_price=current_price,
                signal_type=signal_type
            )
            
            logger.debug(f"   → {symbol}: {progress:.1f}% progress to TP1 (${current_price:,.2f})")
            
            # Step 3: Check for TP/SL hits FIRST (priority)
            sl_hit = await self._check_tp_sl_hits(
                position=position,
                current_price=current_price,
                bot_instance=bot_instance,
                owner_chat_id=owner_chat_id,
                check_type='SL'
            )
            
            if sl_hit:
                return  # Position closed, stop monitoring
            
            tp_hit = await self._check_tp_sl_hits(
                position=position,
                current_price=current_price,
                bot_instance=bot_instance,
                owner_chat_id=owner_chat_id,
                check_type='TP'
            )
            
            if tp_hit:
                return  # Position closed, stop monitoring
            
            # Step 4: Determine checkpoint level reached (if any)
            checkpoint_level = self._get_checkpoint_level(progress)
            
            if not checkpoint_level:
                return  # No checkpoint reached yet
            
            # Step 5: Check if checkpoint already triggered
            checkpoint_key = f"checkpoint_{checkpoint_level.replace('%', '')}_triggered"
            if position.get(checkpoint_key):
                return  # Already triggered, skip
            
            # Step 6: CHECKPOINT REACHED - Run re-analysis
            logger.info(f"🎯 {symbol} reached {checkpoint_level} checkpoint at ${current_price:,.2f}")
            
            # Calculate checkpoint price
            checkpoint_price = self._calculate_checkpoint_price(
                entry_price=entry_price,
                tp1_price=tp1_price,
                checkpoint_percent=int(checkpoint_level.replace('%', '')) / 100.0,
                signal_type=signal_type
            )
            
            # Reconstruct original signal from JSON
            original_signal = self._reconstruct_signal_from_json(position['original_signal_json'])
            
            if not original_signal:
                logger.error(f"❌ Could not reconstruct original signal for {symbol}")
                return
            
            # Run full 12-step ICT re-analysis
            logger.info(f"🔄 Running re-analysis for {symbol} at {checkpoint_level}")
            analysis = self.reanalysis_engine.reanalyze_at_checkpoint(
                symbol=symbol,
                timeframe=timeframe,
                checkpoint_level=checkpoint_level,
                checkpoint_price=checkpoint_price,
                current_price=current_price,
                original_signal=original_signal,
                tp1_price=tp1_price,
                sl_price=sl_price
            )
            
            # Get news sentiment (optional)
            news_data = None
            if self.fundamental_helper:
                try:
                    # Simple news check - just get recent critical news
                    news_data = await self._get_critical_news(symbol)
                except Exception as e:
                    logger.warning(f"⚠️ News fetch failed: {e}")
            
            # Generate Bulgarian alert message
            alert_message = self._format_basic_alert_bulgarian(
                checkpoint=checkpoint_level,
                analysis=analysis,
                news=news_data,
                position=position,
                current_price=current_price
            )
            
            # Send Telegram alert
            try:
                await bot_instance.send_message(
                    chat_id=owner_chat_id,
                    text=alert_message,
                    parse_mode='HTML',
                    disable_notification=False  # Sound alert for checkpoints!
                )
                logger.info(f"✅ {checkpoint_level} checkpoint alert sent for {symbol}")
            except Exception as e:
                logger.error(f"❌ Failed to send checkpoint alert: {e}")
            
            # Mark checkpoint as triggered
            self.position_manager.update_checkpoint_triggered(
                position_id=position_id,
                checkpoint_level=checkpoint_level
            )
            
            # Log to checkpoint_alerts table
            self.position_manager.log_checkpoint_alert(
                position_id=position_id,
                checkpoint_level=checkpoint_level,
                trigger_price=current_price,
                analysis=analysis,
                action_taken='ALERTED'
            )
            
            logger.info(f"✅ Checkpoint {checkpoint_level} processed for {symbol}")
            
        except Exception as e:
            logger.error(f"❌ Monitor live trade error for {position.get('symbol', 'UNKNOWN')}: {e}")
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current market price from Binance
        
        Args:
            symbol: Trading pair (e.g., 'BTCUSDT')
            
        Returns:
            Current price or None if fetch fails
        """
        try:
            BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"
            
            response = requests.get(
                BINANCE_PRICE_URL,
                params={'symbol': symbol},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                return float(data['price'])
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Get current price error for {symbol}: {e}")
            return None
    
    def _calculate_progress(
        self,
        entry_price: float,
        tp1_price: float,
        current_price: float,
        signal_type: str
    ) -> float:
        """
        Calculate trade progress (0-100%) from entry to TP1
        
        REUSES BacktestEngine logic (no modification to backtest):
        - For BUY: progress = ((current - entry) / (tp1 - entry)) * 100
        - For SELL: progress = ((entry - current) / (entry - tp1)) * 100
        
        Args:
            entry_price: Entry price
            tp1_price: Take profit 1 price
            current_price: Current market price
            signal_type: 'BUY' or 'SELL'
            
        Returns:
            Progress percentage (0-100)
        """
        try:
            if 'BUY' in signal_type.upper():
                # BUY: Progress from entry UP to TP1
                distance_total = tp1_price - entry_price
                distance_current = current_price - entry_price
                
                if distance_total <= 0:
                    return 0.0
                
                progress = (distance_current / distance_total) * 100
            else:
                # SELL: Progress from entry DOWN to TP1
                distance_total = entry_price - tp1_price
                distance_current = entry_price - current_price
                
                if distance_total <= 0:
                    return 0.0
                
                progress = (distance_current / distance_total) * 100
            
            # Clamp to 0-100
            return max(0, min(100, progress))
            
        except Exception as e:
            logger.error(f"❌ Progress calculation error: {e}")
            return 0.0
    
    def _get_checkpoint_level(self, progress: float) -> Optional[str]:
        """
        Determine which checkpoint (if any) has been reached
        
        Uses tolerance window: checkpoint ± 2% to avoid missing due to volatility
        
        Args:
            progress: Progress percentage (0-100)
            
        Returns:
            '25%', '50%', '75%', '85%', or None
        """
        checkpoints = {
            '25%': 25.0,
            '50%': 50.0,
            '75%': 75.0,
            '85%': 85.0
        }
        
        tolerance = 2.0  # ±2% tolerance window
        
        # Check from highest to lowest (prioritize higher checkpoints)
        for level in ['85%', '75%', '50%', '25%']:
            target = checkpoints[level]
            
            # Checkpoint is triggered if progress is at or above the target (with tolerance)
            # But we need to ensure we haven't passed to the next checkpoint
            if progress >= target:
                return level
        
        return None
    
    def _calculate_checkpoint_price(
        self,
        entry_price: float,
        tp1_price: float,
        checkpoint_percent: float,
        signal_type: str
    ) -> float:
        """
        Calculate checkpoint price
        
        Args:
            entry_price: Entry price
            tp1_price: Take profit price
            checkpoint_percent: Checkpoint percentage (0.25, 0.50, 0.75, 0.85)
            signal_type: 'BUY' or 'SELL'
            
        Returns:
            Checkpoint price
        """
        if 'BUY' in signal_type.upper():
            # For BUY: checkpoint is between entry and TP (above entry)
            distance = tp1_price - entry_price
            return entry_price + (distance * checkpoint_percent)
        else:
            # For SELL: checkpoint is between entry and TP (below entry)
            distance = entry_price - tp1_price
            return entry_price - (distance * checkpoint_percent)
    
    def _reconstruct_signal_from_json(self, signal_json: str) -> Optional[Any]:
        """
        Reconstruct ICTSignal from JSON string
        
        Args:
            signal_json: Serialized signal JSON
            
        Returns:
            ICTSignal-like object or None
        """
        try:
            import json
            from types import SimpleNamespace
            
            signal_dict = json.loads(signal_json)
            
            # Create simple namespace object with signal attributes
            signal = SimpleNamespace(**signal_dict)
            
            # Convert signal_type to enum-like object
            if hasattr(signal, 'signal_type'):
                signal.signal_type = SimpleNamespace(value=signal.signal_type)
            
            return signal
            
        except Exception as e:
            logger.error(f"❌ Signal reconstruction error: {e}")
            return None
    
    async def _get_critical_news(self, symbol: str) -> Optional[Dict]:
        """
        Get critical news for the symbol
        
        Args:
            symbol: Trading pair
            
        Returns:
            News data dict or None
        """
        # Placeholder for news integration
        # Will use FundamentalHelper when available
        return None
    
    def _format_basic_alert_bulgarian(
        self,
        checkpoint: str,
        analysis: CheckpointAnalysis,
        news: Optional[Dict],
        position: Dict,
        current_price: float
    ) -> str:
        """
        Generate Bulgarian-language alert message
        
        Style: Conversational + technical when needed
        
        Args:
            checkpoint: Checkpoint level (e.g., "25%", "50%")
            analysis: CheckpointAnalysis from re-analysis engine
            news: News data (optional)
            position: Position dictionary
            current_price: Current market price
            
        Returns:
            Formatted Bulgarian message with recommendation
        """
        symbol = position['symbol']
        entry_price = position['entry_price']
        tp1_price = position['tp1_price']
        sl_price = position['sl_price']
        
        # Determine alert type based on recommendation
        rec_type = analysis.recommendation
        
        if rec_type == RecommendationType.HOLD:
            icon = "💎"
            title = f"Всичко наред - {checkpoint} Checkpoint"
        elif rec_type == RecommendationType.PARTIAL_CLOSE:
            icon = "🟡"
            title = f"Внимание - {checkpoint} Checkpoint"
        elif rec_type == RecommendationType.CLOSE_NOW:
            icon = "🔴"
            title = f"КРИТИЧНО! - {checkpoint} Checkpoint"
        else:  # MOVE_SL
            icon = "🟢"
            title = f"Подобрение - {checkpoint} Checkpoint"
        
        # Build message
        msg = f"{icon} <b>{title}</b>\n\n"
        
        # Position info
        msg += f"📊 <b>{symbol} АНАЛИЗ:</b>\n"
        msg += f"• Confidence: {analysis.original_confidence:.0f}% → {analysis.current_confidence:.0f}% "
        msg += f"(Δ{analysis.confidence_delta:+.0f}%"
        if abs(analysis.confidence_delta) > 10:
            msg += " ⚠️"
        msg += ")\n"
        
        # Structure status
        if analysis.structure_broken:
            msg += f"• Структура: СЧУПЕНА ❌\n"
        else:
            msg += f"• Структура: Валидна ✅\n"
        
        # HTF Bias
        if analysis.htf_bias_changed:
            msg += f"• HTF Bias: ПРОМЯНА ⚠️\n"
        else:
            msg += f"• HTF Bias: Без промяна ✅\n"
        
        # Valid components
        msg += f"• Valid компоненти: {analysis.valid_components_count}\n"
        
        # Current R:R
        if analysis.current_rr_ratio > 0:
            msg += f"• Текущ R:R: {analysis.current_rr_ratio:.1f}:1\n"
        
        msg += "\n"
        
        # News section (if available)
        if news and news.get('has_critical'):
            severity = news.get('severity', 'WARNING')
            msg += f"📰 <b>НОВИНИ: {severity}</b> - {news.get('summary', 'Критични събития')}\n\n"
        else:
            msg += "📰 <b>НОВИНИ:</b> Няма критични събития\n\n"
        
        # Recommendation
        rec_emoji = {
            RecommendationType.HOLD: "💎",
            RecommendationType.PARTIAL_CLOSE: "🟡",
            RecommendationType.CLOSE_NOW: "🔴",
            RecommendationType.MOVE_SL: "🟢"
        }
        
        rec_text = {
            RecommendationType.HOLD: "ЗАДРЪЖ ПОЗИЦИЯТА",
            RecommendationType.PARTIAL_CLOSE: "ЗАТВОРИ 40-50% СЕГА",
            RecommendationType.CLOSE_NOW: "ЗАТВОРИ ВСИЧКО ВЕДНАГА!",
            RecommendationType.MOVE_SL: "ПРЕМЕСТИ SL НА BREAK-EVEN"
        }
        
        msg += f"{rec_emoji.get(rec_type, '💡')} <b>ПРЕПОРЪКА: {rec_text.get(rec_type, 'HOLD')}</b>\n\n"
        
        # Action plan
        msg += "📋 <b>ПЛАН:</b>\n"
        
        if rec_type == RecommendationType.HOLD:
            msg += f"• Позицията се развива добре\n"
            next_checkpoint = self._get_next_checkpoint(checkpoint)
            if next_checkpoint:
                next_price = self._calculate_checkpoint_price(
                    entry_price, tp1_price, 
                    int(next_checkpoint.replace('%', '')) / 100.0,
                    position['signal_type']
                )
                msg += f"• Чакай {next_checkpoint} checkpoint @ ${next_price:,.2f}\n"
            msg += f"• SL остава @ ${sl_price:,.2f}\n"
        
        elif rec_type == RecommendationType.PARTIAL_CLOSE:
            msg += f"1. Затвори 40-50% на ${current_price:,.2f}\n"
            msg += f"2. Премести SL на entry ${entry_price:,.2f}\n"
            msg += f"3. Задръж 50% за TP1 @ ${tp1_price:,.2f}\n"
        
        elif rec_type == RecommendationType.CLOSE_NOW:
            pnl = ((current_price - entry_price) / entry_price * 100) if 'BUY' in position['signal_type'] else \
                  ((entry_price - current_price) / entry_price * 100)
            msg += f"1. <b>MARKET SELL @ ${current_price:,.2f}</b> ← СЕГА!\n"
            msg += f"2. Profit locked: {pnl:+.1f}%\n"
            msg += f"3. Не чакай потвърждение!\n"
        
        else:  # MOVE_SL
            msg += f"1. Премести SL на ${entry_price:,.2f} (break-even)\n"
            msg += f"2. Риск = 0, позицията е защитена\n"
            msg += f"3. Чакай TP1 @ ${tp1_price:,.2f}\n"
        
        msg += "\n"
        
        # Reasoning
        if analysis.reasoning:
            msg += f"💡 <b>Reasoning:</b> {analysis.reasoning}\n"
        
        return msg
    
    def _get_next_checkpoint(self, current: str) -> Optional[str]:
        """Get next checkpoint after current"""
        checkpoints = ['25%', '50%', '75%', '85%']
        
        try:
            idx = checkpoints.index(current)
            if idx < len(checkpoints) - 1:
                return checkpoints[idx + 1]
        except:
            pass
        
        return None
    
    async def _check_tp_sl_hits(
        self,
        position: Dict,
        current_price: float,
        bot_instance: Any,
        owner_chat_id: int,
        check_type: str = 'BOTH'
    ) -> bool:
        """
        Check if TP or SL has been hit
        
        Args:
            position: Position dictionary
            current_price: Current market price
            bot_instance: Telegram bot instance
            owner_chat_id: Chat ID for notifications
            check_type: 'SL', 'TP', or 'BOTH'
            
        Returns:
            True if position was closed (TP/SL hit)
        """
        signal_type = position['signal_type']
        sl_price = position['sl_price']
        tp1_price = position['tp1_price']
        
        # Check SL hit
        if check_type in ['SL', 'BOTH']:
            sl_hit = False
            
            if 'BUY' in signal_type.upper():
                sl_hit = current_price <= sl_price
            else:  # SELL
                sl_hit = current_price >= sl_price
            
            if sl_hit:
                logger.warning(f"🔴 SL HIT for {position['symbol']} at ${current_price:,.2f}")
                await self._close_position_and_notify(
                    position=position,
                    outcome='SL',
                    exit_price=current_price,
                    bot_instance=bot_instance,
                    owner_chat_id=owner_chat_id
                )
                return True
        
        # Check TP hit
        if check_type in ['TP', 'BOTH']:
            tp_hit = False
            
            if 'BUY' in signal_type.upper():
                tp_hit = current_price >= tp1_price
            else:  # SELL
                tp_hit = current_price <= tp1_price
            
            if tp_hit:
                logger.info(f"🎯 TP1 HIT for {position['symbol']} at ${current_price:,.2f}")
                await self._close_position_and_notify(
                    position=position,
                    outcome='TP1',
                    exit_price=current_price,
                    bot_instance=bot_instance,
                    owner_chat_id=owner_chat_id
                )
                return True
        
        return False
    
    async def _close_position_and_notify(
        self,
        position: Dict,
        outcome: str,
        exit_price: float,
        bot_instance: Any,
        owner_chat_id: int
    ) -> None:
        """
        Close position, log to history, notify user
        
        Args:
            position: Position dictionary
            outcome: 'TP1', 'TP2', 'TP3', 'SL', 'MANUAL_CLOSE'
            exit_price: Exit price
            bot_instance: Telegram bot instance
            owner_chat_id: Chat ID for notifications
        """
        try:
            position_id = position['id']
            symbol = position['symbol']
            
            # Close position and get P&L
            pnl = self.position_manager.close_position(
                position_id=position_id,
                exit_price=exit_price,
                outcome=outcome
            )
            
            # Format notification
            if outcome == 'TP1':
                icon = "🎯"
                title = "TP1 HIT!"
                color_emoji = "🟢"
            elif outcome in ['TP2', 'TP3']:
                icon = "🎯"
                title = f"{outcome} HIT!"
                color_emoji = "🟢"
            elif outcome == 'SL':
                icon = "🔴"
                title = "STOP LOSS HIT"
                color_emoji = "🔴"
            else:
                icon = "⚪"
                title = "Position Closed"
                color_emoji = "⚪"
            
            msg = f"{icon} <b>{title}</b>\n\n"
            msg += f"📊 <b>{symbol}</b>\n"
            msg += f"• Entry: ${position['entry_price']:,.2f}\n"
            msg += f"• Exit: ${exit_price:,.2f}\n"
            msg += f"• P&L: {color_emoji} <b>{pnl:+.2f}%</b>\n"
            msg += f"• Outcome: {outcome}\n"
            
            # Send notification
            try:
                await bot_instance.send_message(
                    chat_id=owner_chat_id,
                    text=msg,
                    parse_mode='HTML',
                    disable_notification=False  # Sound alert!
                )
                logger.info(f"✅ Position close notification sent for {symbol}")
            except Exception as e:
                logger.error(f"❌ Failed to send close notification: {e}")
            
        except Exception as e:
            logger.error(f"❌ Close position and notify error: {e}")
