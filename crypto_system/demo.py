import csv
import math
import random
from datetime import date, timedelta
from pathlib import Path


def generate(path: str, days: int = 900) -> None:
    """Deterministic synthetic fixture for plumbing tests, never performance evidence."""
    rng = random.Random(7)
    symbols = {"BTC": (20000, 0.0007), "ETH": (1200, 0.0009), "SOL": (30, 0.0012),
               "BNB": (250, 0.0006), "XRP": (0.4, 0.0005), "ADA": (0.35, 0.0004),
               "AVAX": (15, 0.0008), "LINK": (7, 0.0009)}
    rows = []
    start = date(2021, 1, 1)
    for symbol, (price, drift) in symbols.items():
        p = price
        for i in range(days):
            cycle = 0.012 * math.sin(i / 55 + len(symbol))
            ret = drift + cycle + rng.gauss(0, 0.025)
            op = p * (1 + rng.gauss(0, 0.006)); close = max(0.001, op * (1 + ret))
            high = max(op, close) * (1 + abs(rng.gauss(0.009, 0.006)))
            low = min(op, close) * (1 - abs(rng.gauss(0.009, 0.005)))
            volume = 1_000_000 * (1.8 if ret > 0.035 else 1.0) * (1 + rng.random())
            rows.append([start + timedelta(days=i), symbol, op, high, low, close, volume]); p = close
    target = Path(path); target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["timestamp", "symbol", "open", "high", "low", "close", "volume"]); writer.writerows(rows)

