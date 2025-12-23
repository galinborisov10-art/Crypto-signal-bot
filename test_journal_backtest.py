"""
🧪 COMPREHENSIVE TESTS FOR JOURNAL BACKTEST ENGINE
===================================================

Tests verify:
1. READ-ONLY mode (CRITICAL)
2. Statistics accuracy
3. ML vs Classical detection
4. Filtering capabilities
5. NO ML modifications (CRITICAL)
6. Concurrent access safety
"""

import json
import os
import tempfile
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pytest

from journal_backtest import JournalBacktestEngine, get_backtest_engine


# ===================== FIXTURES =====================

@pytest.fixture
def temp_dir():
    """Create temporary directory for test files"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_journal(temp_dir):
    """Create sample trading journal for testing"""
    journal_path = os.path.join(temp_dir, 'trading_journal.json')
    
    # Create sample trades
    now = datetime.now(timezone.utc)
    
    journal_data = {
        'metadata': {
            'created': now.isoformat(),
            'version': '1.0',
            'total_trades': 10,
            'last_updated': now.isoformat()
        },
        'trades': [
            # Recent WIN trade - Classical mode
            {
                'id': 1,
                'timestamp': (now - timedelta(days=5)).isoformat(),
                'symbol': 'BTCUSDT',
                'timeframe': '4h',
                'signal': 'BUY',
                'confidence': 75.5,
                'entry_price': 45000.0,
                'tp_price': 46350.0,
                'sl_price': 44325.0,
                'outcome': 'WIN',
                'profit_loss_pct': 3.0,
                'closed_at': (now - timedelta(days=4)).isoformat(),
                'conditions': {
                    'rsi': 45.2,
                    'price_change_pct': 2.5,
                    'volume_ratio': 1.25,
                    'volatility': 5.0,
                    'bb_position': 0.3,
                    'ict_confidence': 0.75,
                    'ml_mode': False
                }
            },
            # Recent LOSS trade - Classical mode
            {
                'id': 2,
                'timestamp': (now - timedelta(days=10)).isoformat(),
                'symbol': 'ETHUSDT',
                'timeframe': '1h',
                'signal': 'SELL',
                'confidence': 68.0,
                'entry_price': 3000.0,
                'tp_price': 2940.0,
                'sl_price': 3030.0,
                'outcome': 'LOSS',
                'profit_loss_pct': -1.0,
                'closed_at': (now - timedelta(days=9)).isoformat(),
                'conditions': {
                    'rsi': 65.0,
                    'price_change_pct': -1.5,
                    'volume_ratio': 0.9,
                    'volatility': 6.0,
                    'bb_position': 0.8,
                    'ict_confidence': 0.68,
                    'ml_mode': False
                }
            },
            # Recent WIN trade - ML mode
            {
                'id': 3,
                'timestamp': (now - timedelta(days=7)).isoformat(),
                'symbol': 'BTCUSDT',
                'timeframe': '1h',
                'signal': 'BUY',
                'confidence': 82.0,
                'entry_price': 46000.0,
                'tp_price': 47380.0,
                'sl_price': 45310.0,
                'outcome': 'SUCCESS',
                'profit_loss_pct': 3.0,
                'closed_at': (now - timedelta(days=6)).isoformat(),
                'conditions': {
                    'rsi': 42.0,
                    'price_change_pct': 3.0,
                    'volume_ratio': 1.5,
                    'volatility': 4.5,
                    'bb_position': 0.25,
                    'ict_confidence': 0.82,
                    'ml_mode': True
                }
            },
            # Old trade (>30 days) - should be filtered out
            {
                'id': 4,
                'timestamp': (now - timedelta(days=35)).isoformat(),
                'symbol': 'XRPUSDT',
                'timeframe': '4h',
                'signal': 'BUY',
                'confidence': 70.0,
                'entry_price': 0.5,
                'tp_price': 0.515,
                'sl_price': 0.4925,
                'outcome': 'WIN',
                'profit_loss_pct': 3.0,
                'closed_at': (now - timedelta(days=34)).isoformat(),
                'conditions': {
                    'rsi': 50.0,
                    'ml_mode': False
                }
            },
            # PENDING trade - should be excluded
            {
                'id': 5,
                'timestamp': (now - timedelta(days=2)).isoformat(),
                'symbol': 'BTCUSDT',
                'timeframe': '4h',
                'signal': 'BUY',
                'confidence': 75.0,
                'entry_price': 47000.0,
                'tp_price': 48410.0,
                'sl_price': 46295.0,
                'status': 'PENDING',
                'conditions': {
                    'rsi': 48.0,
                    'ml_mode': False
                }
            },
            # Additional trades for statistical significance
            {
                'id': 6,
                'timestamp': (now - timedelta(days=8)).isoformat(),
                'symbol': 'SOLUSDT',
                'timeframe': '1h',
                'signal': 'BUY',
                'confidence': 72.0,
                'entry_price': 100.0,
                'tp_price': 103.0,
                'sl_price': 98.5,
                'outcome': 'WIN',
                'profit_loss_pct': 3.0,
                'closed_at': (now - timedelta(days=7)).isoformat(),
                'conditions': {
                    'rsi': 45.0,
                    'ml_mode': False
                }
            },
            {
                'id': 7,
                'timestamp': (now - timedelta(days=12)).isoformat(),
                'symbol': 'BTCUSDT',
                'timeframe': '4h',
                'signal': 'SELL',
                'confidence': 78.0,
                'entry_price': 44000.0,
                'tp_price': 43120.0,
                'sl_price': 44440.0,
                'outcome': 'WIN',
                'profit_loss_pct': 2.0,
                'closed_at': (now - timedelta(days=11)).isoformat(),
                'conditions': {
                    'rsi': 70.0,
                    'ml_mode': True
                }
            },
            {
                'id': 8,
                'timestamp': (now - timedelta(days=15)).isoformat(),
                'symbol': 'ETHUSDT',
                'timeframe': '1h',
                'signal': 'BUY',
                'confidence': 65.0,
                'entry_price': 2900.0,
                'tp_price': 2987.0,
                'sl_price': 2856.5,
                'outcome': 'FAILED',
                'profit_loss_pct': -1.5,
                'closed_at': (now - timedelta(days=14)).isoformat(),
                'conditions': {
                    'rsi': 35.0,
                    'ml_mode': False
                }
            }
        ],
        'patterns': {},
        'ml_insights': {}
    }
    
    # Write journal
    with open(journal_path, 'w', encoding='utf-8') as f:
        json.dump(journal_data, f, indent=2)
    
    return journal_path


# ===================== CRITICAL TESTS =====================

def test_backtest_read_only(sample_journal, temp_dir):
    """
    CRITICAL: Verify journal is NEVER modified
    This test MUST pass - if it fails, the entire PR is REJECTED
    """
    # Get original file content
    with open(sample_journal, 'rb') as f:
        original_content = f.read()
    
    original_mtime = os.path.getmtime(sample_journal)
    
    # Run backtest
    engine = JournalBacktestEngine(journal_path=sample_journal)
    results = engine.run_backtest(days=30)
    
    # Verify file was NOT modified
    with open(sample_journal, 'rb') as f:
        new_content = f.read()
    
    assert original_content == new_content, "❌ CRITICAL: Journal was modified!"
    assert os.path.getmtime(sample_journal) == original_mtime, "❌ CRITICAL: Journal timestamp changed!"
    
    print("✅ CRITICAL TEST PASSED: Journal remains READ-ONLY")


def test_no_ml_modifications(sample_journal, temp_dir):
    """
    CRITICAL: Verify ML models are NOT modified
    This test MUST pass - if it fails, the entire PR is REJECTED
    """
    # Check for any ML-related files that might be created/modified
    ml_files = [
        'ml_model.pkl',
        'ml_ensemble.pkl',
        'ml_scaler.pkl',
        'ml_performance.json',
        'ml_feature_importance.json'
    ]
    
    # Record initial state
    initial_state = {}
    for ml_file in ml_files:
        file_path = os.path.join(temp_dir, ml_file)
        if os.path.exists(file_path):
            initial_state[ml_file] = os.path.getmtime(file_path)
        else:
            initial_state[ml_file] = None
    
    # Run backtest
    engine = JournalBacktestEngine(journal_path=sample_journal)
    results = engine.run_backtest(days=30)
    
    # Verify NO ML files were created or modified
    for ml_file in ml_files:
        file_path = os.path.join(temp_dir, ml_file)
        current_state = os.path.getmtime(file_path) if os.path.exists(file_path) else None
        
        assert initial_state[ml_file] == current_state, \
            f"❌ CRITICAL: ML file {ml_file} was modified/created!"
    
    print("✅ CRITICAL TEST PASSED: No ML modifications")


# ===================== FUNCTIONAL TESTS =====================

def test_backtest_statistics_accuracy(sample_journal):
    """Verify win rate, P/L calculations are correct"""
    engine = JournalBacktestEngine(journal_path=sample_journal)
    results = engine.run_backtest(days=30)
    
    assert results['success'] is True
    
    overall = results['overall']
    
    # Should have 6 completed trades within 30 days (excluding PENDING and old trades)
    assert overall['total_trades'] == 6, f"Expected 6 trades, got {overall['total_trades']}"
    
    # Count expected wins and losses from sample data
    # Wins: id 1, 3, 6, 7 = 4 wins
    # Losses: id 2, 8 = 2 losses
    assert overall['wins'] == 4, f"Expected 4 wins, got {overall['wins']}"
    assert overall['losses'] == 2, f"Expected 2 losses, got {overall['losses']}"
    
    # Win rate should be 4/6 = 66.67%
    expected_win_rate = 66.67
    assert abs(overall['win_rate'] - expected_win_rate) < 0.1, \
        f"Expected win rate ~{expected_win_rate}%, got {overall['win_rate']}%"
    
    # Total P/L: +3.0 +3.0 +3.0 +2.0 -1.0 -1.5 = +8.5%
    expected_pnl = 8.5
    assert abs(overall['total_pnl'] - expected_pnl) < 0.1, \
        f"Expected total P/L ~{expected_pnl}%, got {overall['total_pnl']}%"
    
    # Profit factor (total wins / total losses) = 11.0 / 2.5 = 4.4
    assert overall['profit_factor'] > 0, "Profit factor should be positive"
    
    print("✅ Statistics accuracy test passed")


def test_ml_vs_classical_detection(sample_journal):
    """Verify correct ML/Classical identification"""
    engine = JournalBacktestEngine(journal_path=sample_journal)
    results = engine.run_backtest(days=30)
    
    ml_vs_classical = results['ml_vs_classical']
    
    # ML trades: id 3, 7 = 2 trades
    assert ml_vs_classical['ml']['total_trades'] == 2, \
        f"Expected 2 ML trades, got {ml_vs_classical['ml']['total_trades']}"
    
    # Classical trades: id 1, 2, 6, 8 = 4 trades
    assert ml_vs_classical['classical']['total_trades'] == 4, \
        f"Expected 4 classical trades, got {ml_vs_classical['classical']['total_trades']}"
    
    # ML should have 100% win rate (both id 3 and 7 are wins)
    assert ml_vs_classical['ml']['win_rate'] == 100.0, \
        f"Expected ML win rate 100%, got {ml_vs_classical['ml']['win_rate']}%"
    
    # Classical should have 50% win rate (2 wins, 2 losses)
    assert ml_vs_classical['classical']['win_rate'] == 50.0, \
        f"Expected classical win rate 50%, got {ml_vs_classical['classical']['win_rate']}%"
    
    # Delta should show ML outperforming by 50%
    assert ml_vs_classical['delta']['win_rate'] == 50.0, \
        f"Expected delta +50%, got {ml_vs_classical['delta']['win_rate']}%"
    
    # Insight should recommend ML
    assert '✅' in ml_vs_classical['insight'] or 'RECOMMENDED' in ml_vs_classical['insight'], \
        "Insight should recommend ML mode"
    
    print("✅ ML vs Classical detection test passed")


def test_backtest_symbol_filtering(sample_journal):
    """Verify symbol-specific filtering works"""
    engine = JournalBacktestEngine(journal_path=sample_journal)
    
    # Filter for BTCUSDT
    results = engine.run_backtest(days=30, symbol='BTCUSDT')
    
    assert results['success'] is True
    
    # Should have 3 BTCUSDT trades (id 1, 3, 7)
    assert results['overall']['total_trades'] == 3, \
        f"Expected 3 BTCUSDT trades, got {results['overall']['total_trades']}"
    
    # All trades should be BTCUSDT
    assert 'BTCUSDT' in results['by_symbol'], "BTCUSDT should be in breakdown"
    assert len(results['by_symbol']) == 1, "Should only have BTCUSDT in breakdown"
    
    print("✅ Symbol filtering test passed")


def test_backtest_timeframe_filtering(sample_journal):
    """Verify timeframe-specific filtering works"""
    engine = JournalBacktestEngine(journal_path=sample_journal)
    
    # Filter for 1h timeframe
    results = engine.run_backtest(days=30, timeframe='1h')
    
    assert results['success'] is True
    
    # Should have 4 trades with 1h timeframe (id 2, 3, 6, 8)
    assert results['overall']['total_trades'] == 4, \
        f"Expected 4 '1h' trades, got {results['overall']['total_trades']}"
    
    # All trades should be 1h
    assert '1h' in results['by_timeframe'], "'1h' should be in breakdown"
    assert len(results['by_timeframe']) == 1, "Should only have '1h' in breakdown"
    
    print("✅ Timeframe filtering test passed")


def test_concurrent_backtest(sample_journal):
    """Verify multiple backtests don't cause conflicts"""
    engine = JournalBacktestEngine(journal_path=sample_journal)
    
    # Run multiple backtests concurrently (simulated)
    results1 = engine.run_backtest(days=30)
    results2 = engine.run_backtest(days=30, symbol='BTCUSDT')
    results3 = engine.run_backtest(days=30, timeframe='1h')
    
    # All should succeed
    assert results1['success'] is True
    assert results2['success'] is True
    assert results3['success'] is True
    
    # Results should be independent
    assert results1['overall']['total_trades'] != results2['overall']['total_trades']
    assert results1['overall']['total_trades'] != results3['overall']['total_trades']
    
    print("✅ Concurrent backtest test passed")


