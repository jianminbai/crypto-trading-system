import random
from statistics import mean
from typing import Dict, List


def _percentile(values: List[float], probability: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(probability * (len(ordered) - 1))))
    return ordered[index]


def simulate_trade_r(r_multiples: List[float], risk_fraction: float, simulations: int = 10_000,
                     seed: int = 42, ruin_equity: float = 0.5) -> Dict[str, float]:
    if not r_multiples:
        raise ValueError("at least one trade is required")
    if not 0 < risk_fraction <= 0.01:
        raise ValueError("risk_fraction must be in (0, 1%]")
    rng = random.Random(seed)
    max_drawdowns = []
    ruined = dd20 = dd30 = 0
    for _ in range(simulations):
        sequence = list(r_multiples); rng.shuffle(sequence)
        equity = peak = 1.0
        worst = 0.0
        for r_value in sequence:
            equity *= max(0.0, 1.0 + risk_fraction * r_value)
            peak = max(peak, equity)
            worst = min(worst, equity / peak - 1.0)
        max_drawdowns.append(worst)
        ruined += equity <= ruin_equity
        dd20 += worst <= -0.20
        dd30 += worst <= -0.30
    # More negative is worse; lower-tail percentiles represent stress outcomes.
    return {"risk_per_trade": risk_fraction, "simulations": float(simulations),
            "expected_max_drawdown": mean(max_drawdowns),
            "max_drawdown_95": _percentile(max_drawdowns, 0.05),
            "max_drawdown_99": _percentile(max_drawdowns, 0.01),
            "probability_of_ruin": ruined / simulations,
            "probability_of_20pct_drawdown": dd20 / simulations,
            "probability_of_30pct_drawdown": dd30 / simulations}

