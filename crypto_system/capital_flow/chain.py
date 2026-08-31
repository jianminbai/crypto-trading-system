from typing import Dict, List
from ..market.liquidity import _growth_score


METRICS = ("stablecoin_growth", "tvl_growth", "dex_volume_growth", "perp_volume_growth",
           "bridge_netflow", "users_growth", "fees_revenue_growth")


def chain_momentum_score(row: Dict, config: Dict) -> Dict:
    weights = config["chain_weights"]
    components = {}
    for metric in METRICS:
        scale = config["netflow_score_scale_pct"] if metric == "bridge_netflow" else config["growth_score_scale_pct"]
        components[metric] = _growth_score(float(row.get(metric, 0.0)), scale)
    score = sum(components[k] * weights[k] for k in weights) / sum(weights.values())
    return {"chain": row["chain"], "window": row["window"], "score": round(score, 2), "components": components}


def rank_chains(rows: List[Dict], config: Dict, window: str = "7d") -> List[Dict]:
    ranked = [chain_momentum_score(row, config) for row in rows if row["window"] == window]
    ranked.sort(key=lambda item: item["score"], reverse=True)
    for rank, item in enumerate(ranked, 1): item["rank"] = rank
    return ranked

