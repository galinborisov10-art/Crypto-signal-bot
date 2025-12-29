"""
Real-time Position Monitor for Telegram Deep Integration
Monitors live trading signals and sends alerts at 80% TP and final outcomes

Features:
- Tracks all active signals per user
- Monitors price every 30 seconds
- Triggers 80% TP alerts (75-85% range) using ICT80AlertHandler
- Sends final WIN/LOSS notifications
- Integrates with existing signal tracking system
"""

import asyncio
import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import requests
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

# Alert stage thresholds
ALERT_STAGES = {
    'early': (0, 25),        # 0-25%: Only critical changes
    'halfway': (25, 50),     # 25-50%: Halfway alert ✅
    'approaching': (50, 75), # 50-75%: Approaching target
    'eighty_pct': (75, 85),  # 75-85%: 80% TP alert (existing)
    'final': (85, 100),      # 85-100%: Final phase
}


class RealTimePositionMonitor:
    """
    Real-time monitoring of live trading positions
    Sends Telegram alerts at 80% TP and final outcomes
    """
    
    def __init__(
        self,
        bot: Bot,
        ict_80_handler,
        owner_chat_id: int,
        binance_price_url: str,
        binance_klines_url: str
    ):
        """
        Initialize real-time monitor
        
        Args:
            bot: Telegram Bot instance
            ict_80_handler: ICT80AlertHandler instance for re-analysis
            owner_chat_id: Owner's Telegram chat ID
            binance_price_url: Binance API endpoint for price
            binance_klines_url: Binance API endpoint for klines
        """
        self.bot = bot
        self.ict_80_handler = ict_80_handler
        self.owner_chat_id = owner_chat_id
        self.binance_price_url = binance_price_url
        self.binance_klines_url = binance_klines_url
        self.monitoring = False
        self.monitored_signals: Dict[str, Dict] = {}  # signal_id -> signal_data
        
    def add_signal(
        self,
        signal_id: str,
        symbol: str,
        signal_type: str,
        entry_price: float,
        tp_price: float,
        sl_price: float,
        confidence: float,
        timeframe: str,
        user_chat_id: int = None
    ) -> None:
        """
        Add signal to real-time monitoring
        
        Args:
            signal_id: Unique signal identifier
            symbol: Trading symbol (e.g., BTCUSDT)
            signal_type: BUY or SELL
            entry_price: Entry price
            tp_price: Take profit target
            sl_price: Stop loss price
            confidence: Signal confidence (0-100)
            timeframe: Trading timeframe
            user_chat_id: User's chat ID (defaults to owner)
        """
        # ✅ Skip HOLD signals from monitoring
        if signal_type == 'HOLD':
            logger.info("ℹ️ Skipping HOLD signal from monitor")
            return
        
        if user_chat_id is None:
            user_chat_id = self.owner_chat_id
        
        # Generate unique Trade ID
        try:
            from utils.trade_id_generator import TradeIDGenerator
            trade_id = TradeIDGenerator.generate(symbol, timeframe)
        except Exception as e:
            logger.warning(f"Could not generate trade ID: {e}, using fallback")
            trade_id = f"#{symbol}-{signal_id[:8]}"
        
        self.monitored_signals[signal_id] = {
            # NEW: Trade identification
            'trade_id': trade_id,
            'opened_at': datetime.now(timezone.utc),
            'last_alerted_stage': None,
            
            # EXISTING: Signal data
            'symbol': symbol,
            'signal_type': signal_type,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'confidence': confidence,
            'timeframe': timeframe,
            'user_chat_id': user_chat_id,
            'timestamp': datetime.now(timezone.utc),
            
            # EXISTING: Alert tracking
            'tp_80_alerted': False,
            'result_sent': False,
            'last_checked': None
        }
        
        logger.info(f"📊 Signal {signal_id} ({trade_id}) added to real-time monitor")
        
    def remove_signal(self, signal_id: str) -> None:
        """Remove signal from monitoring"""
        if signal_id in self.monitored_signals:
            del self.monitored_signals[signal_id]
            logger.info(f"🗑️ Signal {signal_id} removed from monitor")
            
    async def start_monitoring(self) -> None:
        """Start the real-time monitoring loop (runs every 30 seconds)"""
        self.monitoring = True
        logger.info("🎯 Real-time position monitor STARTED")
        
        while self.monitoring:
            try:
                await self._check_all_signals()
            except Exception as e:
                logger.error(f"❌ Error in monitoring loop: {e}")
            
            # Wait 30 seconds before next check
            await asyncio.sleep(30)
            
    def stop_monitoring(self) -> None:
        """Stop the monitoring loop"""
        self.monitoring = False
        logger.info("🛑 Real-time position monitor STOPPED")
        
    async def _check_all_signals(self) -> None:
        """Check all monitored signals"""
        if not self.monitored_signals:
            return
            
        signals_to_remove = []
        
        for signal_id, signal in self.monitored_signals.items():
            try:
                # Skip already completed signals
                if signal.get('result_sent', False):
                    signals_to_remove.append(signal_id)
                    continue
                
                # Get current price
                current_price = await self._fetch_current_price(signal['symbol'])
                
                if current_price is None:
                    logger.warning(f"⚠️ Could not fetch price for {signal['symbol']}")
                    continue
                
                # Update last checked time
                signal['last_checked'] = datetime.now(timezone.utc)
                
                # Calculate progress to TP
                progress_pct = self._calculate_progress(
                    signal['signal_type'],
                    signal['entry_price'],
                    current_price,
                    signal['tp_price']
                )
                
                # Check if SL hit
                sl_hit = self._check_sl_hit(
                    signal['signal_type'],
                    current_price,
                    signal['sl_price']
                )
                
                # Check if TP hit
                tp_hit = self._check_tp_hit(
                    signal['signal_type'],
                    current_price,
                    signal['tp_price']
                )
                
                # Handle SL hit (PRIORITY - check first)
                if sl_hit and not signal.get('result_sent', False):
                    await self._send_loss_alert(signal_id, signal, current_price)
                    signal['result_sent'] = True
                    signals_to_remove.append(signal_id)
                    
                # Handle TP hit (PRIORITY - check second)
                elif tp_hit and not signal.get('result_sent', False):
                    await self._send_win_alert(signal_id, signal, current_price)
                    signal['result_sent'] = True
                    signals_to_remove.append(signal_id)
                
                # Handle 80% TP alert (75-85% range) - EXISTING ALERT
                elif not signal.get('tp_80_alerted', False) and 75 <= progress_pct <= 85:
                    await self._send_80_percent_alert(signal_id, signal, current_price, progress_pct)
                    signal['tp_80_alerted'] = True
                
                # NEW: Multi-stage alerts (only if feature enabled and no terminal state)
                elif not signal.get('result_sent', False):
                    if self._is_multi_stage_enabled():
                        await self._check_stage_alerts(signal_id, signal, current_price, progress_pct)
                    
            except Exception as e:
                logger.error(f"❌ Error checking signal {signal_id}: {e}")
                
        # Remove completed signals
        for signal_id in signals_to_remove:
            self.remove_signal(signal_id)
            
    async def _fetch_current_price(self, symbol: str) -> Optional[float]:
        """Fetch current price from Binance (async)"""
        try:
            import asyncio
            # Use asyncio.to_thread to run sync request in thread pool
            response = await asyncio.to_thread(
                requests.get,
                self.binance_price_url,
                params={'symbol': symbol},
                timeout=5
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Handle list or dict response
                if isinstance(data, list):
                    data = next((s for s in data if s['symbol'] == symbol), None)
                    
                if data:
                    return float(data['price'])
                    
        except Exception as e:
            logger.error(f"❌ Error fetching price for {symbol}: {e}")
            
        return None
        
    async def _fetch_klines(self, symbol: str, timeframe: str, limit: int = 100) -> Optional[List]:
        """Fetch klines data from Binance (async)"""
        try:
            import asyncio
            # Use asyncio.to_thread to run sync request in thread pool
            response = await asyncio.to_thread(
                requests.get,
                self.binance_klines_url,
                params={
                    'symbol': symbol,
                    'interval': timeframe,
                    'limit': limit
                },
                timeout=10
            )
            
            if response.status_code == 200:
                return response.json()
                
        except Exception as e:
            logger.error(f"❌ Error fetching klines for {symbol}: {e}")
            
        return None
        
    def _calculate_progress(
        self,
        signal_type: str,
        entry_price: float,
        current_price: float,
        tp_price: float
    ) -> float:
        """Calculate progress percentage towards TP"""
        if signal_type == 'BUY':
            if tp_price <= entry_price:
                return 0
            progress = ((current_price - entry_price) / (tp_price - entry_price)) * 100
        else:  # SELL
            if entry_price <= tp_price:
                return 0
            progress = ((entry_price - current_price) / (entry_price - tp_price)) * 100
            
        return max(0, min(100, progress))
        
    def _check_sl_hit(
        self,
        signal_type: str,
        current_price: float,
        sl_price: float
    ) -> bool:
        """Check if stop loss was hit"""
        if signal_type == 'BUY':
            return current_price <= sl_price
        else:  # SELL
            return current_price >= sl_price
            
    def _check_tp_hit(
        self,
        signal_type: str,
        current_price: float,
        tp_price: float
    ) -> bool:
        """Check if take profit was hit"""
        if signal_type == 'BUY':
            return current_price >= tp_price
        else:  # SELL
            return current_price <= tp_price
            
    def _calculate_profit_pct(
        self,
        signal_type: str,
        entry_price: float,
        current_price: float
    ) -> float:
        """Calculate profit/loss percentage"""
        if signal_type == 'BUY':
            return ((current_price - entry_price) / entry_price) * 100
        else:  # SELL
            return ((entry_price - current_price) / entry_price) * 100
            
    async def _send_80_percent_alert(
        self,
        signal_id: str,
        signal: Dict,
        current_price: float,
        progress_pct: float
    ) -> None:
        """Send 80% TP alert with ICT re-analysis"""
        try:
            logger.info(f"🎯 Sending 80% TP alert for {signal_id}")
            
            # Fetch fresh klines for ICT re-analysis
            klines = await self._fetch_klines(
                signal['symbol'],
                signal['timeframe'],
                limit=100
            )
            
            # Perform ICT re-analysis using ICT80AlertHandler
            recommendation = {'recommendation': 'PARTIAL_CLOSE', 'confidence': 0, 'reasoning': 'No ICT analysis available'}
            
            if klines and self.ict_80_handler:
                recommendation = await self.ict_80_handler.analyze_position(
                    symbol=signal['symbol'],
                    timeframe=signal['timeframe'],
                    signal_type=signal['signal_type'],
                    entry_price=signal['entry_price'],
                    tp_price=signal['tp_price'],
                    current_price=current_price,
                    original_confidence=signal['confidence'],
                    klines=klines
                )
            
            # Format alert message
            emoji_map = {
                'HOLD': '💎',
                'PARTIAL_CLOSE': '⚠️',
                'CLOSE_NOW': '❌'
            }
            
            action = recommendation.get('recommendation', 'PARTIAL_CLOSE')
            emoji = emoji_map.get(action, '⚠️')
            
            signal_emoji = '🟢' if signal['signal_type'] == 'BUY' else '🔴'
            
            profit_pct = self._calculate_profit_pct(
                signal['signal_type'],
                signal['entry_price'],
                current_price
            )
            
            message = f"""🎯 <b>80% TP ALERT!</b> {emoji}

{signal_emoji} <b>{signal['symbol']}</b> - {signal['signal_type']}
⏰ <b>Timeframe:</b> {signal['timeframe']}

📊 <b>Progress:</b> {progress_pct:.1f}% to TP
💰 <b>Current Profit:</b> {profit_pct:+.2f}%

💵 <b>Prices:</b>
   Entry: ${signal['entry_price']:,.4f}
   Current: ${current_price:,.4f}
   TP Target: ${signal['tp_price']:,.4f}

🎯 <b>ICT RE-ANALYSIS:</b>
<b>Recommendation:</b> {action} {emoji}
<b>New Confidence:</b> {recommendation.get('confidence', 0):.1f}%

📝 <b>Reasoning:</b>
{recommendation.get('reasoning', 'No analysis available')}

⚖️ <b>Scores:</b>
   HOLD: {recommendation.get('score_hold', 0)} points
   CLOSE: {recommendation.get('score_close', 0)} points
"""
            
            if recommendation.get('warnings'):
                message += f"\n⚠️ <b>Warnings:</b>\n"
                for warning in recommendation['warnings']:
                    message += f"   • {warning}\n"
            
            # Send alert
            await self.bot.send_message(
                chat_id=signal['user_chat_id'],
                text=message,
                parse_mode='HTML',
                disable_notification=False  # WITH SOUND
            )
            
            logger.info(f"✅ 80% TP alert sent for {signal_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending 80% alert for {signal_id}: {e}")
            
    async def _send_win_alert(
        self,
        signal_id: str,
        signal: Dict,
        current_price: float
    ) -> None:
        """Send WIN alert when TP is reached"""
        try:
            profit_pct = self._calculate_profit_pct(
                signal['signal_type'],
                signal['entry_price'],
                current_price
            )
            
            signal_emoji = '🟢' if signal['signal_type'] == 'BUY' else '🔴'
            
            message = f"""🎉 <b>WIN! TARGET REACHED!</b> 🎉

{signal_emoji} <b>{signal['symbol']}</b> - {signal['signal_type']}
⏰ <b>Timeframe:</b> {signal['timeframe']}

💰 <b>PROFIT:</b> {profit_pct:+.2f}%

💵 <b>Prices:</b>
   Entry: ${signal['entry_price']:,.4f}
   Exit: ${current_price:,.4f}
   Target: ${signal['tp_price']:,.4f}

📊 <b>Original Confidence:</b> {signal['confidence']:.1f}%

✅ <b>Trade closed successfully at TP!</b>
"""
            
            await self.bot.send_message(
                chat_id=signal['user_chat_id'],
                text=message,
                parse_mode='HTML',
                disable_notification=False  # WITH SOUND
            )
            
            logger.info(f"🎉 WIN alert sent for {signal_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending WIN alert for {signal_id}: {e}")
            
    async def _send_loss_alert(
        self,
        signal_id: str,
        signal: Dict,
        current_price: float
    ) -> None:
        """Send LOSS alert when SL is hit"""
        try:
            loss_pct = self._calculate_profit_pct(
                signal['signal_type'],
                signal['entry_price'],
                current_price
            )
            
            signal_emoji = '🟢' if signal['signal_type'] == 'BUY' else '🔴'
            
            message = f"""❌ <b>LOSS - STOP LOSS HIT</b> ❌

{signal_emoji} <b>{signal['symbol']}</b> - {signal['signal_type']}
⏰ <b>Timeframe:</b> {signal['timeframe']}

💔 <b>LOSS:</b> {loss_pct:+.2f}%

💵 <b>Prices:</b>
   Entry: ${signal['entry_price']:,.4f}
   Exit: ${current_price:,.4f}
   Stop Loss: ${signal['sl_price']:,.4f}

📊 <b>Original Confidence:</b> {signal['confidence']:.1f}%

⚠️ <b>Trade closed at Stop Loss</b>
"""
            
            await self.bot.send_message(
                chat_id=signal['user_chat_id'],
                text=message,
                parse_mode='HTML',
                disable_notification=False  # WITH SOUND
            )
            
            logger.info(f"❌ LOSS alert sent for {signal_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending LOSS alert for {signal_id}: {e}")
    
    # ===== NEW: MULTI-STAGE ALERT SYSTEM =====
    
    def _is_multi_stage_enabled(self) -> bool:
        """Check if multi-stage alerts are enabled via feature flags"""
        try:
            with open('config/feature_flags.json') as f:
                flags = json.load(f)
            fundamental = flags.get('fundamental_analysis', {})
            return fundamental.get('multi_stage_alerts', False)
        except Exception as e:
            logger.warning(f"Could not read feature flags: {e}")
            return False
    
    async def _check_stage_alerts(self, signal_id: str, signal: Dict, current_price: float, progress_pct: float) -> None:
        """Check and send multi-stage alerts based on progress"""
        try:
            current_stage = self._get_stage(progress_pct)
            last_stage = signal.get('last_alerted_stage')
            
            # Only alert for NEW stages (avoid duplicate alerts)
            # Skip 'early' (no alert unless critical) and 'eighty_pct' (handled by existing method)
            if current_stage != last_stage and current_stage not in ['early', 'eighty_pct']:
                
                if current_stage == 'halfway':
                    await self._send_halfway_alert(signal_id, signal, current_price, progress_pct)
                elif current_stage == 'approaching':
                    await self._send_approaching_alert(signal_id, signal, current_price, progress_pct)
                elif current_stage == 'final':
                    await self._send_final_phase_alert(signal_id, signal, current_price, progress_pct)
                
                # Update last alerted stage
                signal['last_alerted_stage'] = current_stage
                
        except Exception as e:
            logger.error(f"Error in multi-stage alert check for {signal_id}: {e}")
    
    def _get_stage(self, progress_pct: float) -> str:
        """Determine current stage based on progress percentage"""
        for stage_name, (min_pct, max_pct) in ALERT_STAGES.items():
            if min_pct <= progress_pct < max_pct:
                return stage_name
        if progress_pct >= 100:
            return 'completed'
        return 'early'
    
    async def _send_halfway_alert(self, signal_id: str, signal: Dict, current_price: float, progress_pct: float) -> None:
        """Send halfway (25-50%) progress alert"""
        try:
            logger.info(f"🔄 Sending halfway alert for {signal_id}")
            
            # Fetch fresh klines for ICT re-analysis
            klines = await self._fetch_klines(
                signal['symbol'],
                signal['timeframe'],
                limit=100
            )
            
            # Perform ICT re-analysis
            recommendation = {'recommendation': 'HOLD', 'confidence': 0, 'reasoning': 'Няма налична ICT информация'}
            
            if klines and self.ict_80_handler:
                recommendation = await self.ict_80_handler.analyze_position(
                    symbol=signal['symbol'],
                    timeframe=signal['timeframe'],
                    signal_type=signal['signal_type'],
                    entry_price=signal['entry_price'],
                    tp_price=signal['tp_price'],
                    current_price=current_price,
                    original_confidence=signal['confidence'],
                    klines=klines
                )
            
            # Format and send message
            message = self._format_halfway_message(signal, current_price, progress_pct, recommendation)
            
            await self.bot.send_message(
                chat_id=signal['user_chat_id'],
                text=message,
                parse_mode='HTML',
                reply_markup=self._get_stage_buttons(signal_id),
                disable_notification=False
            )
            
            logger.info(f"✅ Halfway alert sent for {signal_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending halfway alert for {signal_id}: {e}")
    
    async def _send_approaching_alert(self, signal_id: str, signal: Dict, current_price: float, progress_pct: float) -> None:
        """Send approaching target (50-75%) progress alert"""
        try:
            logger.info(f"🎯 Sending approaching target alert for {signal_id}")
            
            # Fetch fresh klines for ICT re-analysis
            klines = await self._fetch_klines(
                signal['symbol'],
                signal['timeframe'],
                limit=100
            )
            
            # Perform ICT re-analysis
            recommendation = {'recommendation': 'HOLD', 'confidence': 0, 'reasoning': 'Няма налична ICT информация'}
            
            if klines and self.ict_80_handler:
                recommendation = await self.ict_80_handler.analyze_position(
                    symbol=signal['symbol'],
                    timeframe=signal['timeframe'],
                    signal_type=signal['signal_type'],
                    entry_price=signal['entry_price'],
                    tp_price=signal['tp_price'],
                    current_price=current_price,
                    original_confidence=signal['confidence'],
                    klines=klines
                )
            
            # Format and send message
            message = self._format_approaching_message(signal, current_price, progress_pct, recommendation)
            
            await self.bot.send_message(
                chat_id=signal['user_chat_id'],
                text=message,
                parse_mode='HTML',
                reply_markup=self._get_stage_buttons(signal_id),
                disable_notification=False
            )
            
            logger.info(f"✅ Approaching alert sent for {signal_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending approaching alert for {signal_id}: {e}")
    
    async def _send_final_phase_alert(self, signal_id: str, signal: Dict, current_price: float, progress_pct: float) -> None:
        """Send final phase (85-100%) progress alert"""
        try:
            logger.info(f"🚀 Sending final phase alert for {signal_id}")
            
            profit_pct = self._calculate_profit_pct(
                signal['signal_type'],
                signal['entry_price'],
                current_price
            )
            
            signal_emoji = '🟢' if signal['signal_type'] == 'BUY' else '🔴'
            
            # Calculate duration
            opened_at = signal.get('opened_at', signal.get('timestamp'))
            duration = datetime.now(timezone.utc) - opened_at
            hours = int(duration.total_seconds() // 3600)
            minutes = int((duration.total_seconds() % 3600) // 60)
            duration_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
            
            # Calculate distance to TP
            if signal['signal_type'] == 'BUY':
                distance_to_tp = signal['tp_price'] - current_price
            else:
                distance_to_tp = current_price - signal['tp_price']
            
            distance_pct = (distance_to_tp / signal['entry_price']) * 100
            
            message = f"""<b>🚀 ФИНАЛНА ФАЗА! Близо до целта!</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ТРЕЙД: {signal.get('trade_id', 'N/A')}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{signal_emoji} <b>{signal['symbol']} - {signal['signal_type']}</b>
⏰ Времева рамка: {signal['timeframe']}
📅 Отворен: {opened_at.strftime('%d.%m.%Y %H:%M')}
⏱️ Активен: {duration_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Текуща печалба:</b> {profit_pct:+.2f}%
📊 <b>Прогрес:</b> {progress_pct:.1f}% до целта
📍 <b>Остава:</b> {distance_pct:.2f}% до TP

💵 <b>Цени:</b>
   Вход: ${signal['entry_price']:,.2f}
   Сега: ${current_price:,.2f}
   Цел (TP): ${signal['tp_price']:,.2f}
   SL: ${signal['sl_price']:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

⚠️ <b>ВНИМАНИЕ:</b>
• Следи за ликвидност около ${signal['tp_price']:,.2f}
• Голяма вероятност за удар на целта!
• Размисли за затягане на SL към БЕП

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Продължавам да следя всяка секунда...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            await self.bot.send_message(
                chat_id=signal['user_chat_id'],
                text=message,
                parse_mode='HTML',
                disable_notification=False
            )
            
            logger.info(f"✅ Final phase alert sent for {signal_id}")
            
        except Exception as e:
            logger.error(f"❌ Error sending final phase alert for {signal_id}: {e}")
    
    def _format_halfway_message(self, signal: Dict, current_price: float, progress_pct: float, recommendation: Dict) -> str:
        """Format halfway alert message in Bulgarian"""
        
        profit_pct = self._calculate_profit_pct(
            signal['signal_type'],
            signal['entry_price'],
            current_price
        )
        
        direction_emoji = '🟢' if signal['signal_type'] == 'BUY' else '🔴'
        
        # Calculate duration
        opened_at = signal.get('opened_at', signal.get('timestamp'))
        duration = datetime.now(timezone.utc) - opened_at
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        duration_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
        
        rec_emoji = {
            'HOLD': '💎',
            'PARTIAL_CLOSE': '🟡',
            'CLOSE_NOW': '❌'
        }.get(recommendation.get('recommendation', 'HOLD'), '⚠️')
        
        rec_action = recommendation.get('recommendation', 'HOLD')
        
        message = f"""<b>{'💎 ПОЛОВИН ПЪТ! Всичко е наред!' if rec_action == 'HOLD' else '🟡 ПОЛОВИН ПЪТ! Отслабване забелязано'}</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ТРЕЙД: {signal.get('trade_id', 'N/A')}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{direction_emoji} <b>{signal['symbol']} - {signal['signal_type']}</b>
⏰ Времева рамка: {signal['timeframe']}
📅 Отворен: {opened_at.strftime('%d.%m.%Y %H:%M')}
⏱️ Активен: {duration_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Текуща печалба:</b> {profit_pct:+.2f}%
📊 <b>Прогрес:</b> {progress_pct:.1f}% до целта

💵 <b>Цени:</b>
   Вход: ${signal['entry_price']:,.2f}
   Сега: ${current_price:,.2f}
   Цел (TP): ${signal['tp_price']:,.2f}
   SL: ${signal['sl_price']:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>{'✅' if rec_action == 'HOLD' else '⚠️'} ICT ПРОВЕРКА:</b>
{recommendation.get('reasoning', 'Няма налична информация')}

🎲 <b>ИЗЧИСЛЕНА ВЕРОЯТНОСТ:</b> {recommendation.get('confidence', 0):.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>ПРЕПОРЪКА: {rec_action} {rec_emoji}</b>

{'Има отлична вероятност да удариш целта. Продължавам да следя непрекъснато.' if rec_action == 'HOLD' else 'Има признаци на отслабване. Размисли за вземане на частична печалба.'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Следваща проверка след 2 минути...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return message
    
    def _format_approaching_message(self, signal: Dict, current_price: float, progress_pct: float, recommendation: Dict) -> str:
        """Format approaching target alert message in Bulgarian"""
        
        profit_pct = self._calculate_profit_pct(
            signal['signal_type'],
            signal['entry_price'],
            current_price
        )
        
        direction_emoji = '🟢' if signal['signal_type'] == 'BUY' else '🔴'
        
        # Calculate duration
        opened_at = signal.get('opened_at', signal.get('timestamp'))
        duration = datetime.now(timezone.utc) - opened_at
        hours = int(duration.total_seconds() // 3600)
        minutes = int((duration.total_seconds() % 3600) // 60)
        duration_str = f"{hours}ч {minutes}мин" if hours > 0 else f"{minutes}мин"
        
        rec_emoji = {
            'HOLD': '💎',
            'PARTIAL_CLOSE': '🟡',
            'CLOSE_NOW': '❌'
        }.get(recommendation.get('recommendation', 'HOLD'), '⚠️')
        
        rec_action = recommendation.get('recommendation', 'HOLD')
        
        message = f"""<b>🎯 ПРИБЛИЖАВА ЦЕЛТА! {progress_pct:.0f}% готово</b>

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 <b>ТРЕЙД: {signal.get('trade_id', 'N/A')}</b>
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{direction_emoji} <b>{signal['symbol']} - {signal['signal_type']}</b>
⏰ Времева рамка: {signal['timeframe']}
📅 Отворен: {opened_at.strftime('%d.%m.%Y %H:%M')}
⏱️ Активен: {duration_str}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💰 <b>Текуща печалба:</b> {profit_pct:+.2f}%
📊 <b>Прогрес:</b> {progress_pct:.1f}% до целта

💵 <b>Цени:</b>
   Вход: ${signal['entry_price']:,.2f}
   Сега: ${current_price:,.2f}
   Цел (TP): ${signal['tp_price']:,.2f}
   SL: ${signal['sl_price']:,.2f}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

<b>{'✅' if rec_action == 'HOLD' else '⚠️'} ICT ПРОВЕРКА:</b>
{recommendation.get('reasoning', 'Няма налична информация')}

🎲 <b>ИЗЧИСЛЕНА ВЕРОЯТНОСТ:</b> {recommendation.get('confidence', 0):.0f}%

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💡 <b>ПРЕПОРЪКА: {rec_action} {rec_emoji}</b>

{'Продължи да държиш! Целта е на досег.' if rec_action == 'HOLD' else 'Размисли за частична печалба. Близо си до целта.'}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⏰ Следваща проверка след 2 минути...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        return message
    
    def _get_stage_buttons(self, signal_id: str) -> InlineKeyboardMarkup:
        """Create interactive buttons for stage alerts"""
        keyboard = [
            [
                InlineKeyboardButton("🟡 Вземи 50%", callback_data=f"partial50_{signal_id}"),
                InlineKeyboardButton("🟡 Вземи 30%", callback_data=f"partial30_{signal_id}")
            ],
            [
                InlineKeyboardButton("💎 Дръж Всичко", callback_data=f"hold_{signal_id}"),
                InlineKeyboardButton("📊 Пълен Анализ", callback_data=f"analyze_{signal_id}")
            ]
        ]
        
        return InlineKeyboardMarkup(keyboard)
    
    def get_user_trades(self, user_chat_id: int) -> List[Dict]:
        """Get all active trades for a specific user"""
        user_trades = []
        for signal_id, signal in self.monitored_signals.items():
            if signal.get('user_chat_id') == user_chat_id and not signal.get('result_sent', False):
                user_trades.append({
                    'signal_id': signal_id,
                    **signal
                })
        return user_trades
            

    def get_monitored_signals_count(self) -> int:
        """Get count of currently monitored signals"""
        return len(self.monitored_signals)
        
    def get_signal_status(self, signal_id: str) -> Optional[Dict]:
        """Get status of a specific signal"""
        return self.monitored_signals.get(signal_id)
