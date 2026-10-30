import unittest

from agente.risk import COST_BUFFER, MAX_WEIGHT, check_weights


def account(**kw):
    a = {"equity": 100.0, "peak": 100.0, "day_start": 100.0, "halted": False}
    a.update(kw)
    return a


class RiskGate(unittest.TestCase):
    def test_halted_goes_to_cash(self):
        w, why = check_weights(account(halted=True), {"A": 0.5}, {"A": 0.5})
        self.assertEqual(w, {})
        self.assertIn("parado", why)

    def test_max_drawdown_goes_to_cash(self):
        w, why = check_weights(account(equity=75.0, day_start=75.0), {"A": 0.5}, {})
        self.assertEqual(w, {})
        self.assertIn("drawdown", why)

    def test_daily_loss_blocks_increases_but_allows_cuts(self):
        a = account(equity=95.0)
        w, why = check_weights(a, {"A": 0.5, "B": 0.1}, {"A": 0.2, "B": 0.3})
        self.assertEqual(w, {"A": 0.2, "B": 0.1})
        self.assertIn("diária", why)

    def test_caps_single_coin_weight(self):
        w, _ = check_weights(account(), {"A": 0.9}, {})
        self.assertAlmostEqual(w["A"], MAX_WEIGHT)

    def test_no_leverage(self):
        w, _ = check_weights(account(), {"A": 0.5, "B": 0.5, "C": 0.5}, {})
        self.assertLessEqual(sum(w.values()), 1 / COST_BUFFER + 1e-12)

    def test_normal_weights_pass_unchanged(self):
        w, why = check_weights(account(), {"A": 0.3, "B": 0.2}, {})
        self.assertEqual(w, {"A": 0.3, "B": 0.2})
        self.assertEqual(why, "aprovado")


if __name__ == "__main__":
    unittest.main()
