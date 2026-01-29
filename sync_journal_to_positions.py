"""
🔄 JOURNAL TO POSITIONS SYNC
============================

Synchronizes pending trades from trading_journal.json to positions.db
for checkpoint monitoring by UnifiedTradeManager.

Purpose:
- Read PENDING trades from trading_journal.json (source of truth)
- Add them to positions.db (tracking database)
- Enable checkpoint monitoring for all journal trades

Features:
- Idempotent (safe to run multiple times)
- Duplicate detection (skips existing positions)
- Comprehensive logging
- Error handling

Author: galinborisov10-art
Date: 2026-01-28
"""

import json
import os
import logging
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass

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

JOURNAL_PATH = os.path.join(BASE_PATH, 'trading_journal.json')


@dataclass
class MockSignal:
    """
    Mock ICTSignal object created from journal trade data
    
    Used to pass journal trade data to position_manager.open_position()
    which expects an ICTSignal-like object.
    """
    timestamp: str
    symbol: str
    timeframe: str
    signal_type: str
    entry_price: float
    sl_price: float
    tp_prices: List[float]
    confidence: float
    risk_reward_ratio: float = 0.0
    bias: str = 'UNKNOWN'
    htf_bias: Optional[str] = None
    
    def __post_init__(self):
        """Ensure tp_prices is a list"""
        if self.tp_prices is None:
            self.tp_prices = []
        elif not isinstance(self.tp_prices, list):
            self.tp_prices = [self.tp_prices]


def load_journal() -> Optional[Dict]:
    """
    Load trading journal
    
    Returns:
        Journal dict or None if error
    """
    try:
        if not os.path.exists(JOURNAL_PATH):
            logger.warning(f"⚠️  Journal not found: {JOURNAL_PATH}")
            return None
        
        with open(JOURNAL_PATH, 'r') as f:
            journal = json.load(f)
        
        logger.info(f"✅ Loaded journal: {len(journal.get('trades', []))} total trades")
        return journal
        
    except Exception as e:
        logger.error(f"❌ Error loading journal: {e}")
        return None


def get_pending_trades(journal: Dict) -> List[Dict]:
    """
    Filter pending trades from journal
    
    Args:
        journal: Journal dictionary
        
    Returns:
        List of pending trades
    """
    if not journal or 'trades' not in journal:
        return []
    
    pending = [
        trade for trade in journal['trades']
        if trade.get('status') == 'PENDING'
    ]
    
    logger.info(f"📊 Found {len(pending)} PENDING trades in journal")
    return pending


def create_mock_signal(trade: Dict) -> MockSignal:
    """
    Create MockSignal from journal trade data
    
    Args:
        trade: Trade dictionary from journal
        
    Returns:
        MockSignal object
    """
    # Extract TP prices (handle both single TP and multiple TPs)
    tp_price = trade.get('tp_price', 0)
    tp_prices = [tp_price] if tp_price else []
    
    # If trade has tp1, tp2, tp3 fields, use those instead
    if 'tp1_price' in trade:
        tp_prices = []
        if trade.get('tp1_price'):
            tp_prices.append(trade['tp1_price'])
        if trade.get('tp2_price'):
            tp_prices.append(trade['tp2_price'])
        if trade.get('tp3_price'):
            tp_prices.append(trade['tp3_price'])
    
    # Create signal
    signal = MockSignal(
        timestamp=trade.get('timestamp', datetime.now().isoformat()),
        symbol=trade.get('symbol', ''),
        timeframe=trade.get('timeframe', ''),
        signal_type=trade.get('signal', ''),
        entry_price=trade.get('entry_price', 0),
        sl_price=trade.get('sl_price', 0),
        tp_prices=tp_prices,
        confidence=trade.get('confidence', 0),
        risk_reward_ratio=0.0,  # Not stored in journal
        bias='UNKNOWN',  # Not stored in journal
        htf_bias=None  # Not stored in journal
    )
    
    return signal


