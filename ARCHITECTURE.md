# Crypto Capital Flow + Trend Following System V1

## Scope and research contract

V1 is the price-only control group. It implements point-in-time OHLCV ingestion,
a BTC regime filter, cross-asset relative strength, breakout entries, structural
or ATR stops, fixed-R sizing, partial exits, trailing stops and an event-driven
backtest. On-chain, ETF, stablecoin, chain and sector factors are intentionally
excluded from the baseline so later ablations can measure their marginal value.

The engine is a research tool, not a claim of profitability. Every signal records
the data and rule values that caused it.

## Data model

- `Bar`: immutable timestamped OHLCV observation.
- `AssetMetadata`: point-in-time listing/delisting and liquidity metadata. Universe
  membership is evaluated on each date, never from today's survivors.
- `Signal`: generated after bar close and eligible for fill on the next bar only.
- `Position`: entry, initial risk, remaining quantity, stop, targets, MAE/MFE and fees.
- `Trade`: immutable closed-trade ledger expressed in currency and R multiples.
- `EquityPoint`: cash plus marked-to-market positions for each timestamp.

CSV V1 columns are `timestamp,symbol,open,high,low,close,volume`. Timestamps are
UTC dates. Provider interfaces isolate business logic from CSV, exchange or API sources.

## Modules and interfaces

```text
MarketDataProvider -> bars_by_symbol()
        |
        +-> indicators -> regime / relative strength / breakout
                                  |
                                  v
                           pending Signal (t)
                                  |
                         next-bar execution (t+1)
                                  |
             stop / partial take-profit / trailing-stop state machine
                                  |
                    trades + equity -> metrics/reporting
```

- `data.providers`: replaceable data sources; CSV and deterministic demo provider.
- `market.regime`: configurable BTC trend state using only information available at t.
- `tokens.relative_strength`: token/BTC return strength over trailing windows.
- `strategy.breakout`: N-day high and volume confirmation; the current bar is excluded
  from the prior-high calculation.
- `execution`: ATR and confirmed-past swing stops, R targets and causal trailing stops.
- `risk`: fee/slippage-aware position size and portfolio open-risk limits.
- `backtest`: bar-by-bar event loop and performance accounting.

## No-look-ahead rules

Signals computed at close t fill at open t+1 with configured slippage. Rolling
breakout highs exclude t. ATR/EMA use data through t. A swing low at index i is
usable only after `pivot_window` later bars have closed; no future-confirmed pivot
is retroactively exposed. If stop and target are both crossed inside one daily bar,
the pessimistic stop-first ordering is used.

## Risk model

`risk_budget = equity * risk_per_trade`. Position quantity solves for worst-case
loss at the stop including estimated entry/exit fees and slippage. Leverage changes
margin required, never notional risk. Trades are rejected when the structural stop
is wider than configured maximum or tighter than the configured ATR floor.

Portfolio admission requires total initial open risk and per-symbol risk to remain
below configured caps. Future phases add sector/chain correlated-risk buckets.

## Backtest accounting

Cash is debited/credited by realized PnL and all fees. Open positions are marked to
close. Funding is an explicit cost field (zero for spot baseline). Metrics derive
from the equity curve and closed-trade ledger. Results include CSV/JSON and a
self-contained HTML report.

## Phase boundaries

1. Price baseline (implemented): BTC regime, RS, breakout, risk/exits, reports.
2. Liquidity and capital flow: stablecoins, ETF, chain, sector providers and ablations.
3. Fundamentals and supply risk.
4. Walk-forward and parameter plateau (ordering-only Monte Carlo is implemented;
   richer correlation and regime stress tests remain outstanding).
5. Paper execution and real-time scanning.
