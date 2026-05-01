import logging
from datetime import datetime
from typing import Optional, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class OrderStatus(Enum):
    PENDING = "pending"
    EXECUTED = "executed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class Order:
    """Represents a trade order"""
    order_id: str
    contract_id: str
    signal_id: str
    order_type: str  # BUY or SELL
    quantity: float
    price: float
    status: OrderStatus = OrderStatus.PENDING
    executed_price: Optional[float] = None
    executed_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)


class TradeExecutor:
    """Executes trades based on signals from the market monitor"""

    def __init__(self, account_balance: float = 5000, min_confidence: float = 0.60):
        self.account_balance = account_balance
        self.min_confidence = min_confidence
        self.orders: List[Order] = []
        self.trade_history: List[Order] = []
        self.position_size_limit = 500  # Max per trade unless trade exceeds $500

    def can_execute_trade(self, signal, quantity: float, price: float) -> tuple[bool, str]:
        """Validate if trade can be executed"""
        # Check confidence threshold
        if signal.confidence < self.min_confidence:
            return False, f"Confidence {signal.confidence:.0%} below threshold {self.min_confidence:.0%}"

        # Check account balance
        trade_cost = quantity * price
        if trade_cost > self.account_balance:
            return False, f"Insufficient balance: need ${trade_cost:.2f}, have ${self.account_balance:.2f}"

        return True, "OK"

    def execute_trade(self, signal, quantity: float, price: float) -> Optional[Order]:
        """Execute a trade order"""
        can_execute, reason = self.can_execute_trade(signal, quantity, price)

        if not can_execute:
            logger.warning(f"Cannot execute trade: {reason}")
            return None

        # Generate order
        order_id = f"ORD-{datetime.now().strftime('%Y%m%d%H%M%S')}-{signal.contract_id}"
        order = Order(
            order_id=order_id,
            contract_id=signal.contract_id,
            signal_id=signal.contract_id,
            order_type=signal.signal_type,
            quantity=quantity,
            price=price
        )

        # Execute order (in real implementation, would call Kalshi API)
        order.executed_price = price
        order.executed_at = datetime.now()
        order.status = OrderStatus.EXECUTED

        # Update balance
        trade_amount = quantity * price
        if signal.signal_type == "BUY":
            self.account_balance -= trade_amount
        else:  # SELL
            self.account_balance += trade_amount

        self.orders.append(order)
        self.trade_history.append(order)

        logger.info(
            f"✓ EXECUTED {order.order_type}: {signal.title} | "
            f"Qty: {quantity} @ ${price} | Balance: ${self.account_balance:.2f}"
        )

        return order

    def get_position_value(self, quantity: float, current_price: float) -> float:
        """Calculate current position value"""
        return quantity * current_price

    def get_account_summary(self) -> dict:
        """Get trading account summary"""
        total_trades = len(self.trade_history)
        buys = sum(1 for o in self.trade_history if o.order_type == "BUY")
        sells = sum(1 for o in self.trade_history if o.order_type == "SELL")

        return {
            "balance": self.account_balance,
            "total_trades": total_trades,
            "buys": buys,
            "sells": sells,
            "win_rate": self._calculate_win_rate()
        }

    def _calculate_win_rate(self) -> float:
        """Calculate winning trade percentage"""
        if not self.trade_history:
            return 0.0

        # TODO: Implement PnL calculation when order closes
        return 0.0

    def get_large_trades(self, threshold: float = 500) -> List[Order]:
        """Get trades over specified threshold"""
        return [o for o in self.trade_history if (o.quantity * o.executed_price) >= threshold]
