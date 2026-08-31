from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional


@dataclass(frozen=True)
class Bar:
    timestamp: date
    symbol: str
    open: float
    high: float
    low: float
    close: float
    volume: float

    def __post_init__(self):
        if min(self.open, self.high, self.low, self.close) <= 0:
            raise ValueError("OHLC prices must be positive")
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("invalid OHLC range")


@dataclass(frozen=True)
class Signal:
    created_at: date
    symbol: str
    side: str
    reference_price: float
    stop: float
    atr: float
    regime: str
    relative_strength: float
    reason: str


@dataclass
class Position:
    symbol: str
    entry_date: date
    entry: float
    quantity: float
    initial_quantity: float
    initial_stop: float
    stop: float
    atr: float
    risk_amount: float
    tp1: float
    tp2: float
    tp1_done: bool = False
    tp2_done: bool = False
    realized_pnl: float = 0.0
    fees: float = 0.0
    highest: float = 0.0
    mae: float = 0.0
    mfe: float = 0.0
    entry_reason: str = ""


@dataclass(frozen=True)
class Trade:
    symbol: str
    entry_date: date
    exit_date: date
    entry: float
    exit: float
    pnl: float
    r_multiple: float
    fees: float
    holding_days: int
    mae: float
    mfe: float
    reason: str


@dataclass
class BacktestResult:
    equity: List[Dict[str, float]] = field(default_factory=list)
    trades: List[Trade] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)

