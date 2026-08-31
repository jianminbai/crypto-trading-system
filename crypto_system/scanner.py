from typing import Dict, List
from .indicators import atr, ema
from .market.regime import btc_regimes
from .models import Bar
from .strategy.breakout import breakout_flags
from .tokens.relative_strength import relative_strength
from .tokens.universe import build_universe


def market_status(data: Dict[str, List[Bar]], config: Dict) -> Dict:
    btc = data["BTC"]
    regimes = btc_regimes(btc, config["regime_ema_fast"], config["regime_ema_slow"])
    closes = [b.close for b in btc]
    fast = ema(closes, config["regime_ema_fast"])[-1]
    slow = ema(closes, config["regime_ema_slow"])[-1]
    return {"as_of": btc[-1].timestamp.isoformat(), "market_regime": regimes[-1],
            "btc_price": closes[-1], "btc_ema_fast": fast, "btc_ema_slow": slow}


def scan(data: Dict[str, List[Bar]], config: Dict) -> List[Dict]:
    btc = data["BTC"]
    btc_dates = [b.timestamp for b in btc]
    btc_close = [b.close for b in btc]
    universe = build_universe(data, config["minimum_history_days"],
                              config["minimum_average_quote_volume"],
                              config["universe_volume_window"], config["excluded_symbols"])
    output = []
    for symbol, bars in data.items():
        if symbol == "BTC" or not universe[symbol].eligible or [b.timestamp for b in bars] != btc_dates:
            continue
        closes = [b.close for b in bars]
        rs = relative_strength(closes, btc_close, config["relative_strength_window"])[-1]
        e20, e50 = ema(closes, 20)[-1], ema(closes, 50)[-1]
        av = atr(bars, config["atr_period"])[-1]
        breakout = breakout_flags(bars, config["breakout_days"], config["volume_window"], config["volume_multiple"])[-1]
        trend_score = 100.0 if e20 and e50 and closes[-1] > e20 > e50 else 50.0 if e50 and closes[-1] > e50 else 0.0
        rs_score = max(0.0, min(100.0, 50.0 + (rs or 0.0) * 250.0))
        final_score = 0.55 * rs_score + 0.45 * trend_score
        output.append({"rank": 0, "token": symbol, "price": closes[-1], "relative_strength": rs or 0.0,
                       "trend_score": trend_score, "final_score": final_score,
                       "breakout_confirmed": breakout, "atr": av or 0.0,
                       "quote_volume_30d": universe[symbol].average_quote_volume,
                       "trade_candidate": final_score >= 75 and breakout})
    output.sort(key=lambda row: row["final_score"], reverse=True)
    for i, row in enumerate(output, 1):
        row["rank"] = i
    return output

