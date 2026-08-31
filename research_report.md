# Research Report — Current State

## Question

Can a simple price-only relative-strength breakout process produce positive skew
after realistic spot fees and slippage, and does a BTC regime filter improve it?

## Evidence

Data: Binance spot daily OHLCV, 13 current liquid survivors, 2021-01-01 through
2026-01-01. Costs: 0.05% fee plus 0.05% slippage per fill. Risk: 0.5% target per
trade, capped by spot cash and 3% total open initial risk.

| Experiment | Trades | Win rate | Avg R | PF | CAGR | MaxDD | Sharpe | Calmar |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Base: RS + breakout + risk | 51 | 45.10% | 0.254 | 1.506 | 1.254% | -6.367% | 0.346 | 0.197 |
| Base + BTC regime | 48 | 45.83% | 0.264 | 1.519 | 1.227% | -6.367% | 0.344 | 0.193 |
| Base without RS filter | 79 | 53.16% | 0.905 | 3.110 | 6.975% | -9.038% | 0.949 | 0.772 |

The base has positive sample expectancy and profit factor, with eight consecutive
losses at worst. BTC regime removes three trades and marginally improves per-trade
quality, but slightly reduces CAGR and Sharpe and leaves drawdown unchanged.

## Alpha attribution so far

No causal Alpha attribution is established. Contrary to the initial hypothesis,
requiring positive 30-day Token/BTC strength materially worsens this sample: it
removes 28 trades, lowers CAGR and Expectancy, and only reduces drawdown. This exact
RS filter should not be promoted to production. The BTC regime filter also does not
show portfolio-level improvement. Capital-flow factors have not yet been added, so
no claim about their predictive value is possible.

## Biases and limitations

- Current-survivor universe; delisted tokens are absent.
- One exchange, daily bars, spot long-only.
- Only 51 base trades; uncertainty is large.
- No walk-forward or Monte Carlo confidence interval yet.
- Daily OHLC cannot reveal intrabar path; stop-first ordering is pessimistic.

## Monte Carlo risk sizing

10,000 deterministic-seed reshuffles of the 51 base trade R-multiples produced:

| Risk/trade | Expected max DD | 95% max DD | 99% max DD | P(20% DD) | P(30% DD) |
|---:|---:|---:|---:|---:|---:|
| 0.25% | -1.77% | -2.72% | -3.21% | 0% | 0% |
| 0.50% | -3.52% | -5.38% | -6.32% | 0% | 0% |
| 1.00% | -6.94% | -10.51% | -12.29% | 0% | 0% |

This only models ordering risk; it assumes stationary trade outcomes and excludes
correlation shocks, gaps, liquidity degradation and model decay. With only 51 trades,
the zero ruin/tail probabilities are not reliable evidence of safety. The default
remains 0.5%, not 1%.

## Decision

Keep the base unchanged as the control group. Treat BTC regime as experimental.
The ordering-only Monte Carlo step is complete. The next experiment is to source and
freeze point-in-time stablecoin and ETF observations, then run the liquidity factor
as a separate ablation before chain/sector flow. The CSV reader and standalone score
command are implemented. The backtest now also supports a separately configured
liquidity admission filter and reports observation coverage and blocked days. No
factor result is claimed until the point-in-time dataset exists.
Do not tune RS thresholds on this same sample.

## Preliminary partial-liquidity ablation

A point-in-time file with 1,797 daily observations was built for 2021-01-31 through
2026-01-01 from DefiLlama stablecoin supply and the existing Binance BTC closes.
Only 40% of configured component weight is available; ETF, total-market and
derivatives inputs remain explicitly missing.

| Experiment | Trades | Avg R | PF | CAGR | MaxDD | Sharpe | Calmar |
|---|---:|---:|---:|---:|---:|---:|---:|
| Price control | 51 | 0.254 | 1.506 | 1.254% | -6.367% | 0.346 | 0.197 |
| Partial liquidity filter | 42 | 0.262 | 1.484 | 1.059% | -6.367% | 0.314 | 0.166 |

The partial filter blocked 513 of 1,827 candidate signal-generation days and had
98.36% date coverage. It marginally raised average R but reduced CAGR, profit factor,
Sharpe and Calmar without improving drawdown. This is not evidence for or against
the full liquidity hypothesis because most intended components are absent.
