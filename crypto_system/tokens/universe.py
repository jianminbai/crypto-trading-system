from dataclasses import dataclass
from typing import Dict, List
from ..models import Bar


@dataclass(frozen=True)
class UniverseDecision:
    symbol: str
    eligible: bool
    average_quote_volume: float
    history_days: int
    reason: str


def build_universe(data: Dict[str, List[Bar]], minimum_history_days: int,
                   minimum_average_quote_volume: float, volume_window: int,
                   excluded_symbols: List[str]) -> Dict[str, UniverseDecision]:
    decisions = {}
    excluded = set(excluded_symbols)
    for symbol, bars in data.items():
        sample = bars[-volume_window:]
        quote_volume = (sum(b.close * b.volume for b in sample) / len(sample)) if sample else 0.0
        reasons = []
        if symbol in excluded:
            reasons.append("excluded stable/wrapped token")
        if len(bars) < minimum_history_days:
            reasons.append("insufficient history")
        if quote_volume < minimum_average_quote_volume:
            reasons.append("insufficient quote volume")
        decisions[symbol] = UniverseDecision(symbol, not reasons, quote_volume, len(bars),
                                             "; ".join(reasons) if reasons else "eligible")
    return decisions

