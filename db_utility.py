#!/usr/bin/env python3
"""
Utility script to inspect and manage the trading bot state database.
"""

import argparse
import sys
from datetime import datetime
from lib.state_persistence import StatePersistence

def list_strategies(db_path: str):
    """List all strategies stored in the database."""
    persistence = StatePersistence(db_path)
    strategies = persistence.list_strategies()
    
    if not strategies:
        print("No strategies found in database.")
        return
    
    print(f"\nFound {len(strategies)} strategy/strategies:\n")
    for strategy_name in strategies:
        last_update = persistence.get_last_update_time(strategy_name)
        print(f"  - {strategy_name}")
        print(f"    Last updated: {last_update}")
        print()

def show_strategy_state(db_path: str, strategy_name: str):
    """Show detailed state for a specific strategy."""
    persistence = StatePersistence(db_path)
    state = persistence.load_strategy_state(strategy_name)
    
    if not state:
        print(f"No state found for strategy: {strategy_name}")
        return
    
    print(f"\n=== State for {strategy_name} ===\n")
    print(f"Current Cash Value: ${state['current_cash_value']:.2f}")
    print(f"Total PnL: ${state['total_pnl']:.2f}")
    print(f"Open Trade Count: {state['open_trade_count']}")
    print(f"Total Trades: {state['total_trade']}")
    print(f"Win Rate: {state['winrate']:.2f}%")
    print(f"Average Winner: ${state['avg_winner']:.2f}")
    print(f"Average Loser: ${state['avg_loser']:.2f}")
    print(f"Reward to Risk: {state['reward_to_risk']:.2f}")
    print(f"Max Losing Streak: {state['max_losing_streak']}")
    print(f"\nLast Price: {state['last_price']}")
    print(f"Last Index: {state['index']}")
    
    print(f"\n--- Open Trades ---")
    if state['open_trade_list']:
        for i, trade in enumerate(state['open_trade_list'], 1):
            print(f"  Trade {i}:")
            print(f"    Entry Time: {trade[0]}")
            print(f"    Entry Price: {trade[1]}")
            print(f"    Stop Level: {trade[2]}")
            print(f"    Trailing Stop: {trade[3]}")
            print(f"    Traded Level: {trade[4]}")
            print(f"    Take Profit Level: {trade[5]}")
    else:
        print("  No open trades")
    
    print(f"\n--- Trade History (last 10) ---")
    if state['trade_history']:
        for trade in state['trade_history'][-10:]:
            print(f"  {trade[0]}: {trade[1]} @ {trade[2]:.2f}, PnL: ${trade[3]:.2f}")
    else:
        print("  No trade history")
    
    print(f"\n--- Retrace Levels ---")
    down_count = sum(1 for v in state['retrace_levels'].values() if v == 'down')
    up_count = sum(1 for v in state['retrace_levels'].values() if v == 'up')
    none_count = sum(1 for v in state['retrace_levels'].values() if v is None)
    print(f"  Total levels: {len(state['retrace_levels'])}")
    print(f"  Crossed DOWN: {down_count}")
    print(f"  Crossed UP: {up_count}")
    print(f"  Not crossed: {none_count}")
    
    if state['static_levels']:
        print(f"\n--- Static Levels ---")
        print(f"  Total static levels loaded: {len(state['static_levels'])}")
        print(f"  Range: {min(state['static_levels']):.2f} - {max(state['static_levels']):.2f}")

def delete_strategy(db_path: str, strategy_name: str, confirm: bool = False):
    """Delete a strategy's state from the database."""
    if not confirm:
        response = input(f"Are you sure you want to delete '{strategy_name}'? (yes/no): ")
        if response.lower() != 'yes':
            print("Deletion cancelled.")
            return
    
    persistence = StatePersistence(db_path)
    persistence.delete_strategy_state(strategy_name)
    print(f"Successfully deleted state for: {strategy_name}")

def reset_all(db_path: str, confirm: bool = False):
    """Delete all strategies from the database."""
    if not confirm:
        response = input("Are you sure you want to delete ALL strategies? This cannot be undone! (yes/no): ")
        if response.lower() != 'yes':
            print("Reset cancelled.")
            return
    
    persistence = StatePersistence(db_path)
    strategies = persistence.list_strategies()
    
    for strategy_name in strategies:
        persistence.delete_strategy_state(strategy_name)
        print(f"Deleted: {strategy_name}")
    
    print(f"\nSuccessfully reset database. Deleted {len(strategies)} strategies.")

def main():
    parser = argparse.ArgumentParser(
        description="Utility to inspect and manage trading bot state database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all strategies
  python db_utility.py list
  
  # Show detailed state for a strategy
  python db_utility.py show "Swing Long Strategy"
  
  # Delete a specific strategy
  python db_utility.py delete "Swing Long Strategy"
  
  # Reset all strategies (use with caution!)
  python db_utility.py reset-all
        """
    )
    
    parser.add_argument(
        'command',
        choices=['list', 'show', 'delete', 'reset-all'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'strategy_name',
        nargs='?',
        help='Strategy name (required for show/delete commands)'
    )
    
    parser.add_argument(
        '--db',
        default='trading_bot_state.db',
        help='Path to database file (default: trading_bot_state.db)'
    )
    
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompts'
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == 'list':
            list_strategies(args.db)
        
        elif args.command == 'show':
            if not args.strategy_name:
                print("Error: strategy_name is required for 'show' command")
                sys.exit(1)
            show_strategy_state(args.db, args.strategy_name)
        
        elif args.command == 'delete':
            if not args.strategy_name:
                print("Error: strategy_name is required for 'delete' command")
                sys.exit(1)
            delete_strategy(args.db, args.strategy_name, args.yes)
        
        elif args.command == 'reset-all':
            reset_all(args.db, args.yes)
    
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
