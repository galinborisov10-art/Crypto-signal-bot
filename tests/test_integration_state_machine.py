"""
Integration Test: Setup State Machine Full Flow
Demonstrates the complete state machine flow from setup detection to signal emission.

Author: galinborisov10-art
Date: 2026-03-08
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from setup_state_manager import SetupStateManager
from entry_scenarios import is_entry_triggered


def test_full_state_machine_flow():
    """
    Integration test demonstrating complete state machine flow:
    1. Setup detected → stored as pending
    2. Trigger false for 3 cycles → TTL decrements
    3. Trigger becomes true → signal emitted
    4. Setup removed → no duplicate signals
    """
    print("=" * 80)
    print("🧪 INTEGRATION TEST: Full State Machine Flow")
    print("=" * 80)
    
    manager = SetupStateManager()
    manager.clear_all()
    
    # ============================================================
    # CYCLE 1: Setup Detection
    # ============================================================
    print("\n📍 CYCLE 1: Setup Detected")
    print("-" * 80)
    
    scenario_data = {
        'scenario': 'ROLLBACK',
        'probability': 0.88,
        'entry_zone': {
            'center': 49500.0,
            'low': 49450.0,
            'high': 49550.0,
            'source': 'ROLLBACK_BOS',
            'quality': 85,
            'distance_pct': 1.0
        },
        'triggers': ['MSS/BOS'],
        'invalidation_anchor': {
            'type': 'SWING_LOW',
            'price': 49450.0
        }
    }
    
    entry_zone = scenario_data['entry_zone']
    
    # Create setup (scenario detected but trigger not met)
    setup = manager.create_setup(
        symbol='BTCUSDT',
        timeframe='2h',
        scenario_name='ROLLBACK',
        scenario_data=scenario_data,
        entry_zone=entry_zone
    )
    
    print(f"✅ Setup created and stored as PENDING")
    print(f"   • Scenario: {setup.scenario_name}")
    print(f"   • Entry: ${entry_zone['center']:.2f}")
    print(f"   • TTL: {setup.ttl_remaining} cycles")
    
    # Check trigger (price far from entry)
    current_price_1 = 50500.0  # 2% away from entry
    is_triggered_1, reason_1 = is_entry_triggered(
        scenario_name='ROLLBACK',
        scenario_data=scenario_data,
        entry_zone=entry_zone,
        current_price=current_price_1,
        ict_components={},
        bias='BULLISH',
        timeframe='2h'
    )
    
    assert not is_triggered_1, "❌ Should not be triggered when price is far"
    print(f"   • Trigger check: {is_triggered_1} - {reason_1}")
    print(f"   • Expected outcome: NO_TRADE (setup pending)")
    
    # ============================================================
    # CYCLE 2-4: Entry Trigger Still False
    # ============================================================
    for cycle in range(2, 5):
        print(f"\n📍 CYCLE {cycle}: Trigger Still False")
        print("-" * 80)
        
        # Price moving closer but not in zone yet
        current_price = 50500.0 - (cycle * 200)  # Moving closer
        
        is_triggered, reason = is_entry_triggered(
            scenario_name='ROLLBACK',
            scenario_data=scenario_data,
            entry_zone=entry_zone,
            current_price=current_price,
            ict_components={},
            bias='BULLISH',
            timeframe='2h'
        )
        
        assert not is_triggered, f"❌ Should not be triggered at cycle {cycle}"
        
        # Decrement TTL
        still_active = manager.decrement_ttl('BTCUSDT', '2h')
        assert still_active, f"❌ Setup should still be active at cycle {cycle}"
        
        setup = manager.get_setup('BTCUSDT', '2h')
        print(f"   • Current price: ${current_price:.2f}")
        print(f"   • Trigger check: {is_triggered} - {reason}")
        print(f"   • TTL remaining: {setup.ttl_remaining}")
        print(f"   • Expected outcome: NO_TRADE (setup still pending)")
    
    # ============================================================
    # CYCLE 5: Entry Trigger Becomes True
    # ============================================================
    print(f"\n📍 CYCLE 5: Entry Trigger TRUE")
    print("-" * 80)
    
    # Price reaches entry zone
    current_price_5 = 49500.0  # At entry center
    
    is_triggered_5, reason_5 = is_entry_triggered(
        scenario_name='ROLLBACK',
        scenario_data=scenario_data,
        entry_zone=entry_zone,
        current_price=current_price_5,
        ict_components={},
        bias='BULLISH',
        timeframe='2h'
    )
    
    assert is_triggered_5, f"❌ Should be triggered when price in zone, reason: {reason_5}"
    print(f"   • Current price: ${current_price_5:.2f}")
    print(f"   • Trigger check: {is_triggered_5} - {reason_5}")
    print(f"   ✅ ENTRY TRIGGERED - Signal should be emitted")
    
    # Mark as triggered (simulates signal emission)
    manager.mark_triggered('BTCUSDT', '2h')
    
    # Verify setup is removed (single-signal rule)
    setup_after_trigger = manager.get_setup('BTCUSDT', '2h')
    assert setup_after_trigger is None, "❌ Setup should be removed after trigger"
    print(f"   ✅ Setup removed from store (single-signal rule enforced)")
    
    # ============================================================
    # CYCLE 6: No Duplicate Signals
    # ============================================================
    print(f"\n📍 CYCLE 6: Verify No Duplicate Signals")
    print("-" * 80)
    
    # On next evaluation, no setup exists
    setup_cycle_6 = manager.get_setup('BTCUSDT', '2h')
    assert setup_cycle_6 is None, "❌ No setup should exist after trigger"
    print(f"   • Setup exists: {setup_cycle_6 is not None}")
    print(f"   ✅ No duplicate signal possible (setup already removed)")
    
    print("\n" + "=" * 80)
    print("✅ INTEGRATION TEST PASSED")
    print("=" * 80)


def test_ttl_expiry_flow():
    """
    Integration test: Setup expires before trigger
    """
    print("\n" + "=" * 80)
    print("🧪 INTEGRATION TEST: TTL Expiry Flow")
    print("=" * 80)
    
    manager = SetupStateManager()
    manager.clear_all()
    
    scenario_data = {
        'scenario': 'PULLBACK',
        'probability': 0.80,
        'entry_zone': {
            'center': 49100.0,
            'low': 49050.0,
            'high': 49150.0,
            'source': 'PULLBACK_OB',
            'quality': 85
        },
        'triggers': ['MSS/BOS']
    }
    
    # Create setup with small TTL (use 4h timeframe = 6 cycles)
    setup = manager.create_setup(
        symbol='ETHUSDT',
        timeframe='4h',
        scenario_name='PULLBACK',
        scenario_data=scenario_data,
        entry_zone=scenario_data['entry_zone']
    )
    
    initial_ttl = setup.ttl_remaining
    print(f"\n📍 Setup created with TTL={initial_ttl}")
    
    # Simulate cycles where trigger never becomes true
    for cycle in range(1, initial_ttl + 1):
        print(f"\n📍 CYCLE {cycle}: Trigger False")
        
        is_triggered, reason = is_entry_triggered(
            scenario_name='PULLBACK',
            scenario_data=scenario_data,
            entry_zone=scenario_data['entry_zone'],
            current_price=50000.0,  # Far from entry
            ict_components={'order_blocks': []},
            bias='BULLISH',
            timeframe='4h',
            recent_candles=[]  # No candles, will use fallback
        )
        
        assert not is_triggered, f"❌ Should not be triggered at cycle {cycle}"
        print(f"   • Trigger: {is_triggered} - {reason}")
        
        # Decrement TTL
        still_active = manager.decrement_ttl('ETHUSDT', '4h')
        
        if cycle < initial_ttl:
            assert still_active, f"❌ Should be active at cycle {cycle}"
            setup = manager.get_setup('ETHUSDT', '4h')
            print(f"   • TTL remaining: {setup.ttl_remaining}")
            print(f"   • Status: PENDING")
        else:
            assert not still_active, f"❌ Should expire at cycle {cycle}"
            print(f"   • TTL: 0 (EXPIRED)")
            print(f"   ✅ Setup expired - no signal emitted")
    
    # Verify setup is removed
    final_setup = manager.get_setup('ETHUSDT', '4h')
    assert final_setup is None, "❌ Setup should be removed after expiry"
    
    print("\n" + "=" * 80)
    print("✅ TTL EXPIRY TEST PASSED")
    print("=" * 80)


def test_immediate_trigger_flow():
    """
    Integration test: Setup detected with immediate trigger
    (Signal emitted on first detection, no pending state)
    """
    print("\n" + "=" * 80)
    print("🧪 INTEGRATION TEST: Immediate Trigger Flow")
    print("=" * 80)
    
    manager = SetupStateManager()
    manager.clear_all()
    
    # Setup where price is already at entry zone
    scenario_data = {
        'scenario': 'ROLLBACK',
        'probability': 0.90,
        'entry_zone': {
            'center': 50000.0,
            'low': 49950.0,
            'high': 50050.0,
            'source': 'ROLLBACK_MSS',
            'quality': 90
        },
        'triggers': ['MSS/BOS', 'DISPLACEMENT']
    }
    
    entry_zone = scenario_data['entry_zone']
    current_price = 50000.0  # Already at entry
    
    print(f"\n📍 Scenario detected with price already at entry")
    print(f"   • Entry zone: ${entry_zone['center']:.2f}")
    print(f"   • Current price: ${current_price:.2f}")
    
    # Check trigger immediately
    is_triggered, reason = is_entry_triggered(
        scenario_name='ROLLBACK',
        scenario_data=scenario_data,
        entry_zone=entry_zone,
        current_price=current_price,
        ict_components={},
        bias='BULLISH',
        timeframe='2h'
    )
    
    assert is_triggered, f"❌ Should be triggered immediately, reason: {reason}"
    print(f"   • Trigger check: {is_triggered} - {reason}")
    print(f"   ✅ IMMEDIATE TRIGGER - Signal emitted without pending state")
    
    # In real flow, setup would NOT be created if trigger is immediate
    # OR would be created and immediately marked as triggered
    # Let's simulate the second approach:
    
    setup = manager.create_setup(
        symbol='BTCUSDT',
        timeframe='2h',
        scenario_name='ROLLBACK',
        scenario_data=scenario_data,
        entry_zone=entry_zone
    )
    
    # Immediately mark as triggered
    manager.mark_triggered('BTCUSDT', '2h')
    
    # Verify setup is removed
    setup_after = manager.get_setup('BTCUSDT', '2h')
    assert setup_after is None, "❌ Setup should be removed immediately"
    print(f"   ✅ Setup created and triggered in same cycle (no pending state needed)")
    
    print("\n" + "=" * 80)
    print("✅ IMMEDIATE TRIGGER TEST PASSED")
    print("=" * 80)


def run_all_integration_tests():
    """Run all integration tests"""
    print("\n" + "=" * 80)
    print("🧪 SETUP STATE MACHINE - INTEGRATION TESTS")
    print("=" * 80)
    
    tests = [
        test_full_state_machine_flow,
        test_ttl_expiry_flow,
        test_immediate_trigger_flow
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except AssertionError as e:
            print(f"\n❌ TEST FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"\n❌ TEST ERROR: {e}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 80)
    print(f"FINAL RESULTS: {passed} passed, {failed} failed")
    print("=" * 80)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_integration_tests()
    sys.exit(0 if success else 1)
