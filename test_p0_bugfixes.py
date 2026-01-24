#!/usr/bin/env python3
"""
P0 Bug Fixes Test Suite

Tests for:
- C1: Daily report log mismatch
- C3: trading_journal.json race condition (file locking)
- H3: Signal cache cleanup deletes active positions

Author: galinborisov10-art
Date: 2026-01-24
"""

import unittest
import tempfile
import os
import json
import time
import fcntl
from datetime import datetime, timedelta
from pathlib import Path
import sys
import sqlite3
from unittest.mock import patch, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestC1LogStringMatching(unittest.TestCase):
    """Test C1: Daily report log string matching between bot.py and system_diagnostics.py"""
    
    def test_log_string_matches(self):
        """Verify system_diagnostics.py searches for the same string bot.py emits"""
        
        # Extract the log string from bot.py
        bot_py_path = os.path.join(os.path.dirname(__file__), 'bot.py')
        with open(bot_py_path, 'r', encoding='utf-8') as f:
            bot_content = f.read()
        
        # Find the actual log message in bot.py (around line 17469)
        # Looking for: logger.info("✅ Daily report sent successfully")
        bot_log_string = None
        for line in bot_content.split('\n'):
            if 'Daily report sent successfully' in line and 'logger.info' in line:
                # Extract the string between quotes
                start = line.find('"') + 1
                end = line.find('"', start)
                if start > 0 and end > start:
                    bot_log_string = line[start:end]
                    break
        
        self.assertIsNotNone(bot_log_string, "Could not find daily report log message in bot.py")
        
        # Extract the search string from system_diagnostics.py
        diag_py_path = os.path.join(os.path.dirname(__file__), 'system_diagnostics.py')
        with open(diag_py_path, 'r', encoding='utf-8') as f:
            diag_content = f.read()
        
        # Find the grep_logs call (around line 468)
        diag_search_string = None
        for line in diag_content.split('\n'):
            if 'grep_logs' in line and 'Daily report' in line:
                # Extract the string between quotes
                start = line.find("'") + 1
                end = line.find("'", start)
                if start > 0 and end > start:
                    diag_search_string = line[start:end]
                    break
        
        self.assertIsNotNone(diag_search_string, "Could not find grep_logs call in system_diagnostics.py")
        
        # Verify they match
        self.assertEqual(
            bot_log_string, 
            diag_search_string,
            f"Log string mismatch:\n  bot.py: '{bot_log_string}'\n  system_diagnostics.py: '{diag_search_string}'"
        )
        
        print(f"✅ C1 Test Passed: Log strings match: '{bot_log_string}'")