def test_empty_journal(temp_dir):
    """Test behavior with empty journal"""
    journal_path = os.path.join(temp_dir, 'empty_journal.json')
    
    # Create empty journal
    with open(journal_path, 'w', encoding='utf-8') as f:
        json.dump({'metadata': {}, 'trades': []}, f)
    
    engine = JournalBacktestEngine(journal_path=journal_path)
    results = engine.run_backtest(days=30)
    
    # Should return error
    assert 'error' in results
    assert results['total_trades'] == 0
    
    print("✅ Empty journal test passed")


def test_missing_journal(temp_dir):
    """Test behavior when journal doesn't exist"""
    journal_path = os.path.join(temp_dir, 'nonexistent.json')
    
    engine = JournalBacktestEngine(journal_path=journal_path)
    results = engine.run_backtest(days=30)
    
    # Should return error
    assert 'error' in results
    assert 'not found' in results['error'].lower()
    
    print("✅ Missing journal test passed")


def test_breakdown_by_symbol(sample_journal):
    """Test per-symbol breakdown accuracy"""
    engine = JournalBacktestEngine(journal_path=sample_journal)
    results = engine.run_backtest(days=30)
    
    by_symbol = results['by_symbol']
    
    # Should have BTCUSDT, ETHUSDT, SOLUSDT
    assert 'BTCUSDT' in by_symbol
    assert 'ETHUSDT' in by_symbol
    assert 'SOLUSDT' in by_symbol
    
    # BTCUSDT: 3 trades, all wins
    assert by_symbol['BTCUSDT']['total_trades'] == 3
    assert by_symbol['BTCUSDT']['win_rate'] == 100.0
    
    # ETHUSDT: 2 trades, 0 wins, 2 losses
    assert by_symbol['ETHUSDT']['total_trades'] == 2
    assert by_symbol['ETHUSDT']['win_rate'] == 0.0
    
    # SOLUSDT: 1 trade, 1 win
    assert by_symbol['SOLUSDT']['total_trades'] == 1
    assert by_symbol['SOLUSDT']['win_rate'] == 100.0
    
    print("✅ Symbol breakdown test passed")


