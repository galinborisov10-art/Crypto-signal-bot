#!/usr/bin/env python3
"""
Persistent signal deduplication cache
Prevents duplicate signals across bot restarts
"""

import os
import json
from datetime import datetime, timedelta

SENT_SIGNALS_FILE = 'sent_signals_cache.json'
CACHE_CLEANUP_HOURS = 24  # Clean entries older than 24 hours

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
                
                # Clean old entries (older than CACHE_CLEANUP_HOURS)
                cutoff = datetime.now().timestamp() - timedelta(hours=CACHE_CLEANUP_HOURS).total_seconds()
                cache = {
                    k: v for k, v in cache.items() 
                    if datetime.fromisoformat(v['timestamp']).timestamp() > cutoff
                }
                return cache
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
    Check if signal is duplicate (persistent across restarts)
    
    Args:
        symbol: Trading pair (e.g., 'BTCUSDT')
        signal_type: 'BUY' or 'SELL'
        timeframe: Timeframe (e.g., '4h')
        entry_price: Entry price for proximity check
        confidence: Signal confidence level
        cooldown_minutes: Minimum time between duplicate signals (default 60)
        base_path: Base directory path
    
    Returns:
        tuple: (is_duplicate: bool, reason: str)
    """
    cache = load_sent_signals(base_path)
    
    signal_key = f"{symbol}_{signal_type}_{timeframe}"
    
    if signal_key in cache:
        last_sent = cache[signal_key]
        last_time = datetime.fromisoformat(last_sent['timestamp'])
        minutes_ago = (datetime.now() - last_time).total_seconds() / 60
        
        if minutes_ago < cooldown_minutes:
            # Check price proximity (within 0.5%)
            last_price = last_sent.get('entry_price', 0)
            if last_price > 0:
                price_diff_pct = abs((entry_price - last_price) / last_price) * 100
                
                if price_diff_pct < 0.5:
                    return True, f"Duplicate: Same signal sent {minutes_ago:.1f} min ago (price within 0.5%)"
            else:
                # No price data - check cooldown only
                return True, f"Duplicate: Same signal sent {minutes_ago:.1f} min ago"
    
    # Not duplicate - add to cache
    cache[signal_key] = {
        'timestamp': datetime.now().isoformat(),
        'entry_price': entry_price,
        'confidence': confidence
    }
    
    save_sent_signals(cache, base_path)
    return False, "New signal - added to cache"
