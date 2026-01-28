"""
🔄 UNIFIED TRADE MANAGER - Live Position Monitoring System

Integrates existing components for automated trade monitoring:
- Position tracking and progress calculation
- Checkpoint detection (25%, 50%, 75%, 85%)
- ICT re-analysis at checkpoints (via TradeReanalysisEngine)
- News/sentiment integration (via FundamentalHelper)
- Bulgarian narrative alerts
- TP/SL hit detection

Author: galinborisov10-art
Date: 2026-01-27
PR: #202 - Unified Trade Manager
"""

import logging
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import requests

# Constants
BINANCE_PRICE_URL = "https://api.binance.com/api/v3/ticker/price"

# Import existing engines (NO MODIFICATIONS to these files)
try:
    from trade_reanalysis_engine import TradeReanalysisEngine, CheckpointAnalysis
    REANALYSIS_ENGINE_AVAILABLE = True
except ImportError:
    REANALYSIS_ENGINE_AVAILABLE = False
    TradeReanalysisEngine = None
    CheckpointAnalysis = None
    logging.warning("TradeReanalysisEngine not available")

try:
    from position_manager import PositionManager
    POSITION_MANAGER_AVAILABLE = True
except ImportError:
    POSITION_MANAGER_AVAILABLE = False
    PositionManager = None
    logging.warning("PositionManager not available")

try:
    from utils.fundamental_helper import FundamentalHelper
    FUNDAMENTAL_HELPER_AVAILABLE = True
except ImportError:
    FUNDAMENTAL_HELPER_AVAILABLE = False
    FundamentalHelper = None
    logging.warning("FundamentalHelper not available")

try:
    from ict_signal_engine import ICTSignalEngine, ICTSignal
    ICT_ENGINE_AVAILABLE = True
except ImportError:
    ICT_ENGINE_AVAILABLE = False
    ICTSignalEngine = None
    ICTSignal = None
    logging.warning("ICTSignalEngine not available")

try:
    from narrative_templates import SwingTraderNarrative, NarrativeSelector
    NARRATIVE_TEMPLATES_AVAILABLE = True
except ImportError:
    NARRATIVE_TEMPLATES_AVAILABLE = False
    SwingTraderNarrative = None
    NarrativeSelector = None
    logging.warning("NarrativeTemplates not available")

logger = logging.getLogger(__name__)


