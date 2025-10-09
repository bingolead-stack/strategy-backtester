#!/usr/bin/env python3
"""
Test script to verify state persistence functionality.
This can be run independently to test the persistence system.
"""

import os
import sys
from datetime import datetime
from lib.state_persistence import StatePersistence

# Test database path (use a separate test database)
TEST_DB = "test_state.db"

def cleanup():
    """Remove test database if it exists."""
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        print(f"Cleaned up {TEST_DB}")

def test_basic_persistence():
    """Test basic save and load operations."""
    print("\n=== Test 1: Basic Persistence ===")
    
    persistence = StatePersistence(TEST_DB)
    
    # Create test state
    test_state = {
        'current_cash_value': 10000.0,
        'open_trade_count': 2,
        'total_pnl': 350.50,
        'price': 5800.0,
        'last_price': 5799.5,
        'high_price': 5801.0,
        'low_price': 5798.0,
        'index': str(datetime.now()),
        'winrate': 65.5,
        'avg_winner': 150.0,
        'avg_loser': -80.0,
        'total_trade': 10,
        'reward_to_risk': 1.875,
        'max_losing_streak': 3,
        'trade_history': [
            (datetime.now(), 'BUY', 5800.0, 0),
            (datetime.now(), 'EXIT', 5850.0, 250.0),
        ],
        'open_trade_list': [
            [datetime.now(), 5800.0, 5750.0, None, 5764.0, 5900.0],
            [datetime.now(), 5810.0, 5760.0, None, 5764.0, 5910.0],
        ],
        'retrace_levels': {0: None, 1: 'down', 2: 'up'},
        'cumulative_pnl': [100.0, 250.0, 350.50],
        'static_levels': [5764.0, 5822.5, 5881.0]
    }
    
    # Save state
    persistence.save_strategy_state("Test Strategy", test_state)
    print("✓ Saved test state")
    
    # Load state
    loaded_state = persistence.load_strategy_state("Test Strategy")
    print("✓ Loaded test state")
    
    # Verify
    assert loaded_state is not None, "Failed to load state"
    assert loaded_state['total_pnl'] == 350.50, "PnL mismatch"
    assert loaded_state['open_trade_count'] == 2, "Open trade count mismatch"
    assert len(loaded_state['trade_history']) == 2, "Trade history mismatch"
    assert len(loaded_state['open_trade_list']) == 2, "Open trade list mismatch"
    
    print("✓ All assertions passed")
    print("Test 1: PASSED\n")

def test_multiple_strategies():
    """Test multiple strategies with separate state."""
    print("=== Test 2: Multiple Strategies ===")
    
    persistence = StatePersistence(TEST_DB)
    
    # Strategy 1
    state1 = {
        'current_cash_value': 5000.0,
        'open_trade_count': 1,
        'total_pnl': 100.0,
        'price': 5800.0,
        'last_price': 5799.0,
        'high_price': 5801.0,
        'low_price': 5798.0,
        'index': str(datetime.now()),
        'winrate': 50.0,
        'avg_winner': 100.0,
        'avg_loser': -50.0,
        'total_trade': 4,
        'reward_to_risk': 2.0,
        'max_losing_streak': 1,
        'trade_history': [(datetime.now(), 'BUY', 5800.0, 0)],
        'open_trade_list': [[datetime.now(), 5800.0, 5750.0, None, 5764.0, 5900.0]],
        'retrace_levels': {0: 'down'},
        'cumulative_pnl': [100.0],
        'static_levels': [5764.0]
    }
    
    # Strategy 2
    state2 = {
        'current_cash_value': 8000.0,
        'open_trade_count': 3,
        'total_pnl': 500.0,
        'price': 5850.0,
        'last_price': 5849.0,
        'high_price': 5851.0,
        'low_price': 5848.0,
        'index': str(datetime.now()),
        'winrate': 70.0,
        'avg_winner': 200.0,
        'avg_loser': -75.0,
        'total_trade': 10,
        'reward_to_risk': 2.67,
        'max_losing_streak': 2,
        'trade_history': [(datetime.now(), 'SELL', 5850.0, 0)],
        'open_trade_list': [
            [datetime.now(), 5850.0, 5900.0, None, 5881.0, 5800.0],
            [datetime.now(), 5860.0, 5910.0, None, 5881.0, 5810.0],
            [datetime.now(), 5870.0, 5920.0, None, 5881.0, 5820.0],
        ],
        'retrace_levels': {0: None, 1: 'up'},
        'cumulative_pnl': [200.0, 500.0],
        'static_levels': [5764.0, 5822.5]
    }
    
    # Save both
    persistence.save_strategy_state("Strategy Long", state1)
    persistence.save_strategy_state("Strategy Short", state2)
    print("✓ Saved two strategies")
    
    # Load and verify
    loaded1 = persistence.load_strategy_state("Strategy Long")
    loaded2 = persistence.load_strategy_state("Strategy Short")
    print("✓ Loaded both strategies")
    
    assert loaded1['total_pnl'] == 100.0, "Strategy 1 PnL mismatch"
    assert loaded2['total_pnl'] == 500.0, "Strategy 2 PnL mismatch"
    assert loaded1['open_trade_count'] == 1, "Strategy 1 trade count mismatch"
    assert loaded2['open_trade_count'] == 3, "Strategy 2 trade count mismatch"
    
    print("✓ Both strategies maintain separate state")
    print("Test 2: PASSED\n")

