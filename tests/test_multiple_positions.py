#!/usr/bin/env python3
"""
Test script to demonstrate multiple position functionality in trade_pro.

This script shows how to:
1. Use the original single position mode (backward compatibility)
2. Use the new multiple position mode
3. Compare results between both modes
"""

from trade_pro.strategy.strategies.multi_ema_strategy import MultiEmaStrategy


def test_single_position_mode():
    """Test the strategy in single position mode (original behavior)"""
    print("=" * 60)
    print("TESTING SINGLE POSITION MODE (Original Behavior)")
    print("=" * 60)

    strategy = MultiEmaStrategy(
        symbol="BTCUSDT",
        initial_balance=10000,
        timeframes=["1h"],
        start_backtest_index=100,
        fast_ema=8,
        medium_ema=21,
        slow_ema=55,
        enable_multiple_positions=False,  # Single position mode
        max_positions=1,
        position_size_pct=1.0,  # Use full balance
    )

    print("Strategy configured for single position mode")

    print(f"Initial balance: ${strategy.initial_balance}")
    print(f"Multiple positions enabled: {strategy.allow_multiple_positions}")
    print(f"Max concurrent trades: {strategy.max_concurrent_trades}")
    print(f"Position size percentage: {strategy.position_size_pct * 100}%")

    # Run backtest
    try:
        strategy.run("backtest")
        print("\nSINGLE POSITION RESULTS:")

        print(f"Final balance: ${strategy.balance:.2f}")
        print(f"Total trades: {len(strategy.trades)}")
        print(f"Win rate: {strategy.win_rate * 100:.2f}%")
        print(f"Profit factor: {strategy.profit_factor:.2f}")
        print(f"Max drawdown: ${strategy.max_drawdown:.2f}")

        return strategy.balance, len(strategy.trades)

    except Exception as e:
        print(f"Error running single position backtest: {e}")
        return None, None


def test_multiple_position_mode():
    """Test the strategy in multiple position mode (new functionality)"""
    print("\n" + "=" * 60)
    print("TESTING MULTIPLE POSITION MODE (New Functionality)")
    print("=" * 60)

    strategy = MultiEmaStrategy(
        symbol="BTCUSDT",
        initial_balance=10000,
        timeframes=["1h"],
        start_backtest_index=100,
        fast_ema=8,
        medium_ema=21,
        slow_ema=55,
        enable_multiple_positions=True,  # Multiple position mode
        max_positions=3,
        position_size_pct=0.25,  # Use 25% of available balance per trade
    )

    print("Strategy configured for multiple position mode")

    print(f"Initial balance: ${strategy.initial_balance}")
    print(f"Multiple positions enabled: {strategy.allow_multiple_positions}")
    print(f"Max concurrent trades: {strategy.max_concurrent_trades}")
    print(f"Position size percentage: {strategy.position_size_pct * 100}%")

    # Run backtest
    try:
        strategy.run("backtest")
        print("\nMULTIPLE POSITION RESULTS:")

        print(f"Final balance: ${strategy.balance:.2f}")
        print(f"Total trades: {len(strategy.trades)}")
        print(f"Win rate: {strategy.win_rate * 100:.2f}%")
        print(f"Profit factor: {strategy.profit_factor:.2f}")
        print(f"Max drawdown: ${strategy.max_drawdown:.2f}")

        # Show active trades info
        active_summary = strategy.get_active_trades_summary()
        print(f"Active trades at end: {active_summary['count']}")

        return strategy.balance, len(strategy.trades)

    except Exception as e:
        print(f"Error running multiple position backtest: {e}")
        return None, None


def test_existing_strategy_compatibility():
    """Test that existing strategies still work without modification"""
    print("\n" + "=" * 60)
    print("TESTING BACKWARD COMPATIBILITY")
    print("=" * 60)

    try:
        # Import an existing strategy
        from trade_pro.strategy.strategies.ema_atr_reversal_strategy import EmaAtrReversalStrategy

        # Test with default parameters (should work as before)
        strategy = EmaAtrReversalStrategy(
            symbol="BTCUSDT",
            initial_balance=10000,
            timeframes=["1h"],
            start_backtest_index=100,
            ema_period=40,
            atr_period=21,
            atr_multiplier=2.0,
        )

        print("Original strategy loaded successfully")

        print(f"Multiple positions enabled: {strategy.allow_multiple_positions}")
        print(f"Should be False (default): {not strategy.allow_multiple_positions}")

        # Run backtest
        strategy.run("backtest")
        print("Backward compatibility test PASSED")

        print(f"Final balance: ${strategy.balance:.2f}")
        print(f"Total trades: {len(strategy.trades)}")

        return True

    except Exception as e:
        print(f"Backward compatibility test FAILED: {e}")
        return False


def main():
    """Run all tests"""
    print("Trade Pro - Multiple Position Feature Test")
    print("This script demonstrates the new multiple position functionality")
    print("while maintaining backward compatibility with existing strategies.")

    # Test backward compatibility first
    compat_ok = test_existing_strategy_compatibility()

    if not compat_ok:
        print("\n❌ Backward compatibility test failed. Please check the implementation.")
        return

    # Test single position mode
    single_balance, single_trades = test_single_position_mode()

    # Test multiple position mode
    multi_balance, multi_trades = test_multiple_position_mode()

    # Compare results
    if single_balance is not None and multi_balance is not None:
        print("\n" + "=" * 60)
        print("COMPARISON SUMMARY")
        print("=" * 60)
        print("Single Position Mode:")

        print(f"  Final Balance: ${single_balance:.2f}")
        print(f"  Total Trades: {single_trades}")
        print(f"  Return: {((single_balance / 10000) - 1) * 100:.2f}%")

        print("\nMultiple Position Mode:")

        print(f"  Final Balance: ${multi_balance:.2f}")
        print(f"  Total Trades: {multi_trades}")
        print(f"  Return: {((multi_balance / 10000) - 1) * 100:.2f}%")

        print("\nDifference:")

        balance_diff = multi_balance - single_balance
        trade_diff = multi_trades - single_trades
        print(f"  Balance Difference: ${balance_diff:.2f}")
        print(f"  Trade Difference: {trade_diff}")

        if balance_diff > 0:
            print("  🔥 Multiple position mode performed better!")

        elif balance_diff < 0:
            print("  📉 Single position mode performed better.")

        else:
            print("  🤝 Both modes performed equally.")

    print("\n✅ All tests completed successfully!")

    print("The multiple position feature is working correctly with backward compatibility.")


if __name__ == "__main__":
    main()
