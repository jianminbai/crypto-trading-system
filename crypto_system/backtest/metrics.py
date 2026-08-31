import math
from statistics import mean, pstdev
from typing import Dict, List
from ..models import Trade


def calculate_metrics(equity: List[Dict[str, float]], trades: List[Trade], initial: float) -> Dict[str, float]:
    if not equity:
        return {}
    values = [p["equity"] for p in equity]
    returns = [values[i] / values[i - 1] - 1 for i in range(1, len(values)) if values[i - 1]]
    total = values[-1] / initial - 1
    years = max((equity[-1]["ordinal"] - equity[0]["ordinal"]) / 365.25, 1 / 365.25)
    cagr = (values[-1] / initial) ** (1 / years) - 1 if values[-1] > 0 else -1.0
    peak, max_dd = values[0], 0.0
    for value in values:
        peak = max(peak, value)
        max_dd = min(max_dd, value / peak - 1)
    avg = mean(returns) if returns else 0.0
    vol = pstdev(returns) if len(returns) > 1 else 0.0
    downside = [min(r, 0) for r in returns]
    downvol = math.sqrt(mean([r * r for r in downside])) if downside else 0.0
    wins = [t for t in trades if t.pnl > 0]
    losses = [t for t in trades if t.pnl <= 0]
    gross_win = sum(t.pnl for t in wins)
    gross_loss = abs(sum(t.pnl for t in losses))
    avg_win_r = mean([t.r_multiple for t in wins]) if wins else 0.0
    avg_loss_r = abs(mean([t.r_multiple for t in losses])) if losses else 0.0
    win_rate = len(wins) / len(trades) if trades else 0.0
    expectancy = win_rate * avg_win_r - (1 - win_rate) * avg_loss_r
    max_wins = max_losses = current_wins = current_losses = 0
    for trade in trades:
        if trade.pnl > 0:
            current_wins += 1; current_losses = 0
        else:
            current_losses += 1; current_wins = 0
        max_wins = max(max_wins, current_wins); max_losses = max(max_losses, current_losses)
    exposed = [p for p in equity if p.get("gross_exposure", 0.0) > 0]
    avg_exposure = mean([p.get("gross_exposure", 0.0) / p["equity"] for p in equity if p["equity"] > 0])
    return {
        "total_return": total, "cagr": cagr, "max_drawdown": max_dd,
        "sharpe": avg / vol * math.sqrt(365) if vol else 0.0,
        "sortino": avg / downvol * math.sqrt(365) if downvol else 0.0,
        "calmar": cagr / abs(max_dd) if max_dd else 0.0,
        "profit_factor": gross_win / gross_loss if gross_loss else 0.0,
        "win_rate": win_rate, "average_win_r": avg_win_r, "average_loss_r": avg_loss_r,
        "average_r": mean([t.r_multiple for t in trades]) if trades else 0.0,
        "expectancy_r": expectancy, "number_of_trades": float(len(trades)),
        "fees_paid": sum(t.fees for t in trades),
        "average_holding_days": mean([t.holding_days for t in trades]) if trades else 0.0,
        "largest_win": max([t.pnl for t in trades], default=0.0),
        "largest_loss": min([t.pnl for t in trades], default=0.0)
        , "maximum_consecutive_wins": float(max_wins), "maximum_consecutive_losses": float(max_losses)
        , "exposure_time": len(exposed) / len(equity), "average_gross_exposure": avg_exposure
        , "average_mae_r": mean([t.mae for t in trades]) if trades else 0.0
        , "average_mfe_r": mean([t.mfe for t in trades]) if trades else 0.0
        , "funding_paid": 0.0
    }
