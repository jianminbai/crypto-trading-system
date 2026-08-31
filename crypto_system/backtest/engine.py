from datetime import date
from typing import Dict, List, Optional
from ..execution.stops import initial_stop, trailing_stop
from ..indicators import atr, confirmed_swing_lows
from ..market.regime import btc_regimes
from ..models import BacktestResult, Bar, Position, Signal, Trade
from ..risk.portfolio import can_add_risk
from ..risk.position_size import position_size
from ..strategy.breakout import breakout_flags
from ..tokens.relative_strength import relative_strength
from ..tokens.universe import build_universe
from .metrics import calculate_metrics


class BacktestEngine:
    def __init__(self, config: Dict):
        self.c = config

    def run(self, data: Dict[str, List[Bar]], start: Optional[date] = None,
            end: Optional[date] = None, liquidity_by_date: Optional[Dict[date, Dict]] = None) -> BacktestResult:
        if "BTC" not in data:
            raise ValueError("BTC benchmark is required")
        dates = sorted(set(b.timestamp for bars in data.values() for b in bars))
        dates = [d for d in dates if (start is None or d >= start) and (end is None or d <= end)]
        indexed = {s: {b.timestamp: b for b in bars} for s, bars in data.items()}
        full_dates = [b.timestamp for b in data["BTC"]]
        btc_close = [b.close for b in data["BTC"]]
        regimes = dict(zip(full_dates, btc_regimes(data["BTC"], self.c["regime_ema_fast"], self.c["regime_ema_slow"])))
        prepared = {}
        universe = build_universe(data, self.c.get("minimum_history_days", 1),
                                  self.c.get("minimum_average_quote_volume", 0.0),
                                  self.c.get("universe_volume_window", 30),
                                  self.c.get("excluded_symbols", []))
        for symbol, bars in data.items():
            if symbol != "BTC" and not universe[symbol].eligible:
                continue
            if [b.timestamp for b in bars] != full_dates:
                continue  # V1 requires aligned daily histories; provider should align explicitly.
            prepared[symbol] = {
                "bars": bars, "index": {b.timestamp: i for i, b in enumerate(bars)},
                "atr": atr(bars, self.c["atr_period"]),
                "swings": confirmed_swing_lows(bars, self.c["pivot_window"]),
                "breakout": breakout_flags(bars, self.c["breakout_days"], self.c["volume_window"], self.c["volume_multiple"]),
                "rs": relative_strength([b.close for b in bars], btc_close, self.c["relative_strength_window"])
            }
        cash = self.c["initial_equity"]
        positions: Dict[str, Position] = {}
        pending: List[Signal] = []
        trades: List[Trade] = []
        curve = []
        liquidity_filter_enabled = self.c.get("enable_liquidity_filter", False)
        liquidity_blocked_days = 0
        liquidity_candidate_days = 0
        liquidity_covered_days = 0
        for day in dates:
            # Signals from t-1 execute at t open.
            for signal in list(pending):
                bar = indexed.get(signal.symbol, {}).get(day)
                if bar is None:
                    continue
                pending.remove(signal)
                if signal.symbol in positions:
                    continue
                entry = bar.open * (1 + self.c["slippage_rate"])
                stop = signal.stop
                if stop >= entry:
                    continue
                stop_pct = (entry - stop) / entry
                if stop_pct > self.c["max_stop_pct"] or entry - stop < self.c["min_stop_atr"] * signal.atr:
                    continue
                equity_now = cash + sum(p.quantity * indexed[s][day].close for s, p in positions.items() if day in indexed[s])
                sized = position_size(equity_now, self.c["risk_per_trade"], bar.open, stop,
                                      self.c["fee_rate"], self.c["slippage_rate"])
                affordable_quantity = max(0.0, cash / (entry * (1 + self.c["fee_rate"])))
                quantity = min(sized.quantity, affordable_quantity)
                actual_risk = quantity * sized.effective_loss_per_unit
                open_risk = sum(p.risk_amount for p in positions.values())
                if quantity <= 0 or not can_add_risk(equity_now, open_risk, actual_risk, self.c["maximum_open_risk"]):
                    continue
                notional = quantity * entry
                fee = notional * self.c["fee_rate"]
                risk_unit = entry - stop
                cash -= notional + fee
                positions[signal.symbol] = Position(signal.symbol, day, entry, quantity, quantity,
                    stop, stop, signal.atr, actual_risk, entry + self.c["tp1_r"] * risk_unit,
                    entry + self.c["tp2_r"] * risk_unit, fees=fee, highest=entry, entry_reason=signal.reason)
            # Manage exits pessimistically: stop before targets when both occur in one bar.
            for symbol, pos in list(positions.items()):
                bar = indexed[symbol].get(day)
                if bar is None:
                    continue
                pos.highest = max(pos.highest, bar.high)
                pos.mae = min(pos.mae, (bar.low - pos.entry) / (pos.entry - pos.initial_stop))
                pos.mfe = max(pos.mfe, (bar.high - pos.entry) / (pos.entry - pos.initial_stop))
                exit_price, exit_reason = None, ""
                if bar.low <= pos.stop:
                    exit_price, exit_reason = pos.stop * (1 - self.c["slippage_rate"]), "STOP"
                else:
                    for target, fraction, done_name in ((pos.tp1, self.c["tp1_fraction"], "tp1_done"),
                                                        (pos.tp2, self.c["tp2_fraction"], "tp2_done")):
                        if not getattr(pos, done_name) and bar.high >= target:
                            qty = min(pos.initial_quantity * fraction, pos.quantity)
                            fill = target * (1 - self.c["slippage_rate"])
                            fee = qty * fill * self.c["fee_rate"]
                            cash += qty * fill - fee
                            pos.realized_pnl += qty * (fill - pos.entry)
                            pos.fees += fee
                            pos.quantity -= qty
                            setattr(pos, done_name, True)
                            if done_name == "tp1_done" and self.c["breakeven_mode"] == "immediate":
                                pos.stop = max(pos.stop, pos.entry * (1 + 2 * self.c["fee_rate"]))
                    i = prepared[symbol]["index"][day]
                    av = prepared[symbol]["atr"][i]
                    swing = prepared[symbol]["swings"][i]
                    if pos.tp1_done and av:
                        pos.stop = trailing_stop(pos.stop, pos.highest, av, swing,
                                                 self.c["trailing_atr_multiplier"], self.c["atr_buffer"])
                if exit_price is not None:
                    qty = pos.quantity
                    fee = qty * exit_price * self.c["fee_rate"]
                    cash += qty * exit_price - fee
                    total_fees = pos.fees + fee
                    pnl = pos.realized_pnl + qty * (exit_price - pos.entry) - total_fees
                    trades.append(Trade(symbol, pos.entry_date, day, pos.entry, exit_price, pnl,
                                        pnl / pos.risk_amount, total_fees, (day - pos.entry_date).days,
                                        pos.mae, pos.mfe, exit_reason))
                    del positions[symbol]
            gross = sum(p.quantity * indexed[s][day].close for s, p in positions.items() if day in indexed[s])
            marked = cash + gross
            curve.append({"date": day.isoformat(), "ordinal": float(day.toordinal()), "equity": marked,
                          "cash": cash, "gross_exposure": gross})
            # Generate at close for next available bar. BTC is benchmark only.
            if not self.c.get("enable_market_regime", True) or regimes.get(day) != "RISK_OFF":
                liquidity_allowed = True
                if liquidity_filter_enabled:
                    liquidity_candidate_days += 1
                    state = (liquidity_by_date or {}).get(day)
                    if state is not None:
                        liquidity_covered_days += 1
                    liquidity_allowed = bool(
                        state
                        and state["age_days"] <= self.c.get("liquidity_max_age_days", 7)
                        and state["score"] >= self.c.get("liquidity_min_score", 50.0)
                        and state["leverage_risk"] not in self.c.get("liquidity_blocked_leverage_risks", ["EXTREME"])
                    )
                    if not liquidity_allowed:
                        liquidity_blocked_days += 1
                if not liquidity_allowed:
                    continue
                for symbol, state in prepared.items():
                    if symbol == "BTC" or symbol in positions or any(x.symbol == symbol for x in pending):
                        continue
                    i = state["index"].get(day)
                    if i is None or not state["breakout"][i] or state["atr"][i] is None:
                        continue
                    rs = state["rs"][i]
                    if rs is None or (self.c.get("enable_relative_strength", True)
                                      and rs < self.c["relative_strength_min"]):
                        continue
                    bar = state["bars"][i]
                    stop = initial_stop(bar.close, state["atr"][i], state["swings"][i],
                                        self.c["atr_multiplier"], self.c["atr_buffer"])
                    pending.append(Signal(day, symbol, "LONG", bar.close, stop, state["atr"][i],
                                          regimes.get(day, "UNKNOWN"), rs,
                                          "breakout+volume, BTC regime allowed, RS>{:.2%}".format(self.c["relative_strength_min"])))
        # Close remaining positions at final close.
        if dates:
            day = dates[-1]
            for symbol, pos in list(positions.items()):
                price = indexed[symbol][day].close * (1 - self.c["slippage_rate"])
                fee = pos.quantity * price * self.c["fee_rate"]
                total_fees = pos.fees + fee
                pnl = pos.realized_pnl + pos.quantity * (price - pos.entry) - total_fees
                trades.append(Trade(symbol, pos.entry_date, day, pos.entry, price, pnl,
                                    pnl / pos.risk_amount, total_fees, (day-pos.entry_date).days,
                                    pos.mae, pos.mfe, "END_OF_TEST"))
                cash += pos.quantity * price - fee
                del positions[symbol]
            curve[-1]["equity"] = cash
            curve[-1]["cash"] = cash
            curve[-1]["gross_exposure"] = 0.0
        result = BacktestResult(curve, trades)
        result.metrics = calculate_metrics(curve, trades, self.c["initial_equity"])
        result.metrics["turnover"] = (result.metrics["fees_paid"] / self.c["fee_rate"] / self.c["initial_equity"]
                                      if self.c["fee_rate"] else 0.0)
        result.metrics["liquidity_filter_enabled"] = liquidity_filter_enabled
        result.metrics["liquidity_candidate_days"] = liquidity_candidate_days
        result.metrics["liquidity_covered_days"] = liquidity_covered_days
        result.metrics["liquidity_blocked_days"] = liquidity_blocked_days
        result.metrics["liquidity_coverage"] = (liquidity_covered_days / liquidity_candidate_days
                                                if liquidity_candidate_days else 0.0)
        return result
