import unittest
import tempfile
from datetime import date
from pathlib import Path
from crypto_system.config import load_config
from crypto_system.market.liquidity import LiquidityInputs, liquidity_score
from crypto_system.capital_flow.chain import rank_chains
from crypto_system.capital_flow.sector import rank_sectors
from crypto_system.data.providers.capital_flow import CSVLiquidityDataProvider
from crypto_system.cli import main
from contextlib import redirect_stdout
from io import StringIO


class CapitalFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_config("config/capital_flow.json")

    def test_liquidity_score_and_extreme_funding(self):
        normal = liquidity_score(LiquidityInputs(3, 1e9, 2e8, 8, 7, .0001, 5), self.config)
        extreme = liquidity_score(LiquidityInputs(3, 1e9, 2e8, 8, 7, .002, 30), self.config)
        self.assertGreater(normal["score"], extreme["score"])
        self.assertEqual(extreme["leverage_risk"], "EXTREME")

    def test_chain_ranking_rewards_marginal_growth(self):
        rows = [dict(chain="ETH", window="7d", stablecoin_growth=2, tvl_growth=2, dex_volume_growth=2,
                     perp_volume_growth=2, bridge_netflow=1, users_growth=2, fees_revenue_growth=2),
                dict(chain="SOL", window="7d", stablecoin_growth=20, tvl_growth=20, dex_volume_growth=20,
                     perp_volume_growth=20, bridge_netflow=5, users_growth=20, fees_revenue_growth=20)]
        self.assertEqual(rank_chains(rows, self.config)[0]["chain"], "SOL")

    def test_sector_ranking(self):
        rows = [dict(sector="RWA", window="7d", market_cap_growth=20, volume_growth=15, tvl_growth=10,
                     revenue_growth=10, token_relative_strength=15),
                dict(sector="Gaming", window="7d", market_cap_growth=-5, volume_growth=-5, tvl_growth=0,
                     revenue_growth=0, token_relative_strength=-5)]
        self.assertEqual(rank_sectors(rows, self.config)[0]["sector"], "RWA")

    def test_liquidity_csv_is_point_in_time(self):
        header = "timestamp,stablecoin_growth_30d_pct,btc_etf_flow_5d_usd,eth_etf_flow_5d_usd,total_market_trend_30d_pct,btc_trend_30d_pct,funding_rate,oi_growth_7d_pct\n"
        rows = "2024-01-01,1,100,20,2,3,0.0001,4\n2024-01-03,9,900,80,8,7,0.0002,5\n"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "liquidity.csv"
            path.write_text(header + rows, encoding="utf-8")
            provider = CSVLiquidityDataProvider(str(path))
            values = provider.liquidity_inputs(date(2024, 1, 2))
            self.assertEqual(values.stablecoin_growth_30d_pct, 1)
            self.assertEqual(provider.observation_date(date(2024, 1, 2)), date(2024, 1, 1))
            with self.assertRaises(ValueError):
                provider.liquidity_inputs(date(2023, 12, 31))

    def test_liquidity_status_cli(self):
        header = "timestamp,stablecoin_growth_30d_pct,btc_etf_flow_5d_usd,eth_etf_flow_5d_usd,total_market_trend_30d_pct,btc_trend_30d_pct,funding_rate,oi_growth_7d_pct\n"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "liquidity.csv"
            path.write_text(header + "2024-01-01,1,100,20,2,3,0.0001,4\n", encoding="utf-8")
            output = StringIO()
            with redirect_stdout(output):
                self.assertEqual(main(["liquidity-status", "--data", str(path), "--as-of", "2024-01-02"]), 0)
            self.assertEqual(__import__("json").loads(output.getvalue())["observation_date"], "2024-01-01")
