# Multiple Position Feature Documentation

## Overview

The Trade Pro framework has been enhanced to support multiple concurrent positions while maintaining full backward compatibility with existing strategies. This allows for more sophisticated trading strategies that can manage several trades simultaneously.

## Key Features

### 1. **Backward Compatibility**

- All existing strategies work without any modifications
- Default behavior remains single position mode
- No breaking changes to existing APIs

### 2. **Multiple Position Support**

- Execute multiple trades concurrently
- Individual position sizing per trade
- Independent stop-loss and take-profit levels per trade
- Configurable maximum concurrent trades
- Intelligent balance management

### 3. **Enhanced Trade Management**

- Each trade is tracked individually with unique IDs
- Detailed trade metadata storage
- Real-time position monitoring
- Automatic position size calculation based on available balance

## Configuration

### Basic Setup

To enable multiple positions in your strategy, update the constructor:

```python
class MyStrategy(Base):
    def __init__(self, ...):
        super().__init__(
            symbol,
            initial_balance,
            timeframes,
            # Enable multiple positions
            allow_multiple_positions=True,
            max_concurrent_trades=3,
            position_size_pct=0.25,  # 25% of available balance per trade
            ...
        )
```

### Parameters

- **`allow_multiple_positions`** (bool): Enable/disable multiple position mode
- **`max_concurrent_trades`** (int): Maximum number of concurrent trades
- **`position_size_pct`** (float): Percentage of available balance to use per trade (0.0-1.0)

## Implementation Guide

### 1. **Entry Logic**

The framework provides two methods for entry conditions:

#### For Single Position Mode (Legacy)

```python
def entry_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
    # Your entry logic here
    return some_condition
```

#### For Multiple Position Mode (Optional Override)

```python
def should_enter_new_position(self, df: pd.DataFrame, *, index: int = -1) -> bool:
    # Custom logic for when to add new positions
    # By default, this calls entry_condition() if capacity allows
    return custom_condition
```

### 2. **Exit Logic**

#### For Single Position Mode (Legacy)

```python
def exit_condition(self, df: pd.DataFrame, *, index: int = -1) -> bool:
    # Your exit logic here
    return some_condition
```

#### For Multiple Position Mode (Recommended Override)

```python
def should_exit_position(self, trade: Trade, df: pd.DataFrame, *, index: int = -1) -> bool:
    # Individual trade exit logic
    current_price = df.iloc[index]["close"]

    # Check stop-loss/take-profit
    if trade.stop_loss > 0 and current_price <= trade.stop_loss:
        return True
    if trade.take_profit > 0 and current_price >= trade.take_profit:
        return True

    # Custom exit conditions
    return self.exit_condition(df, index=index)
```

### 3. **Trade Customization**

Override the entry execution to set individual trade parameters:

```python
def _execute_multiple_entry(self, row: pd.Series) -> Trade:
    # Create the trade using parent method
    trade = super()._execute_multiple_entry(row)

    # Set individual stop-loss and take-profit
    atr = row["ATR_14"]
    trade.stop_loss = trade.entry_price - 2 * atr
    trade.take_profit = trade.entry_price + 3 * atr

    # Store custom metadata
    trade.metadata.update({
        "entry_signal": "ema_cross",
        "atr_at_entry": atr,
        "market_condition": "bullish"
    })

    return trade
```

## Data Structures

### Trade Object

Each active trade is represented by a `Trade` dataclass:

```python
@dataclass
class Trade:
    id: str                    # Unique trade identifier
    entry_time: pd.Timestamp   # When the trade was opened
    entry_price: float         # Entry price
    units: float              # Number of units/shares
    position_size: float      # Total position value
    stop_loss: float = 0.0    # Stop-loss level
    take_profit: float = 0.0  # Take-profit level
    metadata: dict = {}       # Custom strategy data
```

### Active Trades Management

Access active trades information:

```python
# Get summary of all active trades
summary = self.get_active_trades_summary()
print(f"Active trades: {summary['count']}")
print(f"Total position value: ${summary['total_position_value']:.2f}")
print(f"Available balance: ${summary['available_balance']:.2f}")

# Access individual trades
for trade_id, trade in self.active_trades.items():
    print(f"Trade {trade_id}: Entry @ ${trade.entry_price:.2f}")
```

## Balance Management

The framework automatically manages balance allocation:

1. **Available Balance Calculation**: Current balance minus locked capital in active trades
2. **Position Sizing**: Each new trade uses `position_size_pct` of available balance
3. **Risk Management**: Prevents over-allocation of capital

## Example Strategies

### Simple Multiple EMA Strategy

```python
class MultiEmaStrategy(Base):
    def __init__(self, symbol, initial_balance, timeframes, **kwargs):
        super().__init__(
            symbol, initial_balance, timeframes,
            allow_multiple_positions=True,
            max_concurrent_trades=3,
            position_size_pct=0.3,
            **kwargs
        )

    def entry_condition(self, df, *, index=-1):
        # EMA crossover logic
        return df.iloc[index]["EMA_8"] > df.iloc[index]["EMA_21"]

    def should_exit_position(self, trade, df, *, index=-1):
        current_price = df.iloc[index]["close"]

        # Stop-loss/take-profit
        if trade.stop_loss > 0 and current_price <= trade.stop_loss:
            return True
        if trade.take_profit > 0 and current_price >= trade.take_profit:
            return True

        # Technical exit
        return df.iloc[index]["EMA_8"] < df.iloc[index]["EMA_21"]
```

