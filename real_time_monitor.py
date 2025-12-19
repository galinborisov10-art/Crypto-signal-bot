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
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import requests
from telegram import Bot

logger = logging.getLogger(__name__)


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
        if user_chat_id is None:
            user_chat_id = self.owner_chat_id
            
        self.monitored_signals[signal_id] = {
            'symbol': symbol,
            'signal_type': signal_type,
            'entry_price': entry_price,
            'tp_price': tp_price,
            'sl_price': sl_price,
            'confidence': confidence,
            'timeframe': timeframe,
            'user_chat_id': user_chat_id,
            'timestamp': datetime.now(timezone.utc),
            'tp_80_alerted': False,
            'result_sent': False,
            'last_checked': None
        }
        
        logger.info(f"📊 Signal {signal_id} added to real-time monitor")
        
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
                
                # Handle 80% TP alert (75-85% range)
                if not signal.get('tp_80_alerted', False) and 75 <= progress_pct <= 85:
                    await self._send_80_percent_alert(signal_id, signal, current_price, progress_pct)
                    signal['tp_80_alerted'] = True
                    
                # Handle SL hit
                elif sl_hit and not signal.get('result_sent', False):
                    await self._send_loss_alert(signal_id, signal, current_price)
                    signal['result_sent'] = True
                    signals_to_remove.append(signal_id)
                    
                # Handle TP hit
                elif tp_hit and not signal.get('result_sent', False):
                    await self._send_win_alert(signal_id, signal, current_price)
                    signal['result_sent'] = True
                    signals_to_remove.append(signal_id)
                    
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
            
    def get_monitored_signals_count(self) -> int:
        """Get count of currently monitored signals"""
        return len(self.monitored_signals)
        
    def get_signal_status(self, signal_id: str) -> Optional[Dict]:
        """Get status of a specific signal"""
        return self.monitored_signals.get(signal_id)
