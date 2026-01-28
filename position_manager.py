"""
📊 POSITION MANAGER
Complete position lifecycle management with database operations

Features:
- Open/close positions with full ICTSignal tracking
- Checkpoint monitoring and alerting
- P&L calculation
- Position history with statistics
- Partial close support

Author: galinborisov10-art
Date: 2026-01-13
PR: #7 - Full Auto Re-analysis Monitoring
"""

import sqlite3
import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from pathlib import Path
import os

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Auto-detect base path
if os.getenv('BOT_BASE_PATH'):
    BASE_PATH = os.getenv('BOT_BASE_PATH')
elif os.path.exists('/root/Crypto-signal-bot'):
    BASE_PATH = '/root/Crypto-signal-bot'
elif os.path.exists('/workspaces/Crypto-signal-bot'):
    BASE_PATH = '/workspaces/Crypto-signal-bot'
else:
    BASE_PATH = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_PATH, 'positions.db')


class PositionManager:
    """
    Position Manager - Complete position lifecycle management
    
    Methods:
        - open_position() - Open new position
        - get_open_positions() - Get all open positions
        - get_position_by_id() - Get single position
        - update_checkpoint_triggered() - Mark checkpoint as triggered
        - get_hit_checkpoints() - Get list of checkpoints already hit
        - log_checkpoint_alert() - Log checkpoint analysis
        - close_position() - Close position with P&L
        - partial_close() - Partial position close
        - get_position_history() - Recent closed positions
        - get_position_stats() - Aggregate statistics
    """
    
    def __init__(self, db_path: str = DB_PATH):
        """
        Initialize Position Manager
        
        Args:
            db_path: Path to SQLite database
        """
        self.db_path = db_path
        self._ensure_database_exists()
        logger.info(f"✅ PositionManager initialized (DB: {self.db_path})")
    
    def _ensure_database_exists(self):
        """Ensure database and tables exist"""
        if not os.path.exists(self.db_path):
            logger.warning(f"⚠️  Database not found, creating: {self.db_path}")
            from init_positions_db import create_positions_database
            create_positions_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # Enable column access by name
        return conn
    
    def _get_attr_value(self, obj: Any, attr: str, default: Any = None) -> Any:
        """
        Safely get attribute value, handling enum values
        
        Args:
            obj: Object to get attribute from
            attr: Attribute name
            default: Default value if attribute doesn't exist
            
        Returns:
            Attribute value or default
        """
        if not hasattr(obj, attr):
            return default
        
        value = getattr(obj, attr)
        
        # Handle enum types
        if hasattr(value, 'value'):
            return value.value
        
        # Handle datetime types
        if hasattr(value, 'isoformat'):
            return value.isoformat()
        
        return value
    
    def _serialize_signal(self, signal: Any) -> str:
        """
        Serialize ICTSignal to JSON string
        
        Args:
            signal: ICTSignal object
            
        Returns:
            JSON string
        """
        try:
            # Convert ICTSignal to dict using helper method
            signal_dict = {
                'timestamp': self._get_attr_value(signal, 'timestamp', ''),
                'symbol': self._get_attr_value(signal, 'symbol', ''),
                'timeframe': self._get_attr_value(signal, 'timeframe', ''),
                'signal_type': self._get_attr_value(signal, 'signal_type', ''),
                'signal_strength': self._get_attr_value(signal, 'signal_strength', ''),
                'entry_price': self._get_attr_value(signal, 'entry_price', 0),
                'sl_price': self._get_attr_value(signal, 'sl_price', 0),
                'tp_prices': self._get_attr_value(signal, 'tp_prices', []),
                'confidence': self._get_attr_value(signal, 'confidence', 0),
                'risk_reward_ratio': self._get_attr_value(signal, 'risk_reward_ratio', 0),
                'bias': self._get_attr_value(signal, 'bias', ''),
                'htf_bias': self._get_attr_value(signal, 'htf_bias', None),
            }
            
            return json.dumps(signal_dict)
            
        except Exception as e:
            logger.error(f"❌ Signal serialization error: {e}")
            return "{}"
    
    def open_position(
        self,
        signal: Any,
        symbol: str,
        timeframe: str,
        source: str = 'AUTO'
    ) -> int:
        """
        Open a new position for tracking
        
        Args:
            signal: ICTSignal object or MockSignal object
            symbol: Trading pair (e.g., 'BTCUSDT')
            timeframe: Timeframe (e.g., '1h', '2h')
            source: 'AUTO', 'MANUAL', or 'JOURNAL_SYNC'
            
        Returns:
            position_id: Database ID of opened position
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Extract signal data with defensive parsing
            signal_type = signal.signal_type.value if hasattr(signal.signal_type, 'value') else str(signal.signal_type)
            entry_price = signal.entry_price
            sl_price = signal.sl_price
            
            # Extract tp_prices safely - handle both ICTSignal (tp_prices list) and MockSignal
            tp_prices = []
            if hasattr(signal, 'tp_prices') and signal.tp_prices:
                # Modern format: tp_prices as array
                tp_prices = signal.tp_prices if isinstance(signal.tp_prices, list) else [signal.tp_prices]
            elif hasattr(signal, 'tp1_price'):
                # Legacy format: tp1_price, tp2_price, tp3_price as separate attributes
                if hasattr(signal, 'tp1_price') and signal.tp1_price:
                    tp_prices.append(signal.tp1_price)
                if hasattr(signal, 'tp2_price') and signal.tp2_price:
                    tp_prices.append(signal.tp2_price)
                if hasattr(signal, 'tp3_price') and signal.tp3_price:
                    tp_prices.append(signal.tp3_price)
            
            # Extract individual TP prices for database
            tp1_price = tp_prices[0] if len(tp_prices) > 0 else None
            tp2_price = tp_prices[1] if len(tp_prices) > 1 else None
            tp3_price = tp_prices[2] if len(tp_prices) > 2 else None
            
            # Serialize full signal
            signal_json = self._serialize_signal(signal)
            
            # Insert position
            cursor.execute("""
                INSERT INTO open_positions (
                    symbol, timeframe, signal_type,
                    entry_price, tp1_price, tp2_price, tp3_price, sl_price,
                    original_signal_json, source, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'OPEN')
            """, (
                symbol, timeframe, signal_type,
                entry_price, tp1_price, tp2_price, tp3_price, sl_price,
                signal_json, source
            ))
            
            position_id = cursor.lastrowid
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Position opened: ID={position_id}, {symbol} {signal_type} @ ${entry_price:,.2f}")
            
            return position_id
            
        except Exception as e:
            logger.error(f"❌ Open position error: {e}")
            return -1
    
    def get_open_positions(self) -> List[Dict]:
        """
        Get all open positions
        
        Returns:
            List of position dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM open_positions
                WHERE status IN ('OPEN', 'PARTIAL')
                ORDER BY opened_at DESC
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            positions = []
            for row in rows:
                position = dict(row)
                
                # Parse JSON signal
                try:
                    position['original_signal_parsed'] = json.loads(position['original_signal_json'])
                except:
                    position['original_signal_parsed'] = {}
                
                positions.append(position)
            
            logger.info(f"📊 Retrieved {len(positions)} open position(s)")
            return positions
            
        except Exception as e:
            logger.error(f"❌ Get open positions error: {e}")
            return []
    
    def get_position_by_id(self, position_id: int) -> Optional[Dict]:
        """
        Get single position by ID
        
        Args:
            position_id: Position database ID
            
        Returns:
            Position dictionary or None
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM open_positions
                WHERE id = ?
            """, (position_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return None
            
            position = dict(row)
            
            # Parse JSON signal
            try:
                position['original_signal_parsed'] = json.loads(position['original_signal_json'])
            except:
                position['original_signal_parsed'] = {}
            
            return position
            
        except Exception as e:
            logger.error(f"❌ Get position by ID error: {e}")
            return None
    
    def update_checkpoint_triggered(
        self,
        position_id: int,
        checkpoint_level: str
    ) -> bool:
        """
        Mark checkpoint as triggered
        
        Args:
            position_id: Position database ID
            checkpoint_level: '25%', '50%', '75%', '85%'
            
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Map checkpoint level to column name (whitelist validation)
            checkpoint_map = {
                '25%': 'checkpoint_25_triggered',
                '50%': 'checkpoint_50_triggered',
                '75%': 'checkpoint_75_triggered',
                '85%': 'checkpoint_85_triggered'
            }
            
            column = checkpoint_map.get(checkpoint_level)
            if not column:
                logger.error(f"❌ Invalid checkpoint level: {checkpoint_level}")
                return False
            
            # Safe: column is validated from whitelist, not user input
            # Only 4 possible values: checkpoint_25_triggered, checkpoint_50_triggered,
            # checkpoint_75_triggered, checkpoint_85_triggered
            if column == 'checkpoint_25_triggered':
                cursor.execute("""
                    UPDATE open_positions
                    SET checkpoint_25_triggered = 1,
                        last_checked_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (position_id,))
            elif column == 'checkpoint_50_triggered':
                cursor.execute("""
                    UPDATE open_positions
                    SET checkpoint_50_triggered = 1,
                        last_checked_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (position_id,))
            elif column == 'checkpoint_75_triggered':
                cursor.execute("""
                    UPDATE open_positions
                    SET checkpoint_75_triggered = 1,
                        last_checked_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (position_id,))
            elif column == 'checkpoint_85_triggered':
                cursor.execute("""
                    UPDATE open_positions
                    SET checkpoint_85_triggered = 1,
                        last_checked_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                """, (position_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Checkpoint {checkpoint_level} marked for position {position_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Update checkpoint error: {e}")
            return False
    
    def get_hit_checkpoints(self, position_id: int) -> List[int]:
        """
        Get list of checkpoints already hit for position
        
        Args:
            position_id: Position database ID
            
        Returns:
            List of checkpoint levels (e.g., [25, 50, 75])
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT checkpoint_25_triggered, checkpoint_50_triggered,
                       checkpoint_75_triggered, checkpoint_85_triggered
                FROM open_positions
                WHERE id = ?
            """, (position_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if not row:
                return []
            
            hit_checkpoints = []
            if row['checkpoint_25_triggered']:
                hit_checkpoints.append(25)
            if row['checkpoint_50_triggered']:
                hit_checkpoints.append(50)
            if row['checkpoint_75_triggered']:
                hit_checkpoints.append(75)
            if row['checkpoint_85_triggered']:
                hit_checkpoints.append(85)
            
            return hit_checkpoints
            
        except Exception as e:
            logger.error(f"❌ Get hit checkpoints error: {e}")
            return []
    
    def log_checkpoint_alert(
        self,
        position_id: int,
        checkpoint_level: str,
        trigger_price: float,
        analysis: Dict,
        action_taken: str = 'ALERTED'
    ) -> bool:
        """
        Log checkpoint alert to database
        
        Args:
            position_id: Position database ID
            checkpoint_level: '25%', '50%', '75%', '85%'
            trigger_price: Price at trigger
            analysis: CheckpointAnalysis dict or object
            action_taken: 'ALERTED', 'AUTO_CLOSED', etc.
            
        Returns:
            True if successful
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Extract analysis data
            if hasattr(analysis, 'to_dict'):
                analysis_dict = analysis.to_dict()
            elif isinstance(analysis, dict):
                analysis_dict = analysis
            else:
                logger.error(f"❌ Invalid analysis type: {type(analysis)}")
                return False
            
            # Insert alert
            cursor.execute("""
                INSERT INTO checkpoint_alerts (
                    position_id, checkpoint_level, trigger_price,
                    original_confidence, current_confidence, confidence_delta,
                    htf_bias_changed, structure_broken,
                    valid_components_count, current_rr_ratio,
                    recommendation, reasoning, warnings,
                    action_taken
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_id,
                checkpoint_level,
                trigger_price,
                analysis_dict.get('original_confidence', 0),
                analysis_dict.get('current_confidence', 0),
                analysis_dict.get('confidence_delta', 0),
                1 if analysis_dict.get('htf_bias_changed', False) else 0,
                1 if analysis_dict.get('structure_broken', False) else 0,
                analysis_dict.get('valid_components_count', 0),
                analysis_dict.get('current_rr_ratio', 0),
                analysis_dict.get('recommendation', 'HOLD'),
                analysis_dict.get('reasoning', ''),
                json.dumps(analysis_dict.get('warnings', [])),
                action_taken
            ))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Checkpoint alert logged: position={position_id}, level={checkpoint_level}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Log checkpoint alert error: {e}")
            return False
    
    def close_position(
        self,
        position_id: int,
        exit_price: float,
        outcome: str = 'MANUAL_CLOSE'
    ) -> float:
        """
        Close position and calculate P&L
        
        Args:
            position_id: Position database ID
            exit_price: Exit price
            outcome: 'TP1', 'TP2', 'TP3', 'SL', 'MANUAL_CLOSE', 'EARLY_EXIT'
            
        Returns:
            P&L percentage (positive for profit, negative for loss)
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get position details
            cursor.execute("""
                SELECT * FROM open_positions WHERE id = ?
            """, (position_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.error(f"❌ Position not found: {position_id}")
                return 0.0
            
            position = dict(row)
            
            # Calculate P&L
            entry_price = position['entry_price']
            signal_type = position['signal_type']
            
            if signal_type == 'BUY':
                pl_percent = ((exit_price - entry_price) / entry_price) * 100
            else:  # SELL
                pl_percent = ((entry_price - exit_price) / entry_price) * 100
            
            # Apply partial close multiplier
            current_size = position.get('current_size', 1.0)
            pl_percent *= current_size
            
            # Calculate duration
            opened_at = datetime.fromisoformat(position['opened_at'])
            closed_at = datetime.now(timezone.utc)
            duration_hours = (closed_at - opened_at).total_seconds() / 3600
            
            # Count checkpoints triggered
            checkpoints_triggered = sum([
                position.get('checkpoint_25_triggered', 0),
                position.get('checkpoint_50_triggered', 0),
                position.get('checkpoint_75_triggered', 0),
                position.get('checkpoint_85_triggered', 0)
            ])
            
            # Count recommendations
            cursor.execute("""
                SELECT COUNT(*) FROM checkpoint_alerts
                WHERE position_id = ?
            """, (position_id,))
            recommendations_count = cursor.fetchone()[0]
            
            # Insert into history
            cursor.execute("""
                INSERT INTO position_history (
                    position_id, symbol, timeframe, signal_type,
                    entry_price, exit_price,
                    profit_loss_percent,
                    outcome,
                    opened_at, duration_hours,
                    checkpoints_triggered, recommendations_received
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                position_id,
                position['symbol'],
                position['timeframe'],
                signal_type,
                entry_price,
                exit_price,
                pl_percent,
                outcome,
                position['opened_at'],
                duration_hours,
                checkpoints_triggered,
                recommendations_count
            ))
            
            # Update open_positions status
            cursor.execute("""
                UPDATE open_positions
                SET status = 'CLOSED'
                WHERE id = ?
            """, (position_id,))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Position closed: ID={position_id}, P&L={pl_percent:+.2f}%, outcome={outcome}")
            
            return pl_percent
            
        except Exception as e:
            logger.error(f"❌ Close position error: {e}")
            return 0.0
    
    def partial_close(
        self,
        position_id: int,
        close_percent: float
    ) -> bool:
        """
        Partially close position
        
        Args:
            position_id: Position database ID
            close_percent: Percentage to close (0-100)
            
        Returns:
            True if successful
        """
        try:
            if close_percent <= 0 or close_percent >= 100:
                logger.error(f"❌ Invalid close percent: {close_percent}")
                return False
            
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Get current size
            cursor.execute("""
                SELECT current_size FROM open_positions WHERE id = ?
            """, (position_id,))
            
            row = cursor.fetchone()
            if not row:
                logger.error(f"❌ Position not found: {position_id}")
                return False
            
            current_size = row[0]
            
            # Calculate new size
            close_fraction = close_percent / 100
            new_size = current_size * (1 - close_fraction)
            
            # Update position
            cursor.execute("""
                UPDATE open_positions
                SET current_size = ?,
                    status = 'PARTIAL'
                WHERE id = ?
            """, (new_size, position_id))
            
            conn.commit()
            conn.close()
            
            logger.info(f"✅ Partial close: position={position_id}, closed={close_percent}%, remaining={new_size*100:.0f}%")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Partial close error: {e}")
            return False
    
    def get_position_history(self, limit: int = 20) -> List[Dict]:
        """
        Get recent closed positions
        
        Args:
            limit: Maximum number of positions to return
            
        Returns:
            List of position history dictionaries
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM position_history
                ORDER BY closed_at DESC
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            conn.close()
            
            history = [dict(row) for row in rows]
            
            logger.info(f"📊 Retrieved {len(history)} position(s) from history")
            return history
            
        except Exception as e:
            logger.error(f"❌ Get position history error: {e}")
            return []
    
    def get_position_stats(self) -> Dict:
        """
        Get aggregate position statistics
        
        Returns:
            Dictionary with statistics
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            # Total positions
            cursor.execute("""
                SELECT COUNT(*) FROM position_history
            """)
            total_positions = cursor.fetchone()[0]
            
            # Win rate
            cursor.execute("""
                SELECT COUNT(*) FROM position_history
                WHERE profit_loss_percent > 0
            """)
            winning_positions = cursor.fetchone()[0]
            
            win_rate = (winning_positions / total_positions * 100) if total_positions > 0 else 0
            
            # Average P&L
            cursor.execute("""
                SELECT AVG(profit_loss_percent) FROM position_history
            """)
            avg_pl = cursor.fetchone()[0] or 0
            
            # Average duration
            cursor.execute("""
                SELECT AVG(duration_hours) FROM position_history
            """)
            avg_duration = cursor.fetchone()[0] or 0
            
            # Checkpoint effectiveness
            cursor.execute("""
                SELECT AVG(checkpoints_triggered) FROM position_history
            """)
            avg_checkpoints = cursor.fetchone()[0] or 0
            
            # Open positions
            cursor.execute("""
                SELECT COUNT(*) FROM open_positions
                WHERE status IN ('OPEN', 'PARTIAL')
            """)
            open_positions = cursor.fetchone()[0]
            
            conn.close()
            
            stats = {
                'total_positions': total_positions,
                'winning_positions': winning_positions,
                'losing_positions': total_positions - winning_positions,
                'win_rate': win_rate,
                'avg_pl_percent': avg_pl,
                'avg_duration_hours': avg_duration,
                'avg_checkpoints_triggered': avg_checkpoints,
                'open_positions': open_positions
            }
            
            logger.info(f"📊 Position stats: {total_positions} total, {win_rate:.1f}% win rate")
            
            return stats
            
        except Exception as e:
            logger.error(f"❌ Get position stats error: {e}")
            return {}


if __name__ == "__main__":
    """Test Position Manager functionality"""
    print("\n" + "=" * 70)
    print("  POSITION MANAGER - TEST")
    print("=" * 70 + "\n")
    
    manager = PositionManager()
    
    # Test get open positions
    positions = manager.get_open_positions()
    print(f"Open positions: {len(positions)}")
    
    # Test get stats
    stats = manager.get_position_stats()
    print(f"Stats: {stats}")
    
    print("\n" + "=" * 70)
    print("  ✅ Position Manager test complete!")
    print("=" * 70 + "\n")
