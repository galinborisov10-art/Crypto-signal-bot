#!/usr/bin/env python3
"""
Ultra-Simple Entry-Based Deduplication (PR #118)

PRINCIPLE:
  Entry price is THE key indicator of ICT setup uniqueness.
  If entry differs by ≥1.5%, it's a DIFFERENT market structure zone.
  
  All other parameters (SL/TP/ICT components) correlate with entry,
  so checking entry alone is sufficient.

RATIONALE:
  - Order Blocks: ~1-2% wide
  - Fair Value Gaps: ~0.5-2% wide
  - Liquidity zones: ~1-3% apart
  - 1.5% threshold captures different ICT zones

PROVEN:
  Real data (14.01.2026): 44 signals → 5 unique (88.6% duplicates filtered)
  All duplicates had SAME entry price (0% difference)
"""

import os
import json
import logging
from datetime import datetime, timedelta

try:
    from position_manager import PositionManager
    POSITION_MANAGER_AVAILABLE = True
except ImportError:
    POSITION_MANAGER_AVAILABLE = False
    PositionManager = None

logger = logging.getLogger(__name__)

SENT_SIGNALS_FILE = 'sent_signals_cache.json'
CACHE_CLEANUP_HOURS = 168  # Clean entries older than 7 days (was 24h - too aggressive)
ENTRY_THRESHOLD_PCT = 1.5  # Entry price difference threshold for uniqueness


def _check_if_position_active(position_manager, signal_key):
    """Check if signal_key has active position using existing API"""
    try:
        # Parse signal_key: "BTCUSDT_BUY_4h"
        parts = signal_key.split('_')
        if len(parts) < 3:
            return False
        
        timeframe = parts[-1]
        signal_type = parts[-2]
        symbol = '_'.join(parts[:-2])
        
        # Use EXISTING get_open_positions() method
        positions = position_manager.get_open_positions()
        
        # Check if any position matches
        for pos in positions:
            if (pos.get('symbol') == symbol and 
                pos.get('signal_type') == signal_type and 
                pos.get('timeframe') == timeframe and
                pos.get('status') in ['OPEN', 'PARTIAL']):
                return True
        
        return False
    except:
        return False


def load_sent_signals(base_path=None):
    """
    Load sent signals from persistent JSON file
    
    Returns:
        dict: Signal cache with timestamp and metadata
    """
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    file_path = os.path.join(base_path, SENT_SIGNALS_FILE)
    
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                cache = json.load(f)
                
                print(f"✅ Loaded {len(cache)} signals from cache")
                
                # Clean old entries (older than CACHE_CLEANUP_HOURS)
                before_cleanup = len(cache)
                cutoff = datetime.now().timestamp() - timedelta(hours=CACHE_CLEANUP_HOURS).total_seconds()
                
                # Initialize PositionManager once (if available)
                position_manager = None
                if POSITION_MANAGER_AVAILABLE and PositionManager is not None:
                    try:
                        position_manager = PositionManager()
                    except Exception as e:
                        logger.warning(f"⚠️ Could not initialize PositionManager: {e}")
                
                cleaned_cache = {}
                deleted_count = 0
                preserved_count = 0
                cache_modified = False
                
                for signal_key, signal_data in cache.items():
                    timestamp_str = signal_data.get('last_checked', signal_data.get('timestamp'))
                    
                    try:
                        signal_timestamp = datetime.fromisoformat(timestamp_str).timestamp()
                    except (ValueError, TypeError):
                        # GUARD: Even with corrupted timestamp, check for active position
                        if position_manager and _check_if_position_active(position_manager, signal_key):
                            # Preserve entry with corrupted timestamp if position is active
                            cleaned_cache[signal_key] = signal_data
                            preserved_count += 1
                            logger.warning(f"⚠️ Preserved entry with corrupted timestamp for active position: {signal_key}")
                        else:
                            deleted_count += 1
                            cache_modified = True
                        continue
                    
                    # Check if entry is older than cutoff
                    if signal_timestamp < cutoff:
                        # GUARD: Check if there's an active position for this signal
                        if position_manager and _check_if_position_active(position_manager, signal_key):
                            # DO NOT DELETE - active position exists
                            cleaned_cache[signal_key] = signal_data
                            preserved_count += 1
                            logger.info(f"🛡️ Preserved cache entry for active position: {signal_key}")
                        else:
                            # Safe to delete - no active position
                            deleted_count += 1
                            cache_modified = True
                    else:
                        # Entry is fresh - keep it
                        cleaned_cache[signal_key] = signal_data
                
                if preserved_count > 0 or deleted_count > 0:
                    logger.info(f"Cache cleanup: {len(cleaned_cache)} kept, {deleted_count} deleted, {preserved_count} preserved")
                
                # Save cleaned cache if changed
                if cache_modified:
                    save_sent_signals(cleaned_cache, base_path)
                
                return cleaned_cache
        else:
            print(f"⚠️ Cache file not found, creating new cache")
            return {}
    except Exception as e:
        print(f"⚠️ Error loading signal cache: {e}")
        return {}


