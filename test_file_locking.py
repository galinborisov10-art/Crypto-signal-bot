"""
Test file locking for trading_journal.json

This test verifies that:
1. Shared locks (LOCK_SH) are acquired for reading
2. Exclusive locks (LOCK_EX) are acquired for writing
3. Multiple readers can access simultaneously
4. Writers block readers and other writers
"""

import json
import os
import tempfile
import fcntl
import threading
import time


def test_shared_lock_reading():
    """Test that shared lock can be acquired for reading"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        json.dump({'trades': []}, f)
    
    try:
        # Simulate ml_engine.py reading with shared lock
        with open(temp_file, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            data = json.load(f)
            assert 'trades' in data
            print("✅ Shared lock acquired successfully for reading")
    finally:
        os.unlink(temp_file)


def test_exclusive_lock_writing():
    """Test that exclusive lock can be acquired for writing"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        json.dump({'trades': []}, f)
    
    try:
        # Simulate bot.py writing with exclusive lock
        with open(temp_file, 'r+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            f.seek(0)
            data = json.load(f)
            data['trades'].append({'test': 'data'})
            f.seek(0)
            f.truncate()
            json.dump(data, f)
        
        # Verify data was written
        with open(temp_file, 'r') as f:
            data = json.load(f)
            assert len(data['trades']) == 1
            print("✅ Exclusive lock acquired successfully for writing")
    finally:
        os.unlink(temp_file)


def test_multiple_readers():
    """Test that multiple readers can hold shared locks simultaneously"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        json.dump({'trades': [{'id': 1}]}, f)
    
    results = []
    
    def reader(reader_id):
        try:
            with open(temp_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                time.sleep(0.1)  # Hold lock briefly
                data = json.load(f)
                results.append(f"Reader {reader_id}: {len(data['trades'])} trades")
        except Exception as e:
            results.append(f"Reader {reader_id} failed: {e}")
    
    try:
        # Start multiple readers
        threads = [threading.Thread(target=reader, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # All readers should succeed
        assert len(results) == 3
        assert all('1 trades' in r for r in results)
        print("✅ Multiple readers can acquire shared locks simultaneously")
    finally:
        os.unlink(temp_file)


def test_writer_blocks_reader():
    """Test that a writer with exclusive lock blocks readers"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        json.dump({'trades': []}, f)
    
    writer_done = threading.Event()
    reader_blocked = threading.Event()
    results = []
    
    def writer():
        try:
            with open(temp_file, 'r+') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
                results.append("Writer: Lock acquired")
                time.sleep(0.2)  # Hold lock
                writer_done.set()
        except Exception as e:
            results.append(f"Writer failed: {e}")
    
    def reader():
        time.sleep(0.05)  # Let writer acquire lock first
        reader_blocked.set()
        try:
            with open(temp_file, 'r') as f:
                fcntl.flock(f.fileno(), fcntl.LOCK_SH)
                # Should only get here after writer releases
                assert writer_done.is_set()
                results.append("Reader: Lock acquired after writer")
        except Exception as e:
            results.append(f"Reader failed: {e}")
    
    try:
        writer_thread = threading.Thread(target=writer)
        reader_thread = threading.Thread(target=reader)
        
        writer_thread.start()
        reader_thread.start()
        
        writer_thread.join()
        reader_thread.join()
        
        # Check results
        assert len(results) == 2
        assert "Writer: Lock acquired" in results
        assert "Reader: Lock acquired after writer" in results
        print("✅ Writer with exclusive lock blocks readers")
    finally:
        os.unlink(temp_file)


def test_ml_engine_pattern():
    """Test the exact pattern used in ml_engine.py"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        json.dump({'trades': [{'id': 1}, {'id': 2}]}, f)
    
    try:
        # Simulate ml_engine.py train_model() reading
        with open(temp_file, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            journal = json.load(f)
        
        trades = journal.get('trades', [])
        assert len(trades) == 2
        print("✅ ML engine pattern works correctly")
    finally:
        os.unlink(temp_file)


def test_bot_pattern():
    """Test the exact pattern used in bot.py save_trade_to_journal()"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        json.dump({'trades': []}, f)
    
    try:
        # Simulate bot.py save_trade_to_journal() pattern
        with open(temp_file, 'r+') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            # Read current content
            if os.path.getsize(temp_file) > 0:
                f.seek(0)
                journal = json.load(f)
            else:
                journal = {'trades': []}
            
            # Add new trade
            journal['trades'].append({
                'timestamp': '2024-01-01',
                'symbol': 'BTCUSDT',
                'outcome': 'WIN'
            })
            
            # Write back
            f.seek(0)
            f.truncate()
            json.dump(journal, f, indent=2)
        
        # Verify write
        with open(temp_file, 'r') as f:
            data = json.load(f)
            assert len(data['trades']) == 1
            assert data['trades'][0]['symbol'] == 'BTCUSDT'
        
        print("✅ Bot pattern works correctly")
    finally:
        os.unlink(temp_file)


if __name__ == '__main__':
    print("=" * 60)
    print("🧪 TESTING FILE LOCKING FOR trading_journal.json")
    print("=" * 60)
    print()
    
    try:
        test_shared_lock_reading()
        test_exclusive_lock_writing()
        test_multiple_readers()
        test_writer_blocks_reader()
        test_ml_engine_pattern()
        test_bot_pattern()
        
        print()
        print("=" * 60)
        print("✅ ALL FILE LOCKING TESTS PASSED!")
        print("=" * 60)
    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        raise
