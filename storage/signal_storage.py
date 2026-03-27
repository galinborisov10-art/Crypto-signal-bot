"""
💾 SIGNAL STORAGE V2
Persists and retrieves SignalV2 objects using JSON file storage.

Author: galinborisov10-art
Version: 2.0
"""

import json
import logging
import os
import fcntl
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from models.signal import SignalV2, SignalDirection, SignalStrength, SignalStatus

logger = logging.getLogger(__name__)

_DEFAULT_STORAGE_PATH = "signals_v2.json"


class SignalStorageV2:
    """
    V2 Signal Storage

    Stores and retrieves SignalV2 objects as JSON records.
    Uses file locking to prevent corruption from concurrent writes.

    Args:
        storage_path: Path to the JSON storage file (default 'signals_v2.json')
        max_records: Maximum records to keep (oldest pruned, default 1000)
    """

    def __init__(
        self,
        storage_path: str = _DEFAULT_STORAGE_PATH,
        max_records: int = 1000,
    ):
        self.storage_path = storage_path
        self.max_records = max_records
        logger.info(f"SignalStorageV2 initialized (path={storage_path})")

    def save(self, signal: SignalV2) -> bool:
        """
        Persist a signal to storage.

        Args:
            signal: SignalV2 object to save

        Returns:
            True on success, False on failure
        """
        try:
            records = self._load_all_raw()
            records.append(signal.to_dict())
            # Prune oldest if over limit
            if len(records) > self.max_records:
                records = records[-self.max_records:]
            self._write_all_raw(records)
            logger.debug(f"SignalStorageV2: saved signal {signal.signal_id}")
            return True
        except Exception as e:
            logger.error(f"SignalStorageV2: save failed: {e}")
            return False

    def load_latest(self, n: int = 10) -> List[SignalV2]:
        """
        Load the N most recent signals.

        Args:
            n: Number of signals to return

        Returns:
            List of SignalV2 objects (most recent first)
        """
        records = self._load_all_raw()
        signals = []
        for r in reversed(records[-n:]):
            sig = self._from_dict(r)
            if sig:
                signals.append(sig)
        return signals

    def load_by_symbol(self, symbol: str) -> List[SignalV2]:
        """Load all signals for a specific symbol"""
        records = self._load_all_raw()
        signals = []
        for r in records:
            if r.get("symbol") == symbol:
                sig = self._from_dict(r)
                if sig:
                    signals.append(sig)
        return signals

    def load_by_id(self, signal_id: str) -> Optional[SignalV2]:
        """Load a specific signal by its ID"""
        records = self._load_all_raw()
        for r in records:
            if r.get("signal_id") == signal_id:
                return self._from_dict(r)
        return None

    def count(self) -> int:
        """Return total number of stored signals"""
        return len(self._load_all_raw())

    def _load_all_raw(self) -> List[Dict[str, Any]]:
        """Load raw JSON records from file"""
        if not os.path.exists(self.storage_path):
            return []
        try:
            with open(self.storage_path, "r") as f:
                fcntl.flock(f, fcntl.LOCK_SH)
                try:
                    data = json.load(f)
                    return data if isinstance(data, list) else []
                finally:
                    fcntl.flock(f, fcntl.LOCK_UN)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"SignalStorageV2: could not read storage: {e}")
            return []

    def _write_all_raw(self, records: List[Dict[str, Any]]) -> None:
        """Write raw JSON records to file with exclusive lock"""
        with open(self.storage_path, "w") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                json.dump(records, f, indent=2, default=str)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)

    @staticmethod
    def _from_dict(data: Dict[str, Any]) -> Optional[SignalV2]:
        """Deserialize a SignalV2 from a dict"""
        try:
            return SignalV2(
                signal_id=data["signal_id"],
                symbol=data["symbol"],
                timeframe=data["timeframe"],
                direction=SignalDirection(data["direction"]),
                entry_price=float(data["entry_price"]),
                entry_zone_low=float(data["entry_zone_low"]),
                entry_zone_high=float(data["entry_zone_high"]),
                stop_loss=float(data["stop_loss"]),
                take_profit_1=float(data["take_profit_1"]),
                take_profit_2=float(data["take_profit_2"]),
                take_profit_3=float(data["take_profit_3"]),
                confidence=float(data["confidence"]),
                strength=SignalStrength(data["strength"]),
                status=SignalStatus(data.get("status", "PENDING")),
                created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat())),
                components=data.get("components", []),
                htf_bias=data.get("htf_bias", "UNKNOWN"),
                anchor_level=data.get("anchor_level"),
                risk_reward_ratio=float(data.get("risk_reward_ratio", 0.0)),
                notes=data.get("notes", ""),
            )
        except (KeyError, ValueError, TypeError) as e:
            logger.warning(f"SignalStorageV2: could not deserialize signal: {e}")
            return None
