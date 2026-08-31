import csv
from pathlib import Path
from typing import Dict, List
from ..models import Bar


def write_bars(data: Dict[str, List[Bar]], path: str) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["timestamp", "symbol", "open", "high", "low", "close", "volume"])
        for symbol in sorted(data):
            for bar in data[symbol]:
                writer.writerow([bar.timestamp.isoformat(), symbol, bar.open, bar.high, bar.low, bar.close, bar.volume])

