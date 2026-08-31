from dataclasses import dataclass


@dataclass(frozen=True)
class SizeResult:
    quantity: float
    notional: float
    risk_amount: float
    effective_loss_per_unit: float


def position_size(equity: float, risk_fraction: float, entry: float, stop: float,
                  fee_rate: float, slippage_rate: float) -> SizeResult:
    if not 0 < risk_fraction <= 0.01:
        raise ValueError("risk_fraction must be in (0, 1%]")
    if stop >= entry:
        raise ValueError("long stop must be below entry")
    risk_amount = equity * risk_fraction
    entry_fill = entry * (1 + slippage_rate)
    stop_fill = stop * (1 - slippage_rate)
    costs = entry_fill * fee_rate + stop_fill * fee_rate
    loss_per_unit = entry_fill - stop_fill + costs
    quantity = risk_amount / loss_per_unit
    return SizeResult(quantity, quantity * entry_fill, risk_amount, loss_per_unit)

