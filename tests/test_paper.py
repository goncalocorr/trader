import unittest

from agente import paper

DAY = 86_400_000  # ms


def acc_with_position(stop=95.0, target=110.0):
    a = paper.new_account(1000.0)
    paper.open_position(a, "BTCUSDT", qty=1.0, price=100.0, stop=stop, target=target, t=0)
    return a


class Paper(unittest.TestCase):
    def test_open_pays_price_slippage_and_fee(self):
        a = acc_with_position()
        fill = 100.0 * (1 + paper.SLIP)
        self.assertAlmostEqual(a["cash"], 1000.0 - fill * (1 + paper.FEE))
        self.assertAlmostEqual(a["positions"]["BTCUSDT"]["entry"], fill)

    def test_stop_exit(self):
        a = acc_with_position()
        tr = paper.on_bar(a, "BTCUSDT", (1, 99, 101, 94, 96, 1))
        self.assertEqual(tr["exit_reason"], "stop")
        self.assertAlmostEqual(tr["exit"], 95.0 * (1 - paper.SLIP))
        self.assertNotIn("BTCUSDT", a["positions"])

    def test_gap_through_stop_fills_at_open(self):
        a = acc_with_position()
        tr = paper.on_bar(a, "BTCUSDT", (1, 90, 91, 89, 90, 1))
        self.assertAlmostEqual(tr["exit"], 90.0 * (1 - paper.SLIP))

    def test_target_exit(self):
        a = acc_with_position()
        tr = paper.on_bar(a, "BTCUSDT", (1, 101, 111, 100, 109, 1))
        self.assertEqual(tr["exit_reason"], "alvo")

    def test_stop_before_target_in_same_bar(self):
        a = acc_with_position()
        self.assertEqual(paper.on_bar(a, "BTCUSDT", (1, 100, 111, 94, 100, 1))["exit_reason"], "stop")

    def test_time_exit_after_max_bars(self):
        a = acc_with_position()
        tr = None
        for i in range(paper.MAX_BARS):
            tr = paper.on_bar(a, "BTCUSDT", (i, 100, 101, 99, 100, 1))
        self.assertEqual(tr["exit_reason"], "tempo")

    def test_round_trip_profit_counts_fees(self):
        a = acc_with_position()
        paper.on_bar(a, "BTCUSDT", (1, 101, 111, 100, 109, 1))
        self.assertLess(a["cash"], 1010.0)
        self.assertGreater(a["cash"], 1009.0)

    def test_mark_tracks_equity_peak_and_new_day(self):
        a = acc_with_position()
        paper.mark(a, {"BTCUSDT": 120.0}, t=DAY + 1)
        self.assertAlmostEqual(a["equity"], a["cash"] + 120.0)
        self.assertEqual(a["peak"], a["equity"])
        self.assertEqual(a["day_start"], a["equity"])

    def test_mark_halts_on_max_drawdown(self):
        a = paper.new_account(100.0)
        paper.open_position(a, "BTCUSDT", qty=0.9, price=100.0, stop=50.0, target=200.0, t=0)
        paper.mark(a, {"BTCUSDT": 100.0}, t=0)
        self.assertFalse(a["halted"])
        paper.mark(a, {"BTCUSDT": 70.0}, t=1)  # equity ~73, more than 25% below the ~100 peak
        self.assertTrue(a["halted"])


if __name__ == "__main__":
    unittest.main()
