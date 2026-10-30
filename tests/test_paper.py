import unittest

from agente import paper
from agente.risk import MIN_NOTIONAL

DAY = 86_400_000


class Paper(unittest.TestCase):
    def test_buy_pays_slippage_and_fee(self):
        a = paper.new_account(100.0)
        paper.rebalance(a, {"A": 0.5}, {"A": 10.0}, t=0)
        self.assertAlmostEqual(a["positions"]["A"], 50.0 / (10.0 * (1 + paper.SLIP) * (1 + paper.FEE)))
        self.assertAlmostEqual(a["cash"], 50.0)

    def test_sell_to_zero_removes_position_and_pays_costs(self):
        a = paper.new_account(100.0)
        paper.rebalance(a, {"A": 0.5}, {"A": 10.0}, t=0)
        qty = a["positions"]["A"]
        paper.rebalance(a, {}, {"A": 10.0}, t=1)
        self.assertNotIn("A", a["positions"])
        self.assertAlmostEqual(a["cash"], 50.0 + qty * 10.0 * (1 - paper.SLIP) * (1 - paper.FEE))

    def test_tiny_rebalance_is_skipped(self):
        a = paper.new_account(100.0)
        paper.rebalance(a, {"A": 0.5}, {"A": 10.0}, t=0)
        fills = paper.rebalance(a, {"A": 0.5 + (MIN_NOTIONAL - 1) / 100}, {"A": 10.0}, t=1)
        self.assertEqual(fills, [])

    def test_order_below_minimum_is_not_opened(self):
        a = paper.new_account(100.0)
        paper.rebalance(a, {"A": 0.03}, {"A": 10.0}, t=0)
        self.assertNotIn("A", a["positions"])

    def test_full_exit_happens_even_below_minimum(self):
        a = paper.new_account(100.0)
        a["positions"]["A"] = 0.2  # 2 USDT of dust
        paper.rebalance(a, {}, {"A": 10.0}, t=1)
        self.assertNotIn("A", a["positions"])

    def test_buys_never_overdraw_cash(self):
        a = paper.new_account(100.0)
        paper.rebalance(a, {"A": 0.6, "B": 0.6}, {"A": 10.0, "B": 5.0}, t=0)
        self.assertGreaterEqual(a["cash"], -1e-9)

    def test_mark_tracks_equity_peak_and_new_day(self):
        a = paper.new_account(100.0)
        paper.rebalance(a, {"A": 0.5}, {"A": 10.0}, t=0)
        paper.mark(a, {"A": 20.0}, t=DAY)
        self.assertAlmostEqual(a["equity"], a["cash"] + a["positions"]["A"] * 20.0)
        self.assertEqual(a["peak"], a["equity"])
        self.assertEqual(a["day_start"], 100.0)  # the new day starts from yesterday's close

    def test_a_bad_day_is_measured_from_the_previous_close(self):
        a = paper.new_account(100.0)
        paper.rebalance(a, {"A": 0.5}, {"A": 10.0}, t=0)
        paper.mark(a, {"A": 10.0}, t=0)
        paper.mark(a, {"A": 8.0}, t=DAY)  # -20% on half the account in one day
        self.assertLess(a["equity"], a["day_start"] * 0.95)

    def test_mark_halts_on_max_drawdown(self):
        a = paper.new_account(100.0)
        paper.rebalance(a, {"A": 0.9}, {"A": 10.0}, t=0)
        paper.mark(a, {"A": 10.0}, t=0)
        paper.mark(a, {"A": 6.5}, t=1)
        self.assertTrue(a["halted"])


if __name__ == "__main__":
    unittest.main()