## Configuration Files

### JSON Configuration Example

```json
{
  "strategy_name": "MultiEmaStrategy",
  "strategy_class": "trade_pro.strategy.strategies.multi_ema_strategy.MultiEmaStrategy",
  "symbol": "BTCUSDT",
  "initial_balance": 10000,
  "timeframes": ["1h"],
  "parameters": {
    "enable_multiple_positions": true,
    "max_positions": 3,
    "position_size_pct": 0.25,
    "fast_ema": 8,
    "medium_ema": 21,
    "slow_ema": 55
  }
}
```

## Migration Guide

### Existing Strategies

**No changes required!** All existing strategies continue to work as before:

```python
# This works exactly as before
class ExistingStrategy(Base):
    def __init__(self, ...):
        super().__init__(...)  # Default: single position mode

    def entry_condition(self, df, *, index=-1):
        return some_condition

    def exit_condition(self, df, *, index=-1):
        return some_condition
```

### Enabling Multiple Positions

To upgrade an existing strategy:

1. Add multiple position parameters to constructor
2. Optionally override `should_exit_position()` for individual trade logic
3. Optionally override `_execute_multiple_entry()` for custom trade setup

## Testing

Use the provided test script to compare single vs. multiple position performance:

```bash
python test_multiple_positions.py
```

This script:

- Tests backward compatibility
- Compares single vs. multiple position results
- Demonstrates proper usage patterns

## Best Practices

### 1. **Position Sizing**

- Use conservative `position_size_pct` values (0.2-0.33)
- Consider correlation between trades
- Account for drawdown scenarios

### 2. **Risk Management (Phase 6 Integration)**

**Using Multiple Positions with Risk Management:**

The framework includes an advanced risk management system that works seamlessly with multiple positions:

```python
class MyStrategy(Base):
    def __init__(self, symbol, initial_balance, timeframes, **kwargs):
        super().__init__(
            symbol, initial_balance, timeframes,
            # Multiple position settings
            allow_multiple_positions=True,
            max_concurrent_trades=3,
            # Risk management (Phase 6)
            use_risk_management=True,
            risk_per_trade_pct=0.02,  # 2% risk per trade
            max_daily_loss_pct=0.05,   # 5% daily loss limit
            max_drawdown_pct=0.15,     # 15% max drawdown
            min_risk_reward_ratio=2.0, # Minimum 2:1 R:R
            **kwargs
        )
```

**Key Features:**

- **Automatic Position Sizing**: Position size = (Capital × Risk%) / Stop Distance
- **Circuit Breakers**: Trading stops if daily loss or drawdown limits are hit
- **R:R Validation**: Trades are rejected if risk/reward ratio is too low
- **Total Risk Tracking**: System monitors combined risk across all positions

**Risk Profiles for Multiple Positions:**

- **Conservative**: `max_concurrent_trades=2`, `risk_per_trade_pct=0.01` (2% total risk)
- **Moderate**: `max_concurrent_trades=3`, `risk_per_trade_pct=0.02` (6% total risk)
- **Aggressive**: `max_concurrent_trades=5`, `risk_per_trade_pct=0.02` (10% total risk)

**Important Notes:**

- Circuit breakers apply to ALL trades combined (not per trade)
- With 3 concurrent trades at 2% risk each, you could have 6% total capital at risk
- The system tracks available balance after accounting for active positions
- For detailed risk parameters, see [config_guide.md](./config_guide.md)

### 3. **Stop-Losses and Exits**

- Always set stop-losses for individual trades
- Monitor total exposure across all positions
- Implement maximum drawdown limits

### 4. **Entry/Exit Logic**

- Use different signals for multiple entries to avoid correlated trades
- Implement individual exit conditions per trade
- Consider market conditions for position limits

### 5. **Performance Monitoring**

- Track individual trade performance
- Monitor capital allocation efficiency
- Compare with single position baselines

## Advanced Features

### Custom Trade Metadata

Store strategy-specific information with each trade:

```python
trade.metadata.update({
    "signal_strength": 0.85,
    "market_regime": "trending",
    "entry_catalyst": "earnings_beat",
    "expected_hold_time": "5_days"
})
```

### Dynamic Position Sizing

Adjust position sizes based on market conditions:

```python
def _execute_multiple_entry(self, row: pd.Series) -> Trade:
    # Calculate dynamic position size
    volatility = row["ATR_14"] / row["close"]
    dynamic_size = max(0.1, min(0.4, 1.0 / volatility))

    # Temporarily adjust position size
    original_size = self.position_size_pct
    self.position_size_pct = dynamic_size

    trade = super()._execute_multiple_entry(row)

    # Restore original setting
    self.position_size_pct = original_size

    return trade
```

## Troubleshooting

### Common Issues

1. **Balance Management**: Ensure `position_size_pct * max_concurrent_trades <= 1.0`
2. **Exit Logic**: Override `should_exit_position()` for individual trade management
3. **Performance**: Multiple positions may require more processing time

### Debug Information

Enable detailed logging to monitor trade execution:

```python
import logging
logging.getLogger("trade_pro.strategy.base").setLevel(logging.DEBUG)
```

This will show detailed entry/exit messages for each trade.
