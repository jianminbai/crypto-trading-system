# Phase 1 Baseline Report

## Status

The Phase 1 price-only control group is operational. It uses trend,
relative strength, breakout/volume confirmation, fixed-R sizing, partial profits
and causal trailing stops. It contains no on-chain, capital-flow or sector-flow data.

## Strategy hypothesis

Liquid tokens that outperform BTC and close above a prior N-day high on expanded
volume may exhibit positive-skew trend persistence when BTC is not in `RISK_OFF`.
Losses are bounded near 1R; winners retain a 50% runner after 1R/2R partial exits.

## Test data

The research baseline uses Binance public spot daily OHLCV from 2021-01-01 through
2026-01-01: BTC, ETH, SOL, BNB, XRP, ADA, DOGE, DOT, LINK, LTC, BCH, AVAX and UNI.
Every series has 1,827 aligned observations. Fee and slippage are each 0.05%.

This fixed list is selected from currently surviving liquid assets. It therefore
has survivorship bias and is an **intermediate baseline**, not final evidence. A
point-in-time universe including delisted tokens remains required.

## Frozen baseline results

| Metric | Result |
|---|---:|
| Trades | 51 |
| Win rate | 45.10% |
| Average win | 1.626R |
| Average loss | -0.873R |
| Average R / Expectancy | +0.254R |
| Profit factor | 1.506 |
| Total return | 6.43% |
| CAGR | 1.25% |
| Maximum drawdown | -6.37% |
| Sharpe | 0.346 |
| Calmar | 0.197 |
| Maximum consecutive losses | 8 |
| Exposure time | 30.60% |
| Fees paid | 308.15 USDT |

The baseline clears the provisional expectancy and profit-factor targets, but CAGR,
Sharpe and trade count are weak. No parameter was optimized after observing these
results. The correct conclusion is “promising control group, insufficient evidence,”
not “validated profitable strategy.”

## Ablation 1: BTC regime

`Base + BTC Regime` rejects new entries while BTC is below EMA50 with EMA20 below
EMA50. It was evaluated without changing any other parameter.

| Metric | Base | + BTC Regime | Delta |
|---|---:|---:|---:|
| CAGR | 1.254% | 1.227% | -0.027 pp |
| Maximum drawdown | -6.367% | -6.367% | ~0 pp |
| Expectancy | 0.254R | 0.264R | +0.010R |
| Profit factor | 1.506 | 1.519 | +0.013 |
| Sharpe | 0.346 | 0.344 | -0.002 |
| Trades | 51 | 48 | -3 |

The BTC regime filter slightly improves trade quality but does not improve portfolio
return, drawdown or Sharpe in this sample. It therefore has **no demonstrated Alpha
yet** and should remain an experimental filter pending walk-forward validation.

## Reproducible run

```bash
python -m unittest discover -s tests -v
python -m crypto_system generate-demo-data
python -m crypto_system validate-data --data data/binance_daily.csv
python -m crypto_system backtest --data data/binance_daily.csv \
  --start 2021-01-01 --end 2026-01-01 --report-dir reports/real_baseline
```

Machine-readable results are in `reports/real_baseline/metrics.json`; trades,
equity, drawdown, monthly returns and annual returns are exported as CSV.

## Required next experiment

1. Freeze the current baseline configuration.
2. Load point-in-time exchange OHLCV including delisted assets and listing dates.
3. Run the same test without tuning and record trade count, Win Rate, Average R,
   Expectancy, Profit Factor, CAGR, MaxDD, Sharpe, Calmar and loss streaks.
4. Add one factor at a time: BTC regime ablation, stablecoin, ETF, chain and sector.
5. Record delta metrics and reject factors without out-of-sample improvement.

Monte Carlo, parameter plateaus, walk-forward and full ablation remain Phase 4 work.
