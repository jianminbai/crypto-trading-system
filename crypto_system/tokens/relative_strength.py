from typing import List, Optional, Sequence


def relative_strength(asset: Sequence[float], benchmark: Sequence[float], window: int) -> List[Optional[float]]:
    if len(asset) != len(benchmark):
        raise ValueError("aligned series required")
    result: List[Optional[float]] = [None] * len(asset)
    for i in range(window, len(asset)):
        asset_return = asset[i] / asset[i - window] - 1
        benchmark_return = benchmark[i] / benchmark[i - window] - 1
        result[i] = (1 + asset_return) / (1 + benchmark_return) - 1
    return result

