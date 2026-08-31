import csv
import json
from datetime import date, datetime
from pathlib import Path


def _usd(value):
    if isinstance(value, dict):
        return float(value.get("peggedUSD", 0.0))
    return float(value)


def build(stablecoin_json: str, market_csv: str, output: str) -> None:
    raw = json.loads(Path(stablecoin_json).read_text(encoding="utf-8"))
    supply = {}
    for row in raw:
        day = datetime.utcfromtimestamp(int(row["date"])).date()
        supply[day] = _usd(row["totalCirculatingUSD"])
    btc = {}
    with Path(market_csv).open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["symbol"] == "BTC":
                btc[date.fromisoformat(row["timestamp"])] = float(row["close"])
    days = sorted(set(supply).intersection(btc))
    target = Path(output); target.parent.mkdir(parents=True, exist_ok=True)
    fields = ["timestamp", "stablecoin_growth_30d_pct", "btc_etf_flow_5d_usd",
              "eth_etf_flow_5d_usd", "total_market_trend_30d_pct", "btc_trend_30d_pct",
              "funding_rate", "oi_growth_7d_pct"]
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for day in days:
            prior = date.fromordinal(day.toordinal() - 30)
            if prior not in supply or prior not in btc or not supply[prior] or not btc[prior]:
                continue
            writer.writerow({
                "timestamp": day.isoformat(),
                "stablecoin_growth_30d_pct": 100 * (supply[day] / supply[prior] - 1),
                "btc_etf_flow_5d_usd": "", "eth_etf_flow_5d_usd": "",
                "total_market_trend_30d_pct": "",
                "btc_trend_30d_pct": 100 * (btc[day] / btc[prior] - 1),
                "funding_rate": "", "oi_growth_7d_pct": "",
            })
