from typing import List, Optional, Sequence
from .models import Bar


def ema(values: Sequence[float], period: int) -> List[Optional[float]]:
    out: List[Optional[float]] = [None] * len(values)
    if len(values) < period:
        return out
    seed = sum(values[:period]) / period
    out[period - 1] = seed
    alpha = 2.0 / (period + 1)
    for i in range(period, len(values)):
        seed = values[i] * alpha + seed * (1 - alpha)
        out[i] = seed
    return out


def atr(bars: Sequence[Bar], period: int) -> List[Optional[float]]:
    tr: List[float] = []
    for i, bar in enumerate(bars):
        prev = bars[i - 1].close if i else bar.close
        tr.append(max(bar.high - bar.low, abs(bar.high - prev), abs(bar.low - prev)))
    return ema(tr, period)


def confirmed_swing_lows(bars: Sequence[Bar], window: int) -> List[Optional[float]]:
    """At t, exposes pivots only after window right-hand bars have closed."""
    out: List[Optional[float]] = [None] * len(bars)
    last = None
    for t in range(len(bars)):
        candidate = t - window
        if candidate >= window:
            lo = bars[candidate].low
            segment = bars[candidate - window:candidate + window + 1]
            if all(lo <= b.low for b in segment):
                last = lo
        out[t] = last
    return out

