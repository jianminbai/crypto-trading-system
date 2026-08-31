import csv
from datetime import date
from pathlib import Path
from typing import Dict, List
from .base import MarketDataProvider
from ...models import Bar


class CSVMarketDataProvider(MarketDataProvider):
    def __init__(self, path: str):
        self.path = Path(path)

    def bars_by_symbol(self) -> Dict[str, List[Bar]]:
        result: Dict[str, List[Bar]] = {}
        with self.path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                bar = Bar(date.fromisoformat(row["timestamp"]), row["symbol"],
                          float(row["open"]), float(row["high"]), float(row["low"]),
                          float(row["close"]), float(row["volume"]))
                result.setdefault(bar.symbol, []).append(bar)
        for bars in result.values():
            bars.sort(key=lambda b: b.timestamp)
        return result

