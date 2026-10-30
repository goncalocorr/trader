import unittest

from agente import paper
from agente.desk import decide, window
from tests.helpers import DAY, bars, falling, rising


class Desk(unittest.TestCase):
    def test_window_aligns_closes_and_drops_coins_with_long_gaps(self):
        full = bars(rising(20))
        w = window({"A": full, "B": full[:5] + full[12:]}, 19 * DAY, n=10)
        self.assertEqual(len(w["A"]), 10)
        self.assertNotIn("B", w)

    def test_window_tolerates_a_missing_day(self):
        full = bars(rising(10))
        self.assertIn("B", window({"B": full[:5] + full[6:]}, 9 * DAY, n=5))

    def test_window_drops_coins_with_bad_prices(self):
        full = bars(rising(10))
        full[7] = (full[7][0], 0, 0, 0, 0.0, 0)
        self.assertNotIn("A", window({"A": full}, 9 * DAY, n=5))

    def test_buys_in_a_good_regime_and_logs_every_step(self):
        acc = paper.new_account(1000.0)
        rec = decide(acc, {"BTCUSDT": rising(), "A": rising()}, t=0)
        for key in ("t", "regime", "target", "skeptic", "mc", "risk", "fills"):
            self.assertIn(key, rec)
        self.assertTrue(rec["regime"])
        self.assertIn("A", acc["positions"])

    def test_bad_regime_sells_everything(self):
        acc = paper.new_account(1000.0)
        decide(acc, {"BTCUSDT": rising(), "A": rising()}, t=0)
        rec = decide(acc, {"BTCUSDT": falling(), "A": rising()}, t=DAY)
        self.assertFalse(rec["regime"])
        self.assertEqual(acc["positions"], {})

    def test_halted_account_stays_in_cash(self):
        acc = paper.new_account(1000.0)
        acc["halted"] = True
        decide(acc, {"BTCUSDT": rising(), "A": rising()}, t=0)
        self.assertEqual(acc["positions"], {})


if __name__ == "__main__":
    unittest.main()
