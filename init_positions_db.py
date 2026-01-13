"""
🗄️ POSITION TRACKING DATABASE - INITIALIZATION
Creates database schema for automated position monitoring and re-analysis

Tables:
1. open_positions - Currently active positions with checkpoint tracking
2. checkpoint_alerts - Re-analysis results at each checkpoint
3. position_history - Closed positions with P&L and statistics

Author: galinborisov10-art
Date: 2026-01-13
PR: #7 - Full Auto Re-analysis Monitoring
"""

import sqlite3
import logging
from pathlib import Path
import os
from datetime import datetime, timezone

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


def create_positions_database():
    """
    Create positions database with all required tables
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        logger.info(f"📊 Creating positions database at: {DB_PATH}")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # ============================================
        # TABLE 1: OPEN_POSITIONS
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS open_positions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                
                -- Position details
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal_type TEXT NOT NULL,  -- 'BUY' or 'SELL'
                entry_price REAL NOT NULL,
                tp1_price REAL NOT NULL,
                tp2_price REAL,
                tp3_price REAL,
                sl_price REAL NOT NULL,
                current_size REAL DEFAULT 1.0,  -- 1.0 = 100%, 0.5 = 50% after partial close
                
                -- Original signal data (JSON serialized ICTSignal)
                original_signal_json TEXT NOT NULL,
                
                -- Timestamps
                opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_checked_at TIMESTAMP,
                
                -- Checkpoint tracking (0 = not triggered, 1 = triggered)
                checkpoint_25_triggered INTEGER DEFAULT 0,
                checkpoint_50_triggered INTEGER DEFAULT 0,
                checkpoint_75_triggered INTEGER DEFAULT 0,
                checkpoint_85_triggered INTEGER DEFAULT 0,
                
                -- Status
                status TEXT DEFAULT 'OPEN',  -- 'OPEN', 'PARTIAL', 'CLOSED'
                
                -- Metadata
                source TEXT,  -- 'AUTO', 'MANUAL'
                notes TEXT
            )
        """)
        
        logger.info("✅ Created table: open_positions")
        
        # ============================================
        # TABLE 2: CHECKPOINT_ALERTS
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS checkpoint_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL,
                checkpoint_level TEXT NOT NULL,  -- '25%', '50%', '75%', '85%'
                triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                trigger_price REAL NOT NULL,
                
                -- Re-analysis results
                original_confidence REAL,
                current_confidence REAL,
                confidence_delta REAL,
                htf_bias_changed INTEGER DEFAULT 0,
                structure_broken INTEGER DEFAULT 0,
                valid_components_count INTEGER,
                current_rr_ratio REAL,
                
                -- Recommendation
                recommendation TEXT NOT NULL,  -- 'HOLD', 'PARTIAL_CLOSE', 'CLOSE_NOW', 'MOVE_SL'
                reasoning TEXT,
                warnings TEXT,
                
                -- Action taken
                action_taken TEXT DEFAULT 'ALERTED',  -- 'NONE', 'ALERTED', 'AUTO_CLOSED', 'PARTIAL_CLOSED'
                
                FOREIGN KEY (position_id) REFERENCES open_positions(id)
            )
        """)
        
        logger.info("✅ Created table: checkpoint_alerts")
        
        # ============================================
        # TABLE 3: POSITION_HISTORY
        # ============================================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS position_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                position_id INTEGER NOT NULL,
                
                -- Position summary
                symbol TEXT NOT NULL,
                timeframe TEXT NOT NULL,
                signal_type TEXT NOT NULL,
                entry_price REAL NOT NULL,
                exit_price REAL NOT NULL,
                
                -- P&L
                profit_loss_percent REAL,
                profit_loss_usd REAL,
                
                -- Outcome
                outcome TEXT,  -- 'TP1', 'TP2', 'TP3', 'SL', 'MANUAL_CLOSE', 'EARLY_EXIT'
                
                -- Timestamps
                opened_at TIMESTAMP,
                closed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                duration_hours REAL,
                
                -- Stats
                checkpoints_triggered INTEGER DEFAULT 0,
                recommendations_received INTEGER DEFAULT 0,
                
                FOREIGN KEY (position_id) REFERENCES open_positions(id)
            )
        """)
        
        logger.info("✅ Created table: position_history")
        
        # ============================================
        # CREATE INDEXES FOR PERFORMANCE
        # ============================================
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_open_positions_status 
            ON open_positions(status)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_open_positions_symbol 
            ON open_positions(symbol)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_checkpoint_alerts_position 
            ON checkpoint_alerts(position_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_position_history_closed_at 
            ON position_history(closed_at DESC)
        """)
        
        logger.info("✅ Created indexes for performance")
        
        # Commit and close
        conn.commit()
        conn.close()
        
        logger.info("✅ Positions database created successfully!")
        logger.info(f"   Database path: {DB_PATH}")
        logger.info(f"   Tables: open_positions, checkpoint_alerts, position_history")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Database creation failed: {e}")
        return False


def verify_database():
    """
    Verify database was created correctly
    
    Returns:
        bool: True if verification passed
    """
    try:
        if not os.path.exists(DB_PATH):
            logger.error(f"❌ Database file not found: {DB_PATH}")
            return False
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Check tables exist
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' 
            ORDER BY name
        """)
        
        tables = [row[0] for row in cursor.fetchall()]
        expected_tables = ['checkpoint_alerts', 'open_positions', 'position_history']
        
        for table in expected_tables:
            if table in tables:
                logger.info(f"✅ Table verified: {table}")
            else:
                logger.error(f"❌ Table missing: {table}")
                return False
        
        # Check indexes
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='index'
            ORDER BY name
        """)
        
        indexes = [row[0] for row in cursor.fetchall()]
        logger.info(f"✅ Indexes created: {len(indexes)}")
        
        conn.close()
        
        logger.info("✅ Database verification passed!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database verification failed: {e}")
        return False


def reset_database():
    """
    Reset database (delete and recreate)
    WARNING: This will delete all data!
    
    Returns:
        bool: True if successful
    """
    try:
        if os.path.exists(DB_PATH):
            logger.warning(f"⚠️  Deleting existing database: {DB_PATH}")
            os.remove(DB_PATH)
        
        return create_positions_database()
        
    except Exception as e:
        logger.error(f"❌ Database reset failed: {e}")
        return False


if __name__ == "__main__":
    """Initialize database when run directly"""
    print("\n" + "=" * 70)
    print("  POSITION TRACKING DATABASE - INITIALIZATION")
    print("  PR #7: Full Auto Re-analysis Monitoring")
    print("=" * 70 + "\n")
    
    success = create_positions_database()
    
    if success:
        verify_database()
        print("\n" + "=" * 70)
        print("  ✅ Database initialization complete!")
        print("=" * 70 + "\n")
    else:
        print("\n" + "=" * 70)
        print("  ❌ Database initialization failed!")
        print("=" * 70 + "\n")
