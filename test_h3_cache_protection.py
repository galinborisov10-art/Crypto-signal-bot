#!/usr/bin/env python3
"""
Test suite for BUG H3: Prevent signal cache cleanup of active positions

Tests that cache cleanup respects active positions and never deletes
cache entries for trades that are still open.
"""

import os
import json
import sqlite3
import tempfile
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from signal_cache import load_sent_signals, save_sent_signals, CACHE_CLEANUP_HOURS


def create_test_position_db(db_path, positions):
    """Helper to create a test positions database with given positions"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS open_positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            signal_type TEXT NOT NULL,
            entry_price REAL NOT NULL,
            tp1_price REAL NOT NULL,
            sl_price REAL NOT NULL,
            current_size REAL DEFAULT 1.0,
            original_signal_json TEXT NOT NULL,
            opened_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_checked_at TIMESTAMP,
            checkpoint_25_triggered INTEGER DEFAULT 0,
            checkpoint_50_triggered INTEGER DEFAULT 0,
            checkpoint_75_triggered INTEGER DEFAULT 0,
            checkpoint_85_triggered INTEGER DEFAULT 0,
            status TEXT DEFAULT 'OPEN',
            source TEXT,
            notes TEXT
        )
    """)
    
    # Insert test positions
    for pos in positions:
        cursor.execute("""
            INSERT INTO open_positions 
            (symbol, timeframe, signal_type, entry_price, tp1_price, sl_price, status, original_signal_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pos['symbol'],
            pos['timeframe'],
            pos['signal_type'],
            pos.get('entry_price', 50000.0),
            pos.get('tp1_price', 52000.0),
            pos.get('sl_price', 49000.0),
            pos.get('status', 'OPEN'),
            '{"test": "signal"}'
        ))
    
    conn.commit()
    conn.close()


def test_1_cache_preserves_active_position():
    """
    Test: Cache preserves active position
    - Create a 10-day-old cache entry
    - Mock PositionManager to return True (active position exists)
    - Assert: Entry is preserved, not deleted
    """
    print("\n🧪 TEST 1: Cache preserves active position")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create cache with old entry (10 days old)
        cache_file = os.path.join(tmpdir, 'sent_signals_cache.json')
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
        
        cache = {
            'BTCUSDT_BUY_4h': {
                'timestamp': old_timestamp,
                'last_checked': old_timestamp,
                'entry_price': 50000.0,
                'confidence': 85
            }
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
        
        # Create test database with active position
        db_path = os.path.join(tmpdir, 'positions.db')
        create_test_position_db(db_path, [
            {
                'symbol': 'BTCUSDT',
                'signal_type': 'BUY',
                'timeframe': '4h',
                'status': 'OPEN'
            }
        ])
        
        # Mock PositionManager to use test database
        with patch('signal_cache.PositionManager') as MockPM:
            mock_pm_instance = MagicMock()
            mock_pm_instance.is_position_active.return_value = True
            MockPM.return_value = mock_pm_instance
            
            # Patch POSITION_MANAGER_AVAILABLE
            with patch('signal_cache.POSITION_MANAGER_AVAILABLE', True):
                # Load cache - should preserve the old entry
                loaded_cache = load_sent_signals(tmpdir)
        
        # Assertions
        assert 'BTCUSDT_BUY_4h' in loaded_cache, "Cache entry should be preserved"
        assert loaded_cache['BTCUSDT_BUY_4h']['entry_price'] == 50000.0
        print("✅ TEST 1 PASSED: Active position cache entry preserved")


def test_2_cache_deletes_inactive_stale_entry():
    """
    Test: Cache deletes inactive stale entry
    - Create a 10-day-old cache entry
    - Mock PositionManager to return False (no active position)
    - Assert: Entry is deleted
    """
    print("\n🧪 TEST 2: Cache deletes inactive stale entry")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create cache with old entry (10 days old)
        cache_file = os.path.join(tmpdir, 'sent_signals_cache.json')
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
        
        cache = {
            'ETHUSDT_SELL_1h': {
                'timestamp': old_timestamp,
                'last_checked': old_timestamp,
                'entry_price': 3000.0,
                'confidence': 75
            }
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
        
        # Mock PositionManager - no active position
        with patch('signal_cache.PositionManager') as MockPM:
            mock_pm_instance = MagicMock()
            mock_pm_instance.is_position_active.return_value = False
            MockPM.return_value = mock_pm_instance
            
            # Patch POSITION_MANAGER_AVAILABLE
            with patch('signal_cache.POSITION_MANAGER_AVAILABLE', True):
                # Load cache - should delete the old entry
                loaded_cache = load_sent_signals(tmpdir)
        
        # Assertions
        assert 'ETHUSDT_SELL_1h' not in loaded_cache, "Cache entry should be deleted"
        assert len(loaded_cache) == 0, "Cache should be empty"
        print("✅ TEST 2 PASSED: Inactive stale entry deleted")


def test_3_fallback_without_position_manager():
    """
    Test: Fallback without PositionManager
    - Simulate PositionManager unavailable
    - Assert: Cleanup proceeds without crash
    """
    print("\n🧪 TEST 3: Fallback without PositionManager")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create cache with old entry (10 days old)
        cache_file = os.path.join(tmpdir, 'sent_signals_cache.json')
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
        
        cache = {
            'XRPUSDT_BUY_2h': {
                'timestamp': old_timestamp,
                'last_checked': old_timestamp,
                'entry_price': 2.0,
                'confidence': 80
            }
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
        
        # Patch POSITION_MANAGER_AVAILABLE to False
        with patch('signal_cache.POSITION_MANAGER_AVAILABLE', False):
            with patch('signal_cache.PositionManager', None):
                # Load cache - should delete entry (no protection available)
                loaded_cache = load_sent_signals(tmpdir)
        
        # Assertions - without PositionManager, old entries are deleted
        assert 'XRPUSDT_BUY_2h' not in loaded_cache, "Old entry should be deleted when no PM available"
        print("✅ TEST 3 PASSED: Graceful fallback without PositionManager")


def test_4_fresh_entries_always_preserved():
    """
    Test: Fresh entries are always preserved
    - Create recent cache entries (1 day old)
    - Assert: All entries preserved regardless of position status
    """
    print("\n🧪 TEST 4: Fresh entries always preserved")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create cache with recent entry (1 day old - within 7 day window)
        cache_file = os.path.join(tmpdir, 'sent_signals_cache.json')
        recent_timestamp = (datetime.now() - timedelta(days=1)).isoformat()
        
        cache = {
            'BTCUSDT_BUY_4h': {
                'timestamp': recent_timestamp,
                'last_checked': recent_timestamp,
                'entry_price': 50000.0,
                'confidence': 85
            },
            'ETHUSDT_SELL_1h': {
                'timestamp': recent_timestamp,
                'last_checked': recent_timestamp,
                'entry_price': 3000.0,
                'confidence': 75
            }
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
        
        # Mock PositionManager - no positions
        with patch('signal_cache.PositionManager') as MockPM:
            mock_pm_instance = MagicMock()
            mock_pm_instance.is_position_active.return_value = False
            MockPM.return_value = mock_pm_instance
            
            # Patch POSITION_MANAGER_AVAILABLE
            with patch('signal_cache.POSITION_MANAGER_AVAILABLE', True):
                # Load cache - should keep all recent entries
                loaded_cache = load_sent_signals(tmpdir)
        
        # Assertions
        assert len(loaded_cache) == 2, "All fresh entries should be preserved"
        assert 'BTCUSDT_BUY_4h' in loaded_cache
        assert 'ETHUSDT_SELL_1h' in loaded_cache
        print("✅ TEST 4 PASSED: Fresh entries preserved")


def test_5_mixed_scenario():
    """
    Test: Mixed scenario with fresh, stale-active, and stale-inactive entries
    """
    print("\n🧪 TEST 5: Mixed scenario")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, 'sent_signals_cache.json')
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
        fresh_timestamp = (datetime.now() - timedelta(hours=12)).isoformat()
        
        cache = {
            'BTCUSDT_BUY_4h': {  # Old with active position - PRESERVE
                'timestamp': old_timestamp,
                'last_checked': old_timestamp,
                'entry_price': 50000.0,
                'confidence': 85
            },
            'ETHUSDT_SELL_1h': {  # Old without active position - DELETE
                'timestamp': old_timestamp,
                'last_checked': old_timestamp,
                'entry_price': 3000.0,
                'confidence': 75
            },
            'XRPUSDT_BUY_2h': {  # Fresh - KEEP
                'timestamp': fresh_timestamp,
                'last_checked': fresh_timestamp,
                'entry_price': 2.0,
                'confidence': 80
            }
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
        
        # Mock PositionManager
        with patch('signal_cache.PositionManager') as MockPM:
            mock_pm_instance = MagicMock()
            
            # Only BTCUSDT_BUY_4h has active position
            def mock_is_active(signal_key):
                return signal_key == 'BTCUSDT_BUY_4h'
            
            mock_pm_instance.is_position_active.side_effect = mock_is_active
            MockPM.return_value = mock_pm_instance
            
            with patch('signal_cache.POSITION_MANAGER_AVAILABLE', True):
                loaded_cache = load_sent_signals(tmpdir)
        
        # Assertions
        assert len(loaded_cache) == 2, "Should have 2 entries (preserved + fresh)"
        assert 'BTCUSDT_BUY_4h' in loaded_cache, "Active position entry preserved"
        assert 'ETHUSDT_SELL_1h' not in loaded_cache, "Inactive old entry deleted"
        assert 'XRPUSDT_BUY_2h' in loaded_cache, "Fresh entry kept"
        print("✅ TEST 5 PASSED: Mixed scenario handled correctly")


def test_6_partial_position_also_protected():
    """
    Test: Partial positions are also protected from cleanup
    """
    print("\n🧪 TEST 6: Partial position also protected")
    
    with tempfile.TemporaryDirectory() as tmpdir:
        cache_file = os.path.join(tmpdir, 'sent_signals_cache.json')
        old_timestamp = (datetime.now() - timedelta(days=10)).isoformat()
        
        cache = {
            'BTCUSDT_BUY_4h': {
                'timestamp': old_timestamp,
                'last_checked': old_timestamp,
                'entry_price': 50000.0,
                'confidence': 85
            }
        }
        
        with open(cache_file, 'w') as f:
            json.dump(cache, f)
        
        # Create database with PARTIAL status position
        db_path = os.path.join(tmpdir, 'positions.db')
        create_test_position_db(db_path, [
            {
                'symbol': 'BTCUSDT',
                'signal_type': 'BUY',
                'timeframe': '4h',
                'status': 'PARTIAL'  # Partial close - still active
            }
        ])
        
        # Mock PositionManager
        with patch('signal_cache.PositionManager') as MockPM:
            mock_pm_instance = MagicMock()
            mock_pm_instance.is_position_active.return_value = True
            MockPM.return_value = mock_pm_instance
            
            with patch('signal_cache.POSITION_MANAGER_AVAILABLE', True):
                loaded_cache = load_sent_signals(tmpdir)
        
        # Assertions
        assert 'BTCUSDT_BUY_4h' in loaded_cache, "Partial position entry preserved"
        print("✅ TEST 6 PASSED: Partial position protected")


def run_all_tests():
    """Run all tests"""
    print("=" * 70)
    print("🧪 BUG H3: Cache Protection for Active Positions - Test Suite")
    print("=" * 70)
    
    tests = [
        test_1_cache_preserves_active_position,
        test_2_cache_deletes_inactive_stale_entry,
        test_3_fallback_without_position_manager,
        test_4_fresh_entries_always_preserved,
        test_5_mixed_scenario,
        test_6_partial_position_also_protected
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} ERROR: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"📊 RESULTS: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == '__main__':
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)