class TestC3FileLocking(unittest.TestCase):
    """Test C3: trading_journal.json concurrent access with file locking"""
    
    def setUp(self):
        """Create temporary test files"""
        self.test_dir = tempfile.mkdtemp()
        self.journal_path = os.path.join(self.test_dir, 'trading_journal.json')
        
        # Initialize with empty journal
        with open(self.journal_path, 'w') as f:
            json.dump({'trades': []}, f)
    
    def tearDown(self):
        """Clean up test files"""
        if os.path.exists(self.journal_path):
            os.remove(self.journal_path)
        os.rmdir(self.test_dir)
    
    def test_exclusive_lock_prevents_concurrent_writes(self):
        """Test that exclusive lock prevents concurrent writes"""
        
        # Acquire exclusive lock
        with open(self.journal_path, 'r+') as f1:
            fcntl.flock(f1.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Try to acquire another exclusive lock (should fail with EWOULDBLOCK)
            with open(self.journal_path, 'r+') as f2:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(f2.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            
            # Release lock
            fcntl.flock(f1.fileno(), fcntl.LOCK_UN)
        
        print("✅ C3 Test 1 Passed: Exclusive lock prevents concurrent writes")
    
    def test_shared_lock_allows_concurrent_reads(self):
        """Test that multiple shared locks can coexist"""
        
        # Acquire first shared lock
        with open(self.journal_path, 'r') as f1:
            fcntl.flock(f1.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
            
            # Try to acquire another shared lock (should succeed)
            with open(self.journal_path, 'r') as f2:
                try:
                    fcntl.flock(f2.fileno(), fcntl.LOCK_SH | fcntl.LOCK_NB)
                    success = True
                except BlockingIOError:
                    success = False
                finally:
                    if success:
                        fcntl.flock(f2.fileno(), fcntl.LOCK_UN)
            
            self.assertTrue(success, "Multiple shared locks should be allowed")
            fcntl.flock(f1.fileno(), fcntl.LOCK_UN)
        
        print("✅ C3 Test 2 Passed: Shared locks allow concurrent reads")
    
    def test_read_modify_write_pattern(self):
        """Test read-modify-write pattern with locking"""
        
        # Simulate the pattern used in bot.py
        with open(self.journal_path, 'r+') as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                
                # Read
                journal = json.load(f)
                
                # Modify
                journal['trades'].append({
                    'timestamp': datetime.now().isoformat(),
                    'symbol': 'BTCUSDT',
                    'outcome': 'WIN'
                })
                
                # Write
                f.seek(0)
                f.truncate()
                json.dump(journal, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        
        # Verify the write succeeded
        with open(self.journal_path, 'r') as f:
            journal = json.load(f)
        
        self.assertEqual(len(journal['trades']), 1)
        self.assertEqual(journal['trades'][0]['symbol'], 'BTCUSDT')
        
        print("✅ C3 Test 3 Passed: Read-modify-write pattern works correctly")


class TestH3ActivePositionProtection(unittest.TestCase):
    """Test H3: Signal cache cleanup protects active positions"""
    
    def setUp(self):
        """Create temporary test environment"""
        self.test_dir = tempfile.mkdtemp()
        self.cache_path = os.path.join(self.test_dir, 'sent_signals_cache.json')
        self.db_path = os.path.join(self.test_dir, 'positions.db')
        
        # Create a mock database with an active position
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS open_positions (
                id INTEGER PRIMARY KEY,
                symbol TEXT,
                timeframe TEXT,
                signal_type TEXT,
                status TEXT
            )
        """)
        cursor.execute("""
            INSERT INTO open_positions (symbol, timeframe, signal_type, status)
            VALUES ('BTCUSDT', '4h', 'BUY', 'OPEN')
        """)
        conn.commit()
        conn.close()
        
        # Create cache with old and new entries
        now = datetime.now()
        old_time = (now - timedelta(hours=200)).isoformat()  # Older than 168h
        new_time = (now - timedelta(hours=50)).isoformat()   # Newer than 168h
        
        cache = {
            # Old entry for ACTIVE position (should be kept)
            'BTCUSDT_BUY_4h_50000.0': {
                'timestamp': old_time,
                'last_checked': old_time,
                'entry': 50000.0
            },
            # Old entry for INACTIVE position (should be deleted)
            'ETHUSDT_SELL_1h_3000.0': {
                'timestamp': old_time,
                'last_checked': old_time,
                'entry': 3000.0
            },
            # New entry (should be kept)
            'SOLUSDT_BUY_4h_100.0': {
                'timestamp': new_time,
                'last_checked': new_time,
                'entry': 100.0
            }
        }
        
        with open(self.cache_path, 'w') as f:
            json.dump(cache, f)
    
    def tearDown(self):
        """Clean up test files"""
        for file in [self.cache_path, self.db_path]:
            if os.path.exists(file):
                os.remove(file)
        os.rmdir(self.test_dir)
    
    def test_active_position_cache_protection(self):
        """Test that old cache entries for active positions are NOT deleted"""
        
        # Mock PositionManager
        class MockPositionManager:
            def __init__(self, db_path=None):
                self.db_path = db_path or self.db_path
            
            def get_open_positions(self):
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM open_positions WHERE status = 'OPEN'")
                rows = cursor.fetchall()
                conn.close()
                return [dict(row) for row in rows]
        
        # Import signal_cache module
        import signal_cache
        
        # Temporarily replace PositionManager
        original_pm = getattr(signal_cache, 'PositionManager', None)
        signal_cache.PositionManager = MockPositionManager
        signal_cache.POSITION_MANAGER_AVAILABLE = True
        
        # Mock the db_path in MockPositionManager
        MockPositionManager.db_path = self.db_path
        
        try:
            # Load signals (will trigger cleanup)
            cache = signal_cache.load_sent_signals(base_path=self.test_dir)
            
            # Verify results
            self.assertIn('BTCUSDT_BUY_4h_50000.0', cache, 
                         "Active position cache entry should be kept despite age")
            self.assertNotIn('ETHUSDT_SELL_1h_3000.0', cache,
                            "Inactive old position cache entry should be deleted")
            self.assertIn('SOLUSDT_BUY_4h_100.0', cache,
                         "New cache entry should be kept")
            
            print("✅ H3 Test 1 Passed: Active position cache entries are protected")
        
        finally:
            # Restore original PositionManager
            if original_pm:
                signal_cache.PositionManager = original_pm
    
    def test_fallback_when_position_manager_unavailable(self):
        """Test that cleanup works when position_manager is unavailable"""
        
        # Import signal_cache module
        import signal_cache
        
        # Temporarily disable PositionManager
        original_available = signal_cache.POSITION_MANAGER_AVAILABLE
        signal_cache.POSITION_MANAGER_AVAILABLE = False
        
        try:
            # Load signals (will trigger cleanup without position check)
            cache = signal_cache.load_sent_signals(base_path=self.test_dir)
            
            # Verify results - both old entries should be deleted
            self.assertNotIn('BTCUSDT_BUY_4h_50000.0', cache,
                            "Old entry should be deleted when position manager unavailable")
            self.assertNotIn('ETHUSDT_SELL_1h_3000.0', cache,
                            "Old entry should be deleted")
            self.assertIn('SOLUSDT_BUY_4h_100.0', cache,
                         "New cache entry should be kept")
            
            print("✅ H3 Test 2 Passed: Cleanup works when position manager unavailable")
        
        finally:
            # Restore original state
            signal_cache.POSITION_MANAGER_AVAILABLE = original_available


def run_tests():
    """Run all P0 bug fix tests"""
    print("\n" + "=" * 70)
    print("  P0 BUG FIXES TEST SUITE")
    print("=" * 70 + "\n")
    
    # Create test suite
    suite = unittest.TestSuite()
    
    # Add C1 tests
    suite.addTest(TestC1LogStringMatching('test_log_string_matches'))
    
    # Add C3 tests
    suite.addTest(TestC3FileLocking('test_exclusive_lock_prevents_concurrent_writes'))
    suite.addTest(TestC3FileLocking('test_shared_lock_allows_concurrent_reads'))
    suite.addTest(TestC3FileLocking('test_read_modify_write_pattern'))
    
    # Add H3 tests
    suite.addTest(TestH3ActivePositionProtection('test_active_position_cache_protection'))
    suite.addTest(TestH3ActivePositionProtection('test_fallback_when_position_manager_unavailable'))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    if result.wasSuccessful():
        print("  ✅ ALL TESTS PASSED")
    else:
        print("  ❌ SOME TESTS FAILED")
    print("=" * 70 + "\n")
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
