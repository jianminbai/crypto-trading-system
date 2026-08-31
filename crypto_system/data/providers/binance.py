import json
import time
import urllib.parse
import urllib.request
from datetime import date, datetime, timezone
from typing import Dict, Iterable, List
from ...models import Bar


class BinanceMarketDataProvider:
    """Public spot kline adapter. Fetching is isolated from strategy code."""

    def __init__(self, symbols: Dict[str, str], start: date, end: date,
                 base_url: str = "https://data-api.binance.vision"):
        self.symbols = symbols
        self.start = start
        self.end = end
        self.base_url = base_url.rstrip("/")

    @staticmethod
    def _milliseconds(value: date) -> int:
        return int(datetime(value.year, value.month, value.day, tzinfo=timezone.utc).timestamp() * 1000)

    def _fetch_symbol(self, name: str, exchange_symbol: str) -> List[Bar]:
        start_ms = self._milliseconds(self.start)
        end_ms = self._milliseconds(self.end) + 86_400_000 - 1
        bars: List[Bar] = []
        while start_ms <= end_ms:
            query = urllib.parse.urlencode({"symbol": exchange_symbol, "interval": "1d", "limit": 1000,
                                            "startTime": start_ms, "endTime": end_ms})
            request = urllib.request.Request(f"{self.base_url}/api/v3/klines?{query}",
                                             headers={"User-Agent": "crypto-system-v1/0.1"})
            with urllib.request.urlopen(request, timeout=30) as response:
                payload = json.load(response)
            if not payload:
                break
            for row in payload:
                timestamp = datetime.fromtimestamp(row[0] / 1000, tz=timezone.utc).date()
                bars.append(Bar(timestamp, name, float(row[1]), float(row[2]), float(row[3]),
                                float(row[4]), float(row[5])))
            next_ms = int(payload[-1][0]) + 86_400_000
            if next_ms <= start_ms:
                raise RuntimeError("Binance pagination did not advance")
            start_ms = next_ms
            time.sleep(0.05)
        return bars

    def bars_by_symbol(self) -> Dict[str, List[Bar]]:
        return {name: self._fetch_symbol(name, exchange_symbol)
                for name, exchange_symbol in self.symbols.items()}

