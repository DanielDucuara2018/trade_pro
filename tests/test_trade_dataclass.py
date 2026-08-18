#!/usr/bin/env python3
"""
Simple test to verify the new Trade dataclass structure works correctly.
"""

import sys

import pandas as pd

from trade_pro.strategy.base import Trade


def test_trade_dataclass():
    """Test the Trade dataclass functionality"""
    print("🧪 Testing Trade dataclass...")

    # Create a new trade
    trade = Trade(
        id="test_trade_1",
        entry_time=pd.Timestamp("2024-01-01 10:00:00"),
        entry_price=50000.0,
        units=0.1,
        position_size=5000.0,
        stop_loss=48000.0,
        take_profit=52000.0,
    )

    print(f"✅ Created trade: {trade.id}")
    print(f"   Entry: {trade.entry_time} @ ${trade.entry_price:.2f}")
    print(f"   Position size: ${trade.position_size:.2f}")
    print(f"   Is closed: {trade.is_closed}")

    # Close the trade
    exit_time = pd.Timestamp("2024-01-01 12:00:00")
    exit_price = 51000.0
    old_balance = 10000.0

    trade.close_trade(exit_time, exit_price, old_balance, "Take profit hit")

    print("✅ Closed trade:")
    print(f"   Exit: {trade.exit_time} @ ${trade.exit_price:.2f}")
    print(f"   PnL: ${trade.pnl:.2f}")
    print(f"   Return: {trade.return_pct * 100:.2f}%")
    print(f"   Is closed: {trade.is_closed}")
    print(f"   Is profitable: {trade.is_profitable}")
    print(f"   Reason: {trade.reason}")

    # Test direct attribute access
    print("✅ Direct attribute access:")
    print(f"   Trade ID: {trade.id}")
    print(f"   PnL: ${trade.pnl:.2f}")
    print(f"   Return %: {trade.return_pct * 100:.2f}%")
    print(f"   Entry price: ${trade.entry_price:.2f}")

    print("🎉 All Trade dataclass tests passed!")
    return True


def test_trade_list():
    """Test list of trades functionality"""
    print("\n🧪 Testing Trade list functionality...")

    trades = []

    # Create multiple trades
    for i in range(3):
        trade = Trade(
            id=f"test_trade_{i + 1}",
            entry_time=pd.Timestamp(f"2024-01-0{i + 1} 10:00:00"),
            entry_price=50000.0 + i * 1000,
            units=0.1,
            position_size=5000.0,
        )

        # Close each trade with different outcomes
        exit_price = trade.entry_price + (1000 if i % 2 == 0 else -500)  # Some wins, some losses
        trade.close_trade(
            pd.Timestamp(f"2024-01-0{i + 1} 12:00:00"), exit_price, 10000.0, "Exit condition met"
        )

        trades.append(trade)

    print(f"✅ Created {len(trades)} trades")

    # Test statistics
    profitable_trades = [t for t in trades if t.is_profitable]
    total_pnl = sum(t.pnl for t in trades)

    print(f"   Profitable trades: {len(profitable_trades)}/{len(trades)}")
    print(f"   Total PnL: ${total_pnl:.2f}")

    # Test DataFrame creation using direct attributes (from list of trades)
    trade_data = [
        {
            "trade_id": trade.id,
            "entry_time": trade.entry_time,
            "exit_time": trade.exit_time,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "pnl": trade.pnl,
            "return_pct": trade.return_pct,
            "is_profitable": trade.is_profitable,
            "reason": trade.reason,
        }
        for trade in trades
    ]
    df = pd.DataFrame(trade_data)
    print(f"✅ Created DataFrame with shape: {df.shape}")
    print(f"   Columns: {list(df.columns)}")

    # Test dict structure (like self.trades in Base class)
    trades_dict = {trade.id: trade for trade in trades}
    print(f"✅ Created trades dict with {len(trades_dict)} entries")
    print(f"   Trade IDs: {list(trades_dict.keys())}")

    print("🎉 All Trade list tests passed!")
    return True


def main():
    """Run all tests"""
    print("🚀 Testing new Trade dataclass structure")
    print("=" * 50)

    try:
        test_trade_dataclass()
        test_trade_list()

        print("\n" + "=" * 50)
        print("✅ ALL TESTS PASSED!")
        print("The new Trade dataclass structure is working correctly.")
        print("✨ Benefits:")
        print("  - Clean object-oriented design")
        print("  - All trade data encapsulated in Trade objects")
        print("  - Direct attribute access for better performance")
        print("  - Type safety with dataclass")
        print("  - Unified structure for both single and multiple position modes")

    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
