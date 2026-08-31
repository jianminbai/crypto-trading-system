from typing import List, Optional
from ..models import Bar


def breakout_flags(bars: List[Bar], days: int, volume_window: int,
                   volume_multiple: float) -> List[bool]:
    flags = [False] * len(bars)
    warmup = max(days, volume_window)
    for i in range(warmup, len(bars)):
        prior_high = max(b.high for b in bars[i - days:i])
        avg_volume = sum(b.volume for b in bars[i - volume_window:i]) / volume_window
        flags[i] = bars[i].close > prior_high and bars[i].volume > avg_volume * volume_multiple
    return flags

