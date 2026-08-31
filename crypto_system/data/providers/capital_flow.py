import csv
from bisect import bisect_right
from abc import ABC, abstractmethod
from datetime import date
from pathlib import Path
from typing import Dict, List

from ...market.liquidity import LiquidityInputs


class OnChainDataProvider(ABC):
    @abstractmethod
    def chain_metrics(self, as_of: date) -> List[Dict]:
        raise NotImplementedError


class ETFDataProvider(ABC):
    @abstractmethod
    def etf_flows(self, as_of: date) -> Dict[str, float]:
        raise NotImplementedError


class DerivativesDataProvider(ABC):
    @abstractmethod
    def derivatives_metrics(self, as_of: date) -> Dict[str, float]:
        raise NotImplementedError


class TokenDataProvider(ABC):
    @abstractmethod
    def token_metrics(self, as_of: date) -> List[Dict]:
        raise NotImplementedError


class CSVLiquidityDataProvider:
    """Point-in-time reader for precomputed, daily market-liquidity features.

    A query only returns the most recent observation at or before ``as_of``. This
    makes the no-look-ahead boundary explicit when the provider is used by an
    historical scanner or ablation.
    """

    FIELDS = (
        "stablecoin_growth_30d_pct", "btc_etf_flow_5d_usd",
        "eth_etf_flow_5d_usd", "total_market_trend_30d_pct",
        "btc_trend_30d_pct", "funding_rate", "oi_growth_7d_pct",
    )

    def __init__(self, path: str):
        self.path = Path(path)
        self._rows = self._read()
        self._dates = [item[0] for item in self._rows]

    def _read(self):
        rows = []
        seen = set()
        with self.path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            required = {"timestamp", *self.FIELDS}
            missing = required.difference(reader.fieldnames or ())
            if missing:
                raise ValueError("missing liquidity columns: " + ", ".join(sorted(missing)))
            for raw in reader:
                timestamp = date.fromisoformat(raw["timestamp"])
                if timestamp in seen:
                    raise ValueError(f"duplicate liquidity timestamp: {timestamp}")
                seen.add(timestamp)
                rows.append((timestamp, LiquidityInputs(**{
                    key: float(raw[key]) if raw[key].strip() else None for key in self.FIELDS
                })))
        rows.sort(key=lambda item: item[0])
        if not rows:
            raise ValueError("liquidity data is empty")
        return rows

    def liquidity_inputs(self, as_of: date) -> LiquidityInputs:
        index = bisect_right(self._dates, as_of) - 1
        if index < 0:
            raise ValueError(f"no liquidity observation available at or before {as_of}")
        return self._rows[index][1]

    def observation_date(self, as_of: date) -> date:
        index = bisect_right(self._dates, as_of) - 1
        if index < 0:
            raise ValueError(f"no liquidity observation available at or before {as_of}")
        return self._rows[index][0]
