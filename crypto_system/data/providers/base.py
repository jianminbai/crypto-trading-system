from abc import ABC, abstractmethod
from typing import Dict, List
from ...models import Bar


class MarketDataProvider(ABC):
    @abstractmethod
    def bars_by_symbol(self) -> Dict[str, List[Bar]]:
        raise NotImplementedError