def test_breakdown_by_timeframe(sample_journal):
    """Test per-timeframe breakdown accuracy"""
    engine = JournalBacktestEngine(journal_path=sample_journal)
    results = engine.run_backtest(days=30)
    
    by_timeframe = results['by_timeframe']
    
    # Should have 1h and 4h
    assert '1h' in by_timeframe
    assert '4h' in by_timeframe
    
    # 1h: 4 trades (id 2, 3, 6, 8)
    assert by_timeframe['1h']['total_trades'] == 4
    
    # 4h: 2 trades (id 1, 7)
    assert by_timeframe['4h']['total_trades'] == 2
    
    print("✅ Timeframe breakdown test passed")


def test_top_worst_performers(sample_journal):
    """Test identification of top and worst performers"""
    engine = JournalBacktestEngine(journal_path=sample_journal)
    results = engine.run_backtest(days=30)
    
    top_performers = results['top_performers']
    worst_performers = results['worst_performers']
    
    # Should have top performers (symbols with >= 3 trades)
    assert len(top_performers) > 0
    
    # Top performer should be BTCUSDT (100% win rate)
    assert top_performers[0]['symbol'] == 'BTCUSDT'
    assert top_performers[0]['win_rate'] == 100.0
    
    print("✅ Top/worst performers test passed")


# ===================== RUN TESTS =====================

if __name__ == '__main__':
    print("=" * 60)
    print("🧪 RUNNING JOURNAL BACKTEST ENGINE TESTS")
    print("=" * 60)
    print()
    
    # Run pytest
    exit_code = pytest.main([__file__, '-v', '--tb=short'])
    
    if exit_code == 0:
        print()
        print("=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
    else:
        print()
        print("=" * 60)
        print("❌ SOME TESTS FAILED!")
        print("=" * 60)
    
    exit(exit_code)