class UnifiedTradeManager:
    """
    Unified Trade Manager - Live Position Monitoring
    
    Combines:
    - Position tracking (PositionManager)
    - Progress calculation (backtest-style logic)
    - ICT re-analysis (TradeReanalysisEngine)
    - News integration (FundamentalHelper)
    - Bulgarian narrative generation
    
    Methods:
        monitor_live_trade() - Main monitoring function (called every 60s per position)
    """
    
    def __init__(self, bot_instance=None):
        """
        Initialize Unified Trade Manager
        
        Args:
            bot_instance: Telegram bot instance for sending messages
        """
        self.bot_instance = bot_instance
        
        # Initialize position manager
        if POSITION_MANAGER_AVAILABLE:
            self.position_manager = PositionManager()
        else:
            self.position_manager = None
            logger.warning("⚠️ PositionManager not available")
        
        # Initialize re-analysis engine
        if REANALYSIS_ENGINE_AVAILABLE and ICT_ENGINE_AVAILABLE:
            try:
                ict_engine = ICTSignalEngine()
                self.reanalysis_engine = TradeReanalysisEngine(ict_engine=ict_engine)
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize TradeReanalysisEngine with ICT: {e}")
                self.reanalysis_engine = TradeReanalysisEngine()
        else:
            self.reanalysis_engine = None
            logger.warning("⚠️ TradeReanalysisEngine not available")
        
        # Initialize fundamental helper
        if FUNDAMENTAL_HELPER_AVAILABLE:
            try:
                self.fundamentals = FundamentalHelper()
            except Exception as e:
                logger.warning(f"⚠️ Could not initialize FundamentalHelper: {e}")
                self.fundamentals = None
        else:
            self.fundamentals = None
        
        # Checkpoint levels
        self.checkpoint_levels = [25, 50, 75, 85]
        
        # Store current position for news assessment
        self.current_position = None
        
        logger.info("✅ UnifiedTradeManager initialized")
        logger.info(f"   → PositionManager: {'Available' if self.position_manager else 'Not Available'}")
        logger.info(f"   → ReanalysisEngine: {'Available' if self.reanalysis_engine else 'Not Available'}")
        logger.info(f"   → FundamentalHelper: {'Available' if self.fundamentals else 'Not Available'}")
        logger.info(f"   → NarrativeTemplates: {'Available' if NARRATIVE_TEMPLATES_AVAILABLE else 'Not Available'}")
        logger.info(f"   → Checkpoint levels: {self.checkpoint_levels}")
        
        # AUTO-SYNC from journal on startup
        self._sync_from_journal()
    
    def _sync_from_journal(self):
        """
        Sync pending trades from journal on startup
        
        Ensures all PENDING trades from trading_journal.json
        are tracked in positions.db for checkpoint monitoring.
        """
        try:
            logger.info("🔄 Syncing pending trades from journal...")
            from sync_journal_to_positions import sync_journal_to_positions
            stats = sync_journal_to_positions()
            
            if stats['added'] > 0:
                logger.info(f"✅ Journal sync complete: {stats['added']} positions added")
            elif stats['skipped'] > 0:
                logger.info(f"ℹ️  Journal sync complete: All positions already tracked")
            else:
                logger.info(f"ℹ️  Journal sync complete: No pending trades to sync")
                
        except Exception as e:
            logger.error(f"❌ Journal sync failed: {e}")
    
    async def monitor_live_trade(self, position: Dict) -> None:
        """
        Main monitoring function - called every 60s for each open position
        
        Args:
            position: Position dictionary from database
            
        Process:
        1. Get current price
        2. Calculate progress (reuse backtest logic)
        3. Check if checkpoint reached
        4. If yes → re-analyze + check news + smart filtering
        5. Send alert ONLY if meaningful change
        6. Check TP/SL hits
        """
        try:
            symbol = position['symbol']
            
            # Store current position for news assessment
            self.current_position = position
            
            # 1. Get current price
            current_price = await self._get_current_price(symbol)
            if not current_price:
                logger.warning(f"⚠️ Could not get current price for {symbol}")
                return
            
            # 2. Calculate progress
            progress = self._calculate_progress(position, current_price)
            
            # 3. Check checkpoint
            checkpoint = self._get_checkpoint_level(position, progress)
            
            if checkpoint:
                logger.info(f"🎯 {symbol} reached {checkpoint}% checkpoint!")
                
                # 4. Run re-analysis
                analysis = await self._run_checkpoint_analysis(
                    position,
                    current_price,
                    checkpoint
                )
                
                # 5. Check news
                news_data = await self._check_news(symbol)
                
                # 6. Smart filtering - should we send alert?
                should_alert, alert_type = self._should_send_alert(
                    analysis, news_data, checkpoint, position
                )
                
                if should_alert:
                    logger.info(f"📢 Alert triggered: {alert_type}")
                    
                    # 7. Generate professional narrative
                    alert_message = self._format_professional_alert(
                        position,
                        analysis,
                        news_data,
                        checkpoint,
                        progress,
                        current_price
                    )
                    
                    # 8. Send Telegram alert
                    await self._send_checkpoint_alert(
                        position.get('user_id') or position.get('id'),
                        alert_message
                    )
                else:
                    logger.info(f"🔇 Silent monitoring at {checkpoint}% - no significant changes")
                
                # 9. Save checkpoint event (always, even if no alert sent)
                if self.position_manager:
                    # Mark checkpoint as triggered (use "XX%" format for database)
                    self.position_manager.update_checkpoint_triggered(
                        position['id'],
                        f"{checkpoint}%"
                    )
                    
                    # Log checkpoint alert only if alert was sent
                    if should_alert and analysis:
                        self.position_manager.log_checkpoint_alert(
                            position_id=position['id'],
                            checkpoint_level=f"{checkpoint}%",
                            trigger_price=current_price,
                            analysis=analysis,
                            action_taken='ALERTED' if should_alert else 'MONITORED'
                        )
            
            # 10. Check TP/SL hits
            await self._check_tp_sl_hits(position, current_price)
            
        except Exception as e:
            logger.error(f"❌ Monitor failed for {position.get('symbol', 'UNKNOWN')}: {e}")
    
    def _calculate_progress(self, position: Dict, current_price: float) -> float:
        """
        Calculate progress toward TP1
        REUSES backtest calculation logic
        
        Args:
            position: Position dictionary
            current_price: Current market price
            
        Returns:
            Float 0-100 (percentage progress)
        """
        try:
            entry = position['entry_price']
            tp1 = position['tp1_price']
            signal_type = position['signal_type']
            
            if signal_type in ['BUY', 'STRONG_BUY']:
                # LONG position
                total_distance = tp1 - entry
                current_distance = current_price - entry
                progress = (current_distance / total_distance) * 100
            else:
                # SHORT position
                total_distance = entry - tp1
                current_distance = entry - current_price
                progress = (current_distance / total_distance) * 100
            
            # Clamp to 0-100
            return max(0, min(100, progress))
            
        except Exception as e:
            logger.error(f"❌ Progress calculation error: {e}")
            return 0.0
    
    def _get_checkpoint_level(self, position: Dict, progress: float) -> Optional[int]:
        """
        Determine if checkpoint reached
        
        Args:
            position: Position dictionary
            progress: Current progress percentage
            
        Returns:
            25, 50, 75, or 85 if checkpoint reached, None otherwise
        """
        try:
            # Check each level
            for level in self.checkpoint_levels:
                # Check if already triggered
                checkpoint_key = f'checkpoint_{level}_triggered'
                if position.get(checkpoint_key):
                    continue  # Already triggered
                
                # Check if reached
                if progress >= level:
                    return level
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Checkpoint detection error: {e}")
            return None
    
    async def _run_checkpoint_analysis(
        self,
        position: Dict,
        current_price: float,
        checkpoint: int
    ) -> Optional[CheckpointAnalysis]:
        """
        Run full 12-step ICT re-analysis
        Uses existing TradeReanalysisEngine
        
        Args:
            position: Position dictionary
            current_price: Current market price
            checkpoint: Checkpoint level (25, 50, 75, 85)
            
        Returns:
            CheckpointAnalysis object or None
        """
        try:
            if not self.reanalysis_engine:
                logger.warning("⚠️ ReanalysisEngine not available")
                return None
            
            # Extract position data
            symbol = position['symbol']
            timeframe = position['timeframe']
            checkpoint_level = f"{checkpoint}%"
            
            # Parse original signal from JSON
            original_signal_json = position.get('original_signal_parsed', {})
            if not original_signal_json:
                logger.warning(f"⚠️ No original signal data for position {position['id']}")
                return None
            
            # Create ICTSignal object from JSON
            if ICT_ENGINE_AVAILABLE:
                try:
                    from ict_signal_engine import SignalType, MarketBias, SignalStrength
                    
                    # Reconstruct ICTSignal (basic reconstruction)
                    class SimpleSignal:
                        def __init__(self, data):
                            self.symbol = data.get('symbol', symbol)
                            self.timeframe = data.get('timeframe', timeframe)
                            self.signal_type = data.get('signal_type', 'BUY')
                            self.entry_price = data.get('entry_price', position['entry_price'])
                            self.sl_price = data.get('sl_price', position['sl_price'])
                            self.tp_prices = data.get('tp_prices', [position['tp1_price']])
                            self.confidence = data.get('confidence', 0)
                            self.htf_bias = data.get('htf_bias', 'UNKNOWN')
                    
                    original_signal = SimpleSignal(original_signal_json)
                    
                except Exception as e:
                    logger.warning(f"⚠️ Could not reconstruct signal: {e}")
                    return None
            else:
                logger.warning("⚠️ ICT Engine not available for signal reconstruction")
                return None
            
            # Calculate checkpoint price
            entry_price = position['entry_price']
            tp1_price = position['tp1_price']
            signal_type = position['signal_type']
            
            if signal_type in ['BUY', 'STRONG_BUY']:
                distance = tp1_price - entry_price
                checkpoint_price = entry_price + (distance * (checkpoint / 100))
            else:
                distance = entry_price - tp1_price
                checkpoint_price = entry_price - (distance * (checkpoint / 100))
            
            # Run re-analysis
            analysis = self.reanalysis_engine.reanalyze_at_checkpoint(
                symbol=symbol,
                timeframe=timeframe,
                checkpoint_level=checkpoint_level,
                checkpoint_price=checkpoint_price,
                current_price=current_price,
                original_signal=original_signal,
                tp1_price=tp1_price,
                sl_price=position['sl_price']
            )
            
            return analysis
            
        except Exception as e:
            logger.error(f"❌ Re-analysis failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    async def _check_news(self, symbol: str) -> Optional[Dict]:
        """
        Check for recent news using existing breaking_news_monitor system
        Integrates with FundamentalHelper and analyze_news_impact
        
        Args:
            symbol: Trading symbol
            
        Returns:
            News data dictionary with priority and impact assessment or None
        """
        try:
            if not self.fundamentals:
                return None
            
            # Check if fundamental analysis is enabled
            if not self.fundamentals.is_enabled():
                logger.debug("Fundamental analysis disabled, skipping news check")
                return None
            
            # Get fundamental data (existing system)
            try:
                fund_data = self.fundamentals.get_fundamental_data(symbol)
            except Exception as e:
                logger.warning(f"Could not get fundamental data: {e}")
                return None
            
            if not fund_data:
                return None
            
            sentiment = fund_data.get('sentiment', {})
            label = sentiment.get('label', '').upper()  # POSITIVE/NEGATIVE/NEUTRAL/BEARISH/BULLISH
            top_news = sentiment.get('top_news', [])
            
            # Map labels to priority
            priority = 'moderate'
            if 'CRITICAL' in label:
                priority = 'critical'
            elif any(word in label for word in ['STRONG_BEARISH', 'STRONG_BULLISH']):
                priority = 'critical'
            elif 'BEARISH' in label or 'BULLISH' in label:
                priority = 'important'
            elif 'POSITIVE' in label or 'NEGATIVE' in label:
                priority = 'important'
            else:
                priority = 'low'
            
            # Assess impact on current position
            impact_assessment = ''
            if self.current_position:
                impact_assessment = self._assess_news_vs_position(
                    sentiment, label, self.current_position
                )
            
            return {
                'headline': top_news[0] if top_news else 'Market moving news',
                'priority': priority,
                'sentiment_label': label,
                'impact_assessment': impact_assessment,
                'source': 'fundamental_helper',
                'top_news': top_news
            }
            
        except Exception as e:
            logger.error(f"❌ News check failed: {e}")
            return None
    
    def _assess_news_vs_position(
        self,
        sentiment: Dict,
        label: str,
        position: Dict
    ) -> str:
        """
        Assess how news impacts current position
        Maps sentiment labels (BEARISH/BULLISH) against position direction
        
        Args:
            sentiment: Sentiment data dictionary
            label: Sentiment label (BEARISH/BULLISH/NEUTRAL/etc)
            position: Position dictionary
            
        Returns:
            Impact assessment string
        """
        try:
            is_long = position['signal_type'] in ['BUY', 'STRONG_BUY']
            
            # Check if news contradicts position
            if is_long and ('BEARISH' in label or 'NEGATIVE' in label):
                if 'STRONG_BEARISH' in label or 'CRITICAL' in label:
                    return "🚨 CRITICAL: Bearish news против LONG позиция - HIGH REVERSAL RISK!"
                else:
                    return "⚠️ Bearish news против LONG - Consider partial exit"
            
            elif not is_long and ('BULLISH' in label or 'POSITIVE' in label):
                if 'STRONG_BULLISH' in label or 'CRITICAL' in label:
                    return "🚨 CRITICAL: Bullish news против SHORT позиция - HIGH REVERSAL RISK!"
                else:
                    return "⚠️ Bullish news против SHORT - Consider partial exit"
            
            elif is_long and ('BULLISH' in label or 'POSITIVE' in label):
                return "✅ Bullish news подкрепя LONG позиция - Momentum в наша полза"
            
            elif not is_long and ('BEARISH' in label or 'NEGATIVE' in label):
                return "✅ Bearish news подкрепя SHORT позиция - Momentum в наша полза"
            
            else:
                return "ℹ️ Neutral news - no clear impact на позицията"
            
        except Exception as e:
            logger.error(f"❌ News impact assessment failed: {e}")
            return ""
    
    def _should_send_alert(
        self,
        analysis: Optional[Any],
        news: Optional[Dict],
        checkpoint: int,
        position: Dict
    ) -> tuple:
        """
        Smart alert filtering - determines if alert should be sent
        
        Alert ONLY when:
        - Checkpoint reached AND (bias changed OR structure broken OR confidence drop >10%)
        - Critical news (CRITICAL priority)
        - Important news (important priority) affecting position
        - At 25% and 85% checkpoints (confirmation alerts)
        
        Silent monitoring when:
        - Checkpoint reached but nothing changed
        - News is LOW impact or NEUTRAL
        
        Args:
            analysis: CheckpointAnalysis object
            news: News data dictionary
            checkpoint: Checkpoint level (25, 50, 75, 85)
            position: Position dictionary
            
        Returns:
            Tuple (should_alert: bool, alert_type: str)
        """
        try:
            # Always alert at 25% (entry confirmation) and 85% (near TP1)
            if checkpoint in [25, 85]:
                return (True, f'{checkpoint}% confirmation checkpoint')
            
            # Check for critical news
            if news and news.get('priority') == 'critical':
                return (True, 'critical news alert')
            
            # Check for important news affecting position
            if news and news.get('priority') == 'important':
                impact = news.get('impact_assessment', '')
                if 'против' in impact or 'REVERSAL RISK' in impact:
                    return (True, 'important news contradicting position')
            
            # Check analysis changes (if available)
            if analysis:
                # Structure broken - always alert
                if hasattr(analysis, 'structure_broken') and analysis.structure_broken:
                    return (True, 'structure broken')
                
                # HTF bias changed - always alert
                if hasattr(analysis, 'htf_bias_changed') and analysis.htf_bias_changed:
                    return (True, 'HTF bias changed')
                
                # Confidence drop >10% - alert
                if hasattr(analysis, 'confidence_delta'):
                    if analysis.confidence_delta < -10:
                        return (True, f'confidence drop {analysis.confidence_delta:.0f}%')
            
            # No significant changes - silent monitoring
            return (False, 'no significant changes')
            
        except Exception as e:
            logger.error(f"❌ Alert filtering failed: {e}")
            # Default to sending alert on error (fail-safe)
            return (True, 'error - fail-safe alert')
    
    def _format_professional_alert(
        self,
        position: Dict,
        analysis: Optional[Any],
        news: Optional[Dict],
        checkpoint: int,
        progress: float,
        current_price: float
    ) -> str:
        """
        Generate professional Bulgarian narrative using SwingTraderNarrative
        
        Args:
            position: Position dictionary
            analysis: CheckpointAnalysis object
            news: News data
            checkpoint: Checkpoint level
            progress: Current progress percentage
            current_price: Current market price
            
        Returns:
            Professional Bulgarian alert message with reasoning
        """
        try:
            # Use narrative templates if available
            if NARRATIVE_TEMPLATES_AVAILABLE and NarrativeSelector:
                return NarrativeSelector.select_narrative(
                    position, analysis, news, checkpoint, progress, current_price
                )
            else:
                # Fallback to old format
                return self._format_bulgarian_alert(
                    position, analysis, news, checkpoint, progress
                )
                
        except Exception as e:
            logger.error(f"❌ Professional alert formatting failed: {e}")
            # Fallback to simple format
            return self._format_fallback_alert(position, checkpoint, progress)
    
    def _format_bulgarian_alert(
        self,
        position: Dict,
        analysis: Optional[Any],
        news: Optional[Dict],
        checkpoint: int,
        progress: float
    ) -> str:
        """
        Generate Bulgarian narrative for checkpoint (legacy format)
        
        Args:
            position: Position dictionary
            analysis: CheckpointAnalysis object
            news: News data
            checkpoint: Checkpoint level
            progress: Current progress percentage
            
        Returns:
            Formatted Bulgarian alert message
        """
        if not analysis:
            return self._format_fallback_alert(position, checkpoint, progress)
        
        try:
            # Determine recommendation
            confidence_delta = getattr(analysis, 'confidence_delta', 0)
            
            # Basic decision logic
            if confidence_delta < -15:
                action = "ЗАТВОРИ СЕГА"
                emoji = "🔴"
            elif confidence_delta < -10:
                action = "ЗАТВОРИ 40-50%"
                emoji = "🟡"
            else:
                action = "ЗАДРЪЖ"
                emoji = "💎"
            
            # Format news section
            news_section = ""
            if news and news.get('top_news'):
                top_news = news.get('top_news', [])
                if top_news:
                    news_section = f"\n📰 НОВИНИ: {top_news[0]}"
            
            # Get HTF bias info
            htf_bias = getattr(analysis, 'htf_bias', 'UNKNOWN')
            htf_changed = getattr(analysis, 'htf_bias_changed', False)
            original_confidence = getattr(analysis, 'original_confidence', 0)
            current_confidence = getattr(analysis, 'current_confidence', 0)
            structure_broken = getattr(analysis, 'structure_broken', False)
            valid_components = getattr(analysis, 'valid_components_count', 0)
            current_rr = getattr(analysis, 'current_rr_ratio', 0)
            
            # Build message
            message = f"""
{emoji} {checkpoint}% CHECKPOINT

📊 {position['symbol']} АНАЛИЗ:
• Confidence: {original_confidence:.0f}% → {current_confidence:.0f}% (Δ{confidence_delta:+.0f}%)
• Структура: {'Валидна ✅' if not structure_broken else 'Счупена ❌'}
• HTF Bias: {htf_bias} {'⚠️ ПРОМЕНЕН' if htf_changed else '✅'}
• Valid компоненти: {valid_components}
• R:R: {current_rr:.1f}:1
{news_section}

{emoji} ПРЕПОРЪКА: {action}

💡 Progress: {progress:.1f}% към TP1
"""
            return message
            
        except Exception as e:
            logger.error(f"❌ Alert formatting error: {e}")
            return self._format_fallback_alert(position, checkpoint, progress)
    
    def _format_fallback_alert(self, position: Dict, checkpoint: int, progress: float) -> str:
        """
        Fallback alert if analysis fails
        
        Args:
            position: Position dictionary
            checkpoint: Checkpoint level
            progress: Current progress percentage
            
        Returns:
            Simple fallback message
        """
        next_checkpoint = checkpoint + 25 if checkpoint < 85 else "TP1"
        
        return f"""
💎 {checkpoint}% CHECKPOINT

📊 {position['symbol']}
Progress: {progress:.1f}% към TP1

Позицията се развива. Следващ checkpoint @ {next_checkpoint}
"""
    
    async def _send_checkpoint_alert(self, user_id: int, message: str) -> None:
        """
        Send alert via Telegram
        
        Args:
            user_id: User/chat ID
            message: Alert message
        """
        try:
            if not self.bot_instance:
                logger.warning("⚠️ No bot instance available for sending alerts")
                return
            
            await self.bot_instance.send_message(
                chat_id=user_id,
                text=message,
                parse_mode='HTML'
            )
            logger.info(f"✅ Checkpoint alert sent to {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to send checkpoint alert: {e}")
    
    async def _check_tp_sl_hits(self, position: Dict, current_price: float) -> None:
        """
        Check if TP or SL hit
        
        Args:
            position: Position dictionary
            current_price: Current market price
        """
        try:
            signal_type = position['signal_type']
            tp1_price = position['tp1_price']
            sl_price = position['sl_price']
            
            if signal_type in ['BUY', 'STRONG_BUY']:
                # LONG position
                if current_price >= tp1_price:
                    await self._handle_tp_hit(position, current_price, 'TP1')
                elif current_price <= sl_price:
                    await self._handle_sl_hit(position, current_price)
            else:
                # SHORT position
                if current_price <= tp1_price:
                    await self._handle_tp_hit(position, current_price, 'TP1')
                elif current_price >= sl_price:
                    await self._handle_sl_hit(position, current_price)
                    
        except Exception as e:
            logger.error(f"❌ TP/SL check failed: {e}")
    
    async def _handle_tp_hit(self, position: Dict, price: float, tp_level: str) -> None:
        """
        Handle TP hit
        
        Args:
            position: Position dictionary
            price: Current price
            tp_level: TP level ('TP1', 'TP2', 'TP3')
        """
        try:
            symbol = position['symbol']
            logger.info(f"✅ {symbol} hit {tp_level} @ {price}")
            
            # Close position
            if self.position_manager:
                self.position_manager.close_position(
                    position_id=position['id'],
                    exit_price=price,
                    outcome='TP_HIT'
                )
            
            # Send notification
            message = f"""
✅ TP1 HIT!

{symbol} достигна целта @ {price:.2f}

Позицията е затворена автоматично.
"""
            await self._send_checkpoint_alert(
                position.get('user_id') or position.get('id'),
                message
            )
            
        except Exception as e:
            logger.error(f"❌ Handle TP hit failed: {e}")
    
    async def _handle_sl_hit(self, position: Dict, price: float) -> None:
        """
        Handle SL hit
        
        Args:
            position: Position dictionary
            price: Current price
        """
        try:
            symbol = position['symbol']
            logger.info(f"❌ {symbol} hit SL @ {price}")
            
            # Close position
            if self.position_manager:
                self.position_manager.close_position(
                    position_id=position['id'],
                    exit_price=price,
                    outcome='SL_HIT'
                )
            
            # Send notification
            message = f"""
🛑 STOP LOSS HIT

{symbol} hit SL @ {price:.2f}

Позицията е затворена за защита на капитала.
"""
            await self._send_checkpoint_alert(
                position.get('user_id') or position.get('id'),
                message
            )
            
        except Exception as e:
            logger.error(f"❌ Handle SL hit failed: {e}")
    
    async def _get_current_price(self, symbol: str) -> Optional[float]:
        """
        Get current market price
        
        Args:
            symbol: Trading symbol
            
        Returns:
            Current price or None
        """
        try:
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
