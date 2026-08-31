import argparse
import csv
import json
from datetime import date
from .backtest.engine import BacktestEngine
from .config import load_config
from .data.providers.csv_provider import CSVMarketDataProvider
from .demo import generate
from .data.export import write_bars
from .data.providers.binance import BinanceMarketDataProvider
from .data.validation import validate_bars
from .reporting.report import write_report
from .scanner import market_status, scan
from .backtest.monte_carlo import simulate_trade_r
from .data.providers.capital_flow import CSVLiquidityDataProvider
from .market.liquidity import liquidity_score
from .data.build_liquidity import build as build_liquidity


def main(argv=None):
    parser = argparse.ArgumentParser(prog="crypto-system")
    sub = parser.add_subparsers(dest="command", required=True)
    demo = sub.add_parser("generate-demo-data"); demo.add_argument("--output", default="data/demo.csv")
    download = sub.add_parser("download-binance")
    download.add_argument("--universe", default="config/baseline_universe.json")
    download.add_argument("--start", required=True); download.add_argument("--end", required=True)
    download.add_argument("--output", default="data/binance_daily.csv")
    backtest = sub.add_parser("backtest")
    backtest.add_argument("--data", default="data/demo.csv"); backtest.add_argument("--config", default="config/default.json")
    backtest.add_argument("--start"); backtest.add_argument("--end"); backtest.add_argument("--report-dir", default="reports/baseline")
    backtest.add_argument("--liquidity-data", help="Point-in-time liquidity feature CSV")
    backtest.add_argument("--liquidity-config", default="config/capital_flow.json")
    for command in ("market-status", "scan"):
        p = sub.add_parser(command); p.add_argument("--data", default="data/demo.csv"); p.add_argument("--config", default="config/default.json")
    validate = sub.add_parser("validate-data"); validate.add_argument("--data", required=True)
    monte = sub.add_parser("monte-carlo"); monte.add_argument("--trades", required=True)
    monte.add_argument("--simulations", type=int, default=10000); monte.add_argument("--output")
    liquidity = sub.add_parser("liquidity-status")
    liquidity.add_argument("--data", required=True, help="Point-in-time liquidity feature CSV")
    liquidity.add_argument("--config", default="config/capital_flow.json")
    liquidity.add_argument("--as-of", help="Use latest observation on or before YYYY-MM-DD")
    build_flow = sub.add_parser("build-liquidity-data")
    build_flow.add_argument("--stablecoins", default="data/raw_stablecoincharts_all.json")
    build_flow.add_argument("--market-data", default="data/binance_daily.csv")
    build_flow.add_argument("--output", default="data/liquidity_daily.csv")
    args = parser.parse_args(argv)
    if args.command == "generate-demo-data":
        generate(args.output); print(args.output); return 0
    if args.command == "download-binance":
        with open(args.universe, encoding="utf-8") as handle:
            symbols = json.load(handle)
        provider = BinanceMarketDataProvider(symbols, date.fromisoformat(args.start), date.fromisoformat(args.end))
        bars = provider.bars_by_symbol(); write_bars(bars, args.output)
        print(json.dumps({symbol: len(values) for symbol, values in bars.items()}, indent=2)); return 0
    if args.command == "validate-data":
        validation = validate_bars(CSVMarketDataProvider(args.data).bars_by_symbol())
        print(json.dumps(validation, indent=2)); return 0 if validation["valid"] else 1
    if args.command == "monte-carlo":
        with open(args.trades, newline="", encoding="utf-8") as handle:
            values = [float(row["r_multiple"]) for row in csv.DictReader(handle)]
        results = [simulate_trade_r(values, risk, args.simulations) for risk in (0.0025, 0.005, 0.01)]
        payload = json.dumps(results, indent=2)
        if args.output:
            from pathlib import Path
            target = Path(args.output); target.parent.mkdir(parents=True, exist_ok=True); target.write_text(payload, encoding="utf-8")
        print(payload); return 0
    if args.command == "liquidity-status":
        provider = CSVLiquidityDataProvider(args.data)
        as_of = date.fromisoformat(args.as_of) if args.as_of else date.today()
        observed = provider.observation_date(as_of)
        result = liquidity_score(provider.liquidity_inputs(as_of), load_config(args.config))
        result["as_of"] = as_of.isoformat()
        result["observation_date"] = observed.isoformat()
        print(json.dumps(result, indent=2)); return 0
    if args.command == "build-liquidity-data":
        build_liquidity(args.stablecoins, args.market_data, args.output)
        print(args.output); return 0
    config = load_config(args.config); data = CSVMarketDataProvider(args.data).bars_by_symbol()
    if args.command == "market-status":
        print(json.dumps(market_status(data, config), indent=2)); return 0
    if args.command == "scan":
        print(json.dumps(scan(data, config), indent=2)); return 0
    liquidity_by_date = None
    if args.liquidity_data:
        provider = CSVLiquidityDataProvider(args.liquidity_data)
        flow_config = load_config(args.liquidity_config)
        liquidity_by_date = {}
        for day in (bar.timestamp for bar in data["BTC"]):
            try:
                observed = provider.observation_date(day)
                scored = liquidity_score(provider.liquidity_inputs(day), flow_config)
                scored["age_days"] = (day - observed).days
                scored["observation_date"] = observed.isoformat()
                liquidity_by_date[day] = scored
            except ValueError:
                pass
    if config.get("enable_liquidity_filter") and liquidity_by_date is None:
        parser.error("--liquidity-data is required when enable_liquidity_filter is true")
    result = BacktestEngine(config).run(data, date.fromisoformat(args.start) if args.start else None,
                                        date.fromisoformat(args.end) if args.end else None,
                                        liquidity_by_date=liquidity_by_date)
    write_report(result, args.report_dir); print(json.dumps(result.metrics, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
