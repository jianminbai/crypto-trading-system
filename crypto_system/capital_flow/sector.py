from typing import Dict, List
from ..market.liquidity import _growth_score


METRICS = ("market_cap_growth", "volume_growth", "tvl_growth", "revenue_growth", "token_relative_strength")


def rank_sectors(rows: List[Dict], config: Dict, window: str = "7d") -> List[Dict]:
    weights = config["sector_weights"]
    output = []
    for row in rows:
        if row["window"] != window: continue
        components = {key: _growth_score(float(row.get(key, 0.0)), config["growth_score_scale_pct"]) for key in METRICS}
        score = sum(components[k] * weights[k] for k in weights) / sum(weights.values())
        output.append({"sector": row["sector"], "window": window, "score": round(score, 2), "components": components})
    output.sort(key=lambda item: item["score"], reverse=True)
    for rank, item in enumerate(output, 1): item["rank"] = rank
    return output

