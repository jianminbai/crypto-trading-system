import unittest
from datetime import date, timedelta
from crypto_system.execution.stops import initial_stop, trailing_stop
from crypto_system.indicators import confirmed_swing_lows
from crypto_system.models import Bar
from crypto_system.risk.portfolio import can_add_risk
from crypto_system.risk.position_size import position_size
from crypto_system.strategy.breakout import breakout_flags
from crypto_system.backtest.engine import BacktestEngine
from crypto_system.data.validation import validate_bars
from crypto_system.backtest.monte_carlo import simulate_trade_r


def bar(i, close, high=None, low=None, volume=100):
    high = high if high is not None else close + 1
    low = low if low is not None else close - 1
    return Bar(date(2024, 1, 1) + timedelta(days=i), "X", close, high, low, close, volume)


class PhaseOneTests(unittest.TestCase):
    def test_position_size_caps_effective_risk_including_costs(self):
        sized = position_size(100_000, .005, 100, 95, .0005, .0005)
        self.assertAlmostEqual(sized.quantity * sized.effective_loss_per_unit, 500)
        self.assertLess(sized.notional, 10_000)
        with self.assertRaises(ValueError):
            position_size(100_000, .02, 100, 95, 0, 0)

    def test_breakout_excludes_current_bar(self):
        bars = [bar(i, 100 + i, volume=100) for i in range(5)] + [bar(5, 110, high=111, low=109, volume=250)]
        flags = breakout_flags(bars, 5, 5, 1.2)
        self.assertTrue(flags[5])

    def test_swing_is_not_visible_until_confirmed(self):
        bars = [bar(i, 10, high=11, low=x) for i, x in enumerate([8, 7, 5, 7, 8, 9])]
        swings = confirmed_swing_lows(bars, 2)
        self.assertIsNone(swings[3])
        self.assertEqual(swings[4], 5)

    def test_stop_and_trailing_never_loosen(self):
        self.assertEqual(initial_stop(100, 2, 96, 2, .5), 96)
        self.assertGreaterEqual(trailing_stop(95, 110, 2, 103, 2.5, .5), 95)
        self.assertEqual(trailing_stop(105, 110, 2, 100, 2.5, .5), 105)

    def test_portfolio_risk(self):
        self.assertTrue(can_add_risk(100_000, 2500, 500, .03))
        self.assertFalse(can_add_risk(100_000, 2600, 500, .03))

    def test_signal_fills_on_next_bar_not_signal_bar(self):
        cfg = {
            "initial_equity": 10000, "risk_per_trade": .005, "maximum_open_risk": .03,
            "fee_rate": 0.0, "slippage_rate": 0.0, "breakout_days": 2,
            "volume_window": 2, "volume_multiple": 1.1, "atr_period": 2,
            "atr_multiplier": 2.0, "atr_buffer": .5, "pivot_window": 1,
            "max_stop_pct": .50, "min_stop_atr": .1, "relative_strength_window": 2,
            "relative_strength_min": -1, "tp1_r": 1, "tp1_fraction": .25,
            "tp2_r": 2, "tp2_fraction": .25, "trailing_atr_multiplier": 2.5,
            "breakeven_mode": "structure", "regime_ema_fast": 2, "regime_ema_slow": 3
        }
        btc = [Bar(date(2024,1,1)+timedelta(days=i), "BTC", 100+i, 102+i, 99+i, 101+i, 100) for i in range(7)]
        closes = [10, 10.2, 10.4, 12, 12.2, 12.4, 12.5]
        alt = [Bar(date(2024,1,1)+timedelta(days=i), "ALT", c, c+.2, c-.2, c, 300 if i == 3 else 100) for i,c in enumerate(closes)]
        result = BacktestEngine(cfg).run({"BTC": btc, "ALT": alt})
        self.assertEqual(result.trades[0].entry_date, date(2024, 1, 5))

        cfg["enable_liquidity_filter"] = True
        cfg["liquidity_min_score"] = 50
        cfg["liquidity_max_age_days"] = 1
        allowed = {b.timestamp: {"score": 60, "leverage_risk": "NORMAL", "age_days": 0} for b in btc}
        filtered = {b.timestamp: {"score": 40, "leverage_risk": "NORMAL", "age_days": 0} for b in btc}
        self.assertEqual(len(BacktestEngine(cfg).run({"BTC": btc, "ALT": alt}, liquidity_by_date=allowed).trades), 1)
        blocked = BacktestEngine(cfg).run({"BTC": btc, "ALT": alt}, liquidity_by_date=filtered)
        self.assertEqual(len(blocked.trades), 0)
        self.assertGreater(blocked.metrics["liquidity_blocked_days"], 0)

    def test_liquidity_filter_rejects_stale_and_missing_observations(self):
        cfg = {
            "initial_equity": 10000, "risk_per_trade": .005, "maximum_open_risk": .03,
            "fee_rate": 0.0, "slippage_rate": 0.0, "breakout_days": 2,
            "volume_window": 2, "volume_multiple": 1.1, "atr_period": 2,
            "atr_multiplier": 2.0, "atr_buffer": .5, "pivot_window": 1,
            "max_stop_pct": .50, "min_stop_atr": .1, "relative_strength_window": 2,
            "relative_strength_min": -1, "tp1_r": 1, "tp1_fraction": .25,
            "tp2_r": 2, "tp2_fraction": .25, "trailing_atr_multiplier": 2.5,
            "breakeven_mode": "structure", "regime_ema_fast": 2, "regime_ema_slow": 3,
            "enable_liquidity_filter": True, "liquidity_min_score": 50,
            "liquidity_max_age_days": 1
        }
        btc = [Bar(date(2024,1,1)+timedelta(days=i), "BTC", 100+i, 102+i, 99+i, 101+i, 100) for i in range(7)]
        alt = [Bar(date(2024,1,1)+timedelta(days=i), "ALT", c, c+.2, c-.2, c, 300 if i == 3 else 100)
               for i,c in enumerate([10, 10.2, 10.4, 12, 12.2, 12.4, 12.5])]
        stale = {b.timestamp: {"score": 80, "leverage_risk": "NORMAL", "age_days": 2} for b in btc}
        self.assertFalse(BacktestEngine(cfg).run({"BTC": btc, "ALT": alt}, liquidity_by_date=stale).trades)
        self.assertFalse(BacktestEngine(cfg).run({"BTC": btc, "ALT": alt}).trades)

    def test_trade_pnl_includes_entry_and_exit_fees(self):
        sized = position_size(100_000, .005, 100, 95, .001, 0)
        expected = sized.quantity * ((100 - 95) + 100*.001 + 95*.001)
        self.assertAlmostEqual(expected, 500)

    def test_data_validation_detects_gap(self):
        bars = [bar(0, 10), bar(2, 11)]
        result = validate_bars({"BTC": bars})
        self.assertFalse(result["valid"])
        self.assertEqual(result["symbols"]["BTC"]["gaps"], 1)

    def test_monte_carlo_is_deterministic_and_risk_sensitive(self):
        trades = [-1, -1, -1, 2, 3, 4]
        low = simulate_trade_r(trades, .0025, simulations=200, seed=9)
        high = simulate_trade_r(trades, .01, simulations=200, seed=9)
        self.assertEqual(low, simulate_trade_r(trades, .0025, simulations=200, seed=9))
        self.assertLess(high["expected_max_drawdown"], low["expected_max_drawdown"])


if __name__ == "__main__":
    unittest.main()
