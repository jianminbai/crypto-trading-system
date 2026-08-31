import csv
import html
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from ..models import BacktestResult


def write_report(result: BacktestResult, directory: str) -> None:
    out = Path(directory)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "metrics.json").open("w", encoding="utf-8") as f:
        json.dump(result.metrics, f, indent=2, allow_nan=False)
    with (out / "equity.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["date", "ordinal", "equity", "cash", "gross_exposure"])
        writer.writeheader(); writer.writerows(result.equity)
    peak = 0.0
    with (out / "drawdown.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f); writer.writerow(["date", "drawdown"])
        for point in result.equity:
            peak = max(peak, point["equity"])
            writer.writerow([point["date"], point["equity"] / peak - 1 if peak else 0.0])
    period_ends = {"monthly": {}, "annual": {}}
    for point in result.equity:
        d = date.fromisoformat(point["date"])
        period_ends["monthly"][(d.year, d.month)] = point["equity"]
        period_ends["annual"][d.year] = point["equity"]
    for name, values in period_ends.items():
        previous = result.equity[0]["equity"]
        with (out / f"{name}_returns.csv").open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f); writer.writerow(["period", "return"])
            for period, ending in sorted(values.items()):
                label = f"{period[0]:04d}-{period[1]:02d}" if isinstance(period, tuple) else str(period)
                writer.writerow([label, ending / previous - 1]); previous = ending
    fields = list(result.trades[0].__dataclass_fields__) if result.trades else ["symbol"]
    with (out / "trades.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields); writer.writeheader()
        for trade in result.trades:
            row = trade.__dict__.copy(); row["entry_date"] = str(row["entry_date"]); row["exit_date"] = str(row["exit_date"])
            writer.writerow(row)
    rows = "".join(f"<tr><th>{html.escape(k)}</th><td>{v:.6g}</td></tr>" for k, v in result.metrics.items())
    points = result.equity
    if points:
        lo, hi = min(p["equity"] for p in points), max(p["equity"] for p in points)
        span = hi - lo or 1
        coords = " ".join(f"{i*800/max(1,len(points)-1):.1f},{200-(p['equity']-lo)*180/span:.1f}" for i,p in enumerate(points))
    else:
        coords = ""
    document = ("<!doctype html><meta charset='utf-8'><title>Baseline</title>"
                "<style>body{font:14px system-ui;max-width:900px;margin:2rem auto}table{border-collapse:collapse}th,td{padding:.35rem 1rem;border-bottom:1px solid #ddd;text-align:left}</style>"
                f"<h1>Phase 1 Baseline</h1><svg viewBox='0 0 800 210' role='img' aria-label='Equity curve'><polyline fill='none' stroke='#2563eb' stroke-width='2' points='{coords}'/></svg><table>{rows}</table>")
    (out / "report.html").write_text(document, encoding="utf-8")
