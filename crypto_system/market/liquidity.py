from dataclasses import dataclass
from typing import Dict, Optional


def _clamp(value: float) -> float:
    return max(0.0, min(100.0, value))


def _growth_score(value: float, scale: float) -> float:
    return _clamp(50.0 + 50.0 * value / scale)


@dataclass(frozen=True)
class LiquidityInputs:
    stablecoin_growth_30d_pct: Optional[float]
    btc_etf_flow_5d_usd: Optional[float]
    eth_etf_flow_5d_usd: Optional[float]
    total_market_trend_30d_pct: Optional[float]
    btc_trend_30d_pct: Optional[float]
    funding_rate: Optional[float]
    oi_growth_7d_pct: Optional[float]


def liquidity_score(values: LiquidityInputs, config: Dict) -> Dict:
    scales, weights = config["liquidity_scales"], config["liquidity_weights"]
    if values.funding_rate is None or values.oi_growth_7d_pct is None:
        funding_score, leverage_risk = None, "UNKNOWN"
    elif abs(values.funding_rate) >= config["funding_extreme"]:
        funding_score, leverage_risk = 0.0, "EXTREME"
    elif values.funding_rate >= config["funding_high"] and values.oi_growth_7d_pct >= config["oi_growth_high_pct"]:
        funding_score, leverage_risk = 25.0, "HIGH"
    else:
        funding_score, leverage_risk = 75.0, "NORMAL"
    components = {
        "stablecoin_supply_growth": None if values.stablecoin_growth_30d_pct is None else _growth_score(values.stablecoin_growth_30d_pct, scales["stablecoin_growth_pct"]),
        "btc_etf_flow": None if values.btc_etf_flow_5d_usd is None else _growth_score(values.btc_etf_flow_5d_usd, scales["btc_etf_flow_usd"]),
        "eth_etf_flow": None if values.eth_etf_flow_5d_usd is None else _growth_score(values.eth_etf_flow_5d_usd, scales["eth_etf_flow_usd"]),
        "total_market_trend": None if values.total_market_trend_30d_pct is None else _growth_score(values.total_market_trend_30d_pct, scales["total_market_trend_pct"]),
        "btc_trend": None if values.btc_trend_30d_pct is None else _growth_score(values.btc_trend_30d_pct, scales["btc_trend_pct"]),
        "funding_oi_risk": funding_score
    }
    available = [key for key in weights if components[key] is not None]
    if not available:
        raise ValueError("liquidity observation has no usable components")
    score = sum(components[k] * weights[k] for k in available) / sum(weights[k] for k in available)
    status = "RISK_OFF" if score < 30 else "NEUTRAL" if score < 50 else "POSITIVE" if score < 70 else "STRONG" if score < 85 else "OVERHEATED"
    if leverage_risk == "EXTREME":
        status = "OVERHEATED" if score >= 50 else status
    return {"score": round(score, 2), "status": status, "leverage_risk": leverage_risk,
            "component_coverage": sum(weights[k] for k in available) / sum(weights.values()),
            "components": components, "inputs": values.__dict__}