def check_position_exists(position_manager, symbol: str, timeframe: str, entry_price: float) -> bool:
    """
    Check if position already exists in database
    
    Args:
        position_manager: PositionManager instance
        symbol: Trading symbol
        timeframe: Timeframe
        entry_price: Entry price
        
    Returns:
        True if position exists
    """
    try:
        open_positions = position_manager.get_open_positions()
        
        for pos in open_positions:
            # Match by symbol, timeframe, and entry price (with 0.01% tolerance)
            if (pos.get('symbol') == symbol and 
                pos.get('timeframe') == timeframe):
                # Use percentage-based comparison for entry price
                pos_entry = pos.get('entry_price', 0)
                if pos_entry > 0:
                    price_diff_pct = abs(pos_entry - entry_price) / pos_entry
                    if price_diff_pct < 0.0001:  # 0.01% tolerance
                        return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error checking position existence: {e}")
        return False


def sync_journal_to_positions() -> Dict[str, int]:
    """
    Main sync function - sync pending journal trades to positions.db
    
    Returns:
        Dictionary with sync statistics: {added, skipped, errors}
    """
    stats = {
        'added': 0,
        'skipped': 0,
        'errors': 0
    }
    
    logger.info("=" * 70)
    logger.info("🔄 JOURNAL TO POSITIONS SYNC - START")
    logger.info("=" * 70)
    
    try:
        # Import PositionManager
        from position_manager import PositionManager
        position_manager = PositionManager()
        
    except ImportError as e:
        logger.error(f"❌ Cannot import PositionManager: {e}")
        stats['errors'] = 1
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to initialize PositionManager: {e}")
        stats['errors'] = 1
        return stats
    
    # Load journal
    journal = load_journal()
    if not journal:
        logger.error("❌ Failed to load journal")
        return stats
    
    # Get pending trades
    pending_trades = get_pending_trades(journal)
    if not pending_trades:
        logger.info("ℹ️  No pending trades to sync")
        return stats
    
    # Process each pending trade
    for trade in pending_trades:
        try:
            trade_id = trade.get('id', 'unknown')
            symbol = trade.get('symbol', '')
            timeframe = trade.get('timeframe', '')
            signal_type = trade.get('signal', '')
            entry_price = trade.get('entry_price', 0)
            
            logger.info(f"\n📝 Processing trade #{trade_id}: {symbol} {signal_type} @ ${entry_price}")
            
            # Validate required fields
            if not symbol:
                logger.error(f"   ❌ SKIPPED - Missing symbol")
                stats['errors'] += 1
                continue
            
            if not timeframe:
                logger.error(f"   ❌ SKIPPED - Missing timeframe")
                stats['errors'] += 1
                continue
            
            if entry_price <= 0:
                logger.error(f"   ❌ SKIPPED - Invalid entry price: {entry_price}")
                stats['errors'] += 1
                continue
            
            # Check if already exists
            if check_position_exists(position_manager, symbol, timeframe, entry_price):
                logger.debug(f"   ⏭️  SKIPPED - Position already exists")
                stats['skipped'] += 1
                continue
            
            # Create mock signal
            signal = create_mock_signal(trade)
            
            # Add to position tracking
            position_id = position_manager.open_position(
                signal=signal,
                symbol=symbol,
                timeframe=timeframe,
                source='JOURNAL_SYNC'
            )
            
            if position_id > 0:
                logger.info(f"   ✅ ADDED - Position ID: {position_id}")
                stats['added'] += 1
            else:
                logger.error(f"   ❌ ERROR - Failed to add position")
                stats['errors'] += 1
                
        except Exception as e:
            logger.error(f"   ❌ ERROR - Exception: {e}")
            stats['errors'] += 1
    
    # Summary
    logger.info("\n" + "=" * 70)
    logger.info("🔄 JOURNAL TO POSITIONS SYNC - COMPLETE")
    logger.info("=" * 70)
    logger.info(f"✅ Added:   {stats['added']}")
    logger.info(f"⏭️  Skipped: {stats['skipped']}")
    logger.info(f"❌ Errors:  {stats['errors']}")
    logger.info("=" * 70 + "\n")
    
    return stats


if __name__ == "__main__":
    """Run sync when script is executed directly"""
    sync_journal_to_positions()