def test_incremental_updates():
    """Test incremental updates (adding trades without duplicating)."""
    print("=== Test 3: Incremental Updates ===")
    
    persistence = StatePersistence(TEST_DB)
    
    # Initial state with 2 trades
    state = {
        'current_cash_value': 1000.0,
        'open_trade_count': 0,
        'total_pnl': 150.0,
        'price': 5800.0,
        'last_price': 5799.0,
        'high_price': 5801.0,
        'low_price': 5798.0,
        'index': str(datetime.now()),
        'winrate': 100.0,
        'avg_winner': 75.0,
        'avg_loser': 0.0,
        'total_trade': 2,
        'reward_to_risk': 0.0,
        'max_losing_streak': 0,
        'trade_history': [
            (datetime.now(), 'BUY', 5800.0, 0),
            (datetime.now(), 'EXIT', 5825.0, 75.0),
        ],
        'open_trade_list': [],
        'retrace_levels': {},
        'cumulative_pnl': [75.0],
        'static_levels': []
    }
    
    persistence.save_strategy_state("Test Incremental", state)
    print("✓ Saved initial state with 2 trades")
    
    # Add 2 more trades
    state['trade_history'].extend([
        (datetime.now(), 'BUY', 5830.0, 0),
        (datetime.now(), 'EXIT', 5855.0, 75.0),
    ])
    state['cumulative_pnl'].append(150.0)
    state['total_trade'] = 4
    state['total_pnl'] = 150.0
    
    persistence.save_strategy_state("Test Incremental", state)
    print("✓ Updated state with 2 additional trades")
    
    # Verify
    loaded = persistence.load_strategy_state("Test Incremental")
    assert len(loaded['trade_history']) == 4, f"Expected 4 trades, got {len(loaded['trade_history'])}"
    assert len(loaded['cumulative_pnl']) == 2, f"Expected 2 PnL values, got {len(loaded['cumulative_pnl'])}"
    
    print("✓ Incremental updates work correctly")
    print("Test 3: PASSED\n")

def test_list_and_delete():
    """Test listing and deleting strategies."""
    print("=== Test 4: List and Delete ===")
    
    persistence = StatePersistence(TEST_DB)
    
    # List strategies
    strategies = persistence.list_strategies()
    print(f"✓ Found {len(strategies)} strategies in database")
    for s in strategies:
        print(f"  - {s}")
    
    # Delete one
    if strategies:
        to_delete = strategies[0]
        persistence.delete_strategy_state(to_delete)
        print(f"✓ Deleted '{to_delete}'")
        
        # Verify deletion
        remaining = persistence.list_strategies()
        assert to_delete not in remaining, "Strategy not deleted"
        print(f"✓ Verified deletion (now {len(remaining)} strategies)")
    
    print("Test 4: PASSED\n")

def main():
    """Run all tests."""
    print("=" * 50)
    print("State Persistence Test Suite")
    print("=" * 50)
    
    # Clean up any previous test database
    cleanup()
    
    try:
        # Run tests
        test_basic_persistence()
        test_multiple_strategies()
        test_incremental_updates()
        test_list_and_delete()
        
        print("=" * 50)
        print("✓ ALL TESTS PASSED!")
        print("=" * 50)
        print("\nState persistence is working correctly.")
        print("You can now safely use it in your trading bot.\n")
        
    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: {e}\n")
        sys.exit(1)
    finally:
        # Clean up test database
        cleanup()

if __name__ == '__main__':
    main()
