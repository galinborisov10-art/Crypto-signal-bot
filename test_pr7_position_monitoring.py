#!/usr/bin/env python3
"""
Test for PR #7: Position Monitoring & Auto Re-analysis
Validates that position tracking and monitoring features work correctly
"""

import os
import sys
import ast
import sqlite3

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def test_database_schema():
    """Test that positions database schema is correct"""
    print("\n🧪 Test 1: Database Schema")
    
    from init_positions_db import create_positions_database, verify_database, DB_PATH
    
    # Create database
    assert create_positions_database(), "Database creation failed"
    
    # Verify schema
    assert verify_database(), "Database verification failed"
    
    # Check tables exist
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT name FROM sqlite_master 
        WHERE type='table' 
        ORDER BY name
    """)
    
    tables = [row[0] for row in cursor.fetchall()]
    expected_tables = ['checkpoint_alerts', 'open_positions', 'position_history']
    
    for table in expected_tables:
        assert table in tables, f"Table {table} not found"
    
    # Check open_positions columns
    cursor.execute("PRAGMA table_info(open_positions)")
    columns = {row[1] for row in cursor.fetchall()}
    
    required_columns = {
        'id', 'symbol', 'timeframe', 'signal_type', 'entry_price',
        'tp1_price', 'sl_price', 'current_size', 'original_signal_json',
        'checkpoint_25_triggered', 'checkpoint_50_triggered',
        'checkpoint_75_triggered', 'checkpoint_85_triggered', 'status'
    }
    
    for col in required_columns:
        assert col in columns, f"Column {col} not found in open_positions"
    
    conn.close()
    
    print("✅ Database schema test passed")


def test_position_manager():
    """Test that PositionManager class works correctly"""
    print("\n🧪 Test 2: Position Manager")
    
    from position_manager import PositionManager
    from datetime import datetime, timezone
    
    manager = PositionManager()
    
    # Test get_open_positions (should be empty initially)
    positions = manager.get_open_positions()
    assert isinstance(positions, list), "get_open_positions should return a list"
    
    # Test get_position_stats
    stats = manager.get_position_stats()
    assert isinstance(stats, dict), "get_position_stats should return a dict"
    assert 'total_positions' in stats, "Stats should include total_positions"
    assert 'win_rate' in stats, "Stats should include win_rate"
    
    # Test get_position_history
    history = manager.get_position_history()
    assert isinstance(history, list), "get_position_history should return a list"
    
    print("✅ Position Manager test passed")


def test_helper_functions_exist():
    """Test that all helper functions exist in bot.py"""
    print("\n🧪 Test 3: Helper Functions")
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for helper functions
    helper_functions = [
        'get_live_price',
        'calculate_checkpoint_price',
        'check_checkpoint_reached',
        'check_sl_hit',
        'check_tp_hit',
        'reconstruct_signal_from_json',
        # 'format_checkpoint_alert',  # REMOVED - checkpoint alert system disabled
        'handle_sl_hit',
        'handle_tp_hit'
    ]
    
    for func in helper_functions:
        assert f'def {func}(' in content, f"Helper function {func} not found"
    
    print("✅ Helper functions test passed")


def test_monitoring_job_exists():
    """Test that monitor_positions_job exists"""
    print("\n🧪 Test 4: Monitoring Job")
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    assert 'async def monitor_positions_job(' in content, "monitor_positions_job function not found"
    assert '@safe_job("position_monitor"' in content, "position_monitor safe_job decorator not found"
    
    # Check for key monitoring logic
    assert 'position_manager_global.get_open_positions()' in content, "Monitoring job doesn't get positions"
    assert 'get_live_price(' in content, "Monitoring job doesn't get live price"
    assert 'check_checkpoint_reached(' in content, "Monitoring job doesn't check checkpoints"
    assert 'reanalyze_at_checkpoint' in content, "Monitoring job doesn't perform re-analysis"
    
    print("✅ Monitoring job test passed")


def test_auto_integration():
    """Test that auto signal job integrates with position tracking"""
    print("\n🧪 Test 5: Auto Signal Integration")
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for auto position opening in auto_signal_job
    assert 'AUTO_POSITION_TRACKING_ENABLED' in content, "AUTO_POSITION_TRACKING_ENABLED flag not found"
    assert 'position_manager_global.open_position(' in content, "Auto position opening not implemented"
    assert 'Position tracking started for' in content, "Position tracking confirmation message not found"
    
    print("✅ Auto signal integration test passed")


def test_scheduler_registration():
    """Test that position monitor is registered with scheduler"""
    print("\n🧪 Test 6: Scheduler Registration")
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for scheduler registration
    assert "id='position_monitor'" in content, "Position monitor scheduler job not found"
    assert "minute='*'" in content, "Position monitor not scheduled every minute"
    assert 'monitor_positions_job(application.bot)' in content, "Position monitor job not called"
    
    print("✅ Scheduler registration test passed")


def test_commands_exist():
    """Test that position management commands exist"""
    print("\n🧪 Test 7: Position Commands")
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for command functions
    commands = [
        'position_list_cmd',
        'position_close_cmd',
        'position_history_cmd',
        'position_stats_cmd'
    ]
    
    for cmd in commands:
        assert f'async def {cmd}(' in content, f"Command {cmd} not found"
    
    # Check for command handler registration
    assert 'CommandHandler("position_list", position_list_cmd)' in content, "position_list not registered"
    assert 'CommandHandler("position_close", position_close_cmd)' in content, "position_close not registered"
    assert 'CommandHandler("position_history", position_history_cmd)' in content, "position_history not registered"
    assert 'CommandHandler("position_stats", position_stats_cmd)' in content, "position_stats not registered"
    
    print("✅ Position commands test passed")


def test_configuration_flags():
    """Test that configuration flags are defined"""
    print("\n🧪 Test 8: Configuration Flags")
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for config flags
    config_flags = [
        'AUTO_POSITION_TRACKING_ENABLED',
        'AUTO_CLOSE_ON_SL_HIT',
        'AUTO_CLOSE_ON_TP_HIT',
        'CHECKPOINT_MONITORING_ENABLED',
        'POSITION_MONITORING_INTERVAL_SECONDS'
    ]
    
    for flag in config_flags:
        assert flag in content, f"Configuration flag {flag} not found"
    
    print("✅ Configuration flags test passed")


def test_imports():
    """Test that required imports are present"""
    print("\n🧪 Test 9: Imports")
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for PositionManager import
    assert 'from position_manager import PositionManager' in content, "PositionManager not imported"
    assert 'position_manager_global = PositionManager()' in content, "PositionManager not initialized"
    
    # Check for availability flag
    assert 'POSITION_MANAGER_AVAILABLE' in content, "POSITION_MANAGER_AVAILABLE flag not found"
    
    print("✅ Imports test passed")


def test_no_syntax_errors():
    """Test that bot.py has no syntax errors"""
    print("\n🧪 Test 10: Syntax Check")
    
    with open('bot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    try:
        ast.parse(content)
        print("✅ Syntax check test passed")
    except SyntaxError as e:
        print(f"❌ Syntax error found: {e}")
        raise


def run_all_tests():
    """Run all tests"""
    print("\n" + "=" * 70)
    print("  PR #7: POSITION MONITORING - TEST SUITE")
    print("=" * 70)
    
    tests = [
        test_database_schema,
        test_position_manager,
        test_helper_functions_exist,
        test_monitoring_job_exists,
        test_auto_integration,
        test_scheduler_registration,
        test_commands_exist,
        test_configuration_flags,
        test_imports,
        test_no_syntax_errors
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"❌ {test.__name__} failed: {e}")
            failed += 1
        except Exception as e:
            print(f"❌ {test.__name__} error: {e}")
            failed += 1
    
    print("\n" + "=" * 70)
    print(f"  RESULTS: {passed} passed, {failed} failed")
    print("=" * 70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
