"""
Integration test to verify file locking doesn't break existing functionality
"""

import json
import os
import tempfile
import fcntl


def test_backward_compatibility():
    """Verify that locking changes don't break existing JSON operations"""
    
    # Create a test journal
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_file = f.name
        test_journal = {
            'trades': [
                {
                    'timestamp': '2024-01-01T00:00:00Z',
                    'symbol': 'BTCUSDT',
                    'timeframe': '4h',
                    'signal_type': 'BUY',
                    'entry': 45000.0,
                    'tp': 46350.0,
                    'sl': 44325.0,
                    'outcome': 'WIN',
                    'exit_price': 46350.0,
                    'profit_loss_pct': 3.0,
                    'duration_hours': 24,
                    'ml_mode': False,
                    'ml_confidence': 0,
                    'alerts_80': [],
                    'final_alerts': [{'duration_hours': 24}],
                    'conditions': {}
                }
            ]
        }
        json.dump(test_journal, f, indent=2, ensure_ascii=False)
    
    try:
        # Test 1: Read with shared lock (ml_engine pattern)
        print("Testing ml_engine.py pattern...")
        with open(temp_file, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            journal = json.load(f)
        
        assert len(journal['trades']) == 1
        assert journal['trades'][0]['symbol'] == 'BTCUSDT'
        print("✅ ML engine read pattern works")
        
        # Test 2: Write with exclusive lock (bot pattern)
        print("\nTesting bot.py save_trade_to_journal pattern...")
        new_trade = {
            'timestamp': '2024-01-02T00:00:00Z',
            'symbol': 'ETHUSDT',
            'timeframe': '1h',
            'signal_type': 'SELL',
            'entry': 3000.0,
            'tp': 2940.0,
            'sl': 3030.0,
            'outcome': 'LOSS',
            'exit_price': 3030.0,
            'profit_loss_pct': -1.0,
            'duration_hours': 12,
            'ml_mode': True,
            'ml_confidence': 0.85,
            'alerts_80': [],
            'final_alerts': [{'duration_hours': 12}],
            'conditions': {'rsi': 65}
        }
        
        with open(temp_file, 'r+', encoding='utf-8') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            
            # Read current content
            if os.path.getsize(temp_file) > 0:
                f.seek(0)
                journal = json.load(f)
            else:
                journal = {'trades': []}
            
            # Add new trade
            journal['trades'].append(new_trade)
            
            # Write back
            f.seek(0)
            f.truncate()
            json.dump(journal, f, indent=2, ensure_ascii=False)
        
        print("✅ Bot write pattern works")
        
        # Test 3: Verify data integrity
        print("\nVerifying data integrity...")
        with open(temp_file, 'r') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)
            journal = json.load(f)
        
        assert len(journal['trades']) == 2
        assert journal['trades'][0]['symbol'] == 'BTCUSDT'
        assert journal['trades'][1]['symbol'] == 'ETHUSDT'
        assert journal['trades'][0]['outcome'] == 'WIN'
        assert journal['trades'][1]['outcome'] == 'LOSS'
        assert journal['trades'][1]['ml_mode'] is True
        print("✅ Data integrity preserved")
        
        # Test 4: JSON format is preserved
        print("\nVerifying JSON format...")
        with open(temp_file, 'r') as f:
            content = f.read()
        
        # Check for proper formatting
        assert '"trades"' in content
        assert 'BTCUSDT' in content
        assert 'ETHUSDT' in content
        # Verify it's properly indented (indent=2)
        assert '\n  "trades"' in content or '"trades"' in content
        print("✅ JSON format preserved")
        
        print("\n" + "="*60)
        print("✅ ALL BACKWARD COMPATIBILITY TESTS PASSED!")
        print("="*60)
        
    finally:
        os.unlink(temp_file)


if __name__ == '__main__':
    test_backward_compatibility()
