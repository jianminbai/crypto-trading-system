from datetime import timedelta
from typing import Dict, List
from ..models import Bar


def validate_bars(data: Dict[str, List[Bar]]) -> Dict:
    errors = []
    summary = {}
    benchmark_dates = [b.timestamp for b in data.get("BTC", [])]
    if not benchmark_dates:
        errors.append("BTC history is missing")
    for symbol, bars in sorted(data.items()):
        dates = [b.timestamp for b in bars]
        duplicates = len(dates) - len(set(dates))
        gaps = sum(1 for a, b in zip(dates, dates[1:]) if b - a != timedelta(days=1))
        aligned = dates == benchmark_dates
        if duplicates:
            errors.append(f"{symbol}: {duplicates} duplicate dates")
        if gaps:
            errors.append(f"{symbol}: {gaps} daily gaps")
        if benchmark_dates and not aligned:
            errors.append(f"{symbol}: calendar not aligned with BTC")
        summary[symbol] = {"bars": len(bars), "start": dates[0].isoformat() if dates else None,
                           "end": dates[-1].isoformat() if dates else None, "gaps": gaps,
                           "duplicates": duplicates, "btc_aligned": aligned}
    return {"valid": not errors, "errors": errors, "symbols": summary}

