# Crypto Capital Flow + Trend Following System V1

一个可重复、可解释、逐根 K 线运行的加密趋势跟踪研究系统。核心流程是先判断市场环境，再比较相对强度，最后只交易有成交量确认的突破；仓位始终由固定账户风险决定。

当前版本是 Phase 1 price-only control group。它刻意不使用链上、ETF、稳定币、Chain Flow 或 Sector Flow，便于后续逐因素消融，判断新增因子是否真的贡献 Alpha。

## Architecture

详见 [ARCHITECTURE.md](ARCHITECTURE.md)。业务逻辑依赖 `MarketDataProvider` 抽象；当前提供 CSV provider。信号在 t 日收盘生成，只允许在 t+1 开盘成交。Swing 只有在右侧窗口完成后才可见。

## Signal generation

- BTC EMA20/EMA50 产生 `RISK_OFF`、`BTC_ACCUMULATION`、`BTC_TREND`。
- Token 30 日收益除以 BTC 30 日收益得到相对强度。
- 收盘突破此前 N 日最高价，且成交量高于此前均量倍数，产生候选。
- `RISK_OFF` 禁止新开多仓。

## Risk management

默认单笔风险 0.5%，上限强制为 1%；组合初始开放风险上限 3%。止损优先采用已确认 swing low 加 ATR buffer，否则采用 2 ATR。仓位计算包括双边手续费和预估滑点。杠杆不会改变允许的风险预算。

默认在 1R、2R 各退出 25%，剩余 50% 使用结构 trailing，结构不可用时回退 ATR trailing。同一根日 K 同时触发止损与止盈时采用保守的止损优先顺序。

## Data sources

CSV schema: `timestamp,symbol,open,high,low,close,volume`。BTC 必须存在且各资产日历在 V1 中需对齐。`generate-demo-data` 仅生成确定性的合成数据，用于验证软件链路，不是策略收益证据。真实研究应接入带下架币和 point-in-time universe 的交易所数据。

## Run

```bash
python -m crypto_system generate-demo-data
python -m crypto_system backtest --start 2021-01-01 --end 2023-06-19
python -m unittest discover -s tests -v
```

下载并回测 Binance 公共现货日线：

```bash
python -m crypto_system download-binance --start 2021-01-01 --end 2026-01-01
python -m crypto_system backtest --data data/binance_daily.csv \
  --start 2021-01-01 --end 2026-01-01 --report-dir reports/real_baseline
python -m crypto_system monte-carlo --trades reports/real_baseline/trades.csv \
  --simulations 10000 --output reports/real_baseline/monte_carlo.json
python -m crypto_system liquidity-status --data data/liquidity_daily.csv \
  --as-of 2025-12-31
python -m crypto_system backtest --data data/binance_daily.csv \
  --config config/with_liquidity_filter.json \
  --liquidity-data data/liquidity_daily.csv \
  --liquidity-config config/capital_flow.json \
  --start 2021-01-01 --end 2026-01-01 \
  --report-dir reports/with_liquidity_filter
```

流动性 CSV schema：`timestamp,stablecoin_growth_30d_pct,btc_etf_flow_5d_usd,eth_etf_flow_5d_usd,total_market_trend_30d_pct,btc_trend_30d_pct,funding_rate,oi_growth_7d_pct`。查询严格选取 `as-of` 当日或之前的最近观测，避免未来数据泄漏。该命令只计算独立因子状态，尚不改变价格基线的入场规则。

`with_liquidity_filter.json` 是独立消融配置：评分低于 50、杠杆风险为 `EXTREME`、观测超过 7 天或缺失时禁止产生新信号，但不干预已有仓位的退出。报告记录覆盖天数和过滤天数；应与相同区间、相同价格配置的 control 报告比较。

输出位于 `reports/baseline/`：`metrics.json`、`equity.csv`、`trades.csv`、`report.html`。

## Configuration

所有 Phase 1 阈值位于 `config/default.json`，包括突破周期、成交量倍数、ATR、pivot window、风险、手续费、滑点、分批止盈与 trailing 模式。基线参数在看到结果前固定，不能为美化回测而修改。

## Metrics and research roadmap

当前输出 Total Return、CAGR、Max Drawdown、Sharpe、Sortino、Calmar、Profit Factor、Win Rate、Average R、Expectancy、持有期、交易数量和费用。后续阶段按顺序加入 stablecoin/ETF、chain flow、sector flow，并对每个增量记录 CAGR、MaxDD、Expectancy、Profit Factor、Sharpe 的变化。

Walk-forward、参数平台、Monte Carlo、资金流模块和真实 API provider 属于后续阶段，不能把合成数据 baseline 当作这些研究问题的答案。

## Known limitations

- 当前是 spot long-only 日线模型，不含 funding、做空和盘中路径。
- V1 只接受完全对齐的历史，尚未实现 point-in-time token universe 数据库。
- HTML 是最小可审计报告，图表、月度收益、MAE/MFE 分布将在报告阶段扩展。
- 合成数据只证明执行、会计与因果时序可以运行，不证明正期望。
