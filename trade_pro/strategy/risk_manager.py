"""Risk Management Module"""

import logging
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from trade_pro.strategy.base import Mode

logger = logging.getLogger(__name__)


class RiskManager:
    """Handles risk management, position sizing, and circuit breakers"""

    def __init__(
        self,
        initial_balance: float,
        use_risk_management: bool = False,
        risk_per_trade_pct: float = 0.02,
        max_daily_loss_pct: float = 0.05,
        max_drawdown_pct: float = 0.20,
        min_risk_reward_ratio: float = 1.5,
        position_size_pct: float = 1.0,
    ):
        self.use_risk_management = use_risk_management
        self.risk_per_trade_pct = risk_per_trade_pct
        self.max_daily_loss_pct = max_daily_loss_pct
        self.max_drawdown_pct = max_drawdown_pct
        self.min_risk_reward_ratio = min_risk_reward_ratio
        self.position_size_pct = position_size_pct

        # State tracking
        self._daily_start_balance = initial_balance
        self._trading_day_start = None
        self._peak_balance = initial_balance
        self._circuit_breaker_triggered = False

    def reset(self, balance: float | None = None) -> None:
        """Reset risk management state"""
        if balance is not None:
            self._daily_start_balance = balance
            self._peak_balance = balance
        self._trading_day_start = None
        self._circuit_breaker_triggered = False

    def check_circuit_breakers(
        self, current_time: pd.Timestamp, current_balance: float, mode: "Mode", telegram_bot=None
    ) -> bool:
        """Check if circuit breakers have been triggered"""
        if not self.use_risk_management:
            return False

        if self._circuit_breaker_triggered:
            return True

        # Reset daily tracking at start of new day
        if self._trading_day_start is None or current_time.date() != self._trading_day_start:
            self._daily_start_balance = current_balance
            self._trading_day_start = current_time.date()

        # Update peak balance
        if current_balance > self._peak_balance:
            self._peak_balance = current_balance

        # Check daily loss limit
        daily_loss = self._daily_start_balance - current_balance
        daily_loss_pct = (
            daily_loss / self._daily_start_balance if self._daily_start_balance > 0 else 0
        )
        if daily_loss_pct >= self.max_daily_loss_pct:
            self._circuit_breaker_triggered = True
            msg = f"⛔ CIRCUIT BREAKER: Daily loss limit reached ({daily_loss_pct:.2%})"
            logger.warning(msg)
            if mode == "live" and telegram_bot:
                telegram_bot.send_telegram_message(msg)
            return True

        # Check max drawdown limit
        drawdown = self._peak_balance - current_balance
        drawdown_pct = drawdown / self._peak_balance if self._peak_balance > 0 else 0
        if drawdown_pct >= self.max_drawdown_pct:
            self._circuit_breaker_triggered = True
            msg = f"⛔ CIRCUIT BREAKER: Max drawdown limit reached ({drawdown_pct:.2%})"
            logger.warning(msg)
            if mode == "live" and telegram_bot:
                telegram_bot.send_telegram_message(msg)
            return True

        return False

    def calculate_position_size(
        self, entry_price: float, stop_loss_price: float, available_capital: float
    ) -> float:
        """Calculate position size based on risk per trade"""
        if not self.use_risk_management or stop_loss_price == 0:
            return available_capital * self.position_size_pct

        # Risk amount in dollars
        risk_amount = available_capital * self.risk_per_trade_pct

        # Risk per unit (distance from entry to stop)
        risk_per_unit = abs(entry_price - stop_loss_price)

        if risk_per_unit == 0:
            return available_capital * self.position_size_pct

        # Position size = risk amount / risk per unit
        units = risk_amount / risk_per_unit
        position_value = units * entry_price

        # Cap at maximum position size
        max_position = available_capital * self.position_size_pct
        return min(position_value, max_position)

    def validate_risk_reward(
        self, entry_price: float, stop_loss: float, take_profit: float
    ) -> bool:
        """Validate trade meets minimum risk/reward ratio"""
        if not self.use_risk_management or stop_loss == 0 or take_profit == 0:
            return True

        risk = abs(entry_price - stop_loss)
        reward = abs(take_profit - entry_price)

        if risk == 0:
            return True

        risk_reward = reward / risk
        return risk_reward >= self.min_risk_reward_ratio

    def get_metrics(self, current_balance: float) -> dict:
        """Get current risk management metrics"""
        if not self.use_risk_management:
            return {}

        daily_loss = self._daily_start_balance - current_balance
        daily_loss_pct = (
            daily_loss / self._daily_start_balance if self._daily_start_balance > 0 else 0
        )

        drawdown = self._peak_balance - current_balance
        drawdown_pct = drawdown / self._peak_balance if self._peak_balance > 0 else 0

        return {
            "circuit_breaker_active": self._circuit_breaker_triggered,
            "daily_start_balance": self._daily_start_balance,
            "daily_pnl": -daily_loss,
            "daily_loss_pct": daily_loss_pct,
            "daily_loss_limit": self.max_daily_loss_pct,
            "peak_balance": self._peak_balance,
            "current_drawdown": drawdown,
            "drawdown_pct": drawdown_pct,
            "drawdown_limit": self.max_drawdown_pct,
            "risk_per_trade": self.risk_per_trade_pct,
            "min_risk_reward": self.min_risk_reward_ratio,
        }
