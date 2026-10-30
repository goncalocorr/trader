import unittest

from agente.risk import check


def account(**kw):
    a = {"equity": 100.0, "cash": 100.0, "peak": 100.0, "day_start": 100.0, "positions": {}}
    a.update(kw)
    return a


def proposal(**kw):
    p = {"symbol": "BTCUSDT", "entry": 100.0, "stop": 95.0, "target": 110.0, "ev_r": 0.04}
    p.update(kw)
    return p


class RiskGate(unittest.TestCase):
    def test_rejects_without_stop(self):
        self.assertFalse(check(account(), proposal(stop=None))["ok"])

    def test_rejects_stop_at_or_above_entry(self):
        self.assertFalse(check(account(), proposal(stop=100.0))["ok"])

    def test_rejects_target_at_or_below_entry(self):
        self.assertFalse(check(account(), proposal(target=100.0))["ok"])

    def test_rejects_non_positive_expectancy(self):
        self.assertFalse(check(account(), proposal(ev_r=0.0))["ok"])

    def test_rejects_after_daily_loss_limit(self):
        r = check(account(equity=95.0, cash=95.0, day_start=100.0), proposal())
        self.assertFalse(r["ok"])
        self.assertIn("diária", r["reason"])

    def test_rejects_after_max_drawdown(self):
        r = check(account(equity=75.0, cash=75.0, peak=100.0, day_start=75.0), proposal())
        self.assertFalse(r["ok"])
        self.assertIn("drawdown", r["reason"])

    def test_rejects_when_halted(self):
        self.assertFalse(check(account(halted=True), proposal())["ok"])

    def test_rejects_second_position_same_symbol(self):
        a = account(positions={"BTCUSDT": {"qty": 1}})
        self.assertFalse(check(a, proposal())["ok"])

    def test_sizes_half_kelly(self):
        # ev 0.04R, R 2 -> kelly 0.02 -> half 0.01 -> risk 1.0 on 100 equity, 5 per unit
        r = check(account(), proposal())
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["risk_frac"], 0.01)
        self.assertAlmostEqual(r["qty"], 0.2)

    def test_caps_risk_at_two_percent(self):
        r = check(account(), proposal(ev_r=1.0))
        self.assertAlmostEqual(r["risk_frac"], 0.02)
        self.assertAlmostEqual(r["qty"], 0.4)

    def test_caps_notional_at_cash(self):
        # tight stop -> qty 2.0 -> notional 200 > cash 50 -> qty ~0.5 after the cost buffer
        r = check(account(cash=50.0), proposal(stop=99.5, target=101.0, ev_r=1.0))
        self.assertTrue(r["ok"])
        self.assertLessEqual(r["qty"] * 100.0 * 1.0005 * 1.001, 50.0)
        self.assertGreater(r["qty"], 0.49)

    def test_total_open_risk_is_capped(self):
        # 5.5 of 100 already at risk, heat cap 6 -> only 0.5 more allowed
        a = account(positions={"ETHUSDT": {"qty": 1.1, "entry": 10.0, "stop": 5.0}})
        r = check(a, proposal(ev_r=1.0))
        self.assertTrue(r["ok"])
        self.assertAlmostEqual(r["risk_frac"], 0.005)

    def test_rejects_when_open_risk_at_cap(self):
        a = account(positions={"ETHUSDT": {"qty": 1.2, "entry": 10.0, "stop": 5.0}})
        r = check(a, proposal(ev_r=1.0))
        self.assertFalse(r["ok"])
        self.assertIn("risco total", r["reason"])

    def test_rejects_below_exchange_minimum(self):
        r = check(account(equity=25.0, cash=3.0, peak=25.0, day_start=25.0), proposal(ev_r=1.0))
        self.assertFalse(r["ok"])
        self.assertIn("mínimo", r["reason"])


if __name__ == "__main__":
    unittest.main()
