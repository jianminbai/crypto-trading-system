from typing import Optional


def initial_stop(entry: float, atr_value: float, swing_low: Optional[float],
                 atr_multiplier: float, atr_buffer: float) -> float:
    atr_stop = entry - atr_multiplier * atr_value
    if swing_low is None or swing_low >= entry:
        return atr_stop
    return max(atr_stop, swing_low - atr_buffer * atr_value)


def trailing_stop(current: float, highest: float, atr_value: float,
                  swing_low: Optional[float], multiplier: float, buffer: float) -> float:
    fallback = highest - multiplier * atr_value
    structural = swing_low - buffer * atr_value if swing_low is not None else fallback
    return max(current, min(highest, structural if swing_low is not None else fallback))

