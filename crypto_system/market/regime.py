from typing import List
from ..indicators import ema
from ..models import Bar


def btc_regimes(bars: List[Bar], fast: int = 20, slow: int = 50) -> List[str]:
    closes = [b.close for b in bars]
    ef, es = ema(closes, fast), ema(closes, slow)
    result = []
    for i, price in enumerate(closes):
        if ef[i] is None or es[i] is None:
            result.append("UNKNOWN")
        elif price < es[i] and ef[i] < es[i]:
            result.append("RISK_OFF")
        elif price > ef[i] > es[i]:
            result.append("BTC_TREND")
        else:
            result.append("BTC_ACCUMULATION")
    return result

