"""
Setup State Machine - POI Persistence Layer
Manages pending entry setups with TTL tracking.

Author: galinborisov10-art
Date: 2026-03-08
"""

from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


# ============================================================
# TTL CONFIGURATION (Cycle-Based)
# ============================================================

# TTL measured in evaluation cycles, not candle timestamps
TTL_CYCLES_BY_TIMEFRAME = {
    '1m': 30,   # 30 minutes / 1min = 30 cycles
    '5m': 24,   # 2 hours / 5min = 24 cycles
    '15m': 16,  # 4 hours / 15min = 16 cycles
    '30m': 12,  # 6 hours / 30min = 12 cycles
    '1h': 12,   # 12 hours / 1h = 12 cycles
    '2h': 8,    # 16 hours / 2h = 8 cycles (default)
    '4h': 6,    # 24 hours / 4h = 6 cycles
    '6h': 6,    # 36 hours / 6h = 6 cycles
    '8h': 5,    # 40 hours / 8h = 5 cycles
    '12h': 4,   # 48 hours / 12h = 4 cycles
    '1d': 4,    # 4 days / 1d = 4 cycles
    '3d': 3,    # 9 days / 3d = 3 cycles
    '1w': 2,    # 2 weeks / 1w = 2 cycles
}

DEFAULT_TTL_CYCLES = 8


@dataclass
class SetupState:
    """
    Represents a pending entry setup (scenario detected, waiting for entry trigger).
    """
    symbol: str
    timeframe: str
    scenario_name: str
    scenario_data: Dict
    entry_zone: Dict
    ttl_remaining: int
    created_at: datetime = field(default_factory=datetime.now)
    last_checked_at: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        """Convert to JSON-serializable dict for logging."""
        return {
            'symbol': self.symbol,
            'timeframe': self.timeframe,
            'scenario_name': self.scenario_name,
            'entry_zone': self.entry_zone,
            'ttl_remaining': self.ttl_remaining,
            'created_at': self.created_at.isoformat(),
            'last_checked_at': self.last_checked_at.isoformat()
        }


class SetupStateManager:
    """
    In-memory state machine for managing pending entry setups.
    """
    
    def __init__(self):
        """Initialize empty state store."""
        self._setups: Dict[Tuple[str, str], SetupState] = {}
    
    def get_ttl_for_timeframe(self, timeframe: str) -> int:
        """Get TTL cycles for a given timeframe."""
        return TTL_CYCLES_BY_TIMEFRAME.get(timeframe, DEFAULT_TTL_CYCLES)
    
    def create_setup(
        self,
        symbol: str,
        timeframe: str,
        scenario_name: str,
        scenario_data: Dict,
        entry_zone: Dict
    ) -> SetupState:
        """
        Create and store a new pending setup.
        
        Args:
            symbol: Trading symbol (e.g., 'BTCUSDT')
            timeframe: Trading timeframe (e.g., '2h')
            scenario_name: Scenario type ('ROLLBACK', 'PULLBACK', etc.)
            scenario_data: Full scenario dict from scenario scoring
            entry_zone: Entry zone dict
            
        Returns:
            Created SetupState
        """
        ttl = self.get_ttl_for_timeframe(timeframe)
        
        setup = SetupState(
            symbol=symbol,
            timeframe=timeframe,
            scenario_name=scenario_name,
            scenario_data=scenario_data,
            entry_zone=entry_zone,
            ttl_remaining=ttl
        )
        
        key = (symbol, timeframe)
        self._setups[key] = setup
        
        logger.info(
            f"🧠 SETUP_DETECTED scenario={scenario_name} tf={timeframe} "
            f"symbol={symbol} ttl={ttl} entry=${entry_zone.get('center', 0):.2f}"
        )
        
        return setup
    
    def get_setup(self, symbol: str, timeframe: str) -> Optional[SetupState]:
        """
        Get active setup for symbol/timeframe.
        
        Returns:
            SetupState if exists and TTL > 0, else None
        """
        key = (symbol, timeframe)
        setup = self._setups.get(key)
        
        if setup and setup.ttl_remaining > 0:
            return setup
        
        return None
    
    def decrement_ttl(self, symbol: str, timeframe: str) -> bool:
        """
        Decrement TTL for a setup.
        
        Returns:
            True if setup still active (TTL > 0), False if expired
        """
        key = (symbol, timeframe)
        setup = self._setups.get(key)
        
        if not setup:
            return False
        
        setup.ttl_remaining -= 1
        setup.last_checked_at = datetime.now()
        
        if setup.ttl_remaining <= 0:
            logger.info(
                f"⌛ SETUP_EXPIRED scenario={setup.scenario_name} tf={timeframe} "
                f"symbol={symbol} reason=ttl"
            )
            # Remove expired setup
            del self._setups[key]
            return False
        
        logger.debug(
            f"⏳ SETUP_PENDING_ENTRY scenario={setup.scenario_name} tf={timeframe} "
            f"symbol={symbol} ttl_remaining={setup.ttl_remaining}"
        )
        
        return True
    
    def mark_triggered(self, symbol: str, timeframe: str) -> None:
        """
        Mark setup as triggered and remove from active store.
        Ensures single-signal rule (no repeated signals from same setup).
        
        Args:
            symbol: Trading symbol
            timeframe: Trading timeframe
        """
        key = (symbol, timeframe)
        setup = self._setups.get(key)
        
        if setup:
            logger.info(
                f"🎯 ENTRY_TRIGGERED scenario={setup.scenario_name} tf={timeframe} "
                f"symbol={symbol}"
            )
            # Remove from active store to prevent duplicate signals
            del self._setups[key]
    
    def remove_setup(self, symbol: str, timeframe: str) -> None:
        """
        Remove a setup from the store (e.g., invalidated by context change).
        
        Args:
            symbol: Trading symbol
            timeframe: Trading timeframe
        """
        key = (symbol, timeframe)
        if key in self._setups:
            del self._setups[key]
    
    def get_all_setups(self) -> Dict[Tuple[str, str], SetupState]:
        """Get all active setups (for debugging/monitoring)."""
        return self._setups.copy()
    
    def clear_all(self) -> None:
        """Clear all setups (for testing)."""
        self._setups.clear()


# Global instance (singleton pattern)
_global_setup_manager: Optional[SetupStateManager] = None


def get_setup_manager() -> SetupStateManager:
    """Get or create the global setup state manager instance."""
    global _global_setup_manager
    if _global_setup_manager is None:
        _global_setup_manager = SetupStateManager()
    return _global_setup_manager
