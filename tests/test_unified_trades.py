#!/usr/bin/env python3
"""
Quick test to verify the unified trades structure works correctly.
"""

import sys
from pathlib import Path

import pandas as pd

# Add the trade_pro package to Python path
sys.path.insert(0, str(Path(__file__).parent))

from trade_pro.strategy.base import Base, Trade


# Create a minimal strategy for testing
class TestStrategy(Base):
    def check_config(self) -> bool:
        return True

    def compute_indicators(self, data):
        return data[self.timeframes[0]]  # Just return first timeframe data

    def entry_condition(self, df, *, index=-1) -> bool:
        return False  # No entries for this test

    def exit_condition(self, df, *, index=-1) -> bool:
        return False  # No exits for this test


def test_unified_trades():
    """Test the unified trades structure"""
    print("🧪 Testing unified trades structure...")

    # Create strategy instance
    strategy = TestStrategy(
        symbol="BTC/USDT",
        initial_balance=10000.0,
        timeframes=["1h"],
        allow_multiple_positions=True,
        max_concurrent_trades=3,
    )

    # Create some test trades directly
    trade1 = Trade(
        id="test_1",
        entry_time=pd.Timestamp("2024-01-01 10:00:00"),
        entry_price=50000.0,
        units=0.1,
        position_size=5000.0,
    )

    trade2 = Trade(
        id="test_2",
        entry_time=pd.Timestamp("2024-01-01 11:00:00"),
        entry_price=51000.0,
        units=0.1,
        position_size=5100.0,
    )

    # Add trades to strategy
    strategy.trades["test_1"] = trade1
    strategy.trades["test_2"] = trade2

    print(f"✅ Total trades: {len(strategy.trades)}")
    print(f"✅ Active trades: {len(strategy.active_trades)}")
    print(f"✅ Completed trades: {len(strategy.completed_trades)}")

    # Close one trade
    trade1.close_trade(pd.Timestamp("2024-01-01 12:00:00"), 52000.0, 10000.0, "Test close")

    print("\nAfter closing trade1:")

    print(f"✅ Total trades: {len(strategy.trades)}")
    print(f"✅ Active trades: {len(strategy.active_trades)}")
    print(f"✅ Completed trades: {len(strategy.completed_trades)}")

    # Verify the properties work correctly
    assert len(strategy.trades) == 2
    assert len(strategy.active_trades) == 1
    assert len(strategy.completed_trades) == 1
    assert "test_1" in strategy.completed_trades
    assert "test_2" in strategy.active_trades

    print("🎉 All unified trades tests passed!")
    return True


if __name__ == "__main__":
    test_unified_trades()
