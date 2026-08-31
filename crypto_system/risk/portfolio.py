def can_add_risk(equity: float, open_risk: float, new_risk: float, max_open_fraction: float) -> bool:
    return open_risk + new_risk <= equity * max_open_fraction + 1e-9