def save_sent_signals(cache, base_path=None):
    """
    Save sent signals to persistent JSON file
    
    Args:
        cache: Signal cache dict
        base_path: Base directory path
    """
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    file_path = os.path.join(base_path, SENT_SIGNALS_FILE)
    
    try:
        with open(file_path, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"❌ Error saving signal cache: {e}")


def is_signal_duplicate(symbol, signal_type, timeframe, entry_price, 
                        confidence, cooldown_minutes=60, base_path=None):
    """
    Check if signal is duplicate using ONLY entry price comparison
    
    Simplified logic:
    - Compare entry_price with last signal for same symbol/type/timeframe
    - If difference >= 1.5% → NEW signal
    - If difference < 1.5% → DUPLICATE
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        signal_type: 'BUY', 'SELL', or 'STRONG_BUY'
        timeframe: Timeframe (e.g., '4h')
        entry_price: Entry price for comparison
        confidence: Signal confidence (stored but not used for duplicate check)
        cooldown_minutes: DEPRECATED - kept for compatibility but NOT used
        base_path: Base directory path
    
    Returns:
        tuple: (is_duplicate: bool, reason: str)
    """
    cache = load_sent_signals(base_path)
    
    # Create key WITHOUT entry_price (different from PR #117)
    signal_key = f"{symbol}_{signal_type}_{timeframe}"
    
    if signal_key not in cache:
        # First signal for this combination
        cache[signal_key] = {
            'timestamp': datetime.now().isoformat(),      # When SENT
            'last_checked': datetime.now().isoformat(),   # When CHECKED
            'entry_price': entry_price,
            'confidence': confidence
        }
        save_sent_signals(cache, base_path)
        
        print(f"✅ NEW signal (first): {signal_key} @ ${entry_price}")
        return False, "First signal for this symbol/direction/timeframe"
    
    # Compare entry prices
    last_entry = cache[signal_key]['entry_price']
    
    # Validate entry prices to prevent division by zero
    if last_entry == 0:
        print(f"⚠️ WARNING: Invalid last_entry (0) for {signal_key}, treating as first signal")
        cache[signal_key] = {
            'timestamp': datetime.now().isoformat(),
            'last_checked': datetime.now().isoformat(),
            'entry_price': entry_price,
            'confidence': confidence
        }
        save_sent_signals(cache, base_path)
        return False, "Invalid cached entry price, treating as new signal"
    
    entry_diff_pct = abs((entry_price - last_entry) / last_entry) * 100
    
    if entry_diff_pct >= ENTRY_THRESHOLD_PCT:
        # Significant difference → NEW unique setup
        old_entry = cache[signal_key]['entry_price']
        cache[signal_key] = {
            'timestamp': datetime.now().isoformat(),      # New SENT time
            'last_checked': datetime.now().isoformat(),   # New CHECK time
            'entry_price': entry_price,
            'confidence': confidence
        }
        save_sent_signals(cache, base_path)
        
        print(f"✅ NEW signal (entry diff): {signal_key}")
        print(f"   Old entry: ${old_entry}, New entry: ${entry_price} (Δ{entry_diff_pct:.2f}%)")
        return False, f"Entry difference: {entry_diff_pct:.2f}% (>={ENTRY_THRESHOLD_PCT}%)"
    else:
        # Too similar → DUPLICATE
        last_time = cache[signal_key]['timestamp']
        
        # ✅ FIX: Update last_checked to prevent cleanup
        cache[signal_key]['last_checked'] = datetime.now().isoformat()
        save_sent_signals(cache, base_path)  # ✅ SAVE cache
        
        print(f"🔴 DUPLICATE blocked: {signal_key}")
        print(f"   Entry: ${entry_price} vs ${last_entry} (Δ{entry_diff_pct:.2f}% < {ENTRY_THRESHOLD_PCT}%)")
        print(f"   Last sent: {last_time}")
        return True, f"Entry diff: {entry_diff_pct:.2f}% (<{ENTRY_THRESHOLD_PCT}%), last sent: {last_time}"


def validate_cache(base_path=None):
    """
    Validate cache integrity on bot startup
    
    Returns:
        tuple: (is_valid: bool, message: str)
    """
    if base_path is None:
        base_path = os.path.dirname(os.path.abspath(__file__))
    
    file_path = os.path.join(base_path, SENT_SIGNALS_FILE)
    
    # Check file exists
    if not os.path.exists(file_path):
        return True, "Cache file doesn't exist (will be created)"
    
    # Check file size
    file_size = os.path.getsize(file_path)
    if file_size > 10 * 1024 * 1024:  # 10MB
        return False, f"Cache file too large ({file_size / (1024*1024):.1f}MB)"
    
    # Check JSON validity
    try:
        with open(file_path, 'r') as f:
            cache = json.load(f)
            
        if not isinstance(cache, dict):
            return False, "Cache is not a dictionary"
        
        # Check entry format
        for key, value in list(cache.items())[:5]:  # Check first 5
            if not isinstance(value, dict):
                return False, f"Invalid entry format for key: {key}"
            
            if 'timestamp' not in value:
                return False, f"Missing timestamp in entry: {key}"
        
        return True, f"Cache valid ({len(cache)} entries)"
        
    except json.JSONDecodeError as e:
        return False, f"Corrupted JSON: {e}"
    except Exception as e:
        return False, f"Validation error: {e}"
